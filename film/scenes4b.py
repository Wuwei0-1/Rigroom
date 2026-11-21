"""More story graphics for The Ring of Gyges IV: eighteen pictures over the arguments of every book.

scenes4.py calls register(itself) after its own PLAN, which adds these scenes and their places to SCENES and PLAN.
"""
import math
import random

from gfx import CYAN, DIM, GOLD, INK, MUTED, ORANGE, RED, TEAL, VIOLET, WHITE, ap, ease, lerp, mix  # noqa: F401
import figs as F
from figs import BRONZE, IRON, SILVER

M = None      # scenes4, once registered


def u(t, a, d):
    """0 to 1 over d seconds from a, eased."""
    return ease(min(1.0, max(0.0, (t - a) / d)))


def check(g, x, y, a, col=GOLD):
    g.line([(x - 10, y), (x - 2, y + 9), (x + 13, y - 10)], col, a, 3.5, False)


def cross(g, x, y, s, a, col=RED):
    g.line([(x - s, y - s), (x + s, y + s)], col, a, 5)
    g.line([(x - s, y + s), (x + s, y - s)], col, a, 5)


def sword(g, x, y, s, a, rot=0.0, col=SILVER):
    c = g.c
    c.save()
    c.translate(x, y)
    c.rotate(math.radians(rot))
    g.path([(0, -70 * s), (6 * s, -60 * s), (5 * s, 0), (-5 * s, 0), (-6 * s, -60 * s)], fill=(*col, 0.7), stroke=col, a=a, lw=1.6, smooth=False)
    g.line([(-16 * s, 0), (16 * s, 0)], GOLD, a, 4 * s, False)
    g.line([(0, 0), (0, 18 * s)], BRONZE, a, 5 * s, False)
    c.restore()


def house(g, x, y, s, col, a, lit=0.0):
    g.path([(x - 40 * s, y), (x - 40 * s, y - 50 * s), (x, y - 82 * s), (x + 40 * s, y - 50 * s), (x + 40 * s, y)], fill=(*col, 0.15 + 0.3 * lit), stroke=col, a=a, lw=2, smooth=False)
    g.rrect(x - 9 * s, y - 30 * s, 18 * s, 30 * s, 2, fill=(*mix(INK, GOLD, lit), 0.9), a=a)
    if lit > 0:
        M.glow(g, x, y - 40 * s, 90 * s, GOLD, 0.35 * lit * a)


# ---------------------------------------------------------------- Book I

def s_deposit(g, t, B, D):
    g.background(t, GOLD, 71)
    M.head(g, t, 'Republic, Book I', 'Truth and debts')
    for k, (b, w) in enumerate((('truth', 'speak the truth'), ('debts', 'pay your debts'))):
        kk = ap(t, B[b], 0.5)
        g.text(w, 160, 220 + k * 44, 26, WHITE, kk, bold=True)
        check(g, 130, 211 + k * 44, kk * out_(t, B['mind'] + 0.6), GOLD)
        cross(g, 130, 211 + k * 44, 10, kk * ap(t, B['give'] + 0.8, 0.5))
    gy = 590
    M.ground(g, gy, ap(t, 0.2, 0.6))
    sx = 860
    F.fig(g, sx, gy, 1.7, SILVER, ap(t, B['deposited'] - 0.8, 0.6), -1, 'stand', robe=1.0)
    g.text('Socrates', sx, gy + 36, 17, SILVER, ap(t, B['deposited'] - 0.8, 0.6), bold=True, align='c')
    hand_over = u(t, B['deposited'], 1.4)
    mad = ap(t, B['mind'], 0.6)
    walk_back = u(t, B['deposited'] + 1.8, 1.4)
    fx = lerp(lerp(380, 700, u(t, B['deposited'] - 1.0, 1.2)), 520, walk_back) + lerp(0, 120, u(t, B['mind'], 1.2))
    sh = F.shake(t, mad * 0.7, 4)
    col = mix(WHITE, RED, mad)
    pose = 'stand' if mad < 0.5 else F.blend_pose(F.POSES['reach'], F.POSES['fist'], 0.5 + 0.5 * math.sin(t * 6))
    F.fig(g, fx + sh[0], gy + sh[1], 1.6, col, ap(t, B['deposited'] - 1.2, 0.6), 1, pose)
    g.text('a friend' if mad < 0.5 else 'the same friend, out of his mind', fx, gy + 36, 17, col, ap(t, B['deposited'] - 1.2, 0.6), bold=True, align='c')
    # the sword: carried over and left with Socrates
    swx = lerp(fx + 30, sx - 40, hand_over)
    sword(g, swx, gy - 100 - 20 * math.sin(math.pi * hand_over), 1.0, ap(t, B['deposited'] - 1.2, 0.6), rot=-30 + 30 * hand_over)
    if mad > 0:
        M.glow(g, fx + sh[0], gy - 130, 80, RED, 0.3 * mad)
        F.bubble(g, fx + 40, gy - 230, 'Give me my sword!', RED, ap(t, B['mind'] + 1.0, 0.4), 18)
    F.caption(g, 'Ought I to give it back to him?', ap(t, B['give'], 0.5), 196 + 0, 22, GOLD) if False else None
    kq = ap(t, B['give'], 0.5)
    g.text('?', sx - 40, gy - 210, 70, GOLD, kq, bold=True, align='c')


def out_(t, t1, d=0.6):
    return 1.0 - ap(t, t1, d)


def s_friends(g, t, B, D):
    g.background(t, TEAL, 72)
    M.head(g, t, 'Republic, Book I', 'Help friends, harm enemies')
    gy = 560
    M.ground(g, gy, ap(t, 0.2, 0.6))
    kc = ap(t, 0.3, 0.6)
    F.fig(g, 640, gy, 1.6, WHITE, kc, 1, 'stand', robe=0.8)
    g.text("Polemarchus's just man", 640, gy + 36, 17, WHITE, kc, bold=True, align='c')
    kf = ap(t, B['friend'], 0.6)
    ke = ap(t, B['enemy'], 0.6)
    for k in range(3):
        x = 230 + k * 85
        F.fig(g, x, gy, 1.2, TEAL, kf * ap(t, B['friend'] + 0.15 * k, 0.4), 1, 'stand' if t < B['friend'] + 1.5 else 'arms_up')
        F.flow(g, [(610, gy - 110), (520, gy - 200), (x + 60, gy - 200), (x, gy - 120)], t + k * 0.3, GOLD, kf, n=5, speed=0.4, prog=u(t, B['friend'] + 0.3, 1.0))
        xe = 860 + k * 85
        hurt = ap(t, B['evil'], 0.6)
        F.fig(g, xe, gy, 1.2, RED, ke * ap(t, B['enemy'] + 0.15 * k, 0.4), -1, F.blend_pose(F.POSES['stand'], F.POSES['breast'], hurt))
        F.flow(g, [(670, gy - 110), (760, gy - 200), (xe - 60, gy - 200), (xe, gy - 120)], t + k * 0.3, RED, ke, n=5, speed=0.55, prog=u(t, B['enemy'] + 0.3, 1.0))
    g.text('friends: good', 315, gy + 36, 18, TEAL, kf, bold=True, align='c')
    g.text('enemies: harm', 945, gy + 36, 18, RED, ke, bold=True, align='c')
    F.caption(g, 'justice, says Polemarchus: good to friends, harm to enemies', ap(t, B['justice'], 0.6), 196, 20, GOLD)


