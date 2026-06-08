// Metric framework filter glue: all / positive / negative.
// Delegated click listener on the filter bar toggles row visibility by the
// row's data-signal. No inline handlers; data comes from the DOM.
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
      const signal = tr.getAttribute('data-signal') || 'neutral';
      let show = true;
      if (f === 'positive') show = signal === 'positive';
      else if (f === 'negative') show = signal === 'negative';
      tr.style.display = show ? '' : 'none';
    });
  });
})();
