"""Edward's cast as 3D cartoon characters: Socrates, Aria, Cleon and Julian, after his booth storyboard.

Each is built in the T-pose of the motion-capture skeleton it will be driven by, so recorded motion plays on it as is.
Characters face -Y; +X is their left.
"""
import math
import random

import bpy
from mathutils import Quaternion, Vector

from kit import Body, capsule, curls, frustum, material, ring, slab, sphere, tube

V = Vector


RING_ON = 'Socrates'     # who wears the brass ring (Gyges IV: Julian)
SPLIT_SKIRT = False     # Gyges IV: the long skirt of a chiton is its own object (hidden on a seated figure), with a short one on the body


def skirt_object(arm, who, top, hem, r0, r1, mat, squash=0.8, extra=()):
    """The long part of a skirt as its own skinned object, bound to the hips, named '<who> skirt'."""
    cx, cy = joints(arm)['hip'].x, joints(arm)['hip'].y
    S = Body(who + ' skirt')
    S.add(frustum((cx, cy, top), (cx, cy, hem), r0, r1, caps=False, squash=squash, seg=28), 'hip', mat)
    for shape, m in extra:
        S.add(shape, 'hip', m)
    return S.finish(arm)


def joints(arm):
    return {b.name: b.head_local.copy() for b in arm.data.bones}


def add_bone(arm, name, head, parent='head', up=0.03):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones.new(name)
    eb.head = head
    eb.tail = V(head) + V((0, 0, up))
    eb.roll = 0
    eb.parent = arm.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')


class Head:
    """Where things sit on a head: an ellipsoid at C with radii R, facing -Y."""

    def __init__(self, C, R):
        self.C, self.R = V(C), V(R)

    def at(self, yaw, pitch, out=1.0):
        """A point on the head: yaw to the character's left (+X), pitch up, in degrees."""
        y, p = math.radians(yaw), math.radians(pitch)
        d = V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
        return self.C + V((d.x * self.R.x, d.y * self.R.y, d.z * self.R.z)) * out

    def along(self, d, out=1.0):
        return self.C + V((d.x * self.R.x, d.y * self.R.y, d.z * self.R.z)) * out


def torso(B, j, mat, hipr, belly, chest, depth=0.78, neckr=0.5, mat_low=None):
    """The trunk from hips to neck, bending with the spine."""
    hip, s1, s2, s3, neck = j['hip'], j['spine_01'], j['spine_02'], j['spine_03'], j['neck']
    z0, z1 = hip.z - 0.11, neck.z + 0.015
    H = z1 - z0
    prof = [(0, z0), (hipr * 0.6, z0 + 0.015 * H), (hipr * 0.9, z0 + 0.06 * H), (hipr, z0 + 0.14 * H), ((hipr + belly) / 2, z0 + 0.26 * H), (belly, z0 + 0.38 * H),
            ((belly + chest) / 2, z0 + 0.55 * H), (chest, z0 + 0.7 * H), (chest * 1.02, z0 + 0.82 * H), (chest * 0.9, z0 + 0.9 * H), (chest * neckr, z0 + 0.97 * H), (0, z1)]
    from kit import lathe
    from mathutils import Matrix
    M = Matrix.Translation(V((hip.x, hip.y, 0))) @ Matrix.Diagonal((1, depth, 1, 1))
    hs = [('hip', hip.z), ('spine_01', s1.z), ('spine_02', s2.z), ('spine_03', s3.z)]

    def w(co):
        if co.z <= hs[0][1]:
            return {'hip': 1.0}
        for (a, za), (b, zb) in zip(hs, hs[1:]):
            if co.z <= zb:
                t = (co.z - za) / (zb - za)
                return {a: 1 - t, b: t}
        return {'spine_03': 1.0}

    v, f = lathe(prof, 32, M)
    waist = z0 + 0.2 * H
    B.add((v, f), None, mat, weights=w, mat_of=(lambda c: mat_low if c.z < waist else mat) if mat_low else None)


