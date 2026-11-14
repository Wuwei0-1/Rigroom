"""Rigroom render server: surfaces, lights, environments and lens finishing.

The app exports plain shapes and names each prop's material "rr:<preset>". Here every preset becomes a
full procedural surface (grain, pores, bumps, rounded edges), scanned people get skin that scatters
light, and the frame gets the small flaws of a real lens. Everything is procedural or shipped in
assets/env, so the renderer needs no downloads.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

ENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'env')
SKIES = ('studio', 'interior', 'courtyard', 'city', 'forest', 'sunrise', 'sunset', 'night')


def to_blender(v):
    return Vector((v[0], -v[2], v[1]))


def hex_to_linear(h):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb] + [1.0]


# ───────── a small node-graph builder ─────────

class Graph:
    def __init__(self, tree):
        self.tree, self.nodes, self.links = tree, tree.nodes, tree.links
        self._coords = None

    def new(self, kind, **props):
        n = self.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def set(self, sock, value):
        """Give an input a constant or connect an output to it."""
        if isinstance(value, bpy.types.NodeSocket):
            self.links.new(value, sock)
        elif value is not None:
            sock.default_value = value

    def coords(self):
        if self._coords is None:
            self._coords = self.new('ShaderNodeTexCoord').outputs['Object']
        return self._coords

    def mapping(self, scale=(1, 1, 1), vector=None, location=(0, 0, 0)):
        n = self.new('ShaderNodeMapping')
        self.set(n.inputs['Vector'], vector or self.coords())
        n.inputs['Scale'].default_value = scale
        n.inputs['Location'].default_value = location
        return n.outputs['Vector']

    def noise(self, scale, detail=2.0, rough=0.5, vector=None, distortion=0.0, color=False):
        n = self.new('ShaderNodeTexNoise')
        self.set(n.inputs['Vector'], vector or self.coords())
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = distortion
        return n.outputs['Color' if color else 'Fac']

    def voronoi(self, scale, vector=None, randomness=1.0):
        n = self.new('ShaderNodeTexVoronoi')
        self.set(n.inputs['Vector'], vector or self.coords())
        n.inputs['Scale'].default_value = scale
        n.inputs['Randomness'].default_value = randomness
        return n.outputs['Distance']

    def math(self, op, a, b=None, clamp=False):
        n = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.set(n.inputs[0], a)
        if b is not None:
            self.set(n.inputs[1], b)
        return n.outputs[0]

    def remap(self, value, lo, hi, out_lo=0.0, out_hi=1.0, smooth=False):
        n = self.new('ShaderNodeMapRange')
        if smooth:
            n.interpolation_type = 'SMOOTHSTEP'
        self.set(n.inputs['Value'], value)
        for name, v in (('From Min', lo), ('From Max', hi), ('To Min', out_lo), ('To Max', out_hi)):
            n.inputs[name].default_value = v
        return n.outputs['Result']

    def mix(self, fac, a, b, blend='MIX'):
        n = self.new('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        ins = {s.identifier: s for s in n.inputs}
        self.set(ins['Factor_Float'], fac)
        self.set(ins['A_Color'], a)
        self.set(ins['B_Color'], b)
        return next(s for s in n.outputs if s.identifier == 'Result_Color')

    def planar(self, u_axis, v_axis):
        """Object coordinates laid flat: u along one local axis, v along another (for bricks and boards)."""
        sep = self.new('ShaderNodeSeparateXYZ')
        self.set(sep.inputs[0], self.coords())
        comb = self.new('ShaderNodeCombineXYZ')
        self.set(comb.inputs[0], sep.outputs[u_axis])
        self.set(comb.inputs[1], sep.outputs[v_axis])
        return comb.outputs[0]

    def bump(self, height, distance, normal=None, strength=1.0):
        n = self.new('ShaderNodeBump')
        n.inputs['Strength'].default_value = strength
        n.inputs['Distance'].default_value = distance
        self.set(n.inputs['Height'], height)
        if normal is not None:
            self.set(n.inputs['Normal'], normal)
        return n.outputs['Normal']

    def bevel(self, radius):
        if os.environ.get('RR_NOBEVEL'):
            return None
        n = self.new('ShaderNodeBevel', samples=int(os.environ.get('RR_BEVEL', 4)))
        n.inputs['Radius'].default_value = radius
        return n.outputs['Normal']


def shade(col, k):
    return (col[0] * k, col[1] * k, col[2] * k, 1.0)


def fresh(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    g = Graph(mat.node_tree)
    return mat, g, g.nodes.get('Principled BSDF')


# ───────── prop surfaces ─────────

def surface(preset, col, dims, name):
    """A material for one prop. col is its linear RGBA colour, dims its size in meters (local axes)."""
    mat, g, b = fresh(name)
    I = b.inputs
    edge = min(0.006, 0.12 * min(dims))  # every real edge is a little round
    normal = g.bevel(edge)

    if preset == 'wood':
        axis = max(range(3), key=lambda i: dims[i])
        stretch = [14.0, 14.0, 14.0]
        stretch[axis] = 1.0
        grain_v = g.mapping(stretch)
        rings = g.noise(2.2, 5.0, 0.6, grain_v, distortion=1.2)
        fine = g.noise(40.0, 3.0, 0.5, g.mapping([s * 6 for s in stretch]))
        tone = g.mix(g.remap(rings, 0.3, 0.75, smooth=True), shade(col, 0.62), shade(col, 1.18))
        g.set(I['Base Color'], g.mix(g.remap(fine, 0.35, 0.7), tone, shade(col, 0.8)))
        g.set(I['Roughness'], g.remap(fine, 0.2, 0.8, 0.3, 0.5))
        I['Coat Weight'].default_value = 0.25
        I['Coat Roughness'].default_value = 0.18
        normal = g.bump(fine, 0.0004, g.bump(rings, 0.0006, normal))
    elif preset == 'leather':
        cloud = g.noise(5.0, 4.0, 0.55)
        pores = g.voronoi(700.0)
        creases = g.noise(38.0, 5.0, 0.6, distortion=0.6)
        g.set(I['Base Color'], g.mix(g.remap(cloud, 0.3, 0.75), shade(col, 0.72), shade(col, 1.1)))
        g.set(I['Roughness'], g.remap(cloud, 0.2, 0.8, 0.36, 0.56))
        I['Coat Weight'].default_value = 0.12
        I['Coat Roughness'].default_value = 0.35
        I['Sheen Weight'].default_value = 0.08
        normal = g.bump(pores, 0.0005, g.bump(creases, 0.0018, normal))
    elif preset == 'fabric':
        cloud = g.noise(9.0, 3.0, 0.5)
        warp = g.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X')
        weft = g.new('ShaderNodeTexWave', wave_type='BANDS', bands_direction='Y')
        for w in (warp, weft):
            g.set(w.inputs['Vector'], g.coords())
            w.inputs['Scale'].default_value = 420.0
        weave = g.math('MAXIMUM', warp.outputs['Fac'], weft.outputs['Fac'])
        g.set(I['Base Color'], g.mix(g.remap(cloud, 0.3, 0.7), shade(col, 0.82), shade(col, 1.08)))
        I['Roughness'].default_value = 0.92
        I['Sheen Weight'].default_value = 0.6
        I['Sheen Roughness'].default_value = 0.5
        normal = g.bump(weave, 0.0005, g.bump(g.noise(30.0, 3.0), 0.001, normal))
    elif preset == 'stone':
        big = g.noise(1.3, 8.0, 0.62, distortion=0.4)
        speck = g.noise(160.0, 2.0, 0.5)
        pits = g.voronoi(55.0)
        tone = g.mix(g.remap(big, 0.25, 0.8, smooth=True), shade(col, 0.78), shade(col, 1.1))
        g.set(I['Base Color'], g.mix(g.remap(speck, 0.55, 0.8, 0.0, 0.35), tone, shade(col, 0.6)))
        g.set(I['Roughness'], g.remap(big, 0.2, 0.8, 0.55, 0.78))
        normal = g.bump(g.noise(26.0, 6.0, 0.6), 0.0016, g.bump(g.math('MINIMUM', pits, 0.12), 0.002, normal))
    elif preset == 'plaster':
        big = g.noise(0.7, 6.0, 0.6)
        g.set(I['Base Color'], g.mix(g.remap(big, 0.25, 0.8), shade(col, 0.9), shade(col, 1.05)))
        I['Roughness'].default_value = 0.9
        normal = g.bump(g.noise(70.0, 5.0, 0.6), 0.0007, g.bump(g.noise(3.0, 4.0), 0.003, normal))
    elif preset == 'metal':
        smear = g.noise(7.0, 4.0, 0.6, distortion=0.8)
        I['Base Color'].default_value = col
        I['Metallic'].default_value = 1.0
        g.set(I['Roughness'], g.remap(smear, 0.25, 0.8, 0.18, 0.36))
        normal = g.bump(g.noise(300.0, 2.0), 0.00005, normal)
    elif preset == 'paper':
        fibre = g.noise(260.0, 4.0, 0.6)
        g.set(I['Base Color'], g.mix(g.remap(fibre, 0.3, 0.8, 0.0, 0.5), col, shade(col, 0.93)))
        I['Roughness'].default_value = 0.78
        I['Sheen Weight'].default_value = 0.2
        normal = g.bump(fibre, 0.0001, normal)
    elif preset == 'glass':
        I['Base Color'].default_value = (min(1.0, col[0] * 0.3 + 0.7), min(1.0, col[1] * 0.3 + 0.7), min(1.0, col[2] * 0.3 + 0.7), 1.0)
        I['Transmission Weight'].default_value = 1.0
        I['Roughness'].default_value = 0.02
        I['IOR'].default_value = 1.5
    elif preset == 'plastic':
        I['Base Color'].default_value = col
        g.set(I['Roughness'], g.remap(g.noise(12.0, 3.0), 0.3, 0.8, 0.26, 0.4))
        I['Coat Weight'].default_value = 0.3
        I['Coat Roughness'].default_value = 0.1
    elif preset == 'ceramic':
        I['Base Color'].default_value = col
        I['Roughness'].default_value = 0.35
        I['Coat Weight'].default_value = 1.0
        I['Coat Roughness'].default_value = 0.04
    elif preset == 'brick':
        # courses run along the wall's long side and stack upward (local Z is up for an upright wall)
        thin = min(range(3), key=lambda i: dims[i])
        u, v = ((0, 1) if thin == 2 else ((1, 2) if thin == 0 else (0, 2)))
        flat = g.planar(u, v)
        bricks = g.new('ShaderNodeTexBrick', offset=0.5, offset_frequency=2, squash=1.0)
        g.set(bricks.inputs['Vector'], flat)
        for name, val in (('Scale', 1.0), ('Brick Width', 0.225), ('Row Height', 0.075), ('Mortar Size', 0.011), ('Mortar Smooth', 0.25), ('Bias', 0.0)):
            bricks.inputs[name].default_value = val
        bricks.inputs['Color1'].default_value = shade(col, 0.7)
        bricks.inputs['Color2'].default_value = shade(col, 1.2)
        bricks.inputs['Mortar'].default_value = (0.32, 0.3, 0.27, 1.0)
        soot = g.noise(1.1, 7.0, 0.65, distortion=0.6)
        grit = g.noise(130.0, 4.0, 0.6)
        tone = g.mix(g.remap(soot, 0.3, 0.8, 0.0, 0.6, smooth=True), bricks.outputs['Color'], shade(col, 0.45), 'MULTIPLY')
        g.set(I['Base Color'], g.mix(g.remap(grit, 0.4, 0.8, 0.0, 0.3), tone, shade(col, 0.55)))
        g.set(I['Roughness'], g.remap(grit, 0.2, 0.8, 0.78, 0.95))
        face = g.math('SUBTRACT', 1.0, bricks.outputs['Fac'])
        normal = g.bump(grit, 0.0015, g.bump(g.noise(18.0, 5.0, 0.6), 0.003, g.bump(face, 0.007, None)))
    elif preset == 'velvet':
        cloud = g.noise(7.0, 4.0, 0.55)
        g.set(I['Base Color'], g.mix(g.remap(cloud, 0.3, 0.75), shade(col, 0.6), shade(col, 0.95)))
        I['Roughness'].default_value = 1.0
        I['Sheen Weight'].default_value = 1.0
        I['Sheen Roughness'].default_value = 0.3
        I['Sheen Tint'].default_value = (min(1.0, col[0] * 1.6 + 0.1), min(1.0, col[1] * 1.6 + 0.1), min(1.0, col[2] * 1.6 + 0.1), 1.0)
        normal = g.bump(g.noise(900.0, 2.0), 0.0004, g.bump(g.noise(20.0, 3.0), 0.0015, normal))
    elif preset in ('glow', 'neon'):
        I['Base Color'].default_value = col
        I['Emission Color'].default_value = col
        I['Emission Strength'].default_value = 14.0 if preset == 'glow' else 45.0
        I['Roughness'].default_value = 0.6
    if normal is not None:
        g.set(I['Normal'], normal)
    return mat


def weld(mesh):
    """Exported shapes have one copy of each corner per face; join them so edges can be worked on."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(mesh)
    bm.free()
    for name in ('custom_normal', 'sharp_face', 'sharp_edge'):
        attr = mesh.attributes.get(name)
        if attr:
            mesh.attributes.remove(attr)


