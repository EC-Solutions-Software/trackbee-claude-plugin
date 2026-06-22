let SANKEY_KEY = 'multi';
const prettify = arr => arr.map(l => l.replace(/ @ step (\d+)/, ' (step $1)'));
const _CCY_CODE = (PAGE_DATA.store.currency || 'EUR').toUpperCase();
const fmt = {
  eur:  v => v == null ? '—' : new Intl.NumberFormat('en-US', {style:'currency',currency:_CCY_CODE,maximumFractionDigits:0}).format(v),
  eur2: v => v == null ? '—' : new Intl.NumberFormat('en-US', {style:'currency',currency:_CCY_CODE,minimumFractionDigits:2,maximumFractionDigits:2}).format(v),
  num:  v => v == null ? '—' : Number(v).toLocaleString('en-US'),
  pct:  v => v == null ? '—' : (v*100).toFixed(2)+'%',
  fix:  (v,d=2) => v == null ? '—' : Number(v).toFixed(d),
};
function delta(cur, prev) {
  if (!prev || prev === 0 || cur == null) return '';
  const p = (cur - prev) / prev;
  const cls = p >= 0 ? 'delta-up' : 'delta-dn';
  const arr = p >= 0 ? '▲' : '▼';
  return `<span class="${cls}">${arr} ${(Math.abs(p)*100).toFixed(1)}%</span>`;
}
function tile(label, value, sub) {
  return `<div class="kpi"><div class="kpi-label">${label}</div>
    <div class="kpi-value">${value}</div>
    <div class="kpi-sub">${sub||''}</div></div>`;
}

function renderBlended(b) {
  const tiles = [
    tile('Ad spend', fmt.eur(b.ad_spend), ''),
    tile('Revenue', fmt.eur(b.revenue), delta(b.revenue, b._revenue_prev)),
    tile('New customers', fmt.num(b.new_customers), 'first-ever orders'),
    tile('Orders', fmt.num(b.orders), delta(b.orders, b._orders_prev)),
    tile('AOV', fmt.eur2(b.aov), ''),
    tile('Blended ROAS', fmt.fix(b.roas, 2), 'Revenue ÷ Spend'),
    tile('Blended CPA', fmt.eur2(b.cpa), 'Spend ÷ Orders'),
    tile('Blended NC-CPA', fmt.eur2(b.nc_cpa), 'Spend ÷ NC orders'),
    tile('Blended NC-ROAS', fmt.fix(b.nc_roas, 2), 'NC Revenue ÷ Spend'),
    tile('Sessions', fmt.num(b.sessions), delta(b.sessions, b._pv_prev)),
    tile('Added-to-cart rate', fmt.pct(b.atc_rate), delta(b.atc_rate, b._atc_rate_prev)),
    tile('Started checkout rate', fmt.pct(b.co_rate), delta(b.co_rate, b._co_rate_prev)),
    tile('Conversion rate', fmt.pct(b.cvr), delta(b.cvr, b._cvr_prev)),
    tile('Revenue / session', fmt.eur2(b.rev_per_session), ''),
  ];
  document.getElementById('kpiBlended').innerHTML = tiles.join('');
}

function renderPlatforms(plats) {
  const html = Object.values(plats).map(p => `
    <div class="platform-block">
      <div class="platform-name">${PAGE_DATA.logos[p.logo]}${p.label}</div>
      <div class="kpis">
        ${tile('ROAS (in-platform)', fmt.fix(p.roas), '')}
        ${tile('Revenue (in-platform)', fmt.eur(p.revenue), '')}
        ${tile('Ad spend', fmt.eur(p.spend), '')}
        ${tile('CTR', (p.ctr).toFixed(2)+'%', '')}
        ${tile('CPC', fmt.eur2(p.cpc), '')}
        ${tile('CPM', fmt.eur2(p.cpm), '')}
        ${tile('Impressions', fmt.num(p.impressions), '')}
        ${tile('Clicks', fmt.num(p.clicks), '')}
        ${tile('Purchases', fmt.num(p.purchases), 'in-platform')}
      </div>
    </div>
  `).join('');
  document.getElementById('platformTiles').innerHTML = html;
}

