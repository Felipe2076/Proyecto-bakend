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
    ficha_extra,
    fichas_funcionario,
    identidad,
    nombre_almacenado,
    rut_de,
    rut_libre_trabajador,
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


def _escribir_ficha(fun, ficha):
    fun.rut = ficha["rut"]
    fun.nombres = (ficha["nombres"] or "")[:60]
    fun.apellido_paterno = (ficha["apellido_paterno"] or "")[:60]
    fun.apellido_materno = (ficha["apellido_materno"] or None)
    if fun.apellido_materno:
        fun.apellido_materno = fun.apellido_materno[:60]
    fun.es_simulacion = True
    fun.nombre = (ficha["nombre"] or nombre_almacenado(fun.nombres, fun.apellido_paterno, fun.apellido_materno or ""))[:120]
    fun.save()


def _plan_funcionarios(funcionarios, fichas):
    """Cada código del JSON conserva su RUT. El resto parte en el 33."""
    reservados = {ficha["rut"] for ficha in fichas.values()}
    usados = set(reservados)
    plan = {}
    extras = []
    for fun in funcionarios:
        ficha = fichas.get(fun.codigo)
        if ficha:
            plan[fun.pk] = ficha
        else:
            extras.append(fun)
    desde = 33
    for fun in extras:
        desde, rut = rut_libre_trabajador(usados, desde)
        usados.add(rut)
        plan[fun.pk] = ficha_extra(desde)
        desde += 1
    return plan, usados


def _aplicar_fichas(funcionarios, plan):
    """Dos pasadas para no chocar con uq_funcionario_rut si ya existe."""
    mapa = {}
    pendientes = []
    for fun in funcionarios:
        ficha = plan[fun.pk]
        if fun.rut == ficha["rut"] and fun.es_simulacion and fun.nombres == ficha["nombres"]:
            continue
        pendientes.append(fun)
    for fun in pendientes:
        fun.rut = rut_de(33_800_000, fun.pk)
        fun.save(update_fields=["rut"])
    for fun in pendientes:
        viejo = fun.nombre
        _escribir_ficha(fun, plan[fun.pk])
        if viejo and viejo != fun.nombre:
            mapa[viejo] = fun.nombre
    return mapa


def _ceder_usuario(Usuario, using, campo, valor, propio_pk):
    if not valor:
        return
    consulta = Usuario.objects.using(using).filter(**{campo: valor})
    if propio_pk:
        consulta = consulta.exclude(pk=propio_pk)
    for otro in list(consulta):
        reserva = f"reserva-{otro.pk}"
        if campo == "username":
            otro.username = reserva
        else:
            otro.correo = f"{reserva}@siged.test"
        otro.save(update_fields=[campo])


def _ceder_auth(User, using, username, propio_pk):
    if not username:
        return
    consulta = User.objects.using(using).filter(username=username)
    if propio_pk:
        consulta = consulta.exclude(pk=propio_pk)
    for otro in list(consulta):
        otro.username = f"reserva-auth-{otro.pk}"
        otro.save(update_fields=["username"])


def _clave_inutilizable():
    """No autentica. importar_json asigna después una clave distinta por cuenta."""
    return "!"


def _sincronizar_acceso(usuario, fun, User, Usuario, using):
    correo = correo_funcionario(fun.codigo)
    _ceder_usuario(Usuario, using, "username", fun.rut, usuario.pk)
    _ceder_usuario(Usuario, using, "correo", correo, usuario.pk)
    usuario.username = fun.rut
    usuario.nombre = fun.nombre
    usuario.correo = correo
    if fun.delegacion_id:
        usuario.delegacion_id = fun.delegacion_id
    user = usuario.user if usuario.user_id else User.objects.using(using).filter(username=fun.rut).first()
    _ceder_auth(User, using, fun.rut, user.pk if user is not None and user.pk else None)
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


