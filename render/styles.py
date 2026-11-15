"""Rigroom render server: render styles.

A job's "style" picks how the same scene is drawn:

    photoreal     Cycles path tracing with real surfaces, light, haze and lens (the default)
    black-figure  Greek black-figure vase painting with neon outlines, as in The Ring of Gyges, Chapter 1:
                  black figures outlined in each character's colour on terracotta; the speaker's outline glows
    cel           cartoon: the people's own colours in flat bands of light and shade, with ink outlines
    sketch        pencil on paper: graphite lines and hatched shadows
    clay          a matte clay maquette under the scene's lights
    edward        Edward's style (from his booth storyboard): a grey page, the set laid in with blue construction
                  lines that overshoot their corners and show through the figures, the people drawn over it in loose
                  charcoal with hatching on dark clothes; the speaker is drawn with a heavier line

Every style but photoreal is drawn with Eevee, which is many times faster. "style_colors" in the job
can set a character's outline colour: { "Socrates": "#ffc04d" }.
"""
import math

import bpy

from surfaces import Graph, hex_to_linear

STYLES = ('photoreal', 'black-figure', 'cel', 'sketch', 'clay', 'edward')
NEON = {'Socrates': '#ffc04d', 'Aria': '#3fe0ff', 'Cleon': '#ff3fa4', 'Julian': '#9dff5a'}
EXTRA = ['#ffd1f5', '#ffe08a', '#8ad9ff', '#c9ff8a']


