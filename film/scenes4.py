"""The Ring of Gyges IV's story graphics: the eleven INSERT cues of the script, drawn as moving pictures.

    python scenes4.py PHRASES.json OUT_DIR --plans seq1.json,...,seq7.json [--only ID] [--sheet SHEET.png] [--render]
    python scenes4.py PHRASES.json OUT_DIR --index VOICES_DIR/index.json ...   (no plans yet: lines laid end to end)

PLAN lists each graphic: the line it cuts in on, the line it runs to the end of, and beats (words in the lines that
bring each part of the picture on). PHRASES.json (from phrases.py) gives word times within each line. Each graphic is
written as OUT_DIR/ID.mp4 at 24 fps, with OUT_DIR/graphics.json listing them (sequence, start and end in seconds).
"""
import json
import math
import os
import random
import subprocess
import sys

import cairo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import (CYAN, DIM, GOLD, INK, MUTED, ORANGE, RED, TEAL, VIOLET, WHITE, G, ap, ease, lerp, mix)  # noqa: E402
import figs as F  # noqa: E402
from figs import BRONZE, FIRE, IRON, SILVER  # noqa: E402

FPS = 24
PH = {}
SKY = (0.04, 0.07, 0.16)


def word_t(el, word, nth=1, end=False):
    """Seconds into element el's clip where a word (or phrase) starts (or ends)."""
    ws = PH['e%03d' % el]['words']
    if word is None:
        return PH['e%03d' % el]['secs'] if end else 0.0
    toks = word.lower().split()
    hit = 0
    for k in range(len(ws)):
        if all(k + j < len(ws) and toks[j] in ws[k + j][0].lower() for j in range(len(toks))):
            hit += 1
            if hit == nth:
                return ws[k + len(toks) - 1][2] if end else ws[k][1]
    raise KeyError('%s not found in e%03d' % (word, el))


def out(t, t1, d=0.6):
    return 1.0 - ap(t, t1, d)


def win(t, t0, t1, d=0.6):
    """In from t0, out from t1."""
    return ap(t, t0, d) * (1.0 - ap(t, t1, d))


def head(g, t, kicker, title, col=GOLD, fade_at=None):
    """The kicker and title at the top left; fades away from fade_at (for pictures that need the room)."""
    k = 1.0 if fade_at is None else out(t, fade_at, 1.2)
    k1, k2 = ap(t, 0.0, 0.5) * k, ap(t, 0.15, 0.6) * k
    g.text(kicker.upper(), 64, 70, 15, col, k1, bold=True, spacing=3.2)
    g.c.set_source_rgba(*col, 0.8 * k1)
    g.c.rectangle(64, 80, 46 * ap(t, 0, 0.5), 2.5)
    g.c.fill()
    g.text(title, 64 - 14 * (1 - ap(t, 0.15, 0.6)), 124, 40, WHITE, k2, bold=True)


def label(g, x, y, text, col=WHITE, a=1.0, size=18, align='c', sub=None):
    g.text(text, x, y, size, col, a, bold=True, align=align)
    if sub:
        g.text(sub, x, y + size + 4, size - 4, MUTED, a, align=align)


def glow(g, x, y, r, col, a):
    if a <= 0.003:
        return
    gr = cairo.RadialGradient(x, y, 0, x, y, r)
    gr.add_color_stop_rgba(0, *col, a)
    gr.add_color_stop_rgba(1, *col, 0)
    g.c.set_source(gr)
    g.c.arc(x, y, r, 0, 2 * math.pi)
    g.c.fill()


def shade(g, a, col=(0.0, 0.0, 0.0)):
    if a <= 0.003:
        return
    g.c.set_source_rgba(*col, a)
    g.c.paint()


def ground(g, y, a=1.0, col=MUTED, x0=0, x1=1280):
    g.c.set_source_rgba(0.02, 0.04, 0.07, 0.85 * a)
    g.c.rectangle(x0, y, x1 - x0, 720 - y)
    g.c.fill()
    g.line([(x0, y), (x1, y)], col, a * 0.7, 1.6)


# ================================================================ 1. the laws of the strong (Book I)

def s_laws(g, t, B, D):
    g.background(t, GOLD, 61)
    head(g, t, 'Republic, Book I', 'The laws of the strong')
    xs = (250, 640, 1030)
    base = 420
    kt, kr, km = ap(t, B['tyrant'], 0.7), ap(t, B['rich'], 0.7), ap(t, B['many'], 0.7)
    # a tyrant
    F.chair_fig(g, xs[0], base, 1.5, WHITE, kt, 1, 'sit', prop='crown')
    label(g, xs[0], base + 36, 'a tyrant', GOLD, kt)
    # a council of the rich: three on a long bench
    if kr > 0:
        x = xs[1]
        g.path([(x - 95, base - 40), (x + 95, base - 40), (x + 95, base - 34), (x - 95, base - 34)], fill=(*GOLD, 0.35), stroke=GOLD, a=kr, lw=2, smooth=False)
        g.path([(x - 95, base - 40), (x - 95, base - 130), (x - 85, base - 130), (x - 85, base - 40)], fill=(*GOLD, 0.25), stroke=GOLD, a=kr, lw=2, smooth=False)
        for dx in (-62, 0, 62):
            g.line([(x + dx + 30, base - 34), (x + dx + 30, base)], GOLD, kr, 3, False)
            F.fig(g, x + dx - 6, base - 46, 1.15, WHITE, kr, 1, 'sit', anchor='hip', prop='coin')
    label(g, xs[1], base + 36, 'a council of the rich', GOLD, kr)
    # an assembly of the many: rows of heads on tiered benches
    if km > 0:
        x = xs[2]
        for row in range(3):
            y = base - 18 - row * 34
            g.line([(x - 110 + row * 14, y + 4), (x + 110 - row * 14, y + 4)], GOLD, km * 0.8, 2.5, False)
            n = 7 - row
            for k in range(n):
                px = x - 90 + row * 14 + k * (180 - row * 28) / (n - 1)
                bob = math.sin(t * 6 + k * 1.7 + row) * 2 * ap(t, B['many'] + 0.5, 0.5)
                g.person(px, y + bob, 0.48, WHITE, km * ap(t, B['many'] + 0.05 * (k + row * 3), 0.4))
    label(g, xs[2], base + 36, 'an assembly of the many', GOLD, km)
    # the subjects below
    ks = ap(t, B['laws'] - 0.6, 0.8)
    for k in range(17):
        px = 110 + k * (1060 / 16)
        g.person(px, 650, 0.62, MUTED, ks)
    g.text('the subjects', 640, 690, 15, MUTED, ks, align='c')
    # laws stream down from each throne...
    kl = ap(t, B['laws'], 0.8)
    for i, x in enumerate(xs):
        for j, dx in enumerate((-120, 0, 120)):
            F.flow(g, [(x, base + 50), (x, base + 110), (x + dx, base + 120), (x + dx, 595)], t + i * 0.3 + j * 0.2, GOLD, kl, n=5, speed=0.45,
                   prog=min(1.0, max(0.0, (t - B['laws']) / 1.2)))
    # ...and each stream bends back up toward the throne that wrote it
    kb = ap(t, B['bends'], 0.8)
    pb = min(1.0, max(0.0, (t - B['bends']) / 1.6))
    for i, x in enumerate(xs):
        F.flow(g, [(x + 150, 600), (x + 205, 520), (x + 190, base - 140), (x + 60, base - 150)], t + i * 0.4, ORANGE, kb, n=6, speed=0.5, prog=pb, r=3.6)
        if pb > 0.95:
            g.arrow(x + 80, base - 151, x + 55, base - 150, 1.0, ORANGE, kb, lw=2.2)
    kc = ap(t, B['bends'] + 1.8, 0.8)
    F.caption(g, 'justice: the interest of the stronger', kc, 196, 22, ORANGE)


# ================================================================ 2. the shepherd's ring (Book II)

def horse_bronze(g, x, y, s, a, door, inside=0.0):
    """The hollow bronze horse, standing on y, with a door in its flank (door 0 shut, 1 open); inside makes its hull see-through.
    Returns the door's centre."""
    F.horse_statue(g, x, y, s, BRONZE, a, fill=lerp(0.32, 0.1, inside))
    dx, dy, dw, dh = x - 40 * s, y - 136 * s, 64 * s, 42 * s
    g.rrect(dx, dy, dw, dh, 3, fill=(0.0, 0.0, 0.0, 0.6 * door * (1 - inside)), stroke=BRONZE, a=a, lw=2)
    if door < 1:
        w = dw * (1 - door)
        g.rrect(dx, dy, max(2, w), dh, 2, fill=(*BRONZE, 0.55), a=a)
    if door > 0:
        glow(g, dx + dw / 2, dy + dh / 2, 70 * s, GOLD, 0.3 * a * door)
    return dx + dw / 2, dy + dh / 2


