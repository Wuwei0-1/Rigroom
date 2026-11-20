"""The courtyard of Cephalus's house at the Piraeus, as a cartoon set in the style of the lounge: a court open to the sky,
plastered walls with a painted frieze, a colonnade, an altar, racks of bronze shields (the family's trade), lamp
stands, and chairs in a semicircle round the old man's cushioned chair. Metres, Z up; the front camera looks along +Y.

SEATS gives each place a sitter can take: (x, y, yaw in degrees), the yaw turning a figure that faces -Y to face
the middle of the semicircle (MID). LAMPS lists the lamp stands' flame positions, for the director to light.
"""
import math
import random

import bpy
from mathutils import Matrix, Quaternion, Vector

from kit import capsule, frustum, hexc, lathe, material, ring, slab, sphere, static, tube

V = Vector
SEAT = 0.44              # seat height
MID = V((0.0, 0.25, 0))  # the middle of the semicircle, where a speaker stands
ARC_R = 2.05
WALL_X, WALL_BACK, WALL_FRONT = 4.6, 3.7, -4.2
COLUMN_R = 0.19


def _yaw_to(p, c):
    d = (V(c) - V(p))
    return math.degrees(math.atan2(d.x, -d.y))


def arc_seat(deg, r=ARC_R):
    a = math.radians(deg)
    p = V((MID.x + r * math.cos(a), MID.y + r * math.sin(a), 0))
    return (p.x, p.y, _yaw_to(p, MID))


SEATS = {
    'arc25': arc_seat(22), 'arc45': arc_seat(43), 'arc70': arc_seat(67), 'cephalus': arc_seat(90, ARC_R + 0.05),
    'arc110': arc_seat(113), 'arc135': arc_seat(137), 'arc158': arc_seat(158), 'arc178': arc_seat(179, ARC_R + 0.05),
    'bench1': (-2.95, -0.55, 90.0), 'bench2': (-2.95, 0.2, 90.0),
}
CHAIR_KIND = {k: ('throne' if k == 'cephalus' else ('bench' if k.startswith('bench') else 'chair')) for k in SEATS}
# where people stand or sit on the floor (x, y); which way they face is given by whoever places them
SPOTS = {'mid': (MID.x, MID.y), 'mid_left': (-0.38, 0.3), 'mid_right': (0.38, 0.3),
         'column': (3.22, -0.35), 'column_floor': (3.2, -0.45),          # by the right-hand column, where Julian hides
         'back_column_floor': (-1.8, 2.52),                              # against a column behind the chairs
         'wall_front': (0.9, -3.05),                                     # among the shadows on the front wall
         'corner': (3.15, -2.3), 'corner_floor': (3.2, -2.3), 'before_corner': (2.45, -1.75),
         'altar': (-2.55, -1.72), 'gate_in': (4.0, -2.35), 'gate_out': (6.2, -2.35),
         'pace_a': (-0.85, 0.05), 'pace_b': (0.85, 0.05), 'toward_gate': (1.75, -0.95),
         'block_a': (2.71, -1.04), 'block_b': (2.41, -1.66), 'by_julian': (3.0, -0.95)}
COLUMNS = [(-3.6, 2.85), (-1.8, 2.85), (0.0, 2.85), (1.8, 2.85), (3.6, 2.85), (3.62, 1.05), (3.62, -0.75), (3.62, -2.55)]
LAMPS = [(-1.05, 2.45, 1.52), (1.05, 2.45, 1.52), (-3.15, 1.25, 1.52), (2.9, 1.65, 1.52), (0.9, 3.45, 0.62)]
BACK_LAMP = 4            # a low lamp behind the chairs: lit alone, it throws the company's shadows up the front wall
# named points to look at
LOOKS = {'gate': (6.5, -2.35, 1.9), 'sky': (-3.0, 1.0, 7.0), 'wall': (0.6, -4.2, 1.7), 'altar': (-2.55, -2.35, 1.0), 'column': (3.62, -0.75, 1.4),
         'back_column': (-1.8, 2.85, 0.7), 'corner': (3.2, -2.3, 0.7), 'corner_up': (3.15, -2.3, 1.6), 'mid': (0.0, 0.25, 1.3)}
