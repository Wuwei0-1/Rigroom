"""Cut explainer graphics into a rendered sequence, and write subtitles for a whole film.

    python compose.py cut SHOT.mp4 GRAPHICS_DIR SEQ OUT.mp4
        Lays each graphic of sequence SEQ (from GRAPHICS_DIR/graphics.json) over the shot at its time, dissolving
        in and out over a third of a second; graphics that follow one another at once dissolve straight from one
        to the next. The shot's sound runs on underneath.

    python compose.py srt SCRIPT.json PHRASES.json OUT.srt --plans P1.json,P2.json,... --offsets O1,O2,...
        Subtitles for every spoken line and narration, one or two lines at a time, timed to the phrases.
        Each plan's times are shifted by its offset (where that sequence starts in the film).
"""
import json
import os
import re
import subprocess
import sys

FADE = 0.35
JOIN = 1.5        # graphics closer together than this dissolve straight into each other
NAMES = {'CLEON', 'ARIA', 'JULIAN', 'SOCRATES'}


def cut(shot, gdir, seq, out):
    wins = [w for w in json.load(open(os.path.join(gdir, 'graphics.json'))) if w['seq'] == int(seq)]
    args = ['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', shot]
    for w in wins:
        args += ['-i', os.path.join(gdir, w['id'] + '.mp4')]
    chains, last = [], '0:v'
    wins.sort(key=lambda w: w['t0'])
    for k, w in enumerate(wins):
        d = w['t1'] - w['t0']
        nxt = wins[k + 1] if k + 1 < len(wins) else None
        f = '[%d:v]format=yuva420p,fade=t=in:st=0:d=%.3f:alpha=1' % (k + 1, FADE)
        if nxt is not None and nxt['t0'] - w['t1'] < JOIN:
            # the next graphic follows at once: hold this one's last frame under it, so one dissolves into the other
            end = nxt['t0'] + FADE + 0.05
            f += ',tpad=stop_mode=clone:stop_duration=%.3f' % (end - w['t1'] + 0.5)
        else:
            end = w['t1']
            f += ',fade=t=out:st=%.3f:d=%.3f:alpha=1' % (d - FADE, FADE)
        chains.append(f + ',setpts=PTS-STARTPTS+%.3f/TB[g%d]' % (w['t0'], k))
        chains.append('[%s][g%d]overlay=eof_action=pass:enable=\'between(t,%.3f,%.3f)\'[v%d]' % (last, k, w['t0'], end, k))
        last = 'v%d' % k
    if wins:
        args += ['-filter_complex', ';'.join(chains), '-map', '[%s]' % last]
    else:
        args += ['-map', '0:v']
    args += ['-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'copy', out]
    subprocess.run(args, check=True)
    print(out, len(wins), 'graphics')


def stamp(t):
    ms = int(round(t * 1000))
    return '%02d:%02d:%02d,%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def chunks(phrases, max_chars=84, max_secs=6.5):
    """Group phrases into subtitles of up to two lines, breaking at sentence ends where it can."""
    out, cur = [], []
    for p in phrases:
        text = ' '.join(x[0] for x in cur + [p])
        if cur and (len(text) > max_chars or p[2] - cur[0][1] > max_secs):
            out.append(cur)
            cur = []
        cur.append(p)
        if p[0].endswith(('.', '?', '!')) and len(' '.join(x[0] for x in cur)) > 40:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def two_lines(text, width=46):
    if len(text) <= width:
        return text
    best = None
    for k, ch in enumerate(text):
        if ch == ' ':
            score = abs(k - len(text) / 2)
            if best is None or score < best[0]:
                best = (score, k)
    return text[:best[1]] + '\n' + text[best[1] + 1:]


def srt(script, phrases, out, plans, offsets):
    els = json.load(open(script))
    ph = json.load(open(phrases))
    cues = []
    for plan, off in zip(plans, offsets):
        for (i, who, t, secs) in json.load(open(plan))['items']:
            key = 'e%03d' % i
            if key not in ph or els[i]['kind'] == 'sequence':
                continue
            for grp in chunks(ph[key]['phrases']):
                a = off + t + grp[0][1]
                b = off + t + grp[-1][2] + 0.25
                text = re.sub(r'\b([A-Z]{3,})\b', lambda m: m.group(1).title() if m.group(1) in NAMES else m.group(1), ' '.join(x[0] for x in grp))
                cues.append([a, b, text, who])
    cues.sort()
    for k in range(len(cues) - 1):
        cues[k][1] = min(cues[k][1], cues[k + 1][0] - 0.04)
        cues[k][1] = max(cues[k][1], cues[k][0] + 0.8)
    with open(out, 'w') as fh:
        for n, (a, b, text, who) in enumerate(cues, 1):
            body = two_lines(text)
            if who == 'Narrator':
                body = '\n'.join('<i>%s</i>' % ln for ln in body.split('\n'))
            fh.write('%d\n%s --> %s\n%s\n\n' % (n, stamp(a), stamp(b), body))
    print(out, len(cues), 'subtitles')


if __name__ == '__main__':
    if sys.argv[1] == 'cut':
        cut(*sys.argv[2:6])
    else:
        a = sys.argv
        srt(a[2], a[3], a[4], a[a.index('--plans') + 1].split(','), [float(x) for x in a[a.index('--offsets') + 1].split(',')])