def s_ring(g, t, B, D):
    g.background(t, GOLD, 62)
    kA = out(t, B['chasm'] + 0.4, 1.2)
    kB = ap(t, B['chasm'] + 0.4, 1.2) * out(t, B['reascended'], 1.0)
    kC = ap(t, B['reascended'], 1.0) * out(t, B['court'] - 0.4, 0.8)
    kE = ap(t, B['court'] - 0.4, 0.8)
    # ---- A: the hillside, the storm, the earth splitting
    if kA > 0:
        sx, sy = F.shake(t, ap(t, B['quake'], 0.3) * out(t, B['chasm'], 0.8), 7)
        c = g.c
        c.save()
        c.translate(sx, sy)
        ks = ap(t, B['storm'], 1.0)
        for k in range(7):  # storm clouds
            cx = 150 + k * 170 + math.sin(t * 0.3 + k) * 20
            g.path([(cx - 120, 250), (cx - 90, 200), (cx - 20, 185), (cx + 60, 196), (cx + 120, 240), (cx, 262)], fill=(0.25, 0.3, 0.38, 0.7), a=kA * ks)
        rng = random.Random(int(t * 12))
        for k in range(60):  # rain
            x, y = rng.uniform(0, 1280), rng.uniform(250, 560)
            g.line([(x, y), (x - 6, y + 22)], CYAN, kA * ks * 0.35, 1.2, False)
        fl = max(0.0, math.sin((t - B['storm']) * 3.7)) ** 30 * ks
        shade(g, 0.35 * fl * kA, WHITE)
        gy = 470
        split = 140 * ease(min(1.0, max(0.0, (t - B['split']) / 1.6)))
        g.path([(0, gy + 10), (300, gy - 12), (640 - split / 2, gy), (640 - split / 2 - 30 * split / 140, 720), (0, 720)], fill=(0.06, 0.1, 0.12, 1), stroke=MUTED, a=kA, lw=1.5, smooth=False)
        g.path([(640 + split / 2, gy), (980, gy - 16), (1280, gy + 6), (1280, 720), (640 + split / 2 + 30 * split / 140, 720)], fill=(0.06, 0.1, 0.12, 1), stroke=MUTED, a=kA, lw=1.5, smooth=False)
        if split > 2:
            for k in range(6):
                yy = gy + k * 40
                g.line([(640 - split / 2 + k * 5, yy), (640 + split / 2 - k * 5, yy + 20)], (0.0, 0.0, 0.0), kA * 0.5, 2, False)
        sh = ap(t, 0.4, 0.8)
        F.fig(g, 440 - split * 0.4, gy - 6, 1.25, WHITE, kA * sh, 1, 'stand', prop='crook')
        for k, (x, s_) in enumerate(((300, 1.0), (520, 1.1), (580, 0.9), (760, 1.0), (850, 1.15), (220, 0.9))):
            off = -split * 0.4 if x < 640 else split * 0.4
            F.sheep(g, x + off, gy - 2 + (k % 2) * 6, s_, kA * ap(t, 0.6 + k * 0.15, 0.6), t, k)
        label(g, 440 - split * 0.4, gy + 40, 'a young shepherd', GOLD, kA * ap(t, B['shepherd'], 0.6) * out(t, B['split'] + 1.5, 0.6))
        c.restore()
        head(g, t, 'Republic, Book II', "The shepherd's ring", fade_at=B['storm'] + 2.5)
    # ---- B: inside the chasm, the bronze horse and the giant
    if kB > 0:
        g.path([(110, 720), (170, 300), (330, 190), (640, 160), (950, 190), (1120, 300), (1180, 720)], fill=(0.03, 0.05, 0.07, 1), stroke=BRONZE, a=kB * 0.8, lw=1.6)
        ground(g, 610, kB * 0.6, BRONZE, 150, 1150)
        kh = ap(t, B['horse'], 0.8)
        door = ease(min(1.0, max(0.0, (t - B['doors']) / 1.2)))
        kin = ap(t, B['inside'], 0.8)
        hx, hy, hs = 560, 610, 1.45
        dcx, dcy = horse_bronze(g, hx, hy, hs, kB * kh, door, kin)
        label(g, hx, 660, 'a hollow bronze horse, with doors', BRONZE, kB * kh * out(t, B['inside'], 0.6))
        kb = ap(t, B['body'], 1.0)
        gx, gy_ = hx - 6, hy - 118 * hs
        if kin > 0:
            glow(g, gx, gy_, 170, GOLD, 0.12 * kin * kB)
            F.fig(g, gx - 10, gy_, 1.95, SILVER, kB * kb, 1, 'lie', rot=-90, anchor='hip', robe=0.0)
            label(g, hx, 660, 'a dead body, more than human stature', SILVER, kB * kb)
        took = ease(min(1.0, max(0.0, (t - B['took']) / 1.4)))
        sx_ = 790
        F.fig(g, sx_, hy, 1.15, WHITE, kB * ap(t, B['horse'] + 0.8, 0.6), -1, F.blend_pose(F.POSES['reach'], F.POSES['stand'], took), prop='crook')
        kr = ap(t, B['ring'], 0.6)
        hand = (gx + 64, gy_ - 30)
        if kr > 0:
            rx, ry = lerp(hand[0], sx_ - 30, took), lerp(hand[1], hy - 70, took)
            glow(g, rx, ry, 46, GOLD, 0.7 * kr * kB)
            g.dot(rx, ry, 5, GOLD, kr * kB)
            F.ring_icon(g, 1010, 250, 0.9, kB * kr * out(t, B['took'] + 0.6, 0.6), 0.0)
            g.arrow(960, 268, hand[0] + 12, hand[1] - 8, kr, GOLD, kB * kr * 0.8 * out(t, B['took'], 0.4), lw=2, bend=-30)
            label(g, 1010, 330, 'nothing but a ring', GOLD, kB * kr * out(t, B['took'] + 0.6, 0.6))
    # ---- C: among the shepherds, the collet turned
    if kC > 0:
        gy = 520
        ground(g, gy, kC)
        # the king's palace far off, and the monthly report going to it
        kk = ap(t, B['king'], 0.8)
        for k in range(4):
            F.column(g, 1020 + k * 50, gy - 2, 150, 0.8, WHITE, kC * kk)
        g.path([(1000, gy - 160), (1185, gy - 160), (1092, gy - 205)], fill=(*WHITE, 0.12), stroke=WHITE, a=kC * kk * 0.8, lw=1.6, smooth=False)
        label(g, 1095, gy + 34, "the king's court", WHITE, kC * kk, 16)
        u = ((t - B['king']) * 0.35) % 1.0
        if t > B['king']:
            F.scroll(g, lerp(560, 1000, u), gy - 60 - 40 * math.sin(math.pi * u), 1.2, GOLD, kC * kk * math.sin(math.pi * u))
        inv = ap(t, B['invisible'] - 0.3, 0.8) * out(t, B['reappeared'] - 0.2, 0.8)
        places = ((240, -1), (330, -1), (420, 1), (560, 1), (650, -1))
        for k, (x, f) in enumerate(places):
            if k == 2:
                if inv < 1:
                    F.fig(g, x, gy - 14, 1.2, WHITE, kC * (1 - inv), f, 'sit_ground', anchor='hip')
                if inv > 0:
                    F.fig(g, x, gy - 14, 1.2, GOLD, kC * inv * 0.8, f, 'sit_ground', anchor='hip', ghost=True)
                glow(g, x + 40, gy - 30, 30, GOLD, 0.5 * kC * ap(t, B['collet'], 0.4))
            else:
                F.fig(g, x, gy - 14, 1.2, MUTED, kC, f, 'sit_ground', anchor='hip')
        # the ring, close up, its collet turning in and out
        kc = ap(t, B['collet'] - 0.4, 0.6)
        turn = ease(min(1.0, max(0.0, (t - B['collet']) / 1.0))) * (1 - ease(min(1.0, max(0.0, (t - B['outwards']) / 1.0))))
        F.ring_icon(g, 640, 250, 0.85, kC * kc, turn)
        label(g, 640, 330, 'collet turned inward' if turn > 0.5 else 'collet turned outward', GOLD, kC * kc, 16)
        ks = ap(t, B['speak'], 0.5) * out(t, B['reappeared'], 0.6)
        F.bubble(g, 240, gy - 120, 'Where has he gone?', WHITE, kC * ks)
        F.bubble(g, 650, gy - 120, 'He left us.', WHITE, kC * ap(t, B['speak'] + 1.0, 0.5) * out(t, B['reappeared'], 0.6))
        head(g, t, 'Republic, Book II', 'Seen and unseen', fade_at=None) if False else None
    # ---- E: the court, the queen, the king slain, the shepherd crowned
    if kE > 0:
        panels = (('court', 'messengers', 'to the royal court'), ('queen', 'seduced', 'the queen'), ('slain', 'slew', 'the king slain'),
                  ('crowned', 'kingdom', 'the shepherd crowned'))
        for i, (beat, hi, cap) in enumerate(panels):
            x = 70 + i * 290
            k = ap(t, B[beat], 0.7) * kE
            lit = 0.55 + 0.45 * win(t, B[hi], (B[panels[i + 1][1]] if i < 3 else D + 9), 0.4) if t > B.get('messengers', 1e9) else 1.0
            g.rrect(x, 200, 270, 360, 14, fill=(*INK, 0.9), stroke=GOLD, a=k * lit, lw=2.2 if lit > 0.9 else 1.4, glow=lit > 0.9)
            cx, gy = x + 135, 500
            g.line([(x + 14, gy), (x + 256, gy)], MUTED, k * 0.6, 1.4, False)
            if i == 0:
                for j in range(3):
                    F.column(g, x + 60 + j * 75, gy, 190, 0.8, WHITE, k * lit * 0.8)
                F.fig(g, x + 40 + 130 * ap(t, B['court'], 3.0), gy, 1.0, GOLD, k * lit, 1, F.walk_pose(t))
            elif i == 1:
                F.fig(g, cx, gy, 1.4, SILVER, k * lit, -1, 'stand', prop='crown', robe=1.0)
                g.path([(cx - 26, gy - 70), (cx + 26, gy - 70), (cx + 36, gy), (cx - 36, gy)], fill=(*SILVER, 0.25), a=k * lit, smooth=False)
            elif i == 2:
                g.rrect(x + 40, gy - 50, 190, 22, 6, fill=(*WHITE, 0.15), stroke=WHITE, a=k * lit * 0.8, lw=1.4)
                F.fig(g, x + 150, gy - 64, 1.05, RED, k * lit, 1, 'lie', rot=-90, anchor='hip', prop='crown')
                glow(g, x + 150, gy - 70, 70, RED, 0.25 * k * lit)
            else:
                F.chair_fig(g, cx, gy, 1.45, GOLD, k * lit, 1, 'sit', prop='crown')
                glow(g, cx, gy - 120, 50, GOLD, 0.3 * k * lit)
            label(g, cx, 600, cap, GOLD if i != 2 else RED, k, 17)
        head(g, t - B['court'] + 0.4, 'Republic, Book II', 'The ring of Gyges', col=GOLD)


# ================================================================ 3. the city in speech (Book II-IV)

def tiers(g, x, y, s, a, prog=(1, 1, 1), t=0.0, people=True):
    """The city's three classes as stacked tiers; x, y the middle of its base. Returns the tiers' centres."""
    rows = ((300, 110, IRON, 'brass and iron'), (220, 90, SILVER, 'silver'), (140, 80, GOLD, 'gold'))
    cy = y
    centres = []
    for i, (w, h, col, _) in enumerate(rows):
        k = prog[i] * a
        top = cy - h * s
        if k > 0:
            g.path([(x - w * s, cy), (x + w * s, cy), (x + (w - 26) * s, top), (x - (w - 26) * s, top)], fill=(*col, 0.16), stroke=col, a=k, lw=2.2, smooth=False)
            if people:
                n = (7, 5, 3)[i]
                for j in range(n):
                    px = x + (j - (n - 1) / 2) * (w * 1.7 / n) * s
                    kk = k * ap(prog[i], 0.3 + 0.08 * j, 0.3)
                    if i == 0:
                        F.fig(g, px, cy - 8 * s, 0.62 * s, col, kk, 1 if j % 2 else -1, 'stand', prop=('staff', None, 'torch')[j % 3])
                    elif i == 1:
                        F.fig(g, px, cy - 8 * s, 0.62 * s, col, kk, 1, 'stand', prop='shield')
                    else:
                        F.fig(g, px, cy - 8 * s, 0.62 * s, col, kk, 1, 'stand', prop='staff')
        centres.append((x, (cy + top) / 2, w * s))
        cy = top
    return centres


def icon_work(g, kind, x, y, col, a, t=0.0):
    if a <= 0.003:
        return
    if kind == 'farm':
        for k in range(5):
            g.line([(x - 16 + k * 8, y + 22), (x - 10 + k * 5, y - 18)], col, a, 2, False)
            g.dot(x - 10 + k * 5, y - 22, 3.5, col, a, glow=False)
    elif kind == 'build':
        for r in range(3):
            for k in range(3):
                g.rrect(x - 24 + k * 16 + (8 if r % 2 else 0), y + 8 - r * 12, 15, 10, 1, fill=(*col, 0.35), stroke=col, a=a, lw=1.2)
    elif kind == 'weave':
        g.rrect(x - 22, y - 22, 44, 44, 2, stroke=col, a=a, lw=1.8)
        for k in range(5):
            g.line([(x - 15 + k * 7.5, y - 20), (x - 15 + k * 7.5, y + 20)], col, a * 0.7, 1.2, False)
        yy = y - 20 + ((t * 12) % 40)
        g.line([(x - 20, yy), (x + 20, yy)], col, a, 2, False)
    elif kind == 'guard':
        F.shield_icon = None
        g.shield(x, y, 0.45, col, a)
    elif kind == 'rule':
        F.sun(g, x, y, 12, t, col, a, 10)


def s_city(g, t, B, D):
    g.background(t, GOLD, 63)
    head(g, t, 'Republic, Books II to IV', 'The city in speech')
    p0 = ap(t, B['base'], 1.4)
    p1 = ap(t, B['silver'], 1.2)
    p2 = ap(t, B['gold'], 1.2)
    k = ap(t, 0.2, 0.8)
    ctr = tiers(g, 380, 620, 1.15, k, (p0, p1, p2), t)
    labs = (('the producers', 'farmers, builders, weavers', IRON), ('the guardians', 'auxiliaries with their shields', SILVER), ('the rulers', 'the few of gold', GOLD))
    works = ((('farm', 'farming'), ('build', 'building'), ('weave', 'weaving')), (('guard', 'guarding'),), (('rule', 'ruling'),))
    kl = ap(t, B['lines'], 0.8)
    for i, ((cx, cy, w), (name, sub, col), wk, p) in enumerate(zip(ctr, labs, works, (p0, p1, p2))):
        g.text(name, 770, cy - 6, 20, col, p, bold=True)
        g.text(sub, 770, cy + 18, 15, MUTED, p)
        for j, (kind, wl) in enumerate(wk):
            ix = 1140 + (j - (len(wk) - 1) / 2) * 68
            iy = cy + 4
            icon_work(g, kind, ix, iy - 4, col, kl, t)
            g.text(wl, ix, iy + 40, 13, col, kl * 0.9, align='c')
            F.flow(g, [(cx + w * 0.55, cy), (cx + w * 0.9 + 60, cy - 30), (ix - 120, iy - 30), (ix - 32, iy)], t + i * 0.3 + j * 0.2, col, kl, n=4, speed=0.4,
                   prog=min(1.0, max(0.0, (t - B['lines'] - 0.2 * i) / 1.0)), r=2.6)
    F.caption(g, 'one class, one work', ap(t, B['lines'] + 2.2, 0.8), 196, 20, GOLD)


# ================================================================ 4. Leontius (Book IV)

def wall(g, x0, x1, top, base, a, col=MUTED):
    g.c.set_source_rgba(0.07, 0.1, 0.13, a)
    g.c.rectangle(x0, top, x1 - x0, base - top)
    g.c.fill()
    for k in range(int((x1 - x0) / 60) + 1):
        g.rrect(x0 + k * 60, top - 24, 34, 26, 2, fill=(0.07, 0.1, 0.13, 1), stroke=col, a=a * 0.8, lw=1.2)
    for r in range(int((base - top) / 30)):
        y = top + r * 30
        g.line([(x0, y), (x1, y)], col, a * 0.18, 1, False)
        for k in range(int((x1 - x0) / 80) + 1):
            xx = x0 + k * 80 + (40 if r % 2 else 0)
            g.line([(xx, y), (xx, y + 30)], col, a * 0.18, 1, False)
    g.line([(x0, top), (x1, top)], col, a * 0.6, 1.4, False)


def s_leontius(g, t, B, D):
    g.background(t, RED, 64)
    k = ap(t, 0.0, 0.6)
    gy = 600
    wall(g, 0, 1280, 300, gy, k)
    ground(g, gy, k)
    kr = ap(t, B['running'], 1.0)
    glow(g, 1290, 520, 380, RED, 0.35 * kr)
    g.text('outside the north wall', 1240, 650, 15, RED, kr * 0.8, align='r')
    tr, tf = B['running'], B['fist']
    if t < tr:
        pose = F.blend_pose(F.POSES['stand'], F.POSES['hands_eyes'], ap(t, B['hands'] - 0.3, 0.6))
        x = 380
    elif t < tf:
        u = (t - tr) / max(0.5, tf - tr)
        x = lerp(380, 830, ease(u))
        pose = F.walk_pose(t, 1.0, run=True)
    else:
        x = 830
        sh = math.sin(t * 22) * 6 * ap(t, tf, 0.3)
        p = dict(F.POSES['fist'])
        p['arms'] = (p['arms'][0], (p['arms'][1][0] + sh, p['arms'][1][1] - sh))
        pose = F.blend_pose(F.POSES['stand'], p, ap(t, tf, 0.4))
    F.fig(g, x, gy, 1.9, WHITE, ap(t, B['young'] - 0.6, 0.6), 1, pose)
    kf = ap(t, tf + 0.6, 0.6)
    g.text('"Look, ye wretches, take your fill of the fair sight!"', 640, 225, 24, WHITE, kf, italic=True, align='c')
    head(g, t, 'Republic, Book IV', 'Leontius', col=RED)


