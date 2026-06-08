// Daily Store Pulse — store filter glue.
//
// The portfolio renders every store the user has access to as one .pulse-card
// with a data-store="<id>" attribute. The filter bar holds an "All stores"
// chip (data-store="all") plus one chip per store. Clicking chips shows/hides
// cards client-side — no re-fetch. The choice persists to localStorage so
// reopening the artifact remembers it.
//
// Selection model:
//   - "All stores" selects everything and clears any subset.
//   - Clicking a store chip while "All" is active narrows to just that store.
//   - Clicking more store chips toggles them into / out of the subset.
//   - Emptying the subset (or selecting every store) falls back to "All".
//
// No inline onclick — a single delegated listener reads data-store from the DOM.
(function () {
  var bar = document.getElementById('storeFilter');
  if (!bar) return;

  // Stable per-artifact key so different stores' pulses don't clobber each other.
  var KEY = 'tb-pulse-filter:' + (bar.getAttribute('data-artifact') || 'default');

  var allIds = Array.prototype.map.call(
    bar.querySelectorAll('.store-chip[data-store]:not([data-store="all"])'),
    function (b) { return b.getAttribute('data-store'); }
  );

  function load() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return null;
      // Drop ids that no longer exist (store list changed since last visit).
      var kept = parsed.filter(function (id) { return allIds.indexOf(id) !== -1; });
      return kept.length ? kept : null;
    } catch (e) { return null; }
  }

  function save(selected) {
    try {
      if (!selected || selected.length === 0 || selected.length === allIds.length) {
        window.localStorage.removeItem(KEY); // "all" is the implicit default
      } else {
        window.localStorage.setItem(KEY, JSON.stringify(selected));
      }
    } catch (e) { /* storage unavailable — filtering still works in-session */ }
  }

  // null / full set means "all".
  var selected = load();

  function isAll() {
    return !selected || selected.length === 0 || selected.length === allIds.length;
  }

  function apply() {
    var showAll = isAll();
    // Cards
    Array.prototype.forEach.call(document.querySelectorAll('.pulse-card[data-store]'), function (card) {
      var id = card.getAttribute('data-store');
      var show = showAll || selected.indexOf(id) !== -1;
      card.classList.toggle('is-hidden', !show);
    });
    // Chip active states
    Array.prototype.forEach.call(bar.querySelectorAll('.store-chip[data-store]'), function (chip) {
      var id = chip.getAttribute('data-store');
      var active = id === 'all' ? showAll : (!showAll && selected.indexOf(id) !== -1);
      chip.classList.toggle('active', active);
      chip.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  bar.addEventListener('click', function (ev) {
    var chip = ev.target.closest('.store-chip[data-store]');
    if (!chip) return;
    var id = chip.getAttribute('data-store');

    if (id === 'all') {
      selected = null;
    } else if (isAll()) {
      // Narrowing from "all" to a single store.
      selected = [id];
    } else {
      var i = selected.indexOf(id);
      if (i === -1) selected.push(id);
      else selected.splice(i, 1);
      if (selected.length === 0) selected = null; // back to all
    }
    save(selected);
    apply();
  });

  apply();
})();
