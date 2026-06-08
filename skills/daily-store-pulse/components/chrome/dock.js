// Go-deeper dock glue. Each .dock-link button carries a data-prompt. In a live
// artifact (window.sendPrompt defined) clicking sends the prompt to the chat;
// otherwise it copies the prompt to the clipboard. One delegated listener on
// document — no inline handlers, prompts come from data-prompt in the DOM.
(function () {
  var live = typeof window.sendPrompt === 'function';

  // Reflect the available action in each button's CTA chip on load.
  Array.prototype.forEach.call(document.querySelectorAll('.dock-link[data-prompt]'), function (btn) {
    var cta = btn.querySelector('.dock-cta');
    if (cta) cta.textContent = live ? 'Send →' : 'Copy →';
  });

  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest('.dock-link[data-prompt]');
    if (!btn) return;
    var prompt = btn.getAttribute('data-prompt') || '';
    if (!prompt) return;
    var cta = btn.querySelector('.dock-cta');

    if (typeof window.sendPrompt === 'function') {
      try { window.sendPrompt(prompt); } catch (err) { console.warn('sendPrompt failed', err); }
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(prompt).then(function () {
        btn.classList.add('copied');
        if (cta) cta.textContent = 'Copied ✓';
        setTimeout(function () {
          btn.classList.remove('copied');
          if (cta) cta.textContent = 'Copy →';
        }, 1800);
      });
    }
  });
})();