# ================================================================ 5. the soul writ small (Book IV)

BODY = [(0, 0), (30, 10), (36, 44), (24, 78), (14, 92), (70, 108), (92, 140), (98, 230), (84, 300), (70, 300), (66, 200), (58, 250), (52, 420), (12, 420),
        (4, 290), (-4, 290), (-12, 420), (-52, 420), (-58, 250), (-66, 200), (-70, 300), (-84, 300), (-98, 230), (-92, 140), (-70, 108), (-14, 92), (-24, 78),
        (-36, 44), (-30, 10)]


def body_shards(g, x, y, s, col, a, k, t, seed=5):
    """The body outline broken into pieces flying apart (k 0 whole, 1 scattered)."""
    rng = random.Random(seed)
    pts = [(x + u * s, y + v * s) for u, v in BODY]
    cx, cy = x, y + 200 * s
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = mx - cx, my - cy
        L = math.hypot(dx, dy) or 1
        d = k * (80 + rng.uniform(0, 140))
        rot = k * rng.uniform(-1.5, 1.5)
        ox, oy = dx / L * d, dy / L * d + k * k * 60
        cs, sn = math.cos(rot), math.sin(rot)
        P = lambda pt: (mx + ox + (pt[0] - mx) * cs - (pt[1] - my) * sn, my + oy + (pt[0] - mx) * sn + (pt[1] - my) * cs)
        g.line([P(p), P(q)], col, a * (1 - 0.6 * k), 2.2)


def s_soul(g, t, B, D):
    g.background(t, GOLD, 65)
    head(g, t, 'Republic, Book IV', 'The soul writ small')
    k = ap(t, 0.3, 0.8)
    tiers(g, 250, 560, 0.62, k * out(t, B['steadily'], 1.0) + k * 0.35 * ap(t, B['steadily'], 1.0), (1, 1, 1), t, people=False)
    g.text('the city', 250, 600, 17, MUTED, k, align='c')
    kf = ap(t, B['figure'], 0.8)
    g.arrow(440, 430, 620, 430, kf, GOLD, kf, lw=2.4)
    x, y, s = 820, 205, 1.12
    sh = ap(t, B['shatters'], 1.4)
    shat = ease(min(1.0, max(0.0, (t - B['shatters']) / 1.6)))
    surge = ease(min(1.0, max(0.0, (t - B['surges']) / 1.6)))
    steady = ap(t, B['steadily'], 0.8) * out(t, B['surges'], 0.6)
    if shat <= 0:
        g.body(x, y, s, mix(CYAN, GOLD, steady), kf)
        if steady > 0:
            g.path([(x + u * s, y + v * s) for u, v in BODY], stroke=GOLD, a=steady * (0.6 + 0.25 * math.sin(t * 2.4)), lw=2.6)
    else:
        body_shards(g, x, y, s, RED, kf, shat, t)
        shade(g, 0.25 * win(t, B['shatters'], B['shatters'] + 0.25, 0.15), WHITE)
    regions = (('reason', 'Reason', 'gold, in the head', GOLD, 46), ('spirit', 'Spirit', 'silver, in the chest', SILVER, 160), ('appetite', 'Appetite', 'brass and iron, in the belly', BRONZE, 245))
    for i, (key, name, sub, col, v) in enumerate(regions):
        kk = ap(t, B[key], 0.6) * (1 - shat)
        yy = y + v * s
        if key == 'appetite':
            yy = lerp(yy, y + 60 * s, surge)
            r = lerp(46, 120, surge)
            colr = mix(BRONZE, RED, surge)
            glow(g, x, yy, r, colr, (0.55 + 0.1 * math.sin(t * 9) * surge) * kk)
            g.dot(x, yy, 10 + 8 * surge, colr, kk)
        else:
            pulse = 0.5 + 0.12 * math.sin(t * 2.4 + i) * steady
            glow(g, x, yy, 50, col, pulse * kk * (1 - 0.7 * surge))
            g.dot(x, yy, 9, col, kk * (1 - 0.6 * surge))
        ly = y + v * s
        g.line([(x + 30, ly), (x + 130, ly), (x + 150, ly)], col, kk * 0.7, 1.4, False)
        g.text(name, x + 160, ly - 2, 21, col, ap(t, B[key], 0.6), bold=True)
        g.text(sub, x + 160, ly + 20, 15, MUTED, ap(t, B[key], 0.6))
    F.caption(g, 'each part keeps to its own work', steady, 196, 20, GOLD)
    F.caption(g, 'when appetite rules, the light shatters', ap(t, B['surges'] + 0.3, 0.6), 196, 20, RED)


# ================================================================ 6. the ship of state (Book VI)

def ship(g, t, a, x0=160, x1=1060, deck=470):
    """The hull, mast and sail; returns the deck height at x."""
    bob = math.sin(t * 0.9) * 4
    hull = [(x0 - 30, deck - 30 + bob), (x0 + 40, deck + bob), (x1 - 20, deck + bob), (x1 + 30, deck - 40 + bob), (x1 - 10, deck + 70 + bob), (x0 + 80, deck + 80 + bob)]
    g.path(hull, fill=(0.2, 0.13, 0.08, 0.95), stroke=BRONZE, a=a, lw=2.2, smooth=False)
    for k in range(9):
        xx = x0 + 100 + k * 95
        g.dot(xx, deck + 40 + bob, 4, BRONZE, a * 0.7, glow=False)
    g.line([(x0 - 30, deck - 30 + bob), (x0 - 60, deck - 70 + bob)], BRONZE, a, 4, False)
    mx = (x0 + x1) / 2 - 20
    g.line([(mx, deck + bob), (mx, 165 + bob)], BRONZE, a, 5, False)
    g.line([(mx - 170, 185 + bob), (mx + 170, 185 + bob)], BRONZE, a, 3, False)
    billow = 18 + 6 * math.sin(t * 1.3)
    g.path([(mx - 165, 188 + bob), (mx + 165, 188 + bob), (mx + 150 + billow * 0.3, 360 + bob), (mx, 360 + billow + bob), (mx - 150 - billow * 0.3, 360 + bob)],
           fill=(*WHITE, 0.12), stroke=WHITE, a=a * 0.7, lw=1.6)
    return bob


def s_ship(g, t, B, D):
    g.c.set_source_rgb(0.01, 0.02, 0.05)
    g.c.paint()
    k = ap(t, 0.0, 0.8)
    # the phone frame: in the last line the whole voyage shrinks into a feed
    feed = ease(min(1.0, max(0.0, (t - B['feed']) / 1.4)))
    c = g.c
    c.save()
    sc = 1 - 0.5 * feed
    c.translate(640 * (1 - sc), 360 * (1 - sc) + 10 * feed)
    c.scale(sc, sc)
    F.stars(g, t, k * 0.5 + 0.5 * ap(t, B['stars'], 0.8), 80, 7, (60, 150, 560, 340))
    ks = ap(t, B['stars'], 1.0)
    cons = [(140, 220), (200, 190), (260, 230), (330, 205), (390, 250), (300, 300), (200, 285)]
    g.line(cons[:int(1 + 6 * ks)] + ([cons[int(1 + 6 * ks)]] if ks < 1 and int(1 + 6 * ks) < len(cons) else []), CYAN, ks * 0.8, 1.4)
    for p in cons:
        g.dot(*p, 3, WHITE, ks)
    F.waves(g, t, 560, 0, 1280, CYAN, k * 0.8, 5, 8, 26)
    bob = ship(g, t, k * ap(t, B['ship'] - 0.6, 1.0))
    deck = 470 + bob
    # the captain, dazed, at the stern; the wheel behind him
    kc = ap(t, B['captain'], 0.6)
    wx, wy = 1010, deck - 62
    spin = ap(t, B['mutiny'], 0.6) * (t - B['mutiny']) * 2.2 if t > B['mutiny'] else 0.0
    g.ring(wx, wy, 34, BRONZE, k, 4)
    for j in range(8):
        ang = j * math.pi / 4 + spin + (math.sin(t * 3) * 0.25 * ap(t, B['wheel'], 0.6) if t < B['mutiny'] else 0)
        g.line([(wx, wy), (wx + math.cos(ang) * 44, wy + math.sin(ang) * 44)], BRONZE, k, 2.5, False)
    sway = math.sin(t * 1.8) * 6
    cx = 905
    F.fig(g, cx, deck - 30, 1.3, SILVER, kc, -1, F.blend_pose(F.POSES['sit'], F.POSES['sit_chain'], 0.6 + 0.3 * math.sin(t * 1.8)), anchor='hip', prop='crown')
    g.rrect(cx - 26, deck - 30, 46, 30, 4, fill=(*BRONZE, 0.4), stroke=BRONZE, a=k, lw=1.4)
    kd = ap(t, B['chain'], 0.6)
    for j in range(5):
        ang = t * 2.5 + j * 1.256
        g.dot(cx - 4 + math.cos(ang) * 26, deck - 115 + math.sin(ang) * 8 + sway * 0.2, 3, VIOLET, kc * kd)
    label(g, cx, deck + 120, 'the captain', SILVER, kc * out(t, B['chain'] + 3, 0.6), 16)
    # the crew: pulling at the wheel, pouring wine, then turning to laugh at the bow
    kw = ap(t, B['sailors'], 0.6)
    laugh = ap(t, B['laughs'] - 0.3, 0.5)
    crew = ((780, 1, 'pour'), (700, 1, 'reach'), (620, 1, 'reach'), (840, -1, 'reach'), (965, 1, 'pull'))
    for j, (x, f, pz) in enumerate(crew):
        if j == 4:
            mut = ap(t, B['mutiny'], 0.8)
            pose = F.POSES['pull'] if mut < 0.5 else F.blend_pose(F.POSES['pull'], F.POSES['arms_up'], 0.3 + 0.3 * math.sin(t * 4))
            F.fig(g, x - 30 * (1 - ap(t, B['wheel'], 0.8)), deck, 1.3, GOLD if mut > 0.5 else WHITE, kw * ap(t, B['wheel'] - 0.5, 0.6), 1, pose)
            continue
        if laugh > 0 and j in (1, 2):
            pose = F.blend_pose(F.POSES[pz], F.POSES['point'] if j == 1 else F.POSES['laugh'], laugh)
            ff = -1
        else:
            pose, ff = F.POSES[pz], f
        F.fig(g, x, deck, 1.3, WHITE, kw * ap(t, B['sailors'] + 0.2 * j, 0.5), ff, pose)
    kwine = ap(t, B['wine'], 0.6)
    if kwine > 0:
        F.amphora(g, 832, deck - 118, 0.9, ORANGE, kwine * kw, rot=-115)
        for j in range(6):
            u = ((t * 1.4 + j / 6) % 1.0)
            g.dot(lerp(860, 885, u), lerp(deck - 112, deck - 82, u), 2.6, RED, kwine * kw)
    ksto = ap(t, B['stores'], 0.6)
    for j in range(3):
        F.amphora(g, 470 + j * 50, deck - 4, 0.7, ORANGE, k * 0.9, rot=-80 * ksto * (1 if j != 1 else 0.6))
        if ksto > 0:
            for q in range(3):
                g.dot(470 + j * 50 - 30 - q * 9, deck - 8, 2.2, RED, ksto * 0.7, glow=False)
    for j, (b, word) in enumerate((('laughs', 'ha!'), ('laughs', 'ha ha!'))):
        F.bubble(g, (690, 610)[j], deck - 150 - j * 30, word, WHITE, win(t, B[b] + 0.2 * j, B['chain'] - 0.2, 0.4))
    # the true pilot at the bow, alone, reading the stars
    kp = ap(t, B['bow'], 0.6)
    F.fig(g, 225, deck - 6, 1.3, CYAN, kp, -1, 'look_up')
    glow(g, 225, deck - 80, 90, CYAN, 0.25 * kp * (0.6 + 0.4 * ap(t, B['true'], 0.6)))
    # what the crew calls each of them
    for j, (b, w) in enumerate((('sailor', 'a sailor'), ('pilot', 'a pilot'), ('seaman', 'an able seaman'))):
        g.tag(965, deck - 200 - j * 34, w, GOLD, ap(t, B[b], 0.4) * out(t, B['drug'], 0.6), 15)
    for j, (b, w) in enumerate((('prater', 'a prater'), ('gazer', 'a star-gazer'), ('good', 'a good-for-nothing'))):
        g.tag(250, deck - 200 - j * 34, w, RED, ap(t, B[b], 0.4) * out(t, B['drug'], 0.6), 15)
    c.restore()
    head(g, t, 'Republic, Book VI', 'The ship of state', col=CYAN, fade_at=B['sailors'] + 2.5)
    # the feed
    if feed > 0:
        pw, ph = 1280 * 0.5 + 40, 720 * 0.5 + 120
        px, py = 640 - pw / 2, 370 - ph / 2
        g.rrect(px, py, pw, ph, 34, stroke=WHITE, a=feed, lw=3)
        g.rrect(640 - 50, py + 12, 100, 14, 7, fill=(*WHITE, 0.6), a=feed)
        g.text('♥ 2.4M', px + 30, py + ph - 26, 16, RED, feed, bold=True)
        g.text('the voyage, every night', px + pw - 30, py + ph - 26, 15, MUTED, feed, align='r')
    for j, (b, w) in enumerate((('drug', 'drug the captain'), ('flatter', 'flatter the crew'), ('laugh2', 'laugh at the one who reads the stars'))):
        nxt = (B['flatter'], B['laugh2'], B['feed'])[j]
        F.caption(g, w, win(t, B[b], nxt, 0.35), 690, 22, (RED, GOLD, CYAN)[j])


