"""Holograms over the lounge table and the wall screens, for The Ring of Gyges III.

Every hologram is one object of glowing parts whose material has a keyable 'Power' value; it blooms in and out
by scale. The wall screens share one material that blends three pictures (raid footage, network traffic, dawn)."""
import math
import random

import bpy
from mathutils import Matrix, Quaternion, Vector

from kit import capsule, hexc, lathe, ring, sphere, static, tube

V = Vector
CENTRE = V((0.0, 0.05, 1.42))


def glow(name, colour, strength=3.0, pulse=0.0):
    """An emission material with a keyable Power value; pulse > 0 adds a slow travelling flicker."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in [n for n in nt.nodes if n.type != 'OUTPUT_MATERIAL']:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = hexc(colour)
    pw = nt.nodes.new('ShaderNodeValue')
    pw.name = pw.label = 'Power'
    pw.outputs[0].default_value = strength
    if pulse:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.noise_dimensions = '4D'
        nz.name = 'Pulse'
        nz.inputs['Scale'].default_value = 3.0
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        rp = nt.nodes.new('ShaderNodeMapRange')
        rp.inputs['From Min'].default_value, rp.inputs['From Max'].default_value = 0.35, 0.7
        rp.inputs['To Min'].default_value, rp.inputs['To Max'].default_value = 1.0 - pulse, 1.0 + pulse
        nt.links.new(nz.outputs['Fac'], rp.inputs['Value'])
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        nt.links.new(rp.outputs['Result'], mul.inputs[0])
        nt.links.new(pw.outputs[0], mul.inputs[1])
        nt.links.new(mul.outputs[0], e.inputs['Strength'])
    else:
        nt.links.new(pw.outputs[0], e.inputs['Strength'])
    nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m


def power(mat, frame, value):
    n = mat.node_tree.nodes['Power']
    n.outputs[0].default_value = value
    n.outputs[0].keyframe_insert('default_value', frame=frame)


def pulse_clock(mat, frames, speed=0.25):
    """Make a pulsing material flicker over the whole timeline (linear keys on the noise's W)."""
    nz = mat.node_tree.nodes.get('Pulse')
    if not nz:
        return
    for f, w in ((0, 0.0), (frames, frames / 24 * speed)):
        nz.inputs['W'].default_value = w
        nz.inputs['W'].keyframe_insert('default_value', frame=f)
    for fc in mat.node_tree.animation_data.action.fcurves if hasattr(mat.node_tree.animation_data.action, 'fcurves') else []:
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'


def holder(name, parts):
    ob = static(name, parts)
    ob.location = CENTRE
    for v in ob.data.vertices:
        v.co -= CENTRE
    ob.scale = (0.0, 0.0, 0.0)
    return ob


def web(rng=None):
    """Sequence One: a sprawling, chaotic data visualization."""
    rng = rng or random.Random(5)
    node = glow('Holo web nodes', '#7fe8ff', 6.0, pulse=0.8)
    link = glow('Holo web links', '#3cb4ff', 2.5, pulse=0.6)
    hot = glow('Holo web hot', '#ff6a5a', 7.0, pulse=0.9)
    pts = []
    while len(pts) < 70:
        p = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if p.length <= 1:
            pts.append(CENTRE + V((p.x * 0.42, p.y * 0.3, p.z * 0.26)))
    parts = []
    for i, p in enumerate(pts):
        parts.append((sphere(p, 0.012 if i % 7 else 0.02, seg=10, rings=6), hot if i % 11 == 0 else node))
        near = sorted(range(len(pts)), key=lambda j: (pts[j] - p).length)[1:3 + (i % 2)]
        for j in near:
            if j > i or i % 3 == 0:
                parts.append((tube([p, pts[j]], 0.0025, seg=5, caps=False), link))
    return holder('Holo web', parts), (node, link, hot)


def network(rng=None):
    """Sequence Two: the underlying architecture: nodes on shells, pulsing, linked."""
    rng = rng or random.Random(9)
    node = glow('Holo net nodes', '#9ff7ff', 6.0, pulse=0.7)
    link = glow('Holo net links', '#35d0c8', 2.2, pulse=0.5)
    core = glow('Holo net core', '#ffffff', 8.0, pulse=0.4)
    pts = []
    n = 64
    for i in range(n):          # a fibonacci sphere, then a smaller one inside
        y = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - y * y)
        a = i * math.pi * (3 - math.sqrt(5))
        pts.append(CENTRE + V((math.cos(a) * r * 0.4, math.sin(a) * r * 0.3, y * 0.28)))
    inner = [CENTRE + V((0.16 * math.cos(2 * math.pi * k / 8), 0.12 * math.sin(2 * math.pi * k / 8), 0.06 * (-1) ** k)) for k in range(8)]
    parts = [(sphere(CENTRE, 0.045, seg=16, rings=10), core)]
    for p in pts:
        parts.append((sphere(p, 0.011, seg=10, rings=6), node))
        for j in sorted(range(len(pts)), key=lambda j: (pts[j] - p).length)[1:4]:
            parts.append((tube([p, pts[j]], 0.002, seg=5, caps=False), link))
    for k, q in enumerate(inner):
        parts.append((sphere(q, 0.016, seg=10, rings=6), node))
        parts.append((tube([CENTRE, q], 0.003, seg=5, caps=False), link))
        parts.append((tube([q, pts[(k * 8) % n]], 0.0022, seg=5, caps=False), link))
    return holder('Holo network', parts), (node, link, core)


