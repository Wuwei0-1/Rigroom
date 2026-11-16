// 3D printing: turns what is on stage, in the pose it is in now, into one STL file for a slicer.
// The scene is in metres with y up; a print is in millimetres with z up, standing on the bed.
import * as THREE from 'three';

const _v = new THREE.Vector3(), _m = new THREE.Matrix4();

/** Every visible mesh under the given objects as loose triangles in scene space (9 numbers each).
 *  Skinned people are taken as posed, with their morphs, not in their rest pose. */
export function collectTriangles(roots) {
  const chunks = []; let total = 0;
  for (const root of roots) {
    root.updateWorldMatrix(true, true);
    root.traverseVisible(o => {
      if (!o.isMesh || !o.geometry || !o.geometry.attributes.position) return;
      const mats = [].concat(o.material || []); if (mats.length && mats.every(m => !m || m.visible === false)) return;
      const g = o.geometry, pos = g.attributes.position, idx = g.index, n = pos.count;
      if (o.isSkinnedMesh && o.skeleton) o.skeleton.update();
      const local = new Float64Array(n * 3);
      for (let i = 0; i < n; i++) { o.getVertexPosition(i, _v); local[3 * i] = _v.x; local[3 * i + 1] = _v.y; local[3 * i + 2] = _v.z; }
      const avail = idx ? idx.count : n, start = Math.min(avail, Math.max(0, g.drawRange.start || 0));
      const count = Math.floor(Math.min(avail - start, g.drawRange.count) / 3) * 3; if (count <= 0) return;
      const copies = o.isInstancedMesh ? o.count : 1;
      for (let c = 0; c < copies; c++) {
        if (o.isInstancedMesh) { o.getMatrixAt(c, _m); _m.premultiply(o.matrixWorld); } else _m.copy(o.matrixWorld);
        const world = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) { _v.set(local[3 * i], local[3 * i + 1], local[3 * i + 2]).applyMatrix4(_m); world[3 * i] = _v.x; world[3 * i + 1] = _v.y; world[3 * i + 2] = _v.z; }
        const flip = _m.determinant() < 0, out = new Float32Array(count * 3);   // a mirrored mesh would otherwise face inward
        for (let t = 0; t < count; t += 3) for (let k = 0; k < 3; k++) {
          const src = start + t + (flip ? 2 - k : k), vi = idx ? idx.getX(src) : src;
          out.set(world.subarray(3 * vi, 3 * vi + 3), 3 * (t + k));
        }
        chunks.push(out); total += out.length;
      }
    });
  }
  const all = new Float32Array(total); let at = 0; for (const c of chunks) { all.set(c, at); at += c.length; }
  return all;
}

/* Corners at the same spot (to a thousandth of a millimetre) share a number, so edges can be matched up. */
function weld(T) {
  const n = T.length / 3, q = new Int32Array(T.length); for (let i = 0; i < T.length; i++) q[i] = Math.round(T[i] * 1000);
  let size = 16; while (size < n * 2) size *= 2;
  const table = new Int32Array(size).fill(-1), id = new Uint32Array(n); let count = 0;
  for (let i = 0; i < n; i++) {
    const x = q[3 * i], y = q[3 * i + 1], z = q[3 * i + 2];
    let h = (Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791)) & (size - 1);
    for (;;) { const j = table[h];
      if (j < 0) { table[h] = i; id[i] = count++; break; }
      if (q[3 * j] === x && q[3 * j + 1] === y && q[3 * j + 2] === z) { id[i] = id[j]; break; }
      h = (h + 1) & (size - 1); }
  }
  return { id, count };
}
/* A printable solid is closed: every edge joins an even number of faces. Counts the edges that do not. */
const CHECK_LIMIT = 700000;
function openEdges(id, count, keep) {
  const seen = new Map();
  for (const t of keep) for (let k = 0; k < 3; k++) {
    const a = id[3 * t + k], b = id[3 * t + (k + 1) % 3], key = a < b ? a * count + b : b * count + a;
    seen.set(key, (seen.get(key) || 0) + 1);
  }
  let open = 0; for (const c of seen.values()) if (c % 2) open++; return open;
}

/* A round base: a closed disc from z = 0 up to its thickness, facing outward. */
function baseDisc(cx, cy, r, t, seg = 72) {
  const out = new Float32Array(seg * 4 * 9); let at = 0;
  const tri = (...p) => { out.set(p, at); at += 9; };
  for (let i = 0; i < seg; i++) {
    const a = i / seg * Math.PI * 2, b = (i + 1) % seg / seg * Math.PI * 2;
    const ax = cx + Math.cos(a) * r, ay = cy + Math.sin(a) * r, bx = cx + Math.cos(b) * r, by = cy + Math.sin(b) * r;
    tri(cx, cy, 0, bx, by, 0, ax, ay, 0); tri(cx, cy, t, ax, ay, t, bx, by, t);
    tri(ax, ay, 0, bx, by, 0, bx, by, t); tri(ax, ay, 0, bx, by, t, ax, ay, t);
  }
  return out;
}