def pad(ob, width):
    """Round the edges of a box for real: upholstery and soft things have fat, soft corners."""
    weld(ob.data)
    for p in ob.data.polygons:
        p.use_smooth = True
    bev = ob.modifiers.new('Soft edges', 'BEVEL')
    bev.width = width
    bev.segments = 5
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(40)
    wn = ob.modifiers.new('Even shading', 'WEIGHTED_NORMAL')
    wn.keep_sharp = False
    wn.weight = 60


def dress_props(scene):
    """Turn every "rr:<preset>" material into its full surface, sized to the prop it is on."""
    done = 0
    for ob in list(scene.objects):
        if ob.type != 'MESH' or ob.find_armature() or not ob.data.materials:
            continue
        slot = ob.data.materials[0]
        if not slot or not slot.name.startswith('rr:'):
            continue
        preset = slot.name[3:].split('.')[0]
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        # bake the prop's size into its shape, so textures are measured in meters
        sc = ob.scale.copy()
        ob.data.transform(Matrix.Diagonal((sc.x, sc.y, sc.z, 1.0)))
        ob.scale = (1.0, 1.0, 1.0)
        dims = [max(1e-4, d) for d in ob.dimensions]
        bsdf = slot.node_tree.nodes.get('Principled BSDF') if slot.use_nodes else None
        col = tuple(bsdf.inputs['Base Color'].default_value) if bsdf else (0.5, 0.5, 0.5, 1.0)
        is_box = len(ob.data.polygons) <= 12
        if preset == 'plain':
            if bsdf and is_box:  # keep the look the user set; just take the razor edge off
                g = Graph(slot.node_tree)
                edge = g.bevel(min(0.004, 0.1 * min(dims)))
                if edge is not None:
                    g.set(bsdf.inputs['Normal'], edge)
            continue
        ob.data.materials[0] = surface(preset, col, dims, 'Surface ' + preset + ' ' + ob.name)
        if preset in ('leather', 'fabric', 'velvet') and is_box and min(dims) > 0.05:
            pad(ob, min(0.04 if preset == 'leather' else 0.03, 0.3 * min(dims)))
        if preset in ('glow', 'neon'):
            ob.visible_shadow = False
        done += 1
    return done


