"""The Ring of Gyges IV: a sequence (or a stretch) of the script as a 3D cartoon scene, for the render server.

    python athens.py -- --script script.json --voices DIR --idle IDLE.fbx --walk WALK.fbx (--seq N | --range A,B)
                        [--cache DIR] [--save OUT.blend] [--plan OUT.json] [--still F,F OUT.png] [--cams F OUT.png]
                        [--check N [--lab 1]] [--tracks 1] [--width 1280] [--samples 8]

Elements of the script are timed from their voice recordings (eNNN.wav and index.json in the voices folder). Who is
where, and when people rise, walk, sit or sit on the floor, comes from toon/staging4.py, written from the script's
stage directions. Bodies move with recorded motion (an idle, and a walk); heads turn to whoever speaks; mouths follow
the voices; brows, mouth corners and lids act the notes; Julian, wearing the ring turned inward, is a glassy outline
that casts no shadow until he turns it outward. Several sets can share one sequence: each stands at its own place in
the world (the courtyard at the origin, the lounge and the Piraeus street far off), and the cameras cut between them.
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
import staging4

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
STARTS = [i for i, e in enumerate(ELS) if e['kind'] == 'sequence']
if opt('--seq'):
    SEQ = int(opt('--seq'))
    I0 = STARTS[SEQ - 1]
    I1 = (STARTS[SEQ] - 1) if SEQ < len(STARTS) else len(ELS) - 1
else:
    I0, I1 = (int(x) for x in opt('--range').split(','))
    SEQ = max(k + 1 for k, s in enumerate(STARTS) if s <= I0)
SPOKEN = ('line', 'direction', 'super', 'sequence', 'insert')
GAP_AFTER = {'CUT TO BLACK.': 1.8, 'DISSOLVE TO:': 0.9, 'CUT TO:': 0.4, 'FADE OUT.': 3.0, 'BACK TO SCENE.': 0.3, 'FADE IN:': 0.6}

# ------------------------------------------------------------------ the timeline


def envelope(path):
    w = wave.open(path)
    sr = w.getframerate()
    raw = w.readframes(w.getnframes())
    y = np.frombuffer(raw, np.int16).astype(float) / 32768
    hop = sr // FPS
    n = len(y) // hop
    e = np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))
    return np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)


ITEMS = []
TRANS = []
t = 1.2
for i in range(I0, I1 + 1):
    e = ELS[i]
    if e['kind'] == 'transition':
        TRANS.append((t, e['text'], i))
        t += GAP_AFTER.get(e['text'], 0.3)
        continue
    if e['kind'] not in SPOKEN or e.get('cut') or e['text'].startswith('From here on, whenever the bezel'):     # cut, or a note for the animators
        continue
    iid = 'e%03d' % i
    who = e['who'] if e['kind'] == 'line' else 'Narrator'
    if iid in INDEX:
        secs = INDEX[iid]['secs']
    else:
        w_ = wave.open(os.path.join(VOICES, iid + '.wav'))
        secs = round(w_.getnframes() / w_.getframerate(), 3)
    vo = e.get('vo', False)
    ITEMS.append({'i': i, 'id': iid, 'who': who, 'kind': e['kind'], 'text': e['text'], 'note': e.get('note', ''), 't': t, 'secs': secs,
                  'vo': vo, 'env': envelope(os.path.join(VOICES, iid + '.wav')) if who != 'Narrator' and not vo else np.zeros(1)})
    t += secs + (0.55 if who != 'Narrator' else 0.45)
    if e['kind'] == 'sequence':
        t += 0.4
END = int(round((t + float(opt('--tail', 1.5))) * FPS))
END += END % 2
BY = {it['i']: it for it in ITEMS}


def env_at(who, f):
    for it in ITEMS:
        if it['who'] == who and not it['vo']:
            k = f - int(round(it['t'] * FPS))
            if 0 <= k < len(it['env']):
                return float(it['env'][k])
    return 0.0


def F(time):
    return int(round(time * FPS))


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def window(t0, t1, ramp=0.5):
    return lambda tt: ease((tt - t0) / ramp) * ease((t1 - tt) / ramp)


# ------------------------------------------------------------------ staging: who is where, and what happens


class Stage:
    """What staging4.py writes into: places, scenes, looks, gestures and effects, all timed by the script."""

    def __init__(self):
        self.places = {}          # who -> [(t, station, mode)]
        self.scenes = []          # [(t, set, time of day)]
        self.looks = []           # (who, t0, t1 or None, target)
        self.exprs = []           # (who, t0, t1, preset, k)
        self.gests = []           # (name, who, t0, t1, kw)
        self.leans = []           # (who, t0, t1, deg)
        self.nods = []
        self.lamps = []           # (t, which, on, dur)
        self.vis = []             # (who, t, visible, dur)
        self.shim = []            # (who, t0, t1) shimmer then fade out
        self.cams = []            # (t, camera name)
        self.sleeps = []          # (who, t0, t1)
        self.blush = []           # (who, t0, t1)
        self.props = []           # (kind, t, kw)
        self.half = []            # (who, t0, t1, amount): rise part way and sit again
        self.turns = []           # (who, t0, t1, degrees): a seated body turns on its chair
        self.quiet = set()        # people who never gesture

    def it(self, snippet, nth=1):
        k = 0
        for it in ITEMS:
            if snippet in it['text'] or (snippet.startswith('~') and snippet[1:] in it['note']):
                k += 1
                if k == nth:
                    return it
        return None

    def has(self, snippet):
        return self.it(snippet) is not None

    def t(self, snippet, frac=0.0, plus=0.0, nth=1, word=None):
        it = self.it(snippet, nth)
        if it is None:
            return None
        if word:
            pos = it['text'].find(word)
            frac = max(0.0, pos / max(1, len(it['text'])))
        return it['t'] + it['secs'] * frac + plus

    def end(self, snippet, plus=0.0, nth=1):
        it = self.it(snippet, nth)
        return None if it is None else it['t'] + it['secs'] + plus

    def place(self, who, t, station, mode='cut'):
        if t is not None:
            self.places.setdefault(who, []).append((t, station, mode))

    def scene(self, t, set_, tod):
        if t is not None:
            self.scenes.append((t, set_, tod))

    def look(self, who, t0, target, t1=None):
        if t0 is not None:
            self.looks.append((who, t0, t1, target))

    def expr(self, who, t0, t1, preset, k=1.0):
        if t0 is not None and t1 is not None:
            self.exprs.append((who, t0, t1, preset, k))

    def gesture(self, name, who, t0, t1=None, **kw):
        if t0 is not None:
            self.gests.append((name, who, t0, t1 if t1 is not None else t0 + 3.0, kw))

    def lean(self, who, t0, t1, deg):
        if t0 is not None and t1 is not None:
            self.leans.append((who, t0, t1, deg))

    def nod(self, who, t0, t1, deg=5.0):
        if t0 is not None:
            self.nods.append((who, t0, t1, deg))

    def lamp(self, t, which, on, dur=0.6):
        if t is not None:
            self.lamps.append((t, which, on, dur))

    def visible(self, who, t, on, dur=1.0):
        if t is not None:
            self.vis.append((who, t, on, dur))

    def vanish(self, who, t0, t1):
        if t0 is not None:
            self.shim.append((who, t0, t1))

    def cam(self, t, name):
        if t is not None:
            self.cams.append((t, name))

    def sleep(self, who, t0, t1=1e9):
        if t0 is not None:
            self.sleeps.append((who, t0, t1))

    def redden(self, who, t0, t1):
        if t0 is not None:
            self.blush.append((who, t0, t1))

    def prop(self, kind, t, **kw):
        if t is not None:
            self.props.append((kind, t, kw))

    def half_rise(self, who, t0, t1, amount=0.35):
        if t0 is not None:
            self.half.append((who, t0, t1, amount))

    def turn(self, who, t0, t1, deg):
        if t0 is not None:
            self.turns.append((who, t0, t1, deg))


S = Stage()
staging4.stage(SEQ, S, I0, I1)
S.scenes.sort(key=lambda s: s[0])
if not S.scenes:
    S.scenes = [(0.0, 'court', 'LATE AFTERNOON')]


def scene_at(time):
    cur = S.scenes[0]
    for sc_ in S.scenes:
        if sc_[0] <= time + 1e-6:
            cur = sc_
    return cur


# ------------------------------------------------------------------ build

cast.SPLIT_SKIRT = True
cast.RING_ON = 'Julian'
stage.reset()
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 0, END - 1
src, IDLE = stage.load_rig(opt('--idle'), os.path.join(CACHE, 'idle.pkl'))
WALK = stage.read_motion(opt('--walk'), os.path.join(CACHE, 'walk.pkl')) if opt('--walk') else None

OFFSET = {'court': V((0, 0, 0)), 'lounge': V((0, 90, 0)), 'piraeus': V((0, -90, 0))}
SETS = {}
used_sets = {s_[1] for s_ in S.scenes}


def set_module(name):
    if name == 'court':
        return courtyard
    if name == 'lounge':
        import lounge4
        return lounge4
    import piraeus
    return piraeus


def build_set(name):
    before = set(bpy.data.objects)
    info = set_module(name).build()
    for ob in set(bpy.data.objects) - before:
        if ob.parent is None:
            ob.location = ob.location + OFFSET[name]
    return info


for name in ('court', 'lounge', 'piraeus'):
    if name in used_sets:
        SETS[name] = build_set(name)

SCALE = {'Socrates': 1.08, 'Julian': 1.06, 'Thrasymachus': 1.1, 'Polemarchus': 1.04, 'Glaucon': 1.05, 'Adeimantus': 1.03, 'Cephalus': 0.97,
         'Lysias': 1.0, 'Euthydemus': 0.98, 'Cleitophon': 1.0, 'Charmantides': 1.01, 'Aria': 0.93, 'Cleon': 1.0}
SCALE.update(getattr(athenians, 'SCALES', {}))
TH = {'Socrates': 1.05, 'Julian': 0.86, 'Aria': 1.06, 'Cleon': 0.98}
TH.update({w: athenians.SPECS[w]['th'] for w in athenians.SPECS})


def spot_of(name, set_):
    """A named spot or seat in a set, or an (x, y) pair in that set, as world (x, y)."""
    m = set_module(set_)
    if isinstance(name, (tuple, list)):
        return V((name[0], name[1])) + OFFSET[set_].xy
    if name in m.SEATS:
        return V(m.SEATS[name][:2]) + OFFSET[set_].xy
    if name in m.SPOTS:
        return V(m.SPOTS[name][:2]) + OFFSET[set_].xy
    return V(m.LOOKS[name][:2]) + OFFSET[set_].xy


def station_set(st):
    """Stations: ('seat', seat[, set]), ('stand', spot, face[, set]), ('floor', spot, face[, set]), ('away',)."""
    if st[0] == 'away':
        return None
    if st[0] == 'seat':
        return st[2] if len(st) > 2 else 'court'
    return st[3] if len(st) > 3 else 'court'


def mark_xy(st):
    if st[0] == 'seat':
        return spot_of(st[1], station_set(st))
    return spot_of(st[1], station_set(st))


# ------------------------------------------------------------------ casting

for who, ks in S.places.items():
    ks.sort(key=lambda k: k[0])
CH = {}
for who in S.places:
    arm, body, Hd = stage.cast_one(src, who, (0, 0, 0), 0.0, SCALE.get(who, 1.0))
    CH[who] = {'name': who, 'arm': arm, 'body': body, 'Hd': Hd, 'moves': [], 'leans': [], 'nods': [], 'expr': [],
               'skirt': bpy.data.objects.get(who + ' skirt'), 'scale': SCALE.get(who, 1.0)}
NAMES = list(CH)
rng = random.Random(23)

# ---- Julian with the ring: a glassy outline while it is turned inward (Visible 0); a shimmer and a fade when he goes
FX = {}
RING_MAT = {}
for who in ('Julian',):
    if who not in CH:
        continue
    FX[who] = []
    body = CH[who]['body']
    for slot in body.material_slots:
        m = slot.material.copy()
        m.name = slot.material.name + ' fx'
        slot.material = m
        if hasattr(m, 'surface_render_method'):
            m.surface_render_method = 'BLENDED'
        if hasattr(m, 'use_transparency_overlap'):
            m.use_transparency_overlap = False
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        shader = out.inputs['Surface'].links[0].from_socket
        vis = nt.nodes.new('ShaderNodeValue'); vis.name = vis.label = 'Visible'; vis.outputs[0].default_value = 1.0
        fade = nt.nodes.new('ShaderNodeValue'); fade.name = fade.label = 'Fade'; fade.outputs[0].default_value = 1.0
        shim = nt.nodes.new('ShaderNodeValue'); shim.name = shim.label = 'Shimmer'; shim.outputs[0].default_value = 0.0
        lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.25
        pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
        nt.links.new(lw.outputs['Facing'], pw.inputs[0])
        base_ = nt.nodes.new('ShaderNodeMath'); base_.operation = 'MULTIPLY_ADD'; base_.inputs[1].default_value = 0.85; base_.inputs[2].default_value = 0.07
        nt.links.new(pw.outputs[0], base_.inputs[0])
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = kit.hexc('#cfe9ff')
        k_ = nt.nodes.new('ShaderNodeMath'); k_.operation = 'MULTIPLY'; k_.inputs[1].default_value = 2.2
        nt.links.new(pw.outputs[0], k_.inputs[0]); nt.links.new(k_.outputs[0], em.inputs['Strength'])
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        edge = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(base_.outputs[0], edge.inputs['Fac'])
        nt.links.new(tr.outputs[0], edge.inputs[1]); nt.links.new(em.outputs[0], edge.inputs[2])
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 26.0; nz.noise_dimensions = '4D'
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        sp = nt.nodes.new('ShaderNodeMath'); sp.operation = 'POWER'; sp.inputs[1].default_value = 6.0
        nt.links.new(nz.outputs['Fac'], sp.inputs[0])
        sm = nt.nodes.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'
        nt.links.new(sp.outputs[0], sm.inputs[0]); nt.links.new(shim.outputs[0], sm.inputs[1])
        sm2 = nt.nodes.new('ShaderNodeMath'); sm2.operation = 'MULTIPLY'; sm2.inputs[1].default_value = 60.0
        nt.links.new(sm.outputs[0], sm2.inputs[0])
        em2 = nt.nodes.new('ShaderNodeEmission'); em2.inputs['Color'].default_value = kit.hexc('#fff1c8')
        nt.links.new(sm2.outputs[0], em2.inputs['Strength'])
        add = nt.nodes.new('ShaderNodeAddShader')
        nt.links.new(shader, add.inputs[0]); nt.links.new(em2.outputs[0], add.inputs[1])
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(vis.outputs[0], mix.inputs['Fac'])
        nt.links.new(edge.outputs[0], mix.inputs[1]); nt.links.new(add.outputs[0], mix.inputs[2])
        tr2 = nt.nodes.new('ShaderNodeBsdfTransparent')
        mix2 = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(fade.outputs[0], mix2.inputs['Fac'])
        nt.links.new(tr2.outputs[0], mix2.inputs[1]); nt.links.new(mix.outputs[0], mix2.inputs[2])
        nt.links.new(mix2.outputs[0], out.inputs['Surface'])
        if slot.material.name.startswith('Ring brass'):
            # the ring itself can be taken off (before he picks it up): RingOn 0 hides it
            ron = nt.nodes.new('ShaderNodeValue'); ron.name = ron.label = 'RingOn'; ron.outputs[0].default_value = 1.0
            tr3 = nt.nodes.new('ShaderNodeBsdfTransparent')
            mix3 = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(ron.outputs[0], mix3.inputs['Fac'])
            nt.links.new(tr3.outputs[0], mix3.inputs[1]); nt.links.new(mix2.outputs[0], mix3.inputs[2])
            nt.links.new(mix3.outputs[0], out.inputs['Surface'])
            RING_MAT[who] = m
        FX[who].append(m)


def fx_key(who, frame, **vals):
    for m in FX.get(who, []):
        for name, v in vals.items():
            n = m.node_tree.nodes[name]
            n.outputs[0].default_value = v
            n.outputs[0].keyframe_insert('default_value', frame=frame)


# ------------------------------------------------------------------ posing helpers (as in film.py)

def posed(arm, bone, p_rest):
    return arm.pose.bones[bone].matrix @ arm.data.bones[bone].matrix_local.inverted() @ V(p_rest)


SIT_UP = float(opt('--sit-up', 0.135))
FRONT = float(opt('--front', 0.55))
BELLY_OUT = {'Thrasymachus': 0.06, 'Cephalus': 0.04}   # extra room for the hands' way past a big belly       # how far in front of a seat people stand to sit down or after rising
SPREAD = float(opt('--spread', 0.15))
ALONG = [float(v) for v in opt('--along', '0.5,0.5').split(',')]
LEAN = [float(v) for v in opt('--lean', '6,11').split(',')]
REST_OUT = [float(v) for v in opt('--rest-out', '0.04,0.09').split(',')]
HANG_CLEAR = float(opt('--hang', 0.06))
DRAPE_CLEAR = float(opt('--drape', 0.06))
OUT = {'Socrates': 0.2, 'Julian': 0.17, 'Aria': 0.17, 'Cleon': 0.18}
PALM = 0.056
PALM_T = 0.030


def sit(arm, height, lean=0.0, spread=0.1, thigh=-0.04, shin=(0, -0.1, -1.0), up=0.0):
    s = arm.scale.x
    h = kit.rest(arm, 'hip')
    kit.pose_move(arm, 'hip', (h.x, h.y, (height + SIT_UP) / s))
    if lean:
        kit.pose_turn(arm, 'hip', (1, 0, 0), -math.radians(lean))
    if up:
        kit.pose_turn(arm, 'spine_02', (1, 0, 0), math.radians(up))
    for sd, sg in (('l', 1), ('r', -1)):
        kit.pose_point(arm, 'upperleg_' + sd, 'lowerleg_' + sd, (sg * spread, -1, thigh))
        kit.pose_point(arm, 'lowerleg_' + sd, 'foot_' + sd, shin[sd] if isinstance(shin, dict) else shin)


def sit_floor(arm):
    """Sitting on the stone floor, back to a column, knees drawn up."""
    s = arm.scale.x
    h = kit.rest(arm, 'hip')
    kit.pose_move(arm, 'hip', (h.x, h.y + 0.03 / s, 0.13 / s))
    kit.pose_turn(arm, 'hip', (1, 0, 0), math.radians(12))
    kit.pose_turn(arm, 'spine_02', (1, 0, 0), -math.radians(6))
    for sd, sg in (('l', 1), ('r', -1)):
        kit.pose_point(arm, 'upperleg_' + sd, 'lowerleg_' + sd, (sg * 0.32, -0.62, 0.72))
        kit.pose_point(arm, 'lowerleg_' + sd, 'foot_' + sd, (sg * 0.05, -0.32, -1.0))


def hand_to(arm, side, target, pole):
    return kit.reach(arm, ('upperarm_' + side, 'lowerarm_' + side, 'hand_' + side), target, pole)


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
    r = (0.098 + (0.08 - 0.098) * along) * TH.get(who, 1.0)
    p = hp.lerp(kn, along) + n * (r + PALM_T + lift) + V((sg * out, 0, 0))
    f = (ax + V((-sg * inward, 0, 0))).normalized()
    S_ = kit.joint(arm, 'upperarm_' + side)
    place_hand(arm, side, p, f, -n, S_ + V((sg * 1.0, 0.0, -0.1)))


def rest_on_knee(who, side):
    arm = CH[who]['arm']
    sg = 1 if side == 'l' else -1
    kn = kit.joint(arm, 'lowerleg_' + side)
    S_ = kit.joint(arm, 'upperarm_' + side)
    p = kn + V((sg * 0.02, -0.02, 0.1 * TH.get(who, 1.0) + PALM_T))
    place_hand(arm, side, p, V((-sg * 0.3, -1.0, -0.35)), V((0, 0.1, -1.0)), S_ + V((sg * 0.9, -0.2, -0.2)))


ARM_BONES = lambda sd: ['shoulder_' + sd, 'upperarm_' + sd, 'lowerarm_' + sd, 'hand_' + sd]
LID_OPEN = {'Socrates': -22, 'Julian': -30, 'Cephalus': -26, 'Cleon': -38, 'Aria': -48}
YW = (0.1, 0.36, 0.52)
YW_SEATED = (0.0, 0.42, 0.56)


def set_base(who, kind):
    c = CH[who]
    for pb in c['arm'].pose.bones:
        q, l, s_ = c['states'][kind]['base'][pb.name]
        pb.rotation_quaternion, pb.location, pb.scale = q, l, s_
    kit.refresh()


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    kit.refresh()


def seat_height(set_):
    return set_module(set_).SEAT


KINDS_NEEDED = {}
for who, ks in S.places.items():
    need = set()
    for (_, st, _m) in ks:
        if st[0] == 'seat':
            need.add('seat:%s' % station_set(st))
        elif st[0] in ('stand', 'floor'):
            need.add(st[0])
        if len(ks) > 1 and any(m_ == 'move' for (_t, _s, m_) in ks):
            need.add('stand')
    if any(g_[0] == who for g_ in S.half):
        need.add('stand')
    if not need:
        need.add('stand')
    KINDS_NEEDED[who] = need

for who, c in CH.items():
    a = c['arm']
    c['states'] = {}
    for kind in sorted(KINDS_NEEDED[who]):
        reset_pose(a)
        if kind == 'stand':
            th = TH.get(who, 1.0)
            for sd, sg in (('l', 1), ('r', -1)):
                S_ = kit.joint(a, 'upperarm_' + sd)
                o = OUT.get(who, 0.2 * th) + ((HANG_CLEAR if sd == 'l' else DRAPE_CLEAR) * th if who in athenians.SPECS else 0.0)
                place_hand(a, sd, S_ + V((sg * o, -0.08, -0.55)), (sg * 0.15, -0.18, -1.0), (-sg, 0.2, 0.0), S_ + V((sg * 0.35, 0.35, -0.25)))
        elif kind.startswith('seat'):
            r_ = random.Random(hash(who) % 1000)
            sit(a, seat_height(kind.split(':')[1]) + max(0.0, TH.get(who, 1.0) - 1.0) * 0.2, lean=r_.uniform(LEAN[0], LEAN[1]), spread=SPREAD, thigh=-0.05, shin=(0, r_.uniform(-0.4, -0.2), -1.0),
                up=r_.uniform(3, 6))
            belly = athenians.SPECS[who]['belly'] * athenians.SPECS[who]['th'] if who in athenians.SPECS else 0.18
            more = max(0.0, belly - 0.19) * 2.6           # a big belly pushes the resting hands further along the thighs
            for sd in 'lr':
                rest_hand(who, sd, ALONG[0 if sd == 'l' else 1] + more, lift=0.018, inward=-0.2, out=(REST_OUT[0 if sd == 'l' else 1] + more * 0.35) * TH.get(who, 1.0))
        elif kind == 'floor':
            sit_floor(a)
            for sd in 'lr':
                rest_on_knee(who, sd)
        st = {'base': kit.snapshot(a)}
        st['axz'] = {b: kit.local_axis(a, b, (0, 0, 1)) for b in ('spine_01', 'spine_02', 'spine_03', 'neck', 'head')}
        st['axx'] = {b: kit.local_axis(a, b, (1, 0, 0)) for b in ('spine_01', 'spine_02', 'spine_03', 'neck', 'head', 'lid_l', 'lid_r')}
        st['head'] = posed(a, 'head', c['Hd'].C)
        pbs = a.pose.bones
        st['plant'] = {sd: (pbs['hand_' + sd].matrix.copy(), pbs['lowerarm_' + sd].matrix.translation.copy()) for sd in 'lr'}
        c['states'][kind] = st

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


SPEED = 1.0
if WALK:
    WR = prep(WALK)
    WN = WALK['n']
    LEGB = [p + sd for p in ('upperleg_', 'lowerleg_', 'foot_') for sd in 'lr'] + ['hip']
    best = None
    for i0 in range(0, WN - 30):
        for j0 in range(i0 + 28, min(WN, i0 + 42)):
            d = sum(1 - abs(WR[b][i0].dot(WR[b][j0])) for b in LEGB if b in WR)
            if best is None or d < best[0]:
                best = (d, i0, j0)
    W0, W1 = best[1], best[2]
    STRIDE = (V(WALK['loc']['root'][W1]) - V(WALK['loc']['root'][W0])).length
    WALK_PLAY = 0.8
    SPEED = STRIDE / ((W1 - W0) / 30.0) * WALK_PLAY


def wsample(b, x):
    span = W1 - W0
    y = W0 + (x % span)
    i = int(math.floor(y))
    j = i + 1 if i + 1 <= W1 else W0 + 1
    return WR[b][i].slerp(WR[b][min(j, WN - 1)], y - i)


def wloc(b, x):
    span = W1 - W0
    y = W0 + (x % span)
    i = int(math.floor(y))
    return V(WALK['loc'][b][i]).lerp(V(WALK['loc'][b][min(i + 1, WN - 1)]), y - i)


WMEAN = {}
if WALK:
    for b in [x for sd in 'lr' for x in ARM_BONES(sd)]:
        if b in WR:
            m = Quaternion((0, 0, 0, 0))
            for q in WR[b][W0:W1]:
                m = Quaternion((m.w + q.w, m.x + q.x, m.y + q.y, m.z + q.z))
            WMEAN[b] = m.normalized()


def scaled(q, k):
    if abs(k - 1) < 1e-6:
        return q
    ax, ang = q.to_axis_angle()
    if ang > math.pi:
        ang -= 2 * math.pi
    return Quaternion(ax, ang * k)


BODY = ['spine_01', 'spine_02', 'spine_03', 'neck', 'head'] + ARM_BONES('l') + ARM_BONES('r')
LEGS = ['root', 'hip'] + [p + sd for p in ('upperleg_', 'lowerleg_', 'foot_', 'ball_') for sd in 'lr']
ARMSET = set(ARM_BONES('l') + ARM_BONES('r'))
PHASE = {who: (A0 + (k * 97) % (A1 - A0), 0.85 + 0.05 * (k % 4)) for k, who in enumerate(sorted(CH))}
SWAY = float(opt('--sway', 0.9))
AMOUNT = {'spine_01': SWAY, 'spine_02': SWAY, 'spine_03': SWAY, 'neck': 1.3, 'head': 1.3}
for sd in 'lr':
    AMOUNT.update({'shoulder_' + sd: 0.25, 'upperarm_' + sd: 0.125, 'lowerarm_' + sd: 0.1, 'hand_' + sd: 0.1})


def idle_x(who, time):
    ph, speed = PHASE[who]
    return pingpong(ph + time * 30 * speed, A0, A1)


# where the idle stance puts a standing figure's hips (taken off its mark, so it stands on it)
for who, c in CH.items():
    c['idle_off'] = V((0, 0, 0))
    if 'stand' not in c['states']:
        continue
    a = c['arm']
    set_base(who, 'stand')
    x0 = PHASE[who][0]
    for b in LEGS + BODY:
        if b not in ARMSET:
            a.pose.bones[b].rotation_quaternion = isample(b, x0)
    for b in ('hip', 'root'):
        a.pose.bones[b].location = iloc(b, x0)
    kit.refresh()
    off = kit.joint(a, 'hip') - kit.rest(a, 'hip')
    c['idle_off'] = V((off.x, off.y, 0)) * a.scale.x
    c['states']['stand']['head'] = posed(a, 'head', c['Hd'].C)
    set_base(who, 'stand')

# ------------------------------------------------------------------ tracks: where each person is, and how they get there


def yaw_between(a, b):
    return (b - a + math.pi) % (2 * math.pi) - math.pi


def held_xy(who, time):
    ks = S.places[who]
    cur = ks[0]
    for k in ks:
        if time is not None and k[0] <= time:
            cur = k
    return mark_xy(cur[1]) if cur[1][0] != 'away' else V((0, 0))


def resolve(who, st, time=None):
    """(world xy of the person's mark, yaw radians, kind) for a station."""
    if st[0] == 'away':
        return V((0, 0)), 0.0, 'away'
    set_ = station_set(st)
    if st[0] == 'seat':
        m = set_module(set_)
        x, y, yaw = m.SEATS[st[1]]
        f = V((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw))))
        return V((x, y)) + OFFSET[set_].xy + f * 0.03, math.radians(yaw), 'seat:' + set_
    p = spot_of(st[1], set_)
    face = st[2] if len(st) > 2 else 0.0
    if isinstance(face, (int, float)):
        yaw = math.radians(face)
    else:
        if isinstance(face, str) and face in S.places and face != who:
            q = held_xy(face, time)
        else:
            q = spot_of(face, set_)
        d = q - p
        yaw = math.atan2(d.x, -d.y)
    return p, yaw, st[0]


