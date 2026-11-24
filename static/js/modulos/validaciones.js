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

/* Tolerante al tipeo, igual que rut_canonico() en Python: puntos, espacios, guion opcional, «k» minúscula. */
export function rutCanonico(rut) {
    const limpio = (rut || "").replace(/[.\s-]/g, "").toUpperCase();
    if (!/^\d{7,8}[\dK]$/.test(limpio)) return null;
    const cuerpo = limpio.slice(0, -1);
    const dv = limpio.slice(-1);
    return dvRut(cuerpo) === dv ? `${cuerpo}-${dv}` : null;
}

export function validarRut(rut) {
    return rutCanonico(rut) !== null;
}

/* Motivo del rechazo; mismo texto que motivo_rut_invalido() en Python. */
export function motivoRut(rut) {
    const texto = (rut || "").trim();
    if (!texto) return "Ingrese el RUT; el campo está vacío.";
    if (rutCanonico(texto)) return "";
    const limpio = texto.replace(/[.\s-]/g, "").toUpperCase();
    if (/^\d{7,8}[\dK]$/.test(limpio)) {
        const cuerpo = limpio.slice(0, -1);
        return `El dígito verificador no corresponde: con ese número el RUT correcto sería ${formatearRut(`${cuerpo}-${dvRut(cuerpo)}`)}.`;
    }
    return "El RUT tiene un formato inválido. Use 7 u 8 dígitos y el verificador, por ejemplo 33.100.001-9.";
}

export function formatearRut(rut) {
    const normal = rutCanonico(rut) || normalizarRut(rut);
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
            input.setCustomValidity(motivoRut(valor));
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
                input.setCustomValidity(ok ? "" : motivoRut(valor));
                if (ok) input.value = formatearRut(valor);
                return !ok;
            });
            if (malos.length) {
                ev.preventDefault();
                avisar("Revise los datos ingresados", motivoRut(malos[0].value) || "El RUT no es válido.");
                malos[0].focus();
            }
        });
    });
}

if (typeof document !== "undefined") {
    iniciarValidacionRut();
}
