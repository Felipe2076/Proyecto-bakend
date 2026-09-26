/* Inclinación 3D sutil (máx. 3°) con sombra dinámica. Sólo mouse/lápiz. */
import { lerp, limitar } from "./preferencias.js";

const SELECTOR = ".e3d-tilt, .kpi-card, .flow-card";
const MAX_GRADOS = 3;

export function iniciarTilt() {
    const activos = new Set();
    let corriendo = false;

    const paso = () => {
        activos.forEach((el) => {
            const s = el.__tilt;
            s.x = lerp(s.x, s.tx, 0.15);
            s.y = lerp(s.y, s.ty, 0.15);
            s.l = lerp(s.l, s.tl, 0.12);
            el.style.setProperty("--e3d-tx", s.x.toFixed(4));
            el.style.setProperty("--e3d-ty", s.y.toFixed(4));
            el.style.setProperty("--e3d-lift", s.l.toFixed(4));
            if (Math.abs(s.x - s.tx) + Math.abs(s.y - s.ty) + Math.abs(s.l - s.tl) < 0.003) activos.delete(el);
        });
        if (activos.size) requestAnimationFrame(paso); else corriendo = false;
    };
    const activar = (el) => {
        activos.add(el);
        if (!corriendo) { corriendo = true; requestAnimationFrame(paso); }
    };

    document.querySelectorAll(SELECTOR).forEach((el) => {
        const max = limitar(parseFloat(el.dataset.tiltMax || "") || MAX_GRADOS, 0, MAX_GRADOS);
        el.__tilt = { x: 0, y: 0, l: 0, tx: 0, ty: 0, tl: 0 };
        el.classList.add("e3d-tilt-on");
        el.style.setProperty("--e3d-max", String(max));
        el.addEventListener("pointermove", (ev) => {
            if (ev.pointerType === "touch") return;
            const r = el.getBoundingClientRect();
            el.__tilt.tx = (limitar((ev.clientX - r.left) / r.width, 0, 1) - 0.5) * 2;
            el.__tilt.ty = (limitar((ev.clientY - r.top) / r.height, 0, 1) - 0.5) * 2;
            el.__tilt.tl = 1;
            activar(el);
        });
        el.addEventListener("pointerleave", () => {
            Object.assign(el.__tilt, { tx: 0, ty: 0, tl: 0 });
            activar(el);
        });
    });
}
