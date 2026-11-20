"""Pictures for the story graphics: posed figures, thrones, ships, fire, sun and the rest, in the gfx kit's glowing line style.

Every call takes a G (gfx.G) first. Figures are about 100*s tall, drawn in profile facing right (f=1) or left (f=-1).
"""
import math
import random

import cairo

from gfx import CYAN, DIM, GOLD, INK, MUTED, ORANGE, RED, TEAL, VIOLET, WHITE, ap, ease, lerp, mix  # noqa: F401

BRONZE = (0.85, 0.55, 0.3)
SILVER = (0.8, 0.86, 0.92)
IRON = (0.62, 0.5, 0.42)
FIRE = (1.0, 0.55, 0.2)

# poses: lean (torso, degrees forward), arms ((upper, fore) back arm, (upper, fore) front arm), legs ((thigh, shin) back, front),
# angles in degrees from straight down, positive = forward; head = head tilt (positive looks up)
POSES = {
    'stand': dict(lean=0, arms=((-8, 8), (8, 10)), legs=((-4, 0), (5, 0))),
    'walk0': dict(lean=4, arms=((22, 20), (-22, 15)), legs=((-24, -8), (24, -4))),
    'walk1': dict(lean=4, arms=((-22, 15), (22, 20)), legs=((24, -4), (-24, -8))),
    'sit': dict(lean=-4, arms=((20, 50), (30, 55)), legs=((86, -86), (90, -90)), seat=True),
    'sit_chain': dict(lean=6, arms=((25, 70), (32, 70)), legs=((84, -84), (88, -88)), seat=True, head=-6),
    'kneel': dict(lean=12, arms=((15, 30), (40, 30)), legs=((-5, -85), (90, -90)), kneel=True, head=-18),
    'sit_ground': dict(lean=8, arms=((40, 30), (50, 30)), legs=((115, -95), (120, -100)), head=-4),
    'shield_eyes': dict(lean=-6, arms=((-10, 10), (125, 80)), legs=((-6, 0), (6, 0)), head=8),
    'hands_eyes': dict(lean=10, arms=((95, 95), (105, 90)), legs=((-4, 0), (4, 0)), head=-10),
    'arms_up': dict(lean=-4, arms=((165, 0), (170, 0)), legs=((-6, 0), (6, 0)), head=12),
    'carry': dict(lean=0, arms=((160, 10), (168, -10)), legs=((-14, -4), (14, -2))),
    'point': dict(lean=0, arms=((-6, 8), (95, 5)), legs=((-6, 0), (6, 0)), head=4),
    'point_up': dict(lean=-4, arms=((-6, 8), (140, 5)), legs=((-6, 0), (6, 0)), head=20),
    'laugh': dict(lean=-10, arms=((-20, 40), (30, 80)), legs=((-6, 0), (8, 0)), head=16),
    'look_up': dict(lean=-8, arms=((-10, 10), (20, 30)), legs=((-6, 0), (6, 0)), head=35),
    'fist': dict(lean=6, arms=((-10, 20), (100, 110)), legs=((-8, 0), (10, 0)), head=-4),
    'breast': dict(lean=14, arms=((20, 110), (30, 105)), legs=((-6, 0), (8, 0)), head=-14),
    'run0': dict(lean=18, arms=((50, 70), (-40, 60)), legs=((-40, -60), (60, -30))),
    'run1': dict(lean=18, arms=((-40, 60), (50, 70)), legs=((60, -30), (-40, -60))),
    'pour': dict(lean=8, arms=((60, 40), (110, 20)), legs=((-6, 0), (8, 0))),
    'pull': dict(lean=-24, arms=((80, 0), (90, 0)), legs=((-30, 0), (20, -10))),
    'reach': dict(lean=24, arms=((60, 10), (80, 10)), legs=((-14, 0), (14, 0)), head=-10),
    'torch': dict(lean=4, arms=((-8, 10), (60, -50)), legs=((-6, 0), (8, 0)), head=-8),
    'lie': dict(lean=0, arms=((-10, 6), (10, 6)), legs=((-3, 0), (3, 0))),
}