def brain(rng=None):
    """Sequence Three: a rotating schematic of the human nervous system, its prefrontal cortex a separate part."""
    rng = rng or random.Random(13)
    shell = glow('Holo brain shell', '#7fb8ff', 1.6, pulse=0.3)
    nerve = glow('Holo brain nerves', '#a8d8ff', 3.2, pulse=0.7)
    pfc_m = glow('Holo PFC', '#ffb347', 2.0, pulse=0.35)
    C = CENTRE + V((0, 0, 0.05))
    parts = []
    for s in (-1, 1):           # two hemispheres as glowing latitude and longitude rings
        hc = C + V((s * 0.085, 0.0, 0.0))
        for k in range(7):
            z = -0.11 + 0.035 * k
            r = math.sqrt(max(0.0, 1 - (z / 0.15) ** 2))
            parts.append((ring(hc + V((0, 0, z)), 1.0, 0.0022, rot=Matrix.Diagonal((0.075 * r, 0.21 * r, 1)), seg=40, tseg=4), shell))
        for k in range(6):
            a = math.pi * k / 6
            pts = [hc + V((0.08 * math.sin(t) * math.cos(a) * 0.95, 0.21 * math.cos(t), 0.15 * math.sin(t) * math.sin(a) + 0.0)) for t in [math.pi * i / 20 for i in range(21)]]
            parts.append((tube(pts, 0.0022, seg=4, caps=False), shell))
    stem = [C + V((0, 0.07, -0.08)), C + V((0, 0.09, -0.2)), C + V((0, 0.08, -0.33))]
    parts.append((tube(stem, [0.018, 0.014, 0.01], seg=8), nerve))
    for k in range(26):         # neurons branching through the brain
        a = V((rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.17), rng.uniform(-0.09, 0.11)))
        b = a + V((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), rng.uniform(-0.05, 0.05)))
        parts.append((tube([C + a, C + (a + b) / 2 + V((0, 0, 0.01)), C + b], 0.0018, seg=4, caps=False), nerve))
        parts.append((sphere(C + a, 0.007, seg=8, rings=5), nerve))
    body = holder('Holo brain', parts)
    # the prefrontal cortex: the front of both hemispheres, glowing, with branching dendrites
    P = C + V((0, -0.16, 0.03))
    pp = [(sphere(P, (0.13, 0.06, 0.09), seg=24, rings=14), pfc_m)]
    for k in range(18):
        d = V((rng.uniform(-1, 1), rng.uniform(-1, 0.3), rng.uniform(-0.6, 1))).normalized()
        a = P + V((d.x * 0.1, d.y * 0.05, d.z * 0.07))
        b = a + d * rng.uniform(0.04, 0.08)
        c2 = b + (d + V((rng.uniform(-0.6, 0.6), 0, rng.uniform(-0.6, 0.6)))).normalized() * 0.04
        pp.append((tube([a, b, c2], [0.004, 0.003, 0.0015], seg=5, caps=False), pfc_m))
    pfc = static('Holo PFC', pp)
    pfc.parent = body
    for v in pfc.data.vertices:
        v.co -= P
    pfc.location = P - CENTRE
    return body, pfc, (shell, nerve, pfc_m)


