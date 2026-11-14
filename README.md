# Rigroom Animator

A character animation tool that runs in the browser, built for iPad. Stage characters and props, pose them, keyframe a shot, and let a built-in Claude agent do the work from a sentence. Path-traced stills are rendered in the page.

No build step. The site is plain HTML, CSS and ES modules; three.js loads from a CDN.

## Put it online with GitHub Pages

1. Push these files to the `main` branch of a GitHub repository.
2. In the repository: **Settings → Pages → Build and deployment → Source: Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
3. After a minute the site is live at `https://<your-username>.github.io/<repository-name>/`.
4. On the iPad, open that address in Safari and use **Share → Add to Home Screen** to run it full screen.

## The agent

The Agent tab talks to the Claude API directly from your browser. Open **Agent settings**, paste an API key from [console.anthropic.com](https://console.anthropic.com), pick a model and save.

- The key is stored only in that browser's local storage and is sent only to `api.anthropic.com`.
- **Never commit a key to this repository.** The site is public; each person who uses the agent enters their own key.
- Usage is billed to the key's account.

## Real people (looks)

Any character can wear a look: a rigged human model. Select the character, then Stage → Look and choose one of **Your people** (everyone this browser or your studio has), or **Real model…** and pick a `.glb` (or an `.fbx` or `.gltf` together with its texture images). The character keeps its name, place, animation and controls: you, the timeline, Reach and the agent still pose the mannequin skeleton, and the model follows it every frame. Its proportions are fitted to the model, so hands and feet land where you put them.

- Skeletons are matched by bone name. Mixamo, Unreal, Character Creator, Rigify, 3ds Max Biped, VRM and Ready Player Me style rigs work.
- Models are stored in the browser (IndexedDB), and with a studio connected they are copied there too, so every device has the same people.
- Large scan textures are reduced to 2048 px so a tablet can hold several people at once.
- `.glb` export, the render server and the in-browser render all use the real models.

Scanned people come two ways. **Rigged** scans have a skeleton and can be a look. **Posed** scans (such as Renderpeople's Posed People) are frozen in one pose with no skeleton: import them with Stage → Import model and stand them in the scene as extras. Pick the 100k version of a scan on a tablet.

Where to get models: Mixamo characters (free with an Adobe account), Renderpeople's free rigged scanned people, Character Creator, or any rigged humanoid you have the rights to use. Check each model's licence before publishing renders.

## Motion (motion capture)

Recorded movement from a file can go on any character. Pose → Motion → **Import motion…** and pick an animated `.fbx` or `.glb` (with its textures if you want the person in it too), such as a Renderpeople animated person or a Mixamo clip. The movement is moved onto Rigroom's standard skeleton once, so a walk recorded on one person plays on anyone: steps are scaled to the new character's legs.

- Choose a motion, select a character, set the frame, and press **Apply at this frame**. It becomes ordinary keys on the timeline, which you and the agent can edit like any other.
- **Body** limits it to the upper body, arms, hips and legs, or head. **Replace** swaps out those bones' keys over the span; **Layer on top** adds the movement to the pose that is there (an idle over a seated pose keeps the character seated).
- **Speed** retimes it, **Repeat** plays it again (a walk keeps travelling), and **In place** takes out the forward travel.
- The agent has the same: `list_motions` and `apply_motion` (with `from` and `to` in seconds to take a piece of a long clip).
- Motions are stored in the browser and in your studio (`motions/`). Fingers and faces are not carried over yet.

## Photoreal sets: light, surfaces, air

The viewport is a preview. The render server draws the real thing, and these are what make it look real:

- **Lights.** Stage → **+ Light** adds a soft panel, a spot or a bulb. Place it, pick who or what it aims at, set power (watts), size and colour. A bigger panel gives softer shadows. For interiors, turn the sun off (Project → Look → Sun power 0) and light with lamps.
- **Materials.** A prop's Material preset becomes a full surface in the render: wood (grain), leather and velvet (padded, with soft corners), fabric, stone, brick (courses and mortar), plaster, metal, paper, glass, plastic, ceramic. **Glow** and **Neon** make a prop shine, for lampshades, screens, signs and far-off bulbs that blur into discs. Hard edges are rounded slightly, as every real edge is.
- **Environment** (Project → Look): the surroundings that light the scene from every side: a photographed studio, interior, courtyard, city, forest, sunrise, sunset or night (1K HDR images in `assets/env`, CC0 from Poly Haven), or the soft grey default. **Turn** rotates it; **Ambient** is its strength.
- **Floor:** matte, wood boards, concrete, tiles or carpet. **Haze** puts smoke or dust in the air, so light beams show and the distance softens.
- **People.** Skin scatters light under its surface. Imports pick up a scan's normal and gloss maps by file name (`…_norm.jpg`, `…_gloss.jpg` next to `…_dif.jpg`).
- **Holding things.** Select a prop and set **Held by** to a character's hand (or ask the agent: `hold`). The prop sits in the palm, the fingers close around it, and it follows the hand through every pose.
- **Hands and faces.** Stage → Look → Hands sets each hand of a real person: relaxed, open, grip, fist or point. Every character also has a **jaw** and **lids** control on the rig (rotate about x: about 3 to 8° for speech, 26° for a blink) that drive a real person's jaw and eyelids.
- **Lens.** A camera key can carry an f-stop (through the agent's `set_camera`), which blurs what is nearer or farther than the target. Renders get a little bloom, grain and corner darkening; shots get motion blur.

The agent has all of this: `add_light`, `place` (material, light settings), `set_lighting` (environment, floor, haze), `set_hands`, and `set_camera` with `fstop`.

## Film: script to video

`film/` turns a script into a film on the render server. The script, voices and results live in the studio under `film/<id>/`.

1. `python3 film/script_to_lines.py SCRIPT.txt film/<id>/script.json` reads a play laid out as numbered `N. SPEAKER: line` entries with stage directions.
2. The **Voices** workflow (inputs `film=<id>`, optional `lines=1-9`) speaks every line with [Chatterbox](https://github.com/resemble-ai/chatterbox) and writes `film/<id>/audio/NNN.mp3` and `audio.json` (lengths and loudness curves). Each character's voice comes from a reference clip, `film/<id>/voices/<Character>.wav`: record 8 to 20 seconds yourself, or let the workflow design one (the built-in voice shifted to the pitch set in `voices.json`, belonging to no real person). A speech recogniser listens to every take and bad takes are redone.
3. `film/director.js` runs inside the app on a posed scene and keys it from the audio: jaws from loudness, blinks, who looks at whom, breathing, hand gestures, and one camera per shot with cuts on the lines.
4. The scene goes to the render server as a job with `audio` (which lines start when) and `speaker_light` (who speaks when): the result is an MP4 with the voices mixed in, and whoever is speaking is lit from behind so their outline glows.

## Studio

The studio is a private repository (by default `<this repository>-studio`, for example `Wuwei0-1/Rigroom-studio`) that holds your scenes, the people and models they use, render jobs and finished renders. Keep it private: licensed models must not be shared publicly.

Connect it once per device under Project → Studio → Studio settings, with a fine-grained token that has **Contents: Read and write** and **Actions: Read and write** on both this repository and the studio.

- The scene saves to `scenes/current.json` a few seconds after each change, and when the app goes to the background.
- People, models and motions you import are uploaded once (`models/<fingerprint>.glb`, `motions/<id>.json`) and downloaded by any device that needs them.
- When the studio has a newer scene than this device (saved on another device, or by Claude), the app opens it, or asks first if this device has unsaved work.

## Render server

Project → Render server renders the scene with Blender Cycles on GitHub's machines, which are free for this public repository. A job is a small description written to the studio (`jobs/<id>/job.json`): the scene, the frames, the camera and the quality. The workflow rebuilds the scene from it with the app itself in headless Chrome (`render/export_scene.mjs`), using the people stored in the studio, renders it, and writes the result to `out/<id>/` in the studio. A shot is split across up to 16 machines at once and comes back as an MP4. Frames are encrypted while they move between machines, so nothing from the studio is left in this public repository.

The workflow needs one secret in this repository: **STUDIO_TOKEN**, a token with Contents read and write on the studio.

To render from outside the app (for example from a Claude chat): `python3 tools/studio_job.py STUDIO_DIR still 0 --quality good`, commit and push the job to the studio, then start the workflow with inputs `job=<id>` and `store=studio`.

The token is stored only in the browser and sent only to `api.github.com`; never commit it.

Pushing changes to `render/` or the workflow re-renders a small mannequin-only self-test job from this repository's `renders` branch, so a broken render setup shows up in the Actions tab.

## What it does

- **Stage:** characters (a built-in mannequin, or rigged `.glb` models you import) and props, each with position, facing, scale, color, roughness and metalness.
- **Posing:** Rotate a bone, Move the root, Reach a hand or foot to a point (two-bone IK), Place the whole thing. Pin a hand or foot so it stays put while the body moves.
- **Timeline:** keyframes per bone, auto-key, loop, three motion modes, undo and redo.
- **Shot camera:** camera keyframes, Shot view with a locked frame, a reference image overlay for posing against a drawing.
- **Look:** image-based lighting, a sun you can aim, exposure, filmic tone mapping, soft shadows.
- **Photoreal render:** path-traces the current frame (real light bounces) and saves a PNG.
- **Output:** project `.json`, a `.glb` of the whole scene with baked animation (opens in Blender), and video of the viewport.

## Layout

```
index.html        page and import map (library versions are pinned here)
src/ui.css        styles
src/main.js       entry point and the opening booth scene
src/app.js        viewport, stage, posing, timeline, agent tools
src/agent.js      Claude API tool-use loop
src/trace.js      path-traced still render in the browser (loaded on first use)
src/server.js     render server: sends jobs to GitHub Actions and fetches results
src/github.js     GitHub access: the token, the studio, commits
src/studio.js     studio sync: saving and opening scenes and their models
src/models.js     human models: loading, fitting, skeleton matching, browser storage
render/           Blender render script, surfaces and lights, and frame planner run by the workflow
film/             script parser, voices (Chatterbox) and the film director
assets/env/       environment light images (CC0)
.github/workflows/render.yml   the render server itself
.github/workflows/voices.yml   speaks a film's lines
assets/sketch.jpg reference sketch for the booth scene
```

## Updates

Every release stamps a version (`python3 tools/bump_version.py`) into `index.html`, `version.json` and the URL of each app file, so browsers never mix old and new files. A running copy checks `version.json` when it opens or comes back to the foreground and offers **Update now**. The current version is shown under Project.

## Run it locally

Any static server works, for example `python3 -m http.server` in this folder, then open `http://localhost:8000`. Opening `index.html` straight from disk will not work, because browsers block ES modules on `file://`.

## Known limits

- Project files refer to imported models by fingerprint; without a studio, the models stay in the browser that imported them.
- Looks and motions follow the body and limbs; fingers, faces and shoulder shrugs stay in the model's rest pose for now.
- IK is two-bone only. Feet are not planted automatically during playback.
- Path-traced renders are grainy at low sample counts and have no denoiser yet. Only stills are path-traced; video is the real-time viewport.
