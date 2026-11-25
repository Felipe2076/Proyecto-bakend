# Sumativa 4 — API RESTful SIGED: reparto Felipe · Aixa · Sakty

## Regla de oro (para no romper la página)

La API nueva vive **aparte**, en una app nueva `api_rest/` y bajo la ruta `/api/v2/`.

- **No se toca:**
  - `/api/v1/`: la usa la app Android.
  - Los modelos: **cero migraciones**.
  - Las vistas y plantillas web existentes.
- **Lo único que se cambia fuera de `api_rest/`** son 4 archivos, y solo los cambia Felipe (Parte 1):
  - `requirements.txt`
  - `config/settings.py`
  - `config/urls.py`
  - `config/middleware.py`
- **Ramas:**
  - Cada una trabaja en su propia rama, creada desde `codigos-backend`.
  - Nadie sube directo a `codigos-backend`, `proyecto-integrado` ni `sumativa-3`. Esas dos últimas son respaldo.
- **Antes de cada push:**
  ```
  SIGED_DB=sqlite python manage.py test
  ```
  Tiene que terminar en `OK` (hoy: 298 pruebas). Si algo falla, no se sube.
- **AWS:** solo lo hace Felipe, al final, con el script de despliegue (respaldo + reversión automática).

## Qué pide la pauta y quién lo hace

| Requisito de la pauta | Quién |
|---|---|
| DRF instalado y configurado en `settings.py` | Felipe |
| JWT (token, refresh, endpoints protegidos) | Felipe |
| Swagger/OpenAPI con botón **Authorize** | Felipe |
| Mantenedor 1 (GET/POST/PUT/DELETE): **Organizaciones comunitarias** | Sakty |
| Mantenedor 2 (GET/POST/PUT/DELETE): **Vecinos** | Sakty |
| Perfil Administrador / Usuario (campos sensibles ocultos) en mantenedores | Sakty |
| Transacción del negocio por API: **Tickets (Requerimientos)** | Aixa |
| Respuestas JSON con códigos HTTP y manejo de errores | Aixa |
| Informe técnico (diagrama, DRF, seguridad, IA, Swagger, AWS, conclusiones) | Aixa (con capturas de los tres) |
| Despliegue en EC2 y evidencias AWS | Felipe |

Orden de trabajo:

1. Felipe hace la Parte 1 y la sube.
2. Aixa y Sakty crean su rama desde esa versión y trabajan **en paralelo**. Sus archivos no se cruzan.
3. Felipe junta las ramas, corre las pruebas y despliega.

---

## Parte 1 — Felipe: base DRF + JWT + Swagger (va primero)

Rama: `api-base`

1. **`requirements.txt`**: agregar 3 líneas.
   - Fijar las versiones exactas que instale `pip`.
   - Revisar que sean compatibles con Django 6.1.
   ```
   djangorestframework
   djangorestframework-simplejwt
   drf-spectacular
   ```
2. **Crear la app** con `python manage.py startapp api_rest`.
   - Borrar `models.py` y `admin.py`: la app no lleva modelos propios.
   - Dejar `api_rest/urls.py` vacío con un `router`, para que Aixa y Sakty registren lo suyo.
3. **`config/settings.py`:**
   ```python
   INSTALLED_APPS += ["rest_framework", "rest_framework_simplejwt", "drf_spectacular", "api_rest"]

   REST_FRAMEWORK = {
       # Solo afecta a las vistas DRF; la web sigue usando sesión normal.
       "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
       "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
       "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
       "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
       "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
       "PAGE_SIZE": 20,
       "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
       "DEFAULT_THROTTLE_RATES": {"anon": "20/min", "user": "120/min"},
       "EXCEPTION_HANDLER": "api_rest.errores.manejar_error",  # lo escribe Aixa
   }
   from datetime import timedelta
   SIMPLE_JWT = {
       "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
       "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
       "ROTATE_REFRESH_TOKENS": True,
       "AUTH_HEADER_TYPES": ("Bearer",),
   }
   SPECTACULAR_SETTINGS = {"TITLE": "SIGED API", "VERSION": "2.0.0", "SERVE_INCLUDE_SCHEMA": False}
   ```
   Mientras Aixa no suba `errores.py`, comentar la línea `EXCEPTION_HANDLER`.
4. **`config/urls.py`:** una línea, antes de las rutas `""`:
   ```python
   path("api/v2/", include("api_rest.urls")),
   ```
5. **`config/middleware.py`, línea 42:** agregar `/api/v2/` a las rutas exentas del login web. Sin esto, la API redirige a `/login/`.
   ```python
   if request.path.startswith(('/admin/', '/api/v1/', '/api/v2/')):
   ```
