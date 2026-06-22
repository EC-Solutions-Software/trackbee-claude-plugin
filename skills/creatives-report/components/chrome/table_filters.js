// TrackBee Creatives report — client-side table glue.
//
// Wires up (all delegated off `data-action` attributes — no inline onclick):
//   * Store tabs           data-action="switch-store"     data-sid
//   * Platform tabs        data-action="filter-platform"  data-plat data-sid
//   * Format <select>      data-action="filter-format"    data-sid
//   * Search input         data-action="filter-search"    data-sid
//   * Sortable headers     th[data-sort] click-to-sort with asc/desc indicator
//   * Question buttons     data-action="ask-question"     data-q
//     (send-first like the attribution dashboard: clicking sends the
//     prompt via window.sendPrompt in a live artifact; clipboard copy
//     is the fallback when the page is opened as a plain file)

(function () {
  const state = {
    store:     null,
    platform:  {},
    format:    {},
    search:    {},
  };

  function switchStore(sid) {
    document.querySelectorAll('.store-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.store-tab').forEach(b => b.classList.remove('active'));
    const sec = document.getElementById('store-' + sid);
    if (sec) sec.style.display = 'block';
    const tab = document.querySelector('.store-tab[data-sid="' + sid + '"]');
    if (tab) tab.classList.add('active');
    state.store = sid;
    applyFilters(sid);
  }

  function filterPlatform(btn, plat, sid) {
    document.querySelectorAll('#store-' + sid + ' .plat-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.platform[sid] = plat;
    applyFilters(sid);
  }

  function filterFormat(sid) {
    const el = document.getElementById('fmt-' + sid);
    state.format[sid] = el ? (el.value || 'all') : 'all';
    applyFilters(sid);
  }

  function filterSearch(sid) {
    const el = document.getElementById('search-' + sid);
    state.search[sid] = el ? (el.value || '').toLowerCase() : '';
    applyFilters(sid);
  }

  function applyFilters(sid) {
    const plat   = state.platform[sid] || 'all';
    const fmt    = state.format[sid]   || 'all';
    const term   = state.search[sid]   || '';
    const rows = document.querySelectorAll('#tbody-' + sid + ' tr.ad-row');
    rows.forEach(function (row) {
      const rPlat   = row.dataset.platform || '';
      const rFmt    = row.dataset.format   || '';
      const rName   = row.dataset.name     || '';
      const platOk   = (plat === 'all'   || rPlat === plat);
      const fmtOk    = (fmt === 'all'    || rFmt === fmt);
      const searchOk = (!term            || rName.indexOf(term) !== -1);
      row.classList.toggle('hidden', !(platOk && fmtOk && searchOk));
    });
  }

  function sortByHeader(th) {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    const col = Array.from(th.parentElement.children).indexOf(th);
    const asc = th.dataset.asc !== 'true';
    th.dataset.asc = asc;
    th.parentElement.querySelectorAll('th').forEach(function (other) {
      if (other !== th) {
        other.classList.remove('sort-asc', 'sort-desc');
        delete other.dataset.asc;
      }
    });
    th.classList.toggle('sort-asc',  asc);
    th.classList.toggle('sort-desc', !asc);
    // Extract each row's sort key ONCE before sorting — a comparator that
    // queries the DOM runs O(n log n) traversals per click and janks on
    // multi-hundred-row tables.
    const keyed = Array.from(tbody.querySelectorAll('tr.ad-row')).map(function (r) {
      const cell = r.querySelectorAll('td')[col];
      const text = cell ? cell.textContent : '';
      const num = window.TB && window.TB.stripNumeric ? window.TB.stripNumeric(text) : parseFloat(text);
      return { row: r, text: text, num: num };
    });
    keyed.sort(function (a, b) {
      if (!isNaN(a.num) && !isNaN(b.num)) return asc ? a.num - b.num : b.num - a.num;
      return asc ? a.text.localeCompare(b.text) : b.text.localeCompare(a.text);
    });
    keyed.forEach(function (k) { tbody.appendChild(k.row); });
  }

  function activateQuestion(btn) {
    const text = btn.dataset.q || '';
    // Live artifact: send the prompt straight into the conversation.
    if (typeof window.sendPrompt === 'function') {
      try { window.sendPrompt(text); return; }
      catch (err) { console.warn('sendPrompt failed', err); }
    }
    // Plain-file fallback: copy to clipboard.
    const label = btn.querySelector('.q-copy-label');
    const done = function () {
      btn.classList.add('copied');
      if (label) label.textContent = 'Copied';
      setTimeout(function () {
        btn.classList.remove('copied');
        if (label) label.textContent = 'Copy';
      }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else {
      fallbackCopy(text); done();
    }
  }

  function fallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  // ── Delegated event wiring (no inline onclick) ────────────────────
  document.addEventListener('click', function (e) {
    const th = e.target.closest('.audit-table thead th[data-sort]');
    if (th) { sortByHeader(th); return; }
    const t = e.target.closest('[data-action]');
    if (!t) return;
    const action = t.dataset.action;
    if (action === 'switch-store') {
      switchStore(t.dataset.sid);
    } else if (action === 'filter-platform') {
      filterPlatform(t, t.dataset.plat, t.dataset.sid);
    } else if (action === 'ask-question') {
      activateQuestion(t);
    }
  });

  document.addEventListener('change', function (e) {
    const t = e.target.closest('[data-action="filter-format"]');
    if (t) filterFormat(t.dataset.sid);
  });

  document.addEventListener('input', function (e) {
    const t = e.target.closest('[data-action="filter-search"]');
    if (t) filterSearch(t.dataset.sid);
  });

  // Init: open the first store on load. In a live artifact the question
  // buttons send rather than copy — relabel them so the CTA is honest.
  document.addEventListener('DOMContentLoaded', function () {
    const first = document.querySelector('.store-tab');
    if (first && first.dataset && first.dataset.sid) {
      switchStore(first.dataset.sid);
    }
    if (typeof window.sendPrompt === 'function') {
      document.querySelectorAll('[data-action="ask-question"]').forEach(function (btn) {
        const label = btn.querySelector('.q-copy-label');
        if (label) label.textContent = 'Send';
        btn.setAttribute('aria-label', 'Send question to the conversation');
      });
    }
  });
})();
