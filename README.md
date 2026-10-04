# SIGED-SGR Delegaciones La Serena

Prototipo web de la **Primera Entrega** del Proyecto Integrado.

**Equipo Los watones PC** — Felipe, Aixa y Gabriel  
Municipalidad de La Serena · 6 delegaciones territoriales  
Profesor: Jorge Cortés

El sistema cubre la navegación por módulos, los formularios con validación y la persistencia en **MySQL** (Django ORM). Los JSON de `data/` son la fuente para sembrar la base, no el almacén en tiempo de ejecución.

## Stack

- Python 3.12+ y Django 6.1
- MySQL 8.4 (utf8mb4, InnoDB). La suite puede usar `SIGED_DB=sqlite` si no hay servidor MySQL
- `DEBUG` sale del entorno y queda **apagado** si no se define. Secretos (`SECRET_KEY`, `DB_*`) van en `.env`, que no se versiona
- Bootstrap 5.3 + íconos locales (layout; la identidad visual no es una plantilla genérica)
- Paleta municipal **roja**, tipografía display Fraunces (OFL) + Source Sans 3 (OFL)
- Motion gratis: Lottie original self-hosted, Lordicon *wired/outline* FREE, Lenis (jsDelivr)
- `requests` solo para el clima de demostración (Open-Meteo), con fallback
- Licencias y lista de íconos: [`docs/ASSETS_LIBRES.md`](docs/ASSETS_LIBRES.md)

## Cómo ejecutarlo en Windows (PowerShell)

```powershell
git clone https://github.com/Felipe2076/Proyecto-bakend.git
cd Proyecto-bakend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # completar SECRET_KEY, ALLOWED_HOSTS y DB_* (DEBUG queda False)
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
python manage.py runserver
```

Si PowerShell no deja activar el entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Requiere MySQL 8.4+ con la base creada (ver *Backend con MySQL* más abajo). Abrir http://127.0.0.1:8000/

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # completar SECRET_KEY, ALLOWED_HOSTS y DB_* (DEBUG queda False)
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
python manage.py runserver
```

## Quién entra (simulación)

El ingreso es **RUT + clave**. Cada cuenta es un funcionario ficticio, marcado `(ficticio)`, con correo `@siged.test`. Hay al menos una cuenta por cada rol (`administrador`, `jefatura`, `funcionario`, `ventanilla`) en cada una de las seis delegaciones, más un administrador global (`USR-025`).

La clave de **todas** las cuentas de simulación es la convención `Simulacion#2026`. No es un secreto de producción: no está en `data/usuarios.json` (ahí no hay clave) y en la base queda solo el hash. Con `DEBUG=True` el login lista los RUT, sin mostrar la clave.

| RUT | Rol | Delegación | Código |
| --- | --- | --- | --- |
| `33100024-8` | administrador | Delegación Av. del Mar | USR-017 |
| `33100026-4` | funcionario | Delegación Av. del Mar | USR-019 |
| `33100025-6` | jefatura | Delegación Av. del Mar | USR-018 |
| `33100027-2` | ventanilla | Delegación Av. del Mar | USR-020 |
| `33100011-6` | administrador | Delegación Centro | USR-001 |
| `33100032-9` | administrador (global) | Delegación Centro | USR-025 |
| `33100013-2` | funcionario | Delegación Centro | USR-006 |
| `33100012-4` | jefatura | Delegación Centro | USR-005 |
| `33100014-0` | ventanilla | Delegación Centro | USR-007 |
| `33100016-7` | administrador | Delegación La Antena | USR-009 |
| `33100018-3` | funcionario | Delegación La Antena | USR-011 |
| `33100017-5` | jefatura | Delegación La Antena | USR-010 |
| `33100019-1` | ventanilla | Delegación La Antena | USR-012 |
| `33100020-5` | administrador | Delegación La Pampa | USR-013 |
| `33100022-1` | funcionario | Delegación La Pampa | USR-015 |
| `33100021-3` | jefatura | Delegación La Pampa | USR-014 |
| `33100023-K` | ventanilla | Delegación La Pampa | USR-016 |
| `33100028-0` | administrador | Delegación Las Compañías | USR-021 |
| `33100030-2` | funcionario | Delegación Las Compañías | USR-023 |
| `33100029-9` | jefatura | Delegación Las Compañías | USR-022 |
| `33100031-0` | ventanilla | Delegación Las Compañías | USR-024 |
| `33100015-9` | administrador | Delegación Rural | USR-008 |
| `33100002-7` | funcionario | Delegación Rural | USR-003 |
| `33100001-9` | jefatura | Delegación Rural | USR-002 |
| `33100004-3` | ventanilla | Delegación Rural | USR-004 |