# ───────── floor ─────────

def floor_material(kind, fallback):
    mat, g, b = fresh('Floor ' + kind)
    I = b.inputs
    if kind == 'wood':
        col = hex_to_linear('#8a6444')
        boards = g.new('ShaderNodeTexBrick', offset=0.37, offset_frequency=2, squash=1.0)
        g.set(boards.inputs['Vector'], g.coords())
        for name, v in (('Scale', 1.0), ('Brick Width', 1.6), ('Row Height', 0.13), ('Mortar Size', 0.0025), ('Mortar Smooth', 0.2), ('Bias', 0.0)):
            boards.inputs[name].default_value = v
        boards.inputs['Color1'].default_value = shade(col, 0.82)
        boards.inputs['Color2'].default_value = shade(col, 1.12)
        boards.inputs['Mortar'].default_value = shade(col, 0.25)
        grain = g.noise(3.0, 5.0, 0.6, g.mapping((1.0, 16.0, 16.0)), distortion=1.0)
        fine = g.noise(60.0, 3.0, 0.5, g.mapping((6.0, 90.0, 90.0)))
        g.set(I['Base Color'], g.mix(g.remap(grain, 0.3, 0.75, 0.0, 0.55, smooth=True), boards.outputs['Color'], shade(col, 0.6), 'MULTIPLY'))
        g.set(I['Roughness'], g.remap(fine, 0.2, 0.8, 0.28, 0.46))
        I['Coat Weight'].default_value = 0.3
        I['Coat Roughness'].default_value = 0.15
        g.set(I['Normal'], g.bump(g.math('SUBTRACT', 1.0, boards.outputs['Fac']), 0.0012, g.bump(fine, 0.0003)))
    elif kind == 'concrete':
        col = hex_to_linear('#8b8a86')
        big = g.noise(0.6, 8.0, 0.65, distortion=0.5)
        stain = g.noise(2.5, 6.0, 0.7)
        g.set(I['Base Color'], g.mix(g.remap(stain, 0.35, 0.8, smooth=True), g.mix(big, shade(col, 0.8), shade(col, 1.08)), shade(col, 0.68)))
        g.set(I['Roughness'], g.remap(stain, 0.3, 0.8, 0.5, 0.82))
        g.set(I['Normal'], g.bump(g.noise(90.0, 6.0, 0.6), 0.0008, g.bump(g.voronoi(30.0), 0.0006)))
    elif kind == 'tiles':
        col = hex_to_linear('#c9c3b6')
        tiles = g.new('ShaderNodeTexBrick', offset=0.0, squash=1.0)
        g.set(tiles.inputs['Vector'], g.coords())
        for name, v in (('Scale', 1.0), ('Brick Width', 0.6), ('Row Height', 0.6), ('Mortar Size', 0.004), ('Mortar Smooth', 0.3), ('Bias', 0.0)):
            tiles.inputs[name].default_value = v
        tiles.inputs['Color1'].default_value = shade(col, 0.92)
        tiles.inputs['Color2'].default_value = shade(col, 1.06)
        tiles.inputs['Mortar'].default_value = shade(col, 0.35)
        cloud = g.noise(1.2, 6.0, 0.6)
        g.set(I['Base Color'], g.mix(g.remap(cloud, 0.3, 0.8, 0.0, 0.25), tiles.outputs['Color'], shade(col, 0.8), 'MULTIPLY'))
        g.set(I['Roughness'], g.math('ADD', g.remap(cloud, 0.2, 0.8, 0.1, 0.24), g.math('MULTIPLY', tiles.outputs['Fac'], 0.6), clamp=True))
        g.set(I['Normal'], g.bump(g.math('SUBTRACT', 1.0, tiles.outputs['Fac']), 0.0015))
    elif kind == 'carpet':
        col = hex_to_linear('#5d5764')
        pile = g.noise(900.0, 2.0, 0.5)
        g.set(I['Base Color'], g.mix(pile, shade(col, 0.75), shade(col, 1.15)))
        I['Roughness'].default_value = 1.0
        I['Sheen Weight'].default_value = 0.8
        g.set(I['Normal'], g.bump(pile, 0.002, g.bump(g.noise(6.0, 3.0), 0.003)))
    else:
        I['Base Color'].default_value = hex_to_linear(fallback.get('color', '#6b6e76'))
        I['Roughness'].default_value = float(fallback.get('roughness', 0.92))
    return mat


