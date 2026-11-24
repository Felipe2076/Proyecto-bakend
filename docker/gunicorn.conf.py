"""Gunicorn de SIGED: límites de petición y tiempos acotados (mitigación de agotamiento a nivel de aplicación)."""
import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_class = "gthread"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 20
keepalive = 5
# Reciclar procesos acota fugas de memoria bajo carga sostenida.
max_requests = 1000
max_requests_jitter = 100

# Cabeceras y línea de petición acotadas.
limit_request_line = 4094
limit_request_fields = 60
limit_request_field_size = 8190

# Solo el proxy declarado puede fijar X-Forwarded-Proto/For (red de Docker o host).
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1")

# Registro de acceso sin IP ni parámetros de consulta (pueden traer RUT o nombres).
# La IP queda en el registro del proxy, que tiene su propia retención.
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "warning")
access_log_format = '%(t)s "%(m)s %(U)s" %(s)s %(b)s %(M)sms'
