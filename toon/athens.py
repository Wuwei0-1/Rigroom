"""The Ring of Gyges IV in Cephalus's courtyard: a stretch of the script as a 3D cartoon scene, for the render server.

    python athens.py -- --script script.json --voices DIR --idle IDLE.fbx --range A,B [--cache DIR] [--save OUT.blend]
                        [--plan OUT.json] [--still F,F OUT.png] [--preview DIR] [--width 1280] [--samples 8]

Elements A..B of the script (lines, stage directions, inserts) are timed from their voice recordings (eNNN.wav and
index.json in the voices folder). The Athenians sit on the chairs of the courtyard set or stand on their marks; bodies
move with the recorded idle; heads turn to whoever speaks; mouths follow the voices; brows, mouth corners and lids
act the script's notes; Julian, wearing the ring turned inward, is a glassy outline that casts no shadow.
The directing follows film.py (The Ring of Gyges III), made general for any number of people.
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

import athenians
import cast
import courtyard
import kit
import stage

V = Vector
FPS = 24
argv = sys.argv[sys.argv.index('--') + 1:]


def opt(name, default=None, n=1):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if n == 1 else argv[i + 1:i + 1 + n]
    return default


ELS = json.load(open(opt('--script')))
VOICES = opt('--voices')
INDEX = json.load(open(os.path.join(VOICES, 'index.json'))) if os.path.exists(os.path.join(VOICES, 'index.json')) else {}
CACHE = opt('--cache', '/tmp')
WIDTH = int(opt('--width', 1280))
I0, I1 = (int(x) for x in opt('--range').split(','))
SPOKEN = ('line', 'direction', 'super', 'sequence', 'insert')

# ------------------------------------------------------------------ the stretch's timeline


def envelope(path):
    w = wave.open(path)
    sr = w.getframerate()
    raw = w.readframes(w.getnframes())
    y = (np.frombuffer(raw, np.int16).astype(float) / 32768) if w.getsampwidth() == 2 else np.frombuffer(raw, np.int32).astype(float) / 2 ** 31
    hop = sr // FPS
    n = len(y) // hop
    e = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    return np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)


ITEMS = []
t = 1.2
for i in range(I0, I1 + 1):
    e = ELS[i]
    if e['kind'] not in SPOKEN:
        continue
    iid = 'e%03d' % i
    who = e['who'] if e['kind'] == 'line' else 'Narrator'
    if iid in INDEX:
        secs = INDEX[iid]['secs']
    else:
        w_ = wave.open(os.path.join(VOICES, iid + '.wav'))
        secs = round(w_.getnframes() / w_.getframerate(), 3)
    ITEMS.append({'i': i, 'id': iid, 'who': who, 'kind': e['kind'], 'text': e['text'], 'note': e.get('note', ''), 't': t, 'secs': secs,
                  'vo': e.get('vo', False), 'env': envelope(os.path.join(VOICES, iid + '.wav')) if who != 'Narrator' and not e.get('vo') else np.zeros(1)})
    t += secs + (0.55 if who != 'Narrator' else 0.45)
    if e['kind'] == 'sequence':
        t += 0.4
END = int(round((t + 1.5) * FPS))
END += END % 2
BY = {it['i']: it for it in ITEMS}


def T(i, frac=0.0, plus=0.0):
    it = BY[i]
    return it['t'] + it['secs'] * frac + plus


def env_at(who, f):
    for it in ITEMS:
        if it['who'] == who and not it['vo']:
            k = f - int(round(it['t'] * FPS))
            if 0 <= k < len(it['env']):
                return float(it['env'][k])
    return 0.0


def slug_before(i):
    for k in range(i, -1, -1):
        if ELS[k]['kind'] == 'slug':
            if 'CONTINUOUS' in ELS[k]['text']:
                continue
            return ELS[k]['text']
    return ''


TIME = slug_before(I0).split('–')[-1].strip()

# ------------------------------------------------------------------ who is where
# a station: ('seat', name) on a courtyard seat, or ('stand', spot, face) where face is a person or a point to turn to

SCALE = {'Socrates': 1.08, 'Julian': 1.06, 'Thrasymachus': 1.1, 'Polemarchus': 1.04, 'Glaucon': 1.05, 'Adeimantus': 1.03, 'Cephalus': 0.97,
         'Lysias': 1.0, 'Euthydemus': 0.98, 'Cleitophon': 1.0, 'Charmantides': 1.01}
TH = {'Socrates': 1.05, 'Julian': 0.86}
TH.update({w: athenians.SPECS[w]['th'] for w in athenians.SPECS})

AFTER_CEPHALUS = {      # Cephalus has gone to the altar; Polemarchus has his father's chair
    'Polemarchus': ('seat', 'cephalus'), 'Socrates': ('seat', 'arc70'), 'Glaucon': ('seat', 'arc45'), 'Adeimantus': ('seat', 'arc25'),
    'Euthydemus': ('seat', 'arc110'), 'Lysias': ('seat', 'arc135'), 'Charmantides': ('seat', 'arc158'), 'Cleitophon': ('seat', 'bench2'),
    'Thrasymachus': ('stand', 'mid', 'Socrates'), 'Julian': ('stand', 'column', 'mid'),
}
STATIONS = dict(AFTER_CEPHALUS)
INVISIBLE = {'Julian'}       # the ring turned inward

cast.SPLIT_SKIRT = True
cast.RING_ON = 'Julian'
stage.reset()
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 0, END - 1
src, IDLE = stage.load_rig(opt('--idle'), os.path.join(CACHE, 'idle.pkl'))
SET = courtyard.build()


def spot_xy(st):
    return V(courtyard.SEATS[st[1]][:2]) if st[0] == 'seat' else V(courtyard.SPOTS[st[1]][:2])


CH = {}
for who, st in STATIONS.items():
    if st[0] == 'seat':
        x, y, yaw = courtyard.SEATS[st[1]]
        f = V((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw))))
        loc = (x + f.x * 0.03, y + f.y * 0.03, 0)
    else:
        p = spot_xy(st)
        tgt = st[2]
        q = spot_xy(STATIONS[tgt]) if tgt in STATIONS else (V(courtyard.SPOTS[tgt][:2]) if tgt in courtyard.SPOTS else V(tgt))
        d = q - p
        yaw = math.degrees(math.atan2(d.x, -d.y))
        loc = (p.x, p.y, 0)
    arm, body, Hd = stage.cast_one(src, who, loc, math.radians(yaw), SCALE.get(who, 1.0))
    sk = bpy.data.objects.get(who + ' skirt')
    if sk and st[0] == 'seat':
        sk.hide_render = sk.hide_viewport = True        # seated: the clothed thighs show the chiton
    CH[who] = {'name': who, 'arm': arm, 'body': body, 'Hd': Hd, 'moves': [], 'leans': [], 'nods': [], 'still': [], 'expr': [],
               'yaw0': math.radians(yaw), 'standing': st[0] == 'stand', 'spot': V(loc)}
NAMES = list(CH)
rng = random.Random(23)

# ---- Julian with the ring turned inward: a glassy outline, no shadow
GHOST = []
for who in INVISIBLE & set(CH):
    body = CH[who]['body']
    body.visible_shadow = False
    for slot in body.material_slots:
        m = slot.material.copy()
        m.name = slot.material.name + ' ghost'
        slot.material = m
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
        elif hasattr(m, 'blend_method'):
            m.blend_method = 'BLEND'
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        shader = out.inputs['Surface'].links[0].from_socket
        vis = nt.nodes.new('ShaderNodeValue'); vis.name = vis.label = 'Visible'; vis.outputs[0].default_value = 0.0
        lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.25
        pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
        nt.links.new(lw.outputs['Facing'], pw.inputs[0])
        base = nt.nodes.new('ShaderNodeMath'); base.operation = 'MULTIPLY_ADD'; base.inputs[1].default_value = 0.85; base.inputs[2].default_value = 0.07
        nt.links.new(pw.outputs[0], base.inputs[0])
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = kit.hexc('#cfe9ff')
        k_ = nt.nodes.new('ShaderNodeMath'); k_.operation = 'MULTIPLY'; k_.inputs[1].default_value = 2.2
        nt.links.new(pw.outputs[0], k_.inputs[0]); nt.links.new(k_.outputs[0], em.inputs['Strength'])
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        edge = nt.nodes.new('ShaderNodeMixShader')          # transparent in the middle, a pale glow at the edges
        nt.links.new(base.outputs[0], edge.inputs['Fac'])
        nt.links.new(tr.outputs[0], edge.inputs[1]); nt.links.new(em.outputs[0], edge.inputs[2])
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(vis.outputs[0], mix.inputs['Fac'])
        nt.links.new(edge.outputs[0], mix.inputs[1]); nt.links.new(shader, mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
        if hasattr(m, 'use_transparency_overlap'):
            m.use_transparency_overlap = False      # only the outermost skin shows, not the pieces inside
        if hasattr(m, 'show_transparent_back'):
            m.show_transparent_back = False
        GHOST.append(m)


def F(time):
    return int(round(time * FPS))


# ------------------------------------------------------------------ posing helpers (as in film.py)

def posed(arm, bone, p_rest):
    return arm.pose.bones[bone].matrix @ arm.data.bones[bone].matrix_local.inverted() @ V(p_rest)


def sit(arm, lean=0.0, spread=0.1, thigh=-0.04, shin=(0, -0.1, -1.0), up=0.0):
    s = arm.scale.x
    h = kit.rest(arm, 'hip')
    kit.pose_move(arm, 'hip', (h.x, h.y, (courtyard.SEAT + SIT_UP) / s))
    if lean:
        kit.pose_turn(arm, 'hip', (1, 0, 0), -math.radians(lean))
    if up:
        kit.pose_turn(arm, 'spine_02', (1, 0, 0), math.radians(up))
    for sd, sg in (('l', 1), ('r', -1)):
        kit.pose_point(arm, 'upperleg_' + sd, 'lowerleg_' + sd, (sg * spread, -1, thigh))
        kit.pose_point(arm, 'lowerleg_' + sd, 'foot_' + sd, shin[sd] if isinstance(shin, dict) else shin)


def hand_to(arm, side, target, pole):
    return kit.reach(arm, ('upperarm_' + side, 'lowerarm_' + side, 'hand_' + side), target, pole)


PALM = 0.056
PALM_T = 0.030


def orient_hand(arm, side, fingers, palm):
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
    n = V(palm).normalized()
    f = V(fingers)
    f = (f - n * f.dot(n)).normalized()
    hand_to(arm, side, V(palm_c) - f * PALM, pole)
    orient_hand(arm, side, f, palm)


def rest_hand(who, side, along=0.62, lift=0.018, inward=0.2, out=0.0):
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


ARM_BONES = lambda sd: ['shoulder_' + sd, 'upperarm_' + sd, 'lowerarm_' + sd, 'hand_' + sd]
LID_OPEN = {'Socrates': -22, 'Julian': -30, 'Cephalus': -26}
YW = (0.1, 0.36, 0.52)
YW_SEATED = (0.0, 0.42, 0.56)
OUT = {'Socrates': 0.2, 'Julian': 0.17}     # how far a standing figure's hands hang out from the hips
HANG_CLEAR = float(opt('--hang', 0.06))     # the left hand further out, past the himation's hanging end
DRAPE_CLEAR = float(opt('--drape', 0.06))   # the right hand further out, past the himation across the right hip
REST_OUT = [float(v) for v in opt('--rest-out', '0.04,0.09').split(',')]      # seated hands out from the thighs: left, right (past the drape at the right hip)
SIT_UP = float(opt('--sit-up', 0.135))
SPREAD = float(opt('--spread', 0.15))
ALONG = [float(v) for v in opt('--along', '0.5,0.5').split(',')]
LEAN = [float(v) for v in opt('--lean', '6,11').split(',')]
LAP = float(opt('--lap', 0.0))      # the chiton over the lap, on which the hands rest

for who, c in CH.items():
    a = c['arm']
    if c['standing']:
        for sd, sg in (('l', 1), ('r', -1)):
            S = kit.joint(a, 'upperarm_' + sd)
            o = OUT.get(who, 0.2 * TH[who]) + ((HANG_CLEAR if sd == 'l' else DRAPE_CLEAR) * TH[who] if who in athenians.SPECS else 0.0)
            place_hand(a, sd, S + V((sg * o, -0.08, -0.55)), (sg * 0.15, -0.18, -1.0), (-sg, 0.2, 0.0), S + V((sg * 0.35, 0.35, -0.25)))
    else:
        r_ = random.Random(hash(who) % 1000)
        sit(a, lean=r_.uniform(LEAN[0], LEAN[1]), spread=SPREAD, thigh=-0.05, shin=(0, r_.uniform(-0.4, -0.2), -1.0), up=r_.uniform(3, 6))
        for sd in 'lr':
            rest_hand(who, sd, ALONG[0 if sd == 'l' else 1], lift=0.018 + LAP * TH[who], inward=-0.2, out=REST_OUT[0 if sd == 'l' else 1] * TH[who])

for who, c in CH.items():
    c['base'] = kit.snapshot(c['arm'])
    c['axz'] = {b: kit.local_axis(c['arm'], b, (0, 0, 1)) for b in ('spine_01', 'spine_02', 'spine_03', 'neck', 'head')}
    c['axx'] = {b: kit.local_axis(c['arm'], b, (1, 0, 0)) for b in ('spine_01', 'spine_02', 'spine_03', 'neck', 'head', 'lid_l', 'lid_r')}

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
PHASE = {who: (A0 + (k * 97) % (A1 - A0), 0.85 + 0.05 * (k % 4)) for k, who in enumerate(sorted(CH))}
SWAY = float(opt('--sway', 0.9))         # how much of the recorded idle a seated body takes (spine)
AMOUNT = {'spine_01': SWAY, 'spine_02': SWAY, 'spine_03': SWAY, 'neck': 1.3, 'head': 1.3}
for sd in 'lr':
    AMOUNT.update({'shoulder_' + sd: 0.25, 'upperarm_' + sd: 0.125, 'lowerarm_' + sd: 0.1, 'hand_' + sd: 0.1})

# a standing figure stands where the idle stance puts its hips on its mark
for who, c in CH.items():
    if not c['standing']:
        continue
    a = c['arm']
    x0 = PHASE[who][0]
    for b in LEGS + BODY:
        a.pose.bones[b].rotation_quaternion = isample(b, x0)
    for b in ('hip', 'root'):
        a.pose.bones[b].location = iloc(b, x0)
    kit.refresh()
    off = kit.joint(a, 'hip') - kit.rest(a, 'hip')
    c['idle_off'] = V((off.x, off.y, 0)) * a.scale.x
    for pb in a.pose.bones:
        q, l, s_ = c['base'][pb.name]
        pb.rotation_quaternion, pb.location = q, l
    kit.refresh()

# ------------------------------------------------------------------ moves (arm poses blended over time)


def move(who, keys):
    CH[who]['moves'].append(sorted(keys, key=lambda k: k[0]))


def move_at(keys, time):
    if time <= keys[0][0] or time >= keys[-1][0]:
        return 0.0, None
    for (ta, pa), (tb, pb) in zip(keys, keys[1:]):
        if ta <= time <= tb:
            k = ease((time - ta) / max(1e-6, tb - ta))
            if pa and pb:
                out = {}
                for b in pa:
                    if b.startswith('_follow_'):
                        out[b] = pa[b]
                    elif b.startswith('_plant_'):
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


LAB = []


def capture2(ch, fn, name='', sides='lr', planted=False, want=None, follow=None, elbow=None):
    arm = ch['arm']
    before = kit.snapshot(arm)
    fn()
    g = {b: arm.pose.bones[b].rotation_quaternion.copy() for sd in sides for b in ARM_BONES(sd)}
    if planted:
        for sd in sides:
            H = arm.pose.bones['hand_' + sd].matrix.copy()
            if want and sd in want:
                H.translation = want[sd]
            g['_plant_' + sd] = (H, elbow[sd] if elbow and sd in elbow else arm.pose.bones['lowerarm_' + sd].matrix.translation.copy())
            if follow is not None:
                g['_follow_' + sd] = follow
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
        arm.pose.bones[b].location = l
    kit.refresh()
    LAB.append((ch['name'], name, g))
    return g


def capture(ch, side, fn, name='', planted=False, want=None, follow=None, elbow=None):
    return capture2(ch, fn, name, side, planted, {side: want} if want is not None else None, follow, {side: elbow} if elbow is not None else None)


def idle_x(who, time):
    ph, speed = PHASE[who]
    return pingpong(ph + time * 30 * speed, A0, A1)


def explain_pose(who, side, var, big=False):
    """An open hand raised in front of the chest, palm up and in, as people hold a hand when they make a point."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    standing = c['standing']
    fwd = (-0.36 if standing else -0.33) - (0.08 if big else 0)
    down = (-0.22 if standing else -0.16) + (0.1 if big else 0)
    p = S + V((sg * (0.02 + 0.06 * var + (0.1 if big else 0)), fwd + 0.04 * var, down + 0.07 * var))
    f = V((-sg * 0.35, -1.0, 0.25 + 0.15 * var))
    n = V((-sg * 0.45, -0.1, 0.9))
    pole = S + V((sg * 0.6, 0.15, -0.45)) if standing else S + V((sg * 0.5, -0.45, -0.5))
    return capture(c, side, lambda: place_hand(arm, side, p, f, n, pole), 'explain %s %.0f' % (side, var))


