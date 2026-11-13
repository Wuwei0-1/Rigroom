// Motion capture: recorded movement from a model file, moved onto Rigroom's standard character skeleton.
// A motion is stored once (this browser's IndexedDB, and the studio) and can be put on any character.
import * as THREE from 'three';
import { mapSkeleton, fitModel } from './models.js';

const V3 = THREE.Vector3, Q4 = THREE.Quaternion;
// the control skeleton: each bone's parent and its rest direction in the mannequin's T-pose
export const PARENT = { hips: null, spine: 'hips', chest: 'spine', neck: 'chest', head: 'neck', upperArm_L: 'chest', forearm_L: 'upperArm_L', hand_L: 'forearm_L', upperArm_R: 'chest', forearm_R: 'upperArm_R', hand_R: 'forearm_R', thigh_L: 'hips', shin_L: 'thigh_L', foot_L: 'shin_L', thigh_R: 'hips', shin_R: 'thigh_R', foot_R: 'shin_R' };
const ORDER = Object.keys(PARENT);
const CHILD = { hips: 'spine', spine: 'chest', chest: 'neck', neck: 'head', upperArm_L: 'forearm_L', forearm_L: 'hand_L', upperArm_R: 'forearm_R', forearm_R: 'hand_R', thigh_L: 'shin_L', shin_L: 'foot_L', thigh_R: 'shin_R', shin_R: 'foot_R' };
const INHERIT = { head: 'neck', hand_L: 'forearm_L', hand_R: 'forearm_R', foot_L: 'shin_L', foot_R: 'shin_R' };
const DIR = { hips: [0, 1, 0], spine: [0, 1, 0], chest: [0, 1, 0], neck: [0, 1, 0], upperArm_L: [1, 0, 0], forearm_L: [1, 0, 0], upperArm_R: [-1, 0, 0], forearm_R: [-1, 0, 0], thigh_L: [0, -1, 0], shin_L: [0, -1, 0], thigh_R: [0, -1, 0], shin_R: [0, -1, 0] };
export const PARTS = {
  body: ORDER,
  upper: ['spine', 'chest', 'neck', 'head', 'upperArm_L', 'forearm_L', 'hand_L', 'upperArm_R', 'forearm_R', 'hand_R'],
  arms: ['upperArm_L', 'forearm_L', 'hand_L', 'upperArm_R', 'forearm_R', 'hand_R'],
  lower: ['hips', 'thigh_L', 'shin_L', 'foot_L', 'thigh_R', 'shin_R', 'foot_R'],
  head: ['neck', 'head']
};
const r4 = v => Math.round(v * 1e4) / 1e4;

/**
 * Sample a clip on a model and express it on the control skeleton: for every frame, each bone's
 * rotation relative to its parent (from the T-pose), and the hips' offset from standing height,
 * as a fraction of hip height so it fits a taller or shorter character.
 * Changes the model (it is fitted and posed); pass a copy you no longer need.
 */
export function extractMotion(root, clip, name, fps = 30) {
  const { map, missing } = mapSkeleton(root); if (missing.length) return null;
  const wrap = fitModel(root, map); wrap.updateMatrixWorld(true);
  const P = o => o.getWorldPosition(new V3()), Q = o => o.getWorldQuaternion(new Q4());
  const entries = [], R = {};
  for (const k of ORDER) {
    const dst = map[k]; let rot;
    if (CHILD[k]) { let c = CHILD[k]; while (c && map[c] === dst) c = CHILD[c]; rot = new Q4().setFromUnitVectors(P(map[c]).sub(P(dst)).normalize(), new V3(...DIR[k])); }
    else rot = (R[INHERIT[k]] || new Q4()).clone();
    R[k] = rot;
    entries.push({ k, dst, TrInv: Q(dst).invert(), RInv: rot.clone().invert() });
  }
  const hips0 = P(map.hips), hipH = Math.max(0.2, hips0.y);
  const mixer = new THREE.AnimationMixer(root); mixer.clipAction(clip).play();
  const frames = Math.min(Math.round(clip.duration * fps) + 1, 9000);
  const bones = {}, hips = [], S = {};
  for (const e of entries) bones[e.k] = [];
  for (let i = 0; i < frames; i++) {
    // a repeating clip wraps to its start exactly at its end, so the last sample is taken a hair before it
    mixer.setTime(Math.min(i / fps, clip.duration - 1e-4)); wrap.updateMatrixWorld(true);
    for (const e of entries) {
      const s = Q(e.dst).multiply(e.TrInv).multiply(e.RInv); S[e.k] = s;   // the control bone's orientation in character space
      const local = PARENT[e.k] ? S[PARENT[e.k]].clone().invert().multiply(s) : s.clone();
      bones[e.k].push(...local.toArray().map(r4));
    }
    const h = P(map.hips).sub(hips0).divideScalar(hipH); hips.push(r4(h.x), r4(h.y), r4(h.z));
  }
  mixer.stopAllAction(); mixer.uncacheRoot(root);
  return { v: 1, name, fps, frames, seconds: r4((frames - 1) / fps), bones, hips };
}
/** Name a motion from its file: "rp_nathan_animated_003_walking.fbx" becomes "Walking (Nathan)". */
export function motionName(file, clip) {
  const base = file.replace(/\.[^.]+$/, ''), rp = base.match(/^rp_([a-z]+)_animated_\d+_([a-z]+)/i);
  const cap = s => s[0].toUpperCase() + s.slice(1).toLowerCase();
  if (rp) return cap(rp[2]) + ' (' + cap(rp[1]) + ')';
  const c = clip && clip.name && !/^(take|mixamo|animation|armature|clip)/i.test(clip.name) ? clip.name : '';
  return (c || base.replace(/[_]+/g, ' ')).trim() || 'Motion';
}

