/* Validación Bootstrap para formularios .needs-validation de las páginas públicas
   (base.html ya trae su propio script; aquí sólo actúa en body.v3-publico). */
export function iniciarValidacion() {
    if (!document.body.classList.contains("v3-publico")) return;
    document.querySelectorAll(".needs-validation").forEach((form) => {
        form.addEventListener("submit", (ev) => {
            if (!form.checkValidity()) {
                ev.preventDefault();
                ev.stopPropagation();
            }
            form.classList.add("was-validated");
        });
    });
}
