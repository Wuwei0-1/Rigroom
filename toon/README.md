# Toon: 3D cartoon films

Full-colour 3D cartoon characters and sets built in Blender from code, moved by recorded motion.

- `kit.py`: shapes (ellipsoids, capsules, tubes, rings), materials, a one-mesh skinned body, posing helpers (two-bone reach).
- `cast.py`: Edward's cast after his booth storyboard (IMG_1359): Socrates (curly hair and beard, chiton and red himation, a brass ring), Aria (bun, round glasses, mustard cardigan), Cleon (man-bun, beard, green hoodie), Julian (tall, swept hair, vest). Each is built on the motion-capture skeleton it is driven by, with lids, a mouth and brows.
- `lounge.py`: the botanical lounge laid out like the storyboard: two columns, a U-shaped velvet booth, a pedestal table, screens on brick, plants, glowing slates.
- `stage.py`: loads the animated-person FBX, keeps only its skeleton and samples its motion; Eevee, lights, cameras.
- `shot.py`: a test scene: seated characters take the upper-body part of the recorded idle, the standing one all of it; gestures blend in; heads turn to whoever speaks; mouths follow the voice; eyes blink; cuts are timeline markers. `--save` writes a .blend for the render server (job `source: blend`).
- `lineup.py`: a line-up render for checking the designs.

The skeleton and motion come from a licensed Renderpeople file, so the saved .blend files go in the private studio, never in this repository.
