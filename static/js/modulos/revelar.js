/* Aparición suave de bloques [data-revelar] al entrar en pantalla */
export function iniciarRevelar(prefs) {
    const elementos = document.querySelectorAll("[data-revelar]");
    if (!elementos.length) return;
    if (prefs.movimientoReducido || !("IntersectionObserver" in window)) {
        elementos.forEach((el) => el.classList.add("is-visible"));
        return;
    }
    const io = new IntersectionObserver((entradas) => {
        entradas.forEach((en) => {
            if (!en.isIntersecting) return;
            en.target.classList.add("is-visible");
            io.unobserve(en.target);
        });
    }, { threshold: 0.12, rootMargin: "0px 0px -30px 0px" });
    elementos.forEach((el) => io.observe(el));
}
