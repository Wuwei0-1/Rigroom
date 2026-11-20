"""Gyges IV's Piraeus: a sunlit street of white houses running down to the harbour, an alley, a little square and the
road up the hill to Cephalus's house, on the day of the festival of Bendis.

Like courtyard.py it gives SEAT, SEATS, SPOTS, LOOKS, CAMERAS, build() and animate(info, S, F, offset), which keys:
    S.prop('goddess', t0, t1=..., path=[spot names])   the image of the goddess carried along the street
Metres, Z up. The street runs along X (the harbour is off to -X, the hill road climbs away at +X); the houses stand
along its far side (+Y), the alley opens between them at x 1.6..2.6; the camera mostly looks along +Y.
"""
import math
import random

import bpy

import kit
import stage
from kit import capsule, frustum, material, slab, sphere, static

SEAT = 0.45
SEATS = {}
SPOTS = {
    # the procession, coming up from the harbour along the street
    'proc_a': (-12.0, 0.2), 'proc_b': (13.0, 0.2),
    'julian_mid': (-0.6, -0.2), 'julian_back': (0.9, 1.0), 'alley_mouth': (2.1, 2.3), 'alley_in': (2.1, 3.6), 'alley_deep': (2.1, 4.6),
    'fish': (-3.6, -1.85), 'child': (-2.2, -1.2), 'child_mother': (-2.6, -1.5),
    'archer_a': (5.5, 0.6), 'archer_b': (6.1, 0.9), 'archer_corner_a': (1.55, 1.6), 'archer_corner_b': (2.6, 1.7),
    'archer_on_a': (-6.0, 1.1), 'archer_on_b': (-6.4, 1.6),
    'square_a': (8.5, -1.6), 'square_b': (5.0, -0.6), 'soc_stop': (4.4, -0.5), 'glaucon_stop': (5.0, -0.9),
    'boy_run': (6.5, -0.2), 'boy_at': (4.0, -0.1),
    'pol_in': (10.5, -0.3), 'pol_at': (5.6, 0.2), 'adei_at': (6.1, -0.7), 'nic_at': (6.4, 0.6), 'yman1_at': (6.9, 0.0), 'yman2_at': (6.8, -1.2),
    'hill_a': (11.5, -0.4), 'hill_b': (15.5, -0.6), 'hill_c': (19.0, -0.8),
}
LOOKS = {'alley': (2.1, 3.0, 1.5), 'harbour': (-14.0, 4.0, 2.0), 'square': (6.0, -0.5, 1.5), 'shoes': (-0.6, -0.2, 0.05), 'hand': (0, 0, 1.5),
         'hill': (16.0, -0.6, 2.0), 'goddess': (0.0, 0.2, 2.2)}
CAMERAS = {
    'wide': ((-1.0, -8.5, 2.4), (0.6, 1.2, 1.3), 26),
    'harbour': ((5.5, -5.0, 2.2), (-6.0, 2.5, 1.4), 24),
    'julian': ((-1.3, -2.6, 1.55), (-0.6, -0.2, 1.4), 34),
    'alley': ((2.1, 6.8, 1.6), (2.1, 1.0, 1.2), 30),
    'alley_out': ((2.0, -3.0, 1.6), (2.1, 3.0, 1.35), 32),
    'square': ((1.6, -3.1, 1.8), (6.0, -0.3, 1.3), 30),
    'group': ((3.0, -3.4, 1.65), (5.6, -0.2, 1.4), 32),
    'hill': ((6.0, -6.0, 2.2), (14.0, -0.5, 1.6), 30),
    'follow': ((0.5, -7.0, 2.2), (2.0, 0.0, 1.3), 26),
}


