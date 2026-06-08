// Daily-revenue sparkline hover glue. Each .spark-wrap carries its points as
// JSON in data-points ({l: date label, v: formatted revenue, x: percent of
// width, y: px from top}). Moving the pointer over the chart snaps a marker +
// guide line to the nearest day and shows a tooltip with that day's revenue.
// One delegated set of listeners per wrapper; no inline handlers.
(function () {
  var wraps = document.querySelectorAll('.spark-wrap[data-points]');
  Array.prototype.forEach.call(wraps, function (wrap) {
    var pts;
    try { pts = JSON.parse(wrap.getAttribute('data-points')); }
    catch (e) { return; }
    if (!pts || !pts.length) return;

    var vline = wrap.querySelector('.spark-vline');
    var dot = wrap.querySelector('.spark-dot');
    var tip = wrap.querySelector('.spark-tip');
    if (!vline || !dot || !tip) return;

    function show(p) {
      vline.style.left = p.x + '%';
      vline.hidden = false;
      dot.style.left = p.x + '%';
      dot.style.top = p.y + 'px';
      dot.hidden = false;
      tip.innerHTML = '<span class="spark-tip-d">' + p.l + '</span>' +
                      '<span class="spark-tip-v">' + p.v + '</span>';
      tip.hidden = false;
      // Position the tip above the dot, clamped within the chart width.
      tip.style.left = p.x + '%';
      tip.style.top = Math.max(p.y - 8, 0) + 'px';
      tip.style.transform =
        'translate(' + (p.x > 80 ? '-100%' : p.x < 20 ? '0' : '-50%') + ', -100%)';
    }

    function hide() {
      vline.hidden = true;
      dot.hidden = true;
      tip.hidden = true;
    }

    function nearest(clientX) {
      var rect = wrap.getBoundingClientRect();
      if (!rect.width) return null;
      var fx = ((clientX - rect.left) / rect.width) * 100;
      var best = pts[0], bestD = Infinity;
      for (var i = 0; i < pts.length; i++) {
        var d = Math.abs(pts[i].x - fx);
        if (d < bestD) { bestD = d; best = pts[i]; }
      }
      return best;
    }

    wrap.addEventListener('mousemove', function (e) {
      var p = nearest(e.clientX);
      if (p) show(p);
    });
    wrap.addEventListener('mouseleave', hide);
    // Touch: tap-and-drag scrubbing.
    wrap.addEventListener('touchstart', function (e) {
      var p = nearest(e.touches[0].clientX); if (p) show(p);
    }, { passive: true });
    wrap.addEventListener('touchmove', function (e) {
      var p = nearest(e.touches[0].clientX); if (p) show(p);
    }, { passive: true });
    wrap.addEventListener('touchend', hide);
  });
})();
