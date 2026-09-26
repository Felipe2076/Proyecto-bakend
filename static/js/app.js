/* app.js — punto de entrada JS (módulo ES, sin dependencias ni CDN).
   Cada efecto vive en js/modulos/ y respeta prefers-reduced-motion. */
import { prefs } from "./modulos/preferencias.js";
import { iniciarHeader } from "./modulos/header.js";
import { iniciarRevelar } from "./modulos/revelar.js";
import { iniciarTilt } from "./modulos/tilt.js";
import { iniciarParallax } from "./modulos/parallax.js";
import { iniciarValidacion } from "./modulos/validacion.js";

const root = document.documentElement;
root.classList.add("js-listo");
if (prefs.punteroFino) root.classList.add("puntero-fino");

iniciarHeader();
iniciarValidacion();
iniciarRevelar(prefs);
if (!prefs.movimientoReducido) {
    if (prefs.punteroFino) iniciarTilt();
    iniciarParallax();
}