def waypoint(who, side):
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    hp, kn = kit.joint(arm, 'upperleg_' + side), kit.joint(arm, 'lowerleg_' + side)
    p = kn.lerp(hp, 0.15) + V((sg * 0.07, -0.12, 0.2))
    return capture(c, side, lambda: place_hand(arm, side, p, V((-sg * 0.2, -1.0, 0.1)), V((0, 0, -1)), S + V((sg * 0.9, 0.0, -0.2))), 'way %s' % side)


BUSY = {}        # who -> [(t0, t1)] when the hands are taken by a gesture of their own


def busy(who, t0, t1):
    BUSY.setdefault(who, []).append((t0, t1))


def is_busy(who, t0, t1):
    return any(a < t1 and t0 < b for a, b in BUSY.get(who, []))


def explain(who, t0, t1, big=False, both=False):
    """Talking gestures through a long line: the free hand rises, makes a point or two, and settles."""
    c = CH[who]
    sides = ['r', 'l']
    tt, k = t0 + 1.0, 0
    while tt + 2.6 < t1:
        dur = rng.uniform(2.4, 3.4)
        if is_busy(who, tt, tt + dur):
            tt += 1.0
            continue
        for side in (sides if both and k % 2 == 0 else [sides[k % 2]]):
            A, B = explain_pose(who, side, 0.0, big), explain_pose(who, side, 1.0, big)
            if c['standing']:
                move(who, [(tt, None), (tt + 0.5, A), (tt + dur * 0.5, B), (tt + dur - 0.5, A), (tt + dur, None)])
            else:
                Wp = waypoint(who, side)
                move(who, [(tt, None), (tt + 0.3, Wp), (tt + 0.65, A), (tt + dur * 0.5, B), (tt + dur - 0.6, A), (tt + dur - 0.3, Wp), (tt + dur, None)])
        busy(who, tt, tt + dur)
        tt += dur + rng.uniform(1.6 if big else 2.6, 3.2 if big else 4.6)
        k += 1


