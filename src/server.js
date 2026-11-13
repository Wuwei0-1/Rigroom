// Render server: sends the scene to GitHub Actions, where Blender Cycles renders it.
// Jobs go to the "renders" branch of the repository; results come back to out/<id>/ there.
// The GitHub token stays in this browser's storage and is only sent to api.github.com.
import { exportGLB, cameraAt, frameAspect, ctx, anim, saveFile, toast } from './app.js';

const $ = s => document.querySelector(s);
const API = 'https://api.github.com';
const BRANCH = 'renders', WORKFLOW = 'render.yml';
const QUALITY = { draft: { width: 960, samples: 48 }, good: { width: 1280, samples: 128 }, final: { width: 1920, samples: 400 } };
const POLL_MS = 20000;
const store = {
  get(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } },
  set(k, v) { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch (e) { /* storage unavailable */ } }
};
let token = store.get('rigroom.ghToken'), repo = store.get('rigroom.ghRepo') || guessRepo();
let jobs = []; try { jobs = JSON.parse(store.get('rigroom.jobs') || '[]'); } catch (e) { jobs = []; }
let pollTimer = null, sending = false, shown = null;

function guessRepo() {
  const m = location.hostname.match(/^([^.]+)\.github\.io$/i), seg = location.pathname.split('/').filter(Boolean)[0];
  return m && seg ? m[1] + '/' + seg : '';
}
async function gh(path, opts = {}) {
  const res = await fetch(API + path, { ...opts, headers: { Authorization: 'Bearer ' + token, Accept: opts.raw ? 'application/vnd.github.raw+json' : 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', ...(opts.body ? { 'Content-Type': 'application/json' } : {}) } });
  if (res.status === 404 && opts.allow404) return null;
  if (!res.ok) { let msg = 'HTTP ' + res.status; try { msg = (await res.json()).message || msg; } catch (e) { /* no body */ } const err = new Error(msg); err.status = res.status; throw err; }
  if (opts.raw === 'blob') return res.blob();
  if (opts.raw) return res.text();
  return res.status === 204 ? null : res.json();
}
function b64(buf) {
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf); let s = '';
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
  return btoa(s);
}
const putFile = (path, bytes, message) => gh(`/repos/${repo}/contents/${path}`, { method: 'PUT', body: JSON.stringify({ message, content: b64(bytes), branch: BRANCH }) });
async function ensureBranch() {
  if (await gh(`/repos/${repo}/branches/${BRANCH}`, { allow404: true })) return;
  const main = await gh(`/repos/${repo}/git/ref/heads/main`);
  await gh(`/repos/${repo}/git/refs`, { method: 'POST', body: JSON.stringify({ ref: 'refs/heads/' + BRANCH, sha: main.object.sha }) });
}
function newId(kind) {
  const d = new Date(), p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}-${kind}-${Math.random().toString(36).slice(2, 6)}`;
}
function saveJobs() { store.set('rigroom.jobs', JSON.stringify(jobs.slice(0, 20))); }
function explain(e) {
  if (e.status === 401) return 'GitHub rejected the token. Check it under Server settings.';
  if (e.status === 403) return 'The token is missing a permission: it needs Contents and Actions, read and write, on this repository.';
  if (e.status === 404) return 'GitHub could not find the repository or the render workflow. Check the repository name under Server settings.';
  if (e.status === 422) return 'GitHub refused the request: ' + e.message;
  return e.status ? 'GitHub error: ' + e.message : 'Could not reach GitHub. Check the connection.';
}

async function send(kind) {
  if (sending) return;
  if (!token || !repo) { $('#srvSetup').open = true; return toast('Add the repository and a GitHub token under Server settings first.', true); }
  const q = QUALITY[$('#srvQuality').value] || QUALITY.good, f = Math.round(ctx.frame);
  const frames = kind === 'still' ? [f, f] : [0, anim.length];
  const width = q.width, height = Math.round(width / frameAspect() / 2) * 2;
  const id = newId(kind);
  sending = true; $('#srvStill').disabled = $('#srvShot').disabled = true;
  const job = { id, kind, frames, status: 'sending', created: Date.now(), repo };
  jobs.unshift(job); renderList();
  try {
    const glb = await exportGLB({ animated: kind === 'shot' });
    const cameras = []; for (let i = frames[0]; i <= frames[1]; i++) cameras.push({ f: i, ...cameraAt(i) });
    const spec = { v: 1, id, kind, frames, fps: anim.fps, width, height, samples: q.samples,
      dof: $('#srvDof').checked ? { fstop: +$('#srvFstop').value } : null,
      cameras, look: { ...ctx.look }, floor: { color: '#6b6e76', roughness: 0.92 } };
    await ensureBranch();
    await putFile(`jobs/${id}/scene.glb`, glb, `Render job ${id}: scene`);
    await putFile(`jobs/${id}/job.json`, new TextEncoder().encode(JSON.stringify(spec)), `Render job ${id}`);
    await gh(`/repos/${repo}/actions/workflows/${WORKFLOW}/dispatches`, { method: 'POST', body: JSON.stringify({ ref: 'main', inputs: { job: id } }) });
    job.status = 'rendering'; job.started = Date.now();
    toast(kind === 'still' ? 'Frame ' + f + ' sent to the render server.' : 'Shot sent: ' + (frames[1] - frames[0] + 1) + ' frames.');
  } catch (e) {
    job.status = 'failed'; job.error = explain(e); toast(job.error, true);
    if (e.status === 401 || e.status === 404) $('#srvSetup').open = true;
  } finally {
    sending = false; $('#srvStill').disabled = $('#srvShot').disabled = false; saveJobs(); renderList(); schedulePoll(2000);
  }
}

async function poll() {
  pollTimer = null;
  const pending = jobs.filter(j => j.status === 'rendering' && j.repo === repo);
  if (!pending.length || !token) return;
  for (const j of pending) {
    try {
      const txt = await gh(`/repos/${repo}/contents/out/${j.id}/result.json?ref=${BRANCH}`, { raw: true, allow404: true });
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
    const blob = await gh(`/repos/${j.repo}/contents/out/${j.id}/${j.file}?ref=${BRANCH}`, { raw: 'blob' });
    const typed = new Blob([blob], { type: j.file.endsWith('.mp4') ? 'video/mp4' : 'image/png' });
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
      a.href = j.run || `https://github.com/${j.repo}/actions/workflows/${WORKFLOW}`; row.append(a);
    }
    list.append(row);
  }
  const failed = jobs[0] && jobs[0].status === 'failed' && jobs[0].error;
  $('#srvNote').textContent = failed ? jobs[0].error : 'Renders with Blender on GitHub’s machines, for free. A frame takes a few minutes; a whole shot is split across many machines at once.';
}

