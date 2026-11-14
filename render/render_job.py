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
import shutil
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import surfaces  # noqa: E402
from surfaces import to_blender  # noqa: E402

QUALITY_MAX_SAMPLES = 4096


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

    look = job.get('look', {})
    # people first (their materials come from the scans), then the set's surfaces
    people = surfaces.shade_people(scene)
    props = surfaces.dress_props(scene, os.path.join(job_dir, 'images'))

    # floor: the app draws a large floor that is not part of the exported stage
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = 'Floor'
    floor.data.materials.append(surfaces.floor_material(look.get('floor', 'matte'), job.get('floor', {})))
    print('surfaces: %d people materials, %d props' % (people, props), flush=True)

    # sun, aimed like the app's sun: angle around the scene, height above the horizon
    a, h = math.radians(look.get('sunAngle', 35)), math.radians(look.get('sunHeight', 55))
    toward_sun = to_blender([math.sin(a) * math.cos(h), math.sin(h), math.cos(a) * math.cos(h)]).normalized()
    sun_data = bpy.data.lights.new('Sun', 'SUN')
    sun_data.energy = float(look.get('sunPower', 2.0)) * 1.6
    sun_data.angle = math.radians(1.5)
    sun_data.color = (1.0, 0.957, 0.902)
    if sun_data.energy > 0.001:
        sun = bpy.data.objects.new('Sun', sun_data)
        sun.rotation_euler = toward_sun.to_track_quat('Z', 'Y').to_euler()
        scene.collection.objects.link(sun)

    # the scene's own lights, the environment around it, and the air in it
    surfaces.add_lights(scene, job.get('lights'))
    surfaces.build_world(scene, look)
    surfaces.add_haze(scene, float(look.get('haze', 0) or 0))

    # colour management: filmic-style tone mapping, exposure in stops
    vs = scene.view_settings
    try:
        vs.view_transform = 'AgX'
    except TypeError:
        vs.view_transform = 'Filmic'
    try:
        vs.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    vs.exposure = math.log2(max(0.05, float(look.get('exposure', 1.0))))
    return scene


def setup_camera(scene, job):
    """The shot camera. It is set frame by frame (never interpolated), so a cut is a clean cut."""
    cams = {int(c['f']): c for c in job['cameras']}
    frames = sorted(cams)
    data = bpy.data.cameras.new('Camera')
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 24.0
    cam = bpy.data.objects.new('Camera', data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dof = job.get('dof') or {}
    offset = int(job.get('frame_offset', 0))

    def place(sc, *_):
        f = sc.frame_current - offset
        c = cams.get(f) or cams[min(frames, key=lambda x: abs(x - f))]
        p, t = to_blender(c['p']), to_blender(c['t'])
        cam.location = p
        cam.rotation_euler = (t - p).to_track_quat('-Z', 'Y').to_euler()
        data.lens = 12.0 / math.tan(math.radians(float(c.get('fov', 35))) / 2)
        fstop = c.get('fstop') or dof.get('fstop')   # a shot's own aperture, else the job's
        data.dof.use_dof = bool(fstop)
        if fstop:
            data.dof.aperture_fstop = float(fstop)
            data.dof.focus_distance = (t - p).length

    bpy.app.handlers.frame_change_pre.append(place)
    place(scene)
    return cams


def setup_speaker_light(scene, job, cams):
    """Whoever is speaking gets a light from behind and above, so their outline glows against the room.
    The light sits on the far side of the speaker from the camera, wherever the camera is in that shot."""
    sp = job.get('speaker_light') or {}
    cues = sp.get('speakers') or []
    if not cues:
        return
    data = bpy.data.lights.new('Speaker rim', 'SPOT')
    data.spot_size = math.radians(float(sp.get('spread', 30)))
    data.spot_blend = 0.6
    data.shadow_soft_size = 0.06
    data.color = surfaces.hex_to_linear(sp.get('color', '#fff0dc'))[:3]
    ob = bpy.data.objects.new('Speaker rim', data)
    ob.visible_camera = False
    scene.collection.objects.link(ob)
    power = float(sp.get('power', 260))
    offset = int(job.get('frame_offset', 0))
    frames = sorted(cams)

    def place(sc, *_):
        f = sc.frame_current - offset
        best, w = None, 0.0
        for c in cues:                                   # fades up as a line starts and down after it ends
            fade = min((f - c['f0'] + 6) / 6.0, (c['f1'] + 10 - f) / 10.0)
            if fade > w:
                best, w = c, fade
        data.energy = float(best.get('power', power) if best else power) * max(0.0, min(1.0, w))
        if not best:
            return
        cam = cams.get(f) or cams[min(frames, key=lambda x: abs(x - f))]
        head, eye = to_blender(best['head']), to_blender(cam['p'])
        away = head - eye
        away.z = 0
        if away.length < 1e-4:
            away.y = 1.0
        away.normalize()
        side = away.cross(surfaces.Vector((0, 0, 1)))
        pos = head + away * 1.0 + side * 0.45 + surfaces.Vector((0, 0, 0.85))
        ob.location = pos
        ob.rotation_euler = (head - pos).to_track_quat('-Z', 'Y').to_euler()

    bpy.app.handlers.frame_change_pre.append(place)
    place(scene)


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
    c.adaptive_threshold = 0.006 if c.samples >= 300 else 0.012
    c.max_bounces = 12
    c.diffuse_bounces = 6   # interiors are mostly lit by light that has bounced
    c.glossy_bounces = 6
    c.transmission_bounces = 8
    c.volume_bounces = 1
    c.transparent_max_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    c.sample_clamp_indirect = 8.0  # tames fireflies from small bright paths
    # moving things smear across the open shutter, as in a film camera
    if job.get('kind') == 'shot' and job.get('motion_blur', True):
        r.use_motion_blur = True
        r.motion_blur_shutter = 0.5
    surfaces.lens_finish(scene, float(job.get('lens', 1.0)))


def main():
    job_dir, out_dir, first, last = args()
    with open(os.path.join(job_dir, 'job.json')) as fh:
        job = json.load(fh)
    os.makedirs(out_dir, exist_ok=True)
    scene = setup_scene(job, job_dir)
    cams = setup_camera(scene, job)
    setup_speaker_light(scene, job, cams)
    setup_render(scene, job)

    f0, f1 = job['frames']
    first = f0 if first is None else max(f0, first)
    last = f1 if last is None else min(f1, last)
    # glTF time 0 lands on Blender frame 0 when the importer runs at the job's frame rate
    offset = int(job.get('frame_offset', 0))
    # "on twos": a job with step 2 renders every second frame and holds it, as hand-drawn animation does
    step = max(1, int(job.get('step', 1)))
    held = None
    for f in range(first, last + 1):
        path = os.path.join(out_dir, 'frame_%04d.png' % f)
        if (f - f0) % step and held:
            shutil.copyfile(held, path)
            continue
        held = path
        started = time.time()
        scene.frame_set(f + offset)
        scene.render.filepath = os.path.join(out_dir, 'frame_%04d.png' % f)
        bpy.ops.render.render(write_still=True)
        surfaces.film_finish(scene.render.filepath, f, float(job.get('grain', 1.0)))
        print('rendered frame %d in %.1f s' % (f, time.time() - started), flush=True)


if __name__ == '__main__':
    main()
