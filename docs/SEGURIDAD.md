# Refuerzo defensivo de SIGED

Propuesta para revisión de Codex antes de publicar. Probada en local con SQLite y datos ficticios.
No se ejecutaron pruebas ofensivas ni cambios en AWS.

## 1. Cambios en la aplicación

| Control | Implementación | Archivo |
|---|---|---|
| Sesión en servidor | `SESSION_ENGINE=db`. La cookie solo lleva un identificador aleatorio. Antes viajaban nombre, rol y delegación firmados pero legibles. El cierre de sesión la invalida en el servidor. Duración de 8 h. | `config/settings.py` |
| Cookies | `Secure` (por defecto fuera de DEBUG), `HttpOnly` y `SameSite=Lax` en sesión y CSRF | `config/settings.py` |
| CSRF | Se mantiene `CsrfViewMiddleware` en todo formulario. La API usa solo Bearer (sin cookies) y sigue exenta. | sin cambio + prueba |
| Cabeceras | `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, COOP, `Permissions-Policy`, `no-store` en login, recuperación y API. HSTS y redirección se activan por variable. | `config/settings.py`, `core/seguridad.py` |
| ORM parametrizado | Revisado: la aplicación no ejecuta SQL crudo con datos del usuario. `generar_simulacion` solo escribe un script offline con valores escapados. `/salud/` ejecuta un `SELECT 1` constante. | revisión |
| Permisos por módulo | Dashboard y Áreas exigen `acceso_control_gestion`. Semáforo, Metas por funcionario, Resumen y detalle de funcionario exigen `acceso_matriz_sgr` (el detalle acepta también `acceso_actividades`). Antes bastaba con iniciar sesión. | `control_gestion/views.py` |
| Permisos por delegación y objeto | Los listados de un perfil no administrador se limitan a su delegación. Una sesión no administradora sin delegación no ve ninguna. El detalle de un funcionario de otra delegación se niega. Resumen toma por defecto la delegación propia. | `cuentas/ambito.py`, `control_gestion/views.py` |
| Límite de login web | 60 intentos por IP y 8 por cuenta cada 15 min. La cuota de la cuenta se libera al ingresar. Al exceder: HTTP 429. | `cuentas/views.py`, `core/seguridad.py` |
| Recuperación | 10 solicitudes por IP y 3 por correo cada 15 min, incluido "reenviar". La respuesta es la misma exista o no el correo (no confirma titulares). | `cuentas/views.py` |
| Límite de API | Se mantiene la cuota de la API móvil (120 por IP y 8 por cuenta). La IP sale de `ip_cliente`: X-Forwarded-For solo cuenta si viene del proxy declarado. | `control_gestion/api_movil.py` |
| Cuotas sin datos personales | La tabla `IntentosMovil` guarda HMAC de IP, RUT y correo, nunca valores en claro. | `core/seguridad.py` |
| Cargas | Petición máxima de 12 MB (413 antes de leer el cuerpo), 5 archivos, 500 campos y 2,5 MB en memoria. Imagen de 40 MP como máximo. Permisos 0640/0750 para cargas. Los estáticos van con 0644/0755 propios (`STORAGES["staticfiles"]`); sin eso, `collectstatic` heredaba 0640 y Apache respondía 403 (incidente corregido con `siged-estaticos.diff`). | `config/settings.py`, `control_gestion/evidencias.py` |
| Evidencias privadas | Nombre aleatorio (`uuid4`), porque el original puede traer RUT o nombres. Directorio fuera del código (`SIGED_MEDIA_ROOT`) en un volumen que Apache nunca publica. La entrega sigue por una vista con control de ámbito. | `control_gestion/models.py`, migración `0013` |
| Logs | Salida a stdout con un filtro que oculta RUT, correos, tokens y parámetros de consulta. Fuera de DEBUG, los tracebacks se reducen al tipo de error. Gunicorn no registra IP ni consulta. Los eventos `login_web_limitado`, `recuperacion_limitada` y `salud_bd_no_disponible` no llevan datos personales. | `config/settings.py`, `core/seguridad.py`, `docker/gunicorn.conf.py` |
| Healthcheck | `/salud/` responde `{"estado":"ok"}` o 503, sin detalles. | `core/seguridad.py`, `config/urls.py` |

## 2. Docker (propuesta; comparar con los archivos vigentes en EC2)

- `Dockerfile`: imagen slim, usuario `siged` (UID 10001) sin shell, código propiedad de root, `HEALTHCHECK` contra `/salud/`. Gunicorn queda fijado en `docker/requirements-docker.txt`.
- `docker-compose.yml`:
  - **web**: `read_only` con `tmpfs` en `/tmp`, `cap_drop: ALL`, `no-new-privileges`, `pids_limit` y `mem_limit`. Se publica solo en `127.0.0.1:8000`, detrás de Apache.
  - **db**: MySQL 8.4 en una red `internal` y sin puertos publicados. No recibe el `.env` de Django. La clave root se entrega como secret de Docker. `local-infile=0` y `max-connections=60`.
  - Healthcheck de MySQL sin la clave en la línea de comandos.
  - Rotación de logs con `json-file` (10 MB × 5).
- `docker/entrypoint.sh`: no migra solo. Las migraciones se aplican a mano, después de respaldar.
- `docker/apache-siged.conf.example`: `LimitRequestBody`, `RequestReadTimeout` contra Slowloris, reemplazo de X-Forwarded-For y bloqueo de `/media/` y `/archivos-privados/`.
- `.env.example` y `.dockerignore`: ningún secreto, dato, evidencia ni base entra a la imagen.

**No verificado:** Docker no está instalado en el equipo de prueba. El Compose se validó estructuralmente y el entrypoint con `sh -n`. Hay que confirmar en staging que MySQL arranca con las capacidades listadas y que los volúmenes con nombre heredan el propietario 10001.

## 3. Mitigación DDoS (evaluación, sin contratar recursos)

- **AWS Shield Standard** viene activado sin costo en todas las cuentas. Cubre ataques comunes de red y transporte (L3/L4: inundaciones SYN/UDP y reflexión). No hay que contratar ni configurar nada. Rinde más con CloudFront o Route 53 delante. Sobre una EC2 con IP pública directa, la protección es la de la red de AWS y no filtra L7.
- **Fuera de alcance** porque implican contratar: Shield Advanced (cuota mensual alta), AWS WAF y rate-based rules (cobro por regla y por petición), CloudFront y ALB. AWS Academy además puede restringirlos. Se dejan como recomendación para un entorno productivo municipal.
- **Límites defensivos sin costo, ya incluidos:**
  - cuotas de login, recuperación y API;
  - 413 por tamaño;
  - Gunicorn con `timeout` de 30 s, `limit_request_*` y reciclado de workers;
  - `mem_limit` y `pids_limit` por contenedor;
  - `max-connections` en MySQL;
  - Apache con `RequestReadTimeout`, `LimitRequestBody` y `LimitRequestFields`.
- **Recomendado para el security group** (lo aplica Codex; aquí no se modificó AWS):
  - abrir solo 443, y 80 si redirige;
  - 22 solo desde el rango de EC2 Instance Connect de us-east-1, o cerrado cuando no se usa;
  - 3306 nunca abierto.
- **Opcional sin contratar:** las métricas básicas de CloudWatch ya existen. Una alarma de CPU o red cabe en la capa gratuita, pero crear la alarma es un cambio en AWS que queda a decisión de Codex.

## 4. Correspondencia normativa (orientativa, no es una certificación)

| Referencia | Cobertura |
|---|---|
| ISO/IEC 27001:2022 A.5.15 / 27002 5.15, 8.3 (control de acceso, restricción de acceso a la información) | módulo + delegación + objeto |
| 27002 8.5 (autenticación segura) | cuotas de intentos, sesión en servidor, cookies seguras |
| 27002 8.9 / 8.20 / 8.22 (configuración, seguridad de redes, segregación) | Compose de mínimo privilegio, MySQL en red interna |
| 27002 8.12 / 8.11 (prevención de fuga, enmascaramiento) | logs filtrados, nombres de evidencia aleatorios, cuotas con HMAC |
| 27002 8.15 / 8.16 (registro y monitoreo) | eventos de seguridad sin datos personales, rotación |
| 27002 8.26 / 8.28 (requisitos de seguridad de aplicaciones, codificación segura) | CSRF, ORM parametrizado, validación de cargas |
| ISO/IEC 27701 (PII) y Ley 19.628 (art. 7 deber de secreto, art. 11 cuidado de los datos) | minimización en cookies y logs, recuperación sin enumeración |
| Ley 21.719 (principios de minimización y seguridad, deber de adoptar medidas técnicas; vigencia diferida) | mismas medidas; la retención de logs e IP queda como pendiente organizacional |

## 5. Despliegue sugerido (Codex)

1. Respaldar MySQL (`mysqldump --single-transaction`), el volumen o carpeta de evidencias y la imagen vigente (`docker tag siged-web:actual siged-web:respaldo-AAAAMMDD`).
2. Aplicar el parche y ejecutar `python manage.py migrate`. Las migraciones son `django_session` (ya existe porque `contrib.sessions` está instalado) y `0013`, un `AlterField` sin cambio de esquema.
3. Definir en `.env`: `SIGED_COOKIES_SEGURAS=True`, `SIGED_PROXY_CONFIABLE` (puerta de enlace de Docker), `GUNICORN_FORWARDED_ALLOW_IPS` y `SIGED_MEDIA_ROOT`.
4. Al cambiar el motor de sesión, todos los usuarios deben volver a iniciar sesión una vez.
5. Verificar: `/salud/`, login y logout, una evidencia propia y una ajena (404) y la cuota con la cuenta de prueba.

## 6. Reversión

- **Código:** `patch -R -p1 < siged-seguridad.diff`, o volver a la imagen `siged-web:respaldo-AAAAMMDD`.
- **Migración `0013`:** `python manage.py migrate control_gestion 0012`. Solo cambia el `upload_to`; los archivos ya guardados no cambian de nombre.
- **Sesiones:** al revertir vuelven las cookies firmadas. Se puede ejecutar `python manage.py clearsessions`.
- **Docker:** restaurar los archivos de Compose anteriores. Los volúmenes `mysql-datos` y `evidencias` no se borran con `docker compose down` (no usar `-v`).

## 7. Pendiente

- Política de retención de logs de Apache con IP y de `CodigoUnUso.ip_origen` (Ley 21.719): hay que definir plazo y responsable.
- CSP con nonce: las plantillas usan scripts y estilos en línea, así que requiere su propio trabajo.
- Los permisos iniciales de grupos nuevos no incluyen la consulta de organizaciones para jefatura y funcionario (difieren de la migración 0008).
- Otros mantenedores con delegación (vecinos, atenciones, ausencias) aún permiten guardar sin delegación a perfiles no administradores.
- 2FA para administradores y rotación de `SECRET_KEY` con `SECRET_KEY_FALLBACKS`.

## 8. Alta de usuarios y cuentas de acceso huérfanas

- El error «Ingrese un RUT válido» del alta tenía una causa legítima (dígito verificador incorrecto) pero un mensaje que no la explicaba. Ahora indica el RUT correcto y acepta puntos, espacios, guion opcional y «k» minúscula (`core/validaciones.py`).
- Borrar un *Usuario* desde el admin de Django dejaba su cuenta de acceso (`auth_user`) huérfana, y volver a crear a esa persona fallaba con error 500. El admin ahora borra también esa cuenta (nunca staff ni superusuario) y la vista de alta rechaza con un mensaje claro si ya existe una huérfana.
- `python manage.py cuentas_huerfanas` informa las huérfanas existentes (RUT enmascarado, solo lectura); `--eliminar` borra las que no sean del personal técnico.
- Errores de base durante el alta ya no devuelven 500: la transacción se revierte, se muestra un aviso y el registro no incluye datos personales.
- Delegación: ya no se crea una nueva por escribir mal el nombre. Ficha SGR: se puede vincular una ficha con el mismo RUT y no se sobrescribe un RUT distinto.
