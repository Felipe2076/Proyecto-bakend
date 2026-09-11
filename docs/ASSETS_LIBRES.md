# Assets libres — SIGED-SGR Delegaciones La Serena

Cero assets de pago. Si la licencia de un Lottie público no era clara, se usó un JSON **original** del equipo.

## Tipografía (SIL Open Font License)

| Fuente | Uso | Origen |
| --- | --- | --- |
| Fraunces | Títulos / display institucional | Google Fonts, OFL |
| Source Sans 3 | Cuerpo y formularios | Google Fonts, OFL |

## Lottie (self-hosted)

| Archivo | Qué es | Licencia |
| --- | --- | --- |
| `static/lottie/siged-ticket-loader.json` | Loader original: anillo + ficha de ticket | Autoría propia · Los watones PC |
| `static/js/lottie.min.js` | Reproductor lottie-web 5.12.2 | MIT (cdnjs) |

No se hotlinkeó LottieFiles Premium. El overlay aparece al navegar o al enviar un formulario válido. Respeta `prefers-reduced-motion`.

## Lordicon — solo *wired/outline* FREE

Player self-hosted: `static/js/lordicon.js` (paquete público `@lordicon/element`).

Íconos bajados a `static/lordicon/` (no PRO). Verificado en lordicon.com, **Plan type: FREE**:

| Archivo | Ícono oficial | Dónde se usa |
| --- | --- | --- |
| `56-document.json` | wired/outline 56 file-text | Tablero: listado/ficha y encuesta |
| `35-pencil.json` | wired/outline 35 pencil | Tablero: ingresar ticket |
| `19-magnifier.json` | wired/outline 19 magnifier | Tablero: actividad y evidencia |
| `21-avatar.json` | wired/outline 21 avatar | Tablero: compromisos y administración |
| `45-clock.json` | wired/outline 45 clock | Tablero: agenda colectiva |
| `18-location-pin.json` | wired/outline 18 location-pin | Tablero: las 6 delegaciones |
| `27-globe.json` | wired/outline 27 globe | Clima La Serena en el hero |

No se usaron íconos PRO documentados (p. ej. traffic-lights 927, calendar 28, building-office 3308, gráficos de barras). El menú lateral sigue con Bootstrap Icons (MIT) para no cargar 20 animaciones.

## Lenis

`https://cdn.jsdelivr.net/npm/lenis@1.1.20/` (CSS + JS). Scroll suave solo si el usuario no pidió menos movimiento.

## Motivos locales (autoría propia)

| Archivo | Idea |
| --- | --- |
| `static/img/marca-siged.svg` | Marca abstracta: faro + olas (no es el escudo municipal oficial) |
| `static/img/patron-costa.svg` | Atardecer costa / dunas / cielo de La Serena |
| `static/img/escudo_la_serena.svg` | Composición geométrica propia (faro + mar), no copia del escudo con copyright |
| `static/img/faro_monumental.svg` | Ilustración propia de costa y faro |
| `static/img/dashboard_analitica.svg` | Panel de indicadores propio, paleta roja |

Bootstrap 5.3 y Bootstrap Icons: MIT, ya empaquetados en `static/`.
