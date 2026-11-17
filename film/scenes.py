"""The Ring of Gyges III's explainer graphics: what each one shows, when it cuts in, and how it is drawn.

    python scenes.py PHRASES.json OUT_DIR [--only ID] [--sheet SHEET.png] [--stills]

PLAN lists each graphic: the script element and word where it cuts in and out, and beats (words in the dialogue
that bring each part of the drawing on). PHRASES.json (from phrases.py) gives word times within each line.
Each graphic is written as OUT_DIR/ID.mp4 at 24 fps, with OUT_DIR/graphics.json listing them.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import (CYAN, DIM, GOLD, INK, MUTED, ORANGE, RED, TEAL, VIOLET, WHITE, G, ap, ease, lerp, mix)  # noqa: E402

FPS = 24
PH = {}


def word_t(el, word, nth=1, end=False):
    """Seconds into element el's clip where a word (or phrase start) is said."""
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


# ---------------------------------------------------------------- the scenes

def s_outrage(g, t, B, D):
    g.background(t, RED, 11)
    g.header(t, 'Weaponized raids', 'Outrage on demand', 'One news event, turned into a million personal threat stories')
    k1 = ap(t, 0.3)
    g.card(80, 330, 190, 90, 'THE RAIDS', 'one real event', GOLD, k1)
    g.arrow(275, 375, 455, 375, ap(t, 0.9, 0.8), GOLD)
    k2 = ap(t, 1.2)
    g.rrect(465, 315, 210, 120, 16, fill=(*INK, 0.9), stroke=CYAN, a=k2, lw=2.5, glow=True)
    g.text('ALGORITHM', 570, 370, 24, WHITE, k2, bold=True, align='c')
    g.text('micro-targeting', 570, 398, 16, CYAN, k2, align='c')
    stories = ["They're coming for you", 'It was all staged', 'Your town is next', 'The elites are hiding it', 'Trust no one', 'This is war']
    for i, s in enumerate(stories):
        y = 220 + i * 62
        kk = ap(t, B['targets'] + i * 0.35, 0.6)
        g.arrow(680, 375, 860, y, kk, RED, a=0.85, lw=1.8, bend=10)
        g.person(900, y + 22, 0.55, WHITE, kk)
        g.tag(1060, y + 6, s, RED, kk, 15)
    # the loop
    kl = ap(t, B['loop'], 0.9)
    if kl > 0:
        cx, cy, r = 360, 510, 48
        for i, lab in enumerate(('outrage', 'engagement', 'ad money')):
            ang = -math.pi / 2 + i * 2 * math.pi / 3
            g.text(lab, cx + (r + 50) * math.cos(ang), cy + (r + 22) * math.sin(ang) + 6, 16, ORANGE, kl, bold=True, align='c')
        g.ring(cx, cy, r, ORANGE, kl, 2.5, prog=min(1, (t - B['loop']) / 1.5))
        ang = -math.pi / 2 + (t * 1.6)
        g.dot(cx + r * math.cos(ang), cy + r * math.sin(ang), 6, ORANGE, kl)
        g.text('a conspiracy loop', 160, 516, 18, MUTED, kl, align='c')


def s_hydra(g, t, B, D):
    g.background(t, TEAL, 12)
    g.header(t, 'After the takedown', 'Cut off one head, the body lives', 'What the whole infrastructure still produces')
    for i, (lab, key) in enumerate((('Pervasive alienation', 'a1'), ('Existential anxiety', 'a2'), ('Neurochemical deregulation', 'a3'))):
        g.card(70, 220 + i * 92, 390, 74, lab, None, VIOLET, ap(t, B[key]), 21, align='l')
    k = ap(t, B['hydra'], 0.9)
    cx, cy = 880, 470
    g.path([(cx - 150, cy + 60), (cx - 120, cy - 20), (cx, cy - 50), (cx + 120, cy - 20), (cx + 150, cy + 60)], fill=(*TEAL, 0.15), stroke=TEAL, a=k, lw=2.5)
    g.text('the platforms', cx, cy + 40, 18, WHITE, k, bold=True, align='c')
    heads = [(-150, -260, 'the network'), (-60, -300, 'feeds'), (30, -310, 'ads'), (120, -280, 'data brokers'), (190, -220, 'bots')]
    cut = ap(t, B['cut'], 0.5)
    for i, (dx, dy, lab) in enumerate(heads):
        kk = ap(t, B['hydra'] + 0.2 + i * 0.25, 0.6)
        hx, hy = cx + dx, cy + dy
        if i == 0:
            mx, my = lerp(cx - 80, hx, 0.5), lerp(cy - 30, hy, 0.5)
            g.line([(cx - 80, cy - 30), (mx, my)], TEAL, kk, 6)
            g.line([(mx + 10 * cut, my - 25 * cut), (hx + 20 * cut, hy + 30 * cut)], RED if cut > 0 else TEAL, kk * (1 - 0.6 * cut), 6)
            g.dot(hx + 20 * cut, hy + 30 * cut, 16, RED if cut > 0 else TEAL, kk * (1 - 0.6 * cut))
            if cut > 0:
                g.line([(mx - 22, my - 14), (mx + 22, my + 14)], RED, cut, 4)
                g.line([(mx - 22, my + 14), (mx + 22, my - 14)], RED, cut, 4)
            g.text(lab, hx - 10, hy - 26, 15, MUTED, kk, align='c')
        else:
            g.line([(cx + dx * 0.25, cy - 40), (hx, hy)], TEAL, kk, 6)
            g.dot(hx, hy, 16, TEAL, kk)
            g.text(lab, hx, hy - 26, 15, WHITE, kk, align='c')
    kp = ap(t, B['pudding'], 1.2)
    if kp > 0:
        g.rrect(560, 560, 640, 34, 17, fill=(0.35, 0.55, 0.2, 0.55), a=kp)
        g.text('a toxic pudding', 880, 584, 18, WHITE, kp, bold=True, align='c')


def s_phronesis(g, t, B, D):
    g.background(t, GOLD, 13)
    g.header(t, 'Socrates names it', 'Two words from Athens', None, GOLD)
    k = ap(t, B['phron'])
    g.greek(330, 300, 'φρόνησις', 'phronesis', 'practical wisdom', GOLD, k, 54)
    for i, (lab, key) in enumerate((('holistic', 'h'), ('morally grounded', 'm'), ('aims at the good', 'g'))):
        g.tag(150 + i * 190, 450, lab, GOLD, ap(t, B[key]), 17)
    g.arrow(500, 310, 770, 310, ap(t, B['eud'], 0.8), GOLD, lw=3)
    g.text('the prerequisite for', 635, 290, 15, MUTED, ap(t, B['eud']), align='c')
    g.greek(950, 300, 'εὐδαιμονία', 'eudaimonia', 'the flourishing life', TEAL, ap(t, B['eud'] + 0.5), 54)
    kq = ap(t, B['q'], 0.8)
    g.rrect(250, 520, 780, 56, 28, fill=(*RED, 0.12), stroke=RED, a=kq, lw=1.5)
    g.text('What kind of intelligence builds a machine that feasts on outrage?', 640, 556, 20, WHITE, kq, align='c')


def gear(g, x, y, r, t, col, a):
    for k in range(8):
        ang = t * 0.8 + k * math.pi / 4
        g.line([(x + r * 0.8 * math.cos(ang), y + r * 0.8 * math.sin(ang)), (x + r * 1.18 * math.cos(ang), y + r * 1.18 * math.sin(ang))], col, a, 9, glow=False)
    g.ring(x, y, r * 0.8, col, a, 6)
    g.ring(x, y, r * 0.3, col, a, 3)


