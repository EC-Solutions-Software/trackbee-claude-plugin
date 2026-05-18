// NC ROAS daily line chart — Acquisition MER over time.
//
// Renders an inline SVG into #ncRoasInline and writes the period average
// into #ncRoasPeriodAvg. Hand-rolled SVG with area fill, dashed
// period-average line, 5-tick grid, dense x-labels, and invisible hit-target
// circles wired to the tooltip system via data-tip.
//
// Exposes window.TB.render.ncRoas(daily) so window_filter can re-render on
// 3d/7d/28d switches.

(function () {
  var TB = window.TB || (window.TB = {});
  var render = TB.render || (TB.render = {});

  function el(id) { return document.getElementById(id); }

  function ncRoas(daily) {
    var slot = el('ncRoasInline');
    var avgSlot = el('ncRoasPeriodAvg');
    if (!slot) return;

    daily = daily || [];
    var n = daily.length;
    if (!n) {
      slot.innerHTML = '<div style="padding:24px;color:var(--ink-muted);'
        + 'background:#FAFAFA;border:1px solid var(--line);border-radius:8px;'
        + 'font-size:13px;text-align:center">No data for this window.</div>';
      if (avgSlot) avgSlot.textContent = '—';
      return;
    }

    var W = 760, H = 220;
    var PT = 14, PB = 30, PL = 38, PR = 14;
    var plotW = W - PL - PR;
    var plotH = H - PT - PB;

    var vals = daily.map(function (d) { return +d.value || 0; });
    var totRev = 0, totSpend = 0;
    for (var i = 0; i < n; i++) {
      totRev   += +daily[i].nc_revenue  || 0;
      totSpend += +daily[i].daily_spend || 0;
    }
    var avg = totSpend ? totRev / totSpend : 0;
    if (avgSlot) avgSlot.textContent = avg.toFixed(2);

    var vmax = Math.max.apply(null, vals.concat([avg, 1]));
    var vmin = 0;
    function x(i) {
      return n > 1 ? PL + plotW * (i / (n - 1)) : PL + plotW / 2;
    }
    function y(v) {
      return vmax > vmin
        ? PT + plotH * (1 - (v - vmin) / (vmax - vmin))
        : PT + plotH / 2;
    }

    var ptsArr = [];
    for (var j = 0; j < n; j++) ptsArr.push(x(j).toFixed(1) + ',' + y(vals[j]).toFixed(1));
    var pts = ptsArr.join(' ');

    // Area fill under the line.
    var areaParts = ['M' + x(0).toFixed(1) + ',' + y(0).toFixed(1)];
    for (var a = 0; a < n; a++) areaParts.push('L' + x(a).toFixed(1) + ',' + y(vals[a]).toFixed(1));
    areaParts.push('L' + x(n - 1).toFixed(1) + ',' + y(0).toFixed(1) + ' Z');
    var areaD = areaParts.join(' ');

    // 5 horizontal grid ticks + axis labels.
    var ticks = '';
    for (var k = 0; k < 5; k++) {
      var gv = vmin + (vmax - vmin) * k / 4;
      var gy = y(gv);
      ticks += '<line x1="' + PL + '" y1="' + gy.toFixed(1)
        + '" x2="' + (W - PR) + '" y2="' + gy.toFixed(1)
        + '" stroke="rgba(204,209,223,0.6)" stroke-width="1"/>';
      ticks += '<text x="' + (PL - 6) + '" y="' + (gy + 3).toFixed(1)
        + '" font-size="10" fill="#696E7C" text-anchor="end" '
        + 'font-family="Inter, system-ui">' + gv.toFixed(1) + '</text>';
    }

    // X-axis labels thinned for readability (every Nth + last).
    var step = Math.max(1, Math.floor(n / 7));
    var xLabels = '';
    for (var i2 = 0; i2 < n; i2++) {
      if (i2 % step === 0 || i2 === n - 1) {
        var d = daily[i2].date || '';
        var mmdd = d.length >= 10 ? d.slice(5) : d;
        xLabels += '<text x="' + x(i2).toFixed(1) + '" y="' + (H - PB + 16)
          + '" font-size="10" fill="#696E7C" text-anchor="middle" '
          + 'font-family="Inter, system-ui">' + mmdd + '</text>';
      }
    }

    // Visible dots + invisible hit-target circles with multi-line data-tip.
    var dotR = n <= 7 ? 2.5 : 1.8;
    var dots = '';
    for (var p = 0; p < n; p++) {
      var dd = daily[p];
      var tip = '<strong>' + (dd.date || '') + '</strong>'
        + 'NC ROAS: <b>' + vals[p].toFixed(2) + '</b>\n'
        + 'NC revenue: ' + Number(dd.nc_revenue || 0).toLocaleString('en-US') + '\n'
        + 'Daily spend: ' + Number(dd.daily_spend || 0).toLocaleString('en-US');
      dots += '<circle cx="' + x(p).toFixed(1) + '" cy="' + y(vals[p]).toFixed(1)
        + '" r="' + dotR + '" fill="#0072FF"></circle>';
      dots += '<circle class="tb-hit" cx="' + x(p).toFixed(1) + '" cy="' + y(vals[p]).toFixed(1)
        + '" r="10" pointer-events="all" data-tip="' + tip.replace(/"/g, '&quot;') + '"></circle>';
    }

    var avgY = y(avg);
    slot.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="240" '
      + 'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="NC ROAS over time">'
      + ticks
      + '<path d="' + areaD + '" fill="rgba(0,114,255,0.10)" stroke="none"/>'
      + '<polyline points="' + pts + '" fill="none" stroke="#0072FF" stroke-width="2"/>'
      + dots
      + '<line x1="' + PL + '" y1="' + avgY.toFixed(1) + '" x2="' + (W - PR) + '" y2="' + avgY.toFixed(1)
      + '" stroke="rgba(231,152,16,0.7)" stroke-width="1.5" stroke-dasharray="4 4"/>'
      + '<text x="' + (W - PR - 4) + '" y="' + (avgY - 4).toFixed(1) + '" font-size="10" '
      + 'fill="rgba(231,152,16,1)" text-anchor="end" font-family="Inter, system-ui">'
      + 'avg ' + avg.toFixed(2) + '</text>'
      + xLabels
      + '</svg>';
  }

  render.ncRoas = ncRoas;
})();
