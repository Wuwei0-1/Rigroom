// Human models: loading, fitting, skeleton mapping and storage.
// A loaded model is kept as a self-contained .glb in this browser's IndexedDB, keyed by its hash,
// so scenes that use it come back after a reload.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';

const LIBS = 'https://cdn.jsdelivr.net/npm/three@0.172.0/examples/jsm/libs/';
const MAX_TEXTURE = 2048;   // tablets run out of GPU memory on 8K scan textures
let renderer = null, gltfLoader = null;
const cache = new Map();    // hash -> { name, bytes, template }
let remoteFetch = null;     // fetches a model's bytes from the studio when this browser lacks it
export function setRemoteFetcher(fn) { remoteFetch = fn; }

export function initModels(r) { renderer = r; }
let draco = null, ktx2 = null;
function makeLoader(manager) {
  const l = new GLTFLoader(manager);
  if (!draco) draco = new DRACOLoader().setDecoderPath(LIBS + 'draco/gltf/');
  l.setDRACOLoader(draco); l.setMeshoptDecoder(MeshoptDecoder);
  if (renderer) { try { if (!ktx2) ktx2 = new KTX2Loader().setTranscoderPath(LIBS + 'basis/').detectSupport(renderer); l.setKTX2Loader(ktx2); } catch (e) { /* KTX2 unsupported here */ } }
  return l;
}
function loader() { return gltfLoader || (gltfLoader = makeLoader()); }

/* ───────── storage ───────── */
const DB = 'rigroom', STORE = 'models';
function db() {
  return new Promise((res, rej) => {
    if (!window.indexedDB) return rej(new Error('no IndexedDB'));
    const r = indexedDB.open(DB, 1);
    r.onupgradeneeded = () => r.result.createObjectStore(STORE);
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  });
}
async function idb(mode, fn) {
  const d = await db();
  return new Promise((res, rej) => { const t = d.transaction(STORE, mode), req = fn(t.objectStore(STORE)); t.oncomplete = () => res(req && req.result); t.onerror = () => rej(t.error); });
}
async function hashOf(bytes) {
  const h = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(h).slice(0, 12), b => b.toString(16).padStart(2, '0')).join('');
}
export async function listModels() {
  try { const rows = await idb('readonly', s => s.getAll()); return (rows || []).map(r => ({ hash: r.hash, name: r.name, size: r.bytes.byteLength })); }
  catch (e) { return [...cache.entries()].map(([hash, m]) => ({ hash, name: m.name, size: m.bytes.byteLength })); }
}
export async function deleteModel(hash) { cache.delete(hash); try { await idb('readwrite', s => s.delete(hash)); } catch (e) { /* storage unavailable */ } }
export function cachedName(hash) { const m = cache.get(hash); return m ? m.name : null; }
export function cachedModels() { return [...cache.entries()].map(([hash, m]) => ({ hash, name: m.name })); }