6. **`api_rest/urls.py`:**
   ```python
   from django.urls import include, path
   from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
   from rest_framework.routers import DefaultRouter
   from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

   router = DefaultRouter()
   # Sakty y Aixa registran aquí sus ViewSets (router.register(...)).

   urlpatterns = [
       path("token/", TokenObtainPairView.as_view(), name="api_token"),
       path("token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
       path("esquema/", SpectacularAPIView.as_view(permission_classes=[]), name="api_esquema"),
       path("docs/", SpectacularSwaggerView.as_view(url_name="api_esquema", permission_classes=[]), name="api_docs"),
       path("", include(router.urls)),
   ]
   ```
7. **`api_rest/permisos.py`:** lo usan Sakty y Aixa. Reutiliza el rol que ya existe en SIGED.
   ```python
   from rest_framework.permissions import BasePermission, SAFE_METHODS
   from cuentas.alcance import es_superusuario
   from cuentas.models import Usuario

   def perfil_de(request):
       return Usuario.objects.select_related("rol").filter(user=request.user).first()

   def es_admin(request):
       return request.user.is_staff or es_superusuario(perfil_de(request))

   class AdminEscribeUsuarioLee(BasePermission):
       """Usuario: solo lectura. Administrador: todo."""
       def has_permission(self, request, view):
           return request.method in SAFE_METHODS or es_admin(request)
   ```
8. **Probar en local:**
   - Abrir `/api/v2/docs/`.
   - Con `POST /api/v2/token/` (RUT y clave de prueba) obtener un token.
   - Pegar el token en **Authorize** y llamar a un endpoint protegido.
9. **Subir y avisar:** subir `api-base` y avisar a Aixa y Sakty para que creen su rama desde ella.

**Al final:**
- Juntar las 3 ramas en `codigos-backend` y correr las pruebas.
- Desplegar en AWS. **Ojo:** las dependencias nuevas obligan a reconstruir la imagen Docker; eso se hace con respaldo.
- Sacar las capturas de AWS: instancia, IP, Swagger y consumo de endpoints.

---

## Parte 2 — Sakty: Mantenedores 1 y 2 (Organizaciones y Vecinos)

Rama: `api-mantenedores` (crearla desde `api-base`).
Archivos: solo `api_rest/serializers_mantenedores.py`, `api_rest/views_mantenedores.py`, `api_rest/tests_mantenedores.py` y 2 líneas en `api_rest/urls.py`.

1. **Serializers diferenciados:** el administrador ve todo; el usuario no ve datos sensibles.
   ```python
   from rest_framework import serializers
   from control_gestion.models import OrganizacionComunitaria
   from requerimientos.models import Vecino

   class OrganizacionAdminSerializer(serializers.ModelSerializer):
       class Meta:
           model = OrganizacionComunitaria
           exclude = ["clave_origen", "eliminado_en"]

   class OrganizacionUsuarioSerializer(serializers.ModelSerializer):
       class Meta:
           model = OrganizacionComunitaria
           exclude = ["clave_origen", "eliminado_en", "telefono", "correo",
                      "presidente_rut", "tesorero_rut", "secretario_rut"]

   class VecinoAdminSerializer(serializers.ModelSerializer):
       class Meta:
           model = Vecino
           fields = "__all__"

   class VecinoUsuarioSerializer(serializers.ModelSerializer):
       class Meta:
           model = Vecino
           exclude = ["rut", "telefono", "correo"]
   ```
   Para validar el RUT, reutilizar la validación de `core/validaciones.py`. **No escribir una nueva.**
2. **ViewSets:**
   ```python
   from django.db.models import ProtectedError
   from rest_framework import status, viewsets
   from rest_framework.response import Response
   from api_rest.permisos import AdminEscribeUsuarioLee, es_admin
   from . import serializers_mantenedores as s

   class OrganizacionViewSet(viewsets.ModelViewSet):
       permission_classes = [AdminEscribeUsuarioLee]
       http_method_names = ["get", "post", "put", "delete"]
       lookup_field = "codigo"

       def get_queryset(self):
           return OrganizacionComunitaria.objects.filter(eliminado_en__isnull=True).order_by("-pk")

       def get_serializer_class(self):
           return s.OrganizacionAdminSerializer if es_admin(self.request) else s.OrganizacionUsuarioSerializer

       def perform_destroy(self, org):
           # La web hace baja lógica: aquí igual, no se borra de la base.
           from django.utils import timezone
           org.eliminado_en = timezone.now()
           org.save(update_fields=["eliminado_en"])
   ```
   - El `VecinoViewSet` es igual, pero sin baja lógica.
   - En `destroy`, capturar `ProtectedError` (un vecino con tickets no se puede borrar) y responder 409 con un mensaje claro.
