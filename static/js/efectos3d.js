/* efectos3d.js — tilt 3D, brillo y parallax para SIGED-SGR (vanilla, sin CDN).
 * - Tilt: tarjetas rotan hasta --e3d-max grados siguiendo el cursor (rAF + lerp).
 * - Brillo: radial-gradient que sigue al cursor (variables --e3d-gx/--e3d-gy).
 * - Parallax: capas [data-e3d-depth] se desplazan con el mouse y el scroll;
 *   las capas de fondo (depth bajo) se mueven más lento que el contenido.
 * Se desactiva con prefers-reduced-motion y en dispositivos táctiles (sin hover).
 */
(() => {
    "use strict";
    const root = document.documentElement;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    root.classList.add("e3d-js");
    if (reduce) { root.classList.add("e3d-reduced"); return; }
    if (fine) root.classList.add("e3d-fine");

    const lerp = (a, b, t) => a + (b - a) * t;
    const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

    /* ---------------- Tilt + brillo ---------------- */
    // Tarjetas pequeñas que siempre rotan.
    const TILT_SEL = ".e3d-tilt, .kpi-card, .flow-card, .hero-glass";
    // Tarjetas genéricas: rotan poco sólo si no contienen tablas/formularios/modales.
    const GENERIC_SEL = ".siged-content .card, .login-glass";
    const HEAVY_SEL = "table, form, .modal, .dropdown, select, textarea, .kanban-cards-container, iframe";

    const items = new Set();
    let loopActivo = false;

    function prepararTilt(el, max) {
        if (el.__e3d) return;
        el.__e3d = { tx: 0, ty: 0, lift: 0, glare: 0, ttx: 0, tty: 0, tlift: 0, tglare: 0, gx: 50, gy: 0, tilt: max > 0 };
        el.classList.add("e3d-glare-on");
        if (max > 0) {
            el.classList.add("e3d-tilt-on");
            el.style.setProperty("--e3d-max", String(max));
        }
        el.addEventListener("pointermove", (ev) => {
            if (ev.pointerType && ev.pointerType !== "mouse" && ev.pointerType !== "pen") return;
            const r = el.getBoundingClientRect();
            const nx = clamp((ev.clientX - r.left) / r.width, 0, 1);
            const ny = clamp((ev.clientY - r.top) / r.height, 0, 1);
            const s = el.__e3d;
            s.ttx = (nx - 0.5) * 2;
            s.tty = (ny - 0.5) * 2;
            s.tlift = 1;
            s.tglare = 1;
            s.gx = nx * 100;
            s.gy = ny * 100;
            activar(el);
        });
        el.addEventListener("pointerleave", () => {
            const s = el.__e3d;
            s.ttx = 0; s.tty = 0; s.tlift = 0; s.tglare = 0;
            activar(el);
        });
    }

    function activar(el) {
        items.add(el);
        if (!loopActivo) { loopActivo = true; requestAnimationFrame(paso); }
    }

    function paso() {
        items.forEach((el) => {
            const s = el.__e3d;
            s.tx = lerp(s.tx, s.ttx, 0.14);
            s.ty = lerp(s.ty, s.tty, 0.14);
            s.lift = lerp(s.lift, s.tlift, 0.12);
            s.glare = lerp(s.glare, s.tglare, 0.18);
            if (s.tilt) {
                el.style.setProperty("--e3d-tx", s.tx.toFixed(4));
                el.style.setProperty("--e3d-ty", s.ty.toFixed(4));
                el.style.setProperty("--e3d-lift", s.lift.toFixed(4));
            }
            el.style.setProperty("--e3d-glare", (s.glare * 0.9).toFixed(3));
            el.style.setProperty("--e3d-gx", s.gx.toFixed(1));
            el.style.setProperty("--e3d-gy", s.gy.toFixed(1));
            const quieto = Math.abs(s.tx - s.ttx) < 0.002 && Math.abs(s.ty - s.tty) < 0.002 &&
                Math.abs(s.lift - s.tlift) < 0.002 && Math.abs(s.glare - s.tglare) < 0.002;
            if (quieto) items.delete(el);
        });
        if (items.size) requestAnimationFrame(paso); else loopActivo = false;
    }

    if (fine) {
        document.querySelectorAll(TILT_SEL).forEach((el) => {
            const max = parseFloat(el.dataset.tiltMax || "") || 8;
            prepararTilt(el, clamp(max, 0, 8));
        });
        document.querySelectorAll(GENERIC_SEL).forEach((el) => {
            if (el.__e3d) return;
            const pesada = el.querySelector(HEAVY_SEL) || el.matches("form") || el.offsetHeight > 420;
            prepararTilt(el, pesada ? 0 : 3);
        });
    }

    /* ---------------- Parallax por capas ---------------- */
    const escenas = Array.from(document.querySelectorAll(".e3d-escena"));
    if (!escenas.length) return;
    const capas = [];
    escenas.forEach((esc) => {
        esc.querySelectorAll("[data-e3d-depth]").forEach((capa) => {
            capas.push({ el: capa, esc, depth: parseFloat(capa.dataset.e3dDepth) || 0.2, px: 0, py: 0, sy: 0 });
        });
    });
    if (!capas.length) return;

    let mx = 0, my = 0;            // cursor normalizado -1..1 respecto al viewport
    let pendiente = false;
    const MOUSE_PX = 28;           // desplazamiento máx. por mouse (depth = 1)
    const SCROLL_F = 0.35;         // fracción de desplazamiento por scroll

    function pedirFrame() {
        if (!pendiente) { pendiente = true; requestAnimationFrame(render); }
    }

    function render() {
        pendiente = false;
        const vh = window.innerHeight || 1;
        let seguir = false;
        capas.forEach((c) => {
            const r = c.esc.getBoundingClientRect();
            if (r.bottom < -50 || r.top > vh + 50) return;   // fuera de pantalla
            // Scroll: capa de fondo se desplaza en sentido contrario → se mueve más lento.
            const centro = r.top + r.height / 2 - vh / 2;
            const tsy = clamp(-centro * SCROLL_F * c.depth, -r.height * 0.07, r.height * 0.07);
            const tpx = fine ? -mx * MOUSE_PX * c.depth : 0;
            const tpy = fine ? -my * MOUSE_PX * c.depth : 0;
            c.px = lerp(c.px, tpx, 0.08);
            c.py = lerp(c.py, tpy, 0.08);
            c.sy = lerp(c.sy, tsy, 0.25);
            c.el.style.setProperty("--e3d-px", c.px.toFixed(2));
            c.el.style.setProperty("--e3d-py", c.py.toFixed(2));
            c.el.style.setProperty("--e3d-sy", c.sy.toFixed(2));
            if (Math.abs(c.px - tpx) > 0.05 || Math.abs(c.py - tpy) > 0.05 || Math.abs(c.sy - tsy) > 0.05) seguir = true;
        });
        if (seguir) pedirFrame();
    }

    if (fine) {
        window.addEventListener("pointermove", (ev) => {
            if (ev.pointerType && ev.pointerType !== "mouse" && ev.pointerType !== "pen") return;
            mx = (ev.clientX / window.innerWidth - 0.5) * 2;
            my = (ev.clientY / window.innerHeight - 0.5) * 2;
            pedirFrame();
        }, { passive: true });
    }
    window.addEventListener("scroll", pedirFrame, { passive: true });
    window.addEventListener("resize", pedirFrame, { passive: true });
    pedirFrame();
})();