def s_craft(g, t, B, D):
    g.background(t, CYAN, 73)
    M.head(g, t, 'Republic, Book I', 'Every art serves its subject')
    rows = (('physician', 'patient', 'the physician', 'heals the sick', 250), ('pilot', 'sailor', 'the true pilot', 'rules for the sailors', 390),
            ('science', 'science', 'every art', 'serves the weaker, not itself', 530))
    for k, (b, b2, name, verb, y) in enumerate(rows):
        kk = ap(t, B[b], 0.6)
        F.fig(g, 300, y + 50, 1.0, GOLD, kk, 1, 'point' if k < 2 else 'stand', robe=0.7, prop=('staff', None, None)[k])
        g.text(name, 300, y + 80, 16, GOLD, kk, bold=True, align='c')
        ks = ap(t, B[b2] + 0.4, 0.6)
        if k == 0:
            g.rrect(800, y + 22, 150, 26, 6, fill=(*WHITE, 0.15), stroke=WHITE, a=ks, lw=1.4)
            F.fig(g, 875, y + 18, 0.95, SILVER, ks, 1, 'lie', rot=-90, anchor='hip', robe=0.3)
            g.line([(980, y), (980, y + 24)], TEAL, ks, 6, False)
            g.line([(968, y + 12), (992, y + 12)], TEAL, ks, 6, False)
        elif k == 1:
            for j in range(4):
                F.fig(g, 790 + j * 55, y + 50, 0.9, SILVER, ks * ap(t, B[b2] + 0.4 + 0.1 * j, 0.4), -1, 'stand')
            F.waves(g, t, y + 62, 760, 1040, CYAN, ks * 0.6, 2, 4, 12)
        else:
            for j in range(5):
                g.person(780 + j * 55, y + 50, 0.6, SILVER, ks)
        F.flow(g, [(360, y + 10), (480, y - 20), (640, y - 20), (760, y + 10)], t + k * 0.4, GOLD, ap(t, B[b2], 0.6), n=6, speed=0.4, prog=u(t, B[b2], 1.2))
        g.text(verb, 560, y - 34, 16, MUTED, ks, align='c')
    kc = ap(t, B['science'] + 1.5, 0.6)
    g.text('the interest of the stronger?', 1110, 300, 18, RED, kc, bold=True, align='c')
    cross(g, 1110, 340, 22, kc)


def s_shepherd(g, t, B, D):
    g.background(t, ORANGE, 74)
    M.head(g, t, 'Republic, Book I', "Thrasymachus's shepherd", col=ORANGE)
    gy = 560
    M.ground(g, gy, ap(t, 0.2, 0.6))
    ks = ap(t, B['shepherd'], 0.6)
    F.fig(g, 330, gy, 1.6, WHITE, ks, 1, 'stand', prop='crook')
    g.text('the shepherd', 330, gy + 36, 17, WHITE, ks, bold=True, align='c')
    fat = u(t, B['fattens'], 2.0)
    turn = ap(t, B['rulers'], 0.8)
    for k in range(5):
        x = 540 + k * 115
        y = gy - 2 + (k % 2) * 8
        s_ = 1.1 + 0.5 * fat
        if turn < 1:
            F.sheep(g, x, y, s_, ks * ap(t, B['shepherd'] + 0.2 * k, 0.5) * (1 - turn), t, k)
        if turn > 0:
            g.person(x, y - 8, 0.85, SILVER, turn * ks)
    km = ap(t, B['master'], 0.6)
    for k in range(5):
        F.flow(g, [(540 + k * 115, gy - 70), (520 + k * 80, gy - 220), (380, gy - 250), (330, gy - 170)], t + k * 0.25, GOLD, km, n=4, speed=0.4, prog=u(t, B['master'], 1.2), r=3.5)
    g.text('for himself, and his master', 450, gy - 270, 18, GOLD, km, bold=True, align='c')
    F.caption(g, 'rulers see their subjects as sheep', ap(t, B['rulers'] + 0.6, 0.6), 196, 20, ORANGE)
    if turn > 0:
        F.crown(g, 330, gy - 142, 0.6, GOLD, turn * ks, 0.5, t)


def s_band(g, t, B, D):
    g.background(t, RED, 75)
    M.head(g, t, 'Republic, Book I', 'Even a band of thieves', col=RED)
    cx, cy, R = 470, 410, 150
    kr = ap(t, B['robbers'], 0.6)
    broke = ap(t, B['injured'], 0.8) * (1 - ap(t, B['harmony'], 0.8))
    harm = ap(t, B['harmony'], 0.8)
    pts = []
    for k in range(7):
        ang = -math.pi / 2 + k * 2 * math.pi / 7
        x, y = cx + math.cos(ang) * R, cy + math.sin(ang) * R
        sh = F.shake(t + k, broke * 0.5, 4)
        pts.append((x + sh[0], y + sh[1]))
        g.person(x + sh[0], y + 40 + sh[1], 0.75, mix(WHITE, RED, broke), kr * ap(t, B['robbers'] + 0.1 * k, 0.4))
    for k in range(7):
        a_, b_ = pts[k], pts[(k + 1) % 7]
        if broke > 0.5:
            mx, my = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2
            g.line([a_, (lerp(a_[0], mx, 0.7), lerp(a_[1], my, 0.7))], RED, kr, 3)
            g.line([b_, (lerp(b_[0], mx, 0.7), lerp(b_[1], my, 0.7))], RED, kr, 3)
        else:
            g.line([a_, b_], mix(GOLD, TEAL, harm), kr, 3)
    g.text('they act together' if broke < 0.5 else 'they turn on one another', cx, cy + R + 90, 18, RED if broke >= 0.5 else GOLD, kr, bold=True, align='c')
    kd = ap(t, B['divisions'], 0.6)
    g.tag(cx, cy - R - 60, 'injustice: division and hatred', RED, kd * (1 - harm), 16)
    g.tag(cx, cy - R - 60, 'justice: harmony and friendship', TEAL, harm, 16)
    kc = ap(t, B['city'], 0.6)
    for k, (w, sz) in enumerate((('a city', 1.0), ('an army', 0.85), ('a family', 0.7), ('a single person', 0.55))):
        y = 220 + k * 105
        kk = kc * ap(t, B['city'] + 0.4 * k, 0.4)
        split = ap(t, B['enemy'], 0.8)
        for sd in (-1, 1):
            g.c.new_path()
            g.c.arc(950 + sd * 16 * split, y + 20, 34 * sz, math.pi / 2 if sd < 0 else -math.pi / 2, -math.pi / 2 if sd < 0 else math.pi / 2)
            g.c.set_source_rgba(*mix(TEAL, RED, split), kk)
            g.c.set_line_width(3)
            g.c.stroke()
        g.text(w, 1020, y + 27, 18, WHITE, kk, bold=True)
    F.caption(g, 'its own enemy', ap(t, B['enemy'] + 0.4, 0.6), 690, 22, RED)


