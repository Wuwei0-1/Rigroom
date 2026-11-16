"""The botanical lounge as a cartoon set, laid out like Edward's booth storyboard: two columns, a U-shaped velvet booth,
a pedestal table, glowing screens on a brick wall, plants. Metres, Z up; the camera looks along +Y."""
import math
import random

import bpy
from mathutils import Matrix, Quaternion, Vector

from kit import capsule, frustum, hexc, lathe, material, ring, slab, sphere, static, tube

V = Vector
SEAT = 0.40          # height of the seat cushions
TABLE = 0.72         # height of the table top


def brick(name='Brick'):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (math.pi / 2, 0, 0)
    mp.inputs['Scale'].default_value = (3.2, 3.2, 3.2)
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = hexc('#8f4634')
    br.inputs['Color2'].default_value = hexc('#7a3a2c')
    br.inputs['Mortar'].default_value = hexc('#3b2520')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Brick Width'].default_value = 0.62
    br.inputs['Row Height'].default_value = 0.2
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.9
    return m


def hologram(name, image_path=None, tint='#58d6ff', strength=1.3):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in [n for n in nt.nodes if n.type != 'OUTPUT_MATERIAL']:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Strength'].default_value = strength
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    mix.inputs['B'].default_value = hexc(tint)
    if image_path:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(image_path)
        tex.image.pack()
        tex.extension = 'CLIP'
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        nt.links.new(tex.outputs['Color'], bw.inputs[0])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.06, 0.1, 0.16, 1)
        ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.85, (1, 1, 1, 1)
        nt.links.new(bw.outputs[0], ramp.inputs['Fac'])
        nt.links.new(ramp.outputs['Color'], mix.inputs['A'])
    else:
        wave = nt.nodes.new('ShaderNodeTexNoise')
        wave.inputs['Scale'].default_value = 9
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.35, (0.1, 0.2, 0.3, 1)
        ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.7, (1, 1, 1, 1)
        nt.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
        nt.links.new(ramp.outputs['Color'], mix.inputs['A'])
    nt.links.new(mix.outputs['Result'], e.inputs['Color'])
    nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m