def s_metis(g, t, B, D):
    g.background(t, CYAN, 14)
    g.header(t, 'Hyper-optimized instrumental rationality', 'Efficient means, extractive ends')
    k = ap(t, 0.4)
    gear(g, 210, 330, 60, t, CYAN, k)
    g.text('MEANS', 210, 430, 20, WHITE, k, bold=True, align='c')
    g.text('ever more efficient', 210, 456, 16, MUTED, k, align='c')
    g.arrow(300, 330, 520, 330, ap(t, 0.9), CYAN, lw=3)
    ke = ap(t, B['ends'])
    g.card(530, 280, 230, 100, 'ENDS', 'extraction', RED, ke, 24)
    km = ap(t, B['metis'], 0.8)
    g.greek(1000, 300, 'μῆτις', 'metis', 'tactical cunning', GOLD, km, 54)
    kg = ap(t, B['agnostic'], 0.8)
    if kg > 0:
        cx, cy = 640, 520
        g.ring(cx, cy, 48, MUTED, kg, 2)
        ang = t * 3.1
        g.line([(cx, cy), (cx + 40 * math.cos(ang), cy + 40 * math.sin(ang))], RED, kg, 3)
        g.text('N', cx, cy - 58, 14, MUTED, kg, align='c')
        g.text('No moral compass: the goal is never questioned', cx + 80, cy + 6, 20, WHITE, kg)


def s_thrasymachus(g, t, B, D):
    g.background(t, GOLD, 15)
    g.header(t, 'Plato, Republic, Book I', 'Thrasymachian realism', None, GOLD)
    k = ap(t, 0.3, 0.8)
    g.rrect(140, 200, 1000, 120, 18, fill=(*INK, 0.85), stroke=GOLD, a=k, lw=2)
    g.text('“Justice is nothing else than the interest of the stronger.”', 640, 255, 28, WHITE, k, italic=True, align='c')
    g.text('— Thrasymachus, Republic 338c (Jowett translation)', 640, 295, 16, MUTED, k, align='c')
    ku = ap(t, B['rewards'], 0.7)
    g.card(160, 420, 280, 90, 'Unjust behaviour', 'manipulation, cunning', RED, ku, 22)
    g.arrow(450, 465, 800, 465, ap(t, B['rewards'] + 0.4), GOLD, lw=3)
    for i in range(6):
        ph = ((t - B['rewards']) * 0.7 + i / 6) % 1.0
        g.dot(lerp(470, 790, ph), 465 - 20 * math.sin(ph * math.pi), 7, GOLD, ku * (1 - abs(ph - 0.5)) * 1.6)
    kc = ap(t, B['capital'], 0.6)
    g.card(810, 420, 300, 90, 'Rewarded', 'with quantifiable capital', GOLD, kc, 24)


def s_acute(g, t, B, D, variant='feed'):
    g.background(t, ORANGE, 16)
    g.header(t, 'Evolutionary mismatch', 'Built for sprints, not sieges', 'The stress response, then and now')
    x0, y0, w, h = 90, 230, 500, 250
    ka = ap(t, B['acute'])
    g.axes(x0, y0, w, h, 'time', 'stress', MUTED, ka)
    g.text('ACUTE: ' + ('fleeing a predator' if variant == 'savanna' else 'a short physical crisis'), x0, y0 + h + 60, 18, TEAL, ka, bold=True)
    spike = lambda u: 0.12 + 0.82 * math.exp(-((u - 0.35) / 0.08) ** 2)
    g.plot(x0, y0, w, h, spike, ap(t, B['acute'], 2.0), TEAL, ka, fill=True)
    g.text('then it ends', x0 + w * 0.68, y0 + h - 40, 16, MUTED, ap(t, B['acute'] + 1.6), bold=True)
    x1 = 690
    kc = ap(t, B['chronic'])
    g.axes(x1, y0, w, h, 'time', 'stress', MUTED, kc)
    g.text('CHRONIC: ' + ('weaponized threat narratives' if variant == 'savanna' else 'the algorithmic feed'), x1, y0 + h + 60, 18, RED, kc, bold=True)
    chronic = lambda u: min(0.95, 0.12 + 0.75 * ease(u * 4) + 0.08 * math.sin(u * 70) + 0.05 * math.sin(u * 23))
    g.plot(x1, y0, w, h, chronic, ap(t, B['chronic'], 3.0), RED, kc, fill=True)
    if 'on' in B:
        ko = ap(t, B['on'], 0.5)
        g.rrect(x1 + w - 150, y0 - 66, 150, 46, 23, fill=(*RED, 0.25), stroke=RED, a=ko, lw=2)
        g.dot(x1 + w - 30, y0 - 43, 15, RED, ko)
        g.text('LOCKED ON', x1 + w - 92, y0 - 37, 16, WHITE, ko, bold=True, align='c')


def s_hpa(g, t, B, D, variant=1):
    g.background(t, ORANGE, 17)
    g.header(t, 'The stress axis', 'HPA-axis overdrive', 'Hypothalamus, pituitary, adrenal glands')
    bx, by, s = 300, 175, 0.98
    kb = ap(t, 0.2)
    g.body(bx, by, s, CYAN, kb * 0.9)
    pts = {'h': (bx, by + 30), 'p': (bx, by + 52), 'a': (bx, by + 230)}
    labels = {'h': 'Hypothalamus', 'p': 'Pituitary', 'a': 'Adrenal glands'}
    order = ['h', 'p', 'a']
    tb = {'h': B['h'], 'p': max(B['p'], B['h'] + 0.8)}
    tb['a'] = max(B['a'], tb['p'] + 0.8)
    for i, key in enumerate(order):
        kk = ap(t, tb[key], 0.5)
        x, y = pts[key]
        g.dot(x, y, 8 if key != 'a' else 11, ORANGE, kk)
        lx = bx - 190 if key != 'p' else bx + 140
        g.line([(x, y), (lx + (110 if key != 'p' else -10), y)], ORANGE, kk * 0.8, 1.5, glow=False)
        g.text(labels[key], lx + (100 if key != 'p' else 0), y + 6, 18, WHITE, kk, bold=True, align='r' if key != 'p' else 'l')
        if i:
            px, py = pts[order[i - 1]]
            g.arrow(px + 14, py + 4, x + 14, y - 6, kk, ORANGE, lw=2, bend=-30 if key == 'a' else -8)
    # cortisol rising toward the brain
    kc = ap(t, B['cortisol'], 0.6)
    if kc > 0:
        g.text('cortisol', bx + 100, by + 300, 20, ORANGE, kc, bold=True)
        for i in range(26):
            ph = ((t - B['cortisol']) * 0.35 + i / 26) % 1.0
            x = lerp(bx + 20, 900, ph) + 18 * math.sin(i * 1.7 + t)
            y = lerp(by + 230, 330, ph) + 30 * math.sin(i * 2.3)
            g.dot(x, y, 4, ORANGE, kc * min(1, ph * 4) * 0.9, glow=False)
    shrink = ap(t, B['shrink'], 2.5) if 'shrink' in B else 0.0
    kbrain = ap(t, B.get('brain', B['cortisol']), 0.8)
    g.brain(930, 330, 0.95, CYAN, kbrain, pfc=mix(GOLD, RED, shrink), pfc_k=1.0 - 0.38 * shrink)
    g.text('prefrontal cortex', 760, 220, 17, GOLD, kbrain, bold=True)
    if shrink > 0:
        g.text('measurable shrinking', 930, 520, 22, RED, shrink, bold=True, align='c')
    if variant == 2:
        k1, k2 = ap(t, B['short']), ap(t, B['neuro'])
        g.tag(820, 575, 'short term: keeps you alive', TEAL, k1, 16)
        g.tag(1080, 575, 'prolonged: neurotoxic', RED, k2, 16)


