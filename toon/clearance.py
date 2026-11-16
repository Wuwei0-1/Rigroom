"""Clearances on the skinned characters: where hands, arms and legs pass into each other, a slate or the furniture.

Each character is one mesh whose pieces are bound to bones. A part is the set of vertices whose strongest bone is in a
list. Posed points come from linear blend skinning with the pose-bone matrices, as the armature modifier does it.
The signed distance from a point to a part is (point - nearest vertex) . (that vertex's normal); below zero is inside.
Slates and furniture are boxes, with exact box distances.

    blender -b --python clearance.py -- SCENE.blend [--step 4] [--min 0.004] [--json OUT.json]
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from scipy.spatial import cKDTree

PARTS = {
    'hand_l': ['hand_l'], 'hand_r': ['hand_r'],
    'fore_l': ['lowerarm_l'], 'fore_r': ['lowerarm_r'],
    'upper_l': ['upperarm_l', 'shoulder_l'], 'upper_r': ['upperarm_r', 'shoulder_r'],
    'trunk': ['hip', 'spine_01', 'spine_02', 'spine_03'],
    'head': ['neck', 'head', 'lid_l', 'lid_r', 'mouth'],
    'thigh_l': ['upperleg_l'], 'thigh_r': ['upperleg_r'],
    'shin_l': ['lowerleg_l', 'foot_l', 'ball_l'], 'shin_r': ['lowerleg_r', 'foot_r', 'ball_r'],
}
# pairs of a character's own parts that must never meet
SELF = [('hand_l', 'hand_r'), ('hand_l', 'fore_r'), ('hand_l', 'upper_r'), ('hand_r', 'fore_l'), ('hand_r', 'upper_l'), ('fore_l', 'fore_r'),
        ('hand_l', 'trunk'), ('hand_r', 'trunk'), ('hand_l', 'head'), ('hand_r', 'head'), ('fore_l', 'trunk'), ('fore_r', 'trunk'),
        ('fore_l', 'head'), ('fore_r', 'head'),
        ('hand_l', 'thigh_l'), ('hand_l', 'thigh_r'), ('hand_r', 'thigh_l'), ('hand_r', 'thigh_r'),
        ('fore_l', 'thigh_l'), ('fore_l', 'thigh_r'), ('fore_r', 'thigh_l'), ('fore_r', 'thigh_r')]
LIMBS = ['hand_l', 'hand_r', 'fore_l', 'fore_r', 'upper_l', 'upper_r']
LEGS = ['thigh_l', 'thigh_r', 'shin_l', 'shin_r']
SLATE_BOX = ((-0.13, -0.09, 0.0), (0.13, 0.09, 0.0115))     # lounge.slate() in its own space


class Figure:
    """One character's mesh, ready to pose: rest points, normals and up to two bone weights per vertex."""

    def __init__(self, arm, body):
        self.arm, self.body = arm, body
        me = body.data
        n = len(me.vertices)
        co = np.empty(n * 3); me.vertices.foreach_get('co', co)
        nr = np.empty(n * 3); me.vertices.foreach_get('normal', nr)
        self.co = np.c_[co.reshape(n, 3), np.ones(n)]
        self.nr = nr.reshape(n, 3)
        names = [g.name for g in body.vertex_groups]
        self.bones = [b for b in names]
        idx = np.zeros((n, 2), int); w = np.zeros((n, 2))
        for v in me.vertices:
            gs = sorted(((g.weight, g.group) for g in v.groups), reverse=True)[:2]
            s = sum(x[0] for x in gs) or 1.0
            for k, (ww, gi) in enumerate(gs):
                idx[v.index, k] = gi; w[v.index, k] = ww / s
        self.idx, self.w = idx, w
        top = idx[:, 0]
        self.part = {}
        for p, bs in PARTS.items():
            gis = [names.index(b) for b in bs if b in names]
            sel = np.nonzero(np.isin(top, gis))[0]
            if len(sel):
                self.part[p] = sel
        self.inv = {b: arm.data.bones[b].matrix_local.inverted() for b in names if b in arm.data.bones}

    def pose(self):
        """World points and normals for the current pose."""
        W = self.arm.matrix_world
        Ms = np.array([np.array(W @ self.arm.pose.bones[b].matrix @ self.inv[b]) if b in self.inv else np.array(W) for b in self.bones])
        A = Ms[self.idx[:, 0]] * self.w[:, 0, None, None] + Ms[self.idx[:, 1]] * self.w[:, 1, None, None]
        p = np.einsum('nij,nj->ni', A, self.co)[:, :3]
        q = np.einsum('nij,nj->ni', A[:, :3, :3], self.nr)
        q /= np.linalg.norm(q, axis=1, keepdims=True) + 1e-12
        self.P, self.N = p, q
        self.trees = {}
        return p

    def pts(self, part):
        return self.P[self.part[part]]

    def tree(self, part):
        if part not in self.trees:
            self.trees[part] = cKDTree(self.pts(part))
        return self.trees[part]

    def signed(self, part, X):
        """Signed distance of points X to a part (negative inside)."""
        d, i = self.tree(part).query(X)
        sel = self.part[part][i]
        dot = np.einsum('ij,ij->i', X - self.P[sel], self.N[sel])
        # inside only where the point lies well behind the surface; a far point beside a vertex is just far
        return np.where(dot < -0.5 * d, dot, d)


