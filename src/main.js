// Entry point: wires the modules together and opens the booth scene.
import * as THREE from 'three';
import * as app from './app.js';
import { initAgent, addMsg } from './agent.js';
import { initTrace } from './trace.js';
import { initServer } from './server.js';

const V3 = THREE.Vector3;

/* The booth scene: a 3D blockout of the milestone sketch. */
export function buildBooth() {
  app.clearStage();
  Object.assign(app.anim, { length: 96, fps: 24, loop: true, ease: 'spline' });
  const wood = '#8a6a4f', seat = '#70494b', stone = '#b9b3a6', metal = '#4a4f58';
  const P = (name, shape, size, pos, color, rot, rough, met) => app.addProp({ name, shape, size, pos, color, rot, rough, metal: met });
  P('Table top', 'box', [1.5, .05, .8], [0, .745, 0], wood, null, .45); P('Table leg', 'cylinder', [.1, .7, .1], [0, .37, 0], metal, null, .35, .9); P('Table foot', 'cylinder', [.5, .04, .5], [0, .02, 0], metal, null, .35, .9);
  P('Bench left', 'box', [.5, .45, 1.5], [-1.15, .225, -.15], seat, null, .6); P('Bench left back', 'box', [.14, 1, 1.5], [-1.47, .5, -.15], seat, null, .6);
  P('Bench right', 'box', [.5, .45, 1.5], [1.15, .225, -.15], seat, null, .6); P('Bench right back', 'box', [.14, 1, 1.5], [1.47, .5, -.15], seat, null, .6);
  P('Bench rear', 'box', [1.8, .45, .5], [0, .225, -.75], seat, null, .6); P('Bench rear back', 'box', [3.08, 1, .14], [0, .5, -1.07], seat, null, .6);
  P('Column left', 'cylinder', [.62, 3.6, .62], [-1.8, 1.8, -1.9], stone); P('Column left base', 'box', [.9, .5, .9], [-1.8, .25, -1.9], stone);
  P('Column right', 'cylinder', [.62, 3.6, .62], [1.8, 1.8, -1.9], stone); P('Column right base', 'box', [.9, .5, .9], [1.8, .25, -1.9], stone);
  P('Back wall', 'box', [7, 3.6, .1], [0, 1.8, -2.5], '#8f8a80');
  P('Paper', 'box', [.21, .28, .006], [.12, 1.0, -.27], '#e9e6dc', [-28, 0, 0]); P('Phone', 'box', [.07, .14, .012], [-.43, .93, .03], '#2b2e36', [-15, 90, 0], .25, .3);
  const K = (e, f, map) => { for (const [bone, v] of Object.entries(map)) { const b = e.byName.get(bone); Array.isArray(v) ? app.writeKey(e, b, f, v, null) : app.writeKey(e, b, f, v.rot, v.pos); } };
  const R = (e, f, bone, t, pole) => { app.evaluateEnt(e, f); const ch = app.reach(e.byName.get(bone), new V3(...t), pole ? new V3(...pole) : null, false); ch.forEach(x => app.keyCurrent(x, f)); };
  const sit = { hips: { rot: [0, 0, 0], pos: [0, -.4, 0] }, thigh_L: [-88, 0, 6], thigh_R: [-88, 0, -6], shin_L: [84, 0, 0], shin_R: [84, 0, 0] };
  // Bram: left bench, leaning in on the table with a phone
  const bram = app.addMannequin({ name: 'Bram', pos: [-1.12, 0, .12], facing: 90, color: '#b59f86' });
  K(bram, 0, sit); K(bram, 0, { spine: [18, 0, 0], chest: [10, 0, 0], neck: [-6, 0, 0], head: [-4, -18, 0], thigh_R: [-78, 0, -10], shin_R: [38, 0, 0] });
  R(bram, 0, 'hand_L', [-.47, .9, -.02]); R(bram, 0, 'hand_R', [-.5, .8, .24]);
  [[0, 0], [48, 3], [96, 0]].forEach(([f, d]) => K(bram, f, { chest: [10 + d, 0, 0], head: [-4, -18 + d * 2, 0] }));
  // Victor: standing behind the booth, looking down at the table
  const victor = app.addMannequin({ name: 'Victor', pos: [-.52, 0, -1.5], facing: 0, scale: 1.12, color: '#8894aa' });
  K(victor, 0, { upperArm_L: [0, 0, -78], upperArm_R: [0, 0, 78], forearm_L: [0, -12, 0], forearm_R: [0, 12, 0], chest: [4, 10, 0] });
  [[0, [16, 24, 0]], [40, [20, 30, 3]], [96, [16, 24, 0]]].forEach(([f, r]) => K(victor, f, { head: r }));
  // Ines: rear bench, holding a sheet of paper
  const ines = app.addMannequin({ name: 'Ines', pos: [.12, 0, -.74], facing: 0, scale: .97, color: '#c29a9c' });
  K(ines, 0, sit); K(ines, 0, { spine: [6, 0, 0], chest: [4, 0, 0] });
  R(ines, 0, 'hand_L', [.25, .96, -.3]); R(ines, 0, 'hand_R', [-.01, .96, -.3]);
  [[0, [14, 0, 0]], [30, [4, -26, 0]], [70, [6, -24, -3]], [96, [14, 0, 0]]].forEach(([f, r]) => K(ines, f, { head: r }));
  // Rosa: right bench, one finger raised, making her point
  const rosa = app.addMannequin({ name: 'Rosa', pos: [1.12, 0, .12], facing: -90, color: '#a3b392' });
  K(rosa, 0, sit); K(rosa, 0, { spine: [2, 0, 0], chest: [0, 0, 0], head: [-6, 10, 0] });
  R(rosa, 0, 'hand_L', [.52, .8, .26]);
  [[0, [.74, 1.4, -.05]], [12, [.69, 1.47, -.05]], [24, [.75, 1.39, -.05]], [36, [.69, 1.46, -.05]], [48, [.74, 1.4, -.05]], [72, [.72, 1.43, -.05]], [96, [.74, 1.4, -.05]]].forEach(([f, t]) => R(rosa, f, 'hand_R', t, [.2, -1, -.3]));
  [[0, [-6, 10, 0]], [24, [-2, 14, 0]], [60, [-8, 6, 0]], [96, [-6, 10, 0]]].forEach(([f, r]) => K(rosa, f, { head: r }));
  app.camKeys.push({ f: 0, p: [0.1, 1.3, 4.9], t: [0.05, 0.95, -0.5], fov: 30 });
  app.setRef('sketch', app.SKETCH_URL, app.SKETCH_ASPECT);
  app.setActive(rosa); app.applyFrame(0); app.frameCameraToShot(); app.syncUI(); app.changed(); app.setPlayIcon();
}

