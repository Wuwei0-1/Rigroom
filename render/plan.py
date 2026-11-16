"""Splits a render job into frame chunks for parallel runners. Prints a JSON list.

Chunks share out the frames that are actually rendered: frames a job skips (covered by another picture in the
edit) and frames held on twos cost nothing, so a chunk spans more of the timeline where there are many of them."""
import json
import math
import sys

MAX_RUNNERS = 18      # parallel machines per job: GitHub runs 20 at once for free, 2 stay free to plan and publish other jobs
MIN_PER_RUNNER = 3    # each runner spends about a minute installing Blender, so give it real work

with open(sys.argv[1]) as fh:
    job = json.load(fh)
f0, f1 = (int(v) for v in job['frames'])
step = max(1, int(job.get('step', 1)))
skip = [(int(a), int(b)) for a, b in job.get('skip', [])]
work = [f for f in range(f0, f1 + 1) if (f - f0) % step == 0 and not any(a <= f <= b for a, b in skip)] or [f0]
k = max(1, min(MAX_RUNNERS, math.ceil(len(work) / MIN_PER_RUNNER)))
starts = sorted({f0} | {work[round(i * len(work) / k)] for i in range(1, k)})
chunks = [{'i': i, 'first': s, 'last': (starts[i + 1] - 1) if i + 1 < len(starts) else f1} for i, s in enumerate(starts)]
print(json.dumps(chunks))
