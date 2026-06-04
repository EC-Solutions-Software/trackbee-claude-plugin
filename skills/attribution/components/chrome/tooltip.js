(function(){
  const tip = document.getElementById('tbTooltip');
  if (!tip) return;
  function show(html, x, y){
    tip.innerHTML = html;
    tip.classList.add('visible');
    tip.setAttribute('aria-hidden', 'false');
    const r = tip.getBoundingClientRect();
    const pad = 14;
    let nx = x + pad, ny = y + pad;
    if (nx + r.width  > window.innerWidth  - 8) nx = x - r.width  - pad;
    if (ny + r.height > window.innerHeight - 8) ny = y - r.height - pad;
    tip.style.left = nx + 'px';
    tip.style.top  = ny + 'px';
  }
  function hide(){
    tip.classList.remove('visible');
    tip.setAttribute('aria-hidden', 'true');
  }
  document.addEventListener('mouseover', e => {
    const el = e.target.closest('[data-tip]');
    if (!el) return;
    show(el.getAttribute('data-tip'), e.clientX, e.clientY);
  });
  document.addEventListener('mousemove', e => {
    if (!tip.classList.contains('visible')) return;
    const el = e.target.closest('[data-tip]');
    if (!el) { hide(); return; }
    show(el.getAttribute('data-tip'), e.clientX, e.clientY);
  });
  document.addEventListener('mouseout', e => {
    const from = e.target.closest && e.target.closest('[data-tip]');
    const to = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('[data-tip]');
    if (from && from !== to) hide();
  });
})();
