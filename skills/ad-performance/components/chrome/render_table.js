// Sortable performance table. Click a thead column to sort the tbody
// (camp rows only — ad rows trail their parent campaign row).

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.perf-table thead th[data-sort]').forEach(function (th) {
    th.addEventListener('click', function () {
      var table = th.closest('table');
      var tbody = table.querySelector('tbody');
      var col = Array.from(th.parentElement.children).indexOf(th);
      var asc = th.dataset.asc !== 'true';
      th.dataset.asc = asc;

      // Clear sort indicator on sibling headers, then mark this one.
      th.parentElement.querySelectorAll('th').forEach(function (other) {
        if (other !== th) {
          other.classList.remove('sort-asc', 'sort-desc');
          delete other.dataset.asc;
        }
      });
      th.classList.toggle('sort-asc', asc);
      th.classList.toggle('sort-desc', !asc);

      // Sort camp-rows only; ad rows follow their parent after re-insert.
      var campRows = Array.from(tbody.querySelectorAll('tr.camp-row'));
      campRows.sort(function (a, b) {
        var av = a.querySelectorAll('td')[col];
        var bv = b.querySelectorAll('td')[col];
        if (!av || !bv) return 0;
        // Keep minus signs so negatives sort correctly.
        var at = av.textContent.replace(/[^0-9.\-]/g, '');
        var bt = bv.textContent.replace(/[^0-9.\-]/g, '');
        var an = parseFloat(at);
        var bn = parseFloat(bt);
        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
        return asc
          ? av.textContent.localeCompare(bv.textContent)
          : bv.textContent.localeCompare(av.textContent);
      });

      // Re-insert: each camp row followed by its ad rows.
      campRows.forEach(function (cr) {
        tbody.appendChild(cr);
        var cid = cr.dataset.campaign;
        var plat = cr.dataset.platform;
        if (cid) {
          tbody.querySelectorAll(
            'tr.ad-row[data-campaign="' + cid + '"][data-platform="' + plat + '"]'
          ).forEach(function (ar) { tbody.appendChild(ar); });
        }
      });
    });
  });
});
