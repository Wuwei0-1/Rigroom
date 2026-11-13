"""Turn a play script (text laid out like a PDF: numbered "N. SPEAKER: line" entries, indented stage
directions, ACT and SCENE headings) into the lines file the voice and film steps read.

    python script_to_lines.py SCRIPT.txt OUT.json

Each line keeps the text as written (for subtitles), the stage direction in its brackets (for acting),
and "say": what the voice should speak, with directions removed and abbreviations spelled out.
"""
import json
import re
import sys

LETTERS = {'VPN', 'FBI', 'ISP', 'IP', 'DM', 'DMs', 'ID', 'SIM'}


def say(text):
    t = re.sub(r'18 U\.S\.C\. Section (\d\d)(\d\d)\((\w)\)', lambda m: 'Title 18, section %s %s %s' % (m.group(1), m.group(2), m.group(3).upper()), text)
    t = re.sub(r'\([^)]*\)', ' ', t)                         # stage directions
    t = t.replace('“', '').replace('”', '').replace('"', '').replace('’', "'").replace('—', ', ')
    t = re.sub(r'\[([A-Z ]+)\]', lambda m: m.group(1).capitalize() + '.', t)   # [THE FREEZE] is read as a heading
    def spell(m):
        w = m.group(0)
        if w in ('SIM', 'ID'):
            return w
        if w == 'DMs':
            return 'D Ms'
        return ' '.join(w) if w in LETTERS else w
    t = re.sub(r"\b[A-Z]{2,4}s?\b", spell, t)
    t = t.replace('Wi-Fi', 'wifi')
    return re.sub(r'\s+', ' ', t).strip()


def parse(src):
    lines, stage, act, scene, cast, title = [], [], None, None, [], []
    cur, pending = None, []
    blocks = re.split(r'\n\s*\n', src.replace('\r', '').replace('\f', '\n\n'))
    for block in blocks:
        raw = block.strip('\n')
        if not raw.strip():
            continue
        rows = [r.strip() for r in raw.split('\n') if r.strip()]
        head = re.match(r'^(ACT [IVX]+|SCENE \d+): (.+)$', rows[0])
        if head and len(rows) > 1:                      # a heading with its stage direction right under it
            pending.append(' '.join(rows[1:]))
        flat = re.sub(r'\s+', ' ', raw).strip()
        m = re.match(r'^(\d+)\. ([A-Z][A-Z ]+): (.*)$', flat)
        if head:
            if head.group(1).startswith('ACT'):
                act, scene = head.group(1) + ': ' + head.group(2), None
            else:
                scene = head.group(1) + ': ' + head.group(2)
        elif m:
            text = m.group(3)
            d = re.match(r'^\(([^)]*)\)\s*', text)
            cur = {'n': int(m.group(1)), 'act': act, 'scene': scene, 'speaker': m.group(2).title(), 'direction': d.group(1) if d else None, 'text': text, 'before': pending}
            pending = []
            lines.append(cur)
        elif cur and flat.startswith('['):            # an indented list that belongs to the line above
            cur['text'] += ' ' + flat
        elif flat == 'END OF PLAY':
            continue
        elif flat.startswith('CHARACTERS'):
            for row in raw.split('\n')[1:]:
                c = re.match(r'^\s*([A-Z][A-Z ]+) — (.+)$', row)
                if c:
                    cast.append({'name': c.group(1).title(), 'about': c.group(2).strip()})
        elif act is None:
            title.append(flat)
        else:
            pending.append(flat)                        # a stage direction between lines
    for ln in lines:
        ln['say'] = say(ln['text'])
    return {'title': ' '.join(title).replace(' A Play in Three Acts', ''), 'cast': cast, 'lines': lines, 'after': pending}


if __name__ == '__main__':
    out = parse(open(sys.argv[1], encoding='utf-8').read())
    json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    words = sum(len(l['say'].split()) for l in out['lines'])
    print('%s: %d lines, %d spoken words (about %.0f minutes), cast: %s' % (out['title'], len(out['lines']), words, words / 150, ', '.join(c['name'] for c in out['cast'])))