# ================================================================ 7. the divided line (Book VI)

def tree(g, x, y, s, col, a, fill=0.25):
    g.line([(x, y), (x, y - 60 * s)], col, a, 5 * s, False)
    for (dx, dy, r) in ((0, -82, 30), (-24, -66, 22), (24, -66, 22), (0, -108, 20)):
        g.dot(x + dx * s, y + dy * s, r * s, col, a * fill * 2.4, glow=False)


def s_line(g, t, B, D):
    g.background(t, GOLD, 66)
    head(g, t, 'Republic, Book VI', 'The divided line')
    x = 560
    cuts = (660, 600, 500, 400, 234)
    kl = ap(t, B['line'], 0.8)
    grow = ease(min(1.0, max(0.0, (t - B['line']) / 1.2)))
    ytop = lerp(660, 234, grow)
    g.line([(x, 660), (x, ytop)], mix(DIM, WHITE, 0.5), kl, 4)
    k4 = ap(t, B['four'], 0.6)
    for y in cuts[1:-1]:
        g.line([(x - 22, y), (x + 22, y)], WHITE, k4, 2.5)
    segs = (('shadows', 'shadows and reflections', MUTED), ('things', 'the things that cast them', TEAL),
            ('diagrams', "the mathematician's diagrams", CYAN), ('forms', 'the forms themselves', GOLD))
    for i, (b, name, col) in enumerate(segs):
        k = ap(t, B[b], 0.6)
        y0, y1 = cuts[i], cuts[i + 1]
        g.line([(x, y0 - 3), (x, y1 + 3)], mix(col, WHITE, 0.2 * i), k, 6 + i)
        cy = (y0 + y1) / 2
        ix = x + 110
        if i == 0:
            tree(g, ix - 14, cy + 4, 0.32, (0.25, 0.3, 0.35), k, 0.5)
            g.c.save()
            g.c.translate(0, 2 * (cy + 6))
            g.c.scale(1, -1)
            tree(g, ix + 30, cy + 6, 0.32, CYAN, k * 0.35, 0.3)
            g.c.restore()
            g.line([(ix + 6, cy + 6), (ix + 56, cy + 6)], CYAN, k * 0.6, 1.4, False)
        elif i == 1:
            tree(g, ix, cy + 34, 0.6, TEAL, k)
            g.horse(ix + 70, cy + 20, 0.32, TEAL, k, gallop=t * 3, fill=0.6)
        elif i == 2:
            g.ring(ix + 20, cy, 34, CYAN, k, 2)
            g.path([(ix + 20, cy - 34), (ix + 50, cy + 17), (ix - 10, cy + 17)], stroke=CYAN, a=k, lw=2, smooth=False)
            g.dot(ix + 20, cy, 3, CYAN, k)
        else:
            for j, r in enumerate((44, 30, 16)):
                g.ring(ix + 24, cy, r + 2 * math.sin(t * 2 + j), GOLD, k * (0.5 + 0.2 * j), 2.2)
            glow(g, ix + 24, cy, 70, GOLD, 0.3 * k)
        g.text(name, ix + 110, cy + 7, 21, col, k, bold=True)
    ks = ap(t, B['sun'], 0.8)
    F.sun(g, x, 186, 26 + 4 * math.sin(t * 2), t, GOLD, ks, 18)
    g.text('the good', x + 64, 193, 22, GOLD, ks, bold=True)
    kb = ap(t, B['four'] + 0.8, 0.8)
    for (y0, y1, name) in ((660, 500, 'the visible'), (500, 234, 'the intelligible')):
        g.line([(x - 60, y0 - 4), (x - 74, y0 - 4), (x - 74, y1 + 4), (x - 60, y1 + 4)], MUTED, kb, 1.6, False)
        g.c.save()
        g.c.translate(x - 90, (y0 + y1) / 2)
        g.c.rotate(-math.pi / 2)
        g.text(name, 0, 0, 16, MUTED, kb, bold=True, align='c')
        g.c.restore()
    # light grows upward
    glow(g, x, 234, 260, GOLD, 0.12 * ap(t, B['forms'], 1.0))



# ================================================================ 8. the cave (Book VII)

CAVE_HOLLOW = [(40, 250), (200, 205), (520, 222), (820, 246), (1010, 262), (1100, 226), (1160, 150), (1205, 108), (1250, 118), (1235, 220), (1190, 330),
               (1180, 450), (1200, 560), (1250, 650), (1250, 700), (30, 700), (30, 560)]
PANEL = [(70, 262), (330, 278), (330, 560), (70, 600)]
PRISONERS = (400, 485, 570, 655)
PASSAGE = [(655, 640), (1130, 640), (1162, 520), (1186, 380), (1210, 236), (1222, 132)]
FIRE_XY = (1090, 560)


def along(pts, u):
    """The point a fraction u of the way along a polyline."""
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    d = max(0.0, min(1.0, u)) * sum(segs)
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if d <= L:
            k = d / L if L else 0
            return lerp(a[0], b[0], k), lerp(a[1], b[1], k)
        d -= L
    return pts[-1]


def carried(g, kind, x, y, s, col, a, t=0.0, dark=False):
    """A statue or vessel held up by a carrier, or its shadow (dark)."""
    fl = 1.0 if dark else 0.5
    if kind == 'horse':
        g.horse(x, y + 18 * s, 0.42 * s, col, a, flip=True, gallop=0.8, fill=fl)
    elif kind == 'jar':
        F.amphora(g, x, y + 10 * s, 1.0 * s, col, a)
    elif kind == 'man':
        F.fig(g, x, y + 34 * s, 0.62 * s, col, a, -1, 'point', robe=0.0, glow=not dark)
    elif kind == 'bird':
        fl_ = math.sin(t * 5) * 8
        g.path([(x - 30 * s, y - (6 + fl_) * s), (x - 8 * s, y - 2 * s), (x + 16 * s, y - 4 * s), (x + 26 * s, y - 10 * s), (x + 20 * s, y), (x + 4 * s, y + 6 * s),
                (x - 12 * s, y + 4 * s), (x - 26 * s, y + 10 * s)], fill=(*col, fl), stroke=col, a=a, lw=1.6)
        g.path([(x - 6 * s, y - 2 * s), (x + 4 * s, y - (26 + fl_) * s), (x + 10 * s, y - 2 * s)], fill=(*col, fl), stroke=col, a=a, lw=1.6)


def s_cave(g, t, B, D):
    g.c.set_source_rgb(0.012, 0.012, 0.016)
    g.c.paint()
    kcave = out(t, B['sun1'], 0.25)
    if kcave > 0:
        cave(g, t, B, kcave)
    if t > B['sun1'] - 0.3:
        above(g, t, B, ap(t, B['sun1'], 0.25))
    shade(g, 0.95 * win(t, B['sun1'] - 0.35, B['sun1'] + 0.1, 0.3), WHITE)
    head(g, t, 'Republic, Book VII', 'The cave', col=ORANGE, fade_at=B['prisoners'] + 3.0)


