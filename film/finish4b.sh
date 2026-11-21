#!/bin/sh
# Finish The Ring of Gyges IV (second edit): graphics, the ten books, the whole film with book cards, and the Shorts.
#   ./finish4b.sh   (expects out/gyges4b-seq1..7/shot.mp4 in the studio, pulled with git lfs)
set -e
G=/home/claude/gyges4
FILM=/home/claude/rigroom-remote/film
ST=/home/claude/rigroom-studio
W=$G/finish_b
mkdir -p $W $G/gfx_b
PLANS=$(ls $G/b/seq[1-7]_plan.json | tr '\n' ',' | sed 's/,$//')
# the 29 graphics, timed to the final plans (skipped if already made)
python3 $FILM/scenes4.py $G/phrases_b.json $G/gfx_b --plans $PLANS > /dev/null
for id in $(python3 -c "import json;print(' '.join(w['id'] for w in json.load(open('$G/gfx_b/graphics.json'))))"); do
  [ -s $G/gfx_b/$id.mp4 ] || python3 $FILM/scenes4.py $G/phrases_b.json $G/gfx_b --plans $PLANS --only $id --render > /dev/null
done
python3 $FILM/scenes4.py $G/phrases_b.json $G/gfx_b --plans $PLANS > /dev/null    # graphics.json for all of them again
for n in 1 2 3 4 5 6 7; do
  [ -s $W/seq$n.mp4 ] || python3 $FILM/compose.py cut $ST/out/gyges4b-seq$n/shot.mp4 $G/gfx_b $n $W/seq$n.mp4
done
python3 $FILM/books4.py sections $W $G/b $G/script_b.json $G/phrases_b.json $W/books
python3 $FILM/books4.py film $W/books "Out of the Cave"
python3 $FILM/books4.py shorts $W/books $G/b $G/phrases_b.json $G/script_b.json
ls -la $W/books/film.mp4 $W/books/book-*.mp4 $W/books/short-*.mp4
