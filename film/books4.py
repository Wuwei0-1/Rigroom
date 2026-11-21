"""Split The Ring of Gyges IV into the ten books of the Republic, and make a YouTube Short for each.

    python books4.py sections   SEQ_DIR PLAN_DIR SCRIPT.json PHRASES.json OUT_DIR
        Cuts the sequence videos (SEQ_DIR/seqN.mp4, graphics already cut in) at the line where each book begins and
        writes OUT_DIR/bookNN_raw.mp4 (no subtitles) and OUT_DIR/bookNN.srt (times from the section's start).
    python books4.py film       OUT_DIR TITLE_SUB
        Burns subtitles into each section, then writes OUT_DIR/film.mp4 (title card, then a card and the section for
        each book, end card), OUT_DIR/film.srt and OUT_DIR/chapters.txt (YouTube chapter times), and
        OUT_DIR/book-NN.mp4, one video per book (title card, the book, end card). All at -16 LUFS.
    python books4.py shorts     OUT_DIR PLAN_DIR PHRASES.json SCRIPT.json
        One 1080x1920 Short per book from the lines in SHORTS: the scene in the middle, the book's name above and
        large captions below, at most 60 seconds.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose  # noqa: E402

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
# where each book begins (the first element of it), and its card
BOOKS = [(0, 'What Is Justice?'), (98, 'The Ring of Gyges'), (137, 'The Noble Lie'), (142, 'The City and the Soul'),
         (158, 'The Three Waves'), (171, 'The Ship, the Sun and the Line'), (192, 'The Cave'), (223, 'The Decline of Cities'),
         (230, 'The Tyrant and the Beast Within'), (240, 'The Myth of Er')]
# each book's Short: its first and last element
SHORTS = [(69, 75), (106, 111), (137, 141), (148, 152), (165, 169), (172, 174), (196, 200), (226, 228), (232, 234), (240, 245)]
END = 'end:wuwei0-1.github.io/Wuwei01'
FILM = os.path.dirname(os.path.abspath(__file__))
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000']


def run(args):
    subprocess.run(args, check=True)


def dur(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                capture_output=True, text=True, check=True).stdout)


def plans(plan_dir):
    """Every kept element's (seq, start) and the element order, from the seven plans."""
    at, order, seqlen = {}, [], {}
    for n in range(1, 8):
        p = json.load(open(os.path.join(plan_dir, 'seq%d_plan.json' % n)))
        seqlen[n] = p['seconds']
        for (i, who, t, secs) in p['items']:
            at[i] = (n, t, secs, who)
            order.append(i)
    return at, sorted(order), seqlen


def first_kept(at, i):
    while i not in at:
        i += 1
    return i


def srt_for(plan_dir, phrases, script, seq, t0, t1, out):
    """Subtitles for seq's lines that start in [t0, t1), timed from t0."""
    els = json.load(open(script))
    ph = json.load(open(phrases))
    p = json.load(open(os.path.join(plan_dir, 'seq%d_plan.json' % seq)))
    cues = []
    for (i, who, t, secs) in p['items']:
        key = 'e%03d' % i
        if key not in ph or not (t0 - 0.01 <= t < t1):
            continue
        for grp in compose.chunks(ph[key]['phrases']):
            a = t - t0 + grp[0][1]
            b = t - t0 + grp[-1][2] + 0.25
            text = re.sub(r'\b([A-Z]{3,})\b', lambda m: m.group(1).title() if m.group(1) in compose.NAMES else m.group(1), ' '.join(x[0] for x in grp))
            cues.append([a, b, text, who])
    cues.sort()
    for k in range(len(cues) - 1):
        cues[k][1] = min(cues[k][1], cues[k + 1][0] - 0.04)
        cues[k][1] = max(cues[k][1], cues[k][0] + 0.8)
    return cues


def write_srt(cues, out, offset=0.0, italic=True):
    with open(out, 'w') as fh:
        for n, (a, b, text, who) in enumerate(cues, 1):
            body = compose.two_lines(text)
            if who == 'Narrator' and italic:
                body = '\n'.join('<i>%s</i>' % ln for ln in body.split('\n'))
            fh.write('%d\n%s --> %s\n%s\n\n' % (n, compose.stamp(a + offset), compose.stamp(b + offset), body))


