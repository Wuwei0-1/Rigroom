// Render server: renders the scene with Blender Cycles on GitHub's machines.
// A job is a small description (the scene, frames, camera, quality) written to the private studio;
// the renderer rebuilds the scene there from the people already stored in the studio.
import { cameraAt, frameAspect, ctx, anim, saveFile, toast, sceneJSON } from './app.js';
import { conf, ready, canRender, readText, readBytes, commitFiles, dispatchRender, explain } from './github.js';
import { saveNow } from './studio.js';

const $ = s => document.querySelector(s);
const WORKFLOW = 'render.yml';
const QUALITY = { draft: { width: 960, samples: 48 }, good: { width: 1280, samples: 128 }, final: { width: 1920, samples: 400 } };
const POLL_MS = 20000;
let jobs = []; try { jobs = JSON.parse(localStorage.getItem('rigroom.jobs') || '[]'); } catch (e) { jobs = []; }
let pollTimer = null, sending = false, shown = null;

function newId(kind) {
  const d = new Date(), p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}-${kind}-${Math.random().toString(36).slice(2, 6)}`;
}
function saveJobs() { try { localStorage.setItem('rigroom.jobs', JSON.stringify(jobs.slice(0, 20))); } catch (e) { /* storage unavailable */ } }

async function send(kind) {
  if (sending) return;
  if (!ready() || !canRender()) { $('#srvSetup').open = true; return toast('Connect your studio first, under Studio settings.', true); }
  const q = QUALITY[$('#srvQuality').value] || QUALITY.good, f = Math.round(ctx.frame);
  const frames = kind === 'still' ? [f, f] : [0, anim.length];
  const width = q.width, height = Math.round(width / frameAspect() / 2) * 2;
  const id = newId(kind);
  sending = true; $('#srvStill').disabled = $('#srvShot').disabled = true;
  const job = { id, kind, frames, status: 'sending', created: Date.now(), repo: conf.studio };
  jobs.unshift(job); renderList();
  try {
    // the people in the scene must be in the studio before the renderer can use them
    if (!(await saveNow())) throw Object.assign(new Error('Could not save the scene to your studio.'), { shown: true });
    const cameras = []; for (let i = frames[0]; i <= frames[1]; i++) cameras.push({ f: i, ...cameraAt(i) });
    const spec = { v: 2, id, kind, frames, fps: anim.fps, width, height, samples: q.samples,
      dof: $('#srvDof').checked ? { fstop: +$('#srvFstop').value } : null,
      cameras, look: { ...ctx.look }, floor: { color: '#6b6e76', roughness: 0.92 }, source: 'scene', scene: sceneJSON(false) };
    await commitFiles([{ path: `jobs/${id}/job.json`, text: JSON.stringify(spec) }], `Render job ${id}`);
    await dispatchRender(id);
    job.status = 'rendering'; job.started = Date.now();
    toast(kind === 'still' ? 'Frame ' + f + ' sent to the render server.' : 'Shot sent: ' + (frames[1] - frames[0] + 1) + ' frames.');
  } catch (e) {
    job.status = 'failed'; job.error = e.shown ? e.message : explain(e); toast(job.error, true);
    if (e.status === 401 || e.status === 404) $('#srvSetup').open = true;
  } finally {
    sending = false; $('#srvStill').disabled = $('#srvShot').disabled = false; saveJobs(); renderList(); schedulePoll(2000);
  }
}

async function poll() {
  pollTimer = null;
  const pending = jobs.filter(j => j.status === 'rendering' && j.repo === conf.studio);
  if (!pending.length || !ready()) return;
  for (const j of pending) {
    try {
      const txt = await readText(`out/${j.id}/result.json`);
      if (!txt) continue;
      const r = JSON.parse(txt); j.status = r.status === 'done' ? 'done' : 'failed'; j.file = r.file; j.run = r.run;
      if (j.status === 'done') toast((j.kind === 'still' ? 'Frame ' + j.frames[0] : 'Shot') + ' is rendered. Tap View.');
      else j.error = 'The render failed on the server.';
    } catch (e) { if (e.status === 401) { j.status = 'failed'; j.error = explain(e); } }
  }
  saveJobs(); renderList(); schedulePoll();
}
function schedulePoll(ms) { if (pollTimer) clearTimeout(pollTimer); if (jobs.some(j => j.status === 'rendering')) pollTimer = setTimeout(poll, ms ?? POLL_MS); }

async function view(j) {
  try {
    toast('Downloading the render…');
    const bytes = await readBytes(`out/${j.id}/${j.file}`); if (!bytes) throw Object.assign(new Error('missing'), { status: 404 });
    const typed = new Blob([bytes], { type: j.file.endsWith('.mp4') ? 'video/mp4' : 'image/png' });
    if (shown) URL.revokeObjectURL(shown.url);
    shown = { url: URL.createObjectURL(typed), blob: typed, name: 'rigroom-' + j.id + (j.file.endsWith('.mp4') ? '.mp4' : '.png') };
    const media = $('#resultMedia'); media.textContent = '';
    const el = document.createElement(j.file.endsWith('.mp4') ? 'video' : 'img');
    el.src = shown.url; if (el.tagName === 'VIDEO') { el.controls = true; el.loop = true; el.playsInline = true; el.autoplay = true; el.muted = true; } else el.alt = 'Rendered frame';
    media.append(el);
    $('#resultCap').textContent = j.kind === 'still' ? 'Frame ' + j.frames[0] : 'Frames ' + j.frames[0] + ' to ' + j.frames[1];
    $('#resultView').hidden = false;
  } catch (e) { toast(explain(e), true); }
}

function ago(t) { const m = Math.round((Date.now() - t) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : Math.round(m / 60) + ' h ago'; }
function renderList() {
  const list = $('#srvJobs'); list.textContent = '';
  for (const j of jobs.slice(0, 6)) {
    const row = document.createElement('div'); row.className = 'job';
    const what = document.createElement('span'); what.className = 'what';
    what.textContent = (j.kind === 'still' ? 'Frame ' + j.frames[0] : 'Shot ' + j.frames[0] + '–' + j.frames[1]) + ' · ' + ago(j.created);
    const pill = document.createElement('span');
    const label = { sending: 'Sending', rendering: 'Rendering', done: 'Done', failed: 'Failed' }[j.status] || j.status;
    pill.className = 'pill' + (j.status === 'done' ? ' done' : j.status === 'failed' ? ' bad' : ' run'); pill.textContent = label;
    if (j.error) pill.title = j.error;
    row.append(what, pill);
    if (j.status === 'done') { const b = document.createElement('button'); b.className = 'btn'; b.textContent = 'View'; b.onclick = () => view(j); row.append(b); }
    if ((j.status === 'rendering' || j.status === 'failed') && (j.run || j.repo)) {
      const a = document.createElement('a'); a.className = 'btn ghost'; a.textContent = 'Log'; a.target = '_blank'; a.rel = 'noopener';
      a.href = j.run || `https://github.com/${conf.site}/actions/workflows/${WORKFLOW}`; row.append(a);
    }
    list.append(row);
  }
  const failed = jobs[0] && jobs[0].status === 'failed' && jobs[0].error;
  $('#srvNote').textContent = failed ? jobs[0].error : 'Renders with Blender on GitHub’s machines, for free. A frame takes a few minutes; a whole shot is split across many machines at once.';
}

export function initServer() {
  $('#srvStill').onclick = () => send('still');
  $('#srvShot').onclick = () => send('shot');
  $('#resultClose').onclick = () => { $('#resultView').hidden = true; const v = $('#resultMedia video'); if (v) v.pause(); };
  $('#resultSave').onclick = () => { if (shown) saveFile(shown.name, shown.blob); };
  for (const j of jobs) if (j.status === 'sending') { j.status = 'failed'; j.error = 'Interrupted while sending.'; }
  renderList(); schedulePoll(1500);
  setInterval(() => { if (jobs.length) renderList(); }, 60000);
}
