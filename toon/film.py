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
# the wall screens: clean topic pictures that change as the conversation moves on
SLIDES = {1: [('news', 'raids_left', 'raids_right'), ('traffic', 'traffic_side', 'traffic_side')],
          2: [('traffic', 'traffic_side', 'traffic_side'), ('architecture', 'ocean_side', 'ocean_side')],
          3: [('architecture', 'ocean_side', 'ocean_side'), ('neuro', 'cortisol_side', 'cortisol_side')],
          4: [('neuro', 'cortisol_side', 'cortisol_side'), ('mirror', 'water_side', 'water_side')]}
SCR = []
for pos, n in enumerate(('Screen centre', 'Screen left', 'Screen right')):
    ob = bpy.data.objects[n]
    ob.data.materials.clear()
    m = holo.slides_material(n + ' pictures', [os.path.join(opt('--screens'), sl[pos] + '.png') for sl in SLIDES[SEQ]], power=1.0 if pos else 1.1)
    ob.data.materials.append(m)
    SCR.append(m)
    if pos:      # side screens show their whole picture
        uv = ob.data.uv_layers.active.data
        us = [d.uv[0] for d in uv]; vs = [d.uv[1] for d in uv]
        for d in uv:
            d.uv = ((d.uv[0] - min(us)) / (max(us) - min(us)), (d.uv[1] - min(vs)) / (max(vs) - min(vs)))


def screens_key(name, frame, v):
    for m in SCR:
        if name in m.node_tree.nodes:
            holo.key_value(m, name, frame, v)


SOC_SPOT = V((-0.75, 1.85, 0))
PLACES = {'Cleon': ((-1.53, 0.12, 0), 62, 1.0), 'Aria': ((0.16, 0.8, 0), 0, 0.93), 'Julian': ((1.58, 0.12, 0), -62, 1.06), 'Socrates': (tuple(SOC_SPOT), 8, 1.08)}
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


TH = {'Socrates': 1.05, 'Aria': 1.06, 'Cleon': 0.98, 'Julian': 0.86}      # limb thickness each was built with
PALM = 0.056       # wrist to the middle of the palm, along the fingers (armature units)
PALM_T = 0.030     # half the palm's thickness


def orient_hand(arm, side, fingers, palm):
    """Turn a hand about its wrist so its fingers point one way and its palm faces another (armature space)."""
    s = 1 if side == 'l' else -1
    f = V(fingers).normalized()
    n = V(palm)
    n = (n - f * n.dot(f)).normalized()
    e1, e2 = V((s, 0, 0)), V((0, 0, -1))
    Rb = Matrix((e1, e2, e1.cross(e2))).transposed()
    Tb = Matrix((f, n, f.cross(n))).transposed()
    pb = arm.pose.bones['hand_' + side]
    p = pb.matrix.translation.copy()
    M = (Tb @ Rb.transposed() @ arm.data.bones['hand_' + side].matrix_local.to_3x3()).to_4x4()
    M.translation = p
    pb.matrix = M
    kit.refresh()


def place_hand(arm, side, palm_c, fingers, palm, pole):
    """Put the middle of a palm at a point, fingers and palm facing the given ways (the fingers kept square to the palm)."""
    n = V(palm).normalized()
    f = V(fingers)
    f = (f - n * f.dot(n)).normalized()
    hand_to(arm, side, V(palm_c) - f * PALM, pole)
    orient_hand(arm, side, f, palm)


def rest_hand(who, side, along=0.62, lift=0.018, inward=0.2, out=0.0):
    """A hand resting palm down on its own thigh, just clear of it."""
    arm = CH[who]['arm']
    sg = 1 if side == 'l' else -1
    hp, kn = kit.joint(arm, 'upperleg_' + side), kit.joint(arm, 'lowerleg_' + side)
    ax = (kn - hp).normalized()
    n = (V((0, 0, 1)) - ax * ax.z).normalized()
    r = (0.098 + (0.08 - 0.098) * along) * TH[who]
    p = hp.lerp(kn, along) + n * (r + PALM_T + lift) + V((sg * out, 0, 0))
    f = (ax + V((-sg * inward, 0, 0))).normalized()
    S = kit.joint(arm, 'upperarm_' + side)
    place_hand(arm, side, p, f, -n, S + V((sg * 1.0, 0.0, -0.1)))


