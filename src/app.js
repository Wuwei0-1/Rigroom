// Rigroom core: viewport, stage, posing, timeline, agent tools.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { initModels, importFiles, instantiate, mapSkeleton, fitModel, measureFit, cachedName, preloadModels, libraryModels } from './models.js';
import { PARENT, PARTS, extractMotion, motionName, sampleBone, sampleHips, saveMotion, listMotions, getMotion, findMotion } from './motion.js';

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
initModels(renderer);
const canvas = renderer.domElement;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x3a3d44);
const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 200);
camera.position.set(1.7, 1.45, 4.4);
// image-based lighting: surfaces pick up soft light and reflections from a studio room
try { const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; pm.dispose(); } catch (e) { /* no IBL */ }
const look = { exposure: 1, sunAngle: 35, sunHeight: 55, sunPower: 2, env: 0.6, sky: 'soft', skyTurn: 0, floor: 'matte', haze: 0 };
// environments light the scene from every direction; the files are 1K HDR photographs (CC0, Poly Haven), shared with the renderer
export const SKIES = ['soft', 'studio', 'interior', 'courtyard', 'city', 'forest', 'sunrise', 'sunset', 'night'];
export const FLOORS = { matte: 0x6b6e76, wood: 0x7a5a40, concrete: 0x7f7e7a, tiles: 0xb5b0a6, carpet: 0x5b5560 };
const roomEnv = scene.environment, skyCache = new Map();
async function applySky() {
  const name = look.sky, turn = () => { if (scene.environmentRotation) scene.environmentRotation.y = look.skyTurn * DEG; };
  if (name === 'soft' || !SKIES.includes(name)) { scene.environment = roomEnv; if (scene.environmentRotation) scene.environmentRotation.y = 0; return; }
  try {
    let t = skyCache.get(name);
    if (!t) {
      const { EXRLoader } = await import('three/addons/loaders/EXRLoader.js');
      const tex = await new EXRLoader().loadAsync('./assets/env/' + name + '.exr'); tex.mapping = THREE.EquirectangularReflectionMapping;
      const pm = new THREE.PMREMGenerator(renderer); t = pm.fromEquirectangular(tex).texture; pm.dispose(); tex.dispose(); skyCache.set(name, t);
    }
    if (look.sky === name) { scene.environment = t; turn(); scene.environmentIntensity = look.env / 0.6; }
  } catch (e) { scene.environment = roomEnv; }
}
const hemi = new THREE.HemisphereLight(0xffffff, 0x3c3f48, scene.environment ? 0.15 : 0.8); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff4e6, 1.2); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: .5, far: 30 }); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03;
scene.add(sun);
function applyLook() {
  renderer.toneMappingExposure = look.exposure;
  const a = look.sunAngle * DEG, h = look.sunHeight * DEG, d = 9;
  sun.position.set(Math.sin(a) * Math.cos(h) * d, Math.sin(h) * d, Math.cos(a) * Math.cos(h) * d); sun.intensity = look.sunPower;
  const sky = look.sky !== 'soft';
  if (scene.environment) scene.environmentIntensity = sky ? look.env / 0.6 : look.env; hemi.intensity = sky ? 0 : scene.environment ? 0.15 * look.env : 0.8 * look.env;
  applySky(); floor.material.color.setHex(FLOORS[look.floor] || FLOORS.matte);
  $('#haze').value = Math.round(look.haze * 100); $('#hazeV').textContent = Math.round(look.haze * 100) + '%';
  $('#skyPick').value = look.sky; $('#floorPick').value = look.floor; $('#skyTurn').value = look.skyTurn; $('#skyTurnV').textContent = Math.round(look.skyTurn) + '°';
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
  if (e.kind === 'mannequin') { buildMannequin(e); if (e.params.look) attachLook(e); }
  else if (e.kind === 'prop') buildProp(e);
  else if (e.kind === 'import' && e.params.model) buildImport(e);
  return e;
}
function applyPlacement(e) { e.group.position.fromArray(e.pos); e.group.rotation.set(e.rot[0] * DEG, e.rot[1] * DEG, e.rot[2] * DEG, 'YXZ'); e.group.scale.setScalar(e.scale); if (e.kind === 'prop' && e.params.shape === 'light') aimLight(e); }
function finalizeRig(e, objs) {
  e.group.updateMatrixWorld(true);
  const set = new Set(objs), used = new Set(), bones = [];
  for (const o of objs) { let nm = o.name || 'bone', base = nm, i = 2; while (used.has(nm)) nm = base + '_' + (i++); used.add(nm); o.userData.rigName = nm; }
  for (const o of objs) {
    let p = o.parent; while (p && !set.has(p)) p = p.parent;
    bones.push({ ent: e, name: o.userData.rigName, obj: o, parent: p ? p.userData.rigName : null, isRoot: !p, depth: 0, dir: null,
      restQ: o.quaternion.clone(), restP: o.position.clone(),
      parentRestWQ: o.parent.getWorldQuaternion(new Q4()), restWP: o.getWorldPosition(new V3()), restCQ: o.getWorldQuaternion(new Q4()) });
  }
  e.bones = bones; e.byName = new Map(bones.map(b => [b.name, b]));
  for (const b of bones) { let d = 0, p = b.parent; while (p) { d++; p = e.byName.get(p).parent; } b.depth = d; }
  for (const b of bones) { const kid = bones.find(c => c.parent === b.name); if (kid) { const v = kid.restWP.clone().sub(b.restWP); if (v.length() > 1e-5) b.dir = v.normalize().toArray().map(r2); } }
  for (const b of bones) { const m = new THREE.Mesh(HANDLE_GEO, new THREE.MeshBasicMaterial({ color: 0xe3e6ec, depthTest: false, transparent: true, opacity: .8 })); m.renderOrder = 20; m.visible = false; b.handle = m; handles.add(m); }
}
function buildMannequin(e) {
  const mat = () => new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: e.params.rough, metalness: e.params.metal });
  const M = { MID: mat(), LEFT: mat(), RIGHT: mat(), DARK: mat() }; e.mats = M; tintMannequin(e);
  const Y = new V3(0, 1, 0), sh = me => { me.castShadow = true; me.receiveShadow = true; me.userData.mq = true; return me; };
  const F = Object.assign({ hipY: .96, spine: .12, chest: .18, neck: .22, head: .08, shoulderX: .2, shoulderY: .17, upper: .28, fore: .26, hipX: .1, hipYoff: -.05, thigh: .42, shin: .42 }, e.params.fit || {});
  const seg = (bone, tip, r, m) => { const v = new V3(...tip), len = v.length(); const me = sh(new THREE.Mesh(new THREE.CapsuleGeometry(r, Math.max(0.001, len - r * 0.6), 6, 14), m));
    me.position.copy(v).multiplyScalar(.5); me.quaternion.setFromUnitVectors(Y, v.clone().normalize()); bone.add(me); };
  const blob = (bone, pos, scale, m) => { const me = sh(new THREE.Mesh(new THREE.SphereGeometry(1, 22, 16), m)); me.position.set(...pos); me.scale.set(...scale); bone.add(me); };
  const box = (bone, pos, size, m) => { const me = sh(new THREE.Mesh(new THREE.BoxGeometry(...size), m)); me.position.set(...pos); bone.add(me); };
  const B = {}, order = [];
  const add = (name, parent, pos) => { const b = new THREE.Bone(); b.name = name; b.position.set(...pos); (parent ? B[parent] : e.group).add(b); B[name] = b; order.push(b); };
  add('hips', null, [0, F.hipY, 0]); blob(B.hips, [0, 0, 0], [.17, .11, .11], M.MID);
  add('spine', 'hips', [0, F.spine, 0]); blob(B.spine, [0, .08, 0], [.145, .14, .1], M.MID);
  add('chest', 'spine', [0, F.chest, 0]); blob(B.chest, [0, .1, 0], [.2, .16, .115], M.MID);
  add('neck', 'chest', [0, F.neck, 0]); seg(B.neck, [0, F.head, 0], .042, M.MID);
  add('head', 'neck', [0, F.head, 0]); blob(B.head, [0, .12, 0], [.1, .125, .11], M.MID); box(B.head, [0, .11, .105], [.03, .035, .04], M.DARK);
  // the face: jaw opens with rotation about x (degrees, about 4 to 18 when speaking); lids close the eyes the same way (about 25)
  add('jaw', 'head', [0, .055, .075]); box(B.jaw, [0, -.02, .02], [.05, .018, .04], M.DARK);
  add('lids', 'head', [0, .135, .1]);
  for (const [S, sx, m] of [['L', 1, M.LEFT], ['R', -1, M.RIGHT]]) {
    add('upperArm_' + S, 'chest', [F.shoulderX * sx, F.shoulderY, 0]); seg(B['upperArm_' + S], [F.upper * sx, 0, 0], .046, m);
    add('forearm_' + S, 'upperArm_' + S, [F.upper * sx, 0, 0]); seg(B['forearm_' + S], [F.fore * sx, 0, 0], .038, m);
    add('hand_' + S, 'forearm_' + S, [F.fore * sx, 0, 0]); box(B['hand_' + S], [.06 * sx, 0, 0], [.11, .03, .075], m);
  }
  for (const [S, sx, m] of [['L', 1, M.LEFT], ['R', -1, M.RIGHT]]) {
    add('thigh_' + S, 'hips', [F.hipX * sx, F.hipYoff, 0]); seg(B['thigh_' + S], [0, -F.thigh, 0], .066, m);
    add('shin_' + S, 'thigh_' + S, [0, -F.thigh, 0]); seg(B['shin_' + S], [0, -F.shin, 0], .05, m);
    add('foot_' + S, 'shin_' + S, [0, -F.shin, 0]); box(B['foot_' + S], [0, -.04, .07], [.09, .06, .23], m);
  }
  finalizeRig(e, order);
}
/* ───────── looks: a real human model that follows a character's mannequin rig ───────── */
const LOOK_ORDER = ['hips', 'spine', 'chest', 'neck', 'head', 'upperArm_L', 'forearm_L', 'hand_L', 'upperArm_R', 'forearm_R', 'hand_R', 'thigh_L', 'shin_L', 'foot_L', 'thigh_R', 'shin_R', 'foot_R'];
const LOOK_CHILD = { hips: 'spine', spine: 'chest', chest: 'neck', neck: 'head', upperArm_L: 'forearm_L', forearm_L: 'hand_L', upperArm_R: 'forearm_R', forearm_R: 'hand_R', thigh_L: 'shin_L', shin_L: 'foot_L', thigh_R: 'shin_R', shin_R: 'foot_R' };
const LOOK_INHERIT = { head: 'neck', hand_L: 'forearm_L', hand_R: 'forearm_R', foot_L: 'shin_L', foot_R: 'shin_R' };
const _qa = new Q4(), _qb = new Q4(), _qc = new Q4(), _qd = new Q4(), _va = new V3(), _vb = new V3();
/* hands: a look's fingers take a pose per hand (they are not on the control rig) */
export const HAND_POSES = ['relaxed', 'open', 'grip', 'fist', 'point'];
const CURL = {   // degrees of curl at each finger's three joints
  open: {},
  relaxed: { thumb: [8, 10, 8], index: [14, 20, 10], middle: [18, 24, 12], ring: [22, 28, 14], pinky: [26, 30, 14] },
  grip: { thumb: [18, 22, 20], index: [42, 55, 30], middle: [46, 58, 32], ring: [50, 60, 32], pinky: [52, 60, 32] },
  fist: { thumb: [28, 38, 40], index: [80, 95, 60], middle: [82, 98, 62], ring: [84, 98, 62], pinky: [86, 98, 62] },
  point: { thumb: [28, 38, 40], index: [4, 6, 4], middle: [82, 98, 62], ring: [84, 98, 62], pinky: [86, 98, 62] }
};
const fingerKind = n => /thumb/i.test(n) ? 'thumb' : /index|fore/i.test(n) ? 'index' : /mid/i.test(n) ? 'middle' : /ring/i.test(n) ? 'ring' : /pinky|little/i.test(n) ? 'pinky' : null;
function findFingers(map, S) {
  const hand = map['hand_' + S], out = []; if (!hand) return out;
  const P = o => o.getWorldPosition(new V3()), roots = hand.children.filter(c => c.isBone && c.children.length && fingerKind(c.name));
  const idx = roots.find(c => fingerKind(c.name) === 'index'), pin = roots.find(c => fingerKind(c.name) === 'pinky') || roots.find(c => fingerKind(c.name) === 'ring');
  if (!idx || !pin) return out;
  // the palm faces away from the back of the hand, which the spread of the knuckles gives
  const hp = P(hand), palm = P(idx).sub(hp).cross(P(pin).sub(hp)).normalize(); if (S === 'L') palm.negate();
  for (const root of roots) {
    let bone = root, j = 0; const kind = fingerKind(root.name);
    while (bone && j < 3) {
      const kid = bone.children.find(c => c.isBone); if (!kid) break;
      const axis = P(kid).sub(P(bone)).normalize().cross(palm); if (axis.lengthSq() < 1e-6) break;
      axis.normalize().applyQuaternion(bone.parent.getWorldQuaternion(new Q4()).invert());
      out.push({ bone, rest: bone.quaternion.clone(), axis, kind, j }); bone = kid; j++;
    }
  }
  return out;
}
function applyHands(e) {
  if (!e.look) return; const H = e.params.hands || {};
  for (const S of ['L', 'R']) { const pose = CURL[H[S]] ? H[S] : 'relaxed';
    for (const f of e.look.fingers[S]) f.bone.quaternion.setFromAxisAngle(f.axis, ((CURL[pose][f.kind] || [0, 0, 0])[f.j] || 0) * DEG).multiply(f.rest); }
}
/** Set a character's hand poses: { L, R } each one of HAND_POSES. */
export function setHands(e, hands) {
  const H = { ...(e.params.hands || {}) }; for (const S of ['L', 'R']) if (hands && HAND_POSES.includes(hands[S])) H[S] = hands[S];
  e.params.hands = H; applyHands(e); if (e.look) retarget(e);
}
function attachLook(e) {
  const obj = instantiate(e.params.look);
  if (!obj) { e.lookMissing = true; return; }
  const { map, missing } = mapSkeleton(obj); if (missing.length) { e.lookMissing = true; return; }
  const wrap = fitModel(obj, map); e.group.add(wrap); e.group.updateMatrixWorld(true);
  const Einv = e.group.getWorldQuaternion(new Q4()).invert(), toChar = v => e.group.worldToLocal(v);
  const P = o => toChar(o.getWorldPosition(new V3()));
  const entries = [], R = {}, used = new Set();
  for (const k of LOOK_ORDER) {
    const dst = map[k], src = e.byName.get(k); if (!dst || !src || used.has(dst)) continue; used.add(dst);
    let rot;
    if (LOOK_CHILD[k]) {
      let c = LOOK_CHILD[k]; while (c && map[c] === dst) c = LOOK_CHILD[c];   // a model with a one-bone spine
      const sd = e.byName.get(c).restWP.clone().sub(src.restWP).normalize(), dd = P(map[c]).sub(P(dst)).normalize();
      rot = new Q4().setFromUnitVectors(dd, sd);
    } else rot = (R[LOOK_INHERIT[k]] || new Q4()).clone();
    R[k] = rot;
    entries.push({ src, dst, SrInv: src.restCQ.clone().invert(), R: rot, Tr: dst.getWorldQuaternion(new Q4()).premultiply(Einv) });
  }
  // the face follows its controls directly: the model's jaw and eyelids turn by whatever the control turned
  for (const [k, dsts] of [['jaw', [map.jaw]], ['lids', [map.lid_L, map.lid_R]]]) { const src = e.byName.get(k); if (!src) continue;
    for (const dst of dsts) if (dst && !used.has(dst)) { used.add(dst); entries.push({ src, dst, SrInv: src.restCQ.clone().invert(), R: new Q4(), Tr: dst.getWorldQuaternion(new Q4()).premultiply(Einv) }); } }
  e.group.traverse(o => { if (o.userData.mq) o.visible = false; });
  const hips = e.byName.get('hips');
  e.look = { wrap, entries, hips: { dst: map.hips, restChar: P(map.hips), src: hips, srcRest: hips.restWP.clone() }, fingers: { L: findFingers(map, 'L'), R: findFingers(map, 'R') } };
  e.lookMissing = false;
  applyHands(e); retarget(e);
}
export function retarget(e) {
  const L = e.look; if (!L) return;
  e.group.updateMatrixWorld(true);
  const Einv = e.group.getWorldQuaternion(_qa).invert();
  for (const m of L.entries) {
    const T = m.src.obj.getWorldQuaternion(_qc).premultiply(Einv).multiply(m.SrInv).multiply(m.R).multiply(m.Tr);
    const Pw = m.dst.parent.getWorldQuaternion(_qd).premultiply(Einv).invert();
    m.dst.quaternion.copy(Pw.multiply(T)); m.dst.updateMatrixWorld(true);
  }
  const h = L.hips, off = e.group.worldToLocal(h.src.obj.getWorldPosition(_va)).sub(h.srcRest);
  const t = e.group.localToWorld(_vb.copy(h.restChar).add(off)); h.dst.parent.worldToLocal(t);
  h.dst.position.copy(t); h.dst.updateMatrixWorld(true);
}
/** Dress a character in a stored human model (hash), or back in the mannequin (null). Keeps its animation. */
export function swapLook(e, hash, name) {
  if (!e || e.kind !== 'mannequin') throw new Error('Only characters can wear a look.');
  let fit = null;
  if (hash) {
    const obj = instantiate(hash); if (!obj) throw new Error('That model is not loaded on this device. Import it again.');
    const { map, missing } = mapSkeleton(obj);
    if (missing.length) throw new Error('This model\u2019s skeleton is missing: ' + missing.join(', ') + '. Use a rigged humanoid (Mixamo, Unreal, Character Creator and similar skeletons work).');
    fitModel(obj, map); fit = measureFit(map, v => v);
  }
  const oldHipY = (e.params.fit && e.params.fit.hipY) || .96, newHipY = fit ? fit.hipY : .96;
  const spec = JSON.parse(JSON.stringify(sceneJSON(true))), s = spec.ents.find(x => x.id === e.id);
  s.params = { ...s.params }; delete s.params.look; delete s.params.lookName; delete s.params.fit;
  if (hash) { s.params.look = hash; s.params.lookName = name || cachedName(hash) || 'Model'; s.params.fit = fit; }
  // hips heights move with the new body, so poses keep their offsets from standing height
  for (const k of (s.tracks.hips || [])) if (k.p) k.p = [k.p[0], k.p[1] - oldHipY + newHipY, k.p[2]];
  applyScene(spec, true);
  const ne = ents.find(x => x.id === e.id); setActive(ne); applyFrame(frame); return ne;
}
function buildImport(e) {
  const obj = instantiate(e.params.model); if (!obj) { e.missing = true; return; }
  const { map, missing } = mapSkeleton(obj), wrap = fitModel(obj, missing.length ? null : map, !missing.length);
  e.group.add(wrap); e.group.updateMatrixWorld(true);
  let objs = []; obj.traverse(o => { if (o.isBone) objs.push(o); });
  if (!objs.length) { obj.traverse(o => { if (o !== obj && o.name && !o.isMesh && objs.length < 200) objs.push(o); }); if (!objs.length) obj.traverse(o => { if (o !== obj && o.name && objs.length < 200) objs.push(o); }); }
  if (!objs.length) { const n = new THREE.Object3D(); n.name = 'object'; e.group.add(n); n.attach(wrap); objs = [n]; }
  finalizeRig(e, objs);
}
function tintMannequin(e) {
  const base = new THREE.Color(e.params.color || '#b4b9c4'), M = e.mats;
  M.MID.color.copy(base); M.LEFT.color.copy(base).lerp(new THREE.Color(0xe6a052), .3); M.RIGHT.color.copy(base).lerp(new THREE.Color(0x5a8fe6), .3); M.DARK.color.copy(base).lerp(new THREE.Color(0x15171c), .75);
  for (const m of Object.values(M)) { m.roughness = e.params.rough; m.metalness = e.params.metal; m.needsUpdate = true; }
}
// material presets: the viewport shows their sheen; the render server builds the full surface (grain, pores, bumps, rounded edges)
export const MATS = { plain: null, wood: { rough: .45 }, leather: { rough: .5 }, fabric: { rough: .9 }, stone: { rough: .7 }, plaster: { rough: .92 }, metal: { rough: .3, metal: 1 }, paper: { rough: .8 },
  glass: { rough: .05, opacity: .3 }, plastic: { rough: .35 }, ceramic: { rough: .15 }, brick: { rough: .9 }, velvet: { rough: 1 }, glow: { glow: 1.5 }, neon: { glow: 3 } };