TRACK = {}
for who, ks in S.places.items():
    segs = []
    p, y, k = resolve(who, ks[0][1], ks[0][0])
    cur = {'xy': p, 'yaw': y, 'kind': k}
    segs.append({'t0': -1e9, 't1': 1e9, 'type': 'hold', **cur})
    for (tk, st, mode) in ks[1:]:
        p, y, k = resolve(who, st, tk)
        segs[-1]['t1'] = tk
        if mode == 'cut' or cur['kind'] == 'away' or k == 'away':
            cur = {'xy': p, 'yaw': y, 'kind': k}
            segs.append({'t0': tk, 't1': 1e9, 'type': 'hold', **cur})
            continue
        tt = tk
        if cur['kind'].startswith('seat'):
            f = V((math.sin(cur['yaw']), -math.cos(cur['yaw'])))
            front = cur['xy'] + f * FRONT
            segs.append({'t0': tt, 't1': tt + 1.1, 'type': 'blend', 'ka': cur['kind'], 'kb': 'stand', 'xya': cur['xy'], 'xyb': front, 'yaw': cur['yaw']})
            tt += 1.1
            cur = {'xy': front, 'yaw': cur['yaw'], 'kind': 'stand'}
        elif cur['kind'] == 'floor':
            segs.append({'t0': tt, 't1': tt + 1.4, 'type': 'blend', 'ka': 'floor', 'kb': 'stand', 'xya': cur['xy'], 'xyb': cur['xy'], 'yaw': cur['yaw']})
            tt += 1.4
            cur = {'xy': cur['xy'], 'yaw': cur['yaw'], 'kind': 'stand'}
        goal = p
        if k.startswith('seat'):
            goal = p + V((math.sin(y), -math.cos(y))) * FRONT
        d = goal - cur['xy']
        if d.length > 0.15 and WALK:
            yw = math.atan2(d.x, -d.y)
            if abs(yaw_between(cur['yaw'], yw)) > 0.2:
                segs.append({'t0': tt, 't1': tt + 0.6, 'type': 'turn', 'xy': cur['xy'], 'ya': cur['yaw'], 'yb': yw})
                tt += 0.6
            dur = d.length / SPEED
            segs.append({'t0': tt, 't1': tt + dur, 'type': 'walk', 'xya': cur['xy'], 'xyb': goal, 'yaw': yw})
            tt += dur
            cur = {'xy': goal, 'yaw': yw, 'kind': 'stand'}
        elif d.length > 0.01:
            cur['xy'] = goal
        if abs(yaw_between(cur['yaw'], y)) > 0.05:
            segs.append({'t0': tt, 't1': tt + 0.6, 'type': 'turn', 'xy': cur['xy'], 'ya': cur['yaw'], 'yb': y})
            tt += 0.6
            cur['yaw'] = y
        if k.startswith('seat'):
            segs.append({'t0': tt, 't1': tt + 1.1, 'type': 'blend', 'ka': 'stand', 'kb': k, 'xya': cur['xy'], 'xyb': p, 'yaw': y})
            tt += 1.1
        elif k == 'floor':
            segs.append({'t0': tt, 't1': tt + 1.5, 'type': 'blend', 'ka': 'stand', 'kb': 'floor', 'xya': cur['xy'], 'xyb': p, 'yaw': y})
            tt += 1.5
        cur = {'xy': p, 'yaw': y, 'kind': k}
        segs.append({'t0': tt, 't1': 1e9, 'type': 'hold', **cur})
    TRACK[who] = segs
    if opt('--tracks'):
        for s_ in segs:
            print('TRACK %-12s %-6s %7.1f-%7.1f %s' % (who, s_['type'], max(-1, s_['t0']), min(s_['t1'], 9999),
                                                   s_.get('kind', s_.get('ka', '')) + ('>' + s_['kb'] if 'kb' in s_ else '')))


