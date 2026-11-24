/* Territorios según la delegación elegida.
 * Conserva siempre el territorio guardado («registro anterior») y la elección previa
 * si vuelve a estar disponible, para que corregir la delegación no borre el dato. */
(() => {
  const territorio = document.querySelector('[data-territorios-url]');
  const delegacion = territorio?.form.elements.namedItem('delegacion');
  if (!delegacion) return;
  const guardado = (territorio.dataset.actual || '').trim();
  let consulta;
  const opcionAnterior = () => guardado ? new Option(`${guardado} (registro anterior)`, guardado) : null;
  const poner = (texto, nombres = []) => {
    const elegido = territorio.value;
    territorio.replaceChildren(new Option(texto, ''));
    nombres.forEach((nombre) => territorio.add(new Option(nombre, nombre)));
    if (guardado && !nombres.includes(guardado)) territorio.add(opcionAnterior());
    const preferido = [elegido, guardado].find((v) => v && [...territorio.options].some((o) => o.value === v));
    territorio.value = preferido || '';
  };
  delegacion.addEventListener('change', async () => {
    consulta?.abort();
    if (!delegacion.value) {
      poner('Seleccione una delegación');
      return;
    }
    territorio.disabled = true;
    territorio.setAttribute('aria-busy', 'true');
    poner('Cargando territorios…');
    consulta = new AbortController();
    const signal = consulta.signal;
    const url = new URL(territorio.dataset.territoriosUrl, location.href);
    url.searchParams.set('delegacion', delegacion.value);
    try {
      const response = await fetch(url, {headers: {Accept: 'application/json'}, signal});
      const datos = await response.json().catch(() => ({}));
      if (!response.ok || response.redirected) throw new Error(datos.error || 'No se pudo cargar el catálogo');
      if (signal.aborted) return;
      const {territorios = []} = datos;
      poner(territorios.length ? 'Seleccione un territorio' : 'Esta delegación aún no tiene territorios', territorios);
    } catch (error) {
      if (error.name !== 'AbortError') poner(error.message || 'No se pudo cargar el catálogo');
    } finally {
      territorio.disabled = false;
      territorio.removeAttribute('aria-busy');
    }
  });
})();
