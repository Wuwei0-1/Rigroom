"""Make a render job from the scene saved in a studio checkout, for rendering from outside the app.

Usage:
  python3 tools/studio_job.py STUDIO_DIR still FRAME [--quality draft|good|final] [--fstop 2.8]
  python3 tools/studio_job.py STUDIO_DIR shot  FIRST LAST [--quality ...]
Writes STUDIO_DIR/jobs/<id>/job.json and prints the id. Commit and push it, then start the
renderer: gh api -X POST repos/OWNER/Rigroom/actions/workflows/render.yml/dispatches \\
           -f ref=main -f 'inputs[job]=<id>' -f 'inputs[store]=studio'
The renderer fills in the camera and frame height from the scene, exactly as the app would.
"""
import argparse
import datetime
import json
import pathlib
import random
import string

QUALITY = {'draft': (960, 48), 'good': (1280, 128), 'final': (1920, 400)}
ap = argparse.ArgumentParser()
ap.add_argument('studio'); ap.add_argument('kind', choices=['still', 'shot']); ap.add_argument('frames', type=int, nargs='+')
ap.add_argument('--quality', choices=QUALITY, default='good'); ap.add_argument('--fstop', type=float)
a = ap.parse_args()
studio = pathlib.Path(a.studio)
scene = json.loads((studio / 'scenes' / 'current.json').read_text())
scene.pop('meta', None)
frames = [a.frames[0], a.frames[0]] if a.kind == 'still' else [a.frames[0], a.frames[-1]]
width, samples = QUALITY[a.quality]
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
jid = f"{stamp}-{a.kind}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
job = {'v': 2, 'id': jid, 'kind': a.kind, 'frames': frames, 'fps': scene.get('fps', 24), 'width': width, 'samples': samples,
       'dof': {'fstop': a.fstop} if a.fstop else None, 'look': scene.get('look'), 'floor': {'color': '#6b6e76', 'roughness': 0.92},
       'source': 'scene', 'scene': scene}
(studio / 'jobs' / jid).mkdir(parents=True, exist_ok=True)
(studio / 'jobs' / jid / 'job.json').write_text(json.dumps(job))
print(jid)
