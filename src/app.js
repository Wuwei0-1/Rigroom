// Rigroom core: viewport, stage, posing, timeline, agent tools.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export const SKETCH_URL = './assets/sketch.jpg', SKETCH_ASPECT = 1.6364;
const $ = s => document.querySelector(s);
const DEG = Math.PI / 180;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
const V3 = THREE.Vector3, Q4 = THREE.Quaternion;
const num3 = (a, d) => Array.isArray(a) && a.length === 3 && a.every(v => isFinite(v)) ? a.map(Number) : d;
const isHex = c => /^#[0-9a-f]{6}$/i.test(c || '');

let toastTimer = null;
export function toast(msg, bad) {
  const t = $('#toast'); t.textContent = msg; t.classList.toggle('bad', !!bad); t.style.display = 'block';
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.style.display = 'none'; }, bad ? 5200 : 2800);
}

/* ───────── viewport ───────── */
const view = $('#view'), frameEl = $('#frame'), refEl = $('#ref');
let renderer;
try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
catch (e) { $('#hint').textContent = 'This device could not start WebGL, so the viewport cannot draw.'; throw e; }
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
frameEl.insertBefore(renderer.domElement, refEl);
const canvas = renderer.domElement;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x3a3d44);
const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 200);
camera.position.set(1.7, 1.45, 4.4);
// image-based lighting: surfaces pick up soft light and reflections from a studio room
try { const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; pm.dispose(); } catch (e) { /* no IBL */ }
const look = { exposure: 1, sunAngle: 35, sunHeight: 55, sunPower: 2, env: 0.6 };
const hemi = new THREE.HemisphereLight(0xffffff, 0x3c3f48, scene.environment ? 0.15 : 0.8); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff4e6, 1.2); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: .5, far: 30 }); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03;
scene.add(sun);
function applyLook() {
  renderer.toneMappingExposure = look.exposure;
  const a = look.sunAngle * DEG, h = look.sunHeight * DEG, d = 9;
  sun.position.set(Math.sin(a) * Math.cos(h) * d, Math.sin(h) * d, Math.cos(a) * Math.cos(h) * d); sun.intensity = look.sunPower;
  if (scene.environment) scene.environmentIntensity = look.env; hemi.intensity = scene.environment ? 0.15 * look.env : 0.8 * look.env;
  $('#exposure').value = Math.round(look.exposure * 100); $('#exposureV').textContent = look.exposure.toFixed(2);
  $('#sunAngle').value = look.sunAngle; $('#sunAngleV').textContent = Math.round(look.sunAngle) + '°';
  $('#sunHeight').value = look.sunHeight; $('#sunHeightV').textContent = Math.round(look.sunHeight) + '°';
  $('#sunPower').value = Math.round(look.sunPower * 100); $('#sunPowerV').textContent = look.sunPower.toFixed(1);
  $('#envPower').value = Math.round(look.env * 100); $('#envPowerV').textContent = look.env.toFixed(1);
}
const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({ color: 0x6b6e76, roughness: .92 })); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const grid = new THREE.GridHelper(12, 24, 0x565961, 0x4f525a); grid.position.y = 0.002; scene.add(grid);

const orbit = new OrbitControls(camera, canvas);
orbit.target.set(0, 0.95, 0); orbit.enableDamping = true; orbit.dampingFactor = 0.12; orbit.minDistance = 0.3; orbit.maxDistance = 60;
const tc = new TransformControls(camera, canvas); tc.setSize(1.0); const tcHelper = tc.getHelper(); scene.add(tcHelper);
const stage = new THREE.Group(); scene.add(stage);
const handles = new THREE.Group(); scene.add(handles);
const ikTarget = new THREE.Object3D(); scene.add(ikTarget);
const HANDLE_GEO = new THREE.SphereGeometry(1, 14, 10);
let boneLines = null;

/* shot frame: free view fills the viewport, shot view locks the frame shape */
let shotView = false;
const ref = { kind: null, url: null, aspect: 16 / 9, opacity: .35 };
function layoutFrame() {
  const W = view.clientWidth || 1, H = view.clientHeight || 1; let w = W, h = H, x = 0, y = 0;
  if (shotView) { const a = ref.url ? ref.aspect : 16 / 9; if (W / H > a) { w = Math.round(H * a); x = Math.round((W - w) / 2); } else { h = Math.round(W / a); y = Math.round((H - h) / 2); } }
  Object.assign(frameEl.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px' });
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
  refEl.style.display = shotView && ref.url && ref.opacity > 0 && !tracing ? 'block' : 'none'; refEl.style.opacity = ref.opacity;
  drawTimeline();
}
new ResizeObserver(layoutFrame).observe(view);

/* ───────── stage entities ───────── */
const ents = [], graveyard = new Map();
let uid = 1, active = null, sel = null, mode = 'rotate';
const anim = { fps: 24, length: 48, loop: true, ease: 'spline' };
const camKeys = [];
let frame = 0, playing = false, autoKey = true, recording = null, tracing = null;

function uniqueName(base, skip) { let n = base || 'Object', i = 2; while (ents.some(e => e !== skip && e.name.toLowerCase() === n.toLowerCase())) n = base + ' ' + (i++); return n; }
function makeEnt(spec) {
  const e = { id: spec.id || ('e' + (uid++)), kind: spec.kind, name: spec.name, params: JSON.parse(JSON.stringify(spec.params || {})), group: new THREE.Group(), bones: [], byName: new Map(), tracks: {}, pins: new Map(), pos: [0, 0, 0], rot: [0, 0, 0], scale: 1 };
  const n = parseInt(String(e.id).slice(1), 10); if (isFinite(n)) uid = Math.max(uid, n + 1);
  if (e.params.rough == null) e.params.rough = .8; if (e.params.metal == null) e.params.metal = 0;
  e.group.userData.ent = e; stage.add(e.group);
  if (e.kind === 'mannequin') buildMannequin(e); else if (e.kind === 'prop') buildProp(e);
  return e;
}
function applyPlacement(e) { e.group.position.fromArray(e.pos); e.group.rotation.set(e.rot[0] * DEG, e.rot[1] * DEG, e.rot[2] * DEG, 'YXZ'); e.group.scale.setScalar(e.scale); }
function finalizeRig(e, objs) {
  e.group.updateMatrixWorld(true);
  const set = new Set(objs), used = new Set(), bones = [];
  for (const o of objs) { let nm = o.name || 'bone', base = nm, i = 2; while (used.has(nm)) nm = base + '_' + (i++); used.add(nm); o.userData.rigName = nm; }
  for (const o of objs) {
    let p = o.parent; while (p && !set.has(p)) p = p.parent;
    bones.push({ ent: e, name: o.userData.rigName, obj: o, parent: p ? p.userData.rigName : null, isRoot: !p, depth: 0, dir: null,
      restQ: o.quaternion.clone(), restP: o.position.clone(),
      parentRestWQ: o.parent.getWorldQuaternion(new Q4()), restWP: o.getWorldPosition(new V3()) });
  }
  e.bones = bones; e.byName = new Map(bones.map(b => [b.name, b]));
  for (const b of bones) { let d = 0, p = b.parent; while (p) { d++; p = e.byName.get(p).parent; } b.depth = d; }
  for (const b of bones) { const kid = bones.find(c => c.parent === b.name); if (kid) { const v = kid.restWP.clone().sub(b.restWP); if (v.length() > 1e-5) b.dir = v.normalize().toArray().map(r2); } }
  for (const b of bones) { const m = new THREE.Mesh(HANDLE_GEO, new THREE.MeshBasicMaterial({ color: 0xe3e6ec, depthTest: false, transparent: true, opacity: .8 })); m.renderOrder = 20; m.visible = false; b.handle = m; handles.add(m); }
}
function buildMannequin(e) {
  const mat = () => new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: e.params.rough, metalness: e.params.metal });
  const M = { MID: mat(), LEFT: mat(), RIGHT: mat(), DARK: mat() }; e.mats = M; tintMannequin(e);
  const Y = new V3(0, 1, 0), sh = me => { me.castShadow = true; me.receiveShadow = true; return me; };
  const seg = (bone, tip, r, m) => { const v = new V3(...tip), len = v.length(); const me = sh(new THREE.Mesh(new THREE.CapsuleGeometry(r, Math.max(0.001, len - r * 0.6), 6, 14), m));
    me.position.copy(v).multiplyScalar(.5); me.quaternion.setFromUnitVectors(Y, v.clone().normalize()); bone.add(me); };
  const blob = (bone, pos, scale, m) => { const me = sh(new THREE.Mesh(new THREE.SphereGeometry(1, 22, 16), m)); me.position.set(...pos); me.scale.set(...scale); bone.add(me); };
  const box = (bone, pos, size, m) => { const me = sh(new THREE.Mesh(new THREE.BoxGeometry(...size), m)); me.position.set(...pos); bone.add(me); };
  const B = {}, order = [];
  const add = (name, parent, pos) => { const b = new THREE.Bone(); b.name = name; b.position.set(...pos); (parent ? B[parent] : e.group).add(b); B[name] = b; order.push(b); };
  add('hips', null, [0, 0.96, 0]); blob(B.hips, [0, 0, 0], [.17, .11, .11], M.MID);
  add('spine', 'hips', [0, 0.12, 0]); blob(B.spine, [0, .08, 0], [.145, .14, .1], M.MID);
  add('chest', 'spine', [0, 0.18, 0]); blob(B.chest, [0, .1, 0], [.2, .16, .115], M.MID);
  add('neck', 'chest', [0, 0.22, 0]); seg(B.neck, [0, .08, 0], .042, M.MID);
  add('head', 'neck', [0, 0.08, 0]); blob(B.head, [0, .12, 0], [.1, .125, .11], M.MID); box(B.head, [0, .11, .105], [.03, .035, .04], M.DARK);
  for (const [S, sx, m] of [['L', 1, M.LEFT], ['R', -1, M.RIGHT]]) {
    add('upperArm_' + S, 'chest', [.2 * sx, .17, 0]); seg(B['upperArm_' + S], [.28 * sx, 0, 0], .046, m);
    add('forearm_' + S, 'upperArm_' + S, [.28 * sx, 0, 0]); seg(B['forearm_' + S], [.26 * sx, 0, 0], .038, m);
    add('hand_' + S, 'forearm_' + S, [.26 * sx, 0, 0]); box(B['hand_' + S], [.06 * sx, 0, 0], [.11, .03, .075], m);
  }
  for (const [S, sx, m] of [['L', 1, M.LEFT], ['R', -1, M.RIGHT]]) {
    add('thigh_' + S, 'hips', [.1 * sx, -.05, 0]); seg(B['thigh_' + S], [0, -.42, 0], .066, m);
    add('shin_' + S, 'thigh_' + S, [0, -.42, 0]); seg(B['shin_' + S], [0, -.42, 0], .05, m);
    add('foot_' + S, 'shin_' + S, [0, -.42, 0]); box(B['foot_' + S], [0, -.04, .07], [.09, .06, .23], m);
  }
  finalizeRig(e, order);
}
function tintMannequin(e) {
  const base = new THREE.Color(e.params.color || '#b4b9c4'), M = e.mats;
  M.MID.color.copy(base); M.LEFT.color.copy(base).lerp(new THREE.Color(0xe6a052), .3); M.RIGHT.color.copy(base).lerp(new THREE.Color(0x5a8fe6), .3); M.DARK.color.copy(base).lerp(new THREE.Color(0x15171c), .75);
  for (const m of Object.values(M)) { m.roughness = e.params.rough; m.metalness = e.params.metal; m.needsUpdate = true; }
}
function propMesh(e) {
  const p = e.params, s = num3(p.size, [.5, .5, .5]).map(v => Math.max(.005, v)); let geo;
  if (p.shape === 'cylinder') geo = new THREE.CylinderGeometry(.5, .5, 1, 36); else if (p.shape === 'sphere') geo = new THREE.SphereGeometry(.5, 28, 18); else geo = new THREE.BoxGeometry(1, 1, 1);
  const me = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: new THREE.Color(p.color || '#8d8f96'), roughness: p.rough, metalness: p.metal })); me.scale.set(s[0], s[1], s[2]); me.castShadow = true; me.receiveShadow = true; return me;
}
function buildProp(e) { const node = new THREE.Object3D(); node.name = 'object'; e.group.add(node); e.mesh = propMesh(e); node.add(e.mesh); finalizeRig(e, [node]); }
function refreshProp(e) { const node = e.bones[0].obj; node.remove(e.mesh); e.mesh.geometry.dispose(); e.mesh = propMesh(e); node.add(e.mesh); }
function applyMaterial(e) { if (e.kind === 'mannequin') tintMannequin(e); else if (e.kind === 'prop') refreshProp(e); }