async function parseGLB(bytes) {
  return new Promise((res, rej) => loader().parse(bytes.slice(0), '', g => { g.scene.animations = g.animations || []; res(g.scene); }, e => rej(e instanceof Error ? e : new Error(String(e && e.message || e)))));
}
/** Make sure the models with these hashes are parsed and ready to clone. Returns the hashes still missing. */
export async function preloadModels(hashes) {
  const missing = [];
  for (const hash of new Set(hashes)) {
    if (!hash || cache.has(hash)) continue;
    try {
      let row = null; try { row = await idb('readonly', s => s.get(hash)); } catch (e) { /* storage unavailable */ }
      if (!row && remoteFetch) { const bytes = await remoteFetch(hash); if (bytes) { row = { hash, name: await remoteName(hash), bytes }; try { await idb('readwrite', s => s.put(row, hash)); } catch (e) { /* kept for this visit */ } } }
      if (!row) { missing.push(hash); continue; }
      cache.set(hash, { name: row.name, bytes: row.bytes, template: await parseGLB(row.bytes) });
    } catch (e) { missing.push(hash); }
  }
  return missing;
}
let nameLookup = null, remoteList = null;
/** remoteList: async () => [{ hash, name, size }] of the models kept in the studio. */
export function setRemoteLister(fn) { remoteList = fn; }
/** Every model this browser or the studio has: [{ hash, name, size, here }]. */
export async function libraryModels() {
  const out = new Map((await listModels()).map(m => [m.hash, { ...m, here: true, rigged: modelRigged(m.hash) }]));
  if (remoteList) { try { for (const m of await remoteList()) { const o = out.get(m.hash); if (!o) out.set(m.hash, { ...m, here: false }); else if (o.rigged == null) o.rigged = m.rigged ?? null; } } catch (e) { /* offline */ } }
  return [...out.values()].sort((a, b) => a.name.localeCompare(b.name));
}
export function setNameLookup(fn) { nameLookup = fn; }
async function remoteName(hash) { try { return (nameLookup && await nameLookup(hash)) || 'Model'; } catch (e) { return 'Model'; } }
/** Add a model that arrived as .glb bytes (from the studio or a tool). */
export async function addModelBytes(hash, name, bytes) {
  if (!cache.has(hash)) cache.set(hash, { name, bytes, template: await parseGLB(bytes) });
  try { await idb('readwrite', s => s.put({ hash, name, bytes }, hash)); } catch (e) { /* kept for this visit */ }
}
/** A fresh copy of a stored model, or null if it is not loaded. */
export function instantiate(hash) {
  const m = cache.get(hash); if (!m) return null;
  const obj = cloneSkinned(m.template);
  obj.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; if (o.isSkinnedMesh) o.frustumCulled = false; } });
  return obj;
}
export function modelBytes(hash) { const m = cache.get(hash); return m ? m.bytes : null; }
/** Whether a loaded model has a humanoid skeleton a character can wear (null if it is not loaded here). */
export function modelRigged(hash) { const m = cache.get(hash); if (!m) return null; if (m.rigged == null) m.rigged = !mapSkeleton(m.template).missing.length; return m.rigged; }
/** A stored model's bytes, from memory or this browser's storage. */
export async function storedModel(hash) {
  const m = cache.get(hash); if (m) return { name: m.name, bytes: m.bytes };
  try { const r = await idb('readonly', s => s.get(hash)); return r ? { name: r.name, bytes: r.bytes } : null; } catch (e) { return null; }
}

/* ───────── loading from files ───────── */
// "rp_eric_rigged_001_yup_t.fbx" becomes "Eric"; other names just lose their extension and underscores
function niceName(file) {
  let n = file.replace(/\.[^.]+$/, '');
  const rp = n.match(/^rp_([a-z]+)_(?:rigged|animated|posed)_\d+/i);
  if (rp) return rp[1][0].toUpperCase() + rp[1].slice(1);
  n = n.replace(/_(?:[yz]up_[at]|\d+k)$/i, '').replace(/[_]+/g, ' ').trim();
  return n || 'Model';
}
async function downscale(file) {
  // big scan textures are shrunk to MAX_TEXTURE on their long side; small ones pass through
  try {
    const bmp = await createImageBitmap(file);
    const s = Math.min(1, MAX_TEXTURE / Math.max(bmp.width, bmp.height));
    if (s >= 1) { bmp.close && bmp.close(); return file; }
    const c = document.createElement('canvas'); c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
    c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height); bmp.close && bmp.close();
    return await new Promise(r => c.toBlob(b => r(b || file), /png$/i.test(file.name) ? 'image/png' : 'image/jpeg', 0.92));
  } catch (e) { return file; }
}
function toStandard(m) {
  if (!m || m.isMeshStandardMaterial || m.isMeshBasicMaterial) return m;
  const s = new THREE.MeshStandardMaterial({ name: m.name, color: m.color ? m.color.clone() : new THREE.Color(1, 1, 1), map: m.map || null, normalMap: m.normalMap || null,
    alphaMap: m.alphaMap || null, transparent: !!m.transparent, opacity: m.opacity ?? 1, side: m.side, roughness: m.shininess != null ? THREE.MathUtils.clamp(1 - Math.sqrt(m.shininess / 100), 0.25, 0.95) : 0.7, metalness: 0 });
  if (m.emissiveMap) { s.emissiveMap = m.emissiveMap; s.emissive = m.emissive ? m.emissive.clone() : new THREE.Color(1, 1, 1); }
  if (s.map) s.map.colorSpace = THREE.SRGBColorSpace;
  return s;
}
/**
 * Load a model from the files the user picked (a .glb, or a .gltf/.fbx with its textures). Stores it and returns
 * { hash, name, file, anim }. hash is null when the file holds only a skeleton (an animation file without a body).
 * anim, when the file carries recorded movement, is { root, clips }: a parsed copy to read the motion from.
 */