def point_at(who, side, world, t0, t1):
    """Reach toward a point in the room, as far as the arm goes, and hold it."""
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S = kit.joint(arm, 'upperarm_' + side)
    d = kit.to_arm(arm, world) - S
    p = S + d.normalized() * min(d.length, 0.56)
    dn = (p - S).normalized()
    A = capture(c, side, lambda: place_hand(arm, side, p, dn, V((0, 0, -1)), S + V((sg * 0.6, 0.2, -0.3))), 'point %s' % side)
    if c['standing']:
        move(who, [(t0, None), (t0 + 0.5, A), (t1 - 0.5, A), (t1, None)])
    else:
        Wp = waypoint(who, side)
        move(who, [(t0, None), (t0 + 0.3, Wp), (t0 + 0.7, A), (t1 - 0.6, A), (t1 - 0.3, Wp), (t1, None)])
    busy(who, t0, t1)


def spread_hands(who, t0, t1):
    """Both hands open out to the sides, palms up: 'what do you want of me?'"""
    c = CH[who]; arm = c['arm']

    def fn():
        for sd, sg in (('l', 1), ('r', -1)):
            S = kit.joint(arm, 'upperarm_' + sd)
            place_hand(arm, sd, S + V((sg * 0.3, -0.3, -0.25 if c['standing'] else -0.18)), V((sg * 0.6, -0.8, 0.0)), V((0, 0, 1)), S + V((sg * 0.6, 0.2, -0.4)))
    P = capture2(c, fn, 'spread hands')
    move(who, [(t0, None), (t0 + 0.6, P), (t1 - 0.5, P), (t1, None)])
    busy(who, t0, t1)


