// TrackBee Ad Performance — interactivity layer.
// Wires store-switching, platform/zero-spend/search filters, row sorting,
// ad-row expansion, and copy-to-clipboard for the "Questions to ask next"
// cards. This is the only place the dashboard touches the DOM after load.

(function () {
  var currentStore = null;
  var currentPlatforms = {};
  var searchTerms = {};

  function _firstStoreId() {
    var nav = document.getElementById('storeNav');
    if (!nav) return null;
    var btn = nav.querySelector('.store-tab[data-sid]');
    return btn ? btn.dataset.sid : null;
  }

  window.switchStore = function (sid) {
    document.querySelectorAll('.store-section').forEach(function (s) { s.style.display = 'none'; });
    document.querySelectorAll('.store-tab').forEach(function (b) { b.classList.remove('active'); });
    var section = document.getElementById('store-' + sid);
    var tab = document.querySelector('.store-tab[data-sid="' + sid + '"]');
    if (section) section.style.display = 'block';
    if (tab) tab.classList.add('active');
    currentStore = sid;
    applyFilters(sid);
  };

  window.filterPlatform = function (btn, plat, sid) {
    document.querySelectorAll('#store-' + sid + ' .plat-tab').forEach(function (b) { b.classList.remove('active'); });
    btn.classList.add('active');
    currentPlatforms[sid] = plat;
    applyFilters(sid);
  };

  window.toggleZero = function (sid) { applyFilters(sid); };

  window.filterSearch = function (sid) {
    var box = document.getElementById('search-' + sid);
    searchTerms[sid] = (box && box.value || '').toLowerCase();
    applyFilters(sid);
  };

  function applyFilters(sid) {
    var plat = currentPlatforms[sid] || 'all';
    var hideZeroChk = document.getElementById('hide-zero-' + sid);
    var hideZero = hideZeroChk && hideZeroChk.checked;
    var term = (searchTerms[sid] || '').toLowerCase();
    var rows = document.querySelectorAll('#tbody-' + sid + ' tr.camp-row');

    rows.forEach(function (row) {
      var rPlat = row.dataset.platform || '';
      var rName = (row.querySelector('.camp-name') || {}).textContent || '';
      var numCells = row.querySelectorAll('td.num');
      var spendTxt = numCells.length ? numCells[0].textContent.replace(/[^0-9.-]/g, '') : '';
      var spendVal = parseFloat(spendTxt) || 0;

      var platOk = (plat === 'all' || rPlat === plat);
      var searchOk = (!term || rName.toLowerCase().indexOf(term) > -1);
      var zeroOk = (!hideZero || spendVal > 0);

      var show = platOk && searchOk && zeroOk;
      row.classList.toggle('hidden', !show);

      var cid = row.dataset.campaign;
      if (cid) {
        document.querySelectorAll('#tbody-' + sid + ' tr.ad-row[data-campaign="' + cid + '"]').forEach(function (ar) {
          if (!show) ar.classList.add('hidden');
        });
      }
    });
  }

  window.toggleAds = function (btn) {
    var cid = btn.dataset.campaign, sid = btn.dataset.store, plat = btn.dataset.platform;
    var adRows = document.querySelectorAll(
      '#tbody-' + sid + ' tr.ad-row[data-campaign="' + cid + '"][data-platform="' + plat + '"]'
    );
    var isOpen = btn.classList.contains('open');
    btn.classList.toggle('open', !isOpen);
    btn.textContent = isOpen ? '▶' : '▼';
    adRows.forEach(function (r) { r.classList.toggle('hidden', isOpen); });
  };

  // Sortable headers.
  document.querySelectorAll('.perf-table thead th[data-sort]').forEach(function (th) {
    th.addEventListener('click', function () {
      var table = th.closest('table');
      var tbody = table.querySelector('tbody');
      var col = Array.prototype.indexOf.call(th.parentElement.children, th);
      var asc = th.dataset.asc !== 'true';
      th.dataset.asc = asc;

      th.parentElement.querySelectorAll('th').forEach(function (other) {
        if (other !== th) { other.classList.remove('sort-asc', 'sort-desc'); delete other.dataset.asc; }
      });
      th.classList.toggle('sort-asc', asc);
      th.classList.toggle('sort-desc', !asc);

      var campRows = Array.prototype.slice.call(tbody.querySelectorAll('tr.camp-row'));
      campRows.sort(function (a, b) {
        var av = a.querySelectorAll('td')[col], bv = b.querySelectorAll('td')[col];
        if (!av || !bv) return 0;
        var an = parseFloat(av.textContent.replace(/[^0-9.-]/g, ''));
        var bn = parseFloat(bv.textContent.replace(/[^0-9.-]/g, ''));
        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
        return asc ? av.textContent.localeCompare(bv.textContent)
                   : bv.textContent.localeCompare(av.textContent);
      });
      campRows.forEach(function (cr) {
        tbody.appendChild(cr);
        var cid = cr.dataset.campaign, plat = cr.dataset.platform;
        if (cid) {
          tbody.querySelectorAll('tr.ad-row[data-campaign="' + cid + '"][data-platform="' + plat + '"]')
            .forEach(function (ar) { tbody.appendChild(ar); });
        }
      });
    });
  });

  window.copyQuestion = function (btn) {
    var text = btn.dataset.q || '';
    var label = btn.querySelector('.q-copy-label');
    var done = function () {
      btn.classList.add('copied');
      if (label) label.textContent = 'Copied';
      setTimeout(function () { btn.classList.remove('copied'); if (label) label.textContent = 'Copy'; }, 1600);
    };
    var fallback = function () {
      var ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
      document.body.appendChild(ta); ta.focus(); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(); done(); });
    } else { fallback(); done(); }
  };

  // Boot.
  var first = _firstStoreId();
  if (first) switchStore(first);
})();
