/* Parallax de scroll suave para imágenes de fondo [data-parallax="0.15"]
   (la imagen se mueve más lento que el contenido). */
import { limitar } from "./preferencias.js";

export function iniciarParallax() {
    const capas = Array.from(document.querySelectorAll("[data-parallax], .hero-panel .e3d-capa--foto-faro"));
    if (!capas.length) return;
    let pendiente = false;
    const render = () => {
        pendiente = false;
        const vh = window.innerHeight || 1;
        capas.forEach((el) => {
            const r = (el.parentElement || el).getBoundingClientRect();
            if (r.bottom < 0 || r.top > vh) return;
            const factor = parseFloat(el.dataset.parallax || "0.12");
            const centro = r.top + r.height / 2 - vh / 2;
            const y = limitar(-centro * factor, -r.height * 0.05, r.height * 0.05);
            el.style.setProperty("--parallax-y", y.toFixed(1) + "px");
        });
    };
    const pedir = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(render); } };
    window.addEventListener("scroll", pedir, { passive: true });
    window.addEventListener("resize", pedir, { passive: true });
    pedir();
}
