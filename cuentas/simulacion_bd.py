"""Aplica datos de simulación sobre una base que ya tiene filas de demostración.

Si no hay funcionarios, no hace nada: ``migrate`` en una base vacía (y la suite
de pruebas) no inserta las 25 cuentas. Esas llegan por fixtures o por
``importar_json``.
"""

import re

from django.utils import timezone

from core.validaciones import cuerpo_en_rango_ficticio
from cuentas.simulacion import (
    CARGO_POR_ROL,
    CODIGO_ADMIN_GLOBAL,
    ROLES_ORDEN,
    correo_funcionario,
    correo_vecino,
    direccion_ficticia,
    es_organizacion,
    identidad,
    nombre_almacenado,
    rut_trabajador,
    rut_vecino,
    telefono_ficticio,
)
from cuentas.vocabulario import DELEGACIONES_OFICIALES

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_FONO = re.compile(r"\+?\s*56\s*9(?:\s*\d){8}")
_RUT_TXT = re.compile(r"\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]")


def _indice_trabajador(rut):
    if not rut or "-" not in rut:
        return 0
    cuerpo = rut.split("-", 1)[0]
    if cuerpo.isdigit() and cuerpo.startswith("331"):
        return int(cuerpo) - 33_100_000
    return 0


def _indice_vecino(rut):
    if not rut or "-" not in rut:
        return 0
    cuerpo = rut.split("-", 1)[0]
    if cuerpo.isdigit() and cuerpo.startswith("335"):
        return int(cuerpo) - 33_500_000
    return 0


def _siguiente_codigo(modelo, prefijo, using):
    patron = re.compile(rf"^{re.escape(prefijo)}(\d+)$")
    maximo = 0
    for valor in modelo.objects.using(using).values_list("codigo", flat=True):
        coincidencia = patron.match(valor or "")
        if coincidencia:
            maximo = max(maximo, int(coincidencia.group(1)))
    return f"{prefijo}{maximo + 1:03d}"


def _ya_simulado(obj):
    """Ya tiene RUT de simulación y la marca en la columna, no en el nombre."""
    return bool(getattr(obj, "es_simulacion", False)) and cuerpo_en_rango_ficticio(getattr(obj, "rut", "") or "")


def _limpiar_texto(texto, mapa):
    if not texto:
        return texto
    for viejo, nuevo in sorted(mapa.items(), key=lambda item: -len(item[0])):
        if viejo and len(viejo) >= 5 and viejo in texto:
            texto = texto.replace(viejo, nuevo)

    def _rut(coincidencia):
        if cuerpo_en_rango_ficticio(coincidencia.group(0)):
            return coincidencia.group(0)
        return "33100001-9"

    texto = _EMAIL.sub("correo@siged.test", texto)
    texto = _FONO.sub("+56900000000", texto)
    return _RUT_TXT.sub(_rut, texto)


def _marcar_funcionario(fun, indice):
    nombres, paterno, materno = identidad(indice)
    fun.rut = rut_trabajador(indice)
    fun.nombres = nombres
    fun.apellido_paterno = paterno
    fun.apellido_materno = materno
    fun.es_simulacion = True
    fun.nombre = nombre_almacenado(nombres, paterno, materno)
    fun.save()


def _clave_inutilizable():
    """No autentica. importar_json asigna después una clave distinta por cuenta."""
    return "!"


def _sincronizar_acceso(usuario, fun, User, using):
    correo = correo_funcionario(fun.codigo)
    usuario.username = fun.rut
    usuario.nombre = fun.nombre
    usuario.correo = correo
    if fun.delegacion_id:
        usuario.delegacion_id = fun.delegacion_id
    user = usuario.user if usuario.user_id else User.objects.using(using).filter(username=fun.rut).first()
    if user is None:
        user = User(
            username=fun.rut,
            email=correo,
            is_active=usuario.estado == "activo",
            is_staff=False,
            is_superuser=False,
            date_joined=timezone.now(),
        )
    user.username = fun.rut
    user.email = correo
    user.first_name = (fun.nombres or "")[:150]
    user.last_name = (fun.apellido_paterno or "")[:150]
    user.is_active = usuario.estado == "activo"
    user.password = _clave_inutilizable()
    user.save()
    usuario.user = user
    usuario.save()