def seg_at(who, time):
    for s_ in TRACK[who]:
        if s_['t0'] <= time < s_['t1']:
            return s_
    return TRACK[who][-1]


def kind_at(who, time):
    s_ = seg_at(who, time)
    if s_['type'] == 'hold':
        return s_['kind']
    if s_['type'] == 'blend':
        return s_['kb'] if (time - s_['t0']) / (s_['t1'] - s_['t0']) > 0.5 else s_['ka']
    return 'stand'


def any_state(who):
    return 'stand' if 'stand' in CH[who]['states'] else sorted(CH[who]['states'])[0]


def obj_loc_for(who, kind, xy, yaw):
    if kind == 'stand':
        off = Matrix.Rotation(yaw, 3, 'Z') @ CH[who]['idle_off']
        return V((xy.x - off.x, xy.y - off.y, 0))
    return V((xy.x, xy.y, 0))


def turned(who, time):
    return sum(math.radians(d) * ease((time - a_) / 1.2) * (1 - ease((time - b_) / 1.2)) for (w_, a_, b_, d) in S.turns if w_ == who)


def where(who, time):
    """(object location, yaw, kind a, kind b, blend, walk mix, walk distance) at a time."""
    s_ = seg_at(who, time)
    k = (time - s_['t0']) / max(1e-6, s_['t1'] - s_['t0'])
    if s_['type'] == 'hold':
        if s_['kind'] == 'away':
            return V((0, 0, -200)), 0.0, any_state(who), None, 0.0, 0.0, 0.0
        yaw = s_['yaw'] + turned(who, time)
        return obj_loc_for(who, s_['kind'], s_['xy'], s_['yaw']), yaw, s_['kind'], None, 0.0, 0.0, 0.0
    if s_['type'] == 'blend':
        e_ = ease(k)
        la = obj_loc_for(who, s_['ka'], s_['xya'], s_['yaw'])
        lb = obj_loc_for(who, s_['kb'], s_['xyb'], s_['yaw'])
        # the hips travel ahead of the legs: forward before rising, back over the seat before sitting down
        return la.lerp(lb, ease(min(1.0, k * 1.5))), s_['yaw'], s_['ka'], s_['kb'], e_, 0.0, 0.0
    if s_['type'] == 'turn':
        y_ = s_['ya'] + yaw_between(s_['ya'], s_['yb']) * ease(k)
        return obj_loc_for(who, 'stand', s_['xy'], y_), y_, 'stand', None, 0.0, 0.0, 0.0
    ramp = ease((time - s_['t0']) / 0.4) * ease((s_['t1'] - time) / 0.4)
    xy = s_['xya'].lerp(s_['xyb'], k)
    return V((xy.x, xy.y, 0)), s_['yaw'], 'stand', None, 0.0, ramp, (time - s_['t0']) * SPEED


