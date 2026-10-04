# Scripts SQL de SIGED-SGR

Convención del plan: `sql/migraciones/V0xx__*.sql`, `sql/rollback/R0xx__*.sql` y `sql/datos/D0xx__*.sql`.

Cada cambio de esquema de la prioridad 1 tiene script y rollback, y también una migración Django. **No aplicar los dos caminos sobre el mismo esquema.**

| Orden | Script | Qué hace | Rollback |
| --- | --- | --- | --- |
| 1 | `V017__funcionario_rut_nombres.sql` | Columnas anulables `rut`, `nombres`, apellidos y `es_simulacion`; índice `idx_funcionario_delegacion_apellido` | `R017__funcionario_rut_nombres.sql` |
| 2 | `D003__datos_simulacion.sql` | Reemplaza identidades por la simulación (RUT del rango 33.xxx, hash de clave, sin texto plano) | No hay rollback de datos: restaurar el `mysqldump` |
| 3 | `V018__rut_obligatorio.sql` | `rut` y nombres obligatorios, `uq_funcionario_rut`, `CHECK` con `REGEXP_LIKE`, `cuentas_usuario.funcionario_id` obligatorio | `R018__rut_obligatorio.sql` |

El índice equivalente en Django se llama `idx_fun_deleg_apellido` porque el ORM limita el nombre a 30 caracteres. El `CHECK` de formato vive solo en MySQL (`V018`); SQLite, usado por la suite, no tiene `REGEXP_LIKE`. El dígito verificador se exige en Python y en JavaScript.

## Base nueva o de desarrollo

```bash
mysqldump -u "$DB_USER" -p --single-transaction --routines gestion_muni > backups/gestion_muni_antes.sql
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
```

La migración `cuentas.0003` reescribe los datos si ya hay funcionarios. En una base vacía no inserta la simulación: eso lo hacen el fixture y `importar_json`.

## Esquema ya creado por Django 0001, sin pasar por migrate de la 0002/0003

```bash
mysqldump -u "$DB_USER" -p --single-transaction --routines gestion_muni > backups/gestion_muni_antes.sql
mysql gestion_muni < sql/migraciones/V017__funcionario_rut_nombres.sql
mysql gestion_muni < sql/datos/D003__datos_simulacion.sql
mysql gestion_muni < sql/migraciones/V018__rut_obligatorio.sql
python manage.py migrate --fake
```

`D003` actualiza los vecinos con `id` 1 a 21, que es el orden del fixture de la sumativa 2. Si la base local tiene otros id, no usar `D003`: aplicar `migrate` y la migración de datos, que localiza las filas por código de funcionario y por el mapa en memoria, no por esos id.

`migrate --fake` marca como aplicadas las migraciones cuyo SQL ya se ejecutó. No volver a correr `V017`/`V018` después de un `migrate` real.
