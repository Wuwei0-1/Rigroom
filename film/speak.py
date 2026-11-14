"""Rigroom voices: speaks a script's lines with Chatterbox (https://github.com/resemble-ai/chatterbox).

    python speak.py voices SCRIPT.json VOICES.json REF_DIR OUT_DIR
    python speak.py lines  SCRIPT.json VOICES.json PROMPT_DIR OUT_DIR [--part I/N] [--only A-B] [--speaker NAME]

Every character needs a short reference clip that sets what its voice sounds like.
  - If REF_DIR holds "<Character>.wav" (a recording you made, 8 to 20 seconds), that is the voice.
  - Otherwise a voice is designed: Chatterbox's built-in voice reads a sentence, the recording is
    shifted to the pitch set for the character in VOICES.json, and Chatterbox re-reads the sentence
    in that shifted voice, which gives a clean, natural clip of a voice that belongs to no real person.
Lines are spoken a sentence or two at a time (the model is steadier on short passages) and joined.
"""
import argparse
import json
import math
import os
import re
import sys

import numpy as np

SAMPLE = ("The harbor was quiet that morning, and the boats rocked gently against the pier. "
          "I remember thinking how strange it was, that a place so busy could suddenly feel so still.")
DEFAULT_VOICE = {'pitch': None, 'exaggeration': 0.5, 'cfg': 0.5, 'temperature': 0.8}


def load_model():
    import torch
    from chatterbox.tts import ChatterboxTTS
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    return ChatterboxTTS.from_pretrained(device='cpu')


def seed(n):
    import random
    import torch
    random.seed(n)
    np.random.seed(n % (2 ** 31))
    torch.manual_seed(n)


def median_pitch(wav, sr):
    import librosa
    f0, voiced, _ = librosa.pyin(wav.astype(np.float32), fmin=60, fmax=420, sr=sr, frame_length=2048)
    f0 = f0[voiced & ~np.isnan(f0)]
    return float(np.median(f0)) if len(f0) else 0.0


def tidy(wav, sr, top_db=38):
    """Cut the silence off both ends and bring the level to a steady loudness."""
    import librosa
    cut, _ = librosa.effects.trim(wav, top_db=top_db, frame_length=1024, hop_length=256)
    if len(cut) < sr * 0.15:
        cut = wav
    rms = float(np.sqrt(np.mean(cut ** 2)) + 1e-9)
    cut = cut * (10 ** (-23 / 20) / rms)
    peak = float(np.max(np.abs(cut)) + 1e-9)
    return (cut * min(1.0, 0.97 / peak)).astype(np.float32)


def write(path, wav, sr):
    import soundfile as sf
    sf.write(path, wav, sr, subtype='PCM_16')


def speak(model, text, voice, seed_n):
    seed(seed_n)
    wav = model.generate(text, exaggeration=float(voice.get('exaggeration', 0.5)), cfg_weight=float(voice.get('cfg', 0.5)),
                         temperature=float(voice.get('temperature', 0.8)))
    return wav.squeeze(0).numpy().astype(np.float32)


_asr = None


def heard(wav, sr, text):
    """How much of the text a speech recogniser hears in the take (0 to 1). 1.0 when no recogniser is installed."""
    global _asr
    try:
        if _asr is None:
            from faster_whisper import WhisperModel
            _asr = WhisperModel('base.en', device='cpu', compute_type='int8')
        import difflib
        import librosa
        audio = librosa.resample(wav, orig_sr=sr, target_sr=16000)
        segments, _ = _asr.transcribe(audio, language='en', beam_size=3)
        norm = lambda t: re.sub(r"[^a-z0-9' ]+", ' ', t.lower()).split()
        return difflib.SequenceMatcher(None, norm(text), norm(' '.join(seg.text for seg in segments))).ratio()
    except ImportError:
        return 1.0
    except Exception as err:
        print('listening check skipped:', err, flush=True)
        return 1.0


def passages(text, limit=260):
    """Split a line into sentences and pack them into passages short enough to speak in one go."""
    parts = [p.strip() for p in re.split(r'(?<=[.!?;:])\s+', text) if p.strip()]
    out = []
    for p in parts:
        while len(p) > limit:                       # a very long sentence: break at a comma
            cut = p.rfind(', ', 0, limit)
            cut = cut + 1 if cut > 60 else limit
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if out and len(out[-1]) + len(p) + 1 <= limit:
            out[-1] += ' ' + p
        else:
            out.append(p)
    return out


