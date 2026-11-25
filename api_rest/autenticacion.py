"""Obtención de token JWT con RUT y clave, usando el mismo autenticador que el login web."""
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from cuentas.servicios import autenticar


class TokenSerializer(serializers.Serializer):
    rut = serializers.CharField(max_length=32)
    password = serializers.CharField(max_length=256, write_only=True, style={"input_type": "password"})


class TokenRespuesta(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class ObtenerToken(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    @extend_schema(
        tags=["Autenticación"], summary="Obtener access y refresh token con RUT y clave",
        request=TokenSerializer, responses={200: TokenRespuesta},
        examples=[OpenApiExample("Ingreso", value={"rut": "11.111.111-1", "password": "********"}, request_only=True)])
    def post(self, request):
        datos = TokenSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        perfil = autenticar(datos.validated_data["rut"], datos.validated_data["password"])
        if perfil is None or not perfil.user_id:
            # Mismo mensaje para RUT inexistente o clave mala: no revela qué cuentas existen.
            return Response({"error": "Unauthorized", "detalle": "RUT o clave incorrectos."},
                            status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(perfil.user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
