"""Where each phrase of a spoken line falls in its audio: for subtitles, and for timing graphics to the words.

    python phrases.py SCRIPT.json VOICES_DIR OUT.json

VOICES_DIR holds eNNN.wav and index.json (as speak.py writes them). Each line's text is split at punctuation into
phrases; the speech is assumed to run at an even pace between pauses, and each phrase boundary is moved onto the
nearest pause the audio actually has. OUT.json maps eNNN to [[phrase, start, end], ...] in seconds from the clip's start,
and to its words with estimated times: {"phrases": [...], "words": [[word, start, end], ...]}.
"""
import json
import os
import re
import sys
import wave

import numpy as np

HOP = 0.01


def envelope(path):
    w = wave.open(path)
    sr = w.getframerate()
    y = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    hop = int(sr * HOP)
    n = len(y) // hop
    return np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1))


def pauses(e, min_len=0.11):
    """Silent stretches as (start, end) in seconds."""
    thr = max(np.percentile(e, 95) * 0.06, 1e-4)
    quiet = e < thr
    out, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - k) * HOP >= min_len:
                out.append((k * HOP, j * HOP))
            k = j
        else:
            k += 1
    return out


def split(text):
    """Phrases: break after . ? ! ; : , and dashes, keeping the punctuation with the phrase before."""
    parts = re.split(r'(?<=[.?!;:,—–])\s+|(?<=—)(?=\w)', text.strip())
    return [p.strip() for p in parts if p.strip()]


def align(text, wav):
    e = envelope(wav)
    total = len(e) * HOP
    ps = pauses(e)
    lead = ps[0][1] if ps and ps[0][0] <= 0.02 else 0.0
    tail = ps[-1][0] if ps and ps[-1][1] >= total - 0.02 else total
    inner = [p for p in ps if p[0] > lead + 0.05 and p[1] < tail - 0.05]
    phrases = split(text)
    weights = [max(1, len(p)) + 6 for p in phrases]          # a little time for each phrase's start and end
    speech = (tail - lead) - sum(b - a for a, b in inner)
    # time with pauses taken out -> real time
    def real(t_speech):
        t = lead + t_speech
        for a, b in inner:
            if t > a:
                t += b - a
        return t
    cum = np.cumsum([0] + weights) / sum(weights) * speech
    bounds = [real(c) for c in cum]
    # snap each inner boundary to the nearest pause, if one is near
    used = set()
    for k in range(1, len(bounds) - 1):
        best = None
        for idx, (a, b) in enumerate(inner):
            if idx in used:
                continue
            d = abs((a + b) / 2 - bounds[k])
            if d < 0.9 and (best is None or d < best[0]):
                best = (d, idx, a, b)
        if best:
            used.add(best[1])
            bounds[k] = (best[2] + best[3]) / 2
    for k in range(1, len(bounds)):
        bounds[k] = max(bounds[k], bounds[k - 1] + 0.2)
    out = []
    words = []
    for k, p in enumerate(phrases):
        a, b = bounds[k], bounds[k + 1]
        # trim the pause off the phrase's end
        for pa, pb in inner:
            if a < pa < b <= pb + 0.01:
                b = pa
        out.append([p, round(a, 3), round(b, 3)])
        ws = p.split()
        wl = [len(w) + 2 for w in ws]
        c = np.cumsum([0] + wl) / sum(wl) * (b - a) + a
        words += [[w, round(c[i], 3), round(c[i + 1], 3)] for i, w in enumerate(ws)]
    return {'phrases': out, 'words': words, 'secs': round(total, 3)}


if __name__ == '__main__':
    els = json.load(open(sys.argv[1]))
    vdir = sys.argv[2]
    index = json.load(open(os.path.join(vdir, 'index.json')))
    res = {}
    for key in sorted(index):
        i = int(key[1:])
        res[key] = align(els[i]['text'], os.path.join(vdir, key + '.wav'))
    json.dump(res, open(sys.argv[3], 'w'), indent=0)
    print(len(res), 'lines aligned')
