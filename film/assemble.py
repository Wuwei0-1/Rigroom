"""Join rendered parts into one film, with title cards between them.

    python assemble.py OUT.mp4 [--size 1280x720] [--fps 24] ITEM [ITEM ...]

Each ITEM is a video file, or a card written as "card:Big line|Smaller line" (5 seconds, fading in and out),
or "end:Text" (4 seconds). Parts may differ in size, frame rate and sound: each is fitted to the size
(letterboxed if its shape differs), brought to the frame rate (12 fps parts hold each drawing for two
frames), and given silence if it has no sound.
"""
import argparse
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('items', nargs='+')
ap.add_argument('--size', default='1280x720')
ap.add_argument('--fps', default='24')
a = ap.parse_args()
W, H = (int(v) for v in a.size.split('x'))
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSerif%s.ttf'
tmp = tempfile.mkdtemp()
AUDIO = ['-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2']
VIDEO = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', a.fps]


def run(args):
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y'] + args, check=True)


def card(i, lines, secs):
    img = Image.new('RGB', (W, H), (6, 5, 8))
    d = ImageDraw.Draw(img)
    s = H / 540
    sizes = [(t, int((40 if k == 0 else 22) * s), k == 0) for k, t in enumerate(lines)]
    y = H / 2 - sum(z for _, z, _ in sizes) * 1.35 / 2
    for text, size, bold in sizes:
        f = ImageFont.truetype(FONT % ('-Bold' if bold else ''), size)
        d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=(232, 222, 205) if bold else (170, 162, 150))
        y += size * 1.35
    png, mp4 = os.path.join(tmp, 'card%d.png' % i), os.path.join(tmp, 'item%d.mp4' % i)
    img.save(png)
    run(['-loop', '1', '-framerate', a.fps, '-i', png, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(secs),
         '-vf', 'fade=t=in:st=0:d=1,fade=t=out:st=%g:d=1' % (secs - 1)] + VIDEO + AUDIO + [mp4])
    return mp4


def has_audio(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout
    return bool(out.strip())


def part(i, path):
    mp4 = os.path.join(tmp, 'item%d.mp4' % i)
    fit = 'scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=%s' % (W, H, W, H, a.fps)
    if has_audio(path):
        run(['-i', path, '-vf', fit] + VIDEO + AUDIO + [mp4])
    else:
        run(['-i', path, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-shortest', '-vf', fit, '-map', '0:v', '-map', '1:a'] + VIDEO + AUDIO + [mp4])
    return mp4


pieces = []
for i, item in enumerate(a.items):
    if item.startswith('card:'):
        pieces.append(card(i, item[5:].split('|'), 5))
    elif item.startswith('end:'):
        pieces.append(card(i, [item[4:]], 4))
    else:
        pieces.append(part(i, item))
lst = os.path.join(tmp, 'list.txt')
with open(lst, 'w') as fh:
    fh.writelines("file '%s'\n" % p for p in pieces)
run(['-f', 'concat', '-safe', '0', '-i', lst, '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-maxrate', '4M', '-bufsize', '8M',
     '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', a.out])
print(a.out)
