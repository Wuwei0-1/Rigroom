"""Building blocks for 3D cartoon characters and sets in Blender (bpy): shapes, materials, a skinned body, posing.

Shapes are plain vertex/face lists so a whole character is one mesh, each piece bound to one bone of the
motion-capture skeleton (no weight painting): a puppet whose joints are overlapping round forms.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector


def hexc(h, a=1.0):
    """sRGB hex colour -> linear RGBA."""
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (a,)


def material(name, colour, rough=0.65, sss=0.0, sheen=0.0, emit=0.0, metal=0.0, coat=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    col = hexc(colour) if isinstance(colour, str) else colour
    I = b.inputs
    I['Base Color'].default_value = col
    I['Roughness'].default_value = rough
    I['Metallic'].default_value = metal
    if sss:
        I['Subsurface Weight'].default_value = sss
        I['Subsurface Radius'].default_value = (0.9, 0.35, 0.2)
        I['Subsurface Scale'].default_value = 0.02
    if sheen:
        I['Sheen Weight'].default_value = sheen
        I['Sheen Roughness'].default_value = 0.5
    if coat:
        I['Coat Weight'].default_value = coat
        I['Coat Roughness'].default_value = 0.08
    if emit:
        I['Emission Color'].default_value = col
        I['Emission Strength'].default_value = emit
    m.diffuse_color = col
    return m


# ---------------------------------------------------------------- shapes (vertex and face lists)

def lathe(profile, seg=20, M=None):
    """Spin a profile [(radius, z), ...] about Z. A radius of 0 makes a pole."""
    M = M or Matrix.Identity(4)
    verts, rings = [], []
    for r, z in profile:
        if r <= 1e-9:
            rings.append([len(verts)])
            verts.append(M @ Vector((0, 0, z)))
        else:
            ring = []
            for i in range(seg):
                a = 2 * math.pi * i / seg
                ring.append(len(verts))
                verts.append(M @ Vector((r * math.cos(a), r * math.sin(a), z)))
            rings.append(ring)
    faces = []
    for A, B in zip(rings, rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        for i in range(seg):
            j = (i + 1) % seg
            if len(A) == 1:
                faces.append((A[0], B[j], B[i]))
            elif len(B) == 1:
                faces.append((A[i], A[j], B[0]))
            else:
                faces.append((A[i], A[j], B[j], B[i]))
    return verts, faces


def aim(z_to, origin=(0, 0, 0)):
    """A matrix that puts local +Z along a direction, at an origin."""
    d = Vector(z_to).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    return Matrix.Translation(Vector(origin)) @ q.to_matrix().to_4x4()


def sphere(c, r, rot=None, seg=20, rings=12):
    """An ellipsoid: centre, radii (one number or three), optional rotation (Quaternion or Matrix)."""
    r = (r, r, r) if isinstance(r, (int, float)) else r
    prof = [(math.sin(math.pi * i / rings), -math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    prof[0], prof[-1] = (0, -1), (0, 1)
    R = rot.to_matrix().to_4x4() if isinstance(rot, Quaternion) else (rot.to_4x4() if rot is not None else Matrix.Identity(4))
    M = Matrix.Translation(Vector(c)) @ R @ Matrix.Diagonal((r[0], r[1], r[2], 1))
    return lathe(prof, seg, M)


def capsule(p0, p1, r0, r1=None, seg=24, cap=8):
    """A rounded limb from p0 to p1 with radius r0 at the start and r1 at the end."""
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    prof = [(r0 * math.sin(0.5 * math.pi * i / cap), -r0 * math.cos(0.5 * math.pi * i / cap)) for i in range(cap + 1)]
    prof[0] = (0, -r0)
    prof += [(r1 * math.cos(0.5 * math.pi * i / cap), L + r1 * math.sin(0.5 * math.pi * i / cap)) for i in range(cap + 1)]
    prof[-1] = (0, L + r1)
    return lathe(prof, seg, aim(p1 - p0, p0))


def frustum(p0, p1, r0, r1, seg=24, caps=True, squash=1.0):
    """A cone section from p0 to p1 (skirts, cups, lampshades). squash flattens it front to back."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    prof = ([(0, 0)] if caps else []) + [(r0, 0), (r1, L)] + ([(0, L)] if caps else [])
    return lathe(prof, seg, aim(p1 - p0, p0) @ Matrix.Diagonal((1, squash, 1, 1)))


