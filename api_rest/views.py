from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from api_rest.permisos import es_admin, perfil_de


class Yo(APIView):
    """Endpoint protegido de prueba: devuelve el perfil de quien envía el token."""

    @extend_schema(tags=["Autenticación"], summary="Perfil del token actual (requiere Bearer)")
    def get(self, request):
        perfil = perfil_de(request)
        return Response({
            "nombre": str(perfil.funcionario) if perfil and perfil.funcionario_id else request.user.get_username(),
            "rol": perfil.rol.nombre if perfil else None,
            "perfil_api": "administrador" if es_admin(request) else "usuario",
        })
