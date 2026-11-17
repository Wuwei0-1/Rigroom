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
    # each stretch is encoded on its own and the pieces joined without re-encoding, so nothing has to be held in memory
    import os
    import tempfile
    tmp = tempfile.mkdtemp(prefix='splice_')
    enc = ['-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '%g' % fps]
    pieces, f = [], 0

    def piece(args):
        path = os.path.join(tmp, 'p%03d.mp4' % len(pieces))
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y'] + args + enc + [path], check=True)
        pieces.append(path)
    for p0, p1, path, (pw, ph) in patches:
        if p0 > f:
            piece(['-i', base, '-vf', 'trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS' % (f, p0)])
        piece(['-i', path, '-vf', 'scale=%d:%d,setsar=1,setpts=PTS-STARTPTS' % (w, h)])
        f = p1 + 1
    if f < total:
        piece(['-i', base, '-vf', 'trim=start_frame=%d,setpts=PTS-STARTPTS' % f])
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as fh:
        fh.write(''.join("file '%s'\n" % x for x in pieces))
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', base, '-map', '0:v', '-map', '1:a?',
           '-c', 'copy', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    for x in pieces + [lst]:
        os.remove(x)
    os.rmdir(tmp)
    n, *_ = probe(out)
    print('%s: %d frames (base %d), %d stretch(es) replaced' % (out, n, total, len(patches)))
    if n != total:
        sys.exit('frame count changed: %d -> %d' % (total, n))


if __name__ == '__main__':
    main(sys.argv[1:])
