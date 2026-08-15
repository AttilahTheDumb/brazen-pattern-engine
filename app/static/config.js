// Localhost stays same-origin. GitHub Pages uses the Render API service.
window.BRAZEN_API_BASE = ['127.0.0.1', 'localhost'].includes(window.location.hostname)
  ? ''
  : 'https://brazen-pattern-engine-api.onrender.com';
