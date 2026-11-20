"""Write a Rigroom render job for a Gyges IV sequence, skipping the frames its story graphics will cover.

    python3 make_job.py SEQ PLAN.json STUDIO_DIR [OTHER_PLANS...]
"""
import json
import math
import os
import sys

sys.path.insert(0, '/home/claude/rigroom-remote/film')
import scenes4  # noqa: E402

seq, plan_path, studio = int(sys.argv[1]), sys.argv[2], sys.argv[3]
plan = json.load(open(plan_path))
scenes4.PH.update(json.load(open('/home/claude/gyges4/phrases.json')))
items = {i: (seq, t) for (i, who, t, secs) in plan['items']}
fps = plan['fps']
skip = []
for ww in scenes4.windows(items):
    skip.append([int(math.ceil(ww['t0'] * fps)), int(math.floor(ww['t1'] * fps)) - 1])
jid = 'gyges4-seq%d' % seq
job = {'v': 2, 'id': jid, 'kind': 'shot', 'source': 'blend', 'blend': 'film/gyges4/seq%d.blend' % seq, 'frames': plan['frames'], 'fps': fps,
       'width': 1280, 'samples': 8, 'step': 2, 'fade': 0.6, 'skip': skip, 'audio': {'film': 'gyges4', 'cues': plan['cues']}}
os.makedirs(os.path.join(studio, 'jobs', jid), exist_ok=True)
json.dump(job, open(os.path.join(studio, 'jobs', jid, 'job.json'), 'w'))
n = plan['frames'][1] - plan['frames'][0] + 1
sk = sum(b - a + 1 for a, b in skip)
print(jid, 'frames', n, 'skip', skip, '(%d frames, %.0f%%)' % (sk, 100.0 * sk / n), 'cues', len(plan['cues']))
