// Metric framework filter glue: all / up / down.
// Delegated click listener on the filter bar toggles row visibility by the
// row's data-signal (direction of the week-over-week change — never a
// good/bad judgement). No inline handlers; data comes from the DOM.
(function () {
  const filter = document.getElementById('metricFilter');
  if (!filter) return;
  filter.addEventListener('click', function (ev) {
    const btn = ev.target.closest('button[data-f]');
    if (!btn) return;
    Array.from(filter.querySelectorAll('button')).forEach(function (b) {
      b.classList.toggle('active', b === btn);
    });
    const f = btn.getAttribute('data-f');
    const rows = document.querySelectorAll('#metricsBody tr');
    rows.forEach(function (tr) {
      const signal = tr.getAttribute('data-signal') || 'flat';
      let show = true;
      if (f === 'up') show = signal === 'up';
      else if (f === 'down') show = signal === 'down';
      tr.style.display = show ? '' : 'none';
    });
  });
})();