def screen(name, c, w, h, mat, frame, facing=0.0, uv=(0, 0, 1, 1)):
    """An upright glowing panel centred at c, facing -Y unless turned (radians about Z)."""
    me = bpy.data.meshes.new(name)
    hw, hh = w / 2, h / 2
    me.from_pydata([(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)], [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new()
    for i, co in enumerate(((uv[0], uv[1]), (uv[2], uv[1]), (uv[2], uv[3]), (uv[0], uv[3]))):
        uvl.data[i].uv = co
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = c
    ob.rotation_euler = (0, 0, facing)
    fr = static(name + ' frame', [(slab((0, 0.03, 0), (w + 0.1, 0.04, h + 0.1)), frame)], smooth=False, bevel=0.01, loc=c, rot_z=facing)
    return ob


def column(x, y, stone, trim):
    prof = [(0, 0), (0.5, 0), (0.5, 0.12), (0.44, 0.14), (0.44, 0.3), (0.38, 0.34), (0.33, 0.4), (0.31, 0.5), (0.3, 2.6), (0.33, 2.72), (0.42, 2.8), (0.46, 2.86), (0.46, 3.0), (0, 3.0)]
    shapes = [(lathe(prof, 40, Matrix.Translation(V((x, y, 0)))), stone)]
    for k in range(16):       # fluting hinted with thin ribs
        a = 2 * math.pi * k / 16
        shapes.append((capsule((x + 0.3 * math.cos(a), y + 0.3 * math.sin(a), 0.56), (x + 0.3 * math.cos(a), y + 0.3 * math.sin(a), 2.56), 0.022, seg=8, cap=3), stone))
    shapes.append((ring((x, y, 2.66), 0.33, 0.03, seg=36, tseg=6), trim))
    return static('Column', shapes)


def plant(x, y, rng, pot, leaf, stem, h=1.3, n=9):
    shapes = [(frustum((x, y, 0), (x, y, 0.42), 0.17, 0.24, seg=24), pot), (ring((x, y, 0.42), 0.24, 0.025, seg=24, tseg=6), pot)]
    for k in range(n):
        a = 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
        r = rng.uniform(0.25, 0.55)
        top = V((x + r * math.cos(a), y + r * math.sin(a), rng.uniform(0.75, h)))
        mid = V((x + 0.35 * r * math.cos(a), y + 0.35 * r * math.sin(a), 0.42 + (top.z - 0.42) * 0.7))
        shapes.append((tube([(x, y, 0.4), mid, top], 0.012, seg=6), stem))
        d = (top - mid).normalized()
        q = V((0, 0, 1)).rotation_difference(d)
        shapes.append((sphere(top + d * 0.14, (0.11, 0.022, 0.2), rot=q, seg=14, rings=8), leaf))
    return static('Plant', shapes)


def build(news=None):
    velvet = material('Velvet', '#17594c', rough=0.9, sheen=0.25)
    velvet2 = material('Velvet dark', '#114338', rough=0.9, sheen=0.25)
    brass = material('Brass', '#c9983a', rough=0.35, metal=1.0)
    wood = material('Walnut', '#5a3320', rough=0.5)
    floor = material('Floor', '#2b1d18', rough=0.7)
    stone = material('Stone', '#d9cdb8', rough=0.8)
    pot = material('Pot', '#b5623c', rough=0.8)
    leaf = material('Leaf', '#2f7d3b', rough=0.55)
    stem = material('Stem', '#3d6b33', rough=0.7)
    dark = material('Screen frame', '#15181d', rough=0.5)
    wall = brick()
    rng = random.Random(3)
    static('Floor', [(slab((0, 2, -0.05), (16, 16, 0.1)), floor)], smooth=False)
    static('Wall', [(slab((0, 2.75, 2.0), (12, 0.2, 4.4)), wall)], smooth=False)
    static('Wall left', [(slab((-4.6, 0.5, 2.0), (0.2, 6, 4.4)), wall)], smooth=False)
    static('Wall right', [(slab((4.6, 0.5, 2.0), (0.2, 6, 4.4)), wall)], smooth=False)
    static('Skirting', [(slab((0, 2.63, 0.09), (12, 0.06, 0.18)), wood)], smooth=False, bevel=0.01)
    column(-2.35, 2.2, stone, brass)
    column(2.35, 2.2, stone, brass)
    # the booth: a U of cushions with tall backs
    sw = 0.62       # seat depth
    cushions = [(slab((0, 0.82, SEAT - 0.1), (3.9, sw, 0.2)), velvet), (slab((-1.64, 0.02, SEAT - 0.1), (sw, 1.3, 0.2)), velvet), (slab((1.64, 0.02, SEAT - 0.1), (sw, 1.3, 0.2)), velvet)]
    static('Booth seats', cushions, smooth=False, bevel=0.06)
    backs = [(slab((0, 1.2, 0.5), (4.3, 0.2, 0.8)), velvet2), (slab((-2.03, 0.12, 0.56), (0.2, 1.7, 0.95)), velvet2), (slab((2.03, 0.12, 0.56), (0.2, 1.7, 0.95)), velvet2)]
    static('Booth backs', backs, smooth=False, bevel=0.09)
    static('Booth base', [(slab((0, 0.86, 0.1), (3.9, 0.56, 0.2)), dark), (slab((-1.66, 0.02, 0.1), (0.56, 1.26, 0.2)), dark), (slab((1.66, 0.02, 0.1), (0.56, 1.26, 0.2)), dark)], smooth=False)
    trim = [(capsule((-2.13, 1.3, 0.91), (2.13, 1.3, 0.91), 0.018, seg=8), brass)]
    static('Booth trim', trim)
    # the table
    static('Table top', [(slab((0, 0, TABLE - 0.025), (1.7, 0.8, 0.05)), wood)], smooth=False, bevel=0.022)
    static('Table leg', [(lathe([(0, 0), (0.32, 0), (0.32, 0.035), (0.09, 0.07), (0.06, 0.12), (0.06, TABLE - 0.08), (0.1, TABLE - 0.05), (0, TABLE - 0.05)], 32), brass)])
    # glowing screens on the brick
    holo = hologram('Hologram', news)
    screen('Screen centre', (0, 2.6, 2.05), 2.9, 1.5, holo, dark)
    screen('Screen left', (-3.55, 2.6, 2.0), 1.5, 1.6, holo, dark, uv=(0.02, 0.3, 0.42, 0.95))
    screen('Screen right', (3.55, 2.6, 2.0), 1.5, 1.6, holo, dark, uv=(0.55, 0.3, 0.95, 0.95))
    plant(-3.1, 1.75, rng, pot, leaf, stem, h=1.9, n=11)
    plant(3.15, 1.7, rng, pot, leaf, stem, h=1.8, n=11)
    plant(-3.6, 0.2, rng, pot, leaf, stem, h=1.5, n=9)
    plant(3.65, 0.1, rng, pot, leaf, stem, h=1.5, n=9)
    # a pendant lamp over the table
    glow = material('Lamp glow', '#ffd9a0', emit=4.0)
    static('Pendant', [(frustum((0, 0, 2.05), (0, 0, 2.32), 0.3, 0.08, seg=32, caps=False), brass), (capsule((0, 0, 2.32), (0, 0, 4.0), 0.008, seg=6), dark), (sphere((0, 0, 2.08), 0.07), glow)])
    # on the table: glasses and a small plant
    glass = material('Glass', '#bfe6e0', rough=0.1, coat=1.0)
    static('Glasses', [(frustum((-0.42, 0.18, TABLE), (-0.42, 0.18, TABLE + 0.12), 0.03, 0.036, seg=16), glass), (frustum((0.5, -0.2, TABLE), (0.5, -0.2, TABLE + 0.12), 0.03, 0.036, seg=16), glass),
                       (frustum((0.02, 0.26, TABLE), (0.02, 0.26, TABLE + 0.07), 0.05, 0.065, seg=20), pot), (sphere((0.02, 0.26, TABLE + 0.12), (0.07, 0.07, 0.06)), leaf)])


def boxes():
    """The furniture people sit on, lean on and reach over, as (name, low corner, high corner) boxes."""
    def b(name, c, s):
        return (name, tuple(c[k] - s[k] / 2 for k in range(3)), tuple(c[k] + s[k] / 2 for k in range(3)))
    sw = 0.62
    return [b('seat back row', (0, 0.82, SEAT - 0.1), (3.9, sw, 0.2)), b('seat left', (-1.64, 0.02, SEAT - 0.1), (sw, 1.3, 0.2)),
            b('seat right', (1.64, 0.02, SEAT - 0.1), (sw, 1.3, 0.2)),
            b('back', (0, 1.2, 0.5), (4.3, 0.2, 0.8)), b('back left', (-2.03, 0.12, 0.56), (0.2, 1.7, 0.95)), b('back right', (2.03, 0.12, 0.56), (0.2, 1.7, 0.95)),
            b('base back row', (0, 0.86, 0.1), (3.9, 0.56, 0.2)), b('base left', (-1.66, 0.02, 0.1), (0.56, 1.26, 0.2)), b('base right', (1.66, 0.02, 0.1), (0.56, 1.26, 0.2)),
            b('table', (0, 0, TABLE - 0.025), (1.7, 0.8, 0.05))]


def slate(name, glow_strength=3.0):
    """A hand-held glowing slate, lying flat at the origin with its screen up; returns the object."""
    body = material('Slate body', '#1a1d24', rough=0.4)
    scr = material('Slate screen', '#7fd4ff', emit=glow_strength, rough=0.3)
    return static(name, [(slab((0, 0, 0.005), (0.26, 0.18, 0.01)), body), (slab((0, 0, 0.0105), (0.24, 0.16, 0.002)), scr)], smooth=False)