# ───────── people ─────────

def shade_people(scene):
    """Scanned people: skin scatters light under its surface, cloth has a soft sheen."""
    done = 0
    seen = set()
    for ob in scene.objects:
        if ob.type != 'MESH':
            continue
        for mat in ob.data.materials:
            if not mat or mat.name in seen or mat.name.startswith(('rr:', 'Surface ', 'Floor')) or not mat.use_nodes:
                continue
            seen.add(mat.name)
            b = mat.node_tree.nodes.get('Principled BSDF')
            if not b or not b.inputs['Base Color'].links:
                continue
            g = Graph(mat.node_tree)
            base = b.inputs['Base Color'].links[0].from_socket
            hsv = g.new('ShaderNodeSeparateColor', mode='HSV')
            g.set(hsv.inputs['Color'], base)
            h, s, v = hsv.outputs[0], hsv.outputs[1], hsv.outputs[2]
            # skin: orange-red hues of middling saturation, wherever the scan is not shiny cloth or hair
            mask = g.math('MULTIPLY', g.remap(h, 0.115, 0.085, smooth=True), g.remap(s, 0.14, 0.24, smooth=True))
            mask = g.math('MULTIPLY', mask, g.remap(s, 0.85, 0.7, smooth=True))
            mask = g.math('MULTIPLY', mask, g.remap(v, 0.1, 0.22, smooth=True))
            rough = b.inputs['Roughness']
            if rough.links:
                mask = g.math('MULTIPLY', mask, g.remap(rough.links[0].from_socket, 0.6, 0.5, smooth=True))
            else:
                g.set(rough, g.remap(mask, 0.0, 1.0, 0.8, 0.44))
            # inside an open mouth no light arrives and the tongue and teeth would render black: where the surface
            # is deep in a small hollow, and is flesh- or tooth-coloured, it is lit from within
            ao = g.new('ShaderNodeAmbientOcclusion', samples=4, only_local=True)
            ao.inputs['Distance'].default_value = 0.035
            hollow = g.remap(ao.outputs['AO'], 0.5, 0.18, smooth=True)
            flesh = g.math('MAXIMUM', g.remap(h, 0.1, 0.07, smooth=True), g.remap(h, 0.9, 0.94, smooth=True))
            teeth = g.math('MULTIPLY', g.remap(s, 0.3, 0.18, smooth=True), g.remap(v, 0.45, 0.6, smooth=True))
            inner = g.math('MULTIPLY', hollow, g.math('MAXIMUM', flesh, teeth))
            g.set(b.inputs['Emission Color'], base)
            g.set(b.inputs['Emission Strength'], g.math('MULTIPLY', inner, 0.9))
            g.set(b.inputs['Subsurface Weight'], g.math('MULTIPLY', mask, 0.6))
            b.subsurface_method = 'RANDOM_WALK_SKIN'
            b.inputs['Subsurface Radius'].default_value = (1.0, 0.36, 0.2)
            b.inputs['Subsurface Scale'].default_value = 0.004
            b.inputs['Subsurface Anisotropy'].default_value = 0.8
            # a trace of sheen softens cloth; more than that frosts hair
            g.set(b.inputs['Sheen Weight'], g.remap(mask, 0.0, 1.0, 0.06, 0.0))
            b.inputs['Sheen Roughness'].default_value = 0.6
            g.set(b.inputs['Sheen Tint'], base)
            done += 1
    return done