export function addMannequin(o) { o = o || {}; const e = makeEnt({ kind: 'mannequin', name: uniqueName(o.name || 'Character'), params: { color: o.color || '#b4b9c4', rough: .8, metal: 0 } });
  e.pos = num3(o.pos, [0, 0, 0]); e.rot = [0, +o.facing || 0, 0]; e.scale = clamp(+o.scale || 1, .2, 5); applyPlacement(e); ents.push(e); return e; }
export function addProp(o) { o = o || {}; const e = makeEnt({ kind: 'prop', name: uniqueName(o.name || 'Prop'), params: { shape: ['box', 'cylinder', 'sphere'].includes(o.shape) ? o.shape : 'box', size: num3(o.size, [.5, .5, .5]), color: o.color || '#8d8f96', rough: o.rough ?? .85, metal: o.metal ?? 0 } });
  e.pos = num3(o.pos, [0, .25, 0]); e.rot = num3(o.rot, [0, 0, 0]); e.scale = 1; applyPlacement(e); ents.push(e); return e; }
function detach(e) { stage.remove(e.group); e.bones.forEach(b => handles.remove(b.handle)); if (sel && sel.ent === e) sel = null; if (e.kind === 'import') graveyard.set(e.id, e); }
function reattach(e) { stage.add(e.group); e.bones.forEach(b => handles.add(b.handle)); graveyard.delete(e.id); }
function removeEnt(e) { detach(e); const i = ents.indexOf(e); if (i >= 0) ents.splice(i, 1); if (active === e) setActive(ents.find(x => x.kind !== 'prop') || ents[0] || null); }

export function loadGLB(buf, fileName) {
  new GLTFLoader().parse(buf, '', gltf => {
    let e = null;
    try {
      pushUndo();
      e = makeEnt({ kind: 'import', name: uniqueName(fileName.replace(/\.[^.]+$/, '') || 'Model'), params: { file: fileName } });
      const fit = new THREE.Group(); e.group.add(fit); fit.add(gltf.scene); e.group.updateMatrixWorld(true);
      let objs = []; gltf.scene.traverse(o => { if (o.isBone) objs.push(o); if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } if (o.isSkinnedMesh) o.frustumCulled = false; });
      let note = '';
      if (!objs.length) { gltf.scene.traverse(o => { if (o !== gltf.scene && o.name && !o.isMesh && objs.length < 200) objs.push(o); });
        if (!objs.length) gltf.scene.traverse(o => { if (o !== gltf.scene && o.name && objs.length < 200) objs.push(o); });
        note = ' It has no skeleton, so its parts are used as bones.'; }
      if (!objs.length) throw new Error('nothing to animate in that file');
      const bb = new THREE.Box3(), v = new V3();
      if (objs.length >= 3 && !note) objs.forEach(o => bb.expandByPoint(o.getWorldPosition(v))); else bb.setFromObject(gltf.scene);
      const size = bb.getSize(new V3()), c = bb.getCenter(new V3()), s = size.y > 1e-6 ? 1.6 / size.y : 1;
      fit.scale.setScalar(s); fit.position.set(-c.x * s, -bb.min.y * s, -c.z * s);
      finalizeRig(e, objs); e.pos = [0, 0, 1.2]; applyPlacement(e); ents.push(e); setActive(e); changed(); refreshStageUI();
      toast('Loaded ' + fileName + '.' + note);
    } catch (err) { if (e) stage.remove(e.group); undoStack.pop(); updateUndoUI(); toast('Could not set up that model: ' + err.message, true); }
  }, () => toast('Could not read that file. Use a self-contained .glb without Draco compression.', true));
}

/* rotation convention shared by the sliders and the agent:
   [x,y,z] degrees about the character's own axes, relative to rest, in the parent's frame */
function eulerToLocal(b, rot) {
  const D = new Q4().setFromEuler(new THREE.Euler((+rot[0] || 0) * DEG, (+rot[1] || 0) * DEG, (+rot[2] || 0) * DEG, 'XYZ'));
  return b.parentRestWQ.clone().invert().multiply(D).multiply(b.parentRestWQ).multiply(b.restQ);
}
function localToEuler(b, q) {
  const D = b.parentRestWQ.clone().multiply(q).multiply(b.restQ.clone().invert()).multiply(b.parentRestWQ.clone().invert());
  const e = new THREE.Euler().setFromQuaternion(D, 'XYZ'); return [e.x / DEG, e.y / DEG, e.z / DEG];
}
function relMatrix(b) { const par = b.obj.parent; b.ent.group.updateWorldMatrix(true, false); par.updateWorldMatrix(true, false); return new THREE.Matrix4().copy(b.ent.group.matrixWorld).invert().multiply(par.matrixWorld); }
function offsetToLocalPos(b, off) { const Mi = relMatrix(b).invert(); const o = new V3().applyMatrix4(Mi); return b.restP.clone().add(new V3(+off[0] || 0, +off[1] || 0, +off[2] || 0).applyMatrix4(Mi).sub(o)); }
function localPosToOffset(b, p) { const M = relMatrix(b); return new V3(...p).applyMatrix4(M).sub(b.restP.clone().applyMatrix4(M)).toArray(); }

/* ───────── reach (two-bone IK) ───────── */
function chainOf(b) { const p = b.parent && b.ent.byName.get(b.parent), g = p && p.parent && b.ent.byName.get(p.parent); return p && g ? [g, p] : null; }
function rotateWorld(obj, R) { const pw = obj.parent.getWorldQuaternion(new Q4()), w = obj.getWorldQuaternion(new Q4()); obj.quaternion.copy(pw.invert().multiply(R).multiply(w)); obj.updateWorldMatrix(false, true); }
function defaultPole(A) { const leg = A.dir && A.dir[1] < -0.7, side = Math.sign(A.restWP.x) || 1;
  const v = leg ? new V3(.1 * side, 0, 1) : new V3(.35 * side, -.6, -.7); return v.applyQuaternion(A.ent.group.getWorldQuaternion(new Q4())).normalize(); }
export function reach(b, target, pole, keepBend) {
  const ch = chainOf(b); if (!ch) return null; const [A, B] = ch;
  b.ent.group.updateWorldMatrix(true, true);
  const a = A.obj.getWorldPosition(new V3()), m = B.obj.getWorldPosition(new V3()), c = b.obj.getWorldPosition(new V3());
  const l1 = a.distanceTo(m), l2 = m.distanceTo(c); if (l1 < 1e-6 || l2 < 1e-6) return ch;
  const d = target.clone().sub(a); let dist = d.length(); if (dist < 1e-6) return ch; d.divideScalar(dist);
  dist = clamp(dist, Math.abs(l1 - l2) + 1e-4, l1 + l2 - 1e-4);
  let h = null; const orth = v => v.addScaledVector(d, -v.dot(d));
  if (pole) h = orth(pole.clone());
  if ((!h || h.lengthSq() < 1e-6) && keepBend) { h = orth(m.clone().sub(a)); if (h.length() < 0.06 * l1) h = null; }
  if (!h || h.lengthSq() < 1e-6) h = orth(defaultPole(A));
  if (h.lengthSq() < 1e-6) h = orth(new V3(0, 1, 0)); if (h.lengthSq() < 1e-6) h = orth(new V3(1, 0, 0));
  h.normalize();
  const cosA = clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1, 1), sinA = Math.sqrt(Math.max(0, 1 - cosA * cosA));
  const elbow = a.clone().addScaledVector(d, l1 * cosA).addScaledVector(h, l1 * sinA), end = a.clone().addScaledVector(d, dist);
  rotateWorld(A.obj, new Q4().setFromUnitVectors(m.sub(a).normalize(), elbow.clone().sub(a).normalize()));
  const m2 = B.obj.getWorldPosition(new V3()), c2 = b.obj.getWorldPosition(new V3());
  rotateWorld(B.obj, new Q4().setFromUnitVectors(c2.sub(m2).normalize(), end.sub(m2).normalize()));
  return ch;
}
function solvePins(e, edited) { for (const [name, t] of e.pins) { const b = e.byName.get(name); if (!b) continue; const ch = reach(b, t, null, true); if (ch && edited) ch.forEach(x => edited.add(x)); } }

/* ───────── animation data ───────── */
const undoStack = [], redoStack = [];
function setKey(e, name, f, q, p) {
  const tr = e.tracks[name] || (e.tracks[name] = []);
  const k = { f, q: q.toArray ? q.toArray() : q, p: p ? (p.toArray ? p.toArray() : p) : null };
  const i = tr.findIndex(x => x.f >= f);
  if (i < 0) tr.push(k); else if (tr[i].f === f) tr[i] = k; else tr.splice(i, 0, k);
}
export function keyCurrent(b, f) { setKey(b.ent, b.name, f, b.obj.quaternion, b.isRoot ? b.obj.position : null); }
function removeKey(e, name, f) { const tr = e.tracks[name]; if (!tr) return 0; const i = tr.findIndex(x => x.f === f); if (i < 0) return 0; tr.splice(i, 1); if (!tr.length) delete e.tracks[name]; return 1; }