def s_funnel(g, t, B, D):
    g.background(t, CYAN, 18)
    g.header(t, 'Steerable', 'Behavioural funnels', 'Below conscious choice, one nudge at a time')
    k = ap(t, 0.4, 0.5)
    g.funnel(760, 200, 520, 380, ['Attention', 'Threat', 'Fear', 'Reaction', 'Action'], min(1, (t - 0.3) / 3.0), CYAN, k, hi=2)
    ph = ((t - 0.5) * 0.28) % 1.0
    g.person(760, 220 + 330 * ph, 0.5, GOLD, k * 0.9, fill=True)
    ks = ap(t, B['shell'], 0.8)
    g.person(200, 390, 1.6, WHITE, k)
    g.text('sovereign citizen', 200, 420, 18, WHITE, k * (1 - ks), align='c', bold=True)
    g.person(200, 390, 1.6, RED, ks * 0.9)
    g.text('an emptied psychic shell', 200, 420, 18, RED, ks, align='c', bold=True)


def s_cave(g, t, B, D, variant=1):
    g.background(t, ORANGE, 19)
    if variant == 1:
        g.header(t, 'Plato, Republic, Book VII', 'The digital cave', 'Prisoners watch shadows; the chains hold them there')
    else:
        g.header(t, 'The Allegory of the Cave, automated', 'Personalised shadows', 'A puppeteer that learns what frightens each prisoner')
    k = ap(t, 0.3)
    g.path([(60, 600), (60, 260), (180, 190), (900, 180), (1220, 230), (1220, 600)], fill=(0.08, 0.06, 0.05, 0.9), stroke=MUTED, a=k, lw=1.5, smooth=False)
    # the wall of shadows
    g.rrect(860, 230, 330, 300, 8, fill=(0.14, 0.11, 0.1, 1), a=k)
    for i in range(3):
        ks = ap(t, 0.8 + i * 0.5)
        x = 900 + i * 100
        wob = 6 * math.sin(t * 2 + i)
        if variant == 1:
            g.person(x + 25, 420 + wob, 0.9, (0.02, 0.02, 0.02), ks, fill=True)
        else:
            g.rrect(x, 290 + i * 40, 90, 60, 6, fill=(*RED, 0.25), stroke=RED, a=ks, lw=1.5)
            g.text(['fear', 'outrage', 'panic'][i], x + 45, 326 + i * 40, 15, WHITE, ks, bold=True, align='c')
    g.text('the wall', 1025, 560, 16, MUTED, k, align='c')
    # the prisoners, chained, facing the wall
    for i in range(4):
        x = 380 + i * 95
        g.person(x, 540, 0.9, WHITE, k)
        g.line([(x - 18, 545), (x + 18, 545)], MUTED, k, 3, glow=False)
    kc = ap(t, B['chains'], 0.7)
    for i in range(4):
        x = 380 + i * 95
        g.line([(x, 545), (x + 20, 590), (x + 60, 595)], GOLD, kc, 3)
    if kc > 0 and variant == 1:
        g.text('chains forged from our own evolutionary biology', 560, 232, 18, GOLD, kc, bold=True, align='c')
    # the fire, now a projector
    kf = ap(t, 0.6)
    g.rrect(160, 300, 110, 74, 8, fill=(*CYAN, 0.25), stroke=CYAN, a=kf, lw=2)
    g.text('the feed', 215, 343, 16, WHITE, kf, bold=True, align='c')
    g.line([(270, 320), (860, 250)], CYAN, kf * 0.25, 1, glow=False)
    g.line([(270, 355), (860, 520)], CYAN, kf * 0.25, 1, glow=False)
    if variant == 2:
        kp = ap(t, B['puppet'], 0.8)
        g.rrect(150, 210, 140, 50, 10, fill=(*INK, 0.9), stroke=RED, a=kp, lw=2)
        g.text('ALGORITHM', 220, 242, 16, WHITE, kp, bold=True, align='c')
        for i in range(3):
            g.line([(180 + i * 40, 260), (190 + i * 30, 300)], RED, kp * 0.7, 1.2, glow=False)
        if 'metrics' in B:
            km = ap(t, B['metrics'], 0.6)
            g.gauge(470, 330, 40, 0.3 + 0.6 * ease((t - B['metrics']) / 3), RED, km, 'typing speed', '')
            g.gauge(620, 330, 40, 0.2 + 0.7 * ease((t - B['metrics'] - 0.8) / 3), RED, ap(t, B['metrics'] + 0.8, 0.6), 'gaze time', '')


def s_hegemony(g, t, B, D):
    g.background(t, CYAN, 20)
    g.header(t, 'After the raids', 'A decentralized algorithmic hegemony')
    k1 = ap(t, 0.3)
    g.text('BEFORE: gatekeepers', 300, 210, 18, MUTED, k1, bold=True, align='c')
    cx, cy = 300, 400
    g.card(cx - 70, cy - 30, 140, 60, 'Institutions', None, GOLD, k1, 17)
    for i, lab in enumerate(('press', 'church', 'parties', 'courts', 'schools', 'unions')):
        ang = i * math.pi / 3
        x, y = cx + 170 * math.cos(ang), cy + 120 * math.sin(ang)
        g.line([(cx, cy), (x, y)], GOLD, k1 * 0.6, 1.5, glow=False)
        g.tag(x, y + 6, lab, GOLD, k1, 14)
    k2 = ap(t, B['now'], 0.8)
    g.text('NOW: no centre, no one at the wheel', 920, 210, 18, CYAN, k2, bold=True, align='c')
    g.node_net(920, 400, 220, 140, 34, t, min(1, (t - B['now']) / 2.0), CYAN, k2, seed=5, links=3)
    ko = ap(t, B['oversight'], 0.6)
    g.person(920, 600, 0.7, WHITE, ko)
    g.line([(880, 540), (960, 610)], RED, ko, 4)
    g.text('without human oversight', 1000, 590, 17, RED, ko, bold=True)


def s_ocean(g, t, B, D):
    g.background(t, VIOLET, 21)
    g.header(t, '2016: the behavioral coup', 'Psychographic targeting', 'Personality models built from what people leave online', VIOLET)
    traits = [('Openness', 0.42), ('Conscientiousness', 0.35), ('Extraversion', 0.5), ('Agreeableness', 0.55), ('Neuroticism', 0.86)]
    ko = ap(t, B['ocean'], 0.6)
    g.text('O C E A N', 300, 222, 26, VIOLET, ko, bold=True, align='c', spacing=6)
    for i, (lab, v) in enumerate(traits):
        kk = ap(t, B['ocean'] + 0.3 + i * 0.35, 0.8)
        g.bar(90, 285 + i * 62, 420, 14, v * kk, RED if lab == 'Neuroticism' else VIOLET, ko, lab, '%d%%' % round(v * 100 * kk))
    kp = ap(t, 0.4)
    g.person(900, 520, 2.0, WHITE, kp)
    kd = ap(t, B['drill'], 0.6)
    for i, lab in enumerate(('likes', 'shares', 'pauses', 'words', 'friends')):
        ph = ((t - B['drill']) * 0.5 + i / 5) % 1.0
        x = 680 + i * 110
        g.tag(x, 230, lab, VIOLET, kd, 15)
        g.dot(lerp(x, 900, ph), lerp(250, 420, ph), 4, VIOLET, kd * 0.8, glow=False)
    kb = ap(t, B['bypass'], 0.6)
    g.tag(900, 590, 'bypassing religious and political mediators', RED, kb, 15)


def s_optimize(g, t, B, D):
    g.background(t, RED, 22)
    g.header(t, 'Not rational thought', 'What the feed optimizes for')
    for i, (lab, key) in enumerate((('Neuroticism', 'n'), ('Fear', 'f'), ('Confusion', 'c'))):
        kk = ap(t, B[key], 0.5)
        g.gauge(170 + i * 190, 330, 64, 0.85 * ease((t - B[key]) / 2.0), RED, kk, lab, '')
    ka = ap(t, B['anx'], 0.7)
    g.arrow(610, 330, 720, 330, ka, ORANGE, lw=3)
    g.card(730, 270, 240, 120, 'Mapped anxieties', 'each person\'s deep fears', ORANGE, ka, 21)
    kf = ap(t, B['fin'], 0.7)
    g.arrow(850, 395, 850, 470, kf, GOLD, lw=3)
    g.card(700, 475, 300, 100, '$  Predictive products', 'sold on what you will do', GOLD, kf, 21)