def slate_on_palm(who, side, name, centre, gap=0.004):
    """A slate lying on an upturned palm in front of the chest, its screen toward the eyes. centre is relative to the shoulder."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    eye = posed(arm, 'head', c['Hd'].C)
    p = S + V(centre)
    n = (eye - p).normalized()
    x = V((1, 0, 0)); x = (x - n * x.dot(n)).normalized()
    y = n.cross(x)
    f = (y * 0.9 - x * sg * 0.3).normalized()
    palm_c = p - n * (PALM_T + gap) - f * 0.09
    place_hand(arm, side, palm_c, f, n, S + V((sg * 0.55, 0.15, -0.5)))
    ob = lounge.slate(name)
    M = Matrix((x, y, n)).transposed().to_4x4()
    M.translation = p
    W = arm.matrix_world @ M
    pb = arm.pose.bones['hand_' + side]
    pm = arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    ob.parent, ob.parent_type, ob.parent_bone = arm, 'BONE', 'hand_' + side
    ob.matrix_parent_inverse = pm.inverted()
    ob.matrix_basis = W
    return ob


def slate_at(name, loc, yaw=0.0, tilt=0.0):
    ob = lounge.slate(name)
    ob.location = loc
    ob.rotation_euler = (math.radians(tilt), 0, math.radians(yaw))
    return ob


ARM_BONES = lambda sd: ['shoulder_' + sd, 'upperarm_' + sd, 'lowerarm_' + sd, 'hand_' + sd]
LID_OPEN = {'Cleon': -38, 'Aria': -48, 'Julian': -30, 'Socrates': -22}
SOC_OUT = float(opt('--soc-out', 0.2))
YW = (0.1, 0.36, 0.52)         # how a turn of the gaze is shared by the chest, neck and head
SLATE_HELD = SEQ <= 2       # Cleon holds his slate in the first two sequences; from the third it lies on the seat beside him

# ---- base poses: seated hands rest on the thighs, clear of them; slates lie on a palm or on the table
c = CH['Cleon']; a = c['arm']
sit(a, lean=14, spread=0.12, thigh=-0.05, shin={'l': (0.03, -0.3, -1.0), 'r': (-0.03, -0.55, -0.85)}, up=6)
rest_hand('Cleon', 'l', out=0.03)
if SLATE_HELD:
    c['slate'] = slate_on_palm('Cleon', 'r', 'Slate Cleon', (0.13, -0.33, -0.22))
else:
    rest_hand('Cleon', 'r', out=0.055, inward=0.0)
    c['slate'] = slate_at('Slate Cleon', (-1.47, 0.47, lounge.SEAT + 0.002), yaw=62 + 15)

c = CH['Aria']; a = c['arm']
sit(a, lean=4, spread=0.12, shin=(0, -0.32, -1.0))
for sd in 'lr':
    rest_hand('Aria', sd, 0.64, inward=-0.2, out=0.045)
c['slate'] = slate_at('Slate Aria', (0.22, 0.29, lounge.TABLE + 0.001), yaw=-4)

c = CH['Julian']; a = c['arm']
sit(a, lean=13, spread=0.11, thigh=-0.06, shin=(0, -0.25, -1.0), up=5)
for sd in 'lr':
    rest_hand('Julian', sd, 0.64, inward=-0.2, out=0.06)
JSLATE = slate_at('Slate Julian', (0.74, 0.02, lounge.TABLE + 0.001), yaw=72)

# Socrates stands with his arms easy at his sides, hands clear of the chiton's skirt and the himation
c = CH['Socrates']; a = c['arm']
for sd, sg in (('l', 1), ('r', -1)):
    S = kit.joint(a, 'upperarm_' + sd)
    place_hand(a, sd, S + V((sg * SOC_OUT, -0.08, -0.55)), (sg * 0.15, -0.18, -1.0), (-sg, 0.2, 0.0), S + V((sg * 0.35, 0.35, -0.25)))

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
AMOUNT = {'spine_01': 1.25, 'spine_02': 1.25, 'spine_03': 1.25, 'neck': 1.3, 'head': 1.3}
for sd in 'lr':
    AMOUNT.update({'shoulder_' + sd: float(opt('--arm-idle', 0.25)), 'upperarm_' + sd: float(opt('--arm-idle', 0.25)) * 0.5, 'lowerarm_' + sd: float(opt('--arm-idle', 0.25)) * 0.4, 'hand_' + sd: float(opt('--arm-idle', 0.25)) * 0.4})

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
                out = {}
                for b in pa:
                    if b.startswith('_plant_'):
                        (Ha, ea), (Hb, eb) = pa[b], pb[b]
                        H = Ha.to_quaternion().slerp(Hb.to_quaternion(), k).to_matrix().to_4x4()
                        H.translation = Ha.translation.lerp(Hb.translation, k)
                        out[b] = (H, ea.lerp(eb, k))
                    else:
                        out[b] = pa[b].slerp(pb[b], k)
                return 1.0, out
            if pa:
                return 1.0 - k, pa
            if pb:
                return k, pb
            return 0.0, None
    return 0.0, None


rng = random.Random(23)
FREE = {'Socrates': ['r', 'l'], 'Julian': ['l', 'r'], 'Cleon': ['l'] if SLATE_HELD else ['l', 'r'], 'Aria': ['r', 'l']}
LAB = []          # every pose a gesture asks for, to check for clearances: (who, name, {bone: q})


def capture2(ch, fn, name='', sides='lr', planted=False):
    """Like capture, for gestures that use both hands: {bone: q} for the arm bones of the given sides.
    planted: the hand is held at its spot in the room (over a slate on the table) however the body sways."""
    arm = ch['arm']
    before = kit.snapshot(arm)
    fn()
    g = {b: arm.pose.bones[b].rotation_quaternion.copy() for sd in sides for b in ARM_BONES(sd)}
    if planted:
        for sd in sides:
            g['_plant_' + sd] = (arm.pose.bones['hand_' + sd].matrix.copy(), arm.pose.bones['lowerarm_' + sd].matrix.translation.copy())
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
        arm.pose.bones[b].location = l
    kit.refresh()
    LAB.append((ch['name'], name, g))
    return g


def capture(ch, side, fn, name='', planted=False):
    return capture2(ch, fn, name, side, planted)


def still(who, t0, t1, yaw, pitch, x=None):
    """Hold the head steady, looking one way, while a hand is near it (x: the idle frame its neck and head keep)."""
    CH[who]['still'].append((t0, t1, yaw, pitch, x))


def idle_x(who, time):
    ph, speed = PHASE[who]
    return pingpong(ph + time * 30 * speed, A0, A1)


for who in CH:
    CH[who]['name'] = who
    CH[who]['still'] = []
    CH[who]['expr'] = []


def look_now(who, yaw, pitch):
    c = CH[who]
    for b, ky, kp in (('spine_03', YW[0], 0.0), ('neck', YW[1], 0.35), ('head', YW[2], 0.5)):
        pb = c['arm'].pose.bones[b]
        pb.rotation_quaternion = c['base'][b][0] @ Quaternion(c['axz'][b], yaw * ky) @ Quaternion(c['axx'][b], -pitch * kp)
    kit.refresh()


def explain_pose(who, side, var):
    """An open hand raised in front of the chest, palm up and in, as people hold a hand when they make a point."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    standing = who == 'Socrates'
    fwd = -0.36 if standing else -0.33
    down = -0.22 if standing else -0.16
    p = S + V((sg * (0.02 + 0.06 * var), fwd + 0.04 * var, down + 0.07 * var))
    f = V((-sg * 0.35, -1.0, 0.25 + 0.15 * var))
    n = V((-sg * 0.45, -0.1, 0.9))
    return capture(c, side, lambda: place_hand(arm, side, p, f, n, S + V((sg * 0.5, -0.45, -0.5)) if not standing else S + V((sg * 0.6, 0.15, -0.45))), 'explain %s %.0f' % (side, var))


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
    return S + d.normalized() * min(d.length, 0.6 * reach)


def point_at(who, side, world, t0, t1, sweep=None):
    """Reach toward a point (the hologram); with sweep, trace across it to a second point."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)

    behind_table = who == 'Aria'        # she sits behind the table: her hand rises over its edge first, and holds its place

    def at(w):
        p = toward_world(who, side, w)
        d = (p - S).normalized()
        return capture(c, side, lambda: place_hand(arm, side, p, d, V((0, 0, -1)), S + V((sg * 0.6, 0.2, -0.3))), 'point %s' % side, planted=behind_table)
    A = at(world)
    if behind_table:
        L = hover(who, side, kit.to_world(arm, S) + V((sg * 0.12, -0.32, -0.12)) * arm.scale.x, 'lift')
        move(who, [(t0 - 0.2, None), (t0 + 0.25, L), (t0 + 0.6, A), (t1 - 0.6, A), (t1 - 0.3, L), (t1 + 0.1, None)])
    elif sweep is None:
        move(who, [(t0, None), (t0 + 0.6, A), (t1 - 0.6, A), (t1, None)])
    else:
        B = at(sweep)
        move(who, [(t0, None), (t0 + 0.6, A), (t0 + (t1 - t0) * 0.55, B), (t1 - 0.5, B), (t1, None)])


def head_point(who, yaw, pitch, out):
    """A point off the head's surface, and the outward direction there, in armature space for the current pose."""
    c = CH[who]; arm = c['arm']; Hd = c['Hd']
    p0 = posed(arm, 'head', Hd.at(yaw, pitch, 1.0))
    p1 = posed(arm, 'head', Hd.at(yaw, pitch, 1.0 + out))
    return p1, (p1 - p0).normalized()


def temple(t0, t1):
    """Julian leans back and rubs his temple: the left palm just off the side of his head."""
    c = CH['Julian']; arm = c['arm']
    yaw, pitch = math.radians(-24), 0.08

    def fn():
        look_now('Julian', yaw, pitch)
        p, n = head_point('Julian', 72, 14, 0.12)
        S = kit.joint(arm, 'upperarm_l')
        place_hand(arm, 'l', p + n * (PALM_T + 0.035), V((0, 0.25, 1.0)), -n, S + V((0.6, -0.35, -0.15)))
    P = capture(c, 'l', fn, 'temple')
    for b in ('spine_03', 'neck', 'head'):
        arm.pose.bones[b].rotation_quaternion = c['base'][b][0]
    kit.refresh()
    move('Julian', [(t0, None), (t0 + 0.7, P), (t1 - 0.7, P), (t1, None)])
    still('Julian', t0, t1, yaw, pitch)