# ------------------------------------------------------------------ gaze

def head_w(who):
    c = CH[who]
    return kit.to_world(c['arm'], posed(c['arm'], 'head', c['Hd'].C))


for who in CH:
    CH[who]['head_w'] = head_w(who)


def target_point(who, name):
    if name in CH:
        return CH[name]['head_w']
    if name == 'down':
        return CH[who]['head_w'] + V((math.sin(CH[who]['yaw0']), -math.cos(CH[who]['yaw0']), 0)) * 0.6 + V((0, 0, -0.7))
    if name == 'mid':
        return V((courtyard.MID.x, courtyard.MID.y, 1.2))
    return V(name)


def angles(who, name, yaw_extra=0.0):
    c = CH[who]
    hw = c['head_w']
    d = Matrix.Rotation(-(c['yaw0'] + yaw_extra), 3, 'Z') @ (target_point(who, name) - hw)
    yaw = math.atan2(d.x, -d.y)
    pitch = math.atan2(d.z, math.hypot(d.x, d.y))
    lim = math.radians(62)
    return max(-lim, min(lim, yaw)), max(-0.55, min(0.35, pitch))


def mentioned(text):
    out = []
    for n in CH:
        if n.lower() in text.lower():
            out.append(n)
    return out


def addressee(it, prev):
    for n in mentioned(it['text'][:80]):
        if n != it['who']:
            return n
    if it['who'] != 'Socrates':
        return 'Socrates' if 'Socrates' in CH else prev
    return prev if prev and prev != 'Socrates' and prev in CH else ('Thrasymachus' if 'Thrasymachus' in CH else NAMES[0])


AT_MID = [w for w, st in STATIONS.items() if st[0] == 'stand' and st[1] == 'mid']
LOOKS = {}
for who in CH:
    st = STATIONS[who]
    first = st[2] if (st[0] == 'stand' and st[2] in CH) else (AT_MID[0] if AT_MID and AT_MID[0] != who else 'Socrates')
    LOOKS[who] = [(0.0, first if first != who else 'mid')]
prev = None
for it in ITEMS:
    t0, t1, who = it['t'], it['t'] + it['secs'], it['who']
    if who == 'Narrator' or it['vo']:
        for w in mentioned(it['text']):
            for o in CH:
                if o != w and o != 'Julian' and rng.random() < 0.7:
                    LOOKS[o].append((t0 + rng.uniform(0.3, 1.2), w))
        continue
    to = addressee(it, prev)
    LOOKS[who].append((t0 - 0.2, to))
    if it['secs'] > 8:          # the speaker takes in the others now and then
        others = [n for n in NAMES if n not in (who, to, 'Julian')]
        for tt in np.arange(t0 + 5.0, t1 - 3.0, 6.0):
            LOOKS[who].append((tt, rng.choice(others)))
            LOOKS[who].append((tt + 2.0, to))
    for w in CH:
        if w == who:
            continue
        LOOKS[w].append((t0 + 0.25 + 0.3 * rng.random(), who))
        if w != 'Julian' and it['secs'] > 8 and rng.random() < 0.4:
            g = t0 + rng.uniform(3.0, it['secs'] - 2.5)
            LOOKS[w].append((g, rng.choice([n for n in NAMES if n != w])))
            LOOKS[w].append((g + rng.uniform(1.2, 2.2), who))
    prev = who
