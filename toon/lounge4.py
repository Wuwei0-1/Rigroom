"""Gyges IV's botanical lounge at dawn: lounge.build() with its screens dark, a door in the left wall, a window with
blinds in the right wall, and the brass ring on the table.

Like courtyard.py it gives SEAT, SEATS, SPOTS, LOOKS, CAMERAS, build() and animate(info, S, F, offset), which keys:
    S.prop('door', t, open=True|False, dur=1.0)       the door swings open or shut
    S.prop('blinds', t, dur=1.6)                       the blinds go up and the low sun floods in
    S.prop('ring_table', t)                            the ring is picked up off the table
Metres, Z up; the booth faces -Y, the left wall is at x -4.6 and the right wall at x +4.6.
"""
import math

import bpy

import kit
import lounge
import stage
from kit import capsule, material, ring, slab, static

SEAT = lounge.SEAT
TABLE = lounge.TABLE
SEATS = {'cleon': (-1.53, 0.12, 62.0), 'aria': (0.16, 0.8, 0.0), 'julian': (1.52, 0.12, -62.0)}
DOOR_Y, DOOR_W, DOOR_H = -1.0, 1.0, 2.15
WIN_Y, WIN_W, WIN_Z0, WIN_Z1 = -0.55, 1.6, 0.8, 2.6
SPOTS = {
    'door': (-3.85, DOOR_Y), 'door_out': (-5.6, DOOR_Y), 'door_in': (-3.6, DOOR_Y + 0.1),
    'front_left': (-0.9, -0.95), 'front': (0.0, -1.0), 'front_right': (0.95, -0.9), 'by_julian': (0.9, -0.45),
    'window': (3.85, WIN_Y), 'mid_floor': (1.9, -1.4), 'aria_bench': (-0.6, -1.2),
}
LOOKS = {
    'socrates_spot': (0.0, -0.95, 1.55), 'door': (-4.6, DOOR_Y, 1.4), 'window': (4.6, WIN_Y, 1.7), 'ring': (0.3, -0.12, TABLE),
    'table': (0.0, 0.0, TABLE), 'out': (6.0, WIN_Y, 1.4), 'floor': (1.0, -1.5, 0.0), 'mid': (0.0, 0.2, 1.1),
}
CAMERAS = {
    'wide': ((0.0, -4.5, 1.3), (0.0, 0.4, 1.0), 30),
    'reverse': ((-1.2, 2.3, 2.0), (0.4, -0.3, 0.9), 28),
    'julian': ((-0.35, -1.45, 1.3), (1.52, 0.12, 1.12), 42),
    'table': ((0.15, -0.95, 1.35), (0.3, -0.1, TABLE + 0.05), 40),
    'door': ((2.2, -3.4, 1.55), (-4.2, DOOR_Y, 1.2), 28),
    'window': ((-2.6, -3.6, 1.6), (3.4, -0.4, 1.0), 26),
    'follow': ((0.0, -4.2, 1.5), (0.0, 0.0, 1.0), 30),
}
OPEN = 1.25          # radians the door swings


def _wall_with_hole(name, x, y0, y1, z0, z1, hy0, hy1, hz0, hz1, mat):
    """A wall along Y at x, from y0 to y1 and z0 to z1, with a rectangular hole."""
    parts = []
    if hy0 > y0:
        parts.append(slab((x, (y0 + hy0) / 2, (z0 + z1) / 2), (0.2, hy0 - y0, z1 - z0)))
    if y1 > hy1:
        parts.append(slab((x, (hy1 + y1) / 2, (z0 + z1) / 2), (0.2, y1 - hy1, z1 - z0)))
    if hz0 > z0:
        parts.append(slab((x, (hy0 + hy1) / 2, (z0 + hz0) / 2), (0.2, hy1 - hy0, hz0 - z0)))
    if z1 > hz1:
        parts.append(slab((x, (hy0 + hy1) / 2, (hz1 + z1) / 2), (0.2, hy1 - hy0, z1 - hz1)))
    return static(name, [(p, mat) for p in parts], smooth=False)