const qa = new Q4(), qb = new Q4();
const dot4 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
const align = (q, r) => dot4(q, r) < 0 ? [-q[0], -q[1], -q[2], -q[3]] : q;
function poseKey(b, k) { b.obj.quaternion.fromArray(k.q); if (k.p) b.obj.position.fromArray(k.p); }
function evalTrack(b, tr, f) {
  const n = tr.length;
  if (n === 1 || f <= tr[0].f) return poseKey(b, tr[0]);
  if (f >= tr[n - 1].f) return poseKey(b, tr[n - 1]);
  let lo = 0, hi = n - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (tr[m].f <= f) lo = m; else hi = m; }
  const a = tr[lo], c = tr[lo + 1], span = c.f - a.f, t = (f - a.f) / span;
  if (anim.ease !== 'spline') {
    const u = anim.ease === 'ease' ? t * t * (3 - 2 * t) : t;
    qa.fromArray(a.q); qb.fromArray(c.q); b.obj.quaternion.slerpQuaternions(qa, qb, u);
    if (a.p && c.p) b.obj.position.set(a.p[0] + (c.p[0] - a.p[0]) * u, a.p[1] + (c.p[1] - a.p[1]) * u, a.p[2] + (c.p[2] - a.p[2]) * u);
    return;
  }
  // Hermite spline through the keys; a loop whose first and last keys match wraps its tangents
  const cyc = anim.loop && n > 2 && tr[0].f === 0 && tr[n - 1].f === anim.length && Math.abs(dot4(tr[0].q, tr[n - 1].q)) > 0.9995;
  let pv = null, pf = 0, nx = null, nf = 0;
  if (lo > 0) { pv = tr[lo - 1]; pf = pv.f; } else if (cyc) { pv = tr[n - 2]; pf = pv.f - anim.length; }
  if (lo + 2 < n) { nx = tr[lo + 2]; nf = nx.f; } else if (cyc) { nx = tr[1]; nf = nx.f + anim.length; }
  const t2 = t * t, t3 = t2 * t, h00 = 2 * t3 - 3 * t2 + 1, h10 = t3 - 2 * t2 + t, h01 = -2 * t3 + 3 * t2, h11 = t3 - t2;
  const q1 = a.q, q2 = align(c.q, q1), q0 = pv ? align(pv.q, q1) : null, q3 = nx ? align(nx.q, q2) : null, out = [0, 0, 0, 0];
  for (let i = 0; i < 4; i++) { const m1 = q0 ? (q2[i] - q0[i]) / (c.f - pf) * span : 0, m2 = q3 ? (q3[i] - q1[i]) / (nf - a.f) * span : 0; out[i] = h00 * q1[i] + h10 * m1 + h01 * q2[i] + h11 * m2; }
  b.obj.quaternion.fromArray(out).normalize();
  if (a.p && c.p) { const o = [0, 0, 0];
    for (let i = 0; i < 3; i++) { const m1 = pv && pv.p ? (c.p[i] - pv.p[i]) / (c.f - pf) * span : 0, m2 = nx && nx.p ? (nx.p[i] - a.p[i]) / (nf - a.f) * span : 0; o[i] = h00 * a.p[i] + h10 * m1 + h01 * c.p[i] + h11 * m2; }
    b.obj.position.fromArray(o); }
}
export function evaluateEnt(e, f) { for (const b of e.bones) { const tr = e.tracks[b.name]; if (tr && tr.length) evalTrack(b, tr, f); } }
function evaluate(f) { for (const e of ents) evaluateEnt(e, f); }
export function applyFrame(f) { frame = f; evaluate(f); updateFrameUI(); }
function restEnt(e) { for (const b of e.bones) { b.obj.quaternion.copy(b.restQ); b.obj.position.copy(b.restP); } }

/* scene <-> JSON */
function specOf(e) { return { id: e.id, kind: e.kind, name: e.name, params: e.params, pos: e.pos, rot: e.rot, scale: e.scale, tracks: e.tracks }; }
export function sceneJSON(withImports) { return { app: 'rigroom', v: 3, fps: anim.fps, length: anim.length, loop: anim.loop, ease: anim.ease, cam: camKeys, look: { ...look }, ref: ref.kind === 'sketch' ? 'sketch' : null, ents: ents.filter(e => withImports || e.kind !== 'import').map(specOf) }; }
function cleanTracks(e, tracks) { const out = {};
  for (const [name, tr] of Object.entries(tracks || {})) { if (!e.byName.has(name) || !Array.isArray(tr)) continue;
    const t = tr.filter(k => k && Array.isArray(k.q) && k.q.length === 4 && isFinite(k.f)).map(k => ({ f: Math.round(k.f), q: k.q.map(Number), p: Array.isArray(k.p) ? k.p.map(Number) : null })).sort((a, b) => a.f - b.f);
    if (t.length) out[name] = t; }
  return out; }
function applyScene(o, reuse) {
  anim.fps = clamp(+o.fps || 24, 1, 60); anim.length = clamp(Math.round(+o.length || 48), 1, 2000); anim.loop = o.loop !== false; anim.ease = ['spline', 'ease', 'linear'].includes(o.ease) ? o.ease : 'spline';
  camKeys.length = 0; for (const k of (Array.isArray(o.cam) ? o.cam : [])) if (k && num3(k.p) && num3(k.t) && isFinite(k.f)) camKeys.push({ f: Math.round(k.f), p: k.p.map(Number), t: k.t.map(Number), fov: clamp(+k.fov || 35, 10, 90) });
  camKeys.sort((a, b) => a.f - b.f);
  if (o.look) { for (const k of Object.keys(look)) if (isFinite(o.look[k])) look[k] = +o.look[k]; } applyLook();
  const keep = new Map(ents.map(e => [e.id, e])), next = []; let skipped = 0;
  for (const s of (Array.isArray(o.ents) ? o.ents : [])) {
    if (!s || !['mannequin', 'prop', 'import'].includes(s.kind)) continue;
    let e = reuse ? (keep.get(s.id) || graveyard.get(s.id)) : null;
    if (e && e.kind === s.kind && (e.kind === 'import' || JSON.stringify(e.params) === JSON.stringify(s.params))) { if (keep.has(s.id)) keep.delete(s.id); else reattach(e); }
    else if (s.kind !== 'import') { ents.length = 0; ents.push(...next, ...keep.values()); e = makeEnt({ id: reuse ? s.id : null, kind: s.kind, name: String(s.name || 'Object'), params: s.params }); }
    else { skipped++; continue; }
    e.name = String(s.name || e.name).slice(0, 40); e.pos = num3(s.pos, [0, 0, 0]); e.rot = num3(s.rot, [0, 0, 0]); e.scale = clamp(+s.scale || 1, .05, 20); applyPlacement(e);
    e.tracks = cleanTracks(e, s.tracks); next.push(e);
  }
  for (const e of keep.values()) detach(e);
  ents.length = 0; ents.push(...next);
  if (o.ref === 'sketch') setRef('sketch', SKETCH_URL, SKETCH_ASPECT); else if (!reuse) setRef(null, null, 16 / 9);
  return skipped;
}
function snapshot() {
  const poses = {}; for (const e of ents) { const p = poses[e.id] = {}; for (const b of e.bones) p[b.name] = [...b.obj.quaternion.toArray(), ...b.obj.position.toArray()]; }
  return JSON.stringify({ scene: sceneJSON(true), poses, active: active && active.id, sel: sel && sel.name });
}
function restoreSnap(s) {
  const o = JSON.parse(s); applyScene(o.scene, true);
  for (const e of ents) { const p = o.poses[e.id]; for (const b of e.bones) { const v = p && p[b.name]; if (v) { b.obj.quaternion.fromArray(v); b.obj.position.fromArray(v, 4); } else { b.obj.quaternion.copy(b.restQ); b.obj.position.copy(b.restP); } } }
  const a = ents.find(e => e.id === o.active) || ents[0] || null; sel = null; setActive(a); if (a && o.sel && a.byName.has(o.sel)) select(a.byName.get(o.sel));
  frame = clamp(frame, 0, anim.length); applyFrame(frame); syncUI(); changed();
}
export function pushUndo() { undoStack.push(snapshot()); if (undoStack.length > 40) undoStack.shift(); redoStack.length = 0; updateUndoUI(); }
function updateUndoUI() { $('#undo').disabled = !undoStack.length; $('#redo').disabled = !redoStack.length; }
$('#undo').onclick = () => { if (!undoStack.length) return; pause(); redoStack.push(snapshot()); restoreSnap(undoStack.pop()); updateUndoUI(); };
$('#redo').onclick = () => { if (!redoStack.length) return; pause(); undoStack.push(snapshot()); restoreSnap(redoStack.pop()); updateUndoUI(); };

let saveTimer = null;
export function changed() {
  drawTimeline(); markKeyed(); refreshSliders(); refreshHeader();
  clearTimeout(saveTimer); saveTimer = setTimeout(() => { try { localStorage.setItem('rigroom.v3', JSON.stringify(sceneJSON(false))); } catch (e) { /* storage unavailable */ } }, 700);
}
export function loadSceneObject(o) {
  if (!o || o.app !== 'rigroom') throw new Error('not a Rigroom project');
  if (!o.v || o.v < 2) o = { app: 'rigroom', v: 3, fps: o.fps, length: o.length, loop: o.loop, ease: o.ease, cam: [], ents: [{ kind: 'mannequin', name: 'Character', params: { color: '#b4b9c4' }, pos: [0, 0, 0], rot: [0, 0, 0], scale: 1, tracks: o.tracks }] };
  playing = false; [...ents].forEach(detach); ents.length = 0; graveyard.clear(); active = null; sel = null;
  const skipped = applyScene(o, false);
  setActive(ents.find(e => e.kind !== 'prop') || ents[0] || null); applyFrame(0); frameCameraToShot(); syncUI(); changed(); setPlayIcon(); return skipped;
}
export function clearStage() { playing = false; [...ents].forEach(detach); ents.length = 0; graveyard.clear(); active = null; sel = null; camKeys.length = 0; }

/* ───────── selection and posing ───────── */
export function setActive(e) {
  active = e || null; if (sel && sel.ent !== active) sel = null;
  if (boneLines) { scene.remove(boneLines); boneLines.geometry.dispose(); boneLines = null; }
  if (active) { const lg = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(Math.max(1, active.bones.length) * 6), 3));
    boneLines = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0xe3e6ec, depthTest: false, transparent: true, opacity: .45 })); boneLines.renderOrder = 19; boneLines.frustumCulled = false; boneLines.visible = handles.visible; scene.add(boneLines); }
  buildBoneList(); refreshStageUI(); select(sel);
}
export function select(b) {
  if (b && b.ent !== active) { sel = b; setActive(b.ent); return; }
  sel = b || null;
  if (sel) { if (mode === 'move' && !sel.isRoot) mode = 'rotate'; if (mode === 'reach' && !chainOf(sel)) mode = 'rotate'; }
  updateGizmo();
  const chip = $('#selChip'); chip.textContent = active ? (active.name + (sel && active.bones.length > 1 ? ' › ' + sel.name : '')) : 'Nothing selected'; chip.classList.toggle('none', !active);
  document.querySelectorAll('#boneList .item').forEach(el => el.classList.toggle('on', !!sel && el.dataset.name === sel.name));
  const pinned = !!(sel && sel.ent.pins.has(sel.name)); $('#pinBtn').disabled = !sel || !chainOf(sel); $('#pinBtn').classList.toggle('on', pinned); $('#pinBtn').textContent = pinned ? 'Unpin' : 'Pin in place';
  refreshSliders(); drawTimeline();
}
function updateGizmo() {
  tc.detach();
  for (const m of ['rotate', 'move', 'reach', 'place']) $('#mode-' + m).classList.toggle('on', mode === m);
  $('#mode-rotate').disabled = !sel; $('#mode-move').disabled = !sel || !sel.isRoot; $('#mode-reach').disabled = !sel || !chainOf(sel); $('#mode-place').disabled = !active;
  if (mode === 'place') { if (active) { tc.setMode('translate'); tc.setSpace('world'); tc.attach(active.group); } return; }
  if (!sel) return;
  if (mode === 'rotate') { tc.setMode('rotate'); tc.setSpace('local'); tc.attach(sel.obj); }
  else if (mode === 'move') { tc.setMode('translate'); tc.setSpace('world'); tc.attach(sel.obj); }
  else if (mode === 'reach') { sel.obj.getWorldPosition(ikTarget.position); tc.setMode('translate'); tc.setSpace('world'); tc.attach(ikTarget); }
}
export function setMode(m) { mode = m; if (sel) { if (m === 'move' && !sel.isRoot) mode = 'rotate'; if (m === 'reach' && !chainOf(sel)) mode = 'rotate'; } updateGizmo(); }
for (const m of ['rotate', 'move', 'reach', 'place']) $('#mode-' + m).onclick = () => setMode(m);