export const LIGHT_TYPES = ['area', 'spot', 'point'];
const LIGHT_K = { point: .016, spot: .016, area: .064 };   // viewport brightness per watt, matched by eye to the renderer
const isLight = e => !!e && e.kind === 'prop' && e.params.shape === 'light';
function lightMesh(e) {
  const p = e.params; p.type = LIGHT_TYPES.includes(p.type) ? p.type : 'area'; p.power = clamp(isFinite(p.power) ? +p.power : 150, 0, 5000); p.color = isHex(p.color) ? p.color : '#ffe9cf';
  p.lsize = clamp(+p.lsize || .6, .02, 5); p.spread = clamp(+p.spread || 60, 5, 160); p.target = num3(p.target, null); p.size = [.1, .1, .1];
  const g = new THREE.Group(), col = new THREE.Color(p.color);
  const L = p.type === 'point' ? new THREE.PointLight(col, p.power * LIGHT_K.point, 0, 2) : new THREE.SpotLight(col, p.power * LIGHT_K[p.type], 0, p.type === 'area' ? 80 * DEG : p.spread / 2 * DEG, p.type === 'area' ? 1 : .35, 2);
  g.add(L); if (L.target) { L.target.position.set(0, 0, 1); g.add(L.target); }
  // what you see and tap in the viewport; never rendered
  const giz = new THREE.Group(), gm = new THREE.MeshBasicMaterial({ color: col, side: THREE.DoubleSide, transparent: true, opacity: .85 });
  giz.add(new THREE.Mesh(new THREE.SphereGeometry(.05, 14, 10), gm));
  if (p.type !== 'point') { const d = new THREE.Mesh(p.type === 'area' ? new THREE.RingGeometry(p.lsize / 2 * .92, p.lsize / 2, 40) : new THREE.ConeGeometry(Math.tan(p.spread / 2 * DEG) * .3, .3, 24, 1, true), gm);
    if (p.type === 'spot') { d.rotation.x = -Math.PI / 2; d.position.z = .15; } giz.add(d);
    const ray = new THREE.Mesh(new THREE.CylinderGeometry(.006, .006, .45, 6), gm); ray.rotation.x = Math.PI / 2; ray.position.z = .225; giz.add(ray); }
  giz.visible = overlaysOn; g.add(giz); e.gizmo = giz; return g;
}
let overlaysOn = true;
function aimLight(e) {
  const t = e.params.target ? new V3(...e.params.target) : new V3(e.pos[0], e.pos[1] - 1, e.pos[2] + 1e-4);
  e.group.rotation.set(0, 0, 0); e.group.lookAt(t);
}
/** Every light on stage, for the render job: where it is, what it aims at, and how bright. */
export function lightList() {
  return ents.filter(isLight).map(e => { const p = e.params, pos = e.bones[0].obj.getWorldPosition(new V3()), t = p.target ? new V3(...p.target) : new V3(pos.x, pos.y - 1, pos.z);
    return { name: e.name, type: p.type, power: p.power, color: p.color, size: p.lsize, spread: p.spread, p: pos.toArray().map(r2), t: t.toArray().map(r2) }; });
}
function propMesh(e) {
  if (e.params.shape === 'light') return lightMesh(e);
  const p = e.params, s = num3(p.size, [.5, .5, .5]).map(v => Math.max(.005, v)); let geo;
  if (!(p.mat in MATS)) p.mat = 'plain';
  if (p.shape === 'cylinder') geo = new THREE.CylinderGeometry(.5, .5, 1, 36); else if (p.shape === 'sphere') geo = new THREE.SphereGeometry(.5, 28, 18); else geo = new THREE.BoxGeometry(1, 1, 1);
  const pre = MATS[p.mat], col = new THREE.Color(p.color || '#8d8f96');
  const mat = new THREE.MeshStandardMaterial({ name: 'rr:' + p.mat, color: col, roughness: pre ? pre.rough ?? .6 : p.rough, metalness: pre ? pre.metal || 0 : p.metal });
  if (pre && pre.opacity) { mat.transparent = true; mat.opacity = pre.opacity; }
  if (pre && pre.glow) { mat.emissive = col; mat.emissiveIntensity = pre.glow; }
  const me = new THREE.Mesh(geo, mat); me.scale.set(s[0], s[1], s[2]); me.castShadow = !(pre && (pre.opacity || pre.glow)); me.receiveShadow = true; return me;
}
function buildProp(e) { const node = new THREE.Object3D(); node.name = 'object'; e.group.add(node); e.mesh = propMesh(e); node.add(e.mesh); finalizeRig(e, [node]); }
function refreshProp(e) { const node = e.bones[0].obj; node.remove(e.mesh); e.mesh.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.dispose && o.isLight) o.dispose(); }); e.mesh = propMesh(e); node.add(e.mesh); if (isLight(e)) aimLight(e); }
function applyMaterial(e) { if (e.kind === 'mannequin') tintMannequin(e); else if (e.kind === 'prop') refreshProp(e); }

