// ═══ STATE ═══════════════════════════════════════════════════
var curFile = null;
var curSessionId = null;
var procData = [];
var curFilter = 'all';

// ═══ NAV ═════════════════════════════════════════════════════
function goPanel(name) {
  document.querySelectorAll('.panel').forEach(function(p) { p.classList.remove('active'); });
  document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
  document.getElementById('panel-' + name).classList.add('active');
  var nav = document.getElementById('nav-' + name);
  if (nav) nav.classList.add('active');
}

// ═══ DRAG & DROP ═════════════════════════════════════════════
var dz = document.getElementById('dz');
var fi = document.getElementById('fi');

dz.addEventListener('dragover', function(e) { e.preventDefault(); dz.classList.add('drag'); });
dz.addEventListener('dragleave', function() { dz.classList.remove('drag'); });
dz.addEventListener('drop', function(e) {
  e.preventDefault(); dz.classList.remove('drag');
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});
dz.addEventListener('click', function(e) { if (e.target.tagName !== 'SPAN' || !e.target.parentElement.classList.contains('dz-sub')) fi.click(); });
fi.addEventListener('change', function(e) { if (e.target.files.length) setFile(e.target.files[0]); });

function setFile(f) {
  curFile = f;
  document.getElementById('pillName').textContent = f.name;
  document.getElementById('filePill').style.display = 'flex';
  document.getElementById('btnRun').style.display = 'block';
  dz.style.display = 'none';
  setStatus('Archivo listo', false);
}

function resetTool() {
  curFile = null; curSessionId = null; procData = [];
  fi.value = '';
  document.getElementById('filePill').style.display = 'none';
  document.getElementById('btnRun').style.display = 'none';
  document.getElementById('procState').style.display = 'none';
  dz.style.display = 'block';
  document.getElementById('nav-dl').style.opacity = '.4';
  document.getElementById('nav-dl').style.pointerEvents = 'none';
  document.getElementById('nav-reset').style.opacity = '.4';
  document.getElementById('nav-reset').style.pointerEvents = 'none';
  document.getElementById('nb-results').textContent = '';
  document.getElementById('nb-alerts').textContent = '';
  setStatus('Sin archivo', false);
  goPanel('upload');
}

function setStatus(txt, ready) {
  var el = document.getElementById('topStatus');
  el.textContent = '';
  var dot = document.createElement('div');
  dot.className = 'status-dot';
  el.appendChild(dot);
  el.appendChild(document.createTextNode(' ' + txt));
  el.className = 'status-chip' + (ready ? ' ready' : '');
}

function setMsg(label, sub) {
  document.getElementById('procLabel').textContent = label;
  document.getElementById('procSub').textContent = sub || '';
}

// ═══ PROCESS (backend hace el parsing y la validacion) ═══════
function runProcess() {
  if (!curFile) return;
  document.querySelector('.upload-wrap').style.display = 'none';
  document.getElementById('procState').style.display = 'block';
  setMsg('Subiendo archivo al servidor...', curFile.name);

  (async function() {
    try {
      var fd = new FormData();
      fd.append('file', curFile);

      setMsg('Procesando en el servidor...', curFile.name);
      var resp = await fetch('/api/upload', { method: 'POST', body: fd });

      if (!resp.ok) {
        var errBody = await resp.json().catch(function() { return {}; });
        throw new Error(errBody.detail || ('Error del servidor (' + resp.status + ')'));
      }

      var data = await resp.json();
      curSessionId = data.session_id;
      procData = data.productos;
      buildResults(procData, data.stats);

    } catch (err) {
      document.getElementById('procState').style.display = 'none';
      document.querySelector('.upload-wrap').style.display = 'block';
      alert('Error al procesar:\n' + err.message);
    }
  })();
}

