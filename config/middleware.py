from django.shortcuts import redirect


RUTAS_PREFIJO_LIBRES = ("/static/", "/admin/", "/recuperar")
# Sitio público (app publico). /recuperar cubre /recuperar/, /recuperar/codigo/ y /recuperar/nueva/.
RUTAS_PUBLICAS = {
    "/",
    "/municipio/",
    "/servicios/",
    "/tramites/",
    "/delegaciones/",
    "/noticias/",
    "/transparencia/",
    "/contacto/",
    "/creditos/",
}
RUTAS_EXACTAS_LIBRES = {
    "/activar/",
    "/login/",
    "/logout/",
    "/recuperar/",
    "/recuperar/codigo/",
    "/recuperar/nueva/",
} | RUTAS_PUBLICAS


class AutenticacionMockMiddleware:
    """Exige autenticación Django y actualiza los permisos en cada petición."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth import logout
        from cuentas.models import Usuario, EstadoRegistro
        from cuentas.servicios import sesion_desde_usuario
        if request.user.is_authenticated:
            perfil = Usuario.objects.select_related('user','rol','rol__grupo','funcionario','funcionario__delegacion','cargo','delegacion').filter(
                user=request.user, estado=EstadoRegistro.ACTIVO, user__is_active=True).first()
            if perfil is None:
                logout(request)
            else:
                request._perfil_siged = perfil
                request.session['usuario'] = sesion_desde_usuario(perfil)
        else:
            request.session.pop('usuario', None)
        path = request.path
        libre = path in RUTAS_EXACTAS_LIBRES or any(path.startswith(prefijo) for prefijo in RUTAS_PREFIJO_LIBRES)
        if libre:
            return self.get_response(request)
        if not request.user.is_authenticated or not request.session.get("usuario"):
            if 'application/json' in request.headers.get('Accept',''):
                from django.http import JsonResponse
                return JsonResponse({'error':'La sesión terminó. Vuelva a iniciar sesión.'},status=401)
            destino = path
            if request.GET:
                destino = request.get_full_path()
            return redirect(f"/login/?next={destino}")
        return self.get_response(request)
