// Window filter — wires the 3d / 7d / 28d buttons + triggers a re-render
// of every window-scoped section. Journeys are 90d-only and rendered once
// at load (here as well, since this script runs after the DOM is parsed).

(function () {
  var DATA = window.TB_DATA || {};
  var WINDOWS = DATA.windows || {};
  var R = (window.TB && window.TB.render) || {};

  function renderWindow(key) {
    var w = WINDOWS[key] || {};
    R.exec        && R.exec(w.exec_takeaways, w.label);
    R.blended     && R.blended(w.blended);
    R.ncRoas      && R.ncRoas(w.daily_nc_roas);
    R.platforms   && R.platforms(w.platforms);
    R.attribution && R.attribution(w.channels);
    R.insightList && R.insightList('chInsights', w.ch_insights);
    R.caveatLine  && R.caveatLine(w);
  }

  var filter = document.getElementById('windowFilter');
  if (filter) {
    filter.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('button[data-w]');
      if (!btn) return;
      var buttons = filter.querySelectorAll('button');
      for (var i = 0; i < buttons.length; i++) buttons[i].classList.remove('active');
      btn.classList.add('active');
      renderWindow(btn.getAttribute('data-w'));
    });
  }

  // Initial render — pick whichever button is marked active, default 28d.
  var activeBtn = filter && filter.querySelector('button.active');
  renderWindow(activeBtn ? activeBtn.getAttribute('data-w') : '28d');

  // Journeys (90d, not window-scoped) — render once.
  if (R.journeys) R.journeys(DATA.journeys);

  // Expose for testing / external triggering.
  (window.TB = window.TB || {}).renderWindow = renderWindow;
})();