def blend_pose(p, q, k):
    """A pose part way from p to q (dicts as in POSES)."""
    k = max(0.0, min(1.0, k))
    out = {'lean': lerp(p.get('lean', 0), q.get('lean', 0), k), 'head': lerp(p.get('head', 0), q.get('head', 0), k)}
    for part in ('arms', 'legs'):
        out[part] = tuple(tuple(lerp(a, b, k) for a, b in zip(pa, qa)) for pa, qa in zip(p[part], q[part]))
    for flag in ('seat', 'kneel'):
        out[flag] = q.get(flag, False) if k > 0.5 else p.get(flag, False)
    return out


def walk_pose(t, speed=1.0, run=False):
    a, b = (POSES['run0'], POSES['run1']) if run else (POSES['walk0'], POSES['walk1'])
    return blend_pose(a, b, 0.5 + 0.5 * math.sin(t * speed * (9 if run else 5.5)))


def joints(pose, s=1.0, f=1):
    """Joint positions relative to the hip, screen coordinates (y down)."""
    lean = math.radians(pose.get('lean', 0))
    D = lambda ang, L: (f * math.sin(math.radians(ang)) * L * s, math.cos(math.radians(ang)) * L * s)
    hip = (0.0, 0.0)
    neck = (f * math.sin(lean) * 36 * s, -math.cos(lean) * 36 * s)
    up = (neck[0] / (36 * s), neck[1] / (36 * s))
    ht = math.radians(pose.get('head', 0))
    head = (neck[0] + up[0] * 10 * s + f * 2 * s * math.cos(ht), neck[1] + up[1] * 10 * s - 2 * s * math.sin(ht))
    sh = (neck[0] + (hip[0] - neck[0]) * 0.08, neck[1] + (hip[1] - neck[1]) * 0.08)
    L = math.degrees(lean)
    arms = []
    for (a1, a2) in pose['arms']:
        e = (sh[0] + D(a1 + L, 17)[0], sh[1] + D(a1 + L, 17)[1])
        h = (e[0] + D(a1 + a2 + L, 16)[0], e[1] + D(a1 + a2 + L, 16)[1])
        arms.append((sh, e, h))
    legs = []
    for (l1, l2) in pose['legs']:
        k = (D(l1, 25)[0], D(l1, 25)[1])
        ft = (k[0] + D(l1 + l2, 26)[0], k[1] + D(l1 + l2, 26)[1])
        legs.append((hip, k, ft))
    return dict(hip=hip, neck=neck, head=head, arms=arms, legs=legs, ht=ht)


def fig(g, x, y, s=1.0, col=WHITE, a=1.0, f=1, pose='stand', rot=0.0, robe=0.6, anchor='feet', lw=5.0, glow=True, fill_head=True,
        prop=None, ghost=False):
    """A figure standing on (x, y) (anchor 'feet'), or with its hip at (x, y) (anchor 'hip'). rot turns the whole figure (degrees).
    prop: 'crook', 'spear', 'shield', 'torch', 'staff', 'crown', 'laurel', 'coin' drawn with it. ghost: a dashed outline only."""
    P = POSES[pose] if isinstance(pose, str) else pose
    J = joints(P, s, f)
    if a <= 0.003:
        return J
    if anchor == 'feet':
        if P.get('seat'):
            oy = 0.0
        elif P.get('kneel'):
            oy = -max(J['legs'][0][1][1], J['legs'][1][2][1])
        else:
            oy = -max(l[2][1] for l in J['legs'])
    else:
        oy = 0.0
    c = g.c
    c.save()
    c.translate(x, y + oy if anchor == 'feet' and not P.get('seat') else y)
    if rot:
        c.rotate(math.radians(rot))
    width = lw * s
    dash = [6 * s, 6 * s] if ghost else None
    gl = glow and not ghost
    # the robe: shoulders to just above the knees
    if robe and not ghost:
        n = J['neck']
        k0, k1 = J['legs'][0][1], J['legs'][1][1]
        hem0 = (k0[0] * 0.75, k0[1] * 0.75)
        hem1 = (k1[0] * 0.75, k1[1] * 0.75)
        side = -8 * s * f
        g.path([(n[0] - 7 * s * f, n[1] + 4 * s), (n[0] + 7 * s * f, n[1] + 4 * s), (hem1[0] + 4 * s * f, hem1[1]), (hem0[0] + side * 0.5, hem0[1])],
               fill=(*col, 0.22 * robe), a=a, smooth=False)
    limbs = [([h, k, ft], 1.0) for (h, k, ft) in J['legs']] + [([J['hip'], J['neck']], 1.15)] + [([sh, e, hd], 0.85) for (sh, e, hd) in J['arms']]
    if gl:
        for pts, m in limbs:
            g.line(pts, col, a * 0.13, width * m * 2.3, False)
    for pts, m in limbs:
        g.line(pts, col, a, width * m, False, dash)
    hx, hy = J['head']
    if not ghost:
        ht = J['ht']
        nx, ny = f * math.cos(ht), -math.sin(ht)
        g.path([(hx + nx * 12 * s, hy + ny * 12 * s), (hx + nx * 6 * s - ny * 3 * s, hy + ny * 6 * s + nx * 3 * s * f * f),
                (hx + nx * 6 * s + ny * 3 * s, hy + ny * 6 * s - nx * 3 * s)], fill=(*col, 1), a=a, smooth=False)
    c.new_path()
    c.arc(hx, hy, 8 * s, 0, 2 * math.pi)
    if fill_head and not ghost:
        c.set_source_rgba(*col, a)
        c.fill()
    else:
        c.set_source_rgba(*col, a)
        c.set_line_width(2 * s)
        if dash:
            c.set_dash([4 * s, 4 * s])
        c.stroke()
        c.set_dash([])
    if prop:
        hand = J['arms'][1][2]
        _prop(g, prop, hand, J, s, f, col, a)
    c.restore()
    return J