def crystal():
    """Sequence Four: the crystalline protocol of the Mirror Force: nested faceted frames round a mirror core."""
    edge = glow('Holo crystal edges', '#dff6ff', 4.5, pulse=0.3)
    edge2 = glow('Holo crystal inner', '#8fe3ff', 3.5, pulse=0.5)
    mirror = bpy.data.materials.new('Holo mirror core')
    mirror.use_nodes = True
    b = next(n for n in mirror.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.04
    b.inputs['Base Color'].default_value = hexc('#e8f4ff')
    phi = (1 + 5 ** 0.5) / 2
    ico = [V(v).normalized() for v in [(-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0), (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi), (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)]]
    edges = {(i, j) for i in range(12) for j in range(i + 1, 12) if abs((ico[i] - ico[j]).length - 1.0515) < 0.01}
    octa = [V(v) for v in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
    oedges = {(i, j) for i in range(6) for j in range(i + 1, 6) if abs((octa[i] - octa[j]).length - 2 ** 0.5) < 0.01}
    parts = []
    R = 0.27
    for i, j in edges:
        parts.append((capsule(CENTRE + ico[i] * R, CENTRE + ico[j] * R, 0.0045, seg=6, cap=2), edge))
    for p in ico:
        parts.append((sphere(CENTRE + p * R, 0.012, seg=10, rings=6), edge))
    outer = holder('Holo crystal', parts)
    ip = []
    for i, j in oedges:
        ip.append((capsule(CENTRE + octa[i] * 0.15, CENTRE + octa[j] * 0.15, 0.004, seg=6, cap=2), edge2))
    ip.append((sphere(CENTRE, 0.075, seg=24, rings=16), mirror))
    inner = static('Holo crystal core', ip)
    for v in inner.data.vertices:
        v.co -= CENTRE
    inner.parent = outer
    return outer, inner, (edge, edge2)


def screens_material(news_path):
    """One material for the wall screens: raid footage, network traffic and dawn, mixed by keyable values Net and Dawn,
    all scaled by Power."""
    m = bpy.data.materials.new('Screens')
    m.use_nodes = True
    nt = m.node_tree
    for n in [n for n in nt.nodes if n.type != 'OUTPUT_MATERIAL']:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    L = nt.links.new

    def value(name, v):
        n = nt.nodes.new('ShaderNodeValue')
        n.name = n.label = name
        n.outputs[0].default_value = v
        return n

    net, dawn, pw = value('Net', 0.0), value('Dawn', 0.0), value('Power', 1.3)
    # the raid footage, tinted cool
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(news_path)
    tex.image.pack()
    tex.extension = 'CLIP'
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    L(tex.outputs['Color'], bw.inputs[0])
    r1 = nt.nodes.new('ShaderNodeValToRGB')
    r1.color_ramp.elements[0].position, r1.color_ramp.elements[0].color = 0.0, (0.01, 0.025, 0.05, 1)
    r1.color_ramp.elements[1].position, r1.color_ramp.elements[1].color = 0.85, hexc('#58d6ff')
    L(bw.outputs[0], r1.inputs['Fac'])
    # network traffic: cells of a moving Voronoi pattern with bright edges
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vo = nt.nodes.new('ShaderNodeTexVoronoi')
    vo.voronoi_dimensions = '4D'
    vo.feature = 'DISTANCE_TO_EDGE'
    vo.name = 'Traffic'
    vo.inputs['Scale'].default_value = 22.0
    L(tc.outputs['UV'], vo.inputs['Vector'])
    r2 = nt.nodes.new('ShaderNodeValToRGB')
    r2.color_ramp.elements[0].position, r2.color_ramp.elements[0].color = 0.0, hexc('#6fe0f0')
    r2.color_ramp.elements[1].position, r2.color_ramp.elements[1].color = 0.035, (0.01, 0.03, 0.06, 1)
    L(vo.outputs['Distance'], r2.inputs['Fac'])
    # dawn: a warm horizon under a pale sky
    gr = nt.nodes.new('ShaderNodeSeparateXYZ')
    L(tc.outputs['UV'], gr.inputs[0])
    r3 = nt.nodes.new('ShaderNodeValToRGB')
    r3.color_ramp.elements[0].position, r3.color_ramp.elements[0].color = 0.0, hexc('#ff8a3d')
    r3.color_ramp.elements[1].position, r3.color_ramp.elements[1].color = 0.75, hexc('#9fc6e8')
    L(gr.outputs['Y'], r3.inputs['Fac'])

    def mix(a, b, fac):
        n = nt.nodes.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        L(fac, n.inputs['Factor'])
        L(a, n.inputs['A'])
        L(b, n.inputs['B'])
        return n.outputs['Result']

    c = mix(mix(r1.outputs['Color'], r2.outputs['Color'], net.outputs[0]), r3.outputs['Color'], dawn.outputs[0])
    e = nt.nodes.new('ShaderNodeEmission')
    L(c, e.inputs['Color'])
    L(pw.outputs[0], e.inputs['Strength'])
    L(e.outputs[0], out.inputs['Surface'])
    return m


def key_value(mat, name, frame, v):
    n = mat.node_tree.nodes[name]
    n.outputs[0].default_value = v
    n.outputs[0].keyframe_insert('default_value', frame=frame)
