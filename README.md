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
src/trace.js      path-traced still render (loaded on first use)
assets/sketch.jpg reference sketch for the booth scene
```

## Run it locally

Any static server works, for example `python3 -m http.server` in this folder, then open `http://localhost:8000`. Opening `index.html` straight from disk will not work, because browsers block ES modules on `file://`.

## Known limits

- Imported models must be self-contained `.glb` files with a skeleton; Draco compression is not supported yet, and imported models are not stored in the project file.
- IK is two-bone only. Feet are not planted automatically during playback.
- Path-traced renders are grainy at low sample counts and have no denoiser yet. Only stills are path-traced; video is the real-time viewport.
