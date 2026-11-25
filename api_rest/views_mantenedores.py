
"""ViewSets de los mantenedores de organizaciones y vecinos."""

from django.utils import timezone
from django.db.models.deletion import ProtectedError

from rest_framework import viewsets, status
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiResponse,
)

from drf_spectacular.types import OpenApiTypes

from control_gestion.models import OrganizacionComunitaria
from requerimientos.models import Vecino

from .permisos import AdminEscribeUsuarioLee, es_admin

from .serializers_mantenedores import (
    OrganizacionAdminSerializer,
    OrganizacionUsuarioSerializer,
    VecinoAdminSerializer,
    VecinoUsuarioSerializer,
)


# RESPUESTAS HTTP PARA SWAGGER

RESPUESTA_400 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Datos invalidos o error de validacion.",
)

RESPUESTA_401 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Token de autenticacion ausente, invalido o expirado.",
)

RESPUESTA_403 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="El usuario no tiene permisos para realizar esta operacion.",
    examples=[
        OpenApiExample(
            "Operacion no autorizada",
            value={
                "error": "Forbidden",
                "detalle": {
                    "detail": (
                        "Su perfil solo permite consultar. "
                        "Las modificaciones requieren perfil administrador."
                    )
                },
            },
            response_only=True,
            status_codes=["403"],
        )
    ],
)

RESPUESTA_404 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="El registro solicitado no existe o no esta disponible.",
)


# EJEMPLOS FICTICIOS PARA SWAGGER

EJEMPLO_ORGANIZACION = {
    "nombre": "Organizacion de Prueba",
    "tipo": "JJVV",
    "territorio": "Norte",
    "correo": "organizacion@example.invalid",
    "presidente_nombre": "Presidente de Prueba",
    "presidente_rut": "33100001-9",
    "socios_activos": 20,
    "activa": True,
}

EJEMPLO_VECINO = {
    "nombre": "Vecino de Prueba",
    "rut": "33100001-9",
    "correo": "vecino@example.invalid",
    "territorio": "Norte",
    "es_simulacion": True,
}


# MANTENEDOR 1: ORGANIZACIONES COMUNITARIAS

