(() => {
  let tarjeta;
  let ocupado = false;
  let resaltado;

  const limpiar = () => {
    resaltado?.classList.remove('siged-destino-activo');
    resaltado = null;
    tarjeta?.classList.remove('siged-arrastrando');
    tarjeta = null;
  };
  const aviso = (texto, error = false) => {
    const node = document.querySelector('[data-movimiento-aviso]');
    if (!node) return;
    node.classList.toggle('text-danger', error);
    node.textContent = texto;
  };
  const actualizarVista = async destino => {
    const url = new URL(destino, location.href);
    const partes = [...document.querySelectorAll('[data-resultado]')];
    const periodo = document.querySelector('[data-periodo-agenda]');
    const cambioDeMes = periodo && ['anio', 'mes'].some(campo =>
      url.searchParams.get(campo) !== periodo.elements.namedItem(campo).value);
    if (!partes.length || url.pathname !== location.pathname || cambioDeMes) {
      location.assign(url);
      return;
    }
    const response = await fetch(url, {cache: 'no-store', credentials: 'same-origin'});
    if (!response.ok || response.redirected) throw new Error('El cambio se guardó. Recargue para ver el resultado.');
    const html = new DOMParser().parseFromString(await response.text(), 'text/html');
    const nuevas = new Map([...html.querySelectorAll('[data-resultado]')].map(node => [node.dataset.resultado, node]));
    if (partes.some(node => !nuevas.has(node.dataset.resultado))) {
      throw new Error('El cambio se guardó. Recargue para ver el resultado.');
    }
    partes.forEach(node => node.replaceWith(nuevas.get(node.dataset.resultado)));
    history.replaceState(history.state, '', url);
  };
  const mover = async (form, campo, valor) => {
    if (ocupado) return;
    ocupado = true;
    aviso('Guardando…');
    const datos = new FormData(form);
    datos.set(campo, valor);
    const url = campo === 'estado' ? location.href : form.action;
    const id = datos.get('id_compromiso') || form.action;
    const enfocado = form.contains(document.activeElement);
    let guardado = false;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(url, {method: 'POST', body: datos, signal: controller.signal,
        credentials: 'same-origin', headers: {Accept: 'application/json'}});
      const json = response.headers.get('Content-Type')?.includes('application/json') ? await response.json() : {};
      if (!response.ok || !json.destino) throw new Error(json.error || 'No se pudo guardar. Recargue la página e inténtelo de nuevo.');
      guardado = true;
      await actualizarVista(json.destino);
      aviso(json.mensaje || 'Cambio guardado.');
      if (enfocado) {
        const nuevoForm = [...document.querySelectorAll('[data-form-mover]')].find(node =>
          (node.elements.namedItem('id_compromiso')?.value || node.action) === id);
        const control = nuevoForm?.elements.namedItem(campo);
        if (control) {
          const detalles = control.closest('details');
          if (detalles) detalles.open = true;
          control.focus({preventScroll: true});
        }
      }
    } catch (error) {
      aviso(guardado ? 'El cambio se guardó. Recargue para ver el resultado.' :
        error instanceof TypeError || error.name === 'AbortError'
          ? 'Se interrumpió la conexión. Recargue para comprobar si se guardó.'
          : error.message, true);
    } finally {
      clearTimeout(timeout);
      ocupado = false;
    }
  };

  const destino = target => tarjeta && target.closest(`[data-destino-${tarjeta.dataset.mover}]`);
  document.addEventListener('dragstart', event => {
    const elemento = event.target.closest('[draggable="true"][data-mover]');
    if (!elemento) return;
    if (ocupado || event.target.closest('form, a, summary, button')) {
      event.preventDefault();
      return;
    }
    tarjeta = elemento;
    tarjeta.classList.add('siged-arrastrando');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', 'siged');
  });
  document.addEventListener('dragover', event => {
    const zona = destino(event.target);
    if (zona !== resaltado) {
      resaltado?.classList.remove('siged-destino-activo');
      resaltado = zona;
      resaltado?.classList.add('siged-destino-activo');
    }
    if (!zona) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  });
  document.addEventListener('drop', event => {
    const zona = destino(event.target);
    if (!zona) return;
    event.preventDefault();
    const campo = tarjeta.dataset.mover;
    const valor = zona.getAttribute(`data-destino-${campo}`);
    const form = tarjeta.querySelector('[data-form-mover]');
    limpiar();
    if (form && valor && valor !== form.elements.namedItem(`${campo}_anterior`).value) mover(form, campo, valor);
  });
  document.addEventListener('dragend', limpiar);
  document.addEventListener('submit', event => {
    const form = event.target.closest('[data-form-mover]');
    if (!form) return;
    event.preventDefault();
    const campo = form.elements.namedItem('estado') ? 'estado' : 'fecha';
    mover(form, campo, form.elements.namedItem(campo).value);
  });

  document.addEventListener('click', async event => {
    const copiar = event.target.closest('[data-copiar]');
    if (copiar) {
      try {
        await navigator.clipboard.writeText(copiar.dataset.copiar);
        copiar.textContent = 'Enlace copiado';
      } catch (_) {
        copiar.previousElementSibling.select();
      }
      return;
    }
  });
})();
