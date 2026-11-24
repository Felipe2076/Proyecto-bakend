"""Búsqueda inteligente de la barra superior y autocompletado de vecinos por RUT.

- Busca tickets, vecinos, organizaciones y compromisos mientras se escribe, sin tildes y por RUT.
- Si no hay resultados, corrige faltas de ortografía comparando con los nombres reales («Gonzales» → «González»).
- Todo respeta el alcance: cada perfil ve solo su delegación (el superusuario, todas) y solo los módulos permitidos.
"""
import difflib
import re

from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from control_gestion.consultas import queryset_compromisos
from control_gestion.kanban import perfil_actual, tickets_visibles
from control_gestion.models import OrganizacionComunitaria
from core.busqueda import buscar, normalizar
from cuentas.auth import puede_ver
from requerimientos.models import Vecino

POR_GRUPO = 5


def _en_alcance(qs, perfil):
    if perfil.rol.codigo == "superusuario":
        return qs
    return qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()


def _fuentes(perfil, user):
    """(clave, título, ícono, queryset, campos de búsqueda, función que arma cada resultado, campo de nombre)."""
    fuentes = []
    if puede_ver(perfil, "requerimientos"):
        fuentes.append(("tickets", "Tickets", "ticket-detailed", tickets_visibles(perfil).select_related("vecino"),
                        ["codigo", "descripcion", "vecino__nombre", "vecino__rut"],
                        lambda t: {"texto": f"{t.codigo} · {t.vecino.nombre_mostrado}", "detalle": f"{t.get_estado_display()} · {t.descripcion[:70]}",
                                   "url": reverse("detalle_requerimiento", args=[t.codigo])}, "vecino__nombre"))
        fuentes.append(("vecinos", "Vecinos", "person", _en_alcance(Vecino.objects.all(), perfil),
                        ["nombre", "rut", "telefono", "correo", "direccion"],
                        lambda v: {"texto": v.nombre_mostrado + (" · Extranjero/a" if v.es_extranjero else ""),
                                   "detalle": " · ".join(x for x in (v.rut or "", v.nacionalidad or "", v.telefono, v.direccion) if x),
                                   "url": reverse("nuevo_requerimiento") + f"?vecino_rut={v.rut or ''}",
                                   "ficha": reverse("ficha_vecino", args=[v.pk])}, "nombre"))
    if user.has_perm("control_gestion.view_organizacioncomunitaria"):
        fuentes.append(("organizaciones", "Organizaciones", "buildings",
                        _en_alcance(OrganizacionComunitaria.objects.filter(activa=True), perfil),
                        ["codigo", "nombre", "territorio", "presidente_nombre", "presidente_rut"],
                        lambda o: {"texto": o.nombre, "detalle": " · ".join(x for x in (o.codigo, o.territorio) if x),
                                   "url": reverse("mant_organizaciones_editar", args=[o.pk])}, "nombre"))
    if puede_ver(perfil, "compromisos"):
        fuentes.append(("compromisos", "Compromisos", "kanban", _en_alcance(queryset_compromisos(), perfil),
                        ["codigo", "descripcion", "vecino__nombre", "funcionario__nombre"],
                        lambda c: {"texto": f"{c.codigo} · {c.descripcion[:60]}", "detalle": f"{c.funcionario.nombre} · plazo {c.fecha_compromiso:%d/%m/%Y}",
                                   "url": reverse("compromiso_detalle", args=[c.codigo])}, "descripcion"))
    return fuentes


def _corregir(texto, fuentes):
    """Propone la palabra real más parecida a cada palabra escrita (tolera 1-2 letras distintas)."""
    vocabulario = set()
    for *_, qs, _campos, _armar, campo_nombre in fuentes:
        for valor in qs.values_list(campo_nombre, flat=True)[:3000]:
            vocabulario.update(p for p in normalizar(valor).split() if len(p) > 2)
    corregidas, cambio = [], False
    for palabra in normalizar(texto).split():
        if palabra in vocabulario or len(palabra) < 4:
            corregidas.append(palabra); continue
        parecidas = difflib.get_close_matches(palabra, vocabulario, n=1, cutoff=0.75)
        corregidas.append(parecidas[0] if parecidas else palabra)
        cambio = cambio or bool(parecidas)
    return " ".join(corregidas) if cambio else None


def _resultados(texto, fuentes):
    grupos = []
    for clave, titulo, icono, qs, campos, armar, _ in fuentes:
        items = [armar(obj) for obj in buscar(qs, texto, campos)[:POR_GRUPO]]
        if items:
            grupos.append({"clave": clave, "titulo": titulo, "icono": icono, "items": items})
    return grupos


@never_cache
@require_GET
def sugerencias(request):
    perfil = perfil_actual(request)
    if perfil is None:
        return JsonResponse({"error": "Sesión vencida."}, status=401)
    texto = " ".join(request.GET.get("q", "").split())[:80]
    if len(texto) < 2:
        return JsonResponse({"grupos": [], "sugerencia": None})
    fuentes = _fuentes(perfil, request.user)
    grupos = _resultados(texto, fuentes)
    sugerencia = None
    if not grupos and len(texto) >= 4 and not re.search(r"\d", texto):
        sugerencia = _corregir(texto, fuentes)
        if sugerencia:
            grupos = _resultados(sugerencia, fuentes)
    return JsonResponse({"grupos": grupos, "sugerencia": sugerencia})


