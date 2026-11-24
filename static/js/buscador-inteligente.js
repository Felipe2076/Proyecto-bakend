/* Búsqueda inteligente (barra superior) y autocompletado del vecino por RUT. Sin librerías externas. */
(() => {
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

    // ---------------------------------------------------------------- buscador de la barra superior
    const caja = document.querySelector('[data-buscador]');
    if (caja) {
        const input = caja.querySelector('input');
        const panel = caja.querySelector('[data-buscador-panel]');
        const url = caja.dataset.buscador;
        let temporizador = null, ultimo = '', activo = -1, controlador = null;

        const cerrar = () => { panel.hidden = true; activo = -1; input.setAttribute('aria-expanded', 'false'); };
        const enlaces = () => [...panel.querySelectorAll('a')];
        const marcar = i => {
            const items = enlaces();
            items.forEach((a, k) => a.classList.toggle('active', k === i));
            if (items[i]) items[i].scrollIntoView({block: 'nearest'});
            activo = i;
        };

        const pintar = (datos, texto) => {
            if (!datos.grupos.length) {
                panel.innerHTML = `<div class="buscador__vacio"><i class="bi bi-search"></i> Sin resultados para «${esc(texto)}».</div>`;
            } else {
                let html = datos.sugerencia ? `<div class="buscador__sugerencia"><i class="bi bi-magic"></i> Mostrando resultados para «<b>${esc(datos.sugerencia)}</b>»</div>` : '';
                for (const g of datos.grupos) {
                    html += `<div class="buscador__grupo"><i class="bi bi-${esc(g.icono)}"></i> ${esc(g.titulo)}</div>`;
                    for (const it of g.items) {
                        const ficha = it.ficha ? ` data-ficha="${esc(it.ficha)}"` : '';
                        html += `<a class="buscador__item" href="${esc(it.url)}"${ficha}><span class="buscador__texto">${it.ficha ? '<i class="bi bi-person-vcard"></i> ' : ''}${esc(it.texto)}</span><span class="buscador__detalle">${esc(it.detalle)}</span></a>`;
                    }
                }
                panel.innerHTML = html;
            }
            panel.hidden = false; activo = -1; input.setAttribute('aria-expanded', 'true');
        };

        const consultar = async texto => {
            if (controlador) controlador.abort();
            controlador = new AbortController();
            panel.hidden = false;
            panel.innerHTML = '<div class="buscador__vacio"><span class="spinner-border spinner-border-sm"></span> Buscando…</div>';
            try {
                const r = await fetch(`${url}?q=${encodeURIComponent(texto)}`, {headers: {Accept: 'application/json'}, signal: controlador.signal});
                if (!r.ok) throw new Error();
                if (texto === input.value.trim()) pintar(await r.json(), texto);
            } catch (e) {
                if (e.name !== 'AbortError') panel.innerHTML = '<div class="buscador__vacio">No se pudo buscar. Intente nuevamente.</div>';
            }
        };

        input.addEventListener('input', () => {
            const texto = input.value.trim();
            clearTimeout(temporizador);
            if (texto.length < 2) { cerrar(); ultimo = ''; return; }
            if (texto === ultimo) return;
            temporizador = setTimeout(() => { ultimo = texto; consultar(texto); }, 220);
        });
        input.addEventListener('keydown', e => {
            const items = enlaces();
            if (e.key === 'ArrowDown' && items.length) { e.preventDefault(); marcar((activo + 1) % items.length); }
            else if (e.key === 'ArrowUp' && items.length) { e.preventDefault(); marcar((activo - 1 + items.length) % items.length); }
            else if (e.key === 'Enter') { e.preventDefault(); (items[activo] || items[0])?.click(); }
            else if (e.key === 'Escape') { cerrar(); input.blur(); }
        });
        // Un vecino abre su ficha emergente en vez de navegar.
        panel.addEventListener('click', e => {
            const a = e.target.closest('a[data-ficha]');
            if (!a) return;
            e.preventDefault(); cerrar(); abrirFicha(a.dataset.ficha);
        });
        input.addEventListener('focus', () => { if (panel.innerHTML && input.value.trim().length >= 2) panel.hidden = false; });
        document.addEventListener('click', e => { if (!caja.contains(e.target)) cerrar(); });
        // Atajo: «/» o Ctrl+K enfoca el buscador desde cualquier pantalla.
        document.addEventListener('keydown', e => {
            const escribiendo = /input|textarea|select/i.test(document.activeElement?.tagName || '');
            if ((e.key === '/' && !escribiendo) || (e.key.toLowerCase() === 'k' && (e.ctrlKey || e.metaKey))) { e.preventDefault(); input.focus(); input.select(); }
        });
    }

    // ---------------------------------------------------------------- ficha emergente del vecino
    function barraFases(fases, actual, vencido) {
        return `<ol class="fases ${vencido ? 'fases--vencido' : ''}" aria-label="Fase ${actual + 1} de ${fases.length}: ${esc(fases[actual])}">` +
            fases.map((f, i) => `<li class="${i < actual ? 'hecha' : i === actual ? 'actual' : ''}"><span class="fases__punto">${i < actual || (i === actual && i === fases.length - 1) ? '<i class="bi bi-check-lg"></i>' : i + 1}</span><span class="fases__nombre">${esc(f)}</span></li>`).join('') +
            '</ol>';
    }

    async function abrirFicha(url) {
        let modal = document.getElementById('ficha-vecino');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'ficha-vecino'; modal.className = 'modal fade'; modal.tabIndex = -1;
            modal.setAttribute('aria-labelledby', 'ficha-vecino-titulo');
            modal.innerHTML = '<div class="modal-dialog modal-lg modal-dialog-scrollable"><div class="modal-content ficha"></div></div>';
            document.body.appendChild(modal);
        }
        const cont = modal.querySelector('.modal-content');
        cont.innerHTML = '<div class="p-5 text-center text-muted"><span class="spinner-border"></span><div class="mt-2">Cargando ficha…</div></div>';
        const instancia = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modal) : null;
        instancia?.show();
        try {
            const r = await fetch(url, {headers: {Accept: 'application/json'}});
            if (!r.ok) throw new Error();
            const d = await r.json(), v = d.vecino;
            const dato = (icono, etq, val) => val ? `<div class="ficha__dato"><i class="bi bi-${icono}"></i><div><small>${etq}</small><div>${esc(val)}</div></div></div>` : '';
            const insignia = v.extranjero === true ? '<span class="badge rounded-pill ficha__badge ficha__badge--ext"><i class="bi bi-globe-americas"></i> Extranjero/a</span>'
                : v.extranjero === false ? '<span class="badge rounded-pill ficha__badge">No extranjero/a</span>'
                : '<span class="badge rounded-pill text-bg-light border">Nacionalidad no registrada</span>';
            const acts = d.actividades.length ? d.actividades.map(a => `
                <a class="ficha__actividad" href="${esc(a.url)}">
                    <div class="d-flex justify-content-between gap-2 flex-wrap">
                        <div><b>${esc(a.codigo)}</b> · ${esc(a.descripcion)}</div>
                        ${a.vencido ? '<span class="badge text-bg-danger"><i class="bi bi-exclamation-triangle"></i> Vencido</span>' : ''}
                    </div>
                    <div class="ficha__meta"><span><i class="bi bi-person-badge"></i> ${esc(a.funcionario)}</span><span><i class="bi bi-calendar3"></i> ${esc(a.periodo)}</span><span><i class="bi bi-hourglass-split"></i> plazo ${esc(a.plazo)}</span></div>
                    ${barraFases(d.fases, a.fase, a.vencido)}
                </a>`).join('') : '<p class="text-muted small mb-0">Sin actividades registradas para este vecino.</p>';
            const tks = d.tickets.length ? d.tickets.map(t => `
                <a class="ficha__ticket" href="${esc(t.url)}"><b>${esc(t.codigo)}</b><span>${esc(t.descripcion)}</span>
                <span class="ficha__meta"><span><i class="bi bi-person-badge"></i> ${esc(t.funcionario)}</span><span><i class="bi bi-calendar3"></i> ${esc(t.periodo)}</span><span class="badge text-bg-light border">${esc(t.estado)}</span></span></a>`).join('')
                : '<p class="text-muted small mb-0">Sin tickets.</p>';
            cont.innerHTML = `
                <div class="ficha__cabecera">
                    <div class="ficha__avatar">${esc(v.nombre.split(' ').filter(Boolean).slice(0, 2).map(p => p[0]).join('').toUpperCase())}</div>
                    <div class="flex-grow-1"><h2 class="h5 mb-1" id="ficha-vecino-titulo">${esc(v.nombre)}</h2>${insignia}</div>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                </div>
                <div class="modal-body">
                    <div class="ficha__datos">${dato('person-vcard', 'RUT', v.rut)}${dato('globe-americas', '¿Extranjero/a?', v.nacionalidad)}${dato('telephone', 'Teléfono', v.telefono)}${dato('envelope', 'Correo', v.correo)}${dato('geo-alt', 'Dirección', v.direccion)}${dato('map', 'Delegación', [v.delegacion, v.territorio].filter(Boolean).join(' · '))}</div>
                    <h3 class="ficha__titulo"><i class="bi bi-kanban"></i> Actividades <span class="badge rounded-pill text-bg-secondary">${d.actividades.length}</span></h3>${acts}
                    <h3 class="ficha__titulo"><i class="bi bi-ticket-detailed"></i> Tickets <span class="badge rounded-pill text-bg-secondary">${d.tickets.length}</span></h3>${tks}
                </div>
                <div class="modal-footer"><a class="btn btn-primary" href="${esc(v.nuevo_ticket)}"><i class="bi bi-plus-lg"></i> Nuevo ticket para este vecino</a></div>`;
        } catch (e) {
            cont.innerHTML = '<div class="p-4"><p class="mb-3">No se pudo cargar la ficha. Intente nuevamente.</p><button class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button></div>';
        }
    }

    // ---------------------------------------------------------------- ¿extranjero? muestra el país solo si responde «Sí»
    const bloqueExt = document.querySelector('[data-extranjero]');
    if (bloqueExt) {
        const pais = bloqueExt.querySelector('[data-nacionalidad]');
        const campoPais = pais.querySelector('input');
        const actualizar = () => {
            const si = bloqueExt.querySelector('input[value="si"]').checked;
            pais.hidden = !si; campoPais.required = si;
            if (si) setTimeout(() => campoPais.focus(), 50);
        };
        bloqueExt.querySelectorAll('input[name="es_extranjero"]').forEach(r => r.addEventListener('change', actualizar));
    }

    // ---------------------------------------------------------------- autocompletar vecino por RUT
    const rut = document.querySelector('[data-autocompletar-rut]');
    if (rut) {
        const url = rut.dataset.autocompletarRut;
        const campos = {nombre: '#vecino_nombre', telefono: '#telefono_whatsapp', correo: '#email'};
        const aviso = document.createElement('div');
        aviso.className = 'form-text'; aviso.setAttribute('role', 'status'); aviso.setAttribute('aria-live', 'polite');
        rut.parentNode.appendChild(aviso);
        let ultimo = '';

        const completar = async () => {
            const valor = rut.value.trim();
            if (valor.replace(/[^0-9kK]/g, '').length < 8 || valor === ultimo) return;
            ultimo = valor;
            try {
                const r = await fetch(`${url}?rut=${encodeURIComponent(valor)}`, {headers: {Accept: 'application/json'}});
                if (!r.ok) return;
                const d = await r.json();
                if (!d.valido) { aviso.innerHTML = ''; return; }
                if (!d.encontrado) { aviso.innerHTML = '<i class="bi bi-person-plus"></i> Vecino nuevo: complete sus datos y quedará registrado.'; aviso.className = 'form-text text-primary'; return; }
                let llenados = 0;
                for (const [clave, selector] of Object.entries(campos)) {
                    const el = document.querySelector(selector);
                    if (el && !el.value.trim() && d.vecino[clave]) {
                        el.value = d.vecino[clave]; llenados++;
                        el.classList.add('campo-autocompletado');
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        setTimeout(() => el.classList.remove('campo-autocompletado'), 1600);
                    }
                }
                if (d.vecino.es_extranjero !== null && d.vecino.es_extranjero !== undefined) {
                    const radio = document.querySelector(`input[name="es_extranjero"][value="${d.vecino.es_extranjero ? 'si' : 'no'}"]`);
                    if (radio && !document.querySelector('input[name="es_extranjero"]:checked')) {
                        radio.checked = true; radio.dispatchEvent(new Event('change', {bubbles: true})); llenados++;
                        const p = document.querySelector('#nacionalidad');
                        if (p && d.vecino.nacionalidad && !p.value) p.value = d.vecino.nacionalidad;
                    }
                }
                const sel = document.querySelector('#delegacion');
                if (sel && !sel.value && d.vecino.delegacion) { sel.value = d.vecino.delegacion; if (sel.value) llenados++; }
                aviso.className = 'form-text text-success';
                aviso.innerHTML = `<i class="bi bi-check-circle"></i> ${esc(d.vecino.nombre)} ya está registrado` +
                    (llenados ? ` · se completaron ${llenados} campo(s)` : '') +
                    (d.vecino.tickets ? ` · tiene ${d.vecino.tickets} ticket(s) anteriores` : '') + '.';
            } catch (e) { /* sin conexión: el formulario sigue funcionando a mano */ }
        };
        rut.addEventListener('blur', completar);
        rut.addEventListener('input', () => { if (/^\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]$/.test(rut.value.trim())) completar(); });
        if (rut.value.trim()) completar();
    }
})();
