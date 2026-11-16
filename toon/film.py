"""The Ring of Gyges III as a 3D cartoon, one sequence at a time.

    python film.py -- --seq N --script script.json --voices DIR --idle IDLE.fbx --walk WALK.fbx --news IMAGE
                      [--cache DIR] [--save OUT.blend] [--plan OUT.json] [--still F,F OUT.png] [--preview DIR] [--width 1280]

The voices folder holds one WAV per script element (eNNN.wav) and index.json. The plan JSON lists the audio
cues for the render job. Bodies move with recorded motion (an idle, and a walk for Socrates's pacing); gestures
come from the script's notes and stage directions; heads turn to whoever speaks; mouths follow the voices.
"""
import json
import math
import os
import random
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import holo
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


SEQ = int(opt('--seq', 1))
ELS = json.load(open(opt('--script')))
VOICES = opt('--voices')
INDEX = json.load(open(os.path.join(VOICES, 'index.json')))
CACHE = opt('--cache', '/tmp')
WIDTH = int(opt('--width', 1280))

# ------------------------------------------------------------------ the sequence's timeline

starts = [i for i, e in enumerate(ELS) if e['kind'] == 'sequence']
lo = starts[SEQ - 1]
hi = starts[SEQ] if SEQ < len(starts) else len(ELS)
PAUSE_AFTER = {'No one answers.': 2.2, 'A beat.': 0.0}
SILENT = {'A beat.': 1.6}           # stage directions played as a pause, not read


def envelope(path):
    w = wave.open(path)
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    hop = sr // FPS
    n = len(y) // hop
    e = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    e = np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)
    return e


ITEMS = []
t = 1.2
for i in range(lo, hi):
    e = ELS[i]
    if e['kind'] not in ('line', 'direction', 'super', 'sequence'):
        continue
    iid = 'e%03d' % i
    if e['kind'] != 'line' and e['text'] in SILENT:
        ITEMS.append({'i': i, 'id': None, 'who': 'Narrator', 'kind': e['kind'], 'text': e['text'], 'note': '', 't': t, 'secs': SILENT[e['text']], 'env': np.zeros(1)})
        t += SILENT[e['text']] + 0.3
        continue
    who = e['who'] if e['kind'] == 'line' else 'Narrator'
    secs = INDEX[iid]['secs']
    ITEMS.append({'i': i, 'id': iid, 'who': who, 'kind': e['kind'], 'text': e['text'], 'note': e.get('note', ''), 't': t, 'secs': secs,
                  'env': envelope(os.path.join(VOICES, iid + '.wav')) if who != 'Narrator' else np.zeros(1)})
    t += secs + (0.55 if who != 'Narrator' else 0.45) + PAUSE_AFTER.get(e['text'], 0.0)
    if e['kind'] == 'sequence':
        t += 0.4
TAIL = 5.0 if SEQ == 4 else 2.0
END = int(round((t + TAIL) * FPS))
END += END % 2
BY = {it['i']: it for it in ITEMS}


def T(i, frac=0.0, plus=0.0):
    """The time of a script element, or a fraction of the way through it."""
    it = BY[i]
    return it['t'] + it['secs'] * frac + plus


def speaking(who, time):
    for it in ITEMS:
        if it['who'] == who and it['t'] <= time < it['t'] + it['secs']:
            return it
    return None


def env_at(who, f):
    for it in ITEMS:
        if it['who'] == who:
            k = f - int(round(it['t'] * FPS))
            if 0 <= k < len(it['env']):
                return float(it['env'][k])
    return 0.0


# ------------------------------------------------------------------ build

stage.reset()
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 0, END - 1
src, IDLE = stage.load_rig(opt('--idle'), os.path.join(CACHE, 'idle.pkl'))
WALK = stage.read_motion(opt('--walk'), os.path.join(CACHE, 'walk.pkl')) if opt('--walk') else None
lounge.build(None)
for n in ('Screen centre', 'Screen left', 'Screen right'):
    bpy.data.objects[n].data.materials.clear()
SCREENS = holo.screens_material(opt('--news'))
for n in ('Screen centre', 'Screen left', 'Screen right'):
    bpy.data.objects[n].data.materials.append(SCREENS)

SOC_SPOT = V((-0.75, 1.6, 0))
PLACES = {'Cleon': ((-1.62, 0.12, 0), 62, 1.0), 'Aria': ((0.16, 0.92, 0), 0, 0.93), 'Julian': ((1.62, 0.12, 0), -62, 1.06), 'Socrates': (tuple(SOC_SPOT), 8, 1.08)}
CH = {}
for who, (loc, yaw, scale) in PLACES.items():
    arm, body, Hd = stage.cast_one(src, who, loc, math.radians(yaw), scale)
    CH[who] = {'arm': arm, 'body': body, 'Hd': Hd, 'moves': [], 'leans': [], 'lids': [], 'smiles': [], 'nods': [], 'yaw0': math.radians(yaw)}