def cave(g, t, B, ka):
    fire_k = ap(t, B['fire'], 0.8) * (1 + 0.6 * ap(t, B['light'], 0.6) * out(t, B['freed'] + 2, 1.0))
    flick = 0.85 + 0.15 * math.sin(t * 11) * math.sin(t * 7.3)
    g.path(CAVE_HOLLOW, fill=(0.06, 0.05, 0.05, 1), stroke=(0.35, 0.28, 0.24), a=ka * ap(t, 0.2, 1.0), lw=2)
    glow(g, FIRE_XY[0], FIRE_XY[1] - 40, 700, FIRE, 0.22 * fire_k * flick * ka)
    # the wall the prisoners face, lit by the fire
    kp = ap(t, B['faces'], 0.8)
    pl = 0.25 + 0.55 * fire_k * flick
    g.path(PANEL, fill=(0.55 * pl, 0.38 * pl, 0.24 * pl, 1), stroke=(0.5, 0.38, 0.3), a=ka * kp, lw=1.5, smooth=False)
    # the shadows of the things carried, sliding across it
    ksh = ap(t, B['shadows'], 1.0) * ka * min(1.0, fire_k)
    carriers = []
    kinds = ('horse', 'jar', 'man', 'bird')
    for j in range(4):
        u = ((t - B['carry']) * 0.075 + j / 4) % 1.0
        x = lerp(1000, 735, u)
        fade = min(1.0, u / 0.08, (1 - u) / 0.08)
        carriers.append((x, kinds[j], fade))
    digital = win(t, B['digital'], B['released'], 0.6)
    for x, kind, fade in carriers:
        sx = lerp(310, 95, (1000 - x) / 265)
        carried(g, kind, sx, 400, 1.9, (0.03, 0.02, 0.02), ksh * fade * 0.9 * kp, t, dark=True)
        kh = digital * fade
        if kh > 0:
            g.text('♥ %dk' % (12 + int(abs(math.sin(x * 0.05)) * 80 + t * 3) % 90), sx, 500, 13, RED, kh * ka, bold=True, align='c')
    kown = ap(t, B['own'], 0.8)
    for j, px in enumerate(PRISONERS):
        sx = lerp(300, 120, j / 3)
        g.dot(sx, 548, 15, (0.03, 0.02, 0.02), ka * kown * kp * 0.9, glow=False)
        g.path([(sx - 26, 600), (sx - 22, 566), (sx, 560), (sx + 22, 566), (sx + 26, 600)], fill=(0.03, 0.02, 0.02, 0.9), a=ka * kown * kp, smooth=False)
    # the echo: voices seem to come from the shadows
    ke = win(t, B['echo'], B['naming'], 0.5)
    for j in range(4):
        ph = ((t * 0.6 + j / 4) % 1.0)
        g.c.new_path()
        g.c.arc(330, 420, 30 + 260 * ph, -0.5, 0.5)
        g.c.set_source_rgba(*CYAN, ka * ke * (1 - ph) * 0.8)
        g.c.set_line_width(2)
        g.c.stroke()
    # the digital cave: the wall becomes a screen
    if digital > 0:
        g.rrect(58, 238, 290, 384, 26, stroke=CYAN, a=ka * digital, lw=3, glow=True)
        g.rrect(173, 248, 60, 9, 4, fill=(*CYAN, 0.7), a=ka * digital)
    # the predictions: which shadow comes next
    kpr = win(t, B['predict'], B['puppeteers'], 0.4)
    g.arrow(110, 330, 300, 330, ap(t, B['predict'], 1.0), GOLD, ka * kpr, lw=2, bend=-20)
    g.tag(205, 300, 'next: a horse?', GOLD, ka * kpr, 14)
    # the raised path, the carriers and the low wall
    kpath = ap(t, B['path'], 0.8)
    g.path([(715, 641), (735, 560), (1010, 560), (1030, 641)], fill=(0.09, 0.075, 0.07, 1), stroke=(0.45, 0.36, 0.3), a=ka * kpath, lw=1.6, smooth=False)
    kc = ap(t, B['carry'], 0.8)
    pup = ap(t, B['puppeteers'], 0.5) * out(t, B['released'], 0.8)
    for j, (x, kind, fade) in enumerate(carriers):
        pose = F.walk_pose(t + j)
        pose = dict(pose, arms=F.POSES['carry']['arms'])
        col = mix(MUTED, RED, pup)
        F.fig(g, x, 560, 1.05, col, ka * kc * fade, -1, pose, robe=0.4)
        carried(g, kind, x - 6, 400, 1.0, mix(BRONZE, WHITE, 0.2), ka * kc * fade, t)
        kt = win(t, B['talking'] + j * 0.5, B['echo'], 0.4) * (j % 2)
        F.bubble(g, x, 360, '...', WHITE, ka * kt * fade, 14)
    g.text('puppeteers', 870, 330, 18, RED, ka * pup, bold=True, align='c')
    kw = ap(t, B['wall'], 0.8)
    scr = ap(t, B['screen'], 0.5) * out(t, B['released'], 0.8)
    g.rrect(722, 505, 290, 56, 3, fill=(0.1, 0.085, 0.08, 1), stroke=mix((0.5, 0.4, 0.32), CYAN, scr), a=ka * kw, lw=1.6 + 1.5 * scr, glow=scr > 0.3)
    for k in range(6):
        g.line([(722 + k * 48, 533), (722 + k * 48 + 24, 533)], (0.4, 0.32, 0.26), ka * kw * 0.5, 1, False)
    # the fire
    F.flame if False else None
    if fire_k > 0:
        g.flame(FIRE_XY[0], FIRE_XY[1], 1.3 * min(1.6, fire_k) * flick, t, ORANGE, ka * min(1.0, fire_k))
        glow(g, FIRE_XY[0], FIRE_XY[1] - 50, 140, GOLD, 0.35 * ka * min(1.0, fire_k))
    kpain = win(t, B['pains'], B['dragged'], 0.4)
    if kpain > 0:
        for k in range(14):
            ang = k * 2 * math.pi / 14 + t * 0.3
            g.line([(FIRE_XY[0] + math.cos(ang) * 70, FIRE_XY[1] - 60 + math.sin(ang) * 70),
                    (FIRE_XY[0] + math.cos(ang) * 190, FIRE_XY[1] - 60 + math.sin(ang) * 190)], WHITE, ka * kpain * 0.6, 2)
    # the passage up to the white opening
    kop = ap(t, B['den'], 1.0)
    g.line([(1130, 641), (1150, 600), (1158, 560), (1175, 520), (1176, 470), (1190, 430), (1192, 380), (1205, 330), (1206, 280), (1218, 236), (1222, 160)],
           (0.45, 0.36, 0.3), ka * kop * 0.7, 2, False)
    bright = 0.5 + 0.5 * ap(t, B['opening'], 1.0)
    glow(g, 1226, 122, 90, WHITE, ka * kop * 0.5 * bright)
    g.dot(1226, 122, 18, WHITE, ka * kop * bright)
    # the prisoners, chained by the legs and neck
    kpr_ = ap(t, B['prisoners'], 0.8)
    kch = ap(t, B['chained'], 0.6)
    necks, feet = [], []
    for j, px in enumerate(PRISONERS):
        free = j == 3
        if free and t > B['released']:
            continue
        crowned = j == 1 and t > B['laurel']
        col = mix(SILVER, GOLD, ap(t, B['honours'], 0.6) if crowned else 0.0)
        J = F.fig(g, px, 640, 1.35, col, ka * kpr_ * ap(t, B['prisoners'] + 0.25 * j, 0.5), -1, 'sit_ground', prop='laurel' if crowned else None)
        hip_y = 640 - max(l[2][1] for l in J['legs'])
        necks.append((px + J['neck'][0], hip_y + J['neck'][1] + 4))
        feet.append((px + J['legs'][1][2][0], 640 - 4))
        if crowned:
            glow(g, px - 4, hip_y - 60, 60, GOLD, 0.3 * ka * ap(t, B['honours'], 0.6))
            kz = ap(t, B['prizes'], 0.5) * out(t, B['released'], 0.6)
            for q in range(5):
                ang = t * 1.4 + q * 1.256
                g.dot(px - 4 + math.cos(ang) * 30, hip_y - 72 + math.sin(ang) * 10, 2.6, GOLD, ka * kz)
    for pts in (necks, feet):
        if len(pts) > 1:
            for a_, b_ in zip(pts, pts[1:]):
                F.chain(g, a_[0], a_[1], b_[0], b_[1], ka * kch, (0.6, 0.55, 0.5))
        if pts:
            F.chain(g, pts[0][0], pts[0][1], 370, pts[0][1] + 6, ka * kch, (0.6, 0.55, 0.5))
    for j, (b, w) in enumerate((('naming', 'A horse!'), ('naming', 'A jar!'), ('laurel', 'He saw it first!'))):
        kb_ = win(t, B[b] + 0.7 * j, B['honours'] + 0.5, 0.3)
        F.bubble(g, PRISONERS[j] - 30, 470 - 26 * (j % 2), w, WHITE, ka * kb_, 14)
    # the freed prisoner: stands, turns to the fire, is dragged up and out
    if t > B['released']:
        brk = win(t, B['released'], B['released'] + 0.8, 0.2)
        for q in range(8):
            ang = q * 0.785
            g.dot(PRISONERS[3] - 20 + math.cos(ang) * 30 * brk, 560 + math.sin(ang) * 30 * brk, 2.4, GOLD, ka * brk)
        up = ap(t, B['stand'], 1.2)
        f = 1 if t > B['turn'] + 0.3 else -1
        pose = F.blend_pose(F.POSES['sit_ground'], F.POSES['stand'], up)
        pose = F.blend_pose(pose, F.POSES['shield_eyes'], ap(t, B['pains'], 0.5))
        u = ease(min(1.0, max(0.0, (t - B['dragged']) / max(1.0, B['sun1'] - B['dragged']))))
        x, y = along(PASSAGE, u)
        wob = math.sin(t * 5) * 8 * ap(t, B['staggers'], 0.4) * out(t, B['dragged'], 0.5)
        if u > 0:
            pose = dict(F.walk_pose(t, 0.8), arms=F.POSES['shield_eyes']['arms'], lean=-6, head=8)
            f = 1
        F.fig(g, x + wob, y, 1.15, WHITE, ka, f, pose)
        kg = ap(t, B['dragged'], 0.6)
        if kg > 0:
            gx, gy = along(PASSAGE, min(1.0, u + 0.07))
            F.fig(g, gx, gy, 1.15, GOLD, ka * kg, 1, dict(F.POSES['pull'], legs=F.walk_pose(t, 0.8)['legs']))
            g.line([(gx - 18, gy - 62), (x + wob + 18, y - 58)], GOLD, ka * kg * 0.8, 2, False)


def above(g, t, B, ka):
    """Above ground: the dazzled man, shadows, reflections, things, the moon and stars, and at last the sun."""
    dawn = ap(t, B['last'], 6.0) * 0.35 + ap(t, B['rising'] - 1.2, 2.4) * 0.65
    top = mix(SKY, (0.32, 0.5, 0.75), dawn)
    low = mix((0.06, 0.09, 0.18), (1.0, 0.62, 0.35), dawn)
    gr = cairo.LinearGradient(0, 0, 0, 470)
    gr.add_color_stop_rgba(0, *top, ka)
    gr.add_color_stop_rgba(1, *low, ka)
    g.c.set_source(gr)
    g.c.rectangle(0, 0, 1280, 470)
    g.c.fill()
    night = ap(t, B['moon'], 1.0) * (1 - dawn)
    F.stars(g, t, ka * (0.25 + 0.75 * night), 110, 11, (0, 0, 1280, 420))
    kh = ap(t, B['heaven'], 1.0) * (1 - dawn)
    cons = [(180, 120), (240, 90), (310, 110), (380, 80), (430, 140)]
    g.line(cons, CYAN, ka * kh * 0.6, 1.2)
    F.moon(g, 300, 210, 30, ka * ap(t, B['moon'], 1.0) * (1 - 0.7 * dawn))
    # the sun, rising at last
    sy = lerp(520, 340, ease(min(1.0, max(0.0, (t - B['rising'] + 1.2) / 2.4))))
    if t > B['rising'] - 1.4:
        F.sun(g, 1060, sy, 40, t, GOLD, ka * ap(t, B['rising'] - 1.4, 1.0))
    glow(g, 1060, 470, 520, (1.0, 0.6, 0.3), 0.45 * dawn * ka)
    # the land
    g.c.set_source_rgba(0.03, 0.05, 0.05, ka)
    g.c.rectangle(0, 470, 1280, 250)
    g.c.fill()
    g.line([(0, 470), (1280, 470)], mix(MUTED, GOLD, dawn), ka * 0.8, 1.6)
    rng = random.Random(3)
    for k in range(70):
        x, y = rng.uniform(0, 1280), rng.uniform(480, 715)
        g.line([(x, y), (x + 3, y - 9)], (0.2, 0.3, 0.25), ka * 0.6, 1.2, False)
    # the tree and its shadow; the pool and what it reflects
    lit = 0.45 + 0.55 * max(ap(t, B['objects'], 0.6) * out(t, B['moon'], 0.8), dawn)
    tcol = mix((0.2, 0.32, 0.3), TEAL, lit)
    ksd = ap(t, B['sh2'], 0.6)
    g.path([(880, 470), (700, 488), (560, 500), (690, 506), (900, 474)], fill=(0.0, 0.0, 0.0, 0.7), a=ka * (0.5 + 0.5 * ksd), smooth=True)
    tree(g, 890, 470, 1.6, tcol, ka)
    px, py, rx, ry = 760, 580, 170, 34
    g.c.save()
    g.c.translate(px, py)
    g.c.scale(1, ry / rx)
    g.c.arc(0, 0, rx, 0, 2 * math.pi)
    g.c.restore()
    g.c.set_source_rgba(0.05, 0.12, 0.2, ka)
    g.c.fill_preserve()
    g.c.set_source_rgba(*CYAN, 0.5 * ka)
    g.c.set_line_width(1.6)
    g.c.stroke()
    kre = ap(t, B['refl'], 0.6)
    g.c.save()
    g.c.translate(px, py)
    g.c.scale(1, ry / rx)
    g.c.arc(0, 0, rx, 0, 2 * math.pi)
    g.c.restore()
    g.c.clip()
    g.c.save()
    g.c.translate(0, 2 * 560)
    g.c.scale(1, -1)
    tree(g, 820, 560 - 30, 0.8, CYAN, ka * (0.25 + 0.5 * kre))
    g.c.restore()
    g.c.reset_clip()
    g.ripples(px, py, 1.2, t, CYAN, ka * 0.4, 3)
    # the freed man
    sched = [(B['sun1'], 'shield_eyes', 1), (B['sh2'], 'kneel', 1), (B['objects'], 'stand', 1), (B['moon'], 'look_up', -1), (B['last'], 'look_up', 1),
             (B['kneels'], 'kneel', 1), (B['stars'], 'look_up', -1), (B['rising'], 'stand', 1)]
    cur, f = F.POSES['shield_eyes'], 1
    for k, (tk, pz, ff) in enumerate(sched):
        if t >= tk:
            prev = F.POSES[sched[k - 1][1]] if k else F.POSES['shield_eyes']
            cur, f = F.blend_pose(prev, F.POSES[pz], ap(t, tk, 0.8)), ff
    F.fig(g, 560, 560, 1.4, WHITE, ka, f, cur)
    for (b, nb, w, x, y, col) in (('sh2', 'refl', 'shadows', 640, 520, MUTED), ('refl', 'objects', 'reflections', 760, 650, CYAN),
                                  ('objects', 'moon', 'the things themselves', 890, 270, TEAL), ('moon', 'last', 'the moon and the stars', 300, 280, SILVER),
                                  ('rising', None, 'the sun', 1060, 300, GOLD)):
        kk = ap(t, B[b], 0.5) * (out(t, B[nb], 0.6) if nb else 1.0)
        g.tag(x, y, w, col, ka * kk, 16)
    shade(g, ka * 0.92 * out(t, B['sun1'] + 0.2, 3.2), WHITE)


# ================================================================ 9. the decline of cities (Book VIII)

