"""Turn a screenplay PDF (Ring of Gyges III layout) into a list of elements.

    python3 parse_script.py SCRIPT.pdf OUT.json

Elements, in order: {"kind": "sequence", "text"}, {"kind": "slug", "text"}, {"kind": "transition", "text"},
{"kind": "super", "text"}, {"kind": "direction", "text"}, {"kind": "line", "who", "note", "text"}.
Paragraphs are told apart by the vertical gap between lines; a paragraph straight after a character cue is
that character's dialogue, the next paragraph is a stage direction.
"""
import json, re, sys
import pdfplumber

CAST = ('SOCRATES', 'JULIAN', 'ARIA', 'CLEON')


def lines_of(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages):
            for l in page.extract_text_lines(return_chars=True):
                c = l['chars'][0]
                size = round(c['size'], 1)
                if size < 7:            # running header and page numbers
                    continue
                out.append({'p': pno, 'top': l['top'], 'bottom': l['bottom'], 'text': l['text'].strip(), 'size': size, 'bold': 'Semibold' in c['fontname'] or 'Bold' in c['fontname']})
    return out


def paragraphs(ls):
    paras, cur, last = [], None, None
    for l in ls:
        gap = None if last is None or l['p'] != last['p'] else l['top'] - last['bottom']
        new = cur is None or l['size'] != cur['size'] or l['bold'] != cur['bold'] or (gap is not None and gap > 6) or (gap is None and last is not None and not cur['open'])
        if l['p'] != (last or {}).get('p') and cur is not None:
            # a page break: carry on only if the paragraph had not ended (no closing punctuation)
            new = cur['text'].rstrip()[-1:] in '.?!:)"\'”' or l['bold'] != cur['bold']
        if new:
            cur = {'size': l['size'], 'bold': l['bold'], 'text': l['text'], 'open': True}
            paras.append(cur)
        else:
            sep = '' if cur['text'].endswith('-') and not cur['text'].endswith(' -') else ' '
            cur['text'] = (cur['text'] + sep + l['text']).strip()
        last = l
    return paras


def parse(path):
    paras = paragraphs(lines_of(path))
    els, expect = [], None
    title_done = False
    for p in paras:
        t = re.sub(r'\s+', ' ', p['text']).strip()
        t = t.replace('— ', '—').replace(' —', '—')
        if p['size'] >= 20:
            continue                                    # the title
        if p['size'] < 11:
            continue                                    # date and author line
        if p['size'] >= 14:
            els.append({'kind': 'sequence', 'text': t}); expect = None; continue
        if els and els[-1]['kind'] == 'line' and els[-1].get('open'):
            els[-1]['note'] = (els[-1]['note'] + ' ' + t).strip()
            if els[-1]['note'].endswith(')'):
                els[-1]['note'] = els[-1]['note'][1:-1].strip() if els[-1]['note'].startswith('(') else els[-1]['note'].rstrip(')')
                del els[-1]['open']
            continue
        if p['bold']:
            m = re.match(r'^(%s)\b\s*(.*)$' % '|'.join(CAST), t)
            if m:
                note = m.group(2).strip()
                note = re.sub(r"\(CONT'D\)", '', note).strip()
                e = {'kind': 'line', 'who': m.group(1).title(), 'note': note, 'text': ''}
                if note.startswith('(') and not note.endswith(')'):
                    e['open'] = True
                else:
                    e['note'] = note[1:-1].strip() if note.startswith('(') and note.endswith(')') else note
                els.append(e); expect = 'dialogue'; continue
            if t.startswith('SUPER:'):
                els.append({'kind': 'super', 'text': t[6:].strip()}); expect = None; continue
            if t.startswith(('INT.', 'EXT.')):
                els.append({'kind': 'slug', 'text': t}); expect = None; continue
            els.append({'kind': 'transition', 'text': t}); expect = None; continue
        if expect == 'dialogue':
            els[-1]['text'] = t; expect = None; continue
        els.append({'kind': 'direction', 'text': t})
    return els


if __name__ == '__main__':
    els = parse(sys.argv[1])
    json.dump(els, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
    for e in els:
        print(e['kind'][:4], e.get('who', ''), ('(' + e['note'] + ')') if e.get('note') else '', '|', e['text'][:110])