for w in LOOKS:
    LOOKS[w].sort(key=lambda k: k[0])


def gaze(who, time, yaw_extra=0.0):
    ks = LOOKS[who]
    cur = angles(who, ks[0][1], yaw_extra)
    for (t0, name) in ks[1:]:
        if time < t0:
            break
        nxt = angles(who, name, yaw_extra)
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
    o = LID_OPEN.get(who, -34)
    for b in BLINK[who]:
        d = f - b
        if 0 <= d <= 5:
            k = (0.6, 1.0, 1.0, 0.6, 0.25, 0.0)[d]
            return o + (72 - o) * k
    return o


# ------------------------------------------------------------------ faces

PRESETS = {
    'tired': dict(up=-0.002, tilt=0.22, smile=-0.3, lid=16, head=3),
    'worry': dict(up=0.004, tilt=0.42, knit=0.003, smile=-0.4, lid=-4),
    'tense': dict(up=0.003, tilt=0.4, knit=0.004, smile=-0.45, tight=0.8, lid=-6),
    'frown': dict(up=-0.006, tilt=-0.38, knit=0.005, smile=-0.5, tight=0.4, lid=6),
    'clench': dict(up=-0.008, tilt=-0.5, knit=0.006, smile=-0.6, tight=1.0, lid=9, wide=0.004),
    'rage': dict(up=-0.009, tilt=-0.55, knit=0.007, smile=-0.7, lid=-8, wide=0.008, open=0.4),
    'grave': dict(up=-0.003, tilt=0.18, knit=0.003, smile=-0.4, tight=0.3, lid=7, head=2),
    'sorrow': dict(up=0.003, tilt=0.6, knit=0.003, smile=-0.85, lid=20, head=7),
    'raise': dict(up=0.011, lid=-9),
    'curious': dict(up_l=0.013, up_r=0.001, tilt=-0.08, smile=0.12, lid=-5),
    'wonder': dict(up=0.014, lid=-20, smile=-0.1, open=0.35),
    'alarm': dict(up=0.014, tilt=0.3, lid=-22, smile=-0.35, open=0.3),
    'hope': dict(up=0.007, tilt=0.12, smile=0.55, lid=0, open=0.1),
    'smile': dict(up=0.008, tilt=-0.05, smile=1.0, wide=0.01, lid=5, open=0.45),
    'smug': dict(up_l=0.009, up_r=-0.003, tilt=-0.15, smile=0.55, wide=0.004, lid=10),
    'warm': dict(up=0.005, smile=0.65, wide=0.006, lid=3, open=0.15),
    'determined': dict(up=-0.004, tilt=-0.22, knit=0.003, smile=0.15, tight=0.45, lid=4),
    'calm': dict(smile=0.35, wide=0.003, lid=4),
    'serious': dict(up=-0.002, tilt=-0.12, knit=0.002, smile=-0.18, tight=0.2),
}
NOTE_EXPR = [('roaring', 'rage', 1.0), ('quiver', 'alarm', 1.0), ('curtly', 'frown', 1.0), ('amused', 'warm', 1.0), ('delighted', 'smile', 1.0),
             ('smil', 'smile', 0.9), ('laugh', 'smile', 1.0), ('sighing', 'grave', 0.9), ('hesitat', 'serious', 0.8), ('mildly', 'calm', 1.0),
             ('quietly', 'calm', 0.7), ('gently', 'warm', 0.8), ('eagerly', 'warm', 1.0), ('fading', 'grave', 1.0), ('whisper', 'serious', 0.8),
             ('earnest', 'wonder', 1.0), ('aloud', 'determined', 0.8), ('interposing', 'determined', 0.8), ('pause', 'grave', 0.8),
             ('spreading', 'raise', 0.8), ('settling', 'calm', 0.6), ('slowly', 'grave', 0.6)]
TEMPER = {'Thrasymachus': ('frown', 0.6), 'Socrates': ('calm', 0.35), 'Glaucon': ('determined', 0.4), 'Adeimantus': ('serious', 0.5),
          'Cephalus': ('warm', 0.6), 'Polemarchus': ('serious', 0.3)}


def expr(who, t0, t1, name, k=1.0):
    if who in CH:
        CH[who]['expr'].append((t0, t1, PRESETS[name], k))


# ------------------------------------------------------------------ what the stage directions say bodies do
# (a phrase of a direction or a line, and what follows from it)


def cue_shrink(it):
    t0 = it['t']
    for w, c in CH.items():
        if w in ('Thrasymachus', 'Julian'):
            continue
        c['leans'].append((t0 + 0.4, t0 + 22.0, -7.0 if not c['standing'] else -4.0))
        expr(w, t0 + 0.4, t0 + 20.0, 'worry', 0.8)
    # Julian flinches behind his column
    tj = t0 + it['secs'] * 0.72
    CH['Julian']['leans'].append((tj, tj + 3.0, -11.0))
    expr('Julian', tj - 0.1, tj + 4.0, 'alarm', 1.0)


def cue_roar(it):
    t0, t1 = it['t'], it['t'] + it['secs']
    point_at('Thrasymachus', 'r', CH['Socrates']['head_w'], t0 + 0.3, t0 + 3.6)
    spread_hands('Thrasymachus', t1 - 7.5, t1 - 3.2)
    CH['Thrasymachus']['leans'].append((t0, t0 + 4.0, 9.0))


def cue_praise(it):
    t1 = it['t'] + it['secs']
    spread_hands('Thrasymachus', t1 - 3.8, t1 + 0.4)
    expr('Thrasymachus', t1 - 3.8, t1 + 0.8, 'smug', 1.0)