def fresh(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    out = nt.nodes.get('Material Output')
    for n in [n for n in nt.nodes if n != out]:
        nt.nodes.remove(n)
    return mat, Graph(nt), out


def flat(name, col, strength=1.0):
    mat, g, out = fresh(name)
    e = g.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = col
    e.inputs['Strength'].default_value = strength
    g.set(out.inputs['Surface'], e.outputs[0])
    return mat


def setmat(ob, mat):
    if ob.data.materials:
        ob.data.materials[0] = mat
    else:
        ob.data.materials.append(mat)


def luma(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def toon_light(g, ramp):
    """Eevee only: how lit a surface is, cut into flat bands. ramp: [(position, value), ...]."""
    d = g.new('ShaderNodeBsdfDiffuse')
    d.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = g.new('ShaderNodeShaderToRGB')
    g.set(s2r.inputs[0], d.outputs[0])
    bw = g.new('ShaderNodeRGBToBW')
    g.set(bw.inputs[0], s2r.outputs['Color'])
    cr = g.new('ShaderNodeValToRGB')
    cr.color_ramp.interpolation = 'CONSTANT'
    els = cr.color_ramp.elements
    while len(els) > 1:
        els.remove(els[-1])
    els[0].position, els[0].color = ramp[0][0], (ramp[0][1],) * 3 + (1,)
    for p, v in ramp[1:]:
        e = els.new(p)
        e.color = (v, v, v, 1)
    g.set(cr.inputs[0], bw.outputs[0])
    return cr.outputs['Color']


# ───────── what is what ─────────

def classify(scene, job):
    """Sort the scene's meshes: people (by character), props (by their surface), the floor, the haze."""
    names = [e['name'] for e in (job.get('scene') or {}).get('ents', []) if e.get('kind') == 'mannequin']
    people, props = {}, []
    floor = haze = None
    for ob in scene.objects:
        if ob.type != 'MESH':
            continue
        if ob.name == 'Haze':
            haze = ob
            continue
        if ob.name.startswith('Floor'):
            floor = ob
            continue
        if ob.find_armature():
            who, p = None, ob
            while p is not None and who is None:   # the character's group is named after it
                base = p.name.split('.')[0]
                who = base if base in names else None
                p = p.parent
            people.setdefault(who or 'Someone', []).append(ob)
            continue
        m = ob.data.materials[0] if ob.data.materials else None
        kind = 'plain'
        if m:
            if m.name.startswith('Surface '):
                kind = m.name.split(' ')[1]
            elif m.name.startswith('Screen '):
                kind = 'screen'
        props.append((ob, kind, m))
    return people, props, floor, haze


def base_colour(mat):
    """The colour a prop was given in the app, read back from its surface."""
    if not mat or not mat.node_tree:
        return (0.5, 0.5, 0.5, 1.0)
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            s = n.inputs['Base Color']
            if not s.is_linked:
                return tuple(s.default_value)
        if n.type == 'EMISSION':
            return tuple(n.inputs['Color'].default_value)
    # a procedural surface: the colours are in its mixes; take the first constant one
    for n in mat.node_tree.nodes:
        if n.type == 'MIX':
            for s in n.inputs:
                if s.type == 'RGBA' and not s.is_linked:
                    return tuple(s.default_value)
    return (0.5, 0.5, 0.5, 1.0)


def scan_texture(mat):
    """A scanned person's colour picture, if the material has one."""
    if not mat or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image and any(l.to_socket.name == 'Base Color' or l.to_node.type == 'SEPARATE_COLOR' for l in n.outputs['Color'].links):
            return n.image
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            return n.image
    return None


# ───────── lines ─────────

def lines_on(scene):
    r = scene.render
    r.use_freestyle = True
    r.line_thickness_mode = 'RELATIVE'   # lines scale with the frame size (measured at 1080 lines)
    vl = scene.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = math.radians(128)
    fs.use_culling = True
    fs.use_smoothness = True
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    return fs


def lineset(fs, name, coll, colour, thickness, alpha=1.0, crease=False, edges=('silhouette', 'border'), sketchy=0.0, min_length=0.0, hidden=False, overshoot=0.0):
    ls = fs.linesets.new(name)
    ls.select_by_visibility = True
    ls.visibility = 'HIDDEN' if hidden else 'VISIBLE'
    ls.select_by_edge_types = True
    for k in ('silhouette', 'border', 'crease', 'contour', 'external_contour', 'material_boundary'):
        setattr(ls, 'select_' + k, k in edges or (k == 'crease' and crease))
    if coll is not None:
        ls.select_by_collection = True
        ls.collection = coll
    st = bpy.data.linestyles.new(name)
    st.color = colour[:3]
    st.alpha = alpha
    st.thickness = thickness
    st.caps = 'ROUND'
    st.chaining = 'PLAIN'
    if min_length:   # scans are full of tiny folds: strokes shorter than this are left out
        st.use_length_min = True
        st.length_min = min_length
    # Freestyle's backbone stretcher can fail on strokes made by sketchy chaining, and a failure drops the whole
    # line set from that frame: so a line set either goes over its strokes several times, or runs them on, never both
    if sketchy and not overshoot:
        st.use_chaining = True
        st.chaining = 'SKETCHY'
        st.rounds = 3
    if sketchy:
        n = st.geometry_modifiers.new('Wobble', 'PERLIN_NOISE_1D')
        n.frequency, n.amplitude = 4.0, sketchy
        t = st.thickness_modifiers.new('Pressure', 'ALONG_STROKE')
        t.mapping = 'CURVE'
        t.influence = 0.8
    if overshoot:   # construction lines run on past the corner, as a ruler stroke does
        st.geometry_modifiers.new('Run on', 'BACKBONE_STRETCHER').backbone_length = overshoot
    ls.linestyle = st
    return ls


def group(name, objs):
    coll = bpy.data.collections.new(name)
    for ob in objs:
        coll.objects.link(ob)
    return coll


def speaking(job):
    """[(character, first frame, last frame)] from the job's speaker cues."""
    cues = (job.get('speaker_light') or {}).get('speakers') or []
    return [(c.get('who'), int(c['f0']), int(c['f1'])) for c in cues if c.get('who')]


def key_emphasis(style, cues, who, low, high, prop):
    """Animate a line style property up while the character speaks: fade over 6 frames in, 10 out."""
    setattr(style, prop, low)
    style.keyframe_insert(prop, frame=0)
    for w, f0, f1 in cues:
        if w != who:
            continue
        for f, v in ((f0 - 6, low), (f0, high), (f1, high), (f1 + 10, low)):
            setattr(style, prop, v)
            style.keyframe_insert(prop, frame=max(0, f))


# ───────── the engine ─────────

def use_eevee(scene, job, samples=None):
    r = scene.render
    r.engine = 'BLENDER_EEVEE'
    ee = scene.eevee
    ee.taa_render_samples = int(samples or max(8, min(64, int(job.get('samples', 24)))))
    for k, v in (('use_shadows', True), ('use_raytracing', False), ('use_gtao', True), ('use_volumetric_shadows', False)):
        if hasattr(ee, k):
            setattr(ee, k, v)
    r.use_motion_blur = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'


def world_colour(scene, top, bottom):
    w = bpy.data.worlds.new('Style world')
    w.use_nodes = True
    g = Graph(w.node_tree)
    bg = w.node_tree.nodes.get('Background')
    sep = g.new('ShaderNodeSeparateXYZ')
    g.set(sep.inputs[0], g.new('ShaderNodeTexCoord').outputs['Generated'])
    g.set(bg.inputs['Color'], g.mix(g.remap(sep.outputs['Z'], 0.45, 0.62, smooth=True), bottom, top))
    bg.inputs['Strength'].default_value = 1.0
    scene.world = w


# ───────── the styles ─────────

def black_figure(scene, job, people, props, floor):
    TERRA, DARK, RED, CREAM = hex_to_linear('#c96a34'), hex_to_linear('#1a0d0a'), hex_to_linear('#5e2620'), hex_to_linear('#ead7b0')
    world_colour(scene, hex_to_linear('#2a1240'), hex_to_linear('#d9733a'))
    for ob, kind, m in props:
        col = base_colour(m)
        if kind in ('neon', 'glow'):
            setmat(ob, flat('BF neon ' + ob.name, col, 5.0 if kind == 'neon' else 3.0))
        elif kind == 'screen':
            continue
        elif kind in ('brick', 'plaster') and ob.dimensions.z < 0.5 and ob.matrix_world.translation.z > 2.2:
            setmat(ob, flat('BF ceiling ' + ob.name, DARK))
        elif kind in ('brick', 'plaster') and ob.dimensions.z > 1.5:
            # walls are the clay ground of the vase: warm terracotta, darker toward the floor
            mat, g, out = fresh('BF wall ' + ob.name)
            sep = g.new('ShaderNodeSeparateXYZ')
            g.set(sep.inputs[0], g.new('ShaderNodeTexCoord').outputs['Generated'])
            tone = g.mix(g.remap(sep.outputs['Z'], 0.0, 0.8, smooth=True), (TERRA[0] * .45, TERRA[1] * .4, TERRA[2] * .4, 1), TERRA)
            tone = g.mix(g.remap(g.noise(0.6, 3.0, 0.5), 0.3, 0.8, 0.0, 0.25), tone, (TERRA[0] * 1.15, TERRA[1] * .95, TERRA[2] * .8, 1))
            e = g.new('ShaderNodeEmission')
            g.set(e.inputs['Color'], tone)
            g.set(out.inputs['Surface'], e.outputs[0])
            setmat(ob, mat)
        elif kind == 'velvet' and ob.dimensions.z > 2.5:   # drapes hang like dark cloth against the clay
            setmat(ob, flat('BF drape ' + ob.name, RED))
        elif kind in ('ceramic', 'paper') or luma(col) > 0.45:
            setmat(ob, flat('BF cream ' + ob.name, CREAM))
        else:
            k = min(1.0, luma(col) * 3.0)
            setmat(ob, flat('BF figure ' + ob.name, tuple(DARK[i] + (RED[i] - DARK[i]) * k for i in range(3)) + (1,)))
    if floor:
        setmat(floor, flat('BF floor', hex_to_linear('#24110d')))
    black = flat('BF people', hex_to_linear('#120a08'))
    fs = lines_on(scene)
    cues = speaking(job)
    colours = dict(NEON, **(job.get('style_colors') or {}))
    for i, (who, obs) in enumerate(sorted(people.items())):
        for ob in obs:
            for j in range(len(ob.data.materials)):
                ob.data.materials[j] = black
        coll = group('Figure ' + who, obs)
        col = hex_to_linear(colours.get(who, EXTRA[i % len(EXTRA)]))
        lineset(fs, who + ' incised', coll, hex_to_linear('#c97a48'), 0.9, 0.8, crease=True, edges=(), min_length=10)
        lineset(fs, who + ' outline', coll, col, 2.6)
        glow = lineset(fs, who + ' glow', coll, col, 9.0, 0.22)
        key_emphasis(glow.linestyle, cues, who, 0.18, 0.55, 'alpha')
        key_emphasis(glow.linestyle, cues, who, 8.0, 16.0, 'thickness')
    setcoll = group('Set', [ob for ob, kind, m in props if kind not in ('neon', 'glow', 'screen')])
    lineset(fs, 'Set outline', setcoll, hex_to_linear('#0d0605'), 1.6)


def cel(scene, job, people, props, floor):
    world_colour(scene, hex_to_linear('#26334d'), hex_to_linear('#57627a'))
    RAMP = [(0.0, 0.42), (0.08, 0.72), (0.45, 1.0)]
    for who, obs in people.items():
        for ob in obs:
            for j, m in enumerate(ob.data.materials):
                img = scan_texture(m)
                mat, g, out = fresh('Cel ' + ob.name + str(j))
                if img:
                    t = g.new('ShaderNodeTexImage')
                    t.image = img
                    g.set(t.inputs['Vector'], g.new('ShaderNodeUVMap').outputs['UV'])
                    hsv = g.new('ShaderNodeHueSaturation')   # flatter, brighter, a little more colour, as drawn
                    hsv.inputs['Saturation'].default_value = 1.25
                    hsv.inputs['Value'].default_value = 1.1
                    g.set(hsv.inputs['Color'], t.outputs['Color'])
                    albedo = hsv.outputs['Color']
                else:
                    albedo = (0.7, 0.55, 0.45, 1)
                e = g.new('ShaderNodeEmission')
                g.set(e.inputs['Color'], g.mix(1.0, albedo, toon_light(g, RAMP), 'MULTIPLY'))
                g.set(out.inputs['Surface'], e.outputs[0])
                ob.data.materials[j] = mat
    for ob, kind, m in props:
        if kind in ('neon', 'glow', 'screen'):
            continue
        col = base_colour(m)
        mat, g, out = fresh('Cel ' + ob.name)
        e = g.new('ShaderNodeEmission')
        g.set(e.inputs['Color'], g.mix(1.0, (min(1, col[0] * 1.3), min(1, col[1] * 1.3), min(1, col[2] * 1.3), 1), toon_light(g, RAMP), 'MULTIPLY'))
        g.set(out.inputs['Surface'], e.outputs[0])
        setmat(ob, mat)
    if floor:
        col = base_colour(floor.data.materials[0])
        setmat(floor, flat('Cel floor', tuple(c * 0.8 for c in col[:3]) + (1,)))
    fs = lines_on(scene)
    allp = [ob for obs in people.values() for ob in obs]
    lineset(fs, 'People ink', group('People', allp), (0.03, 0.025, 0.03, 1), 1.8, crease=True, min_length=8)
    lineset(fs, 'Set ink', group('Set', [ob for ob, k, m in props if k not in ('neon', 'glow')]), (0.03, 0.025, 0.03, 1), 1.4)


def sketch(scene, job, people, props, floor):
    PAPER, TONE = hex_to_linear('#f3eee3'), hex_to_linear('#cfc6b4')
    world_colour(scene, PAPER, PAPER)

    def paper(name):
        mat, g, out = fresh(name)
        lit = toon_light(g, [(0.0, 0.0), (0.25, 0.45), (0.55, 0.8), (0.85, 1.0)])
        # hatching: diagonal pencil strokes fixed to the page, showing through where the light is low
        win = g.new('ShaderNodeTexCoord').outputs['Window']
        wave = g.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL')
        g.set(wave.inputs['Vector'], win)
        wave.inputs['Scale'].default_value = 140.0
        wave.inputs['Distortion'].default_value = 1.2
        strokes = g.remap(wave.outputs['Fac'], 0.55, 0.9)
        shade = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, lit), strokes)
        tone = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, lit), 0.5), PAPER, TONE)
        e = g.new('ShaderNodeEmission')
        g.set(e.inputs['Color'], g.mix(g.math('MULTIPLY', shade, 0.8), tone, hex_to_linear('#6d6a64')))
        g.set(out.inputs['Surface'], e.outputs[0])
        return mat

    p = paper('Sketch paper')
    for obs in people.values():
        for ob in obs:
            for j in range(len(ob.data.materials)):
                ob.data.materials[j] = p
    for ob, kind, m in props:
        setmat(ob, p)
    if floor:
        setmat(floor, flat('Sketch floor', PAPER))
    fs = lines_on(scene)
    allp = [ob for obs in people.values() for ob in obs]
    fs.crease_angle = math.radians(150)
    lineset(fs, 'People pencil', group('People', allp), hex_to_linear('#2f2d2a'), 1.4, 0.9, crease=True, sketchy=1.0, min_length=14)
    lineset(fs, 'Set pencil', group('Set', [ob for ob, k, m in props]), hex_to_linear('#3d3a36'), 1.1, 0.8, sketchy=1.4, min_length=10)