export function initServer() {
  $('#srvRepo').value = repo; $('#srvToken').value = token; $('#srvSetup').open = !token;
  $('#srvSave').onclick = () => {
    repo = $('#srvRepo').value.trim().replace(/^https:\/\/github\.com\//, '').replace(/\/+$/, ''); token = $('#srvToken').value.trim();
    store.set('rigroom.ghRepo', repo); store.set('rigroom.ghToken', token);
    toast(token && /^[\w.-]+\/[\w.-]+$/.test(repo) ? 'Render server settings saved.' : 'Enter the repository as owner/name and a token.', !(token && repo));
    if (token) { $('#srvSetup').open = false; schedulePoll(500); }
  };
  $('#srvForget').onclick = () => { token = ''; $('#srvToken').value = ''; store.set('rigroom.ghToken', ''); toast('Token removed from this browser.'); };
  $('#srvStill').onclick = () => send('still');
  $('#srvShot').onclick = () => send('shot');
  $('#resultClose').onclick = () => { $('#resultView').hidden = true; const v = $('#resultMedia video'); if (v) v.pause(); };
  $('#resultSave').onclick = () => { if (shown) saveFile(shown.name, shown.blob); };
  for (const j of jobs) if (j.status === 'sending') { j.status = 'failed'; j.error = 'Interrupted while sending.'; }
  renderList(); schedulePoll(1500);
  setInterval(() => { if (jobs.length) renderList(); }, 60000);
}