def moving(who, t0, t1):
    return any(s_['type'] != 'hold' and s_['t0'] < t1 and t0 < s_['t1'] for s_ in TRACK[who])


def station_at(who, time):
    ks = S.places[who]
    cur = ks[0][1]
    for k in ks:
        if k[0] <= time:
            cur = k[1]
    return cur


def hidden(who, time):
    """Whether someone is kept out of sight altogether (S.prop('hide', t, who=, on=True/False))."""
    state = False
    for kind, t_, kw in sorted(S.props, key=lambda p: p[1]):
        if kind == 'hide' and kw.get('who') == who and t_ <= time:
            state = kw.get('on', True)
    return state


def here(time):
    """The people in the set being shown at a time (not those kept hidden)."""
    set_ = scene_at(time)[1]
    return [w for w in CH if station_at(w, time)[0] != 'away' and station_set(station_at(w, time)) == set_ and not hidden(w, time)]


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
                    if b.startswith('_follow_') or b == '_kind':
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
    g['_kind'] = ch.get('_kind')
    for b, (q, l, s_) in before.items():
        arm.pose.bones[b].rotation_quaternion = q
        arm.pose.bones[b].location = l
    kit.refresh()
    LAB.append((ch['name'], name, g))
    return g


def capture(ch, side, fn, name='', planted=False, want=None, follow=None, elbow=None):
    return capture2(ch, fn, name, side, planted, {side: want} if want is not None else None, follow, {side: elbow} if elbow is not None else None)


def in_state(who, time):
    """Pose the armature in the base of the state a person is in at a time (gestures are made from it)."""
    k = kind_at(who, time)
    if k == 'away' or k not in CH[who]['states']:
        k = any_state(who)
    set_base(who, k)
    CH[who]['_kind'] = k
    return k


BUSY = {}


def busy(who, t0, t1):
    BUSY.setdefault(who, []).append((t0, t1))


def is_busy(who, t0, t1):
    return any(a < t1 and t0 < b for a, b in BUSY.get(who, []))


def explain_pose(who, side, var, big=False):
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S_ = kit.joint(arm, 'upperarm_' + side)
    standing = c['_kind'] == 'stand'
    fwd = (-0.36 if standing else -0.33) - (0.08 if big else 0)
    down = (-0.22 if standing else -0.16) + (0.1 if big else 0)
    p = S_ + V((sg * (0.02 + 0.06 * var + (0.1 if big else 0)), fwd + 0.04 * var, down + 0.07 * var))
    f = V((-sg * 0.35, -1.0, 0.25 + 0.15 * var))
    n = V((-sg * 0.45, -0.1, 0.9))
    pole = S_ + V((sg * 0.6, 0.15, -0.45)) if standing else S_ + V((sg * 0.5, -0.45, -0.5))
    return capture(c, side, lambda: place_hand(arm, side, p, f, n, pole), 'explain %s %.0f' % (side, var))


def waypoint(who, side):
    c = CH[who]; arm = c['arm']
    sg = 1 if side == 'l' else -1
    S_ = kit.joint(arm, 'upperarm_' + side)
    hp, kn = kit.joint(arm, 'upperleg_' + side), kit.joint(arm, 'lowerleg_' + side)
    p = kn.lerp(hp, 0.15) + V((sg * (0.07 + BELLY_OUT.get(who, 0.03)), -0.12, 0.2))
    return capture(c, side, lambda: place_hand(arm, side, p, V((-sg * 0.2, -1.0, 0.1)), V((0, 0, -1)), S_ + V((sg * 0.9, 0.0, -0.2))), 'way %s' % side)


def explain(who, t0, t1, big=False, both=False):
    c = CH[who]
    sides = ['r', 'l']
    tt, k = t0 + 1.0, 0
    while tt + 2.6 < t1:
        dur = rng.uniform(2.4, 3.4)
        kind = kind_at(who, tt)
        ok = kind == 'stand' or kind.startswith('seat')
        if is_busy(who, tt, tt + dur) or moving(who, tt - 0.3, tt + dur + 0.3) or not ok or kind_at(who, tt + dur) != kind:
            tt += 1.0
            continue
        in_state(who, tt)
        for side in (sides if both and k % 2 == 0 else [sides[k % 2]]):
            A, B = explain_pose(who, side, 0.0, big), explain_pose(who, side, 1.0, big)
            if c['_kind'] == 'stand':
                move(who, [(tt, None), (tt + 0.5, A), (tt + dur * 0.5, B), (tt + dur - 0.5, A), (tt + dur, None)])
            else:
                Wp = waypoint(who, side)
                move(who, [(tt, None), (tt + 0.3, Wp), (tt + 0.65, A), (tt + dur * 0.5, B), (tt + dur - 0.6, A), (tt + dur - 0.3, Wp), (tt + dur, None)])
        busy(who, tt, tt + dur)
        tt += dur + rng.uniform(1.6 if big else 2.6, 3.2 if big else 4.6)
        k += 1


def to_arm_space(who, world, time):
    loc, yaw = where(who, time)[:2]
    M = Matrix.Translation(loc) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Scale(CH[who]['scale'], 4)
    return M.inverted() @ V(world)


def g_point(who, t0, t1, target, side=None):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)
    if isinstance(target, str) and target not in CH:
        set_ = scene_at(t0)[1]
        tw = V(set_module(set_).LOOKS[target]) + OFFSET[set_]
    else:
        tw = head_at(target, t0) if isinstance(target, str) else V(target)
    if side is None:      # the hand on the target's side of the body
        mid = (kit.joint(arm, 'upperarm_l') + kit.joint(arm, 'upperarm_r')) * 0.5
        side = 'l' if (to_arm_space(who, tw, t0) - mid).x > 0 else 'r'
    sg = 1 if side == 'l' else -1
    S_ = kit.joint(arm, 'upperarm_' + side)
    d = to_arm_space(who, tw, t0) - S_
    if d.y > -0.25 * d.length:          # never reach back behind the body: point forward and out toward it
        d.y = -0.25 * d.length
    p = S_ + d.normalized() * min(d.length, 0.56)
    dn = (p - S_).normalized()
    A = capture(c, side, lambda: place_hand(arm, side, p, dn, V((0, 0, -1)), S_ + V((sg * 0.6, 0.2, -0.3))), 'point %s' % side)
    if c['_kind'] == 'stand':
        move(who, [(t0, None), (t0 + 0.5, A), (t1 - 0.5, A), (t1, None)])
    else:
        Wp = waypoint(who, side)
        move(who, [(t0, None), (t0 + 0.3, Wp), (t0 + 0.7, A), (t1 - 0.6, A), (t1 - 0.3, Wp), (t1, None)])
    busy(who, t0, t1)


def g_spread(who, t0, t1):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)
    standing = c['_kind'] == 'stand'

    def fn():
        for sd, sg in (('l', 1), ('r', -1)):
            S_ = kit.joint(arm, 'upperarm_' + sd)
            place_hand(arm, sd, S_ + V((sg * 0.3, -0.3, -0.25 if standing else -0.18)), V((sg * 0.6, -0.8, 0.0)), V((0, 0, 1)), S_ + V((sg * 0.6, 0.2, -0.4)))
    P = capture2(c, fn, 'spread hands')
    move(who, [(t0, None), (t0 + 0.6, P), (t1 - 0.5, P), (t1, None)])
    busy(who, t0, t1)


def g_point_up(who, t0, t1):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)
    S_ = kit.joint(arm, 'upperarm_r')
    A = capture(c, 'r', lambda: place_hand(arm, 'r', S_ + V((-0.22, -0.2, 0.46)), V((-0.2, -0.3, 1.0)), V((0, -1, 0.0)), S_ + V((-0.6, 0.3, -0.2))), 'point up')
    move(who, [(t0, None), (t0 + 0.8, A), (t1 - 0.7, A), (t1, None)])
    busy(who, t0, t1)


def g_hands_mouth(who, t0, t1):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)

    def fn():
        mouth = posed(arm, 'head', c['Hd'].at(0, -36, 1.0))
        for sd, sg in (('l', 1), ('r', -1)):
            S_ = kit.joint(arm, 'upperarm_' + sd)
            p = mouth + V((sg * 0.035, -0.06 - (0.03 if sd == 'l' else 0.0), -0.01 + (0.02 if sd == 'l' else -0.02)))
            place_hand(arm, sd, p, V((-sg * 0.9, -0.1, 0.35)), V((0, 1, 0)), S_ + V((sg * 0.5, -0.2, -0.5)))
    P = capture2(c, fn, 'hands over mouth')
    move(who, [(t0, None), (t0 + 0.35, P), (t1 - 0.6, P), (t1, None)])
    busy(who, t0, t1)


def g_look_hand(who, t0, t1, side='r'):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)
    sg = 1 if side == 'l' else -1
    S_ = kit.joint(arm, 'upperarm_' + side)
    eye = posed(arm, 'head', c['Hd'].C)
    p = eye + V((-sg * 0.04, -0.36, -0.34))
    A = capture(c, side, lambda: place_hand(arm, side, p, V((-sg * 0.35, -0.3, 0.9)), V((0, 1.0, 0.2)), S_ + V((sg * 0.6, 0.1, -0.5))), 'look at hand')
    move(who, [(t0, None), (t0 + 0.7, A), (t1 - 0.6, A), (t1, None)])
    busy(who, t0, t1)
    OVERRIDES.append((who, t0 + 0.4, t1 - 0.3, ('hand', side)))


def g_ring(who, t0, t1, turning=True):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)
    standing = c['_kind'] == 'stand'
    sp = kit.joint(arm, 'spine_01')

    def at(dz):
        def fn():
            base = V((sp.x, sp.y - (0.3 if standing else 0.34), sp.z + (0.02 if standing else 0.1)))
            Sr, Sl = kit.joint(arm, 'upperarm_r'), kit.joint(arm, 'upperarm_l')
            place_hand(arm, 'r', base + V((-0.05, 0, 0)), V((0.7, -0.5, 0.1)), V((0.1, 0.3, 1.0)), Sr + V((-0.6, 0.1, -0.5)))
            place_hand(arm, 'l', base + V((0.06, -0.02, 0.05 + dz)), V((-0.8, -0.4, -0.2)), V((0.0, 0.2, -1.0)), Sl + V((0.6, 0.1, -0.5)))
        return capture2(c, fn, 'ring')
    A, B = at(0.0), at(0.015)
    keys = [(t0, None), (t0 + 0.7, A)]
    tt = t0 + 0.7
    while turning and tt + 0.9 < t1 - 0.7:
        keys += [(tt + 0.45, B), (tt + 0.9, A)]
        tt += 0.9
    keys += [(t1 - 0.6, A), (t1, None)]
    move(who, keys)
    busy(who, t0, t1)
    OVERRIDES.append((who, t0 + 0.3, t1 - 0.4, 'down'))


