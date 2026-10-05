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

Corrección de `D003` y `V018`, sin número nuevo. En la bitácora del equipo el último dato ocupado es `D004` (EQ-47); `V023` sigue siendo EQ-41. No se reutilizan esos números. `D003` y `V018` se corrigen en su archivo porque en las bases que ya tienen filas (EC2 y WAMP) no llegaron a quedar aplicados: el `migrate` se cortó dentro de `0003` y el SQL solo nombraba vecinos 1 a 21. Un script posterior no arregla el que el equipo va a ejecutar en el ensayo.

`D003` sigue asignando `FUN-001`…`FUN-032` por código. Cualquier otra fila (`FUN-DEMO-ADMIN`, vecino id 22 u otro id) recibe un RUT del rango 33.xxx.xxx. `V018` no vuelve a crear `uq_funcionario_rut` ni `ck_funcionario_rut` si ya existen. La comprobación es `sql/verificacion/B7__rut_simulacion.sql`: cada consulta debe devolver 0. No es un cambio de esquema y no lleva `V`/`R`.