def _crear_funcionario(Funcionario, cargo, delegacion, indice, using, fichas):
    codigo = _siguiente_codigo(Funcionario, "FUN-", using)
    ficha = fichas.get(codigo) or ficha_extra(indice)
    return Funcionario.objects.using(using).create(
        codigo=codigo,
        rut=ficha["rut"],
        nombres=(ficha["nombres"] or "")[:60],
        apellido_paterno=(ficha["apellido_paterno"] or "")[:60],
        apellido_materno=((ficha["apellido_materno"] or None)[:60] if ficha["apellido_materno"] else None),
        nombre=(ficha["nombre"] or "")[:120],
        es_simulacion=True,
        cargo=cargo,
        delegacion=delegacion,
        estado="activo",
    )


def _crear_cuenta(apps, using, rol_codigo, delegacion, indice, fichas, codigo_usuario=None):
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
    fun = _crear_funcionario(Funcionario, cargo, delegacion, indice, using, fichas)
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
    _sincronizar_acceso(usuario, fun, User, Usuario, using)
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

    fichas = fichas_funcionario()
    funcionarios = list(Funcionario.objects.using(using).order_by("codigo", "pk"))
    plan, usados = _plan_funcionarios(funcionarios, fichas)
    mapa = _aplicar_fichas(funcionarios, plan)
    indice = max((_indice_trabajador(rut) for rut in usados), default=32)

    def _indice_libre():
        nonlocal indice
        indice += 1
        while rut_trabajador(indice) in usados:
            indice += 1
        usados.add(rut_trabajador(indice))
        return indice

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
        usuario.funcionario = _crear_funcionario(Funcionario, cargo, delegacion, _indice_libre(), using, fichas)
        usados.add(usuario.funcionario.rut)
        usuario.save()

    for usuario in Usuario.objects.using(using).select_related("funcionario"):
        if usuario.funcionario_id:
            _sincronizar_acceso(usuario, usuario.funcionario, User, Usuario, using)

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
            _crear_cuenta(apps, using, rol_codigo, delegacion, _indice_libre(), fichas)

    if not Usuario.objects.using(using).filter(codigo=CODIGO_ADMIN_GLOBAL).exists():
        centro = Delegacion.objects.using(using).filter(nombre="Delegación Centro").first()
        if centro is not None:
            _crear_cuenta(apps, using, "administrador", centro, _indice_libre(), fichas, codigo_usuario=CODIGO_ADMIN_GLOBAL)

    if Vecino is not None:
        ocupados = set()
        for vecino in Vecino.objects.using(using).all():
            if vecino.rut and _ya_simulado(vecino):
                ocupados.add(vecino.rut)
        indice_v = 0
        pendientes = []
        for vecino in Vecino.objects.using(using).order_by("pk"):
            if _ya_simulado(vecino):
                continue
            indice_v += 1
            while rut_vecino(indice_v) in ocupados:
                indice_v += 1
            ocupados.add(rut_vecino(indice_v))
            pendientes.append((vecino.pk, indice_v, vecino.nombre))
        for pk, _indice, _viejo in pendientes:
            vecino = Vecino.objects.using(using).get(pk=pk)
            vecino.rut = rut_de(33_700_000, pk)
            vecino.save(update_fields=["rut"])
        for pk, indice_asignado, viejo in pendientes:
            vecino = Vecino.objects.using(using).get(pk=pk)
            if es_organizacion(viejo):
                vecino.nombre = f"Organización Ficticia {indice_asignado:02d}"
            else:
                nombres, paterno, materno = identidad(indice_asignado + 40)
                vecino.nombre = nombre_almacenado(nombres, paterno, materno)
            vecino.rut = rut_vecino(indice_asignado)
            vecino.telefono = telefono_ficticio(indice_asignado)
            vecino.correo = correo_vecino(indice_asignado)
            vecino.direccion = direccion_ficticia(indice_asignado)
            vecino.es_simulacion = True
            vecino.save()
            if viejo and viejo != vecino.nombre:
                mapa[viejo] = vecino.nombre

        for delegacion in Delegacion.objects.using(using).all():
            cantidad = Vecino.objects.using(using).filter(delegacion=delegacion).count()
            while cantidad < 10:
                indice_v += 1
                while rut_vecino(indice_v) in ocupados:
                    indice_v += 1
                ocupados.add(rut_vecino(indice_v))
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