def _prop(g, prop, hand, J, s, f, col, a):
    hx, hy = hand
    if prop == 'crook':
        g.line([(hx, hy + 30 * s), (hx, hy - 50 * s)], GOLD, a, 2.4 * s, False)
        g.c.new_path()
        g.c.arc(hx + 7 * s * f, hy - 50 * s, 7 * s, math.pi, 0 if f > 0 else math.pi * 2)
        g.c.set_source_rgba(*GOLD, a)
        g.c.set_line_width(2.4 * s)
        g.c.stroke()
    elif prop in ('spear', 'staff'):
        g.line([(hx - 4 * s * f, hy + 40 * s), (hx + 4 * s * f, hy - 60 * s)], GOLD if prop == 'staff' else SILVER, a, 2.4 * s, False)
        if prop == 'spear':
            g.path([(hx + 4 * s * f, hy - 72 * s), (hx + 8 * s * f, hy - 60 * s), (hx, hy - 60 * s)], fill=(*SILVER, 1), a=a, smooth=False)
    elif prop == 'shield':
        g.dot(hx + 3 * s * f, hy, 14 * s, SILVER, a * 0.5, glow=False)
        g.ring(hx + 3 * s * f, hy, 14 * s, SILVER, a, 2.2 * s)
    elif prop == 'torch':
        g.line([(hx, hy), (hx + 10 * s * f, hy - 26 * s)], IRON, a, 3 * s, False)
    elif prop == 'coin':
        g.dot(hx + 4 * s * f, hy - 2 * s, 5 * s, GOLD, a)
    hd = J['head']
    if prop == 'crown' or prop == 'laurel':
        cx, cy = hd[0], hd[1] - 8 * s
        if prop == 'crown':
            g.path([(cx - 9 * s, cy + 2 * s), (cx - 9 * s, cy - 8 * s), (cx - 4 * s, cy - 3 * s), (cx, cy - 10 * s), (cx + 4 * s, cy - 3 * s),
                    (cx + 9 * s, cy - 8 * s), (cx + 9 * s, cy + 2 * s)], fill=(*GOLD, 1), a=a, smooth=False)
        else:
            for k in range(-3, 4):
                ang = math.radians(k * 24 - 90)
                g.dot(cx + math.cos(ang) * 10 * s, cy + 6 * s + math.sin(ang) * 6 * s, 2.6 * s, TEAL, a, glow=False)