def g_hold_hand(who, t0, t1, other):
    """Socrates folds Julian's fingers over the ring: his hands close round the other's raised right hand."""
    c = CH[who]; arm = c['arm']
    oth = CH[other]
    o_arm = oth['arm']
    in_state(other, t0)
    So = kit.joint(o_arm, 'upperarm_r')
    hand_o = So + V((0.05, -0.32, -0.28))
    Ao = capture(oth, 'r', lambda: place_hand(o_arm, 'r', hand_o, V((0.4, -1.0, 0.1)), V((0, 0, 1)), So + V((-0.6, 0.1, -0.5))), 'offer hand')
    loc_o, yaw_o = where(other, t0)[:2]
    world_h = Matrix.Translation(loc_o) @ Matrix.Rotation(yaw_o, 4, 'Z') @ Matrix.Scale(oth['scale'], 4) @ hand_o
    in_state(who, t0)
    tgt = to_arm_space(who, world_h, t0)

    def fn():
        for sd, sg in (('l', 1), ('r', -1)):
            S_ = kit.joint(arm, 'upperarm_' + sd)
            p = tgt + V((sg * 0.02, 0.02, (0.06 if sd == 'l' else -0.05)))
            place_hand(arm, sd, p, V((-sg * 0.8, -0.6, 0.0)), V((0, 0, -1 if sd == 'l' else 1)), S_ + V((sg * 0.6, 0.1, -0.5)))
    P = capture2(c, fn, 'fold fingers')
    move(other, [(t0 - 0.4, None), (t0 + 0.4, Ao), (t1 - 0.5, Ao), (t1, None)])
    move(who, [(t0, None), (t0 + 0.8, P), (t1 - 0.6, P), (t1, None)])
    busy(who, t0, t1)
    busy(other, t0 - 0.4, t1)


def g_raise_gently(who, t0, t1):
    c = CH[who]; arm = c['arm']
    in_state(who, t0)
    S_ = kit.joint(arm, 'upperarm_r')
    P = capture(c, 'r', lambda: place_hand(arm, 'r', S_ + V((-0.1, -0.36, -0.08)), V((-0.1, -0.2, 1.0)), V((0, -1, 0.1)), S_ + V((-0.6, 0.2, -0.4))), 'raise gently')
    move(who, [(t0, None), (t0 + 0.8, P), (t1 - 0.7, P), (t1, None)])
    busy(who, t0, t1)


GESTURES = {'point': g_point, 'spread': g_spread, 'point_up': g_point_up, 'hands_mouth': g_hands_mouth, 'look_hand': g_look_hand, 'ring': g_ring,
            'hold_hand': g_hold_hand, 'raise_gently': g_raise_gently}

# ------------------------------------------------------------------ gaze


def head_at(who, time):
    loc, yaw, ka, kb, w = where(who, time)[:5]
    c = CH[who]
    h = c['states'][ka]['head']
    if kb:
        h = h.lerp(c['states'][kb]['head'], w)
    return loc + Matrix.Rotation(yaw, 3, 'Z') @ (h * c['scale'])


def target_point(who, name, time):
    if isinstance(name, tuple) and name and name[0] == 'hand':
        loc, yaw = where(who, time)[:2]
        return head_at(who, time) + Matrix.Rotation(yaw, 3, 'Z') @ V((0.0, -0.4, -0.35))
    if isinstance(name, str) and name in CH:
        return head_at(name, time)
    loc, yaw = where(who, time)[:2]
    fwd = Matrix.Rotation(yaw, 3, 'Z') @ V((0, -1, 0))
    if name == 'down':
        return head_at(who, time) + fwd * 0.6 + V((0, 0, -0.75))
    if name == 'ahead':
        return head_at(who, time) + fwd * 2.0
    if isinstance(name, str):
        set_ = scene_at(time)[1]
        m = set_module(set_)
        if name in getattr(m, 'LOOKS', {}):
            return V(m.LOOKS[name]) + OFFSET[set_]
        p = spot_of(name, set_)
        return V((p.x, p.y, 1.2))
    return V(name)


def angles(who, name, time):
    loc, yaw = where(who, time)[:2]
    hw = head_at(who, time)
    d = Matrix.Rotation(-yaw, 3, 'Z') @ (target_point(who, name, time) - hw)
    a = math.atan2(d.x, -d.y)
    p = math.atan2(d.z, math.hypot(d.x, d.y))
    lim = math.radians(62)
    return max(-lim, min(lim, a)), max(-0.55, min(0.35, p))


def mentioned(text, time):
    return [n for n in here(time) if n.lower() in text.lower()]


def addressee(it, prev):
    pres = here(it['t'] + 0.1)
    for n in mentioned(it['text'][:80], it['t'] + 0.1):
        if n != it['who']:
            return n
    if it['who'] != 'Socrates' and 'Socrates' in pres:
        return 'Socrates'
    if prev and prev != it['who'] and prev in pres:
        return prev
    others = [w for w in pres if w not in (it['who'], 'Julian')]
    return others[0] if others else it['who']


OVERRIDES = [(who, t0, t1 if t1 is not None else 1e9, target) for (who, t0, t1, target) in S.looks]
LOOKS = {who: [] for who in CH}
prev = None
for it in ITEMS:
    t0, t1, who = it['t'], it['t'] + it['secs'], it['who']
    pres = here(t0 + 0.1)
    if who == 'Narrator' or it['vo'] or who not in CH:
        for w in mentioned(it['text'], t0 + 0.1):
            for o in pres:
                if o != w and o != 'Julian' and rng.random() < 0.6:
                    LOOKS[o].append((t0 + rng.uniform(0.3, 1.2), w))
        continue
    to = addressee(it, prev)
    LOOKS[who].append((t0 - 0.2, to))
    if it['secs'] > 8:
        others = [n for n in pres if n not in (who, to, 'Julian')]
        if others:
            for tt in np.arange(t0 + 5.0, t1 - 3.0, 6.0):
                LOOKS[who].append((tt, rng.choice(others)))
                LOOKS[who].append((tt + 2.0, to))
    for w in pres:
        if w == who:
            continue
        LOOKS[w].append((t0 + 0.25 + 0.3 * rng.random(), who))
        if w != 'Julian' and it['secs'] > 8 and rng.random() < 0.4:
            g = t0 + rng.uniform(3.0, it['secs'] - 2.5)
            others = [n for n in pres if n != w]
            if others:
                LOOKS[w].append((g, rng.choice(others)))
                LOOKS[w].append((g + rng.uniform(1.2, 2.2), who))
    prev = who
for w in LOOKS:
    LOOKS[w].sort(key=lambda k: k[0])
    if not LOOKS[w]:
        LOOKS[w] = [(0.0, 'ahead')]
    elif LOOKS[w][0][0] > 0:
        LOOKS[w].insert(0, (0.0, LOOKS[w][0][1]))


def look_name(who, time):
    best = None
    for (w_, a_, b_, tg) in OVERRIDES:
        if w_ == who and a_ <= time < b_ and (best is None or a_ > best[1]):
            best = (tg, a_)
    if best:
        return best
    ks = LOOKS[who]
    cur = ks[0]
    for k in ks:
        if k[0] <= time:
            cur = k
    return cur[1], cur[0]


def usable(who, name, time):
    if isinstance(name, str) and name in CH:
        return name != who and kind_at(name, time) != 'away' and name in here(time)
    return True


def gaze(who, time):
    name, since = look_name(who, time)
    if not usable(who, name, time):
        name = 'ahead'
    b = angles(who, name, time)
    k = ease((time - since) / 0.55)
    if k >= 1.0:
        return b
    pn, _ = look_name(who, since - 0.01) if since > 0 else (name, 0)
    if not usable(who, pn, time) or pn == name:
        return b
    a = angles(who, pn, time)
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)


BLINK = {}
for who in CH:
    ts, x = [], rng.uniform(0.5, 2.5)
    while x < END / FPS:
        ts.append(int(x * FPS))
        x += rng.uniform(2.2, 5.0)
    BLINK[who] = ts


def lid_angle(who, f):
    o = LID_OPEN.get(who, -34)
    t_ = f / FPS
    for (a_, b_) in SLEEPING.get(who, []):          # no blink while falling asleep or asleep: the lids just droop
        if a_ - 2.5 <= t_ < b_:
            return o
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
    'laugh': dict(up=0.01, tilt=-0.05, smile=1.2, wide=0.012, lid=22, open=0.9, head=-4),
    'smug': dict(up_l=0.009, up_r=-0.003, tilt=-0.15, smile=0.55, wide=0.004, lid=10),
    'warm': dict(up=0.005, smile=0.65, wide=0.006, lid=3, open=0.15),
    'determined': dict(up=-0.004, tilt=-0.22, knit=0.003, smile=0.15, tight=0.45, lid=4),
    'calm': dict(smile=0.35, wide=0.003, lid=4),
    'serious': dict(up=-0.002, tilt=-0.12, knit=0.002, smile=-0.18, tight=0.2),
    'sullen': dict(up=-0.006, tilt=-0.2, knit=0.004, smile=-0.6, tight=0.6, lid=14, head=5),
    'puzzled': dict(up_l=0.012, up_r=-0.002, tilt=0.15, knit=0.003, smile=-0.15, lid=-4),
    'asleep': dict(lid=200, head=16),
    'drowsy': dict(lid=30, head=6),
}
NOTE_EXPR = [('roaring', 'rage', 1.0), ('quiver', 'alarm', 1.0), ('curtly', 'frown', 1.0), ('amused', 'warm', 1.0), ('delighted', 'smile', 1.0),
             ('smil', 'smile', 0.9), ('laugh', 'smile', 1.0), ('sighing', 'grave', 0.9), ('hesitat', 'serious', 0.8), ('mildly', 'calm', 1.0),
             ('quietly', 'calm', 0.7), ('gently', 'warm', 0.8), ('eagerly', 'warm', 1.0), ('fading', 'grave', 1.0), ('whisper', 'serious', 0.8),
             ('earnest', 'wonder', 1.0), ('aloud', 'determined', 0.8), ('interposing', 'determined', 0.8), ('pause', 'grave', 0.8),
             ('spreading', 'raise', 0.8), ('settling', 'calm', 0.6), ('slowly', 'grave', 0.6), ('softly', 'warm', 0.7), ('a beat', 'grave', 0.7)]
TEMPER = {'Thrasymachus': ('frown', 0.6), 'Socrates': ('calm', 0.35), 'Glaucon': ('determined', 0.4), 'Adeimantus': ('serious', 0.5),
          'Cephalus': ('warm', 0.6), 'Polemarchus': ('serious', 0.3), 'Julian': ('serious', 0.3)}


def expr(who, t0, t1, name, k=1.0):
    if who in CH and t0 is not None:
        CH[who]['expr'].append((t0, t1, PRESETS[name], k))


for who, t0, t1, name, k in S.exprs:
    expr(who, t0, t1, name, k)
for who, t0, t1 in S.sleeps:
    if t0 > 0.5:     # falling asleep on screen: the lids grow heavy first, then close
        expr(who, t0 - 1.4, t0 + 0.6, 'drowsy', 0.8)
    expr(who, t0 + (0.5 if t0 > 0.5 else 0.0), t1, 'asleep', 1.0)
for who, t0, t1, deg in S.leans:
    if who in CH:
        CH[who]['leans'].append((t0, t1, deg))
for who, t0, t1, deg in S.nods:
    if who in CH:
        CH[who]['nods'].append((t0, t1, deg))
for name, who, t0, t1, kw in S.gests:
    if who in CH:
        GESTURES[name](who, t0, t1, **kw)

SLEEPING = {}
for who, t0, t1 in S.sleeps:
    SLEEPING.setdefault(who, []).append((t0, t1))


def asleep(who, time):
    return any(a_ <= time < b_ for a_, b_ in SLEEPING.get(who, []))


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
    if it['secs'] > 5.5 and who not in S.quiet and not is_busy(who, t0, t1):
        explain(who, t0, t1, big=who == 'Thrasymachus', both=who == 'Thrasymachus')

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
        for w in here(it['t'] + 0.1):
            if w != who and w != 'Julian' and rng.random() < 0.5:
                t0 = it['t'] + rng.uniform(3.0, it['secs'] - 2.5)
                if not asleep(w, t0):
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
LIFT = {'Socrates': 0.011, 'Julian': 0.009, 'Cleon': 0.009, 'Aria': 0.01}