Al entrar, `/` abre **Mi panel**: el administrador ve la vista global, la jefatura ve su delegación y funcionario o ventanilla ven solo su panel personal.

## Pantallas ↔ casos de uso

| Módulo | Pantalla | CU |
| --- | --- | --- |
| Ingreso | Login | CU-E01 |
| Atención ciudadana | Ingresar ticket (ventanilla / WhatsApp / correo) | CU-E02 |
| Atención ciudadana | Listado de tickets + semáforo | CU-E03 |
| Atención ciudadana | Ficha del ticket | CU-E04 |
| Atención ciudadana | Tablero Kanban | CU-E05 |
| Gestión interna | Actividad diaria | CU-E06 |
| Gestión interna | Evidencia (upload simulado) | CU-E07 |
| Gestión interna | Compromisos (CRUD) | CU-E08 |
| Gestión interna | Agenda colectiva | CU-E09 |
| Desempeño | Semáforo, indicadores y metas | CU-E10 |
| Administración | Usuarios, cargos, parámetros | CU-E11 |
| Atención / avisos | Encuesta 1–5 y notificaciones | CU-E12 |

Detalle para el informe: [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md).

Delegaciones de demo: **Centro, Rural, La Antena, La Pampa, Av. del Mar, Las Compañías**.  
Tipificación de ticket: **RECLAMO, SOLICITUD, CONSULTA, SUGERENCIA, FELICITACIÓN**.

## Pruebas

Con MySQL local (variables `DB_*` en `.env`) o, si no hay servidor, con SQLite solo para la suite:

```bash
SIGED_DB=sqlite SECRET_KEY=clave-de-prueba DEBUG=False python manage.py test
SIGED_DB=sqlite SECRET_KEY=clave-de-prueba DEBUG=False python tests_siged.py
```

## Documentación de contexto

- `Documentacion_SIGED_LaSerena.pdf` / `.docx` (si el equipo las adjunta en la entrega)
- Marca propia abstracta (faro + costa), no el escudo municipal con copyright. Ver [`docs/ASSETS_LIBRES.md`](docs/ASSETS_LIBRES.md).

## Backend con MySQL (Evaluación Sumativa 2)

Los datos de trabajo viven en **MySQL** (Django ORM + Django Admin). Los `data/*.json` quedan como origen para sembrar; el login no los lee.

1. Copiar `.env.example` como `.env` y completar `SECRET_KEY`, `ALLOWED_HOSTS` y las variables `DB_*` (el `.env` no se sube a GitHub). `DEBUG` no se define, o se deja en `False`.
2. Crear la base vacía (`CREATE DATABASE gestion_muni CHARACTER SET utf8mb4;`). Las tablas son **InnoDB** (se fuerza en `settings.py`).
3. Seguir *Aplicar en un MySQL local* (respaldo con `mysqldump` si la base ya tiene datos).

- `fixtures/01_catalogos.json`: roles, delegaciones, tipos de gestión, tipos/sub atención, canales, metas y parámetros.
- `fixtures/02_datos_sistema.json`: funcionarios, vecinos y cuentas de simulación. Las claves de `auth.user` van hasheadas.
- `python manage.py importar_json [--sin-auth]`: relee `data/*.json`. Si el JSON no trae clave, usa la convención de simulación y la guarda hasheada.

## Aplicar en un MySQL local

No mezclar los dos caminos sobre la misma base: o Django crea el esquema, o se aplican los scripts a mano y después se marcan las migraciones como hechas.

1. Respaldo antes de tocar datos existentes:

```bash
mysqldump -u "$DB_USER" -p --single-transaction --routines gestion_muni > backups/gestion_muni_antes.sql
```

2. Camino recomendado (base nueva o la de desarrollo):

```bash
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
```

`importar_json` asigna la convención `Simulacion#2026` solo si el usuario Django aún no tiene clave usable. `02_datos_sistema.json` ya trae el hash.

3. Camino manual, equivalente, sobre un esquema que ya tiene las tablas de `0001`:

```bash
mysql gestion_muni < sql/migraciones/V017__funcionario_rut_nombres.sql
mysql gestion_muni < sql/datos/D003__datos_simulacion.sql
mysql gestion_muni < sql/migraciones/V018__rut_obligatorio.sql
python manage.py migrate --fake
```

`D003` actualiza vecinos por `id` 1–21 del fixture. Si esos id no coinciden con la base local, usar el camino de `migrate` (la migración de datos no depende de esos id). Detalle en [`sql/README.md`](sql/README.md).

El usuario MySQL de la aplicación solo necesita permisos sobre `gestion_muni` para el trabajo de Django (consultar, insertar, actualizar, borrar y, al migrar, alterar). La clave va en `.env`, no en este archivo. Host, llaves y consolas de administración del servidor no se documentan en el repositorio.
