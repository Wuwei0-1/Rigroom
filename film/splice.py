"""Put re-rendered stretches into a finished film part, keeping its sound.

    python3 splice.py BASE.mp4 OUT.mp4 PATCH.mp4@FRAME [PATCH.mp4@FRAME ...]

Each patch is a render of the same scene that starts at FRAME of the base (a render job whose frames run
[FRAME, ...]); its frames replace the base's frames one for one. The base's audio is kept as it is, and the
patches' own audio (if any) is ignored. Frame-accurate: the picture is re-encoded once with H.264.
"""
import json, subprocess, sys


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries',
                          'stream=nb_read_packets,r_frame_rate,width,height', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)['streams'][0]
    num, den = (int(x) for x in s['r_frame_rate'].split('/'))
    return int(s['nb_read_packets']), num / den, s['width'], s['height']


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    base, out = argv[0], argv[1]
    total, fps, w, h = probe(base)
    patches = []
    for arg in argv[2:]:
        path, _, at = arg.rpartition('@')
        n, pfps, pw, ph = probe(path)
        if abs(pfps - fps) > 1e-6:
            sys.exit('%s runs at %g fps, the base at %g' % (path, pfps, fps))
        patches.append((int(at), int(at) + n - 1, path, (pw, ph)))
    patches.sort()
    for (a0, a1, pa, _), (b0, b1, pb, _) in zip(patches, patches[1:]):
        if b0 <= a1:
            sys.exit('%s and %s overlap' % (pa, pb))
    if patches[-1][1] >= total:
        sys.exit('%s runs past the end of the base (%d frames)' % (patches[-1][2], total))
    inputs, parts, f = ['-i', base], [], 0
    for i, (p0, p1, path, (pw, ph)) in enumerate(patches, 1):
        inputs += ['-i', path]
        if p0 > f:
            parts.append('[0:v]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS[s%d]' % (f, p0, len(parts)))
        parts.append('[%d:v]scale=%d:%d,setsar=1,setpts=PTS-STARTPTS[s%d]' % (i, w, h, len(parts)))
        f = p1 + 1
    if f < total:
        parts.append('[0:v]trim=start_frame=%d,setpts=PTS-STARTPTS[s%d]' % (f, len(parts)))
    graph = ';'.join(parts) + ';' + ''.join('[s%d]' % i for i in range(len(parts))) + 'concat=n=%d:v=1:a=0,format=yuv420p[v]' % len(parts)
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y'] + inputs + ['-filter_complex', graph, '-map', '[v]', '-map', '0:a?',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-r', '%g' % fps, '-c:a', 'copy', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    n, *_ = probe(out)
    print('%s: %d frames (base %d), %d stretch(es) replaced' % (out, n, total, len(patches)))
    if n != total:
        sys.exit('frame count changed: %d -> %d' % (total, n))


if __name__ == '__main__':
    main(sys.argv[1:])
