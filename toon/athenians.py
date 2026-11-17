"""The Athenians of the Republic, as 3D cartoon characters in Edward's style (after his booth storyboard, like cast.py).

Each is a chiton and a himation over the motion-capture skeleton, with a face from cast.face(): lids, brows and a
mouth on their own bones. Importing this module adds them to cast.CAST, so stage.cast_one() can build them.
Characters face -Y; +X is their left.
"""
import math
import random

from mathutils import Quaternion, Vector

import cast
from cast import Head, base_mats, face, joints, limb, skirt_object, torso
from kit import Body, capsule, curls, frustum, material, ring, sphere, tube

V = Vector

# who: skin, hair colour, hair style, beard, chiton, himation, border, build, head radii, nose, extras
SPECS = {
    'Glaucon': dict(skin='#d39b70', hair='#3a2416', style='crop', beard='none', chiton='#f0e8d6', wrap='#2f5f8f', border='#e0c27a',
                    th=1.0, head=(0.142, 0.15, 0.162), nose='straight', chest=0.19, belly=0.17, seed=11),
    'Adeimantus': dict(skin='#c99064', hair='#2a1a12', style='crop', beard='short', chiton='#dfe0cf', wrap='#4d6b38', border='#d8c48a',
                       th=1.0, head=(0.145, 0.152, 0.158), nose='straight', chest=0.185, belly=0.175, seed=12),
    'Cephalus': dict(skin='#dcae8e', hair='#f1ede6', style='bald', beard='long', chiton='#f2ecdf', wrap='#5e3570', border='#d9a836',
                     th=0.94, head=(0.15, 0.155, 0.15), nose='round', chest=0.175, belly=0.2, seed=13, garland=True),
    'Polemarchus': dict(skin='#c58a5e', hair='#5a3a22', style='curls', beard='short', chiton='#e6d6b4', wrap='#b9822c', border='#7a3a1c',
                        th=1.03, head=(0.148, 0.155, 0.155), nose='round', chest=0.19, belly=0.19, seed=14),
    'Thrasymachus': dict(skin='#b67b55', hair='#141012', style='curls', beard='full', chiton='#d8c49a', wrap='#5a1d5c', border='#d9a836',
                         th=1.12, head=(0.16, 0.162, 0.156), nose='hook', chest=0.21, belly=0.215, seed=15),
    'Lysias': dict(skin='#cf9a73', hair='#4a2e1c', style='crop', beard='short', chiton='#efe8d8', wrap='#2f7a78', border='#e8d9a8',
                   th=0.98, head=(0.143, 0.15, 0.158), nose='straight', chest=0.185, belly=0.175, seed=16),
    'Euthydemus': dict(skin='#d6a37c', hair='#6b4426', style='crop', beard='none', chiton='#f2ead8', wrap='#b4552f', border='#f0d9a0',
                       th=0.95, head=(0.14, 0.148, 0.158), nose='round', chest=0.18, belly=0.17, seed=17),
    'Cleitophon': dict(skin='#bf8760', hair='#1f1712', style='curls', beard='short', chiton='#e9e0ca', wrap='#7a6a3a', border='#3a3020',
                       th=1.0, head=(0.146, 0.152, 0.156), nose='straight', chest=0.185, belly=0.185, seed=18),
    'Charmantides': dict(skin='#d8a985', hair='#8a6a48', style='crop', beard='full', chiton='#efe7d4', wrap='#3d4f7a', border='#c9b27a',
                         th=1.0, head=(0.148, 0.154, 0.154), nose='round', chest=0.19, belly=0.2, seed=19),
}