def limb(B, j, side, m, th=1.0, sleeve=None, short_sleeve=False, legs=None, shin=None, shoe=None, hand_kind='open', hs=1.25, foot=1.0):
    s = 1 if side == 'l' else -1
    sh, el, wr = j['upperarm_' + side], j['lowerarm_' + side], j['hand_' + side]
    skin = m['skin']
    up = sleeve or skin
    B.add(sphere(sh, 0.064 * th), 'upperarm_' + side, up)
    if short_sleeve:
        mid = sh.lerp(el, 0.5)
        B.add(capsule(sh, mid, 0.07 * th, 0.066 * th), 'upperarm_' + side, sleeve)
        B.add(capsule(sh, el, 0.056 * th, 0.05 * th), 'upperarm_' + side, skin)
        B.add(capsule(el, wr, 0.05 * th, 0.04 * th), 'lowerarm_' + side, skin)
    else:
        B.add(capsule(sh, el, 0.064 * th, 0.056 * th), 'upperarm_' + side, up)
        B.add(capsule(el, wr - V((s * 0.02, 0, 0)), 0.056 * th, 0.046 * th), 'lowerarm_' + side, up)
        if sleeve:
            B.add(ring(wr - V((s * 0.02, 0, 0)), 0.045 * th, 0.014, rot=Quaternion((0, 1, 0), math.pi / 2), tseg=6, seg=16), 'lowerarm_' + side, sleeve)
    hand(B, j, side, hand_kind, skin, hs)
    hp, kn, an = j['upperleg_' + side], j['lowerleg_' + side], j['foot_' + side]
    B.add(capsule(hp, kn, 0.098 * th, 0.08 * th), 'upperleg_' + side, legs or skin)
    B.add(capsule(kn, an, 0.074 * th, 0.052 * th), 'lowerleg_' + side, shin or legs or skin)
    B.add(sphere(an + V((0, -0.075 * foot, -0.022)), (0.058 * foot, 0.135 * foot, 0.045)), 'foot_' + side, shoe or skin)


def hand(B, j, side, kind, skin, hs=1.25):
    """A four-fingered cartoon hand. kind: open, hold (curled round something), point (index out), fist."""
    s = 1 if side == 'l' else -1
    H = j['hand_' + side]
    bone = 'hand_' + side

    def P(x, y, z):
        return H + V((s * x, y, z)) * hs

    B.add(sphere(P(0.045, 0, 0), V((0.052, 0.046, 0.024)) * hs), bone, skin)
    for i, y in enumerate((-0.033, -0.011, 0.011, 0.032)):
        ln = (0.062, 0.07, 0.066, 0.052)[i]
        out = kind == 'open' or (kind == 'point' and i == 0)
        if out:
            B.add(capsule(P(0.085, y, 0), P(0.085 + ln, y, -0.004), 0.0135 * hs, 0.012 * hs, seg=10, cap=4), bone, skin)
        else:
            c = 0.03 if kind == 'hold' else 0.018
            B.add(capsule(P(0.085, y, 0), P(0.085 + c, y, -0.034), 0.0135 * hs, 0.0125 * hs, seg=10, cap=4), bone, skin)
            B.add(capsule(P(0.085 + c, y, -0.034), P(0.07, y, -0.05 if kind == 'hold' else -0.036), 0.0125 * hs, 0.012 * hs, seg=10, cap=4), bone, skin)
    if kind in ('open', 'point'):
        B.add(capsule(P(0.03, -0.04, 0), P(0.075, -0.075, -0.006), 0.016 * hs, 0.013 * hs, seg=10, cap=4), bone, skin)
    else:
        B.add(capsule(P(0.03, -0.04, -0.004), P(0.07, -0.05, -0.03), 0.016 * hs, 0.013 * hs, seg=10, cap=4), bone, skin)