def make_voices(args):
    import librosa
    import soundfile as sf
    script = json.load(open(args.script, encoding='utf-8'))
    voices = json.load(open(args.voices, encoding='utf-8'))
    os.makedirs(args.out, exist_ok=True)
    model = load_model()
    sr = model.sr
    base = None
    report = {}
    for c in script['cast']:
        name = c['name']
        v = {**DEFAULT_VOICE, **voices.get(name, {})}
        ref = os.path.join(args.ref, name + '.wav')
        dst = os.path.join(args.out, name + '.wav')
        if os.path.exists(ref):
            wav, _ = librosa.load(ref, sr=sr, mono=True)
            write(dst, tidy(wav[:sr * 20], sr), sr)
            report[name] = {'source': 'kept from the studio', 'pitch': round(median_pitch(wav[:sr * 12], sr), 1)}
            continue
        if base is None:
            base = tidy(speak(model, SAMPLE, DEFAULT_VOICE, 7), sr)
            base_f0 = median_pitch(base, sr)
            builtin = model.conds
            write(os.path.join(args.out, '_builtin.wav'), base, sr)
            report['_builtin'] = {'pitch': round(base_f0, 1)}
        target = v.get('pitch')
        if not target or not base_f0:
            write(dst, base, sr)
            report[name] = {'source': 'built-in voice', 'pitch': round(base_f0, 1)}
            continue
        steps = 12 * math.log2(float(target) / base_f0)
        shifted = librosa.effects.pitch_shift(base, sr=sr, n_steps=steps)
        rough = os.path.join(args.out, '_' + name + '_shifted.wav')
        write(rough, shifted.astype(np.float32), sr)
        # the model re-reads the sentence in the shifted voice: same timbre, none of the shifting artefacts
        model.prepare_conditionals(rough, exaggeration=float(v['exaggeration']))
        clean = tidy(speak(model, SAMPLE, v, 11), sr)
        model.conds = builtin
        os.remove(rough)
        write(dst, clean, sr)
        report[name] = {'source': 'designed', 'target': target, 'shift_semitones': round(steps, 2), 'pitch': round(median_pitch(clean, sr), 1)}
        print(name, report[name], flush=True)
    json.dump(report, open(os.path.join(args.out, 'voices_report.json'), 'w'), indent=1)
    print(json.dumps(report), flush=True)


def speak_lines(args):
    script = json.load(open(args.script, encoding='utf-8'))
    voices = json.load(open(args.voices, encoding='utf-8'))
    os.makedirs(args.out, exist_ok=True)
    lines = script['lines']
    if args.only:
        a, b = (int(x) for x in args.only.split('-'))
        lines = [l for l in lines if a <= l['n'] <= b]
    if args.speaker:
        lines = [l for l in lines if l['speaker'].lower() == args.speaker.lower()]
    i, n = (int(x) for x in args.part.split('/'))
    # spread the work by length, so every machine speaks about the same amount
    order = sorted(lines, key=lambda l: -len(l['say']))
    mine = sorted(order[i - 1::n], key=lambda l: (l['speaker'], l['n']))
    if not mine:
        json.dump([], open(os.path.join(args.out, 'part.json'), 'w'))
        return
    model = load_model()
    sr = model.sr
    gap = np.zeros(int(sr * 0.26), dtype=np.float32)
    done, current = [], None
    for l in mine:
        v = {**DEFAULT_VOICE, **voices.get(l['speaker'], {})}
        if current != l['speaker']:
            model.prepare_conditionals(os.path.join(args.prompts, l['speaker'] + '.wav'), exaggeration=float(v['exaggeration']))
            current = l['speaker']
        pieces, worst = [], 1.0
        for k, text in enumerate(passages(l['say'])):
            words = max(1, len(text.split()))
            best = None
            for attempt in range(4):               # a take with wrong words, or far too long or short, is a slip: try again
                wav = tidy(speak(model, text, v, 1000 * l['n'] + 10 * k + attempt), sr)
                pace = len(wav) / sr / words
                match = heard(wav, sr, text)
                score = (1 - match) * 4 + abs(math.log(max(pace, 1e-3) / 0.38))
                if best is None or score < best[0]:
                    best = (score, wav, pace, match)
                if match >= 0.9 and 0.2 <= pace <= 0.75:
                    break
            pieces.append(best[1])
            worst = min(worst, best[3])
            print('line %d.%d %s: %.1f s, %.2f s a word, heard %.0f%%, takes %d' % (l['n'], k, l['speaker'], len(best[1]) / sr, best[2], best[3] * 100, attempt + 1), flush=True)
        wav = np.concatenate([x for p in pieces for x in (p, gap)][:-1])
        write(os.path.join(args.out, '%03d.wav' % l['n']), wav, sr)
        done.append({'n': l['n'], 'speaker': l['speaker'], 'seconds': round(len(wav) / sr, 3), 'passages': len(pieces), 'heard': round(worst, 2)})
    json.dump(done, open(os.path.join(args.out, 'part.json'), 'w'))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('voices')
    a.add_argument('script'); a.add_argument('voices'); a.add_argument('ref'); a.add_argument('out')
    b = sub.add_parser('lines')
    b.add_argument('script'); b.add_argument('voices'); b.add_argument('prompts'); b.add_argument('out')
    b.add_argument('--part', default='1/1'); b.add_argument('--only', default=''); b.add_argument('--speaker', default='')
    args = ap.parse_args()
    make_voices(args) if args.cmd == 'voices' else speak_lines(args)


if __name__ == '__main__':
    main()