/** Build the print from scene-space triangles.
 *  size: the model's longest side in millimetres. base: stand it on a round base.
 *  Returns { stl (ArrayBuffer, binary STL), triangles, size: [wide, deep, tall] in mm, base (mm across, or 0), open (edges that are not closed, or null when too big to check) }. */
export function buildPrint(scene, opts = {}) {
  const N = scene.length / 3; if (!N) throw new Error('There is nothing solid there to print.');
  // y up becomes z up: a quarter turn about x, so the model stands on the bed and faces the front of the printer
  let T = new Float32Array(scene.length);
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < N; i++) {
    const p = [scene[3 * i], -scene[3 * i + 2], scene[3 * i + 1]];
    for (let k = 0; k < 3; k++) { if (!isFinite(p[k])) throw new Error('The model has broken geometry (a point with no position).'); T[3 * i + k] = p[k]; if (p[k] < lo[k]) lo[k] = p[k]; if (p[k] > hi[k]) hi[k] = p[k]; }
  }
  const longest = Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]); if (!(longest > 1e-6)) throw new Error('The model has no size to print.');
  const want = Math.min(2000, Math.max(5, +opts.size || 120)), s = want / longest;
  const mid = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2], tall = (hi[2] - lo[2]) * s;
  for (let i = 0; i < N; i++) { T[3 * i] = (T[3 * i] - mid[0]) * s; T[3 * i + 1] = (T[3 * i + 1] - mid[1]) * s; T[3 * i + 2] = (T[3 * i + 2] - lo[2]) * s; }

  let baseAcross = 0;
  if (opts.base) {
    // the base sits under whatever touches the ground (the feet), wide enough that the figure will not tip over
    const reach = Math.max(.3, tall * .02); let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (let i = 0; i < N; i++) if (T[3 * i + 2] <= reach) { const x = T[3 * i], y = T[3 * i + 1]; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2; let r = 0;
    for (let i = 0; i < N; i++) if (T[3 * i + 2] <= reach) r = Math.max(r, Math.hypot(T[3 * i] - cx, T[3 * i + 1] - cy));
    const margin = Math.max(3, want * .04), thick = Math.min(5, Math.max(2, want * .025));
    r = Math.max(r + margin, Math.hypot(cx, cy) + margin, tall * .15);
    // the model sinks a little into the base, so the slicer joins them into one piece
    const lift = thick - Math.min(.5, thick / 4); for (let i = 0; i < N; i++) T[3 * i + 2] += lift;
    const disc = baseDisc(cx, cy, r, thick), both = new Float32Array(T.length + disc.length); both.set(T); both.set(disc, T.length); T = both; baseAcross = r * 2;
  }

  // faces with no area (the poles of spheres and capsules) only confuse a slicer: leave them out
  const { id, count } = weld(T), keep = [];
  for (let t = 0; t < T.length / 9; t++) { const a = id[3 * t], b = id[3 * t + 1], c = id[3 * t + 2]; if (a !== b && b !== c && a !== c) keep.push(t); }
  if (!keep.length) throw new Error('There is nothing solid there to print.');
  const open = keep.length > CHECK_LIMIT ? null : openEdges(id, count, keep);

  // binary STL: an 80-byte header, the face count, then 50 bytes a face (normal, three corners, two spare bytes)
  const stl = new ArrayBuffer(84 + keep.length * 50), dv = new DataView(stl), head = 'Rigroom 3D print, millimetres, z up' + (opts.name ? ': ' + opts.name : '');
  for (let i = 0; i < Math.min(80, head.length); i++) dv.setUint8(i, head.charCodeAt(i) & 127);
  dv.setUint32(80, keep.length, true);
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity]; let o = 84;
  for (const t of keep) {
    const p = T.subarray(9 * t, 9 * t + 9);
    const ux = p[3] - p[0], uy = p[4] - p[1], uz = p[5] - p[2], vx = p[6] - p[0], vy = p[7] - p[1], vz = p[8] - p[2];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const len = Math.hypot(nx, ny, nz) || 1; nx /= len; ny /= len; nz /= len;
    dv.setFloat32(o, nx, true); dv.setFloat32(o + 4, ny, true); dv.setFloat32(o + 8, nz, true); o += 12;
    for (let k = 0; k < 9; k++) { dv.setFloat32(o, p[k], true); o += 4; const a = k % 3; if (p[k] < min[a]) min[a] = p[k]; if (p[k] > max[a]) max[a] = p[k]; }
    o += 2;
  }
  return { stl, triangles: keep.length, size: [max[0] - min[0], max[1] - min[1], max[2] - min[2]], base: baseAcross, open };
}