def box_sdf(X, lo, hi):
    c = (np.array(lo) + np.array(hi)) / 2
    h = (np.array(hi) - np.array(lo)) / 2
    q = np.abs(X - c) - h
    out = np.linalg.norm(np.maximum(q, 0), axis=1)
    inside = np.minimum(q.max(axis=1), 0)
    return out + inside


def to_local(M, X):
    Mi = np.array(M.inverted())
    return X @ Mi[:3, :3].T + Mi[:3, 3]


def gap(fig, a, b):
    if a not in fig.part or b not in fig.part:
        return 1.0
    return float(min(fig.signed(b, fig.pts(a)).min(), fig.signed(a, fig.pts(b)).min()))


def measure(figs, slates=(), boxes=(), limbs_vs_boxes=True):
    """Every clearance that matters in the current pose: {(who, a, b): metres}, negative where they pass into each other."""
    out = {}
    for who, fig in figs.items():
        fig.pose()
        for a, b in SELF:
            out[(who, a, b)] = gap(fig, a, b)
        for sl in slates:
            M = sl.matrix_world
            for p in LIMBS + LEGS + ['trunk']:
                if p in fig.part:
                    X = to_local(M, fig.pts(p))
                    out[(who, p, sl.name)] = float(box_sdf(X, *SLATE_BOX).min())
        for name, lo, hi in boxes:
            for p in (LEGS + LIMBS + ['trunk'] if limbs_vs_boxes else LEGS):
                if p in fig.part:
                    out[(who, p, name)] = float(box_sdf(fig.pts(p), lo, hi).min())
    return out


def figures(names=('Socrates', 'Aria', 'Cleon', 'Julian')):
    return {n: Figure(bpy.data.objects[n + ' rig'], bpy.data.objects[n]) for n in names if n in bpy.data.objects}


def scan(frames, figs, slates, boxes, need=0.004, holds=None):
    """Measure every frame; returns runs [(who, a, b, first, last, worst)] where the clearance falls below need.

    holds: {(who, part, slate name)} allowed to touch (a hand holding its slate) but not to pass in."""
    sc = bpy.context.scene
    bad = {}
    for f in frames:
        sc.frame_set(f)
        for k, v in measure(figs, slates, boxes).items():
            lim = -0.002 if holds and (k[0], k[1], k[2]) in holds else need
            if v < lim:
                bad.setdefault(k, []).append((f, v))
    runs = []
    for k, fs in bad.items():
        cur = None
        for f, v in fs:
            if cur and f - cur[1] <= (frames[1] - frames[0]) * 2:
                cur = [cur[0], f, min(cur[2], v)]
            else:
                if cur:
                    runs.append((*k, *cur))
                cur = [f, f, v]
        runs.append((*k, *cur))
    return sorted(runs, key=lambda r: (r[3], r[0]))


if __name__ == '__main__' and '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]
    step = int(argv[argv.index('--step') + 1]) if '--step' in argv else 4
    need = float(argv[argv.index('--min') + 1]) if '--min' in argv else 0.004
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lounge
    bpy.ops.wm.open_mainfile(filepath=argv[0], load_ui=False, use_scripts=False)
    figs = figures()
    for fig in figs.values():
        for m in fig.body.modifiers:
            m.show_viewport = False
    slates = [o for o in bpy.data.objects if o.name.startswith('Slate')]
    sc = bpy.context.scene
    runs = scan(list(range(sc.frame_start, sc.frame_end + 1, step)), figs, slates, lounge.boxes())
    for r in runs:
        print('%-9s %-8s %-14s frames %5d-%5d  worst %+.3f m' % r)
    print(len(runs), 'runs')
    if '--json' in argv:
        json.dump(runs, open(argv[argv.index('--json') + 1], 'w'))