// ═══ RESULTS ═════════════════════════════════════════════════
function buildResults(data, stats) {
  // Stats
  var total = data.length;
  var ok    = data.filter(function(r) { return r.estado==='ok'; }).length;
  var warn  = data.filter(function(r) { return r.estado==='warn'; }).length;
  var err   = data.filter(function(r) { return r.estado==='err'; }).length;

  var statsHtml = [
    ['Total', total, ''],
    ['Completos', ok, 's-ok'],
    ['Advertencias', warn, 's-warn'],
    ['Errores', err, 's-err'],
    ['Desc >250', data.filter(function(r){return r.warns.some(function(w){return w.indexOf('250')>=0;});}).length, '']
  ].map(function(s) {
    return '<div class="stat-card ' + s[2] + '"><div class="stat-val">' + s[1] + '</div><div class="stat-lbl">' + s[0] + '</div></div>';
  }).join('');
  document.getElementById('statsRow').innerHTML = statsHtml;

  // Nav badges
  document.getElementById('nb-results').textContent = total;
  document.getElementById('nb-results').className = 'nav-badge';
  var alertCount = err + warn;
  document.getElementById('nb-alerts').textContent = alertCount || '';
  document.getElementById('nb-alerts').className = 'nav-badge' + (err > 0 ? ' err' : warn > 0 ? ' warn' : '');

  // Enable sidebar actions
  document.getElementById('nav-dl').style.opacity = '1';
  document.getElementById('nav-dl').style.pointerEvents = 'auto';
  document.getElementById('nav-reset').style.opacity = '1';
  document.getElementById('nav-reset').style.pointerEvents = 'auto';

  renderTable(data, 'all');
  buildAlerts(data);
  mostrarAvisosPopup(stats);

  document.getElementById('procState').style.display = 'none';
  document.querySelector('.upload-wrap').style.display = 'block';
  setStatus(total + ' productos listos', ok === total);

  goPanel('results');
}

// Popup cerrable que resume, aparte de la tabla, los casos que el KAM
// necesita tener presentes: productos sin codigo de barras (informativo,
// no bloquea nada) y sin imagen (obligatoria — hay que pedirle los links
// al partner).
function mostrarAvisosPopup(stats) {
  var existing = document.getElementById('avisosPopup');
  if (existing) existing.remove();
  if (!stats) return;

  var mensajes = [];
  if (stats.sin_barcode > 0) {
    mensajes.push({
      tipo: 'info',
      texto: stats.sin_barcode + ' producto(s) sin código de barras. No es obligatorio, pero conviene revisarlo.',
    });
  }
  if (stats.sin_imagen > 0) {
    mensajes.push({
      tipo: 'error',
      texto: stats.sin_imagen + ' producto(s) sin imagen. Es obligatoria — pedile los links al partner antes de cargar el catálogo.',
    });
  }
  if (!mensajes.length) return;

  var popup = document.createElement('div');
  popup.id = 'avisosPopup';
  popup.className = 'avisos-popup';
  popup.innerHTML =
    '<button class="avisos-popup-close" aria-label="Cerrar">&times;</button>' +
    '<div class="avisos-popup-title">Antes de descargar, revisá esto:</div>' +
    mensajes.map(function(m) {
      return '<div class="avisos-popup-item avisos-' + m.tipo + '">' + esc(m.texto) + '</div>';
    }).join('');
  document.body.appendChild(popup);
  popup.querySelector('.avisos-popup-close').addEventListener('click', function() { popup.remove(); });
}

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ═══ FORMULAS K / P (preview — mismo calculo que el Excel real) ═
function properCase(s) {
  s = (s === null || s === undefined) ? '' : String(s);
  // Replica PROPER() de Excel: capitaliza toda letra que sigue a un
  // caracter no-letra (espacio, guion, parentesis, inicio de string, etc.),
  // no solo despues de espacios — así "Coca-Cola" queda "Coca-Cola", no "Coca-cola".
  var out = '';
  var prevIsLetter = false;
  for (var i = 0; i < s.length; i++) {
    var ch = s[i];
    if (/[a-zA-ZÀ-ÿ]/.test(ch)) {
      out += prevIsLetter ? ch.toLowerCase() : ch.toUpperCase();
      prevIsLetter = true;
    } else {
      out += ch;
      prevIsLetter = false;
    }
  }
  return out;
}