# ───────── light ─────────

def add_lights(scene, lights):
    for i, L in enumerate(lights or []):
        kind = {'area': 'AREA', 'spot': 'SPOT', 'point': 'POINT'}.get(L.get('type'), 'AREA')
        data = bpy.data.lights.new(L.get('name') or 'Light %d' % i, kind)
        data.energy = max(0.0, float(L.get('power', 150)))
        data.color = hex_to_linear(L.get('color', '#ffffff'))[:3]
        size = max(0.02, float(L.get('size', 0.6)))
        if kind == 'AREA':
            data.shape = 'DISK'
            data.size = size
        else:
            data.shadow_soft_size = size / 2
        if kind == 'SPOT':
            data.spot_size = math.radians(min(170.0, max(5.0, float(L.get('spread', 60)))))
            data.spot_blend = 0.35
        ob = bpy.data.objects.new(data.name, data)
        p, t = to_blender(L['p']), to_blender(L['t'])
        ob.location = p
        if (t - p).length > 1e-6:
            ob.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
        ob.visible_camera = False  # the light is felt, not seen; a "glow" prop plays the lamp
        scene.collection.objects.link(ob)


def build_world(scene, look):
    world = bpy.data.worlds.new('World')
    world.use_nodes = True
    g = Graph(world.node_tree)
    bg = g.nodes.get('Background')
    sky = look.get('sky', 'soft')
    amb = float(look.get('env', 0.6))
    path = os.path.join(ENV_DIR, sky + '.exr')
    if sky in SKIES and os.path.exists(path):
        tex = g.new('ShaderNodeTexEnvironment')
        tex.image = bpy.data.images.load(path)
        turn = math.radians(float(look.get('skyTurn', 0)))
        m = g.new('ShaderNodeMapping')
        g.set(m.inputs['Vector'], g.new('ShaderNodeTexCoord').outputs['Generated'])
        m.inputs['Rotation'].default_value = (0.0, 0.0, math.pi + turn)  # lines the picture up with the app's view of it
        g.set(tex.inputs['Vector'], m.outputs['Vector'])
        g.set(bg.inputs['Color'], tex.outputs['Color'])
        bg.inputs['Strength'].default_value = amb / 0.6
    else:
        bg.inputs['Color'].default_value = (0.62, 0.63, 0.66, 1.0)
        bg.inputs['Strength'].default_value = amb * 1.1
    scene.world = world


