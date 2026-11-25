"""Permisos por rol para la API v2. Reutiliza el rol SIGED (superusuario) y is_staff."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from cuentas.alcance import es_superusuario
from cuentas.models import EstadoRegistro, Usuario


def perfil_de(request):
    if not getattr(request.user, "is_authenticated", False):
        return None
    return Usuario.objects.select_related("rol", "delegacion").filter(
        user=request.user, estado=EstadoRegistro.ACTIVO).first()


def es_admin(request):
    return bool(request.user.is_staff or es_superusuario(perfil_de(request)))


class AdminEscribeUsuarioLee(BasePermission):
    """Perfil Usuario: solo lectura. Perfil Administrador: todas las operaciones."""
    message = "Su perfil solo permite consultar. Las modificaciones requieren perfil administrador."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and (request.method in SAFE_METHODS or es_admin(request)))