function computeNombreFormado(r) {
  var contTxt = (r.cont !== null && r.cont !== undefined && r.cont !== '') ? String(r.cont) : '';
  var partes = [properCase(r.que_es), properCase(r.marca), properCase(r.variante), properCase(contTxt), (r.uni || '')];
  return partes.join(' ').replace(/\s+/g, ' ').trim();
}

function computeValidationInfo(r) {
  var faltan = !r.sku || !r.precio || !r.que_es ||
    (r.cont === null || r.cont === undefined || r.cont === '') || !r.uni;
  return faltan ? 'Las columnas en naranja deben tener datos cuando el producto NO existe en la base' : 'OK';
}

// Validaciones de imagen y SKU — mismo criterio que validar_imagen() y
// validar_sku_caracteres() en el backend (rules.py), para que la tabla
// avise en vivo sin esperar a resubir el archivo.
var IMG_RE = /^https?:\/\/.+\.(jpg|jpeg|png)$/i;
var SKU_RE = /^[A-Za-z0-9_-]+$/;

function validarImagen(url) {
  var u = String(url || '').trim();
  if (/es\.imgbb\.com/i.test(u)) return 'El link de imagen no puede alojarse en es.imgbb.com';
  if (!IMG_RE.test(u)) return 'Link de imagen inválido (debe empezar con http(s):// y terminar en .jpg/.jpeg/.png)';
  return null;
}

function validarSku(sku) {
  if (sku && !SKU_RE.test(sku)) return 'SKU contiene caracteres no permitidos (solo letras, números, - y _)';
  return null;
}

// Recalcula errores/advertencias/estado de un producto a partir de sus
// valores actuales (se llama despues de cada edicion en la tabla). Refleja
// las mismas reglas obligatorias que procesar_filas() en el backend para
// el template fijo de PedidosYa: F, Contenido, Unidad e Imagen son
// obligatorios; Codigo de Barras (B) es opcional.
//
// Nota: la normalizacion de unidades (alias, envases, prohibidas) y los
// chequeos de emojis/abreviaciones solo corren en el backend al procesar
// el archivo — si el KAM edita la unidad a mano ahi en la tabla, esos
// chequeos no se vuelven a correr hasta la proxima subida.
function revalidar(r) {
  r.errs = [];
  if (!r.sku) {
    r.errs.push('SKU vacío');
  } else {
    var skuErr = validarSku(r.sku);
    if (skuErr) r.errs.push(skuErr);
  }
  if (!r.precio) r.errs.push('Precio vacío o inválido');
  if (!r.sec)    r.errs.push('Sección vacía');
  if (!r.que_es || !String(r.que_es).trim()) r.errs.push('Que producto es vacío');
  if (r.cont === null || r.cont === undefined || r.cont === '' || !r.uni) {
    r.errs.push('Contenido/Unidad vacíos');
  }
  if (!r.img) {
    r.errs.push('Imagen vacía — el partner debe enviar el link');
  } else {
    var imgErr = validarImagen(r.img);
    if (imgErr) r.errs.push(imgErr);
  }

  r.warns = [];
  var descLen = (r.desc || '').length;
  if (descLen > 250) r.warns.push('Descripción ' + descLen + ' car. (máx 250)');
  var nfLen = computeNombreFormado(r).length;
  if (nfLen > 64) r.warns.push('Nombre formado ' + nfLen + ' car. (máx 64)');

  r.estado = r.errs.length > 0 ? 'err' : (r.warns.length > 0 ? 'warn' : 'ok');
}

var BADGE_CLASS = { ok: 'badge-ok', warn: 'badge-warn', err: 'badge-err' };
var BADGE_TEXT  = { ok: 'OK', warn: 'Aviso', err: 'Error' };
var ROW_CLASS   = { ok: 'r-ok', warn: 'r-warn', err: 'r-err' };

