// Hover tooltip — wires [data-tip] elements to the #tbTooltip popover.
//
// Any element with a `data-tip="..."` attribute (or any descendant of one)
// shows the tooltip at the cursor on mouseover. Used by the NC ROAS hit-target
// circles and the sankey rects/paths.

(function () {
  var tip = document.getElementById('tbTooltip');
  if (!tip) return;

  function show(html, mx, my) {
    tip.innerHTML = html;
    tip.classList.add('visible');
    tip.setAttribute('aria-hidden', 'false');
    var r = tip.getBoundingClientRect();
    var pad = 14;
    var nx = mx + pad, ny = my + pad;
    if (nx + r.width  > window.innerWidth  - 8) nx = mx - r.width  - pad;
    if (ny + r.height > window.innerHeight - 8) ny = my - r.height - pad;
    tip.style.left = nx + 'px';
    tip.style.top  = ny + 'px';
  }
  function hide() {
    tip.classList.remove('visible');
    tip.setAttribute('aria-hidden', 'true');
  }

  document.addEventListener('mouseover', function (e) {
    var t = e.target.closest && e.target.closest('[data-tip]');
    if (!t) return;
    show(t.getAttribute('data-tip'), e.clientX, e.clientY);
  });
  document.addEventListener('mousemove', function (e) {
    if (!tip.classList.contains('visible')) return;
    var t = e.target.closest && e.target.closest('[data-tip]');
    if (!t) { hide(); return; }
    show(t.getAttribute('data-tip'), e.clientX, e.clientY);
  });
  document.addEventListener('mouseout', function (e) {
    var from = e.target.closest && e.target.closest('[data-tip]');
    var to   = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('[data-tip]');
    if (from && from !== to) hide();
  });
})();
