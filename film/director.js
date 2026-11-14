// Rigroom film director: turns spoken lines into a filmed scene.
// Runs inside the app page after the posing helpers (key, look, reach, headOf, jp, V, TH) with:
//   data = { lines: [{ id, n, speaker, seconds, env, narration }],   (a narration is heard over the picture; nobody's mouth moves) cast: { Name: { jaw, hand, handBase } }, cams: { name: { p, t, fov, fstop } },
//            shotFor: { Speaker: camName }, cutaways: { Speaker: [camName, ...] }, addressee: { Speaker: [names] }, lead, gap, tail, fps,
//            offstage: { Voice: [x,y,z] }   a voice with no body on stage (a broadcast): people look at that point,
//            shotForLine / cutawaysForLine: { lineId: ... }, lineGaze: { lineId: { listeners: name|point, speaker: [name|point] } },
//            noGesture: [lineIds], speakerPower: { lineId: watts }, prepare(cues, F): keys of its own (standing up, leaving) made first }
// It keys: jaws from each line's loudness, blinks, who looks at whom, breathing, small hand gestures, and one camera per shot.
// It returns { length, cues: [{ n, t }], shots: [{ f, cam }], speakers: [{ n, f0, f1, head }] } and leaves the keys on the scene.
const fps = data.fps || 24, F = s => Math.round(s * fps);
let seedN = 20261113; const rnd = () => (seedN = (seedN * 1664525 + 1013904223) >>> 0) / 4294967296;
const names = Object.keys(data.cast);
const baseEuler = (name, bone) => { const tr = by(name).tracks[bone], q = tr && tr.length ? new TH.Quaternion(...tr[0].q) : new TH.Quaternion(); const e = new TH.Euler().setFromQuaternion(q, 'XYZ'); return [e.x, e.y, e.z].map(v => v * 180 / Math.PI); };

// 1. when each line is spoken
let t = data.lead; const cues = [];
for (const l of data.lines) { cues.push({ id: l.id || String(l.n).padStart(3, '0'), n: l.n, t: +t.toFixed(3), f0: F(t), f1: F(t + l.seconds), speaker: l.speaker, narration: !!l.narration }); t += l.seconds + (l.gap ?? data.gap); }
const first = cues.find(c => !c.narration) || cues[0];   // the first spoken line: the opening is timed back from it
const length = F(t - data.gap + data.tail);
A.anim.length = Math.max(A.anim.length, length); A.anim.fps = fps; A.anim.loop = false;
const onStage = n => names.includes(n);
if (data.prepare) data.prepare(cues, F);   // big moves first, so heads and eye lines below follow them

// 2. jaws: the mouth opens with the loudness of the voice
for (const [i, l] of data.lines.entries()) { if (l.narration || !onStage(l.speaker)) continue;
  const c = cues[i], amp = (data.cast[l.speaker] || {}).jaw ?? 5, keys = [{ bone: 'jaw', frame: Math.max(0, c.f0 - 2), rot: [0, 0, 0] }];
  let prev = 0;
  for (let k = 0; k < l.env.length; k += 2) {
    const e = Math.max(l.env[k], l.env[k + 1] ?? 0), open = Math.pow(Math.max(0, (e - .1) / .9), .7) * amp, v = prev * .35 + open * .65; prev = v;
    keys.push({ bone: 'jaw', frame: c.f0 + k, rot: [+v.toFixed(2), 0, 0] });
  }
  keys.push({ bone: 'jaw', frame: c.f1 + 3, rot: [0, 0, 0] });
  T('set_keyframes').execute({ character: l.speaker, keys });
}

// 3. blinks, a few seconds apart, each character on their own rhythm
for (const n of names) { const keys = []; let f = Math.round(20 + rnd() * 60);
  while (f < length - 6) { keys.push({ bone: 'lids', frame: f - 2, rot: [0, 0, 0] }, { bone: 'lids', frame: f, rot: [26, 0, 0] }, { bone: 'lids', frame: f + 3, rot: [0, 0, 0] }); f += Math.round(fps * (2.2 + rnd() * 4)); }
  T('set_keyframes').execute({ character: n, keys }); }

// 4. breathing: the chest rises and settles
for (const n of names) { const b = baseEuler(n, 'chest'), keys = [], period = Math.round(fps * (3.4 + rnd() * 1.2)); let up = rnd() > .5;
  for (let f = Math.round(rnd() * period); f < length; f += Math.round(period / 2)) { keys.push({ bone: 'chest', frame: f, rot: [b[0] + (up ? -.9 : .5), b[1], b[2]] }); up = !up; }
  T('set_keyframes').execute({ character: n, keys }); }

// 5. eyes on the speaker: listeners turn to whoever speaks, the speaker looks at who they address
const gaze = {}; for (const n of names) gaze[n] = [];
const spotOf = x => Array.isArray(x) ? { point: x } : onStage(x) ? { target: x } : data.offstage && data.offstage[x] ? { point: data.offstage[x] } : null;
const lookAtName = (who, target, f, amount) => { const sp = spotOf(target); if (sp && who !== target) gaze[who].push({ f, ...sp, amount }); };
for (const g of data.opening || []) gaze[g.who].push({ f: g.before != null ? Math.max(0, first.f0 - g.before) : g.f, point: g.point, target: g.target, amount: g.amount });
for (const [i, l] of data.lines.entries()) { if (l.narration) continue; const c = cues[i], lg = (data.lineGaze || {})[c.id] || {};
  for (const n of names) if (n !== l.speaker) lookAtName(n, lg.listeners ?? l.speaker, c.f0 + Math.round(2 + rnd() * 10), .92);
  if (!onStage(l.speaker)) continue;
  const to = lg.speaker || data.addressee[l.speaker] || names.filter(x => x !== l.speaker);
  // the speaker's eyes move between the people they address, every few seconds
  let f = Math.max(0, c.f0 - 6), k = Math.floor(rnd() * to.length);
  while (f < c.f1) { lookAtName(l.speaker, to[k % to.length], f, .9); k++; f += Math.round(fps * (3 + rnd() * 3)); } }
