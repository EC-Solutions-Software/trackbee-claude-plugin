// TrackBee Creatives report — shared client-side helpers.
//
// All cell values are pre-formatted server-side, so the only client-side
// need is numeric coercion for the table sort + filter glue
// (table_filters.js).
(function () {
  // Strip currency / pct / commas off a rendered cell so numeric sort
  // can coerce it. Mirrors the Python templates' format outputs.
  function stripNumeric(text) {
    if (text == null) return NaN;
    const m = String(text).replace(/[^0-9.\-]/g, '');
    return m === '' ? NaN : parseFloat(m);
  }
  window.TB = window.TB || {};
  window.TB.stripNumeric = stripNumeric;
})();