def s_taxonomy(g, t, B, D):
    g.background(t, GOLD, 23)
    g.header(t, 'Aristotle, Nicomachean Ethics, Book VI', 'A taxonomy of intellect', 'Kinds of mind, sorted by what they aim at', GOLD)
    items = [('τέχνη', 'techne', 'craft'), ('ἐπιστήμη', 'episteme', 'knowledge'), ('φρόνησις', 'phronesis', 'practical wisdom'),
             ('σοφία', 'sophia', 'wisdom'), ('νοῦς', 'nous', 'insight')]
    for i, (gr, la, me) in enumerate(items):
        kk = ap(t, 0.5 + i * 0.4, 0.6)
        x = 150 + i * 245
        hi = la == 'phronesis'
        k_hi = ap(t, B['phron'], 0.6) if hi else 0
        g.rrect(x - 105, 330, 210, 170, 14, fill=(*INK, 0.85), stroke=mix(DIM, GOLD, 0.5 + 0.5 * k_hi) if not hi else mix(MUTED, GOLD, k_hi), a=kk, lw=2 + 2 * k_hi, glow=hi)
        g.greek(x, 400, gr, la, me, GOLD if hi else WHITE, kk, 34)
    kt = ap(t, B['telos'], 0.7)
    g.rrect(440, 205, 400, 70, 35, fill=(*GOLD, 0.12), stroke=GOLD, a=kt, lw=2)
    g.text('τέλος  telos: the end it serves', 640, 248, 22, WHITE, kt, bold=True, align='c')
    for i in range(5):
        g.arrow(150 + i * 245, 325, 640 + (i - 2) * 40, 280, kt * 0.8, GOLD, lw=1.5, head=8)


def s_whole(g, t, B, D):
    g.background(t, TEAL, 24)
    g.header(t, 'Phronesis', 'Wisdom that sees the whole', 'Not calculation alone: judgement aimed at the good', TEAL)
    cx, cy = 470, 400
    k = ap(t, 0.3)
    labels = ['self', 'others', 'the city', 'nature', 'the future', 'the good']
    kl = ap(t, B['inter'], 1.0)
    pts = []
    for i, lab in enumerate(labels):
        ang = -math.pi / 2 + i * 2 * math.pi / len(labels)
        x, y = cx + 220 * math.cos(ang), cy + 150 * math.sin(ang)
        pts.append((x, y))
        g.line([(cx, cy), (x, y)], TEAL, k * 0.5, 1.5, glow=False)
        g.tag(x, y + 6, lab, TEAL, ap(t, 0.6 + i * 0.25), 16)
    for i in range(len(pts)):
        g.line([pts[i], pts[(i + 1) % len(pts)]], TEAL, kl * 0.8, 2)
    g.text('interdependency', cx, cy + 190, 17, TEAL, kl, bold=True, align='c')
    g.dot(cx, cy, 56, GOLD, k)
    g.text('φρόνησις', cx, cy + 7, 19, INK, k, bold=True, align='c')
    ke = ap(t, B['eud'], 0.7)
    g.arrow(720, 400, 880, 400, ke, GOLD, lw=3)
    g.greek(1040, 390, 'εὐδαιμονία', 'eudaimonia', 'the virtuous, flourishing life', GOLD, ke, 44)


def s_growth(g, t, B, D):
    g.background(t, CYAN, 25)
    g.header(t, 'The digital panopticon', 'One mandate: infinite compound growth')
    k = ap(t, 0.3)
    x0, y0, w, h = 420, 220, 700, 330
    g.axes(x0, y0, w, h, 'time', 'growth', MUTED, k)
    g.plot(x0, y0, w, h, lambda u: min(1.08, 0.04 * math.exp(3.3 * u)), min(1, (t - 0.5) / 4.0), CYAN, k, fill=True)
    g.text('no end point: an unfinished picture', x0 + 24, y0 + 34, 18, CYAN, ap(t, B['unfinished']), bold=True)
    # the panopticon: a ring of cells round a watchtower
    cx, cy = 230, 400
    for i in range(16):
        ang = i * math.pi / 8
        g.rrect(cx + 120 * math.cos(ang) - 9, cy + 120 * math.sin(ang) - 9, 18, 18, 3, stroke=MUTED, a=k, lw=1.5)
    g.dot(cx, cy, 22, CYAN, k)
    g.text('the watchtower', cx, cy + 165, 16, MUTED, k, align='c')
    ke = ap(t, B['eud'], 0.6)
    g.tag(cx, cy - 160, 'eudaimonia: not in its vocabulary', RED, ke, 15)


def s_inversion(g, t, B, D):
    g.background(t, GOLD, 26)
    g.header(t, 'The epistemic inversion', 'Phronesis over metis, turned upside down', None, GOLD)
    k = ap(t, 0.3)
    flip = ap(t, B['flip'], 1.4)
    cx = 520
    top_y, bot_y = 300, 470
    yp = lerp(top_y, bot_y, flip)
    ym = lerp(bot_y, top_y, flip)
    g.rrect(cx - 260, yp - 60, 520, 120, 16, fill=(*INK, 0.9), stroke=GOLD, a=k, lw=2.5, glow=True)
    g.text('PHRONESIS  practical wisdom', cx, yp + 8, 26, GOLD, k, bold=True, align='c')
    g.rrect(cx - 260, ym - 60, 520, 120, 16, fill=(*INK, 0.9), stroke=RED, a=ap(t, B['metis']), lw=2.5, glow=True)
    g.text('METIS  tactical cunning', cx, ym - 6, 26, RED, ap(t, B['metis']), bold=True, align='c')
    g.text('manipulates variables toward a narrow goal', cx, ym + 24, 16, MUTED, ap(t, B['metis']), align='c')
    g.text('the classical order' if flip < 0.5 else 'the digital order', 1000, 390, 26, WHITE, k * abs(2 * flip - 1) if 0.3 < flip < 0.7 else k, bold=True, align='c')
    g.text('↑ higher', 960, 300, 18, MUTED, k)
    g.text('↓ lower', 960, 480, 18, MUTED, k)


def s_market(g, t, B, D):
    g.background(t, GOLD, 27)
    g.header(t, 'Under surveillance capitalism', 'What gets rewarded', None, GOLD)
    k = ap(t, 0.3)
    # podium
    g.rrect(520, 420, 240, 160, 6, fill=(*GOLD, 0.2), stroke=GOLD, a=k, lw=2)
    g.text('1', 640, 520, 60, GOLD, k, bold=True, align='c')
    km = ap(t, B['metis'], 0.7)
    g.card(510, 300, 260, 100, 'METIS', 'the pinnacle, they say', RED, km, 28)
    for i in range(10):
        ph = ((t - B['metis']) * 0.5 + i / 10) % 1.0
        g.text('$', 530 + (i * 53) % 230, 190 + 95 * ph, 22, GOLD, km * (1 - ph) * 0.9, bold=True)
    kp = ap(t, B['phron'], 0.7)
    dx = 120 * ap(t, B['phron'] + 0.8, 1.5)
    g.card(150 - dx * 0.3, 470, 250, 90, 'PHRONESIS', 'marginalized: "inefficient"', MUTED, kp, 24)
    kr = ap(t, B['rewarded'], 0.6)
    g.tag(1010, 330, 'engineer engagement', GOLD, kr, 16)
    g.tag(1010, 390, 'exploit psychographic weak points', GOLD, ap(t, B['rewarded'] + 0.4, 0.6), 16)
    g.tag(1010, 450, 'culturally and financially rewarded', WHITE, ap(t, B['rewarded'] + 0.8, 0.6), 16)