def _crear_funcionario(Funcionario, cargo, delegacion, indice, using):
    nombres, paterno, materno = identidad(indice)
    codigo = _siguiente_codigo(Funcionario, "FUN-", using)
    return Funcionario.objects.using(using).create(
        codigo=codigo,
        rut=rut_trabajador(indice),
        nombres=nombres,
        apellido_paterno=paterno,
        apellido_materno=materno,
        nombre=nombre_almacenado(nombres, paterno, materno),
        es_simulacion=True,
        cargo=cargo,
        delegacion=delegacion,
        estado="activo",
    )


def _crear_cuenta(apps, using, rol_codigo, delegacion, indice, codigo_usuario=None):
    Funcionario = apps.get_model("cuentas", "Funcionario")
    Usuario = apps.get_model("cuentas", "Usuario")
    Rol = apps.get_model("cuentas", "Rol")
    Cargo = apps.get_model("cuentas", "Cargo")
    User = apps.get_model("auth", "User")
    rol = Rol.objects.using(using).filter(codigo=rol_codigo).first()
    if rol is None or delegacion is None:
        return None
    cargo = (
        Cargo.objects.using(using).filter(nombre=CARGO_POR_ROL.get(rol_codigo, "")).first()
        or Cargo.objects.using(using).order_by("pk").first()
    )
    if cargo is None:
        return None
    fun = _crear_funcionario(Funcionario, cargo, delegacion, indice, using)
    usuario = Usuario(
        codigo=codigo_usuario or _siguiente_codigo(Usuario, "USR-", using),
        username=fun.rut,
        nombre=fun.nombre,
        correo=correo_funcionario(fun.codigo),
        rol=rol,
        cargo=cargo,
        delegacion=delegacion,
        funcionario=fun,
        estado="activo",
    )
    _sincronizar_acceso(usuario, fun, User, using)
    return usuario


def aplicar(apps, schema_editor):
    using = schema_editor.connection.alias
    Funcionario = apps.get_model("cuentas", "Funcionario")
    Usuario = apps.get_model("cuentas", "Usuario")
    Delegacion = apps.get_model("cuentas", "Delegacion")
    Cargo = apps.get_model("cuentas", "Cargo")
    User = apps.get_model("auth", "User")
    Vecino = apps.get_model("requerimientos", "Vecino")

    if not Funcionario.objects.using(using).exists() and not Usuario.objects.using(using).exists():
        return

    mapa = {}
    indice = max(
        (_indice_trabajador(fun.rut) for fun in Funcionario.objects.using(using).all()),
        default=0,
    )
    for fun in Funcionario.objects.using(using).order_by("codigo", "pk"):
        if _ya_simulado(fun):
            continue
        viejo = fun.nombre
        indice += 1
        _marcar_funcionario(fun, indice)
        if viejo and viejo != fun.nombre:
            mapa[viejo] = fun.nombre

    cargo_defecto = Cargo.objects.using(using).order_by("pk").first()
    deleg_defecto = (
        Delegacion.objects.using(using).filter(nombre="Delegación Centro").first()
        or Delegacion.objects.using(using).order_by("pk").first()
    )
    for usuario in Usuario.objects.using(using).select_related("funcionario"):
        if usuario.funcionario_id:
            continue
        delegacion_id = usuario.delegacion_id or (deleg_defecto.pk if deleg_defecto else None)
        delegacion = Delegacion.objects.using(using).filter(pk=delegacion_id).first() if delegacion_id else None
        cargo = usuario.cargo if usuario.cargo_id else cargo_defecto
        if delegacion is None or cargo is None:
            continue
        indice += 1
        usuario.funcionario = _crear_funcionario(Funcionario, cargo, delegacion, indice, using)
        usuario.save()

    for usuario in Usuario.objects.using(using).select_related("funcionario"):
        if usuario.funcionario_id:
            _sincronizar_acceso(usuario, usuario.funcionario, User, using)

    for nombre_delegacion in DELEGACIONES_OFICIALES:
        delegacion = Delegacion.objects.using(using).filter(nombre=nombre_delegacion).first()
        if delegacion is None:
            continue
        for rol_codigo in ROLES_ORDEN:
            cubierto = Usuario.objects.using(using).filter(
                rol__codigo=rol_codigo,
                funcionario__delegacion=delegacion,
            ).exists()
            if cubierto:
                continue
            indice += 1
            _crear_cuenta(apps, using, rol_codigo, delegacion, indice)

    if not Usuario.objects.using(using).filter(codigo=CODIGO_ADMIN_GLOBAL).exists():
        centro = Delegacion.objects.using(using).filter(nombre="Delegación Centro").first()
        if centro is not None:
            indice += 1
            _crear_cuenta(apps, using, "administrador", centro, indice, codigo_usuario=CODIGO_ADMIN_GLOBAL)

    if Vecino is not None:
        indice_v = max(
            (_indice_vecino(vec.rut) for vec in Vecino.objects.using(using).all()),
            default=0,
        )
        for vecino in Vecino.objects.using(using).order_by("pk"):
            if _ya_simulado(vecino):
                continue
            viejo = vecino.nombre
            indice_v += 1
            if es_organizacion(viejo):
                vecino.nombre = f"Organización Ficticia {indice_v:02d}"
            else:
                nombres, paterno, materno = identidad(indice_v + 40)
                vecino.nombre = nombre_almacenado(nombres, paterno, materno)
            vecino.rut = rut_vecino(indice_v)
            vecino.telefono = telefono_ficticio(indice_v)
            vecino.correo = correo_vecino(indice_v)
            vecino.direccion = direccion_ficticia(indice_v)
            vecino.es_simulacion = True
            vecino.save()
            if viejo and viejo != vecino.nombre:
                mapa[viejo] = vecino.nombre

        for delegacion in Delegacion.objects.using(using).all():
            cantidad = Vecino.objects.using(using).filter(delegacion=delegacion).count()
            while cantidad < 10:
                indice_v += 1
                nombres, paterno, materno = identidad(indice_v + 40)
                Vecino.objects.using(using).create(
                    nombre=nombre_almacenado(nombres, paterno, materno),
                    rut=rut_vecino(indice_v),
                    telefono=telefono_ficticio(indice_v),
                    correo=correo_vecino(indice_v),
                    direccion=direccion_ficticia(indice_v),
                    delegacion=delegacion,
                    es_simulacion=True,
                    estado="activo",
                )
                cantidad += 1

    _limpiar_textos(apps, using, mapa)


