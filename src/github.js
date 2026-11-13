// GitHub access for Rigroom: one token, two repositories.
// The site repository (public) runs the renderer; the studio repository (private) holds scenes,
// models, render jobs and results. The token stays in this browser and is only sent to api.github.com.
const API = 'https://api.github.com';
const store = {
  get(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } },
  set(k, v) { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch (e) { /* storage unavailable */ } }
};
export function guessSite() {
  const m = location.hostname.match(/^([^.]+)\.github\.io$/i), seg = location.pathname.split('/').filter(Boolean)[0];
  return m && seg ? m[1] + '/' + seg : '';
}
const savedSite = store.get('rigroom.ghRepo');
export const conf = {
  token: store.get('rigroom.ghToken'),
  site: guessSite() || savedSite || '',
  studio: store.get('rigroom.studioRepo') || ((guessSite() || savedSite) ? (guessSite() || savedSite) + '-studio' : '')
};
export function saveConf({ token, studio }) {
  if (token !== undefined) { conf.token = token.trim(); store.set('rigroom.ghToken', conf.token); }
  if (studio !== undefined) { conf.studio = studio.trim().replace(/^https:\/\/github\.com\//, '').replace(/\/+$/, ''); store.set('rigroom.studioRepo', conf.studio); }
}
export const ready = () => !!(conf.token && /^[\w.-]+\/[\w.-]+$/.test(conf.studio));
export const canRender = () => ready() && /^[\w.-]+\/[\w.-]+$/.test(conf.site);

export async function gh(path, opts = {}) {
  const res = await fetch(API + path, {
    method: opts.method || 'GET', cache: 'no-store', body: opts.body,
    headers: { Authorization: 'Bearer ' + conf.token, Accept: opts.raw ? 'application/vnd.github.raw+json' : 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', ...(opts.body ? { 'Content-Type': 'application/json' } : {}) }
  });
  if (res.status === 404 && opts.allow404) return null;
  if (!res.ok) { let msg = 'HTTP ' + res.status; try { msg = (await res.json()).message || msg; } catch (e) { /* no body */ } const err = new Error(msg); err.status = res.status; throw err; }
  if (opts.raw === 'bytes') return res.arrayBuffer();
  if (opts.raw) return res.text();
  return res.status === 204 ? null : res.json();
}
export function b64(buf) {
  const u8 = buf instanceof Uint8Array ? buf : new Uint8Array(buf); let s = '';
  for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
  return btoa(s);
}
const enc = p => p.split('/').map(encodeURIComponent).join('/');
/** A file from the studio as text, or null if it does not exist. */
export const readText = path => gh(`/repos/${conf.studio}/contents/${enc(path)}?ref=main`, { raw: true, allow404: true });
/** A file from the studio as bytes (files up to 100 MB), or null. */
export const readBytes = path => gh(`/repos/${conf.studio}/contents/${enc(path)}?ref=main`, { raw: 'bytes', allow404: true });

/**
 * Can this token see the studio, and can it write there? A private repository the token cannot
 * see looks the same as a missing one (404), so that is checked before anything else.
 */
let access = null;
export async function checkStudio(force) {
  if (access && !force) return access;
  const r = await gh(`/repos/${conf.studio}`, { allow404: true });
  if (!r) { const e = new Error('cannot see the studio'); e.status = 404; throw e; }
  access = { write: !r.permissions || !!r.permissions.push, private: r.private };
  return access;
}
export function forgetAccess() { access = null; }
/** Write several files to the studio's main branch as one commit. files: [{ path, text } | { path, bytes }] */
export async function commitFiles(files, message) {
  const R = `/repos/${conf.studio}`, acc = await checkStudio();
  if (!acc.write) { const e = new Error('read only'); e.status = 403; throw e; }
  let ref, empty = false;
  try { ref = await gh(`${R}/git/ref/heads/main`); }
  catch (e) { if (e.status === 409) empty = true; else if (e.status === 404) { const x = new Error('The studio has no main branch.'); x.status = 422; throw x; } else throw e; }
  if (empty) {   // GitHub answers 409 only for a repository with no commits at all: start it with a README
    await gh(`${R}/contents/README.md`, { method: 'PUT', body: JSON.stringify({ message: 'Start the Rigroom studio', content: btoa('# Rigroom studio\n\nPrivate storage for Rigroom.\n'), branch: 'main' }) });
    ref = await gh(`${R}/git/ref/heads/main`);
  }
  const tree = [];
  for (const f of files) {
    const body = f.text != null ? { content: f.text, encoding: 'utf-8' } : { content: b64(f.bytes), encoding: 'base64' };
    const blob = await gh(`${R}/git/blobs`, { method: 'POST', body: JSON.stringify(body) });
    tree.push({ path: f.path, mode: '100644', type: 'blob', sha: blob.sha });
  }
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt) ref = await gh(`${R}/git/ref/heads/main`);
    const base = await gh(`${R}/git/commits/${ref.object.sha}`);
    const t = await gh(`${R}/git/trees`, { method: 'POST', body: JSON.stringify({ base_tree: base.tree.sha, tree }) });
    const c = await gh(`${R}/git/commits`, { method: 'POST', body: JSON.stringify({ message, tree: t.sha, parents: [ref.object.sha] }) });
    try { await gh(`${R}/git/refs/heads/main`, { method: 'PATCH', body: JSON.stringify({ sha: c.sha }) }); return c.sha; }
    catch (e) { if (e.status !== 422 || attempt === 2) throw e; }   // someone else committed first: rebuild on top
  }
}
/** Start the renderer on the site repository for a job in the studio. */
export const dispatchRender = id => gh(`/repos/${conf.site}/actions/workflows/render.yml/dispatches`, { method: 'POST', body: JSON.stringify({ ref: 'main', inputs: { job: id, store: 'studio' } }) });

export function explain(e) {
  if (e.status === 401) return 'GitHub rejected the token. Check it under Studio settings.';
  if (e.status === 403) return 'Your token can read the studio but not write to it. On GitHub, edit the token and set Contents to Read and write (and Actions to Read and write).';
  if (e.status === 404) return 'This token cannot see ' + conf.studio + '. Check the name under Studio settings, and that the token includes that repository.';
  if (e.status === 409) return 'The studio repository is empty or busy. Try again in a moment.';
  if (e.status === 422) return 'GitHub refused the request: ' + e.message;
  return e.status ? 'GitHub error: ' + e.message : 'Could not reach GitHub. Check the connection.';
}
