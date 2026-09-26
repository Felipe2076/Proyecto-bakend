/* Sombra en la cabecera pública al hacer scroll */
export function iniciarHeader() {
    const header = document.querySelector(".v3-header");
    if (!header) return;
    const actualizar = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
    window.addEventListener("scroll", actualizar, { passive: true });
    actualizar();
}