function renderAttribution(channels) {
  const html = channels.map(r => {
    const isOverall = r.channel === 'Overall';
    const cls = isOverall ? ' class="overall"' : '';
    const chLogo = r.logo ? PAGE_DATA.logos[r.logo] : '';
    return `<tr${cls}>
      <td><span class="row-icon">${chLogo}${r.channel}</span></td>
      <td class="num">${fmt.num(r.sessions)}</td>
      <td class="num">${r.purch_in != null ? fmt.num(Math.round(r.purch_in)) : (r.purch_tb ? fmt.num(r.purch_tb) : '—')}</td>
      <td class="num">${r.rev_in != null ? fmt.eur(r.rev_in) : (r.rev_tb ? fmt.eur(r.rev_tb) : '—')}</td>
      <td class="num">${r.spend > 0 ? fmt.eur(r.spend) : '—'}</td>
      <td class="num">${r.cpa == null ? '—' : fmt.eur2(r.cpa)}</td>
      <td class="num">${r.roas == null ? '—' : fmt.fix(r.roas)}</td>
    </tr>`;
  }).join('');
  document.getElementById('attrBody').innerHTML = html;
}

function renderInsightList(elId, insights) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.className = 'insight-list';
  // Insights are factual observations only — no TrackBee-authored action line.
  el.innerHTML = (insights || []).map(i => {
    const obs = typeof i === 'string' ? i : i.obs;
    return `<li class="insight-item">
      <span class="insight-bullet"></span>
      <div>
        <div class="insight-obs">${obs}</div>
      </div>
    </li>`;
  }).join('');
}

function renderExecSummary(takeaways, label) {
  document.getElementById('execWindowTag').textContent = label;
  document.getElementById('execTakeaways').innerHTML =
    (takeaways || []).map(t => `<li>${t}</li>`).join('');
}

function renderNcRoasChart(daily) {
  // CDN-independent: swap inline-SVG visibility, recompute period avg.
  const wrap = document.getElementById('ncRoasInline');
  if (!wrap || !daily || !daily.length) return;
  const totalRev = daily.reduce((a, d) => a + (d.nc_revenue || 0), 0);
  const totalSpend = daily.reduce((a, d) => a + (d.daily_spend || 0), 0);
  const avg = totalSpend ? (totalRev / totalSpend) : 0;
  document.getElementById('ncRoasPeriodAvg').textContent = avg.toFixed(2);
  const activeBtn = document.querySelector('#windowFilter button.active');
  const key = activeBtn ? activeBtn.dataset.w : '28d';
  wrap.querySelectorAll('[data-w]').forEach(el => {
    el.style.display = (el.dataset.w === key) ? 'block' : 'none';
  });
}

function renderFunnel(w) {
  // Tag in section header.
  const tag = document.getElementById('funnelWindowTag');
  if (tag) tag.textContent = w.label;

  // Headline KPIs.
  const summary = w.funnel_summary || {};
  const topRate = summary.top_to_order_rate || 0;
  const topEl = document.getElementById('funnelTopToOrder');
  if (topEl) topEl.textContent = fmt.pct(topRate);

  const worstStepEl = document.getElementById('funnelWorstStep');
  const worstRateEl = document.getElementById('funnelWorstRate');
  if (summary.worst_to_label && summary.worst_rate != null) {
    worstStepEl.textContent = summary.worst_to_label;
    worstRateEl.textContent = `(${fmt.pct(summary.worst_rate)} conversion from the previous step)`;
  } else {
    worstStepEl.textContent = '—';
    worstRateEl.textContent = '';
  }

  // Stage rows.
  const stages = w.funnel_stages || [];
  const drops = w.funnel_drops || [];
  const dropByTo = {};
  drops.forEach(d => { dropByTo[d.to_step] = d; });
  const topCount = stages[0]?.count || 1;
  const worstStep = summary.worst_to_label || null;

  const rowsHtml = stages.map((s, i) => {
    const widthPct = topCount ? Math.max(0.5, (s.count / topCount) * 100) : 0;
    const drop = dropByTo[s.step];
    const isWorst = drop && summary.worst_to_label === s.label;
    let convHtml = '';
    if (i === 0) {
      convHtml = `<div class="funnel-conv"><span class="fc-meta">Top of funnel</span></div>`;
    } else if (drop) {
      const rate = drop.rate || 0;
      let cls = '';
      if (rate < 0.25) cls = 'warn';
      else if (rate >= 0.6) cls = 'good';
      convHtml = `<div class="funnel-conv">
        <span class="fc-rate ${cls}">${fmt.pct(rate)}</span>
        <span class="fc-meta">from ${drop.from_label} — ${fmt.num(drop.lost)} lost</span>
        <span class="fc-top">${fmt.pct(s.rate_from_top || 0)} of page views reach this step</span>
      </div>`;
    }
    const labelInside = widthPct >= 22;
    const labelHtml = labelInside
      ? `<span class="funnel-bar-label">${fmt.num(s.count)}</span>`
      : `<span class="funnel-bar-label outside">${fmt.num(s.count)}</span>`;
    const fillCls = s.count > 0 ? '' : 'empty';
    return `<div class="funnel-stage${isWorst ? ' worst' : ''}">
      <div class="fs-stage-label">
        <span>${s.label}</span>
        <span class="fs-stage-count">${fmt.num(s.count)} events</span>
      </div>
      <div class="funnel-bar-track">
        <div class="funnel-bar-fill ${fillCls}" style="width:${widthPct.toFixed(2)}%"></div>
        ${labelHtml}
      </div>
      ${convHtml}
    </div>`;
  }).join('');
  document.getElementById('funnelList').innerHTML = rowsHtml;

  // Insights list — uses the same renderer as the other observation/action cards.
  renderInsightList('funnelInsights', w.funnel_insights);
}