# cameras: name -> (position, aim, lens)
CAMERAS = {
    'wide': ((0.75, -3.95, 1.75), (0.55, 1.1, 0.95), 20),
    'reverse': ((1.25, 3.3, 1.95), (-0.25, -0.6, 1.0), 24),
    'side': ((-2.1, -3.9, 1.8), (1.0, 1.5, 1.0), 24),
    'high': ((0.0, -3.8, 3.3), (0.0, 1.0, 0.5), 20),
    'wall': ((-0.2, 2.3, 1.75), (0.4, -4.2, 1.7), 22),
    'wall_julian': ((1.3, 0.2, 1.65), (0.75, -4.2, 1.5), 28),
    'gate': ((1.4, 0.9, 1.45), (4.6, -2.3, 1.5), 28),
    'altar': ((-0.9, -0.6, 1.6), (-2.55, -2.1, 1.15), 30),
    'corner': ((0.4, 0.3, 1.55), (3.1, -2.2, 1.0), 30),
    'follow': ((0.0, -3.9, 1.65), (0.0, 0.5, 1.2), 26),
    'chair': ((0.95, 0.35, 1.25), (0.0, 2.33, 0.62), 34),
    'column_view': ((1.35, 0.55, 1.25), (3.2, -0.42, 0.85), 30),
}
ALTAR = (-2.55, -2.35)


def plaster(name, colour, scale=3.0, var=0.06):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = 6.0
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    c = hexc(colour)
    ramp.color_ramp.elements[0].color = tuple(max(0.0, x * (1 - var * 2)) for x in c[:3]) + (1,)
    ramp.color_ramp.elements[1].color = tuple(min(1.0, x * (1 + var)) for x in c[:3]) + (1,)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.92
    m.diffuse_color = c
    return m