@never_cache
@require_GET
def vecino_por_rut(request):
    """Datos del vecino ya registrado, para completar solo el formulario al escribir su RUT."""
    from core.validaciones import normalizar_rut, validar_rut

    perfil = perfil_actual(request)
    if perfil is None or not puede_ver(perfil, "requerimientos"):
        return JsonResponse({"error": "Sin acceso."}, status=403)
    rut = (request.GET.get("rut") or "").strip()
    if not validar_rut(rut):
        return JsonResponse({"encontrado": False, "valido": False})
    normal = normalizar_rut(rut)
    vecino = (_en_alcance(Vecino.objects.all(), perfil).filter(rut=normal).first()
              or Vecino.objects.filter(rut=normal, delegacion__isnull=True).first())
    if vecino is None:
        return JsonResponse({"encontrado": False, "valido": True})
    return JsonResponse({"encontrado": True, "valido": True, "vecino": {
        "nombre": vecino.nombre_mostrado, "telefono": vecino.telefono, "correo": vecino.correo,
        "direccion": vecino.direccion, "territorio": vecino.territorio,
        "delegacion": vecino.delegacion.nombre if vecino.delegacion else "",
        "es_extranjero": vecino.es_extranjero, "nacionalidad": vecino.nacionalidad or "",
        "tickets": tickets_visibles(perfil).filter(vecino=vecino).count(),
    }})


FASES = ["INGRESADO", "PENDIENTE", "EN PROCESO", "REALIZADO"]


def _periodo(fecha):
    """Trimestre configurado que contiene la fecha; si no hay, el trimestre del calendario."""
    from control_gestion.models import Medicion
    from control_gestion.trimestres import trimestre_calendario

    m = Medicion.objects.filter(fecha_inicio__lte=fecha, fecha_termino__gte=fecha).order_by("-fecha_inicio").first()
    return m.periodo if m else trimestre_calendario(fecha)["periodo"]


@never_cache
@require_GET
def ficha_vecino(request, pk):
    """Ficha emergente del buscador: datos del vecino, nacionalidad, sus actividades (4 fases) y tickets."""
    from django.utils import timezone

    from core.validaciones import formatear_rut

    perfil = perfil_actual(request)
    if perfil is None or not puede_ver(perfil, "requerimientos"):
        return JsonResponse({"error": "Sin acceso."}, status=403)
    vecino = _en_alcance(Vecino.objects.select_related("delegacion"), perfil).filter(pk=pk).first()
    if vecino is None:
        return JsonResponse({"error": "No encontrado."}, status=404)
    hoy = timezone.localdate()
    actividades = []
    if puede_ver(perfil, "compromisos"):
        for c in _en_alcance(queryset_compromisos(), perfil).filter(vecino=vecino).order_by("-fecha_ingreso")[:20]:
            fase = FASES.index(c.estado) if c.estado in FASES else 0
            actividades.append({
                "codigo": c.codigo, "descripcion": c.descripcion, "funcionario": c.funcionario.nombre,
                "periodo": _periodo(c.fecha_ingreso), "ingreso": c.fecha_ingreso.strftime("%d/%m/%Y"),
                "plazo": c.fecha_compromiso.strftime("%d/%m/%Y"), "estado": c.get_estado_display(), "fase": fase,
                "vencido": c.estado != "REALIZADO" and c.fecha_compromiso < hoy,
                "url": reverse("compromiso_detalle", args=[c.codigo]),
            })
    tickets = [{
        "codigo": r.codigo, "estado": r.get_estado_display(), "fecha": r.fecha_ingreso.strftime("%d/%m/%Y"),
        "periodo": _periodo(r.fecha_ingreso), "descripcion": r.descripcion[:90],
        "funcionario": (r.funcionario.nombre if r.funcionario_id else r.asignado_a) or "Sin asignar",
        "url": reverse("detalle_requerimiento", args=[r.codigo]),
    } for r in tickets_visibles(perfil).filter(vecino=vecino).select_related("funcionario").order_by("-fecha_ingreso")[:20]]
    if vecino.es_extranjero is None:
        nacionalidad = "No registrada"
    else:
        nacionalidad = f"Sí · {vecino.nacionalidad}" if vecino.es_extranjero else "No"
    return JsonResponse({
        "vecino": {"nombre": vecino.nombre_mostrado, "rut": formatear_rut(vecino.rut) if vecino.rut else "Sin RUT", "telefono": vecino.telefono,
                   "correo": vecino.correo, "direccion": vecino.direccion, "territorio": vecino.territorio,
                   "delegacion": vecino.delegacion.nombre if vecino.delegacion else "", "extranjero": vecino.es_extranjero,
                   "nacionalidad": nacionalidad,
                   "nuevo_ticket": reverse("nuevo_requerimiento") + (f"?vecino_rut={vecino.rut}" if vecino.rut else "")},
        "fases": ["Ingresado", "Pendiente", "En proceso", "Realizado"],
        "actividades": actividades, "tickets": tickets,
    })