document.querySelector('#boothBtn').onclick = () => { app.pushUndo(); buildBooth(); app.toast('Booth scene loaded.'); };
initAgent(); initTrace(); initServer();

// the saved scene may use human models kept in this browser; load them before building it
let saved = null, missingModels = 0;
try { const s = localStorage.getItem('rigroom.v3'); if (s) { const o = JSON.parse(s); if (o && o.app === 'rigroom' && Array.isArray(o.ents) && o.ents.length) saved = o; } } catch (e) { /* start fresh */ }
if (saved) { try { missingModels = await app.preloadForScene(saved); } catch (e) { /* show mannequins instead */ } }

app.start(() => {
  let restored = false;
  if (saved) { try { app.loadSceneObject(saved); restored = true; } catch (e) { /* start fresh */ } }
  if (missingModels) app.toast(missingModels + ' model(s) in this scene are not stored in this browser, so mannequins stand in for them.', true);
  if (!restored) { buildBooth(); addMsg('agent', 'This is your booth sketch blocked out in 3D: Bram, Victor, Ines and Rosa around the table. Turn on Shot view in Project to see the drawing over it. Tell me what should move.'); }
  else addMsg('agent', 'Your last scene is back on stage. Tell me what to change.');
});

// test hook for automated checks; harmless in normal use
window.__rigroom = { app, buildBooth };
