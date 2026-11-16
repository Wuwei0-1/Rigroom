"""The Ring of Gyges III, opening test: Edward's cast in the botanical lounge, moved by recorded idle motion.

    python shot.py -- RIG.fbx --audio DIR [--cache idle.pkl] [--news IMAGE] [--still FRAME OUT.png] [--save OUT.blend] [--width 960]

Socrates stands behind the booth and speaks; Julian answers. Bodies get the recorded motion (all of it for the
standing figure, the upper body for the seated ones); mouths follow the voices; eyes blink; heads turn to whoever speaks.
"""
import math
import os
import random
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import kit
import lounge
import stage

V = Vector
FPS = 24
argv = sys.argv[sys.argv.index('--') + 1:]


def opt(name, default=None, n=1):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if n == 1 else argv[i + 1:i + 1 + n]
    return default


FBX = argv[0]
AUDIO = opt('--audio')
WIDTH = int(opt('--width', 1280))

# ------------------------------------------------------------------ the lines

LINES = [('t01', 'Socrates'), ('t02', 'Julian')]


def envelope(path):
    w = wave.open(path)
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    hop = sr // FPS
    n = len(y) // hop
    e = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    e = np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)
    return e, len(y) / sr


t = 1.0
CUES = []
for lid, who in LINES:
    env, secs = envelope(os.path.join(AUDIO, lid + '.wav'))
    CUES.append({'id': lid, 'who': who, 't': t, 'secs': secs, 'env': env})
    t += secs + 0.6
END = int(round((t + 0.3) * FPS))


def speaking(time):
    for c in CUES:
        if c['t'] <= time < c['t'] + c['secs']:
            return c
    return None


def env_at(who, f):
    for c in CUES:
        if c['who'] == who:
            i = f - int(round(c['t'] * FPS))
            if 0 <= i < len(c['env']):
                return float(c['env'][i])
    return 0.0


# ------------------------------------------------------------------ build

stage.reset()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 0, END - 1
src, motion = stage.load_rig(FBX, opt('--cache'))
lounge.build(opt('--news'))

PLACES = {'Cleon': ((-1.62, 0.12, 0), 62, 1.0), 'Aria': ((0.16, 0.92, 0), 0, 0.93), 'Julian': ((1.62, 0.12, 0), -62, 1.06), 'Socrates': ((-0.72, 1.58, 0), 8, 1.08)}
CH = {}
for who, (loc, yaw, scale) in PLACES.items():
    arm, body, Hd = stage.cast_one(src, who, loc, math.radians(yaw), scale)
    CH[who] = {'arm': arm, 'body': body, 'Hd': Hd, 'gestures': []}


def posed(arm, bone, p_rest):
    """Where a rest-pose point attached to a bone is now (armature space)."""
    return arm.pose.bones[bone].matrix @ arm.data.bones[bone].matrix_local.inverted() @ V(p_rest)


def sit(arm, lean=0.0, spread=0.1, thigh=-0.04, shin=(0, -0.1, -1.0), up=0.0):
    s = arm.scale.x
    h = kit.rest(arm, 'hip')
    kit.pose_move(arm, 'hip', (h.x, h.y, (lounge.SEAT + 0.118) / s))
    if lean:
        kit.pose_turn(arm, 'hip', (1, 0, 0), -math.radians(lean))
    if up:
        kit.pose_turn(arm, 'spine_02', (1, 0, 0), math.radians(up))
    for sd, sg in (('l', 1), ('r', -1)):
        kit.pose_point(arm, 'upperleg_' + sd, 'lowerleg_' + sd, (sg * spread, -1, thigh))
        kit.pose_point(arm, 'lowerleg_' + sd, 'foot_' + sd, shin[sd] if isinstance(shin, dict) else shin)


def hand_to(arm, side, target, pole):
    return kit.reach(arm, ('upperarm_' + side, 'lowerarm_' + side, 'hand_' + side), target, pole)


def twist(arm, side, deg):
    a = kit.joint(arm, 'hand_' + side) - kit.joint(arm, 'lowerarm_' + side)
    kit.pose_turn(arm, 'lowerarm_' + side, a, math.radians(deg))