def _limpiar_textos(apps, using, mapa):
    Requerimiento = apps.get_model("requerimientos", "Requerimiento")
    Atencion = apps.get_model("requerimientos", "Atencion")
    Area = apps.get_model("requerimientos", "AreaSoporte")
    Actividad = apps.get_model("control_gestion", "Actividad")
    Compromiso = apps.get_model("control_gestion", "Compromiso")
    Agenda = apps.get_model("control_gestion", "EventoAgenda")
    Aviso = apps.get_model("control_gestion", "Notificacion")

    for area in Area.objects.using(using).all():
        if area.encargado_id:
            fun = area.encargado
            area.encargado_nombre = fun.nombre
        else:
            area.encargado_nombre = _limpiar_texto(area.encargado_nombre, mapa)
        area.descripcion = _limpiar_texto(area.descripcion, mapa)
        area.save()

    for req in Requerimiento.objects.using(using).all():
        req.descripcion = _limpiar_texto(req.descripcion, mapa)
        req.comentario_satisfaccion = _limpiar_texto(req.comentario_satisfaccion, mapa)
        if req.funcionario_id:
            req.asignado_a = req.funcionario.nombre
        else:
            req.asignado_a = _limpiar_texto(req.asignado_a, mapa)
        req.save()

    for atencion in Atencion.objects.using(using).all():
        atencion.observacion = _limpiar_texto(atencion.observacion, mapa)
        atencion.save()

    for actividad in Actividad.objects.using(using).all():
        if actividad.contacto:
            actividad.contacto = f"Contacto ficticio {actividad.pk}"
        actividad.servicio = _limpiar_texto(actividad.servicio, mapa)
        actividad.save()

    for compromiso in Compromiso.objects.using(using).all():
        compromiso.descripcion = _limpiar_texto(compromiso.descripcion, mapa)
        compromiso.save()

    for evento in Agenda.objects.using(using).all():
        evento.titulo = _limpiar_texto(evento.titulo, mapa)
        evento.lugar = _limpiar_texto(evento.lugar, mapa)
        evento.save()

    for aviso in Aviso.objects.using(using).all():
        aviso.titulo = _limpiar_texto(aviso.titulo, mapa)
        aviso.mensaje = _limpiar_texto(aviso.mensaje, mapa)
        aviso.save()
