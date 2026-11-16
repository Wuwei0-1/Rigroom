"""Pictures for the lounge's wall screens in The Ring of Gyges III, drawn in the explainer graphics' style.

    python screens.py NEWS.jpg OUT_DIR

Centre screen pictures are 1740x900 (the screen's 2.9 x 1.5 m shape); side screens 840x896 (1.5 x 1.6 m).
"""
import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import CYAN, GOLD, MUTED, ORANGE, RED, TEAL, VIOLET, WHITE, G  # noqa: E402

CW, CH = 1740, 900
SW, SH = 840, 896


def centre():
    return G(CW, CH, 1280)


def side():
    return G(SW, SH, 700)


def label(g, kicker, title, col=CYAN):
    g.text(kicker.upper(), 48, 60, 16, col, 1, bold=True, spacing=3)
    g.text(title, 48, 104, 36, WHITE, 1, bold=True)


def traffic():
    g = centre()
    g.background(3.0, CYAN, 61)
    label(g, 'Live', 'Global network traffic')
    g.node_net(640, 420, 560, 210, 90, 2.0, 1.0, CYAN, 1.0, seed=9, links=3)
    for i in range(24):
        h = 30 + 90 * abs(math.sin(i * 1.7)) ** 1.5
        g.rrect(60 + i * 48, 650 - h, 30, h, 4, fill=(*(RED if h > 100 else CYAN), 0.7), a=1)
    g.text('engagement per minute', 60, 680, 16, MUTED)
    return g


def architecture():
    g = centre()
    g.background(3.0, TEAL, 62)
    label(g, 'Underlying architecture', 'A self-sustaining system', TEAL)
    pts = g.node_net(640, 400, 540, 200, 70, 1.0, 1.0, TEAL, 1.0, seed=12, links=3)
    for i, lab in enumerate(('recommender', 'ad exchange', 'data broker', 'feed ranker', 'bot farm')):
        x, y = pts[i * 9 + 3]
        g.tag(x, y - 16, lab, TEAL, 1, 16)
    g.text('no human oversight', 1232, 680, 20, RED, 1, bold=True, align='r')
    return g


def neuro():
    g = centre()
    g.background(3.0, ORANGE, 63)
    label(g, 'Neural mapping', 'The physical host', ORANGE)
    g.body(300, 150, 1.05, CYAN, 0.9)
    for (x, y, lab) in ((300, 180, 'hypothalamus'), (300, 202, 'pituitary'), (300, 392, 'adrenals')):
        g.dot(x, y, 8, ORANGE, 1)
        g.text(lab, x + 26, y + 6, 16, WHITE, 1)
    g.brain(900, 380, 1.25, CYAN, 1.0, pfc=GOLD)
    g.text('prefrontal cortex', 700, 220, 20, GOLD, 1, bold=True)
    return g


def mirror():
    g = centre()
    g.background(3.0, TEAL, 64)
    label(g, 'Protocol', 'The Mirror Force', TEAL)
    g.shield(640, 330, 2.1, TEAL, 1.0)
    g.ripples(640, 520, 2.0, 1.3, CYAN, 1.0, 5)
    g.text('lens  >  shield  >  still water', 640, 630, 22, WHITE, 1, bold=True, align='c')
    return g


def panel_bars(kicker, title, labels, values, col):
    g = side()
    g.background(2.0, col, 70)
    g.text(kicker.upper(), 40, 60, 15, col, 1, bold=True, spacing=3)
    g.text(title, 40, 100, 30, WHITE, 1, bold=True)
    for i, (lab, v) in enumerate(zip(labels, values)):
        g.bar(40, 190 + i * 100, 600, 18, v, RED if v > 0.8 else col, 1, lab, '%d%%' % (v * 100))
    return g


def panel_curve(kicker, title, col):
    g = side()
    g.background(2.0, col, 71)
    g.text(kicker.upper(), 40, 60, 15, col, 1, bold=True, spacing=3)
    g.text(title, 40, 100, 30, WHITE, 1, bold=True)
    g.axes(50, 170, 600, 420, 'weeks', 'cortisol', MUTED, 1)
    g.plot(50, 170, 600, 420, lambda u: min(0.95, 0.15 + 0.7 * u + 0.06 * math.sin(u * 50)), 1.0, RED, 1, fill=True)
    return g


def panel_water():
    g = side()
    g.background(2.0, CYAN, 72)
    g.text('SOMATIC EGRESS', 40, 60, 15, CYAN, 1, bold=True, spacing=3)
    g.text('Fire into Water', 40, 100, 30, WHITE, 1, bold=True)
    g.flame(200, 420, 1.3, 0.4, ORANGE, 0.8)
    g.arrow(280, 360, 420, 360, 1.0, TEAL, lw=3)
    g.ripples(540, 370, 1.0, 0.7, CYAN, 1.0)
    return g


def news_sides(path, out):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    for nm, (u0, v0, u1, v1) in (('raids_left', (0.02, 0.3, 0.42, 0.95)), ('raids_right', (0.55, 0.3, 0.95, 0.95))):
        box = (int(u0 * w), int((1 - v1) * h), int(u1 * w), int((1 - v0) * h))
        im.crop(box).resize((SW, SH)).save(os.path.join(out, nm + '.png'))
    im.resize((CW, CH)).save(os.path.join(out, 'news.png'))


if __name__ == '__main__':
    news, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    news_sides(news, out)
    for nm, g in (('traffic', traffic()), ('architecture', architecture()), ('neuro', neuro()), ('mirror', mirror()),
                  ('traffic_side', panel_bars('Engagement', 'Outrage metrics', ['conspiracy', 'fear', 'anger', 'trust'], [0.86, 0.78, 0.92, 0.18], CYAN)),
                  ('ocean_side', panel_bars('Psychographics', 'O C E A N', ['Openness', 'Conscientiousness', 'Extraversion', 'Agreeableness', 'Neuroticism'],
                                            [0.42, 0.35, 0.5, 0.55, 0.86], VIOLET)),
                  ('cortisol_side', panel_curve('Chronic exposure', 'Cortisol', ORANGE)), ('water_side', panel_water())):
        Image.fromarray(g.rgb()).save(os.path.join(out, nm + '.png'))
    print('screens written to', out)
