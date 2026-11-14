"""Rigroom render server: renders frames of a Blender file brought by a job, as the file was made.

    python render_blend.py JOB_DIR OUT_DIR FIRST LAST

JOB_DIR holds scene.blend and job.json. The file keeps its own engine, sets, lights and animation;
the job may only set the frame size ("width", or "scale" as a fraction of the file's own size),
the quality ("samples"), and "step" (render every Nth frame and hold it). Scripts inside the file
never run. Frames are written as OUT_DIR/frame_NNNN.png.
"""
import json
import os
import shutil
import sys
import time

import bpy


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    job_dir, out_dir, first, last = argv[0], argv[1], int(argv[2]), int(argv[3])
    with open(os.path.join(job_dir, 'job.json')) as fh:
        job = json.load(fh)
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=os.path.join(job_dir, 'scene.blend'), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    if job.get('scene_name') and job['scene_name'] in bpy.data.scenes:
        scene = bpy.data.scenes[job['scene_name']]
        bpy.context.window.scene = scene
    r = scene.render
    # size: the file's own shape, scaled
    w0, h0 = r.resolution_x * r.resolution_percentage / 100, r.resolution_y * r.resolution_percentage / 100
    k = float(job['width']) / w0 if job.get('width') else float(job.get('scale', 1.0))
    r.resolution_x, r.resolution_y, r.resolution_percentage = int(round(w0 * k / 2) * 2), int(round(h0 * k / 2) * 2), 100
    # quality
    if job.get('samples'):
        if r.engine == 'CYCLES':
            scene.cycles.samples = int(job['samples'])
        elif hasattr(scene, 'eevee'):
            scene.eevee.taa_render_samples = int(job['samples'])
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.image_settings.color_depth = '8'
    r.use_file_extension = True
    os.makedirs(out_dir, exist_ok=True)
    print('rendering %s with %s at %dx%d, frames %d-%d of %d-%d, %s fps' % (os.path.basename(job_dir), r.engine, r.resolution_x, r.resolution_y,
          first, last, scene.frame_start, scene.frame_end, r.fps / r.fps_base), flush=True)
    step = max(1, int(job.get('step', 1)))
    f0 = int(job['frames'][0])
    held = None
    for f in range(first, last + 1):
        path = os.path.join(out_dir, 'frame_%04d.png' % f)
        if (f - f0) % step and held:
            shutil.copyfile(held, path)
            continue
        started = time.time()
        scene.frame_set(f)
        r.filepath = path
        bpy.ops.render.render(write_still=True, scene=scene.name)
        held = path
        print('rendered frame %d in %.1f s' % (f, time.time() - started), flush=True)


if __name__ == '__main__':
    main()
