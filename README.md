# SIGED-SGR Delegaciones La Serena

Sistema de gestión de delegaciones municipales: atención ciudadana, tickets, actividad y evidencia, compromisos, agenda e indicadores. Equipo Los watones PC: Felipe, Aixa y Gabriel.

## Evaluación Sumativa 3

Se conservan los requisitos originales y se completan grupos y permisos de Django, recuperación mediante enlace seguro y administración desde Django Templates. Las operaciones de la revisión se realizan en las pantallas municipales y no dependen de Django Admin.

- RUT y contraseña, cierre de sesión y vistas protegidas.
- Administrador, Jefatura/Supervisor, Funcionario y Ventanilla/Administrativo, con grupos y paneles diferenciados.
- Administración propia de usuarios, asignación de grupos y permisos.
- Recuperación por correo con token de Django, caducidad de diez minutos y confirmación del cambio. Se conserva el código de respaldo.
- Las nuevas cuentas reciben una invitación en su propio correo y definen su contraseña.
- Mantenedores: delegaciones, usuarios, roles, metas, tipos de atención, subatenciones, tipos de gestión y vecinos.
- Transacciones: tickets y asignación, atenciones relacionadas y compromisos ciudadanos.
- Se conservan búsquedas, códigos automáticos, Kanban, Excel y paginadores superiores.

Alcance, perfiles, seguridad y guion presencial: [docs/SUMATIVA3.md](docs/SUMATIVA3.md).

## Tecnología

Python y Django según `requirements.txt`, MySQL 8.4/InnoDB, Django ORM, formularios Django, Bootstrap 5.3 e identidad municipal existente. Producción en AWS EC2 con Docker, Gunicorn, Apache y HTTPS. SQLite se usa exclusivamente en pruebas aisladas.

## Instalación local

```powershell
git clone https://github.com/Felipe2076/Proyecto-bakend.git
cd Proyecto-bakend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Completar una `SECRET_KEY` propia, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` y `ALLOWED_HOSTS` en `.env`. Mantener `DEBUG=False`. Crear una base MySQL vacía con utf8mb4 e InnoDB.

```powershell
python manage.py migrate
```

Solo para una base **nueva de demostración**:

```powershell
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
python manage.py runserver
```

`importar_json` genera claves de simulación en `.demo_credentials.local`, que no se versiona. No ejecutarlo para actualizar una base de producción con contraseñas y cuentas de trabajo.

Si la base ya existe, respaldarla y aplicar solamente las migraciones pendientes. Las migraciones de esta evaluación vinculan roles con grupos; no reemplazan las claves ni eliminan registros de negocio.

## Correo y recuperación

Configurar `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` y `DEFAULT_FROM_EMAIL` en el entorno privado. Para Gmail se utiliza smtp.gmail.com, puerto 587, TLS y una contraseña de aplicación del remitente. Nunca guardar una contraseña o clave SMTP en Git.

En `/recuperar/` se solicita el enlace. El correo lleva a `/recuperar/enlace/<uid>/<token>/`, donde se establece y confirma la nueva contraseña. El token vence en diez minutos y no se puede reutilizar tras el cambio. `/recuperar/codigo/` conserva la alternativa de seis dígitos. Probar la recepción con un correo real autorizado antes de presentar.

## Rutas principales

- `/login/` y `/logout/`: ingreso y cierre.
- `/`: panel según el perfil; sin sesión comienza por el login.
- `/administracion/usuarios/`: creación y estado de cuentas.
- `/administracion/grupos/`: grupos, permisos y asignación.
- `/mantenedores/`: CRUD propio con formularios Django.
- `/lista/`, `/control/kanban/`: tickets y seguimiento.
- `/control/actividades/`, `/control/tubo-trabajo/`, `/control/agenda/`: gestión interna.
- `/control/semaforo-sgr/`: desempeño e indicadores.

## Pruebas

Las pruebas crean una base temporal y no deben apuntarse a los datos de producción.

```powershell
$env:SIGED_DB='sqlite'
$env:SIGED_SQLITE_PATH=':memory:'
$env:SECRET_KEY='solo-para-pruebas'
python manage.py test --noinput
```

Incluyen autenticación, grupos, accesos directos, revocación de permisos, invitaciones, recuperación por enlace/código, tokens alterados o caducados, CRUD, ámbito territorial, Excel, Kanban y paginación. Las importaciones de prueba usan archivos temporales de claves.

## Publicación y evidencias

Instancia `Gestion_municipalidad_delegaciones`, en us-east-1. [Login publicado](https://54.205.69.94/login/). La sesión del laboratorio de AWS Academy y la instancia deben estar activas durante la revisión.

Antes de desplegar: respaldar código y MySQL, verificar migraciones, construir la imagen, ejecutar pruebas y cambiar a la versión sana. Conservar la anterior para recuperación. Variables privadas y claves SSH no forman parte de Git ni de los documentos.

Para tres integrantes se requieren seis mantenedores y tres transacciones. El sistema dispone de módulos para demostrarlos; el guion debe realizar las operaciones y comprobar su persistencia.

Licencias: [docs/ASSETS_LIBRES.md](docs/ASSETS_LIBRES.md). Los documentos de etapas anteriores se conservan como referencia y no sustituyen las evidencias actuales de Sumativa 3.
