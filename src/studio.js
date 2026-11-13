// Studio sync: the scene and the people it uses are saved to the private studio repository,
// so every device (and Claude, from chat) works on the same scene.
import { conf, ready, readText, readBytes, commitFiles, explain, saveConf, checkStudio, forgetAccess } from './github.js';
import { sceneJSON, loadSceneObject, preloadForScene, pushUndo, toast, onSceneChange } from './app.js';
import { modelBytes, cachedName, setRemoteFetcher, setNameLookup } from './models.js';

const $ = s => document.querySelector(s);
const SCENE = 'scenes/current.json', INDEX = 'models/index.json', SAVE_AFTER_MS = 8000;
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } }
};
let meta = store.get('rigroom.studio.meta') || {};   // { savedAt, hash, by } of the last scene this browser saved or opened
let index = null, dirty = false, timer = null, saving = null, offer = null, suspend = 0;

const hashText = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36) + ':' + s.length; };
const sceneText = () => JSON.stringify(sceneJSON(false));
const device = () => /iPad/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1) ? 'iPad' : /iPhone/.test(navigator.userAgent) ? 'iPhone' : /Android/.test(navigator.userAgent) ? 'Android' : 'computer';
function ago(t) { if (!t) return ''; const m = Math.round((Date.now() - t) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : Math.round(m / 1440) + ' d ago'; }
function status(text, bad) { const el = $('#studioStatus'); if (!el) return; el.textContent = text; el.classList.toggle('bad-text', !!bad); }
function idle() {
  if (!ready()) return status('Not connected. Your scenes stay in this browser. Open Studio settings to connect.');
  status(dirty ? 'Unsaved changes; saving shortly…' : meta.savedAt ? 'Saved to your studio ' + ago(meta.savedAt) + (meta.by ? ' (' + meta.by + ')' : '') + '.' : 'Connected to ' + conf.studio + '.');
}
const refs = scene => (scene.ents || []).map(s => s && s.params && (s.params.look || s.params.model)).filter(Boolean);

async function loadIndex() { if (index) return index; const t = await readText(INDEX); index = t ? JSON.parse(t) : {}; return index; }

/** Save the scene, and any people or models it uses that the studio does not have yet. */
export async function saveNow(force) {
  if (!ready()) return false;
  if (saving) return saving;
  saving = (async () => {
    clearTimeout(timer);
    const text = sceneText(), h = hashText(text);
    if (!force && h === meta.hash) { dirty = false; idle(); return true; }
    status('Saving to your studio…');
    try {
      const scene = JSON.parse(text), idx = await loadIndex(), files = [], added = [];
      for (const m of new Set(refs(scene))) if (!idx[m]) { const b = modelBytes(m); if (b) { files.push({ path: `models/${m}.glb`, bytes: b }); idx[m] = { name: cachedName(m) || 'Model', size: b.byteLength }; added.push(idx[m].name); } }
      const savedAt = Date.now(), by = device();
      files.push({ path: SCENE, text: JSON.stringify({ ...scene, meta: { savedAt, by } }) });
      if (added.length) files.push({ path: INDEX, text: JSON.stringify(idx, null, 1) });
      await commitFiles(files, added.length ? 'Save scene with ' + added.join(', ') : 'Save scene');
      meta = { savedAt, hash: h, by }; store.set('rigroom.studio.meta', meta);
      dirty = sceneText() !== text; idle(); if (dirty) schedule();
      return true;
    } catch (e) { index = null; status(explain(e), true); return false; }
    finally { saving = null; }
  })();
  return saving;
}
function schedule() { clearTimeout(timer); if (ready()) timer = setTimeout(() => saveNow(), SAVE_AFTER_MS); }

/** Open a scene from the studio, fetching any people it uses. */
async function open(remote) {
  suspend++;
  try {
    status('Opening the studio scene…');
    const missing = await preloadForScene(remote);
    pushUndo(); loadSceneObject(remote);
    meta = { savedAt: remote.meta && remote.meta.savedAt, hash: hashText(sceneText()), by: remote.meta && remote.meta.by }; store.set('rigroom.studio.meta', meta);
    dirty = false; idle(); hideOffer();
    toast('Opened the scene from your studio' + (remote.meta && remote.meta.by ? ', saved by ' + remote.meta.by + ' ' + ago(remote.meta.savedAt) : '') + '.' + (missing ? ' ' + missing + ' model(s) could not be fetched.' : ''), !!missing);
  } finally { suspend--; }
}
/** Check the studio for a newer scene. Opens it straight away unless this browser has unsaved work. */
export async function pull(manual) {
  if (!ready()) { if (manual) { $('#srvSetup').open = true; toast('Connect your studio first, under Studio settings.', true); } return; }
  try {
    const acc = await checkStudio();
    const t = await readText(SCENE);
    if (!t) {   // the studio is reachable but has no scene yet: this browser's scene becomes the first
      if (!acc.write) return status(explain({ status: 403 }), true);
      if (manual) toast('Your studio has no saved scene yet. Saving this one.');
      return saveNow(true);
    }
    const remote = JSON.parse(t), at = (remote.meta && remote.meta.savedAt) || 0;
    if (!manual && at <= (meta.savedAt || 0)) { idle(); return; }
    const local = meta.hash ? hashText(sceneText()) !== meta.hash : true;   // never saved here: treat local work as worth asking about
    if (manual || !local) return open(remote);
    showOffer(remote);
  } catch (e) { status(explain(e), true); }
}
function showOffer(remote) {
  offer = remote; const bar = $('#syncBar');
  $('#syncMsg').textContent = 'Your studio has a newer scene' + (remote.meta && remote.meta.by ? ', saved by ' + remote.meta.by + ' ' + ago(remote.meta.savedAt) : '') + '.';
  bar.hidden = false;
}
function hideOffer() { offer = null; $('#syncBar').hidden = true; }

/** Called before the saved scene is built: models it needs but this browser lacks come from the studio. */
export function prepareStudio() {
  setRemoteFetcher(async hash => (ready() ? readBytes(`models/${hash}.glb`) : null));
  setNameLookup(async hash => { const i = await loadIndex(); return i[hash] && i[hash].name; });
}
export function initStudio() {
  onSceneChange(() => { if (suspend) return; dirty = true; if (ready()) { idle(); schedule(); } });
  $('#studioSave').onclick = async () => { if (!ready()) { $('#srvSetup').open = true; return toast('Connect your studio first, under Studio settings.', true); } if (await saveNow(true)) toast('Saved to your studio.'); };
  $('#studioOpen').onclick = () => pull(true);
  $('#syncOpen').onclick = () => { if (offer) open(offer); };
  $('#syncKeep').onclick = async () => { hideOffer(); if (await saveNow(true)) toast('Kept this scene and saved it to your studio.'); };
  $('#srvRepo').value = conf.studio; $('#srvToken').value = conf.token; $('#srvSetup').open = !conf.token;
  $('#siteNote').textContent = conf.site ? 'Renders run on ' + conf.site + '.' : '';
  $('#srvSave').onclick = () => {
    saveConf({ studio: $('#srvRepo').value, token: $('#srvToken').value }); index = null; forgetAccess();
    if (!ready()) return toast('Enter the studio repository as owner/name and a token.', true);
    $('#srvSetup').open = false; toast('Studio connected.'); pull(false);
  };
  $('#srvForget').onclick = () => { saveConf({ token: '' }); $('#srvToken').value = ''; idle(); toast('Token removed from this browser.'); };
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') pull(false); else if (dirty) saveNow(); });
  window.addEventListener('pagehide', () => { if (dirty) saveNow(); });
  setInterval(() => { if (!dirty) idle(); }, 60000);
  idle();
  if (ready()) pull(false);
}
export const studioReady = ready;