3. **Registrar las rutas en `api_rest/urls.py`:**
   ```python
   router.register("organizaciones", OrganizacionViewSet, basename="organizaciones")
   router.register("vecinos", VecinoViewSet, basename="vecinos")
   ```
4. **Swagger:** agregar `@extend_schema(summary=..., examples=[OpenApiExample(...)])` de drf-spectacular en los ViewSets, para que la documentación muestre ejemplos JSON.
5. **Pruebas en `tests_mantenedores.py`:**
   - Sin token, responde 401.
   - Un usuario normal no ve `telefono`, `correo` ni los RUT.
   - Un usuario normal que hace POST recibe 403.
   - El administrador puede crear, editar y borrar.
   - Un DELETE de organización la deja con `eliminado_en`; no la borra.
6. **Datos:** solo datos ficticios en las pruebas, como en `pruebas_locales/crear_demo.py`.

---

## Parte 3 — Aixa: Transacción (Tickets), errores JSON e Informe

Rama: `api-transaccion` (crearla desde `api-base`).
Archivos: solo `api_rest/serializers_tickets.py`, `api_rest/views_tickets.py`, `api_rest/errores.py`, `api_rest/tests_tickets.py`, 1 línea en `api_rest/urls.py`, y el informe.

1. **Tickets por API:** la transacción une Vecino (mantenedor 2), delegación, área y funcionario.
   - **Ruta:** `router.register("tickets", TicketViewSet, basename="tickets")`, con `lookup_field = "codigo"` (TK-1001).
   - **GET:** usar `control_gestion.kanban.tickets_visibles(perfil)`. Así cada usuario ve solo los tickets de su delegación, igual que en la web. **No filtrar a mano.**
   - **POST:** crear el ticket con `requerimientos.consultas.crear_requerimiento(valores)`, que ya genera el código TK-xxxx y aplica las reglas del negocio. **No usar `Requerimiento.objects.create`.**
   - **PUT:** permitir cambiar solo `estado`, `descripcion` y `funcionario`. El código y el vecino quedan como `read_only`.
   - **DELETE:** solo el administrador (`es_admin`). Para el resto, 403.
   - **Datos sensibles:** el serializer de usuario muestra el vecino solo con su nombre, sin RUT, teléfono ni correo.
2. **`api_rest/errores.py`:** un solo formato JSON para todos los errores.
   ```python
   import logging
   from rest_framework.views import exception_handler
   from rest_framework.response import Response

   log = logging.getLogger(__name__)

   def manejar_error(exc, context):
       respuesta = exception_handler(exc, context)
       if respuesta is None:  # error no previsto → 500 sin filtrar detalles internos
           log.exception("Error no controlado en la API")
           return Response({"error": "Error interno del servidor."}, status=500)
       respuesta.data = {"error": respuesta.status_text, "detalle": respuesta.data}
       return respuesta
   ```
   Cuando esté subido, avisar a Felipe para que descomente `EXCEPTION_HANDLER` en settings.
3. **Pruebas en `tests_tickets.py`:**
   - POST crea el ticket y responde 201 con un código TK-.
   - Datos inválidos responden 400.
   - Un ticket de otra delegación responde 404.
   - Un DELETE de usuario normal responde 403.
   - Un token vencido o falso responde 401.
4. **Informe técnico** (estructura de la pauta, pág. 8–9):
   - Introducción.
   - Diagrama lógico: Cliente Web / App → API REST `/api/v2` → Django → MySQL, todo dentro de EC2 (Docker).
   - DRF: configuración, serializers y endpoints. Pedir los fragmentos a Felipe y Sakty.
   - Seguridad: JWT de 15 min con rotación, permisos por rol, campos ocultos, límite de peticiones y errores sin datos internos.
   - Recomendaciones de IA: anotar cada recomendación usada, por ejemplo token corto, *throttling*, no exponer RUT ni correo, y errores 500 genéricos.
   - Swagger: capturas de **Authorize** y de una llamada protegida.
   - AWS: las capturas las saca Felipe.
   - Conclusiones.

---

## Checklist final (Felipe, antes de la presentación)

- [ ] Las 3 ramas juntas en `codigos-backend` y las pruebas en `OK`.
- [ ] La web sigue funcionando igual: login, tablero, tickets y la app Android (`/api/v1/`).
- [ ] `/api/v2/docs/` abre en AWS, **Authorize** funciona, el refresh entrega un token nuevo y sin token responde 401.
- [ ] Usuario normal vs administrador: se ven campos distintos (captura de los dos).
- [ ] Copia final también en `proyecto-integrado` (respaldo).