# Socrates is a visitor: his own copies of shared materials, a fade and a shimmer on each, and no shadow
soc = CH['Socrates']
soc['body'].visible_shadow = False
SOC_MATS = []
for slot in soc['body'].material_slots:
    m = slot.material.copy()
    m.name = 'Socrates ' + slot.material.name if not slot.material.name.startswith('Socrates') else slot.material.name + ' fx'
    slot.material = m
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    shader = out.inputs['Surface'].links[0].from_socket
    fade = nt.nodes.new('ShaderNodeValue'); fade.name = fade.label = 'Fade'; fade.outputs[0].default_value = 1.0
    shim = nt.nodes.new('ShaderNodeValue'); shim.name = shim.label = 'Shimmer'; shim.outputs[0].default_value = 0.0
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 26.0; nz.noise_dimensions = '4D'; nz.name = 'Sparkle'
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 6.0
    nt.links.new(nz.outputs['Fac'], pw.inputs[0])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(shim.outputs[0], mul.inputs[1])
    mul2 = nt.nodes.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; mul2.inputs[1].default_value = 60.0
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = kit.hexc('#fff1c8')
    nt.links.new(mul2.outputs[0], em.inputs['Strength'])
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(shader, add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fade.outputs[0], mix.inputs['Fac'])
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(add.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    SOC_MATS.append(m)


def soc_key(frame, fade=None, shimmer=None):
    for m in SOC_MATS:
        for name, v in (('Fade', fade), ('Shimmer', shimmer)):
            if v is not None:
                n = m.node_tree.nodes[name]
                n.outputs[0].default_value = v
                n.outputs[0].keyframe_insert('default_value', frame=frame)


def F(time):
    return int(round(time * FPS))


# ------------------------------------------------------------------ posing helpers (from the test)

def posed(arm, bone, p_rest):
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


def hold_slate(ch, name, hand, where, face_to):
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


ARM_BONES = lambda sd: ['shoulder_' + sd, 'upperarm_' + sd, 'lowerarm_' + sd, 'hand_' + sd]
LID_OPEN = {'Cleon': -38, 'Aria': -48, 'Julian': -30, 'Socrates': -22}

# ---- base poses
c = CH['Cleon']; a = c['arm']
sit(a, lean=14, spread=0.12, thigh=-0.05, shin={'l': (0.03, -0.3, -1.0), 'r': (-0.03, -0.55, -0.85)}, up=6)
S = kit.joint(a, 'upperarm_r'); hand_to(a, 'r', S + V((0.12, -0.34, -0.14)), S + V((-0.4, 0.1, -0.6))); twist(a, 'r', -80)
S = kit.joint(a, 'upperarm_l'); hand_to(a, 'l', S + V((0.02, -0.3, -0.36)), S + V((0.5, 0.1, -0.5)))
c['slate'] = hold_slate(c, 'Slate Cleon', 'hand_r', kit.joint(a, 'hand_r') + V((0.11, -0.05, 0.05)), posed(a, 'head', c['Hd'].C))

c = CH['Aria']; a = c['arm']
sit(a, lean=2, spread=0.09)
for sd, sg in (('l', 1), ('r', -1)):
    S = kit.joint(a, 'upperarm_' + sd)
    hand_to(a, sd, (kit.joint(a, 'hip').x + sg * 0.15, S.y - 0.33, S.z - 0.2), S + V((sg * 0.5, 0.15, -0.6)))
    twist(a, sd, sg * 60)
mid = (kit.joint(a, 'hand_l') + kit.joint(a, 'hand_r')) / 2
c['slate'] = hold_slate(c, 'Slate Aria', 'hand_r', mid + V((0, -0.08, 0.02)), posed(a, 'head', c['Hd'].C))

c = CH['Julian']; a = c['arm']
sit(a, lean=13, spread=0.11, thigh=-0.06, shin=(0, -0.25, -1.0), up=5)
for sd, sg in (('l', 1), ('r', -1)):
    S = kit.joint(a, 'upperarm_' + sd)
    hand_to(a, sd, S + V((-sg * 0.05, -0.2, -0.5)), S + V((sg * 0.5, 0.2, -0.4)))
    twist(a, sd, sg * 50)
JSLATE = lounge.slate('Slate Julian')
JSLATE.location = (0.74, 0.02, lounge.TABLE)
JSLATE.rotation_euler = (0, 0, math.radians(72))

for who, ch in CH.items():
    ch['base'] = kit.snapshot(ch['arm'])
    ch['axz'] = {b: kit.local_axis(ch['arm'], b, (0, 0, 1)) for b in ('spine_01', 'spine_02', 'spine_03', 'neck', 'head')}
    ch['axx'] = {b: kit.local_axis(ch['arm'], b, (1, 0, 0)) for b in ('spine_01', 'spine_02', 'spine_03', 'neck', 'head', 'lid_l', 'lid_r')}

# ------------------------------------------------------------------ recorded motion

def prep(motion):
    rot = {b: [Quaternion(q) for q in qs] for b, qs in motion['rot'].items()}
    for qs in rot.values():
        for i in range(1, len(qs)):
            if qs[i].dot(qs[i - 1]) < 0:
                qs[i].negate()
    return rot


IR = prep(IDLE)
IN = IDLE['n']
A0, A1 = 211, 509
MEAN = {}
for b, qs in IR.items():
    m = Quaternion((0, 0, 0, 0))
    for q in qs[A0:A1]:
        m = Quaternion((m.w + q.w, m.x + q.x, m.y + q.y, m.z + q.z))
    MEAN[b] = m.normalized()


def pingpong(x, lo_, hi_):
    span = hi_ - lo_
    y = (x - lo_) % (2 * span)
    return lo_ + (y if y <= span else 2 * span - y)


def isample(b, x):
    i = max(0, min(IN - 2, int(math.floor(x))))
    return IR[b][i].slerp(IR[b][i + 1], x - i)


def iloc(b, x):
    i = max(0, min(IN - 2, int(math.floor(x))))
    return V(IDLE['loc'][b][i]).lerp(V(IDLE['loc'][b][i + 1]), x - i)


if WALK:
    WR = prep(WALK)
    WN = WALK['n']
    # find the best loop of about one stride pair: two frames whose legs match
    LEGB = [p + sd for p in ('upperleg_', 'lowerleg_', 'foot_') for sd in 'lr'] + ['hip']
    best = None
    for i0 in range(0, WN - 30):
        for j0 in range(i0 + 28, min(WN, i0 + 42)):
            d = sum(1 - abs(WR[b][i0].dot(WR[b][j0])) for b in LEGB if b in WR)
            if best is None or d < best[0]:
                best = (d, i0, j0)
    W0, W1 = best[1], best[2]
    STRIDE = (V(WALK['loc']['root'][W1]) - V(WALK['loc']['root'][W0])).length      # metres per loop
    print('walk loop', W0, W1, 'stride %.3f m' % STRIDE)


def wsample(b, x):
    span = W1 - W0
    y = W0 + (x % span)
    i = int(math.floor(y))
    j = i + 1 if i + 1 <= W1 else W0 + 1
    q = WR[b][i].slerp(WR[b][min(j, WN - 1)], y - i)
    return q


def wloc(b, x):
    span = W1 - W0
    y = W0 + (x % span)
    i = int(math.floor(y))
    p = V(WALK['loc'][b][i]).lerp(V(WALK['loc'][b][min(i + 1, WN - 1)]), y - i)
    return p


def scaled(q, k):
    if abs(k - 1) < 1e-6:
        return q
    ax, ang = q.to_axis_angle()
    if ang > math.pi:
        ang -= 2 * math.pi
    return Quaternion(ax, ang * k)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def window(t0, t1, ramp=0.5):
    return lambda tt: ease((tt - t0) / ramp) * ease((t1 - tt) / ramp)


BODY = ['spine_01', 'spine_02', 'spine_03', 'neck', 'head'] + ARM_BONES('l') + ARM_BONES('r')
LEGS = ['root', 'hip'] + [p + sd for p in ('upperleg_', 'lowerleg_', 'foot_', 'ball_') for sd in 'lr']
PHASE = {'Cleon': (230, 0.9), 'Aria': (330, 1.0), 'Julian': (430, 0.85), 'Socrates': (260, 1.0)}
AMOUNT = {'spine_01': 1.6, 'spine_02': 1.6, 'spine_03': 1.6, 'neck': 1.3, 'head': 1.3}
for sd in 'lr':
    AMOUNT.update({'shoulder_' + sd: 0.5, 'upperarm_' + sd: 0.3, 'lowerarm_' + sd: 0.25, 'hand_' + sd: 0.2})

# Socrates stands where the idle stance puts his hips on his mark
a = soc['arm']
x0 = PHASE['Socrates'][0]
for b in LEGS + BODY:
    a.pose.bones[b].rotation_quaternion = isample(b, x0)
for b in ('hip', 'root'):
    a.pose.bones[b].location = iloc(b, x0)
kit.refresh()
IDLE_OFF = kit.joint(a, 'hip') - kit.rest(a, 'hip')
IDLE_OFF = V((IDLE_OFF.x, IDLE_OFF.y, 0)) * a.scale.x
for pb in a.pose.bones:
    q, l, s_ = soc['base'][pb.name]
    pb.rotation_quaternion, pb.location = q, l
kit.refresh()

# ------------------------------------------------------------------ Socrates's path (pacing in Sequence Two)

# a list of (t0, t1, x0, x1, mode) on the line y = SOC_SPOT.y; mode 'stand' or 'walk'; yaw follows
PATH = [(0, 1e9, SOC_SPOT.x, SOC_SPOT.x, 'stand')]
SPEED = 0.0
if SEQ == 2 and WALK:
    play = 0.62                          # slow pacing
    SPEED = STRIDE / ((W1 - W0) / 30.0) * play * 1.08
    tA, tB = T(33, 0.3), T(44, 0.35)
    legs = []
    xs = [SOC_SPOT.x, 1.25, -1.35, 1.25, -1.35, 1.05, -0.75]
    tt = tA
    PATH = [(0, tA, SOC_SPOT.x, SOC_SPOT.x, 'stand')]
    walk_total = sum(abs(xs[k + 1] - xs[k]) for k in range(len(xs) - 1)) / SPEED
    turns = 1.0 * (len(xs) - 1) * 2
    pause = max(1.5, (tB - tA - walk_total - turns) / (len(xs) - 2))
    for k in range(len(xs) - 1):
        d = abs(xs[k + 1] - xs[k]) / SPEED
        PATH.append((tt, tt + 1.0, xs[k], xs[k], 'turn'))
        tt += 1.0
        PATH.append((tt, tt + d, xs[k], xs[k + 1], 'walk'))
        tt += d
        PATH.append((tt, tt + 1.0, xs[k + 1], xs[k + 1], 'turnback'))
        tt += 1.0
        if k < len(xs) - 2:
            PATH.append((tt, tt + pause, xs[k + 1], xs[k + 1], 'stand'))
            tt += pause
    PATH.append((tt, 1e9, xs[-1], xs[-1], 'stand'))
    print('pacing: speed %.2f m/s, pauses %.1f s, ends %.1f s (stop cue %.1f s)' % (SPEED, pause, tt, T(44)))


def walk_yaw(seg):
    return math.radians(90 if seg[3] > seg[2] else -90)


def soc_state(time):
    """Where Socrates is (x), which way he faces (yaw added to his base yaw), how much he is walking (0-1), and how far."""
    for idx, (t0, t1, xa, xb, mode) in enumerate(PATH):
        if t0 <= time < t1:
            k = (time - t0) / max(1e-6, t1 - t0)
            if mode == 'stand':
                return xa, 0.0, 0.0, 0.0
            if mode == 'walk':
                ramp = ease((time - t0) / 0.45) * ease((t1 - time) / 0.45)
                return xa + (xb - xa) * k, walk_yaw(PATH[idx]), ramp, (time - t0) * SPEED
            if mode == 'turn':
                return xa, walk_yaw(PATH[idx + 1]) * ease(k), 0.0, 0.0
            return xa, walk_yaw(PATH[idx - 1]) * (1 - ease(k)), 0.0, 0.0
    return PATH[-1][2], 0.0, 0.0, 0.0


# ------------------------------------------------------------------ moves (arm poses blended over time)

def capture(ch, side, fn):
    arm = ch['arm']
    before = kit.snapshot(arm)
    fn()
    g = {b: arm.pose.bones[b].rotation_quaternion.copy() for b in ARM_BONES(side)}
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
        arm.pose.bones[b].location = l
    kit.refresh()
    return g


def move(who, keys):
    """keys: [(time, pose or None)], each pose {bone: quaternion} from capture(); blended between keys."""
    CH[who]['moves'].append(sorted(keys, key=lambda k: k[0]))


def move_at(keys, time):
    """The pose a move asks for at a time: (weight, {bone: q})."""
    if time <= keys[0][0] or time >= keys[-1][0]:
        return 0.0, None
    for (ta, pa), (tb, pb) in zip(keys, keys[1:]):
        if ta <= time <= tb:
            k = ease((time - ta) / max(1e-6, tb - ta))
            if pa and pb:
                return 1.0, {b: pa[b].slerp(pb[b], k) for b in pa}
            if pa:
                return 1.0 - k, pa
            if pb:
                return k, pb
            return 0.0, None
    return 0.0, None


rng = random.Random(23)
FREE = {'Socrates': ['r', 'l'], 'Julian': ['l', 'r'], 'Cleon': ['l'], 'Aria': ['l']}


def look_now(who, yaw, pitch):
    c = CH[who]
    for b, ky, kp in (('spine_03', 0.22, 0.0), ('neck', 0.3, 0.35), ('head', 0.42, 0.5)):
        pb = c['arm'].pose.bones[b]
        pb.rotation_quaternion = c['base'][b][0] @ Quaternion(c['axz'][b], yaw * ky) @ Quaternion(c['axx'][b], -pitch * kp)
    kit.refresh()


def explain_pose(who, side, var):
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    standing = who == 'Socrates'
    fwd = -0.4 if standing else -0.36
    down = -0.2 if standing else -0.13
    def fn():
        hand_to(arm, side, S + V((sg * (0.07 + 0.05 * var), fwd + 0.05 * var, down + 0.06 * var)), S + V((sg * 0.55, 0.15, -0.45)))
        twist(arm, side, sg * (-35 - 25 * var))
    return capture(c, side, fn)


def explain(who, t0, t1):
    """Talking gestures through a long line: the free hand rises, makes a point or two, and settles."""
    sides = FREE[who]
    tt, k = t0 + 1.2, 0
    while tt + 2.8 < t1:
        side = sides[k % len(sides)]
        A, B = explain_pose(who, side, 0.0), explain_pose(who, side, 1.0)
        dur = rng.uniform(2.6, 3.6)
        move(who, [(tt, None), (tt + 0.55, A), (tt + dur * 0.5, B), (tt + dur - 0.5, A), (tt + dur, None)])
        tt += dur + rng.uniform(2.8, 4.8)
        k += 1


def toward_world(who, side, world, reach=0.95):
    """A hand target toward a world point, as far as the arm goes."""
    arm = CH[who]['arm']
    S = kit.joint(arm, 'upperarm_' + side)
    d = kit.to_arm(arm, world) - S
    return S + d.normalized() * min(d.length, 0.62 * reach)


def point_at(who, side, world, t0, t1, sweep=None):
    """Reach toward a point (the hologram); with sweep, trace across it to a second point."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    A = capture(c, side, lambda: (hand_to(arm, side, toward_world(who, side, world), S + V((sg * 0.6, 0.2, -0.3))), twist(arm, side, sg * -60)))
    if sweep is None:
        move(who, [(t0, None), (t0 + 0.6, A), (t1 - 0.6, A), (t1, None)])
    else:
        B = capture(c, side, lambda: (hand_to(arm, side, toward_world(who, side, sweep), S + V((sg * 0.6, 0.2, -0.3))), twist(arm, side, sg * -60)))
        move(who, [(t0, None), (t0 + 0.6, A), (t0 + (t1 - t0) * 0.55, B), (t1 - 0.5, B), (t1, None)])


def temple(t0, t1):
    c = CH['Julian']; arm = c['arm']; Hd = c['Hd']
    def fn():
        look_now('Julian', math.radians(-30), 0.05)
        S = kit.joint(arm, 'upperarm_l')
        hand_to(arm, 'l', posed(arm, 'head', Hd.at(74, 20, 1.14)), S + V((0.55, -0.25, -0.2)))
    P = capture(c, 'l', fn)
    for pb in arm.pose.bones:
        q, l, s_ = c['base'][pb.name]
        pb.rotation_quaternion = q
    kit.refresh()
    move('Julian', [(t0, None), (t0 + 0.7, P), (t1 - 0.7, P), (t1, None)])


def swipe(t0):
    """Aria sweeps her free hand across her slate."""
    c = CH['Aria']; arm = c['arm']
    sl = kit.to_arm(arm, c['slate'].matrix_world.translation)
    S = kit.joint(arm, 'upperarm_l')
    A = capture(c, 'l', lambda: (hand_to(arm, 'l', sl + V((0.13, -0.02, 0.07)), S + V((0.5, 0.1, -0.5))), twist(arm, 'l', -70)))
    B = capture(c, 'l', lambda: (hand_to(arm, 'l', sl + V((-0.12, -0.03, 0.06)), S + V((0.5, 0.1, -0.5))), twist(arm, 'l', -70)))
    move('Aria', [(t0, None), (t0 + 0.5, A), (t0 + 1.1, B), (t0 + 1.6, B), (t0 + 2.2, None)])


def stroke_beard(t0, t1):
    c = CH['Socrates']; arm = c['arm']; Hd = c['Hd']
    S = kit.joint(arm, 'upperarm_r')
    A = capture(c, 'r', lambda: hand_to(arm, 'r', posed(arm, 'head', Hd.at(8, -60, 1.42)), S + V((-0.5, -0.1, -0.6))))
    B = capture(c, 'r', lambda: hand_to(arm, 'r', posed(arm, 'head', Hd.at(4, -82, 1.36)), S + V((-0.5, -0.1, -0.6))))
    keys = [(t0, None), (t0 + 0.7, A)]
    tt = t0 + 0.7
    while tt + 1.6 < t1 - 0.7:
        keys += [(tt + 0.8, B), (tt + 1.6, A)]
        tt += 1.6
    keys += [(t1, None)]
    move('Socrates', keys)


def cross_arms(t0, t1):
    c = CH['Cleon']; arm = c['arm']
    sp = kit.joint(arm, 'spine_03')
    P = {}
    def fn():
        for sd, sg in (('l', 1), ('r', -1)):
            S = kit.joint(arm, 'upperarm_' + sd)
            other = kit.joint(arm, 'lowerarm_' + ('r' if sd == 'l' else 'l'))
            tgt = V((sp.x - sg * 0.13, sp.y - 0.17 - (0.03 if sd == 'l' else 0), sp.z - 0.1 + (0.02 if sd == 'l' else 0)))
            hand_to(arm, sd, tgt, S + V((sg * 0.6, 0.1, -0.5)))
    before = kit.snapshot(arm)
    fn()
    for sd in 'lr':
        P[sd] = {b: arm.pose.bones[b].rotation_quaternion.copy() for b in ARM_BONES(sd)}
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
    kit.refresh()
    for sd in 'lr':
        move('Cleon', [(t0, None), (t0 + 0.8, P[sd]), (t1 - 0.8, P[sd]), (t1, None)])
    sl = c['slate']           # the slate goes down on the bench while his arms are crossed
    for f, v in ((F(t0 + 0.3), 1), (F(t0 + 0.5), 0), (F(t1 - 0.5), 0), (F(t1 - 0.3), 1)):
        sl.scale = (v, v, v)
        sl.keyframe_insert('scale', frame=f)


def fold_hands(t0, t1):
    c = CH['Socrates']; arm = c['arm']
    s1 = kit.joint(arm, 'spine_01')
    before = kit.snapshot(arm)
    P = {}
    for sd, sg in (('l', 1), ('r', -1)):
        S = kit.joint(arm, 'upperarm_' + sd)
        hand_to(arm, sd, V((s1.x + sg * 0.035, s1.y - 0.24, s1.z + 0.08)), S + V((sg * 0.6, 0.1, -0.5)))
        P[sd] = {b: arm.pose.bones[b].rotation_quaternion.copy() for b in ARM_BONES(sd)}
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
    kit.refresh()
    for sd in 'lr':
        move('Socrates', [(t0, None), (t0 + 0.9, P[sd]), (t1 - 0.8, P[sd]), (t1, None)])


def raise_hand(t0, t1):
    c = CH['Socrates']; arm = c['arm']
    S = kit.joint(arm, 'upperarm_r')
    P = capture(c, 'r', lambda: (hand_to(arm, 'r', S + V((-0.3, -0.3, 0.12)), S + V((-0.6, 0.2, -0.4))), twist(arm, 'r', 70)))
    move('Socrates', [(t0, None), (t0 + 0.9, P), (t1 - 0.8, P), (t1, None)])


def reach_slate(t0):
    """Julian reaches out and taps his slate on the table."""
    c = CH['Julian']; arm = c['arm']
    S = kit.joint(arm, 'upperarm_r')
    tgt = kit.to_arm(arm, V(JSLATE.location) + V((0, 0, 0.03)))
    A = capture(c, 'r', lambda: hand_to(arm, 'r', tgt + V((0, 0, 0.05)), S + V((-0.6, 0.1, -0.4))))
    B = capture(c, 'r', lambda: hand_to(arm, 'r', tgt, S + V((-0.6, 0.1, -0.4))))
    move('Julian', [(t0, None), (t0 + 0.8, A), (t0 + 1.2, B), (t0 + 1.5, A), (t0 + 2.3, None)])
    c['leans'].append((t0, t0 + 2.3, 12))


# ------------------------------------------------------------------ direction: who does what when

NAMES = ('Socrates', 'Julian', 'Aria', 'Cleon')
for it in ITEMS:
    if it['who'] == 'Narrator':
        continue
    t0, t1 = it['t'], it['t'] + it['secs']
    note = it['note'].lower()
    who = it['who']
    if it['secs'] > 5.5 and not ('temple' in note or 'beard' in note or 'arms' in note or 'folding' in note):
        explain(who, t0, t1)
    if 'nodding' in note:
        CH[who]['nods'].append((t0, t0 + 4.0))
    if 'widening' in note:
        CH[who]['lids'].append((t0 - 0.3, t1, -14))
    if 'leaning back' in note:
        CH[who]['leans'].append((t0 - 0.4, t0 + 6.0, -6))
    if 'leaning closer' in note:
        CH[who]['leans'].append((t0 - 0.3, t1 + 0.5, 16))

HOLO_AT = holo.CENTRE
for it in ITEMS:
    i, t0, t1 = it['i'], it['t'], it['t'] + it['secs']
    if i == 9:
        temple(t0 - 0.3, t0 + 5.2)
    elif i == 10:
        swipe(t0 + 0.1)
    elif i == 14:
        stroke_beard(t0 - 0.2, t0 + 6.5)
    elif i == 30:
        point_at('Aria', 'l', HOLO_AT, t0 + 0.6, t0 + 5.0)
    elif i == 32:
        point_at('Julian', 'l', HOLO_AT + V((0.3, 0.05, 0.05)), t0 + 0.5, t0 + 5.5, sweep=HOLO_AT + V((-0.3, 0.0, -0.05)))
    elif i == 49:
        reach_slate(T(49, 0.35))
    elif i == 50:
        point_at('Julian', 'l', HOLO_AT, t0 + 0.8, t0 + 5.5)
    elif i == 55:
        cross_arms(t0 - 0.4, t1 + 0.6)
    elif i == 75:
        swipe(t0 + 0.2)
    elif i == 81:
        fold_hands(t0 - 0.3, t1 + 1.0)
        CH['Socrates']['nods'].append((t0, t0 + 3.5))
    elif i == 84:
        CH['Socrates']['smiles'].append((t0 + 1.0, T(85, 1.0) + 0.5))
    elif i == 89:
        raise_hand(t0 + 0.8, T(90, 1.0) + 0.4)
    elif i == 68:
        CH['Socrates']['nods'].append((t0 + 0.5, t0 + 4.0))
    elif i == 23:
        pass
    elif i == 61:
        pass

# ------------------------------------------------------------------ gaze

def head_w(who):
    c = CH[who]
    return kit.to_world(c['arm'], posed(c['arm'], 'head', c['Hd'].C))


for who in CH:
    CH[who]['head_w'] = head_w(who)


def soc_head_at(time):
    x = soc_state(time)[0]
    return V((x, SOC_SPOT.y, CH['Socrates']['head_w'].z))


def target_point(who, name, time):
    if name == 'Socrates':
        return soc_head_at(time)
    if name in CH:
        return CH[name]['head_w']
    if name == 'slate' and 'slate' in CH[who]:
        return CH[who]['slate'].matrix_world.translation
    if name == 'holo':
        return holo.CENTRE
    if name == 'down':
        return CH[who]['head_w'] + V((0, -0.6, -0.6))
    return V((0.2, -0.05, lounge.TABLE + 0.05))


def angles(who, name, time, yaw_extra=0.0, at=None):
    c = CH[who]
    hw = soc_head_at(time) if who == 'Socrates' else c['head_w']
    yaw0 = c['yaw0'] + yaw_extra
    d = Matrix.Rotation(-yaw0, 3, 'Z') @ (target_point(who, name, time) - hw)
    yaw = math.atan2(d.x, -d.y)
    pitch = math.atan2(d.z, math.hypot(d.x, d.y))
    lim = math.radians(58)
    return max(-lim, min(lim, yaw)), max(-0.55, min(0.35, pitch))


def holo_up(time):
    return SEQ > 1 or (11 in BY and time > T(11) + 1.0)


def addressee(it, prev):
    for n in NAMES:
        if n != it['who'] and n in it['text'][:60]:
            return n
    if it['who'] != 'Socrates':
        return 'Socrates'
    return prev if prev and prev != 'Socrates' else 'Julian'


LOOKS = {who: [(0.0, 'holo' if who != 'Socrates' else 'table')] for who in CH}
prev = None
for it in ITEMS:
    t0, t1, who = it['t'], it['t'] + it['secs'], it['who']
    if who == 'Narrator':
        for w in CH:
            LOOKS[w].append((t0 + 0.4 + 0.3 * NAMES.index(w), 'holo' if holo_up(t0 + 1) else ('slate' if 'slate' in CH[w] else 'table')))
        continue
    to = addressee(it, prev)
    LOOKS[who].append((t0 - 0.2, to))
    note = it['note'].lower()
    if 'slate' in note or 'metrics' in note:
        LOOKS[who].append((t0 - 0.2, 'slate'))
        LOOKS[who].append((t0 + min(4.5, it['secs'] * 0.6), to))
    if 'projection' in note or 'nodes' in note or 'data' in note or 'scan' in note or 'anatomical' in note:
        LOOKS[who].append((t0 - 0.2, 'holo'))
        LOOKS[who].append((t0 + min(5.0, it['secs'] * 0.6), to))
    if it['secs'] > 9:          # the speaker takes in the others now and then
        others = [n for n in NAMES if n not in (who, to)]
        k = 0
        for tt in np.arange(t0 + 6.0, t1 - 3.0, 7.0):
            LOOKS[who].append((tt, others[k % len(others)]))
            LOOKS[who].append((tt + 2.2, to))
            k += 1
    for w in CH:
        if w == who:
            continue
        d = 0.25 + 0.2 * rng.random()
        LOOKS[w].append((t0 + d, who))
        if it['secs'] > 8 and rng.random() < 0.6:
            g = t0 + rng.uniform(3.5, it['secs'] - 3.0)
            LOOKS[w].append((g, 'holo' if holo_up(g) else ('slate' if 'slate' in CH[w] else 'table')))
            LOOKS[w].append((g + rng.uniform(1.5, 2.5), who))
    prev = who
for w in LOOKS:
    LOOKS[w].sort(key=lambda k: k[0])
if 25 in BY:          # No one answers: they look away
    for w in ('Cleon', 'Aria', 'Julian'):
        LOOKS[w].append((T(25, 0.2), 'down' if w != 'Aria' else 'slate'))
        LOOKS[w].sort(key=lambda k: k[0])


def gaze(who, time, yaw_extra=0.0):
    ks = LOOKS[who]
    cur = angles(who, ks[0][1], time, yaw_extra)
    for (t0, name) in ks[1:]:
        if time < t0:
            break
        nxt = angles(who, name, time, yaw_extra)
        k = ease((time - t0) / 0.55)
        cur = (cur[0] + (nxt[0] - cur[0]) * k, cur[1] + (nxt[1] - cur[1]) * k)
    return cur


BLINK = {}
for who in CH:
    ts, x = [], rng.uniform(0.5, 2.5)
    while x < END / FPS:
        ts.append(int(x * FPS))
        x += rng.uniform(2.2, 5.0)
    BLINK[who] = ts


def lid_angle(who, f):
    o = LID_OPEN[who]
    time = f / FPS
    for (t0, t1, extra) in CH[who]['lids']:
        o += extra * window(t0, t1, 0.4)(time)
    for (t0, t1) in CH[who]['smiles']:
        o += 14 * window(t0, t1, 0.6)(time)
    for b in BLINK[who]:
        d = f - b
        if 0 <= d <= 5:
            k = (0.6, 1.0, 1.0, 0.6, 0.25, 0.0)[d]
            return o + (72 - o) * k
    return o


# ------------------------------------------------------------------ holograms, screens, lights through the sequence

web, web_m = holo.web()
net, net_m = holo.network()
brain, pfc, brain_m = holo.brain()
crys, crys_core, crys_m = holo.crystal()
HOLOS = {'web': web, 'net': net, 'brain': brain, 'crys': crys}


def show(ob, t0, dur=1.6, size=1.0):
    for f, s in ((F(t0), 0.0), (F(t0 + dur * 0.7), size * 1.06), (F(t0 + dur), size)):
        ob.scale = (s, s, s)
        ob.keyframe_insert('scale', frame=f)


def hide(ob, t0, dur=0.9):
    for f, s in ((F(t0), ob.scale.x if ob.scale.x > 0 else 1.0), (F(t0 + dur), 0.0)):
        ob.scale = (s, s, s)
        ob.keyframe_insert('scale', frame=f)


def present(ob, size=1.0):
    ob.scale = (size, size, size)
    ob.keyframe_insert('scale', frame=0)


def spin(ob, rate):
    for f in (0, END):
        ob.rotation_euler = (0, 0, rate * f / FPS)
        ob.keyframe_insert('rotation_euler', frame=f, index=2)


for ob, r in ((web, 0.05), (net, 0.08), (brain, 0.1), (crys, 0.12)):
    spin(ob, r)
crys_core.rotation_euler = (0.3, 0.2, 0)
for f in (0, END):
    crys_core.rotation_euler[2] = -0.25 * f / FPS
    crys_core.keyframe_insert('rotation_euler', frame=f, index=2)
for m in list(web_m) + list(net_m) + list(brain_m) + list(crys_m):
    holo.pulse_clock(m, END)
for m in SOC_MATS:
    nz = m.node_tree.nodes['Sparkle']
    for f, w in ((0, 0.0), (END, END / FPS * 1.2)):
        nz.inputs['W'].default_value = w
        nz.inputs['W'].keyframe_insert('default_value', frame=f)
holo.pulse_clock(SCREENS, END)
tr = SCREENS.node_tree.nodes['Traffic']
for f, w in ((0, 0.0), (END, END / FPS * 0.12)):
    tr.inputs['W'].default_value = w
    tr.inputs['W'].keyframe_insert('default_value', frame=f)

GLOW = stage.light('Holo glow', 'POINT', holo.CENTRE, 0.0, (0.5, 0.85, 1.0), 0.25, shadow=False)


def glow_key(t0, energy, colour=None):
    GLOW.data.energy = energy
    GLOW.data.keyframe_insert('energy', frame=F(t0))
    if colour:
        GLOW.data.color = colour
        GLOW.data.keyframe_insert('color', frame=F(t0))


soc_key(0, fade=1.0, shimmer=0.0)
if SEQ == 1:
    holo.key_value(SCREENS, 'Net', 0, 0.0)
    glow_key(0, 0.0, (0.5, 0.85, 1.0))
    # Socrates materializes out of a shimmer
    ta = T(7, 0.45)
    soc_key(0, fade=0.0, shimmer=0.0)
    soc_key(F(ta - 0.1), fade=0.0, shimmer=0.0)
    soc_key(F(ta + 0.6), shimmer=2.5)
    soc_key(F(ta + 2.6), fade=1.0)
    soc_key(F(ta + 3.6), shimmer=0.0)
    show(web, T(11, 0.1), 1.8)
    glow_key(T(11, 0.1), 0.0)
    glow_key(T(11, 0.1) + 1.6, 40.0, (0.5, 0.85, 1.0))
elif SEQ == 2:
    present(web)
    holo.key_value(SCREENS, 'Net', 0, 0.0)
    ts = T(29, 0.25)
    holo.key_value(SCREENS, 'Net', F(ts), 0.0)
    holo.key_value(SCREENS, 'Net', F(ts + 2.5), 1.0)
    hide(web, ts + 0.6, 1.0)
    show(net, ts + 1.6, 1.8)
    glow_key(0, 40.0, (0.5, 0.85, 1.0))
    glow_key(ts + 1.6, 40.0, (0.45, 1.0, 0.9))
elif SEQ == 3:
    present(net)
    holo.key_value(SCREENS, 'Net', 0, 1.0)
    holo.key_value(SCREENS, 'Power', 0, 0.9)
    tap = T(49, 0.35) + 1.2
    hide(net, tap + 0.2, 0.8)
    show(brain, tap + 1.2, 2.0)
    for m, v in ((brain_m[2], 1.6),):
        holo.power(m, 0, v)
    glow_key(0, 40.0, (0.45, 1.0, 0.9))
    glow_key(tap + 1.2, 10.0, (0.6, 0.75, 1.0))
    glow_key(tap + 3.0, 35.0, (0.6, 0.75, 1.0))
    # the prefrontal cortex glows bright, then dims and shrivels
    t1 = T(53, 0.2)
    holo.power(brain_m[2], F(t1), 1.6)
    holo.power(brain_m[2], F(t1 + 1.5), 6.0)
    t2 = T(59, 0.2)
    holo.power(brain_m[2], F(t2), 6.0)
    holo.power(brain_m[2], F(t2 + 4.0), 0.35)
    for f, s in ((F(t2), 1.0), (F(t2 + 4.0), 0.62)):
        pfc.scale = (s, s, s)
        pfc.keyframe_insert('scale', frame=f)
    glow_key(t1, 35.0, (0.6, 0.75, 1.0))
    glow_key(t1 + 1.5, 45.0, (1.0, 0.75, 0.45))
    glow_key(t2, 45.0, (1.0, 0.75, 0.45))
    glow_key(t2 + 4.0, 22.0, (0.6, 0.75, 1.0))
elif SEQ == 4:
    present(brain)
    holo.power(brain_m[2], 0, 0.35)
    pfc.scale = (0.62,) * 3
    holo.key_value(SCREENS, 'Net', 0, 1.0)
    holo.key_value(SCREENS, 'Power', 0, 0.9)
    glow_key(0, 22.0, (0.6, 0.75, 1.0))
    sw = T(75, 0.1) + 1.0
    hide(brain, sw, 0.8)
    show(crys, T(76, 0.15), 2.2)
    glow_key(T(76, 0.15), 8.0, (0.8, 0.95, 1.0))
    glow_key(T(76, 0.15) + 2.2, 45.0, (0.8, 0.95, 1.0))
    # the ring gleams
    gold = bpy.data.materials['Socrates Gold'] if 'Socrates Gold' in bpy.data.materials else None
    if gold:
        b = next(n for n in gold.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Emission Color'].default_value = kit.hexc('#ffd27a')
        for f, v in ((F(T(89, 0.6)), 0.0), (F(T(89, 0.6) + 0.8), 6.0), (F(T(90, 0.3)), 6.0), (F(T(90, 0.3) + 1.5), 0.5)):
            b.inputs['Emission Strength'].default_value = v
            b.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
    # he begins to shimmer, then the wind: every projection out for a second, and he is gone
    soc_key(F(T(92, 0.3)), shimmer=0.0)
    soc_key(F(T(92, 0.3) + 3.0), shimmer=0.35)
    soc_key(F(T(95, 1.0)), shimmer=0.5, fade=1.0)
    tw = T(96, 0.25)
    soc_key(F(tw), shimmer=1.8)
    soc_key(F(tw + 0.7), fade=0.0)
    for name, v0 in (('Power', 0.9),):
        holo.key_value(SCREENS, name, F(tw - 0.2), v0)
        holo.key_value(SCREENS, name, F(tw), 0.0)
        holo.key_value(SCREENS, name, F(tw + 1.2), 0.0)
        holo.key_value(SCREENS, name, F(tw + 2.2), 1.6)
    holo.key_value(SCREENS, 'Dawn', F(tw + 1.2), 0.0)
    holo.key_value(SCREENS, 'Dawn', F(tw + 1.25), 1.0)
    for m in crys_m:
        holo.power(m, F(tw - 0.2), m.node_tree.nodes['Power'].outputs[0].default_value)
        holo.power(m, F(tw), 0.0)
        holo.power(m, F(tw + 1.2), 0.0)
        holo.power(m, F(tw + 2.6), 1.6)
    glow_key(tw - 0.2, 45.0)
    glow_key(tw, 0.0)
    glow_key(tw + 1.2, 0.0)
    glow_key(tw + 2.6, 20.0, (0.8, 0.95, 1.0))
    DAWN_T = tw + 1.2

# ------------------------------------------------------------------ keys

KEYS = {who: {} for who in CH}
OBJ = {'loc': [], 'yaw': []}


def put(who, path, vals):
    for i, v in enumerate(vals):
        KEYS[who].setdefault((path, i), []).append(v)


STEP = 2
FRAMES = list(range(0, END, STEP))
for f in FRAMES:
    time = f / FPS
    for who, c in CH.items():
        arm = c['arm']
        ph, speed = PHASE[who]
        x = pingpong(ph + time * 30 * speed, A0, A1)
        standing = who == 'Socrates'
        talk = env_at(who, f)
        talk_s = float(np.mean([env_at(who, g) for g in range(f - 3, f + 4)]))
        if standing:
            sx, syaw, wmix, dist = soc_state(time)
        else:
            sx, syaw, wmix, dist = 0, 0, 0, 0
        yaw, pitch = gaze(who, time, syaw)
        lean = sum(d * window(t0, t1, 0.6)(time) for (t0, t1, d) in c['leans'])
        nod = sum(math.radians(5.5) * math.sin(2 * math.pi * 0.9 * (time - t0)) * window(t0, t1, 0.4)(time) for (t0, t1) in c['nods'])
        wx = (dist / (STRIDE * 1.08) * (W1 - W0)) if (WALK and wmix > 0) else 0.0
        for b in BODY + (LEGS if standing else []):
            d = MEAN[b].inverted() @ isample(b, x)
            if standing:
                q = isample(b, x)
                if wmix > 0 and WALK and b in WR:
                    q = q.slerp(wsample(b, wx), wmix)
            else:
                q = c['base'][b][0] @ scaled(d, AMOUNT.get(b, 0.8))
            for keys in c['moves']:
                w, pose = move_at(keys, time)
                if w > 0 and pose and b in pose:
                    q = q.slerp(pose[b] @ scaled(d, 0.5), w)
            if b == 'spine_01' and lean:
                q = q @ Quaternion(c['axx'][b], math.radians(lean) * 0.4)
            elif b == 'spine_02' and lean:
                q = q @ Quaternion(c['axx'][b], math.radians(lean) * 0.6)
            if b == 'spine_03':
                q = q @ Quaternion(c['axz'][b], yaw * 0.22)
            elif b == 'neck':
                q = q @ Quaternion(c['axz'][b], yaw * 0.3) @ Quaternion(c['axx'][b], -pitch * 0.35)
            elif b == 'head':
                bob = math.radians(4.0) * (talk_s - 0.25) if talk_s > 0.02 else 0.0
                q = q @ Quaternion(c['axz'][b], yaw * 0.42) @ Quaternion(c['axx'][b], -pitch * 0.5 + bob + nod)
            put(who, 'pose.bones["%s"].rotation_quaternion' % b, tuple(q))
        if standing:
            for b in ('hip', 'root'):
                l = iloc(b, x)
                if wmix > 0 and WALK:
                    wl = V((0, 0, 0)) if b == 'root' else wloc(b, wx)
                    l = l.lerp(wl, wmix)
                put(who, 'pose.bones["%s"].location' % b, tuple(l))
            yaw_t = c['yaw0'] + syaw
            off = Matrix.Rotation(yaw_t, 3, 'Z') @ IDLE_OFF * (1 - wmix)
            OBJ['loc'].append(tuple(V((sx, SOC_SPOT.y, 0)) - off))
            OBJ['yaw'].append(yaw_t)
        la = math.radians(lid_angle(who, f))
        for sd in 'lr':
            put(who, 'pose.bones["lid_%s"].rotation_quaternion' % sd, tuple(Quaternion(c['axx']['lid_' + sd], la)))
        sm = sum(window(t0, t1, 0.6)(time) for (t0, t1) in c['smiles'])
        put(who, 'pose.bones["mouth"].scale', (1.0 - 0.2 * talk + 0.35 * sm, 0.45 + 1.8 * talk - 0.2 * sm, 1.0))


def simplify(x, y, tol):
    """Keep the fewest samples whose straight-line joins stay within tol of every sample (Ramer-Douglas-Peucker)."""
    n = len(y)
    keep = np.zeros(n, bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        seg = y[a] + (y[b] - y[a]) * (x[a + 1:b] - x[a]) / (x[b] - x[a])
        err = np.abs(y[a + 1:b] - seg)
        k = int(np.argmax(err))
        if err[k] > tol:
            m = a + 1 + k
            keep[m] = True
            stack += [(a, m), (m, b)]
    return keep


def tol_for(path):
    if 'rotation_quaternion' in path:
        return 0.0012
    if 'mouth' in path:
        return 0.03
    if path == 'rotation_euler':
        return 0.002
    return 0.0015


TOTAL = [0, 0]


def write_keys(idb, keys, frames, linear=True):
    act = bpy.data.actions.new(idb.name + ' seq%d' % SEQ)
    idb.animation_data_create()
    idb.animation_data.action = act
    for (path, idx), vals in keys.items():
        y = np.array(vals, float)
        keep = simplify(frames, y, tol_for(path))
        TOTAL[0] += len(y); TOTAL[1] += int(keep.sum())
        vals = y[keep]
        fr = frames[keep]
        fc = act.fcurve_ensure_for_datablock(idb, path, index=idx) if hasattr(act, 'fcurve_ensure_for_datablock') else act.fcurves.new(path, index=idx)
        fc.keyframe_points.add(len(vals))
        co = np.empty(len(vals) * 2)
        co[0::2] = fr
        co[1::2] = vals
        fc.keyframe_points.foreach_set('co', co)
        if linear:
            fc.keyframe_points.foreach_set('interpolation', [1] * len(vals))
        fc.update()


for who, c in CH.items():
    keys = dict(KEYS[who])
    if who == 'Socrates':
        for i in range(3):
            keys[('location', i)] = [p[i] for p in OBJ['loc']]
        keys[('rotation_euler', 2)] = OBJ['yaw']
        c['arm'].rotation_euler = (0, 0, c['yaw0'])
    write_keys(c['arm'], keys, np.array(FRAMES, float))
print('keys kept %d of %d' % (TOTAL[1], TOTAL[0]))

# ------------------------------------------------------------------ light

stage.world(sc, kit.hexc('#141a2a'), 0.35)
stage.light('Pendant', 'POINT', (0, 0, 1.95), 110, (1.0, 0.82, 0.6), 0.15)
KEY = stage.light('Key', 'AREA', (-2.6, -3.6, 3.3), 420, (1.0, 0.9, 0.78), 3.0, to=(0, 0.4, 1.1))
stage.light('Fill', 'AREA', (3.4, -3.0, 1.6), 110, (0.62, 0.78, 1.0), 3.0, to=(0, 0.4, 1.1), shadow=False)
SCRL = stage.light('Screens', 'AREA', (0, 2.45, 2.1), 220, (0.45, 0.85, 1.0), 2.6, to=(0, 0, 1.2))
stage.light('Rim left', 'AREA', (-3.6, 2.2, 2.6), 260, (0.5, 0.85, 1.0), 1.5, to=(-0.5, 0.8, 1.3), shadow=False)
stage.light('Rim right', 'AREA', (3.6, 2.2, 2.6), 260, (0.5, 0.85, 1.0), 1.5, to=(0.5, 0.8, 1.3), shadow=False)
for who in ('Cleon', 'Aria'):
    p = CH[who]['slate'].matrix_world.translation
    n = CH[who]['slate'].matrix_world.to_3x3() @ V((0, 0, 1))
    L = stage.light('Glow ' + who, 'POINT', p + n * 0.12, 9, (0.5, 0.82, 1.0), 0.08, shadow=False)
    L.parent = CH[who]['slate']
    L.matrix_parent_inverse = CH[who]['slate'].matrix_world.inverted()
stage.light('Glow Julian', 'POINT', (0.74, 0.02, lounge.TABLE + 0.12), 8, (0.5, 0.82, 1.0), 0.08, shadow=False)
if SEQ == 4:
    # the screens go dark with the wind, then the dawn comes up warm
    for L_, e0 in ((SCRL, 220),):
        for f, e in ((F(DAWN_T - 1.4), e0), (F(DAWN_T - 1.2), 0), (F(DAWN_T), 0), (F(DAWN_T + 1.0), 300)):
            L_.data.energy = e
            L_.data.keyframe_insert('energy', frame=f)
        for f, col in ((F(DAWN_T), (0.45, 0.85, 1.0)), (F(DAWN_T + 0.5), (1.0, 0.72, 0.5))):
            L_.data.color = col
            L_.data.keyframe_insert('color', frame=f)
    for f, e, col in ((F(DAWN_T), 420, (1.0, 0.9, 0.78)), (F(DAWN_T + 3.0), 560, (1.0, 0.8, 0.62))):
        KEY.data.energy, KEY.data.color = e, col
        KEY.data.keyframe_insert('energy', frame=f)
        KEY.data.keyframe_insert('color', frame=f)

# ------------------------------------------------------------------ cameras and cuts

for who in CH:
    CH[who]['head_w'] = head_w(who)
hs = soc_head_at(END / FPS)
hs1 = V((SOC_SPOT.x, SOC_SPOT.y, CH['Socrates']['head_w'].z))
hj, hc, ha = CH['Julian']['head_w'], CH['Cleon']['head_w'], CH['Aria']['head_w']
CAMS = {
    'wide': stage.camera('Cam wide', (0, -4.4, 1.12), (0, 0.5, 1.02), 40),
    'soc': stage.camera('Cam Socrates', (-0.15, -0.45, 2.02), (hs1.x + 0.02, hs1.y, hs1.z - 0.14), 46),
    'soc2': stage.camera('Cam Socrates wide', (hs1.x + 1.1, hs1.y - 2.55, 1.02), (hs1.x - 0.05, hs1.y, hs1.z - 0.2), 40),
    'jul': stage.camera('Cam Julian', (0.42, 0.62, hj.z + 0.04), (hj.x, hj.y, hj.z - 0.12), 42),
    'cle': stage.camera('Cam Cleon', (-0.42, 0.62, hc.z + 0.04), (hc.x, hc.y, hc.z - 0.12), 42),
    'ari': stage.camera('Cam Aria', (-0.95, -0.55, ha.z - 0.02), (ha.x, ha.y, ha.z - 0.08), 46),
    'three': stage.camera('Cam listeners', (2.6, -1.6, 1.38), (-0.3, 0.9, 1.15), 36),
    'holo': stage.camera('Cam hologram', (0.25, -1.95, 1.02), (0.0, 0.35, 1.38), 30),
    'rev': stage.camera('Cam reverse', (-1.35, 2.45, 2.05), (0.35, -0.1, 0.95), 30),
}
if SEQ == 2:
    pc = stage.camera('Cam pacing', (0.0, -2.6, 2.25), (0, 1.6, 1.6), 42)
    con = pc.constraints.new('DAMPED_TRACK')
    con.target = soc['arm']
    con.subtarget = 'head'
    con.track_axis = 'TRACK_NEGATIVE_Z'
    CAMS['pace'] = pc
CLOSE = {'Socrates': 'soc', 'Julian': 'jul', 'Cleon': 'cle', 'Aria': 'ari'}
SHOT_FOR = {3: 'wide', 5: 'three', 6: 'wide', 7: 'soc2', 11: 'holo', 23: 'soc', 25: 'wide', 29: 'holo', 33: 'pace', 44: 'pace',
            49: 'holo', 53: 'holo', 59: 'holo', 61: 'soc', 68: 'soc', 73: 'holo', 76: 'holo', 84: 'soc', 89: 'soc', 92: 'soc2', 96: 'wide', 97: 'wide'}
CUTS = []


def cut(time, name):
    if CUTS and CUTS[-1][1] == name:
        return
    if CUTS and time - CUTS[-1][0] < 1.6:
        CUTS[-1] = (CUTS[-1][0], name)
        return
    CUTS.append((time, name))


def pacing(time):
    return SEQ == 2 and T(33) <= time <= T(45, 0.0)


prev = None
for it in ITEMS:
    t0, t1, who, i = it['t'], it['t'] + it['secs'], it['who'], it['i']
    start = 0.0 if it is ITEMS[0] else t0 - 0.25
    if who == 'Narrator':
        cut(start, SHOT_FOR.get(i, 'wide' if it['kind'] == 'sequence' else ('holo' if SEQ > 1 else 'wide')))
        continue
    me = 'pace' if (who == 'Socrates' and pacing(t0)) else CLOSE[who]
    cut(start, me)
    to = addressee(it, prev)
    if it['secs'] > 9:
        options = [CLOSE[to] if not (to == 'Socrates' and pacing(t0)) else 'pace', 'three' if who != 'Socrates' else 'wide', 'rev', 'holo' if SEQ > 1 else 'wide']
        k = 0
        for tt in np.arange(t0 + 5.0, t1 - 3.5, 8.5):
            cut(tt, options[k % len(options)])
            cut(tt + 3.2, me)
            k += 1
    prev = who
CUTS.sort()
for tm, name in CUTS:
    mk = sc.timeline_markers.new(name, frame=F(tm))
    mk.camera = CAMS[name]
sc.camera = CAMS[CUTS[0][1]]
stage.eevee(sc, WIDTH, WIDTH * 9 // 16, int(opt('--samples', 8)))

plan = {'seq': SEQ, 'frames': [0, END - 1], 'fps': FPS, 'seconds': round(END / FPS, 2),
        'cues': [{'id': it['id'], 't': round(it['t'], 4)} for it in ITEMS if it['id']], 'cuts': CUTS,
        'items': [(it['i'], it['who'], round(it['t'], 2), round(it['secs'], 2)) for it in ITEMS]}
print('sequence', SEQ, 'frames', END, 'seconds %.1f' % (END / FPS), 'items', len(ITEMS), 'cuts', len(CUTS))
if opt('--plan'):
    json.dump(plan, open(opt('--plan'), 'w'), indent=1)
if opt('--save'):
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=opt('--save'), compress=True)
still = opt('--still', n=2)
if still:
    for fr in still[0].split(','):
        sc.frame_set(int(fr))
        sc.render.filepath = still[1].replace('.png', '_%s.png' % fr)
        bpy.ops.render.render(write_still=True)
if opt('--preview'):
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x, sc.render.resolution_y = 480, 270
    step = int(opt('--pstep', 12))
    for fr in range(0, END, step):
        sc.frame_set(fr)
        sc.render.filepath = os.path.join(opt('--preview'), 'p_%05d.png' % fr)
        bpy.ops.render.render(write_still=True)