@extend_schema_view(
    list=extend_schema(
        summary="Listar organizaciones comunitarias",
        description=(
            "Lista organizaciones que no han sido dadas de baja. "
            "Los administradores pueden visualizar adicionalmente "
            "telefono, correo y RUT de presidente, tesorero y secretario. "
            "Los campos clave_origen y eliminado_en no se exponen."
        ),
        responses={
            200: OrganizacionUsuarioSerializer(many=True),
            401: RESPUESTA_401,
        },
    ),
    retrieve=extend_schema(
        summary="Consultar una organizacion",
        description=(
            "Los campos visibles dependen del perfil del usuario. "
            "Los datos sensibles solo son visibles para administradores."
        ),
        responses={
            200: OrganizacionUsuarioSerializer,
            401: RESPUESTA_401,
            404: RESPUESTA_404,
        },
    ),
    create=extend_schema(
        summary="Crear una organizacion",
        description="Operacion exclusiva para administradores.",
        request=OrganizacionAdminSerializer,
        responses={
            201: OrganizacionAdminSerializer,
            400: RESPUESTA_400,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
        },
        examples=[
            OpenApiExample(
                "Nueva organizacion ficticia",
                value=EJEMPLO_ORGANIZACION,
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Modificar una organizacion",
        description="Operacion exclusiva para administradores.",
        request=OrganizacionAdminSerializer,
        responses={
            200: OrganizacionAdminSerializer,
            400: RESPUESTA_400,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
            404: RESPUESTA_404,
        },
        examples=[
            OpenApiExample(
                "Modificar organizacion ficticia",
                value=EJEMPLO_ORGANIZACION,
                request_only=True,
            )
        ],
    ),
    destroy=extend_schema(
        summary="Dar de baja una organizacion",
        description=(
            "Operacion exclusiva para administradores. "
            "Realiza una baja logica. "
            "El registro permanece en la base de datos, "
            "pero deja de estar disponible en la API."
        ),
        responses={
            204: None,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
            404: RESPUESTA_404,
        },
    ),
)
class OrganizacionViewSet(viewsets.ModelViewSet):

    queryset = OrganizacionComunitaria.objects.filter(
        eliminado_en__isnull=True
    )

    permission_classes = [AdminEscribeUsuarioLee]

    http_method_names = ["get", "post", "put", "delete"]

    def get_serializer_class(self):  # pyright: ignore[reportIncompatibleMethodOverride]

        if getattr(self, "swagger_fake_view", False):
            return OrganizacionUsuarioSerializer

        if es_admin(self.request):
            return OrganizacionAdminSerializer

        return OrganizacionUsuarioSerializer

    def perform_destroy(self, instance):

        instance.eliminado_en = timezone.now()

        instance.save(update_fields=["eliminado_en"])


# MANTENEDOR 2: VECINOS

@extend_schema_view(
    list=extend_schema(
        summary="Listar vecinos",
        description=(
            "Lista los vecinos registrados. "
            "Los campos RUT, telefono y correo "
            "solo son visibles para administradores."
        ),
        responses={
            200: VecinoUsuarioSerializer(many=True),
            401: RESPUESTA_401,
        },
    ),
    retrieve=extend_schema(
        summary="Consultar un vecino",
        description=(
            "Los campos visibles dependen del perfil del usuario. "
            "El administrador puede visualizar RUT, telefono y correo."
        ),
        responses={
            200: VecinoUsuarioSerializer,
            401: RESPUESTA_401,
            404: RESPUESTA_404,
        },
    ),
    create=extend_schema(
        summary="Crear un vecino",
        description="Operacion exclusiva para administradores.",
        request=VecinoAdminSerializer,
        responses={
            201: VecinoAdminSerializer,
            400: RESPUESTA_400,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
        },
        examples=[
            OpenApiExample(
                "Nuevo vecino ficticio",
                value=EJEMPLO_VECINO,
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        summary="Modificar un vecino",
        description="Operacion exclusiva para administradores.",
        request=VecinoAdminSerializer,
        responses={
            200: VecinoAdminSerializer,
            400: RESPUESTA_400,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
            404: RESPUESTA_404,
        },
        examples=[
            OpenApiExample(
                "Modificar vecino ficticio",
                value=EJEMPLO_VECINO,
                request_only=True,
            )
        ],
    ),
    destroy=extend_schema(
        summary="Eliminar un vecino",
        description=(
            "Operacion exclusiva para administradores. "
            "Elimina fisicamente al vecino si no tiene registros "
            "protegidos asociados. En caso contrario, "
            "la API devuelve un error 409."
        ),
        responses={
            204: None,
            401: RESPUESTA_401,
            403: RESPUESTA_403,
            404: RESPUESTA_404,
            409: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="El vecino tiene registros asociados.",
            ),
        },
        examples=[
            OpenApiExample(
                "Vecino con registros protegidos",
                value={
                    "detail": (
                        "No se puede eliminar el vecino porque "
                        "tiene tickets u otros registros asociados."
                    )
                },
                response_only=True,
                status_codes=["409"],
            )
        ],
    ),
)
class VecinoViewSet(viewsets.ModelViewSet):

    queryset = Vecino.objects.all()

    permission_classes = [AdminEscribeUsuarioLee]

    http_method_names = ["get", "post", "put", "delete"]

    def get_serializer_class(self):  # pyright: ignore[reportIncompatibleMethodOverride]

        if getattr(self, "swagger_fake_view", False):
            return VecinoUsuarioSerializer

        if es_admin(self.request):
            return VecinoAdminSerializer

        return VecinoUsuarioSerializer

    def destroy(self, request, *args, **kwargs):

        try:
            return super().destroy(request, *args, **kwargs)

        except ProtectedError:

            return Response(
                {
                    "detail": (
                        "No se puede eliminar el vecino porque "
                        "tiene tickets u otros registros asociados."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
