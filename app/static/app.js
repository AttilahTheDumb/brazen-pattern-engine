(() => {
  const state = { sample: null, study: null, fit: null, pattern: null, svg: null };
  const API_BASE = String(window.BRAZEN_API_BASE || '').replace(/\/$/, '');
  let API_TOKEN = sessionStorage.getItem('brazen_api_token') || '';
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const toast = (message) => { const node = $('#toast'); node.textContent = message; node.classList.add('visible'); clearTimeout(toast.timer); toast.timer = setTimeout(() => node.classList.remove('visible'), 3200); };
  const setResult = (selector, message, kind = '') => { const node = $(selector); node.textContent = message; node.className = `result-box ${kind}`; };
  const pretty = (value) => JSON.stringify(value, null, 2);
  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {}); headers.set('Content-Type', 'application/json'); if (API_TOKEN) headers.set('Authorization', `Bearer ${API_TOKEN}`);
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    const data = await response.json();
    if (response.status === 401) { $('#connection-status').innerHTML = '<span class="signal-dot amber-dot"></span>API auth required'; throw new Error('API authentication required. Use Connect API to enter the session token.'); }
    if (!response.ok) throw new Error(data.error || 'The local engine rejected the request.');
    $('#connection-status').innerHTML = '<span class="signal-dot"></span>Engine online';
    return data;
  }
  function connectApi() {
    if (!API_BASE) { toast('Local mode is same-origin; no API token is required.'); return; }
    const token = window.prompt('Enter the Render API token for this browser session. It is kept in session memory only.');
    if (!token) return;
    API_TOKEN = token.trim(); sessionStorage.setItem('brazen_api_token', API_TOKEN); $('#connection-status').innerHTML = '<span class="signal-dot"></span>API connected'; toast('API token stored for this browser session.');
  }
  function switchView(view) {
    $$('.view').forEach((node) => { const active = node.id === `${view}-view`; node.hidden = !active; node.classList.toggle('active', active); });
    $$('.nav-item').forEach((node) => { const active = node.dataset.view === view; node.classList.toggle('active', active); node.setAttribute('aria-selected', active); });
    $('#view-title').textContent = view === 'overview' ? 'Overview' : ({ measurements: 'Measurement floor', corrections: 'Fit corrections', geometry: 'Geometry lab' }[view] || view);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  async function loadSample(showToast = true) {
    state.sample = await api('/api/sample');
    state.fit = state.sample.fitCorrection; state.pattern = state.sample.pattern;
    $('#correction-state').textContent = state.fit.recordId + ' / loaded';
    setResult('#fit-result', 'Sample record loaded locally. Choose a floor, then validate.', '');
    renderPattern(state.pattern);
    if (showToast) toast('Sample pattern and fit record loaded locally.');
  }
  function parseFile(input, callback) {
    const file = input.files?.[0]; if (!file) return;
    const reader = new FileReader(); reader.onload = () => { try { callback(JSON.parse(reader.result)); toast(`${file.name} loaded locally.`); } catch (error) { toast(`Could not parse ${file.name}: ${error.message}`); } }; reader.readAsText(file);
  }
  async function runFit() {
    if (!state.fit) await loadSample(false);
    const floor = Number($('#fit-floor').value || 10);
    try { const result = await api('/api/validate-fit', { method: 'POST', body: JSON.stringify({ record: state.fit, toleranceFitMm: floor }) }); setResult('#fit-result', pretty(result), result.status === 'PASS' ? 'pass' : 'fail'); $('#correction-state').textContent = `${state.fit.recordId} / ${result.trainable ? 'trainable' : 'retained only'}`; toast(result.status === 'PASS' ? 'Fit-correction gate passed.' : 'Fit-correction record retained with blockers.'); } catch (error) { setResult('#fit-result', error.message, 'fail'); }
  }
  function renderPattern(pattern) { if (!pattern) return; state.pattern = pattern; $('#hash-label').textContent = 'Ready for deterministic hash'; $('#geometry-result').textContent = 'Pattern loaded locally. Run hash + inspect.'; $('#download-svg').disabled = true; }
  async function runPattern() {
    if (!state.pattern) await loadSample(false);
    try { const result = await api('/api/hash-pattern', { method: 'POST', body: JSON.stringify({ pattern: state.pattern }) }); state.svg = result.svg; $('#hash-label').textContent = result.patternHash; $('#geometry-result').textContent = `${result.status}\n${result.patternHash}\n\nInspection export only.`; $('#geometry-result').className = 'result-box pass'; $('#svg-preview').innerHTML = `<div class="preview-grid"></div>${result.svg}`; $('#download-svg').disabled = false; toast('Deterministic geometry hash verified.'); } catch (error) { setResult('#geometry-result', error.message, 'fail'); }
  }
  async function runStudy() {
    if (!state.study) { setResult('#study-result', 'No study loaded. Select a JSON file first.', 'fail'); return; }
    const policy = Number($('#tem-policy').value || 0);
    try { const result = await api('/api/repeatability', { method: 'POST', body: JSON.stringify({ sessions: state.study.sessions || state.study, maxRelativeTemPct: policy || null }) }); setResult('#study-result', pretty(result), result.status === 'PASS' ? 'pass' : 'fail'); toast('Repeatability analysis completed locally.'); } catch (error) { setResult('#study-result', error.message, 'fail'); }
  }
  async function runAll() { await loadSample(false); await runFit(); await runPattern(); toast('Software gates checked. Physical gates remain human-owned.'); }
  $$('.nav-item').forEach((node) => node.addEventListener('click', () => switchView(node.dataset.view)));
  $$('[data-view-target]').forEach((node) => node.addEventListener('click', () => switchView(node.dataset.viewTarget)));
  $('[data-action="connect-api"]').addEventListener('click', connectApi);
  $('[data-action="load-sample"]').addEventListener('click', () => loadSample());
  $('[data-action="run-check"]').addEventListener('click', runAll);
  $('[data-action="validate-fit"]').addEventListener('click', runFit);
  $('[data-action="hash-pattern"]').addEventListener('click', runPattern);
  $('[data-action="run-study"]').addEventListener('click', runStudy);
  $('#fit-file').addEventListener('change', (event) => parseFile(event.target, (data) => { state.fit = data; $('#correction-state').textContent = `${data.recordId || 'record'} / loaded`; setResult('#fit-result', 'Record loaded locally. Choose a floor, then validate.'); }));
  $('#pattern-file').addEventListener('change', (event) => parseFile(event.target, (data) => renderPattern(data)));
  $('#study-file').addEventListener('change', (event) => parseFile(event.target, (data) => { state.study = data; setResult('#study-result', 'Study loaded locally. Enter an approved max inter-TEM policy, then analyse.'); }));
  $('#download-svg').addEventListener('click', () => { if (!state.svg) return; const blob = new Blob([state.svg], { type: 'image/svg+xml' }); const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'brazen-inspection.svg'; link.click(); URL.revokeObjectURL(link.href); });
  document.addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); $('#view-title').focus?.(); toast('Use the navigation to inspect a workspace.'); } });
  loadSample(false).catch(() => toast('Engine is offline. Start the local console server.'));
})();
