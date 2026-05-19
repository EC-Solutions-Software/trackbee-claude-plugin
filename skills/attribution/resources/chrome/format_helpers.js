// Exposes window.TB with:
//   fmt.eur(v)    -> currency, 0 decimals
//   fmt.eur2(v)   -> currency, 2 decimals
//   fmt.num(v)    -> integer with thousands separators
//   fmt.pct(v)    -> percentage, 2 decimals
//   fmt.fix(v, d) -> fixed decimals
//   TB.delta(cur, prev) -> coloured ▲/▼ HTML span
(function () {
  const _CCY = (window.TB_DATA && window.TB_DATA.store && window.TB_DATA.store.currency || 'EUR').toUpperCase();
  const fmt = {
    eur:  v => v == null ? '—' :
            new Intl.NumberFormat('en-US', {style:'currency',currency:_CCY,maximumFractionDigits:0}).format(v),
    eur2: v => v == null ? '—' :
            new Intl.NumberFormat('en-US', {style:'currency',currency:_CCY,minimumFractionDigits:2,maximumFractionDigits:2}).format(v),
    num:  v => v == null ? '—' : Number(v).toLocaleString('en-US'),
    pct:  v => v == null ? '—' : (v*100).toFixed(2) + '%',
    fix:  (v, d=2) => v == null ? '—' : Number(v).toFixed(d),
  };
  function delta(cur, prev) {
    if (!prev || prev === 0 || cur == null) return '';
    const p = (cur - prev) / prev;
    const cls = p >= 0 ? 'delta-up' : 'delta-dn';
    const arr = p >= 0 ? '▲' : '▼';
    return '<span class="' + cls + '">' + arr + ' ' + (Math.abs(p)*100).toFixed(1) + '%</span>';
  }
  window.TB = { fmt, delta };
})();