def s_profile(g, t, B, D):
    g.background(t, CYAN, 28)
    g.header(t, 'An evolutionary and ethical regression', 'People as data profiles', 'Treated merely as means to an end')
    k = ap(t, 0.3)
    dis = ap(t, B['profiles'], 2.5)
    g.person(380, 520, 4.0, WHITE, k * (1 - dis))
    import random as _r
    rng = _r.Random(4)
    for i in range(140):
        x, y = 290 + rng.uniform(0, 180), 330 + rng.uniform(0, 200)
        tx, ty = 700 + (i % 14) * 34, 240 + (i // 14) * 34
        g.rrect(lerp(x, tx, dis) - 9, lerp(y, ty, dis) - 9, 18, 18, 3, fill=(*CYAN, 0.25 + 0.5 * ((i * 7) % 5 == 0)), a=k * dis)
    km = ap(t, B['means'], 0.6)
    g.tag(940, 588, 'a means to an end', RED, km, 17)


def s_track(g, t, B, D):
    g.background(t, TEAL, 29)
    g.header(t, 'The Mirror Force', 'Seeing the trap before it snaps shut', None, TEAL)
    k = ap(t, 0.3)
    g.funnel(560, 200, 520, 380, ['Attention', 'Trigger', 'Fear', 'Reaction', 'Action'], 1.0, CYAN, k, hi=-1)
    kl = ap(t, B['track'], 0.6)
    yy = 200 + (380 / 5) * (1.5 + 1.0 * ease((t - B['track']) / 3.0))
    g.lens(960, yy - 20, 1.1, TEAL, kl)
    g.line([(830, yy), (920, yy - 10)], TEAL, kl * 0.6, 1.5, glow=False)
    ks = ap(t, B['snap'], 0.6)
    for i, y in enumerate((276 + 30, 352 + 30)):
        g.tag(250, y, ['trigger: a threat story', 'fear: the primate brain'][i], RED, ap(t, B['vuln'] + i * 0.5, 0.6), 16)
    g.text('visible before it closes', 960, 590, 18, TEAL, ks, bold=True, align='c')


def s_pfc(g, t, B, D):
    g.background(t, GOLD, 30)
    g.header(t, 'Reason is bound by flesh', 'The prefrontal cortex', 'The newest part of the hominid brain', GOLD)
    k = ap(t, B['pfc'] - 0.4, 0.8)
    g.brain(560, 380, 1.15, CYAN, k, pfc=GOLD)
    for i, (lab, key, y) in enumerate((('critical analysis', 'crit', 250), ('logical thinking', 'logic', 310), ('autonomous willpower', 'will', 370))):
        kk = ap(t, B[key], 0.5)
        g.line([(400, 300), (230, y)], GOLD, kk * 0.7, 1.5, glow=False)
        g.text(lab, 220, y + 6, 19, WHITE, kk, bold=True, align='r')
    ke = ap(t, B['cost'], 0.6)
    drain = 1 - 0.75 * ease((t - B['cost']) / 4.0)
    g.bar(820, 270, 340, 18, drain, ORANGE, ke, 'Metabolic cost: very high', 'energy')
    g.text('holds back impulsive, threat-driven behaviour', 990, 340, 17, MUTED, ap(t, B['suppress'], 0.6), align='c')


def s_dendrites(g, t, B, D):
    g.background(t, CYAN, 31)
    g.header(t, 'The cortisol cascade', 'Dendritic atrophy', 'Branches of prefrontal neurons thin and retract')
    k = ap(t, 0.3)
    shrink = ap(t, B['atrophy'], 3.0)
    import random as _r

    def branch(x, y, ang, L, depth, rng):
        if depth == 0 or L < 6:
            return
        L2 = L * (1 - 0.55 * shrink * (1 - depth / 6))
        x2, y2 = x + L2 * math.cos(ang), y + L2 * math.sin(ang)
        g.line([(x, y), (x2, y2)], mix(CYAN, RED, shrink * 0.7), k * (1 - 0.3 * shrink * (depth < 3)), max(1.0, depth * 0.9), glow=depth > 3)
        for d in (-0.45, 0.4):
            branch(x2, y2, ang + d + rng.uniform(-0.15, 0.15), L * 0.72, depth - 1, rng)
    for i, base in enumerate((-math.pi / 2, -math.pi / 2 - 1.0, -math.pi / 2 + 1.0, math.pi / 2)):
        branch(640, 390, base, 86 if i < 3 else 46, 6, _r.Random(i + 3))
    g.dot(640, 390, 22, CYAN, k)
    g.text('healthy' if shrink < 0.5 else 'after chronic cortisol', 640, 588, 20, CYAN if shrink < 0.5 else RED, k, bold=True, align='c')


def s_chariot(g, t, B, D):
    g.background(t, GOLD, 32)
    g.header(t, 'Plato, Phaedrus', 'The soul as a charioteer', 'Reason guides two horses that pull different ways', GOLD)
    kc = ap(t, min(B['char'], 0.8), 0.7)
    g.charioteer(250, 470, 1.8, GOLD, kc)
    g.text('Charioteer: Reason (Logos)', 250, 560, 20, GOLD, kc, bold=True, align='c')
    k1 = ap(t, B['noble'], 0.7)
    g.horse(640, 330, 1.0, WHITE, k1, gallop=t * 3)
    g.text('Thymos: the noble horse,', 980, 300, 20, WHITE, k1, bold=True)
    g.text('righteous passion', 980, 326, 18, MUTED, k1)
    k2 = ap(t, B['wild'], 0.7)
    g.horse(640, 520, 1.0, (0.42, 0.36, 0.42), k2, gallop=t * 3 + 1.5, fill=0.95)
    g.text('The wild horse,', 980, 490, 20, RED, k2, bold=True)
    g.text('base appetites', 980, 516, 18, MUTED, k2)
    g.line([(330, 330), (690, 250)], GOLD, kc * k1, 1.5, glow=False)
    g.line([(330, 330), (690, 440)], GOLD, kc * k2, 1.5, glow=False)


def s_chariot2(g, t, B, D):
    g.background(t, RED, 33)
    g.header(t, 'When cortisol drains reason', 'The charioteer passes out at the reins', None, RED)
    slump = ap(t, B['out'], 1.2)
    k = ap(t, 0.3)
    g.charioteer(330, 480, 1.3, mix(GOLD, MUTED, slump), k, slump=slump)
    g.bar(200, 578, 260, 14, 1 - 0.92 * slump, mix(GOLD, RED, slump), k, 'executive control', '')
    bolt = ap(t, B['bolt'], 3.0)
    g.horse(640 + 420 * bolt, 400, 1.15, WHITE, k * (1 - 0.7 * bolt), gallop=t * (3 + 5 * bolt))
    kl = ap(t, B['map'], 0.8)
    g.tag(820, 250, 'charioteer = prefrontal cortex', GOLD, kl, 16)
    g.tag(820, 300, 'spirited horse = ancient threat brain', RED, ap(t, B['map'] + 0.6, 0.8), 16)
    kb = ap(t, B['bolt'], 0.6)
    g.text('defence, tribe, combat: it bolts blindly', 760, 560, 20, RED, kb, bold=True, align='c')


def s_whip(g, t, B, D):
    g.background(t, RED, 34)
    g.header(t, 'Into the vacuum of agency', 'The algorithm takes the whip', None, RED)
    k = ap(t, 0.3)
    g.charioteer(380, 480, 1.3, MUTED, k * 0.6, slump=1.0)
    g.horse(700, 420, 1.15, WHITE, k, gallop=t * 7)
    kw = ap(t, B['whip'], 0.6)
    g.rrect(820, 190, 210, 56, 12, fill=(*INK, 0.9), stroke=RED, a=kw, lw=2, glow=True)
    g.text('ALGORITHM', 925, 226, 20, WHITE, kw, bold=True, align='c')
    lash = math.sin(t * 5) * 30
    g.line([(860, 246), (800 + lash, 300), (760, 340 + lash * 0.3)], RED, kw, 3)
    ka = ap(t, B['amyg'], 0.7)
    g.brain(240, 260, 0.45, CYAN, ka, folds=False)
    g.dot(250, 270, 12, RED, ka)
    g.text('amygdala, hijacked', 240, 340, 16, RED, ka, bold=True, align='c')
    kg = ap(t, B['anger'], 0.7)
    g.tag(560, 588, 'confusion', MUTED, kg, 17)
    g.arrow(640, 581, 760, 581, kg, RED)
    g.tag(900, 588, 'focused, external anger', RED, kg, 17)


def s_neurochem(g, t, B, D):
    g.background(t, ORANGE, 35)
    g.header(t, 'The physiological sequence', 'Dopamine, then norepinephrine', 'Mapped step by step, so it can be seen as it starts')
    x0, y0, w, h = 120, 220, 980, 300
    k = ap(t, 0.3)
    g.axes(x0, y0, w, h, 'seconds', 'level', MUTED, k)
    kd = ap(t, B['dopa'], 0.5)
    g.plot(x0, y0, w, h, lambda u: 0.1 + 0.8 * math.exp(-((u - 0.3) / 0.07) ** 2), ap(t, B['dopa'], 2.5), VIOLET, kd)
    g.text('dopamine: aberrant salience', x0 + w * 0.3, y0 + 10, 18, VIOLET, kd, bold=True, align='c')
    kn = ap(t, B['nor'], 0.5)
    g.plot(x0, y0, w, h, lambda u: 0.1 + 0.85 * math.exp(-((u - 0.62) / 0.06) ** 2) * (u > 0.4), ap(t, B['nor'], 2.5), RED, kn)
    g.text('norepinephrine: the panic spike', x0 + w * 0.64, y0 - 6, 18, RED, kn, bold=True, align='c')
    kw = ap(t, B['witness'], 0.6)
    xw = x0 + w * 0.2
    g.line([(xw, y0 + 10), (xw, y0 + h)], TEAL, kw, 2, dash=[6, 6])
    g.tag(xw, y0 + h + 50, 'witness the fire as it starts', TEAL, kw, 16)


def s_marathon(g, t, B, D):
    g.background(t, ORANGE, 36)
    g.header(t, 'Willpower is not enough', 'A fractured leg cannot run a marathon')
    k = ap(t, 0.3)
    g.rrect(240, 280, 280, 140, 14, stroke=WHITE, a=k, lw=3)
    g.rrect(520, 325, 22, 50, 4, fill=(*WHITE, 1), a=k)
    lvl = 1 - 0.85 * ap(t, B['cortisol'], 2.0)
    g.rrect(252, 292, 256 * lvl, 116, 8, fill=(*mix(RED, TEAL, lvl), 0.9), a=k)
    g.text('prefrontal reserves', 380, 460, 19, WHITE, k, bold=True, align='c')
    kd = ap(t, B['demand'], 0.6)
    g.card(720, 300, 380, 110, 'Demand: pure willpower', '"just wake up"', RED, kd, 22)
    g.line([(740, 300), (1080, 410)], RED, kd, 4)


def s_shield(g, t, B, D):
    g.background(t, TEAL, 37)
    g.header(t, 'Evolving their creation', 'From a lens to a shield', None, TEAL)
    m = ap(t, B['shield'], 1.4)
    k = ap(t, 0.3)
    g.lens(380, 380, 1.6 * (1 - m * 0.6), CYAN, k * (1 - m))
    g.text('a lens to unmask the corrupt', 380, 540, 20, CYAN, k * (1 - m), bold=True, align='c')
    g.text('asymmetric accountability', 380, 570, 16, MUTED, k * (1 - m), align='c')
    g.arrow(560, 380, 720, 380, k, TEAL, lw=3)
    g.shield(900, 380, 1.8 * (0.5 + 0.5 * m), TEAL, m)
    g.text('a psychological shield for the citizen', 900, 560, 20, TEAL, m, bold=True, align='c')


def s_tiers(g, t, B, D):
    g.background(t, TEAL, 38)
    g.header(t, 'Two tiers of defence', 'Algorithmic hygiene', None, TEAL)
    k1 = ap(t, B['tier1'], 0.6)
    g.rrect(110, 220, 500, 300, 18, fill=(*INK, 0.85), stroke=TEAL, a=k1, lw=2.5, glow=True)
    g.text('TIER 1: SYSTEMIC', 140, 266, 20, TEAL, k1, bold=True)
    g.para('Write algorithmic hygiene into the law', 140, 320, 440, 26, WHITE, k1, bold=True)
    kb = ap(t, B['bar'], 0.6)
    g.para('Bar platforms from making money out of a user\'s biological panic', 140, 420, 440, 19, MUTED, kb)
    k2 = ap(t, B['tier1'] + 1.0, 0.8) * 0.45
    g.rrect(670, 220, 500, 300, 18, fill=(*INK, 0.6), stroke=MUTED, a=k2, lw=2)
    g.text('TIER 2: SOMATIC', 700, 266, 20, MUTED, k2, bold=True)
    g.para('A defence inside each person\'s own body (next)', 700, 320, 440, 22, MUTED, k2)


def s_lag(g, t, B, D):
    g.background(t, ORANGE, 39)
    g.header(t, 'Here and now', 'Law lags behind extraction')
    x0, y0, w, h = 110, 210, 620, 330
    k = ap(t, 0.3)
    g.axes(x0, y0, w, h, 'years', '', MUTED, k)
    g.plot(x0, y0, w, h, lambda u: 0.05 + 0.9 * u ** 1.6, min(1, (t - 0.4) / 3), RED, k)
    g.plot(x0, y0, w, h, lambda u: 0.05 + 0.45 * max(0, u - 0.3) ** 1.2, min(1, (t - 1.2) / 3), TEAL, ap(t, 1.2))
    g.text('technological extraction', x0 + w, y0 + 20, 17, RED, k, bold=True, align='r')
    g.text('regulation', x0 + w, y0 + h - 70, 17, TEAL, ap(t, 1.2), bold=True, align='r')
    ks = ap(t, B['spike'], 0.6)
    x1, y1 = 800, 260
    g.text('the nervous system spikes', x1 + 200, y1 - 10, 18, WHITE, ks, bold=True, align='c')
    beat = lambda u: 0.3 + 0.12 * math.sin(u * 40) + 0.5 * math.exp(-((u - 0.6) / 0.05) ** 2)
    g.plot(x1, y1, 400, 200, beat, ap(t, B['spike'], 2.5), RED, ks, lw=2.5)
    ki = ap(t, B['intercept'], 0.5)
    g.line([(x1 + 400 * 0.52, y1), (x1 + 400 * 0.52, y1 + 200)], TEAL, ki, 2, dash=[6, 6])
    g.tag(x1 + 400 * 0.52, y1 + 250, 'intercept here', TEAL, ki, 16)


def s_fire(g, t, B, D):
    g.background(t, ORANGE, 40)
    g.header(t, 'Internal Qigong alchemy, after Dr. Carl Totton', 'Notice the Fire', 'Threat narratives create physical hyper-arousal')
    k = ap(t, 0.3)
    g.body(330, 170, 0.98, CYAN, k * 0.8)
    kf = ap(t, B['fire'], 0.7)
    g.flame(330, 330, 0.9 + 0.3 * kf, t, ORANGE, kf)
    kh = ap(t, B['heart'], 0.6)
    rate = lambda u: 0.35 + 0.25 * u + 0.2 * max(0, math.sin(u * 26)) ** 8
    g.plot(620, 260, 520, 160, rate, ap(t, B['heart'], 3.0), RED, kh, lw=2.5)
    g.text('heart rate rising', 880, 250, 18, RED, kh, bold=True, align='c')
    ko = ap(t, B['observe'], 0.6)
    g.eye(880, 520, 1.0, TEAL, ko, open_=0.3 + 0.7 * ap(t, B['observe'], 1.0))
    g.text('observe the heat, before the mind latches on', 880, 590, 18, TEAL, ko, bold=True, align='c')


def s_water(g, t, B, D):
    g.background(t, CYAN, 41)
    g.header(t, 'The manual override', 'Turning Fire into Water', 'Attention moves off the screen and into the body\'s contact with the ground')
    k = ap(t, 0.3)
    g.rrect(250, 190, 160, 100, 10, fill=(*CYAN, 0.2), stroke=CYAN, a=k * (1 - 0.6 * ap(t, B['drop'], 1.0)), lw=2)
    g.text('the screen', 330, 248, 17, WHITE, k, bold=True, align='c')
    g.body(620, 175, 0.85, CYAN, k * 0.8)
    kd = ap(t, B['drop'], 2.0)
    yy = lerp(240, 520, kd)
    g.arrow(420, 240, 590, yy, kd, TEAL, lw=3, bend=-60)
    kc = ap(t, B['contact'], 0.7)
    for x in (592, 648):
        g.dot(x, 535, 9, TEAL, kc)
    g.ripples(620, 542, 1.2, t, TEAL, kc)
    g.text('contact points with the earth', 620, 594, 17, TEAL, kc, bold=True, align='c')
    kt = ap(t, B['trans'], 1.5)
    g.flame(940, 380, 0.9 * (1 - kt), t, ORANGE, 1 - kt)
    g.ripples(940, 380, 1.0, t, CYAN, kt)
    g.text('Fire' if kt < 0.5 else 'Water', 940, 450, 26, ORANGE if kt < 0.5 else CYAN, ap(t, B['trans'] - 0.6), bold=True, align='c')
    ks = ap(t, B['off'], 0.6)
    g.bar(830, 520, 220, 14, 0.9 - 0.75 * ap(t, B['off'], 2.0), ORANGE, ks, 'cortisol', '')


def s_predict(g, t, B, D):
    g.background(t, CYAN, 42)
    g.header(t, 'Predictive models', 'A rigid target, or still water')
    k1 = ap(t, B['rigid'], 0.6)
    for i in range(4):
        for j in range(3):
            g.rrect(150 + i * 70, 260 + j * 70, 58, 58, 6, fill=(*WHITE, 0.15), stroke=WHITE, a=k1, lw=1.5)
    lock = ap(t, B['rigid'] + 1.0, 1.0)
    cx, cy = 290, 365
    g.ring(cx, cy, 120 - 40 * lock, RED, k1, 2)
    g.line([(cx - 150, cy), (cx + 150, cy)], RED, k1 * 0.6, 1.2, glow=False)
    g.line([(cx, cy - 150), (cx, cy + 150)], RED, k1 * 0.6, 1.2, glow=False)
    g.text('rigid habits: predictable, exploitable', cx, 560, 18, RED, k1, bold=True, align='c')
    kw = ap(t, B['water'], 0.8)
    g.rrect(700, 380, 420, 6, 3, fill=(*CYAN, 0.8), a=kw)
    g.dot(910, 300, 26, GOLD, kw)
    g.dot(910, 466, 26, GOLD, kw * 0.45)
    g.ripples(910, 383, 1.2, t * 0.5, CYAN, kw * 0.6, 3)
    g.text('reflects everything, absorbs nothing', 910, 560, 18, CYAN, kw, bold=True, align='c')


def s_hook(g, t, B, D):
    g.background(t, TEAL, 43)
    g.header(t, 'A formless, fluid mind', 'Nothing for the hook to catch', None, TEAL)
    k = ap(t, 0.3)
    # left: a rigid anchor gets hooked
    g.rrect(180, 380, 120, 120, 10, fill=(*RED, 0.3), stroke=RED, a=k, lw=2)
    g.text('rigid emotional habit', 240, 540, 17, RED, k, bold=True, align='c')
    g.line([(240, 190), (240, 330), (225, 360), (240, 380)], MUTED, k, 2.5)
    # right: the hook drops onto water and finds nothing
    kh = ap(t, B['inject'], 0.6)
    y = lerp(190, 400, ease((t - B['inject']) / 2.0))
    g.rrect(620, 410, 520, 8, 4, fill=(*CYAN, 0.7), a=k)
    g.line([(880, 180), (880, y), (865, y + 22), (880, y + 34)], GOLD, kh, 2.5)
    g.ripples(880, 414, 1.0, t, CYAN, k * ap(t, B['inject'] + 1.6, 0.6))
    g.text('an injection of panic', 880, 170, 17, GOLD, kh, bold=True, align='c')
    ks = ap(t, B['starve'], 0.6)
    g.text('no anchor: the snare loses its power', 880, 500, 20, TEAL, ks, bold=True, align='c')


def s_screen_net(g, t, B, D):
    """A wall-screen picture: global network traffic."""
    g.background(t, CYAN, 50)
    g.text('GLOBAL NETWORK TRAFFIC', 64, 70, 18, CYAN, 1, bold=True, spacing=3)
    g.node_net(640, 400, 560, 250, 70, t, 1.0, CYAN, 1.0, seed=8, links=3)


SCENES = {f.__name__[2:]: f for f in (s_outrage, s_hydra, s_phronesis, s_metis, s_thrasymachus, s_acute, s_hpa, s_funnel, s_cave, s_hegemony,
                                       s_ocean, s_optimize, s_taxonomy, s_whole, s_growth, s_inversion, s_market, s_profile, s_track, s_pfc,
                                       s_dendrites, s_chariot, s_chariot2, s_whip, s_neurochem, s_marathon, s_shield, s_tiers, s_lag, s_fire,
                                       s_water, s_predict, s_hook, s_screen_net)}

# ---------------------------------------------------------------- the plan
# id, scene, (element, word where it cuts in), (element, word it runs to the end of, or None for the end of the line),
# beats {name: (element, word)}, extra arguments
PLAN = [
    ('g01', 'outrage', (13, 'They are micro-targeting'), (13, None), {'targets': (13, 'hyper-personalized'), 'loop': (13, 'conspiracy')}, {}),
    ('g02', 'hydra', (15, 'The baseline'), (15, 'toxic pudding'), {'a1': (15, 'alienation'), 'a2': (15, 'existential'), 'a3': (15, 'neurochemical'), 'hydra': (15, 'Hydra'),
                                                                     'cut': (15, 'head'), 'pudding': (15, 'toxic pudding')}, {}),
    ('g03', 'phronesis', (16, 'We sought phronesis'), (16, None), {'phron': (16, 'phronesis'), 'h': (16, 'holistic'), 'm': (16, 'morally'), 'g': (16, 'objective good'),
                                                                   'eud': (16, 'eudaimonia'), 'q': (16, 'What kind')}, {}),
    ('g04', 'metis', (17, 'It is the capacity'), (17, None), {'ends': (17, 'extractive'), 'metis': (17, 'metis'), 'agnostic': (17, 'agnostic')}, {}),
    ('g05', 'thrasymachus', (18, 'You have built'), (18, None), {'rewards': (18, 'structurally rewards'), 'capital': (18, 'quantifiable')}, {}),
    ('g06', 'acute', (19, 'The human nervous system'), (19, None), {'acute': (19, 'acute'), 'chronic': (19, 'chronic')}, {}),
    ('g07', 'hpa', (20, 'They force'), (20, None), {'h': (20, 'Hypothalamic-Pituitary-Adrenal'), 'p': (20, 'Hypothalamic-Pituitary-Adrenal'), 'a': (20, 'axis'),
                                                    'cortisol': (20, 'glucocorticoids'), 'brain': (20, 'floods'), 'shrink': (20, 'shrinking')}, {}),
    ('g08', 'funnel', (22, 'They reduce'), (22, None), {'shell': (22, 'emptied')}, {}),
    ('g09', 'cave', (24, 'How will you'), (24, None), {'chains': (24, 'chains')}, {'variant': 1}),
    ('g10', 'hegemony', (30, 'The system no longer'), (30, None), {'now': (30, 'decentralized'), 'oversight': (30, 'without human')}, {}),
    ('g11', 'ocean', (31, 'Data-driven'), (31, None), {'bypass': (31, 'bypass'), 'ocean': (31, 'OCEAN'), 'drill': (31, 'data drilling')}, {}),
    ('g12', 'optimize', (32, 'They intentionally'), (32, None), {'n': (32, 'neuroticism'), 'f': (32, 'fear'), 'c': (32, 'confusion'), 'anx': (32, 'anxieties'),
                                                                 'fin': (32, 'financial')}, {}),
    ('g13', 'taxonomy', (36, 'Classical Greek'), (36, None), {'telos': (36, 'telos'), 'phron': (36, 'phronesis')}, {}),
    ('g14', 'whole', (38, 'Because phronesis'), (38, None), {'inter': (38, 'interdependency'), 'eud': (38, 'eudaimonia')}, {}),
    ('g15', 'growth', (39, 'And the digital'), (39, None), {'eud': (39, 'eudaimonia'), 'unfinished': (39, 'unfinished')}, {}),
    ('g16', 'inversion', (40, 'In stark contrast'), (40, None), {'metis': (40, 'stands metis'), 'flip': (40, 'inverted')}, {}),
    ('g17', 'market', (41, 'Under the mandates'), (41, None), {'phron': (41, 'phronesis'), 'metis': (41, 'metis'), 'rewarded': (41, 'efficiently engineer')}, {}),
    ('g18', 'profile', (42, 'To reduce'), (42, None), {'profiles': (42, 'data profiles'), 'means': (42, 'means to')}, {}),
    ('g19', 'track', (43, 'We can deploy'), (43, None), {'track': (43, 'track'), 'vuln': (43, 'trigger'), 'snap': (43, 'snap')}, {}),
    ('g20', 'pfc', (52, 'The Prefrontal'), (52, None), {'pfc': (52, 'Prefrontal'), 'crit': (52, 'critical'), 'logic': (52, 'logical'), 'will': (52, 'willpower'),
                                                       'cost': (52, 'expensive'), 'suppress': (52, 'suppress')}, {}),
    ('g21', 'cave', (54, 'They function'), (54, None), {'chains': (54, 'micro-metrics'), 'puppet': (54, 'automated puppeteer'), 'metrics': (54, 'typing')}, {'variant': 2}),
    ('g22', 'acute', (55, 'The human nervous system'), (55, None), {'acute': (55, 'acute'), 'chronic': (55, 'chronic'), 'on': (55, 'lock')}, {'variant': 'savanna'}),
    ('g23', 'hpa', (56, 'This continuous'), (56, None), {'h': (56, 'Hypothalamic-Pituitary-Adrenal'), 'p': (56, 'Hypothalamic-Pituitary-Adrenal'), 'a': (56, 'HPA-axis'),
                                                        'cortisol': (56, 'glucocorticoids'), 'short': (56, 'short term'), 'neuro': (56, 'neurotoxic')}, {'variant': 2}),
    ('g24', 'dendrites', (58, 'Yes.'), (58, None), {'atrophy': (58, 'dendritic')}, {}),
    ('g25', 'chariot', (62, 'In my student'), (62, None), {'char': (62, 'Charioteer'), 'noble': (62, 'noble'), 'wild': (62, 'wild horse')}, {}),
    ('g26', 'chariot2', (64, 'then the energy'), (65, None), {'out': (64, 'passes out'), 'map': (65, 'logical driver'), 'bolt': (65, 'bolts')}, {}),
    ('g27', 'whip', (66, 'It acts as'), (66, None), {'whip': (66, 'whip'), 'amyg': (66, 'amygdala'), 'anger': (66, 'focused')}, {}),
    ('g28', 'neurochem', (67, 'We can map'), (67, None), {'dopa': (67, 'dopamine'), 'nor': (67, 'norepinephrine'), 'witness': (67, 'witness')}, {}),
    ('g29', 'marathon', (74, 'When the prefrontal'), (74, None), {'cortisol': (74, 'chronic cortisol'), 'demand': (74, 'demanding')}, {}),
    ('g30', 'shield', (77, 'We built'), (77, None), {'shield': (77, 'psychological shield')}, {}),
    ('g31', 'tiers', (79, 'The first tier'), (79, None), {'tier1': (79, 'first tier'), 'bar': (79, 'barring')}, {}),
    ('g32', 'lag', (80, 'But regulatory'), (80, None), {'spike': (80, 'chemical sequence'), 'intercept': (80, 'intercept')}, {}),
    ('g33', 'fire', (82, 'When the algorithm'), (82, None), {'fire': (82, 'Fire'), 'heart': (82, 'heart rate'), 'observe': (82, 'observe')}, {}),
    ('g34', 'water', (83, 'Once that'), (83, None), {'drop': (83, 'drop'), 'contact': (83, 'contact points'), 'trans': (83, 'transmutes'), 'off': (83, 'shuts off')}, {}),
    ('g35', 'predict', (86, 'Predictive'), (86, None), {'rigid': (86, 'rigid'), 'water': (86, 'But water')}, {}),
    ('g36', 'hook', (88, 'By cultivating'), (88, None), {'inject': (88, 'injection'), 'starve': (88, 'loses')}, {}),
]


def windows(items_by_el):
    """Each graphic's place: {id, seq, t0, t1 (seconds in its sequence), beats (seconds from t0)}.
    items_by_el maps element -> (seq, item start time in the sequence)."""
    out = []
    for gid, scene, (e0, w0), (e1, w1), beats, extra in PLAN:
        s0, it0 = items_by_el[e0]
        s1, it1 = items_by_el[e1]
        t0 = it0 + word_t(e0, w0) - 0.25
        t1 = it1 + word_t(e1, w1, end=True) + (0.35 if w1 is None else 0.4)
        B = {}
        for name, (e, w) in beats.items():
            B[name] = items_by_el[e][1] + word_t(e, w) - t0
        out.append({'id': gid, 'scene': scene, 'seq': s0, 't0': round(t0, 3), 't1': round(t1, 3), 'beats': B, 'extra': extra})
    return out


def render(win, out_path, size=(1280, 720)):
    D = win['t1'] - win['t0']
    n = int(round(D * FPS))
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % size, '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', out_path], stdin=subprocess.PIPE)
    fn = SCENES[win['scene']]
    for k in range(n):
        g = G(*size)
        fn(g, k / FPS, win['beats'], D, **win['extra'])
        p.stdin.write(g.rgb().tobytes())
    p.stdin.close()
    p.wait()
    return n