export async function importFiles(fileList) {
  const files = [...fileList], main = files.find(f => /\.(glb|gltf|fbx)$/i.test(f.name));
  if (!main) throw new Error('Pick a .glb, .gltf or .fbx file (with its texture images, if it has separate ones).');
  const name = niceName(main.name);
  let bytes, anim = null, meshes = 0;
  if (/\.glb$/i.test(main.name)) {
    bytes = await main.arrayBuffer();
    // scans often carry 4K or 8K textures; re-pack them at a size a tablet can hold
    const scene = await parseGLB(bytes); let big = 0;
    scene.traverse(o => { if (o.isMesh) meshes++; });
    if (scene.animations.length) anim = { root: await parseGLB(bytes), clips: scene.animations };
    scene.traverse(o => { if (!o.isMesh) return; for (const m of [].concat(o.material)) for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap', 'alphaMap']) { const im = m && m[k] && m[k].image; if (im && Math.max(im.width || 0, im.height || 0) > MAX_TEXTURE) big++; } });
    if (big) { scene.animations = []; bytes = await new GLTFExporter().parseAsync(scene, { binary: true, maxTextureSize: MAX_TEXTURE }); }
  }
  else {
    // resolve the textures and buffers the model refers to by file name
    const urls = new Map();
    for (const f of files) if (f !== main) { const blob = /\.(jpe?g|png|webp)$/i.test(f.name) ? await downscale(f) : f; urls.set(f.name.split(/[\\/]/).pop().toLowerCase(), URL.createObjectURL(blob)); }
    let loading = 0, settle = null;
    const allLoaded = new Promise(r => { settle = r; });
    const manager = new THREE.LoadingManager(() => { loading = 0; settle(); }, undefined, () => {});
    manager.onStart = () => { loading = 1; };
    manager.setURLModifier(u => { const base = decodeURIComponent(u.split(/[\\/]/).pop().split('?')[0]).toLowerCase(); return urls.get(base) || u; });
    let root;
    if (/\.fbx$/i.test(main.name)) {
      const { FBXLoader } = await import('three/addons/loaders/FBXLoader.js');
      root = new FBXLoader(manager).parse(await main.arrayBuffer(), '');
    } else {
      const text = await main.text();
      root = (await new Promise((res, rej) => makeLoader(manager).parse(text, '', res, rej))).scene;
    }
    // let texture images finish decoding before they are written into the stored copy
    await new Promise(res => setTimeout(res, 50));
    if (loading) await Promise.race([allLoaded, new Promise(res => setTimeout(res, 20000))]);
    const clips = (root.animations || []).filter(c => c.tracks.length && c.duration > 0);
    root.animations = [];
    root.traverse(o => { if (o.isMesh) meshes++; });
    root.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(toStandard) : toStandard(o.material); });
    bytes = await new GLTFExporter().parseAsync(root, { binary: true, maxTextureSize: MAX_TEXTURE });
    for (const u of urls.values()) URL.revokeObjectURL(u);
    if (clips.length) anim = { root, clips };
  }
  if (anim) anim.clips = anim.clips.filter(c => c.tracks.length && c.duration > 0);
  if (anim && !anim.clips.length) anim = null;
  if (!meshes) { if (anim) return { hash: null, name, file: main.name, anim }; throw new Error('That file has nothing to show.'); }
  const hash = await hashOf(bytes);
  if (!cache.has(hash)) cache.set(hash, { name, bytes, template: await parseGLB(bytes) });
  try { await idb('readwrite', s => s.put({ hash, name, bytes }, hash)); } catch (e) { /* kept for this visit only */ }
  return { hash, name, file: main.name, anim };
}

