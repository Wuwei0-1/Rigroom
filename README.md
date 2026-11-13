# Rigroom render data

This branch holds render jobs and results for the Rigroom render server. It is not part of the website.

- `jobs/<id>/` — a job sent from the app: `scene.glb` (the stage) and `job.json` (camera, lighting, frames, quality).
- `out/<id>/` — the result: `render.png` for a frame, `shot.mp4` and `poster.png` for a shot, and `result.json`.

The workflow that renders them lives on `main` in `.github/workflows/render.yml`. Old jobs can be deleted from this branch at any time.
