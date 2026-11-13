"""Rigroom render server: renders one job with Blender Cycles.

Usage (Blender as a Python module, or inside Blender):
    python render_job.py JOB_DIR OUT_DIR [FIRST_FRAME LAST_FRAME]

JOB_DIR holds scene.glb and job.json, both written by the Rigroom app.
Frames are written to OUT_DIR as frame_0000.png, numbered by app frame.
Scene space conversion: app (three.js) is Y-up, Blender is Z-up: (x, y, z) -> (x, -z, y).
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

QUALITY_MAX_SAMPLES = 4096


def to_blender(v):
    return Vector((v[0], -v[2], v[1]))


def hex_to_linear(h):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb] + [1.0]


def args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    if len(argv) < 2:
        sys.exit(__doc__)
    job_dir, out_dir = argv[0], argv[1]
    first = int(argv[2]) if len(argv) > 2 else None
    last = int(argv[3]) if len(argv) > 3 else first
    return job_dir, out_dir, first, last


def setup_scene(job, job_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    fps = int(job.get('fps', 24))
    scene.render.fps = fps
    scene.render.fps_base = 1.0

    # the stage: characters and props, with baked animation for shots
    bpy.ops.import_scene.gltf(filepath=os.path.join(job_dir, 'scene.glb'))
    # every imported action becomes the object's active action, so all animation plays together
    for ob in scene.objects:
        ad = ob.animation_data
        if ad and not ad.action and ad.nla_tracks:
            strips = [s for t in ad.nla_tracks for s in t.strips]
            if strips:
                ad.action = strips[0].action

    # floor: the app draws a large matte floor that is not part of the exported stage
    fl = job.get('floor', {})
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = 'Floor'
    mat = bpy.data.materials.new('Floor')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = hex_to_linear(fl.get('color', '#6b6e76'))
    bsdf.inputs['Roughness'].default_value = float(fl.get('roughness', 0.92))
    floor.data.materials.append(mat)

    look = job.get('look', {})
    # sun, aimed like the app's sun: angle around the scene, height above the horizon
    a, h = math.radians(look.get('sunAngle', 35)), math.radians(look.get('sunHeight', 55))
    toward_sun = to_blender([math.sin(a) * math.cos(h), math.sin(h), math.cos(a) * math.cos(h)]).normalized()
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun_data.energy = float(look.get('sunPower', 2.0)) * 1.6
    sun_data.angle = math.radians(1.5)
    sun_data.color = (1.0, 0.957, 0.902)
    sun = bpy.data.objects.new('Sun', sun_data)
    sun.rotation_euler = toward_sun.to_track_quat('Z', 'Y').to_euler()
    scene.collection.objects.link(sun)

    # world: soft studio-like ambient light, like the app's environment
    world = bpy.data.worlds.new('World')
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.62, 0.63, 0.66, 1.0)
    bg.inputs['Strength'].default_value = float(look.get('env', 0.6)) * 1.1
    scene.world = world

    # colour management: filmic-style tone mapping, exposure in stops
    vs = scene.view_settings
    try:
        vs.view_transform = 'AgX'
    except TypeError:
        vs.view_transform = 'Filmic'
    vs.exposure = math.log2(max(0.05, float(look.get('exposure', 1.0))))
    return scene


def setup_camera(scene, job):
    cams = {int(c['f']): c for c in job['cameras']}
    data = bpy.data.cameras.new('Camera')
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 24.0
    cam = bpy.data.objects.new('Camera', data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dof = job.get('dof')
    data.dof.use_dof = bool(dof)
    if dof:
        data.dof.aperture_fstop = float(dof.get('fstop', 2.8))

    def place(c, frame=None):
        p, t = to_blender(c['p']), to_blender(c['t'])
        cam.location = p
        cam.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
        data.lens = 12.0 / math.tan(math.radians(float(c.get('fov', 35))) / 2)
        if dof:
            data.dof.focus_distance = (t - p).length
        if frame is not None:
            cam.keyframe_insert('location', frame=frame)
            cam.keyframe_insert('rotation_euler', frame=frame)
            data.keyframe_insert('lens', frame=frame)
            if dof:
                data.dof.keyframe_insert('focus_distance', frame=frame)

    if len(cams) == 1:
        place(next(iter(cams.values())))
    else:
        for f, c in sorted(cams.items()):
            place(c, frame=f)
    return cams


def setup_render(scene, job):
    r = scene.render
    r.engine = 'CYCLES'
    r.resolution_x = int(job.get('width', 1280))
    r.resolution_y = int(job.get('height', 720))
    r.resolution_percentage = 100
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.use_persistent_data = True
    c = scene.cycles
    c.device = 'CPU'
    c.samples = max(1, min(QUALITY_MAX_SAMPLES, int(job.get('samples', 128))))
    c.use_adaptive_sampling = True
    c.use_denoising = True
    try:
        c.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    c.max_bounces = 8
    c.diffuse_bounces = 4
    c.glossy_bounces = 4
    c.transparent_max_bounces = 8
    c.sample_clamp_indirect = 10.0  # tames fireflies from small bright paths


def main():
    job_dir, out_dir, first, last = args()
    with open(os.path.join(job_dir, 'job.json')) as fh:
        job = json.load(fh)
    os.makedirs(out_dir, exist_ok=True)
    scene = setup_scene(job, job_dir)
    setup_camera(scene, job)
    setup_render(scene, job)

    f0, f1 = job['frames']
    first = f0 if first is None else max(f0, first)
    last = f1 if last is None else min(f1, last)
    # glTF time 0 lands on Blender frame 0 when the importer runs at the job's frame rate
    offset = int(job.get('frame_offset', 0))
    for f in range(first, last + 1):
        started = time.time()
        scene.frame_set(f + offset)
        scene.render.filepath = os.path.join(out_dir, 'frame_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
        print('rendered frame %d in %.1f s' % (f, time.time() - started), flush=True)


if __name__ == '__main__':
    main()