# ------------------------------------------------------------------ the arm solve that holds a resting hand in place

REL = {}
for who, c in CH.items():
    bones = c['arm'].data.bones
    REL[who] = {b.name: ((b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy(), b.parent.name if b.parent else None) for b in bones}


def fk(who, kind, local, bone, memo):
    if bone in memo:
        return memo[bone]
    base = CH[who]['states'][kind]['base']
    rel, par = REL[who][bone]
    q = local.get(bone)
    if q is None:
        q = base[bone][0]
    L = Matrix.Translation(base[bone][1]) @ q.to_matrix().to_4x4()
    M = (fk(who, kind, local, par, memo) @ rel @ L) if par else (rel @ L)
    memo[bone] = M
    return M


SP0 = {(who, k): fk(who, k, {}, 'spine_03', {}) for who in CH for k in CH[who]['states']}
ELBOW_FOLLOW = float(opt('--elbow-follow', 0.85))


def plant(who, kind, side, local, target=None, follow=None):
    c = CH[who]
    base = c['states'][kind]['base']
    Hm, elbow = target or c['states'][kind]['plant'][side]
    memo = {}
    elbow = elbow.lerp(fk(who, kind, local, 'spine_03', memo) @ SP0[(who, kind)].inverted() @ elbow, ELBOW_FOLLOW if follow is None else follow)
    up, lo, hd = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    Msh = fk(who, kind, local, 'shoulder_' + side, memo)
    rel_up = REL[who][up][0]
    S_ = (Msh @ rel_up).translation
    L1 = (REL[who][lo][0].translation).length
    L2 = (REL[who][hd][0].translation).length
    Tw = Hm.translation
    d = (Tw - S_).length
    dd = max(abs(L1 - L2) + 1e-4, min(d, L1 + L2 - 1e-4))
    u = (Tw - S_).normalized()
    a_ = (L1 * L1 - L2 * L2 + dd * dd) / (2 * dd)
    h_ = math.sqrt(max(0.0, L1 * L1 - a_ * a_))
    pv = elbow - S_
    pv = pv - u * pv.dot(u)
    pv = pv.normalized() if pv.length > 1e-6 else V((0, 0, -1))
    E = S_ + u * a_ + pv * h_
    out = {}
    rel_lo = REL[who][lo][0]
    rel_h = REL[who][hd][0]
    base_up = Msh @ rel_up @ base[up][0].to_matrix().to_4x4()
    v = (base_up @ rel_lo).translation - S_
    R = v.rotation_difference(E - S_).to_matrix()
    want = R @ base_up.to_3x3()
    out[up] = ((Msh @ rel_up).to_3x3().inverted() @ want).to_quaternion()
    Mup = (Msh @ rel_up).to_3x3() @ out[up].to_matrix()
    Mup4 = Mup.to_4x4(); Mup4.translation = S_
    base_lo = Mup4 @ rel_lo @ base[lo][0].to_matrix().to_4x4()
    Ea = base_lo.translation
    v = (base_lo @ rel_h).translation - Ea
    R = v.rotation_difference(Tw - Ea).to_matrix()
    want = R @ base_lo.to_3x3()
    out[lo] = ((Mup4 @ rel_lo).to_3x3().inverted() @ want).to_quaternion()
    Mlo = (Mup4 @ rel_lo).to_3x3() @ out[lo].to_matrix()
    Mlo4 = Mlo.to_4x4(); Mlo4.translation = (Mup4 @ rel_lo).translation
    out[hd] = ((Mlo4 @ rel_h).to_3x3().inverted() @ Hm.to_3x3()).to_quaternion()
    return out


# ------------------------------------------------------------------ a pose for one person at one frame


def kind_pose(who, kind, time, x, yaw, pitch, ex, lean, nod, talk_s, wmix, wdist):
    c = CH[who]
    st = c['states'][kind]
    base = st['base']
    standing = kind == 'stand'
    seated = kind.startswith('seat') or kind == 'floor'
    yw = YW if standing else YW_SEATED
    sleepy = asleep(who, time)
    rot, loc = {}, {}
    local = {}
    planted = {}
    wx = (wdist / STRIDE * (W1 - W0)) if (WALK and wmix > 0) else 0.0
    for b in BODY + LEGS:
        d = MEAN[b].inverted() @ isample(b, x)
        sd_ = b[-1] if b.startswith(('upperarm_', 'lowerarm_', 'hand_')) else None
        if seated and sd_ and sd_ not in planted:
            planted[sd_] = plant(who, kind, sd_, local)
        if standing:
            if b in ARMSET:
                q = base[b][0] @ scaled(d, 0.12)
                if wmix > 0 and b in WMEAN:
                    q = q.slerp(base[b][0] @ scaled(WMEAN[b].inverted() @ wsample(b, wx), 0.55), wmix)
            elif b in ('neck', 'head'):
                q = base[b][0] @ d
            else:
                q = isample(b, x)
                if wmix > 0 and WALK and b in WR:
                    q = q.slerp(wsample(b, wx), wmix)
        elif sd_:
            q = planted[sd_][b]
        elif b in LEGS:
            q = base[b][0]
        else:
            q = base[b][0] @ scaled(d, AMOUNT.get(b, 0.8) * (0.4 if sleepy else 1.0))
        for keys in c['moves']:
            w, pose = move_at(keys, time)
            if w > 0 and pose and b in pose and pose.get('_kind') == kind:
                if sd_ and ('_plant_' + sd_) in pose:
                    tgt = plant(who, kind, sd_, local, pose['_plant_' + sd_], pose.get('_follow_' + sd_)) if b == 'upperarm_' + sd_ or ('_solved', sd_) not in planted else None
                    if tgt:
                        planted[('_solved', sd_)] = tgt
                    q = q.slerp(planted[('_solved', sd_)][b], w)
                else:
                    q = q.slerp(pose[b] @ scaled(d, 0.15), w)
        axx, axz = st['axx'], st['axz']
        if b == 'spine_01' and lean:
            q = q @ Quaternion(axx[b], math.radians(lean) * 0.4)
        elif b == 'spine_02' and lean:
            q = q @ Quaternion(axx[b], math.radians(lean) * 0.6)
        if b == 'spine_03':
            q = q @ Quaternion(axz[b], yaw * yw[0])
        elif b == 'neck':
            q = q @ Quaternion(axz[b], yaw * yw[1]) @ Quaternion(axx[b], -pitch * 0.35)
        elif b == 'head':
            bob = math.radians(4.0) * (talk_s - 0.25) if talk_s > 0.02 else 0.0
            bow = math.radians(ex.get('head', 0.0))
            q = q @ Quaternion(axz[b], yaw * yw[2]) @ Quaternion(axx[b], -pitch * 0.5 + bob + nod + bow)
        local[b] = q
        rot[b] = q
    for b in ('hip', 'root'):
        if standing:
            l = iloc(b, x)
            if wmix > 0 and WALK:
                l = l.lerp(V((0, 0, 0)) if b == 'root' else wloc(b, wx), wmix)
            loc[b] = l
        else:
            loc[b] = V(base[b][1])
    return rot, loc


def frame_pose(who, f):
    c = CH[who]
    time = f / FPS
    x = idle_x(who, time)
    talk = env_at(who, f)
    talk_s = float(np.mean([env_at(who, g) for g in range(f - 3, f + 4)]))
    loc, oyaw, ka, kb, bw, wmix, wdist = where(who, time)
    if asleep(who, time):
        yaw, pitch = 0.0, -0.2
    else:
        yaw, pitch = gaze(who, time)
    ex = expr_at(who, time)
    lean = sum(d * window(t0, t1, 0.5)(time) for (t0, t1, d) in c['leans'])
    nod = sum(math.radians(a_) * math.sin(2 * math.pi * 0.9 * (time - t0)) * window(t0, t1, 0.4)(time) for (t0, t1, a_) in c['nods'])
    rot, lc = kind_pose(who, ka, time, x, yaw, pitch, ex, lean, nod, talk_s, wmix, wdist)
    if kb:
        rb, lb = kind_pose(who, kb, time, x, yaw, pitch, ex, lean, nod, talk_s, 0.0, 0.0)
        rot = {b: rot[b].slerp(rb[b], bw) for b in rot}
        lc = {b: lc[b].lerp(lb[b], bw) for b in lc}
    for (w_, a_, b_, amt) in S.half:
        if w_ == who and a_ <= time <= b_ and ka != 'stand':
            hw_ = window(a_, b_, 0.7)(time) * amt
            rs, ls = kind_pose(who, 'stand', time, x, yaw, pitch, ex, lean, nod, talk_s, 0.0, 0.0)
            rot = {b: rot[b].slerp(rs[b], hw_) for b in rot}
            lc = {b: lc[b].lerp(ls[b], hw_) for b in lc}
            loc = loc + V((math.sin(oyaw), -math.cos(oyaw), 0)) * 0.2 * hw_
    out = {}
    for b, q in rot.items():
        out['pose.bones["%s"].rotation_quaternion' % b] = tuple(q)
    for b, l in lc.items():
        out['pose.bones["%s"].location' % b] = tuple(l)
    axx = c['states'][ka]['axx']
    la = math.radians(min(72.0, lid_angle(who, f) + ex.get('lid', 0.0)))
    for sd in 'lr':
        out['pose.bones["lid_%s"].rotation_quaternion' % sd] = tuple(Quaternion(axx['lid_' + sd], la))
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
    if asleep(who, time):
        opn = 0.3
    out['pose.bones["mouth"].scale'] = (1.0, max(0.18, opn), 1.0)
    out['_loc'] = tuple(loc)
    out['_yaw'] = oyaw
    shown = kb if (kb and bw >= 0.5) else ka
    out['_seated'] = 1.0 if (shown.startswith('seat') or shown == 'floor') else 0.0
    return out


def apply_pose(who, vals):
    arm = CH[who]['arm']
    for path, v in vals.items():
        if path == '_loc':
            arm.location = v
        elif path == '_yaw':
            arm.rotation_euler = (0, 0, v)
        elif path.startswith('_'):
            continue
        else:
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
    BOXES = courtyard.boxes() if 'court' in SETS else []
    if opt('--debug'):
        f_ = int(opt('--frame'))
        for who in CH:
            apply_pose(who, frame_pose(who, f_))
        kit.refresh()
        w_, a_, b_ = opt('--debug').split(',')
        fg = figs[w_]
        fg.pose()
        for pa, pb_ in ((a_, b_), (b_, a_)):
            X = fg.pts(pa)
            sd = fg.signed(pb_, X)
            i = int(np.argmin(sd))
            dd, j = fg.tree(pb_).query(X[i])
            vi = int(fg.part[pb_][j])
            me = CH[w_]['body'].data
            mats = {me.materials[p_.material_index].name for p_ in me.polygons if vi in p_.vertices}
            M = CH[w_]['arm'].matrix_world.inverted()
            print('DEBUG %s %s in %s: point %s signed %.3f nearest %s mats %s' % (w_, pa, pb_, tuple(round(v, 3) for v in (M @ V(X[i]))), sd[i],
                  tuple(round(v, 3) for v in (M @ V(fg.P[vi]))), mats))
        sys.exit(0)
    if opt('--lab'):
        for who, name, g in LAB:
            c = CH[who]
            set_base(who, g.get('_kind') or any_state(who))
            c['arm'].location, c['arm'].rotation_euler = (0, 0, 0), (0, 0, 0)
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
        tm = f / FPS
        for who in CH:
            apply_pose(who, frame_pose(who, f))
        kit.refresh()
        vis_ = {w: fg for w, fg in figs.items() if kind_at(w, tm) != 'away'}
        for k, v in clearance.measure(vis_, (), BOXES).items():
            if v < 0.003 and not (k[2].startswith('seat') and k[1] == 'trunk'):
                if k[2].startswith('seat') and kind_at(k[0], tm).startswith('seat') and k[1] in ('thigh_l', 'thigh_r') and v > -0.01:
                    continue
                bad.setdefault(k, []).append((f, v))
    for k, fs in sorted(bad.items(), key=lambda kv: min(v for _, v in kv[1])):
        fw = min(fs, key=lambda z: z[1])[0]
        print('CLASH %-12s %-8s %-16s frames %5d-%5d worst %+.3f m at %d (%.1f s) (%d samples)' % (k[0], k[1], k[2], fs[0][0], fs[-1][0], min(v for _, v in fs),
                                                                                              fw, fw / FPS, len(fs)))
    print('CLASHES', len(bad))
    sys.exit(0)

KEYS = {who: {} for who in CH}          # (data path, index) -> one value per frame, in numpy (a long sequence has millions)
SEATED = {who: np.zeros(len(FRAMES)) for who in CH}
NF = len(FRAMES)


def keep_value(who, key, fi, x_):
    a = KEYS[who].get(key)
    if a is None:
        a = KEYS[who][key] = np.empty(NF, np.float32)
    a[fi] = x_


for fi, f in enumerate(FRAMES):
    for who in CH:
        for path, v in frame_pose(who, f).items():
            if path == '_loc':
                for i_, x_ in enumerate(v):
                    keep_value(who, ('location', i_), fi, x_)
            elif path == '_yaw':
                keep_value(who, ('rotation_euler', 2), fi, v)
            elif path == '_seated':
                SEATED[who][fi] = v
            else:
                for i_, x_ in enumerate(v):
                    keep_value(who, (path, i_), fi, x_)


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
    if path in ('location', 'rotation_euler'):
        return 0.0008
    return 0.0015


TOTAL = [0, 0]


def write_keys(idb, keys, frames):
    act = bpy.data.actions.new(idb.name + ' action')
    idb.animation_data_create()
    idb.animation_data.action = act
    for (path, idx), vals in keys.items():
        y = np.asarray(vals, float)
        keep = simplify(frames, y, tol_for(path))
        if path in ('location', 'rotation_euler'):
            for j in np.nonzero(np.abs(np.diff(y)) > (0.25 if path == 'location' else 0.6))[0]:
                keep[j] = keep[j + 1] = True        # both sides of a jump (a cut to another place)
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
    sk = c['skirt']
    if sk:
        prev_ = None
        for f, v in zip(FRAMES, SEATED[who]):
            if v != prev_:
                sk.hide_render = sk.hide_viewport = bool(v)
                sk.keyframe_insert('hide_render', frame=f)
                sk.keyframe_insert('hide_viewport', frame=f)
                prev_ = v
print('keys kept %d of %d' % (TOTAL[1], TOTAL[0]))

# ---- Julian's ring: the glassy outline or the solid figure, his shadow, and the shimmer when he goes
for who in FX:
    evs = sorted([(t_, on, d_) for (w_, t_, on, d_) in S.vis if w_ == who])
    body = CH[who]['body']
    vis0 = 1.0
    if evs and evs[0][0] <= 0.05:
        vis0 = 1.0 if evs[0][1] else 0.0
        evs = evs[1:]
    fx_key(who, 0, Visible=vis0, Fade=1.0, Shimmer=0.0)
    body.visible_shadow = vis0 > 0.5
    body.keyframe_insert('visible_shadow', frame=0)
    cur = vis0
    for (t_, on, d_) in evs:
        v = 1.0 if on else 0.0
        fx_key(who, F(t_), Visible=cur)
        fx_key(who, F(t_ + d_), Visible=v)
        body.visible_shadow = on
        body.keyframe_insert('visible_shadow', frame=F(t_ + d_ * 0.5))
        cur = v
    for (w_, t0, t1) in S.shim:
        if w_ != who:
            continue
        fx_key(who, F(t0), Shimmer=0.0, Fade=1.0)
        fx_key(who, F(t0 + (t1 - t0) * 0.5), Shimmer=1.0)
        fx_key(who, F(t1 - 0.3), Fade=1.0)
        fx_key(who, F(t1), Shimmer=0.0, Fade=0.0)
        body.visible_shadow = False
        body.keyframe_insert('visible_shadow', frame=F(t1))

# ---- people kept out of sight altogether
for kind, t_, kw in sorted(S.props, key=lambda p: p[1]):
    if kind == 'hide' and kw.get('who') in CH:
        w_ = kw['who']
        obs = [o for o in bpy.data.objects if o.name.startswith(w_) or o is CH[w_]['body']]
        for o in obs:
            o.hide_render = not kw.get('on', True)
            o.keyframe_insert('hide_render', frame=max(0, F(t_) - 1))
            o.hide_render = kw.get('on', True)
            o.keyframe_insert('hide_render', frame=F(t_))

# ---- the ring put on (it lies on the lounge table until he picks it up), and a figure faded out coming back
for kind, t_, kw in S.props:
    if kind == 'ring_on' and kw.get('who', 'Julian') in RING_MAT:
        n_ = RING_MAT[kw.get('who', 'Julian')].node_tree.nodes['RingOn']
        n_.outputs[0].default_value = 0.0 if kw.get('on', True) else 1.0
        n_.outputs[0].keyframe_insert('default_value', frame=max(0, F(t_) - 1))
        n_.outputs[0].default_value = 1.0 if kw.get('on', True) else 0.0
        n_.outputs[0].keyframe_insert('default_value', frame=F(t_))
    if kind == 'appear' and kw.get('who', 'Julian') in FX:
        w_ = kw.get('who', 'Julian')
        fx_key(w_, F(t_), Fade=0.0, Shimmer=0.6)
        fx_key(w_, F(t_ + kw.get('dur', 1.0)), Fade=1.0, Shimmer=0.0)
        body = CH[w_]['body']
        body.visible_shadow = bool(kw.get('shadow', False))
        body.keyframe_insert('visible_shadow', frame=F(t_ + kw.get('dur', 1.0)))

# ---- a blush: the skin warms toward red for a while
for who, t0, t1 in S.blush:
    if who not in CH:
        continue
    for slot in CH[who]['body'].material_slots:
        if slot.material.name == who + ' skin':
            b = next(n for n in slot.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            c0 = tuple(b.inputs['Base Color'].default_value)
            red = (min(1.0, c0[0] * 1.25), c0[1] * 0.62, c0[2] * 0.6, 1.0)
            for fr, col in ((F(t0), c0), (F(t0 + 1.2), red), (F(t1 - 1.0), red), (F(t1), c0)):
                b.inputs['Base Color'].default_value = col
                b.inputs['Base Color'].keyframe_insert('default_value', frame=fr)

# ------------------------------------------------------------------ light: the sky, the sun and the lamps through the sequence

TOD = {   # sky top, horizon, sky strength, sun energy, sun colour, sky fill
    'DAY': ('#5f93cf', '#f2d6a8', 0.8, 3.6, (1.0, 0.88, 0.7), 420),
    'LATE AFTERNOON': ('#5f93cf', '#f2d6a8', 0.75, 3.4, (1.0, 0.84, 0.64), 380),
    'DUSK': ('#3b2f6b', '#e08a5a', 0.6, 0.6, (1.0, 0.55, 0.35), 230),
    'NIGHT': ('#0b1430', '#1f2a4a', 0.3, 0.0, (1, 1, 1), 25),
    'LATER THAT NIGHT': ('#0a1128', '#1a2340', 0.25, 0.0, (1, 1, 1), 20),
    'DEEP NIGHT': ('#05080f', '#0b1020', 0.1, 0.0, (1, 1, 1), 4),
    'BEFORE DAWN': ('#121a33', '#3b4566', 0.28, 0.0, (1, 1, 1), 18),
    'GREY': ('#4b5878', '#a7a9b8', 0.45, 0.0, (1, 1, 1), 70),
    'SUNRISE': ('#6b84b8', '#ffc58a', 0.7, 2.8, (1.0, 0.68, 0.42), 220),
    'DAWN': ('#6b84b8', '#ffc58a', 0.55, 0.0, (1.0, 0.72, 0.5), 60),
    'INDOOR': ('#20242c', '#30343c', 0.2, 0.0, (1, 1, 1), 0),
}
w_ = bpy.data.worlds.new('Sky')
w_.use_nodes = True
nt = w_.node_tree
bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
tc = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
nt.links.new(tc.outputs['Generated'], sep.inputs[0])
mr = nt.nodes.new('ShaderNodeMapRange')
mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.5, 0.75
nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
top = nt.nodes.new('ShaderNodeRGB'); top.name = 'Top'
hor = nt.nodes.new('ShaderNodeRGB'); hor.name = 'Horizon'
mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
nt.links.new(mr.outputs['Result'], mx.inputs['Factor'])
nt.links.new(hor.outputs[0], mx.inputs['A']); nt.links.new(top.outputs[0], mx.inputs['B'])
nt.links.new(mx.outputs['Result'], bg.inputs['Color'])
sc.world = w_
SUN = stage.light('Sun', 'SUN', (5.0, -3.0, 6.5), 3.4, (1.0, 0.84, 0.64), 0.03, to=(0, 0, 0))
FILL = stage.light('Sky fill', 'AREA', (0.5, -2.0, 6.0), 380, (0.72, 0.84, 1.0), 9.0, to=(0, 0.3, 0), shadow=False)
MOON = stage.light('Moon', 'SUN', (-3, 4, 7), 0.0, (0.6, 0.72, 1.0), 0.02, to=(0, 0, 0))
if 'court' in SETS:
    stage.light('Bounce', 'AREA', (0.0, 0.8, 0.3), 60, (1.0, 0.85, 0.65), 6.0, to=(0, 0.8, 2.0), shadow=False)


def sky_key(frame, tod):
    tp, hz, strength, sun, sun_col, fill = TOD[tod]
    top.outputs[0].default_value = kit.hexc(tp); top.outputs[0].keyframe_insert('default_value', frame=frame)
    hor.outputs[0].default_value = kit.hexc(hz); hor.outputs[0].keyframe_insert('default_value', frame=frame)
    bg.inputs['Strength'].default_value = strength; bg.inputs['Strength'].keyframe_insert('default_value', frame=frame)
    SUN.data.energy = sun; SUN.data.keyframe_insert('energy', frame=frame)
    SUN.data.color = sun_col; SUN.data.keyframe_insert('color', frame=frame)
    FILL.data.energy = fill; FILL.data.keyframe_insert('energy', frame=frame)
    MOON.data.energy = 0.25 if sun == 0 and tod != 'INDOOR' else 0.0; MOON.data.keyframe_insert('energy', frame=frame)


for k, (t0, set_, tod) in enumerate(S.scenes):
    f0 = F(t0)
    if k and f0 > 0:
        sky_key(max(0, f0 - 1), S.scenes[k - 1][2])
    sky_key(f0, tod)
for p in S.props:
    if p[0] == 'sky':
        sky_key(F(p[1]), p[2]['frm'])
        sky_key(F(p[1] + p[2].get('dur', 6.0)), p[2]['to'])

LAMPL = []
if 'court' in SETS:
    flames = SETS['court']['flames']
    LAMP_E = float(opt('--lamp', 180))
    BACK_E = float(opt('--back-lamp', 650))
    for k, (x, y, z) in enumerate(courtyard.LAMPS):
        L = stage.light('Lamp %d' % k, 'POINT', (x + 0.135, y, z + 0.12), 0.0, (1.0, 0.66, 0.34), 0.05 if k == courtyard.BACK_LAMP else 0.08)
        LAMPL.append(L)
        flames[k].scale = (0.001,) * 3
        flames[k].keyframe_insert('scale', frame=0)
        L.data.keyframe_insert('energy', frame=0)
    stage.light('Altar glow', 'POINT', (courtyard.ALTAR[0], courtyard.ALTAR[1], 1.1), 18, (1.0, 0.5, 0.2), 0.3, shadow=False)
    lit = {k: False for k in range(len(LAMPL))}
    for (t_, which, on, dur) in sorted(S.lamps, key=lambda z: z[0]):
        ks_ = list(range(len(LAMPL) - 1)) if which == 'all' else (list(which) if isinstance(which, (list, tuple)) else [which])
        for n_, k in enumerate(ks_):
            tt = t_ + n_ * dur
            e_on = BACK_E if k == courtyard.BACK_LAMP else LAMP_E
            flames[k].scale = ((1.0 if lit[k] else 0.001),) * 3
            flames[k].keyframe_insert('scale', frame=F(tt))
            LAMPL[k].data.energy = e_on if lit[k] else 0.0
            LAMPL[k].data.keyframe_insert('energy', frame=F(tt))
            flames[k].scale = ((1.0 if on else 0.001),) * 3
            flames[k].keyframe_insert('scale', frame=F(tt + 0.35))
            LAMPL[k].data.energy = e_on if on else 0.0
            LAMPL[k].data.keyframe_insert('energy', frame=F(tt + 0.35))
            lit[k] = on

for p in S.props:
    if p[0] == 'torches' and 'court' in SETS:
        t0, kw = p[1], p[2]
        tmat = courtyard.flame_material('Torch flame')
        for n_ in range(kw.get('n', 4)):
            ob = kit.static('Torch %d' % n_, [(kit.sphere((0, 0, 0), (0.07, 0.07, 0.16)), tmat)])
            ob.visible_shadow = False
            L = stage.light('Torch light %d' % n_, 'POINT', (0, 0, 0), 220, (1.0, 0.6, 0.3), 0.1, shadow=False)
            L.parent = ob
            L.location = (0, 0, 0)
            ts_ = t0 + n_ * kw.get('gap', 1.1)
            for fr, y in ((F(ts_), -14.0), (F(ts_ + kw.get('dur', 3.4)), 10.0)):
                ob.location = (courtyard.WALL_X + 2.4, y, 2.0)
                ob.keyframe_insert('location', frame=fr)
    if p[0] == 'garland' and 'court' in SETS:
        leaf = kit.material('Garland', '#5c7d34', rough=0.6)
        x, y, yaw = courtyard.SEATS['cephalus']
        g_ = []
        for a in range(0, 360, 18):
            r_ = math.radians(a)
            g_.append((kit.sphere((x + 0.13 * math.cos(r_), y + 0.13 * math.sin(r_), courtyard.SEAT + 0.075), (0.026, 0.016, 0.014)), leaf))
        kit.static('Garland on the chair', g_)
S.speed = SPEED
for set_, info in SETS.items():
    if hasattr(set_module(set_), 'animate'):
        set_module(set_).animate(info, S, F, OFFSET[set_])

# ------------------------------------------------------------------ cameras and cuts

CAMS = {}
for set_ in SETS:
    m = set_module(set_)
    off = OFFSET[set_]
    for name, (loc, to, lens) in m.CAMERAS.items():
        CAMS['%s %s' % (set_, name)] = stage.camera('Cam %s %s' % (set_, name), tuple(V(loc) + off), tuple(V(to) + off), lens)


def close(who, time):
    """The close-up camera for a person where they are at a time (made on first use)."""
    loc, yaw, ka, kb, bw = where(who, time)[:5]
    k = kb if (kb and bw > 0.5) else ka
    key = 'close %s %.2f %.2f %.2f %s' % (who, loc.x, loc.y, yaw, k)
    if key not in CAMS:
        h = head_at(who, time)
        f = V((math.sin(yaw), -math.cos(yaw), 0))
        r = V((f.y, -f.x, 0))
        dist = {'stand': 1.75, 'floor': 1.45}.get(k, 1.6)
        lift = V((0, 0, 0.0 if k != 'floor' else 0.25))
        others = [head_at(o, tt) for tt in (time, time + 2.5, time + 5.0) for o in here(tt) if o != who and o in CH]

        def clear(p):
            # the smallest angle (degrees) between this face and any other head nearer the camera: under ~24 it is in the frame
            best = 180.0
            d = h - p
            for o in others:
                e = o - p
                if e.length < d.length + 0.2:
                    best = min(best, (math.degrees(d.angle(e)) - math.degrees(math.atan(0.22 / e.length))) if e.length > 0.05 else 0.0)
            return best
        cands = [h + f * dist + r * sd + lift for sd in (0.26, -0.26, 0.6, -0.6, 0.95, -0.95)]
        for a_ in (55, -55, 75, -75):           # three-quarter and profile angles, for two people face to face
            a_ = math.radians(a_)
            cands.append(h + (f * math.cos(a_) + r * math.sin(a_)) * dist + lift)
        ok_ = [c_ for c_ in cands if clear(c_) > 16.0]
        pos = ok_[0] if ok_ else max(cands, key=clear)
        if os.environ.get('CLOSE_DEBUG'):
            print('CLOSEDBG', who, round(time, 1), k, [o for o in here(time)], [round(clear(c_), 1) for c_ in cands])
        CAMS[key] = stage.camera('Cam ' + key, tuple(pos), tuple(h + V((0, 0, -0.14 if k != 'floor' else -0.1))), 36)
    return key


def two_shot(speaker, listener, time):
    hs, hl = head_at(speaker, time), head_at(listener, time)
    key = 'ots %s %s %.1f %.1f' % (speaker, listener, hl.x, hl.y)
    if key not in CAMS:
        d = (hl - hs); d.z = 0; d.normalize()
        side = V((-d.y, d.x, 0))
        if kind_at(listener, time) == 'stand':
            pos = hl + d * 0.95 + side * 0.5 + V((0, 0, 0.22))
        else:
            pos = hl + d * 1.25 + side * 0.62 + V((0, 0, 0.62))
        CAMS[key] = stage.camera('Cam ' + key, tuple(pos), tuple(hs + V((0, 0, -0.22))), 30)
    return key


def follow_cam(who, time):
    """A camera that turns to follow a walking person from its place."""
    set_ = scene_at(time)[1]
    key = 'follow %s %s' % (who, set_)
    if key not in CAMS:
        m = set_module(set_)
        spec = m.CAMERAS.get('follow', m.CAMERAS['wide'])
        cam = stage.camera('Cam ' + key, tuple(V(spec[0]) + OFFSET[set_]), tuple(head_at(who, time)), spec[2] + 6)
        con = cam.constraints.new('TRACK_TO')
        con.target = CH[who]['arm']
        con.subtarget = 'head'
        con.track_axis = 'TRACK_NEGATIVE_Z'
        con.up_axis = 'UP_Y'
        CAMS[key] = cam
    return key


def wide(time):
    return '%s wide' % scene_at(time)[1]


CUTS = []


def cut(time, name):
    if CUTS and CUTS[-1][1] == name:
        return
    if CUTS and time - CUTS[-1][0] < 1.6:
        CUTS[-1] = (CUTS[-1][0], name)
        return
    CUTS.append((time, name))


def shot_of(who, time):
    if who not in here(time):
        return wide(time)
    if moving(who, time, time + 2.0):
        return follow_cam(who, time)
    return close(who, time + 0.5)


prev = None
for it in ITEMS:
    t0, t1, who = it['t'], it['t'] + it['secs'], it['who']
    start = 0.0 if it is ITEMS[0] else t0 - 0.25
    if who == 'Narrator' or it['vo'] or who not in CH:
        low = it['text'].lower()
        marks = sorted((low.find(n.lower()) / max(1, len(low)), n) for n in mentioned(it['text'], t0 + 0.1))
        if it['vo'] and who in here(t0 + 0.1) and who not in [m_[1] for m_ in marks]:
            marks = [(0.0, who)] + marks
        if not marks or marks[0][0] > 0.12 or it['kind'] in ('sequence', 'insert'):
            cut(start, wide(t0 + 0.3))
        for frac, n in marks:
            if it['kind'] in ('sequence', 'insert'):
                break
            tt = start if frac <= 0.12 else t0 + it['secs'] * frac - 0.2
            cut(tt, shot_of(n, tt))
        continue
    cut(start, shot_of(who, t0))
    to = addressee(it, prev)
    if it['secs'] > 8.5:
        opts = [lambda tt: shot_of(to, tt), lambda tt: two_shot(who, to, tt) if to in here(tt) and to != who else wide(tt), lambda tt: wide(tt)]
        k = 0
        for tt in np.arange(t0 + 4.5, t1 - 3.0, 7.5):
            cut(tt, opts[k % len(opts)](tt))
            cut(tt + 3.0, shot_of(who, tt + 3.0))
            k += 1
    prev = who
AIMED = {'column_view': 'Julian', 'wall_julian': 'Julian', 'alley': 'Julian'}     # set cameras framed on one person
_kept = []
for (t_, name) in S.cams:
    # a staged shot of someone kept out of sight is dropped; the automatic cuts cover that moment
    named = [w for w in CH if w in name] + ([AIMED[name]] if name in AIMED else [])
    if any(hidden(w, t_ + 0.3) for w in named):
        continue
    _kept.append((t_, name))
S.cams[:] = _kept
for (t_, name) in S.cams:
    if name.startswith('close '):
        name = close(name[6:], t_ + 0.3)
    elif name.startswith('follow '):
        name = follow_cam(name[7:], t_)
    elif name.startswith('ots '):
        a_, b_ = name[4:].split(',')
        name = two_shot(a_, b_, t_ + 0.3)
    elif name not in CAMS:
        name = '%s %s' % (scene_at(t_ + 0.3)[1], name)
    CUTS = [c_ for c_ in CUTS if abs(c_[0] - t_) > 0.8]
    CUTS.append((t_, name))
CUTS.sort()
for (t_, set_, tod) in S.scenes[1:]:
    if set_ != scene_at(t_ - 0.05)[1]:
        CUTS = [c_ for c_ in CUTS if not (t_ - 0.3 <= c_[0] < t_ + 1.2)]
        CUTS.append((t_, '%s wide' % set_))
CUTS.sort()
CUTS = [c_ for k, c_ in enumerate(CUTS) if k == 0 or c_[1] != CUTS[k - 1][1]]
for tm, name in CUTS:
    mk = sc.timeline_markers.new(name[:60], frame=F(tm))
    mk.camera = CAMS[name]
sc.camera = CAMS[CUTS[0][1]]
stage.eevee(sc, WIDTH, WIDTH * 9 // 16, int(opt('--samples', 8)))

plan = {'seq': SEQ, 'range': [I0, I1], 'frames': [0, END - 1], 'fps': FPS, 'seconds': round(END / FPS, 2),
        'cues': [{'id': it['id'], 't': round(it['t'], 4)} for it in ITEMS if it['id']], 'cuts': CUTS,
        'items': [(it['i'], it['who'], round(it['t'], 2), round(it['secs'], 2)) for it in ITEMS],
        'transitions': [(round(t_, 2), txt, i) for (t_, txt, i) in TRANS]}
print('seq', SEQ, 'range', I0, I1, 'frames', END, 'seconds %.1f' % (END / FPS), 'items', len(ITEMS), 'cuts', len(CUTS), 'people', len(CH))
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
        if opt('--only-cams') and not any(s_ in name for s_ in opt('--only-cams').split(',')):
            continue
        sc.camera = cam
        sc.render.filepath = out_.replace('.png', '_%s.png' % name.replace(' ', '_')[:50])
        bpy.ops.render.render(write_still=True)
still = opt('--still', n=2)
if still:
    for fr in still[0].split(','):
        sc.frame_set(int(fr))
        sc.render.filepath = still[1].replace('.png', '_%s.png' % fr)
        bpy.ops.render.render(write_still=True)