def slate_top(ob, u=0.0, v=0.0, h=0.03):
    """A world point h above a slate's screen, at (u, v) across it (-1..1)."""
    return ob.matrix_world @ V((0.11 * u, 0.07 * v, 0.0115 + h))


def over_slate(who, side, ob, u, v, h, name):
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    p = kit.to_arm(arm, slate_top(ob, u, v, h + PALM_T))
    nrm = (arm.matrix_world.inverted().to_3x3() @ (ob.matrix_world.to_3x3() @ V((0, 0, 1)))).normalized()
    f = (p - S); f = (f - nrm * f.dot(nrm)).normalized()
    p = p - f * 0.06      # the palm a little short of the point, the fingers over it
    return capture(c, side, lambda: place_hand(arm, side, p, f, -nrm, S + V((sg * 0.55, -0.1, -0.45))), name, planted=True)


def hover(who, side, world, name):
    """A palm-down hand held at a point in the room, a step on the way over the table's edge."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    p = kit.to_arm(arm, world)
    f = p - S
    f = V((f.x, f.y, 0)).normalized()
    return capture(c, side, lambda: place_hand(arm, side, p, f, V((0, 0, -1)), S + V((sg * 0.55, -0.1, -0.45))), name, planted=True)


def lift_for(who, side, ob):
    """Where a hand rises to before it reaches over the table to a slate: above the table's near edge, on the way."""
    c = CH[who]
    hw = kit.to_world(c['arm'], posed(c['arm'], 'head', c['Hd'].C))
    sp = ob.matrix_world.translation
    edge = hw.lerp(sp, 0.55)
    return V((edge.x, edge.y, lounge.TABLE + 0.12))


def swipe(t0):
    """Aria sweeps her right hand across the slate on the table, just above the screen."""
    sl = CH['Aria']['slate']
    L = hover('Aria', 'r', lift_for('Aria', 'r', sl), 'lift')
    A = over_slate('Aria', 'r', sl, 0.7, -0.3, 0.05, 'swipe A')
    B = over_slate('Aria', 'r', sl, -0.6, -0.2, 0.038, 'swipe B')
    move('Aria', [(t0 - 0.3, None), (t0 + 0.15, L), (t0 + 0.5, A), (t0 + 1.1, B), (t0 + 1.6, B), (t0 + 1.95, L), (t0 + 2.4, None)])


def tap_dance(t0, t1):
    """Aria's fingers dance across her slate: the hand hops from place to place, dipping toward the screen."""
    sl = CH['Aria']['slate']
    L = hover('Aria', 'r', lift_for('Aria', 'r', sl), 'lift')
    keys = [(t0 - 0.3, None), (t0 + 0.15, L)]
    tt = t0 + 0.5
    k = 0
    while tt < t1 - 0.8:
        u, v = rng.uniform(-0.6, 0.6), rng.uniform(-0.5, 0.3)
        keys.append((tt, over_slate('Aria', 'r', sl, u, v, 0.04, 'dance up')))
        keys.append((tt + 0.25, over_slate('Aria', 'r', sl, u, v, 0.02, 'dance down')))
        tt += 0.55
        k += 1
    keys += [(t1 - 0.4, L), (t1, None)]
    move('Aria', keys)


def stroke_beard(t0, t1):
    """Socrates strokes his beard: the hand moves down the front of it, just clear of the curls."""
    c = CH['Socrates']; arm = c['arm']
    S = kit.joint(arm, 'upperarm_r')

    yaw, pitch, xm = 0.3, -0.2, idle_x('Socrates', (t0 + t1) / 2)
    for b, ky, kp in (('neck', YW[1], 0.35), ('head', YW[2], 0.5)):
        arm.pose.bones[b].rotation_quaternion = isample(b, xm) @ Quaternion(c['axz'][b], yaw * ky) @ Quaternion(c['axx'][b], -pitch * kp)
    kit.refresh()

    def at(pitch_, out):
        def fn():
            p, n = head_point('Socrates', 4, pitch_, out)
            place_hand(arm, 'r', p + n * (PALM_T + 0.035), V((1.0, -0.1, -0.25)), -n, S + V((-0.15, -0.65, -0.35)))
        return capture(c, 'r', fn, 'beard')
    A, B = at(-34, 0.4), at(-41, 0.4)
    for b in ('neck', 'head'):
        arm.pose.bones[b].rotation_quaternion = c['base'][b][0]
    kit.refresh()
    keys = [(t0, None), (t0 + 0.7, A)]
    tt = t0 + 0.7
    while tt + 1.6 < t1 - 0.7:
        keys += [(tt + 0.8, B), (tt + 1.6, A)]
        tt += 1.6
    keys += [(t1, None)]
    move('Socrates', keys)
    still('Socrates', t0, t1, yaw, pitch, xm)


def cross_arms(t0, t1):
    """Cleon folds his arms: the left forearm across the waist, the right over it and in front, hands clear."""
    c = CH['Cleon']; arm = c['arm']
    sp = kit.joint(arm, 'spine_03')
    CROSS = [float(v) for v in opt('--cross', '0.1,-0.32,-0.14,0.1,-0.42,-0.05').split(',')]

    def fn():
        for sd, sg, (dx, dy, dz) in (('l', 1, CROSS[:3]), ('r', -1, CROSS[3:])):
            S = kit.joint(arm, 'upperarm_' + sd)
            p = V((sp.x - sg * dx, sp.y + dy, sp.z + dz))
            place_hand(arm, sd, p, V((-sg, -0.15, 0.1)), V((0, 0.3, -1.0)) if sd == 'l' else V((0, 0.6, -0.8)), S + V((sg * 0.6, 0.05, -0.5)))
    P = capture2(c, fn, 'cross arms')
    move('Cleon', [(t0, None), (t0 + 0.8, P), (t1 - 0.8, P), (t1, None)])


def fold_hands(t0, t1):
    """Socrates brings his hands together before him, palms facing, a hand's breadth from touching."""
    c = CH['Socrates']; arm = c['arm']
    s1 = kit.joint(arm, 'spine_01')

    def fn():
        for sd, sg in (('l', 1), ('r', -1)):
            S = kit.joint(arm, 'upperarm_' + sd)
            place_hand(arm, sd, V((s1.x + sg * 0.06, s1.y - 0.3, s1.z + 0.16)), V((sg * 0.1, -0.7, 0.7)), V((-sg, 0, 0)), S + V((sg * 0.6, 0.1, -0.5)))
    P = capture2(c, fn, 'fold hands')
    move('Socrates', [(t0, None), (t0 + 0.9, P), (t1 - 0.8, P), (t1, None)])