def build():
    lounge.build(None)
    # the screens are dark at dawn
    m = bpy.data.materials.get('Hologram')
    if m:
        for n in m.node_tree.nodes:
            if n.type == 'EMISSION':
                n.inputs['Strength'].default_value = 0.06
    wall = bpy.data.materials.get('Brick') or material('Brick', '#6b3a2c', rough=0.9)
    for nm in ('Wall left', 'Wall right'):
        ob = bpy.data.objects.get(nm)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    _wall_with_hole('Wall left', -4.6, -2.5, 3.5, -0.2, 4.2, DOOR_Y - DOOR_W / 2, DOOR_Y + DOOR_W / 2, -0.2, DOOR_H, wall)
    _wall_with_hole('Wall right', 4.6, -2.5, 3.5, -0.2, 4.2, WIN_Y - WIN_W / 2, WIN_Y + WIN_W / 2, WIN_Z0, WIN_Z1, wall)
    wood = material('Door walnut', '#4a2a1a', rough=0.55)
    brass = bpy.data.materials.get('Brass') or material('Brass', '#c9983a', rough=0.35, metal=1.0)
    dark = material('Lounge frame', '#1b1612', rough=0.6)
    # the door, hinged at its back edge
    hinge = bpy.data.objects.new('Door hinge', None)
    bpy.context.scene.collection.objects.link(hinge)
    hinge.location = (-4.56, DOOR_Y + DOOR_W / 2, 0.0)
    door = static('Door', [(slab((0.0, -DOOR_W / 2, DOOR_H / 2), (0.05, DOOR_W - 0.02, DOOR_H - 0.02)), wood),
                           (capsule((0.06, -DOOR_W + 0.1, 1.0), (0.06, -DOOR_W + 0.1, 1.15), 0.015, seg=8), brass)], smooth=False, bevel=0.01)
    door.parent = hinge
    static('Door frame', [(slab((-4.5, DOOR_Y, DOOR_H + 0.04), (0.06, DOOR_W + 0.12, 0.08)), dark),
                          (slab((-4.5, DOOR_Y - DOOR_W / 2 - 0.03, DOOR_H / 2), (0.06, 0.06, DOOR_H)), dark),
                          (slab((-4.5, DOOR_Y + DOOR_W / 2 + 0.03, DOOR_H / 2), (0.06, 0.06, DOOR_H)), dark)], smooth=False)
    # the window: frame, a bright morning outside, and the blinds
    static('Window frame', [(slab((4.5, WIN_Y, WIN_Z0 - 0.04), (0.14, WIN_W + 0.1, 0.08)), dark), (slab((4.5, WIN_Y, WIN_Z1 + 0.04), (0.14, WIN_W + 0.1, 0.08)), dark),
                            (slab((4.5, WIN_Y - WIN_W / 2 - 0.04, (WIN_Z0 + WIN_Z1) / 2), (0.14, 0.08, WIN_Z1 - WIN_Z0)), dark),
                            (slab((4.5, WIN_Y + WIN_W / 2 + 0.04, (WIN_Z0 + WIN_Z1) / 2), (0.14, 0.08, WIN_Z1 - WIN_Z0)), dark),
                            (slab((4.5, WIN_Y, (WIN_Z0 + WIN_Z1) / 2), (0.06, 0.05, WIN_Z1 - WIN_Z0)), dark)], smooth=False)
    sky = material('Morning outside', '#ffd8a0', emit=2.2)
    static('Outside', [(slab((7.5, WIN_Y, 1.8), (0.05, 8.0, 5.0)), sky)], smooth=False)
    slat_m = material('Blind slat', '#e8dcc4', rough=0.6)
    slats = []
    n = 20
    for k in range(n):
        z = WIN_Z1 - 0.05 - k * (WIN_Z1 - WIN_Z0 - 0.08) / (n - 1)
        ob = static('Blind slat %d' % k, [(slab((0.0, 0.0, 0.0), (0.075, WIN_W - 0.04, 0.008)), slat_m)], smooth=False)
        ob.location = (4.38, WIN_Y, z)
        ob.rotation_euler = (0.0, math.radians(38), 0.0)
        slats.append(ob)
    static('Blind rail', [(slab((4.38, WIN_Y, WIN_Z1 - 0.01), (0.09, WIN_W, 0.04)), dark)], smooth=False)
    # the ring on the table, exactly where Socrates stood over it
    rb = material('Ring on table', '#d9a836', rough=0.3, metal=1.0)
    rob = static('Ring on the table', [(ring((0.3, -0.12, TABLE + 0.006), 0.019, 0.0055, tseg=8, seg=20), rb)])
    # lights: grey-gold dawn through the blinds, the pendant low, a soft key from the room
    blind_l = stage.light('Blind light', 'AREA', (5.6, WIN_Y, 1.9), 900, (1.0, 0.78, 0.5), 1.6, to=(1.5, 0.1, 0.4))
    sun = stage.light('Lounge sun', 'SUN', (8.0, WIN_Y + 1.5, 2.6), 0.0, (1.0, 0.76, 0.5), 0.02, to=(0.0, -0.4, 0.95))
    stage.light('Lounge pendant', 'POINT', (0, 0, 1.95), 40, (1.0, 0.82, 0.6), 0.15)
    stage.light('Lounge key', 'AREA', (-2.6, -3.6, 3.3), 160, (0.92, 0.9, 0.95), 3.0, to=(0, 0.4, 1.1))
    stage.light('Lounge fill', 'AREA', (3.0, -3.2, 1.6), 50, (0.7, 0.8, 1.0), 3.0, to=(0, 0.4, 1.1), shadow=False)
    return {'hinge': hinge, 'slats': slats, 'ring': rob, 'sun': sun, 'blind_light': blind_l}