/* ───────── sampling ───────── */
const qa = new Q4(), qb = new Q4();
export function sampleBone(m, k, t) {
  const a = m.bones[k]; if (!a) return null;
  const x = Math.max(0, Math.min(m.frames - 1, t * m.fps)), i = Math.floor(x), j = Math.min(i + 1, m.frames - 1), u = x - i;
  qa.fromArray(a, i * 4); qb.fromArray(a, j * 4);
  return new Q4().slerpQuaternions(qa, qb, u);
}
export function sampleHips(m, t) {
  const a = m.hips, x = Math.max(0, Math.min(m.frames - 1, t * m.fps)), i = Math.floor(x), j = Math.min(i + 1, m.frames - 1), u = x - i;
  return new V3(a[i * 3] + (a[j * 3] - a[i * 3]) * u, a[i * 3 + 1] + (a[j * 3 + 1] - a[i * 3 + 1]) * u, a[i * 3 + 2] + (a[j * 3 + 2] - a[i * 3 + 2]) * u);
}

/* ───────── library: this browser, plus the studio ───────── */
const DB = 'rigroom-motions', STORE = 'motions';
function db() { return new Promise((res, rej) => { if (!window.indexedDB) return rej(new Error('no IndexedDB')); const r = indexedDB.open(DB, 1); r.onupgradeneeded = () => r.result.createObjectStore(STORE); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }); }
async function idb(mode, fn) { const d = await db(); return new Promise((res, rej) => { const t = d.transaction(STORE, mode), q = fn(t.objectStore(STORE)); t.oncomplete = () => res(q && q.result); t.onerror = () => rej(t.error); }); }
const memory = new Map();
let remote = null;   // { index: async () => ({ id: {name, seconds} }), fetch: async id => text }
export function setMotionRemote(r) { remote = r; }
async function idOf(m) {
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(m.name + '|' + m.frames + '|' + m.bones.hips.slice(0, 40).join(',') + '|' + m.hips.slice(-30).join(',')));
  return Array.from(new Uint8Array(h).slice(0, 10), b => b.toString(16).padStart(2, '0')).join('');
}
export async function saveMotion(m) {
  const id = m.id || await idOf(m); m.id = id; memory.set(id, m);
  try { await idb('readwrite', s => s.put(m, id)); } catch (e) { /* kept for this visit */ }
  return id;
}
export async function localMotions() {
  let rows = []; try { rows = (await idb('readonly', s => s.getAll())) || []; } catch (e) { rows = [...memory.values()]; }
  for (const r of rows) memory.set(r.id, r);
  return rows;
}
/** Every motion this browser or the studio has: [{ id, name, seconds }]. */
export async function listMotions() {
  const out = new Map();
  for (const m of await localMotions()) out.set(m.id, { id: m.id, name: m.name, seconds: m.seconds });
  if (remote) { try { const idx = await remote.index(); for (const [id, m] of Object.entries(idx || {})) if (!out.has(id)) out.set(id, { id, name: m.name, seconds: m.seconds }); } catch (e) { /* offline */ } }
  return [...out.values()].sort((a, b) => a.name.localeCompare(b.name));
}
export async function getMotion(id) {
  if (memory.has(id)) return memory.get(id);
  try { const m = await idb('readonly', s => s.get(id)); if (m) { memory.set(id, m); return m; } } catch (e) { /* storage unavailable */ }
  if (remote) { const t = await remote.fetch(id); if (t) { const m = JSON.parse(t); m.id = id; await saveMotion(m); return m; } }
  return null;
}
export async function findMotion(name) {
  const all = await listMotions(), n = String(name || '').toLowerCase();
  const hit = all.find(m => m.id === name) || all.find(m => m.name.toLowerCase() === n) || all.find(m => m.name.toLowerCase().includes(n));
  return hit ? getMotion(hit.id) : null;
}
