"""Evidencias desde la web: listar y subir fotos/PDF de compromisos y tickets desde la tarjeta, la fila o la ficha.

Mismo alcance por delegación que las pantallas de origen y la misma validación de archivos que la app
(control_gestion.evidencias.validar_archivo: JPG/PNG/PDF reales, máximo 10 MB). Máximo 10 evidencias por registro.
"""
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from control_gestion.evidencias import validar_archivo
from control_gestion.kanban import perfil_actual, tickets_visibles
from control_gestion.models import Compromiso, EvidenciaCompromiso
from cuentas.auth import puede_ver
from requerimientos.models import EvidenciaRequerimiento

MAXIMO = 10
TIPOS = {
    # tipo: (módulo, modelo de evidencia, campo FK, ruta para ver el archivo, ruta de la ficha)
    "compromiso": ("compromisos", EvidenciaCompromiso, "compromiso", "evidencia_compromiso", "compromiso_detalle"),
    "ticket": ("requerimientos", EvidenciaRequerimiento, "requerimiento", "ver_evidencia_ticket", "detalle_requerimiento"),
}


def _registro(perfil, tipo, codigo):
    """Compromiso o ticket dentro del alcance del perfil, o None."""
    if tipo == "compromiso":
        from control_gestion.reportes import ambito
        return ambito(Compromiso.objects.all(), perfil).filter(codigo=codigo).first()
    return tickets_visibles(perfil).filter(codigo=codigo).first()


def _json(e, tipo):
    nombre = e.archivo.name.rsplit("/", 1)[-1]
    return {
        "id": e.pk, "tipo": e.tipo, "es_pdf": e.tipo == "DOCUMENTO", "descripcion": e.descripcion,
        "url": reverse(TIPOS[tipo][3], args=[e.pk]), "nombre": nombre,
        "fecha": e.fecha.strftime("%d/%m/%Y %H:%M"),
        "autor": _autor(e),
    }


def _autor(e):
    """Nombre del perfil SIGED de quien subió la evidencia (el usuario de Django es el RUT)."""
    if not e.subido_por_id:
        return ""
    from cuentas.models import Usuario
    perfil = Usuario.objects.filter(user_id=e.subido_por_id).only("nombre").first()
    return perfil.nombre if perfil else (e.subido_por.get_full_name() or e.subido_por.username)


@never_cache
@require_http_methods(["GET", "POST"])
def evidencias(request, tipo, codigo):
    if tipo not in TIPOS:
        raise Http404
    modulo, Modelo, campo, _ver, ficha = TIPOS[tipo]
    perfil = perfil_actual(request)
    if perfil is None:
        return JsonResponse({"error": "Su sesión terminó. Ingrese nuevamente."}, status=401)
    if not puede_ver(perfil, modulo):
        return JsonResponse({"error": "Su perfil no tiene acceso a este módulo."}, status=403)
    registro = _registro(perfil, tipo, codigo)
    if registro is None:
        return JsonResponse({"error": "No existe o no pertenece a su delegación."}, status=404)
    quiere_json = "application/json" in request.headers.get("Accept", "")
    if request.method == "POST":
        archivo = request.FILES.get("archivo")
        error = None
        if archivo is None:
            error = "Adjunte una foto (JPG o PNG) o un documento PDF."
        elif Modelo.objects.filter(**{campo: registro}).count() >= MAXIMO:
            error = f"Ya tiene {MAXIMO} evidencias, que es el máximo."
        else:
            try:
                validar_archivo(archivo)
            except ValueError as motivo:
                error = str(motivo)
        if error:
            if quiere_json:
                return JsonResponse({"error": error}, status=422)
            from django.contrib import messages
            messages.error(request, error)
            return redirect(ficha, codigo)
        Modelo.objects.create(**{campo: registro}, archivo=archivo,
                              tipo="DOCUMENTO" if archivo.name.lower().endswith(".pdf") else "FOTO",
                              descripcion=" ".join(request.POST.get("descripcion", "").split())[:200],
                              subido_por=request.user)
        if not quiere_json:
            from django.contrib import messages
            messages.success(request, "Evidencia subida.")
            return redirect(ficha, codigo)
    lista = [_json(e, tipo) for e in Modelo.objects.filter(**{campo: registro}).select_related("subido_por")]
    return JsonResponse({"codigo": codigo, "tipo": tipo, "evidencias": lista, "cantidad": len(lista), "maximo": MAXIMO,
                         "ficha": reverse(ficha, args=[codigo])}, status=201 if request.method == "POST" else 200)


@never_cache
@require_safe
def ver_evidencia_ticket(request, pk):
    """Archivo de evidencia de un ticket, con el alcance del tablero."""
    perfil = perfil_actual(request)
    if perfil is None or not puede_ver(perfil, "requerimientos"):
        raise Http404("Sin evidencia")
    e = EvidenciaRequerimiento.objects.filter(pk=pk).first()
    if e is None or not tickets_visibles(perfil).filter(pk=e.requerimiento_id).exists():
        raise Http404("Sin evidencia")
    nombre = e.archivo.name.lower()
    tipo = "application/pdf" if nombre.endswith(".pdf") else ("image/png" if nombre.endswith(".png") else "image/jpeg")
    r = FileResponse(e.archivo.open("rb"), content_type=tipo)
    r["X-Content-Type-Options"] = "nosniff"
    r["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return r