def sections(seq_dir, plan_dir, script, phrases, out):
    os.makedirs(out, exist_ok=True)
    at, order, seqlen = plans(plan_dir)
    starts = []
    for k, (i, name) in enumerate(BOOKS):
        j = first_kept(at, i)
        seq, t = at[j][0], (0.0 if k == 0 else at[j][1] - 0.5)
        starts.append((seq, max(0.0, t)))
    info = []
    for k in range(10):
        s0, t0 = starts[k]
        s1, t1 = starts[k + 1] if k < 9 else (7, seqlen[7])
        parts, cues, off = [], [], 0.0
        for seq in range(s0, s1 + 1):
            a = t0 if seq == s0 else 0.0
            b = t1 if seq == s1 else seqlen[seq]
            if seq == s1 and k < 9 and b <= 0.01:
                continue
            part = os.path.join(out, 'b%02d_s%d.mp4' % (k + 1, seq))
            run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', '%.3f' % a, '-to', '%.3f' % b, '-i', os.path.join(seq_dir, 'seq%d.mp4' % seq)] + ENC + [part])
            parts.append(part)
            for c in srt_for(plan_dir, phrases, script, seq, a, b, None):
                cues.append([c[0] + off, c[1] + off, c[2], c[3]])
            off += dur(part)
        lst = os.path.join(out, 'b%02d.txt' % (k + 1))
        open(lst, 'w').write(''.join("file '%s'\n" % os.path.basename(p) for p in parts))
        raw = os.path.join(out, 'book%02d_raw.mp4' % (k + 1))
        # join, with a half-second fade at each end of the book
        tmp = raw + '.join.mp4'
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', tmp])
        D = dur(tmp)
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', tmp, '-vf', 'fade=t=in:st=0:d=0.5,fade=t=out:st=%.3f:d=0.5' % (D - 0.5),
             '-af', 'afade=t=in:st=0:d=0.3,afade=t=out:st=%.3f:d=0.5' % (D - 0.5)] + ENC + [raw])
        os.remove(tmp)
        for p in parts:
            os.remove(p)
        write_srt(cues, os.path.join(out, 'book%02d.srt' % (k + 1)))
        json.dump(cues, open(os.path.join(out, 'book%02d_cues.json' % (k + 1)), 'w'))
        info.append({'book': k + 1, 'name': BOOKS[k][1], 'secs': round(dur(raw), 3), 'from': [s0, round(t0, 3)], 'to': [s1, round(t1, 3)]})
        print('Book', ROMAN[k], BOOKS[k][1], round(dur(raw), 1), 's')
    json.dump(info, open(os.path.join(out, 'books.json'), 'w'), indent=1)


SUBS = "subtitles=%s:force_style='FontName=Inter,FontSize=12,BorderStyle=3,Outline=1,Shadow=0,BackColour=&H90000000,MarginV=16'"