def lids(arm, deg):
    for sd in 'lr':
        arm.pose.bones['lid_' + sd].rotation_quaternion = Quaternion(kit.local_axis(arm, 'lid_' + sd, (1, 0, 0)), math.radians(deg))


ARM_BONES = lambda sd: ['shoulder_' + sd, 'upperarm_' + sd, 'lowerarm_' + sd, 'hand_' + sd]


def gesture(ch, side, pose_fn, weight):
    """Record an alternative arm pose (made by pose_fn) to blend in over time by weight(t)."""
    arm = ch['arm']
    before = kit.snapshot(arm)
    pose_fn()
    g = {b: arm.pose.bones[b].rotation_quaternion.copy() for b in ARM_BONES(side)}
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
        arm.pose.bones[b].location = l
    kit.refresh()
    ch['gestures'].append((g, weight))


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def window(t0, t1, ramp=0.5):
    return lambda t: ease((t - t0) / ramp) * ease((t1 - t) / ramp)


def hold_slate(ch, name, hand, where, face_to, tilt=0.0):
    """Put a slate in a hand: where (armature space) is its centre; its screen faces face_to."""
    arm = ch['arm']
    ob = lounge.slate(name)
    c = kit.to_world(arm, where)
    z = (kit.to_world(arm, face_to) - c).normalized()
    x = (arm.matrix_world.to_3x3() @ V((1, 0, 0))).normalized()
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = c
    pb = arm.pose.bones[hand]
    pm = arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    ob.parent, ob.parent_type, ob.parent_bone = arm, 'BONE', hand
    ob.matrix_parent_inverse = pm.inverted()
    ob.matrix_basis = M
    return ob


t1, t2 = CUES[0]['t'], CUES[1]['t']

# ---- Cleon: lounging on the left bench, slate in his right hand
c = CH['Cleon']
a = c['arm']
sit(a, lean=14, spread=0.12, thigh=-0.05, shin={'l': (0.03, -0.3, -1.0), 'r': (-0.03, -0.55, -0.85)}, up=6)
S = kit.joint(a, 'upperarm_r')
hand_to(a, 'r', S + V((0.12, -0.34, -0.14)), S + V((-0.4, 0.1, -0.6)))
twist(a, 'r', -80)
S = kit.joint(a, 'upperarm_l')
hand_to(a, 'l', S + V((0.02, -0.3, -0.36)), S + V((0.5, 0.1, -0.5)))
lids(a, -38)
hr = kit.joint(a, 'hand_r')
c['slate'] = hold_slate(c, 'Slate Cleon', 'hand_r', hr + V((0.11, -0.05, 0.05)), posed(a, 'head', c['Hd'].C))

# ---- Aria: upright on the back bench, slate in both hands above the table
c = CH['Aria']
a = c['arm']
sit(a, lean=2, spread=0.09)
for sd, sg in (('l', 1), ('r', -1)):
    S = kit.joint(a, 'upperarm_' + sd)
    hand_to(a, sd, (kit.joint(a, 'hip').x + sg * 0.15, S.y - 0.33, S.z - 0.2), S + V((sg * 0.5, 0.15, -0.6)))
    twist(a, sd, sg * 60)
lids(a, -48)
mid = (kit.joint(a, 'hand_l') + kit.joint(a, 'hand_r')) / 2
c['slate'] = hold_slate(c, 'Slate Aria', 'hand_r', mid + V((0, -0.08, 0.02)), posed(a, 'head', c['Hd'].C))

# ---- Julian: leaning back on the right bench, hands in his lap; he rubs his temple when he speaks
c = CH['Julian']
a = c['arm']
sit(a, lean=13, spread=0.11, thigh=-0.06, shin=(0, -0.25, -1.0), up=5)
for sd, sg in (('l', 1), ('r', -1)):
    S = kit.joint(a, 'upperarm_' + sd)
    hand_to(a, sd, S + V((-sg * 0.05, -0.2, -0.5)), S + V((sg * 0.5, 0.2, -0.4)))
    twist(a, sd, sg * 50)
