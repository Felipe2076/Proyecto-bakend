"""Tablero persistente: estado de trabajo separado de la alerta por antigüedad."""
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from cuentas.auth import puede_ver
from cuentas.models import EstadoRegistro, Usuario
from requerimientos.consultas import queryset_requerimientos, ticket_a_dict
from requerimientos.models import Requerimiento

COLUMNAS = (
    (Requerimiento.Estado.PENDIENTE, "Pendientes", "warning"),
    (Requerimiento.Estado.EN_PROCESO, "En proceso", "info"),
    (Requerimiento.Estado.CUELLO_BOTELLA, "Cuello de botella", "danger"),
    (Requerimiento.Estado.RESUELTO, "Resueltos", "success"),
)


def perfil_actual(request):
    # El perfil vigente impide conservar permisos revocados en una sesión antigua.
    if not request.user.is_authenticated:
        return None
    return Usuario.objects.select_related("rol", "delegacion").filter(
        user=request.user, estado=EstadoRegistro.ACTIVO, user__is_active=True,
    ).first()


def tickets_visibles(perfil):
    qs = queryset_requerimientos()
    if perfil.rol.codigo != "superusuario":
        return qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()
    return qs


@never_cache
def tablero(request):
    from control_gestion.views import calcular_semaforo_ticket
    perfil = perfil_actual(request)
    if perfil is None:
        return redirect("login")
    if not puede_ver(perfil, "requerimientos"):
        messages.error(request, "Su perfil no tiene acceso al tablero.")
        return redirect("inicio")
    columnas = [dict(estado=estado, nombre=nombre, color=color, tickets=[])
                for estado, nombre, color in COLUMNAS]
    por_estado = {col["estado"]: col for col in columnas}
    from datetime import timedelta

    from django.db.models import Q
    from django.utils import timezone

    from cuentas.servicios import obtener_parametros

    params = obtener_parametros()
    # Los resueltos antiguos no se mueven más: el tablero muestra los de los últimos 30 días.
    corte = timezone.localdate() - timedelta(days=30)
    visibles = tickets_visibles(perfil).exclude(
        Q(estado=Requerimiento.Estado.RESUELTO) & (Q(fecha_resolucion__lt=corte) | Q(fecha_resolucion__isnull=True, fecha_ingreso__lt=corte)))
    from django.db.models import Count
    for req in visibles.annotate(n_evidencias=Count("evidencias", distinct=True)):
        ticket = calcular_semaforo_ticket(ticket_a_dict(req), params)
        ticket["evidencias"] = req.n_evidencias
        por_estado.get(req.estado, columnas[0])["tickets"].append(ticket)
    vista = "tabla" if request.GET.get("vista") == "tabla" else "kanban"
    filas = sorted((t for col in columnas for t in col["tickets"]), key=lambda t: t.get("fecha_ingreso", ""), reverse=True)
    return render(request, "control_gestion/kanban.html", {
        "columnas": columnas,
        "vista": vista,
        "filas": filas,
        "total_general": sum(len(col["tickets"]) for col in columnas),
        "dias_resueltos": 30,
    })


@require_POST
@never_cache
def mover_ticket(request, ticket_id):
    quiere_json = "application/json" in request.headers.get("Accept", "")

    def error(texto, status):
        if quiere_json:
            return JsonResponse({"error": texto}, status=status)
        messages.error(request, texto)
        return redirect("kanban")

    perfil = perfil_actual(request)
    if perfil is None:
        return error("La sesión terminó. Vuelva a iniciar sesión.", 401)
    if not puede_ver(perfil, "requerimientos"):
        return error("Su perfil no permite mover tickets.", 403)
    estado = request.POST.get("estado", "")
    anterior = request.POST.get("estado_anterior", "")
    if estado not in Requerimiento.Estado.values or anterior not in Requerimiento.Estado.values:
        return error("Seleccione un estado válido y vuelva a cargar el tablero.", 422)
    with transaction.atomic():
        # Solo bloquear el ticket: los joins opcionales no son necesarios al escribir.
        qs = Requerimiento.objects.select_for_update().filter(codigo=ticket_id)
        if perfil.rol.codigo != "superusuario":
            qs = qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()
        ticket = qs.first()
        if ticket is None:
            return error("El ticket no está disponible para su usuario.", 404)
        if ticket.estado != anterior:
            return error("Otra persona cambió este ticket. Actualice el tablero antes de moverlo.", 409)
        ticket.estado = estado
        ticket.save(update_fields=["estado"])
    if quiere_json:
        return JsonResponse({"ticket": ticket.codigo, "estado": ticket.estado})
    messages.success(request, f"Ticket {ticket.codigo}: {ticket.get_estado_display()}.")
    return redirect("kanban")