def face(B, arm, Hd, m, eye_yaw=17, eye_pitch=6, eye_r=0.034, pupil=0.46, brow=None, brow_tilt=0, mouth_w=0.036, mouth_pitch=-36,
         mouth_out=0.985, ears=True, lid_mat=None):
    """Eyes with lids that close, brows, ears and a mouth that opens. Adds the control bones lid_l, lid_r, mouth."""
    skin = m['skin']
    for side, s in (('l', 1), ('r', -1)):
        e = Hd.at(s * eye_yaw, eye_pitch, 1.0) + V((0, eye_r * 0.55, 0))
        add_bone(arm, 'lid_' + side, e)
        B.add(sphere(e, eye_r, seg=18, rings=10), 'head', m['white'])
        B.add(sphere(e + V((-s * 0.004, -eye_r * 0.86, -0.002)), (eye_r * pupil, eye_r * 0.22, eye_r * pupil), seg=14, rings=8), 'head', m['pupil'])
        # the lid: a half shell whose pole points up when the bone is at rest
        prof = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 91, 15)]
        prof[-1] = (0, 1)
        from kit import lathe
        from mathutils import Matrix
        B.add(lathe(prof, 18, Matrix.Translation(e) @ Matrix.Diagonal((eye_r * 1.13,) * 3 + (1,))), 'lid_' + side, lid_mat or skin)
        if brow:
            # each brow on its own bone, so it can lift, knit and tilt
            a = Hd.at(s * (eye_yaw - 9), eye_pitch + 21 + brow_tilt, 1.04)
            b = Hd.at(s * (eye_yaw + 10), eye_pitch + 21 - brow_tilt, 1.04)
            add_bone(arm, 'brow_' + side, (a + b) / 2)
            B.add(capsule(a, b, brow[1], brow[1] * 0.8, seg=10, cap=4), 'brow_' + side, brow[0])
        if ears:
            B.add(sphere(Hd.at(s * 92, 0, 0.99), (0.02, 0.034, 0.045)), 'head', skin)
    # the mouth: a centre bone opens it; a bone at each corner lifts (smile), drops (frown) or draws it in
    mc = Hd.at(0, mouth_pitch, mouth_out)
    add_bone(arm, 'mouth', mc)
    for side, s in (('l', 1), ('r', -1)):
        add_bone(arm, 'mouth_' + side, mc + V((s * mouth_w, 0, 0)))

    def mw(co):
        t = (co.x - mc.x) / mouth_w
        sm = lambda x: 0.0 if x <= 0.15 else (1.0 if x >= 1 else ((x - 0.15) / 0.85) ** 2 * (3 - 2 * (x - 0.15) / 0.85))
        wl, wr = sm(t), sm(-t)
        return {'mouth': max(0.0, 1 - wl - wr), 'mouth_l': wl, 'mouth_r': wr}
    B.add(sphere(mc, (mouth_w, 0.009, 0.012), seg=24, rings=8), None, m['mouth'], weights=mw)
    return mc


def base_mats(tag, skin):
    return {'skin': material(tag + ' skin', skin, rough=0.6, sss=0.08), 'white': material('Eye white', '#f4f1ea', rough=0.3),
            'pupil': material('Eye pupil', '#17120f', rough=0.25, coat=0.6), 'mouth': material('Mouth', '#5a1f24', rough=0.6)}


# ---------------------------------------------------------------- the four

