// Per-section renderers — stateless functions exposed on window.TB.render.*.
//
// Each section's renderer takes the window payload and stamps DOM. The
// window_filter module orchestrates them; this file owns no state.

(function () {
  var TB = window.TB || (window.TB = {});
  var fmt = TB.fmt || {};
  var delta = TB.delta || function () { return ''; };
  var LOGOS = (window.TB_DATA && window.TB_DATA.logos) || {};

  function el(id) { return document.getElementById(id); }
  function setHTML(id, html) { var n = el(id); if (n) n.innerHTML = html; }

  function tile(label, value, sub) {
    return '<div class="kpi"><div class="kpi-label">' + label + '</div>'
      + '<div class="kpi-value">' + value + '</div>'
      + '<div class="kpi-sub">' + (sub || '') + '</div></div>';
  }

  function exec(takeaways, label) {
    var tag = el('execWindowTag');
    if (tag) tag.textContent = label || '';
    setHTML('execTakeaways', (takeaways || []).map(function (t) {
      return '<li>' + t + '</li>';
    }).join(''));
  }

  function blended(b) {
    b = b || {};
    var tiles = [
      tile('Ad spend',              fmt.eur(b.ad_spend),         ''),
      tile('Revenue',               fmt.eur(b.revenue),          delta(b.revenue, b._revenue_prev)),
      tile('New customers',         fmt.num(b.new_customers),    'first-ever orders'),
      tile('Orders',                fmt.num(b.orders),           delta(b.orders, b._orders_prev)),
      tile('AOV',                   fmt.eur2(b.aov),             ''),
      tile('Blended ROAS',          fmt.fix(b.roas, 2),          'Revenue ÷ Spend'),
      tile('Blended CPA',           fmt.eur2(b.cpa),             'Spend ÷ Orders'),
      tile('Blended NC-CPA',        fmt.eur2(b.nc_cpa),          'Spend ÷ NC orders'),
      tile('Blended NC-ROAS',       fmt.fix(b.nc_roas, 2),       'NC Revenue ÷ Spend'),
      tile('Sessions',              fmt.num(b.sessions),         delta(b.sessions, b._pv_prev)),
      tile('Added-to-cart rate',    fmt.pct(b.atc_rate),         delta(b.atc_rate, b._atc_rate_prev)),
      tile('Started checkout rate', fmt.pct(b.co_rate),          delta(b.co_rate, b._co_rate_prev)),
      tile('Conversion rate',       fmt.pct(b.cvr),              delta(b.cvr, b._cvr_prev)),
      tile('Revenue / session',     fmt.eur2(b.rev_per_session), ''),
    ];
    setHTML('kpiBlended', tiles.join(''));
  }

  function platforms(plats) {
    plats = plats || {};
    var keys = Object.keys(plats);
    if (!keys.length) {
      setHTML('platformTiles',
        '<div class="meta" style="padding:12px 0">No platform data available.</div>');
      return;
    }
    var html = keys.map(function (k) {
      var p = plats[k] || {};
      var logo = LOGOS[p.logo] || '';
      return '<div class="platform-block">'
        + '<div class="platform-name">' + logo + (p.label || k) + '</div>'
        + '<div class="kpis">'
        +   tile('ROAS (in-platform)',    fmt.fix(p.roas, 2),      '')
        +   tile('Revenue (in-platform)', fmt.eur(p.revenue),      '')
        +   tile('Ad spend',              fmt.eur(p.spend),        '')
        +   tile('CTR',                   (Number(p.ctr || 0) * 100).toFixed(2) + '%', '')
        +   tile('CPC',                   fmt.eur2(p.cpc),         '')
        +   tile('CPM',                   fmt.eur2(p.cpm),         '')
        +   tile('Impressions',           fmt.num(p.impressions),  '')
        +   tile('Clicks',                fmt.num(p.clicks),       '')
        +   tile('Purchases',             fmt.num(p.purchases),    'in-platform')
        + '</div>'
        + '</div>';
    }).join('');
    setHTML('platformTiles', html);
  }

  function attribution(channels) {
    channels = channels || [];
    var html = channels.map(function (r) {
      var isOverall = r.channel === 'Overall';
      var cls = isOverall ? ' class="overall"' : '';
      var logo = r.logo ? (LOGOS[r.logo] || '') : '';
      return '<tr' + cls + '>'
        + '<td><span class="row-icon">' + logo + (r.channel || '') + '</span></td>'
        + '<td class="num">' + fmt.num(r.sessions) + '</td>'
        + '<td class="num">' + fmt.num(r.purch_tb) + '</td>'
        + '<td class="num">' + (r.purch_in == null ? '—' : fmt.num(Math.round(r.purch_in))) + '</td>'
        + '<td class="num">' + fmt.eur(r.rev_tb) + '</td>'
        + '<td class="num">' + (r.rev_in == null ? '—' : fmt.eur(r.rev_in)) + '</td>'
        + '<td class="num">' + (r.spend > 0 ? fmt.eur(r.spend) : '—') + '</td>'
        + '<td class="num">' + (r.cpa  == null ? '—' : fmt.eur2(r.cpa))  + '</td>'
        + '<td class="num">' + (r.roas == null ? '—' : fmt.fix(r.roas, 2)) + '</td>'
        + '</tr>';
    }).join('');
    setHTML('attrBody', html);
  }

  function insightList(id, insights) {
    var ul = el(id);
    if (!ul) return;
    ul.className = 'insight-list';
    ul.innerHTML = (insights || []).map(function (i) {
      var obs = typeof i === 'string' ? i : i.obs;
      var act = typeof i === 'string' ? ''  : i.act;
      return '<li class="insight-item">'
        + '<span class="insight-bullet"></span>'
        + '<div><div class="insight-obs">' + (obs || '') + '</div>'
        + (act ? '<div class="insight-act">' + act + '</div>' : '')
        + '</div></li>';
    }).join('');
  }

  function caveatLine(win) {
    var node = el('caveatWindow');
    if (!node) return;
    var ccy = (window.TB_DATA && window.TB_DATA.store && window.TB_DATA.store.currency) || 'EUR';
    var fx = (window.TB_DATA && window.TB_DATA.store && window.TB_DATA.store.fx) || {};
    var fxKeys = Object.keys(fx);
    var fxStr = fxKeys.length
      ? ' · ad-account FX: ' + fxKeys.map(function (k) { return k + '=' + fx[k]; }).join(', ')
      : '';
    node.innerHTML = '<strong>' + (win.label || '') + '</strong> · '
      + (win.start || '') + ' → ' + (win.end || '') + ' · '
      + ccy + ' store' + fxStr + '.';
  }

  // Journeys — rendered once at load. Envelope shares come from the
  // channel-interactions payload (no absolute order counts here).
  function journeys(journeysData) {
    journeysData = journeysData || {};
    var k = journeysData.kpis || {};
    var jGrid = el('journeyKpis');
    if (jGrid) {
      var single  = k.single_touch_share || 0;
      var multi   = k.multi_touch_share || 0;
      var organic = k.organic_share || 0;
      jGrid.innerHTML = ''
        + tile('Single-touch share', fmt.pct(single),
               'Orders with one tracked ad touch')
        + tile('Multi-touch share',  fmt.pct(multi),
               'Orders with two or more tracked ad touches')
        + tile('Organic / untracked', fmt.pct(organic),
               'Orders with no tracked ad touch');
    }
    insightList('journeyInsights', journeysData.journey_insights);
    insightList('cooccurInsights', journeysData.cooccur_insights);
  }

  TB.render = {
    exec: exec,
    blended: blended,
    platforms: platforms,
    attribution: attribution,
    insightList: insightList,
    caveatLine: caveatLine,
    journeys: journeys,
  };
})();