def s_decline(g, t, B, D):
    g.background(t, VIOLET, 67)
    head(g, t, 'Republic, Books VIII and IX', 'The decline of cities', col=VIOLET)
    ks = ap(t, B['staircase'], 1.0)
    steps = []
    for i in range(4):
        x0, x1 = 120 + i * 265, 120 + (i + 1) * 265
        y = 330 + i * 92
        steps.append((x0, x1, y))
        g.path([(x0, y), (x1, y), (x1, 720), (x0, 720)], fill=(0.07, 0.09, 0.13, 1), stroke=mix(WHITE, VIOLET, 0.5), a=ks * ap(t, B['staircase'] + 0.25 * i, 0.5), lw=1.6, smooth=False)
    # the darkness below
    gr = cairo.LinearGradient(300, 250, 1150, 720)
    gr.add_color_stop_rgba(0, 0, 0, 0, 0)
    gr.add_color_stop_rgba(1, 0, 0, 0, 0.75 * ap(t, B['darkness'], 1.5))
    g.c.set_source(gr)
    g.c.paint()
    names = (('soldier', 'honour', 'timocracy', GOLD), ('coins', 'wealth', 'oligarchy', ORANGE), ('crowd', 'liberty', 'democracy', CYAN), ('last', 'one man', 'tyranny', RED))
    wolf_k = ap(t, B['wolf'], 1.0)
    grow = ease(min(1.0, max(0.0, (t - B['wolf2']) / 1.8)))
    for i, ((x0, x1, y), (b, rule, name, col)) in enumerate(zip(steps, names)):
        k = ap(t, B[b], 0.7)
        cx = (x0 + x1) / 2
        if i == 3:
            ws = 1.2 + 0.9 * grow
            F.wolf(g, cx + 10, y - 40, 1.2 + 0.4 * grow, RED, k * wolf_k * 0.35 * (1 - grow), 1, fill=0.45)
        if i == 2:
            F.throne(g, cx, y, 1.3, col, k)
            for j in range(6):
                px = cx - 95 + j * 38
                arms = 'arms_up' if (math.sin(t * 5 + j * 1.7) > 0) else 'point'
                F.fig(g, px, y, 0.8, WHITE, k * ap(t, B['crowd'] + 0.12 * j, 0.4), 1 if j < 3 else -1, arms, robe=0.4)
            for j in range(3):
                F.bubble(g, cx - 70 + j * 70, y - 120 - 12 * (j % 2), '!', WHITE, k * ap(t, B['shouting'], 0.4) * (0.6 + 0.4 * math.sin(t * 6 + j)), 14)
        elif i == 3:
            pr = ap(t, B['champion'], 0.8)
            fig_k = k * (1 - grow)
            F.chair_fig(g, cx, y, 1.3, mix(WHITE, RED, grow), fig_k + 0.0001, 1, 'sit', prop='crown' if t > B['protector'] else None, tcol=col)
            g.tag(cx, y - 190, 'protector', GOLD, ap(t, B['protector'], 0.5) * out(t, B['entrails'], 0.6), 15)
            if grow > 0:
                F.wolf(g, cx, y, 0.75, RED, k * grow, 1, fill=0.75)
            if pr > 0 and t < B['protector'] + 1:
                g.arrow(steps[2][1] - 60, steps[2][2] - 140, cx - 20, y - 150, pr, CYAN, k * pr * out(t, B['protector'] + 0.6, 0.5), lw=2, bend=-30)
        else:
            F.chair_fig(g, cx, y, 1.3, WHITE, k, 1, 'sit', prop=('laurel', 'coin')[i], tcol=col)
            if i == 0:
                g.line([(cx + 40, y), (cx + 46, y - 150)], SILVER, k, 2.4, False)
                g.path([(cx + 46, y - 166), (cx + 51, y - 150), (cx + 41, y - 150)], fill=(*SILVER, 1), a=k, smooth=False)
            if i == 1:
                for q in range(int(4 + 3 * math.sin(t * 2) ** 2)):
                    g.dot(cx + 52, y - 6 - q * 7, 6, GOLD, k, glow=False)
        g.text(name, cx, y + 40, 20, col, k, bold=True, align='c')
        g.text('rule of ' + rule, cx, y + 62, 14, MUTED, k, align='c')
    F.caption(g, 'he who tastes the victim becomes a wolf', ap(t, B['wolf2'] + 0.4, 0.6), 196, 20, RED)


# ================================================================ 10. the beast within (Book IX)

def s_beast(g, t, B, D):
    g.background(t, VIOLET, 68)
    head(g, t, 'Republic, Book IX', 'The beast within', col=VIOLET, fade_at=B['fold'])
    fold = ease(min(1.0, max(0.0, (t - B['fold']) / 1.8)))
    skin = ap(t, B['skin'], 1.0)
    strain = ap(t, B['strain'], 0.6) * (0.5 + 0.5 * math.sin(t * 4))
    feast = ap(t, B['feast'], 1.5) * out(t, B['just'], 1.0)
    stronger = ap(t, B['strengthen'], 1.2) * out(t, B['just'], 1.0)
    starve = ap(t, B['starve'], 1.2) * out(t, B['just'], 1.0)
    just = ap(t, B['just'], 1.2)
    feed = ap(t, B['machines'], 1.0)
    bx, by, bs = 640, 105, 1.27
    # the three creatures, first apart, then folded into one human shape
    hx, hy = lerp(290, 640, fold), lerp(560, by + 330 * bs, fold)
    lx, ly = lerp(660, 625, fold), lerp(560, by + 210 * bs, fold)
    mx, my = lerp(990, 640, fold), lerp(560, by + 95 * bs, fold)
    hs = lerp(1.25, 0.85, fold) * (1 + 0.4 * feast + 0.15 * feed)
    ls = lerp(1.0, 0.75, fold) * (1 + 0.3 * stronger)
    ms = lerp(1.0, 0.92, fold) * (1 - 0.45 * starve + 0.1 * just)
    nheads = 9 + (1 if t > B['quarter'] else 0)
    wild = [1, 3, 6, 8, 9] if t > B['husbandman'] else None
    cut = ap(t, B['wild'], 1.0) * out(t, B['machines'], 1.5)
    kb = ap(t, B['beast'], 0.8)
    F.hydra(g, hx, hy, hs, t, VIOLET, kb, heads=nheads, wild=wild, cut=cut, grow=1.0, strain=strain * skin)
    if t > B['quarter']:
        glow(g, hx + 50 * hs, hy - 80 * hs, 40, RED, 0.6 * ap(t, B['quarter'], 0.5) * out(t, B['quarter'] + 1.5, 0.8))
    F.lion(g, lx + 60 * ls, ly, ls, GOLD, ap(t, B['lion'], 0.8), -1, t)
    sway = math.sin(t * 3) * 14 * starve
    F.fig(g, mx + sway, my, ms, mix(WHITE, GOLD, just), ap(t, B['man'], 0.8), 1, 'stand' if not just else 'point', glow=True)
    if fold < 0.3:
        for x, name, b in ((290, 'a many-headed beast', 'beast'), (660, 'a lion', 'lion'), (990, 'a man', 'man')):
            g.text(name, x, 620, 19, WHITE, ap(t, B[b], 0.6) * (1 - fold / 0.3), bold=True, align='c')
    if skin > 0:
        pts = []
        for (u, v) in BODY:
            push = 0.0
            if 220 < v < 300 and abs(u) > 60:
                push = 10 * strain * (1 if u > 0 else -1)
            pts.append((bx + (u + push) * bs, by + v * bs))
        g.path(pts, fill=(*WHITE, 0.05), stroke=WHITE, a=skin * 0.9, lw=2.4)
        g.text('a plain human skin', bx + 160, by + 40, 17, MUTED, skin * out(t, B['feast'], 0.6), bold=True)
    # mastery: reins from the man to the others, the lion his ally
    km = ap(t, B['mastery'], 0.8)
    if km > 0:
        hand = (mx + 26 * ms, my - 64 * ms)
        g.line([hand, (lx + 40, ly - 50)], GOLD, km, 1.8)
        g.line([hand, (hx, hy - 60)], GOLD, km * 0.8, 1.6, dash=[6, 5])
    ka = ap(t, B['ally'], 0.8)
    glow(g, lx + 30, ly - 40, 70, GOLD, 0.4 * ka)
    # feeding: food to the beast, then the machines that feed every head
    if feast > 0.05:
        for j in range(6):
            u = ((t * 0.6 + j / 6) % 1.0)
            g.dot(lerp(1180, hx + 40, u), lerp(470 + 30 * math.sin(j), hy - 30, u), 4, ORANGE, feast * math.sin(math.pi * u))
    if feed > 0:
        for j, (sx_, sy_) in enumerate(((150, 260), (150, 470), (1130, 300), (1130, 520))):
            g.rrect(sx_ - 24, sy_ - 40, 48, 80, 8, fill=(*INK, 0.9), stroke=CYAN, a=feed, lw=2)
            g.rrect(sx_ - 16, sy_ - 30, 32, 52, 3, fill=(*CYAN, 0.25), a=feed)
            for q in range(3):
                u = ((t * 0.7 + q / 3 + j * 0.2) % 1.0)
                g.dot(lerp(sx_, hx + (j - 1.5) * 30, u), lerp(sy_, hy - 70 * hs, u), 3, RED, feed * ap(t, B['feed'], 0.6) * math.sin(math.pi * u))
    for (b, nb, w, col) in (('feast', 'starve', 'feast the beast, strengthen the lion', ORANGE), ('starve', 'just', 'starve the man', RED),
                            ('just', 'machines', 'the just man: the man within is master', GOLD), ('machines', None, 'machines to feed the heads', CYAN)):
        F.caption(g, w, win(t, B[b], B[nb] if nb else D + 9, 0.4), 690, 21, col)


# ================================================================ 11. the myth of Er (Book X)

def lives(g, t, a, which, y=610, dim=None, take=None):
    """The lives laid out on the ground: (kind, x) pairs."""
    for kind, x in which:
        k = a * (0.35 if dim and kind in dim else 1.0)
        if take and kind in take:
            continue
        if kind == 'horse':
            g.horse(x, y - 4, 0.28, WHITE, k, gallop=1.0, fill=0.6)
        elif kind == 'lion':
            F.lion(g, x - 10, y, 0.32, GOLD, k, 1, t)
        elif kind == 'crown':
            F.crown(g, x, y, 0.9, GOLD, k, 1.0, t)
        elif kind == 'lyre':
            g.path([(x - 18, y - 46), (x - 22, y - 10), (x, y), (x + 22, y - 10), (x + 18, y - 46)], closed=False, stroke=SILVER, a=k, lw=2.2)
            for q in range(4):
                g.line([(x - 9 + q * 6, y - 40), (x - 9 + q * 6, y - 6)], SILVER, k * 0.8, 1, False)
            g.line([(x - 20, y - 40), (x + 20, y - 40)], SILVER, k, 2, False)
        elif kind == 'coins':
            for q in range(5):
                g.dot(x + (q % 2) * 6, y - 5 - q * 7, 8, GOLD, k, glow=False)
        elif kind == 'laurel':
            for q in range(9):
                ang = math.radians(q * 30 - 210)
                g.dot(x + math.cos(ang) * 20, y - 22 + math.sin(ang) * 20, 4, TEAL, k, glow=False)
        elif kind == 'plain':
            g.path([(x - 20, y), (x - 20, y - 26), (x, y - 44), (x + 20, y - 26), (x + 20, y)], fill=(*BRONZE, 0.3), stroke=BRONZE, a=k, lw=2, smooth=False)
            g.rrect(x - 6, y - 16, 12, 16, 1, fill=(*BRONZE, 0.6), a=k)


LIVES = (('horse', 260), ('lyre', 380), ('crown', 500), ('coins', 620), ('laurel', 740), ('lion', 860), ('plain', 1040))


def s_er(g, t, B, D):
    g.background(t, TEAL, 69)
    k1 = out(t, B['journey'] - 0.5, 0.8)
    k2 = ap(t, B['journey'] - 0.5, 0.8) * out(t, B['meadow'] - 0.4, 0.8)
    k3 = ap(t, B['meadow'] - 0.4, 0.8) * out(t, B['choose'] - 0.4, 0.8)
    k4 = ap(t, B['choose'] - 0.4, 0.8) * out(t, B['last'] - 0.4, 0.8)
    k5 = ap(t, B['last'] - 0.4, 0.8) * out(t, B['river'] - 0.6, 0.8)
    k6 = ap(t, B['river'] - 0.6, 0.8) * out(t, B['morning'], 1.0)
    k7 = ap(t, B['morning'], 1.0)
    if k1 > 0:
        er_field(g, t, B, k1, 0.0)
    if k7 > 0:
        er_field(g, t, B, k7, 1.0)
    if k2 > 0:
        er_judges(g, t, B, k2)
    if k3 > 0:
        er_spindle(g, t, B, k3)
    if k4 > 0:
        er_choice(g, t, B, k4)
    if k5 > 0:
        er_odysseus(g, t, B, k5)
    if k6 > 0:
        er_river(g, t, B, k6)
    head(g, t, 'Republic, Book X', 'The myth of Er', col=TEAL, fade_at=B['dead'] + 3.0)


def er_field(g, t, B, ka, again):
    """The battlefield and the pyre (again=1: the morning he wakes)."""
    if again:
        dawn = ap(t, B['morning'], 3.0)
        glow(g, 1000, 520, 600, (1.0, 0.6, 0.3), 0.35 * dawn * ka)
    gy = 560
    ground(g, gy, ka)
    rng = random.Random(9)
    if not again:
        for k in range(9):
            x = 120 + k * 125 + rng.uniform(-30, 30)
            if 560 < x < 720:
                continue
            F.fig(g, x, gy - 8, 0.95, MUTED, ka * 0.55 * ap(t, B['dead'], 1.0), 1 if k % 2 else -1, 'lie', rot=-90 if k % 2 else 90, anchor='hip', robe=0.3, glow=False)
            g.line([(x - 40, gy - 2), (x + 30, gy - 22)], IRON, ka * 0.5 * ap(t, B['dead'], 1.0), 2, False)
            g.dot(x + 50, gy - 6, 12, IRON, ka * 0.4 * ap(t, B['dead'], 1.0), glow=False)
    F.pyre(g, 640, gy, 1.4, ka * (ap(t, B['pyre'], 0.8) if not again else 1.0))
    on = ap(t, B['pyre'], 1.2) if not again else 1.0
    bx, by = lerp(460, 640, on), lerp(gy - 8, gy - 64, on)
    F.fig(g, bx, by, 1.05, WHITE, ka * ap(t, B['unmarked'] - 0.4, 0.8), 1, 'lie', rot=-90, anchor='hip', robe=0.5)
    glow(g, bx, by, 80, WHITE, 0.2 * ka * ap(t, B['unmarked'], 0.8))
    if not again:
        kd = ap(t, B['twelfth'], 0.6)
        for q in range(12):
            g.dot(420 + q * 40, 250, 5, GOLD, ka * kd * ap(t, B['twelfth'] + q * 0.08, 0.2))
        g.text('the twelfth day', 640, 225, 20, GOLD, ka * kd, bold=True, align='c')
        ktor = ap(t, B['torch'], 0.6)
        lower = ease(min(1.0, max(0.0, (t - B['torch']) / 2.0)))
        pose = F.blend_pose(F.POSES['torch'], dict(F.POSES['torch'], arms=((-8, 10), (40, -20))), lower)
        J = F.fig(g, 820, gy, 1.3, SILVER, ka * ktor, -1, pose, prop='torch')
        g.flame(820 - 34 - 10 * lower, gy - 118 + 30 * lower, 0.45, t, ORANGE, ka * ktor)
    ke = ap(t, B['eyes'] if not again else B['pyre2'], 0.4)
    op = ease(min(1.0, max(0.0, (t - (B['eyes'] if not again else B['pyre2'])) / 0.9)))
    g.eye(1060, 300, 1.1, WHITE, ka * ke, open_=0.05 + 0.95 * op)
    g.text('he wakes' if again else 'his eyes open', 1060, 370, 17, WHITE, ka * ke, bold=True, align='c')


