// Photoreal still render: path-traces the current frame with real light bounces.
// The renderer is loaded only when first used, so the editor starts fast.
import { ctx, startTracing, saveFile, toast } from './app.js';

const $ = s => document.querySelector(s);
let lib = null, tracer = null, envCube = null, job = null;

async function loadLib() {
  if (!lib) lib = await import('three-gpu-pathtracer');
  return lib;
}
// The path tracer wants the environment as a cube map; the viewport uses a pre-filtered one.
function traceEnvironment() {
  const { THREE, renderer, RoomEnvironment } = ctx;
  if (envCube) return envCube;
  const rt = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType });
  const cam = new THREE.CubeCamera(0.1, 100, rt), room = new RoomEnvironment();
  cam.update(renderer, room); envCube = rt.texture; return envCube;
}
function finish(restore, message, bad) {
  $('#renderBar').hidden = true; $('#renderStill').disabled = false;
  if (job) { ctx.scene.environment = job.viewEnv; job.session.restore(); job = null; }
  if (restore) { ctx.renderer.setRenderTarget(null); ctx.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); ctx.layoutFrame(); }
  if (message) toast(message, bad);
}

async function renderStill() {
  if (job) return;
  const target = Math.max(4, Math.min(4000, Math.round(+$('#rSamples').value || 64))), width = +$('#rSize').value || 1280;
  $('#renderStill').disabled = true; $('#renderBar').hidden = false; $('#renderMsg').textContent = 'Loading renderer…'; $('#renderProg').value = 0;
  let WebGLPathTracer;
  try { ({ WebGLPathTracer } = await loadLib()); }
  catch (e) { $('#renderBar').hidden = true; $('#renderStill').disabled = false; return toast('The photoreal renderer could not load. Check the connection.', true); }
  const { renderer, scene, camera, canvas } = ctx;
  const session = startTracing({ step });
  job = { session, viewEnv: scene.environment, target, started: performance.now(), stopped: false, ready: false };
  try {
    if (scene.environment) scene.environment = traceEnvironment();
    if (!tracer) { tracer = new WebGLPathTracer(renderer); tracer.bounces = 5; tracer.filterGlossyFactor = 0.5; tracer.tiles.set(2, 2); tracer.fadeDuration = 0; tracer.minSamples = 1; tracer.renderDelay = 0; tracer.dynamicLowRes = false; }
    // render at a fixed output size, whatever the viewport is; the canvas keeps its on-screen box
    tracer.renderScale = 1; renderer.setPixelRatio(1); renderer.setSize(width, Math.round(width / camera.aspect), false);
    $('#renderMsg').textContent = 'Preparing scene…';
    await new Promise(r => setTimeout(r, 30));
    scene.updateMatrixWorld(true); tracer.setScene(scene, camera); job.started = performance.now(); job.ready = true;
  } catch (e) { console.error(e); return finish(true, 'This device could not start the photoreal renderer: ' + (e && e.message || e), true); }

  function step() {
    if (!job || !job.ready) return;
    try { tracer.renderSample(); } catch (e) { console.error(e); return finish(true, 'The photoreal render failed: ' + (e && e.message || e), true); }
    const n = Math.floor(tracer.samples);
    $('#renderProg').value = Math.min(1, n / job.target);
    $('#renderMsg').textContent = tracer.isCompiling ? 'Compiling shaders…' : ('Sample ' + n + ' of ' + job.target);
    if (n >= job.target || job.stopped) {
      const secs = ((performance.now() - job.started) / 1000).toFixed(0), got = n;
      if (got < 1) return finish(true, 'Render stopped before the first sample.');
      canvas.toBlob(blob => {
        finish(true);
        if (blob) { saveFile('rigroom-render-f' + String(Math.round(ctx.frame)).padStart(3, '0') + '.png', blob); toast('Rendered ' + got + ' samples in ' + secs + ' s.'); }
        else toast('The render finished but the image could not be saved.', true);
      }, 'image/png');
      job.stopped = false; job.target = Infinity;   // hold the image on screen until toBlob returns
    }
  }
}

export function initTrace() {
  $('#renderStill').onclick = renderStill;
  $('#renderStop').onclick = () => { if (job) job.stopped = true; };
}