# ---------------------------------------------------------------- Book II

def s_goods(g, t, B, D):
    g.background(t, GOLD, 76)
    M.head(g, t, 'Republic, Book II', 'Three kinds of good')
    cols = (('own', 'for their own sake', 'harmless pleasures', TEAL, 260), ('both', 'for themselves and for their results', 'knowledge, sight, health', GOLD, 640),
            ('rewards', 'only for their rewards', 'gymnastic, medicine', ORANGE, 1020))
    for k, (b, name, ex, col, x) in enumerate(cols):
        kk = ap(t, B[b], 0.6)
        g.rrect(x - 165, 210, 330, 330, 16, fill=(*INK, 0.85), stroke=col, a=kk, lw=2.2)
        g.text(name, x, 252, 17, col, kk, bold=True, align='c')
        g.text(ex, x, 515, 15, MUTED, kk, align='c')
        if k == 0:
            for j in range(6):
                ang = j * math.pi / 3 + t * 0.5
                g.dot(x + math.cos(ang) * 22, 380 + math.sin(ang) * 22, 13, TEAL, kk * 0.8, glow=False)
            g.dot(x, 380, 12, GOLD, kk)
        elif k == 1:
            g.eye(x - 60, 380, 0.9, GOLD, kk)
            g.path([(x + 40, 370), (x + 52, 356), (x + 66, 362), (x + 70, 378), (x + 52, 400), (x + 34, 378), (x + 38, 362)], fill=(*RED, 0.7), a=kk)
            g.path([(x + 66, 362), (x + 80, 356), (x + 94, 362), (x + 98, 378), (x + 80, 400), (x + 70, 378)], fill=(*RED, 0.0), a=0)
        else:
            g.line([(x - 50, 380), (x + 10, 380)], IRON, kk, 6, False)
            for dx in (-50, 10):
                g.rrect(x + dx - 8, 362, 16, 36, 3, fill=(*IRON, 0.9), a=kk)
            g.arrow(x + 30, 380, x + 90, 380, 1.0, ORANGE, kk, lw=2)
            g.dot(x + 110, 380, 12, GOLD, kk)
    # justice, carried to its class
    kq = ap(t, B['which'], 0.5)
    if kq > 0:
        go = u(t, B['highest'], 1.4)
        x = lerp(640, 640, go)
        y = lerp(620, 450, go)
        g.tag(x, y, 'justice', GOLD, kq, 20)
        if go < 0.01:
            g.text('?', 640, 660, 36, GOLD, kq, bold=True, align='c')
        M.glow(g, 640, 450, 140, GOLD, 0.3 * go)
    F.caption(g, 'Socrates: in the highest class', ap(t, B['highest'] + 1.4, 0.6), 690, 20, GOLD)


def s_pigs(g, t, B, D):
    g.background(t, TEAL, 77)
    M.head(g, t, 'Republic, Book II', 'The healthy city and the fevered city', fade_at=B['pigs'] + 3.0)
    lux = ap(t, B['pigs'], 1.0)
    # the healthy city: four workers, simple food
    kw = ap(t, B['wants'], 0.6)
    x0 = lerp(640, 330, lux)
    for k, (kind, name) in enumerate((('farm', 'farmer'), ('build', 'builder'), ('weave', 'weaver'), ('shoe', 'shoemaker'))):
        x = x0 - 210 + k * 140
        kk = ap(t, B['farmer'] + 0.6 * k, 0.5)
        F.fig(g, x, 480, 1.0, TEAL, kk, 1, 'stand')
        if kind == 'shoe':
            g.path([(x + 30, 470), (x + 60, 470), (x + 62, 480), (x + 28, 480)], fill=(*BRONZE, 0.8), a=kk, smooth=False)
        else:
            M.icon_work(g, kind, x + 44, 440, TEAL, kk, t)
        g.text(name, x, 510, 14, TEAL, kk, bold=True, align='c')
    kf = ap(t, B['loaves'], 0.6)
    for k in range(14):
        x = x0 - 220 + k * 34
        col = (BRONZE, GOLD, (0.3, 0.5, 0.25), WHITE, VIOLET)[k % 5]
        g.dot(x, 580 + (k % 2) * 8, 9 if k % 5 else 13, col, kf * ap(t, B['loaves'] + 0.08 * k, 0.3), glow=False)
    g.text('the healthy city', x0, 230, 22, TEAL, kw, bold=True, align='c')
    g.text('barley, olives, cheese, figs: peace and health', x0, 640, 15, MUTED, kf, align='c')
    # the fevered city
    if lux > 0:
        x1 = 960
        g.text('the fevered city', x1, 230, 22, RED, lux, bold=True, align='c')
        ks = ap(t, B['sofas'], 0.6)
        g.rrect(x1 - 170, 440, 140, 40, 10, fill=(*VIOLET, 0.5), stroke=VIOLET, a=ks, lw=1.6)
        g.rrect(x1 - 170, 410, 30, 70, 8, fill=(*VIOLET, 0.5), stroke=VIOLET, a=ks, lw=1.6)
        g.rrect(x1 + 20, 450, 150, 12, 3, fill=(*BRONZE, 0.8), a=ks)
        for j in range(5):
            g.dot(x1 + 40 + j * 26, 440 - 6 * math.sin(t * 2 + j), 9, (RED, GOLD, ORANGE, VIOLET, WHITE)[j], ks, glow=True)
        kl = ap(t, B['land'], 0.6)
        r = lerp(120, 230, u(t, B['land'], 2.0))
        g.c.save()
        g.c.translate(x1, 470)
        g.c.scale(1, 0.4)
        g.c.arc(0, 0, r, 0, 2 * math.pi)
        g.c.restore()
        g.c.set_source_rgba(*RED, 0.8 * kl)
        g.c.set_line_width(2)
        g.c.set_dash([8, 6])
        g.c.stroke()
        g.c.set_dash([])
        g.text('more land', x1 + r * 0.7, 560, 16, RED, kl, bold=True, align='c')
        kwar = ap(t, B['war'], 0.6)
        for j in range(5):
            xx = x1 - 140 + j * 70
            g.line([(xx, 400), (xx + 10, 300)], SILVER, kwar, 2.4, False)
            g.path([(xx + 10, 288), (xx + 14, 302), (xx + 6, 302)], fill=(*SILVER, 1), a=kwar, smooth=False)
        g.text('war', x1, 285, 20, RED, kwar, bold=True, align='c')
        kg = ap(t, B['guardians'], 0.6)
        for j in range(3):
            F.fig(g, x1 - 70 + j * 70, 640, 0.9, SILVER, kg * ap(t, B['guardians'] + 0.2 * j, 0.4), 1, 'stand', prop='shield')
        g.text('and so, guardians', x1, 675, 16, SILVER, kg, bold=True, align='c')
    F.caption(g, '"a city of pigs!"', win_(t, B['pigs'], B['sofas'] + 1.5), 196, 22, ORANGE)


