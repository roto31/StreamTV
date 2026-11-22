/* StreamTV UI — core helpers.
 * Loaded synchronously in <head> so every page script (even ones inline in the content block)
 * can rely on these globals. Contract preserved from the legacy base.html:
 *   window.authenticatedFetch / getApiKey / setApiKey / getCsrfToken
 *   window.registerActions / StreamTVActions / openWindow / whenDomReady / bindActionHandlers
 *   window.toggleTheme, localStorage keys: 'theme' ('dark'|'light'), 'streamtv_api_key'
 *   declarative [data-action] dispatch (data-args, data-action-event, data-self-only,
 *   data-prevent-default, data-stop-propagation, data-pass-event)
 */
(function () {
  'use strict';

  /* ---------- Theme ---------- */
  var THEME_KEY = 'theme';
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function storedTheme() {
    try { var v = localStorage.getItem(THEME_KEY); return v === 'light' || v === 'dark' ? v : null; }
    catch (e) { return null; }
  }
  function systemTheme() { return mq && mq.matches ? 'dark' : (mq ? 'light' : 'dark'); }
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    if (document.body) document.body.setAttribute('data-theme', theme);  // legacy selector compat
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
      meta.setAttribute('content', theme === 'dark' ? '#0b0b0d' : '#f5f5f7');
    });
    var icon = document.getElementById('themeIcon');
    if (icon) icon.textContent = theme === 'dark' ? 'light_mode' : 'dark_mode';
    var btn = document.getElementById('themeToggleButton');
    if (btn) {
      var next = theme === 'dark' ? 'light' : 'dark';
      btn.setAttribute('aria-label', 'Switch to ' + next + ' appearance');
      btn.setAttribute('title', 'Switch to ' + next + ' appearance');
      btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    }
  }
  function currentTheme() { return document.documentElement.getAttribute('data-theme') || storedTheme() || systemTheme(); }
  window.toggleTheme = function toggleTheme() {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* storage blocked */ }
    applyTheme(next);
  };
  window.updateThemeIcon = function () { applyTheme(currentTheme()); };
  applyTheme(storedTheme() || systemTheme());           // before first paint: no flash
  if (mq && mq.addEventListener) mq.addEventListener('change', function () {
    if (!storedTheme()) applyTheme(systemTheme());      // follow the OS until the user chooses
  });

  /* ---------- API authentication helpers ---------- */
  var API_KEY_STORAGE_KEY = 'streamtv_api_key';
  function getApiKey() {
    try { return localStorage.getItem(API_KEY_STORAGE_KEY) || ''; }
    catch (e) { console.warn('Unable to read API key from storage', e); return ''; }
  }
  function setApiKey(value) {
    try {
      var v = (value || '').trim();
      if (v) localStorage.setItem(API_KEY_STORAGE_KEY, v); else localStorage.removeItem(API_KEY_STORAGE_KEY);
      document.dispatchEvent(new CustomEvent('streamtv:api-key-changed', { detail: { hasKey: !!v } }));
    } catch (e) { console.warn('Unable to persist API key', e); }
  }
  function getCsrfToken() {
    try {
      var row = document.cookie.split('; ').find(function (r) { return r.indexOf('csrf_token=') === 0; });
      return row ? row.split('=')[1] : '';
    } catch (e) { return ''; }
  }
  async function authenticatedFetch(url, options) {
    var opts = Object.assign({}, options || {});
    var method = String(opts.method || 'GET').toUpperCase();
    opts.method = method;
    var headers = new Headers(opts.headers || {});
    var apiKey = getApiKey();
    if (apiKey) { headers.set('Authorization', 'Bearer ' + apiKey); headers.set('X-API-Key', apiKey); }
    if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
      var csrf = getCsrfToken();
      if (csrf) headers.set('X-CSRF-Token', csrf);
    }
    headers.set('X-Requested-With', 'XMLHttpRequest');
    opts.headers = headers;
    if (!opts.credentials) opts.credentials = 'same-origin';
    return fetch(url, opts);
  }
  window.authenticatedFetch = authenticatedFetch;
  window.getApiKey = getApiKey;
  window.setApiKey = setApiKey;
  window.getCsrfToken = getCsrfToken;

  /* ---------- Declarative actions ---------- */
  window.StreamTVActions = window.StreamTVActions || {};
  window.registerActions = function registerActions(actions) { Object.assign(window.StreamTVActions, actions || {}); };
  window.openWindow = function openWindow(url, target) { window.open(url, target || '_blank', 'noopener'); };
  window.whenDomReady = function whenDomReady(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn();
  };
  window.bindActionHandlers = function bindActionHandlers() { /* delegated; kept for back-compat */ };

  function resolveAction(name) {
    if (!name) return null;
    if (typeof window.StreamTVActions[name] === 'function') return window.StreamTVActions[name];
    var ctx = window, parts = name.split('.');
    for (var i = 0; i < parts.length; i++) ctx = ctx == null ? undefined : ctx[parts[i]];
    return typeof ctx === 'function' ? ctx : null;
  }
  function parseArgs(el) {
    var raw = el.dataset.args;
    if (!raw) return [];
    try { return JSON.parse(raw); }
    catch (err) { console.error('Failed to parse data-args for action element:', el, err); return []; }
  }
  function dispatch(event) {
    var el = event.target.closest && event.target.closest('[data-action]');
    if (!el || !el.dataset.action) return;
    if (event.type !== (el.dataset.actionEvent || 'click')) return;
    if (el.dataset.selfOnly === 'true' && event.target !== el) return;
    if (el.disabled || el.classList.contains('disabled')) return;
    var href = el.tagName === 'A' ? (el.getAttribute('href') || '') : '';
    if (el.dataset.preventDefault === 'true' || href === '#' || href.indexOf('javascript:') === 0) event.preventDefault();
    if (el.dataset.stopPropagation === 'true') event.stopPropagation();
    var fn = resolveAction(el.dataset.action);
    if (!fn) { console.warn('Action handler "' + el.dataset.action + '" not found for', el); return; }
    var args = parseArgs(el);
    fn.apply(el, el.dataset.passEvent === 'true' ? args.concat([event]) : args);
  }
  ['click', 'change', 'input'].forEach(function (t) { document.addEventListener(t, dispatch, true); });

  document.addEventListener('DOMContentLoaded', function () { applyTheme(currentTheme()); });
})();