def raise_hand(t0, t1):
    """Socrates raises his right hand, palm out, so the ring shows."""
    c = CH['Socrates']; arm = c['arm']
    S = kit.joint(arm, 'upperarm_r')
    P = capture(c, 'r', lambda: place_hand(arm, 'r', S + V((-0.28, -0.3, 0.14)), V((-0.15, -0.1, 1.0)), V((0, -1, 0.1)), S + V((-0.6, 0.2, -0.4))), 'raise hand')
    move('Socrates', [(t0, None), (t0 + 0.9, P), (t1 - 0.8, P), (t1, None)])


def reach_slate(t0):
    """Julian reaches out and touches his slate on the table (his fingertips stop just above the screen)."""
    L = hover('Julian', 'r', lift_for('Julian', 'r', JSLATE), 'lift')
    A = over_slate('Julian', 'r', JSLATE, 0.0, -0.4, 0.05, 'reach A')
    B = over_slate('Julian', 'r', JSLATE, 0.0, -0.2, 0.022, 'reach B')
    move('Julian', [(t0 - 0.3, None), (t0 + 0.3, L), (t0 + 0.8, A), (t0 + 1.2, B), (t0 + 1.5, A), (t0 + 1.9, L), (t0 + 2.4, None)])


# ------------------------------------------------------------------ direction: who does what when

NAMES = ('Socrates', 'Julian', 'Aria', 'Cleon')
BUSY = {9, 14, 55, 81, 89}       # lines whose hands are taken by a gesture of their own
for it in ITEMS:
    if it['who'] == 'Narrator':
        continue
    t0, t1 = it['t'], it['t'] + it['secs']
    note = it['note'].lower()
    who = it['who']
    if it['secs'] > 5.5 and it['i'] not in BUSY:
        explain(who, t0, t1)
    if 'nodding' in note:
        CH[who]['nods'].append((t0, t0 + 4.0, 5.5))
    if 'leaning back' in note:
        CH[who]['leans'].append((t0 - 0.4, t0 + 6.0, -6))
    if 'leaning closer' in note:
        CH[who]['leans'].append((t0 - 0.3, t1 + 0.5, 12))

HOLO_AT = holo.CENTRE
for it in ITEMS:
    i, t0, t1 = it['i'], it['t'], it['t'] + it['secs']
    if i == 9:
        temple(t0 - 0.3, t0 + 5.2)
    elif i == 10:
        swipe(t0 + 0.1)
    elif i == 14:
        stroke_beard(t0 - 0.2, t0 + 6.5)
    elif i == 29:
        tap_dance(T(29, 0.45), T(29, 0.95))
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
        CH['Socrates']['nods'].append((t0, t0 + 3.5, 5.5))
    elif i == 89:
        raise_hand(t0 + 0.8, T(90, 1.0) + 0.4)
    elif i == 68:
        CH['Socrates']['nods'].append((t0 + 0.5, t0 + 4.0, 6.0))

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
    for b in BLINK[who]:
        d = f - b
        if 0 <= d <= 5:
            k = (0.6, 1.0, 1.0, 0.6, 0.25, 0.0)[d]
            return o + (72 - o) * k
    return o


# ------------------------------------------------------------------ faces: expressions the script calls for, as they are said

