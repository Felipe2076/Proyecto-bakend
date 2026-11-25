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

# Siempre desde el entorno. No hay clave de respaldo en el código.
SECRET_KEY = env_obligatoria("SECRET_KEY")
# HMAC de codigo_un_uso. Vacío: se usa SECRET_KEY al calcular el hash.
SIGED_CODE_HMAC_KEY = os.getenv("SIGED_CODE_HMAC_KEY", "").strip()

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
    "rest_framework",
    "drf_spectacular",
    "api_rest",
]

MIDDLEWARE = [
    "core.seguridad.PeticionAcotadaMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.AutenticacionMockMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
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
            "builtins": ["core.fechas"],
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
PASSWORD_RESET_TIMEOUT = 600


def env_bool(nombre, por_defecto):
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return por_defecto
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí")


# Sesión en la base: la cookie solo lleva un identificador aleatorio (antes viajaban nombre,
# rol y delegación firmados pero legibles) y el cierre de sesión la invalida en el servidor.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = int(os.getenv("SIGED_SESION_SEGUNDOS", str(8 * 3600)))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True  # kanban.js toma el token del formulario, no de la cookie.
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"
# Cookies solo por HTTPS fuera de desarrollo. SIGED_COOKIES_SEGURAS=False solo para un HTTP local.
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = env_bool("SIGED_COOKIES_SEGURAS", not DEBUG)

# Cabeceras. HSTS y redirección quedan a cargo del entorno: con certificado autofirmado o
# acceso por IP no conviene fijar HSTS. Ver docs/SEGURIDAD.md.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(os.getenv("SIGED_HSTS_SEGUNDOS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_SSL_REDIRECT = env_bool("SIGED_REDIRIGIR_HTTPS", False)
SECURE_REDIRECT_EXEMPT = [r"^salud/$"]

# Proxy inverso (Apache) de confianza: solo entonces se aceptan X-Forwarded-Proto/For.
import ipaddress as _ip  # noqa: E402

SIGED_PROXIES_CONFIABLES = [_ip.ip_network(red, strict=False) for red in env_list("SIGED_PROXY_CONFIABLE")]
if SIGED_PROXIES_CONFIABLES:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Límites de carga: la evidencia admite 10 MB; el resto del formulario es pequeño.
SIGED_MAX_PETICION = int(os.getenv("SIGED_MAX_PETICION", str(12 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500
DATA_UPLOAD_MAX_NUMBER_FILES = 5
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
# Los estáticos son públicos y los sirve Apache (otro usuario): sin modos propios, collectstatic
# heredaba 0640/0750 de arriba y Apache respondía 403. Las evidencias conservan 0640/0750.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        "OPTIONS": {"file_permissions_mode": 0o644, "directory_permissions_mode": 0o755},
    },
}

# Cuotas de intentos por 15 minutos (IP y cuenta). La cuenta se libera al ingresar.
SIGED_LIMITE_LOGIN_IP = int(os.getenv("SIGED_LIMITE_LOGIN_IP", "60"))
# Con 1, los indicadores (dashboard, áreas, panel SGR) excluyen vecinos y funcionarios
# marcados como datos de simulación. Por defecto 0 para no vaciar bases de demostración.
SIGED_OCULTAR_SIMULACION = os.getenv("SIGED_OCULTAR_SIMULACION", "0") == "1"
# Duración del token de la app móvil (se renueva con /api/v1/sesion/renovar/).
SIGED_TOKEN_MOVIL_DIAS = int(os.getenv("SIGED_TOKEN_MOVIL_DIAS", "30"))
SIGED_LIMITE_LOGIN_CUENTA = int(os.getenv("SIGED_LIMITE_LOGIN_CUENTA", "8"))
SIGED_LIMITE_RECUPERAR_IP = int(os.getenv("SIGED_LIMITE_RECUPERAR_IP", "10"))
SIGED_LIMITE_RECUPERAR_CORREO = int(os.getenv("SIGED_LIMITE_RECUPERAR_CORREO", "3"))

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

EMAIL_TIMEOUT = 10

# Los archivos se entregan por una vista autenticada con control de alcance. En Docker
# SIGED_MEDIA_ROOT apunta a un volumen que el proxy no publica (evidencias privadas).
MEDIA_ROOT = Path(os.getenv("SIGED_MEDIA_ROOT", str(BASE_DIR / "media")))
MEDIA_URL = "/archivos-privados/"

# Registros a stdout (Docker los rota); el filtro quita RUT, correos, tokens y consultas.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"datos_personales": {"()": "core.seguridad.FiltroDatosPersonales"}},
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "filters": ["datos_personales"],
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["consola"], "level": os.getenv("SIGED_LOG_NIVEL", "WARNING")},
    "loggers": {
        "django": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
        "siged.seguridad": {"handlers": ["consola"], "level": "INFO", "propagate": False},
    },
}

# --- API REST v2 (Sumativa 4): DRF + JWT + Swagger. Solo afecta a /api/v2/; la web sigue con sesión.
from datetime import timedelta  # noqa: E402

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min", "login": "5/min"},
    "EXCEPTION_HANDLER": "api_rest.errores.manejar_error",
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": False,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "SIGED API v2",
    "DESCRIPTION": "API RESTful de SIGED (Municipalidad de La Serena). Autenticación JWT: obtenga el token en "
                   "/api/v2/token/ y péguelo en Authorize.",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": False},
}