function afterManualEdit(bones) { if (autoKey) { const f = Math.round(frame); bones.forEach(b => keyCurrent(b, f)); } changed(); }
let dragBones = null;
tc.addEventListener('dragging-changed', e => {
  orbit.enabled = !e.value && !shotView;
  if (e.value) { pause(); frame = Math.round(frame); pushUndo(); dragBones = new Set(); }
  else {
    if (mode === 'place' && active) { active.pos = active.group.position.toArray().map(v => Math.round(v * 1000) / 1000); changed(); refreshStageUI(); }
    else if (dragBones) afterManualEdit([...dragBones]);
    dragBones = null;
  }
});
tc.addEventListener('change', () => {
  if (!tc.dragging || !dragBones || mode === 'place' || !sel) return;
  if (mode === 'reach') { const ch = reach(sel, ikTarget.position, null, true); if (ch) ch.forEach(b => dragBones.add(b)); if (sel.ent.pins.has(sel.name)) sel.ent.pins.set(sel.name, ikTarget.position.clone()); }
  else { dragBones.add(sel); solvePins(sel.ent, dragBones); }
  refreshSliders();
});

// tap: a joint of the active character first, otherwise whatever is under the finger
let down = null; const pv3 = new V3(), ray = new THREE.Raycaster();
function nearestBone(e, x, y, limit) { const r = canvas.getBoundingClientRect(); let best = null, bd = limit;
  for (const b of e.bones) { b.obj.getWorldPosition(pv3).project(camera); if (pv3.z > 1) continue;
    const d = Math.hypot((pv3.x * .5 + .5) * r.width + r.left - x, (-pv3.y * .5 + .5) * r.height + r.top - y); if (d < bd) { bd = d; best = b; } }
  return best; }
canvas.addEventListener('pointerdown', e => { down = (tc.axis || tc.dragging) ? null : { x: e.clientX, y: e.clientY, t: performance.now() }; });
canvas.addEventListener('pointerup', e => {
  if (!down || tc.dragging || tracing) return; const d = down; down = null;
  if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 8 || performance.now() - d.t > 450) return;
  if (active && handles.visible && active.bones.length > 1) { const b = nearestBone(active, e.clientX, e.clientY, 34); if (b) return select(b); }
  const r = canvas.getBoundingClientRect(); ray.setFromCamera({ x: (e.clientX - r.left) / r.width * 2 - 1, y: -((e.clientY - r.top) / r.height) * 2 + 1 }, camera);
  const hit = ray.intersectObjects(stage.children, true)[0];
  if (!hit) return select(null);
  let o = hit.object; while (o && !o.userData.ent) o = o.parent; if (!o) return;
  const ent = o.userData.ent; select(nearestBone(ent, e.clientX, e.clientY, 1e9) || ent.bones[0] || null);
});

/* pose pane */
function buildBoneList() {
  const list = $('#boneList'); list.textContent = '';
  if (!active) return;
  for (const b of active.bones) {
    const el = document.createElement('button'); el.className = 'item'; el.dataset.name = b.name; el.style.paddingLeft = (8 + Math.min(b.depth, 8) * 12) + 'px';
    el.append(document.createElement('i'), document.createTextNode(b.name)); el.onclick = () => select(b); list.append(el);
  }
  markKeyed();
}
function markKeyed() { document.querySelectorAll('#boneList .item').forEach(el => el.classList.toggle('keyed', !!(active && active.tracks[el.dataset.name]))); }
const sliders = ['rx', 'ry', 'rz'].map(id => $('#' + id)); let sliding = false;
function refreshSliders() {
  if (sliding) return;
  const e = sel ? localToEuler(sel, sel.obj.quaternion) : [0, 0, 0];
  sliders.forEach((s, i) => { s.disabled = !sel; s.value = Math.round(e[i]); $('#' + s.id + 'v').textContent = Math.round(e[i]) + '°'; });
}
sliders.forEach(s => {
  const begin = () => { if (sel && !sliding) { sliding = true; pause(); frame = Math.round(frame); pushUndo(); dragBones = new Set(); } };
  s.addEventListener('pointerdown', begin);
  s.addEventListener('input', () => { if (!sel) return; begin();
    sel.obj.quaternion.copy(eulerToLocal(sel, sliders.map(x => +x.value))); dragBones.add(sel); solvePins(sel.ent, dragBones); $('#' + s.id + 'v').textContent = s.value + '°'; });
  s.addEventListener('change', () => { sliding = false; if (sel && dragBones) afterManualEdit([...dragBones]); dragBones = null; });
});
$('#pinBtn').onclick = () => { if (!sel || !chainOf(sel)) return; const p = sel.ent.pins;
  if (p.has(sel.name)) { p.delete(sel.name); toast(sel.name + ' unpinned.'); } else { p.set(sel.name, sel.obj.getWorldPosition(new V3())); toast(sel.name + ' pinned. Pose the body and it stays put.'); }
  select(sel); };
$('#resetBone').onclick = () => { if (!sel) return toast('Select a bone first.'); pause(); pushUndo(); sel.obj.quaternion.copy(sel.restQ); sel.obj.position.copy(sel.restP); afterManualEdit([sel]); };
$('#restPose').onclick = () => { if (!active) return; pushUndo(); pause(); restEnt(active); changed(); toast('Rest pose. Press Key pose to keep it on this frame.'); };

/* stage pane */
function refreshHeader() { const c = ents.filter(e => e.kind !== 'prop').length, p = ents.length - c; $('#rigName').textContent = c + ' character' + (c === 1 ? '' : 's') + ' · ' + p + ' prop' + (p === 1 ? '' : 's'); }
export function refreshStageUI() {
  const list = $('#entList'); list.textContent = '';
  for (const e of ents) { const el = document.createElement('button'); el.className = 'item' + (e === active ? ' on' : '') + (Object.keys(e.tracks).length ? ' keyed' : '');
    const sm = document.createElement('small'); sm.textContent = e.kind === 'prop' ? e.params.shape : (e.kind === 'import' ? 'model' : 'character');
    el.append(document.createElement('i'), document.createTextNode(e.name), sm); el.onclick = () => { setActive(e); if (e.bones.length === 1) select(e.bones[0]); }; list.append(el); }
  const ed = $('#entEdit'); ed.style.display = active ? 'flex' : 'none'; if (!active) return;
  $('#entName').value = active.name; $('#entFacing').value = Math.round(active.rot[1]); $('#entFacingV').textContent = Math.round(active.rot[1]) + '°';
  $('#entSize').value = Math.round(active.scale * 100); $('#entSizeV').textContent = Math.round(active.scale * 100) + '%';
  const isProp = active.kind === 'prop', hasMat = active.kind !== 'import';
  $('#propSizeRow').style.display = isProp ? 'flex' : 'none'; for (const id of ['colorRow', 'matRow', 'matRow2']) $('#' + id).style.display = hasMat ? 'flex' : 'none';
  if (isProp) ['pw', 'ph', 'pd'].forEach((id, i) => $('#' + id).value = active.params.size[i]);
  if (hasMat) { $('#entColor').value = active.params.color; $('#matRough').value = Math.round(active.params.rough * 100); $('#matRoughV').textContent = Math.round(active.params.rough * 100) + '%'; $('#matMetal').value = Math.round(active.params.metal * 100); $('#matMetalV').textContent = Math.round(active.params.metal * 100) + '%'; }
  refreshHeader();
}
$('#entName').onchange = e => { if (!active) return; const v = e.target.value.trim(); if (!v) return refreshStageUI(); pushUndo(); active.name = uniqueName(v.slice(0, 40), active); refreshStageUI(); select(sel); changed(); };
let placing = false;
const placeBegin = () => { if (!placing) { placing = true; pushUndo(); } };
$('#entFacing').addEventListener('input', e => { if (!active) return; placeBegin(); active.rot[1] = +e.target.value; applyPlacement(active); $('#entFacingV').textContent = e.target.value + '°'; });
$('#entSize').addEventListener('input', e => { if (!active) return; placeBegin(); active.scale = +e.target.value / 100; applyPlacement(active); $('#entSizeV').textContent = e.target.value + '%'; });
$('#matRough').addEventListener('input', e => { if (!active || active.kind === 'import') return; placeBegin(); active.params.rough = +e.target.value / 100; applyMaterial(active); $('#matRoughV').textContent = e.target.value + '%'; });
$('#matMetal').addEventListener('input', e => { if (!active || active.kind === 'import') return; placeBegin(); active.params.metal = +e.target.value / 100; applyMaterial(active); $('#matMetalV').textContent = e.target.value + '%'; });
['entFacing', 'entSize', 'matRough', 'matMetal'].forEach(id => $('#' + id).addEventListener('change', () => { placing = false; changed(); }));
['pw', 'ph', 'pd'].forEach((id, i) => $('#' + id).onchange = e => { if (!active || active.kind !== 'prop') return; const v = clamp(+e.target.value || .1, .005, 50); pushUndo(); active.params.size[i] = v; refreshProp(active); changed(); });
$('#entColor').onchange = e => { if (!active || active.kind === 'import') return; pushUndo(); active.params.color = e.target.value; applyMaterial(active); changed(); };
const spot = () => { const t = orbit.target; return [r2(t.x), 0, r2(t.z)]; };
$('#addChar').onclick = () => { pushUndo(); const e = addMannequin({ pos: spot() }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); toast(e.name + ' added. Drag the arrows to place it.'); };
$('#addBox').onclick = () => { pushUndo(); const p = spot(); p[1] = .25; const e = addProp({ name: 'Box', shape: 'box', size: [.5, .5, .5], pos: p }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); };
$('#addCyl').onclick = () => { pushUndo(); const p = spot(); p[1] = .25; const e = addProp({ name: 'Cylinder', shape: 'cylinder', size: [.4, .5, .4], pos: p }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); };
$('#dupEnt').onclick = () => { if (!active) return; if (active.kind === 'import') return toast('Imported models cannot be duplicated yet. Import the file again.');
  pushUndo(); const s = JSON.parse(JSON.stringify(specOf(active))); const e = makeEnt({ kind: s.kind, name: uniqueName(s.name), params: s.params });
  e.pos = [s.pos[0] + .6, s.pos[1], s.pos[2]]; e.rot = s.rot; e.scale = s.scale; applyPlacement(e); e.tracks = cleanTracks(e, s.tracks); ents.push(e); setActive(e); applyFrame(frame); changed(); };
