"""Lectura y alta de requerimientos vía ORM."""

from django.db import transaction
from django.utils import timezone

from cuentas.models import Delegacion
from cuentas.servicios import funcionario_por_texto, obtener_parametros, siguiente_codigo
from cuentas.models import Funcionario
from cuentas.vocabulario import AREAS_ESTRATEGICAS, CANALES_INGRESO, TIPOS_TICKET
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino

# Ya no se ofrecen personas de referencia inventadas: la asignación usa
# funcionarios reales. Se conserva el nombre por compatibilidad de importación.
FUNCIONARIOS_REFERENCIA = []
SIN_ASIGNAR = "Sin asignar"


def para_indicadores(qs):
    """Tickets que cuentan en indicadores: sin los DEMO- y, si se configuró, sin vecinos simulados."""
    from django.conf import settings

    qs = qs.exclude(codigo__startswith="DEMO-")
    if getattr(settings, "SIGED_OCULTAR_SIMULACION", False):
        qs = qs.exclude(vecino__es_simulacion=True)
    return qs


def queryset_requerimientos():
    return Requerimiento.objects.select_related(
        "vecino", "delegacion", "canal_ingreso", "tipo_gestion", "area", "funcionario"
    )


def ticket_a_dict(req):
    asignado = req.funcionario.nombre if req.funcionario_id else (req.asignado_a or "")
    if asignado.startswith("Por Asignar"):
        asignado = ""
    return {
        "id_ticket": req.codigo,
        "vecino_nombre": req.vecino.nombre_mostrado,
        "vecino_rut": req.vecino.rut or "",
        "telefono_whatsapp": req.vecino.telefono,
        "email": req.vecino.correo or "",
        "delegacion": req.delegacion.nombre,
        "canal_ingreso": req.canal_ingreso.nombre,
        "tipo_entrada": req.tipo_gestion.nombre,
        "area_tematica": req.area.nombre,
        "descripcion": req.descripcion,
        "fecha_ingreso": req.fecha_ingreso.isoformat(),
        "dias_transcurridos": req.dias_transcurridos,
        "fecha_resolucion": req.fecha_resolucion.isoformat() if req.fecha_resolucion else "",
        "funcionario_asignado": asignado,
        "funcionario_asignado_texto": asignado or SIN_ASIGNAR,
        "estado_proceso": req.estado,
        "evaluacion_satisfaccion": req.evaluacion_satisfaccion,
        "comentario_satisfaccion": req.comentario_satisfaccion,
    }


def opciones_areas():
    nombres = list(AREAS_ESTRATEGICAS)
    for nombre in AreaSoporte.objects.order_by("nombre").values_list("nombre", flat=True):
        if nombre not in nombres:
            nombres.append(nombre)
    return nombres


def opciones_canales():
    nombres = list(obtener_parametros()["canales_ingreso"])
    for nombre in CANALES_INGRESO:
        if nombre not in nombres:
            nombres.append(nombre)
    return nombres


def opciones_tipos():
    return list(TIPOS_TICKET)


def opciones_funcionarios(extra="", delegacion=None):
    """Funcionarios activos reales; si se indica delegación, solo los de ella."""
    qs = Funcionario.objects.filter(estado="activo")
    if delegacion is not None:
        qs = qs.filter(delegacion=delegacion)
    nombres = list(qs.order_by("nombre").values_list("nombre", flat=True))
    if extra and extra not in nombres:
        nombres.append(extra)
    return nombres


def _tipo(nombre):
    tipo = TipoGestion.objects.filter(nombre__iexact=nombre).first()
    if tipo is None:
        tipo = TipoGestion.objects.create(nombre=nombre)
    return tipo


def _canal(nombre):
    canal = CanalIngreso.objects.filter(nombre__iexact=nombre).first()
    if canal is None:
        canal = CanalIngreso.objects.create(nombre=nombre)
    return canal


def _area(nombre):
    area = AreaSoporte.objects.filter(nombre=nombre).first()
    if area is None:
        area = AreaSoporte.objects.create(
            codigo=siguiente_codigo(AreaSoporte, "codigo", "AREA-", 3),
            nombre=nombre or "Sin área",
        )
    return area


def _vecino(nombre, telefono, correo, delegacion, tipo, rut=None):
    """Busca al vecino por RUT; sin RUT, por nombre y teléfono (no solo por nombre,
    para no fusionar homónimos). Si no existe, lo crea."""
    vecino = None
    if rut:
        vecino = Vecino.objects.filter(rut=rut).first()
    if vecino is None and telefono:
        candidatos = Vecino.objects.filter(nombre__iexact=nombre, telefono=telefono)
        if rut:
            # Con RUT nuevo solo se completa una ficha que aún no tenía RUT.
            candidatos = candidatos.filter(rut__isnull=True)
        vecino = candidatos.first()
        if vecino is not None and rut:
            vecino.rut = rut
            vecino.save(update_fields=["rut"])
    if vecino is None:
        return Vecino.objects.create(
            nombre=nombre,
            rut=rut or None,
            telefono=telefono or "",
            correo=correo or "",
            delegacion=delegacion,
            tipo_gestion=tipo,
        )
    cambios = []
    if telefono and not vecino.telefono:
        vecino.telefono = telefono
        cambios.append("telefono")
    if correo and not vecino.correo:
        vecino.correo = correo
        cambios.append("correo")
    if delegacion and not vecino.delegacion_id:
        vecino.delegacion = delegacion
        cambios.append("delegacion")
    if tipo and not vecino.tipo_gestion_id:
        vecino.tipo_gestion = tipo
        cambios.append("tipo_gestion")
    if cambios:
        vecino.save(update_fields=cambios)
    return vecino


@transaction.atomic
def crear_requerimiento(valores):
    delegacion, _ = Delegacion.objects.get_or_create(
        nombre=valores["delegacion"], defaults={"comuna": "La Serena"}
    )
    tipo = _tipo(valores["tipo_entrada"])
    canal = _canal(valores["canal_ingreso"])
    area = _area(valores["area_tematica"])
    vecino = _vecino(
        valores["vecino_nombre"],
        valores["telefono_whatsapp"],
        valores["email"],
        delegacion,
        tipo,
        rut=valores.get("vecino_rut") or None,
    )
    # Nacionalidad declarada en el formulario: siempre se guarda la respuesta más reciente.
    if valores.get("es_extranjero") in ("si", "no"):
        vecino.es_extranjero = valores["es_extranjero"] == "si"
        vecino.nacionalidad = valores.get("nacionalidad") or None
        vecino.save(update_fields=["es_extranjero", "nacionalidad"])
    asignado = valores["funcionario_asignado"] or ""
    return Requerimiento.objects.create(
        codigo=siguiente_codigo(Requerimiento, "codigo", "TK-", 4, minimo=1000),
        vecino=vecino,
        delegacion=delegacion,
        canal_ingreso=canal,
        tipo_gestion=tipo,
        area=area,
        descripcion=valores["descripcion"],
        fecha_ingreso=timezone.localdate(),
        funcionario=funcionario_por_texto(asignado) if asignado else None,
        asignado_a=asignado,
        estado=Requerimiento.Estado.PENDIENTE,
    )
