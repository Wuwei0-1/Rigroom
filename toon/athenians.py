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

# Gyges IV's people of the Piraeus: the same builder, with costume options (hat, trousers, long sleeves, a bow and quiver)
EXTRAS = {
    'Niceratus': dict(skin='#cf9c74', hair='#3b2618', style='curls', beard='none', chiton='#ece2c8', wrap='#8a3a2a', border='#e2c88a',
                      th=0.98, head=(0.14, 0.148, 0.158), nose='straight', chest=0.18, belly=0.17, seed=21),
    'Servant Boy': dict(skin='#c08458', hair='#2a1a10', style='crop', beard='none', chiton='#b89a68', wrap=None, border='#a08a5a',
                        th=0.9, head=(0.15, 0.156, 0.16), nose='round', chest=0.17, belly=0.16, seed=22),
    'Child': dict(skin='#d2a07a', hair='#4a2e18', style='curls', beard='none', chiton='#8fb4cf', wrap=None, border='#c09a5a',
                  th=0.92, head=(0.158, 0.162, 0.166), nose='round', chest=0.17, belly=0.17, seed=23),
    'Fish Seller': dict(skin='#b27a50', hair='#5a5048', style='crop', beard='full', chiton='#cbbd9c', wrap='#6a5a40', border='#4a3a28',
                        th=1.06, head=(0.15, 0.155, 0.152), nose='round', chest=0.2, belly=0.22, seed=24),
    'Archer 1': dict(skin='#d8b08c', hair='#8a6a3a', style='crop', beard='full', chiton='#7a2e22', wrap=None, border='#e0b050',
                     th=1.02, head=(0.146, 0.152, 0.156), nose='straight', chest=0.19, belly=0.18, seed=25,
                     hat='scythian', hat_col='#a8422c', trousers='#3a4a6a', sleeves=True, bow=True),
    'Archer 2': dict(skin='#d2a882', hair='#6a4a2a', style='crop', beard='short', chiton='#2e4a3a', wrap=None, border='#d8b060',
                     th=1.0, head=(0.144, 0.15, 0.156), nose='hook', chest=0.19, belly=0.18, seed=26,
                     hat='scythian', hat_col='#c8a050', trousers='#6a2a2a', sleeves=True, bow=True),
}
for _k, (_cl, _cap) in enumerate((('#c8402a', '#b8662e'), ('#2a6ac8', '#a85a2a'), ('#d8a020', '#b8662e'), ('#2a9a6a', '#9a5228'),
                                  ('#a02a8a', '#b8662e'), ('#e0602a', '#a85a2a'))):
    EXTRAS['Thracian %d' % (_k + 1)] = dict(skin=('#c89068', '#d8a882', '#b88058')[_k % 3], hair=('#2a1a10', '#5a3a20', '#1a1410')[_k % 3],
                                            style='bald', beard=('full', 'short', 'none')[_k % 3], chiton='#efe2c4',
                                            wrap=_cl, border='#f0d080', th=1.0, head=(0.146, 0.152, 0.156), nose=('straight', 'round', 'hook')[_k % 3],
                                            chest=0.19, belly=0.18, seed=40 + _k, hat='fox', hat_col=_cap, trousers=None, cloak=True)
SCALES = {'Servant Boy': 0.66, 'Child': 0.56, 'Niceratus': 1.02, 'Fish Seller': 1.0, 'Archer 1': 1.06, 'Archer 2': 1.03}
SCALES.update({'Thracian %d' % (k + 1): (1.02, 1.05, 0.99, 1.04, 1.0, 1.03)[k] for k in range(6)})
SPECS.update(EXTRAS)