$('#delEnt').onclick = () => { if (!active) return; pushUndo(); const n = active.name; removeEnt(active); refreshStageUI(); changed(); toast(n + ' deleted. Undo brings it back.'); };
$('#importBtn').onclick = () => $('#fileGlb').click();
$('#fileGlb').onchange = async e => { const f = e.target.files[0]; e.target.value = ''; if (!f) return; try { loadGLB(await f.arrayBuffer(), f.name); } catch (err) { toast('Could not read that file.', true); } };

/* ───────── camera, look and reference ───────── */
function camAt(f) {
  if (!camKeys.length) return null; if (f <= camKeys[0].f) return camKeys[0]; const last = camKeys[camKeys.length - 1]; if (f >= last.f) return last;
  let i = 0; while (camKeys[i + 1].f <= f) i++; const a = camKeys[i], c = camKeys[i + 1]; let t = (f - a.f) / (c.f - a.f); t = t * t * (3 - 2 * t);
  const L = (x, y) => x + (y - x) * t; return { p: a.p.map((v, k) => L(v, c.p[k])), t: a.t.map((v, k) => L(v, c.t[k])), fov: L(a.fov, c.fov) };
}
function applyCam(k) { camera.position.fromArray(k.p); orbit.target.fromArray(k.t); camera.lookAt(orbit.target); if (Math.abs(camera.fov - k.fov) > 1e-3) { camera.fov = k.fov; camera.updateProjectionMatrix(); } }
export function frameCameraToShot() { const k = camAt(frame); if (k) { applyCam(k);
    // a tall, narrow free view backs the camera off so the whole shot still fits
    if (!shotView && camera.aspect < 1.6) { const d = camera.position.clone().sub(orbit.target); camera.position.copy(orbit.target).addScaledVector(d, Math.min(2.6, 1.6 / camera.aspect)); } }
  else { camera.position.set(1.7, 1.45, 4.4); orbit.target.set(0, .95, 0); camera.fov = 35; camera.updateProjectionMatrix(); } syncLens(); }
function syncLens() { $('#lens').value = Math.round(camera.fov); $('#lensV').textContent = Math.round(camera.fov) + '°'; }
export function setShot(on) { shotView = !!on; $('#shotView').checked = shotView; orbit.enabled = !shotView; $('#lens').disabled = shotView; layoutFrame(); }
$('#shotView').onchange = e => { if (e.target.checked && !camKeys.length) keyCamera(true); setShot(e.target.checked); toast(shotView ? 'Shot view: looking through the keyed camera.' : 'Free view.'); };
function keyCamera(quiet) { const f = Math.round(frame), k = { f, p: camera.position.toArray().map(v => Math.round(v * 1000) / 1000), t: orbit.target.toArray().map(v => Math.round(v * 1000) / 1000), fov: Math.round(camera.fov * 10) / 10 };
  const i = camKeys.findIndex(x => x.f >= f); if (i < 0) camKeys.push(k); else if (camKeys[i].f === f) camKeys[i] = k; else camKeys.splice(i, 0, k); if (!quiet) toast('Camera keyed at frame ' + f + '.'); changed(); }
$('#keyCam').onclick = () => { if (shotView) return toast('Turn off Shot view, frame the scene, then Key camera.'); pushUndo(); keyCamera(); };
$('#delCam').onclick = () => { const f = Math.round(frame), i = camKeys.findIndex(k => k.f === f); if (i < 0) return toast('No camera key on frame ' + f + '.'); pushUndo(); camKeys.splice(i, 1); if (!camKeys.length && shotView) setShot(false); changed(); toast('Camera key deleted.'); };
$('#lens').addEventListener('input', e => { camera.fov = +e.target.value; camera.updateProjectionMatrix(); $('#lensV').textContent = e.target.value + '°'; });
for (const [id, key, div] of [['exposure', 'exposure', 100], ['sunAngle', 'sunAngle', 1], ['sunHeight', 'sunHeight', 1], ['sunPower', 'sunPower', 100], ['envPower', 'env', 100]])
  $('#' + id).addEventListener('input', e => { look[key] = +e.target.value / div; applyLook(); changed(); });
export function setRef(kind, url, aspect) { if (ref.url && ref.kind === 'file' && ref.url !== url) { try { URL.revokeObjectURL(ref.url); } catch (e) { /* ignore */ } }
  ref.kind = kind; ref.url = url; ref.aspect = aspect || 16 / 9; if (url) refEl.src = url; else refEl.removeAttribute('src');
  $('#refNote').textContent = kind === 'sketch' ? 'Your booth sketch is loaded. It shows over the scene in Shot view.' : (url ? 'Shown over the scene in Shot view.' : 'No image loaded. Load a drawing to pose against it in Shot view.');
  $('#refClear').disabled = !url; layoutFrame(); }
$('#refOp').addEventListener('input', e => { ref.opacity = +e.target.value / 100; $('#refOpV').textContent = e.target.value + '%'; layoutFrame(); });
$('#refLoad').onclick = () => $('#fileRef').click();
$('#fileRef').onchange = e => { const f = e.target.files[0]; e.target.value = ''; if (!f) return; const url = URL.createObjectURL(f), im = new Image();
  im.onload = () => { setRef('file', url, im.naturalWidth / im.naturalHeight); if (!shotView) { if (!camKeys.length) keyCamera(true); setShot(true); } toast('Reference loaded. It shows in Shot view.'); };
  im.onerror = () => toast('That image could not be read.', true); im.src = url; };
$('#refClear').onclick = () => { setRef(null, null, 16 / 9); toast('Reference removed.'); };

/* ───────── timeline ───────── */
const tl = $('#tl'), tctx = tl.getContext('2d'); const PAD = 16;
const fx = (f, w) => PAD + f / anim.length * (w - 2 * PAD);
function drawTimeline() {
  const w = tl.clientWidth, h = tl.clientHeight; if (!w) return; const dpr = Math.min(window.devicePixelRatio || 1, 2);
  if (tl.width !== Math.round(w * dpr) || tl.height !== Math.round(h * dpr)) { tl.width = Math.round(w * dpr); tl.height = Math.round(h * dpr); }
  tctx.setTransform(dpr, 0, 0, dpr, 0, 0); tctx.clearRect(0, 0, w, h);
  const px = (w - 2 * PAD) / anim.length; let minor = 1; for (const s of [1, 2, 5, 10, 20, 50, 100, 200]) { minor = s; if (px * s >= 7) break; }
  let major = minor; for (const s of [5, 10, 20, 50, 100, 200, 500]) { major = s; if (px * s >= 44 && s % minor === 0) break; }
  tctx.font = '11px "IBM Plex Mono",monospace'; tctx.textBaseline = 'top';
  for (let f = 0; f <= anim.length; f += minor) { const x = Math.round(fx(f, w)) + .5, big = f % major === 0;
    tctx.strokeStyle = big ? '#5a606c' : '#3a3f49'; tctx.beginPath(); tctx.moveTo(x, big ? 18 : h - 14); tctx.lineTo(x, h - 4); tctx.stroke();
    if (big) { tctx.fillStyle = '#9da1ab'; tctx.fillText(String(f), x + 3, 4); } }
  const all = new Set(); for (const e of (active ? [active] : ents)) for (const tr of Object.values(e.tracks)) for (const k of tr) all.add(k.f);
  const selSet = new Set(sel && sel.ent.tracks[sel.name] ? sel.ent.tracks[sel.name].map(k => k.f) : []);
  const diamond = (x, y, r) => { tctx.beginPath(); tctx.moveTo(x, y - r); tctx.lineTo(x + r, y); tctx.lineTo(x, y + r); tctx.lineTo(x - r, y); tctx.closePath(); };
  const ky = h - 22;
  for (const f of all) { if (f > anim.length) continue; const x = fx(f, w);
    if (selSet.has(f) || !sel) { diamond(x, ky, 5.5); tctx.fillStyle = '#f0a23e'; tctx.fill(); } else { diamond(x, ky, 4.5); tctx.fillStyle = '#6a5a41'; tctx.fill(); } }
  tctx.fillStyle = '#7db6ff'; for (const k of camKeys) { if (k.f <= anim.length) tctx.fillRect(fx(k.f, w) - 3.5, h - 9, 7, 5); }
  const x = fx(Math.min(frame, anim.length), w);
  tctx.strokeStyle = '#7db6ff'; tctx.lineWidth = 2; tctx.beginPath(); tctx.moveTo(x, 2); tctx.lineTo(x, h - 2); tctx.stroke(); tctx.lineWidth = 1;
  tctx.fillStyle = '#7db6ff'; tctx.beginPath(); tctx.moveTo(x - 6, 0); tctx.lineTo(x + 6, 0); tctx.lineTo(x, 9); tctx.closePath(); tctx.fill();
}
function scrub(e) { const r = tl.getBoundingClientRect(); const f = clamp(Math.round((e.clientX - r.left - PAD) / (r.width - 2 * PAD) * anim.length), 0, anim.length); pause(); applyFrame(f); refreshSliders(); }
tl.addEventListener('pointerdown', e => { tl.setPointerCapture(e.pointerId); tl._drag = true; scrub(e); });
tl.addEventListener('pointermove', e => { if (tl._drag) scrub(e); });
tl.addEventListener('pointerup', () => { tl._drag = false; }); tl.addEventListener('pointercancel', () => { tl._drag = false; });

function updateFrameUI() { $('#frameNow').textContent = String(Math.floor(frame + 1e-6)).padStart(3, '0'); $('#frameLen').textContent = anim.length; drawTimeline(); }
export function setPlayIcon() { $('#playIcon').innerHTML = playing ? '<path d="M3 2h4v12H3zM9 2h4v12H9z"/>' : '<path d="M4 2l10 6-10 6z"/>'; $('#play').setAttribute('aria-label', playing ? 'Pause' : 'Play'); }
export function play() { if (tracing) return; if (frame >= anim.length) frame = 0; playing = true; lastT = performance.now(); setPlayIcon(); }
export function pause() { if (!playing) return; playing = false; applyFrame(Math.round(frame)); refreshSliders(); setPlayIcon(); if (recording) recording.finish(); }
$('#play').onclick = () => playing ? pause() : play();
function keyFrames() { const s = new Set(); const src = sel && sel.ent.tracks[sel.name] ? [sel.ent.tracks[sel.name]] : (active ? Object.values(active.tracks) : ents.flatMap(e => Object.values(e.tracks))); for (const tr of src) for (const k of tr) s.add(k.f); return [...s].sort((a, b) => a - b); }
$('#prevKey').onclick = () => { const ks = keyFrames().filter(f => f < Math.round(frame)); pause(); applyFrame(ks.length ? ks[ks.length - 1] : 0); refreshSliders(); };
$('#nextKey').onclick = () => { const ks = keyFrames().filter(f => f > Math.round(frame) && f <= anim.length); pause(); applyFrame(ks.length ? ks[0] : anim.length); refreshSliders(); };
$('#keyBtn').onclick = () => { if (!active) return toast('Select a character or prop first.'); pause(); pushUndo(); const f = Math.round(frame);
  if (sel) { keyCurrent(sel, f); toast('Key set for ' + sel.name + ' at frame ' + f + '.'); } else { active.bones.forEach(b => keyCurrent(b, f)); toast(active.name + ': whole pose keyed at frame ' + f + '.'); } changed(); };