def win_(t, a, b, d=0.4):
    return ap(t, a, d) * (1 - ap(t, b, d))


def s_lives(g, t, B, D):
    g.background(t, VIOLET, 78)
    M.head(g, t, 'Republic, Book II', 'The two lives', col=VIOLET)
    gy = 560
    M.ground(g, gy, ap(t, 0.2, 0.6))
    # the scales
    kb = ap(t, 0.4, 0.8)
    tilt = math.radians(lerp(0, -12, u(t, B['scourged'], 2.0)))
    px, py = 640, 250
    g.line([(px, py), (px, gy)], MUTED, kb, 4, False)
    L = 300
    ax, ay = px - math.cos(tilt) * L, py - math.sin(tilt) * L
    bx, by = px + math.cos(tilt) * L, py + math.sin(tilt) * L
    g.line([(ax, ay), (bx, by)], GOLD, kb, 4)
    g.dot(px, py, 8, GOLD, kb)
    # the unjust man, with the mask of justice: honoured
    ku = ap(t, B['unjust'], 0.6)
    F.fig(g, ax, gy, 1.5, RED, ku, 1, 'arms_up' if t > B['reputation'] + 1 else 'stand', prop='crown' if t > B['reputation'] else None)
    km = ap(t, B['reputation'], 0.6)
    for (x_, y_) in ((ax, ay), (bx, by)):
        g.line([(x_, y_), (x_ - 40, y_ + 60)], MUTED, kb * 0.6, 1.4, False)
        g.line([(x_, y_), (x_ + 40, y_ + 60)], MUTED, kb * 0.6, 1.4, False)
        g.path([(x_ - 50, y_ + 60), (x_ + 50, y_ + 60), (x_ + 30, y_ + 76), (x_ - 30, y_ + 76)], fill=(*GOLD, 0.3), stroke=GOLD, a=kb, lw=1.6, smooth=False)
    for q in range(5):
        g.dot(ax - 24 + q * 12, ay + 52 - (q % 2) * 6, 6, GOLD, km, glow=False)
    g.rrect(ax - 4 - 15, gy - 152, 30, 20, 8, fill=(*GOLD, 0.9), a=km)
    g.text('perfectly unjust', ax, gy + 34, 18, RED, ku, bold=True, align='c')
    g.text('seen as just: honours, wealth', ax, gy + 58, 15, GOLD, km, align='c')
    # the just man, thought the worst: punished
    kj = ap(t, B['just'], 0.6)
    kw = ap(t, B['worst'], 0.6)
    kp = ap(t, B['scourged'], 0.6)
    F.fig(g, bx, gy, 1.5, GOLD, kj, -1, F.blend_pose(F.POSES['stand'], F.POSES['breast'], kp))
    g.rrect(bx - 15, gy - 152, 30, 20, 8, fill=(0.15, 0.12, 0.18, 0.95), stroke=MUTED, a=kw, lw=1.2)
    if kp > 0:
        F.chain(g, bx - 30, gy - 80, bx + 30, gy - 80, kp)
        F.chain(g, bx - 24, by + 50, bx + 24, by + 50, kp)
        M.glow(g, bx, gy - 90, 90, RED, 0.25 * kp)
    g.text('perfectly just', bx, gy + 34, 18, GOLD, kj, bold=True, align='c')
    g.text('seen as the worst: scourged, racked, bound', bx, gy + 58, 15, RED, kw, align='c')
    F.caption(g, 'so: seem just, do not be just?', ap(t, B['seem'], 0.6), 690, 20, VIOLET)


# ---------------------------------------------------------------- Book III

def s_metals(g, t, B, D):
    g.background(t, GOLD, 79)
    M.head(g, t, 'Republic, Book III', 'The myth of the metals')
    gy = 540
    kt = ap(t, B['tale'], 0.8)
    g.c.set_source_rgba(0.12, 0.08, 0.05, kt)
    g.c.rectangle(0, gy, 1280, 180)
    g.c.fill()
    g.line([(0, gy), (1280, gy)], BRONZE, kt, 2)
    g.text('born of one mother, the earth', 640, 640, 18, BRONZE, kt, bold=True, align='c')
    metals = (('gold', GOLD, 'to rule', 330), ('silver', SILVER, 'to guard', 640), ('brass', BRONZE, 'to farm and make', 950))
    kb = ap(t, B['brothers'], 0.6)
    for k, (b, col, job, x) in enumerate(metals):
        for j in range(3):
            xx = x - 90 + j * 90
            rise = u(t, B['brothers'] + 0.2 * (k * 3 + j), 1.4)
            y = lerp(gy + 120, gy, rise)
            km = ap(t, B[b], 0.6)
            fc = mix(WHITE, col, km)
            F.fig(g, xx, y, 1.2, fc, kb * rise, 1, 'stand', robe=0.6)
            if km > 0:
                M.glow(g, xx, y - 70, 40, col, 0.6 * km)
                g.dot(xx, y - 70, 6, col, km)
        g.text(b if b != 'brass' else 'brass and iron', x, 250, 24, col, ap(t, B[b], 0.6), bold=True, align='c')
        g.text(job, x, 280, 16, MUTED, ap(t, B[b] + 0.4, 0.6), align='c')


# ---------------------------------------------------------------- Book IV