export function addMannequin(o) { o = o || {}; const e = makeEnt({ kind: 'mannequin', name: uniqueName(o.name || 'Character'), params: { color: o.color || '#b4b9c4', rough: .8, metal: 0 } });
  e.pos = num3(o.pos, [0, 0, 0]); e.rot = [0, +o.facing || 0, 0]; e.scale = clamp(+o.scale || 1, .2, 5); applyPlacement(e); ents.push(e); return e; }
export function addLight(o) { o = o || {}; const e = makeEnt({ kind: 'prop', name: uniqueName(o.name || 'Light'), params: { shape: 'light', type: o.type, power: o.power, color: o.color, lsize: o.size, spread: o.spread, target: num3(o.target, null) } });
  e.pos = num3(o.pos, [0, 2.4, 0]); e.rot = [0, 0, 0]; e.scale = 1; applyPlacement(e); ents.push(e); return e; }
export function addProp(o) { o = o || {}; const e = makeEnt({ kind: 'prop', name: uniqueName(o.name || 'Prop'), params: { shape: ['box', 'cylinder', 'sphere'].includes(o.shape) ? o.shape : 'box', size: num3(o.size, [.5, .5, .5]), color: o.color || '#8d8f96', rough: o.rough ?? .85, metal: o.metal ?? 0, mat: o.mat in MATS ? o.mat : 'plain' } });
  e.pos = num3(o.pos, [0, .25, 0]); e.rot = num3(o.rot, [0, 0, 0]); e.scale = 1; applyPlacement(e); ents.push(e); return e; }
function detach(e) { stage.remove(e.group); e.bones.forEach(b => handles.remove(b.handle)); if (sel && sel.ent === e) sel = null; if (e.kind === 'import') graveyard.set(e.id, e); }
function reattach(e) { stage.add(e.group); e.bones.forEach(b => handles.add(b.handle)); graveyard.delete(e.id); }
function removeEnt(e) { detach(e); const i = ents.indexOf(e); if (i >= 0) ents.splice(i, 1); if (active === e) setActive(ents.find(x => x.kind !== 'prop') || ents[0] || null); }

