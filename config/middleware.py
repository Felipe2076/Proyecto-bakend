from django.shortcuts import redirect


RUTAS_PREFIJO_LIBRES = ("/static/", "/admin/")
RUTAS_EXACTAS_LIBRES = {"/login/", "/logout/"}


class AutenticacionMockMiddleware:
    """Exige sesión mock en todas las pantallas del mockup, excepto login y estáticos."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        libre = path in RUTAS_EXACTAS_LIBRES or any(path.startswith(prefijo) for prefijo in RUTAS_PREFIJO_LIBRES)
        if libre:
            return self.get_response(request)
        if not request.session.get("usuario"):
            destino = path
            if request.GET:
                destino = request.get_full_path()
            return redirect(f"/login/?next={destino}")
        return self.get_response(request)