def s_virtues(g, t, B, D):
    g.background(t, GOLD, 80)
    M.head(g, t, 'Republic, Book IV', 'Four virtues in the city')
    k = ap(t, 0.2, 0.6)
    ctr = M.tiers(g, 420, 620, 1.1, k, (1, 1, 1), t)
    (cb, yb, wb), (cs, ys, ws), (cg, yg, wg) = ctr
    kw = ap(t, B['wisdom'], 0.6)
    g.text('wisdom', 790, yg + 6, 24, GOLD, kw, bold=True)
    g.text('in the rulers', 790, yg + 30, 15, MUTED, kw)
    M.glow(g, cg, yg, 120, GOLD, 0.35 * kw)
    kc = ap(t, B['courage'], 0.6)
    g.text('courage', 790, ys + 6, 24, SILVER, kc, bold=True)
    g.text('in the soldiers', 790, ys + 30, 15, MUTED, kc)
    M.glow(g, cs, ys, 160, SILVER, 0.3 * kc)
    kt = ap(t, B['temperance'], 0.6)
    for j in range(3):
        xx = 420 - 120 + j * 120
        F.flow(g, [(xx, 640), (xx + 20, 520), (xx - 20, 400), (xx, 300)], t + j * 0.3, TEAL, kt, n=6, speed=0.35, prog=u(t, B['temperance'], 1.2))
    g.text('temperance', 790, yb + 6, 24, TEAL, kt, bold=True)
    g.text('the harmony running through all', 790, yb + 30, 15, MUTED, kt)
    kj = ap(t, B['justice'], 0.6)
    g.tag(1110, 380, 'and justice...?', WHITE, kj, 20)
    g.text('?', 1110, 470, 60, GOLD, kj * (0.6 + 0.4 * math.sin(t * 3)), bold=True, align='c')


def s_thirst(g, t, B, D):
    g.background(t, CYAN, 81)
    M.head(g, t, 'Republic, Book IV', 'The thirsty man')
    x, y, s = 520, 205, 1.12
    k = ap(t, B['thirsty'], 0.6)
    g.body(x, y, s, CYAN, k)
    cup = (900, 430)
    g.path([(cup[0] - 30, cup[1] - 40), (cup[0] + 30, cup[1] - 40), (cup[0] + 22, cup[1] + 20), (cup[0] - 22, cup[1] + 20)], fill=(*CYAN, 0.25), stroke=CYAN, a=k, lw=2, smooth=False)
    F.waves(g, t, cup[1] - 30, cup[0] - 26, cup[0] + 26, CYAN, k * 0.7, 1, 3, 6)
    kd = ap(t, B['drink'], 0.6)
    pull = 0.5 + 0.5 * math.sin(t * 2.2)
    F.flow(g, [(x + 30, y + 250 * s), (x + 150, y + 250 * s), (cup[0] - 120, cup[1]), (cup[0] - 40, cup[1])], t, RED, kd, n=7, speed=0.6, prog=u(t, B['drink'], 1.0), r=4)
    g.text('drink!', 760, y + 250 * s + 36, 18, RED, kd, bold=True)
    M.glow(g, x, y + 250 * s, 70, RED, 0.5 * kd)
    kf = ap(t, B['forbidding'], 0.6)
    F.flow(g, [(cup[0] - 50, cup[1] - 70), (cup[0] - 140, y + 20), (x + 120, y + 30), (x + 36, y + 46)], t, GOLD, kf, n=7, speed=0.6, prog=u(t, B['forbidding'], 1.0), r=4)
    g.text('no.', 760, y + 20, 18, GOLD, kf, bold=True)
    M.glow(g, x, y + 46 * s, 60, GOLD, 0.5 * kf)
    kr = ap(t, B['rational'], 0.6)
    g.text('the rational part', 140, y + 52, 20, GOLD, kr, bold=True)
    g.line([(330, y + 46), (x - 40, y + 46)], GOLD, kr * 0.6, 1.4, False)
    ka = ap(t, B['appetitive'], 0.6)
    g.text('the appetitive part', 110, y + 250 * s + 6, 20, RED, ka, bold=True)
    g.line([(330, y + 250 * s), (x - 40, y + 250 * s)], RED, ka * 0.6, 1.4, False)
    k3 = ap(t, B['third'], 0.6)
    g.text('and a third...?', 140, y + 160 * s + 6, 20, SILVER, k3, bold=True)
    g.text('?', x, y + 172 * s, 40, SILVER, k3 * (0.6 + 0.4 * math.sin(t * 3)), bold=True, align='c')


# ---------------------------------------------------------------- Book V

def s_waves(g, t, B, D):
    g.c.set_source_rgb(0.02, 0.04, 0.09)
    g.c.paint()
    M.head(g, t, 'Republic, Book V', 'Three waves', col=CYAN)
    F.waves(g, t, 600, 0, 1280, CYAN, ap(t, 0.2, 0.8), 4, 6, 24)
    labels = (('first', 'women guard too', 300, 0.8), ('second', 'all things in common', 640, 1.0), ('third', 'the greatest wave', 980, 1.35))
    for k, (b, w, x, sz) in enumerate(labels):
        rise = u(t, B[b], 1.6)
        if rise <= 0:
            continue
        h = 260 * sz * rise
        crest = 600 - h
        pts = [(x - 200 * sz, 600)]
        for j in range(21):
            uu = j / 20
            xx = x - 200 * sz + 400 * sz * uu
            yy = 600 - h * math.sin(math.pi * uu) ** 1.4 + (18 * sz * math.sin(t * 2 + j) if uu > 0.4 else 0)
            pts.append((xx, yy))
        pts.append((x + 200 * sz, 600))
        g.path(pts, fill=(*mix(CYAN, WHITE, 0.15 * k), 0.25), stroke=mix(CYAN, WHITE, 0.3), a=rise, lw=2.4)
        g.path([(x + 20 * sz, crest + 10), (x + 70 * sz, crest - 20), (x + 110 * sz, crest + 20), (x + 60 * sz, crest + 6)], fill=(*WHITE, 0.6), a=rise)
        g.text(w, x, crest - 30, 20, WHITE, rise, bold=True, align='c')
        if k == 0:
            for j in range(2):
                F.fig(g, x - 30 + j * 60, crest + 140, 0.85, SILVER, rise, 1, 'stand', prop='shield', robe=1.0 if j == 0 else 0.6)
        elif k == 1:
            for j in range(4):
                g.person(x - 66 + j * 44, crest + 130, 0.55, GOLD, rise)
            g.ring(x, crest + 110, 90, GOLD, rise * 0.6, 1.6)
        else:
            g.text('?', x, crest + 160, 90, GOLD, rise * (0.6 + 0.4 * math.sin(t * 2)), bold=True, align='c')
    # Socrates, small, on the shore
    F.fig(g, 120, 650, 1.0, SILVER, ap(t, B['waves'], 0.6), 1, 'stand', robe=1.0)