def greek(arm, who):
    S = SPECS[who]
    j = joints(arm)
    m = base_mats(who, S['skin'])
    hair = material(who + ' hair', S['hair'], rough=0.8)
    tunic = material(who + ' chiton', S['chiton'], rough=0.85)
    wrap = material(who + ' himation', S['wrap'], rough=0.85) if S['wrap'] else tunic
    border = material(who + ' border', S['border'], rough=0.7)
    sandal = material(who + ' sandal', '#6a4526', rough=0.7)
    B = Body(who)
    th = S['th']
    cx, cy = j['hip'].x, j['hip'].y
    torso(B, j, tunic, 0.17 * th, S['belly'] * th, S['chest'] * th, depth=0.84)
    trousers = material(who + ' trousers', S['trousers'], rough=0.8) if S.get('trousers') else None
    for side in 'lr':
        limb(B, j, side, m, th=th, sleeve=tunic, short_sleeve=not S.get('sleeves'), legs=trousers or tunic,
             shin=trousers or (m['skin'] if who != 'Cephalus' else tunic), shoe=sandal, hand_kind='open')
        an = j['foot_' + side]
        B.add(ring(an + V((0, -0.01, 0.03)), 0.058, 0.012, tseg=6, seg=16), 'lowerleg_' + side, sandal)
        B.add(ring(an + V((0, -0.09, -0.012)), 0.05, 0.011, rot=Quaternion((1, 0, 0), math.pi / 2), tseg=6, seg=16), 'foot_' + side, sandal)
    # the chiton's skirt to the knee (to the shin for the old man), and the himation over the left shoulder
    hz = j['hip'].z
    hem = 0.3 if who == 'Cephalus' else 0.44
    # a short skirt on the body; the long part is its own object, hidden when the figure sits (the thighs are clothed)
    B.add(frustum((cx, cy, hz + 0.02), (cx, cy, hz - 0.12), 0.182 * th, 0.19 * th, caps=False, squash=0.82, seg=28), 'hip', tunic)
    r_hem = 0.24 * th          # the skirt's radius at the hem
    sp3 = j['spine_03']
    k = th
    path = [(cx - 0.14 * k, cy + 0.1, hz + 0.12), (cx - 0.172 * k, cy - 0.02, hz + 0.16), (cx - 0.12 * k, cy - 0.145 * k, hz + 0.25), (cx, cy - 0.172 * k, sp3.z - 0.1),
            (cx + 0.11 * k, cy - 0.13 * k, sp3.z + 0.06), (cx + 0.15 * k, cy - 0.01, sp3.z + 0.15), (cx + 0.12 * k, cy + 0.12 * k, sp3.z + 0.07),
            (cx + 0.02, cy + 0.17 * k, sp3.z - 0.12), (cx - 0.1 * k, cy + 0.16 * k, hz + 0.2)]

    def wz(co):
        t = min(1.0, max(0.0, (co.z - j['spine_01'].z) / (sp3.z - j['spine_01'].z)))
        return {'spine_01': 1 - t, 'spine_03': t}
    if S['wrap'] is None:
        wrap = tunic
    B.add(tube(path, [0.06, 0.07, 0.085, 0.1, 0.1, 0.1, 0.1, 0.095, 0.08] if S['wrap'] else [0.03, 0.035, 0.04, 0.045, 0.045, 0.045, 0.045, 0.04, 0.035],
               seg=12, flat=0.42), None, wrap, weights=wz)
    # the end of the himation hanging down the left side: to the waist on the body, the rest with the long skirt
    # (hidden when the figure sits, so it never lies through a thigh or a chair)
    hang = [(cx + 0.15 * k, cy + 0.04, sp3.z + 0.14), (cx + 0.19 * k, cy + 0.1, sp3.z - 0.1), (cx + 0.2 * k, cy + 0.12, hz + 0.12)]
    if S['wrap']:
        B.add(tube(hang, [0.09, 0.1, 0.1], seg=12, flat=0.4), None, wrap, weights=wz)
    if S.get('cloak'):
        # a bright Thracian cloak (zeira) falling from the shoulders down the back
        cl = [(cx - 0.17 * k, cy + 0.06, sp3.z + 0.12), (cx, cy + 0.15 * k, sp3.z + 0.16), (cx + 0.17 * k, cy + 0.06, sp3.z + 0.12)]
        B.add(tube(cl, [0.06, 0.07, 0.06], seg=12, flat=0.5), 'spine_03', wrap)
        B.add(frustum((cx, cy + 0.11 * k, sp3.z + 0.1), (cx, cy + 0.17 * k, j['spine_01'].z - 0.05), 0.17 * k, 0.21 * k, caps=False, squash=0.35, seg=20),
              'spine_03', wrap)
    if S.get('bow'):
        wood_ = material(who + ' bow', '#5a3a1e', rough=0.6)
        q = [(cx + 0.12 * k, cy + 0.16 * k, sp3.z + 0.18), (cx + 0.02, cy + 0.2 * k, sp3.z - 0.05), (cx - 0.12 * k, cy + 0.16 * k, hz + 0.05)]
        B.add(tube(q, [0.012, 0.014, 0.012], seg=8, flat=0.0), 'spine_03', wood_)
        B.add(capsule((cx - 0.17 * k, cy + 0.05, hz + 0.02), (cx - 0.2 * k, cy + 0.08, hz - 0.3), 0.045, 0.04, seg=10), 'hip', border)    # the gorytos
    low = [(cx + 0.2 * k, cy + 0.12, hz + 0.16), (cx + 0.2 * k, cy + 0.12, hz + 0.05), (cx + 0.19 * k, cy + 0.11, hz - 0.25)]
    skirt_object(arm, who, hz + 0.0, hem, 0.199 * th, r_hem, tunic,
                 extra=[(frustum((cx, cy, hem + 0.035), (cx, cy, hem - 0.002), r_hem * 0.985, r_hem * 1.012, caps=False, squash=0.8, seg=28), border),
                        (tube(low, [0.1, 0.1, 0.08], seg=12, flat=0.4), wrap),
                        (sphere(V(low[-1]) + V((0, 0, -0.01)), (0.075, 0.03, 0.022)), border)])
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
    if S.get('hat') == 'fox':
        fur = material(who + ' fox cap', S['hat_col'], rough=0.9)
        B.add(sphere(Hd.C + V((0, 0.005, Hd.R[2] * 0.36)), (Hd.R[0] * 1.13, Hd.R[1] * 1.13, Hd.R[2] * 0.92)), 'head', fur)
        B.add(frustum(Hd.C + V((0, 0.01, Hd.R[2] * 0.9)), Hd.C + V((0, 0.03, Hd.R[2] * 1.55)), Hd.R[0] * 0.62, 0.03, caps=True, squash=0.9, seg=16), 'head', fur)
        for x in (-1, 1):       # ear flaps
            B.add(capsule(Hd.C + V((x * Hd.R[0] * 0.98, 0.0, Hd.R[2] * 0.1)), Hd.C + V((x * Hd.R[0] * 0.9, -0.01, -Hd.R[2] * 0.62)), 0.035, 0.026, seg=10), 'head', fur)
        B.add(capsule(Hd.C + V((0, Hd.R[1] * 0.9, Hd.R[2] * 0.2)), Hd.C + V((0, Hd.R[1] * 1.15, -Hd.R[2] * 1.9)), 0.04, 0.02, seg=10), 'head', fur)  # the tail
        B.add(sphere(Hd.C + V((0, -Hd.R[1] * 0.78, Hd.R[2] * 0.62)), (0.035, 0.04, 0.03)), 'head', fur)      # the fox's snout over the brow
    elif S.get('hat') == 'scythian':
        cap = material(who + ' cap', S['hat_col'], rough=0.8)
        B.add(frustum(Hd.C + V((0, 0.0, Hd.R[2] * 0.15)), Hd.C + V((0, 0.03, Hd.R[2] * 1.9)), Hd.R[0] * 1.08, 0.012, caps=True, squash=0.95, seg=20), 'head', cap)
        for x in (-1, 1):
            B.add(capsule(Hd.C + V((x * Hd.R[0] * 0.98, 0.01, Hd.R[2] * 0.15)), Hd.C + V((x * Hd.R[0] * 0.92, 0.0, -Hd.R[2] * 0.75)), 0.03, 0.024, seg=10), 'head', cap)
    if S.get('garland'):
        leaf = material('Garland', '#5c7d34', rough=0.6)
        for a in range(0, 360, 20):
            p = Hd.at(a, 34 if abs(a - 180) > 60 else 20, 1.02)
            B.add(sphere(p, (0.026, 0.016, 0.014)), 'head', leaf)
    return B.finish(arm), Hd


for _who in SPECS:
    cast.CAST[_who] = (lambda w: (lambda arm: greek(arm, w)))(_who)
ATHENIANS = list(SPECS)
