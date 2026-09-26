/* Preferencias del usuario/dispositivo */
export const prefs = {
    movimientoReducido: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    punteroFino: window.matchMedia("(hover: hover) and (pointer: fine)").matches,
};
export const lerp = (a, b, t) => a + (b - a) * t;
export const limitar = (v, min, max) => Math.min(max, Math.max(min, v));
