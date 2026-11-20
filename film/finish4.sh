#!/bin/sh
# Finish The Ring of Gyges IV from the seven sequence renders in the studio:
# cut in the story graphics, join with a title and end card, subtitle, normalise loudness.
#   ./finish4.sh            (expects out/gyges4-seq1..7/shot.mp4 in the studio, pulled with git lfs)
set -e
G=/home/claude/gyges4
FILM=/home/claude/rigroom-remote/film
ST=/home/claude/rigroom-studio
W=$G/finish
mkdir -p $W
CARD=5
PLANS=""
OFFS=""
T=$CARD
for n in 1 2 3 4 5 6 7; do
  python3 $FILM/compose.py cut $ST/out/gyges4-seq$n/shot.mp4 $G/gfx $n $W/seq$n.mp4
  PLANS="$PLANS${PLANS:+,}$G/seq${n}_plan.json"
  OFFS="$OFFS${OFFS:+,}$T"
  D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $W/seq$n.mp4)
  T=$(python3 -c "print(round($T + $D, 3))")
done
python3 $FILM/assemble.py $W/joined.mp4 "card:The Ring of Gyges IV|Out of the Cave" \
  $W/seq1.mp4 $W/seq2.mp4 $W/seq3.mp4 $W/seq4.mp4 $W/seq5.mp4 $W/seq6.mp4 $W/seq7.mp4 \
  "end:The Ring of Gyges IV  ·  wuwei0-1.github.io/Wuwei01"
python3 $FILM/compose.py srt $G/script.json $G/phrases.json $W/gyges4.srt --plans $PLANS --offsets $OFFS
ffmpeg -nostdin -loglevel error -y -i $W/joined.mp4 \
  -vf "subtitles=$W/gyges4.srt:force_style='FontName=Inter,FontSize=12,BorderStyle=3,Outline=1,Shadow=0,BackColour=&H90000000,MarginV=16'" \
  -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 160k -ar 48000 \
  -movflags +faststart $W/ring-of-gyges-iv.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 $W/ring-of-gyges-iv.mp4
