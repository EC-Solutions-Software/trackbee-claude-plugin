// Sankey filter — switches between pre-rendered sankey SVG views.
//
// Reads the active button's data-sf and toggles which data-sv block under
// #journeyFallback is visible. SVGs are pre-rendered server-side, so this
// is a pure visibility swap.

(function () {
  var filter = document.getElementById('sankeyFilter');
  var wrap = document.getElementById('journeyFallback');
  if (!filter || !wrap) return;

  filter.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('button[data-sf]');
    if (!btn) return;
    var buttons = filter.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) buttons[i].classList.remove('active');
    btn.classList.add('active');
    var key = btn.getAttribute('data-sf');
    var slots = wrap.querySelectorAll('[data-sv]');
    for (var s = 0; s < slots.length; s++) {
      slots[s].style.display = (slots[s].getAttribute('data-sv') === key) ? 'block' : 'none';
    }
  });
})();
