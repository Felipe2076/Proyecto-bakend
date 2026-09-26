/* Compatibilidad: plantillas antiguas cargaban efectos3d.js como script clásico.
   Carga el módulo real (app.js); los módulos ES se evalúan una sola vez. */
(() => {
    const actual = document.currentScript && document.currentScript.src;
    if (actual) import(new URL("app.js", actual).href);
})();
