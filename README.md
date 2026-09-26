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
Copy-Item .env.example .env      # completar SECRET_KEY, DEBUG=True, ALLOWED_HOSTS y DB_* (MySQL local)
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
cp .env.example .env             # completar SECRET_KEY, DEBUG=True, ALLOWED_HOSTS y DB_*
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
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

## Despliegue en AWS EC2

Servidor: Amazon Linux 2023, IP pública `54.205.69.94`.
Arquitectura: Apache (puerto 80) sirve phpMyAdmin en `/phpmyadmin` y los estáticos en `/static/`, y reenvía el resto a Gunicorn (`127.0.0.1:8000`), que ejecuta Django. La base es MySQL 8.4 LTS en la misma instancia.

### 1. Conectarse por SSH
```bash
ssh -i Gestion_muni_nueva.pem ec2-user@54.205.69.94
```

### 2. Paquetes del sistema
```bash
sudo dnf install -y git gcc python3.14 python3.14-devel
```

### 3. MySQL 8.4 LTS (Django 6.1 exige MySQL 8.4 o superior)
```bash
mysqldump -uroot -p --all-databases > ~/backup_mysql80.sql      # respaldo previo
sudo systemctl stop mysqld
sudo dnf install -y https://dev.mysql.com/get/mysql84-community-release-el9-1.noarch.rpm
sudo dnf config-manager --disable mysql80-community
sudo dnf config-manager --enable mysql-8.4-lts-community
sudo dnf upgrade -y 'mysql-community-*'
sudo systemctl start mysqld
```

### 4. Base de datos y usuario propio para Django (no se usa root)
```sql
CREATE DATABASE gestion_muni CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;  -- motor InnoDB
CREATE USER 'django_muni'@'localhost' IDENTIFIED BY '<clave>';
GRANT ALL PRIVILEGES ON gestion_muni.* TO 'django_muni'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Código y entorno virtual
```bash
git clone -b backend-mysql https://github.com/Felipe2076/Proyecto-bakend app
cd app
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env    # completar SECRET_KEY, DEBUG=False, ALLOWED_HOSTS con la IP, CSRF_TRUSTED_ORIGINS y DB_*
chmod 600 .env
```

### 6. Migraciones y datos
```bash
python manage.py migrate
python manage.py loaddata 01_catalogos 02_datos_sistema
python manage.py importar_json
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 7. Gunicorn como servicio (`/etc/systemd/system/gunicorn_muni.service`)
```ini
[Unit]
Description=Gunicorn Django gestion_muni (Proyecto-bakend)
After=network.target mysqld.service

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/app
ExecStart=/home/ec2-user/app/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn_muni
```

### 8. Apache como proxy inverso (`/etc/httpd/conf.d/django.conf`)
```apache
Alias /static/ /home/ec2-user/app/staticfiles/
<Directory /home/ec2-user/app/staticfiles>
    Require all granted
</Directory>
ProxyPreserveHost On
ProxyPass /phpmyadmin !
ProxyPass /static/ !
ProxyPass / http://127.0.0.1:8000/
ProxyPassReverse / http://127.0.0.1:8000/
```
```bash
chmod o+x /home/ec2-user /home/ec2-user/app
chmod -R o+rX /home/ec2-user/app/staticfiles
sudo apachectl configtest && sudo systemctl reload httpd
```

### 9. Actualizar después de un cambio en GitHub
```bash
cd ~/app && git pull && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn_muni
```

### URLs
- App: http://54.205.69.94/
- Django Admin: http://54.205.69.94/admin/
- phpMyAdmin: http://54.205.69.94/phpmyadmin/
