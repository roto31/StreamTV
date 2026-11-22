/* StreamTV UI — application shell behaviour (sidebar, status, global search, disclosures). */
(function () {
  'use strict';
  var MOBILE_BP = 960;
  var $ = function (id) { return document.getElementById(id); };
  var isMobile = function () { return window.innerWidth <= MOBILE_BP; };

  /* ---------- Sidebar ---------- */
  function setDrawer(open) {
    var drawer = $('drawer'), overlay = $('drawerOverlay'), btn = $('drawerToggleButton');
    if (!drawer) return;
    drawer.classList.toggle('closed', !open);
    if (open) drawer.removeAttribute('inert'); else drawer.setAttribute('inert', '');
    if (overlay) overlay.classList.toggle('active', open && isMobile());
    if (btn) btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    document.body.classList.toggle('drawer-open-mobile', open && isMobile());
    if (!isMobile()) { try { localStorage.setItem('streamtv_drawer', open ? 'open' : 'closed'); } catch (e) { /* ignore */ } }
  }
  window.toggleDrawer = function () { var d = $('drawer'); setDrawer(d ? d.classList.contains('closed') : true); };
  window.closeDrawer = function () { setDrawer(false); };

  function initDrawer() {
    var saved = null;
    try { saved = localStorage.getItem('streamtv_drawer'); } catch (e) { /* ignore */ }
    setDrawer(isMobile() ? false : saved !== 'closed');
    var btn = $('drawerToggleButton'); if (btn) btn.addEventListener('click', window.toggleDrawer);
    var ov = $('drawerOverlay'); if (ov) ov.addEventListener('click', window.closeDrawer);
    var tb = $('themeToggleButton'); if (tb) tb.addEventListener('click', window.toggleTheme);
    document.addEventListener('click', function (e) {
      if (!isMobile()) return;
      var link = e.target.closest && e.target.closest('.drawer .nav-link');
      if (link && link.href && !link.target && !link.hasAttribute('aria-expanded')) setTimeout(window.closeDrawer, 80);
    });
    document.addEventListener('keydown', function (e) {
      var d = $('drawer');
      if (e.key === 'Escape' && isMobile() && d && !d.classList.contains('closed')) { window.closeDrawer(); if (btn) btn.focus(); }
    });
    var lastMobile = isMobile();
    window.addEventListener('resize', function () {
      var m = isMobile();
      if (m !== lastMobile) { lastMobile = m; setDrawer(!m); }
    });
  }

  /* ---------- Disclosure groups (Documentation, Help) ---------- */
  function initDisclosures() {
    document.querySelectorAll('[data-dropdown-target]').forEach(function (btn) {
      var panel = $(btn.getAttribute('data-dropdown-target'));
      if (!panel) return;
      var parent = btn.closest('.nav-dropdown');
      var sync = function () {
        var open = parent.classList.contains('active');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        panel.hidden = !open;
      };
      sync();
      btn.addEventListener('click', function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        parent.classList.toggle('active'); sync();
      });
    });
  }

  /* ---------- Live status ---------- */
  function setStatus(ok) {
    var ind = $('statusIndicator'), txt = $('statusText');
    if (ind) ind.className = 'status-indicator ' + (ok ? 'online' : 'offline');
    if (txt) txt.textContent = ok ? 'Online' : 'Offline';
  }
  async function checkStatus() {
    try {
      var res = await fetch('/health', { cache: 'no-store' });
      var data = await res.json();
      setStatus(data && data.status === 'healthy');
    } catch (e) { setStatus(false); }
  }

  /* ---------- Global search (ARIA combobox) ---------- */
  var NAV_PAGES = [
    { title: 'Dashboard', keywords: 'home status overview', url: '/', icon: 'dashboard' },
    { title: 'Player', keywords: 'watch preview mpegts', url: '/player', icon: 'play_circle' },
    { title: 'Manage Channels', keywords: 'channel lineup', url: '/channels', icon: 'tv' },
    { title: 'Channel Builder', keywords: 'builder create newchannel', url: '/builder', icon: 'build' },
    { title: 'Import Channels', keywords: 'yaml upload m3u', url: '/import', icon: 'upload' },
    { title: 'Media Items', keywords: 'library vod', url: '/media', icon: 'video_library' },
    { title: 'Playlists', keywords: 'playlist queue', url: '/playlists', icon: 'playlist_play' },
    { title: 'Playouts', keywords: 'on-air timeline', url: '/playouts', icon: 'play_circle_outline' },
    { title: 'Schedules', keywords: 'epg guide schedule', url: '/schedules', icon: 'schedule' },
    { title: 'Settings', keywords: 'preferences config', url: '/settings', icon: 'tune' },
    { title: 'Transcoding', keywords: 'ffmpeg encode profiles', url: '/settings/transcoding', icon: 'settings_applications' },
    { title: 'HDHomeRun', keywords: 'tuner discovery ssdp', url: '/settings/hdhr', icon: 'tv' },
    { title: 'Playout Settings', keywords: 'stall seek cache', url: '/settings/playout', icon: 'schedule' },
    { title: 'Plex API', keywords: 'plex live tv', url: '/settings/plex', icon: 'integration_instructions' },
    { title: 'Source Authentication', keywords: 'youtube archive oauth', url: '/settings/auth', icon: 'vpn_key' },
    { title: 'Backup & Restore', keywords: 'export import backup', url: '/settings/backup', icon: 'backup' },
    { title: 'Streaming Logs', keywords: 'ffmpeg log errors', url: '/logs', icon: 'terminal' },
    { title: 'Plex Server Logs', keywords: 'plex log', url: '/plex-logs', icon: 'dvr' },
    { title: 'Health Check', keywords: 'diagnostics health', url: '/health-check', icon: 'health_and_safety' },
    { title: 'Cache Status', keywords: 'ram youtube cache', url: '/cache', icon: 'storage' },
    { title: 'Test Stream', keywords: 'debug probe', url: '/test-stream', icon: 'bug_report' },
    { title: 'Documentation', keywords: 'help guides docs', url: '/documentation', icon: 'menu_book' }
  ];
  var cache = { at: 0, channels: [], media: [] };
  var results = [], activeIndex = -1, timer = null;
  var input, list, live;

  function announce(msg) {
    if (!live) {
      live = document.getElementById('searchLive');
      if (!live) {
        live = document.createElement('div');
        live.id = 'searchLive';
        live.className = 'sr-only';
        live.setAttribute('role', 'status');
        live.setAttribute('aria-live', 'polite');
        live.setAttribute('aria-atomic', 'true');
        document.body.appendChild(live);
      }
    }
    live.textContent = '';
    // Force a DOM tick so repeated identical announcements are spoken.
    setTimeout(function () { live.textContent = msg; }, 20);
  }

  async function loadIndex() {
    if (Date.now() - cache.at < 60000) return;
    var get = async function (u) { try { var r = await fetch(u); return r.ok ? await r.json() : []; } catch (e) { return []; } };
    var chans = await get('/api/channels'), media = await get('/api/media');
    cache.channels = Array.isArray(chans) ? chans : [];
    cache.media = Array.isArray(media) ? media : [];
    cache.at = Date.now();
  }
  async function performSearch(q) {
    await loadIndex();
    var needle = q.toLowerCase(), out = [];
    NAV_PAGES.forEach(function (p) {
      var hay = (p.title + ' ' + (p.keywords || '')).toLowerCase();
      if (hay.indexOf(needle) > -1)
        out.push({ type: 'page', title: p.title, subtitle: 'Page', url: p.url, icon: p.icon });
    });
    cache.channels.forEach(function (c) {
      if (String(c.name || '').toLowerCase().indexOf(needle) > -1 || String(c.number || '').indexOf(q) > -1 ||
          (c.group && String(c.group).toLowerCase().indexOf(needle) > -1))
        out.push({ type: 'channel', title: c.name, subtitle: 'Channel ' + c.number, url: '/channels', icon: 'tv' });
    });
    cache.media.filter(function (m) {
      return String(m.title || '').toLowerCase().indexOf(needle) > -1 ||
             (m.description && String(m.description).toLowerCase().indexOf(needle) > -1);
    }).slice(0, 5).forEach(function (m) {
      out.push({ type: 'media', title: m.title, subtitle: m.source, url: '/media?q=' + encodeURIComponent(m.title), icon: 'video_library' });
    });
    results = out.slice(0, 12);
    render(q);
  }
  function hide() {
    if (list) { list.remove(); list = null; }
    results = []; activeIndex = -1;
    if (input) { input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); }
  }
  function render(q) {
    var form = document.querySelector('.search-form');
    if (!form) return;
    if (list) list.remove();
    list = document.createElement('div');
    list.className = 'search-results';
    list.id = 'searchResults';
    list.setAttribute('role', 'listbox');
    list.setAttribute('aria-label', 'Search results');
    if (!results.length) {
      var none = document.createElement('div');
      none.className = 'search-empty'; none.textContent = 'No matches for “' + q + '”. Press Return to search channels.';
      list.appendChild(none);
      announce('No matches for ' + q);
    } else {
      announce(results.length + (results.length === 1 ? ' result' : ' results') + ' available');
    }
    results.forEach(function (r, i) {
      var item = document.createElement('div');
      item.className = 'search-result-item';
      item.id = 'search-opt-' + i;
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', 'false');
      item.dataset.action = 'navigateToResult';
      item.dataset.args = JSON.stringify([r]);
      var ic = document.createElement('span'); ic.className = 'material-icons'; ic.setAttribute('aria-hidden', 'true'); ic.textContent = r.icon;
      var wrap = document.createElement('div'); wrap.className = 'search-result-text';
      var t = document.createElement('div'); t.className = 'search-result-title'; t.textContent = r.title;
      var s = document.createElement('div'); s.className = 'search-result-sub'; s.textContent = r.subtitle || '';
      wrap.appendChild(t); wrap.appendChild(s); item.appendChild(ic); item.appendChild(wrap);
      list.appendChild(item);
    });
    form.appendChild(list);
    if (typeof window.convertMaterialIcons === 'function') window.convertMaterialIcons(list);
    input.setAttribute('aria-expanded', 'true');
    input.setAttribute('aria-controls', 'searchResults');
    activeIndex = -1;
  }
  function setActive(i) {
    if (!list || !results.length) return;
    activeIndex = (i + results.length) % results.length;
    list.querySelectorAll('[role="option"]').forEach(function (el, idx) {
      var on = idx === activeIndex;
      el.setAttribute('aria-selected', on ? 'true' : 'false');
      el.classList.toggle('is-active', on);
      if (on) { input.setAttribute('aria-activedescendant', el.id); el.scrollIntoView({ block: 'nearest' }); }
    });
  }
  window.navigateToResult = function (r) { hide(); if (r && r.url) window.location.href = r.url; };

  function initSearch() {
    input = $('globalSearchInput');
    if (!input) return;
    input.addEventListener('input', function (e) {
      clearTimeout(timer);
      var q = e.target.value.trim();
      if (q.length < 2) { hide(); return; }
      timer = setTimeout(function () { performSearch(q); }, 200);
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); if (!list && input.value.trim().length > 1) performSearch(input.value.trim()); else setActive(activeIndex + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(activeIndex - 1); }
      else if (e.key === 'Escape') { if (list) { e.preventDefault(); hide(); } else { input.blur(); } }
      else if (e.key === 'Enter') {
        e.preventDefault();
        var q = input.value.trim();
        if (results[activeIndex >= 0 ? activeIndex : 0]) window.navigateToResult(results[activeIndex >= 0 ? activeIndex : 0]);
        else if (q) window.location.href = '/channels?search=' + encodeURIComponent(q);
      }
    });
    document.addEventListener('click', function (e) { if (!e.target.closest('.search-form')) hide(); });
    // "/" or Cmd/Ctrl+K focuses search (skipped while typing in a field).
    document.addEventListener('keydown', function (e) {
      var tag = (e.target.tagName || '').toLowerCase();
      var typing = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;
      if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing && !e.metaKey && !e.ctrlKey)) {
        e.preventDefault(); input.focus(); input.select();
      }
    });
    var hint = document.querySelector('.search-kbd');
    if (hint && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)) hint.textContent = '⌘K';
  }

  /* ---------- Boot ---------- */
  function boot() {
    initDrawer(); initDisclosures(); initSearch();
    checkStatus(); setInterval(checkStatus, 30000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) checkStatus(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