def greek(arm, who):
    S = SPECS[who]
    j = joints(arm)
    m = base_mats(who, S['skin'])
    hair = material(who + ' hair', S['hair'], rough=0.8)
    tunic = material(who + ' chiton', S['chiton'], rough=0.85)
    wrap = material(who + ' himation', S['wrap'], rough=0.85)
    border = material(who + ' border', S['border'], rough=0.7)
    sandal = material(who + ' sandal', '#6a4526', rough=0.7)
    B = Body(who)
    th = S['th']
    cx, cy = j['hip'].x, j['hip'].y
    torso(B, j, tunic, 0.17 * th, S['belly'] * th, S['chest'] * th, depth=0.84)
    for side in 'lr':
        limb(B, j, side, m, th=th, sleeve=tunic, short_sleeve=True, legs=tunic, shin=m['skin'] if who != 'Cephalus' else tunic, shoe=sandal, hand_kind='open')
        an = j['foot_' + side]
        B.add(ring(an + V((0, -0.01, 0.03)), 0.058, 0.012, tseg=6, seg=16), 'lowerleg_' + side, sandal)
        B.add(ring(an + V((0, -0.09, -0.012)), 0.05, 0.011, rot=Quaternion((1, 0, 0), math.pi / 2), tseg=6, seg=16), 'foot_' + side, sandal)
    # the chiton's skirt to the knee (to the shin for the old man), and the himation over the left shoulder
    hz = j['hip'].z
    hem = 0.3 if who == 'Cephalus' else 0.44
    # a short skirt on the body; the long part is its own object, hidden when the figure sits (the thighs are clothed)
    B.add(frustum((cx, cy, hz + 0.02), (cx, cy, hz - 0.12), 0.2 * th, 0.208 * th, caps=False, squash=0.8, seg=28), 'hip', tunic)
    r_hem = 0.24 * th          # the skirt's radius at the hem
    skirt_object(arm, who, hz + 0.0, hem, 0.199 * th, r_hem, tunic,
                 extra=[(frustum((cx, cy, hem + 0.035), (cx, cy, hem - 0.002), r_hem * 0.985, r_hem * 1.012, caps=False, squash=0.8, seg=28), border)])
    sp3 = j['spine_03']
    k = th
    path = [(cx - 0.14 * k, cy + 0.1, hz + 0.12), (cx - 0.172 * k, cy - 0.02, hz + 0.16), (cx - 0.12 * k, cy - 0.145 * k, hz + 0.25), (cx, cy - 0.172 * k, sp3.z - 0.1),
            (cx + 0.11 * k, cy - 0.13 * k, sp3.z + 0.06), (cx + 0.15 * k, cy - 0.01, sp3.z + 0.15), (cx + 0.12 * k, cy + 0.12 * k, sp3.z + 0.07),
            (cx + 0.02, cy + 0.17 * k, sp3.z - 0.12), (cx - 0.1 * k, cy + 0.16 * k, hz + 0.2)]

    def wz(co):
        t = min(1.0, max(0.0, (co.z - j['spine_01'].z) / (sp3.z - j['spine_01'].z)))
        return {'spine_01': 1 - t, 'spine_03': t}
    B.add(tube(path, [0.06, 0.07, 0.085, 0.1, 0.1, 0.1, 0.1, 0.095, 0.08], seg=12, flat=0.42), None, wrap, weights=wz)
    hang = [(cx + 0.15 * k, cy + 0.04, sp3.z + 0.14), (cx + 0.19 * k, cy + 0.1, sp3.z - 0.1), (cx + 0.2 * k, cy + 0.12, hz + 0.05), (cx + 0.19 * k, cy + 0.11, hz - 0.25)]
    B.add(tube(hang, [0.09, 0.1, 0.1, 0.08], seg=12, flat=0.4), None, wrap, weights=wz)
    B.add(sphere(V(hang[-1]) + V((0, 0, -0.01)), (0.075, 0.03, 0.022)), 'hip', border)       # the himation's weighted corner
    B.add(sphere((cx + 0.085 * k, cy - 0.165 * k, sp3.z + 0.035), (0.04, 0.016, 0.04)), 'spine_03', border)     # a brooch
    # neck and head
    B.add(capsule(j['neck'], j['head'] + V((0, 0, 0.02)), 0.056, 0.053), 'neck', m['skin'])
    hr = S['head']
    Hd = Head((cx, cy - 0.02, j['head'].z + 0.115), hr)
    B.add(sphere(Hd.C, Hd.R, seg=28, rings=18), 'head', m['skin'])
    old = who == 'Cephalus'
    face(B, arm, Hd, m, eye_yaw=18, eye_pitch=4 if not old else 2, eye_r=0.031 if not old else 0.029, brow=(hair, 0.016 if old else 0.014),
         brow_tilt={'Thrasymachus': -7, 'Cephalus': 3}.get(who, 1), mouth_w=0.034, mouth_pitch=-39,
         mouth_out=1.03 if S['beard'] in ('full', 'long') else 1.0)
    if S['nose'] == 'round':
        B.add(sphere(Hd.at(0, -9, 1.08), (0.034, 0.038, 0.032)), 'head', m['skin'])
    elif S['nose'] == 'hook':
        B.add(capsule(Hd.at(0, 4, 0.98), Hd.at(0, -12, 1.22), 0.026, 0.032, seg=12), 'head', m['skin'])
        B.add(sphere(Hd.at(0, -13, 1.2), (0.03, 0.03, 0.026)), 'head', m['skin'])
    else:
        B.add(capsule(Hd.at(0, 4, 0.98), Hd.at(0, -10, 1.16), 0.02, 0.026, seg=12), 'head', m['skin'])
    rng = random.Random(S['seed'])
    style = S['style']

    def hair_at(d):
        if style == 'bald':
            # a fringe round the back and over the ears, nothing on top
            if d.z > 0.38 or d.z < -0.25 or d.y < -0.15:
                return None
            return Hd.along(d, 1.0)
        if d.y < -0.25 and d.z < 0.72:
            return None
        if d.z < (-0.1 if style == 'curls' else 0.05) and d.y < 0.35:
            return None
        if style == 'crop' and d.z < -0.2:
            return None
        return Hd.along(d, 1.0)
    n_hair = {'curls': 72, 'crop': 80, 'bald': 34}[style]
    rad = {'curls': (0.034, 0.05), 'crop': (0.026, 0.036), 'bald': (0.028, 0.04)}[style]
    for c, r in curls(rng, n_hair, hair_at, rad):
        B.add(sphere(c, r, seg=10, rings=7), 'head', hair)
    beard = S['beard']
    if beard != 'none':
        mouth = Hd.at(0, -39, 1.0)

        def beard_at(d):
            if d.z > -0.08 or d.y > 0.25:
                return None
            if d.y < -0.8 and d.z > -0.42:
                return None
            out = {'short': 1.0, 'full': 1.04, 'long': 1.04}[beard]
            p = Hd.along(d, out) + V((0, -0.012, -0.03 if d.z < -0.5 else 0))
            return None if (p - mouth).length < 0.075 else p
        nb = {'short': 70, 'full': 62, 'long': 62}[beard]
        rb = {'short': (0.022, 0.03), 'full': (0.032, 0.048), 'long': (0.03, 0.044)}[beard]
        for c, r in curls(rng, nb, beard_at, rb):
            B.add(sphere(c, r, seg=10, rings=7), 'head', hair)
        if beard == 'long':
            # a long white beard falling to the chest
            B.add(sphere(Hd.C + V((0, -0.11, -0.2)), (0.1, 0.06, 0.13), seg=20, rings=12), 'head', hair)
            B.add(sphere(Hd.C + V((0, -0.12, -0.3)), (0.06, 0.04, 0.08)), 'head', hair)
        for x in (-1, 1):     # moustache
            B.add(capsule(Hd.at(x * 4, -22, 1.08), Hd.at(x * 20, -28, 1.05), 0.016, 0.012, seg=10, cap=4), 'head', hair)
    if S.get('garland'):
        leaf = material('Garland', '#5c7d34', rough=0.6)
        for a in range(0, 360, 20):
            p = Hd.at(a, 34 if abs(a - 180) > 60 else 20, 1.02)
            B.add(sphere(p, (0.026, 0.016, 0.014)), 'head', leaf)
    return B.finish(arm), Hd


for _who in SPECS:
    cast.CAST[_who] = (lambda w: (lambda arm: greek(arm, w)))(_who)
ATHENIANS = list(SPECS)