def cue_quiver(it):
    expr('Socrates', it['t'], it['t'] + it['secs'], 'worry', 0.6)


CUES = [('The young men shrink back', cue_shrink), ('What folly, Socrates', cue_roar), ('why do you not praise me', cue_praise),
        ("don't be hard upon us", cue_quiver)]
for it in ITEMS:
    for key, fn in CUES:
        if key in it['text']:
            fn(it)


for it in ITEMS:
    who, t0, t1 = it['who'], it['t'], it['t'] + it['secs']
    if who not in CH or it['vo']:
        continue
    note = it['note'].lower()
    hit = False
    for key, name, k in NOTE_EXPR:
        if key in note:
            expr(who, t0 - 0.2, t1 + 0.4, name, k)
            hit = True
            break
    if not hit and who in TEMPER:
        expr(who, t0, t1, TEMPER[who][0], TEMPER[who][1])
    if it['text'].rstrip().endswith('?'):
        expr(who, t1 - 1.4, t1 + 0.6, 'raise', 0.7)
    if it['secs'] > 5.5 and not is_busy(who, t0, t1):
        explain(who, t0, t1, big=who == 'Thrasymachus', both=who == 'Thrasymachus')

# speakers lift their brows at the start of a phrase now and then; listeners nod now and then
for it in ITEMS:
    who = it['who']
    if who not in CH or it['env'].size < 10:
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
    if it['secs'] > 7 and who != 'Thrasymachus':
        for w in CH:
            if w != who and w != 'Julian' and rng.random() < 0.5:
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
LIFT = {'Socrates': 0.011, 'Julian': 0.009}

# ------------------------------------------------------------------ keys

KEYS = {who: {} for who in CH}


def put(who, path, vals):
    for i, v in enumerate(vals):
        KEYS[who].setdefault((path, i), []).append(v)


