# Scripts SQL de SIGED-SGR

Convención del plan: `sql/migraciones/V0xx__*.sql`, `sql/rollback/R0xx__*.sql` y `sql/datos/D0xx__*.sql`.

Cada cambio de esquema de la prioridad 1 tiene script y rollback, y también una migración Django. **No aplicar los dos caminos sobre el mismo esquema.**

| Orden | Script | Qué hace | Rollback |
| --- | --- | --- | --- |
| 1 | `V017__funcionario_rut_nombres.sql` | Columnas anulables `rut`, `nombres`, apellidos y `es_simulacion`; índice `idx_funcionario_delegacion_apellido` | `R017__funcionario_rut_nombres.sql` |
| 2 | `D003__datos_simulacion.sql` | Reemplaza identidades por la simulación, también filas que no están en el fixture | No hay rollback de datos: restaurar el `mysqldump` |
| — | `verificacion/B7__rut_simulacion.sql` | Consultas de lectura. Cada resultado debe ser 0. No cambia el esquema | No aplica |
| 3 | `V018__rut_obligatorio.sql` | `rut` y nombres obligatorios, `uq_funcionario_rut`, `CHECK` con `REGEXP_LIKE`, `cuentas_usuario.funcionario_id` obligatorio | `R018__rut_obligatorio.sql` |
| 4 | `V019__codigo_un_uso.sql` | Tabla `codigo_un_uso`: HMAC del código, vencimiento, intentos, `usado_en` y `anulado_en` | `R019__codigo_un_uso.sql` |

`V019` es esta tabla (MER v1.15), con el `CREATE TABLE` acordado. En MySQL, `cuentas.0004` ejecuta ese mismo enunciado: columnas, tipos y restricciones quedan iguales, para que un `V020` posterior pueda agregar la llave de `cuenta_vecino_id` y el propósito `ACTIVAR_CUENTA`. `cuenta_vecino_id` en `V019` es un entero anulable, sin llave foránea. En el plan del equipo `V023` es EQ-41 (`rol.exige_mfa` y sesión en `cuentas_usuario`) y no se usa aquí. `V020` (cuenta de vecino) y `V022` (MFA) siguen asignados en el plan. `es_simulacion` ya está en `V017`; no hay `V018b`. La restricción `UNIQUE` `uq_funcionario_rut` se mantiene en `V018`.

`R017` crea antes `idx_funcionario_delegacion_id` y solo entonces borra el índice compuesto. Sin ese paso MySQL responde 1553, porque el compuesto es el que sostiene la llave foránea de `delegacion_id`. También contempla el nombre corto `idx_fun_deleg_apellido` de Django. La bitácora que detallaba el arreglo no estaba en el workspace.

El índice equivalente en Django se llama `idx_fun_deleg_apellido` porque el ORM limita el nombre a 30 caracteres. El `CHECK` de formato vive solo en MySQL (`V018`); SQLite, usado por la suite, no tiene `REGEXP_LIKE`. El dígito verificador se exige en Python y en JavaScript.

## Base nueva o de desarrollo

```bash
mysqldump -u "$DB_USER" -p --single-transaction --routines gestion_muni > backups/gestion_muni_antes.sql
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
```

`importar_json` escribe las claves en `.demo_credentials.local` y no las imprime. La migración `cuentas.0003` reescribe los datos si ya hay funcionarios y deja la clave inutilizable; `cuentas.0004` crea `codigo_un_uso`. En una base vacía `0003` no inserta la simulación: eso lo hacen el fixture y `importar_json`.

## Esquema ya creado por Django 0001, sin pasar por migrate de la 0002/0003

```bash
mysqldump -u "$DB_USER" -p --single-transaction --routines gestion_muni > backups/gestion_muni_antes.sql
mysql gestion_muni < sql/migraciones/V017__funcionario_rut_nombres.sql
mysql gestion_muni < sql/datos/D003__datos_simulacion.sql
mysql gestion_muni < sql/migraciones/V018__rut_obligatorio.sql
mysql gestion_muni < sql/migraciones/V019__codigo_un_uso.sql
python manage.py importar_json
mysql gestion_muni < sql/verificacion/B7__rut_simulacion.sql
python manage.py migrate --fake
```

`D003` y `V018` se corrigieron en su archivo. No hay `D005` ni otro `V`: en la bitácora del equipo el siguiente hueco está después de `D004` (EQ-47) y esos dos scripts no habían quedado aplicados en las bases con datos. El detalle está en `docs/mer/BITACORA_MODELO.md`.

## Ensayo sobre una copia (base que ya tiene filas)

No correr esto primero contra la base real. Restaurar una copia (por ejemplo `gestion_muni_ensayo`) y trabajar ahí. `loaddata 02_datos_sistema` no es idempotente: si ya hay usuarios, choca por el correo. En una base con datos el orden es `migrate` y después `importar_json`.

```bash
mysqldump -u "$DB_USER" -p --single-transaction --routines gestion_muni > backups/gestion_muni_antes.sql
mysql -u "$DB_USER" -p -e "CREATE DATABASE gestion_muni_ensayo CHARACTER SET utf8mb4"
mysql -u "$DB_USER" -p gestion_muni_ensayo < backups/gestion_muni_antes.sql
# Apuntar DB_NAME del .env a la copia, o cargar el volcado ahí y no a producción.
python manage.py migrate
python manage.py importar_json
mysql -u "$DB_USER" -p gestion_muni_ensayo < sql/verificacion/B7__rut_simulacion.sql
```

`sql/verificacion/B7__rut_simulacion.sql` no modifica datos. Cada resultado tiene que ser 0: ningún RUT de funcionario, usuario o vecino fuera de 33.xxx.xxx, ningún vecino o funcionario sin marca de simulación, ningún correo de usuario fuera de `@siged.test`, ninguna combinación rol × delegación vacía y ningún RUT de funcionario repetido. Cubre cualquier id, no solo el 1 a 21 ni el código `FUN-DEMO-ADMIN`.

Si alguna consulta no da 0, no repetir el procedimiento sobre la base real. Si todas dan 0, el mismo orden (`migrate`, sin `loaddata`, `importar_json`, otra vez B7) se aplica a la base de trabajo, con el respaldo ya tomado. Volver a correr `migrate` e `importar_json` no duplica personas.

El `CHECK` de `0003` corre fuera de la transacción de Django. Si el migrate anterior se cortó en ese paso, hay que volver a ejecutar `migrate`: no recrea el índice único ni el `CHECK` si ya quedaron creados.

`migrate --fake` marca como aplicadas las migraciones cuyo SQL ya se ejecutó. No volver a correr `V017`/`V018` después de un `migrate` real.