def stamp_yt(t):
    t = int(t)
    return '%d:%02d:%02d' % (t // 3600, t // 60 % 60, t % 60) if t >= 3600 else '%d:%02d' % (t // 60, t % 60)


def film(out, sub):
    info = json.load(open(os.path.join(out, 'books.json')))
    subbed = []
    for b in info:
        n = b['book']
        s = os.path.join(out, 'book%02d_sub.mp4' % n)
        if not os.path.exists(s):
            run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', os.path.join(out, 'book%02d_raw.mp4' % n), '-vf', SUBS % os.path.join(out, 'book%02d.srt' % n)] + ENC + [s])
        subbed.append(s)
    # the whole film: title card, then each book's card and section
    items, t, chapters, allcues = ['card:The Ring of Gyges IV|%s' % sub], 5.0, ['0:00 The Ring of Gyges IV: %s' % sub], []
    for b, s in zip(info, subbed):
        n = b['book']
        chapters.append('%s Book %s: %s' % (stamp_yt(t), ROMAN[n - 1], b['name']))
        items += ['card:Book %s|%s' % (ROMAN[n - 1], b['name']), s]
        t += 5.0
        for c in json.load(open(os.path.join(out, 'book%02d_cues.json' % n))):
            allcues.append([c[0] + t, c[1] + t, c[2], c[3]])
        t += dur(s)
    items.append(END)
    joined = os.path.join(out, 'film_joined.mp4')
    run(['python3', os.path.join(FILM, 'assemble.py'), joined] + items)
    loud(joined, os.path.join(out, 'film.mp4'))
    write_srt(allcues, os.path.join(out, 'film.srt'))
    open(os.path.join(out, 'chapters.txt'), 'w').write('\n'.join(chapters) + '\n')
    # one video per book
    for b, s in zip(info, subbed):
        n = b['book']
        j = os.path.join(out, 'book%02d_joined.mp4' % n)
        run(['python3', os.path.join(FILM, 'assemble.py'), j, 'card:The Ring of Gyges IV|Book %s: %s' % (ROMAN[n - 1], b['name']), s, END])
        loud(j, os.path.join(out, 'book-%02d.mp4' % n))
        write_srt(json.load(open(os.path.join(out, 'book%02d_cues.json' % n))), os.path.join(out, 'book-%02d.srt' % n), offset=5.0)
        os.remove(j)
    print(open(os.path.join(out, 'chapters.txt')).read())


def loud(src, dst):
    run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', src, '-c:v', 'copy', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '160k',
         '-ar', '48000', '-movflags', '+faststart', dst])


def shorts(out, plan_dir, phrases, script):
    at, order, seqlen = plans(plan_dir)
    info = json.load(open(os.path.join(out, 'books.json')))
    for k, (e0, e1) in enumerate(SHORTS):
        b = info[k]
        n = k + 1
        e0, e1 = first_kept(at, e0), e1
        while e1 not in at:
            e1 -= 1
        seq = at[e0][0]
        # times in the book's section: the book's own start in that sequence
        base = b['from'][1] if b['from'][0] == seq else 0.0
        pre = 0.0
        if b['from'][0] != seq:      # the book began in an earlier sequence: add that part's length
            p_ = json.load(open(os.path.join(plan_dir, 'seq%d_plan.json' % b['from'][0])))
            pre = p_['seconds'] - b['from'][1]
        a = pre + at[e0][1] - base - 0.3
        z = pre + at[e1][1] + at[e1][2] - base + 0.6
        z = min(z, a + 60.0)
        cues = [c for c in json.load(open(os.path.join(out, 'book%02d_cues.json' % n))) if c[0] >= a - 0.05 and c[0] < z]
        cues = [[c[0] - a, min(c[1], z) - a, c[2], c[3]] for c in cues]
        srt = os.path.join(out, 'short%02d.srt' % n)
        write_srt(cues, srt, italic=False)
        title = 'Book %s' % ROMAN[k]
        name = b['name'].replace("'", "’").replace(':', '\\:')
        vf = ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.25[bg];"
              "[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2-80[v];"
              "[v]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf:text='THE RING OF GYGES IV':fontcolor=white:fontsize=44:x=(w-tw)/2:y=250,"
              "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf:text='%s':fontcolor=0xF2C04E:fontsize=96:x=(w-tw)/2:y=320,"
              "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf:text='%s':fontcolor=0xF2C04E:fontsize=54:x=(w-tw)/2:y=440,"
              "subtitles=%s:force_style='FontName=Inter,FontSize=10,Bold=1,BorderStyle=3,Outline=2,Shadow=0,BackColour=&HA0000000,Alignment=2,MarginV=70,MarginL=24,MarginR=24'"
              "[o]") % (title, name, srt)
        dst = os.path.join(out, 'short-%02d.mp4' % n)
        run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', '%.3f' % max(0.0, a), '-t', '%.3f' % (z - a), '-i', os.path.join(out, 'book%02d_raw.mp4' % n),
             '-filter_complex', vf, '-map', '[o]', '-map', '0:a', '-af', 'afade=t=out:st=%.3f:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11' % (z - a - 0.6),
             '-r', '30'] + ENC + ['-movflags', '+faststart', dst])
        print('Short', n, title, round(z - a, 1), 's')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'sections':
        sections(*sys.argv[2:7])
    elif cmd == 'film':
        film(sys.argv[2], sys.argv[3])
    elif cmd == 'shorts':
        shorts(*sys.argv[2:6])