ARMSET = set(ARM_BONES('l') + ARM_BONES('r'))
ARM_IDLE_STANDING = 0.12
REL = {}
for who, c in CH.items():
    bones = c['arm'].data.bones
    REL[who] = {b.name: ((b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy(), b.parent.name if b.parent else None) for b in bones}
    pbs = c['arm'].pose.bones
    c['plant'] = {sd: (pbs['hand_' + sd].matrix.copy(), pbs['lowerarm_' + sd].matrix.translation.copy()) for sd in 'lr'}


def fk(who, local, bone, memo):
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
ELBOW_FOLLOW = float(opt('--elbow-follow', 0.85))


def plant(who, side, local, target=None, follow=None):
    """Arm rotations that put the hand on a fixed spot (its resting place, or a gesture's target); the elbow keeps its
    place relative to the chest."""
    c = CH[who]
    Hm, elbow = target or c['plant'][side]
    memo = {}
    elbow = elbow.lerp(fk(who, local, 'spine_03', memo) @ SP0[who].inverted() @ elbow, ELBOW_FOLLOW if follow is None else follow)
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


def frame_pose(who, f):
    c = CH[who]
    time = f / FPS
    x = idle_x(who, time)
    standing = c['standing']
    talk = env_at(who, f)
    talk_s = float(np.mean([env_at(who, g) for g in range(f - 3, f + 4)]))
    yaw, pitch = gaze(who, time)
    ex = expr_at(who, time)
    yw = YW if standing else YW_SEATED
    lean = sum(d * window(t0, t1, 0.5)(time) for (t0, t1, d) in c['leans'])
    nod = sum(math.radians(a_) * math.sin(2 * math.pi * 0.9 * (time - t0)) * window(t0, t1, 0.4)(time) for (t0, t1, a_) in c['nods'])
    out = {}
    local = {}
    planted = {}
    for b in BODY + (LEGS if standing else []):
        d = MEAN[b].inverted() @ isample(b, x)
        sd_ = b[-1] if b.startswith(('upperarm_', 'lowerarm_', 'hand_')) else None
        if not standing and sd_:
            if sd_ not in planted:
                planted[sd_] = plant(who, sd_, local)
        if standing:
            if b in ARMSET:
                q = c['base'][b][0] @ scaled(d, ARM_IDLE_STANDING)
            elif b in ('neck', 'head'):         # the idle's own head turn taken out, so the gaze decides where the face points
                q = c['base'][b][0] @ d
            else:
                q = isample(b, x)
        elif sd_:
            q = planted[sd_][b]
        else:
            q = c['base'][b][0] @ scaled(d, AMOUNT.get(b, 0.8))
        for keys in c['moves']:
            w, pose = move_at(keys, time)
            if w > 0 and pose and b in pose:
                if sd_ and ('_plant_' + sd_) in pose:
                    tgt = plant(who, sd_, local, pose['_plant_' + sd_], pose.get('_follow_' + sd_)) if b == 'upperarm_' + sd_ or ('_solved', sd_) not in planted else None
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
            q = q @ Quaternion(c['axz'][b], yaw * yw[0])
        elif b == 'neck':
            q = q @ Quaternion(c['axz'][b], yaw * yw[1]) @ Quaternion(c['axx'][b], -pitch * 0.35)
        elif b == 'head':
            bob = math.radians(4.0) * (talk_s - 0.25) if talk_s > 0.02 else 0.0
            bow = math.radians(ex.get('head', 0.0))
            q = q @ Quaternion(c['axz'][b], yaw * yw[2]) @ Quaternion(c['axx'][b], -pitch * 0.5 + bob + nod + bow)
        local[b] = q
        out['pose.bones["%s"].rotation_quaternion' % b] = tuple(q)
    if standing:
        for b in ('hip', 'root'):
            out['pose.bones["%s"].location' % b] = tuple(iloc(b, x))
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
        v = REST3[who]['mouth_' + sd] @ V((sg * wide, 0.004 * max(sm, 0.0), sm * LIFT.get(who, 0.01)))
        out['pose.bones["mouth_%s"].location' % sd] = tuple(v)
    tight = min(1.0, ex.get('tight', 0.0))
    opn = (0.45 + 1.8 * talk + ex.get('open', 0.0)) * (1 - 0.6 * tight)
    out['pose.bones["mouth"].scale'] = (1.0, max(0.18, opn), 1.0)
    return out


def apply_pose(who, vals):
    arm = CH[who]['arm']
    for path, v in vals.items():
        b = path.split('"')[1]
        setattr(arm.pose.bones[b], path.split('.')[-1], v)


STEP = 2
FRAMES = list(range(0, END, STEP))
CHECK = opt('--check')
if CHECK:
    import clearance
    for c in CH.values():
        for m in c['body'].modifiers:
            m.show_viewport = False
    figs = {w: clearance.Figure(c['arm'], c['body']) for w, c in CH.items()}
    if opt('--lab'):
        # the base poses, then every gesture pose on its own
        for who, c in CH.items():
            for pb in c['arm'].pose.bones:
                pb.rotation_quaternion = c['base'][pb.name][0]
        kit.refresh()
        m = clearance.measure(figs, (), courtyard.boxes())
        for who in CH:
            worst = sorted(((v, k) for k, v in m.items() if k[0] == who and not k[2].startswith('seat')), key=lambda z: z[0])[:3]
            print('LAB %-12s %-16s' % (who, 'base'), '  '.join('%s/%s %+.3f' % (k[1], k[2], v) for v, k in worst))
        if opt('--debug'):
            w_, a_, b_ = opt('--debug').split(',')
            if opt('--frame'):
                apply_pose(w_, frame_pose(w_, int(opt('--frame'))))
                kit.refresh()
            fg = figs[w_]
            fg.pose()
            X = fg.pts(a_)
            sd = fg.signed(b_, X)
            i = int(np.argmin(sd))
            dd, j = fg.tree(b_).query(X[i])
            vi = int(fg.part[b_][j])
            me = CH[w_]['body'].data
            mats = {me.materials[p_.material_index].name for p_ in me.polygons if vi in p_.vertices}
            arm_ = CH[w_]['arm']
            print('DEBUG %s %s point(arm) %s signed %.3f nearest %s normal %s mats %s' % (w_, a_, tuple(round(v, 3) for v in (arm_.matrix_world.inverted() @ V(X[i]))),
                  sd[i], tuple(round(v, 3) for v in (arm_.matrix_world.inverted() @ V(fg.P[vi]))), tuple(round(v, 2) for v in fg.N[vi]), mats))
        seen = set()
        for who, name, g in LAB:
            if (who, name.split(' ')[0]) in seen:
                continue
            seen.add((who, name.split(' ')[0]))
            c = CH[who]
            for pb in c['arm'].pose.bones:
                pb.rotation_quaternion = c['base'][pb.name][0]
            for b, q in g.items():
                if not b.startswith('_'):
                    c['arm'].pose.bones[b].rotation_quaternion = q
            kit.refresh()
            m = clearance.measure({who: figs[who]}, (), ())
            worst = sorted(((v, k) for k, v in m.items()), key=lambda z: z[0])[:3]
            print('LAB %-12s %-16s' % (who, name), '  '.join('%s/%s %+.3f' % (k[1], k[2], v) for v, k in worst))
        sys.exit(0)
    bad = {}
    step = int(CHECK)
    for f in range(0, END, step):
        for who in CH:
            apply_pose(who, frame_pose(who, f))
        kit.refresh()
        for k, v in clearance.measure(figs, (), courtyard.boxes()).items():
            if v < 0.003:
                bad.setdefault(k, []).append((f, v))
    for k, fs in sorted(bad.items(), key=lambda kv: min(v for _, v in kv[1])):
        fw = min(fs, key=lambda z: z[1])[0]
        print('CLASH %-12s %-8s %-16s frames %5d-%5d worst %+.3f m at %d (%d samples)' % (k[0], k[1], k[2], fs[0][0], fs[-1][0], min(v for _, v in fs), fw, len(fs)))
    print('CLASHES', len(bad))
    sys.exit(0)

for f in FRAMES:
    for who in CH:
        for path, v in frame_pose(who, f).items():
            put(who, path, v)
# standing figures: their mark, less the idle stance's own offset
for who, c in CH.items():
    if c['standing']:
        off = Matrix.Rotation(c['yaw0'], 3, 'Z') @ c['idle_off']
        c['arm'].location = c['spot'] - off


def simplify(x, y, tol):
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
    return 0.0015


TOTAL = [0, 0]


def write_keys(idb, keys, frames):
    act = bpy.data.actions.new(idb.name + ' action')
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
        fc.keyframe_points.foreach_set('interpolation', [1] * len(vals))
        fc.update()


for who, c in CH.items():
    write_keys(c['arm'], KEYS[who], np.array(FRAMES, float))
print('keys kept %d of %d' % (TOTAL[1], TOTAL[0]))

# ------------------------------------------------------------------ light: the time of day the scene heading gives


def sky(colour_top, colour_horizon, strength):
    w = bpy.data.worlds.new('Sky')
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.5, kit.hexc(colour_horizon)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.75, kit.hexc(colour_top)
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    sc.world = w


LIGHTS = {}
if 'AFTERNOON' in TIME or 'DAY' in TIME:
    sky('#5f93cf', '#f2d6a8', 0.75)
    LIGHTS['sun'] = stage.light('Sun', 'SUN', (5.0, -3.0, 6.5), 3.4, (1.0, 0.84, 0.64), 0.03, to=(0, 0, 0))
    stage.light('Sky fill', 'AREA', (0.5, -2.0, 6.0), 380, (0.72, 0.84, 1.0), 9.0, to=(0, 0.3, 0), shadow=False)
    stage.light('Bounce', 'AREA', (0.0, 0.8, 0.3), 90, (1.0, 0.85, 0.65), 6.0, to=(0, 0.8, 2.0), shadow=False)
    for fl in SET['flames']:
        fl.hide_render = True
else:
    sky('#0d1630', '#24304f', 0.35)
    stage.light('Moon', 'SUN', (-3, 4, 7), 0.25, (0.6, 0.72, 1.0), 0.02, to=(0, 0, 0))
    for k, (x, y, z) in enumerate(courtyard.LAMPS):
        LIGHTS['lamp%d' % k] = stage.light('Lamp %d' % k, 'POINT', (x + 0.135, y, z + 0.12), 120, (1.0, 0.68, 0.36), 0.08)
stage.light('Altar glow', 'POINT', (courtyard.ALTAR[0], courtyard.ALTAR[1], 1.1), 18, (1.0, 0.5, 0.2), 0.3, shadow=False)

# ------------------------------------------------------------------ cameras and cuts

for who in CH:
    CH[who]['head_w'] = head_w(who)
CAMS = {'wide': stage.camera('Cam wide', (0.75, -3.95, 1.75), (0.55, 1.1, 0.95), 20),
        'reverse': stage.camera('Cam reverse', (1.25, 3.3, 1.95), (-0.25, -0.6, 1.0), 24),
        'side': stage.camera('Cam side', (-2.1, -3.9, 1.8), (1.0, 1.5, 1.0), 24)}


def facing(who):
    c = CH[who]
    return V((math.sin(c['yaw0']), -math.cos(c['yaw0']), 0))


for who, c in CH.items():
    h = c['head_w']
    f = facing(who)
    r = V((-f.y, f.x, 0)) * -1           # the figure's right
    dist = 1.6 if not c['standing'] else 1.75
    pos = h + f * dist + r * 0.26 + V((0, 0, 0.0))
    CAMS['close ' + who] = stage.camera('Cam ' + who, tuple(pos), tuple(h + V((0, 0, -0.14))), 36)
# Julian at his column, seen from among the company
if 'Julian' in CH:
    hj = CH['Julian']['head_w']
    CAMS['close Julian'].location = hj + V((-2.1, 0.9, -0.1))
    CAMS['close Julian'].rotation_euler = (hj + V((0, 0, -0.25)) - CAMS['close Julian'].location).to_track_quat('-Z', 'Y').to_euler()
    CAMS['close Julian'].data.lens = 30


def two_shot(speaker, listener):
    """Over the listener's shoulder onto the speaker."""
    key = 'ots %s %s' % (speaker, listener)
    if key not in CAMS:
        hs, hl = CH[speaker]['head_w'], CH[listener]['head_w']
        d = (hl - hs); d.z = 0; d.normalize()
        side = V((-d.y, d.x, 0))
        if CH[listener]['standing']:
            pos = hl + d * 0.95 + side * 0.5 + V((0, 0, 0.22))
        else:           # over a seated listener: from higher and further back, clear of the hair
            pos = hl + d * 1.25 + side * 0.62 + V((0, 0, 0.62))
        CAMS[key] = stage.camera('Cam ' + key, tuple(pos), tuple(hs + V((0, 0, -0.22))), 30)
    return key


CUTS = []


def cut(time, name):
    if CUTS and CUTS[-1][1] == name:
        return
    if CUTS and time - CUTS[-1][0] < 1.6:
        CUTS[-1] = (CUTS[-1][0], name)
        return
    CUTS.append((time, name))


prev = None
for it in ITEMS:
    t0, t1, who = it['t'], it['t'] + it['secs'], it['who']
    start = 0.0 if it is ITEMS[0] else t0 - 0.25
    if who == 'Narrator' or it['vo']:
        # narration about someone cuts to them as their name is read; it opens on the whole company
        low = it['text'].lower()
        marks = sorted((low.find(n.lower()) / max(1, len(low)), n) for n in mentioned(it['text']))
        if not marks or marks[0][0] > 0.12 or it['kind'] in ('sequence', 'insert'):
            cut(start, 'wide')
        for frac, n in marks:
            if it['kind'] in ('sequence', 'insert'):
                break
            cut(start if frac <= 0.12 else t0 + it['secs'] * frac - 0.2, 'close ' + n)
        continue
    me = 'close ' + who
    cut(start, me)
    to = addressee(it, prev)
    if it['secs'] > 8.5:
        options = ['close ' + to, two_shot(who, to) if to in CH else 'wide', 'wide' if who != 'Thrasymachus' else 'reverse', 'side']
        k = 0
        for tt in np.arange(t0 + 4.5, t1 - 3.0, 7.5):
            cut(tt, options[k % len(options)])
            cut(tt + 3.0, me)
            k += 1
    prev = who
CUTS.sort()
for tm, name in CUTS:
    mk = sc.timeline_markers.new(name, frame=F(tm))
    mk.camera = CAMS[name]
sc.camera = CAMS[CUTS[0][1]]
stage.eevee(sc, WIDTH, WIDTH * 9 // 16, int(opt('--samples', 8)))

plan = {'range': [I0, I1], 'frames': [0, END - 1], 'fps': FPS, 'seconds': round(END / FPS, 2),
        'cues': [{'id': it['id'], 't': round(it['t'], 4)} for it in ITEMS if it['id']], 'cuts': CUTS,
        'items': [(it['i'], it['who'], round(it['t'], 2), round(it['secs'], 2)) for it in ITEMS]}
print('range', I0, I1, 'frames', END, 'seconds %.1f' % (END / FPS), 'items', len(ITEMS), 'cuts', len(CUTS))
if opt('--plan'):
    json.dump(plan, open(opt('--plan'), 'w'), indent=1)
if opt('--save'):
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=opt('--save'), compress=True)
if opt('--probe'):
    v_ = [float(x) for x in opt('--probe').split(',')]
    CAMS = {'probe': stage.camera('Cam probe', tuple(v_[:3]), tuple(v_[3:6]), v_[6])}
camshots = opt('--cams', n=2)
if camshots:
    fr, out_ = camshots
    sc.timeline_markers.clear()
    sc.frame_set(int(fr))
    for name, cam in CAMS.items():
        sc.camera = cam
        sc.render.filepath = out_.replace('.png', '_%s.png' % name.replace(' ', '_'))
        bpy.ops.render.render(write_still=True)
still = opt('--still', n=2)
if still:
    for fr in still[0].split(','):
        sc.frame_set(int(fr))
        sc.render.filepath = still[1].replace('.png', '_%s.png' % fr)
        bpy.ops.render.render(write_still=True)