/* ───────── humanoid skeleton mapping ───────── */
// canonical names are the mannequin's bones; a model's bones are matched by name in any common convention
// (Mixamo, Unreal, Character Creator, Rigify, 3ds Max Biped, VRM and Ready Player Me style)
const NOISE = new Set(['mixamorig', 'cc', 'base', 'def', 'org', 'mch', 'bip', 'bip01', 'bip001', 'jnt', 'joint', 'bone', 'rig', 'armature', 'skeleton', 'valvebiped', 'j', 'b']);
const KIND = {
  hips: ['hips', 'pelvis', 'hip'], neck: ['neck'], head: ['head'],
  upperArm: ['arm', 'upperarm', 'uparm', 'armupper'], forearm: ['forearm', 'lowerarm', 'elbow', 'armlower'], hand: ['hand', 'wrist'],
  thigh: ['upleg', 'thigh', 'upperleg', 'legupper'], shin: ['leg', 'calf', 'shin', 'lowerleg', 'knee', 'leglower'], foot: ['foot', 'ankle']
};
function parseName(raw) {
  const tokens = String(raw || '').replace(/^.*[:|]/, '').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  let side = null; const rest = [];
  for (const t of tokens) {
    if (t === 'left' || t === 'l') { side = side || 'L'; continue; }
    if (t === 'right' || t === 'r') { side = side || 'R'; continue; }
    if (NOISE.has(t) || /^\d+$/.test(t)) continue;
    rest.push(t.replace(/\d+$/, ''));
  }
  return { side, core: rest.join('') };
}
/** Match a model's skeleton to the mannequin's bones. Returns { map: {canonical: Object3D}, missing: [...] }. */
export function mapSkeleton(root) {
  const bones = []; root.traverse(o => { if (o.isBone) bones.push(o); });
  const pool = bones.length ? bones : (() => { const a = []; root.traverse(o => { if (o !== root && !o.isMesh) a.push(o); }); return a; })();
  // some exporters put the file's own name in front of every bone ("rp_nathan_animated_003_walking_hip"): drop it
  let pre = '';
  if (pool.length >= 8) {
    pre = pool[0].name || '';
    for (const o of pool) { const n = o.name || ''; let i = 0; while (i < pre.length && i < n.length && pre[i] === n[i]) i++; pre = pre.slice(0, i); if (!pre) break; }
    const cut = Math.max(pre.lastIndexOf('_'), pre.lastIndexOf(':'), pre.lastIndexOf('|'), pre.lastIndexOf('.'), pre.lastIndexOf(' '), pre.lastIndexOf('-'));
    pre = cut >= 0 ? pre.slice(0, cut + 1) : '';
  }
  const info = new Map(pool.map(o => [o, parseName((o.name || '').slice(pre.length))]));
  const depth = o => { let d = 0; while (o.parent) { d++; o = o.parent; } return d; };
  const find = (kind, side, under) => pool.filter(o => { const i = info.get(o); return KIND[kind].includes(i.core) && (side ? i.side === side : !i.side) && (!under || isUnder(o, under)); }).sort((a, b) => depth(a) - depth(b))[0] || null;
  const isUnder = (o, p) => { for (let x = o.parent; x; x = x.parent) if (x === p) return true; return false; };
  const map = {};
  map.hips = find('hips', null);
  map.head = find('head', null, map.hips);
  map.neck = find('neck', null, map.hips);
  // spine chain: the spine-like bones between the hips and the neck, in order
  const chain = []; if (map.neck && map.hips) for (let x = map.neck.parent; x && x !== map.hips; x = x.parent) chain.unshift(x);
  const spineish = chain.filter(o => /^(spine|waist|chest|upperchest|torso|abdomen|back)/.test(info.get(o)?.core || ''));
  const spineChain = spineish.length ? spineish : chain;
  map.spine = spineChain[0] || null; map.chest = spineChain[spineChain.length - 1] || null;
  if (map.spine === map.chest && spineChain.length === 1) map.chest = map.spine;
  for (const S of ['L', 'R']) {
    map['upperArm_' + S] = find('upperArm', S, map.hips);
    map['forearm_' + S] = find('forearm', S, map['upperArm_' + S] || map.hips);
    map['hand_' + S] = find('hand', S, map['forearm_' + S] || map.hips);
    map['thigh_' + S] = find('thigh', S, map.hips);
    map['shin_' + S] = find('shin', S, map['thigh_' + S] || map.hips);
    map['foot_' + S] = find('foot', S, map['shin_' + S] || map.hips);
  }
  const need = ['hips', 'spine', 'chest', 'neck', 'head', 'upperArm_L', 'forearm_L', 'hand_L', 'upperArm_R', 'forearm_R', 'hand_R', 'thigh_L', 'shin_L', 'foot_L', 'thigh_R', 'shin_R', 'foot_R'];
  const missing = need.filter(k => !map[k]);
  if (map.spine && map.spine === map.chest) { /* a one-bone spine still works: chest follows spine */ }
  return { map, missing };
}