def er_judges(g, t, B, ka):
    kc = ap(t, B['journey'], 0.8)
    walk = ease(min(1.0, max(0.0, (t - B['journey']) / 4.0)))
    for j in range(7):
        x = lerp(-60, 330, walk) - j * 46
        F.fig(g, x, 470, 0.85, WHITE, ka * kc * out(t, B['openings'] + 1.5, 1.0), 1, F.walk_pose(t + j * 0.4), robe=0.5)
    ko = ap(t, B['openings'], 0.8)
    kh = ap(t, B['heaven'], 0.8)
    for (x, y, col, k) in ((400, 220, GOLD, kh), (880, 220, WHITE, kh), (400, 650, RED, ko), (880, 650, MUTED, ko)):
        g.c.save()
        g.c.translate(x, y)
        g.c.scale(1, 0.25)
        g.c.arc(0, 0, 90, 0, 2 * math.pi)
        g.c.restore()
        g.c.set_source_rgba(*(col if y < 400 else (0.0, 0.0, 0.0)), (0.45 if y < 400 else 0.9) * ka * k)
        g.c.fill_preserve()
        g.c.set_source_rgba(*col, ka * k)
        g.c.set_line_width(2)
        g.c.stroke()
        if y < 400:
            glow(g, x, y, 110, col, 0.25 * ka * k)
    kj = ap(t, B['judges'], 0.8)
    for j in range(3):
        F.chair_fig(g, 570 + j * 70, 470, 0.95, SILVER, ka * kj, 1 if j < 2 else -1, 'sit', tcol=SILVER)
    g.text('the judges', 640, 510, 16, SILVER, ka * kj, bold=True, align='c')
    kf = ap(t, B['judges'] + 1.0, 0.8)
    for ctrl, col in ((((640, 380), (700, 300), (850, 300), (880, 228)), GOLD), (((640, 480), (560, 560), (440, 600), (400, 640)), RED),
                      (((400, 228), (420, 300), (300, 360), (40, 380)), WHITE), (((880, 640), (900, 560), (1050, 520), (1260, 500)), MUTED)):
        F.flow(g, list(ctrl), t, col, ka * kf, n=6, speed=0.3, r=3)
    g.text('up, to heaven', 1010, 290, 15, GOLD, ka * kf, align='c')
    g.text('down, below the earth', 270, 600, 15, RED, ka * kf, align='c')


def er_spindle(g, t, B, ka):
    gy = 620
    ground(g, gy, ka, TEAL)
    km = ap(t, B['meadow'], 0.8)
    rng = random.Random(4)
    for k in range(120):
        x, y = rng.uniform(0, 1280), rng.uniform(gy + 4, 715)
        sw = math.sin(t * 1.5 + x * 0.02) * 3
        g.line([(x, y), (x + sw, y - 12)], TEAL, ka * km * 0.6, 1.4, False)
        if k % 9 == 0:
            g.dot(x + sw, y - 13, 2.5, (GOLD, VIOLET, WHITE)[k % 3], ka * km, glow=False)
    kc = ap(t, B['column'], 1.0)
    if kc > 0:
        cols = ((1.0, 0.35, 0.35), (1.0, 0.6, 0.28), (0.95, 0.85, 0.4), (0.4, 0.9, 0.5), (0.35, 0.75, 1.0), (0.5, 0.45, 1.0), (0.8, 0.5, 1.0))
        rb = ap(t, B['rainbow'], 1.0)
        for j, c_ in enumerate(cols):
            g.c.set_source_rgba(*mix(WHITE, c_, rb), ka * kc * 0.16)
            g.c.rectangle(640 - 35 + j * 10, 0, 10, gy)
            g.c.fill()
        g.c.set_source_rgba(*WHITE, ka * kc * 0.5)
        g.c.rectangle(637, 0, 6, gy)
        g.c.fill()
    ks = ap(t, B['spindle'], 0.8)
    if ks > 0:
        F.chair_fig(g, 400, gy, 2.0, SILVER, ka * ks, 1, 'sit', robe=1.0, tcol=SILVER)
        g.text('Necessity', 400, gy + 40, 18, SILVER, ka * ks, bold=True, align='c')
        g.line([(640, 230), (640, gy - 40)], GOLD, ka * ks, 4)
        whorl_cols = (WHITE, VIOLET, GOLD, ORANGE, CYAN, SILVER, RED, TEAL)
        for j in range(8):
            r = 30 + j * 16
            g.c.save()
            g.c.translate(640, 470)
            g.c.scale(1, 0.26)
            g.c.arc(0, 0, r, 0, 2 * math.pi)
            g.c.restore()
            g.c.set_source_rgba(*whorl_cols[j], ka * ks * 0.7)
            g.c.set_line_width(2)
            g.c.stroke()
            ang = t * (0.9 - j * 0.08) * (1 if j == 0 else -1) + j
            g.dot(640 + math.cos(ang) * r, 470 + math.sin(ang) * r * 0.26, 4, whorl_cols[j], ka * ks)
        g.text('the spindle of Necessity', 640, 600, 16, GOLD, ka * ks, bold=True, align='c')
    kf = ap(t, B['fates'], 0.8)
    for j in range(3):
        x = 880 + j * 120
        F.chair_fig(g, x, gy, 1.15, (GOLD, WHITE, VIOLET)[j], ka * kf * ap(t, B['fates'] + 0.25 * j, 0.5), -1, 'sit', robe=1.0, tcol=(GOLD, WHITE, VIOLET)[j])
        for q in range(3):
            u = ((t * 0.3 + q / 3 + j * 0.2) % 1.0)
            nx, ny = x - 20 + math.sin(u * 6 + j) * 10, gy - 150 - u * 160
            g.dot(nx, ny, 4, (GOLD, WHITE, VIOLET)[j], ka * kf * math.sin(math.pi * u), glow=False)
            g.line([(nx + 4, ny), (nx + 4, ny - 16)], (GOLD, WHITE, VIOLET)[j], ka * kf * math.sin(math.pi * u), 1.4, False)
    g.text('the three Fates, singing', 1000, gy + 40, 16, WHITE, ka * kf, bold=True, align='c')


def er_choice(g, t, B, ka):
    gy = 610
    ground(g, gy, ka, TEAL)
    kp = ap(t, B['prophet'], 0.8)
    F.fig(g, 140, gy, 1.5, SILVER, ka * kp, 1, F.blend_pose(F.POSES['stand'], F.POSES['arms_up'], ap(t, B['lots'], 0.5) * out(t, B['lots'] + 2, 0.6)), robe=1.0)
    g.text('the prophet', 140, gy + 40, 16, SILVER, ka * kp, bold=True, align='c')
    kl = ap(t, B['lots'], 0.4)
    rng = random.Random(12)
    for q in range(18):
        u = ease(min(1.0, max(0.0, (t - B['lots'] - q * 0.04) / 1.2)))
        tx, ty = rng.uniform(260, 1180), rng.uniform(gy + 20, 700)
        g.dot(lerp(150, tx, u), lerp(gy - 140, ty, u) - 120 * math.sin(math.pi * u), 4, WHITE, ka * kl, glow=False)
    ks = ap(t, B['samples'], 0.6)
    taken = t > B['crown'] + 0.3
    for j, (kind, x) in enumerate(LIVES):
        kk = ka * ks * ap(t, B['samples'] + 0.2 * j, 0.5)
        if kind == 'crown' and taken:
            continue
        lives(g, t, kk, [(kind, x)], gy)
    for b, w, y in (('virtue', 'Virtue is free.', 230), ('resp', 'The responsibility is with the chooser.', 268), ('god', 'God is justified.', 306)):
        g.text(w, 640, y, 26 if b == 'resp' else 22, GOLD if b == 'resp' else WHITE, ka * ap(t, B[b], 0.6) * out(t, B['first'] - 0.3, 0.6), bold=b == 'resp', align='c')
    # the first chooser
    kf = ap(t, B['first'], 0.5)
    if kf > 0:
        x = lerp(330, 470, ease(min(1.0, max(0.0, (t - B['first']) / 1.4))))
        dark = ap(t, B['saw'], 1.0)
        beat = ap(t, B['beat'], 0.4)
        if t < B['crown']:
            pose = F.walk_pose(t)
        else:
            pose = F.blend_pose(F.POSES['reach'], F.POSES['stand'], ap(t, B['crown'], 0.6))
            pose = F.blend_pose(pose, F.POSES['breast'], beat)
            if beat > 0:
                pose = dict(pose, lean=pose['lean'] + math.sin(t * 14) * 5)
        J = F.fig(g, x, gy, 1.5, mix(WHITE, MUTED, dark * 0.5), ka * kf, 1, pose, robe=0.6)
        if taken:
            hx, hy = x + J['head'][0], gy - 148
            F.crown(g, hx, hy + 6, 0.55, mix(GOLD, RED, dark), ka * kf, 1.0 - dark, t)
        kfol = ap(t, B['folly'], 0.8)
        glow(g, x + 5, gy - 140, 70, (0.0, 0.0, 0.0), 0.0)
        for q in range(6):
            ang = t * 0.8 + q
            g.dot(x + 6 + math.cos(ang) * 26, gy - 146 + math.sin(ang) * 10, 7, (0.25, 0.2, 0.3), ka * kfol * 0.8, glow=False)
        for j, (w, dx) in enumerate((('chance', -180), ('the gods', 0), ('everything', 180))):
            kb = ap(t, B['blamed'] + 0.35 * j, 0.4) * out(t, B['habit'], 0.6)
            g.arrow(x + 20, gy - 110, x + 160 + dx * 0.4 + 200, gy - 230 - j * 40, kb, RED, ka * kb, lw=2)
            g.tag(x + 200 + dx * 0.4 + 240, gy - 238 - j * 40, w, RED, ka * kb, 15)
        g.tag(x + 10, gy - 230, 'virtue by habit only', MUTED, ka * ap(t, B['habit'], 0.5), 15)
        g.tag(x + 10, gy - 196, 'no philosophy', RED, ka * ap(t, B['philosophy'], 0.5), 15)
        F.caption(g, 'the first chooser takes the greatest tyranny', win(t, B['greatest'], B['blamed'], 0.5), 196, 20, GOLD)


def er_odysseus(g, t, B, ka):
    gy = 610
    ground(g, gy, ka, TEAL)
    left = [(k, x) for k, x in LIVES if k in ('lion', 'plain', 'lyre')]
    lives(g, t, ka, left, gy, dim=('lion', 'lyre') if t > B['neglected'] else None, take=('plain',) if t > B['smiles'] + 0.6 else None)
    walk = min(1.0, max(0.0, (t - B['traveller']) / max(1.0, B['smiles'] - B['traveller'])))
    x = lerp(180, 990, ease(walk))
    stop = t > B['smiles']
    pose = F.walk_pose(t, 0.7) if not stop else F.blend_pose(F.POSES['reach'], F.POSES['stand'], ap(t, B['smiles'] + 0.4, 0.8))
    F.fig(g, x, gy, 1.5, mix(MUTED, WHITE, 0.4), ka * ap(t, B['traveller'] - 0.3, 0.6), 1, pose, prop='staff', robe=0.8)
    if stop:
        kp = ap(t, B['smiles'] + 0.6, 0.6)
        lives(g, t, ka * kp, [('plain', x + 30)], gy - 100)
        glow(g, x + 30, gy - 120, 60, GOLD, 0.5 * ka * ap(t, B['delighted'], 0.8))
    g.text('Odysseus', x, gy + 40, 18, WHITE, ka * ap(t, B['odysseus'], 0.6), bold=True, align='c')
    g.tag(980, 300, 'the life of a private man', BRONZE, ka * ap(t, B['private'], 0.6), 17)
    F.caption(g, 'the last lot, and the best choice', ap(t, B['delighted'], 0.8), 196, 20, GOLD)