def s_kings(g, t, B, D):
    g.background(t, GOLD, 82)
    M.head(g, t, 'Republic, Book V', 'Philosopher kings')
    gy = 560
    M.ground(g, gy, ap(t, 0.2, 0.6))
    kp = ap(t, B['philosophers'], 0.6)
    kk = ap(t, B['kings'], 0.6)
    meet = u(t, B['meet'], 2.0)
    xp = lerp(330, 640, meet)
    xk = lerp(950, 640, meet)
    if meet < 0.98:
        F.fig(g, xp, gy, 1.6, SILVER, kp * (1 - meet), 1, 'stand', robe=1.0, prop='staff')
        F.scroll(g, xp + 40, gy - 90, 1.4, GOLD, kp * (1 - meet))
        g.text('the philosopher', xp, gy + 36, 17, SILVER, kp * (1 - meet), bold=True, align='c')
        F.chair_fig(g, xk, gy, 1.5, WHITE, kk * (1 - meet), -1, 'sit', prop='crown')
        g.text('the king', xk, gy + 36, 17, WHITE, kk * (1 - meet), bold=True, align='c')
    if meet > 0.02:
        F.chair_fig(g, 640, gy, 1.6, GOLD, meet, 1, 'sit', prop='crown')
        F.scroll(g, 690, gy - 70, 1.3, WHITE, meet)
        M.glow(g, 640, gy - 140, 140, GOLD, 0.35 * meet)
        g.text('wisdom and power in one', 640, gy + 36, 18, GOLD, meet, bold=True, align='c')
    kr = ap(t, B['rest'], 0.8)
    rng = random.Random(5)
    for j in range(16):
        x = rng.uniform(80, 1200)
        if 420 < x < 860:
            continue
        hy = gy - rng.uniform(40, 120)
        g.rrect(x - 18, hy, 36, gy - hy, 2, fill=(*mix(RED, GOLD, kr), 0.2), stroke=mix(RED, GOLD, kr), a=ap(t, B['evils'] - 3, 0.8) * 0.6, lw=1.2)
    F.caption(g, 'or cities will never have rest from their evils', ap(t, B['evils'], 0.6), 690, 20, GOLD)


# ---------------------------------------------------------------- Book VI

def s_sun(g, t, B, D):
    g.background(t, GOLD, 83)
    M.head(g, t, 'Republic, Book VI', 'The sun and the good', fade_at=B['author'])
    split = ap(t, B['child'], 1.0)
    # the visible world (top row; at first the whole frame)
    y0 = lerp(380, 260, split)
    night = ap(t, 0.4, 0.6) * out_(t, B['sun'], 0.8)
    day = ap(t, B['sun'], 0.8)
    F.moon(g, 260, y0 - 40, 26, night)
    F.stars(g, t, night * 0.7, 30, 3, (120, y0 - 150, 420, y0 + 20))
    F.sun(g, 260, y0 - 20, 30, t, GOLD, day, 14)
    g.eye(640, y0, 1.1, mix(MUTED, WHITE, day), ap(t, 0.4, 0.6), open_=lerp(0.25, 1.0, day))
    M.tree(g, 1000, y0 + 70, 1.0, mix((0.2, 0.3, 0.3), TEAL, day), ap(t, 0.4, 0.6), 0.25 + 0.2 * day)
    F.flow(g, [(300, y0 - 20), (600, y0 - 120), (900, y0 - 100), (990, y0 - 10)], t, GOLD, day, n=6, speed=0.4, r=3)
    F.flow(g, [(990, y0 + 10), (860, y0 + 40), (720, y0 + 30), (680, y0)], t, TEAL, day, n=5, speed=0.4, r=3)
    g.text('dim: the moon and stars' if day < 0.5 else 'clear: the sun', 640, y0 + 80, 17, GOLD if day > 0.5 else MUTED, ap(t, 0.4, 0.6), bold=True, align='c')
    ka = ap(t, B['author'], 0.6)
    g.tag(260, y0 + 60, 'the author of sight', GOLD, ka, 15)
    # the world of mind
    if split > 0:
        y1 = 530
        g.line([(80, 410), (1200, 410)], MUTED, split * 0.5, 1.2, False)
        g.text('as the sun is in the visible world...', 80, 300 - 120, 15, MUTED, 0.0)
        F.sun(g, 260, y1, 30, t + 1, WHITE, split, 18)
        g.text('the good', 260, y1 + 70, 18, WHITE, split, bold=True, align='c')
        km = ap(t, B['mind'], 0.6)
        g.body(620, y1 - 85, 0.42, GOLD, km)
        M.glow(g, 620, y1 - 66, 40, GOLD, 0.6 * km)
        g.text('the knower', 620, y1 + 128, 16, GOLD, km, bold=True, align='c')
        for j, r in enumerate((30, 20, 10)):
            g.ring(1000, y1, r + 2 * math.sin(t * 2 + j), GOLD, km * (0.5 + 0.2 * j), 2)
        g.text('the things known', 1000, y1 + 70, 16, GOLD, km, bold=True, align='c')
        kt = ap(t, B['truth'], 0.6)
        F.flow(g, [(300, y1), (600, y1 - 110), (900, y1 - 80), (980, y1)], t, WHITE, kt, n=6, speed=0.4, r=3)
        g.text('truth, and the power of knowing', 640, y1 - 120, 16, WHITE, kt, align='c')
        ke = ap(t, B['exceeds'], 0.6)
        M.glow(g, 260, y1, 200, WHITE, 0.25 * ke)
        g.tag(260, y1 - 80, 'beyond being', WHITE, ke, 15)


# ---------------------------------------------------------------- Book VII