def normalizar_filas_sueltas():
    """Cubre cualquier fila que el JSON no nombra.

    No depende de una lista de id. Un ``FUN-DEMO-ADMIN``, un vecino suelto o
    un usuario cuyo nombre de acceso no es un RUT 33.xxx.xxx reciben identidad
    de simulación sin pisar ``FUN-001`` … el código que sí está en el JSON.
    """
    from django.contrib.auth import get_user_model

    from cuentas.models import Funcionario, Usuario
    from requerimientos.models import Vecino

    User = get_user_model()
    fichas = fichas_funcionario()
    reservados = {ficha["rut"] for ficha in fichas.values()}
    usados = set(reservados)
    usados.update(rut for rut in Funcionario.objects.values_list("rut", flat=True) if rut)
    desde = 33
    for fun in Funcionario.objects.exclude(codigo__in=list(fichas)).order_by("codigo", "pk"):
        if (
            fun.rut
            and fun.rut not in reservados
            and cuerpo_en_rango_ficticio(fun.rut)
            and fun.es_simulacion
            and fun.nombres
            and fun.apellido_paterno
        ):
            continue
        desde, rut = rut_libre_trabajador(usados, desde)
        usados.add(rut)
        ficha = dict(ficha_extra(desde))
        ficha["rut"] = rut
        _escribir_ficha(fun, ficha)
        desde += 1

    for usuario in Usuario.objects.select_related("funcionario"):
        fun = usuario.funcionario
        if fun is None or not fun.rut:
            continue
        correo = correo_funcionario(fun.codigo)
        if usuario.username == fun.rut and (usuario.correo or "").endswith("@siged.test"):
            continue
        _ceder_usuario(Usuario, "default", "username", fun.rut, usuario.pk)
        _ceder_usuario(Usuario, "default", "correo", correo, usuario.pk)
        usuario.username = fun.rut
        usuario.nombre = fun.nombre
        usuario.correo = correo
        usuario.save()
        if usuario.user_id:
            _ceder_auth(User, "default", fun.rut, usuario.user_id)
            user = usuario.user
            user.username = fun.rut
            user.email = correo
            user.save(update_fields=["username", "email"])

    ocupados = {vecino.rut for vecino in Vecino.objects.all() if vecino.rut and cuerpo_en_rango_ficticio(vecino.rut)}
    indice = 0
    pendientes = []
    for vecino in Vecino.objects.order_by("pk"):
        if vecino.rut and vecino.es_simulacion and cuerpo_en_rango_ficticio(vecino.rut):
            continue
        indice += 1
        while rut_vecino(indice) in ocupados:
            indice += 1
        ocupados.add(rut_vecino(indice))
        pendientes.append((vecino.pk, indice))
    for pk, _indice in pendientes:
        vecino = Vecino.objects.get(pk=pk)
        vecino.rut = rut_de(33_700_000, pk)
        vecino.save(update_fields=["rut"])
    for pk, indice_asignado in pendientes:
        # No se cambia el nombre: importar_json busca por ese texto y, si
        # desaparece, crea otra fila al repetir la carga.
        vecino = Vecino.objects.get(pk=pk)
        if not (vecino.nombre or "").strip():
            nombres, paterno, materno = identidad(indice_asignado + 40)
            vecino.nombre = nombre_almacenado(nombres, paterno, materno)
        if not vecino.telefono:
            vecino.telefono = telefono_ficticio(indice_asignado)
        if not vecino.correo:
            vecino.correo = correo_vecino(indice_asignado)
        if not vecino.direccion:
            vecino.direccion = direccion_ficticia(indice_asignado)
        vecino.rut = rut_vecino(indice_asignado)
        vecino.es_simulacion = True
        vecino.save()
