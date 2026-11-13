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

Any character can wear a look: a rigged human model. Select the character, then Stage → Look → **Real model…** and pick a `.glb` (or an `.fbx` or `.gltf` together with its texture images). The character keeps its name, place, animation and controls: you, the timeline, Reach and the agent still pose the mannequin skeleton, and the model follows it every frame. Its proportions are fitted to the model, so hands and feet land where you put them.

- Skeletons are matched by bone name. Mixamo, Unreal, Character Creator, Rigify, 3ds Max Biped, VRM and Ready Player Me style rigs work.
- Models are stored in the browser (IndexedDB), so scenes come back after a reload. A project file opened on another device shows mannequins until the models are imported there too.
- Large scan textures are reduced to 2048 px so a tablet can hold several people at once.
- `.glb` export, the render server and the in-browser render all use the real models.

Where to get models: Mixamo characters (free with an Adobe account), Renderpeople's free rigged scanned people, Character Creator, or any rigged humanoid you have the rights to use. Check each model's licence before publishing renders.

## Render server

Project → Render server sends the scene to GitHub Actions, where Blender Cycles renders it on GitHub's machines. Public repositories get these machines free. A frame comes back as a PNG; a shot is split across up to 16 machines at once and comes back as an MP4.

Set it up once:

1. Make a fine-grained token: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token.
   - Repository access: **Only select repositories** → this repository.
   - Permissions: **Contents: Read and write**, **Actions: Read and write**.
2. In Rigroom, open Project → Render server → Server settings, check the repository name, paste the token, Save.

Jobs and results are stored on the `renders` branch (see its README), not on `main`, so the website is not rebuilt for every render. The token is stored only in the browser and sent only to `api.github.com`; never commit it.

Pushing changes to `render/` or the workflow re-renders a small self-test job, so a broken render setup shows up in the Actions tab.

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
src/models.js     human models: loading, fitting, skeleton matching, browser storage
render/           Blender render script and frame planner run by the workflow
.github/workflows/render.yml   the render server itself
assets/sketch.jpg reference sketch for the booth scene
```

## Run it locally

Any static server works, for example `python3 -m http.server` in this folder, then open `http://localhost:8000`. Opening `index.html` straight from disk will not work, because browsers block ES modules on `file://`.

## Known limits

- Project files refer to imported models by fingerprint; the models themselves stay in the browser that imported them.
- Looks follow the body and limbs; fingers and faces stay in the model's rest pose for now.
- IK is two-bone only. Feet are not planted automatically during playback.
- Path-traced renders are grainy at low sample counts and have no denoiser yet. Only stills are path-traced; video is the real-time viewport.