def s_turning(g, t, B, D):
    g.c.set_source_rgb(0.02, 0.02, 0.03)
    g.c.paint()
    M.head(g, t, 'Republic, Book VII', 'Turning the soul', col=ORANGE, fade_at=B['already'])
    gy = 600
    kw = out_(t, B['already'], 0.8)
    # the wrong picture: pouring sight into blind eyes
    if kw > 0:
        kpr = ap(t, B['professors'], 0.6)
        F.fig(g, 470, gy, 1.5, MUTED, kpr * kw, 1, 'pour', robe=0.8)
        F.amphora(g, 545, gy - 140, 0.8, ORANGE, kpr * kw, rot=-110)
        F.fig(g, 700, gy, 1.5, WHITE, ap(t, B['blind'] - 1.0, 0.6) * kw, -1, 'stand')
        g.eye(690, gy - 138, 0.5, WHITE, ap(t, B['blind'], 0.6) * kw, open_=0.05)
        for j in range(5):
            uu = ((t * 1.2 + j / 5) % 1.0)
            g.dot(lerp(575, 680, uu), lerp(gy - 140, gy - 138, uu) + 20 * math.sin(math.pi * uu), 3, ORANGE, kpr * kw)
        cross(g, 590, gy - 260, 40, ap(t, B['blind'] + 0.8, 0.5) * kw)
    # the soul already sees: it faces the wrong way, and is turned around
    kr = ap(t, B['already'], 0.8)
    if kr > 0:
        turn = u(t, B['turning'], 1.6)
        bright = 0.3 + 0.7 * turn
        M.glow(g, 1180, 200, 420, GOLD, 0.4 * kr)
        F.sun(g, 1180, 200, 26, t, GOLD, kr, 12)
        g.c.set_source_rgba(0.08, 0.06, 0.05, kr)
        g.c.rectangle(60, 220, 160, 330)
        g.c.fill()
        for j in range(3):
            g.dot(110 + j * 30, 380, 18, (0.02, 0.02, 0.02), kr, glow=False)
        g.text('shadows', 140, 580, 15, MUTED, kr, align='c')
        f = -1 if turn < 0.5 else 1
        F.fig(g, 640, gy, 1.7, mix(MUTED, GOLD, turn), kr, f, 'stand' if turn < 0.5 else 'look_up')
        g.eye(640 + 26 * f, gy - 158, 0.45, mix(MUTED, GOLD, turn), kr, open_=1.0)
        if 0.05 < turn < 0.95:
            g.ring(640, gy - 100, 120, GOLD, kr, 2.5, prog=turn, start=-180)
        g.text('the power is already there' if turn < 0.5 else 'education: the art of turning it around', 640, 200, 22, mix(WHITE, GOLD, turn), kr, bold=True, align='c')
        kwr = ap(t, B['wrong'], 0.6) * (1 - turn)
        g.arrow(560, gy - 160, 280, gy - 200, kwr, MUTED, kwr, lw=2)
        g.text('turned the wrong way', 420, gy - 220, 15, MUTED, kwr, align='c')


# ---------------------------------------------------------------- Book IX

def s_slave(g, t, B, D):
    g.background(t, RED, 84)
    M.head(g, t, 'Republic, Book IX', 'The tyrant is the real slave', col=RED)
    gy = 600
    M.ground(g, gy, ap(t, 0.2, 0.6))
    kt = ap(t, B['tyrant'], 0.6)
    sh = F.shake(t, ap(t, B['fear'], 0.6) * 0.4, 3)
    F.chair_fig(g, 640 + sh[0], gy, 1.8, mix(WHITE, RED, 0.3), kt, 1, 'sit_chain' if t > B['slave'] else 'sit', prop='crown', tcol=GOLD)
    g.text('the tyrant', 640, gy + 36, 18, GOLD, kt, bold=True, align='c')
    ks = ap(t, B['slave'], 0.6)
    kd = ap(t, B['desires'], 0.6)
    hands = [(640 - 20, gy - 120), (640 + 30, gy - 120)]
    rng = random.Random(8)
    for j in range(9):
        ang = math.radians(-160 + j * 17.5)
        r = 380 + rng.uniform(-30, 40)
        mx, my = 640 + math.cos(ang) * r, gy - 120 + math.sin(ang) * r * 0.6
        hx, hy = hands[j % 2]
        pull = 8 * math.sin(t * 4 + j)
        F.chain(g, hx, hy, mx + pull, my, ks)
        kk = kd * ap(t, B['desires'] + 0.1 * j, 0.4)
        M.glow(g, mx + pull, my, 34, RED, 0.6 * kk)
        g.dot(mx + pull, my, 12, RED, kk)
        g.dot(mx + pull + 4, my - 2, 2.5, INK, kk, glow=False)
    g.tag(640, 210, 'more wants than anyone', RED, kd, 17)
    kp = ap(t, B['poor'], 0.6)
    g.text('truly poor', 300, 650, 20, RED, kp, bold=True, align='c')
    kf = ap(t, B['fear'], 0.6)
    for j in range(5):
        ang = t * 0.5 + j * 1.25
        g.dot(640 + math.cos(ang) * 230, gy - 220 + math.sin(ang) * 60, 26, (0.05, 0.04, 0.06), kf * 0.8, glow=False)
    g.text('beset with fear', 980, 650, 20, VIOLET, kf, bold=True, align='c')


def s_pattern(g, t, B, D):
    g.c.set_source_rgb(0.02, 0.03, 0.08)
    g.c.paint()
    F.stars(g, t, ap(t, 0.0, 1.0), 120, 21, (0, 0, 1280, 470))
    M.head(g, t, 'Republic, Book IX', 'A pattern laid up in heaven', fade_at=B['pattern'] + 2.5)
    kp = ap(t, B['pattern'], 1.2)
    # the city of the dialogue drawn in stars
    cx, cy = 640, 250
    rows = ((220, 70), (160, 60), (100, 55))
    yb = cy + 90
    for i, (w, h) in enumerate(rows):
        pts = [(cx - w, yb), (cx + w, yb), (cx + w - 26, yb - h), (cx - w + 26, yb - h), (cx - w, yb)]
        prog = u(t, B['pattern'] + 0.4 * i, 1.2)
        n = max(2, int(len(pts) * prog + 0.5))
        g.line(pts[:n], (GOLD, SILVER, GOLD)[i] if i != 0 else IRON, kp * 0.8, 1.6)
        for p in pts[:n]:
            g.dot(*p, 3.5, WHITE, kp)
        yb -= h
    gy = 640
    g.c.set_source_rgba(0.02, 0.04, 0.05, 1)
    g.c.rectangle(0, gy, 1280, 80)
    g.c.fill()
    g.line([(0, gy), (1280, gy)], MUTED, 0.7, 1.4)
    kb = ap(t, B['behold'], 0.6)
    F.fig(g, 470, gy, 1.5, WHITE, ap(t, 0.5, 0.8), 1, 'look_up' if t > B['behold'] - 0.5 else 'stand')
    lit = u(t, B['house'], 1.4)
    house(g, 760, gy, 1.3, WHITE, ap(t, 0.8, 0.8), lit)
    g.text('he sets his own house in order', 760, gy + 34 - 0, 16, GOLD, ap(t, B['house'], 0.6), bold=True, align='c') if False else None
    F.caption(g, 'he sets his own house in order', ap(t, B['house'] + 0.6, 0.6), 700, 20, GOLD)
    for j in range(4):
        F.flow(g, [(cx - 60 + j * 40, cy + 100), (cx - 120 + j * 30, cy + 250), (520, gy - 260), (480, gy - 160)], t + j * 0.3, GOLD, kb, n=4, speed=0.3, r=2.6)
    ke = ap(t, B['exists'], 0.6)
    g.text('whether it exists on earth is no matter', 640, 400, 18, MUTED, ke, align='c')


# ---------------------------------------------------------------- Book X