# channels: up (brow lift, m; up_l/up_r for one brow), tilt (inner brow ends up, rad), knit (brows drawn in, m),
# smile (mouth corners up, -1..1), wide (corners out, m), tight (lips pressed, 0..1), open (mouth parted), lid (deg, + closes),
# head (deg, + bows)
PRESETS = {
    'tired': dict(up=-0.002, tilt=0.22, smile=-0.3, lid=16, head=3),
    'worry': dict(up=0.004, tilt=0.42, knit=0.003, smile=-0.4, lid=-4),
    'tense': dict(up=0.003, tilt=0.4, knit=0.004, smile=-0.45, tight=0.8, lid=-6),
    'frown': dict(up=-0.006, tilt=-0.38, knit=0.005, smile=-0.5, tight=0.4, lid=6),
    'clench': dict(up=-0.008, tilt=-0.5, knit=0.006, smile=-0.6, tight=1.0, lid=9, wide=0.004),
    'grave': dict(up=-0.003, tilt=0.18, knit=0.003, smile=-0.4, tight=0.3, lid=7, head=2),
    'sorrow': dict(up=0.003, tilt=0.6, knit=0.003, smile=-0.85, lid=20, head=7),
    'raise': dict(up=0.011, lid=-9),
    'curious': dict(up_l=0.013, up_r=0.001, tilt=-0.08, smile=0.12, lid=-5),
    'wonder': dict(up=0.014, lid=-20, smile=-0.1, open=0.35),
    'hope': dict(up=0.007, tilt=0.12, smile=0.55, lid=0, open=0.1),
    'smile': dict(up=0.008, tilt=-0.05, smile=1.0, wide=0.01, lid=5, open=0.45),
    'warm': dict(up=0.005, smile=0.65, wide=0.006, lid=3, open=0.15),
    'determined': dict(up=-0.004, tilt=-0.22, knit=0.003, smile=0.15, tight=0.45, lid=4),
    'calm': dict(smile=0.35, wide=0.003, lid=4),
    'serious': dict(up=-0.002, tilt=-0.12, knit=0.002, smile=-0.18, tight=0.2),
}
# (element, who, expression, from, to, strength): from/to are fractions of the element's length, or '+s' seconds after its end
EXPR = [
    (5, 'Cleon', 'tired', 0.2, '+28'), (5, 'Aria', 'tired', 0.25, '+28'), (5, 'Julian', 'tired', 0.3, '+28'),
    (7, 'Socrates', 'raise', 0.6, 1.0, 0.7),
    (8, 'Cleon', 'wonder', 0.0, 0.25, 0.6), (8, 'Aria', 'wonder', 0.0, 0.25, 0.6), (8, 'Julian', 'wonder', 0.0, 0.25, 0.5), (8, 'Socrates', 'curious', 0.7, 1.05),
    (9, 'Julian', 'tired', 0.0, 0.5), (9, 'Julian', 'worry', 0.5, 1.0),
    (12, 'Aria', 'worry', 0, 1),
    (13, 'Cleon', 'frown', 0, 1), (13, 'Aria', 'worry', 0.4, 1, 0.5),
    (14, 'Socrates', 'curious', 0, 0.5), (14, 'Socrates', 'grave', 0.5, 1),
    (15, 'Julian', 'frown', 0, 0.6), (15, 'Julian', 'grave', 0.6, 1),
    (16, 'Socrates', 'warm', 0, 0.15), (16, 'Socrates', 'raise', 0.15, 0.75, 0.6), (16, 'Socrates', 'curious', 0.85, 1.05),
    (17, 'Aria', 'serious', 0, 1),
    (18, 'Socrates', 'grave', 0, 1), (18, 'Julian', 'grave', 0.3, 1, 0.6),
    (19, 'Cleon', 'clench', -0.02, 1.0, 1.25),
    (20, 'Julian', 'worry', 0, 1), (20, 'Cleon', 'frown', 0, 1, 0.6),
    (21, 'Socrates', 'wonder', -0.03, 1.0, 1.25),
    (22, 'Cleon', 'grave', 0, 1), (22, 'Socrates', 'sorrow', 0.3, 1, 0.6),
    (23, 'Socrates', 'grave', 0.0, '+3', 1.1),
    (24, 'Socrates', 'grave', 0, 0.8), (24, 'Socrates', 'raise', 0.8, 1.05, 0.7), (24, 'Aria', 'worry', 0.6, 1, 0.6),
    (25, 'Cleon', 'worry', 0, '+3'), (25, 'Aria', 'worry', 0, '+3'), (25, 'Julian', 'worry', 0, '+3'), (25, 'Socrates', 'grave', 0, '+3'),
    (29, 'Aria', 'determined', 0.3, 1),
    (30, 'Aria', 'serious', 0, 1), (31, 'Cleon', 'frown', 0, 1), (32, 'Julian', 'frown', 0, 1),
    (34, 'Socrates', 'raise', 0, 0.4), (34, 'Socrates', 'grave', 0.4, 1),
    (35, 'Aria', 'curious', -0.05, 1.1, 1.25),
    (36, 'Socrates', 'grave', 0, 0.3), (36, 'Socrates', 'raise', 0.3, 1, 0.6),
    (37, 'Cleon', 'curious', 0, 1),
    (38, 'Socrates', 'warm', 0.4, 1, 0.6),
    (39, 'Julian', 'raise', 0, 0.5, 0.7), (39, 'Julian', 'grave', 0.5, 1, 0.6),
    (40, 'Socrates', 'raise', 0, 0.15), (40, 'Socrates', 'grave', 0.5, 1),
    (41, 'Aria', 'worry', 0, 1),
    (42, 'Socrates', 'grave', 0, 0.5), (42, 'Socrates', 'sorrow', 0.5, 1, 0.7),
    (43, 'Cleon', 'determined', 0, 1),
    (44, 'Socrates', 'grave', 0, '+2'),
    (45, 'Socrates', 'warm', 0, 0.1, 0.6), (45, 'Socrates', 'grave', 0.15, 0.85), (45, 'Socrates', 'raise', 0.85, 1.05, 0.7),
    (50, 'Julian', 'grave', 0, 1), (51, 'Socrates', 'curious', 0, 1), (52, 'Julian', 'serious', 0, 1), (53, 'Socrates', 'wonder', 0, 1, 0.6),
    (54, 'Aria', 'frown', 0, 1), (55, 'Cleon', 'frown', 0, 1, 1.15), (56, 'Julian', 'worry', 0, 1),
    (57, 'Socrates', 'wonder', -0.05, 1.0, 1.25), (58, 'Julian', 'grave', 0, 1),
    (59, 'Socrates', 'sorrow', 0, 1, 0.6), (59, 'Aria', 'worry', 0, 1, 0.6), (60, 'Julian', 'worry', 0, 1),
    (61, 'Socrates', 'sorrow', 0.0, '+3', 1.3),
    (62, 'Socrates', 'sorrow', 0, 0.4), (62, 'Socrates', 'grave', 0.4, 1),
    (63, 'Cleon', 'warm', 0, 1, 0.5), (64, 'Socrates', 'grave', 0, 1), (65, 'Julian', 'grave', 0, 1),
    (66, 'Aria', 'tense', 0, 1, 1.25), (67, 'Cleon', 'determined', 0, 1),
    (68, 'Socrates', 'hope', 0.2, '+3', 1.25),
    (69, 'Socrates', 'hope', 0, 0.4), (69, 'Socrates', 'raise', 0.6, 1.05, 0.7),
    (73, 'Socrates', 'grave', 0, 1), (73, 'Cleon', 'tired', 0, 1, 0.6), (73, 'Aria', 'tired', 0, 1, 0.6), (73, 'Julian', 'tired', 0, 1, 0.6),
    (74, 'Cleon', 'grave', 0, 1), (75, 'Aria', 'determined', 0, 1), (77, 'Aria', 'determined', 0, 1),
    (78, 'Socrates', 'curious', -0.05, 1), (79, 'Julian', 'serious', 0, 1),
    (80, 'Cleon', 'frown', 0, 0.5), (80, 'Cleon', 'determined', 0.5, 1),
    (81, 'Socrates', 'raise', 0, 1, 0.6), (82, 'Julian', 'calm', 0, 1), (83, 'Aria', 'calm', 0, 1), (83, 'Socrates', 'warm', 0.6, 1, 0.6),
    (84, 'Socrates', 'smile', 0.0, '+2', 1.3), (85, 'Socrates', 'smile', 0, 1, 1.0),
    (86, 'Cleon', 'hope', 0, 1), (87, 'Aria', 'hope', 0, 1), (88, 'Julian', 'calm', 0, 1),
    (89, 'Socrates', 'warm', 0, 1), (90, 'Socrates', 'warm', 0, 1), (91, 'Cleon', 'hope', 0, 1), (92, 'Socrates', 'warm', 0, 1),
    (93, 'Socrates', 'smile', 0, 1, 0.8), (95, 'Socrates', 'smile', 0, 1, 1.0),
    (96, 'Cleon', 'wonder', 0.2, 1), (96, 'Aria', 'wonder', 0.2, 1), (96, 'Julian', 'wonder', 0.2, 1),
    (97, 'Cleon', 'hope', 0, '+5'), (97, 'Aria', 'hope', 0, '+5'), (97, 'Julian', 'hope', 0, '+5'),
]


def when(i, x):
    if isinstance(x, str):
        return T(i, 1.0, float(x[1:]))
    return T(i, x)


for row in EXPR:
    i, who, name, a_, b_ = row[:5]
    k = row[5] if len(row) > 5 else 1.0
    if i in BY:
        CH[who]['expr'].append((when(i, a_), when(i, b_), PRESETS[name], k))

# what the narration says the body does: Socrates straightens; later he stands upright in sorrow
if 23 in BY:
    CH['Socrates']['leans'].append((T(23, 0.0), T(24, 0.25), -7))
if 61 in BY:
    CH['Socrates']['leans'].append((T(61, 0.0), T(62, 0.3), -6))

# speakers lift their brows at the start of a phrase now and then; listeners nod now and then
for it in ITEMS:
    who = it['who']
    if who == 'Narrator' or it['env'].size < 10:
        continue
    e = np.convolve(it['env'], np.ones(5) / 5, 'same')
    quiet = 0
    for k in range(len(e)):
        if e[k] < 0.12:
            quiet += 1
        else:
            if quiet >= 6 and rng.random() < 0.55:
                t0 = it['t'] + k / FPS
                CH[who]['expr'].append((t0 - 0.05, t0 + 0.45, dict(up=0.007), 1.0))
            quiet = 0
    if it['secs'] > 7:
        for w in CH:
            if w != who and rng.random() < 0.8:
                t0 = it['t'] + rng.uniform(3.0, it['secs'] - 2.5)
                CH[w]['nods'].append((t0, t0 + 1.6, 3.0))


def expr_at(who, time):
    ch = {}
    for (t0, t1, p, k) in CH[who]['expr']:
        w = window(t0, t1, 0.45)(time) * k
        if w > 0:
            for name, v in p.items():
                ch[name] = ch.get(name, 0.0) + v * w
    return ch


