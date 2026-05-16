// TrackBee Ad Performance — shared client-side formatters.
// Exposes window.TB with .fmt, .roasClass, .freqClass, and .actionBadge.
// All thresholds come from window.TB_DATA.thresholds (no client-side
// hard-coded numbers).
(function () {
  function _safeNum(v) {
    if (v === null || v === undefined || v === '') return null;
    var n = (typeof v === 'number') ? v : parseFloat(v);
    return (isNaN(n) || !isFinite(n)) ? null : n;
  }

  function _fixed(v, d) {
    var n = _safeNum(v); if (n === null) return '—';
    return n.toLocaleString('en-US', {
      minimumFractionDigits: d, maximumFractionDigits: d
    });
  }

  var fmt = {
    num: function (v) { var n = _safeNum(v); return n === null ? '—' : Math.round(n).toLocaleString('en-US'); },
    fix: function (v, d) { return _fixed(v, d == null ? 2 : d); },
    pct: function (v, d) { var n = _safeNum(v); if (n === null) return '—'; return (n).toFixed(d == null ? 2 : d) + '%'; },
    money: function (v, sym, d) {
      var n = _safeNum(v); if (n === null) return '—';
      var dec = d == null ? 0 : d;
      return (sym || '') + n.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    }
  };

  function roasClass(roas) {
    var t = (window.TB_DATA && window.TB_DATA.thresholds) || {};
    var n = _safeNum(roas); if (n === null) return '';
    if (n >= (t.roas_good || 2.5)) return 'good';
    if (n >= (t.roas_ok   || 1.5)) return 'ok';
    if (n > 0) return 'bad';
    return '';
  }

  function freqClass(freq) {
    var t = (window.TB_DATA && window.TB_DATA.thresholds) || {};
    var n = _safeNum(freq); if (n === null) return '';
    if (n >= (t.freq_bad || 4.0)) return 'bad';
    if (n >= (t.freq_ok  || 3.0)) return 'ok';
    return '';
  }

  // Returns inline HTML for the action pill. Mirrors the server-side
  // _action_badge logic in transforms/action_rules.py — but here for any
  // client-side rendering that needs it (none today, but reserved).
  function actionBadge(roas, freq, spend) {
    var t = (window.TB_DATA && window.TB_DATA.thresholds) || {};
    var r = _safeNum(roas) || 0, f = _safeNum(freq) || 0, s = _safeNum(spend) || 0;
    var minSpend = t.action_min_spend || 50;
    if (s < minSpend || r <= 0) return '<span class="act-pill act-none">—</span>';
    if (r >= (t.scale_roas || 1.8) && (f === 0 || f < (t.scale_max_freq || 2.5))) {
      return '<span class="act-pill act-scale">SCALE</span>';
    }
    if (f >= (t.refresh_min_freq || 3.5) && r >= (t.refresh_min_roas || 1.2)) {
      return '<span class="act-pill act-refresh">REFRESH</span>';
    }
    if (r < (t.pause_roas || 1.2) && s > (t.pause_min_spend || 100)) {
      return '<span class="act-pill act-pause">PAUSE</span>';
    }
    return '<span class="act-pill act-hold">HOLD</span>';
  }

  window.TB = { fmt: fmt, roasClass: roasClass, freqClass: freqClass, actionBadge: actionBadge };
})();
