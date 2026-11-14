"""Splits a render job into frame chunks for parallel runners. Prints a JSON list."""
import json
import math
import sys

MAX_RUNNERS = 20      # parallel machines per job (GitHub runs up to 20 at once for free)
MIN_PER_RUNNER = 3    # each runner spends about a minute installing Blender, so give it real work

with open(sys.argv[1]) as fh:
    job = json.load(fh)
f0, f1 = (int(v) for v in job['frames'])
n = f1 - f0 + 1
per = max(MIN_PER_RUNNER, math.ceil(n / MAX_RUNNERS))
chunks = [{'i': i, 'first': s, 'last': min(f1, s + per - 1)} for i, s in enumerate(range(f0, f1 + 1, per))]
print(json.dumps(chunks))
