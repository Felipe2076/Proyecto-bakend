"""Adaptadores ORM para control de gestión (las plantillas siguen recibiendo dicts)."""

from datetime import timedelta
from django.core.exceptions import ValidationError
from django.forms import DateField
from django.db import transaction
from django.utils import timezone
from core.busqueda import normalizar
from django.urls import reverse

from cuentas.models import Funcionario
from cuentas.servicios import siguiente_codigo
from control_gestion.models import Actividad, Compromiso, ItemFuncionario, Meta


FECHA_ACTIVIDAD = DateField(input_formats=("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"))


def funcionario_base(fun):
    return {
        "id_funcionario": fun.codigo,
        "pk_funcionario": fun.pk,
        "nombre": fun.nombre,
        "cargo": fun.cargo.nombre if fun.cargo_id else "",
        "delegacion": fun.delegacion.nombre if fun.delegacion_id else "",
        "fecha_ultimo_ingreso": fun.fecha_ultimo_ingreso.isoformat() if fun.fecha_ultimo_ingreso else "",
        "items": [
            {
                "item": item.meta.nombre,
                "codigo": item.codigo,
                "codigo_meta": item.meta.codigo,
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


# Estados de una atención ciudadana en las columnas del Tubo (la atención no tiene estado «Ingresado»).
ESTADO_ATENCION_EN_TUBO = {"pendiente": "PENDIENTE", "en_proceso": "EN PROCESO", "cerrada": "REALIZADO"}
ATENCION_DESDE_TUBO = {valor: clave for clave, valor in ESTADO_ATENCION_EN_TUBO.items()}


def atencion_a_dict(atencion):
    """Tarjeta del Tubo para una atención, con las mismas claves que un compromiso."""
    from django.urls import reverse

    fecha = timezone.localtime(atencion.fecha).date().isoformat()
    return {
        "id_compromiso": f"ATN-{atencion.pk:04d}",
        "es_atencion": True,
        "url_editar": reverse("mant_atenciones_editar", args=[atencion.pk]),
        "descripcion": f"{atencion.tipo_atencion.nombre} · {atencion.sub_atencion.nombre}",
        "origen": "ATN",
        "territorio": "",
        "apoyo": "",
        "observaciones": atencion.observacion,
        "vecino": atencion.vecino.nombre_mostrado,
        "funcionario": atencion.usuario.nombre_mostrado,
        "id_funcionario": "",
        "delegacion": atencion.delegacion.nombre,
        "fecha_ingreso": fecha,
        "fecha_compromiso": fecha,
        "vencido": False,
        "estado": ESTADO_ATENCION_EN_TUBO.get(atencion.estado, "PENDIENTE"),
    }


def atenciones_para_tubo(request, perfil, delegacion="", estado="", q=""):
    """Atenciones visibles para el usuario (permiso de consulta y su delegación) con los filtros del Tubo."""
    if not request.user.has_perm("requerimientos.view_atencion") or estado in ("INGRESADO", "VENCIDO"):
        return []
    from control_gestion.reportes import ambito
    from core.busqueda import buscar
    from requerimientos.models import Atencion

    qs = ambito(Atencion.objects.select_related("vecino", "tipo_atencion", "sub_atencion", "delegacion", "usuario",
                                                "usuario__funcionario"), perfil)
    if delegacion:
        qs = qs.filter(delegacion__nombre=delegacion)
    if estado:
        qs = qs.filter(estado=ATENCION_DESDE_TUBO.get(estado, "__ninguno__"))
    qs = buscar(qs, q, ["vecino__nombre", "vecino__rut", "tipo_atencion__nombre", "sub_atencion__nombre",
                        "delegacion__nombre", "observacion"])
    return [atencion_a_dict(item) for item in qs]


def compromiso_a_dict(compromiso):
    return {
        "id_compromiso": compromiso.codigo,
        "descripcion": compromiso.descripcion,
        "origen": compromiso.origen,
        "territorio": compromiso.territorio,
        "apoyo": compromiso.apoyo,
        "observaciones": compromiso.observaciones,
        "vecino": compromiso.vecino.nombre_mostrado,
        "funcionario": compromiso.funcionario.nombre_mostrado,
        "id_funcionario": compromiso.funcionario.codigo,
        "delegacion": compromiso.delegacion.nombre,
        "fecha_ingreso": compromiso.fecha_ingreso.isoformat(),
        "fecha_compromiso": compromiso.fecha_compromiso.isoformat(),
        "vencido": compromiso.estado != Compromiso.Estado.REALIZADO and compromiso.fecha_compromiso < timezone.localdate(),
        "estado": compromiso.estado,
    }


def queryset_compromisos():
    return Compromiso.objects.select_related("vecino", "funcionario", "funcionario__cargo", "delegacion")


def actividad_a_dict(actividad):
    return {
        "id_actividad": actividad.codigo,
        "id_funcionario": actividad.funcionario.codigo,
        "funcionario_nombre": actividad.funcionario.nombre_mostrado,
        "cargo": actividad.funcionario.cargo.nombre if actividad.funcionario.cargo_id else "",
        "delegacion": actividad.delegacion.nombre,
        "fecha_actividad": actividad.fecha_actividad.isoformat(),
        "contacto": actividad.contacto,
        "item": actividad.meta.nombre,
        "servicio": actividad.servicio,
        "codigo_verificador": actividad.codigo_verificador,
        "imagen_verificadora": actividad.imagen_verificadora,
        "evidencia_nombre": actividad.nombre_archivo_evidencia,
        "evidencia_url": reverse("actividad_evidencia", args=[actividad.codigo]) if actividad.evidencia_archivo else "",
        "punto_validado": actividad.punto_validado,
        "tipo_registro": actividad.tipo_registro,
        "fecha_validacion": actividad.fecha_validacion,
        "estado_revision": actividad.estado_revision,
        "revision_etiqueta": actividad.get_estado_revision_display(),
    }


def queryset_actividades():
    return Actividad.objects.select_related(
        "funcionario", "funcionario__cargo", "delegacion", "meta"
    )


@transaction.atomic
def registrar_actividad_desde_formulario(id_funcionario, post, archivos, *, autor=None):
    contacto = (post.get("contacto") or "").strip()
    item_nombre = (post.get("item") or "").strip()
    servicio = (post.get("servicio") or "").strip()
    imagen = (post.get("imagen_verificadora") or "").strip()
    fecha_actividad = (post.get("fecha_actividad") or "").strip()
    errores = {}
    if len(contacto) < 3:
        errores["contacto"] = "Indique el contacto o vecino atendido (mínimo 3 caracteres)."
    if len(contacto)>150:errores['contacto']='El contacto no puede superar 150 caracteres.'
    if len(servicio)>200:errores['servicio']='El servicio no puede superar 200 caracteres.'
    if len(item_nombre)>150:errores['item']='El nombre del ítem no puede superar 150 caracteres.'
    if not item_nombre:
        errores["item"] = "Seleccione el ítem de la matriz SGR."
    if len(servicio) < 5:
        errores["servicio"] = "Describa el servicio o atención (mínimo 5 caracteres)."
    try:
        fecha = FECHA_ACTIVIDAD.clean(fecha_actividad)
    except ValidationError:
        errores["fecha_actividad"] = "Ingrese una fecha válida con el formato DD/MM/AA."
        fecha = None
    archivo = archivos.get("evidencia") if archivos else None
    if archivo:
        from control_gestion.evidencias import validar_archivo
        try:
            validar_archivo(archivo)
        except ValueError as error:
            errores["evidencia"] = str(error)
        # No se guarda el nombre original del archivo: puede traer RUT o nombres de personas.
        from pathlib import Path as _Path
        imagen = f"Archivo {_Path(archivo.name).suffix.lstrip('.').upper() or 'adjunto'} adjunto"
    if errores:
        return None, errores

    funcionario = (
        Funcionario.objects.select_for_update().select_related("cargo", "delegacion").filter(codigo=id_funcionario).first()
    )
    if funcionario is None:
        return None, {"id_funcionario": "No se encontró el funcionario indicado."}

    hoy = timezone.localdate()
    cierre = fecha - timedelta(days=fecha.weekday()) + timedelta(days=8)
    if fecha > hoy:
        return None, {"fecha_actividad": "No puede registrar actividades futuras."}
    if hoy > cierre:
        return None, {"fecha_actividad": "La semana de esta actividad cerró el martes siguiente."}
    if Actividad.objects.filter(funcionario=funcionario,fecha_actividad=fecha).count() >= 7:
        return None, {"fecha_actividad": "El funcionario ya tiene siete actividades registradas para este día."}
    tipo = post.get('tipo_registro', 'RESULTADO')
    if tipo not in ('RESULTADO','COORDINACION','DELEGADO','FELICITACION'):
        return None, {"tipo_registro": "Seleccione un tipo de registro válido."}

    # Solo ítems existentes de la Matriz SGR: antes un texto libre creaba metas con errores de tipeo.
    meta = Meta.objects.filter(nombre__iexact=item_nombre).first()
    if meta is None:
        return None, {"item": "Elija un ítem de la lista. Los ítems nuevos los agrega el administrador en Metas."}
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
        imagen_verificadora=imagen[:200],
        evidencia_archivo=archivo or "",
        tipo_registro=tipo,
        punto_validado=False,
        creado_por=autor,
    )
    funcionario.fecha_ultimo_ingreso = max(fecha, funcionario.fecha_ultimo_ingreso) if funcionario.fecha_ultimo_ingreso else fecha
    funcionario.save(update_fields=["fecha_ultimo_ingreso"])
    return actividad_a_dict(actividad), {}
