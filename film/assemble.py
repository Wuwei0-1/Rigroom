"""Join a film's rendered parts into one video, with a title card at the start and an end card.

    python assemble.py OUT.mp4 "Title" "Subtitle" PART.mp4 [PART.mp4 ...]

Every part must share frame size and rate (the render server's output does). Cards are drawn here.
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

out, title, subtitle, parts = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate', '-of', 'csv=p=0', parts[0]],
                       capture_output=True, text=True, check=True).stdout.strip().split(',')
W, H, rate = int(probe[0]), int(probe[1]), probe[2]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSerif%s.ttf'
tmp = tempfile.mkdtemp()


def card(name, lines, secs):
    img = Image.new('RGB', (W, H), (6, 5, 8))
    d = ImageDraw.Draw(img)
    y = H / 2 - sum(s for _, s, _ in lines) / 2 * 1.35
    for text, size, bold in lines:
        f = ImageFont.truetype(FONT % ('-Bold' if bold else ''), size)
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, y), text, font=f, fill=(232, 222, 205) if bold else (170, 162, 150))
        y += size * 1.35
    png = os.path.join(tmp, name + '.png')
    img.save(png)
    mp4 = os.path.join(tmp, name + '.mp4')
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-loop', '1', '-framerate', rate, '-i', png,
                    '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(secs),
                    '-vf', 'fade=t=in:st=0:d=1,fade=t=out:st=%g:d=1,format=yuv420p' % (secs - 1),
                    '-c:v', 'libx264', '-crf', '20', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', mp4], check=True)
    return mp4


s = H / 540
first = card('title', [(title, int(40 * s), True), (subtitle, int(22 * s), False)], 5)
last = card('end', [('End of play', int(30 * s), True)], 4)
# bring every part to the same audio format, so the joins are clean
norm = []
for i, p in enumerate(parts):
    q = os.path.join(tmp, 'part%d.mp4' % i)
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', p, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', q], check=True)
    norm.append(q)
lst = os.path.join(tmp, 'list.txt')
with open(lst, 'w') as fh:
    for p in [first] + norm + [last]:
        fh.write("file '%s'\n" % p)
subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-maxrate', '3M', '-bufsize', '6M', '-c:a', 'copy', '-movflags', '+faststart', out], check=True)
print(out)
