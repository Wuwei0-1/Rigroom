"""Drawing kit for explainer graphics: a dark, glowing diagram style that matches the lounge's screens.

Everything is drawn with cairo on a 1280x720 canvas (scaled for other sizes). Times are in seconds; ap() eases
things in. Colours are RGB 0-1 tuples.
"""
import math
import random

import cairo
import numpy as np

W, H = 1280, 720
CYAN = (0.35, 0.84, 1.0)
TEAL = (0.25, 0.88, 0.77)
GOLD = (0.95, 0.77, 0.43)
RED = (1.0, 0.37, 0.37)
ORANGE = (1.0, 0.6, 0.28)
WHITE = (0.92, 0.95, 0.97)
MUTED = (0.54, 0.64, 0.72)
DIM = (0.16, 0.27, 0.37)
INK = (0.03, 0.07, 0.12)
VIOLET = (0.7, 0.55, 1.0)
FONT = 'Inter'


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ap(t, t0, d=0.6):
    """0 before t0, easing to 1 over d seconds."""
    return ease((t - t0) / d) if d > 0 else float(t >= t0)


def lerp(a, b, k):
    return a + (b - a) * k


def mix(c1, c2, k):
    return tuple(lerp(a, b, k) for a, b in zip(c1, c2))


class G:
    """A frame: cairo context with the kit's drawing calls."""

    def __init__(self, w=W, h=H, logical_w=None):
        """logical_w: draw in units where the width is logical_w, keeping the shape (for screens of other shapes)."""
        self.s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
        self.c = cairo.Context(self.s)
        if logical_w:
            self.c.scale(w / logical_w, w / logical_w)
        else:
            self.c.scale(w / W, h / H)
        self.w, self.h = w, h

    # ---- output
    def rgb(self):
        buf = np.frombuffer(self.s.get_data(), np.uint8).reshape(self.h, self.s.get_stride() // 4, 4)[:, :self.w]
        return np.ascontiguousarray(buf[:, :, [2, 1, 0]])

    # ---- background
    def background(self, t, tint=CYAN, seed=1):
        c = self.c
        g = cairo.RadialGradient(W * 0.5, H * 0.42, 60, W * 0.5, H * 0.5, W * 0.75)
        g.add_color_stop_rgb(0, 0.05, 0.12, 0.2)
        g.add_color_stop_rgb(1, 0.012, 0.03, 0.06)
        c.set_source(g)
        c.paint()
        # a faint dot grid and slow drifting motes
        c.set_source_rgba(*tint, 0.07)
        for x in range(40, W, 40):
            for y in range(40, H, 40):
                c.rectangle(x - 0.8, y - 0.8, 1.6, 1.6)
        c.fill()
        rng = random.Random(seed)
        for _ in range(38):
            x0, y0, vx, vy, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(-6, 6), rng.uniform(-9, -2), rng.uniform(0.8, 2.2)
            x, y = (x0 + vx * t) % W, (y0 + vy * t) % H
            c.set_source_rgba(*tint, 0.12)
            c.arc(x, y, r, 0, 2 * math.pi)
            c.fill()

    # ---- text
    def font(self, size, bold=False, italic=False):
        self.c.select_font_face(FONT, cairo.FONT_SLANT_ITALIC if italic else cairo.FONT_SLANT_NORMAL,
                                cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        self.c.set_font_size(size)

    def text_w(self, s, size, bold=False, spacing=0.0):
        self.font(size, bold)
        return self.c.text_extents(s).x_advance + spacing * max(0, len(s) - 1)

    def text(self, s, x, y, size=24, col=WHITE, a=1.0, bold=False, align='l', spacing=0.0, italic=False):
        if a <= 0.003 or not s:
            return
        c = self.c
        self.font(size, bold, italic)
        w = self.text_w(s, size, bold, spacing)
        self.font(size, bold, italic)
        x0 = x - (w / 2 if align == 'c' else (w if align == 'r' else 0))
        c.set_source_rgba(*col, a)
        if spacing:
            xx = x0
            for ch in s:
                c.move_to(xx, y)
                c.show_text(ch)
                xx += c.text_extents(ch).x_advance + spacing
        else:
            c.move_to(x0, y)
            c.show_text(s)
        return w

    def para(self, s, x, y, width, size=20, col=WHITE, a=1.0, lead=1.35, bold=False, align='l'):
        """Wrapped text; returns the y below it."""
        words, line, lines = s.split(), '', []
        for wd in words:
            test = (line + ' ' + wd).strip()
            if self.text_w(test, size, bold) > width and line:
                lines.append(line)
                line = wd
            else:
                line = test
        if line:
            lines.append(line)
        for k, ln in enumerate(lines):
            self.text(ln, x, y + k * size * lead, size, col, a, bold, align)
        return y + len(lines) * size * lead

    def header(self, t, kicker, title, sub=None, col=CYAN):
        """The kicker in small capitals, the title, and an optional line under it, easing in."""
        k1, k2, k3 = ap(t, 0.0, 0.5), ap(t, 0.15, 0.6), ap(t, 0.4, 0.6)
        self.text(kicker.upper(), 64, 70, 15, col, k1, bold=True, spacing=3.2)
        self.c.set_source_rgba(*col, 0.8 * k1)
        self.c.rectangle(64, 80, 46 * k1, 2.5)
        self.c.fill()
        self.text(title, 64 - 14 * (1 - k2), 124, 40, WHITE, k2, bold=True)
        if sub:
            self.text(sub, 64, 156, 19, MUTED, k3)

    # ---- shapes
    def rrect(self, x, y, w, h, r=10, fill=None, stroke=None, a=1.0, lw=2.0, glow=False):
        if a <= 0.003:
            return
        c = self.c
        c.new_path()
        c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        c.close_path()
        if fill:
            c.set_source_rgba(*fill[:3], (fill[3] if len(fill) > 3 else 1.0) * a)
            c.fill_preserve()
        if stroke:
            if glow:
                c.set_source_rgba(*stroke, 0.18 * a)
                c.set_line_width(lw * 4)
                c.stroke_preserve()
            c.set_source_rgba(*stroke, a)
            c.set_line_width(lw)
            c.stroke()
        c.new_path()

    def card(self, x, y, w, h, title, body=None, col=CYAN, a=1.0, size=22, body_size=16, align='c'):
        """A rounded box with a bold label and an optional smaller line."""
        self.rrect(x, y, w, h, 12, fill=(*INK, 0.85), stroke=col, a=a, lw=2, glow=True)
        if body:
            self.text(title, x + w / 2 if align == 'c' else x + 16, y + h / 2 - 4, size, WHITE, a, bold=True, align=align)
            self.para(body, x + w / 2 if align == 'c' else x + 16, y + h / 2 + body_size + 4, w - 24, body_size, MUTED, a, align=align)
        else:
            self.text(title, x + w / 2 if align == 'c' else x + 16, y + h / 2 + size * 0.36, size, WHITE, a, bold=True, align=align)

    def line(self, pts, col=CYAN, a=1.0, lw=2.5, glow=True, dash=None):
        if a <= 0.003 or len(pts) < 2:
            return
        c = self.c
        for width, alpha in (((lw * 4, 0.16), (lw, 1.0)) if glow else ((lw, 1.0),)):
            c.new_path()
            c.move_to(*pts[0])
            for p in pts[1:]:
                c.line_to(*p)
            c.set_source_rgba(*col, alpha * a)
            c.set_line_width(width)
            c.set_line_cap(cairo.LINE_CAP_ROUND)
            c.set_line_join(cairo.LINE_JOIN_ROUND)
            if dash:
                c.set_dash(dash)
            c.stroke()
            c.set_dash([])

    def arrow(self, x0, y0, x1, y1, prog=1.0, col=CYAN, a=1.0, lw=2.5, head=12, bend=0.0, glow=True):
        """An arrow drawn out from its start; bend curves it sideways (pixels)."""
        if prog <= 0.001 or a <= 0.003:
            return
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy) or 1
        cx, cy = mx - dy / L * bend, my + dx / L * bend
        pts = []
        n = 24
        for k in range(n + 1):
            u = k / n * prog
            pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy + u * u * y1))
        self.line(pts, col, a, lw, glow)
        if prog > 0.6:
            (ax, ay), (bx, by) = pts[-2], pts[-1]
            ang = math.atan2(by - ay, bx - ax)
            c = self.c
            c.new_path()
            c.move_to(bx, by)
            c.line_to(bx - head * math.cos(ang - 0.45), by - head * math.sin(ang - 0.45))
            c.line_to(bx - head * math.cos(ang + 0.45), by - head * math.sin(ang + 0.45))
            c.close_path()
            c.set_source_rgba(*col, a * ap(prog, 0.6, 0.3))
            c.fill()

    def dot(self, x, y, r, col=CYAN, a=1.0, glow=True, fill=True):
        if a <= 0.003:
            return
        c = self.c
        if glow:
            g = cairo.RadialGradient(x, y, 0, x, y, r * 3.2)
            g.add_color_stop_rgba(0, *col, 0.35 * a)
            g.add_color_stop_rgba(1, *col, 0)
            c.set_source(g)
            c.arc(x, y, r * 3.2, 0, 2 * math.pi)
            c.fill()
        c.arc(x, y, r, 0, 2 * math.pi)
        c.set_source_rgba(*col, a)
        if fill:
            c.fill()
        else:
            c.set_line_width(2)
            c.stroke()

    def ring(self, x, y, r, col=CYAN, a=1.0, lw=2.5, prog=1.0, start=-90):
        if a <= 0.003 or prog <= 0:
            return
        c = self.c
        a0 = math.radians(start)
        for width, alpha in ((lw * 4, 0.15), (lw, 1.0)):
            c.new_path()
            c.arc(x, y, r, a0, a0 + 2 * math.pi * prog)
            c.set_source_rgba(*col, alpha * a)
            c.set_line_width(width)
            c.stroke()

    def path(self, pts, closed=True, fill=None, stroke=None, a=1.0, lw=2.0, smooth=True):
        """A smooth closed (or open) curve through points (Catmull-Rom)."""
        if a <= 0.003:
            return
        c = self.c
        c.new_path()
        n = len(pts)
        P = pts + pts[:3] if closed else [pts[0]] + pts + [pts[-1]]
        if not smooth:
            c.move_to(*pts[0])
            for p in pts[1:]:
                c.line_to(*p)
        else:
            rng_ = range(n) if closed else range(n - 1)
            off = 0 if closed else 1
            c.move_to(*P[off + (0 if not closed else 1)] if closed else pts[0])
            for i in rng_:
                p0, p1, p2, p3 = (P[i + off - 1] if i + off - 1 >= 0 else P[0]), P[i + off], P[i + off + 1], P[min(i + off + 2, len(P) - 1)]
                if closed:
                    p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
                c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
                c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
                c.curve_to(*c1, *c2, *p2)
        if closed:
            c.close_path()
        if fill:
            c.set_source_rgba(*fill[:3], (fill[3] if len(fill) > 3 else 1.0) * a)
            c.fill_preserve()
        if stroke:
            c.set_source_rgba(*stroke, a * 0.18)
            c.set_line_width(lw * 4)
            c.stroke_preserve()
            c.set_source_rgba(*stroke, a)
            c.set_line_width(lw)
            c.stroke()
        c.new_path()

    def bar(self, x, y, w, h, k, col=CYAN, a=1.0, label=None, value=None):
        """A horizontal meter filled to k (0-1)."""
        self.rrect(x, y, w, h, h / 2, fill=(*DIM, 0.6), a=a)
        if k > 0.01:
            self.rrect(x, y, max(h, w * min(1.0, k)), h, h / 2, fill=col, a=a)
        if label:
            self.text(label, x, y - 8, 16, WHITE, a, bold=True)
        if value:
            self.text(value, x + w, y - 8, 15, col, a, align='r', bold=True)

    # ---- icons
    def person(self, x, y, s=1.0, col=WHITE, a=1.0, fill=False):
        """A simple figure: head and shoulders, about 60*s tall, centred on x, standing on y."""
        if a <= 0.003:
            return
        c = self.c
        c.new_path()
        c.arc(x, y - 44 * s, 11 * s, 0, 2 * math.pi)
        c.new_sub_path()
        c.move_to(x - 22 * s, y)
        c.curve_to(x - 22 * s, y - 22 * s, x - 14 * s, y - 29 * s, x, y - 29 * s)
        c.curve_to(x + 14 * s, y - 29 * s, x + 22 * s, y - 22 * s, x + 22 * s, y)
        c.close_path()
        if fill:
            c.set_source_rgba(*col, a)
            c.fill()
        else:
            c.set_source_rgba(*col, 0.15 * a)
            c.set_line_width(7 * s)
            c.stroke_preserve()
            c.set_source_rgba(*col, a)
            c.set_line_width(2.2 * s)
            c.stroke()

    def brain(self, x, y, s=1.0, col=CYAN, a=1.0, pfc=None, pfc_k=1.0, fill=0.12, folds=True):
        """A brain seen from its left side (front to the left), about 300*s wide, centred at x, y.
        pfc: a colour to light the prefrontal cortex with; pfc_k shrinks it (1 full, 0.6 withered)."""
        if a <= 0.003:
            return
        P = lambda u, v: (x + u * s, y + v * s)
        outline = [P(-150, 10), P(-145, -45), P(-118, -88), P(-70, -118), P(-10, -128), P(55, -118), P(110, -88), P(145, -40), P(150, 10),
                   P(132, 52), P(95, 70), P(60, 66), P(30, 80), P(-20, 82), P(-75, 72), P(-125, 50)]
        self.path(outline, fill=(*col, fill), stroke=col, a=a, lw=2.2)
        # cerebellum and brain stem
        self.path([P(70, 66), P(118, 62), P(132, 82), P(112, 104), P(78, 98), P(62, 80)], fill=(*col, fill * 0.8), stroke=col, a=a * 0.8, lw=1.6)
        self.line([P(40, 78), P(52, 120), P(48, 150)], col, a * 0.8, 9, glow=False)
        if folds:
            for pts in ([(-100, -60), (-60, -40), (-40, -80)], [(-20, -100), (0, -60), (30, -90)], [(60, -90), (50, -40), (90, -50)],
                        [(-110, 0), (-60, 10), (-20, -20)], [(10, -20), (50, 0), (100, -10)], [(-60, 50), (-10, 40), (40, 50)], [(-130, 20), (-110, 40)]):
                self.line([P(*p) for p in pts], col, a * 0.45, 1.6, glow=False)
        if pfc:
            k = pfc_k
            cx, cy = -105, -45
            region = [P(cx + (u - cx) * k, cy + (v - cy) * k) for u, v in [(-148, 0), (-144, -46), (-118, -88), (-78, -112), (-48, -96), (-58, -48), (-82, -8), (-118, 10)]]
            self.path(region, fill=(*pfc, 0.55 * a), stroke=pfc, a=a, lw=2.5)

    def body(self, x, y, s=1.0, col=CYAN, a=1.0):
        """A front-facing human outline, head at the top, about 420*s tall, top at y."""
        P = lambda u, v: (x + u * s, y + v * s)
        self.path([P(0, 0), P(30, 10), P(36, 44), P(24, 78), P(14, 92), P(70, 108), P(92, 140), P(98, 230), P(84, 300), P(70, 300), P(66, 200),
                   P(58, 250), P(52, 420), P(12, 420), P(4, 290), P(-4, 290), P(-12, 420), P(-52, 420), P(-58, 250), P(-66, 200), P(-70, 300),
                   P(-84, 300), P(-98, 230), P(-92, 140), P(-70, 108), P(-14, 92), P(-24, 78), P(-36, 44), P(-30, 10)], fill=(*col, 0.08), stroke=col, a=a, lw=2)

    def flame(self, x, y, s=1.0, t=0.0, col=ORANGE, a=1.0):
        if a <= 0.003:
            return
        for k, (sc, cl) in enumerate(((1.0, col), (0.62, GOLD), (0.32, WHITE))):
            w = math.sin(t * 7 + k) * 4 * s
            pts = [(x, y), (x + 26 * sc * s, y - 24 * sc * s), (x + 16 * sc * s + w, y - 62 * sc * s), (x + w * 1.5, y - 92 * sc * s),
                   (x - 12 * sc * s + w, y - 58 * sc * s), (x - 26 * sc * s, y - 22 * sc * s)]
            self.path(pts, fill=(*cl, 0.85 if k else 0.55), a=a)

    def ripples(self, x, y, s=1.0, t=0.0, col=CYAN, a=1.0, n=4):
        c = self.c
        for k in range(n):
            ph = ((t * 0.35 + k / n) % 1.0)
            r = 20 + 110 * ph
            c.save()
            c.translate(x, y)
            c.scale(1.0, 0.32)
            c.arc(0, 0, r * s, 0, 2 * math.pi)
            c.restore()
            c.set_source_rgba(*col, a * (1 - ph) * 0.9)
            c.set_line_width(2.2)
            c.stroke()

    def shield(self, x, y, s=1.0, col=TEAL, a=1.0, fill=0.15):
        P = lambda u, v: (x + u * s, y + v * s)
        self.path([P(0, -70), P(55, -50), P(52, 10), P(30, 50), P(0, 72), P(-30, 50), P(-52, 10), P(-55, -50)], fill=(*col, fill), stroke=col, a=a, lw=3, smooth=False)

    def lens(self, x, y, s=1.0, col=CYAN, a=1.0):
        self.ring(x, y, 40 * s, col, a, 3.5)
        self.line([(x + 29 * s, y + 29 * s), (x + 70 * s, y + 70 * s)], col, a, 8 * s)

    def eye(self, x, y, s=1.0, col=CYAN, a=1.0, open_=1.0):
        P = lambda u, v: (x + u * s, y + v * s)
        h = 30 * open_
        self.path([P(-60, 0), P(0, -h), P(60, 0), P(0, h)], fill=(*col, 0.1), stroke=col, a=a, lw=2.5)
        if open_ > 0.2:
            self.dot(x, y, 13 * s * open_, col, a)

    def horse(self, x, y, s=1.0, col=WHITE, a=1.0, flip=False, gallop=0.0, fill=0.85):
        """A running horse in profile, facing right (or left if flip), about 220*s long; gallop moves the legs."""
        f = -1 if flip else 1
        P = lambda u, v: (x + f * u * s, y + v * s)
        g = math.sin(gallop) * 18
        body = [P(-80, -10), P(-60, -38), P(10, -40), P(55, -48), P(78, -92), P(100, -100), P(120, -84), P(108, -74), P(90, -70),
                P(80, -40), P(70, -6), P(40, 6), P(-40, 6), P(-75, 4)]
        self.path(body, fill=(*col, fill), stroke=col, a=a, lw=2)
        # tail
        self.line([P(-78, -24), P(-108, -14 + g * 0.3), P(-120, 14)], col, a, 6, glow=False)
        # legs
        for (hx, hy), ph in (((-58, 2), 0), ((-40, 4), 1.4), ((40, 2), 2.6), ((58, 0), 4.0)):
            sw = math.sin(gallop + ph) * 22
            self.line([P(hx, hy), P(hx + sw * 0.5, hy + 30), P(hx + sw, hy + 58)], col, a, 7, glow=False)

    def charioteer(self, x, y, s=1.0, col=GOLD, a=1.0, slump=0.0):
        """A small chariot with its driver, reins forward; slump 0-1 slumps the driver over."""
        P = lambda u, v: (x + u * s, y + v * s)
        self.ring(x, y + 2 * s, 28 * s, col, a, 3)
        self.line([P(-10, 2), P(10, 2)], col, a, 3, glow=False)
        self.path([P(-34, -20), P(30, -20), P(26, -48), P(-30, -48)], fill=(*col, 0.25), stroke=col, a=a, lw=2.5, smooth=False)
        lean = slump * 40
        hx, hy = P(-4 + lean * 0.9, -96 + lean * 1.1)
        self.dot(hx, hy, 11 * s, col, a, glow=False)
        self.line([P(-4, -48), P(-4 + lean * 0.5, -80 + lean * 0.6)], col, a, 7, glow=False)
        if slump < 0.5:
            self.line([P(-2, -74), P(60, -62), P(130, -40)], col, a * (1 - slump * 2), 1.8, glow=False)

    def funnel(self, x, y, w, h, labels, k=1.0, col=CYAN, a=1.0, hi=-1):
        """A funnel narrowing downwards with a band per label; k reveals bands from the top."""
        n = len(labels)
        for i, lab in enumerate(labels):
            kk = ap(k * n, i, 1.0)
            if kk <= 0:
                continue
            y0, y1 = y + h * i / n, y + h * (i + 1) / n - 6
            w0, w1 = w * (1 - 0.62 * i / n), w * (1 - 0.62 * (i + 1) / n)
            cc = RED if i == hi else col
            self.path([(x - w0 / 2, y0), (x + w0 / 2, y0), (x + w1 / 2, y1), (x - w1 / 2, y1)], fill=(*cc, 0.18), stroke=cc, a=a * kk, lw=2, smooth=False)
            self.text(lab, x, (y0 + y1) / 2 + 7, 19, WHITE, a * kk, bold=True, align='c')

    def plot(self, x, y, w, h, fn, prog=1.0, col=CYAN, a=1.0, lw=3, n=120, fill=False):
        """fn(u) -> 0..1 over u 0..1, drawn left to right up to prog, in a box with origin bottom-left."""
        if prog <= 0.001 or a <= 0.003:
            return
        pts = [(x + w * u, y + h - h * fn(u)) for u in np.linspace(0, prog, max(2, int(n * prog)))]
        if fill and len(pts) > 1:
            self.path(pts + [(pts[-1][0], y + h), (x, y + h)], fill=(*col, 0.15), a=a, smooth=False, closed=True)
        self.line(pts, col, a, lw)

    def axes(self, x, y, w, h, xl='', yl='', col=MUTED, a=1.0):
        self.line([(x, y), (x, y + h), (x + w, y + h)], col, a * 0.8, 1.6, glow=False)
        self.text(xl, x + w, y + h + 24, 15, col, a, align='r')
        self.text(yl, x, y - 10, 15, col, a)

    def gauge(self, x, y, r, k, col=CYAN, a=1.0, label='', value=''):
        self.ring(x, y, r, DIM, a, 8, 0.75, start=135)
        self.ring(x, y, r, col, a, 8, 0.75 * min(1, max(0, k)), start=135)
        self.text(value, x, y + 8, 22, WHITE, a, bold=True, align='c')
        self.text(label, x, y + r + 24, 15, MUTED, a, align='c')

    def node_net(self, cx, cy, rw, rh, n, t, k=1.0, col=CYAN, a=1.0, seed=3, links=2, hub=None):
        """A cloud of linked nodes with pulses running along the links."""
        rng = random.Random(seed)
        pts = [(cx + rng.uniform(-1, 1) * rw, cy + rng.uniform(-1, 1) * rh) for _ in range(n)]
        if hub:
            pts[0] = hub
        for i, p in enumerate(pts):
            dist = sorted(range(n), key=lambda j: (pts[j][0] - p[0]) ** 2 + (pts[j][1] - p[1]) ** 2)[1:links + 1]
            for j in dist:
                kk = ap(k * n, min(i, j), 3)
                self.line([p, pts[j]], col, a * 0.45 * kk, 1.2, glow=False)
                ph = (t * 0.6 + (i * 0.37 + j * 0.11)) % 1.0
                q = (lerp(p[0], pts[j][0], ph), lerp(p[1], pts[j][1], ph))
                self.dot(*q, 1.8, col, a * kk * 0.8, glow=False)
        for i, p in enumerate(pts):
            self.dot(*p, 3.2 if i else 5, col, a * ap(k * n, i, 2))
        return pts

    def tag(self, x, y, s, col=CYAN, a=1.0, size=16):
        """A small pill label."""
        w = self.text_w(s, size, True) + 22
        self.rrect(x - w / 2, y - size - 6, w, size + 14, (size + 14) / 2, fill=(*col, 0.16), stroke=col, a=a, lw=1.5)
        self.text(s, x, y + 1, size, WHITE, a, bold=True, align='c')
        return w

    def greek(self, x, y, word, latin, meaning, col=GOLD, a=1.0, size=46):
        """A Greek term: the word, its spelling in Latin letters, and what it means."""
        self.text(word, x, y, size, col, a, bold=True, align='c')
        self.text(latin, x, y + size * 0.72, 20, WHITE, a * 0.9, italic=True, align='c')
        self.text(meaning, x, y + size * 0.72 + 28, 17, MUTED, a, align='c')