def tube(points, radii, seg=10, caps=True, flat=1.0):
    """A hose through points; radii is one number or one per point. flat < 1 flattens it (ribbons, drapes)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    radii = [radii] * n if isinstance(radii, (int, float)) else radii
    tang = [((pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()) for i in range(n)]
    up = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = (up - tang[0] * up.dot(tang[0])).normalized()
    verts, rings = [], []
    if caps:
        rings.append([len(verts)])
        verts.append(pts[0] - tang[0] * radii[0] * 0.6)
    for i in range(n):
        if i:
            q = tang[i - 1].rotation_difference(tang[i])
            nrm = (q @ nrm).normalized()
        bi = tang[i].cross(nrm).normalized()
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring.append(len(verts))
            verts.append(pts[i] + (nrm * math.cos(a) * flat + bi * math.sin(a)) * radii[i])
        rings.append(ring)
    if caps:
        rings.append([len(verts)])
        verts.append(pts[-1] + tang[-1] * radii[-1] * 0.6)
    faces = []
    for A, B in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(A) == 1:
                faces.append((A[0], B[j], B[i]))
            elif len(B) == 1:
                faces.append((A[i], A[j], B[0]))
            else:
                faces.append((A[i], A[j], B[j], B[i]))
    return verts, faces


def ring(c, R, r, rot=None, seg=28, tseg=8, arc=(0, 2 * math.pi), flat=1.0):
    """A torus or an arc of one (glasses rims, collars, hems), in the XY plane unless rotated."""
    R_ = rot.to_matrix() if isinstance(rot, Quaternion) else (rot if rot is not None else Matrix.Identity(3))
    full = abs((arc[1] - arc[0]) - 2 * math.pi) < 1e-6
    n = seg if full else seg + 1
    pts = [Vector(c) + R_ @ Vector((R * math.cos(arc[0] + (arc[1] - arc[0]) * i / seg), R * math.sin(arc[0] + (arc[1] - arc[0]) * i / seg), 0)) for i in range(n)]
    if full:
        pts.append(pts[0])
        v, f = tube(pts, r, tseg, caps=False, flat=flat)
        return v, f
    return tube(pts, r, tseg, caps=True, flat=flat)


def slab(c, size, rot=None, round_=0.0):
    """A box (centre, full sizes)."""
    R_ = rot.to_matrix() if isinstance(rot, Quaternion) else (rot if rot is not None else Matrix.Identity(3))
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    vs = [Vector(c) + R_ @ Vector((sx * hx, sy * hy, sz * hz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return vs, fs


# ---------------------------------------------------------------- a skinned body

class Body:
    """One mesh for a whole character; every piece added is bound to a bone."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.dl = self.bm.verts.layers.deform.verify()
        self.mats, self.groups = [], []

    def _g(self, bone):
        if bone not in self.groups:
            self.groups.append(bone)
        return self.groups.index(bone)

    def add(self, shape, bone, mat, weights=None, flat=False, mat_of=None):
        """shape = (verts, faces). weights(co) -> {bone: w} overrides the single bone; mat_of(face centre) -> material overrides mat."""
        verts, faces = shape
        if mat not in self.mats:
            self.mats.append(mat)
        mi = self.mats.index(mat)
        vs = []
        for co in verts:
            v = self.bm.verts.new(co)
            if weights:
                for b, w in weights(Vector(co)).items():
                    if w > 1e-4:
                        v[self.dl][self._g(b)] = w
            else:
                v[self.dl][self._g(bone)] = 1.0
            vs.append(v)
        for f in faces:
            try:
                face = self.bm.faces.new([vs[i] for i in f])
            except ValueError:
                continue
            face.material_index = mi
            if mat_of:
                mm = mat_of(face.calc_center_median())
                if mm not in self.mats:
                    self.mats.append(mm)
                face.material_index = self.mats.index(mm)
            face.smooth = not flat
        return self

    def finish(self, arm, collection=None):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        have = {g.name for g in ob.vertex_groups}
        # vertex groups must exist in the order the deform layer indexed them
        for g in self.groups:
            if g not in have:
                ob.vertex_groups.new(name=g)
        ob.parent = arm
        mod = ob.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm
        return ob


