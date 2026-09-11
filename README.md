# SIGED-SGR Delegaciones La Serena

Mockup **funcional** del Sistema Integrado de Gestión de Requerimientos y Matriz SGR para las 6 delegaciones territoriales de la Municipalidad de La Serena.

Entrega: **Primera_Entrega / Proyecto Integrado** (profesor Jorge Cortés).  
Repositorio: [Felipe2076/Proyecto-bakend](https://github.com/Felipe2076/Proyecto-bakend)

Este entorno cubre la rúbrica §7.2 (template/mockup funcional en Git):

- Navegación entre pantallas principales, con menú según **rol**
- Flujo de interfaz consistente (Bootstrap 5, textos en español)
- Formularios con validación de obligatorios, formatos y mensajes al usuario
- Persistencia **JSON local** (sin MySQL ni APIs de negocio)

## Stack

- Python 3.12+
- Django 6.1
- Persistencia en archivos `data/*.json`
- Sesión mock en cookie firmada (no requiere `migrate` ni MySQL)
- Bootstrap 5.3 + Bootstrap Icons (archivos locales en `static/`)
- Bootstrap 5.3 + Bootstrap Icons (archivos locales en `static/`)
- `requests` solo para el clima de demostración (Open-Meteo), con fallback si no hay red

No hay dependencia de MySQL para ejecutar el mockup.

## Cómo ejecutar en Windows (PowerShell)

```powershell
git clone https://github.com/Felipe2076/Proyecto-bakend.git
cd Proyecto-bakend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py runserver
```

Si PowerShell bloquea la activación del entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

Abrir [http://127.0.0.1:8000/](http://127.0.0.1:8000/). El sistema pide login de demostración.

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

## Usuarios de demostración

| Usuario | Contraseña | Rol | Qué ve en el menú |
| --- | --- | --- | --- |
| `admin` | `admin123` | Administrador | Todas las pantallas + administración |
| `jefatura` | `jefatura123` | Jefatura | Matriz SGR, control de gestión, operación |
| `funcionario` | `funcionario123` | Funcionario territorial | Tickets, actividades, agenda, compromisos |
| `ventanilla` | `ventanilla123` | Ventanilla ciudadana | Captura multicanal, listado, encuesta, agenda |

Las claves están visibles a propósito: es un mockup académico, no un sistema productivo.

## Pantallas del mockup

1. **Login (mock)** y **inicio / dashboard** de KPIs
2. **Registrar requerimiento ciudadano** (ventanilla, WhatsApp, correo, teléfono, portal) con validaciones
3. **Listado / detalle de tickets** y **Kanban** con semáforo visual (verde / amarillo / rojo)
4. **Actividades diarias** y evidencias (upload simulado: se guarda el nombre del archivo)
5. **Compromisos ciudadanos** (CRUD simple sobre el tubo de trabajo)
6. **Agenda colectiva** (calendario y lista)
7. **Panel semáforo SGR / KPIs** (datos demo)
8. **Administración**: usuarios, cargos y parámetros (solo UI + JSON)
9. **Notificaciones** y **encuesta de satisfacción 1–5**

## Pruebas rápidas

```powershell
python tests_siged.py
```

## Documentación de contexto

- `Documentacion_SIGED_LaSerena.pdf`
- `Documentacion_SIGED_LaSerena.docx`