lids(a, -30)

# ---- Socrates: standing behind the booth; a raised finger for his question
c = CH['Socrates']
a = c['arm']
lids(a, -22)

# a slate lying on the table in front of Julian
sl = lounge.slate('Slate Julian')
sl.location = (0.55, -0.08, lounge.TABLE)
sl.rotation_euler = (0, 0, math.radians(72))

# ------------------------------------------------------------------ motion

N = motion['n']
ROT = {b: [Quaternion(q) for q in qs] for b, qs in motion['rot'].items()}
for qs in ROT.values():                      # keep neighbouring samples on the same side of the sphere
    for i in range(1, len(qs)):
        if qs[i].dot(qs[i - 1]) < 0:
            qs[i].negate()
A0, A1 = 211, 509                            # a stretch where she stands in one place
MEAN = {}
for b, qs in ROT.items():
    m = Quaternion((0, 0, 0, 0))
    for q in qs[A0:A1]:
        m = Quaternion((m.w + q.w, m.x + q.x, m.y + q.y, m.z + q.z))
    MEAN[b] = m.normalized()


def pingpong(x, lo, hi):
    span = hi - lo
    y = (x - lo) % (2 * span)
    return lo + (y if y <= span else 2 * span - y)


def sample(b, x):
    i = int(math.floor(x))
    i = max(0, min(N - 2, i))
    return ROT[b][i].slerp(ROT[b][i + 1], x - i)


def scaled(q, k):
    if abs(k - 1) < 1e-6:
        return q
    ax, ang = q.to_axis_angle()
    if ang > math.pi:
        ang -= 2 * math.pi
    return Quaternion(ax, ang * k)


BODY = ['spine_01', 'spine_02', 'spine_03', 'neck', 'head'] + ARM_BONES('l') + ARM_BONES('r')
LEGS = ['root', 'hip'] + [p + sd for p in ('upperleg_', 'lowerleg_', 'foot_', 'ball_') for sd in 'lr']
PHASE = {'Cleon': (230, 0.9), 'Aria': (330, 1.0), 'Julian': (430, 0.85), 'Socrates': (260, 1.0)}
AMOUNT = {'spine_01': 1.6, 'spine_02': 1.6, 'spine_03': 1.6, 'neck': 1.3, 'head': 1.3}
for sd in 'lr':          # seated hands hold things: keep only a little of the recorded arm movement
    AMOUNT.update({'shoulder_' + sd: 0.5, 'upperarm_' + sd: 0.3, 'lowerarm_' + sd: 0.25, 'hand_' + sd: 0.2})

for who, c in CH.items():
    c['base'] = kit.snapshot(c['arm'])
    c['head_w'] = kit.to_world(c['arm'], posed(c['arm'], 'head', c['Hd'].C))
    c['axz'] = {b: kit.local_axis(c['arm'], b, (0, 0, 1)) for b in ('spine_03', 'neck', 'head')}
    c['axx'] = {b: kit.local_axis(c['arm'], b, (1, 0, 0)) for b in ('neck', 'head', 'lid_l', 'lid_r')}

# who looks where: (from time, target)
LOOK = {
    'Cleon': [(0, 'slate'), (t1 + 0.5, 'Socrates'), (t1 + 8.0, 'slate'), (t1 + 10.5, 'Socrates'), (t2 + 0.6, 'Julian'), (t2 + 8.5, 'slate'), (t2 + 11.0, 'Julian')],
    'Aria': [(0, 'slate'), (t1 + 0.9, 'Socrates'), (t2 + 0.3, 'Julian'), (t2 + 6.0, 'slate'), (t2 + 8.0, 'Julian')],
    'Julian': [(0, 'table'), (t1 + 1.3, 'Socrates'), (t2 - 0.4, 'Socrates'), (t2 + 9.0, 'table'), (t2 + 11.0, 'Socrates')],
    'Socrates': [(0, 'table'), (t1 + 0.2, 'Julian'), (t1 + 4.2, 'Aria'), (t1 + 7.0, 'table'), (t1 + 9.6, 'Cleon'), (t1 + 12.0, 'Julian'), (t2 + 1.0, 'Julian')],
}


