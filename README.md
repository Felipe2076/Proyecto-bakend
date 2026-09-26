# SIGED-SGR Delegaciones La Serena

Prototipo web de la **Primera Entrega** del Proyecto Integrado.

**Equipo Los watones PC** — Felipe, Aixa y Gabriel  
Municipalidad de La Serena · 6 delegaciones territoriales  
Profesor: Jorge Cortés

El mockup cubre la rúbrica §7.2 (template funcional en Git): navegación por módulos, formularios con validación y persistencia **JSON local**. No se conecta MySQL ni APIs de negocio.

## Stack

- Python 3.12+ y Django 6.1
- Datos en `data/*.json` (sesión mock en cookie firmada; no hay que correr `migrate`)
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
python manage.py runserver
```

Si PowerShell no deja activar el entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Abrir http://127.0.0.1:8000/

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

## Quién entra (demo)

| Usuario | Clave | Rol |
| --- | --- | --- |
| `admin` | `admin123` | Administración (ve todo) |
| `jefatura` | `jefatura123` | Jefatura / control de gestión |
| `funcionario` | `funcionario123` | Equipo territorial |
| `ventanilla` | `ventanilla123` | Atención en ventanilla |

Las claves están a la vista a propósito: es un prototipo de curso.

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

```powershell
python tests_siged.py
```

## Documentación de contexto

- `Documentacion_SIGED_LaSerena.pdf` / `.docx` (si el equipo las adjunta en la entrega)
- Marca propia abstracta (faro + costa), no el escudo municipal con copyright. Ver [`docs/ASSETS_LIBRES.md`](docs/ASSETS_LIBRES.md).

## Backend con MySQL (Evaluación Sumativa 2)

Desde la rama `backend-mysql` los datos viven en **MySQL** (Django ORM + Django Admin). Los `data/*.json` quedan solo como origen para migrar los datos.

1. Copiar `.env.example` como `.env` y completar `SECRET_KEY`, `ALLOWED_HOSTS` y las variables `DB_*` (el `.env` no se sube a GitHub).
2. Crear la base de datos vacía (`CREATE DATABASE gestion_muni CHARACTER SET utf8mb4;`). Las tablas deben ser **InnoDB** (ya se fuerza en `settings.py`).
3. Instalar y migrar:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema   # roles, delegaciones, tipos, datos migrados del JSON
python manage.py importar_json                            # (opcional) re-lee data/*.json y crea usuarios Django con clave hasheada
python manage.py createsuperuser                          # acceso a /admin/
python manage.py collectstatic                            # solo en el servidor (EC2)
```

- `fixtures/01_catalogos.json`: roles, delegaciones, tipos de gestión, tipos/sub atención, canales, metas y parámetros.
- `fixtures/02_datos_sistema.json`: todo lo migrado desde `data/*.json` más vecinos y atenciones de ejemplo del mockup (sin contraseñas).
- `python manage.py importar_json [--sin-auth]`: comando idempotente que migra los JSON a la base de datos.
