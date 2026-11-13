"""Collect spoken lines into the film's audio folder: one MP3 per line, and audio.json with each line's
length and loudness curve (one value per 1/24 s, 0 to 1), which drives the speakers' jaws.

    python finish_audio.py PARTS_DIR FILM_DIR
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

parts, film = sys.argv[1], sys.argv[2]
out = os.path.join(film, 'audio')
os.makedirs(out, exist_ok=True)
index_path = os.path.join(out, 'audio.json')
index = {l['n']: l for l in json.load(open(index_path))['lines']} if os.path.exists(index_path) else {}
for part in sorted(glob.glob(os.path.join(parts, '**', 'part.json'), recursive=True)):
    for l in json.load(open(part)):
        wav_path = os.path.join(os.path.dirname(part), '%03d.wav' % l['n'])
        wav, sr = sf.read(wav_path, dtype='float32')
        hop = sr // 24
        frames = [float(np.sqrt(np.mean(wav[i:i + hop] ** 2))) for i in range(0, len(wav), hop)]
        top = float(np.percentile(frames, 95)) or 1.0
        l['env'] = [round(min(1.0, f / top), 2) for f in frames]
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav_path, '-ac', '1', '-b:a', '96k', os.path.join(out, '%03d.mp3' % l['n'])], check=True)
        index[l['n']] = l
lines = [index[n] for n in sorted(index)]
json.dump({'fps': 24, 'lines': lines}, open(index_path, 'w'))
print('%d lines, %.1f minutes of speech; least well heard: %s' % (len(lines), sum(l['seconds'] for l in lines) / 60,
      ', '.join('%d (%.0f%%)' % (l['n'], l.get('heard', 1) * 100) for l in sorted(lines, key=lambda l: l.get('heard', 1))[:5])))
