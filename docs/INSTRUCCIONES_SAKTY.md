# Sakty — tu parte de la Sumativa 4: Mantenedores 1 y 2 por API

La base de la API ya está lista en la rama `codigos-backend`:

- DRF configurado.
- JWT: `/api/v2/token/` y `/api/v2/token/refresh/`.
- Swagger en `/api/v2/docs/`.
- Permisos por rol en `api_rest/permisos.py`.
- Errores en JSON.

**Tú solo agregas los mantenedores.**

## 1. Preparar el proyecto (una vez)

Necesitas **Python 3.12 o más nuevo**, porque Django 6.1 no funciona con versiones anteriores. Revisa tu versión con `python --version`.

```
git clone https://github.com/Felipe2076/Proyecto-bakend.git
cd Proyecto-bakend
git checkout codigos-backend
git checkout -b api-mantenedores
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` ya trae todas las dependencias: Django, DRF, SimpleJWT, drf-spectacular y PyJWT. No hay que instalar nada más.

**SweetAlert no se usa.** Tu parte es solo API: responde JSON y no tiene pantallas. Lo que se muestra es Swagger, y Swagger ya viene incluido.

## 2. Reglas para no romper la página

- **Qué archivos tocas:** solo estos, dentro de `api_rest/`:
  - `serializers_mantenedores.py` (nuevo)
  - `views_mantenedores.py` (nuevo)
  - `tests_mantenedores.py` (nuevo)
  - 2 líneas en `urls.py`
- **No toques:**
  - `config/settings.py` ni `config/middleware.py`.
  - Los modelos: **nada de migraciones**.
  - Las vistas y plantillas web.
  - `/api/v1/` (`control_gestion/api_movil.py`, `api_sincronizacion.py`): es la app Android.
- **Ramas:** sube solo `api-mantenedores`. **Nunca** subas a `codigos-backend`, `proyecto-integrado` ni `sumativa-3`; esas son respaldo.
- **Datos:** solo datos inventados. Nunca uses RUT, correos ni teléfonos reales.
- **Pruebas que ya existen:** si una falla, no la cambies. Pregúntale a Felipe.

## 3. Qué tienes que hacer

### a) Serializers (`api_rest/serializers_mantenedores.py`)

Haz dos por modelo, uno para el administrador (ve todo) y otro para el usuario (sin datos sensibles).

| Modelo | Administrador ve | Usuario **no** ve |
|---|---|---|
| `control_gestion.models.OrganizacionComunitaria` | todo menos `clave_origen` y `eliminado_en` | además `telefono`, `correo`, `presidente_rut`, `tesorero_rut`, `secretario_rut` |
| `requerimientos.models.Vecino` | todo | `rut`, `telefono`, `correo` |

Para validar el RUT usa `core/validaciones.py` (`validar_rut`, `normalizar_rut`). **No escribas una validación nueva.**

### b) ViewSets (`api_rest/views_mantenedores.py`)

Haz `OrganizacionViewSet` y `VecinoViewSet`, basados en `viewsets.ModelViewSet`.

- **Métodos:** `http_method_names = ["get", "post", "put", "delete"]`.
- **Permisos:** `permission_classes = [AdminEscribeUsuarioLee]`, desde `api_rest.permisos`. El usuario solo lee; el administrador hace todo.
- **Serializer según el perfil:** en `get_serializer_class()`, si `es_admin(self.request)` usa el serializer de administrador; si no, el de usuario.
- **Organizaciones:**
  - El queryset es `filter(eliminado_en__isnull=True)`.
  - El **DELETE es baja lógica**: guarda `eliminado_en = timezone.now()` y no borres el registro, igual que la web.
- **Vecinos:** si el DELETE lanza `django.db.models.ProtectedError` (el vecino tiene tickets), responde **409** con un mensaje claro.
- **Swagger:** agrega `@extend_schema(tags=[...], summary=..., examples=[OpenApiExample(...)])` de `drf_spectacular.utils` para que muestre ejemplos JSON.

### c) Rutas (`api_rest/urls.py`)

Debajo de `router = DefaultRouter()`:

```python
from api_rest.views_mantenedores import OrganizacionViewSet, VecinoViewSet
router.register("organizaciones", OrganizacionViewSet, basename="organizaciones")
router.register("vecinos", VecinoViewSet, basename="vecinos")
```

### d) Pruebas (`api_rest/tests_mantenedores.py`)

Copia cómo están hechas las de `api_rest/tests.py`:

- Las cuentas se crean con `crear_cuenta`.
- El token se pide con `POST /api/v2/token/`.

Tus pruebas tienen que comprobar estos casos:

- Sin token, responde 401.
- Un usuario normal no recibe `telefono`, `correo` ni los RUT.
- Un usuario normal que hace POST, PUT o DELETE recibe 403.
- El administrador puede crear (201), editar (200) y borrar (204).
- El DELETE de una organización la deja con `eliminado_en` y sigue en la base.

**Ojo con los RUT de prueba:** el dígito verificador tiene que ser correcto. Si no, el login responde 401 aunque la clave esté bien. Para calcularlo:

```
python -c "from core.validaciones import dv_rut; print(dv_rut('33100150'))"
```

## 4. Correr las pruebas (antes de cada push)

Corre las pruebas **sin** `DEBUG`. Con `DEBUG=1` falla una prueba de seguridad de cookies.

```
set SIGED_DB=sqlite
set SECRET_KEY=solo-pruebas-locales-siged-no-usar-en-produccion-7d2f
python manage.py test
```

Tiene que terminar en `OK`. Hoy son 306 pruebas, más las tuyas. Usa una clave larga como esa: con una corta, JWT avisa que la clave es insegura.

## 5. Probar a mano y sacar capturas

Los scripts de `pruebas_locales/` crean una base SQLite con usuarios **ficticios** y levantan la página. No tocan MySQL ni AWS.

```
python pruebas_locales\crear_demo.py
python pruebas_locales\servidor.py
```

Los usuarios y la clave están en `pruebas_locales/USUARIOS_DE_PRUEBA.txt`. Para las capturas usa estos dos:

- Administrador: superusuario `33.100.011-6`.
- Usuario normal: funcionario `33.100.032-9`.

`crear_demo.py` borra y vuelve a crear la base de prueba cada vez que lo corres.

1. Abre `http://127.0.0.1:8765/api/v2/docs/`.
2. Pide el token en `POST /api/v2/token/` con el RUT y la clave de una de esas cuentas.
3. Copia el `access`, presiona **Authorize** y pégalo.
4. Prueba GET, POST, PUT y DELETE de `organizaciones` y `vecinos`.
5. Saca capturas con un **usuario normal** y con un **administrador**: se tienen que ver campos distintos. Las capturas son para el informe de Aixa.

## 6. Subir

```
git add api_rest/
git commit -m "API v2: mantenedores Organizaciones y Vecinos"
git push origin api-mantenedores
```

Después avísale a Felipe. Él lo revisa, lo junta en `codigos-backend` y lo sube a AWS.
