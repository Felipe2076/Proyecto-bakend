(() => {
  const resultados = '[data-resultado]';
  const key = 'siged-search-focus';
  document.querySelectorAll('form').forEach(form => {
    if (form.method !== 'get') return;
    const input = form.querySelector('input[name="q"]:not([type="hidden"]), input[name="busqueda"]');
    if (!input) return;
    const estado = document.createElement('div');
    estado.className = 'visually-hidden';
    estado.setAttribute('role', 'status');
    form.after(estado);
    let timer, controller;
    let composing = false;

    const urlConsulta = () => {
      const url = new URL(form.action, location.href);
      const campos = new URLSearchParams(new FormData(form));
      const cantidad = new URLSearchParams(location.search).get('per_page');
      if (cantidad && !campos.has('per_page')) campos.set('per_page', cantidad);
      campos.delete('page');
      url.search = campos;
      return url;
    };

    const navegar = url => {
      try { sessionStorage.setItem(key, JSON.stringify({path: url.pathname, value: input.value, cursor: input.selectionStart})); } catch (_) {}
      location.assign(url);
    };

    const buscar = async () => {
      const url = urlConsulta();
      if (!document.querySelector(resultados)) return navegar(url);
      controller = new AbortController();
      const solicitud = controller;
      estado.textContent = 'Buscando…';
      try {
        const respuesta = await fetch(url, {signal: solicitud.signal, credentials: 'same-origin', cache: 'no-store'});
        if (respuesta.redirected || !respuesta.ok) return navegar(url);
        const pagina = new DOMParser().parseFromString(await respuesta.text(), 'text/html');
        if (solicitud.signal.aborted) return;
        const nuevos = new Map([...pagina.querySelectorAll(resultados)].map(node => [node.dataset.resultado, node]));
        const actuales = [...document.querySelectorAll(resultados)];
        if (actuales.some(node => !nuevos.has(node.dataset.resultado))) return navegar(url);
        actuales.forEach(node => node.replaceWith(nuevos.get(node.dataset.resultado)));
        history.replaceState(history.state, '', url);
        estado.textContent = 'Resultados actualizados.';
      } catch (error) {
        if (error.name !== 'AbortError') estado.textContent = 'No se pudo buscar. Inténtelo de nuevo.';
      }
    };

    const cancelar = () => {
      clearTimeout(timer);
      controller?.abort();
    };
    const programar = () => {
      cancelar();
      if (!composing) timer = setTimeout(buscar, 350);
    };
    input.addEventListener('input', programar);
    input.addEventListener('compositionstart', () => { composing = true; cancelar(); });
    input.addEventListener('compositionend', () => { composing = false; programar(); });
    form.addEventListener('submit', event => {
      event.preventDefault();
      cancelar();
      if (!composing) buscar();
    });
    try {
      const saved = JSON.parse(sessionStorage.getItem(key));
      if (saved && saved.path === location.pathname && saved.value.trim() === input.value) {
        input.focus({preventScroll: true});
        input.setSelectionRange(saved.cursor, saved.cursor);
        sessionStorage.removeItem(key);
      }
    } catch (_) {}
  });

  document.addEventListener('change', event => {
    const select = event.target;
    if (select.matches('select[data-auto-enviar]') && select.form) {
      // La búsqueda en vivo cambia «q» sin recargar: se toma la vigente de la dirección.
      const q = select.form.elements.namedItem('q');
      if (q && q.type === 'hidden') q.value = new URLSearchParams(location.search).get('q') || '';
      select.form.requestSubmit();
      return;
    }
    if (!select.matches('select[name="per_page"]')) return;
    const page = select.form.elements.namedItem('page');
    if (page) page.value = '1';
    select.form.requestSubmit();
  });
})();