function alertsHtmlFor(r) {
  return r.errs.map(function(e) { return '<span class="a-err">• ' + esc(e) + '</span>'; })
    .concat(r.warns.map(function(w) { return '<span class="a-warn">• ' + esc(w) + '</span>'; }))
    .join('<br>');
}

function renderTable(data, filtro) {
  curFilter = filtro;
  var filtered = filtro === 'all' ? data : data.filter(function(r) { return r.estado === filtro; });
  var tbody = document.getElementById('tblBody');
  tbody.innerHTML = '';
  var MAX = 400;

  filtered.slice(0, MAX).forEach(function(r) {
    var globalIdx = data.indexOf(r);
    tbody.appendChild(buildRow(r, globalIdx));
  });

  if (filtered.length > MAX) {
    var tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="19" style="text-align:center;color:var(--ink-3);padding:14px;font-size:12px">... y ' + (filtered.length-MAX) + ' filas más en el archivo descargado</td>';
    tbody.appendChild(tr);
  }
}

function buildRow(r, globalIdx) {
  var tr = document.createElement('tr');
  tr.className = ROW_CLASS[r.estado];
  tr.dataset.idx = globalIdx;

  var cells = [
    '<td><div class="cell cell-ro cell-num" style="font-size:11px;color:var(--ink-3)">' + (globalIdx+3) + '</div></td>',
    cellHtml(r, globalIdx, 'activo'),
    cellHtml(r, globalIdx, 'ean'),
    cellHtml(r, globalIdx, 'sku'),
    cellHtml(r, globalIdx, 'precio'),
    cellHtml(r, globalIdx, 'sec'),
    cellHtml(r, globalIdx, 'que_es', { title: r.orig }),
    cellHtml(r, globalIdx, 'marca'),
    cellHtml(r, globalIdx, 'variante'),
    cellHtml(r, globalIdx, 'cont'),
    cellHtml(r, globalIdx, 'uni'),
    '<td><div class="cell cell-ro cell-formula cell-k">' + esc(computeNombreFormado(r)) + '</div></td>',
    cellHtml(r, globalIdx, 'img'),
    cellHtml(r, globalIdx, 'desc'),
    cellHtml(r, globalIdx, 'impuestos'),
    cellHtml(r, globalIdx, 'ean_fraccionado'),
    '<td><div class="cell cell-ro cell-formula cell-p">' + esc(computeValidationInfo(r)) + '</div></td>',
    '<td class="col-sticky" style="right:220px"><div class="cell cell-ro cell-estado"><span class="badge ' + BADGE_CLASS[r.estado] + '">' + BADGE_TEXT[r.estado] + '</span></div></td>',
    '<td class="col-sticky" style="right:0"><div class="cell cell-ro alert-list cell-alertas">' + (alertsHtmlFor(r) || '') + '</div></td>',
  ];

  tr.innerHTML = cells.join('');
  bindRowEditing(tr);
  return tr;
}

function cellHtml(r, globalIdx, field, opts) {
  opts = opts || {};
  var val = r[field];
  var display = (val === null || val === undefined) ? '' : val;
  var emptyCls = (val === null || val === undefined || val === '') ? ' cell-empty' : '';
  var titleAttr = opts.title ? ' title="' + esc(opts.title) + '"' : '';
  return '<td><div class="cell' + emptyCls + '" contenteditable="true" data-field="' + field + '" data-idx="' + globalIdx + '"' + titleAttr + '>' + esc(display) + '</div></td>';
}