def target_point(who, name):
    if name in CH:
        return CH[name]['head_w']
    if name == 'slate' and 'slate' in CH[who]:
        return CH[who]['slate'].matrix_world.translation
    if name == 'down':
        return CH[who]['head_w'] + CH[who]['arm'].matrix_world.to_3x3() @ V((0.05, -0.5, -0.45))
    return V((0.2, -0.05, lounge.TABLE + 0.05))


def angles(who, name):
    c = CH[who]
    d = c['arm'].matrix_world.to_3x3().inverted() @ (target_point(who, name) - c['head_w'])
    yaw = math.atan2(d.x, -d.y)
    pitch = math.atan2(d.z, math.hypot(d.x, d.y))
    lim = math.radians(58)
    return max(-lim, min(lim, yaw)), max(-0.55, min(0.3, pitch))


def gaze(who, time):
    ks = LOOK[who]
    cur = angles(who, ks[0][1])
    for (t0, name) in ks[1:]:
        if time < t0:
            break
        nxt = angles(who, name)
        k = ease((time - t0) / 0.55)
        cur = (cur[0] + (nxt[0] - cur[0]) * k, cur[1] + (nxt[1] - cur[1]) * k)
    return cur


# ------------------------------------------------------------------ gestures (blended in over time)

def look_now(who, name):
    """Turn the head as the gaze code will, so a gesture can be aimed at where the head will be."""
    c = CH[who]
    yaw, pitch = angles(who, name)
    for b, ky, kp in (('spine_03', 0.22, 0.0), ('neck', 0.3, 0.35), ('head', 0.42, 0.5)):
        pb = c['arm'].pose.bones[b]
        pb.rotation_quaternion = c['base'][b][0] @ Quaternion(c['axz'][b], yaw * ky) @ (Quaternion(c['axx'][b], -pitch * kp) if b in c['axx'] else Quaternion())
    kit.refresh()


def temple():
    arm = CH['Julian']['arm']
    Hd = CH['Julian']['Hd']
    look_now('Julian', 'Socrates')
    S = kit.joint(arm, 'upperarm_l')
    hand_to(arm, 'l', posed(arm, 'head', Hd.at(74, 20, 1.14)), S + V((0.55, -0.25, -0.2)))


gesture(CH['Julian'], 'l', temple, window(t2 - 0.3, t2 + 5.2, 0.7))


def finger():
    arm = CH['Socrates']['arm']
    S = kit.joint(arm, 'upperarm_r')
    hand_to(arm, 'r', S + V((-0.1, -0.26, 0.2)), S + V((-0.35, 0.05, -0.5)))


gesture(CH['Socrates'], 'r', finger, window(t1 + 9.3, t1 + 15.4, 0.6))


rng = random.Random(11)
BLINK = {}
for who in CH:
    ts, x = [], rng.uniform(0.5, 2.5)
    while x < END / FPS:
        ts.append(int(x * FPS))
        x += rng.uniform(2.2, 5.0)
    BLINK[who] = ts
LID_OPEN = {'Cleon': -38, 'Aria': -48, 'Julian': -30, 'Socrates': -22}


def lid_angle(who, f):
    o = LID_OPEN[who]
    for b in BLINK[who]:
        d = f - b
        if 0 <= d <= 5:
            k = (0.6, 1.0, 1.0, 0.6, 0.25, 0.0)[d]
            return o + (72 - o) * k
    return o


# place Socrates so the recorded stance sits where he should stand
c = CH['Socrates']
a = c['arm']
hip_rest = kit.rest(a, 'hip')
x0 = PHASE['Socrates'][0]
for b in LEGS + BODY:
    a.pose.bones[b].rotation_quaternion = sample(b, x0)
for b in ('hip', 'root'):
    a.pose.bones[b].location = V(motion['loc'][b][int(x0)])
kit.refresh()
off = kit.joint(a, 'hip') - hip_rest
a.location = V(a.location) - a.matrix_world.to_3x3() @ V((off.x, off.y, 0))
kit.refresh()
c['head_w'] = kit.to_world(a, posed(a, 'head', c['Hd'].C))

