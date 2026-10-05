/* Validación de RUT (mismo módulo 11 que core/validaciones.py) y aviso antes de enviar. */
const PATRON_RUT = /^(\d{1,2}(\.\d{3}){2}|\d{7,8})-[\dkK]$/;

export function dvRut(cuerpo) {
    let suma = 0;
    let factor = 2;
    for (let i = cuerpo.length - 1; i >= 0; i -= 1) {
        suma += Number(cuerpo[i]) * factor;
        factor = factor === 7 ? 2 : factor + 1;
    }
    const resto = 11 - (suma % 11);
    if (resto === 11) return "0";
    if (resto === 10) return "K";
    return String(resto);
}

export function normalizarRut(rut) {
    return (rut || "").trim().replace(/\./g, "").replace(/\s/g, "").toUpperCase();
}

export function validarRut(rut) {
    const texto = (rut || "").trim();
    if (!PATRON_RUT.test(texto)) return false;
    const [cuerpo, dv] = normalizarRut(texto).split("-");
    return dvRut(cuerpo) === dv;
}

export function formatearRut(rut) {
    const normal = normalizarRut(rut);
    if (!validarRut(normal) && !/^\d{7,8}-[\dkK]$/.test(normal)) {
        return (rut || "").trim();
    }
    const [cuerpo, dv] = normal.split("-");
    if (!cuerpo || !dv) return (rut || "").trim();
    let resto = cuerpo;
    const grupos = [];
    while (resto) {
        grupos.push(resto.slice(-3));
        resto = resto.slice(0, -3);
    }
    return `${grupos.reverse().join(".")}-${dv}`;
}

function avisar(titulo, texto) {
    if (window.Swal && typeof window.Swal.fire === "function") {
        window.Swal.fire({
            icon: "error",
            title: titulo,
            text: texto,
            confirmButtonText: "Entendido",
        });
        return;
    }
    window.alert(`${titulo}\n${texto}`);
}

function enlazarRut(input) {
    input.addEventListener("blur", () => {
        const valor = input.value.trim();
        if (!valor) return;
        if (validarRut(valor)) {
            input.value = formatearRut(valor);
            input.classList.remove("is-invalid");
            input.setCustomValidity("");
        } else {
            input.classList.add("is-invalid");
            input.setCustomValidity(input.dataset.mensaje || "Ingrese un RUT válido, por ejemplo 33.100.001-9.");
        }
    });
}

export function iniciarValidacionRut() {
    document.querySelectorAll("[data-regla='rut']").forEach(enlazarRut);
    document.querySelectorAll("form[data-validar]").forEach((form) => {
        form.addEventListener("submit", (ev) => {
            const malos = [...form.querySelectorAll("[data-regla='rut']")].filter((input) => {
                const valor = input.value.trim();
                const ok = valor && validarRut(valor);
                input.classList.toggle("is-invalid", !ok);
                input.setCustomValidity(ok ? "" : (input.dataset.mensaje || "RUT inválido"));
                if (ok) input.value = formatearRut(valor);
                return !ok;
            });
            if (malos.length) {
                ev.preventDefault();
                avisar("Revise los datos ingresados", malos[0].dataset.mensaje || "El RUT no es válido.");
                malos[0].focus();
            }
        });
    });
}

if (typeof document !== "undefined") {
    iniciarValidacionRut();
}