for (const n of names) { gaze[n].sort((a, b) => a.f - b.f); let last = -99;
  for (const g of gaze[n]) { const f = Math.max(g.f, last + 14), pt = g.point || headOf2(g.target, f);
    if (f > 0) holdHead(n, f - 1);        // hold where the head was, then turn over half a second
    look(n, pt, f + 11, g.amount ?? 1); last = f + 11; } }
function headOf2(name, f) { A.applyFrame(f); return by(name).byName.get('head').obj.getWorldPosition(V(0, 0, 0)).toArray(); }
function holdHead(name, f) { A.applyFrame(f); const e = by(name), keys = [];
  for (const b of ['neck', 'head']) { const q = e.byName.get(b).obj.quaternion, eu = new TH.Euler().setFromQuaternion(q, 'XYZ'); keys.push({ bone: b, frame: f, rot: [eu.x, eu.y, eu.z].map(v => +(v * 180 / Math.PI).toFixed(2)) }); }
  T('set_keyframes').execute({ character: name, keys }); }

// 6. hands: the speaker lifts a hand as a thought begins
for (const [i, l] of data.lines.entries()) { if (l.narration || (data.noGesture || []).includes(cues[i].id)) continue; const c = cues[i], cfg = data.cast[l.speaker] || {}; if (!cfg.hand || !cfg.handBase) continue;
  const beats = []; for (let f = c.f0 + 8; f < c.f1 - 30; f += Math.round(fps * (3.5 + rnd() * 3))) beats.push(f);
  for (const f of beats) { const up = cfg.handBase.map((v, k) => v + (cfg.handLift || [0, .1, 0])[k] * (.7 + rnd() * .6));
    reach(l.speaker, cfg.hand, cfg.handBase, f - 8, cfg.pole); reach(l.speaker, cfg.hand, up, f + 2, cfg.pole); reach(l.speaker, cfg.hand, up.map((v, k) => v + (k === 1 ? -.02 : 0)), f + 16, cfg.pole); reach(l.speaker, cfg.hand, cfg.handBase, f + 30, cfg.pole); } }

// 7. the camera: one shot at a time, cut on the line
const shots = [];
const addShot = (f, cam) => { if (shots.length && shots[shots.length - 1].f >= f) return; if (shots.length && shots[shots.length - 1].cam === cam) return; shots.push({ f, cam }); };
for (const s of data.openingShots || []) addShot(s.f, s.cam);
for (const [i, l] of data.lines.entries()) { const c = cues[i];
  if (l.narration) {   // while the narrator sets the scene, the camera looks around it
    const list = (data.narrationShots && (data.narrationShots[c.id] || data.narrationShots.default)) || ['wide'], each = (c.f1 - c.f0 + F(l.gap ?? data.gap)) / list.length;
    list.forEach((cam, k) => addShot(Math.max(0, Math.round(c.f0 - (k ? 0 : 4) + k * each)), cam)); continue; }
  const main = (data.shotForLine || {})[c.id] || data.shotFor[l.speaker] || 'wide', cuts = (data.cutawaysForLine || {})[c.id] || data.cutaways[l.speaker] || ['wide'];
  addShot(Math.max(0, c.f0 - 4), main);
  const dur = c.f1 - c.f0;
  if (dur > fps * 9) { const n = Math.min(7, Math.max(1, Math.floor(dur / (fps * 11))));   // a long speech gets a cutaway every ten seconds or so
    for (let k = 0; k < n; k++) { const at = c.f0 + Math.round(dur * (n === 1 ? .45 : (.18 + .7 * k / (n - 1)))), len = Math.round(fps * (2.4 + rnd() * 1.2)); addShot(at, cuts[(i + k) % cuts.length]); addShot(at + len, main); } } }
for (const s of data.closingShots || []) addShot(length - s.before, s.cam);
A.ctx.camKeys.length = 0;
for (const [i, s] of shots.entries()) { const end = (shots[i + 1] ? shots[i + 1].f : length + 1) - 1, c = data.cams[s.cam];
  // a slow push toward the subject keeps a held shot alive
  const push = (c.push ?? .035) * Math.min(1, (end - s.f) / (fps * 6)), p1 = c.p.map((v, k) => +(v + (c.t[k] - v) * push).toFixed(4));
  A.ctx.camKeys.push({ f: s.f, p: c.p.slice(), t: c.t.slice(), fov: c.fov, fstop: c.fstop });
  if (end > s.f) A.ctx.camKeys.push({ f: end, p: p1, t: c.t.slice(), fov: c.fov, fstop: c.fstop }); }
A.applyFrame(0);
log.push({ length, seconds: +(length / fps).toFixed(1), shots: shots.length, cues: cues.map(c => [c.id, c.t]) });
// who is speaking when, and where their head is: the renderer lights the speaker's outline from behind
const speakers = cues.filter(c => !c.narration && onStage(c.speaker)).map(c => ({ n: c.n, f0: c.f0, f1: c.f1, head: headOf2(c.speaker, Math.min(length, c.f0 + 12)).map(v => +v.toFixed(3)),
  ...((data.speakerPower || {})[c.id] ? { power: data.speakerPower[c.id] } : {}) }));
A.applyFrame(0);
window.__film = { length, cues: cues.map(c => ({ id: c.id, n: c.n, t: c.t })), shots, speakers };
