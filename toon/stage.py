"""Shared stage work: load the motion-capture skeleton, read its motion, cast the characters, set up the picture."""
import math
import os
import pickle

import bpy
from mathutils import Quaternion, Vector

import cast as castmod

PREFIX_END = '_idling_'


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def strip_names(arm):
    import re
    for b in arm.data.bones:
        b.name = re.sub(r'^rp_[a-z]+_animated_\d+_[a-z]+_', '', b.name)


def read_motion(fbx, cache=None, first=1):
    """Only the motion of an animated person: {'fps', 'n', 'rot': {bone: [q]}, 'loc': {'hip', 'root'}} with locations in metres."""
    if cache and os.path.exists(cache):
        return pickle.load(open(cache, 'rb'))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    unit = arm.matrix_world.to_scale().x
    strip_names(arm)
    sc = bpy.context.scene
    act = arm.animation_data.action
    f0, f1 = int(act.frame_range[0]) + first, int(act.frame_range[1])
    m = {'fps': 30, 'n': f1 - f0 + 1, 'rot': {pb.name: [] for pb in arm.pose.bones}, 'loc': {'hip': [], 'root': []}}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        for pb in arm.pose.bones:
            m['rot'][pb.name].append(tuple(pb.rotation_quaternion))
        for b in ('hip', 'root'):
            m['loc'][b].append(tuple(arm.pose.bones[b].location * unit))
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    if cache:
        pickle.dump(m, open(cache, 'wb'))
    return m


def load_rig(fbx, cache=None):
    """Import the animated person, keep only the skeleton (bones renamed hip, spine_01, ...) and return it with its sampled motion.

    motion = {'fps': 30, 'n': frames, 'rot': {bone: [quaternion per frame]}, 'loc': {bone: [vector per frame]}}
    """
    bpy.ops.import_scene.fbx(filepath=fbx)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    for o in list(bpy.data.objects):
        if o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)
    mw = arm.matrix_world.copy()
    unit = mw.to_scale().x                      # the file is in centimetres and Y-up under a control object
    arm.parent = None
    arm.matrix_world = mw
    strip_names(arm)
    motion = None
    if cache and os.path.exists(cache):
        motion = pickle.load(open(cache, 'rb'))
    else:
        sc = bpy.context.scene
        act = arm.animation_data.action
        f0, f1 = int(act.frame_range[0]) + 1, int(act.frame_range[1])       # frame 1 is the T-pose
        motion = {'fps': 30, 'n': f1 - f0 + 1, 'rot': {pb.name: [] for pb in arm.pose.bones}, 'loc': {'hip': [], 'root': []}}
        for f in range(f0, f1 + 1):
            sc.frame_set(f)
            for pb in arm.pose.bones:
                motion['rot'][pb.name].append(tuple(pb.rotation_quaternion))
            for b in ('hip', 'root'):
                motion['loc'][b].append(tuple(arm.pose.bones[b].location * unit))
        if cache:
            pickle.dump(motion, open(cache, 'wb'))
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)     # armature space becomes metres, Z up
    arm.name = 'Rig'
    arm.hide_render = True
    print('rig: unit', unit, 'hip', tuple(round(v, 3) for v in arm.data.bones['hip'].head_local), 'head', tuple(round(v, 3) for v in arm.data.bones['head'].head_local))
    return arm, motion


def cast_one(src, who, loc=(0, 0, 0), yaw=0.0, scale=1.0):
    arm = src.copy()
    arm.data = src.data.copy()
    arm.name = who + ' rig'
    bpy.context.scene.collection.objects.link(arm)
    body, head = castmod.CAST[who](arm)
    arm.location = loc
    arm.rotation_euler = (0, 0, yaw)
    arm.scale = (scale,) * 3
    bpy.context.view_layer.update()
    return arm, body, head


def eevee(scene, width=1280, height=720, samples=24, rays=True):
    for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = width, height, 100
    r.fps = 24
    r.image_settings.file_format = 'PNG'
    r.film_transparent = False
    ee = scene.eevee
    for k, v in (('taa_render_samples', samples), ('use_shadows', True), ('use_raytracing', rays), ('use_gtao', True), ('shadow_ray_count', 2), ('shadow_step_count', 6)):
        if hasattr(ee, k):
            try:
                setattr(ee, k, v)
            except Exception:
                pass
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass


def world(scene, colour, strength=1.0):
    w = bpy.data.worlds.new('World')
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = colour
    bg.inputs[1].default_value = strength
    scene.world = w


def light(name, kind, loc, energy, colour=(1, 1, 1), size=1.0, to=(0, 0, 1), spot=None, blend=0.5, shadow=True):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy
    d.use_shadow = shadow
    d.color = colour
    if kind == 'AREA':
        d.size = size
    elif kind in ('POINT', 'SPOT'):
        d.shadow_soft_size = size
    elif kind == 'SUN':
        d.angle = size
    if kind == 'SPOT' and spot:
        d.spot_size = math.radians(spot)
        d.spot_blend = blend
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(to) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def camera(name, loc, to, lens=35):
    d = bpy.data.cameras.new(name)
    d.lens = lens
    d.sensor_width = 36
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(to) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