KEYS = {who: {} for who in CH}        # who -> (path, index) -> [value per frame]


def put(who, path, vals):
    for i, v in enumerate(vals):
        KEYS[who].setdefault((path, i), []).append(v)


for f in range(END):
    time = f / FPS
    for who, c in CH.items():
        arm = c['arm']
        ph, speed = PHASE[who]
        x = pingpong(ph + time * 30 * speed, A0, A1)
        standing = who == 'Socrates'
        talk = env_at(who, f)
        talk_s = float(np.mean([env_at(who, g) for g in range(f - 3, f + 4)]))
        yaw, pitch = gaze(who, time)
        for b in BODY + (LEGS if standing else []):
            d = MEAN[b].inverted() @ sample(b, x)
            if standing:
                q = sample(b, x)
            else:
                q = c['base'][b][0] @ scaled(d, AMOUNT.get(b, 0.8))
            for g, wfn in c['gestures']:
                w = wfn(time)
                if w > 0 and b in g:
                    q = q.slerp(g[b] @ scaled(d, 0.5), w)
            if b == 'spine_03':
                q = q @ Quaternion(c['axz'][b], yaw * 0.22)
            elif b == 'neck':
                q = q @ Quaternion(c['axz'][b], yaw * 0.3) @ Quaternion(c['axx'][b], -pitch * 0.35)
            elif b == 'head':
                nod = math.radians(4.0) * (talk_s - 0.25) if talk_s > 0.02 else 0.0
                q = q @ Quaternion(c['axz'][b], yaw * 0.42) @ Quaternion(c['axx'][b], -pitch * 0.5 + nod)
            put(who, 'pose.bones["%s"].rotation_quaternion' % b, tuple(q))
        if standing:
            for b in ('hip', 'root'):
                i = int(math.floor(x))
                l = V(motion['loc'][b][i]).lerp(V(motion['loc'][b][min(N - 1, i + 1)]), x - i)
                put(who, 'pose.bones["%s"].location' % b, tuple(l))
        la = math.radians(lid_angle(who, f))
        for sd in 'lr':
            put(who, 'pose.bones["lid_%s"].rotation_quaternion' % sd, tuple(Quaternion(c['axx']['lid_' + sd], la)))
        put(who, 'pose.bones["mouth"].scale', (1.0 - 0.2 * talk, 0.45 + 1.8 * talk, 1.0))

for who, c in CH.items():
    arm = c['arm']
    act = bpy.data.actions.new(who + ' test')
    arm.animation_data_create()
    arm.animation_data.action = act
    made = False
    if hasattr(act, 'fcurve_ensure_for_datablock'):
        try:
            for (path, idx), vals in KEYS[who].items():
                fc = act.fcurve_ensure_for_datablock(arm, path, index=idx)
                fc.keyframe_points.add(len(vals))
                co = np.empty(len(vals) * 2)
                co[0::2] = np.arange(len(vals))
                co[1::2] = vals
                fc.keyframe_points.foreach_set('co', co)
                fc.keyframe_points.foreach_set('interpolation', [1] * len(vals))      # linear
                fc.update()
            made = True
        except Exception as e:
            print('fast keys failed:', e)
    if not made:
        for (path, idx), vals in KEYS[who].items():
            fc = act.fcurves.new(path, index=idx)
            fc.keyframe_points.add(len(vals))
            co = np.empty(len(vals) * 2)
            co[0::2] = np.arange(len(vals))
            co[1::2] = vals
            fc.keyframe_points.foreach_set('co', co)
            fc.update()

# ------------------------------------------------------------------ light, cameras, cuts

