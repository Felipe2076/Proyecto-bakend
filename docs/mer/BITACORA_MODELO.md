# Bitácora del modelo (prioridad 1)

El dibujo del MER sigue pendiente del aporte gráfico (ramoncito). Esta nota registra solo el cambio de esquema aplicado en código y en scripts.

| Versión | Script | Cambio |
| --- | --- | --- |
| v1.12 | `V017` | `cuentas_funcionario` gana `rut`, `nombres`, `apellido_paterno`, `apellido_materno` (anulables) y `es_simulacion`. Índice por delegación y apellido. `requerimientos_vecino.es_simulacion`. |
| datos | `D003` | Identidades de simulación. No cambia columnas. |
| v1.13 | `V018` | `rut`, `nombres` y `apellido_paterno` obligatorios. Único `uq_funcionario_rut`. `CHECK` de formato en MySQL. `cuentas_usuario.funcionario_id` obligatorio (`ON DELETE` protege al funcionario). |
| v1.15 | `V019` | Tabla `codigo_un_uso`: hash HMAC (`codigo_hash` CHAR(64)), `usado_en`, `anulado_en`, vencimiento e intentos. Propósito `RECUPERAR_CLAVE`. `cuenta_vecino_id` queda anulable, sin llave foránea todavía. |

`nombre` en funcionario se conserva como texto compuesto, sin la marca `(ficticio)`. Esa marca se arma al mostrar a partir de `es_simulacion`. El identificador de acceso es `rut` normalizado (`33100001-9`), copiado a `auth_user.username`. La clave de simulación no se guarda en estos scripts: `D003` deja `!`.

Equivalente Django: `cuentas.0002_funcionario_rut`, `requerimientos.0002_vecino_es_simulacion`, `cuentas.0003_rut_obligatorio` (incluye el relleno de datos) y `cuentas.0004_codigo_un_uso` (tabla `codigo_un_uso`). `V023` del plan es EQ-41 y no entra aquí.