def clay(scene, job, people, props, floor):
    world_colour(scene, hex_to_linear('#8d8a86'), hex_to_linear('#b5b0a8'))
    mat = bpy.data.materials.new('Clay')
    mat.use_nodes = True
    b = mat.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = hex_to_linear('#c7b29a')
    b.inputs['Roughness'].default_value = 0.62
    for obs in people.values():
        for ob in obs:
            for j in range(len(ob.data.materials)):
                ob.data.materials[j] = mat
    for ob, kind, m in props:
        setmat(ob, mat)
    if floor:
        setmat(floor, mat)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -0.6


def edward(scene, job, people, props, floor):
    PAGE, CHARCOAL, BLUE = hex_to_linear('#8b8b8b'), hex_to_linear('#1c1c1e'), hex_to_linear('#2b59d9')
    world_colour(scene, PAGE, PAGE)
    page = flat('Edward page', PAGE)

    def hatched(name, img):
        """The page, with charcoal hatching where the scan's clothes or hair are dark."""
        mat, g, out = fresh(name)
        t = g.new('ShaderNodeTexImage')
        t.image = img
        g.set(t.inputs['Vector'], g.new('ShaderNodeUVMap').outputs['UV'])
        bw = g.new('ShaderNodeRGBToBW')
        g.set(bw.inputs[0], t.outputs['Color'])
        dark = g.remap(bw.outputs[0], 0.16, 0.06, smooth=True)
        wave = g.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='DIAGONAL')
        g.set(wave.inputs['Vector'], g.new('ShaderNodeTexCoord').outputs['Window'])
        wave.inputs['Scale'].default_value = 90.0
        wave.inputs['Distortion'].default_value = 2.5
        wave.inputs['Detail'].default_value = 1.0
        strokes = g.remap(wave.outputs['Fac'], 0.82, 0.97)
        e = g.new('ShaderNodeEmission')
        g.set(e.inputs['Color'], g.mix(g.math('MULTIPLY', g.math('MULTIPLY', dark, strokes), 0.75), PAGE, CHARCOAL))
        g.set(out.inputs['Surface'], e.outputs[0])
        return mat

    for obs in people.values():
        for ob in obs:
            for j, m in enumerate(ob.data.materials):
                img = scan_texture(m)
                ob.data.materials[j] = hatched('Edward ' + ob.name + str(j), img) if img else page
    def drawn_screen(ob, m):
        """A screen's picture drawn on the page: its bright parts in charcoal, its dark parts left as page (a negative, the way a sketch shows a lit screen)."""
        tex = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if m and m.node_tree else None
        if not tex:
            return page
        mat = m.copy()
        mat.name = 'Edward screen ' + ob.name
        nt = mat.node_tree
        tex = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image)
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        nt.links.new(tex.outputs['Color'], bw.inputs[0])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.interpolation = 'EASE'
        ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.08, PAGE
        ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.6, CHARCOAL
        nt.links.new(bw.outputs[0], ramp.inputs['Fac'])
        e = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(ramp.outputs['Color'], e.inputs['Color'])
        outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        nt.links.new(e.outputs[0], outn.inputs['Surface'])
        return mat

    for ob, kind, m in props:
        setmat(ob, drawn_screen(ob, m) if kind == 'screen' else page)
    if floor:
        setmat(floor, page)
    fs = lines_on(scene)
    fs.crease_angle = math.radians(134)
    setobs = [ob for ob, k, m in props]
    setcoll = group('Set', setobs)
    # the set: blue ruler lines that run past their corners, and fainter where they pass behind things
    lineset(fs, 'Set blue', setcoll, BLUE, 2.2, 1.0, crease=True, sketchy=0.6, overshoot=14.0, min_length=6)
    lineset(fs, 'Set blue behind', setcoll, BLUE, 1.5, 0.4, crease=False, overshoot=10.0, min_length=12, hidden=True)
    cues = speaking(job)
    for who, obs in sorted(people.items()):
        ls = lineset(fs, who + ' charcoal', group('Figure ' + who, obs), CHARCOAL, 2.6, 1.0, crease=True, sketchy=1.2, min_length=12)
        key_emphasis(ls.linestyle, cues, who, 2.6, 3.8, 'thickness')


def apply(scene, job):
    """Change the built scene to the job's style. Returns the style used."""
    style = job.get('style') or 'photoreal'
    if style not in STYLES:
        print('unknown style %r: rendering photoreal' % style, flush=True)
        style = 'photoreal'
    if style == 'photoreal':
        return style
    people, props, floor, haze = classify(scene, job)
    if haze:
        bpy.data.objects.remove(haze)
    use_eevee(scene, job)
    {'black-figure': black_figure, 'cel': cel, 'sketch': sketch, 'clay': clay, 'edward': edward}[style](scene, job, people, props, floor)
    print('style %s: %d characters (%s), %d props' % (style, len(people), ', '.join(sorted(people)), len(props)), flush=True)
    return style