$('#keyAll').onclick = () => { if (!active) return toast('Select a character or prop first.'); pause(); pushUndo(); const f = Math.round(frame); active.bones.forEach(b => keyCurrent(b, f)); changed(); toast(active.name + ': whole pose keyed at frame ' + f + '.'); };
$('#delKey').onclick = () => { if (!active) return; pause(); const f = Math.round(frame); const names = sel ? [sel.name] : Object.keys(active.tracks);
  if (!names.some(n => (active.tracks[n] || []).some(k => k.f === f))) return toast('No key on frame ' + f + ' for ' + (sel ? sel.name : active.name) + '.');
  pushUndo(); let n = 0; names.forEach(nm => n += removeKey(active, nm, f)); applyFrame(f); changed(); toast(n + ' key' + (n === 1 ? '' : 's') + ' deleted.'); };
$('#autoKey').onclick = e => { autoKey = !autoKey; e.currentTarget.classList.toggle('on', autoKey); e.currentTarget.setAttribute('aria-pressed', autoKey); toast(autoKey ? 'Auto-key on: every pose change sets a key.' : 'Auto-key off: press Key to keep a pose.'); };

/* project pane */
export function syncUI() { $('#len').value = anim.length; $('#fps').value = anim.fps; $('#loop').checked = anim.loop; $('#ease').value = anim.ease; syncLens(); applyLook(); refreshStageUI(); updateFrameUI(); }
$('#len').onchange = e => { pushUndo(); anim.length = clamp(Math.round(+e.target.value || 48), 1, 2000); frame = Math.min(frame, anim.length); syncUI(); changed(); };
$('#fps').onchange = e => { pushUndo(); anim.fps = clamp(Math.round(+e.target.value || 24), 1, 60); syncUI(); changed(); };
$('#loop').onchange = e => { pushUndo(); anim.loop = e.target.checked; changed(); };
$('#ease').onchange = e => { pushUndo(); anim.ease = e.target.value; applyFrame(frame); changed(); };
$('#showBones').onchange = e => { handles.visible = e.target.checked; if (boneLines) boneLines.visible = e.target.checked; };
$('#openBtn').onclick = () => $('#fileProj').click();
$('#fileProj').onchange = async e => { const f = e.target.files[0]; e.target.value = ''; if (!f) return;
  try { const o = JSON.parse(await f.text()); if (!o || o.app !== 'rigroom') throw 0; pushUndo(); const sk = loadSceneObject(o); toast(sk ? ('Opened. ' + sk + ' imported model(s) were not in the file; import them again.') : 'Project opened.'); }
  catch (err) { toast('That file is not a Rigroom project.', true); } };
$('#emptyBtn').onclick = () => { pushUndo(); loadSceneObject({ app: 'rigroom', v: 3, fps: 24, length: 48, loop: true, ease: 'spline', cam: [], ents: [{ kind: 'mannequin', name: 'Character', params: { color: '#b4b9c4', rough: .8, metal: 0 }, pos: [0, 0, 0], rot: [0, 0, 0], scale: 1, tracks: {} }] }); toast('Empty stage with one character.'); };

/* ───────── files out ───────── */
export function saveFile(filename, data) {
  try {
    const blob = data instanceof Blob ? data : new Blob([data], { type: filename.endsWith('.json') ? 'application/json' : 'application/octet-stream' });
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000); toast('Saved ' + filename + '.');
  } catch (e) { toast('Could not save: ' + (e && e.message || 'saving is unavailable here') + '.', true); }
}
$('#saveBtn').onclick = () => saveFile('rigroom-project.json', JSON.stringify(sceneJSON(false)));
function bakeClip() {
  const list = []; for (const e of ents) for (const n of Object.keys(e.tracks)) { const b = e.byName.get(n); if (b) list.push({ b, Q: [], P: b.isRoot ? [] : null }); }
  const times = [];
  for (let f = 0; f <= anim.length; f++) { evaluate(f); times.push(f / anim.fps); for (const x of list) { x.Q.push(...x.b.obj.quaternion.toArray()); if (x.P) x.P.push(...x.b.obj.position.toArray()); } }
  const tracks = []; for (const x of list) { tracks.push(new THREE.QuaternionKeyframeTrack(x.b.obj.uuid + '.quaternion', times, x.Q)); if (x.P) tracks.push(new THREE.VectorKeyframeTrack(x.b.obj.uuid + '.position', times, x.P)); }
  evaluate(0); return new THREE.AnimationClip('RigroomAction', anim.length / anim.fps, tracks);
}
export function exportGLB() {
  return new Promise((res, rej) => { pause(); const keep = frame; let clip; try { clip = bakeClip(); } catch (e) { return rej(e); }
    new GLTFExporter().parse(stage, out => { applyFrame(keep); res(out); }, err => { applyFrame(keep); rej(err); }, { binary: true, animations: clip.tracks.length ? [clip] : [] }); });
}
$('#glbBtn').onclick = async () => { try { const buf = await exportGLB(); saveFile('rigroom-scene.glb', new Blob([buf], { type: 'model/gltf-binary' })); } catch (e) { toast('Export failed: ' + (e && e.message || e), true); } };
$('#videoBtn').onclick = () => {
  if (recording || tracing) return;
  if (!(canvas.captureStream && window.MediaRecorder)) return toast('This browser cannot record video.', true);
  const type = ['video/mp4', 'video/webm;codecs=vp9', 'video/webm'].find(t => { try { return MediaRecorder.isTypeSupported(t); } catch (e) { return false; } });
  if (!type) return toast('This browser cannot record video.', true);
  let rec; const chunks = [];
  try { rec = new MediaRecorder(canvas.captureStream(anim.fps), { mimeType: type, videoBitsPerSecond: 8e6 }); } catch (e) { return toast('This browser cannot record video.', true); }
  const vis = handles.visible, wasShot = shotView; setOverlays(false); if (camKeys.length && !shotView) setShot(true);
  rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
  rec.onstop = () => { setOverlays(vis); if (!wasShot && shotView) setShot(false); recording = null; updateGizmo();
    if (chunks.length) saveFile('rigroom-animation.' + (type.startsWith('video/mp4') ? 'mp4' : 'webm'), new Blob(chunks, { type })); else toast('Nothing was recorded.', true); };
  recording = { finish() { if (rec.state !== 'inactive') setTimeout(() => rec.stop(), 120); } };
  pause(); applyFrame(0); rec.start(); toast('Rendering ' + (anim.length / anim.fps).toFixed(1) + ' seconds…'); play();
};
function setOverlays(on) { handles.visible = on; if (boneLines) boneLines.visible = on; grid.visible = on; tcHelper.visible = on; if (!on) tc.detach(); }

/* ───────── agent tools: the app's own commands ───────── */
let turnUndo = false, turnMutated = false, wantPlay = null, wantShot = false;
function mutate() { if (!turnUndo) { pushUndo(); turnUndo = true; } turnMutated = true; pause(); }
const stageNames = () => ents.map(e => e.name).join(', ') || '(empty)';
function needEnt(name) {
  if (name == null || name === '') { if (active) return active; throw new Error('Say which character or prop. On stage: ' + stageNames()); }
  const n = String(name).toLowerCase(), e = ents.find(x => x.name.toLowerCase() === n) || ents.find(x => x.name.toLowerCase().includes(n));
  if (!e) throw new Error('Nothing on stage is called "' + name + '". On stage: ' + stageNames()); return e;
}
function needBone(e, name) { const b = e.byName.get(name); if (!b) throw new Error('"' + e.name + '" has no bone "' + name + '". Bones: ' + e.bones.slice(0, 60).map(x => x.name).join(', ')); return b; }
let actHook = () => {};
function act(text) { actHook(text); }
export function writeKey(e, b, f, rot, pos) {
  let p = null;
  if (b.isRoot) { if (pos) p = offsetToLocalPos(b, pos); else { const tr = e.tracks[b.name]; if (tr && tr.length) { evalTrack(b, tr, f); p = b.obj.position.clone(); } else p = b.restP.clone(); } }
  setKey(e, b.name, f, eulerToLocal(b, rot), p);
}
function entInfo(e) { const o = { name: e.name, kind: e.kind === 'prop' ? 'prop' : 'character', position: e.pos.map(r2) };
  if (e.kind === 'prop') { o.shape = e.params.shape; o.size = e.params.size.map(r2); o.rotation = e.rot.map(r1); } else { o.facing = r1(e.rot[1]); o.scale = r2(e.scale); o.rig = e.kind === 'mannequin' ? 'mannequin' : 'imported (' + e.bones.length + ' bones)'; }
  if (e.kind !== 'import') o.material = { color: e.params.color, roughness: e.params.rough, metalness: e.params.metal };
  const n = Object.values(e.tracks).reduce((s, t) => s + t.length, 0); if (n) o.keyframes = n; return o; }
