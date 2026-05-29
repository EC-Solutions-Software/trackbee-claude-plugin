// Store switching, platform tabs, search, zero-spend toggle, and ad-row
// expand/collapse. Everything is delegated off `data-action` attributes
// on the buttons / inputs the orchestrator emits — no inline onclick.

(function () {
  var currentStore = null;
  var currentPlatforms = {};   // sid -> "all" | "meta" | "google"
  var searchTerms = {};        // sid -> string

  function switchStore(sid) {
    document.querySelectorAll('.store-section').forEach(function (s) { s.style.display = 'none'; });
    document.querySelectorAll('.store-tab').forEach(function (b) { b.classList.remove('active'); });
    var sec = document.getElementById('store-' + sid);
    if (sec) sec.style.display = 'block';
    var tab = document.querySelector('.store-tab[data-sid="' + sid + '"]');
    if (tab) tab.classList.add('active');
    currentStore = sid;
    applyFilters(sid);
  }

  function filterPlatform(btn, plat, sid) {
    document.querySelectorAll('#store-' + sid + ' .plat-tab').forEach(function (b) { b.classList.remove('active'); });
    btn.classList.add('active');
    currentPlatforms[sid] = plat;
    applyFilters(sid);
  }

  function toggleZero(sid) { applyFilters(sid); }

  function filterSearch(sid) {
    var inp = document.getElementById('search-' + sid);
    searchTerms[sid] = (inp && inp.value || '').toLowerCase();
    applyFilters(sid);
  }

  function applyFilters(sid) {
    var plat = currentPlatforms[sid] || 'all';
    var hideZeroEl = document.getElementById('hide-zero-' + sid);
    var hideZero = hideZeroEl && hideZeroEl.checked;
    var term = (searchTerms[sid] || '').toLowerCase();
    var rows = document.querySelectorAll('#tbody-' + sid + ' tr.camp-row');

    rows.forEach(function (row) {
      var rPlat = row.dataset.platform || '';
      var nameEl = row.querySelector('.camp-name');
      var rName = (nameEl && nameEl.textContent) || '';

      // The first .num cell holds the spend value as a formatted string.
      // Strip every non-digit and non-dot to read the number; minus sign
      // is intentionally NOT stripped so refunds/credits stay negative.
      var numCells = row.querySelectorAll('td.num');
      var spendTxt = numCells.length > 0
        ? numCells[0].textContent.replace(/[^0-9.\-]/g, '')
        : '';
      var spendVal = parseFloat(spendTxt) || 0;

      var platOk = (plat === 'all' || rPlat === plat);
      var searchOk = (!term || rName.toLowerCase().includes(term));
      var zeroOk = (!hideZero || spendVal > 0);

      var show = platOk && searchOk && zeroOk;
      row.classList.toggle('hidden', !show);

      // Hide ad rows belonging to a hidden campaign. When the campaign is
      // visible again, the toggleAds button decides whether ad rows show.
      var cid = row.dataset.campaign;
      if (cid) {
        document.querySelectorAll(
          '#tbody-' + sid + ' tr.ad-row[data-campaign="' + cid + '"]'
        ).forEach(function (ar) {
          if (!show) ar.classList.add('hidden');
        });
      }
    });
  }

  function toggleAds(btn) {
    var cid = btn.dataset.campaign;
    var sid = btn.dataset.store;
    var plat = btn.dataset.platform;
    var adRows = document.querySelectorAll(
      '#tbody-' + sid + ' tr.ad-row[data-campaign="' + cid + '"][data-platform="' + plat + '"]'
    );
    var isOpen = btn.classList.contains('open');
    btn.classList.toggle('open', !isOpen);
    btn.textContent = isOpen ? '▶' : '▼';  // ▶ / ▼
    adRows.forEach(function (r) { r.classList.toggle('hidden', isOpen); });
  }

  // ── Delegated event wiring (no inline onclick) ────────────────────
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-action]');
    if (!t) return;
    var action = t.dataset.action;
    var sid = t.dataset.store;
    if (action === 'switch-store') {
      switchStore(t.dataset.sid);
    } else if (action === 'filter-platform') {
      filterPlatform(t, t.dataset.plat, sid);
    } else if (action === 'toggle-ads') {
      toggleAds(t);
    }
  });

  document.addEventListener('change', function (e) {
    var t = e.target.closest('[data-action="toggle-zero"]');
    if (t) toggleZero(t.dataset.store);
  });

  document.addEventListener('input', function (e) {
    var t = e.target.closest('[data-action="search"]');
    if (t) filterSearch(t.dataset.store);
  });

  // ── Init ──────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var firstSid = document.body.dataset.firstStore;
    if (firstSid && firstSid !== 'null') switchStore(firstSid);
  });
})();
