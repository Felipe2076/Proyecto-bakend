from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from cuentas.auth import puede_ver, usuario_sesion
from control_gestion.models import Notificacion
from requerimientos.models import Requerimiento

LIMITE_ALERTAS = 50


def _enlace_seguro(enlace):
    """Solo rutas internas: evita enlaces javascript: o a sitios externos."""
    enlace = (enlace or "").strip()
    return enlace if enlace.startswith("/") and not enlace.startswith("//") else ""


def _tickets_criticos(perfil):
    """Tickets abiertos que superaron el plazo de alerta, solo de la delegación visible."""
    from control_gestion.kanban import tickets_visibles
    from cuentas.servicios import obtener_parametros

    if perfil is None:
        return Requerimiento.objects.none()
    limite = int(obtener_parametros().get("sla_amarillo_max_dias", 5))
    corte = timezone.localdate() - timedelta(days=limite + 1)
    return (tickets_visibles(perfil)
            .filter(fecha_ingreso__lte=corte)
            .exclude(estado=Requerimiento.Estado.RESUELTO)
            .exclude(codigo__startswith="DEMO-"))


def _alertas_automaticas(perfil):
    """Avisos que se generan solos con los datos del día, sin que nadie los escriba:
    compromisos vencidos (propios para funcionario y ventanilla; de la delegación para el resto)
    y directivas de organizaciones vencidas o que vencen en los próximos 30 días."""
    from control_gestion.models import Compromiso, OrganizacionComunitaria

    if perfil is None:
        return []
    hoy = timezone.localdate()
    alertas = []
    comp = Compromiso.objects.select_related("vecino").filter(fecha_compromiso__lt=hoy).exclude(estado="REALIZADO")
    if perfil.rol.codigo in ("funcionario", "ventanilla"):
        comp = comp.filter(funcionario_id=perfil.funcionario_id) if perfil.funcionario_id else comp.none()
    elif perfil.rol.codigo != "superusuario":
        comp = comp.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else comp.none()
    if puede_ver(perfil, "compromisos"):
        for c in comp.order_by("fecha_compromiso")[:LIMITE_ALERTAS]:
            alertas.append({
                "id": f"AUTO-{c.codigo}", "titulo": f"Compromiso vencido {c.codigo}",
                "mensaje": f"«{c.descripcion[:80]}» venció hace {(hoy - c.fecha_compromiso).days} día(s).",
                "tipo": "critico", "tipo_texto": "Compromiso vencido", "fecha": c.fecha_compromiso.isoformat(),
                "enlace": reverse("compromiso_detalle", args=[c.codigo]),
            })
    user = getattr(perfil, "user", None)
    if user is not None and user.has_perm("control_gestion.view_organizacioncomunitaria"):
        orgs = OrganizacionComunitaria.objects.filter(activa=True, vigencia_directiva_hasta__isnull=False,
                                                      vigencia_directiva_hasta__lte=hoy + timedelta(days=30))
        if perfil.rol.codigo != "superusuario":
            orgs = orgs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else orgs.none()
        for o in orgs.order_by("vigencia_directiva_hasta")[:LIMITE_ALERTAS]:
            vencida = o.vigencia_directiva_hasta < hoy
            alertas.append({
                "id": f"AUTO-ORG-{o.pk}-{o.vigencia_directiva_hasta:%Y%m%d}",
                "titulo": ("Directiva vencida · " if vencida else "Directiva por vencer · ") + o.nombre[:60],
                "mensaje": f"La directiva {'venció' if vencida else 'vence'} el {o.vigencia_directiva_hasta:%d/%m/%Y}. Actualice sus datos.",
                "tipo": "aviso", "tipo_texto": "Organización", "fecha": o.vigencia_directiva_hasta.isoformat(),
                "enlace": reverse("mant_organizaciones_editar", args=[o.pk]),
            })
    return alertas


