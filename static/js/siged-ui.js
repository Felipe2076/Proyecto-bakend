/* siged-ui.js — comportamiento común de las pantallas internas (sin dependencias).
 *
 * - Validación única de formularios: marca campos, resume errores arriba y enfoca el primero.
 * - Máscaras: RUT (data-regla="rut") y celular chileno (data-regla="telefono").
 * - Confirmación antes de acciones delicadas (form[data-confirmar]).
 * - Vista previa de imágenes antes de subir (input[data-vista-previa]).
 * - Menú lateral en móvil: fondo, Escape y aria-expanded.
 *
 * El módulo 11 es el mismo de core/validaciones.py.
 */
(() => {
    "use strict";

    /* ---------- RUT ---------- */
    const dvRut = (cuerpo) => {
        let suma = 0;
        let factor = 2;
        for (let i = cuerpo.length - 1; i >= 0; i -= 1) {
            suma += Number(cuerpo[i]) * factor;
            factor = factor === 7 ? 2 : factor + 1;
        }
        const resto = 11 - (suma % 11);
        return resto === 11 ? "0" : resto === 10 ? "K" : String(resto);
    };
    const rutCanonico = (rut) => {
        const limpio = (rut || "").replace(/[.\s-]/g, "").toUpperCase();
        if (!/^\d{7,8}[\dK]$/.test(limpio)) return null;
        const cuerpo = limpio.slice(0, -1);
        return dvRut(cuerpo) === limpio.slice(-1) ? `${cuerpo}-${limpio.slice(-1)}` : null;
    };
    const formatearRut = (canonico) => {
        const [cuerpo, dv] = canonico.split("-");
        return `${cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".")}-${dv}`;
    };
    const motivoRut = (rut) => {
        const limpio = (rut || "").replace(/[.\s-]/g, "").toUpperCase();
        if (/^\d{7,8}[\dK]$/.test(limpio)) {
            const cuerpo = limpio.slice(0, -1);
            return `El dígito verificador no corresponde: con ese número sería ${formatearRut(`${cuerpo}-${dvRut(cuerpo)}`)}.`;
        }
        return "Formato inválido. Use 7 u 8 dígitos y el verificador, por ejemplo 12.345.678-5.";
    };

    /* ---------- Celular chileno ---------- */
    const digitosTelefono = (valor) => {
        let d = (valor || "").replace(/\D/g, "");
        if (d.startsWith("56")) d = d.slice(2);
        return d;
    };
    const formatearTelefono = (d) => `+56 9 ${d.slice(1, 5)} ${d.slice(5, 9)}`;

    const marcar = (input, mensaje) => {
        input.setCustomValidity(mensaje || "");
        input.classList.toggle("is-invalid", Boolean(mensaje));
        const ayuda = input.parentElement && input.parentElement.querySelector(".invalid-feedback");
        if (ayuda && mensaje) ayuda.textContent = mensaje;
    };

    const revisarRut = (input) => {
        const valor = input.value.trim();
        if (!valor) {
            marcar(input, input.required ? "Ingrese el RUT." : "");
            return;
        }
        const canonico = rutCanonico(valor);
        if (canonico) {
            input.value = formatearRut(canonico);
            marcar(input, "");
        } else {
            marcar(input, motivoRut(valor));
        }
    };

    const revisarTelefono = (input) => {
        const valor = input.value.trim();
        if (!valor) {
            marcar(input, input.required ? "Ingrese un celular." : "");
            return;
        }
        const d = digitosTelefono(valor);
        if (/^9\d{8}$/.test(d)) {
            input.value = formatearTelefono(d);
            marcar(input, "");
        } else {
            marcar(input, "Ingrese un celular chileno de 9 dígitos, por ejemplo +56 9 1234 5678.");
        }
    };

    document.querySelectorAll("[data-regla='rut']").forEach((input) => {
        input.addEventListener("blur", () => revisarRut(input));
        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9kK.\-\s]/g, "");
            if (input.classList.contains("is-invalid") && rutCanonico(input.value)) marcar(input, "");
        });
    });
    document.querySelectorAll("[data-regla='telefono']").forEach((input) => {
        input.addEventListener("blur", () => revisarTelefono(input));
        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9+\s-]/g, "");
        });
    });

    /* RUT con aviso (directiva de organizaciones): un RUT válido se formatea; uno con
       dígito verificador incorrecto NO bloquea el guardado, solo muestra la advertencia. */
    document.querySelectorAll("[data-regla='rut-aviso']").forEach((input) => {
        const aviso = input.parentElement && input.parentElement.querySelector("[data-aviso-rut]");
        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9kK.\-\s]/g, "");
        });
        input.addEventListener("blur", () => {
            const valor = input.value.trim();
            const canonico = valor ? rutCanonico(valor) : null;
            if (canonico) input.value = formatearRut(canonico);
            if (aviso) {
                aviso.hidden = !valor || Boolean(canonico);
                aviso.textContent = valor && !canonico ? `Atención: ${motivoRut(valor)} Se guardará tal cual.` : "";
            }
        });
    });

    /* Teléfono chileno, celular o fijo: se normaliza a +56 9 1234 5678 o +56 51 234 5678. */
    document.querySelectorAll("[data-regla='telefono-libre']").forEach((input) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9+\s-]/g, "");
        });
        input.addEventListener("blur", () => {
            const d = digitosTelefono(input.value);
            if (!input.value.trim()) {
                marcar(input, "");
            } else if (/^9\d{8}$/.test(d)) {
                input.value = formatearTelefono(d);
                marcar(input, "");
            } else if (/^[2-7]\d{8}$/.test(d)) {
                input.value = `+56 ${d.slice(0, 2)} ${d.slice(2, 5)} ${d.slice(5)}`;
                marcar(input, "");
            } else {
                marcar(input, "Ingrese un teléfono chileno de 9 dígitos. Ej.: +56 9 1234 5678.");
            }
        });
    });

    /* ---------- Buscador de organizaciones (agenda) ---------- */
    document.querySelectorAll("select[data-buscar-url]").forEach((select) => {
        const caja = document.createElement("div");
        caja.className = "position-relative";
        const entrada = document.createElement("input");
        entrada.type = "search";
        entrada.className = "form-control";
        entrada.placeholder = "Escriba al menos 2 letras del nombre, código o territorio…";
        entrada.setAttribute("autocomplete", "off");
        entrada.setAttribute("role", "combobox");
        entrada.setAttribute("aria-expanded", "false");
        entrada.setAttribute("aria-label", "Buscar organización");
        const lista = document.createElement("div");
        lista.className = "list-group position-absolute w-100 shadow-sm";
        lista.style.zIndex = "1050";
        lista.setAttribute("role", "listbox");
        const elegida = select.options[select.selectedIndex];
        if (elegida && elegida.value) entrada.value = elegida.text;
        select.hidden = true;
        select.after(caja);
        caja.append(entrada, lista);
        let temporizador = 0;
        let pedido;
        const cerrar = () => { lista.replaceChildren(); entrada.setAttribute("aria-expanded", "false"); };
        const elegir = (id, texto) => {
            let opcion = [...select.options].find((o) => o.value === String(id));
            if (!opcion) { opcion = new Option(texto, id); select.add(opcion); }
            select.value = String(id);
            entrada.value = id ? texto : "";
            select.dispatchEvent(new Event("change", { bubbles: true }));
            cerrar();
        };
        entrada.addEventListener("input", () => {
            window.clearTimeout(temporizador);
            if (!entrada.value.trim()) { elegir("", ""); return; }
            temporizador = window.setTimeout(async () => {
                const texto = entrada.value.trim();
                if (texto.length < 2) { cerrar(); return; }
                pedido?.abort();
                pedido = new AbortController();
                const url = new URL(select.dataset.buscarUrl, location.href);
                url.searchParams.set("q", texto);
                try {
                    const r = await fetch(url, { headers: { Accept: "application/json" }, signal: pedido.signal });
                    const { resultados = [] } = await r.json();
                    lista.replaceChildren(...(resultados.length ? resultados.map((o) => {
                        const b = document.createElement("button");
                        b.type = "button";
                        b.className = "list-group-item list-group-item-action";
                        b.setAttribute("role", "option");
                        b.innerHTML = `<span class="fw-semibold"></span><small class="d-block text-muted"></small>`;
                        b.firstChild.textContent = o.texto;
                        b.lastChild.textContent = o.detalle;
                        b.addEventListener("click", () => elegir(o.id, o.texto));
                        return b;
                    }) : [Object.assign(document.createElement("div"), {
                        className: "list-group-item text-muted small", textContent: "Sin coincidencias activas." })]));
                    entrada.setAttribute("aria-expanded", "true");
                } catch (e) { if (e.name !== "AbortError") cerrar(); }
            }, 250);
        });
        entrada.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrar(); });
        document.addEventListener("click", (e) => { if (!caja.contains(e.target)) cerrar(); });
    });

    /* ---------- Validación de formularios ---------- */
    const etiquetaDe = (campo) => {
        const label = campo.id && document.querySelector(`label[for="${campo.id}"]`);
        const texto = label ? label.textContent : campo.name;
        return (texto || "Campo").replace(/\*/g, "").replace(/\(.*?\)/g, "").trim();
    };

    const resumen = (form, invalidos) => {
        let caja = form.querySelector(".siged-resumen-errores");
        if (!invalidos.length) {
            if (caja) caja.remove();
            return;
        }
        if (!caja) {
            caja = document.createElement("div");
            caja.className = "alert alert-danger siged-resumen-errores";
            caja.setAttribute("role", "alert");
            caja.tabIndex = -1;
            form.prepend(caja);
        }
        const items = invalidos.slice(0, 8).map((campo) => {
            const motivo = campo.validationMessage || "Revise este campo.";
            return `<li><a href="#${campo.id}" class="alert-link">${etiquetaDe(campo)}</a>: ${motivo}</li>`;
        });
        caja.innerHTML = `<strong>No se pudo guardar. Revise ${invalidos.length === 1 ? "este campo" : `estos ${invalidos.length} campos`}:</strong><ul class="mb-0 mt-1">${items.join("")}</ul>`;
    };

    document.querySelectorAll("form").forEach((form) => {
        if (form.method.toLowerCase() !== "post" && !form.classList.contains("needs-validation")) return;
        form.setAttribute("novalidate", "");
        form.addEventListener("submit", (event) => {
            form.querySelectorAll("[data-regla='rut']").forEach(revisarRut);
            form.querySelectorAll("[data-regla='telefono']").forEach(revisarTelefono);
            form.querySelectorAll("[data-regla='telefono-libre'], [data-regla='rut-aviso']").forEach((el) => el.dispatchEvent(new Event("blur")));
            const invalidos = [...form.elements].filter((el) => el.willValidate && !el.checkValidity());
            if (invalidos.length) {
                event.preventDefault();
                event.stopImmediatePropagation();
                form.classList.add("was-validated");
                invalidos.forEach((el) => el.classList.add("is-invalid"));
                resumen(form, invalidos);
                invalidos[0].focus();
                return;
            }
            resumen(form, []);
            const pregunta = form.getAttribute("data-confirmar");
            if (pregunta && !window.confirm(pregunta)) {
                event.preventDefault();
                event.stopImmediatePropagation();
                return;
            }
            // Evita el doble envío por doble clic.
            const boton = event.submitter;
            if (boton && !form.hasAttribute("data-sin-bloqueo")) {
                window.setTimeout(() => { boton.disabled = true; }, 0);
                window.setTimeout(() => { boton.disabled = false; }, 8000);
            }
        }, true);
        form.addEventListener("input", (event) => {
            const el = event.target;
            if (el.classList && el.classList.contains("is-invalid") && el.checkValidity()) {
                el.classList.remove("is-invalid");
            }
        });
    });

    /* ---------- Vista previa de imagen ---------- */
    document.querySelectorAll("input[type='file'][data-vista-previa]").forEach((input) => {
        const destino = document.getElementById(input.getAttribute("data-vista-previa"));
        const maxMb = Number(input.getAttribute("data-max-mb") || 5);
        input.addEventListener("change", () => {
            const archivo = input.files && input.files[0];
            marcar(input, "");
            if (!archivo) return;
            if (!/^image\/(jpeg|png|webp)$/.test(archivo.type)) {
                marcar(input, "Use una imagen JPG, PNG o WebP.");
                input.value = "";
                return;
            }
            if (archivo.size > maxMb * 1024 * 1024) {
                marcar(input, `La imagen pesa ${(archivo.size / 1048576).toFixed(1)} MB; el máximo es ${maxMb} MB.`);
                input.value = "";
                return;
            }
            if (destino) {
                const url = URL.createObjectURL(archivo);
                destino.src = url;
                destino.hidden = false;
                destino.onload = () => URL.revokeObjectURL(url);
                const iniciales = document.getElementById(`${input.getAttribute("data-vista-previa")}-iniciales`);
                if (iniciales) iniciales.hidden = true;
            }
        });
    });

    /* ---------- Menú lateral en móvil ---------- */
    const sidebar = document.getElementById("sigedSidebar");
    const toggle = document.querySelector("[data-siged-toggle]");
    if (sidebar && toggle) {
        const fondo = document.createElement("div");
        fondo.className = "siged-sidebar-fondo";
        document.body.appendChild(fondo);
        const abrir = (si) => {
            sidebar.classList.toggle("is-open", si);
            fondo.classList.toggle("is-visible", si);
            toggle.setAttribute("aria-expanded", si ? "true" : "false");
        };
        toggle.setAttribute("aria-controls", "sigedSidebar");
        toggle.setAttribute("aria-expanded", "false");
        toggle.addEventListener("click", () => abrir(!sidebar.classList.contains("is-open")));
        fondo.addEventListener("click", () => abrir(false));
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
                abrir(false);
                toggle.focus();
            }
        });
    }
})();
