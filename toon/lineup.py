"""Render a line-up of the cast for checking the designs.  python lineup.py -- RIG.fbx OUT.png [CACHE.pkl]"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy

import kit
import stage

fbx, out = sys.argv[sys.argv.index('--') + 1:][:2]
cache = (sys.argv[sys.argv.index('--') + 1:] + [None])[2]
stage.reset()
sc = bpy.context.scene
src, motion = stage.load_rig(fbx, cache)
x = -1.8
for who, scale in (('Cleon', 1.0), ('Aria', 0.93), ('Socrates', 0.97), ('Julian', 1.1)):
    arm, body, head = stage.cast_one(src, who, (x, 0, 0), 0.0, scale)
    for s, sg in (('l', 1), ('r', -1)):
        kit.pose_point(arm, 'upperarm_' + s, 'lowerarm_' + s, (sg * 0.45, -0.1, -1))
        kit.pose_point(arm, 'lowerarm_' + s, 'hand_' + s, (sg * 0.3, -0.5, -1))
    if who == 'Socrates':
        kit.pose_point(arm, 'upperarm_r', 'lowerarm_r', (-0.5, -0.5, -0.7))
        kit.pose_point(arm, 'lowerarm_r', 'hand_r', (-0.1, -0.2, 1))
    x += 1.2
floor = kit.static('Floor', [(kit.slab((0, 0, -0.05), (30, 30, 0.1)), kit.material('Lineup floor', '#b9a48c', rough=0.9))], smooth=False)
stage.world(sc, kit.hexc('#cdbfae'), 0.9)
stage.light('Key', 'AREA', (-3, -5, 4.5), 2600, (1.0, 0.93, 0.84), 4.0, to=(0, 0, 1.1))
stage.light('Fill', 'AREA', (4, -4, 2.5), 700, (0.8, 0.88, 1.0), 4.0, to=(0, 0, 1.1))
stage.light('Rim', 'AREA', (1, 4, 3.5), 1500, (1.0, 0.85, 0.7), 3.0, to=(0, 0, 1.3))
sc.camera = stage.camera('Cam', (0, -6.2, 1.25), (0, 0, 1.0), 50)
stage.eevee(sc, 1600, 900, 24)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
if len(sys.argv[sys.argv.index('--') + 1:]) > 3:
    for i, (who, cx) in enumerate((('Cleon', -1.8), ('Aria', -0.6), ('Socrates', 0.6), ('Julian', 1.8))):
        sc.camera.location = (cx - 0.25, -1.9, 1.62 if who != 'Julian' else 1.78)
        sc.camera.rotation_euler = (__import__('mathutils').Vector((cx - 0.03, 0, 1.55 if who != 'Julian' else 1.7)) - sc.camera.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.resolution_x, sc.render.resolution_y = 640, 640
        sc.render.filepath = out.replace('.png', '_%s.png' % who)
        bpy.ops.render.render(write_still=True)