def animate(info, S, F, offset):
    hinge, slats, rob, sun, bl = info['hinge'], info['slats'], info['ring'], info['sun'], info['blind_light']
    hinge.rotation_euler = (0, 0, 0)
    hinge.keyframe_insert('rotation_euler', frame=0)
    rob.hide_render = False
    rob.keyframe_insert('hide_render', frame=0)
    for ob in slats:
        ob.keyframe_insert('location', frame=0)
        ob.keyframe_insert('rotation_euler', frame=0)
    sun.data.keyframe_insert('energy', frame=0)
    for kind, t, kw in sorted(S.props, key=lambda p: p[1]):
        if kind == 'door':
            d = kw.get('dur', 1.0)
            a0, a1 = (0.0, -OPEN) if kw.get('open', True) else (-OPEN, 0.0)
            hinge.rotation_euler = (0, 0, a0)
            hinge.keyframe_insert('rotation_euler', frame=F(t))
            hinge.rotation_euler = (0, 0, a1)
            hinge.keyframe_insert('rotation_euler', frame=F(t + d))
        elif kind == 'ring_table':
            rob.hide_render = False
            rob.keyframe_insert('hide_render', frame=max(0, F(t) - 1))
            rob.hide_render = True
            rob.keyframe_insert('hide_render', frame=F(t))
        elif kind == 'blinds':
            d = kw.get('dur', 1.6)
            for k, ob in enumerate(slats):
                ob.keyframe_insert('location', frame=F(t))
                ob.keyframe_insert('rotation_euler', frame=F(t))
                top = WIN_Z1 - 0.05 - k * 0.012
                ob.location = (ob.location.x, ob.location.y, top + offset.z)
                ob.rotation_euler = (0.0, math.radians(85), 0.0)
                ob.keyframe_insert('location', frame=F(t + d * (0.4 + 0.6 * k / len(slats))))
                ob.keyframe_insert('rotation_euler', frame=F(t + d * (0.4 + 0.6 * k / len(slats))))
            sun.data.energy = 0.0
            sun.data.keyframe_insert('energy', frame=F(t + d * 0.3))
            sun.data.energy = 7.0
            sun.data.keyframe_insert('energy', frame=F(t + d))
            bl.data.keyframe_insert('energy', frame=F(t + d * 0.3))
            bl.data.energy = 2200
            bl.data.keyframe_insert('energy', frame=F(t + d))