function renderQuestions() {
  const list = document.getElementById('questionsList');
  if (!list) return;
  const items = (PAGE_DATA.suggested_questions || []);
  if (!items.length) {
    list.innerHTML = '<div class="meta">No follow-up questions surfaced for this snapshot.</div>';
    return;
  }
  const live = typeof window.sendPrompt === 'function';
  list.innerHTML = items.map((q, idx) => `
    <button type="button" class="question-card" data-q-idx="${idx}">
      <span class="q-label">${q.label}</span>
      <span class="q-prompt">${q.prompt}</span>
      <span class="q-cta">${live ? 'Send →' : 'Copy →'}</span>
    </button>
  `).join('');
  if (!list.dataset.bound) {
    list.addEventListener('click', e => {
      const card = e.target.closest('button.question-card');
      if (!card) return;
      const idx = +card.dataset.qIdx;
      const q = (PAGE_DATA.suggested_questions || [])[idx];
      if (!q) return;
      if (typeof window.sendPrompt === 'function') {
        try { window.sendPrompt(q.prompt); } catch (err) { console.warn('sendPrompt failed', err); }
      } else if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(q.prompt).then(() => {
          card.classList.add('copied');
          const cta = card.querySelector('.q-cta');
          if (cta) cta.textContent = 'Copied ✓';
          setTimeout(() => {
            card.classList.remove('copied');
            if (cta) cta.textContent = 'Copy →';
          }, 1800);
        });
      }
    });
    list.dataset.bound = '1';
  }
}

function renderWindow(key) {
  const w = PAGE_DATA.windows[key];
  document.getElementById('caveatWindow').innerHTML =
    `<strong>${w.label}</strong> · ${w.start} → ${w.end} · ${PAGE_DATA.store.currency} store${Object.keys(PAGE_DATA.store.fx || {}).length ? ' · ad-account FX: ' + Object.entries(PAGE_DATA.store.fx).map(([k,v]) => k+'='+v).join(', ') : ''}.`;
  renderExecSummary(w.exec_takeaways, w.label);
  renderBlended(w.blended);
  renderPlatforms(w.platforms);
  renderAttribution(w.channels);
  renderInsightList('chInsights', w.ch_insights);
  renderNcRoasChart(w.daily_nc_roas);
  renderFunnel(w);
}

// Filter wiring
document.getElementById('windowFilter').addEventListener('click', e => {
  const btn = e.target.closest('button[data-w]');
  if (!btn) return;
  document.querySelectorAll('#windowFilter button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderWindow(btn.dataset.w);
});

// Initial render
renderWindow('28d');
renderQuestions();

function renderSankey() {
  // CDN-independent: swap inline-SVG visibility for the active filter.
  const wrap = document.getElementById('journeyFallback');
  if (!wrap) return;
  wrap.querySelectorAll('[data-sv]').forEach(el => {
    el.style.display = (el.dataset.sv === SANKEY_KEY) ? 'block' : 'none';
  });
}

const _sankeyFilterEl = document.getElementById('sankeyFilter');
if (_sankeyFilterEl) {
  _sankeyFilterEl.addEventListener('click', e => {
    const btn = e.target.closest('button[data-sf]');
    if (!btn) return;
    document.querySelectorAll('#sankeyFilter button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    SANKEY_KEY = btn.dataset.sf;
    renderSankey();
  });
}

// On full page load, render the chart + sankey. Chart and Plotly may both
// still be loading at the time the inline script runs; wait for them.
function renderAsyncCharts() {
  const activeBtn = document.querySelector('#windowFilter button.active');
  const key = activeBtn ? activeBtn.dataset.w : '28d';
  renderNcRoasChart(PAGE_DATA.windows[key].daily_nc_roas);
  renderSankey();
}
if (document.readyState === 'complete') renderAsyncCharts();
else window.addEventListener('load', renderAsyncCharts);