def s_ringx(g, t, B, D):
    g.background(t, GOLD, 85)
    M.head(g, t, 'Republic, Book X', 'Seen or unseen')
    gy = 580
    M.ground(g, gy, ap(t, 0.2, 0.6))
    kj = ap(t, B['just'], 0.6)
    kr = ap(t, B['ring'], 0.6)
    kh = ap(t, B['helmet'], 0.6)
    ghost = kr
    x = 560
    F.fig(g, x, gy, 1.7, GOLD, kj * (1 - 0.7 * ghost), 1, 'reach', robe=0.6)
    if ghost > 0:
        F.fig(g, x, gy, 1.7, mix(GOLD, WHITE, 0.4), kj * ghost, 1, 'reach', ghost=True)
    F.fig(g, 760, gy, 1.2, SILVER, kj, -1, 'sit_ground', anchor='hip')
    for j in range(4):
        uu = ((t * 0.6 + j / 4) % 1.0)
        g.dot(lerp(620, 735, uu), gy - 140 + 30 * uu, 5, GOLD, kj * math.sin(math.pi * uu))
    g.text('he does what is just', 640, gy + 40, 20, GOLD, kj, bold=True, align='c')
    F.ring_icon(g, 300, 330, 0.9, kr, turn=u(t, B['ring'], 1.2))
    g.text('with the ring of Gyges', 300, 420, 17, GOLD, kr, bold=True, align='c')
    g.text('or without it', 300, 446, 15, MUTED, kr, align='c')
    if kh > 0:
        hx, hy = 1000, 330
        g.path([(hx - 60, hy + 30), (hx - 64, hy - 20), (hx - 40, hy - 60), (hx, hy - 72), (hx + 40, hy - 60), (hx + 64, hy - 20), (hx + 60, hy + 30),
                (hx + 30, hy + 30), (hx + 26, hy), (hx - 26, hy), (hx - 30, hy + 30)], fill=(0.12, 0.12, 0.16, 0.95), stroke=VIOLET, a=kh, lw=2.2, smooth=False)
        g.line([(hx, hy - 72), (hx, hy - 110)], VIOLET, kh, 4, False)
        M.glow(g, hx, hy - 20, 110, VIOLET, 0.3 * kh)
        g.text('and the helmet of Hades', hx, 420, 17, VIOLET, kh, bold=True, align='c')


SCENES_B = (s_deposit, s_friends, s_craft, s_shepherd, s_band, s_goods, s_pigs, s_lives, s_metals, s_virtues, s_thirst, s_waves,
            s_kings, s_sun, s_turning, s_slave, s_pattern, s_ringx)

PLAN_B = [
    ('n01', 'deposit', 45, 45, {'truth': (45, 'truth'), 'debts': (45, 'debts'), 'deposited': (45, 'deposited'), 'mind': (45, 'not in his'),
                                'give': (45, 'give')}),
    ('n02', 'friends', 53, 53, {'friend': (53, 'friend'), 'evil': (53, 'evil'), 'enemy': (53, 'enemy'), 'justice': (53, 'Justice')}),
    ('n03', 'craft', 77, 77, {'physician': (77, 'physician'), 'patient': (77, 'patient'), 'pilot': (77, 'pilot'), 'sailor': (77, 'sailor', 2),
                              'science': (77, 'science')}),
    ('n04', 'shepherd', 81, 81, {'shepherd': (81, 'shepherd'), 'fattens': (81, 'fattens'), 'master': (81, 'master'), 'rulers': (81, 'rulers')}),
    ('n05', 'band', 89, 91, {'robbers': (89, 'robbers'), 'injured': (89, 'injured'), 'divisions': (91, 'divisions'), 'harmony': (91, 'harmony'),
                             'city': (91, 'city'), 'enemy': (91, 'enemy')}),
    ('n06', 'goods', 103, 104, {'own': (103, 'own sakes'), 'both': (103, 'both'), 'rewards': (103, 'rewards'), 'which': (103, 'which class'),
                                'highest': (104, 'highest')}),
    ('n07', 'pigs', 131, 135, {'wants': (131, 'wants'), 'farmer': (131, 'farmer'), 'loaves': (132, 'loaves'), 'pigs': (133, 'pigs'),
                               'sofas': (133, 'sofas'), 'land': (135, 'land'), 'war': (135, 'war'), 'guardians': (135, 'guardians')}),
    ('n08', 'lives', 117, 117, {'unjust': (117, 'perfectly unjust'), 'reputation': (117, 'reputation'), 'just': (117, 'best of men'),
                                'worst': (117, 'worst'), 'scourged': (117, 'scourged'), 'seem': (117, 'seem')}),
    ('n09', 'metals', 138, 138, {'tale': (138, 'tale'), 'brothers': (138, 'brothers'), 'gold': (138, 'gold'), 'silver': (138, 'silver'),
                                 'brass': (138, 'brass')}),
    ('n10', 'virtues', 143, 143, {'wisdom': (143, 'Wisdom'), 'courage': (143, 'courage'), 'temperance': (143, 'temperance'), 'justice': (143, 'justice')}),
    ('n11', 'thirst', 147, 147, {'thirsty': (147, 'thirsty'), 'drink': (147, 'drink'), 'forbidding': (147, 'forbidding'), 'rational': (147, 'rational'),
                                 'appetitive': (147, 'appetitive'), 'third': (147, 'third')}),
    ('n12', 'waves', 165, 165, {'waves': (165, 'waves'), 'first': (165, 'first'), 'second': (165, 'second'), 'third': (165, 'third')}),
    ('n13', 'kings', 167, 167, {'philosophers': (167, 'philosophers'), 'kings': (167, 'kings'), 'meet': (167, 'meet'), 'rest': (167, 'rest'),
                                'evils': (167, 'evils')}),
    ('n14', 'sun', 180, 180, {'sun': (180, 'sun'), 'author': (180, 'author'), 'child': (180, 'child'), 'mind': (180, 'mind'), 'truth': (180, 'truth'),
                              'exceeds': (180, 'exceeds')}),
    ('n15', 'turning', 213, 213, {'professors': (213, 'professors'), 'blind': (213, 'blind'), 'already': (213, 'already'), 'wrong': (213, 'wrong'),
                                  'turning': (213, 'turning')}),
    ('n16', 'slave', 230, 230, {'tyrant': (230, 'tyrant'), 'slave': (230, 'slave'), 'desires': (230, 'desires'), 'poor': (230, 'poor'), 'fear': (230, 'fear')}),
    ('n17', 'pattern', 238, 238, {'pattern': (238, 'pattern'), 'behold': (238, 'behold'), 'house': (238, 'house'), 'exists': (238, 'exists')}),
    ('n18', 'ringx', 241, 241, {'just': (241, 'just'), 'ring': (241, 'ring'), 'helmet': (241, 'helmet')}),
]


def register(m):
    global M
    M = m
    for f in SCENES_B:
        m.SCENES[f.__name__[2:]] = f
    m.PLAN.extend(PLAN_B)