def socrates(arm):
    j = joints(arm)
    m = base_mats('Socrates', '#c68a63')
    hair = material('Socrates hair', '#e4dfd4', rough=0.85)
    tunic = material('Socrates chiton', '#e9dcc0', rough=0.85)
    wrap = material('Socrates himation', '#8a2c36', rough=0.85)
    gold = material('Gold', '#d9a836', rough=0.3, metal=1.0)
    sandal = material('Sandal', '#6a4526', rough=0.7)
    B = Body('Socrates')
    cx, cy = j['hip'].x, j['hip'].y
    torso(B, j, tunic, 0.175, 0.205, 0.185, depth=0.86)
    for side in 'lr':
        limb(B, j, side, m, th=1.05, sleeve=tunic, short_sleeve=True, legs=tunic, shoe=sandal, hand_kind='point' if side == 'r' else 'open')
        s = 1 if side == 'l' else -1
        an = j['foot_' + side]
        B.add(ring(an + V((0, -0.01, 0.03)), 0.058, 0.012, tseg=6, seg=16), 'lowerleg_' + side, sandal)
        B.add(ring(an + V((0, -0.09, -0.012)), 0.05, 0.011, rot=Quaternion((1, 0, 0), math.pi / 2), tseg=6, seg=16), 'foot_' + side, sandal)
    # the chiton's skirt to mid-shin, and the himation over the left shoulder
    hz = j['hip'].z
    if SPLIT_SKIRT:
        B.add(frustum((cx, cy, hz + 0.02), (cx, cy, hz - 0.12), 0.2, 0.208, caps=False, squash=0.8, seg=28), 'hip', tunic)
        skirt_object(arm, 'Socrates', hz + 0.0, 0.34, 0.199, 0.25, tunic)
    else:
        B.add(frustum((cx, cy, hz + 0.02), (cx, cy, 0.34), 0.2, 0.25, caps=False, squash=0.8, seg=28), 'hip', tunic)
    sp3 = j['spine_03']
    path = [(cx - 0.16, cy + 0.11, hz + 0.1), (cx - 0.2, cy - 0.02, hz + 0.14), (cx - 0.13, cy - 0.15, hz + 0.24), (cx, cy - 0.175, sp3.z - 0.1),
            (cx + 0.11, cy - 0.13, sp3.z + 0.06), (cx + 0.15, cy - 0.01, sp3.z + 0.15), (cx + 0.12, cy + 0.12, sp3.z + 0.07), (cx + 0.02, cy + 0.17, sp3.z - 0.12),
            (cx - 0.1, cy + 0.16, hz + 0.2)]

    def wz(co):
        t = min(1.0, max(0.0, (co.z - j['spine_01'].z) / (sp3.z - j['spine_01'].z)))
        return {'spine_01': 1 - t, 'spine_03': t}
    B.add(tube(path, [0.085, 0.09, 0.095, 0.1, 0.1, 0.1, 0.1, 0.095, 0.09], seg=12, flat=0.42), None, wrap, weights=wz)
    B.add(tube([(cx + 0.15, cy + 0.04, sp3.z + 0.14), (cx + 0.19, cy + 0.1, sp3.z - 0.1), (cx + 0.2, cy + 0.12, hz + 0.05), (cx + 0.19, cy + 0.11, hz - 0.25)],
               [0.09, 0.1, 0.1, 0.08], seg=12, flat=0.4), None, wrap, weights=wz)
    B.add(sphere((cx + 0.085, cy - 0.165, sp3.z + 0.035), (0.045, 0.016, 0.045)), 'spine_03', gold)
    B.add(ring((cx + 0.085, cy - 0.176, sp3.z + 0.035), 0.022, 0.006, rot=Quaternion((1, 0, 0), math.pi / 2), tseg=6, seg=16), 'spine_03', gold)
    # a brass ring on the pointing hand
    hr = j['hand_r']
    if RING_ON == 'Socrates':
        B.add(ring(hr + V((-0.118, -0.041, 0)), 0.02, 0.006, rot=Quaternion((0, 1, 0), math.pi / 2), tseg=6, seg=14), 'hand_r', gold)
    B.add(capsule(j['neck'], j['head'] + V((0, 0, 0.02)), 0.058, 0.055), 'neck', m['skin'])
    Hd = Head((cx, cy - 0.02, j['head'].z + 0.115), (0.152, 0.158, 0.152))
    B.add(sphere(Hd.C, Hd.R, seg=28, rings=18), 'head', m['skin'])
    face(B, arm, Hd, m, eye_yaw=18, eye_pitch=5, eye_r=0.033, brow=(hair, 0.017), brow_tilt=6, mouth_w=0.036, mouth_pitch=-38, mouth_out=1.035)
    B.add(sphere(Hd.at(0, -9, 1.1), (0.04, 0.045, 0.036)), 'head', m['skin'])     # a round nose
    rng = random.Random(7)

    def hair_at(d):
        if d.y < -0.25 and d.z < 0.72:
            return None
        if d.z < -0.15 and d.y < 0.35:
            return None
        return Hd.along(d, 1.0)

    def beard_at(d):
        if d.z > -0.08 or d.y > 0.25:
            return None
        if d.y < -0.8 and d.z > -0.42:      # leave the mouth
            return None
        p = Hd.along(d, 1.04) + V((0, -0.012, -0.03 if d.z < -0.5 else 0))
        return None if (p - Hd.at(0, -38, 1.035)).length < 0.08 else p
    for c, r in curls(rng, 70, hair_at, (0.034, 0.05)):
        B.add(sphere(c, r, seg=10, rings=7), 'head', hair)
    for c, r in curls(rng, 60, beard_at, (0.03, 0.046)):
        B.add(sphere(c, r, seg=10, rings=7), 'head', hair)
    for x in (-1, 1):     # moustache
        B.add(capsule(Hd.at(x * 4, -21, 1.1), Hd.at(x * 21, -27, 1.07), 0.02, 0.015, seg=10, cap=4), 'head', hair)
    return B.finish(arm), Hd