def throne(g, x, y, s=1.0, col=GOLD, a=1.0, f=1):
    """A throne seen from the side, its seat at (x, y - 27*s), facing f."""
    P = lambda u, v: (x + f * u * s, y + v * s)
    g.path([P(-26, -30), P(22, -30), P(22, -24), P(-20, -24), P(-20, 0), P(-26, 0)], fill=(*col, 0.35), stroke=col, a=a, lw=2, smooth=False)
    g.path([P(-26, -30), P(-26, -96), P(-14, -106), P(-14, -30)], fill=(*col, 0.25), stroke=col, a=a, lw=2, smooth=False)
    g.line([P(20, -24), P(20, 0)], col, a, 3, False)
    g.dot(*P(-20, -108), 4 * s, col, a)


def seat_y(y, s=1.0):
    return y - 27 * s


def chair_fig(g, x, y, s=1.0, col=WHITE, a=1.0, f=1, pose='sit', prop=None, robe=0.6, tcol=GOLD):
    """A throne with a figure seated on it, the throne standing on y."""
    throne(g, x, y, s, tcol, a, f)
    return fig(g, x - 4 * s * f, seat_y(y, s) - 2 * s, s, col, a, f, pose, anchor='hip', prop=prop, robe=robe)


def bezier(p0, p1, p2, p3, u):
    v = 1 - u
    return (v ** 3 * p0[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u ** 3 * p3[0],
            v ** 3 * p0[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u ** 3 * p3[1])


def flow(g, ctrl, t, col=GOLD, a=1.0, n=7, speed=0.35, prog=1.0, r=3.2, trail=True):
    """Light flowing along a cubic curve ctrl (4 points): a faint trail and dots moving along it; prog draws it out."""
    if a <= 0.003 or prog <= 0:
        return
    pts = [bezier(*ctrl, k / 40 * prog) for k in range(41)]
    if trail:
        g.line(pts, col, a * 0.35, 1.6, glow=True)
    for k in range(n):
        u = (t * speed + k / n) % 1.0
        if u <= prog:
            px, py = bezier(*ctrl, u)
            g.dot(px, py, r, col, a * math.sin(math.pi * u) ** 0.5, glow=True)


def sun(g, x, y, r, t, col=GOLD, a=1.0, rays=16):
    if a <= 0.003:
        return
    c = g.c
    gr = cairo.RadialGradient(x, y, r * 0.2, x, y, r * 4.0)
    gr.add_color_stop_rgba(0, *col, 0.55 * a)
    gr.add_color_stop_rgba(1, *col, 0)
    c.set_source(gr)
    c.arc(x, y, r * 4.0, 0, 2 * math.pi)
    c.fill()
    for k in range(rays):
        ang = k * 2 * math.pi / rays + t * 0.15
        L = r * (1.45 + 0.18 * math.sin(t * 2 + k))
        g.line([(x + math.cos(ang) * r * 1.15, y + math.sin(ang) * r * 1.15), (x + math.cos(ang) * L, y + math.sin(ang) * L)], col, a * 0.8, 2.2)
    g.dot(x, y, r, mix(col, WHITE, 0.45), a, glow=True)


def stars(g, t, a=1.0, n=70, seed=4, box=(0, 0, 1280, 300), col=WHITE):
    if a <= 0.003:
        return
    rng = random.Random(seed)
    x0, y0, x1, y1 = box
    for k in range(n):
        x, y, r, ph = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(0.8, 2.2), rng.uniform(0, 6.3)
        g.dot(x, y, r, col, a * (0.55 + 0.45 * math.sin(t * 1.7 + ph)), glow=r > 1.6)


def moon(g, x, y, r, a=1.0):
    if a <= 0.003:
        return
    g.dot(x, y, r, SILVER, a)
    g.dot(x + r * 0.45, y - r * 0.2, r * 0.92, INK, a, glow=False)


def waves(g, t, y, x0=0, x1=1280, col=CYAN, a=1.0, n=4, amp=7, gap=18):
    for k in range(n):
        pts = [(x, y + k * gap + amp * math.sin(x * 0.018 + t * (1.2 + 0.2 * k) + k)) for x in range(int(x0), int(x1) + 1, 16)]
        g.line(pts, col, a * (0.8 - 0.15 * k), 2.0, glow=k == 0)


def ring_icon(g, x, y, s=1.0, a=1.0, turn=0.0, glow=1.0):
    """The ring: a gold band seen at an angle, its bezel (collet) turning with turn (0 outward, 1 inward)."""
    if a <= 0.003:
        return
    c = g.c
    if glow:
        gr = cairo.RadialGradient(x, y, 0, x, y, 120 * s)
        gr.add_color_stop_rgba(0, *GOLD, 0.25 * a * glow)
        gr.add_color_stop_rgba(1, *GOLD, 0)
        c.set_source(gr)
        c.arc(x, y, 120 * s, 0, 2 * math.pi)
        c.fill()
    c.save()
    c.translate(x, y)
    c.scale(1.0, 0.55)
    c.arc(0, 0, 50 * s, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(*GOLD, a)
    c.set_line_width(9 * s)
    c.stroke()
    ang = math.pi * turn
    bx, by = x + 0, y - 27.5 * s * math.cos(ang)
    front = math.cos(ang) > 0
    g.dot(bx, by, 11 * s, mix(GOLD, WHITE, 0.3), a * (1.0 if front else 0.5))
    g.ring(bx, by, 11 * s, BRONZE, a * (1.0 if front else 0.5), 2.5)


def sheep(g, x, y, s=1.0, a=1.0, t=0.0, ph=0.0):
    if a <= 0.003:
        return
    bob = math.sin(t * 2 + ph) * 1.5 * s
    g.path([(x - 22 * s, y - 14 * s + bob), (x - 14 * s, y - 24 * s + bob), (x + 2 * s, y - 26 * s + bob), (x + 16 * s, y - 20 * s + bob),
            (x + 18 * s, y - 8 * s + bob), (x - 18 * s, y - 6 * s + bob)], fill=(*WHITE, 0.75), a=a)
    g.dot(x + 22 * s, y - 16 * s + bob + math.sin(t + ph) * 3 * s, 5 * s, WHITE, a, glow=False)
    for dx in (-12, -4, 8, 14):
        g.line([(x + dx * s, y - 8 * s), (x + dx * s, y)], WHITE, a, 2.2 * s, False)


def amphora(g, x, y, s=1.0, col=ORANGE, a=1.0, rot=0.0):
    c = g.c
    c.save()
    c.translate(x, y)
    c.rotate(math.radians(rot))
    g.path([(-4 * s, -44 * s), (4 * s, -44 * s), (5 * s, -36 * s), (16 * s, -26 * s), (14 * s, -4 * s), (4 * s, 8 * s), (0, 14 * s),
            (-4 * s, 8 * s), (-14 * s, -4 * s), (-16 * s, -26 * s), (-5 * s, -36 * s)], fill=(*col, 0.4), stroke=col, a=a, lw=2)
    c.restore()


def chain(g, x0, y0, x1, y1, a=1.0, col=MUTED, links=None):
    L = math.hypot(x1 - x0, y1 - y0)
    n = links or max(2, int(L / 9))
    for k in range(n):
        u = (k + 0.5) / n
        x, y = lerp(x0, x1, u), lerp(y0, y1, u)
        c = g.c
        c.save()
        c.translate(x, y)
        c.rotate(math.atan2(y1 - y0, x1 - x0) + (0 if k % 2 else 0))
        c.scale(1.0, 0.55 if k % 2 else 1.0)
        c.arc(0, 0, 4.2, 0, 2 * math.pi)
        c.restore()
        c.set_source_rgba(*col, a)
        c.set_line_width(1.6)
        c.stroke()


def wolf(g, x, y, s=1.0, col=RED, a=1.0, f=1, fill=0.5):
    """A wolf in profile, standing on y, about 230*s long."""
    pts = [(100, -62), (82, -72), (68, -82), (62, -104), (52, -84), (38, -74), (0, -62), (-50, -60), (-82, -56), (-122, -22), (-112, -16), (-86, -40),
           (-80, -20), (-90, 0), (-78, 0), (-68, -16), (-40, -28), (12, -28), (26, -18), (24, 0), (36, 0), (40, -22), (56, -40), (72, -48), (92, -52)]
    g.path([(x + f * u * s, y + v * s) for u, v in pts], fill=(*col, fill), stroke=col, a=a, lw=2, smooth=False)


def lion(g, x, y, s=1.0, col=GOLD, a=1.0, f=1, t=0.0):
    """A lion in profile on y, about 200*s long: body, legs, tail and a rayed mane."""
    if a <= 0.003:
        return
    P = lambda u, v: (x + f * u * s, y + v * s)
    g.path([P(-80, -40), P(-60, -62), P(20, -64), P(50, -58), P(56, -30), P(40, -24), P(-70, -22)], fill=(*col, 0.35), stroke=col, a=a, lw=2)
    for hx in (-66, -50, 30, 46):
        g.line([P(hx, -26), P(hx + 2, 0)], col, a, 6 * s, False)
    g.line([P(-80, -44), P(-110, -60 + 6 * math.sin(t * 2)), P(-118, -82)], col, a, 3 * s, False)
    g.dot(*P(-118, -84), 5 * s, col, a, glow=False)
    mx, my = P(64, -72)
    for k in range(18):
        ang = k * 2 * math.pi / 18
        g.line([(mx + math.cos(ang) * 18 * s, my + math.sin(ang) * 18 * s), (mx + math.cos(ang) * (32 + 3 * math.sin(t * 3 + k)) * s, my + math.sin(ang) * (32 + 3 * math.sin(t * 3 + k)) * s)],
               ORANGE, a, 3 * s, False)
    g.dot(mx, my, 20 * s, col, a, glow=True)
    g.dot(mx + 10 * s * f, my - 4 * s, 2.5 * s, INK, a, glow=False)


def hydra(g, x, y, s=1.0, t=0.0, col=VIOLET, a=1.0, heads=9, wild=None, gentle_col=TEAL, cut=None, grow=1.0, strain=0.0):
    """The many-headed beast: a body with writhing necks. wild: the indices of wild heads (red); cut: their fade 0-1 (pruned)."""
    if a <= 0.003:
        return
    g.path([(x - 60 * s, y), (x - 50 * s, y - 40 * s), (x, y - 52 * s), (x + 50 * s, y - 40 * s), (x + 60 * s, y), (x, y + 14 * s)],
           fill=(*col, 0.35), stroke=col, a=a, lw=2.2)
    for k in range(heads):
        base = (x + (k - (heads - 1) / 2) * 12 * s, y - 40 * s)
        ang0 = math.radians(-90 + (k - (heads - 1) / 2) * (150 / heads))
        L = (70 + 18 * math.sin(k * 2.3)) * s * grow * (1 + 0.25 * strain)
        is_wild = wild is not None and k in wild
        hc = RED if is_wild else (gentle_col if wild is not None else col)
        ha = a * (1 - (cut if (is_wild and cut) else 0.0))
        if ha <= 0.01:
            continue
        pts = []
        for j in range(9):
            u = j / 8
            wob = math.sin(t * (2.4 + k * 0.3) + u * 4 + k) * 12 * s * u
            px = base[0] + math.cos(ang0) * L * u + wob * math.sin(ang0)
            py = base[1] + math.sin(ang0) * L * u - wob * math.cos(ang0) * 0.6
            pts.append((px, py))
        g.line(pts, hc, ha, 4.5 * s, True)
        hx, hy = pts[-1]
        g.dot(hx, hy, 8 * s, hc, ha)
        g.dot(hx + 3 * s * math.cos(ang0 + 0.5), hy + 3 * s * math.sin(ang0 + 0.5), 1.8 * s, INK, ha, glow=False)


def pyre(g, x, y, s=1.0, a=1.0, col=BRONZE):
    for k in range(4):
        yy = y - k * 12 * s
        w = (120 - k * 14) * s
        g.rrect(x - w / 2, yy - 10 * s, w, 10 * s, 4 * s, fill=(*col, 0.5), stroke=col, a=a, lw=1.5)


def column(g, x, y, h, s=1.0, col=WHITE, a=1.0):
    g.rrect(x - 12 * s, y - h, 24 * s, h, 2, fill=(*col, 0.12), stroke=col, a=a * 0.8, lw=1.6)
    for k in (-6, 0, 6):
        g.line([(x + k * s, y - h + 8 * s), (x + k * s, y - 8 * s)], col, a * 0.35, 1.0, False)
    g.rrect(x - 18 * s, y - h - 8 * s, 36 * s, 8 * s, 2, fill=(*col, 0.3), stroke=col, a=a * 0.8, lw=1.4)


def scroll(g, x, y, s=1.0, col=GOLD, a=1.0):
    g.rrect(x - 10 * s, y - 7 * s, 20 * s, 14 * s, 2, fill=(*col, 0.5), stroke=col, a=a, lw=1.2)
    g.line([(x - 6 * s, y - 2 * s), (x + 6 * s, y - 2 * s)], INK, a, 1.2, False)
    g.line([(x - 6 * s, y + 2 * s), (x + 4 * s, y + 2 * s)], INK, a, 1.2, False)


def crown(g, x, y, s=1.0, col=GOLD, a=1.0, sparkle=0.0, t=0.0):
    g.path([(x - 24 * s, y), (x - 26 * s, y - 26 * s), (x - 12 * s, y - 12 * s), (x, y - 32 * s), (x + 12 * s, y - 12 * s), (x + 26 * s, y - 26 * s),
            (x + 24 * s, y)], fill=(*col, 0.6), stroke=col, a=a, lw=2, smooth=False)
    if sparkle > 0:
        for k in range(4):
            ang = t * 1.5 + k * math.pi / 2
            g.dot(x + math.cos(ang) * 34 * s, y - 14 * s + math.sin(ang) * 22 * s, 3 * s, WHITE, a * sparkle)


def shake(t, k, amp=6.0):
    """A jitter offset (x, y) of strength k."""
    return (math.sin(t * 53) * amp * k + math.sin(t * 31) * amp * 0.5 * k, math.cos(t * 47) * amp * 0.6 * k)


def bubble(g, x, y, text, col=WHITE, a=1.0, size=16):
    if a <= 0.003:
        return
    w = g.text_w(text, size) + 22
    g.rrect(x - w / 2, y - size - 10, w, size + 18, (size + 18) / 2, fill=(*INK, 0.85), stroke=col, a=a, lw=1.5)
    g.text(text, x, y + 1, size, col, a, align='c')


def caption(g, text, a=1.0, y=668, size=22, col=WHITE):
    """A centred caption on a soft band near the foot of the frame."""
    if a <= 0.003:
        return
    w = g.text_w(text, size, True) + 48
    g.rrect(640 - w / 2, y - size - 12, w, size + 26, 10, fill=(*INK, 0.78), a=a)
    g.text(text, 640, y + 2, size, col, a, bold=True, align='c')


def horse_statue(g, x, y, s=1.0, col=BRONZE, a=1.0, fill=0.3, f=1):
    """A standing horse like a statue, facing f, standing on y; about 300*s long and 285*s tall."""
    if a <= 0.003:
        return
    P = lambda u, v: (x + f * u * s, y + v * s)
    for pts in (((70, -95), (73, -45), (70, 0)), ((90, -95), (95, -45), (96, 0)), ((-85, -100), (-97, -50), (-88, 0)), ((-62, -95), (-72, -48), (-62, 0))):
        g.line([P(*p) for p in pts], col, a, 13 * s, False)
        g.line([P(pts[-1][0] - 7, 0), P(pts[-1][0] + 8, 0)], col, a, 6 * s, False)
    g.line([P(-108, -132), P(-130, -100), P(-126, -45)], col, a, 8 * s, False)
    body = [(-108, -138), (-80, -152), (-20, -150), (40, -152), (70, -172), (110, -226), (133, -262), (152, -260), (168, -238), (192, -206), (189, -190),
            (171, -186), (142, -198), (116, -170), (102, -130), (90, -96), (60, -82), (-60, -84), (-96, -92), (-112, -112)]
    g.path([P(*p) for p in body], fill=(*col, fill), stroke=col, a=a, lw=2.4)
    g.path([P(138, -262), P(145, -288), P(153, -262)], fill=(*col, 1), a=a, smooth=False)
    g.line([P(108, -226), P(84, -200), P(70, -172)], col, a * 0.6, 4 * s, False)
    g.dot(*P(160, -238), 3 * s, INK, a, glow=False)
