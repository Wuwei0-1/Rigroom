// Studio sync: the scene and the people it uses are saved to the private studio repository,
// so every device (and Claude, from chat) works on the same scene.
import { conf, ready, readText, readBytes, commitFiles, explain, saveConf, checkStudio, forgetAccess } from './github.js';
import { sceneJSON, loadSceneObject, preloadForScene, pushUndo, toast, onSceneChange, onLibraryChange, refreshMotionUI, refreshLookPick } from './app.js';
import { listModels, storedModel, modelRigged, setRemoteFetcher, setNameLookup, setRemoteLister } from './models.js';
import { localMotions, setMotionRemote } from './motion.js';

const $ = s => document.querySelector(s);
const SCENE = 'scenes/current.json', INDEX = 'models/index.json', MINDEX = 'motions/index.json', SAVE_AFTER_MS = 8000;
const MAX_UPLOAD = 45e6;   // bytes of people per save; the rest go with the next one
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } }
};
let meta = store.get('rigroom.studio.meta') || {};   // { savedAt, hash, by } of the last scene this browser saved or opened
let index = null, mindex = null, dirty = false, libDirty = true, timer = null, saving = null, offer = null, suspend = 0;

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
async function loadMotionIndex() { if (mindex) return mindex; const t = await readText(MINDEX); mindex = t ? JSON.parse(t) : {}; return mindex; }

/** Save the scene, and any people, models or motions this browser has that the studio does not have yet. */
export async function saveNow(force) {
  if (!ready()) return false;
  if (saving) return saving;
  saving = (async () => {
    clearTimeout(timer);
    // the scene is written when it was edited here (or on request); a library-only save never replaces it,
    // and nor does anything while a newer studio scene is waiting for the user to choose
    const text = sceneText(), h = hashText(text), sceneNew = force || (dirty && h !== meta.hash && !offer);
    const settle = () => { if (h === meta.hash) dirty = false; };   // unsaved edits stay marked while an offer waits
    if (!sceneNew && !libDirty) { settle(); idle(); return true; }
    try {
      const scene = JSON.parse(text), lib = libDirty, idx = await loadIndex(), midx = lib ? await loadMotionIndex() : {}, files = [], added = [];
      let bytes = 0, more = false;
      // people the scene uses go first, then (after an import) the rest of this browser's library
      const used = new Set(refs(scene)), local = [...used, ...(lib ? (await listModels()).map(m => m.hash).filter(h => !used.has(h)) : [])];
      for (const hash of local) {
        if (idx[hash]) continue;
        const m = await storedModel(hash); if (!m) continue;
        if (bytes && bytes + m.bytes.byteLength > MAX_UPLOAD) { more = true; continue; }
        files.push({ path: `models/${hash}.glb`, bytes: m.bytes }); idx[hash] = { name: m.name || 'Model', size: m.bytes.byteLength }; const rig = modelRigged(hash); if (rig != null) idx[hash].rigged = rig; added.push(idx[hash].name); bytes += m.bytes.byteLength;
      }
      const moves = [];
      for (const m of lib ? await localMotions() : []) if (m.id && !midx[m.id]) { files.push({ path: `motions/${m.id}.json`, text: JSON.stringify(m) }); midx[m.id] = { name: m.name, seconds: m.seconds, frames: m.frames }; moves.push(m.name); }
      if (added.length) files.push({ path: INDEX, text: JSON.stringify(idx, null, 1) });
      if (moves.length) files.push({ path: MINDEX, text: JSON.stringify(midx, null, 1) });
      if (!files.length && !sceneNew) { if (lib) libDirty = false; settle(); idle(); return true; }
      status('Saving to your studio…');
      const savedAt = Date.now(), by = device();
      if (sceneNew) files.push({ path: SCENE, text: JSON.stringify({ ...scene, meta: { savedAt, by } }) });
      const what = [...added, ...moves.map(n => 'motion ' + n)];
      await commitFiles(files, (sceneNew ? 'Save scene' : 'Save to library') + (what.length ? ' with ' + what.join(', ') : ''));
      if (sceneNew) { meta = { savedAt, hash: h, by }; store.set('rigroom.studio.meta', meta); }
      if (lib) libDirty = more; if (sceneNew) dirty = sceneText() !== text; else settle(); idle(); if ((dirty && !offer) || more) schedule();
      return true;
    } catch (e) { index = null; mindex = null; status(explain(e), true); return false; }
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
  // a person that was replaced by a better copy is served as that copy
  setRemoteFetcher(async hash => { if (!ready()) return null; const i = await loadIndex(), to = i[hash] && i[hash].replacedBy; return readBytes(`models/${to || hash}.glb`); });
  setNameLookup(async hash => { const i = await loadIndex(); return i[hash] && i[hash].name; });
  setRemoteLister(async () => (ready() ? Object.entries(await loadIndex()).map(([hash, m]) => ({ hash, name: m.name || 'Model', size: m.size || 0, rigged: m.rigged, retired: !!m.retired })) : []));
  setMotionRemote({ index: async () => (ready() ? loadMotionIndex() : {}), fetch: async id => (ready() ? readText(`motions/${id}.json`) : null) });
}
export function initStudio() {
  onSceneChange(() => { if (suspend) return; dirty = true; if (ready()) { idle(); schedule(); } });
  onLibraryChange(() => { libDirty = true; if (ready()) schedule(); });
  $('#studioSave').onclick = async () => { if (!ready()) { $('#srvSetup').open = true; return toast('Connect your studio first, under Studio settings.', true); } if (await saveNow(true)) toast('Saved to your studio.'); };
  $('#studioOpen').onclick = () => pull(true);
  $('#syncOpen').onclick = () => { if (offer) open(offer); };
  $('#syncKeep').onclick = async () => { hideOffer(); if (await saveNow(true)) toast('Kept this scene and saved it to your studio.'); };
  $('#srvRepo').value = conf.studio; $('#srvToken').value = conf.token; $('#srvSetup').open = !conf.token;
  $('#siteNote').textContent = conf.site ? 'Renders run on ' + conf.site + '.' : '';
  $('#srvSave').onclick = () => {
    saveConf({ studio: $('#srvRepo').value, token: $('#srvToken').value }); index = null; mindex = null; libDirty = true; forgetAccess();
    if (!ready()) return toast('Enter the studio repository as owner/name and a token.', true);
    $('#srvSetup').open = false; toast('Studio connected.'); pull(false);
  };
  $('#srvForget').onclick = () => { saveConf({ token: '' }); $('#srvToken').value = ''; idle(); toast('Token removed from this browser.'); };
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') pull(false); else if (dirty || libDirty) saveNow(); });
  window.addEventListener('pagehide', () => { if (dirty) saveNow(); });
  setInterval(() => { if (!dirty) idle(); }, 60000);
  idle();
  if (ready()) pull(false).then(() => { refreshMotionUI(); refreshLookPick(); if (libDirty) schedule(); });
  else { refreshMotionUI(); refreshLookPick(); }
}
export const studioReady = ready;