const A3 = { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 };
export const TOOLS = [
  { name: 'get_scene', description: 'List everything on stage (characters and props with position, facing, size, material), the timeline settings, the camera keys and the lighting.',
    input_schema: { type: 'object', properties: {} },
    execute() { return { timeline: { length: anim.length, fps: anim.fps, loop: anim.loop, motion: anim.ease }, stage: ents.map(entInfo), camera: camKeys.map(k => ({ frame: k.f, position: k.p.map(r2), target: k.t.map(r2), fov: r1(k.fov) })), lighting: { ...look } }; } },
  { name: 'get_rig', description: 'List the bones of one character: name, parent, rest position and rest direction toward its child, in character space.',
    input_schema: { type: 'object', properties: { character: { type: 'string' } } },
    execute(i) { const e = needEnt(i && i.character); return { character: e.name, bones: e.bones.map(b => ({ name: b.name, parent: b.parent, root: b.isRoot || undefined, pos: b.restWP.toArray().map(r2), dir: b.dir })) }; } },
  { name: 'get_animation', description: 'Read the keyframes of one character or prop, as rotations in degrees relative to rest.',
    input_schema: { type: 'object', properties: { character: { type: 'string' } } },
    execute(i) { const e = needEnt(i && i.character); const keys = {}; let n = 0;
      for (const [name, tr] of Object.entries(e.tracks)) { const b = e.byName.get(name); if (!b) continue;
        keys[name] = tr.map(k => { n++; const o = { frame: k.f, rot: localToEuler(b, new Q4().fromArray(k.q)).map(r1) }; if (k.p && b.isRoot) o.pos = localPosToOffset(b, k.p).map(r2); return o; }); }
      if (n > 400) { for (const k in keys) keys[k] = keys[k].map(x => x.frame); return { character: e.name, note: 'Too many keys to list values; frames only.', keyFrames: keys }; }
      return { character: e.name, keys }; } },
  { name: 'set_keyframes', description: 'Write keyframes. Each key sets one bone of one character at one frame: rot is [x,y,z] degrees from rest about the character\'s own axes; pos (root bones only) is an [x,y,z] offset in meters from rest in character space. A prop has one bone called "object". "character" on a key overrides the top-level one. Existing keys on the same bone and frame are replaced. Send many keys in one call.',
    input_schema: { type: 'object', required: ['keys'], properties: { character: { type: 'string' }, keys: { type: 'array', items: { type: 'object', required: ['bone', 'frame', 'rot'], properties: { character: { type: 'string' }, bone: { type: 'string' }, frame: { type: 'integer' }, rot: A3, pos: A3 } } } } },
    execute(i) { const keys = i && i.keys; if (!Array.isArray(keys) || !keys.length) throw new Error('keys must be a non-empty array');
      const plan = keys.map(k => { const e = needEnt(k.character || i.character), b = needBone(e, k.bone);
        if (!num3(k.rot)) throw new Error('rot must be three numbers for ' + k.bone); if (!isFinite(k.frame) || k.frame < 0) throw new Error('frame must be 0 or more');
        if (k.pos != null && !num3(k.pos)) throw new Error('pos must be three numbers for ' + k.bone); return { e, b, f: Math.min(2000, Math.round(k.frame)), rot: k.rot, pos: k.pos }; });
      mutate(); let maxF = 0; const who = new Set();
      for (const k of plan) { writeKey(k.e, k.b, k.f, k.rot, k.pos); maxF = Math.max(maxF, k.f); who.add(k.e.name); }
      const out = { written: plan.length }; if (maxF > anim.length) { anim.length = maxF; out.note = 'Timeline extended to ' + maxF + ' frames.'; }
      evaluate(frame); act(plan.length + ' keyframe' + (plan.length === 1 ? '' : 's') + ' on ' + [...who].join(', ')); return out; } },
  { name: 'reach', description: 'Put a hand or foot at a point in scene space at one frame. Solves the two bones above it (upper arm and forearm, or thigh and shin) from the pose already keyed at that frame, and keys them. Write body keys (hips, spine, chest) for that frame first. pole is an optional scene-space direction the elbow or knee should point toward.',
    input_schema: { type: 'object', required: ['bone', 'target', 'frame'], properties: { character: { type: 'string' }, bone: { type: 'string' }, target: A3, frame: { type: 'integer' }, pole: A3 } },
    execute(i) { const e = needEnt(i.character), b = needBone(e, i.bone); if (!chainOf(b)) throw new Error(i.bone + ' has no two-bone chain above it. Use a hand or foot.');
      const t = num3(i.target); if (!t) throw new Error('target must be three numbers'); const f = clamp(Math.round(+i.frame || 0), 0, 2000);
      mutate(); if (f > anim.length) anim.length = f; evaluateEnt(e, f);
      const ch = reach(b, new V3(...t), num3(i.pole) ? new V3(...i.pole) : null, false); ch.forEach(x => keyCurrent(x, f));
      const got = b.obj.getWorldPosition(new V3()), miss = got.distanceTo(new V3(...t)); evaluate(frame);
      act(e.name + ' ' + b.name + ' reaches at frame ' + f); return { reached: miss < 0.02, position: got.toArray().map(r2), short_by: miss < 0.02 ? undefined : r2(miss) }; } },
  { name: 'delete_keyframes', description: 'Delete keyframes. character limits it to one character or prop (omit for everything on stage). With bone and frame: one key. With bone only: that track. With frame only: every key on that frame. With neither: clear the animation and return to rest pose.',
    input_schema: { type: 'object', properties: { character: { type: 'string' }, bone: { type: 'string' }, frame: { type: 'integer' } } },
    execute(i) { i = i || {}; const list = i.character ? [needEnt(i.character)] : (i.bone ? [needEnt(null)] : ents); const f = i.frame; let n = 0;
      if (i.bone) needBone(list[0], i.bone); mutate();
      for (const e of list) {
        if (i.bone && f != null) n += removeKey(e, i.bone, Math.round(f));
        else if (i.bone) { n += (e.tracks[i.bone] || []).length; delete e.tracks[i.bone]; const b = e.byName.get(i.bone); b.obj.quaternion.copy(b.restQ); b.obj.position.copy(b.restP); }
        else if (f != null) Object.keys(e.tracks).forEach(nm => n += removeKey(e, nm, Math.round(f)));
        else { for (const tr of Object.values(e.tracks)) n += tr.length; e.tracks = {}; restEnt(e); } }
      evaluate(frame); act(n + ' keyframe' + (n === 1 ? '' : 's') + ' deleted'); return { deleted: n }; } },
  { name: 'set_timeline', description: 'Change timeline settings: length in frames, fps, loop, and motion ("spline" smooth curve through keys, "ease" pose-to-pose with a stop at each key, "linear").',
    input_schema: { type: 'object', properties: { length: { type: 'integer' }, fps: { type: 'integer' }, loop: { type: 'boolean' }, motion: { type: 'string', enum: ['spline', 'ease', 'linear'] } } },
    execute(i) { i = i || {}; mutate();
      if (i.length != null) anim.length = clamp(Math.round(i.length), 1, 2000); if (i.fps != null) anim.fps = clamp(Math.round(i.fps), 1, 60);
      if (i.loop != null) anim.loop = !!i.loop; if (['spline', 'ease', 'linear'].includes(i.motion)) anim.ease = i.motion;
      frame = Math.min(frame, anim.length); act('timeline: ' + anim.length + ' frames at ' + anim.fps + ' fps'); return { length: anim.length, fps: anim.fps, loop: anim.loop, motion: anim.ease }; } },
  { name: 'get_joint_positions', description: 'Check a pose: where a character\'s joints are in scene space (meters, y=0 is the floor) at a frame. Pass bones to limit the list.',
    input_schema: { type: 'object', required: ['frame'], properties: { character: { type: 'string' }, frame: { type: 'number' }, bones: { type: 'array', items: { type: 'string' } } } },
    execute(i) { const e = needEnt(i.character), f = clamp(+i.frame || 0, 0, anim.length); const list = Array.isArray(i.bones) && i.bones.length ? i.bones.map(n => needBone(e, n)) : e.bones.slice(0, 40);
      evaluateEnt(e, f); e.group.updateWorldMatrix(true, true); const out = {}, v = new V3(); for (const b of list) out[b.name] = b.obj.getWorldPosition(v).toArray().map(r2);
      evaluateEnt(e, frame); return { character: e.name, frame: f, positions: out }; } },
  { name: 'add_character', description: 'Add a mannequin character to the stage. position is where its feet stand in scene space; facing is degrees about Y (0 faces +Z).',
    input_schema: { type: 'object', properties: { name: { type: 'string' }, position: A3, facing: { type: 'number' }, scale: { type: 'number' }, color: { type: 'string', description: 'hex like #b4b9c4' } } },
    execute(i) { i = i || {}; mutate(); const e = addMannequin({ name: i.name, pos: num3(i.position, [0, 0, 0]), facing: +i.facing || 0, scale: +i.scale || 1, color: isHex(i.color) ? i.color : undefined }); act('added character ' + e.name); return entInfo(e); } },
  { name: 'add_prop', description: 'Add a prop: a box, cylinder or sphere. size is [width, height, depth] in meters, position is its center in scene space, rotation is [x,y,z] degrees.',
    input_schema: { type: 'object', required: ['shape', 'size', 'position'], properties: { name: { type: 'string' }, shape: { type: 'string', enum: ['box', 'cylinder', 'sphere'] }, size: A3, position: A3, rotation: A3, color: { type: 'string' }, roughness: { type: 'number' }, metalness: { type: 'number' } } },
    execute(i) { if (!num3(i.size) || !num3(i.position)) throw new Error('size and position must each be three numbers'); mutate();
      const e = addProp({ name: i.name || i.shape, shape: i.shape, size: i.size.map(v => clamp(Math.abs(v), .005, 50)), pos: i.position, rot: num3(i.rotation, [0, 0, 0]), color: isHex(i.color) ? i.color : undefined, rough: isFinite(i.roughness) ? clamp(+i.roughness, 0, 1) : undefined, metal: isFinite(i.metalness) ? clamp(+i.metalness, 0, 1) : undefined }); act('added prop ' + e.name); return entInfo(e); } },
  { name: 'place', description: 'Move, turn, resize, recolor or change the material of a character or prop where it stands (not animated). Give only the fields to change. roughness and metalness are 0 to 1.',
    input_schema: { type: 'object', required: ['name'], properties: { name: { type: 'string' }, position: A3, facing: { type: 'number' }, rotation: A3, scale: { type: 'number' }, size: A3, color: { type: 'string' }, roughness: { type: 'number' }, metalness: { type: 'number' }, rename: { type: 'string' } } },
    execute(i) { const e = needEnt(i.name); mutate();
      if (num3(i.position)) e.pos = i.position.map(Number); if (num3(i.rotation)) e.rot = i.rotation.map(Number); if (isFinite(i.facing)) e.rot[1] = +i.facing;
      if (isFinite(i.scale) && e.kind !== 'prop') e.scale = clamp(+i.scale, .05, 20); applyPlacement(e);
      if (e.kind !== 'import') { if (isHex(i.color)) e.params.color = i.color; if (isFinite(i.roughness)) e.params.rough = clamp(+i.roughness, 0, 1); if (isFinite(i.metalness)) e.params.metal = clamp(+i.metalness, 0, 1); }
      if (e.kind === 'prop' && num3(i.size)) e.params.size = i.size.map(v => clamp(Math.abs(v), .005, 50));
      applyMaterial(e);
      if (i.rename) e.name = uniqueName(String(i.rename).slice(0, 40), e);
      act('placed ' + e.name); return entInfo(e); } },
  { name: 'remove', description: 'Remove a character or prop from the stage.',
    input_schema: { type: 'object', required: ['name'], properties: { name: { type: 'string' } } },
    execute(i) { const e = needEnt(i.name); mutate(); const n = e.name; removeEnt(e); act('removed ' + n); return { removed: n }; } },
  { name: 'set_camera', description: 'Key the shot camera at a frame: position and target in scene space, fov in degrees. Several keys make a camera move. The user sees it in Shot view.',
    input_schema: { type: 'object', required: ['position', 'target'], properties: { frame: { type: 'integer' }, position: A3, target: A3, fov: { type: 'number' } } },
    execute(i) { if (!num3(i.position) || !num3(i.target)) throw new Error('position and target must each be three numbers'); mutate();
      const f = clamp(Math.round(+i.frame || 0), 0, anim.length), k = { f, p: i.position.map(Number), t: i.target.map(Number), fov: clamp(+i.fov || 35, 10, 90) };
      const x = camKeys.findIndex(c => c.f >= f); if (x < 0) camKeys.push(k); else if (camKeys[x].f === f) camKeys[x] = k; else camKeys.splice(x, 0, k);
      wantShot = true; act('camera keyed at frame ' + f); return { camera_keys: camKeys.length }; } },
  { name: 'set_lighting', description: 'Change the lighting: exposure (0.2 to 2), sun angle in degrees around the scene, sun height in degrees above the horizon, sun power (0 to 3), ambient (0 to 2).',
    input_schema: { type: 'object', properties: { exposure: { type: 'number' }, sun_angle: { type: 'number' }, sun_height: { type: 'number' }, sun_power: { type: 'number' }, ambient: { type: 'number' } } },
    execute(i) { i = i || {}; mutate();
      if (isFinite(i.exposure)) look.exposure = clamp(+i.exposure, .2, 2); if (isFinite(i.sun_angle)) look.sunAngle = clamp(+i.sun_angle, -180, 180); if (isFinite(i.sun_height)) look.sunHeight = clamp(+i.sun_height, 5, 85);
      if (isFinite(i.sun_power)) look.sunPower = clamp(+i.sun_power, 0, 3); if (isFinite(i.ambient)) look.env = clamp(+i.ambient, 0, 2); applyLook(); act('lighting changed'); return { ...look }; } },
  { name: 'playback', description: 'Control the viewport: "play", "pause", or "goto" a frame.',
    input_schema: { type: 'object', required: ['action'], properties: { action: { type: 'string', enum: ['play', 'pause', 'goto'] }, frame: { type: 'integer' } } },
    execute(i) { if (i.action === 'play') wantPlay = true; else { wantPlay = false; pause(); if (i.action === 'goto') applyFrame(clamp(Math.round(+i.frame || 0), 0, anim.length)); } return { ok: true }; } },
  { name: 'select', description: 'Select a character or prop, and optionally one of its bones, so the user can adjust it by hand.',
    input_schema: { type: 'object', required: ['character'], properties: { character: { type: 'string' }, bone: { type: 'string' } } },
    execute(i) { const e = needEnt(i.character); if (i.bone) select(needBone(e, i.bone)); else { setActive(e); if (e.bones.length === 1) select(e.bones[0]); } return { selected: e.name }; } }
];