BROW_AX = {who: {sd: kit.local_axis(CH[who]['arm'], 'brow_' + sd, (0, 1, 0)) for sd in 'lr'} for who in CH}
REST3 = {who: {b: CH[who]['arm'].data.bones[b].matrix_local.to_3x3().inverted() for b in ('brow_l', 'brow_r', 'mouth_l', 'mouth_r')} for who in CH}
LIFT = {'Socrates': 0.011, 'Aria': 0.01, 'Cleon': 0.009, 'Julian': 0.009}


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
for m in SCR:
    sc_ = m.node_tree.nodes['Scan']
    if 'Phase Offset' in sc_.inputs:
        for f, w in ((0, 0.0), (END, END / FPS * 0.9)):
            sc_.inputs['Phase Offset'].default_value = w
            sc_.inputs['Phase Offset'].keyframe_insert('default_value', frame=f)

GLOW = stage.light('Holo glow', 'POINT', holo.CENTRE, 0.0, (0.5, 0.85, 1.0), 0.25, shadow=False)


def glow_key(t0, energy, colour=None):
    GLOW.data.energy = energy
    GLOW.data.keyframe_insert('energy', frame=F(t0))
    if colour:
        GLOW.data.color = colour
        GLOW.data.keyframe_insert('color', frame=F(t0))


soc_key(0, fade=1.0, shimmer=0.0)
if SEQ == 1:
    tsl = T(10, 0.6)
    screens_key('Slide1', 0, 0.0)
    screens_key('Slide1', F(tsl), 0.0)
    screens_key('Slide1', F(tsl + 1.6), 1.0)
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
    ts = T(29, 0.25)
    screens_key('Slide1', 0, 0.0)
    screens_key('Slide1', F(ts), 0.0)
    screens_key('Slide1', F(ts + 2.5), 1.0)
    hide(web, ts + 0.6, 1.0)
    show(net, ts + 1.6, 1.8)
    glow_key(0, 40.0, (0.5, 0.85, 1.0))
    glow_key(ts + 1.6, 40.0, (0.45, 1.0, 0.9))
elif SEQ == 3:
    present(net)
    tap = T(49, 0.35) + 1.2
    screens_key('Slide1', 0, 0.0)
    screens_key('Slide1', F(tap + 0.8), 0.0)
    screens_key('Slide1', F(tap + 2.6), 1.0)
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
    screens_key('Slide1', 0, 0.0)
    screens_key('Slide1', F(T(76, 0.15)), 0.0)
    screens_key('Slide1', F(T(76, 0.15) + 2.2), 1.0)
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
    for m in SCR:
        v0 = m.node_tree.nodes['Power'].outputs[0].default_value
        holo.key_value(m, 'Power', F(tw - 0.2), v0)
        holo.key_value(m, 'Power', F(tw), 0.0)
        holo.key_value(m, 'Power', F(tw + 1.2), 0.0)
        holo.key_value(m, 'Power', F(tw + 2.2), 1.6)
    screens_key('Dawn', F(tw + 1.2), 0.0)
    screens_key('Dawn', F(tw + 1.25), 1.0)
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


# the walk's arm swing, as a change from its own average, so Socrates keeps his arms clear of his robes as he paces
WMEAN = {}
if WALK:
    for b in [x for sd in 'lr' for x in ARM_BONES(sd)]:
        if b in WR:
            m = Quaternion((0, 0, 0, 0))
            for q in WR[b][W0:W1]:
                m = Quaternion((m.w + q.w, m.x + q.x, m.y + q.y, m.z + q.z))
            WMEAN[b] = m.normalized()
SOC_ARM_IDLE = float(opt('--soc-arm-idle', 0.12))
ARMSET = set(ARM_BONES('l') + ARM_BONES('r'))


