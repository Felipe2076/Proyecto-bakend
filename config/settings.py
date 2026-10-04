import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Variables sensibles en .env (no versionado). Ver .env.example.
load_dotenv(BASE_DIR / ".env")


def env_list(nombre, por_defecto=""):
    valor = os.getenv(nombre, por_defecto)
    return [item.strip() for item in valor.split(",") if item.strip()]


def env_obligatoria(nombre):
    valor = os.getenv(nombre)
    if not valor:
        raise ImproperlyConfigured(f"Falta la variable de entorno {nombre} (revise el archivo .env).")
    return valor


# Único valor con respaldo seguro: si no se define, DEBUG queda apagado.
DEBUG = os.getenv("DEBUG", "False").strip().lower() in ("1", "true", "yes", "si", "sí")

# La aplicación usa MySQL. SIGED_DB=sqlite existe solo para la suite de pruebas
# cuando no hay un servidor MySQL (no es el motor de la demostración ni de EC2).
_USAR_SQLITE = os.getenv("SIGED_DB", "").strip().lower() == "sqlite"

if _USAR_SQLITE:
    SECRET_KEY = os.getenv("SECRET_KEY") or "clave-de-prueba-no-usar-en-produccion"
else:
    SECRET_KEY = env_obligatoria("SECRET_KEY")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cuentas",
    "requerimientos",
    "control_gestion",
    "publico",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "config.middleware.AutenticacionMockMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.sesion_siged",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if _USAR_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SIGED_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    # MySQL 8.x (WAMP en local, MySQL en el servidor). Driver: PyMySQL (ver config/__init__.py).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env_obligatoria("DB_NAME"),
            "USER": env_obligatoria("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                # InnoDB obligatorio: WAMP trae MyISAM por defecto (sin llaves foráneas).
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES', default_storage_engine=INNODB",
            },
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
# Destino de `python manage.py collectstatic` (servidor web en EC2).
STATIC_ROOT = BASE_DIR / "staticfiles"

# Fixtures del proyecto (python manage.py loaddata 01_catalogos ...).
FIXTURE_DIRS = [BASE_DIR / "fixtures"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# El código de recuperación sale por correo. Con DEBUG se imprime en la consola
# del proceso, nunca en el HTML. En pruebas se sustituye por el backend locmem.
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").strip().lower() in ("1", "true", "yes", "si", "sí")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "siged@localhost")
