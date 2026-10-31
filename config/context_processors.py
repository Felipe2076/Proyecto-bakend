from datetime import timedelta

from django.utils import timezone

from cuentas.auth import puede_ver, usuario_sesion
from control_gestion.models import Notificacion
from requerimientos.models import Requerimiento


def _notificaciones_base():
    almacenadas = [
        {
            "id": item.codigo,
            "titulo": item.titulo,
            "mensaje": item.mensaje,
            "tipo": item.tipo,
            "fecha": item.fecha.isoformat(),
            "enlace": item.enlace,
        }
        for item in Notificacion.objects.all()
    ]
    corte = timezone.localdate() - timedelta(days=6)
    automaticas = []
    criticos = (
        Requerimiento.objects.select_related("vecino", "delegacion")
        .filter(fecha_ingreso__lte=corte)
        .exclude(estado=Requerimiento.Estado.RESUELTO)
    )
    for ticket in criticos:
        dias = ticket.dias_transcurridos
        automaticas.append(
            {
                "id": f"AUTO-{ticket.codigo}",
                "titulo": f"Ticket crítico {ticket.codigo}",
                "mensaje": f"{ticket.vecino.nombre} lleva {dias} días en {ticket.delegacion.nombre}.",
                "tipo": "critico",
                "fecha": ticket.fecha_ingreso.isoformat(),
                "enlace": f"/requerimientos/{ticket.codigo}/",
            }
        )
    return almacenadas + automaticas


def sesion_siged(request):
    from cuentas.mantenedores import MANTENEDORES
    from django.urls import reverse
    usuario = usuario_sesion(request)
    presentacion={
        'delegaciones':('Delegaciones','geo-alt'), 'usuarios':('Usuarios','people'),
        'roles':('Roles','person-badge'), 'metas':('Metas','bullseye'),
        'tipos-atencion':('Tipo de Atención','heart-pulse'),
        'sub-atenciones':('Sub Atención','diagram-2'), 'atenciones':('Atenciones','clipboard2-pulse'),
        'tipos-gestion':('Tipo de Gestión','signpost-split'), 'vecinos':('Vecinos','houses'),
    }
    leidas = set(request.session.get("notificaciones_leidas") or [])
    notificaciones = _notificaciones_base()
    pendientes = [item for item in notificaciones if item.get("id") not in leidas]
    return {
        "usuario_actual": usuario,
        "mantenedores_autorizados": [
            {'nombre':m.nombre,'titulo':presentacion[m.ruta][0],'icono':presentacion[m.ruta][1],'url':reverse(m.nombre)}
            for m in MANTENEDORES if request.user.is_authenticated and request.user.has_perm(
                f'{m.modelo._meta.app_label}.view_{m.modelo._meta.model_name}')
        ],
        "puede_requerimientos": puede_ver(usuario, "requerimientos"),
        "puede_matriz_sgr": puede_ver(usuario, "matriz_sgr"),
        "puede_control_gestion": puede_ver(usuario, "control_gestion"),
        "puede_actividades": puede_ver(usuario, "actividades"),
        "puede_agenda": puede_ver(usuario, "agenda"),
        "puede_compromisos": puede_ver(usuario, "compromisos"),
        "puede_notificaciones": puede_ver(usuario, "notificaciones"),
        "puede_encuestas": puede_ver(usuario, "encuestas"),
        "puede_administracion": puede_ver(usuario, "administracion"),
        "notificaciones_pendientes": len(pendientes),
    }