def static(name, shapes, collection=None, smooth=True, bevel=0.0, loc=(0, 0, 0), rot_z=0.0):
    """A set piece: [(shape, material), ...] joined into one object."""
    bm = bmesh.new()
    mats = []
    for shape, mat in shapes:
        if mat not in mats:
            mats.append(mat)
        mi = mats.index(mat)
        vs = [bm.verts.new(co) for co in shape[0]]
        for f in shape[1]:
            try:
                face = bm.faces.new([vs[i] for i in f])
            except ValueError:
                continue
            face.material_index = mi
            face.smooth = smooth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    if bevel:
        b = ob.modifiers.new('Bevel', 'BEVEL')
        b.width = bevel
        b.segments = 4
        b.limit_method = 'ANGLE'
        b.angle_limit = math.radians(40)
        b.harden_normals = True
    return ob


def curls(rng, n, where, r=(0.028, 0.045), tries=4000):
    """Scatter n balls at points accepted by where(direction) -> centre or None (curly hair and beards)."""
    out = []
    for _ in range(tries):
        if len(out) >= n:
            break
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if d.length < 0.2 or d.length > 1:
            continue
        c = where(d.normalized())
        if c is None:
            continue
        rad = rng.uniform(*r)
        if any((c - c2).length < 0.55 * (rad + r2) for c2, r2 in out):
            continue
        out.append((c, rad))
    return out


# ---------------------------------------------------------------- posing

def refresh():
    bpy.context.view_layer.update()


def joint(arm, bone):
    """A bone's head in armature space, in the current pose."""
    return arm.pose.bones[bone].matrix.translation.copy()


def rest(arm, bone):
    return arm.data.bones[bone].head_local.copy()


def pose_turn(arm, bone, axis, angle, pivot=None):
    """Turn a bone (and what hangs from it) about an axis given in armature space."""
    pb = arm.pose.bones[bone]
    p = Vector(pivot) if pivot is not None else pb.matrix.translation.copy()
    R = Matrix.Translation(p) @ Quaternion(Vector(axis).normalized(), angle).to_matrix().to_4x4() @ Matrix.Translation(-p)
    pb.matrix = R @ pb.matrix
    refresh()


def pose_point(arm, bone, child, direction):
    """Swing a bone so the line from it to its child bone points along a direction (armature space)."""
    pb = arm.pose.bones[bone]
    v = arm.pose.bones[child].matrix.translation - pb.matrix.translation
    q = v.rotation_difference(Vector(direction).normalized())
    p = pb.matrix.translation.copy()
    pb.matrix = Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Translation(-p) @ pb.matrix
    refresh()


def pose_move(arm, bone, to):
    pb = arm.pose.bones[bone]
    m = pb.matrix.copy()
    m.translation = Vector(to)
    pb.matrix = m
    refresh()


def local_axis(arm, bone, axis):
    """An armature-space axis expressed in a bone's own rest frame (for keying turns about it)."""
    return (arm.data.bones[bone].matrix_local.to_3x3().inverted() @ Vector(axis)).normalized()


def snapshot(arm, bones=None):
    """The pose as {bone: (quaternion, location)}."""
    return {pb.name: (pb.rotation_quaternion.copy(), pb.location.copy(), pb.scale.copy()) for pb in arm.pose.bones if bones is None or pb.name in bones}


def reach(arm, chain, target, pole):
    """Two-bone reach: bend chain (upper, lower, end) so the end bone's joint lands on target; the middle joint leans toward pole.

    All in armature space. Returns False when the target is out of reach (the limb then points straight at it)."""
    up, lo, end = chain
    S = joint(arm, up)
    L1 = (joint(arm, lo) - S).length
    L2 = (joint(arm, end) - joint(arm, lo)).length
    T = Vector(target)
    d = (T - S).length
    ok = d < L1 + L2 - 1e-4
    d = min(d, L1 + L2 - 1e-4)
    d = max(d, abs(L1 - L2) + 1e-4)
    u = (T - S).normalized()
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    p = Vector(pole) - S
    p = (p - u * p.dot(u))
    p = p.normalized() if p.length > 1e-6 else Vector((0, 0, -1))
    E = S + u * a + p * h
    pose_point(arm, up, lo, E - S)
    pose_point(arm, lo, end, (S + u * d) - E)
    return ok


def to_arm(arm, world):
    """A world-space point in the armature's space."""
    return arm.matrix_world.inverted() @ Vector(world)


def to_world(arm, p):
    return arm.matrix_world @ Vector(p)