export async function importModel(files, asLook) {
  let res;
  try { toast('Loading the model…'); res = await importFiles(files); }
  catch (err) { return toast('Could not load that model: ' + (err && err.message || err), true); }
  const mo = await keepMotions(res), said = mo.kept.length ? ' Its movement is in your motions as ' + mo.kept.map(m => m.name).join(', ') + ' (Pose → Motion).' : '';
  if (res.hash) libraryChanged(); refreshLookPick();
  if (!res.hash) return toast(mo.kept.length ? 'Added ' + mo.kept.map(m => m.name).join(', ') + ' to your motions. Put it on a character from Pose → Motion.' : 'That file has a skeleton but no body or movement Rigroom can use.', !mo.kept.length);
  if (asLook) {
    if (!active || active.kind !== 'mannequin') return toast('Select a character first, then choose its look.', true);
    try { pushUndo(); const e = swapLook(active, res.hash, res.name); toast(e.name + ' now looks like ' + res.name + '. Their animation is unchanged.' + said); refreshStageUI(); changed(); }
    catch (err) { undoStack.pop(); updateUndoUI(); toast(err.message, true); }
    return;
  }
  pushUndo();
  const e = makeEnt({ kind: 'import', name: uniqueName(res.name || 'Model'), params: { model: res.hash, file: res.name } });
  if (e.missing || !e.bones.length) { stage.remove(e.group); undoStack.pop(); updateUndoUI(); return toast('That file has nothing to show.', true); }
  e.pos = [0, 0, 1.2]; applyPlacement(e); ents.push(e); setActive(e); changed(); refreshStageUI();
  const rigged = e.bones.length > 1 && e.group.getObjectByProperty('isSkinnedMesh', true);
  toast('Loaded ' + res.name + '. ' + (rigged ? 'To dress a character in it instead, select the character and use Look → Real model.' : 'It has no skeleton, so it stays in its scanned pose: use Place to stand it where you want.') + said);
}
/** Import a file only for its movement (the person in it is kept too, so they can be worn as a look). */
export async function importMotionFiles(files) {
  let res;
  try { toast('Reading the motion…'); res = await importFiles(files); }
  catch (err) { return toast('Could not read that file: ' + (err && err.message || err), true); }
  const mo = await keepMotions(res);
  if (res.hash) { libraryChanged(); refreshLookPick(); }
  if (!mo.kept.length) return toast(res.anim === null && mo.failed ? 'That file\u2019s skeleton is not a humanoid Rigroom can read.' : 'That file has no recorded movement in it.', true);
  toast('Added ' + mo.kept.map(m => m.name + ' (' + m.seconds.toFixed(1) + ' s)').join(', ') + '. Choose a character and press Apply.' + (res.hash ? ' ' + res.name + ' is in your people too.' : ''));
}
let libHook = null;
/** Called when a model or motion is added to this browser's library, so the studio can keep a copy. */
export function onLibraryChange(fn) { libHook = fn; }
function libraryChanged() { if (libHook) { try { libHook(); } catch (e) { /* best effort */ } } }
export function loadGLB(buf, fileName) { return importModel([new File([buf], fileName.replace(/\.[^.]+$/, '') + '.glb')], false); }
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
/* ───────── motion: recorded movement written onto a character as ordinary keys ───────── */
const tmpBone = { obj: new THREE.Object3D() }, rq = a => a.map(v => Math.round(v * 1e4) / 1e4);
/**
 * Key a stored motion onto a character from frame `start`. Options: parts ('body', 'upper', 'arms', 'lower', 'head',
 * or a list of bones); mode 'replace' (clears those bones' keys over the span) or 'layer' (adds the motion's movement
 * to what is keyed); speed; from / to (seconds within the motion); repeat (a walk keeps travelling each time round);
 * inPlace (takes out the travel, keeps the sway); step (frames between keys).
 */
export function applyMotion(e, m, o = {}) {
  if (!e || e.kind !== 'mannequin') throw new Error('Motions go on characters. Select a character.');
  const parts = Array.isArray(o.parts) ? o.parts.filter(k => k in PARENT) : PARTS[o.parts || 'body'];
  if (!parts || !parts.length) throw new Error('Choose body, upper, arms, lower or head, or a list of bones.');
  const speed = clamp(+o.speed || 1, .1, 4), from = clamp(+o.from || 0, 0, m.seconds), to = clamp(o.to != null ? +o.to : m.seconds, Math.min(m.seconds, from + 1 / m.fps), m.seconds);
  const len = Math.max(1 / m.fps, to - from), repeat = clamp(Math.round(+o.repeat || 1), 1, 50), layer = o.mode === 'layer';
  const start = clamp(Math.round(+o.start || 0), 0, 1999), end = Math.min(2000, start + Math.max(1, Math.round(len / speed * repeat * anim.fps)));
  const step = clamp(Math.round(+o.step || (end - start > 360 ? 2 : 1)), 1, 12);
  const hipY = (e.params.fit && e.params.fit.hipY) || .96, h0 = sampleHips(m, from), drift = sampleHips(m, to).sub(h0).setY(0);
  const fs = []; for (let f = start; f < end; f += step) fs.push(f); fs.push(end);
  // what is keyed now, read before anything changes (for layering)
  const base = {};
  if (layer) for (const k of parts) { const b = e.byName.get(k), tr = e.tracks[k];
    base[k] = fs.map(f => { if (tr && tr.length) { tmpBone.obj.quaternion.copy(b.restQ); tmpBone.obj.position.copy(b.restP); evalTrack(tmpBone, tr, f); return { q: tmpBone.obj.quaternion.clone(), p: tmpBone.obj.position.clone() }; } return { q: b.restQ.clone(), p: b.restP.clone() }; }); }
  else for (const k of parts) { const tr = e.tracks[k]; if (!tr) continue; e.tracks[k] = tr.filter(x => x.f < start || x.f > end); if (!e.tracks[k].length) delete e.tracks[k]; }
  const q0 = {}; for (const k of parts) q0[k] = sampleBone(m, k, from).invert();
  fs.forEach((f, i) => {
    const u = (f - start) / anim.fps * speed, cycle = Math.min(repeat - 1, Math.floor(u / len + 1e-6)), t = Math.min(to, from + u - cycle * len);
    for (const k of parts) {
      const b = e.byName.get(k); let q = sampleBone(m, k, t), p = null;
      if (layer) q = base[k][i].q.clone().multiply(q0[k]).multiply(q);
      if (k === 'hips') {
        // the hips' travel from where the motion starts, scaled to this character's hip height
        const off = sampleHips(m, t).sub(layer ? h0 : new V3(h0.x, 0, h0.z));
        if (o.inPlace) off.addScaledVector(drift, -(t - from) / len); else off.addScaledVector(drift, cycle);
        off.multiplyScalar(hipY); p = (layer ? base[k][i].p.clone() : b.restP.clone()).add(off);
      }
      setKey(e, k, f, rq(q.toArray()), p ? rq(p.toArray()) : null);
    }
  });
  const extended = end > anim.length; if (extended) anim.length = end;
  return { start, end, keys: fs.length * parts.length, extended };
}
/** Read the recorded movement out of an imported file and keep it in the motion library. */
async function keepMotions(res) {
  if (!res || !res.anim) return { kept: [], failed: 0 };
  const kept = []; let failed = 0; const many = res.anim.clips.length > 1;
  for (const clip of res.anim.clips.slice(0, 12)) {
    let m = null; try { m = extractMotion(res.anim.root, clip, motionName(res.file, many ? clip : null)); } catch (e) { m = null; }
    if (m) { await saveMotion(m); kept.push(m); } else failed++;
  }
  res.anim = null;
  if (kept.length) { refreshMotionUI(kept[kept.length - 1].id); libraryChanged(); }
  return { kept, failed };
}
export function evaluateEnt(e, f) { for (const b of e.bones) { const tr = e.tracks[b.name]; if (tr && tr.length) evalTrack(b, tr, f); } if (e.look) retarget(e); }
function evaluate(f) { for (const e of ents) evaluateEnt(e, f); }
export function applyFrame(f) { frame = f; evaluate(f); updateFrameUI(); }
function restEnt(e) { for (const b of e.bones) { b.obj.quaternion.copy(b.restQ); b.obj.position.copy(b.restP); } }

/* scene <-> JSON */
function specOf(e) { return { id: e.id, kind: e.kind, name: e.name, params: e.params, pos: e.pos, rot: e.rot, scale: e.scale, tracks: e.tracks }; }
export function sceneJSON(withImports) { return { app: 'rigroom', v: 3, fps: anim.fps, length: anim.length, loop: anim.loop, ease: anim.ease, cam: camKeys.map(k => ({ ...k, p: [...k.p], t: [...k.t] })), look: { ...look }, ref: ref.kind === 'sketch' ? 'sketch' : null, ents: ents.filter(e => withImports || e.kind !== 'import' || e.params.model).map(specOf) }; }
function cleanTracks(e, tracks) { const out = {};
  for (const [name, tr] of Object.entries(tracks || {})) { if (!e.byName.has(name) || !Array.isArray(tr)) continue;
    const t = tr.filter(k => k && Array.isArray(k.q) && k.q.length === 4 && isFinite(k.f)).map(k => ({ f: Math.round(k.f), q: k.q.map(Number), p: Array.isArray(k.p) ? k.p.map(Number) : null })).sort((a, b) => a.f - b.f);
    if (t.length) out[name] = t; }
  return out; }