stage.world(sc, kit.hexc('#141a2a'), 0.35)
stage.light('Pendant', 'POINT', (0, 0, 1.95), 110, (1.0, 0.82, 0.6), 0.15)
stage.light('Key', 'AREA', (-2.6, -3.6, 3.3), 420, (1.0, 0.9, 0.78), 3.0, to=(0, 0.4, 1.1))
stage.light('Fill', 'AREA', (3.4, -3.0, 1.6), 110, (0.62, 0.78, 1.0), 3.0, to=(0, 0.4, 1.1), shadow=False)
stage.light('Screens', 'AREA', (0, 2.45, 2.1), 220, (0.45, 0.85, 1.0), 2.6, to=(0, 0, 1.2))
stage.light('Rim left', 'AREA', (-3.6, 2.2, 2.6), 260, (0.5, 0.85, 1.0), 1.5, to=(-0.5, 0.8, 1.3), shadow=False)
stage.light('Rim right', 'AREA', (3.6, 2.2, 2.6), 260, (0.5, 0.85, 1.0), 1.5, to=(0.5, 0.8, 1.3), shadow=False)
for who in ('Cleon', 'Aria'):
    p = CH[who]['slate'].matrix_world.translation
    n = CH[who]['slate'].matrix_world.to_3x3() @ V((0, 0, 1))
    L = stage.light('Glow ' + who, 'POINT', p + n * 0.12, 9, (0.5, 0.82, 1.0), 0.08, shadow=False)
stage.light('Glow Julian', 'POINT', (0.55, -0.08, lounge.TABLE + 0.12), 8, (0.5, 0.82, 1.0), 0.08, shadow=False)

hs = CH['Socrates']['head_w']
hj = CH['Julian']['head_w']
CAMS = {
    'wide': stage.camera('Cam wide', (0, -4.4, 1.12), (0, 0.5, 1.02), 40),
    'soc': stage.camera('Cam Socrates', (hs.x + 0.55, hs.y - 2.3, hs.z - 0.32), (hs.x + 0.05, hs.y, hs.z - 0.16), 50),
    'soc2': stage.camera('Cam Socrates low', (hs.x + 1.1, hs.y - 2.55, 1.02), (hs.x - 0.05, hs.y, hs.z - 0.2), 48),
    'jul': stage.camera('Cam Julian', (0.42, 0.62, hj.z + 0.04), (hj.x, hj.y, hj.z - 0.12), 42),
    'three': stage.camera('Cam listeners', (1.5, -3.0, 1.25), (-0.55, 0.75, 1.1), 45),
}
CUTS = [(0, 'wide'), (t1 + 2.2, 'soc'), (t1 + 6.6, 'three'), (t1 + 9.4, 'soc2'), (t2 - 0.5, 'wide'), (t2 + 1.6, 'jul'), (t2 + 7.2, 'three'), (t2 + 9.6, 'jul')]
for tm, name in CUTS:
    mk = sc.timeline_markers.new(name, frame=int(round(tm * FPS)))
    mk.camera = CAMS[name]
sc.camera = CAMS['wide']
stage.eevee(sc, WIDTH, WIDTH * 9 // 16, int(opt('--samples', 24)), rays='--norays' not in argv)

print('frames', END, 'cues', [(c['id'], c['who'], round(c['t'], 2), round(c['secs'], 2)) for c in CUES])
if opt('--save'):
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=opt('--save'))
still = opt('--still', n=2)
if still:
    for fr, out in zip(still[0].split(','), [still[1].replace('.png', '_%s.png' % k) for k in still[0].split(',')]):
        sc.frame_set(int(fr))
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
if opt('--preview'):          # a fast flat-shaded pass to check the motion
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.display.shading.show_shadows = False
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    step = int(opt('--step', 2))
    for fr in range(0, END, step):
        sc.frame_set(fr)
        sc.render.filepath = os.path.join(opt('--preview'), 'p_%04d.png' % (fr // step))
        bpy.ops.render.render(write_still=True)
if '--debug' in argv:
    for who in CH:
        print(who, 'head', tuple(round(v, 2) for v in CH[who]['head_w']), {n: tuple(round(math.degrees(v)) for v in angles(who, n)) for n in list(CH) + ['table', 'down', 'slate'] if n != who})
    for tm in (20.0, 21.8, 24.2, 26.0, 29.2, 30.8, 31.7):
        print('Julian gaze at', tm, tuple(round(math.degrees(v)) for v in gaze('Julian', tm)))
