// Builds scene.glb for a render job from its scene description, using the Rigroom app itself
// in headless Chrome, so the render matches what the app shows.
//
// Usage: node render/export_scene.mjs SITE_DIR STUDIO_DIR JOB_DIR
//   SITE_DIR    a checkout of the Rigroom site (index.html, src/)
//   STUDIO_DIR  a checkout of the studio with the models the scene uses (models/<hash>.glb)
//   JOB_DIR     the job folder; job.json must have "scene". Writes scene.glb, and fills in
//               cameras and height in job.json when they are missing, and the scene's lights.
// Environment: CHROME (path to Chrome), RIGROOM_LOCAL_LIBS (serve three.js from a local
// node_modules folder instead of the CDN, for machines without internet access).
import { chromium } from 'playwright-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const [site, studio, jobDir] = process.argv.slice(2);
if (!site || !studio || !jobDir) { console.error('Usage: node export_scene.mjs SITE_DIR STUDIO_DIR JOB_DIR'); process.exit(2); }
const jobPath = path.join(jobDir, 'job.json');
const job = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
if (!job.scene) { console.error('job.json has no scene'); process.exit(2); }

const types = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.wasm': 'application/wasm', '.glb': 'model/gltf-binary' };
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  const file = url.startsWith('/__studio/') ? path.join(studio, url.slice('/__studio/'.length)) : path.join(site, url === '/' ? 'index.html' : url);
  fs.readFile(file, (err, data) => { if (err) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' }); res.end(data); });
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const port = server.address().port;

const browser = await chromium.launch({
  executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox']
});
let failed = false;
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const local = process.env.RIGROOM_LOCAL_LIBS;
  if (local) {
    await context.route('https://cdn.jsdelivr.net/npm/**', r => {
      const m = r.request().url().split('/npm/')[1].match(/^((?:@[^/]+\/)?[^@/]+)@[^/]+\/(.*)$/);
      const f = m && path.join(local, m[1], m[2]);
      if (!f || !fs.existsSync(f)) return r.fulfill({ status: 404 });
      r.fulfill({ body: fs.readFileSync(f), contentType: types[path.extname(f)] || 'application/javascript' });
    });
    await context.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  }
  const page = await context.newPage();
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.addInitScript(() => { try { localStorage.clear(); } catch (e) { /* none */ } });
  await page.goto(`http://127.0.0.1:${port}/`);
  await page.waitForFunction(() => window.__rigroom && window.__rigroom.app, null, { timeout: 120000 });
  const out = await page.evaluate(async job => {
    const { app, models } = window.__rigroom;
    models.setRemoteFetcher(async h => { const r = await fetch('/__studio/models/' + h + '.glb'); return r.ok ? r.arrayBuffer() : null; });
    models.setNameLookup(async () => 'Model');
    const missing = await app.preloadForScene(job.scene);
    app.loadSceneObject(job.scene);
    const [f0, f1] = job.frames;
    if (!job.cameras || !job.cameras.length) { job.cameras = []; for (let f = f0; f <= f1; f++) job.cameras.push({ f, ...app.cameraAt(f) }); }
    if (!job.height) job.height = Math.round(job.width / app.frameAspect() / 2) * 2;
    job.look = { ...app.ctx.look, ...(job.look || {}) };
    job.lights = app.lightList();
    app.applyFrame(f0);
    const buf = new Uint8Array(await app.exportGLB({ animated: job.kind === 'shot' }));
    let s = ''; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return { missing, glb: btoa(s), job };
  }, job);
  if (out.missing) { console.error(out.missing + ' model(s) used by the scene are not in the studio'); failed = true; }
  fs.writeFileSync(path.join(jobDir, 'scene.glb'), Buffer.from(out.glb, 'base64'));
  const filled = { ...out.job }; delete filled.scene;
  fs.writeFileSync(jobPath, JSON.stringify({ ...filled, scene: job.scene }));
  console.log('scene.glb written:', (Buffer.from(out.glb, 'base64').length / 1e6).toFixed(1) + ' MB');
} finally {
  await browser.close(); server.close();
}
process.exit(failed ? 1 : 0);
