from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from api_rest.autenticacion import ObtenerToken
from api_rest.views import Yo

router = DefaultRouter()
# Mantenedores y transacción se registran aquí: router.register("ruta", ViewSet, basename="...")

urlpatterns = [
    path("token/", ObtenerToken.as_view(), name="api_token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("yo/", Yo.as_view(), name="api_yo"),
    path("esquema/", SpectacularAPIView.as_view(permission_classes=[], authentication_classes=[]), name="api_esquema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_esquema", permission_classes=[], authentication_classes=[]),
         name="api_docs"),
    path("", include(router.urls)),
]