def house(name, x0, x1, y, depth, h, wall, trim, door_mat, rng, roof=None):
    parts = [(slab(((x0 + x1) / 2, y + depth / 2, h / 2), (x1 - x0, depth, h)), wall),
             (slab(((x0 + x1) / 2, y - 0.02, h - 0.06), (x1 - x0 + 0.04, 0.08, 0.12)), trim)]
    w = x1 - x0
    dx = x0 + w * rng.uniform(0.3, 0.7)
    parts.append((slab((dx, y - 0.01, 1.0), (0.95, 0.06, 2.0)), door_mat))
    for k in range(rng.randint(1, 2)):
        wx = x0 + w * (0.2 + 0.6 * rng.random())
        if abs(wx - dx) > 0.9:
            parts.append((slab((wx, y - 0.01, 2.2), (0.42, 0.05, 0.42)), door_mat))
    if roof:
        parts.append((slab(((x0 + x1) / 2, y + depth / 2, h + 0.08), (w + 0.25, depth + 0.3, 0.16)), roof))
    return static(name, parts, smooth=False, bevel=0.03)


def build():
    rng = random.Random(17)
    stone = material('Street stone', '#d6c8ac', rough=0.85)
    joint = material('Street joint', '#a8987a', rough=0.9)
    white = material('Whitewash', '#efe8da', rough=0.8)
    white2 = material('Whitewash warm', '#f2dfc2', rough=0.8)
    ochre = material('Ochre wall', '#d9a86a', rough=0.8)
    trim = material('Blue trim', '#3d6f9a', rough=0.6)
    wood = material('Old wood', '#6a4a2e', rough=0.7)
    tile = material('Roof tile', '#b0532e', rough=0.8)
    sea = material('Harbour water', '#2f6f8f', rough=0.15, coat=1.0)
    hull = material('Hull', '#4a3020', rough=0.6)
    canvas = material('Awning', '#c8b48a', rough=0.9)
    stripe = material('Awning stripe', '#9a3a2a', rough=0.9)
    fish = material('Fish', '#b8c4cc', rough=0.3, metal=0.4)
    # the ground: big flagstones, and the hill road rising at +X
    static('Street', [(slab((0.0, 0.0, -0.05), (40.0, 30.0, 0.1)), stone)], smooth=False)
    js = []
    for k in range(-20, 21):
        js.append((slab((k * 0.9, 0.0, 0.002), (0.025, 14.0, 0.006)), joint))
    for k in range(-7, 8):
        js.append((slab((0.0, k * 0.9 + 0.45, 0.002), (40.0, 0.025, 0.006)), joint))
    static('Street joints', js, smooth=False)
    road = static('Hill road', [(slab((0, 0, 0), (12.0, 4.0, 0.2)), stone)], smooth=False)
    road.location = (17.0, -0.6, 0.55)
    road.rotation_euler = (0.0, -math.radians(6), 0.0)
    # the far side of the street: a row of white houses with the alley between them
    mats = (white, white2, ochre, white)
    x = -11.0
    k = 0
    while x < 11.5:
        w = rng.uniform(2.4, 3.6)
        x1 = min(x + w, 11.5)
        if x < 1.6 < x1:
            x1 = 1.6
        house('House %d' % k, x, x1, 2.6 if k % 2 else 2.75, 4.0, rng.uniform(3.2, 4.6), mats[k % 4], trim, wood, rng, tile if k % 3 == 1 else None)
        k += 1
        x = x1 if x1 != 1.6 else 2.6
    # the alley walls running back
    static('Alley walls', [(slab((1.5, 5.5, 2.0), (0.2, 6.0, 4.0)), white2), (slab((2.7, 5.5, 2.0), (0.2, 6.0, 4.0)), white),
                           (slab((2.1, 8.6, 2.0), (1.4, 0.2, 4.0)), ochre)], smooth=False)
    # the near side, behind the camera: a low wall and a couple of houses so reverse shots see something
    # the fish stall
    st = [(slab((-3.6, -2.5, 0.8), (1.6, 0.8, 0.06)), wood)]
    for dx in (-0.75, 0.75):
        for dy in (-0.35, 0.35):
            st.append((capsule((-3.6 + dx, -2.5 + dy, 0.0), (-3.6 + dx, -2.5 + dy, 2.0), 0.03, seg=8), wood))
    st.append((slab((-3.6, -2.5, 2.05), (1.9, 1.1, 0.03)), canvas))
    for k in range(4):
        st.append((slab((-4.4 + k * 0.5, -2.5, 2.07), (0.22, 1.1, 0.02)), stripe))
    for k in range(7):
        st.append((sphere((-4.15 + k * 0.18, -2.45 + 0.08 * (k % 2), 0.86), (0.08, 0.026, 0.022)), fish))
    static('Fish stall', st, smooth=False)
    # a second stall with jars
    jar = material('Jar', '#b86a3a', rough=0.7)
    st2 = [(slab((-6.6, -2.3, 0.75), (1.4, 0.7, 0.06)), wood), (slab((-6.6, -2.3, 2.0), (1.7, 1.0, 0.03)), stripe)]
    for dx in (-0.65, 0.65):
        for dy in (-0.3, 0.3):
            st2.append((capsule((-6.6 + dx, -2.3 + dy, 0.0), (-6.6 + dx, -2.3 + dy, 1.95), 0.03, seg=8), wood))
    for k in range(4):
        st2.append((frustum((-7.1 + k * 0.32, -2.3, 0.78), (-7.1 + k * 0.32, -2.3, 1.05), 0.09, 0.05, seg=14), jar))
    static('Jar stall', st2, smooth=False)
    # the harbour: water past the end of the street, hulls and a crowd of masts
    static('Harbour', [(slab((-28.0, 6.0, -0.35), (24.0, 40.0, 0.1)), sea), (slab((-16.2, 6.0, -0.1), (0.4, 40.0, 0.5)), stone)], smooth=False)
    ms = []
    for k in range(11):
        mx, my = -18.0 - rng.uniform(0, 10), rng.uniform(-6, 16)
        h = rng.uniform(6.5, 10.0)
        ms.append((capsule((mx, my, -0.2), (mx, my, h), 0.07, 0.05, seg=8), wood))
        ms.append((capsule((mx - 1.4, my, h * 0.82), (mx + 1.4, my, h * 0.82), 0.04, seg=6), wood))
        ms.append((slab((mx, my, 0.1), (1.6, 6.5, 0.8)), hull))
    static('Ships', ms, smooth=False)
    # the litter that carries the image of the goddess
    gold = material('Goddess gold', '#d9a836', rough=0.35, metal=1.0)
    robe = material('Goddess robe', '#e8d8b8', rough=0.6)
    lit = static('Goddess', [(slab((0, 0, 1.15), (1.3, 0.75, 0.08)), wood), (capsule((-1.0, -0.3, 1.1), (1.0, -0.3, 1.1), 0.035, seg=8), wood),
                             (capsule((-1.0, 0.3, 1.1), (1.0, 0.3, 1.1), 0.035, seg=8), wood),
                             (frustum((0, 0, 1.2), (0, 0, 2.15), 0.26, 0.11, seg=20), robe), (sphere((0, 0, 2.27), 0.11), gold),
                             (capsule((0.2, 0, 1.6), (0.25, 0, 2.6), 0.015, seg=6), gold)], smooth=False)
    lit.location = (-30.0, 0.2, 0.0)
    # the sun: high, white and hard
    stage.light('Harbour bounce', 'AREA', (0.0, -3.0, 0.4), 400, (1.0, 0.92, 0.8), 8.0, to=(0.0, 0.0, 2.0), shadow=False)
    return {'goddess': lit}


def animate(info, S, F, offset):
    lit = info['goddess']
    for kind, t, kw in S.props:
        if kind != 'goddess':
            continue
        a, b = kw.get('frm', 'proc_a'), kw.get('to', 'proc_b')
        a, b = (SPOTS[a] if isinstance(a, str) else a), (SPOTS[b] if isinstance(b, str) else b)
        t1 = kw.get('t1') or t + math.hypot(b[0] - a[0], b[1] - a[1]) / max(0.3, getattr(S, 'speed', 1.0))
        for fr, p in ((F(t), a), (F(t1), b)):
            lit.location = (p[0] + offset.x, p[1] + offset.y, 0.0)
            lit.keyframe_insert('location', frame=fr)
        for fc in (lit.animation_data.action.fcurves if hasattr(lit.animation_data.action, 'fcurves') else []):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