def aria(arm):
    j = joints(arm)
    m = base_mats('Aria', '#8a573a')
    hair = material('Aria hair', '#241815', rough=0.55)
    top = material('Aria cardigan', '#dfa22b', rough=0.85)
    skirt = material('Aria skirt', '#5a2a4d', rough=0.85)
    frame = material('Glasses', '#15151a', rough=0.3, coat=0.5)
    shoe = material('Aria shoe', '#2c2024', rough=0.5)
    blouse = material('Aria blouse', '#f1e9dc', rough=0.8)
    B = Body('Aria')
    cx, cy = j['hip'].x, j['hip'].y
    torso(B, j, top, 0.185, 0.19, 0.18, depth=0.84, mat_low=skirt)
    for side in 'lr':
        limb(B, j, side, m, th=1.06, sleeve=top, legs=skirt, shin=skirt, shoe=shoe, hand_kind='open', foot=0.9)
    sp3 = j['spine_03']
    B.add(sphere((cx, cy - 0.105, sp3.z + 0.09), (0.06, 0.03, 0.05)), 'spine_03', blouse)      # blouse at the neckline
    B.add(capsule(j['neck'], j['head'] + V((0, 0, 0.02)), 0.052, 0.05), 'neck', m['skin'])
    Hd = Head((cx, cy - 0.02, j['head'].z + 0.112), (0.156, 0.155, 0.148))
    B.add(sphere(Hd.C, Hd.R, seg=28, rings=18), 'head', m['skin'])
    face(B, arm, Hd, m, eye_yaw=18, eye_pitch=4, eye_r=0.031, pupil=0.5, brow=(hair, 0.011), brow_tilt=3, mouth_w=0.032, mouth_pitch=-38)
    B.add(sphere(Hd.at(0, -12, 1.08), (0.03, 0.034, 0.028)), 'head', m['skin'])
    # hair swept up into a bun
    B.add(sphere(Hd.C + V((0, 0.03, 0.03)), (0.163, 0.158, 0.15), seg=28, rings=18), 'head', hair)
    B.add(sphere(Hd.C + V((0, 0.035, 0.2)), (0.085, 0.085, 0.07)), 'head', hair)
    B.add(ring(Hd.C + V((0, 0.035, 0.15)), 0.05, 0.014, tseg=6, seg=18), 'head', top)
    for s in (-1, 1):
        e = Hd.at(s * 18, 4, 1.0) + V((0, -0.022, 0))
        B.add(ring(e, 0.043, 0.0065, rot=Quaternion((1, 0, 0), math.pi / 2), tseg=6, seg=24), 'head', frame)
        B.add(tube([e + V((s * 0.043, 0, 0)), Hd.at(s * 80, 6, 1.03), Hd.at(s * 100, 4, 1.03)], 0.005, seg=6), 'head', frame)
    B.add(capsule(Hd.at(-18, 4, 1.0) + V((0.043, -0.022, 0.004)), Hd.at(18, 4, 1.0) + V((-0.043, -0.022, 0.004)), 0.0055, seg=6, cap=3), 'head', frame)
    return B.finish(arm), Hd


def cleon(arm):
    j = joints(arm)
    m = base_mats('Cleon', '#e3b08c')
    hair = material('Cleon hair', '#553621', rough=0.6)
    hoodie = material('Cleon hoodie', '#56724c', rough=0.9)
    tee = material('Cleon tee', '#e9e2d3', rough=0.8)
    jeans = material('Cleon jeans', '#2e4268', rough=0.8)
    shoe = material('Cleon shoe', '#e6e0d2', rough=0.6)
    B = Body('Cleon')
    cx, cy = j['hip'].x, j['hip'].y
    torso(B, j, hoodie, 0.16, 0.165, 0.185, depth=0.8, mat_low=jeans)
    for side in 'lr':
        limb(B, j, side, m, th=0.98, sleeve=hoodie, legs=jeans, shoe=shoe, hand_kind='open', foot=1.05)
    sp3 = j['spine_03']
    B.add(sphere((cx, cy - 0.11, sp3.z + 0.085), (0.055, 0.03, 0.05)), 'spine_03', tee)
    B.add(sphere((cx, cy + 0.1, sp3.z + 0.1), (0.14, 0.085, 0.09)), 'spine_03', hoodie)       # the hood, down
    B.add(ring((cx, cy, sp3.z + 0.14), 0.085, 0.028, seg=20, tseg=8), 'spine_03', hoodie)
    B.add(capsule(j['neck'], j['head'] + V((0, 0, 0.02)), 0.055, 0.052), 'neck', m['skin'])
    Hd = Head((cx, cy - 0.02, j['head'].z + 0.118), (0.138, 0.15, 0.158))
    B.add(sphere(Hd.C, Hd.R, seg=28, rings=18), 'head', m['skin'])
    face(B, arm, Hd, m, eye_yaw=17, eye_pitch=8, eye_r=0.03, brow=(hair, 0.014), brow_tilt=4, mouth_w=0.034, mouth_pitch=-40, mouth_out=1.2)
    B.add(capsule(Hd.at(0, 2, 0.98), Hd.at(0, -14, 1.3), 0.024, 0.03, seg=12), 'head', m['skin'])       # a long nose
    B.add(sphere(Hd.C + V((0, 0.035, 0.035)), (0.144, 0.15, 0.155), seg=28, rings=18), 'head', hair)
    B.add(sphere(Hd.C + V((0, 0.13, 0.15)), 0.06), 'head', hair)                                        # the man-bun
    # a full beard: a soft mass round the jaw
    B.add(sphere(Hd.C + V((0, -0.03, -0.085)), (0.13, 0.125, 0.105), seg=24, rings=14), 'head', hair)
    B.add(sphere(Hd.C + V((0, -0.06, -0.15)), (0.085, 0.08, 0.07)), 'head', hair)
    for x in (-1, 1):
        B.add(capsule(Hd.at(x * 3, -25, 1.12), Hd.at(x * 19, -31, 1.1), 0.019, 0.014, seg=10, cap=4), 'head', hair)
        B.add(sphere(Hd.at(x * 70, -4, 0.97), (0.02, 0.04, 0.07)), 'head', hair)      # sideburns
    return B.finish(arm), Hd