def still(win, t, size=(1280, 720)):
    g = G(*size)
    SCENES[win['scene']](g, t, win['beats'], win['t1'] - win['t0'], **win['extra'])
    return g


if __name__ == '__main__':
    PH.update(json.load(open(sys.argv[1])))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    plans = sys.argv[sys.argv.index('--plans') + 1].split(',') if '--plans' in sys.argv else []
    items = {}
    for k, p in enumerate(plans):
        for (i, who, t, secs) in json.load(open(p))['items']:
            items[i] = (k + 1, t)
    wins = windows(items)
    json.dump(wins, open(os.path.join(out, 'graphics.json'), 'w'), indent=1)
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    if '--sheet' in sys.argv:
        from PIL import Image
        ims = []
        for w in wins:
            if only and w['id'] not in only:
                continue
            g = still(w, (w['t1'] - w['t0']) - 0.2, (640, 360))
            ims.append(Image.fromarray(g.rgb()))
        cols = 3
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new('RGB', (640 * cols, 360 * rows))
        for k, im in enumerate(ims):
            sheet.paste(im, ((k % cols) * 640, (k // cols) * 360))
        sheet.save(sys.argv[sys.argv.index('--sheet') + 1])
        print('sheet', len(ims))
    if '--render' in sys.argv:
        tot = 0
        for w in wins:
            if only and w['id'] not in only:
                continue
            tot += render(w, os.path.join(out, w['id'] + '.mp4'))
        print('rendered', tot, 'frames')
    print(len(wins), 'graphics, %.1f s in all' % sum(w['t1'] - w['t0'] for w in wins))