def _notificaciones_base(perfil=None):
    """Avisos internos más alertas de tickets críticos del alcance del perfil."""
    almacenadas = [
        {
            "id": item.codigo,
            "titulo": item.titulo,
            "mensaje": item.mensaje,
            "tipo": item.tipo,
            "tipo_texto": item.get_tipo_display(),
            "fecha": item.fecha.isoformat(),
            "enlace": _enlace_seguro(item.enlace),
        }
        for item in Notificacion.objects.all()[:LIMITE_ALERTAS]
    ]
    automaticas = []
    for ticket in _tickets_criticos(perfil).order_by("fecha_ingreso")[:LIMITE_ALERTAS]:
        dias = ticket.dias_transcurridos
        automaticas.append(
            {
                "id": f"AUTO-{ticket.codigo}",
                "titulo": f"Ticket crítico {ticket.codigo}",
                "mensaje": f"{ticket.vecino.nombre_mostrado} lleva {dias} días en {ticket.delegacion.nombre}.",
                "tipo": "critico",
                "tipo_texto": "Ticket crítico",
                "fecha": ticket.fecha_ingreso.isoformat(),
                "enlace": reverse("detalle_requerimiento", args=[ticket.codigo]),
            }
        )
    return almacenadas + automaticas + _alertas_automaticas(perfil)


def _contar_pendientes(request, perfil, leidas):
    ids = set(Notificacion.objects.values_list("codigo", flat=True)[:LIMITE_ALERTAS])
    ids |= {f"AUTO-{c}" for c in _tickets_criticos(perfil).values_list("codigo", flat=True)[:LIMITE_ALERTAS]}
    ids |= {a["id"] for a in _alertas_automaticas(perfil)}
    return len(ids - leidas)


def _trimestre_vigente(request):
    if not request.user.is_authenticated:
        return None
    from django.db import DatabaseError

    from control_gestion.trimestres import resumen_trimestre_vigente
    try:
        return resumen_trimestre_vigente()
    except DatabaseError:
        return None  # una falla del trimestre no debe dejar sin pantalla al usuario


def sesion_siged(request):
    from cuentas.mantenedores import MANTENEDORES
    usuario = usuario_sesion(request)
    presentacion={
        'delegaciones':('Delegaciones','geo-alt'), 'usuarios':('Usuarios','people'),
        'roles':('Roles','person-badge'), 'metas':('Metas','bullseye'),
        'tipos-atencion':('Tipo de Atención','heart-pulse'),
        'sub-atenciones':('Sub Atención','diagram-2'), 'atenciones':('Atenciones','clipboard2-pulse'),
        'tipos-gestion':('Tipo de Gestión','signpost-split'), 'vecinos':('Vecinos','houses'),
        'periodos':('Configuración trimestral','calendar-range'), 'ausencias':('Ausencias y metas','calendar-x'), 'organizaciones':('Organizaciones comunitarias','buildings'), 'territorios':('Territorios por delegación','map'), 'agenda':('Actividades de organizaciones','calendar-event'),
    }
    perfil = getattr(request, "_perfil_siged", None)
    from cuentas.fotos import iniciales, url_foto
    foto_actual = url_foto(perfil) if perfil is not None else ""
    pendientes = 0
    if request.user.is_authenticated and perfil is not None and puede_ver(usuario, "notificaciones"):
        leidas = set(request.session.get("notificaciones_leidas") or [])
        pendientes = _contar_pendientes(request, perfil, leidas)
    return {
        "usuario_actual": usuario,
        "trimestre_vigente": _trimestre_vigente(request),
        "es_superusuario": bool(isinstance(usuario, dict) and usuario.get("rol") == "superusuario"),
        "mantenedores_autorizados": [
            {'nombre':m.nombre,'titulo':presentacion.get(m.ruta, (m.ruta.replace('-', ' ').capitalize(), 'list'))[0],
             'icono':presentacion.get(m.ruta, ('', 'list'))[1],'url':reverse(m.nombre)}
            for m in MANTENEDORES if request.user.is_authenticated and request.user.has_perm(
                f'{m.modelo._meta.app_label}.view_{m.modelo._meta.model_name}')
            and not (m.nombre == 'mant_usuarios' and puede_ver(usuario, "administracion"))
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
        "notificaciones_pendientes": pendientes,
        "foto_actual": foto_actual,
        "iniciales_actual": iniciales(perfil.nombre) if perfil is not None else "",
    }