def julian(arm):
    j = joints(arm)
    m = base_mats('Julian', '#d5a27c')
    hair = material('Julian hair', '#16161b', rough=0.45)
    shirt = material('Julian shirt', '#9cc0de', rough=0.85)
    collar = material('Julian collar', '#eef3f7', rough=0.8)
    vest = material('Julian vest', '#3b4152', rough=0.85)
    trousers = material('Julian trousers', '#343844', rough=0.8)
    shoe = material('Julian shoe', '#1f1c1c', rough=0.4)
    B = Body('Julian')
    if RING_ON == 'Julian':
        brass = material('Ring brass', '#d9a836', rough=0.3, metal=1.0)
        B.add(ring(j['hand_r'] + V((-0.118, -0.041, 0)), 0.02 * 0.9, 0.006, rot=Quaternion((0, 1, 0), math.pi / 2), tseg=6, seg=14), 'hand_r', brass)
    cx, cy = j['hip'].x, j['hip'].y
    torso(B, j, vest, 0.15, 0.142, 0.176, depth=0.74, mat_low=trousers)
    for side in 'lr':
        limb(B, j, side, m, th=0.86, sleeve=shirt, legs=trousers, shoe=shoe, hand_kind='open', foot=1.05)
    sp3 = j['spine_03']
    B.add(sphere((cx, cy - 0.095, sp3.z + 0.07), (0.05, 0.03, 0.075)), 'spine_03', shirt)
    for s in (-1, 1):       # collar points
        B.add(capsule((cx + s * 0.02, cy - 0.1, sp3.z + 0.13), (cx + s * 0.065, cy - 0.085, sp3.z + 0.075), 0.02, 0.012, seg=10, cap=4), 'spine_03', collar)
    B.add(ring((cx, cy + 0.005, sp3.z + 0.135), 0.062, 0.017, seg=20, tseg=6), 'spine_03', collar)
    B.add(capsule(j['neck'], j['head'] + V((0, 0, 0.02)), 0.045, 0.043), 'neck', m['skin'])
    Hd = Head((cx, cy - 0.02, j['head'].z + 0.13), (0.118, 0.13, 0.172))
    B.add(sphere(Hd.C, Hd.R, seg=28, rings=18), 'head', m['skin'])
    face(B, arm, Hd, m, eye_yaw=19, eye_pitch=10, eye_r=0.029, brow=(hair, 0.009), brow_tilt=4, mouth_w=0.03, mouth_pitch=-40)
    B.add(capsule(Hd.at(0, 6, 0.98), Hd.at(0, -10, 1.2), 0.018, 0.024, seg=12), 'head', m['skin'])
    # hair swept up and over to one side
    B.add(sphere(Hd.C + V((0, 0.03, 0.04)), (0.123, 0.13, 0.165), seg=28, rings=18), 'head', hair)
    B.add(tube([Hd.at(-40, 62, 1.02), Hd.at(-8, 66, 1.12), Hd.at(25, 60, 1.14), Hd.at(55, 45, 1.08)], [0.04, 0.055, 0.05, 0.03], seg=12), 'head', hair)
    return B.finish(arm), Hd


CAST = {'Socrates': socrates, 'Aria': aria, 'Cleon': cleon, 'Julian': julian}
