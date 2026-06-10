/**
 * MedSync Export Utilities
 * Provides CSV download and PDF (print) export for all report screens.
 * Usage:
 *   MedSyncExport.csv('filename.csv', ['Col A','Col B'], [['val','val'], ...]);
 *   MedSyncExport.pdf('Report Title', 'Subtitle / meta line', ['Col A','Col B'], [['val','val'], ...]);
 */
const MedSyncExport = (function () {

  // ── CSV ──────────────────────────────────────────────────────
  function csv(filename, headers, rows) {
    const escape = v => {
      const s = String(v ?? '').replace(/"/g, '""');
      return /[,"\n\r]/.test(s) ? '"' + s + '"' : s;
    };
    const lines = [
      headers.map(escape).join(','),
      ...rows.map(r => r.map(escape).join(','))
    ];
    const blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), { href: url, download: filename });
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url); }, 500);
  }

  // ── PDF (print window) ───────────────────────────────────────
  function pdf(title, meta, headers, rows) {
    const colCount = headers.length;
    const thCells  = headers.map(h => `<th>${h}</th>`).join('');
    const trRows   = rows.map(r =>
      '<tr>' + r.map(v => `<td>${String(v ?? '').replace(/</g,'&lt;')}</td>`).join('') + '</tr>'
    ).join('');

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>${title}</title>
<style>
  @page { margin: 18mm 15mm; }
  body { font-family: Arial, sans-serif; font-size: 11px; color: #1C2B4A; margin: 0; }
  .hdr  { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 14px; border-bottom: 1.5px solid #1C2B4A; padding-bottom: 8px; }
  .hdr-left h1 { font-size: 16px; font-weight: 700; margin: 0 0 2px; }
  .hdr-left p  { font-size: 11px; color: #8899AA; margin: 0; }
  .hdr-right   { font-size: 10px; color: #8899AA; text-align: right; }
  table { width: 100%; border-collapse: collapse; margin-top: 4px; }
  thead tr { background: #1C2B4A; color: #fff; }
  thead th { padding: 6px 8px; text-align: left; font-size: 10px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }
  tbody tr:nth-child(even) { background: #F5F3FA; }
  tbody tr:hover { background: #EEE8F5; }
  tbody td { padding: 6px 8px; font-size: 11px; border-bottom: 0.5px solid #E8E4F4; }
  .ftr { margin-top: 12px; font-size: 9px; color: #8899AA; border-top: 0.5px solid #DDD9EC; padding-top: 6px; display: flex; justify-content: space-between; }
  @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
</style>
</head>
<body>
<div class="hdr">
  <div class="hdr-left">
    <h1>${title}</h1>
    <p>${meta}</p>
  </div>
  <div class="hdr-right">Scout Veterinary · MedSync<br>Exported ${new Date().toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})}</div>
</div>
<table>
  <thead><tr>${thCells}</tr></thead>
  <tbody>${trRows}</tbody>
</table>
<div class="ftr">
  <span>${rows.length} record${rows.length !== 1 ? 's' : ''}</span>
  <span>MedSync — confidential</span>
</div>
<script>window.onload = function(){ window.print(); }<\/script>
</body>
</html>`;

    const w = window.open('', '_blank', 'width=900,height=700');
    if (w) { w.document.write(html); w.document.close(); }
    else    { alert('Pop-up blocked — please allow pop-ups for this site to use PDF export.'); }
  }

  // ── Dropdown helper ──────────────────────────────────────────
  // Renders a small "Export ▾" dropdown button.
  // Call MedSyncExport.attachDropdown(buttonEl, getDataFn)
  // where getDataFn() returns { title, meta, filename, headers, rows }
  function attachDropdown(btn, getDataFn) {
    let menu = null;

    function close() {
      if (menu) { menu.remove(); menu = null; }
      document.removeEventListener('click', close);
    }

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (menu) { close(); return; }

      menu = document.createElement('div');
      menu.style.cssText =
        'position:absolute;z-index:9999;background:#fff;border:0.5px solid #DDD9EC;'
        + 'border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.12);min-width:150px;overflow:hidden;';

      const rect = btn.getBoundingClientRect();
      menu.style.top  = (rect.bottom + 4) + 'px';
      menu.style.left = (rect.left)  + 'px';

      const items = [
        { icon: '⬇', label: 'Download CSV', action: 'csv' },
        { icon: '🖨', label: 'Export PDF',   action: 'pdf' },
      ];

      items.forEach(({ icon, label, action }) => {
        const item = document.createElement('button');
        item.textContent = icon + '  ' + label;
        item.style.cssText =
          'display:block;width:100%;text-align:left;padding:9px 14px;background:none;border:none;'
          + 'font-size:12px;font-family:inherit;color:#1C2B4A;cursor:pointer;';
        item.onmouseenter = () => item.style.background = '#F5F3FA';
        item.onmouseleave = () => item.style.background = 'none';
        item.addEventListener('click', function (e) {
          e.stopPropagation();
          close();
          const d = getDataFn();
          if (!d) return;
          if (action === 'csv') MedSyncExport.csv(d.filename + '.csv', d.headers, d.rows);
          if (action === 'pdf') MedSyncExport.pdf(d.title, d.meta, d.headers, d.rows);
        });
        menu.appendChild(item);
      });

      document.body.appendChild(menu);
      setTimeout(() => document.addEventListener('click', close), 0);
    });
  }

  return { csv, pdf, attachDropdown };
})();