def er_river(g, t, B, ka):
    gy = 470
    g.c.set_source_rgba(0.02, 0.05, 0.1, ka)
    g.c.rectangle(0, gy, 1280, 120)
    g.c.fill()
    F.waves(g, t, gy + 30, 0, 1280, CYAN, ka * 0.7, 3, 6, 28)
    ground(g, gy + 120, ka, TEAL)
    g.text('the river of Unmindfulness', 640, gy + 160, 19, CYAN, ka * ap(t, B['river'], 0.6), bold=True, align='c')
    kf = ap(t, B['forgot'], 1.2)
    for j in range(6):
        x = 150 + j * 150
        if j == 4:
            continue
        F.fig(g, x, gy + 2, 1.2, SILVER, ka, 1, F.blend_pose(F.POSES['stand'], F.POSES['kneel'], ap(t, B['river'] + 0.3 * j, 0.8)))
        for q in range(4):
            ang = t * 0.9 + q * 1.57 + j
            g.dot(x + math.cos(ang) * 22, gy - 120 + math.sin(ang) * 8, 3, GOLD, ka * (1 - kf))
    ke = ap(t, B['air'], 0.6)
    x = 1080
    F.fig(g, x, gy - 30, 1.35, WHITE, ka * ke, -1, 'point', robe=0.6)
    glow(g, x, gy - 90, 80, GOLD, 0.35 * ka * ke)
    g.text('Er', x, gy - 222, 22, GOLD, ka * ke, bold=True, align='c')
    g.text('kept from drinking', x, gy - 198, 15, MUTED, ka * ke, align='c')


# ================================================================ the plan

SCENES = {}


def scene(f):
    SCENES[f.__name__[2:]] = f
    return f


for _f in (s_laws, s_ring, s_city, s_leontius, s_soul, s_ship, s_line, s_cave, s_decline, s_beast, s_er):
    scene(_f)

# id, scene, first line, last line, beats {name: (line, word[, nth])}
PLAN = [
    ('g01', 'laws', 75, 75, {'tyrant': (75, 'tyrant'), 'rich': (75, 'rich'), 'many': (75, 'many'), 'laws': (75, 'laws'), 'bends': (75, 'bends')}),
    ('g02', 'ring', 108, 111, {'storm': (108, 'storm'), 'quake': (108, 'earthquake'), 'split': (108, 'split'), 'shepherd': (108, 'shepherd'),
                               'chasm': (108, 'chasm'), 'horse': (108, 'bronze'), 'doors': (108, 'doors'), 'inside': (108, 'Inside'),
                               'body': (108, 'dead body'), 'ring': (108, 'ring'), 'took': (109, 'took'), 'reascended': (109, 'reascended'),
                               'king': (109, 'king'), 'collet': (109, 'collet'), 'invisible': (109, 'invisible'), 'speak': (109, 'speak'),
                               'outwards': (109, 'outwards'), 'reappeared': (109, 'reappeared'), 'court': (110, 'royal court'),
                               'queen': (110, 'queen'), 'slain': (110, 'slain'), 'crowned': (110, 'crowned'), 'messengers': (111, 'messengers'),
                               'seduced': (111, 'seduced'), 'slew': (111, 'slew'), 'kingdom': (111, 'kingdom')}),
    ('g03', 'city', 141, 141, {'base': (141, 'base'), 'silver': (141, 'silver'), 'gold': (141, 'gold'), 'lines': (141, 'Lines of light')}),
    ('g04', 'leontius', 149, 149, {'young': (149, 'young'), 'hands': (149, 'hands'), 'running': (149, 'running'), 'fist': (149, 'fist')}),
    ('g05', 'soul', 152, 152, {'figure': (152, 'single'), 'reason': (152, 'Reason'), 'spirit': (152, 'Spirit'), 'appetite': (152, 'Appetite'),
                               'steadily': (152, 'glows'), 'surges': (152, 'surges'), 'shatters': (152, 'shatters')}),
    ('g06', 'ship', 173, 175, {'ship': (173, 'great ship'), 'sailors': (173, 'Sailors'), 'captain': (173, 'dazed'), 'wheel': (173, 'wheel'),
                               'wine': (173, 'wine'), 'bow': (173, 'bow'), 'stars': (173, 'stars'), 'laughs': (173, 'laughs'),
                               'chain': (174, 'chain up'), 'mutiny': (174, 'mutiny'), 'stores': (174, 'stores'), 'sailor': (174, 'call a sailor'),
                               'pilot': (174, 'pilot', 1), 'seaman': (174, 'able seaman'), 'true': (174, 'true pilot'), 'prater': (174, 'prater'),
                               'gazer': (174, 'star-gazer'), 'good': (174, 'good-for-nothing'), 'drug': (175, 'Drug'), 'flatter': (175, 'Flatter'),
                               'laugh2': (175, 'Laugh'), 'feed': (175, 'feed')}),
    ('g07', 'line', 188, 188, {'line': (188, 'vertical'), 'four': (188, 'four'), 'shadows': (188, 'shadows'), 'things': (188, 'things'),
                               'diagrams': (188, 'diagrams'), 'forms': (188, 'forms'), 'sun': (188, 'blazing')}),
    ('g08', 'cave', 197, 207, {'den': (197, 'underground'), 'prisoners': (197, 'Rows'), 'chained': (197, 'chained'), 'faces': (197, 'faces'),
                               'path': (197, 'raised'), 'wall': (197, 'low wall'), 'fire': (197, 'fire'), 'carry': (197, 'carry'), 'shadows': (197, 'shadows'),
                               'talking': (198, 'talking'), 'own': (200, 'own shadows'), 'echo': (200, 'echo'), 'naming': (201, 'naming'),
                               'laurel': (201, 'laurel'), 'honours': (202, 'honours'), 'predict': (202, 'predict'), 'puppeteers': (203, 'Puppeteers'),
                               'screen': (203, 'screen'), 'prizes': (203, 'Prizes'), 'digital': (203, 'digital'), 'released': (204, 'released'),
                               'stand': (204, 'stand'), 'turn': (204, 'turn'), 'light': (204, 'light'), 'pains': (204, 'pains'), 'freed': (205, 'freed'),
                               'staggers': (205, 'staggers'), 'dragged': (205, 'dragged'), 'opening': (205, 'opening'), 'sun1': (206, 'presence'),
                               'sh2': (206, 'shadows'), 'refl': (206, 'reflections'), 'objects': (206, 'objects themselves'), 'moon': (206, 'moon'),
                               'heaven': (206, 'spangled'), 'last': (206, 'Last of all'), 'kneels': (207, 'kneels'), 'stars': (207, 'stars'),
                               'rising': (207, 'rising')}),
    ('g09', 'decline', 227, 228, {'staircase': (227, 'staircase'), 'darkness': (227, 'darkness'), 'soldier': (227, 'soldier'), 'coins': (227, 'coins'),
                                  'crowd': (227, 'crowd'), 'shouting': (227, 'shouting'), 'last': (227, 'last'), 'wolf': (227, 'wolf'),
                                  'champion': (228, 'champion'), 'protector': (228, 'protector'), 'entrails': (228, 'entrails'), 'wolf2': (228, 'destined')}),
    ('g10', 'beast', 233, 235, {'beast': (233, 'many-headed'), 'lion': (233, 'lion'), 'man': (233, 'small man'), 'fold': (233, 'fold'),
                                'skin': (233, 'skin'), 'strain': (233, 'strain'), 'feast': (234, 'feast'), 'strengthen': (234, 'strengthen'),
                                'starve': (234, 'starve'), 'just': (234, 'just man'), 'mastery': (234, 'mastery'), 'husbandman': (234, 'husbandman'),
                                'wild': (234, 'wild ones'), 'ally': (234, 'ally'), 'machines': (235, 'machines'), 'feed': (235, 'feed'),
                                'quarter': (235, 'quarter')}),
    ('g11', 'er', 247, 255, {'dead': (247, 'dead'), 'unmarked': (247, 'unmarked'), 'pyre': (247, 'pyre'), 'twelfth': (247, 'twelfth'),
                             'torch': (247, 'torch'), 'eyes': (247, 'eyes'), 'journey': (248, 'journey'), 'openings': (248, 'two openings'),
                             'heaven': (248, 'heaven'), 'judges': (248, 'judges'), 'meadow': (249, 'meadow'), 'column': (249, 'column'),
                             'rainbow': (249, 'rainbow'), 'spindle': (249, 'spindle'), 'fates': (249, 'Fates'), 'choose': (250, 'choose'),
                             'prophet': (250, 'prophet'), 'lots': (250, 'lots'), 'samples': (250, 'samples'), 'virtue': (250, 'Virtue is free'),
                             'resp': (250, 'responsibility'), 'god': (250, 'God is'), 'first': (251, 'steps'), 'crown': (251, 'crown'),
                             'greatest': (252, 'greatest'), 'folly': (252, 'folly'), 'saw': (252, 'saw'), 'beat': (252, 'beat'),
                             'blamed': (252, 'blamed'), 'habit': (252, 'habit'), 'philosophy': (252, 'philosophy'), 'last': (253, 'Last'),
                             'traveller': (253, 'traveller'), 'smiles': (253, 'smiles'), 'odysseus': (254, 'Odysseus'), 'private': (254, 'private man'),
                             'neglected': (254, 'neglected'), 'delighted': (254, 'delighted'), 'river': (255, 'river'), 'forgot': (255, 'forgot'),
                             'air': (255, 'alone'), 'morning': (255, 'morning'), 'pyre2': (255, 'pyre')}),
]


import scenes4b  # noqa: E402
scenes4b.register(sys.modules[__name__])


def windows(items_by_el):
    """Each graphic's place: {id, scene, seq, t0, t1 (seconds in its sequence), beats (seconds from t0)}.
    items_by_el maps element -> (seq, start of its line in the sequence)."""
    res = []
    for gid, scene_, e0, e1, beats in PLAN:
        if e0 not in items_by_el:
            continue
        while e1 > e0 and e1 not in items_by_el:      # a cut line at the end: the graphic ends on the last line kept
            e1 -= 1
        s0, it0 = items_by_el[e0]
        _, it1 = items_by_el[e1]
        t0 = it0 - 0.3
        t1 = it1 + word_t(e1, None, end=True) + 0.4
        B = {}
        for name, spec in beats.items():
            e, w = spec[0], spec[1]
            if e not in items_by_el:          # a beat on a cut line never comes
                B[name] = 1e9
                continue
            B[name] = round(items_by_el[e][1] + word_t(e, w, spec[2] if len(spec) > 2 else 1) - t0, 3)
        res.append({'id': gid, 'scene': scene_, 'seq': s0, 'first': e0, 'last': e1, 't0': round(t0, 3), 't1': round(t1, 3), 'beats': B})
    return res


def render(w, out_path, size=(1280, 720)):
    D = w['t1'] - w['t0']
    n = int(round(D * FPS))
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % size, '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', out_path], stdin=subprocess.PIPE)
    fn = SCENES[w['scene']]
    for k in range(n):
        g = G(*size)
        fn(g, k / FPS, w['beats'], D)
        # fade in and out over a third of a second, so each graphic dissolves from and to the scene
        e = min(1.0, k / (FPS / 3), (n - 1 - k) / (FPS / 3))
        if e < 1:
            g.c.set_source_rgba(0, 0, 0, 1 - e)
            g.c.paint()
        p.stdin.write(g.rgb().tobytes())
    p.stdin.close()
    p.wait()
    return n


def still(w, t, size=(1280, 720)):
    g = G(*size)
    SCENES[w['scene']](g, t, w['beats'], w['t1'] - w['t0'])
    return g


def end_to_end(index):
    """Line starts when there is no plan yet: each window's lines laid end to end, 0.5 s apart."""
    items = {}
    for gid, scene_, e0, e1, beats in PLAN:
        t = 0.0
        for e in range(e0, e1 + 1):
            k = 'e%03d' % e
            if k in index:
                items[e] = (0, t)
                t += index[k]['secs'] + 0.5
    return items


if __name__ == '__main__':
    PH.update(json.load(open(sys.argv[1])))
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    arg = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    if arg('--plans'):
        items = {}
        for p in arg('--plans').split(','):
            pl = json.load(open(p))
            for (i, who, t, secs) in pl['items']:
                items[i] = (pl['seq'], t)
    else:
        items = end_to_end(json.load(open(arg('--index'))))
    wins = windows(items)
    json.dump(wins, open(os.path.join(out_dir, 'graphics.json'), 'w'), indent=1)
    only = arg('--only').split(',') if arg('--only') else None
    sel = [w for w in wins if not only or w['id'] in only]
    if arg('--sheet'):
        from PIL import Image
        at = [float(v) for v in arg('--at').split(',')] if arg('--at') else None
        ims = []
        for w in sel:
            for tt in (at or [w['t1'] - w['t0'] - 0.4]):
                ims.append(Image.fromarray(still(w, tt if tt >= 0 else w['t1'] - w['t0'] + tt, (640, 360)).rgb()))
        cols = 3
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new('RGB', (640 * cols, 360 * rows))
        for k, im in enumerate(ims):
            sheet.paste(im, ((k % cols) * 640, (k // cols) * 360))
        sheet.save(arg('--sheet'))
        print('sheet', len(ims))
    if arg('--beats'):
        for w in sel:
            print(w['id'], round(w['t1'] - w['t0'], 1), w['beats'])
    if '--render' in sys.argv:
        tot = 0
        for w in sel:
            tot += render(w, os.path.join(out_dir, w['id'] + '.mp4'))
        print('rendered', tot, 'frames')
    print(len(wins), 'graphics, %.1f s in all' % sum(w['t1'] - w['t0'] for w in wins))