function bindRowEditing(tr) {
  tr.querySelectorAll('[contenteditable][data-field]').forEach(function(el) {
    el.addEventListener('blur', function() { onCellEdited(el); });
    el.addEventListener('keydown', function(e) {
      if (e.key === 'Tab') {
        e.preventDefault();
        var cells = Array.from(document.querySelectorAll('[contenteditable][data-field]'));
        var cur = cells.indexOf(el);
        var next = cells[e.shiftKey ? cur - 1 : cur + 1];
        if (next) { next.focus(); var range = document.createRange(); range.selectNodeContents(next); window.getSelection().removeAllRanges(); window.getSelection().addRange(range); }
      }
      if (e.key === 'Escape') el.blur();
      if (e.key === 'Enter') { e.preventDefault(); el.blur(); }
    });
  });
}

function onCellEdited(el) {
  var idx   = parseInt(el.dataset.idx, 10);
  var field = el.dataset.field;
  var val   = el.textContent.trim();
  var r     = procData[idx];

  if (field === 'cont') {
    var n = parseFloat(val.replace(',', '.'));
    r[field] = isNaN(n) ? null : (n % 1 === 0 ? parseInt(n) : n);
  } else if (field === 'precio') {
    var n2 = parseFloat(val.replace(/[$.\s]/g, '').replace(',', '.'));
    r[field] = isNaN(n2) || n2 <= 0 ? null : (n2 % 1 === 0 ? parseInt(n2) : n2);
  } else {
    r[field] = val;
  }

  el.classList.toggle('cell-empty', r[field] === null || r[field] === undefined || r[field] === '');

  revalidar(r);

  var tr = el.closest('tr');
  tr.className = ROW_CLASS[r.estado];
  tr.querySelector('.cell-k').textContent = computeNombreFormado(r);
  tr.querySelector('.cell-p').textContent = computeValidationInfo(r);
  var estadoCell = tr.querySelector('.cell-estado');
  estadoCell.innerHTML = '<span class="badge ' + BADGE_CLASS[r.estado] + '">' + BADGE_TEXT[r.estado] + '</span>';
  tr.querySelector('.cell-alertas').innerHTML = alertsHtmlFor(r) || '';
}

function applyFilter(btn) {
  document.querySelectorAll('.fchip').forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
  renderTable(procData, btn.getAttribute('data-f'));
}

function buildAlerts(data) {
  var conA = data.filter(function(r) { return r.errs.length > 0 || r.warns.length > 0; });
  if (conA.length === 0) {
    document.getElementById('alertsContent').innerHTML =
      '<div class="alerts-empty">✓ Sin alertas. Todos los productos están listos para cargar.</div>';
    return;
  }
  var html = '<div style="margin-bottom:16px;font-size:13px;color:var(--ink-3)">' +
    conA.length + ' productos con alertas</div><div class="alerts-grid">';
  conA.forEach(function(r) {
    var fila = data.indexOf(r) + 3;
    var tags = r.errs.map(function(e) { return '<span class="alert-tag t-err">' + esc(e) + '</span>'; })
      .concat(r.warns.map(function(w) { return '<span class="alert-tag t-warn">' + esc(w) + '</span>'; })).join('');
    html += '<div class="alert-card ' + (r.errs.length > 0 ? 'ac-err' : 'ac-warn') + '">' +
      '<div class="alert-fila">Fila ' + fila + '</div>' +
      '<div class="alert-prod">' + esc(r.orig).slice(0,45) + '</div>' +
      '<div class="alert-msgs">' + tags + '</div></div>';
  });
  html += '</div>';
  document.getElementById('alertsContent').innerHTML = html;
}

// ═══ DOWNLOAD (backend inyecta los datos en el template original) ═══
function descargar() {
  if (!procData.length || !curSessionId) return;

  (async function() {
    try {
      var resp = await fetch('/api/download/' + curSessionId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ productos: procData }),
      });

      if (!resp.ok) {
        var errBody = await resp.json().catch(function() { return {}; });
        throw new Error(errBody.detail || ('Error del servidor (' + resp.status + ')'));
      }

      var blob = await resp.blob();
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'template_procesado_' + new Date().toISOString().slice(0, 10) + '.xlsx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error al descargar:\n' + err.message);
    }
  })();
}
