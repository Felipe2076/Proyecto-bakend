"""Adaptadores ORM para control de gestión (las plantillas siguen recibiendo dicts)."""

from datetime import datetime

from cuentas.models import Funcionario
from cuentas.servicios import siguiente_codigo
from control_gestion.models import Actividad, Compromiso, ItemFuncionario, Meta


def funcionario_base(fun):
    return {
        "id_funcionario": fun.codigo,
        "nombre": fun.nombre,
        "cargo": fun.cargo.nombre if fun.cargo_id else "",
        "delegacion": fun.delegacion.nombre if fun.delegacion_id else "",
        "fecha_ultimo_ingreso": fun.fecha_ultimo_ingreso.isoformat() if fun.fecha_ultimo_ingreso else "",
        "items": [
            {
                "item": item.meta.nombre,
                "ponderador": item.ponderador,
                "meta_trimestre": item.meta_trimestre,
                "avance_actual": item.avance_actual,
            }
            for item in fun.items.all()
        ],
    }


def queryset_funcionarios():
    return (
        Funcionario.objects.select_related("cargo", "delegacion")
        .prefetch_related("items__meta")
        .order_by("codigo")
    )


def compromiso_a_dict(compromiso):
    return {
        "id_compromiso": compromiso.codigo,
        "descripcion": compromiso.descripcion,
        "vecino": compromiso.vecino.nombre,
        "funcionario": compromiso.funcionario.nombre,
        "id_funcionario": compromiso.funcionario.codigo,
        "delegacion": compromiso.delegacion.nombre,
        "fecha_ingreso": compromiso.fecha_ingreso.isoformat(),
        "fecha_compromiso": compromiso.fecha_compromiso.isoformat(),
        "estado": compromiso.estado,
    }


def queryset_compromisos():
    return Compromiso.objects.select_related("vecino", "funcionario", "delegacion")


def actividad_a_dict(actividad):
    return {
        "id_actividad": actividad.codigo,
        "id_funcionario": actividad.funcionario.codigo,
        "funcionario_nombre": actividad.funcionario.nombre,
        "cargo": actividad.funcionario.cargo.nombre if actividad.funcionario.cargo_id else "",
        "delegacion": actividad.delegacion.nombre,
        "fecha_actividad": actividad.fecha_actividad.isoformat(),
        "contacto": actividad.contacto,
        "item": actividad.meta.nombre,
        "servicio": actividad.servicio,
        "codigo_verificador": actividad.codigo_verificador,
        "imagen_verificadora": actividad.imagen_verificadora,
        "punto_validado": actividad.punto_validado,
    }


def queryset_actividades():
    return Actividad.objects.select_related(
        "funcionario", "funcionario__cargo", "delegacion", "meta"
    )


def registrar_actividad_desde_formulario(id_funcionario, post, archivos):
    contacto = (post.get("contacto") or "").strip()
    item_nombre = (post.get("item") or "").strip()
    servicio = (post.get("servicio") or "").strip()
    imagen = (post.get("imagen_verificadora") or "").strip()
    fecha_actividad = (post.get("fecha_actividad") or "").strip()
    errores = {}
    if len(contacto) < 3:
        errores["contacto"] = "Indique el contacto o vecino atendido (mínimo 3 caracteres)."
    if not item_nombre:
        errores["item"] = "Seleccione el ítem de la matriz SGR."
    if len(servicio) < 5:
        errores["servicio"] = "Describa el servicio o atención (mínimo 5 caracteres)."
    try:
        fecha = datetime.strptime(fecha_actividad, "%Y-%m-%d").date()
    except ValueError:
        errores["fecha_actividad"] = "Ingrese una fecha válida (AAAA-MM-DD)."
        fecha = None
    archivo = archivos.get("evidencia") if archivos else None
    if archivo:
        imagen = archivo.name
    elif not imagen:
        imagen = "Registro fotográfico pendiente de adjuntar"
    if errores:
        return None, errores

    funcionario = (
        Funcionario.objects.select_related("cargo", "delegacion").filter(codigo=id_funcionario).first()
    )
    if funcionario is None:
        return None, {"id_funcionario": "No se encontró el funcionario indicado."}

    meta, _ = Meta.objects.get_or_create(
        nombre=item_nombre, defaults={"descripcion": "Ítem de la Matriz SGR"}
    )
    codigo = siguiente_codigo(Actividad, "codigo", "ACT-", 3)
    verificador = f"VER-{fecha.strftime('%Y%m%d')}-{id_funcionario}-{codigo}"
    actividad = Actividad.objects.create(
        codigo=codigo,
        funcionario=funcionario,
        delegacion=funcionario.delegacion,
        meta=meta,
        fecha_actividad=fecha,
        contacto=contacto,
        servicio=servicio,
        codigo_verificador=verificador,
        imagen_verificadora=imagen,
        punto_validado=True,
    )
    funcionario.fecha_ultimo_ingreso = fecha
    funcionario.save(update_fields=["fecha_ultimo_ingreso"])
    item = ItemFuncionario.objects.filter(funcionario=funcionario, meta=meta).first()
    if item is not None:
        item.avance_actual = int(item.avance_actual or 0) + 1
        item.save(update_fields=["avance_actual"])
    return actividad_a_dict(actividad), {}
