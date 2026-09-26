"""Consultas ORM compartidas: parámetros, sesión, códigos y claves.

Las vistas no leen `data/*.json`. El comando `importar_json` sigue siendo
quien carga esos archivos hacia la base.
"""

import re

from cuentas.auth import etiqueta_rol
from cuentas.models import Delegacion, Funcionario, ParametroSistema
from cuentas.vocabulario import CANALES_INGRESO, DELEGACIONES_OFICIALES
from requerimientos.models import CanalIngreso


def errores_clave(password):
    """Reglas del mockup de 'Crear nueva contraseña'."""
    errores = []
    if len(password or "") < 8:
        errores.append("Mínimo 8 caracteres.")
    if not re.search(r"[A-Z]", password or ""):
        errores.append("Al menos una letra mayúscula.")
    if not re.search(r"[a-z]", password or ""):
        errores.append("Al menos una letra minúscula.")
    if not re.search(r"\d", password or ""):
        errores.append("Al menos un número.")
    if not re.search(r"[^A-Za-z0-9]", password or ""):
        errores.append("Al menos un carácter especial (por ejemplo ! @ # $ %).")
    return errores


def siguiente_codigo(modelo, campo, prefijo, ancho=3, minimo=0):
    """Siguiente código con prefijo (USR-001, TK-1001, ACT-001)."""
    patron = re.compile(rf"^{re.escape(prefijo)}(\d+)$")
    maximo = minimo
    for valor in modelo.objects.values_list(campo, flat=True):
        if not valor:
            continue
        coincidencia = patron.match(str(valor))
        if coincidencia:
            maximo = max(maximo, int(coincidencia.group(1)))
    return f"{prefijo}{maximo + 1:0{ancho}d}"


def obtener_parametros():
    """Equivalente ORM de la antigua lectura de parametros.json."""
    params = ParametroSistema.objects.order_by("pk").first()
    canales = list(
        CanalIngreso.objects.filter(activo=True).order_by("nombre").values_list("nombre", flat=True)
    )
    datos = {
        "nombre_sistema": "SIGED-SGR Delegaciones La Serena",
        "comuna": "La Serena",
        "region": "Región de Coquimbo",
        "sla_verde_max_dias": 3,
        "sla_amarillo_max_dias": 5,
        "meta_tubo_porcentaje": 80,
        "encuesta_habilitada": True,
        "max_atenciones_mismo_usuario": 3,
        "canales_ingreso": canales or list(CANALES_INGRESO),
    }
    if params is None:
        return datos
    datos.update(
        {
            "nombre_sistema": params.nombre_sistema,
            "comuna": params.comuna,
            "region": params.region,
            "sla_verde_max_dias": params.sla_verde_max_dias,
            "sla_amarillo_max_dias": params.sla_amarillo_max_dias,
            "meta_tubo_porcentaje": params.meta_tubo_porcentaje,
            "encuesta_habilitada": params.encuesta_habilitada,
            "max_atenciones_mismo_usuario": params.max_atenciones_mismo_usuario,
        }
    )
    return datos


def nombres_delegaciones():
    desde_bd = list(Delegacion.objects.order_by("nombre").values_list("nombre", flat=True))
    if not desde_bd:
        return list(DELEGACIONES_OFICIALES)
    oficiales = [nombre for nombre in DELEGACIONES_OFICIALES if nombre in desde_bd]
    resto = [nombre for nombre in desde_bd if nombre not in oficiales]
    return oficiales + resto


def funcionario_por_texto(texto):
    """Busca un funcionario por nombre o por 'Nombre (área)'."""
    if not texto:
        return None
    limpio = re.sub(r"\(.*?\)", "", texto).strip()
    if not limpio or limpio.lower().startswith("por asignar"):
        return None
    return (
        Funcionario.objects.filter(nombre__iexact=limpio).first()
        or Funcionario.objects.filter(nombre__istartswith=limpio).first()
    )


def sesion_desde_usuario(usuario):
    rol = usuario.rol.codigo if usuario.rol_id else ""
    return {
        "id_usuario": usuario.codigo or "",
        "username": usuario.username,
        "nombre": usuario.nombre,
        "email": usuario.correo,
        "rol": rol,
        "rol_etiqueta": etiqueta_rol(rol),
        "cargo": usuario.cargo.nombre if usuario.cargo_id else "",
        "delegacion": usuario.delegacion.nombre if usuario.delegacion_id else "",
        "id_funcionario": usuario.funcionario.codigo if usuario.funcionario_id else "",
        "activo": usuario.activo,
    }


def autenticar(username, password):
    from cuentas.models import Usuario

    usuario = (
        Usuario.objects.select_related("rol", "cargo", "delegacion", "funcionario", "user")
        .filter(username=(username or "").strip())
        .first()
    )
    if usuario is None or not usuario.activo:
        return None
    user = usuario.user
    if user is None or not user.is_active or not user.check_password(password or ""):
        return None
    return usuario
