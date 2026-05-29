// Copy-to-clipboard on the question cards. Buttons emit `data-q` with the
// plain-text version of the question; the click handler is delegated.

(function () {
  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try { document.execCommand('copy'); } catch (e) { /* swallow */ }
    document.body.removeChild(ta);
  }

  function copyQuestion(btn) {
    var text = btn.dataset.q || '';
    var label = btn.querySelector('.q-copy-label');
    var done = function () {
      btn.classList.add('copied');
      if (label) label.textContent = 'Copied';
      setTimeout(function () {
        btn.classList.remove('copied');
        if (label) label.textContent = 'Copy';
      }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {
        fallbackCopy(text); done();
      });
    } else {
      fallbackCopy(text); done();
    }
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-action="copy-question"]');
    if (t) copyQuestion(t);
  });
})();
