"""Lectura y alta de requerimientos vía ORM."""

from django.utils import timezone

from cuentas.models import Delegacion
from cuentas.servicios import funcionario_por_texto, obtener_parametros, siguiente_codigo
from cuentas.models import Funcionario
from cuentas.vocabulario import AREAS_ESTRATEGICAS, CANALES_INGRESO, TIPOS_TICKET
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino

FUNCIONARIOS_REFERENCIA = [
    "Patrulla Sector 3 (Seguridad)",
    "Gonzalo Pizarro (Seguridad)",
    "Cuadrilla Verde (Aseo y Alumbrado)",
    "Juan Carlos Pérez (Cuadrilla Aseo)",
    "Valeria Moraga (Áreas Verdes)",
    "Esteban Barraza (Obras Viales)",
    "Rodrigo Santander (Operaciones)",
    "DIDECO Soporte Social",
    "Marcela Cárdenas (Atención Vecinal)",
]


def queryset_requerimientos():
    return Requerimiento.objects.select_related(
        "vecino", "delegacion", "canal_ingreso", "tipo_gestion", "area", "funcionario"
    )


def ticket_a_dict(req):
    asignado = req.asignado_a or (req.funcionario.nombre if req.funcionario_id else "")
    return {
        "id_ticket": req.codigo,
        "vecino_nombre": req.vecino.nombre,
        "telefono_whatsapp": req.vecino.telefono,
        "email": req.vecino.correo or "no-registra@serena.cl",
        "delegacion": req.delegacion.nombre,
        "canal_ingreso": req.canal_ingreso.nombre,
        "tipo_entrada": req.tipo_gestion.nombre,
        "area_tematica": req.area.nombre,
        "descripcion": req.descripcion,
        "fecha_ingreso": req.fecha_ingreso.isoformat(),
        "dias_transcurridos": req.dias_transcurridos,
        "funcionario_asignado": asignado or "Por Asignar (Jefatura Delegacional)",
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


def opciones_funcionarios(extra=""):
    nombres = list(Funcionario.objects.order_by("nombre").values_list("nombre", flat=True))
    for nombre in FUNCIONARIOS_REFERENCIA:
        if nombre not in nombres:
            nombres.append(nombre)
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


def _vecino(nombre, telefono, correo, delegacion, tipo):
    vecino = Vecino.objects.filter(nombre=nombre).first()
    if vecino is None:
        return Vecino.objects.create(
            nombre=nombre,
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
    )
    asignado = valores["funcionario_asignado"] or "Por Asignar (Jefatura Delegacional)"
    return Requerimiento.objects.create(
        codigo=siguiente_codigo(Requerimiento, "codigo", "TK-", 4, minimo=1000),
        vecino=vecino,
        delegacion=delegacion,
        canal_ingreso=canal,
        tipo_gestion=tipo,
        area=area,
        descripcion=valores["descripcion"],
        fecha_ingreso=timezone.localdate(),
        funcionario=funcionario_por_texto(asignado),
        asignado_a=asignado,
        estado=Requerimiento.Estado.PENDIENTE,
    )
