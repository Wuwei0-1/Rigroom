"""Rebuild a rendered part's sound from its render job, keeping the picture as it is.

    python3 remix.py STUDIO JOB VIDEO.mp4 OUT.mp4 [--drop ID,ID...]

STUDIO is a checkout of the studio, JOB a render job id in it (jobs/JOB/job.json). The job's audio cues are
mixed exactly as the render server's publish step mixes them (each line delayed to its time, summed without
normalising, padded to the part's length) and put under the video, whose picture is copied untouched.
--drop leaves out the cues with these ids (e.g. a sound effect that should go).
"""
import argparse, json, os, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('studio'); ap.add_argument('job'); ap.add_argument('video'); ap.add_argument('out')
    ap.add_argument('--drop', default='')
    o = ap.parse_args()
    job = json.load(open(os.path.join(o.studio, 'jobs', o.job, 'job.json')))
    a = job.get('audio') or {}
    drop = set(x for x in o.drop.split(',') if x)
    cues = []
    for c in a.get('cues', []):
        cid = c.get('id') or '%03d' % c['n']
        p = os.path.join(o.studio, 'film', a.get('film'), 'audio', cid + '.mp3')
        if cid not in drop and os.path.exists(p):
            cues.append((c, p))
    if not cues:
        sys.exit('no audio cues to mix')
    secs = float(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration',
                                 '-of', 'csv=p=0', o.video], capture_output=True, text=True, check=True).stdout.strip())
    args = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', o.video]
    for c, p in cues:
        args += ['-i', p]
    parts = ''.join('[%d:a]adelay=%d:all=1[a%d];' % (i + 1, round(c['t'] * 1000), i) for i, (c, p) in enumerate(cues))
    mix = parts + ''.join('[a%d]' % i for i in range(len(cues))) + 'amix=inputs=%d:normalize=0:dropout_transition=0,apad[a]' % len(cues)
    args += ['-filter_complex', mix, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-ac', '2', '-b:a', '160k',
             '-t', '%.3f' % secs, '-movflags', '+faststart', o.out]
    subprocess.run(args, check=True)
    print('%s: %d cues mixed under %.1f s of picture%s' % (o.out, len(cues), secs, (' (dropped %s)' % ', '.join(sorted(drop))) if drop else ''))


if __name__ == '__main__':
    main()