function applyScene(o, reuse) {
  anim.fps = clamp(+o.fps || 24, 1, 60); anim.length = clamp(Math.round(+o.length || 48), 1, 2000); anim.loop = o.loop !== false; anim.ease = ['spline', 'ease', 'linear'].includes(o.ease) ? o.ease : 'spline';
  camKeys.length = 0; for (const k of (Array.isArray(o.cam) ? o.cam : [])) if (k && num3(k.p) && num3(k.t) && isFinite(k.f)) camKeys.push({ f: Math.round(k.f), p: k.p.map(Number), t: k.t.map(Number), fov: clamp(+k.fov || 35, 10, 90), ...(isFinite(k.fstop) && k.fstop > 0 ? { fstop: clamp(+k.fstop, .7, 32) } : {}) });
  camKeys.sort((a, b) => a.f - b.f);
  if (o.look) { for (const k of Object.keys(look)) if (typeof look[k] === 'number' && o.look[k] != null && isFinite(o.look[k])) look[k] = +o.look[k];
    look.sky = SKIES.includes(o.look.sky) ? o.look.sky : 'soft'; look.floor = o.look.floor in FLOORS ? o.look.floor : 'matte'; }
  applyLook();
  const keep = new Map(ents.map(e => [e.id, e])), next = []; let skipped = 0;
  for (const s of (Array.isArray(o.ents) ? o.ents : [])) {
    if (!s || !['mannequin', 'prop', 'import'].includes(s.kind)) continue;
    let e = reuse ? (keep.get(s.id) || graveyard.get(s.id)) : null;
    if (e && e.kind === s.kind && (e.kind === 'import' || JSON.stringify(e.params) === JSON.stringify(s.params))) { if (keep.has(s.id)) keep.delete(s.id); else reattach(e); }
    else if (s.kind !== 'import' || (s.params && cachedName(s.params.model))) { ents.length = 0; ents.push(...next, ...keep.values()); e = makeEnt({ id: reuse ? s.id : null, kind: s.kind, name: String(s.name || 'Object'), params: s.params }); if (e.missing) { stage.remove(e.group); skipped++; continue; } }
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

let saveTimer = null, changeHook = null;
export function onSceneChange(fn) { changeHook = fn; }
export function changed() {
  drawTimeline(); markKeyed(); refreshSliders(); refreshHeader();
  if (changeHook) { try { changeHook(); } catch (e) { /* sync is best effort */ } }
  clearTimeout(saveTimer); saveTimer = setTimeout(() => { try { localStorage.setItem('rigroom.v3', JSON.stringify(sceneJSON(false))); } catch (e) { /* storage unavailable */ } }, 700);
}
export function loadSceneObject(o) {
  if (!o || o.app !== 'rigroom') throw new Error('not a Rigroom project');
  if (!o.v || o.v < 2) o = { app: 'rigroom', v: 3, fps: o.fps, length: o.length, loop: o.loop, ease: o.ease, cam: [], ents: [{ kind: 'mannequin', name: 'Character', params: { color: '#b4b9c4' }, pos: [0, 0, 0], rot: [0, 0, 0], scale: 1, tracks: o.tracks }] };
  playing = false; [...ents].forEach(detach); ents.length = 0; graveyard.clear(); active = null; sel = null;
  const skipped = applyScene(o, false);
  setActive(ents.find(e => e.kind !== 'prop') || ents[0] || null); applyFrame(0); frameCameraToShot(); syncUI(); changed(); setPlayIcon(); return skipped;
}
/** Load the stored models a scene refers to before building it. Returns how many are not on this device. */
export async function preloadForScene(o) {
  const hashes = (o && Array.isArray(o.ents) ? o.ents : []).map(s => s && s.params && (s.params.look || s.params.model)).filter(Boolean);
  return hashes.length ? (await preloadModels(hashes)).length : 0;
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
function refreshLookUI() {
  const isChar = !!active && active.kind === 'mannequin', looked = isChar && !!active.params.look;
  $('#lookReal').disabled = !isChar; $('#lookMannequin').disabled = !looked; if ($('#lookPick').options.length > 1) $('#lookPick').disabled = !isChar;
  if ($('#motionPick')) updateMotionNote();
  $('#handsRow').style.display = looked ? 'flex' : 'none';
  if (looked) for (const S of ['L', 'R']) $('#hand' + S).value = (active.params.hands && HAND_POSES.includes(active.params.hands[S])) ? active.params.hands[S] : 'relaxed';
  $('#lookName').textContent = !isChar ? (active ? active.name + ' is not a character.' : 'Nothing selected.')
    : active.name + ': ' + (looked ? active.params.lookName + (active.lookMissing ? ' (not on this device, so the mannequin stands in)' : '') : 'mannequin');
  $('#lookNote').textContent = isChar ? 'Pick one of your people above, or Real model… to import a rigged human (.glb, or .fbx picked with its textures). Poses, animation and the agent keep working.'
    : 'Select a character to change how they look: tap them in the viewport or in the list above.';
}
export function refreshStageUI() {
  const list = $('#entList'); list.textContent = '';
  for (const e of ents) { const el = document.createElement('button'); el.className = 'item' + (e === active ? ' on' : '') + (Object.keys(e.tracks).length ? ' keyed' : '');
    const sm = document.createElement('small'); sm.textContent = e.kind === 'prop' ? (isLight(e) ? e.params.type + ' light' : e.params.shape) : (e.kind === 'import' ? 'model' : 'character');
    el.append(document.createElement('i'), document.createTextNode(e.name), sm); el.onclick = () => { setActive(e); if (e.bones.length === 1) select(e.bones[0]); }; list.append(el); }
  refreshLookUI();
  const ed = $('#entEdit'); ed.style.display = active ? 'flex' : 'none'; if (!active) return;
  $('#entName').value = active.name; $('#entFacing').value = Math.round(active.rot[1]); $('#entFacingV').textContent = Math.round(active.rot[1]) + '°';
  $('#entSize').value = Math.round(active.scale * 100); $('#entSizeV').textContent = Math.round(active.scale * 100) + '%';
  const lit = isLight(active), isProp = active.kind === 'prop' && !lit, isChar = active.kind === 'mannequin', looked = isChar && !!active.params.look, hasMat = isChar ? !looked : active.kind !== 'import';
  const preset = isProp && active.params.mat !== 'plain';
  refreshLookUI();
  const show = (id, on) => { $('#' + id).style.display = on ? 'flex' : 'none'; };
  show('propSizeRow', isProp); show('colorRow', hasMat); show('matRow', hasMat && !lit && !preset); show('matRow2', hasMat && !lit && !preset); show('matPickRow', isProp);
  show('facingRow', !lit); show('scaleRow', !lit); for (const id of ['lightTypeRow', 'lightPowerRow', 'lightSizeRow', 'lightAimRow']) show(id, lit); show('lightSpreadRow', lit && active.params.type === 'spot');
  $('#entNote').textContent = lit ? 'Use Place to move the light. It shines at the point you aim it at; the render server draws its real soft shadows.' : 'Use Place in the viewport to move it. Models can be .glb, or .gltf and .fbx picked together with their texture images.';
  if (isProp) { ['pw', 'ph', 'pd'].forEach((id, i) => $('#' + id).value = active.params.size[i]); $('#matPick').value = active.params.mat || 'plain'; }
  if (lit) { const p = active.params; $('#lightType').value = p.type; $('#lightPower').value = p.power; $('#lightPowerV').textContent = Math.round(p.power) + ' W'; $('#lightSize').value = Math.round(p.lsize * 100); $('#lightSizeV').textContent = Math.round(p.lsize * 100) + ' cm';
    $('#lightSpread').value = p.spread; $('#lightSpreadV').textContent = Math.round(p.spread) + '°';
    const pick = $('#lightAim'); pick.textContent = ''; pick.append(new Option(p.target ? 'Aimed at ' + p.target.map(r1).join(', ') : 'Aimed straight down', ''), new Option('Straight down', 'down'));
    for (const c of ents) if (c.kind !== 'prop') pick.append(new Option(c.name, 'ent:' + c.id)); for (const c of ents) if (c.kind === 'prop' && !isLight(c)) pick.append(new Option(c.name, 'ent:' + c.id)); pick.value = ''; }
  if (hasMat) { $('#entColor').value = active.params.color || '#ffffff'; $('#matRough').value = Math.round(active.params.rough * 100); $('#matRoughV').textContent = Math.round(active.params.rough * 100) + '%'; $('#matMetal').value = Math.round(active.params.metal * 100); $('#matMetalV').textContent = Math.round(active.params.metal * 100) + '%'; }
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
$('#matPick').onchange = e => { if (!active || active.kind !== 'prop' || isLight(active)) return; pushUndo(); active.params.mat = e.target.value; refreshProp(active); refreshStageUI(); changed(); };
$('#lightType').onchange = e => { if (!isLight(active)) return; pushUndo(); active.params.type = e.target.value; refreshProp(active); refreshStageUI(); changed(); };
for (const [id, key, div, unit] of [['lightPower', 'power', 1, ' W'], ['lightSize', 'lsize', 100, ' cm'], ['lightSpread', 'spread', 1, '°']]) {
  $('#' + id).addEventListener('input', e => { if (!isLight(active)) return; placeBegin(); active.params[key] = +e.target.value / div; refreshProp(active); $('#' + id + 'V').textContent = e.target.value + unit; });
  $('#' + id).addEventListener('change', () => { placing = false; changed(); });
}
$('#lightAim').onchange = e => { if (!isLight(active)) return; const v = e.target.value; if (!v) return; pushUndo();
  if (v === 'down') active.params.target = null;
  else { const c = ents.find(x => 'ent:' + x.id === v); if (c) { const b = c.byName.get('head') || c.byName.get('chest') || c.bones[0]; active.params.target = b.obj.getWorldPosition(new V3()).toArray().map(r2); } }
  aimLight(active); refreshStageUI(); changed(); };
$('#addLight').onclick = () => { pushUndo(); const p = spot(); p[1] = 2.4; const e = addLight({ name: 'Light', type: 'area', pos: p }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); toast(e.name + ' added. Place it, then aim it at someone.'); };
for (const S of ['L', 'R']) $('#hand' + S).onchange = e => { if (!active || active.kind !== 'mannequin') return; pushUndo(); setHands(active, { [S]: e.target.value }); changed(); };
['pw', 'ph', 'pd'].forEach((id, i) => $('#' + id).onchange = e => { if (!active || active.kind !== 'prop') return; const v = clamp(+e.target.value || .1, .005, 50); pushUndo(); active.params.size[i] = v; refreshProp(active); changed(); });
$('#entColor').onchange = e => { if (!active || active.kind === 'import') return; pushUndo(); active.params.color = e.target.value; applyMaterial(active); changed(); };
// colour pickers have no "empty" state: a light shows its own colour there
const spot = () => { const t = orbit.target; return [r2(t.x), 0, r2(t.z)]; };
$('#addChar').onclick = () => { pushUndo(); const e = addMannequin({ pos: spot() }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); toast(e.name + ' added. Drag the arrows to place it.'); };
$('#addBox').onclick = () => { pushUndo(); const p = spot(); p[1] = .25; const e = addProp({ name: 'Box', shape: 'box', size: [.5, .5, .5], pos: p }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); };
$('#addCyl').onclick = () => { pushUndo(); const p = spot(); p[1] = .25; const e = addProp({ name: 'Cylinder', shape: 'cylinder', size: [.4, .5, .4], pos: p }); setActive(e); mode = 'place'; select(e.bones[0]); changed(); };
$('#dupEnt').onclick = () => { if (!active) return; if (active.kind === 'import') return toast('Imported models cannot be duplicated yet. Import the file again.');
  pushUndo(); const s = JSON.parse(JSON.stringify(specOf(active))); const e = makeEnt({ kind: s.kind, name: uniqueName(s.name), params: s.params });
  e.pos = [s.pos[0] + .6, s.pos[1], s.pos[2]]; e.rot = s.rot; e.scale = s.scale; applyPlacement(e); e.tracks = cleanTracks(e, s.tracks); ents.push(e); setActive(e); applyFrame(frame); changed(); };
$('#delEnt').onclick = () => { if (!active) return; pushUndo(); const n = active.name; removeEnt(active); refreshStageUI(); changed(); toast(n + ' deleted. Undo brings it back.'); };
$('#importBtn').onclick = () => $('#fileGlb').click();
$('#fileGlb').onchange = e => { const f = [...e.target.files]; e.target.value = ''; if (f.length) importModel(f, false); };
$('#fileLook').onchange = e => { const f = [...e.target.files]; e.target.value = ''; if (f.length) importModel(f, true); };
$('#lookReal').onclick = () => { if (!active || active.kind !== 'mannequin') return toast('Select a character first.'); $('#fileLook').click(); };
/* stored people to wear, from this browser and the studio */
export async function refreshLookPick() {
  const el = $('#lookPick'); if (!el) return; const all = (await libraryModels()).filter(m => m.rigged !== false);
  el.textContent = ''; const first = new Option(all.length ? 'Your people…' : 'No people yet', ''); el.append(first);
  for (const m of all) el.append(new Option(m.name + (m.here ? '' : ' (studio)'), m.hash));
  el.value = ''; el.disabled = !all.length || !active || active.kind !== 'mannequin';
}
$('#lookPick').onfocus = () => refreshLookPick();
$('#lookPick').onchange = async ev => {
  const hash = ev.target.value; if (!hash) return; ev.target.value = '';
  if (!active || active.kind !== 'mannequin') return toast('Select a character first.', true);
  const name = ev.target.selectedOptions[0] ? ev.target.selectedOptions[0].textContent.replace(/ \(studio\)$/, '') : 'Model';
  toast('Dressing ' + active.name + ' as ' + name + '…');
  const missing = await preloadModels([hash]); if (missing.length) return toast(name + ' could not be fetched. Check your studio connection.', true);
  try { pushUndo(); const e = swapLook(active, hash, name); toast(e.name + ' now looks like ' + name + '.'); refreshStageUI(); changed(); }
  catch (err) { undoStack.pop(); updateUndoUI(); toast(err.message, true); }
};
/* motion: pick a recorded movement and key it onto the selected character */
export async function refreshMotionUI(pick) {
  const el = $('#motionPick'); if (!el) return; const keep = pick || el.value, all = await listMotions();
  el.textContent = ''; if (!all.length) el.append(new Option('No motions yet', ''));
  for (const m of all) el.append(new Option(m.name + ' · ' + m.seconds.toFixed(1) + ' s', m.id));
  if (keep && all.some(m => m.id === keep)) el.value = keep;
  updateMotionNote();
}
function updateMotionNote() {
  const has = !!$('#motionPick').value, isChar = !!active && active.kind === 'mannequin';
  $('#motionApply').disabled = !has || !isChar;
  $('#motionNote').textContent = !has ? 'Import a file with recorded movement (an animated .fbx or .glb, such as a Renderpeople animated person or a Mixamo clip). It becomes ordinary keys you can edit.'
    : !isChar ? 'Select a character to put the motion on.' : 'Keys it onto ' + active.name + ' from frame ' + Math.round(frame) + '. Replace swaps out those bones\u2019 keys; Layer adds the movement on top of the pose that is there.';
}
$('#motionPick').onchange = updateMotionNote;
$('#motionPick').onfocus = () => refreshMotionUI();
$('#motionSpeed').oninput = ev => { $('#motionSpeedV').textContent = ev.target.value + '%'; };
$('#motionImport').onclick = () => $('#fileMotion').click();
$('#fileMotion').onchange = ev => { const f = [...ev.target.files]; ev.target.value = ''; if (f.length) importMotionFiles(f); };
$('#motionApply').onclick = async () => {
  const id = $('#motionPick').value; if (!id || !active || active.kind !== 'mannequin') return updateMotionNote();
  const m = await getMotion(id); if (!m) return toast('That motion could not be loaded.', true);
  pause(); pushUndo();
  try {
    const r = applyMotion(active, m, { start: Math.round(frame), parts: $('#motionParts').value, mode: $('#motionMode').value, speed: +$('#motionSpeed').value / 100, repeat: +$('#motionRepeat').value || 1, inPlace: $('#motionInPlace').checked });
    syncUI(); applyFrame(frame); changed(); refreshStageUI();
    toast(m.name + ' on ' + active.name + ', frames ' + r.start + '–' + r.end + '.' + (r.extended ? ' The timeline now runs to ' + r.end + '.' : ''));
  } catch (err) { undoStack.pop(); updateUndoUI(); toast(err.message, true); }
};
$('#lookMannequin').onclick = () => { if (!active || active.kind !== 'mannequin' || !active.params.look) return; pushUndo(); const e = swapLook(active, null); toast(e.name + ' is back to the mannequin.'); refreshStageUI(); changed(); };

/* ───────── camera, look and reference ───────── */
function camAt(f) {
  if (!camKeys.length) return null; if (f <= camKeys[0].f) return camKeys[0]; const last = camKeys[camKeys.length - 1]; if (f >= last.f) return last;
  let i = 0; while (camKeys[i + 1].f <= f) i++; const a = camKeys[i], c = camKeys[i + 1]; let t = (f - a.f) / (c.f - a.f); t = t * t * (3 - 2 * t);
  const L = (x, y) => x + (y - x) * t; return { p: a.p.map((v, k) => L(v, c.p[k])), t: a.t.map((v, k) => L(v, c.t[k])), fov: L(a.fov, c.fov), fstop: a.fstop };
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
for (const [id, key, div] of [['exposure', 'exposure', 100], ['sunAngle', 'sunAngle', 1], ['sunHeight', 'sunHeight', 1], ['sunPower', 'sunPower', 100], ['envPower', 'env', 100], ['skyTurn', 'skyTurn', 1], ['haze', 'haze', 100]])
  $('#' + id).addEventListener('input', e => { look[key] = +e.target.value / div; applyLook(); changed(); });
$('#skyPick').onchange = e => { pushUndo(); look.sky = e.target.value; applyLook(); changed(); };
$('#floorPick').onchange = e => { pushUndo(); look.floor = e.target.value; applyLook(); changed(); };
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
  try { const o = JSON.parse(await f.text()); if (!o || o.app !== 'rigroom') throw 0; await preloadForScene(o); pushUndo(); const sk = loadSceneObject(o); toast(sk ? ('Opened. ' + sk + ' imported model(s) were not in the file; import them again.') : 'Project opened.'); }
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
  const list = []; for (const e of ents) for (const n of Object.keys(e.tracks)) { const b = e.byName.get(n); if (b) list.push({ obj: b.obj, Q: [], P: b.isRoot ? [] : null }); }
  for (const e of ents) if (e.look) for (const m of e.look.entries) list.push({ obj: m.dst, Q: [], P: m.dst === e.look.hips.dst ? [] : null });
  const times = [];
  for (let f = 0; f <= anim.length; f++) { evaluate(f); times.push(f / anim.fps); for (const x of list) { x.Q.push(...x.obj.quaternion.toArray()); if (x.P) x.P.push(...x.obj.position.toArray()); } }
  const tracks = []; for (const x of list) { tracks.push(new THREE.QuaternionKeyframeTrack(x.obj.uuid + '.quaternion', times, x.Q)); if (x.P) tracks.push(new THREE.VectorKeyframeTrack(x.obj.uuid + '.position', times, x.P)); }
  evaluate(0); return new THREE.AnimationClip('RigroomAction', anim.length / anim.fps, tracks);
}
export function exportGLB(opts) {
  const animated = !opts || opts.animated !== false;
  return new Promise((res, rej) => { pause(); const keep = frame; let clip = null;
    if (animated) { try { clip = bakeClip(); } catch (e) { return rej(e); } } else evaluate(keep);
    stage.updateMatrixWorld(true);
    const lit = ents.filter(isLight); lit.forEach(e => { e.group.visible = false; }); const back = () => { lit.forEach(e => { e.group.visible = true; }); applyFrame(keep); };
    new GLTFExporter().parse(stage, out => { back(); res(out); }, err => { back(); rej(err); }, { binary: true, maxTextureSize: 2048, animations: clip && clip.tracks.length ? [clip] : [] }); });
}
// the shot camera at a frame, or the free view when no camera is keyed
export function cameraAt(f) { const k = camAt(f); return k ? { p: k.p.slice(), t: k.t.slice(), fov: k.fov, ...(k.fstop ? { fstop: k.fstop } : {}) } : { p: camera.position.toArray(), t: orbit.target.toArray(), fov: camera.fov }; }
export function frameAspect() { return ref.url && shotView ? ref.aspect : (camKeys.length ? (ref.url ? ref.aspect : 16 / 9) : camera.aspect); }
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
function setOverlays(on) { overlaysOn = on; for (const e of ents) if (e.gizmo) e.gizmo.visible = on; handles.visible = on; if (boneLines) boneLines.visible = on; grid.visible = on; tcHelper.visible = on; if (!on) tc.detach(); }

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
function entInfo(e) { if (isLight(e)) { const p = e.params; return { name: e.name, kind: 'light', type: p.type, position: e.pos.map(r2), target: p.target ? p.target.map(r2) : 'straight down', power_watts: p.power, color: p.color, size: p.lsize, spread: p.type === 'spot' ? p.spread : undefined }; }
  const o = { name: e.name, kind: e.kind === 'prop' ? 'prop' : 'character', position: e.pos.map(r2) };
  if (e.kind === 'prop') { o.shape = e.params.shape; o.size = e.params.size.map(r2); o.rotation = e.rot.map(r1); } else { o.facing = r1(e.rot[1]); o.scale = r2(e.scale); o.rig = e.kind === 'mannequin' ? 'mannequin' : 'imported (' + e.bones.length + ' bones)'; }
  if (e.kind === 'prop' && e.params.mat !== 'plain') o.material = { preset: e.params.mat, color: e.params.color };
  else if (e.kind === 'prop' || (e.kind === 'mannequin' && !e.params.look)) o.material = { color: e.params.color, roughness: e.params.rough, metalness: e.params.metal };
  if (e.kind === 'mannequin') { o.look = e.params.look ? e.params.lookName : 'mannequin'; if (e.params.look) o.hands = { left: (e.params.hands && e.params.hands.L) || 'relaxed', right: (e.params.hands && e.params.hands.R) || 'relaxed' }; }
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
    input_schema: { type: 'object', required: ['shape', 'size', 'position'], properties: { name: { type: 'string' }, shape: { type: 'string', enum: ['box', 'cylinder', 'sphere'] }, size: A3, position: A3, rotation: A3, color: { type: 'string' }, material: { type: 'string', enum: Object.keys(MATS) }, roughness: { type: 'number' }, metalness: { type: 'number' } } },
    execute(i) { if (!num3(i.size) || !num3(i.position)) throw new Error('size and position must each be three numbers'); mutate();
      const e = addProp({ name: i.name || i.shape, shape: i.shape, size: i.size.map(v => clamp(Math.abs(v), .005, 50)), pos: i.position, rot: num3(i.rotation, [0, 0, 0]), color: isHex(i.color) ? i.color : undefined, mat: i.material, rough: isFinite(i.roughness) ? clamp(+i.roughness, 0, 1) : undefined, metal: isFinite(i.metalness) ? clamp(+i.metalness, 0, 1) : undefined }); act('added prop ' + e.name); return entInfo(e); } },
  { name: 'add_light', description: 'Add a light. type "area" (a soft panel, the usual choice: bigger size gives softer shadows), "spot" (a cone, spread in degrees) or "point" (a bare bulb). position and target are scene-space points; without a target it shines straight down. power is in watts (a key light 1.5 m from a face: 150 to 400; a fill: 40 to 120). color is hex: warm lamp #ffd9b0, daylight #dfe9ff. size is the panel or bulb width in meters.',
    input_schema: { type: 'object', required: ['position'], properties: { name: { type: 'string' }, type: { type: 'string', enum: LIGHT_TYPES }, position: A3, target: A3, power: { type: 'number' }, color: { type: 'string' }, size: { type: 'number' }, spread: { type: 'number' } } },
    execute(i) { if (!num3(i.position)) throw new Error('position must be three numbers'); mutate();
      const e = addLight({ name: i.name, type: i.type, pos: i.position.map(Number), target: i.target, power: i.power, color: isHex(i.color) ? i.color : undefined, size: i.size, spread: i.spread }); refreshStageUI(); act('added light ' + e.name); return entInfo(e); } },
  { name: 'place', description: 'Move, turn, resize, recolor or change the material of a character, prop or light where it stands (not animated). Give only the fields to change. material is a preset for props; roughness and metalness (0 to 1) apply to the "plain" material. For lights: target, power (watts), light_type, light_size (meters), spread (degrees), color.',
    input_schema: { type: 'object', required: ['name'], properties: { name: { type: 'string' }, position: A3, facing: { type: 'number' }, rotation: A3, scale: { type: 'number' }, size: A3, color: { type: 'string' }, material: { type: 'string', enum: Object.keys(MATS) }, roughness: { type: 'number' }, metalness: { type: 'number' }, target: A3, power: { type: 'number' }, light_type: { type: 'string', enum: LIGHT_TYPES }, light_size: { type: 'number' }, spread: { type: 'number' }, rename: { type: 'string' } } },
    execute(i) { const e = needEnt(i.name); mutate();
      if (num3(i.position)) e.pos = i.position.map(Number); if (num3(i.rotation)) e.rot = i.rotation.map(Number); if (isFinite(i.facing)) e.rot[1] = +i.facing;
      if (isFinite(i.scale) && e.kind !== 'prop') e.scale = clamp(+i.scale, .05, 20); applyPlacement(e);
      if (e.kind !== 'import') { if (isHex(i.color)) e.params.color = i.color; if (isFinite(i.roughness)) e.params.rough = clamp(+i.roughness, 0, 1); if (isFinite(i.metalness)) e.params.metal = clamp(+i.metalness, 0, 1); }
      if (e.kind === 'prop' && !isLight(e)) { if (num3(i.size)) e.params.size = i.size.map(v => clamp(Math.abs(v), .005, 50)); if (i.material in MATS) e.params.mat = i.material; }
      if (isLight(e)) { const p = e.params; if (num3(i.target)) p.target = i.target.map(Number); if (isFinite(i.power)) p.power = +i.power; if (LIGHT_TYPES.includes(i.light_type)) p.type = i.light_type; if (isFinite(i.light_size)) p.lsize = +i.light_size; if (isFinite(i.spread)) p.spread = +i.spread; }
      applyMaterial(e);
      if (i.rename) e.name = uniqueName(String(i.rename).slice(0, 40), e);
      act('placed ' + e.name); return entInfo(e); } },
  { name: 'remove', description: 'Remove a character or prop from the stage.',
    input_schema: { type: 'object', required: ['name'], properties: { name: { type: 'string' } } },
    execute(i) { const e = needEnt(i.name); mutate(); const n = e.name; removeEnt(e); act('removed ' + n); return { removed: n }; } },
  { name: 'set_camera', description: 'Key the shot camera at a frame: position and target in scene space, fov in degrees. Several keys make a camera move; two keys one frame apart make a cut. fstop (optional, 1.4 to 16) blurs what is nearer or farther than the target in render-server renders: 2 for a close-up, 5.6 for a wide shot. The user sees the framing in Shot view.',
    input_schema: { type: 'object', required: ['position', 'target'], properties: { frame: { type: 'integer' }, position: A3, target: A3, fov: { type: 'number' }, fstop: { type: 'number' } } },
    execute(i) { if (!num3(i.position) || !num3(i.target)) throw new Error('position and target must each be three numbers'); mutate();
      const f = clamp(Math.round(+i.frame || 0), 0, anim.length), k = { f, p: i.position.map(Number), t: i.target.map(Number), fov: clamp(+i.fov || 35, 10, 90), ...(isFinite(i.fstop) && i.fstop > 0 ? { fstop: clamp(+i.fstop, .7, 32) } : {}) };
      const x = camKeys.findIndex(c => c.f >= f); if (x < 0) camKeys.push(k); else if (camKeys[x].f === f) camKeys[x] = k; else camKeys.splice(x, 0, k);
      wantShot = true; act('camera keyed at frame ' + f); return { camera_keys: camKeys.length }; } },
  { name: 'set_lighting', description: 'Change the overall lighting: exposure (0.2 to 2), sun angle in degrees around the scene, sun height in degrees above the horizon, sun power (0 to 3; 0 turns the sun off for interiors lit by lights), ambient (0 to 2, the strength of the environment), environment (the surroundings that light the scene: "soft" even grey, or a photographed "studio", "interior", "courtyard", "city", "forest", "sunrise", "sunset", "night"), environment_turn in degrees, floor ("matte", "wood", "concrete", "tiles", "carpet"), and haze (0 to 1: smoke or dust in the air, which makes light beams visible and softens the distance; 0.2 to 0.4 suits a bar).',
    input_schema: { type: 'object', properties: { exposure: { type: 'number' }, sun_angle: { type: 'number' }, sun_height: { type: 'number' }, sun_power: { type: 'number' }, ambient: { type: 'number' }, environment: { type: 'string', enum: SKIES }, environment_turn: { type: 'number' }, floor: { type: 'string', enum: Object.keys(FLOORS) }, haze: { type: 'number' } } },
    execute(i) { i = i || {}; mutate();
      if (isFinite(i.exposure)) look.exposure = clamp(+i.exposure, .2, 2); if (isFinite(i.sun_angle)) look.sunAngle = clamp(+i.sun_angle, -180, 180); if (isFinite(i.sun_height)) look.sunHeight = clamp(+i.sun_height, 5, 85);
      if (isFinite(i.sun_power)) look.sunPower = clamp(+i.sun_power, 0, 3); if (isFinite(i.ambient)) look.env = clamp(+i.ambient, 0, 2);
      if (SKIES.includes(i.environment)) look.sky = i.environment; if (isFinite(i.environment_turn)) look.skyTurn = clamp(+i.environment_turn, -180, 180); if (i.floor in FLOORS) look.floor = i.floor; if (isFinite(i.haze)) look.haze = clamp(+i.haze, 0, 1); applyLook(); act('lighting changed'); return { ...look }; } },
  { name: 'list_looks', description: 'List the human models stored on this device that characters can wear.',
    input_schema: { type: 'object', properties: {} },
    async execute() { const m = (await libraryModels()).filter(x => x.rigged !== false); return { looks: m.map(x => x.name), note: m.length ? undefined : 'No models yet. The user adds them with Stage → Look → Real model.' }; } },
  { name: 'set_look', description: 'Dress a character in one of the stored human models (by name from list_looks), or "mannequin" to go back. The character keeps its position, animation and bone names.',
    input_schema: { type: 'object', required: ['character', 'look'], properties: { character: { type: 'string' }, look: { type: 'string' } } },
    async execute(i) { const e = needEnt(i.character); if (e.kind !== 'mannequin') throw new Error(e.name + ' is not a character.');
      if (/^mannequin$/i.test(String(i.look).trim())) { mutate(); swapLook(e, null); act(e.name + ' back to mannequin'); return { character: e.name, look: 'mannequin' }; }
      const all = await libraryModels(), n = String(i.look).toLowerCase(), m = all.find(x => x.name.toLowerCase() === n) || all.find(x => x.name.toLowerCase().includes(n));
      if (!m) throw new Error('No stored look called "' + i.look + '". Stored looks: ' + (all.map(x => x.name).join(', ') || 'none'));
      const miss = await preloadModels([m.hash]); if (miss.length) throw new Error(m.name + ' is in the studio but could not be fetched.');
      mutate(); swapLook(e, m.hash, m.name); act(e.name + ' now wears ' + m.name); return { character: e.name, look: m.name }; } },
  { name: 'set_hands', description: 'Pose the fingers of a character that wears a look: left and right each "relaxed" (default), "open" (flat), "grip" (holding something), "fist" or "point". Hands are a setting on the character, not keyframes.',
    input_schema: { type: 'object', required: ['character'], properties: { character: { type: 'string' }, left: { type: 'string', enum: HAND_POSES }, right: { type: 'string', enum: HAND_POSES } } },
    execute(i) { const e = needEnt(i.character); if (e.kind !== 'mannequin' || !e.params.look) throw new Error(e.name + ' does not wear a look, so it has no fingers to pose.');
      mutate(); setHands(e, { L: i.left, R: i.right }); refreshStageUI(); act(e.name + ' hands posed'); return entInfo(e); } },
  { name: 'list_motions', description: 'List the recorded motions (motion capture) the user has imported: name and length in seconds.',
    input_schema: { type: 'object', properties: {} },
    async execute() { const m = await listMotions(); return { motions: m.map(x => ({ name: x.name, seconds: x.seconds })), note: m.length ? undefined : 'No motions yet. The user adds them with Pose → Motion → Import motion.' }; } },
  { name: 'apply_motion', description: 'Key a recorded motion onto a character, as ordinary keyframes you can then read and edit. frame is where it starts (default 0). parts: "body" (default), "upper", "arms", "lower" (hips and legs) or "head", or a list of bone names. mode "replace" (default) swaps out those bones\' keys over the span; "layer" adds the motion\'s movement on top of the keys already there. from/to pick seconds within the motion; speed 1 is as recorded; repeat plays it several times (a walk keeps travelling); in_place takes out the forward travel. The timeline grows to fit.',
    input_schema: { type: 'object', required: ['character', 'motion'], properties: { character: { type: 'string' }, motion: { type: 'string' }, frame: { type: 'integer' }, parts: {}, mode: { type: 'string', enum: ['replace', 'layer'] }, from: { type: 'number' }, to: { type: 'number' }, speed: { type: 'number' }, repeat: { type: 'integer' }, in_place: { type: 'boolean' } } },
    async execute(i) { const e = needEnt(i.character); if (e.kind !== 'mannequin') throw new Error(e.name + ' is not a character.');
      const m = await findMotion(i.motion); if (!m) { const all = await listMotions(); throw new Error('No motion called "' + i.motion + '". Motions: ' + (all.map(x => x.name).join(', ') || 'none')); }
      mutate(); const r = applyMotion(e, m, { start: i.frame, parts: i.parts, mode: i.mode, from: i.from, to: i.to, speed: i.speed, repeat: i.repeat, inPlace: i.in_place });
      evaluate(frame); act(m.name + ' on ' + e.name + ', frames ' + r.start + '-' + r.end);
      return { character: e.name, motion: m.name, frames: [r.start, r.end], keys: r.keys, note: r.extended ? 'Timeline extended to ' + r.end + ' frames.' : undefined }; } },
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
LOOKS: a character can wear a look, a real human model. Its controls do not change: you still pose the mannequin bones above, with the same names and the same cheat sheet, and the model follows them. A character wearing a look has the model's proportions, so its arm, leg and seat heights differ a little from the numbers above; use get_rig and get_joint_positions when exact heights matter. Use list_looks and set_look to change what a character wears.
LIGHTING AND MATERIALS, for photoreal renders (the viewport is a preview; the render server draws the real thing): light a scene like a film set. Pick an environment with set_lighting, then add lights with add_light: a key light (large area light to one side of the camera, above head height, aimed at the main character's head), a weaker fill from the other side, and a rim light behind and above to separate people from the background. For interiors turn the sun off (sun_power 0), use the "interior" or "studio" environment at ambient 0.3 to 0.6, and put warm area lights where real lamps would be. Give props a material preset (wood, leather, fabric, velvet, stone, brick, plaster, metal, paper, glass, plastic, ceramic, glow, neon) with add_prop or place: the renderer adds grain, pores, bumps and rounded edges; "glow" makes a prop shine like a lampshade and "neon" like a neon tube: put them in the background of a shot for depth. Use set_hands so held objects are gripped and resting hands are relaxed.
MOTIONS: the user can import recorded movement (motion capture: walks, idles, dances). list_motions shows them and apply_motion keys one onto any character, retargeted to that body. Prefer a recorded motion over hand keys when one fits the request, then refine with set_keyframes: for example apply a walk with parts "lower" and pose the arms yourself, or layer an idle over a seated pose. Recorded motions are keyed every frame or two, so edit them by changing whole spans rather than single frames.
Imported models that are not characters have their own bone names: call get_rig and work from each bone's rest direction.

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
  const list = ents.slice(0, 40).map(e => isLight(e) ? `${e.name} (${e.params.type} light ${Math.round(e.params.power)} W at ${e.pos.map(r2).join(',')})` : e.kind === 'prop' ? `${e.name} (${e.params.shape} ${e.params.size.map(r2).join('x')}${e.params.mat && e.params.mat !== 'plain' ? ' ' + e.params.mat : ''} at ${e.pos.map(r2).join(',')})` : `${e.name} (${e.kind === 'mannequin' ? (e.params.look ? 'character wearing ' + e.params.lookName : 'mannequin') : 'imported model'} at ${e.pos.map(r2).join(',')} facing ${r1(e.rot[1])}${Object.keys(e.tracks).length ? ', animated' : ''})`);
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
  for (const e of ents) if (e.look) retarget(e);
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