# ---- planted hands: a seated hand at rest stays where it lies, whatever the spine does, by solving the arm each frame
REL = {}
for who, c in CH.items():
    bones = c['arm'].data.bones
    REL[who] = {b.name: ((b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy(), b.parent.name if b.parent else None) for b in bones}
    pbs = c['arm'].pose.bones
    c['plant'] = {sd: (pbs['hand_' + sd].matrix.copy(), pbs['lowerarm_' + sd].matrix.translation.copy()) for sd in 'lr'}


def fk(who, local, bone, memo):
    """A bone's armature-space matrix for local rotations (missing bones take the base pose)."""
    if bone in memo:
        return memo[bone]
    rel, par = REL[who][bone]
    q = local.get(bone)
    if q is None:
        q = CH[who]['base'][bone][0]
    L = Matrix.Translation(CH[who]['base'][bone][1]) @ q.to_matrix().to_4x4()
    M = (fk(who, local, par, memo) @ rel @ L) if par else (rel @ L)
    memo[bone] = M
    return M


SP0 = {who: fk(who, {}, 'spine_03', {}) for who in CH}


def plant(who, side, local, target=None):
    """Upper arm, forearm and hand rotations that put the hand on a fixed spot (its resting place, or a gesture's
    target given as (hand matrix, elbow point)) in armature space; the elbow keeps its place relative to the chest."""
    c = CH[who]
    Hm, elbow = target or c['plant'][side]
    memo = {}
    elbow = fk(who, local, 'spine_03', memo) @ SP0[who].inverted() @ elbow
    up, lo, hd = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    Msh = fk(who, local, 'shoulder_' + side, memo)
    rel_up = REL[who][up][0]
    S = (Msh @ rel_up).translation
    L1 = (REL[who][lo][0].translation).length
    L2 = (REL[who][hd][0].translation).length
    Tw = Hm.translation
    d = (Tw - S).length
    dd = max(abs(L1 - L2) + 1e-4, min(d, L1 + L2 - 1e-4))
    u = (Tw - S).normalized()
    a_ = (L1 * L1 - L2 * L2 + dd * dd) / (2 * dd)
    h_ = math.sqrt(max(0.0, L1 * L1 - a_ * a_))
    pv = elbow - S
    pv = pv - u * pv.dot(u)
    pv = pv.normalized() if pv.length > 1e-6 else V((0, 0, -1))
    E = S + u * a_ + pv * h_
    out = {}
    # upper arm: turn its rest-relative frame so the bone runs from S to E
    rel_lo = REL[who][lo][0]
    rel_h = REL[who][hd][0]
    base_up = Msh @ rel_up @ c['base'][up][0].to_matrix().to_4x4()
    v = (base_up @ rel_lo).translation - S
    R = v.rotation_difference(E - S).to_matrix()
    want = R @ base_up.to_3x3()
    out[up] = ((Msh @ rel_up).to_3x3().inverted() @ want).to_quaternion()
    Mup = (Msh @ rel_up).to_3x3() @ out[up].to_matrix()
    Mup4 = Mup.to_4x4(); Mup4.translation = S
    base_lo = Mup4 @ rel_lo @ c['base'][lo][0].to_matrix().to_4x4()
    Ea = base_lo.translation
    v = (base_lo @ rel_h).translation - Ea
    R = v.rotation_difference(Tw - Ea).to_matrix()
    want = R @ base_lo.to_3x3()
    out[lo] = ((Mup4 @ rel_lo).to_3x3().inverted() @ want).to_quaternion()
    Mlo = (Mup4 @ rel_lo).to_3x3() @ out[lo].to_matrix()
    Mlo4 = Mlo.to_4x4(); Mlo4.translation = (Mup4 @ rel_lo).translation
    out[hd] = ((Mlo4 @ rel_h).to_3x3().inverted() @ Hm.to_3x3()).to_quaternion()
    return out


PLANTED = {'Aria': 'lr', 'Julian': 'lr', 'Cleon': 'lr'}
if opt('--fk-test'):
    for who in ('Aria', 'Cleon', 'Julian'):
        pbs = CH[who]['arm'].pose.bones
        e1 = (fk(who, {}, 'hand_l', {}).translation - pbs['hand_l'].matrix.translation).length
        pl = plant(who, 'l', {})
        e2 = {b: round(pl[b].rotation_difference(CH[who]['base'][b][0]).angle, 4) for b in pl}; e2['ydot'] = round(((pbs['lowerarm_l'].matrix.translation - pbs['upperarm_l'].matrix.translation).normalized()).dot(pbs['upperarm_l'].matrix.to_3x3().col[1].normalized()), 5)
        print('FKTEST', who, 'fk error %.6f' % e1, 'plant', e2)


def frame_pose(who, f):
    """Everything keyed on one character at one frame: {data path: value tuple}, and for Socrates his place and heading."""
    c = CH[who]
    time = f / FPS
    x = idle_x(who, time)
    standing = who == 'Socrates'
    talk = env_at(who, f)
    talk_s = float(np.mean([env_at(who, g) for g in range(f - 3, f + 4)]))
    if standing:
        sx, syaw, wmix, dist = soc_state(time)
    else:
        sx, syaw, wmix, dist = 0, 0, 0, 0
    yaw, pitch = gaze(who, time, syaw)
    hold, xf = 0.0, None
    for (t0, t1, hy, hp, hx) in c['still']:
        w = window(t0, t1, 0.6)(time)
        if w > hold:
            hold, xf = w, hx
            yaw, pitch = yaw + (hy - yaw) * w, pitch + (hp - pitch) * w
    ex = expr_at(who, time)
    lean = sum(d * window(t0, t1, 0.6)(time) for (t0, t1, d) in c['leans'])
    nod = sum(math.radians(a_) * math.sin(2 * math.pi * 0.9 * (time - t0)) * window(t0, t1, 0.4)(time) for (t0, t1, a_) in c['nods'])
    wx = (dist / (STRIDE * 1.08) * (W1 - W0)) if (WALK and wmix > 0) else 0.0
    out = {}
    local = {}
    planted = {}
    for b in BODY + (LEGS if standing else []):
        d = MEAN[b].inverted() @ isample(b, x)
        sd_ = b[-1] if b.startswith(('upperarm_', 'lowerarm_', 'hand_')) else None
        if not standing and sd_ and sd_ in PLANTED.get(who, ''):
            if sd_ not in planted:
                planted[sd_] = plant(who, sd_, local)
        if standing:
            if b in ARMSET:
                q = c['base'][b][0] @ scaled(d, SOC_ARM_IDLE)
                if wmix > 0 and b in WMEAN:
                    q = q.slerp(c['base'][b][0] @ scaled(WMEAN[b].inverted() @ wsample(b, wx), 0.55), wmix)
            else:
                q = isample(b, x)
                if b in ('neck', 'head') and hold > 0 and xf is not None:
                    q = q.slerp(isample(b, xf), hold)
                if wmix > 0 and WALK and b in WR:
                    q = q.slerp(wsample(b, wx), wmix)
        elif sd_ and sd_ in planted:
            q = planted[sd_][b]
        else:
            k = AMOUNT.get(b, 0.8)
            if b in ('neck', 'head'):
                k *= (1 - hold)
            q = c['base'][b][0] @ scaled(d, k)
        for keys in c['moves']:
            w, pose = move_at(keys, time)
            if w > 0 and pose and b in pose:
                if sd_ and ('_plant_' + sd_) in pose:
                    tgt = plant(who, sd_, local, pose['_plant_' + sd_]) if b == 'upperarm_' + sd_ or ('_solved', sd_) not in planted else None
                    if tgt:
                        planted[('_solved', sd_)] = tgt
                    q = q.slerp(planted[('_solved', sd_)][b], w)
                else:
                    q = q.slerp(pose[b] @ scaled(d, 0.15), w)
        if b == 'spine_01' and lean:
            q = q @ Quaternion(c['axx'][b], math.radians(lean) * 0.4)
        elif b == 'spine_02' and lean:
            q = q @ Quaternion(c['axx'][b], math.radians(lean) * 0.6)
        if b == 'spine_03':
            q = q @ Quaternion(c['axz'][b], yaw * YW[0])
        elif b == 'neck':
            q = q @ Quaternion(c['axz'][b], yaw * YW[1]) @ Quaternion(c['axx'][b], -pitch * 0.35)
        elif b == 'head':
            bob = math.radians(4.0) * (talk_s - 0.25) if talk_s > 0.02 else 0.0
            bow = math.radians(ex.get('head', 0.0))
            q = q @ Quaternion(c['axz'][b], yaw * YW[2]) @ Quaternion(c['axx'][b], -pitch * 0.5 + (bob + nod + bow) * (1 - hold))
        local[b] = q
        out['pose.bones["%s"].rotation_quaternion' % b] = tuple(q)
    if standing:
        for b in ('hip', 'root'):
            l = iloc(b, x)
            if wmix > 0 and WALK:
                wl = V((0, 0, 0)) if b == 'root' else wloc(b, wx)
                l = l.lerp(wl, wmix)
            out['pose.bones["%s"].location' % b] = tuple(l)
        yaw_t = c['yaw0'] + syaw
        off = Matrix.Rotation(yaw_t, 3, 'Z') @ IDLE_OFF * (1 - wmix)
        out['location'] = tuple(V((sx, SOC_SPOT.y, 0)) - off)
        out['rotation_euler'] = (0.0, 0.0, yaw_t)
    # eyes, brows and mouth
    la = math.radians(lid_angle(who, f) + ex.get('lid', 0.0))
    for sd in 'lr':
        out['pose.bones["lid_%s"].rotation_quaternion' % sd] = tuple(Quaternion(c['axx']['lid_' + sd], la))
    for sd, sg in (('l', 1), ('r', -1)):
        up = ex.get('up', 0.0) + ex.get('up_' + sd, 0.0)
        knit = ex.get('knit', 0.0)
        v = REST3[who]['brow_' + sd] @ V((-sg * knit, 0.3 * max(up, 0.0), up))
        out['pose.bones["brow_%s"].location' % sd] = tuple(v)
        out['pose.bones["brow_%s"].rotation_quaternion' % sd] = tuple(Quaternion(BROW_AX[who][sd], sg * ex.get('tilt', 0.0)))
        sm = max(-1.0, min(1.2, ex.get('smile', 0.0)))
        wide = ex.get('wide', 0.0) - 0.006 * talk * (1 - max(0.0, sm))
        v = REST3[who]['mouth_' + sd] @ V((sg * wide, 0.004 * max(sm, 0.0), sm * LIFT[who]))
        out['pose.bones["mouth_%s"].location' % sd] = tuple(v)
    tight = min(1.0, ex.get('tight', 0.0))
    opn = (0.45 + 1.8 * talk + ex.get('open', 0.0)) * (1 - 0.6 * tight)
    out['pose.bones["mouth"].scale'] = (1.0, max(0.18, opn), 1.0)
    return out


def apply_pose(who, vals):
    arm = CH[who]['arm']
    for path, v in vals.items():
        if path == 'location':
            arm.location = v
        elif path == 'rotation_euler':
            arm.rotation_euler = v
        else:
            b = path.split('"')[1]
            setattr(arm.pose.bones[b], path.split('.')[-1], v)


STEP = 2
FRAMES = list(range(0, END, STEP))
CHECK = opt('--check')
if CHECK:
    # walk the whole sequence with the poses applied directly, and report every place parts pass into each other
    import clearance
    for ch in CH.values():
        for m in ch['body'].modifiers:
            m.show_viewport = False
    figs = clearance.figures()
    slates = [CH['Cleon']['slate'], CH['Aria']['slate'], JSLATE]
    LAB_ONLY = opt('--lab')
    if LAB_ONLY:
        # just the gesture poses, each on its own, standing in the base pose
        for who, name, g in LAB:
            c = CH[who]
            for pb in c['arm'].pose.bones:
                pb.rotation_quaternion = c['base'][pb.name][0]
            for b, q in g.items():
                if not b.startswith('_'):
                    c['arm'].pose.bones[b].rotation_quaternion = q
            kit.refresh()
            m = clearance.measure({who: figs[who]}, slates, lounge.boxes())
            worst = sorted(((v, k) for k, v in m.items()), key=lambda z: z[0])[:3]
            print('LAB %-9s %-14s' % (who, name), '  '.join('%s/%s %+.3f' % (k[1], k[2], v) for v, k in worst))
        for who, c in CH.items():
            for pb in c['arm'].pose.bones:
                pb.rotation_quaternion = c['base'][pb.name][0]
        kit.refresh()
        m = clearance.measure(figs, slates, lounge.boxes())
        for who in CH:
            worst = sorted(((v, k) for k, v in m.items() if k[0] == who), key=lambda z: z[0])[:4]
            print('LAB %-9s %-14s' % (who, 'base'), '  '.join('%s/%s %+.3f' % (k[1], k[2], v) for v, k in worst))
        if opt('--debug'):
            who, a_, b_ = opt('--debug').split(',')
            fg = figs[who]
            X = fg.pts(a_)
            sd = fg.signed(b_, X)
            i = int(np.argmin(sd))
            dd, j = fg.tree(b_).query(X[i])
            print('DEBUG point', X[i], 'signed', sd[i], 'nearest', fg.P[fg.part[b_][j]], 'normal', fg.N[fg.part[b_][j]], 'dist', dd)
            print('DEBUG part sizes', {k: len(v) for k, v in fg.part.items()})
            print('DEBUG bbox', a_, X.min(0), X.max(0))
        sys.exit(0)
    bad = {}
    step = int(CHECK)
    for f in range(0, END, step):
        for who in CH:
            apply_pose(who, frame_pose(who, f))
        kit.refresh()
        for k, v in clearance.measure(figs, slates, lounge.boxes()).items():
            if v < 0.003:
                bad.setdefault(k, []).append((f, v))
    runs = []
    for k, fs in bad.items():
        cur = None
        for f, v in fs:
            if cur and f - cur[1] <= step * 2:
                cur = [cur[0], f, min(cur[2], v)]
            else:
                if cur:
                    runs.append((*k, *cur))
                cur = [f, f, v]
        runs.append((*k, *cur))
    runs.sort(key=lambda r: r[3])
    for r in runs:
        print('CLASH %-9s %-8s %-14s frames %5d-%5d (%.1f-%.1fs) worst %+.3f m' % (r[0], r[1], r[2], r[3], r[4], r[3] / FPS, r[4] / FPS, r[5]))
    print('CLASHES', len(runs))
    json.dump(runs, open(CHECK_OUT, 'w')) if (CHECK_OUT := opt('--check-out')) else None
    sys.exit(0)

for f in FRAMES:
    for who in CH:
        vals = frame_pose(who, f)
        for path, v in vals.items():
            if path == 'location':
                OBJ['loc'].append(v)
            elif path == 'rotation_euler':
                OBJ['yaw'].append(v[2])
            else:
                put(who, path, v)


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
    if 'brow_' in path or 'mouth_' in path:
        return 0.0003 if 'location' in path else 0.002
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
    'soc2': stage.camera('Cam Socrates wide', (hs1.x + 1.75, hs1.y - 2.75, 1.85), (hs1.x - 0.05, hs1.y, hs1.z - 0.3), 36),
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
# a second close-up for each sitter, from in front: for when they look down at a slate or into the projection
for who, key, side in (('Cleon', 'cle2', 1), ('Julian', 'jul2', -1), ('Aria', 'ari2', 0)):
    c = CH[who]
    f = V((math.sin(c['yaw0']), -math.cos(c['yaw0']), 0))        # the way they face
    r = V((-math.cos(c['yaw0']), -math.sin(c['yaw0']), 0))       # their right
    h = c['head_w']
    if who == 'Aria':
        pos = V((0.6, -0.4, h.z - 0.02))
    else:
        pos = V((PLACES[who][0][0], PLACES[who][0][1], 0)) + f * 1.05 + r * 0.25 * side + V((0, 0, h.z - 0.03))
    CAMS[key] = stage.camera('Cam %s front' % who, tuple(pos), (h.x, h.y, h.z - 0.1), 48)
CLOSE = {'Socrates': 'soc', 'Julian': 'jul', 'Cleon': 'cle', 'Aria': 'ari'}
CLOSE2 = {'Julian': 'jul2', 'Cleon': 'cle2', 'Aria': 'ari2'}


def looking_at(who, time):
    name = LOOKS[who][0][1]
    for (t0, n) in LOOKS[who]:
        if t0 <= time:
            name = n
    return name


def close_on(who, time):
    """The sitter's close-up camera that best faces the way their face is turned at that moment."""
    if who not in CLOSE2:
        return CLOSE[who]
    c = CH[who]
    yaw, pitch = gaze(who, time)
    face = V((math.sin(c['yaw0'] + yaw), -math.cos(c['yaw0'] + yaw), 0))
    h = c['head_w']
    best = None
    for key in (CLOSE[who], CLOSE2[who]):
        d = CAMS[key].location - h
        d = V((d.x, d.y, 0)).normalized()
        sc_ = face.dot(d)
        if best is None or sc_ > best[0]:
            best = (sc_, key)
    return best[1]
SHOT_FOR = {3: 'wide', 5: 'three', 6: 'wide', 7: 'soc2', 11: 'holo', 23: 'soc', 25: 'three', 29: 'holo', 33: 'pace', 44: 'pace',
            49: 'holo', 53: 'holo', 59: 'holo', 61: 'soc', 68: 'soc', 73: 'three', 76: 'holo', 84: 'soc', 89: 'soc2', 92: 'soc2', 96: 'wide', 97: 'three'}
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
    me = 'pace' if (who == 'Socrates' and pacing(t0)) else close_on(who, t0 + 0.8)
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
if 73 in BY:            # the trio in the projection's glow, then Socrates waiting, eyes on it
    CUTS.append((T(73, 0.55), 'soc'))
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