export function systemPrompt() {
  return `You are the animation agent built into Rigroom, a 3D animation app on a tablet. You work inside the app: your tools build the stage, pose characters, light the scene and write keyframes on the timeline, and the user sees the result in the viewport straight away. Do the work with tools; do not describe steps for the user to do by hand unless they ask.

STAGE: the scene holds characters and props. Scene space: +Y up, the floor is y=0, meters. The usual camera looks from +Z toward -Z, so +X is screen right and +Z is toward the viewer. Each character has a position (where its feet stand), a facing in degrees about Y (0 faces +Z toward the viewer, 90 faces +X, -90 faces -X, 180 faces away) and a scale. Props are boxes, cylinders or spheres; a prop's position is its center and its size is [width, height, depth]. Characters and props have a material: color, roughness, metalness.

CHARACTER SPACE: bone rotations and hips offsets are in the character's own space, whatever its facing: +X is the character's LEFT, +Y is up, +Z is the way it faces.

ROTATIONS: a key's rot is [x,y,z] in degrees, measured from the bone's rest pose (rot [0,0,0] = rest), about the character axes as carried along by the parent bone (forward kinematics). Right-hand rule: +x turns up toward forward; +y turns forward toward the character's left; +z turns left toward up. When several axes are non-zero, z is applied first, then y, then x.

ROOT: the hips also take pos, an [x,y,z] offset in meters from rest, in character space. Nothing keeps feet on the floor automatically.

REACH: the reach tool puts a hand or foot on a point in scene space at a frame by solving the two bones above it, and keys them. Use it for hands on tables, holding props, pointing, and planting feet. Key the body for that frame first (hips, spine, chest), then reach. To animate a reach, call it on several frames with moving targets. It reports how far short it fell if the point is out of range. Arm length is about 0.6 m at scale 1.

MANNEQUIN (the built-in rig; rest pose is a T-pose, 1.8 m tall at scale 1). Bones: hips (root) > spine > chest > neck > head; chest > upperArm_L > forearm_L > hand_L (and _R); hips > thigh_L > shin_L > foot_L (and _R).
Cheat sheet (degrees):
- thigh: x -30 swings the leg forward, x +30 back. thigh_L z + / thigh_R z - spreads the leg outward.
- shin: x + bends the knee (0 to 130). Never negative.
- foot: x + points the toes down, x - lifts them.
- spine, chest, neck, head: x + bends forward, x - back; y + turns to the character's left; z + tilts toward the character's right.
- upperArm_L: z -80 hangs the arm at the side, z +80 points it straight up. upperArm_R is mirrored: z +80 at the side, z -80 straight up.
- With an arm at the side, swing it using x on the same key: [-25,0,-80] forward and [25,0,-80] back for the left arm, [-25,0,80] and [25,0,80] for the right.
- forearm_L: y - bends the elbow (0 to -140). forearm_R: y + bends the elbow (0 to 140).
- Standing naturally: upperArm_L [0,0,-78], upperArm_R [0,0,78], elbows bent about 10.
- Sitting on a 0.45 m seat: hips pos [0,-0.40,0], thighs x -88, shins x +84.
Imported models have their own bone names: call get_rig and work from each bone's rest direction.

HOW TO WORK:
- The app state in the user's message lists what is on stage. Call get_scene or get_animation when you need exact values.
- Edits: change only what was asked and keep everything else. Read the existing keys of the bones you touch first, so the new motion starts and ends in the pose that is already there.
- Loops: with loop on, playback runs frames 0 to length and wraps. Give each bone you animate identical keys on frame 0 and on frame length.
- Send all keys for a motion in one or two set_keyframes calls. Key every bone you move on the first frame.
- Motion: "spline" for flowing or cyclic motion, "ease" for held poses, "linear" for mechanical motion.
- After a non-trivial pose, check it with get_joint_positions (hands above a table top, feet not under the floor, nothing passing through a prop) and fix what is wrong.
- The app plays the result when you finish. Reply in one to three plain sentences: what you made, and one thing the user could ask to change. No markdown, no lists of keyframes.`;
}
export function stateBlock() {
  const list = ents.slice(0, 40).map(e => e.kind === 'prop' ? `${e.name} (${e.params.shape} ${e.params.size.map(r2).join('x')} at ${e.pos.map(r2).join(',')})` : `${e.name} (${e.kind === 'mannequin' ? 'mannequin' : 'imported model'} at ${e.pos.map(r2).join(',')} facing ${r1(e.rot[1])}${Object.keys(e.tracks).length ? ', animated' : ''})`);
  return `[app state: timeline ${anim.length} frames at ${anim.fps} fps, loop ${anim.loop ? 'on' : 'off'}, motion ${anim.ease}; current frame ${Math.round(frame)}; selected: ${active ? active.name + (sel ? ' / ' + sel.name : '') : 'nothing'}; camera keys: ${camKeys.length}; on stage: ${list.join('; ') || 'nothing'}]`;
}
export function beginAgentTurn(onAct) { turnUndo = false; turnMutated = false; wantPlay = null; wantShot = false; actHook = onAct || (() => {}); }
export function endAgentTurn() {
  actHook = () => {};
  if (active && !ents.includes(active)) setActive(ents[0] || null);
  if (wantShot && !shotView) setShot(true);
  syncUI(); select(sel); changed();
  if (turnMutated) { applyFrame(Math.min(Math.round(frame), anim.length)); if (wantPlay !== false) { frame = 0; play(); } } else if (wantPlay) play();
  return turnMutated;
}

/* ───────── chrome ───────── */
const side = $('#side');
function setSide(open) { side.classList.toggle('closed', !open); $('#sideToggle').setAttribute('aria-expanded', open); $('#sideToggle').classList.toggle('on', open); requestAnimationFrame(layoutFrame); }
$('#sideToggle').onclick = () => setSide(side.classList.contains('closed'));
document.querySelectorAll('.tabs button').forEach(t => t.onclick = () => {
  document.querySelectorAll('.tabs button').forEach(x => x.classList.toggle('on', x === t));
  document.querySelectorAll('.pane').forEach(p => p.classList.toggle('on', p.id === 'pane-' + t.dataset.tab));
});
window.addEventListener('keydown', e => { if (e.code === 'Space' && !/TEXTAREA|INPUT|SELECT|BUTTON/.test(document.activeElement.tagName)) { e.preventDefault(); playing ? pause() : play(); } });

/* ───────── render loop ───────── */
let lastT = performance.now(); const hv = new V3(), pvv = new V3();
function tick(now) {
  requestAnimationFrame(tick);
  const dt = Math.min(.1, (now - lastT) / 1000); lastT = now;
  if (tracing) { tracing.step(); return; }
  if (playing) {
    let f = frame + dt * anim.fps;
    if (f >= anim.length) { if (anim.loop && !recording) f %= anim.length; else { f = anim.length; frame = f; evaluate(f); pause(); } }
    if (playing) { frame = f; evaluate(f); updateFrameUI(); }
  }
  if (shotView && camKeys.length) applyCam(camAt(frame)); else orbit.update();
  if (sel && mode === 'reach' && !tc.dragging) sel.obj.getWorldPosition(ikTarget.position);
  const show = handles.visible; let i = 0; const pos = boneLines && boneLines.geometry.attributes.position;
  for (const e of ents) { const on = show && e === active;
    for (const b of e.bones) { b.handle.visible = on; if (!on) continue;
      b.obj.getWorldPosition(hv); b.handle.position.copy(hv);
      const pinned = e.pins.has(b.name); b.handle.scale.setScalar(camera.position.distanceTo(hv) * (camera.fov / 40) * (b === sel ? 0.016 : 0.0105));
      b.handle.material.color.setHex(b === sel ? 0xf0a23e : (pinned ? 0x7db6ff : 0xe3e6ec)); b.handle.material.opacity = b === sel || pinned ? 1 : .8;
      if (b.parent && pos) { e.byName.get(b.parent).obj.getWorldPosition(pvv); pos.setXYZ(i++, pvv.x, pvv.y, pvv.z); pos.setXYZ(i++, hv.x, hv.y, hv.z); } } }
  if (pos) { boneLines.geometry.setDrawRange(0, i); pos.needsUpdate = true; }
  renderer.render(scene, camera);
}

/* photoreal render hook: trace.js installs a stepper; the loop hands it every frame */
export function startTracing(stepper) {
  pause(); const vis = handles.visible, wasShot = shotView; setOverlays(false);
  tracing = { step: stepper.step, restore() { setOverlays(vis); tracing = null; if (!wasShot && shotView) setShot(false); else layoutFrame(); updateGizmo(); } };
  if (camKeys.length && !shotView) setShot(true); else layoutFrame();
  return tracing;
}
export const ctx = { THREE, renderer, scene, camera, canvas, orbit, stage, RoomEnvironment, layoutFrame, get ents() { return ents; }, anim, camKeys, look, get frame() { return frame; }, get active() { return active; }, get sel() { return sel; }, get shotView() { return shotView; } };

export function start(opening) {
  setMode('rotate'); setSide(window.innerWidth > 820); syncUI(); layoutFrame(); frameCameraToShot(); setPlayIcon(); updateUndoUI();
  if (opening) opening();
  undoStack.length = 0; redoStack.length = 0; updateUndoUI();
  requestAnimationFrame(tick);
}
export { ents, anim, camKeys };