/* ───────── fitting a model into character space ───────── */
const _v = new THREE.Vector3(), _w = new THREE.Vector3();
function poseBind(root) { root.traverse(o => { if (o.isSkinnedMesh && o.skeleton) o.skeleton.pose(); }); root.updateMatrixWorld(true); }
/**
 * Put a model on its feet in character space: up is +Y, its left is +X, it faces +Z, real-world scale in meters,
 * feet on y = 0, centred on x = z = 0. Returns a wrapper group to add to the character.
 */
export function fitModel(model, map, humanoid = true) {
  const wrap = new THREE.Group(); wrap.name = 'look'; wrap.add(model);
  poseBind(model);
  if (map && map.hips && map.head && map.thigh_L && map.thigh_R) {
    const p = o => o.getWorldPosition(new THREE.Vector3());
    const up = p(map.head).sub(p(map.hips)).normalize(), left = p(map.thigh_L).sub(p(map.thigh_R));
    left.addScaledVector(up, -left.dot(up)).normalize();
    if (left.lengthSq() > 0.5) {
      const fwd = new THREE.Vector3().crossVectors(left, up);
      const basis = new THREE.Matrix4().makeBasis(left, up, fwd);   // model axes in world
      model.quaternion.premultiply(new THREE.Quaternion().setFromRotationMatrix(basis).invert());
      wrap.updateMatrixWorld(true);
    }
  }
  const box = new THREE.Box3().setFromObject(model, true);
  let h = box.max.y - box.min.y, s = 1;
  if (!(h > 0)) h = 1;
  if (humanoid) { if (h >= 1.0 && h <= 2.5) s = 1; else if (h >= 100 && h <= 250) s = 0.01; else if (h >= 10 && h <= 25) s = 0.1; else s = 1.75 / h; }
  else { if (h > 30) s = h / 100 <= 30 ? 0.01 : 2 / h; else if (h < 0.02) s = 1 / h; }
  wrap.scale.setScalar(s); wrap.updateMatrixWorld(true);
  box.setFromObject(model, true);
  const c = box.getCenter(_v);
  wrap.position.set(-c.x, -box.min.y, -c.z); wrap.updateMatrixWorld(true);
  return wrap;
}
/** Mannequin proportions that match a fitted model, so posing and reach line up with the real body. */
export function measureFit(map, toChar) {
  const P = k => toChar(map[k].getWorldPosition(new THREE.Vector3()));
  const d = (a, b) => P(a).distanceTo(P(b)), avg = (f) => (f('L') + f('R')) / 2;
  const hips = P('hips'), chest = P('chest');
  const r3 = v => Math.round(v * 1000) / 1000;
  const fit = {
    hipY: hips.y,
    spine: Math.max(0.04, d('hips', 'spine')), chest: Math.max(0.04, d('spine', 'chest')), neck: Math.max(0.04, d('chest', 'neck')), head: Math.max(0.03, d('neck', 'head')),
    shoulderX: avg(S => Math.abs(P('upperArm_' + S).x - chest.x)), shoulderY: avg(S => P('upperArm_' + S).y - chest.y),
    upper: avg(S => d('upperArm_' + S, 'forearm_' + S)), fore: avg(S => d('forearm_' + S, 'hand_' + S)),
    hipX: avg(S => Math.abs(P('thigh_' + S).x - hips.x)), hipYoff: avg(S => P('thigh_' + S).y - hips.y),
    thigh: avg(S => d('thigh_' + S, 'shin_' + S)), shin: avg(S => d('shin_' + S, 'foot_' + S))
  };
  if (map.spine === map.chest) { fit.chest = Math.max(0.04, fit.spine * 0.5); fit.spine *= 0.5; }
  for (const k in fit) fit[k] = r3(fit[k]);
  return fit;
}
export { poseBind };
