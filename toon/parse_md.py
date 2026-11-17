"""Turn a screenplay written as Markdown (the Ring of Gyges IV doc, exported) into a list of elements.

    python3 parse_md.py SCRIPT.md OUT.json [--cont CONT.txt]

Elements, in order: {"kind": "sequence", "text"}, {"kind": "slug", "text"}, {"kind": "transition", "text"},
{"kind": "super", "text"}, {"kind": "insert", "title", "text"}, {"kind": "direction", "text"},
{"kind": "line", "who", "vo", "note", "text"}.

A character cue is a paragraph that is all bold capitals (**NAME**, **NAME (V.O.)**, **NAME (CONT'D)**), with an
optional (note) after it. The paragraph after a cue is the line. A paragraph after a line is a stage direction,
unless it is in the CONT list (a speech that runs to several paragraphs) or is a bare (note), which starts a
new line for the same speaker. Everything before the first "## Sequence" heading (the cast list) is skipped.
"""
import json
import re
import sys

TRANS = ('FADE IN:', 'DISSOLVE TO:', 'CUT TO:', 'BACK TO SCENE.', 'CUT TO BLACK.', 'FADE OUT.')


def paragraphs(md):
    return [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', md) if p.strip()]


def plain(t):
    return re.sub(r'\*+([^*]+)\*+', r'\1', t).strip()


def parse(md, cont=()):
    els, started, speaker, after_line = [], False, None, False
    for p in paragraphs(md):
        if p.startswith('## '):
            h = p[3:].strip()
            if h.startswith('Sequence'):
                started = True
                els.append({'kind': 'sequence', 'text': h})
            speaker, after_line = None, False
            continue
        if not started or p.startswith('# '):
            continue
        m = re.match(r"^\*\*([A-Z][A-Z .'()–-]+?)\*\*\s*(\((.*)\))?\s*$", p)
        if m:
            name = m.group(1).strip()
            if name.startswith(('INT.', 'EXT.')):
                els.append({'kind': 'slug', 'text': name})
                speaker, after_line = None, False
                continue
            vo = '(V.O.)' in name
            who = re.sub(r"\s*\((V\.O\.|CONT'D)\)", '', name).strip().title()
            speaker = {'who': who, 'vo': vo, 'note': (m.group(3) or '').strip()}
            after_line = False
            continue
        t = plain(p)
        if t in TRANS:
            els.append({'kind': 'transition', 'text': t})
            speaker, after_line = None, False
            continue
        if t.startswith('SUPER:'):
            els.append({'kind': 'super', 'text': t[6:].strip()})
            continue
        ins = re.match(r'^INSERT\s*[–-]\s*([^:]+):\s*(.*)$', t)
        if ins:
            els.append({'kind': 'insert', 'title': ins.group(1).strip(), 'text': ins.group(2).strip()})
            speaker, after_line = None, False
            continue
        if speaker and re.match(r'^\(.*\)$', t):
            speaker = dict(speaker, note=t[1:-1].strip())
            after_line = False
            continue
        if speaker and (not after_line or any(t.startswith(c) for c in cont)):
            els.append({'kind': 'line', 'who': speaker['who'], 'vo': speaker['vo'], 'note': speaker['note'], 'text': t})
            speaker = dict(speaker, note='')
            after_line = True
            continue
        els.append({'kind': 'direction', 'text': t})
        speaker, after_line = None, False
    return els


if __name__ == '__main__':
    cont = ()
    if '--cont' in sys.argv:
        cont = tuple(l.strip() for l in open(sys.argv[sys.argv.index('--cont') + 1]) if l.strip())
    els = parse(open(sys.argv[1]).read(), cont)
    json.dump(els, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
    for i, e in enumerate(els):
        print('%3d' % i, e['kind'][:5], e.get('who', ''), ('(' + e['note'] + ')') if e.get('note') else '', '|', (e.get('title', '') + ': ' if e.get('title') else '') + e['text'][:100])