def flagstones(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (0.9, 0.9, 0.9)
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = hexc('#cbbd9f')
    br.inputs['Color2'].default_value = hexc('#b8a787')
    br.inputs['Mortar'].default_value = hexc('#8a7a60')
    br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Brick Width'].default_value = 0.9
    br.inputs['Row Height'].default_value = 0.6
    br.inputs['Bias'].default_value = 0.2
    br.inputs['Scale'].default_value = 1.0
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    m.diffuse_color = hexc('#c2b393')
    return m


def flame_material(name='Flame'):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in [n for n in nt.nodes if n.type != 'OUTPUT_MATERIAL']:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    e = nt.nodes.new('ShaderNodeEmission')
    e.name = 'Emission'
    e.inputs['Color'].default_value = hexc('#ffb54a')
    e.inputs['Strength'].default_value = 18.0
    nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m


def column(x, y, shaft, paint, cap):
    """A Doric column: painted lower drum, plain shaft, a cushion capital and a square abacus."""
    H = 2.7
    prof = [(0, 0), (COLUMN_R + 0.04, 0), (COLUMN_R + 0.04, 0.06), (COLUMN_R, 0.08), (COLUMN_R * 0.86, H - 0.22), (COLUMN_R * 1.12, H - 0.14),
            (COLUMN_R * 1.32, H - 0.1), (0, H - 0.1)]
    M = Matrix.Translation(V((x, y, 0)))
    shapes = [(lathe(prof, 28, M), shaft), (frustum((x, y, 0.08), (x, y, 0.9), COLUMN_R * 1.004, COLUMN_R * 0.965, seg=28, caps=False), paint),
              (slab((x, y, H - 0.05), (0.56, 0.56, 0.1)), cap), (ring((x, y, 0.92), COLUMN_R * 0.97, 0.012, seg=28, tseg=6), cap)]
    return shapes


def chair(name, x, y, yaw, wood, seat_mat):
    """A klismos: curved legs splayed front and back, a curved board for the back. Built facing -Y, then turned."""
    s = []
    hw, hd = 0.24, 0.23
    s.append((slab((0, 0, SEAT - 0.03), (2 * hw, 2 * hd, 0.05)), wood))
    s.append((slab((0, 0.0, SEAT + 0.005), (2 * hw - 0.04, 2 * hd - 0.05, 0.03)), seat_mat))
    for sx in (-1, 1):
        s.append((tube([(sx * (hw - 0.03), -hd + 0.03, SEAT - 0.04), (sx * (hw - 0.02), -hd - 0.02, 0.22), (sx * (hw - 0.01), -hd - 0.12, 0.0)], 0.022, seg=8), wood))
        s.append((tube([(sx * (hw - 0.03), hd - 0.03, SEAT - 0.04), (sx * (hw - 0.02), hd + 0.03, 0.22), (sx * (hw - 0.01), hd + 0.13, 0.0)], 0.022, seg=8), wood))
        s.append((tube([(sx * (hw - 0.03), hd - 0.03, SEAT - 0.02), (sx * (hw - 0.03), hd + 0.02, SEAT + 0.2), (sx * (hw - 0.03), hd + 0.09, SEAT + 0.36)], 0.02, seg=8), wood))
    s.append((tube([(-hw, hd + 0.06, SEAT + 0.34), (0, hd + 0.11, SEAT + 0.36), (hw, hd + 0.06, SEAT + 0.34)], 0.045, seg=10, flat=0.35), wood))
    return static(name, s, loc=(x, y, 0), rot_z=math.radians(yaw))


def throne(name, x, y, yaw, wood, cushion, gold):
    """Cephalus's chair: a high-backed seat with arms, a thick cushion and a footstool."""
    s = []
    hw, hd = 0.31, 0.27
    s.append((slab((0, 0, SEAT - 0.06), (2 * hw, 2 * hd, 0.1)), wood))
    s.append((slab((0, -0.01, SEAT + 0.015), (2 * hw - 0.06, 2 * hd - 0.06, 0.06)), cushion))
    for sx in (-1, 1):
        for sy in (-1, 1):
            s.append((frustum((sx * (hw - 0.05), sy * (hd - 0.05), 0), (sx * (hw - 0.05), sy * (hd - 0.05), SEAT - 0.1), 0.035, 0.045, seg=10), wood))
        s.append((slab((sx * (hw - 0.02), 0.02, SEAT + 0.2), (0.06, 2 * hd - 0.04, 0.05)), wood))       # arms
        s.append((frustum((sx * (hw - 0.02), -hd + 0.05, SEAT), (sx * (hw - 0.02), -hd + 0.05, SEAT + 0.2), 0.022, 0.022, seg=8), wood))
        s.append((sphere((sx * (hw - 0.02), -hd + 0.02, SEAT + 0.225), 0.035), gold))
    s.append((slab((0, hd - 0.02, SEAT + 0.42), (2 * hw, 0.06, 0.84)), wood))
    s.append((slab((0, hd - 0.06, SEAT + 0.4), (2 * hw - 0.1, 0.03, 0.7)), cushion))
    s.append((tube([(-hw - 0.02, hd - 0.02, SEAT + 0.86), (0, hd, SEAT + 0.92), (hw + 0.02, hd - 0.02, SEAT + 0.86)], 0.04, seg=10), gold))
    s.append((slab((0, -hd - 0.25, 0.06), (0.5, 0.26, 0.12)), wood))        # footstool
    s.append((slab((0, -hd - 0.25, 0.13), (0.46, 0.22, 0.03)), cushion))
    return static(name, s, loc=(x, y, 0), rot_z=math.radians(yaw))


def bench(name, x, y, yaw, wood, cushion, length=1.55):
    s = [(slab((0, 0, SEAT - 0.04), (length, 0.5, 0.08)), wood), (slab((0, 0, SEAT + 0.01), (length - 0.06, 0.46, 0.05)), cushion)]
    for sx in (-1, 1):
        s.append((slab((sx * (length / 2 - 0.08), 0, (SEAT - 0.08) / 2), (0.08, 0.42, SEAT - 0.08)), wood))
    return static(name, s, loc=(x, y, 0), rot_z=math.radians(yaw))


def shield(c, normal, bronze, rim, emblem_mat, emblem):
    """A round hoplite shield hanging on a wall, its face toward normal, with a painted emblem."""
    n = V(normal).normalized()
    q = V((0, 0, 1)).rotation_difference(n)
    R = q.to_matrix().to_4x4()
    prof = [(0, 0.06), (0.25, 0.05), (0.42, 0.02), (0.45, 0.0), (0.45, -0.015), (0, -0.015)]
    shapes = [(lathe(prof, 36, Matrix.Translation(V(c)) @ R), bronze), (ring(c, 0.44, 0.022, rot=q, seg=36, tseg=6), rim)]
    if emblem == 'disc':
        shapes.append((sphere(V(c) + n * 0.058, (0.13, 0.13, 0.012), rot=q), emblem_mat))
    elif emblem == 'bar':
        shapes.append((sphere(V(c) + n * 0.058, (0.26, 0.05, 0.012), rot=q), emblem_mat))
    elif emblem == 'ring':
        shapes.append((ring(V(c) + n * 0.055, 0.17, 0.02, rot=q, seg=28, tseg=6), emblem_mat))
    return shapes


def build():
    """Build the courtyard. Returns {'flames': [flame objects], 'embers': altar fire object}."""
    rng = random.Random(5)
    floor = flagstones('Flagstones')
    wall = plaster('Plaster', '#e7d3ad')
    wall_low = plaster('Plaster dado', '#a8432f', var=0.04)
    frieze_a = material('Frieze black', '#2a2420', rough=0.85)
    frieze_b = material('Frieze ochre', '#d39a3a', rough=0.85)
    shaft = plaster('Column shaft', '#efe6d2', scale=6.0, var=0.03)
    paint = material('Column paint', '#a3382a', rough=0.85)
    capm = material('Column capital', '#dccfb4', rough=0.8)
    roof = material('Roof tiles', '#a4552f', rough=0.8)
    beam = material('Beams', '#6a4228', rough=0.7)
    wood = material('Chair wood', '#7a4a2a', rough=0.55)
    seat = material('Seat cloth', '#b8322c', rough=0.9, sheen=0.2)
    cushion = material('Cushion', '#6b2f6e', rough=0.9, sheen=0.25)
    bench_c = material('Bench cushion', '#2f5b6e', rough=0.9, sheen=0.2)
    gold = material('Gilt', '#d9a836', rough=0.3, metal=1.0)
    bronze = material('Shield bronze', '#b07a34', rough=0.32, metal=1.0)
    rim = material('Shield rim', '#8a5a26', rough=0.35, metal=1.0)
    emb = [material('Emblem black', '#1c1714', rough=0.6), material('Emblem red', '#9c2a22', rough=0.6), material('Emblem white', '#efe6d4', rough=0.6)]
    stone = material('Altar stone', '#d8ccb2', rough=0.8)
    ember = material('Embers', '#ff6a1e', emit=6.0)
    ash = material('Ash', '#3a332e', rough=0.95)
    pot = material('Amphora', '#b35a32', rough=0.75)
    potb = material('Amphora black', '#1d1916', rough=0.6)
    leaf = material('Olive leaf', '#6f8a4a', rough=0.6)
    trunk = material('Olive trunk', '#6b5a48', rough=0.85)
    street = material('Street', '#6d6355', rough=0.95)
    house = plaster('House front', '#cdb894', var=0.05)
    door = material('Door', '#4a2e1c', rough=0.7)

    static('Courtyard floor', [(slab((0, -0.25, -0.05), (2 * WALL_X, WALL_BACK - WALL_FRONT, 0.1)), floor)], smooth=False)
    # walls: plaster with a red dado and a painted band near the top
    H = 3.3
    gate_y0, gate_y1 = -2.95, -1.75
    walls = [((0, WALL_BACK + 0.12, H / 2), (2 * WALL_X + 0.5, 0.24, H)), ((0, WALL_FRONT - 0.12, H / 2), (2 * WALL_X + 0.5, 0.24, H)),
             ((-WALL_X - 0.12, -0.25, H / 2), (0.24, WALL_BACK - WALL_FRONT, H))]
    right_parts = [(WALL_FRONT, gate_y0), (gate_y1, WALL_BACK)]
    for (y0, y1) in right_parts:
        walls.append(((WALL_X + 0.12, (y0 + y1) / 2, H / 2), (0.24, y1 - y0, H)))
    static('Walls', [(slab(c, s), wall) for c, s in walls], smooth=False)
    dado = []
    for c, s in walls:
        inward = 0.01
        if s[0] < s[1]:     # side wall
            x = c[0] - math.copysign(0.125 + inward, c[0])
            dado.append((slab((x, c[1], 0.45), (0.01, s[1], 0.9)), wall_low))
            dado.append((slab((x, c[1], 2.42), (0.01, s[1], 0.12)), frieze_a))
            dado.append((slab((x, c[1], 2.56), (0.01, s[1], 0.08)), frieze_b))
        else:
            y = c[1] - math.copysign(0.125 + inward, c[1])
            dado.append((slab((c[0], y, 0.45), (s[0], 0.01, 0.9)), wall_low))
            dado.append((slab((c[0], y, 2.42), (s[0], 0.01, 0.12)), frieze_a))
            dado.append((slab((c[0], y, 2.56), (s[0], 0.01, 0.08)), frieze_b))
    static('Dado and frieze', dado, smooth=False)
    # a doorway into the house in the back wall, and the gate to the street in the right wall
    static('House door', [(slab((0, WALL_BACK - 0.005, 1.15), (1.2, 0.02, 2.3)), door), (slab((0, WALL_BACK - 0.02, 2.36), (1.5, 0.05, 0.16)), beam)], smooth=False)
    static('Gate posts', [(slab((WALL_X + 0.12, gate_y0 - 0.06, 1.3), (0.34, 0.12, 2.6)), beam), (slab((WALL_X + 0.12, gate_y1 + 0.06, 1.3), (0.34, 0.12, 2.6)), beam),
                          (slab((WALL_X + 0.12, (gate_y0 + gate_y1) / 2, 2.62), (0.34, gate_y1 - gate_y0 + 0.24, 0.16)), beam)], smooth=False)
    # the street beyond the gate: a lane and the house across it
    static('Street', [(slab((WALL_X + 3.5, -1.0, -0.06), (6.5, 14, 0.1)), street)], smooth=False)
    static('House across', [(slab((WALL_X + 4.2, -1.0, 2.0), (0.3, 14, 4.0)), house), (slab((WALL_X + 4.04, -2.3, 1.0), (0.04, 0.9, 2.0)), door)], smooth=False)
    # the colonnade: columns along the back and down the right, under a tiled roof on beams
    shapes = []
    for (x, y) in COLUMNS:
        shapes += column(x, y, shaft, paint, capm)
    static('Columns', shapes)
    static('Colonnade roof', [(slab((0, 3.28, 2.8), (2 * WALL_X + 0.2, 1.05, 0.14)), beam), (slab((0, 3.3, 2.98), (2 * WALL_X + 0.2, 1.2, 0.08)), roof),
                              (slab((4.1, -0.75, 2.8), (1.05, 4.6, 0.14)), beam), (slab((4.12, -0.75, 2.98), (1.2, 4.6, 0.08)), roof)], smooth=False)
    # seats
    for name, (x, y, yaw) in SEATS.items():
        kind = CHAIR_KIND[name]
        if kind == 'chair':
            chair('Chair ' + name, x, y, yaw, wood, seat)
    cx, cy, cyaw = SEATS['cephalus']
    throne('Cephalus chair', cx, cy, cyaw, wood, cushion, gold)
    bx = SEATS['bench1'][0]
    bench('Bench', bx - 0.02, (SEATS['bench1'][1] + SEATS['bench2'][1]) / 2, 0.0 + 90.0, wood, bench_c, length=1.7)
    # the altar, with the fire of the sacrifice dying down
    ax, ay = ALTAR
    static('Altar', [(slab((ax, ay, 0.45), (0.9, 0.7, 0.9)), stone), (slab((ax, ay, 0.93), (1.02, 0.82, 0.08)), stone),
                     (slab((ax, ay, 0.06), (1.1, 0.9, 0.12)), stone)], smooth=False, bevel=0.02)
    fire = [(sphere((ax + rng.uniform(-0.25, 0.25), ay + rng.uniform(-0.18, 0.18), 0.99), (rng.uniform(0.05, 0.09), rng.uniform(0.05, 0.08), 0.03)), ember) for _ in range(9)]
    fire += [(sphere((ax + rng.uniform(-0.3, 0.3), ay + rng.uniform(-0.22, 0.22), 0.985), (0.07, 0.06, 0.02)), ash) for _ in range(7)]
    embers = static('Altar fire', fire)
    # racks of shields along the left wall: the family's shield workshop
    sh = []
    for row, z in enumerate((1.05, 1.95)):
        for k in range(5):
            y = -2.9 + k * 1.15 + (0.55 if row else 0)
            if y > 2.8:
                continue
            sh += shield((-WALL_X + 0.1, y, z), (1, 0, 0), bronze, rim, emb[(k + row) % 3], ('disc', 'bar', 'ring', None)[(k + 2 * row) % 4])
    sh.append((slab((-WALL_X + 0.07, -0.25, 0.55), (0.12, 6.5, 0.05)), beam))
    sh.append((slab((-WALL_X + 0.07, -0.25, 1.45), (0.12, 6.5, 0.05)), beam))
    static('Shields', sh)
    # amphorae and a potted olive in the corners
    am = []
    for (x, y) in ((-4.15, 3.25), (-3.8, 3.32), (4.2, 3.3)):
        prof = [(0, 0), (0.06, 0.02), (0.16, 0.18), (0.2, 0.42), (0.17, 0.62), (0.07, 0.72), (0.06, 0.82), (0.08, 0.85), (0, 0.85)]
        am.append((lathe(prof, 24, Matrix.Translation(V((x, y, 0)))), pot))
        am.append((ring((x, y, 0.42), 0.2, 0.012, seg=24, tseg=6), potb))
    static('Amphorae', am)
    ol = [(frustum((-4.0, -3.7, 0), (-4.0, -3.7, 0.45), 0.24, 0.3, seg=24), pot), (tube([(-4.0, -3.7, 0.4), (-3.95, -3.65, 1.1), (-4.05, -3.6, 1.6)], [0.06, 0.05, 0.04], seg=8), trunk)]
    for _ in range(26):
        c = V((-4.0 + rng.uniform(-0.45, 0.45), -3.6 + rng.uniform(-0.3, 0.35), rng.uniform(1.3, 2.2)))
        ol.append((sphere(c, (rng.uniform(0.12, 0.2),) * 2 + (rng.uniform(0.08, 0.12),)), leaf))
    static('Olive', ol)
    # lamp stands: tall bronze stands with an oil lamp on top
    fl = flame_material()
    flames = []
    for k, (x, y, z) in enumerate(LAMPS):
        prof = [(0, 0), (0.17, 0), (0.17, 0.03), (0.05, 0.08), (0.025, 0.12), (0.02, z - 0.12), (0.06, z - 0.08), (0.11, z - 0.05), (0.11, z - 0.03), (0, z - 0.03)]
        static('Lamp stand %d' % k, [(lathe(prof, 20, Matrix.Translation(V((x, y, 0)))), bronze),
                                     (sphere((x, y, z - 0.01), (0.09, 0.06, 0.035)), pot), (capsule((x + 0.08, y, z - 0.005), (x + 0.13, y, z + 0.005), 0.018, 0.012, seg=8), pot)])
        f = static('Lamp flame %d' % k, [(sphere((x + 0.135, y, z + 0.045), (0.018, 0.018, 0.045)), fl)])
        f.visible_shadow = False
        flames.append(f)
    return {'flames': flames, 'embers': embers, 'flame_mat': fl}


def boxes():
    """Seats as (name, low corner, high corner) boxes for the clearance check (axis-aligned around each seat)."""
    out = []
    for name, (x, y, yaw) in SEATS.items():
        r = 0.27 if CHAIR_KIND[name] != 'throne' else 0.33
        out.append(('seat ' + name, (x - r, y - r, SEAT - 0.08), (x + r, y + r, SEAT + 0.03)))
    return out
