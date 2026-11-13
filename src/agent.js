// The built-in agent: a tool-use loop against the Claude API, called straight from the browser.
// The user's API key stays in this browser's storage and is only ever sent to api.anthropic.com.
import { TOOLS, systemPrompt, stateBlock, beginAgentTurn, endAgentTurn } from './app.js';

const $ = s => document.querySelector(s);
const API = 'https://api.anthropic.com/v1/messages';
const KEY_STORE = 'rigroom.apiKey', MODEL_STORE = 'rigroom.model';
const MAX_STEPS = 30;

const store = {
  get(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } },
  set(k, v) { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); return true; } catch (e) { return false; } }
};
let apiKey = store.get(KEY_STORE), busy = false, ac = null, pendingBubble = null;
const history = [];   // plain-text turns kept between requests

function scrollLog() { const p = $('#log'); p.scrollTop = p.scrollHeight; }
export function addMsg(cls, text) { const el = document.createElement('div'); el.className = 'msg ' + cls; el.textContent = text; $('#log').append(el); scrollLog(); return el; }
function addAct(text) { const el = document.createElement('div'); el.className = 'msg act'; el.textContent = '◆ ' + text; $('#log').insertBefore(el, pendingBubble || null); scrollLog(); }
function setBusy(b) { busy = b; $('#send').textContent = b ? 'Stop' : 'Send'; $('#send').classList.toggle('primary', !b); $('#prompt').disabled = b; }

async function callClaude(messages, signal) {
  const res = await fetch(API, {
    method: 'POST', signal,
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: $('#model').value,
      max_tokens: 16000,
      system: systemPrompt(),
      tools: TOOLS.map(t => ({ name: t.name, description: t.description, input_schema: t.input_schema })),
      messages
    })
  });
  let data = null; try { data = await res.json(); } catch (e) { /* non-JSON error body */ }
  if (!res.ok) { const err = new Error((data && data.error && data.error.message) || ('HTTP ' + res.status)); err.status = res.status; throw err; }
  return data;
}

async function runAgent(text) {
  if (busy) return;
  if (!apiKey) { $('#agentSetup').open = true; $('#apiKey').focus(); addMsg('err', 'Add your Claude API key under Agent settings first.'); return; }
  $('#chips').style.display = 'none';
  addMsg('user', text); const bubble = pendingBubble = addMsg('agent', 'Thinking…');
  setBusy(true); beginAgentTurn(addAct);
  const messages = history.slice(-10).concat([{ role: 'user', content: text + '\n\n' + stateBlock() }]);
  ac = new AbortController(); let finalText = '', mutated = false;
  try {
    for (let step = 0; step < MAX_STEPS; step++) {
      const resp = await callClaude(messages, ac.signal);
      const said = (resp.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n').trim();
      if (said) { finalText = said; bubble.textContent = said; scrollLog(); }
      if (resp.stop_reason !== 'tool_use') { if (resp.stop_reason === 'max_tokens' && !said) finalText = 'The reply was cut off before it finished.'; break; }
      messages.push({ role: 'assistant', content: resp.content });
      const results = [];
      for (const block of resp.content) {
        if (block.type !== 'tool_use') continue;
        const tool = TOOLS.find(t => t.name === block.name);
        let content, isError = false;
        try { if (!tool) throw new Error('Unknown tool ' + block.name); content = JSON.stringify(await tool.execute(block.input || {})); }
        catch (e) { content = String(e && e.message || e); isError = true; }
        results.push({ type: 'tool_result', tool_use_id: block.id, content, ...(isError ? { is_error: true } : {}) });
      }
      messages.push({ role: 'user', content: results });
      if (step === MAX_STEPS - 1) finalText = (finalText ? finalText + '\n' : '') + 'Stopped after ' + MAX_STEPS + ' steps; ask me to continue if it is not finished.';
    }
  } catch (e) {
    bubble.className = 'msg err';
    if (ac.signal.aborted) finalText = 'Stopped.';
    else if (e.status === 401) { finalText = 'That API key was rejected. Check it under Agent settings.'; $('#agentSetup').open = true; }
    else if (e.status === 429) finalText = 'Rate limited by the API. Wait a moment, then send again.';
    else if (e.status === 529 || e.status >= 500) finalText = 'The Claude API is busy right now. Try again shortly.';
    else if (e.status) finalText = 'The API refused the request: ' + e.message;
    else finalText = 'Could not reach the Claude API. Check the connection.';
  } finally {
    mutated = endAgentTurn(); pendingBubble = null; setBusy(false);
    const isErr = bubble.classList.contains('err');
    const out = finalText || (mutated ? 'Done.' : 'Nothing was changed.');
    bubble.textContent = out + (isErr && mutated ? ' Changes so far are kept; Undo removes them.' : '');
    if (!isErr) history.push({ role: 'user', content: text }, { role: 'assistant', content: out });
    scrollLog();
  }
}

export function initAgent() {
  const saved = store.get(MODEL_STORE); if (saved && [...$('#model').options].some(o => o.value === saved)) $('#model').value = saved;
  $('#apiKey').value = apiKey; $('#agentSetup').open = !apiKey;
  $('#saveKey').onclick = () => { apiKey = $('#apiKey').value.trim(); const ok = store.set(KEY_STORE, apiKey); store.set(MODEL_STORE, $('#model').value);
    addMsg('agent', apiKey ? (ok ? 'Key saved in this browser. Tell me what to animate.' : 'Key set for this visit; this browser would not store it.') : 'No key entered.'); if (apiKey) $('#agentSetup').open = false; };
  $('#forgetKey').onclick = () => { apiKey = ''; $('#apiKey').value = ''; store.set(KEY_STORE, ''); addMsg('agent', 'Key removed from this browser.'); };
  $('#model').onchange = () => store.set(MODEL_STORE, $('#model').value);
  $('#composer').addEventListener('submit', e => { e.preventDefault(); if (busy) { if (ac) ac.abort(); return; } const t = $('#prompt').value.trim(); if (!t) return; $('#prompt').value = ''; runAgent(t); });
  $('#prompt').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('#composer').requestSubmit(); } });
  document.querySelectorAll('.chip').forEach(c => c.onclick = () => runAgent(c.textContent));
}
