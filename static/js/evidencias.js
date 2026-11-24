/* Ventana de evidencias: ver (miniaturas, foto o PDF en la misma ventana) y subir arrastrando o eligiendo un archivo.
   Se activa con cualquier botón [data-evidencias="url"] (tarjetas del Kanban, Tubo de cartas, filas y fichas)
   y con [data-ver-evidencia="url"] para solo mirar un archivo (Actividad y evidencia). */
(() => {
    'use strict';
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
    const csrf = () => document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
    let modal = null, boton = null, url = '';

    function crearModal() {
        if (modal) return modal;
        modal = document.createElement('div');
        modal.className = 'modal fade'; modal.id = 'modal-evidencias'; modal.tabIndex = -1;
        modal.setAttribute('aria-labelledby', 'modal-evidencias-titulo');
        modal.innerHTML = `
          <div class="modal-dialog modal-lg modal-dialog-scrollable"><div class="modal-content evid">
            <div class="evid__cabecera">
              <div><small>Evidencias</small><h2 class="h5 mb-0" id="modal-evidencias-titulo"></h2></div>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button>
            </div>
            <div class="modal-body">
              <div class="evid__visor" hidden></div>
              <div class="evid__galeria" aria-live="polite"></div>
              <form class="evid__subir" novalidate>
                <label class="evid__zona" tabindex="0">
                  <input type="file" name="archivo" accept="image/jpeg,image/png,application/pdf" hidden>
                  <i class="bi bi-cloud-arrow-up" aria-hidden="true"></i>
                  <span class="evid__zona-texto"><b>Arrastre aquí una foto o un PDF</b> o haga clic para elegirlo<br><small>JPG, PNG o PDF · máximo 10 MB</small></span>
                </label>
                <div class="evid__previa" hidden></div>
                <input class="form-control mt-2" name="descripcion" maxlength="200" placeholder="Descripción breve (opcional): qué muestra la evidencia">
                <div class="evid__error text-danger small mt-2" role="alert" hidden></div>
                <div class="d-flex justify-content-between align-items-center mt-3 gap-2 flex-wrap">
                  <a class="small evid__ficha" href="#">Abrir ficha completa</a>
                  <button type="submit" class="btn btn-primary-custom" disabled><i class="bi bi-upload" aria-hidden="true"></i> Subir evidencia</button>
                </div>
              </form>
            </div>
          </div></div>`;
        document.body.appendChild(modal);
        const form = modal.querySelector('form'), zona = modal.querySelector('.evid__zona'), input = form.archivo;
        const elegir = archivo => {
            const previa = modal.querySelector('.evid__previa'), error = modal.querySelector('.evid__error');
            error.hidden = true;
            if (!archivo) return;
            const tipoOk = /^(image\/(jpeg|png)|application\/pdf)$/.test(archivo.type);
            if (!tipoOk || archivo.size > 10 * 1024 * 1024) {
                error.textContent = !tipoOk ? 'Adjunte una imagen JPG/PNG o un PDF.' : 'El archivo supera los 10 MB.';
                error.hidden = false; form.querySelector('[type=submit]').disabled = true; return;
            }
            const dt = new DataTransfer(); dt.items.add(archivo); input.files = dt.files;
            previa.hidden = false;
            previa.innerHTML = archivo.type === 'application/pdf'
                ? `<i class="bi bi-file-earmark-pdf text-danger fs-2"></i><span>${esc(archivo.name)}</span>`
                : `<img alt="Vista previa" src="${URL.createObjectURL(archivo)}"><span>${esc(archivo.name)}</span>`;
            form.querySelector('[type=submit]').disabled = false;
        };
        input.addEventListener('change', () => elegir(input.files[0]));
        zona.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
        ['dragenter', 'dragover'].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add('is-over'); }));
        ['dragleave', 'drop'].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.remove('is-over'); }));
        zona.addEventListener('drop', e => elegir(e.dataTransfer.files[0]));
        form.addEventListener('submit', async e => {
            e.preventDefault();
            const enviar = form.querySelector('[type=submit]'), error = modal.querySelector('.evid__error');
            enviar.disabled = true; enviar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Subiendo…';
            try {
                const datos = new FormData(form);
                const r = await fetch(url, {method: 'POST', body: datos, credentials: 'same-origin',
                    headers: {'Accept': 'application/json', 'X-CSRFToken': csrf()}});
                const d = await r.json().catch(() => ({}));
                if (!r.ok) throw new Error(d.error || 'No se pudo subir la evidencia.');
                form.reset(); modal.querySelector('.evid__previa').hidden = true;
                pintar(d, true);
            } catch (err) {
                error.textContent = err.message; error.hidden = false; enviar.disabled = false;
            } finally {
                enviar.innerHTML = '<i class="bi bi-upload" aria-hidden="true"></i> Subir evidencia';
            }
        });
        modal.addEventListener('click', e => {
            const a = e.target.closest('[data-ver]');
            if (a) { e.preventDefault(); mostrar(a.dataset.ver, a.dataset.pdf === '1', a.dataset.nombre); }
            if (e.target.closest('[data-cerrar-visor]')) modal.querySelector('.evid__visor').hidden = true;
        });
        return modal;
    }

    function mostrar(src, esPdf, nombre) {
        const visor = crearModal().querySelector('.evid__visor');
        visor.hidden = false;
        visor.innerHTML = `<div class="d-flex justify-content-between align-items-center mb-2"><b class="small text-truncate">${esc(nombre || '')}</b>
            <span class="d-flex gap-2"><a class="btn btn-sm btn-outline-secondary" href="${esc(src)}" target="_blank" rel="noopener"><i class="bi bi-box-arrow-up-right"></i> Abrir</a>
            <button type="button" class="btn btn-sm btn-outline-secondary" data-cerrar-visor><i class="bi bi-x-lg"></i></button></span></div>` +
            // El PDF no se incrusta: el servidor lo entrega con X-Frame-Options DENY y CSP sandbox (protección).
            (esPdf ? `<div class="evid__vacio"><i class="bi bi-file-earmark-pdf"></i><p class="mb-2">Documento PDF</p><a class="btn btn-primary-custom" href="${esc(src)}" target="_blank" rel="noopener"><i class="bi bi-box-arrow-up-right"></i> Abrir el PDF en otra pestaña</a></div>`
                   : `<img alt="${esc(nombre || 'Evidencia')}" src="${esc(src)}">`);
        visor.scrollIntoView({block: 'nearest'});
    }

    function pintar(d, recien) {
        const galeria = modal.querySelector('.evid__galeria');
        modal.querySelector('.evid__ficha').href = d.ficha;
        const lleno = d.cantidad >= d.maximo;
        modal.querySelector('.evid__subir').hidden = lleno;
        galeria.innerHTML = d.evidencias.length ? `<div class="small text-muted mb-2">${d.cantidad} de ${d.maximo} evidencias${lleno ? ' · máximo alcanzado' : ''}</div><div class="evid__grilla">` +
            d.evidencias.map((e, i) => `
              <a href="${esc(e.url)}" class="evid__item ${recien && i === 0 ? 'is-nueva' : ''}" data-ver="${esc(e.url)}" data-pdf="${e.es_pdf ? 1 : 0}" data-nombre="${esc(e.descripcion || e.nombre)}">
                ${e.es_pdf ? '<span class="evid__pdf"><i class="bi bi-file-earmark-pdf"></i>PDF</span>' : `<img loading="lazy" alt="" src="${esc(e.url)}">`}
                <span class="evid__pie"><b>${esc(e.descripcion || e.nombre)}</b><small>${esc(e.fecha)}${e.autor ? ' · ' + esc(e.autor) : ''}</small></span>
              </a>`).join('') + '</div>'
            : '<div class="evid__vacio"><i class="bi bi-images"></i><p class="mb-0">Aún no hay evidencias. Suba la primera: una foto del avance o un documento PDF.</p></div>';
        if (boton) {
            const n = boton.querySelector('[data-evidencias-cantidad]');
            if (n) { n.textContent = d.cantidad; n.className = 'badge rounded-pill ' + (d.cantidad ? 'text-bg-success' : 'text-bg-secondary'); }
            boton.classList.toggle('btn-outline-success', d.cantidad > 0); boton.classList.toggle('btn-outline-primary', !d.cantidad);
        }
    }

    async function abrir(b) {
        boton = b; url = b.dataset.evidencias;
        crearModal();
        modal.querySelector('#modal-evidencias-titulo').textContent = b.dataset.evidenciasTitulo || '';
        modal.querySelector('.evid__visor').hidden = true;
        modal.querySelector('.evid__error').hidden = true;
        modal.querySelector('.evid__previa').hidden = true;
        modal.querySelector('form').reset();
        modal.querySelector('.evid__galeria').innerHTML = '<div class="text-center text-muted py-4"><span class="spinner-border"></span></div>';
        window.bootstrap?.Modal.getOrCreateInstance(modal).show();
        try {
            const r = await fetch(url, {headers: {'Accept': 'application/json'}, credentials: 'same-origin'});
            const d = await r.json();
            if (!r.ok) throw new Error(d.error);
            pintar(d, false);
        } catch (err) {
            modal.querySelector('.evid__galeria').innerHTML = `<p class="text-danger">${esc(err.message || 'No se pudieron cargar las evidencias.')}</p>`;
        }
    }

    document.addEventListener('click', e => {
        const b = e.target.closest('[data-evidencias]');
        if (b) { e.preventDefault(); e.stopPropagation(); abrir(b); return; }
        const v = e.target.closest('[data-ver-evidencia]');
        if (v) {
            e.preventDefault(); crearModal();
            modal.querySelector('#modal-evidencias-titulo').textContent = v.dataset.titulo || 'Evidencia';
            modal.querySelector('.evid__galeria').innerHTML = ''; modal.querySelector('.evid__subir').hidden = true;
            mostrar(v.dataset.verEvidencia, v.dataset.pdf === '1', v.dataset.titulo);
            window.bootstrap?.Modal.getOrCreateInstance(modal).show();
        }
    });
    // ------------------------------------------------------------------ editar en ventana emergente
    // Carga la misma página de edición, muestra solo su formulario y guarda sin salir de la tabla o del Kanban.
    let editor = null;
    function crearEditor() {
        if (editor) return editor;
        editor = document.createElement('div');
        editor.className = 'modal fade'; editor.id = 'modal-editar'; editor.tabIndex = -1;
        editor.setAttribute('aria-labelledby', 'modal-editar-titulo');
        editor.innerHTML = `<div class="modal-dialog modal-lg modal-dialog-scrollable"><div class="modal-content evid">
            <div class="evid__cabecera"><div><small>Editar</small><h2 class="h5 mb-0" id="modal-editar-titulo"></h2></div>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button></div>
            <div class="modal-body"></div></div></div>`;
        document.body.appendChild(editor);
        return editor;
    }
    function mostrarFormulario(html, url, titulo) {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const form = doc.querySelector('form.needs-validation, main form[method="post"]');
        const cuerpo = crearEditor().querySelector('.modal-body');
        if (!form) { window.location.href = url; return; }
        const alerta = doc.querySelector('.alert-danger');
        cuerpo.innerHTML = (alerta ? alerta.outerHTML : '') + form.outerHTML +
            `<p class="small text-muted mt-3 mb-0"><a href="${esc(url)}">Abrir en página completa</a></p>`;
        editor.querySelector('#modal-editar-titulo').textContent = titulo;
        const f = cuerpo.querySelector('form');
        // «Cancelar» cierra la ventana en vez de navegar.
        f.querySelectorAll('a.btn-outline-secondary').forEach(a => { a.removeAttribute('href'); a.setAttribute('role', 'button'); a.dataset.bsDismiss = 'modal'; });
        // La delegación sigue al funcionario elegido (igual que en la página completa).
        const fun = f.querySelector('#id_funcionario'), del = f.querySelector('[data-sigue-funcionario]');
        if (fun && del) fun.addEventListener('change', () => { const op = fun.options[fun.selectedIndex]; if (op?.dataset.delegacion) del.value = op.dataset.delegacion; });
        f.addEventListener('submit', async e => {
            e.preventDefault();
            const enviar = f.querySelector('[type=submit]');
            if (enviar) { enviar.disabled = true; enviar.dataset.texto = enviar.innerHTML; enviar.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Guardando…'; }
            try {
                const r = await fetch(url, {method: 'POST', body: new FormData(f), credentials: 'same-origin', headers: {'Accept': 'text/html'}});
                if (r.redirected || r.url.split('?')[0] !== new URL(url, location.href).href.split('?')[0]) {
                    window.bootstrap?.Modal.getOrCreateInstance(editor).hide();
                    window.location.reload();   // muestra el cambio y el mensaje de éxito
                    return;
                }
                mostrarFormulario(await r.text(), url, titulo);   // vuelve con los errores marcados
            } catch (err) {
                if (enviar) { enviar.disabled = false; enviar.innerHTML = enviar.dataset.texto; }
                alert('No se pudo guardar. Revise su conexión e intente nuevamente.');
            }
        });
        setTimeout(() => f.querySelector('textarea, input:not([type=hidden]), select')?.focus(), 200);
    }
    document.addEventListener('click', async e => {
        const a = e.target.closest('a[data-editar-ventana]');
        if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        const titulo = a.closest('[data-mover], tr')?.querySelector('code, .font-monospace')?.textContent.trim() || 'Compromiso';
        crearEditor().querySelector('.modal-body').innerHTML = '<div class="text-center text-muted py-5"><span class="spinner-border"></span></div>';
        window.bootstrap?.Modal.getOrCreateInstance(editor).show();
        try {
            const r = await fetch(a.href, {credentials: 'same-origin', headers: {'Accept': 'text/html'}});
            mostrarFormulario(await r.text(), a.href, titulo.replace(/^\s*/, ''));
        } catch (err) { window.location.href = a.href; }
    });

    // Atajo: tecla «E» sobre una tarjeta o fila enfocada abre sus evidencias.
    document.addEventListener('keydown', e => {
        if (e.key.toLowerCase() !== 'e' || e.ctrlKey || e.metaKey || e.altKey || /input|textarea|select/i.test(document.activeElement?.tagName || '')) return;
        const b = document.activeElement?.closest?.('[data-ticket], .card, tr')?.querySelector('[data-evidencias]');
        if (b) { e.preventDefault(); abrir(b); }
    });
})();