def add_haze(scene, amount):
    """Thin smoke or dust in the air: light beams show, distance softens. A box, so outside light still gets in."""
    if amount <= 0:
        return
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 4.0))
    box = bpy.context.active_object
    box.name = 'Haze'
    box.scale = (40.0, 40.0, 8.2)
    mat = bpy.data.materials.new('Haze')
    mat.use_nodes = True
    nt = mat.node_tree
    out = nt.nodes.get('Material Output')
    for n in [n for n in nt.nodes if n != out]:
        nt.nodes.remove(n)
    vol = nt.nodes.new('ShaderNodeVolumeScatter')
    vol.inputs['Density'].default_value = 0.03 * min(1.0, amount)
    vol.inputs['Anisotropy'].default_value = 0.35
    vol.inputs['Color'].default_value = (0.9, 0.92, 1.0, 1.0)
    nt.links.new(vol.outputs[0], out.inputs['Volume'])
    box.data.materials.append(mat)
    box.visible_shadow = False


# ───────── lens ─────────

def lens_finish(scene, amount=1.0):
    """Bloom around bright things and a trace of colour fringing, done in Blender's compositor."""
    if amount <= 0:
        return False
    try:
        tree = bpy.data.node_groups.new('Lens', 'CompositorNodeTree')
        tree.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        src = tree.nodes.new('CompositorNodeRLayers')
        glare = tree.nodes.new('CompositorNodeGlare')
        glare.inputs['Type'].default_value = 'Bloom'
        glare.inputs['Threshold'].default_value = 1.2
        glare.inputs['Strength'].default_value = 0.35 * amount
        glare.inputs['Size'].default_value = 0.5
        lens = tree.nodes.new('CompositorNodeLensdist')
        lens.inputs['Dispersion'].default_value = 0.006 * amount
        lens.inputs['Distortion'].default_value = 0.0
        out = tree.nodes.new('NodeGroupOutput')
        tree.links.new(src.outputs['Image'], glare.inputs['Image'])
        tree.links.new(glare.outputs['Image'], lens.inputs['Image'])
        tree.links.new(lens.outputs['Image'], out.inputs[0])
        scene.compositing_node_group = tree
        scene.render.use_compositing = True
        scene.render.compositor_device = 'CPU'   # render machines have no graphics card
        return True
    except Exception as err:  # an older or newer Blender: render without the lens pass
        print('lens pass skipped:', err, flush=True)
        try:
            scene.compositing_node_group = None
        except Exception:
            pass
        return False


def film_finish(path, frame, amount=1.0):
    """Darken the corners slightly and add fine grain, as film and sensors do."""
    if amount <= 0:
        return
    try:
        import numpy as np
        img = bpy.data.images.load(path)
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(h, w, 4)
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        r2 = ((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (w / 2)) ** 2
        px[..., :3] *= (1.0 - 0.16 * amount * np.clip(r2, 0, 2) ** 1.5)[..., None]
        rng = np.random.default_rng(1000 + int(frame))
        lum = px[..., :3].mean(axis=2, keepdims=True)
        grain = rng.normal(0.0, 0.016 * amount, (h, w, 1)).astype(np.float32)
        px[..., :3] = np.clip(px[..., :3] + grain * (1.0 - 0.6 * lum), 0.0, 1.0)
        img.pixels.foreach_set(px.ravel())
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        bpy.data.images.remove(img)
    except Exception as err:
        print('film pass skipped:', err, flush=True)
