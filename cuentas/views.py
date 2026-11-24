import re
from datetime import date

from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.shortcuts import redirect, render
from django.db import DatabaseError, transaction
from django.core.exceptions import ValidationError
from smtplib import SMTPException

import logging

from core.seguridad import LimiteExcedido, clave_limite, consumir, ip_cliente, liberar
from core.validaciones import (
    MENSAJE_NOMBRE, MENSAJE_RUT, formatear_rut, motivo_rut_invalido, rut_canonico, rut_normalizado_valido,
    validar_nombre,
)
from cuentas.auth import requerir_modulo, usuario_sesion
from cuentas.forms import NuevaContrasenaForm, RestablecerEnlaceForm
from cuentas.models import Cargo, Delegacion, EstadoRegistro, Funcionario, ParametroSistema, Rol, Usuario
from cuentas.recuperacion import emitir_codigo, enviar_codigo, verificar_codigo
from cuentas.servicios import (
    autenticar,
    errores_clave,
    nombres_delegaciones,
    obtener_parametros,
    sesion_desde_usuario,
    siguiente_codigo,
)
from cuentas.fotos import iniciales, url_foto
from cuentas.simulacion import CODIGO_ADMIN_GLOBAL, identidad, nombre_almacenado
from control_gestion.models import Medicion

log_seguridad = logging.getLogger("siged.seguridad")
MENSAJE_LIMITE = "Demasiados intentos. Espere 15 minutos antes de volver a intentar."


def _claves_login(request, rut):
    cuenta = rut_normalizado_valido(rut) or "".join(c for c in rut.upper() if c.isalnum())
    return {
        clave_limite("login-ip", ip_cliente(request)): settings.SIGED_LIMITE_LOGIN_IP,
        clave_limite("login-cuenta", cuenta): settings.SIGED_LIMITE_LOGIN_CUENTA,
    }


ROLES_DISPONIBLES = [
    ("superusuario", "Superusuario"),
    ("administrador", "Administrador de delegación"),
    ("jefatura", "Jefatura / Control de gestión"),
    ("funcionario", "Funcionario territorial"),
    ("ventanilla", "Ventanilla ciudadana"),
]


def _next_seguro(valor):
    if valor and valor.startswith("/") and not valor.startswith("//"):
        return valor
    return "/"


def _demos():
    """RUT y rol de las cuentas de simulación. Nunca incluye la clave."""
    demos = []
    usuarios = (
        Usuario.objects.filter(estado=EstadoRegistro.ACTIVO, funcionario__es_simulacion=True)
        .select_related("rol", "funcionario", "funcionario__delegacion")
        .order_by("funcionario__delegacion__nombre", "rol__codigo", "funcionario__rut")
    )
    for usuario in usuarios:
        fun = usuario.funcionario
        demos.append(
            {
                "rut": formatear_rut(fun.rut) if fun else "",
                "nombre": fun.nombre_mostrado if fun else usuario.nombre_mostrado,
                "rol": usuario.rol.codigo if usuario.rol_id else "",
                "delegacion": fun.delegacion.nombre if fun and fun.delegacion_id else "",
                "global": usuario.codigo == CODIGO_ADMIN_GLOBAL,
            }
        )
    return demos


def login_view(request):
    if request.user.is_authenticated and usuario_sesion(request):
        return redirect("inicio")
    errores = {}
    valores = {"rut": ""}
    estado = 200
    if request.method == "POST":
        rut = (request.POST.get("rut") or "").strip()[:32]
        password = (request.POST.get("password") or "")[:256]
        valores["rut"] = rut
        if not rut:
            errores["rut"] = "Ingrese el RUT."
        if not password:
            errores["password"] = "Ingrese la contraseña."
        claves = _claves_login(request, rut) if not errores else {}
        if claves:
            try:
                consumir(claves)
            except LimiteExcedido:
                log_seguridad.warning("login_web_limitado")
                errores["password"] = MENSAJE_LIMITE
                messages.error(request, MENSAJE_LIMITE)
                estado = 429
        if not errores:
            encontrado = autenticar(rut, password)
            if encontrado is None:
                normal = rut_normalizado_valido(rut)
                pendiente = Usuario.objects.select_related('user').filter(username=normal, estado=EstadoRegistro.ACTIVO, user__is_active=True).first() if normal else None
                if pendiente and pendiente.user_id and not pendiente.user.has_usable_password() and re.fullmatch(r'\d{6}',password):
                    if verificar_codigo(pendiente,password) == 'ok':
                        liberar(*claves)
                        _sesion_recuperacion(request,pendiente,verificado=True)
                        messages.info(request,'Primer ingreso: debe definir su contraseña personal para activar el acceso.')
                        return redirect('nueva_contrasena')
                errores["password"] = "RUT o clave incorrectos."
                messages.error(request, "RUT o clave incorrectos.")
            else:
                liberar(*claves)
                auth_login(request, encontrado.user)
                request.session["usuario"] = sesion_desde_usuario(encontrado)
                request.session["notificaciones_leidas"] = []
                perfil = sesion_desde_usuario(encontrado)
                from control_gestion.trimestres import resumen_trimestre_vigente
                trimestre = resumen_trimestre_vigente()
                messages.success(
                    request,
                    f"Bienvenido/a, {perfil['nombre']}. {perfil['rol_etiqueta']}"
                    + (f" · {perfil['delegacion']}" if perfil["delegacion"] else "")
                    + f". Trimestre vigente: {trimestre['periodo']} ({trimestre['inicio']} al {trimestre['termino']}).",
                )
                return redirect(_next_seguro(request.POST.get("next") or request.GET.get("next")))
    contexto = {
        "demos": _demos() if settings.DEBUG else [],
        "mostrar_demos": settings.DEBUG,
        "errores": errores,
        "valores": valores,
        "next_url": _next_seguro(request.GET.get("next") or request.POST.get("next")),
    }
    return render(request, "cuentas/login.html", contexto, status=estado)


def logout_view(request):
    # Por POST: un enlace o imagen de otro sitio no puede cerrar la sesión (CSRF de logout).
    if request.method != "POST":
        if request.user.is_authenticated:
            return render(request, "cuentas/salir.html")
        return redirect("login")
    auth_logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("login")


def _sesion_recuperacion(request, usuario, verificado=False):
    """La cookie guarda el id y, tras acertar, la marca de verificado. Nunca el código."""
    request.session["recuperacion"] = {
        "usuario_id": usuario.pk,
        "verificado": verificado,
    }
    request.session.modified = True


def _usuario_en_recuperacion(request):
    datos = request.session.get("recuperacion") or {}
    usuario_id = datos.get("usuario_id")
    if not usuario_id:
        return None, datos
    usuario = Usuario.objects.select_related("user").filter(pk=usuario_id).first()
    return usuario, datos


def _correo_habilitado():
    backend = settings.EMAIL_BACKEND
    # En desarrollo (DEBUG) el correo sale por consola: así se pueden probar altas y recuperación.
    if settings.DEBUG and backend == 'django.core.mail.backends.console.EmailBackend':
        return True
    return backend == 'django.core.mail.backends.locmem.EmailBackend' or (
        backend == 'django.core.mail.backends.smtp.EmailBackend'
        and settings.EMAIL_HOST not in ('', 'localhost', '127.0.0.1', '::1')
    )


def _emitir_y_enviar(request, usuario):
    try:
        with transaction.atomic():
            codigo = emitir_codigo(usuario, ip=(request.META.get('REMOTE_ADDR') or '')[:45])
            uid=urlsafe_base64_encode(force_bytes(usuario.user_id))
            token=default_token_generator.make_token(usuario.user)
            enlace=request.build_absolute_uri(reverse('recuperar_enlace',kwargs={'uidb64':uid,'token':token}))
            enviar_codigo(usuario, codigo, enlace=enlace)
        return True
    except (OSError, SMTPException, RuntimeError):
        messages.error(request, 'No se pudo enviar el correo. Inténtelo más tarde o contacte al administrador.')
        return False


def recuperar_contrasena_view(request):
    if not _correo_habilitado():
        return render(request, 'cuentas/recuperar.html', {'errores': {}, 'correo': '', 'correo_no_disponible': True})
    errores = {}
    correo = ""
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip()[:254]
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            errores["correo"] = "Ingrese un correo electrónico válido."
        elif not _cuota_recuperacion(request, correo):
            errores["correo"] = MENSAJE_LIMITE
            return render(request, "cuentas/recuperar.html", {"errores": errores, "correo": correo}, status=429)
        else:
            usuario = (
                Usuario.objects.select_related("user")
                .filter(correo__iexact=correo, estado=EstadoRegistro.ACTIVO)
                .first()
            )
            if usuario is None or usuario.user_id is None:
                # Misma respuesta que una cuenta real (Ley 19.628: no confirmar titulares).
                request.session["recuperacion"] = {"usuario_id": None, "correo": correo}
            else:
                if not _emitir_y_enviar(request, usuario):
                    return redirect("recuperar_contrasena")
                _sesion_recuperacion(request, usuario, verificado=False)
            messages.success(
                request,
                "Si el correo corresponde a una cuenta activa, enviamos un enlace seguro y un código "
                "de respaldo. Vencen en 10 minutos. Puede abrir el enlace para crear su nueva contraseña.",
            )
            return redirect("validar_codigo")
    return render(request, "cuentas/recuperar.html", {"errores": errores, "correo": correo})


def _cuota_recuperacion(request, correo):
    try:
        consumir({
            clave_limite("recuperar-ip", ip_cliente(request)): settings.SIGED_LIMITE_RECUPERAR_IP,
            clave_limite("recuperar-correo", correo.lower()): settings.SIGED_LIMITE_RECUPERAR_CORREO,
        })
    except LimiteExcedido:
        log_seguridad.warning("recuperacion_limitada")
        return False
    return True


def _validacion_sin_cuenta(request, datos):
    """Recuperación pedida para un correo sin cuenta: se comporta igual y nunca valida."""
    errores = {}
    if request.method == "POST":
        if (request.POST.get("accion") or "") == "reenviar":
            if not _cuota_recuperacion(request, datos["correo"]):
                messages.error(request, MENSAJE_LIMITE)
            else:
                messages.success(request, "Enviamos un código nuevo a su correo. El anterior ya no sirve.")
            return redirect("validar_codigo")
        intentos = datos.get("intentos", 0) + 1
        request.session["recuperacion"] = {**datos, "intentos": intentos}
        errores["codigo"] = ("Demasiados intentos. Solicite un código nuevo." if intentos >= 5
                             else "El código no coincide. Revíselo e intente de nuevo.")
        messages.error(request, "No pudimos validar el código.")
    return render(request, "cuentas/validar_codigo.html", {"errores": errores, "correo": datos["correo"]})


def validar_codigo_view(request):
    usuario, datos = _usuario_en_recuperacion(request)
    if usuario is None and datos.get("correo"):
        return _validacion_sin_cuenta(request, datos)
    if usuario is None:
        messages.error(request, "No hay una recuperación en curso. Solicite un código nuevo.")
        return redirect("recuperar_contrasena")
    errores = {}
    if request.method == "POST":
        if (request.POST.get("accion") or "") == "reenviar":
            if not _cuota_recuperacion(request, usuario.correo):
                messages.error(request, MENSAJE_LIMITE)
                return redirect("validar_codigo")
            if not _correo_habilitado() or not _emitir_y_enviar(request, usuario):
                return redirect("recuperar_contrasena")
            _sesion_recuperacion(request, usuario, verificado=False)
            messages.success(
                request,
                "Enviamos un código nuevo a su correo. El anterior ya no sirve.",
            )
            return redirect("validar_codigo")
        ingresado = "".join((request.POST.get(f"d{i}") or "").strip() for i in range(1, 7))
        if not re.fullmatch(r"\d{6}", ingresado):
            errores["codigo"] = "Ingrese los 6 dígitos del código."
        else:
            resultado = verificar_codigo(usuario, ingresado)
            if resultado == "ok":
                _sesion_recuperacion(request, usuario, verificado=True)
                messages.success(request, "Código verificado. Defina su nueva contraseña.")
                return redirect("nueva_contrasena")
            if resultado == "agotado":
                errores["codigo"] = "Demasiados intentos. Solicite un código nuevo."
            elif resultado == "expirado":
                errores["codigo"] = "El código expiró. Solicite uno nuevo."
            elif resultado == "ausente":
                errores["codigo"] = "Ese código ya no es válido. Solicite uno nuevo."
            else:
                errores["codigo"] = "El código no coincide. Revíselo e intente de nuevo."
        messages.error(request, "No pudimos validar el código.")
    return render(
        request,
        "cuentas/validar_codigo.html",
        {"errores": errores, "correo": usuario.correo},
    )


def nueva_contrasena_view(request):
    usuario, datos = _usuario_en_recuperacion(request)
    if usuario is None or not datos.get("verificado"):
        messages.error(request, "Primero debe validar el código enviado a su correo.")
        return redirect("validar_codigo" if usuario else "recuperar_contrasena")
    form = NuevaContrasenaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if usuario.user_id is None:
            messages.error(request, "No fue posible actualizar la contraseña de ese usuario.")
            return redirect("recuperar_contrasena")
        usuario.user.set_password(form.cleaned_data["password"])
        usuario.user.save(update_fields=["password"])
        request.session.pop("recuperacion", None)
        messages.success(request, "Su contraseña fue actualizada. Ya puede ingresar.")
        return redirect("login")
    if request.method == "POST":
        messages.error(request, "La contraseña no cumple los requisitos.")
    return render(request, "cuentas/nueva_contrasena.html", {"form": form})


def _usuario_a_fila(usuario):
    fun = usuario.funcionario if usuario.funcionario_id else None
    return {
        "id_usuario": usuario.codigo or str(usuario.pk),
        "username": formatear_rut(fun.rut) if fun else usuario.username,
        "nombre": (fun.nombre_mostrado if fun else usuario.nombre_mostrado),
        "email": usuario.correo,
        "rol": usuario.rol.nombre if usuario.rol_id else "",
        "cargo": usuario.cargo.nombre if usuario.cargo_id else "",
        "activo": usuario.activo,
        "delegacion": usuario.delegacion.nombre if usuario.delegacion_id else "",
        "codigo": usuario.codigo,
        "foto_url": url_foto(usuario),
        "iniciales": iniciales(usuario.nombre),
    }


def _solo_superusuario(request):
    """Lo que rige a todas las delegaciones (cargos, parámetros, grupos) solo lo administra el superusuario."""
    if request._perfil_siged.rol.codigo != "superusuario":
        messages.error(request, "Esta configuración afecta a todas las delegaciones y la administra el superusuario.")
        return redirect("inicio")
    return None


def administracion_usuarios_view(request):
    bloqueo = requerir_modulo(request, "administracion")
    if bloqueo:
        return bloqueo
    perfil = request._perfil_siged
    es_super = perfil.rol.codigo == "superusuario"
    errores = {}
    valores = {}
    if request.method == "POST":
        accion = (request.POST.get("accion") or "crear").strip()
        if accion == "toggle":
            user_id = (request.POST.get("id_usuario") or "").strip()
            usuario = Usuario.objects.select_related("user", "rol").filter(codigo=user_id).first()
            if usuario is None and user_id.isdigit():
                usuario = Usuario.objects.select_related("user", "rol").filter(pk=int(user_id)).first()
            if usuario is not None and not es_super and (
                    usuario.delegacion_id != perfil.delegacion_id or usuario.rol.codigo == "superusuario"):
                usuario = None  # fuera de su delegación: no existe para esta persona
            if usuario is None:
                messages.error(request, "No fue posible actualizar el usuario.")
            elif usuario.pk == perfil.pk:
                messages.error(request, "No puede desactivar su propia cuenta.")
            elif usuario.codigo == CODIGO_ADMIN_GLOBAL:
                messages.error(request, "Esta cuenta está protegida y no puede desactivarse.")
            else:
                usuario.estado = (
                    EstadoRegistro.INACTIVO if usuario.estado == EstadoRegistro.ACTIVO else EstadoRegistro.ACTIVO
                )
                usuario.save(update_fields=["estado"])
                if usuario.user_id:
                    usuario.user.is_active = usuario.activo
                    usuario.user.save(update_fields=["is_active"])
                estado = "activada" if usuario.activo else "desactivada"
                messages.success(request, f"Cuenta de {usuario.nombre} {estado}.")
            return redirect("admin_usuarios")

        rut_ingresado = (request.POST.get("rut") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        email = (request.POST.get("email") or "").strip()
        rol_codigo = (request.POST.get("rol") or "").strip()
        cargo_nombre = (request.POST.get("cargo") or "").strip()
        delegacion_nombre = (request.POST.get("delegacion") or "").strip()
        id_funcionario = (request.POST.get("id_funcionario") or "").strip()
        if not es_super:
            # Quien no es superusuario solo crea cuentas de su delegación y nunca de superusuario.
            delegacion_nombre = perfil.delegacion.nombre if perfil.delegacion_id else ""
            if rol_codigo == "superusuario":
                rol_codigo = ""
        valores = {
            "rut": rut_ingresado,
            "nombre": nombre,
            "email": email,
            "rol": rol_codigo,
            "cargo": cargo_nombre,
            "delegacion": delegacion_nombre,
            "id_funcionario": id_funcionario,
        }
        from django.contrib.auth import get_user_model

        User = get_user_model()
        funcionario = Funcionario.objects.filter(codigo=id_funcionario).first() if id_funcionario else None
        if funcionario is not None and not es_super and funcionario.delegacion_id != perfil.delegacion_id:
            funcionario = None
            errores["id_funcionario"] = "Esa ficha no pertenece a su delegación."
        # Acepta puntos, espacios, «k» minúscula y RUT sin guion; el motivo del rechazo se explica.
        rut = rut_canonico(rut_ingresado)
        if rut is None:
            errores["rut"] = motivo_rut_invalido(rut_ingresado) or MENSAJE_RUT
        elif funcionario is not None and funcionario.rut and funcionario.rut != rut:
            errores["rut"] = "El RUT no coincide con el de la ficha seleccionada. Corrija el RUT o elija otra ficha."
        elif Usuario.objects.filter(username=rut).exists() or (
                Funcionario.objects.filter(rut=rut).exclude(pk=funcionario.pk if funcionario else None).exists()):
            errores["rut"] = "Ese RUT ya está registrado."
        elif User.objects.filter(username=rut).exists():
            # Cuenta de acceso sin perfil (restos de una carga anterior). No se reutiliza: podría
            # conservar una contraseña antigua o ser de un administrador.
            errores["rut"] = ("Ya existe una cuenta de acceso con ese RUT sin perfil asociado. "
                              "Pida al administrador técnico que la revise antes de crear el usuario.")
        if len(nombre) < 5:
            errores["nombre"] = "Ingrese el nombre completo (mínimo 5 caracteres)."
        elif not validar_nombre(nombre):
            errores["nombre"] = MENSAJE_NOMBRE
        if not email:
            errores["email"] = "Ingrese el correo del usuario para enviar su activación."
        if not _correo_habilitado():
            errores["email"] = "El envío de correo no está configurado. No se creó la cuenta."
        if email and (len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
            errores["email"] = "Ingrese un correo válido (hasta 254 caracteres)."
        if email and "email" not in errores and Usuario.objects.filter(correo__iexact=email).exists():
            errores["email"] = "Ese correo ya está registrado."
        rol = Rol.objects.filter(codigo=rol_codigo).first()
        if rol is None:
            errores["rol"] = "Seleccione un rol válido."
        cargo = Cargo.objects.filter(nombre=cargo_nombre).first() if cargo_nombre else None
        if not cargo_nombre or cargo is None:
            errores["cargo"] = "Seleccione o indique un cargo."
        # Solo delegaciones existentes: escribir mal el nombre ya no crea una delegación nueva.
        delegacion = Delegacion.objects.filter(nombre=delegacion_nombre).first() if delegacion_nombre else None
        if delegacion is None:
            errores["delegacion"] = "Seleccione la delegación del trabajador de la lista."
        if funcionario is not None and Usuario.objects.filter(funcionario=funcionario).exists():
            errores["id_funcionario"] = "Esa ficha ya tiene una cuenta."
        if errores:
            messages.error(request, "Revise los campos marcados antes de guardar el usuario.")
        else:
            try:
                with transaction.atomic():
                    partes = [p for p in nombre.split() if p]
                    nombres = partes[0][:60]
                    paterno = (partes[1] if len(partes) > 1 else "Registro")[:60]
                    materno = (" ".join(partes[2:])[:60] or None) if len(partes) > 2 else None
                    if nombres == "Registro":
                        gen_n, gen_p, gen_m = identidad(Funcionario.objects.count() + 1)
                        nombres, paterno, materno = gen_n, gen_p, gen_m
                    visible = nombre_almacenado(nombres, paterno, materno or "")
                    if funcionario is None:
                        funcionario = Funcionario(
                            codigo=siguiente_codigo(Funcionario, "codigo", "FUN-", 3),
                            cargo=cargo,
                            delegacion=delegacion,
                            estado=EstadoRegistro.ACTIVO,
                        )
                    funcionario.rut = rut
                    funcionario.nombres = nombres
                    funcionario.apellido_paterno = paterno
                    funcionario.apellido_materno = materno
                    funcionario.nombre = visible[:120]
                    funcionario.cargo = cargo
                    funcionario.delegacion = delegacion
                    funcionario.es_simulacion = False
                    funcionario.save()
                    correo = email or f"{funcionario.codigo.lower()}@siged.test"
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    user = User(username=rut, email=correo, is_active=True)
                    user.first_name = nombres[:150]
                    user.last_name = paterno[:150]
                    user.set_unusable_password()
                    user.save()
                    creado = Usuario.objects.create(
                        codigo=siguiente_codigo(Usuario, "codigo", "USR-", 3),
                        user=user,
                        username=rut,
                        nombre=funcionario.nombre,
                        correo=correo,
                        rol=rol,
                        cargo=cargo,
                        delegacion=delegacion,
                        funcionario=funcionario,
                        estado=EstadoRegistro.ACTIVO,
                    )
                    codigo = emitir_codigo(creado, ip=(request.META.get('REMOTE_ADDR') or '')[:45])
                    token = signing.dumps({'usuario': creado.pk}, salt='siged-activar-cuenta')
                    enlace = request.build_absolute_uri(reverse('activar_cuenta')) + '?token=' + token
                    enviar_codigo(creado, codigo, enlace=enlace, activacion=True)

            except (OSError, SMTPException, RuntimeError):
                messages.error(request, 'No se pudo enviar la invitación. No se creó el usuario; revise el correo e intente nuevamente.')
            except (DatabaseError, ValidationError) as error:
                # Doble envío, dato que no cabe en la base u otra restricción: no queda nada a medias
                # (la transacción se revierte) y el registro no incluye datos personales.
                log_seguridad.error("alta_usuario_rechazada %s", type(error).__name__)
                messages.error(request, 'No se pudo crear el usuario. No se guardó nada; revise los datos o '
                                        'intente de nuevo en un momento. Si se repite, avise al administrador técnico.')
            else:
                messages.success(request, f'Usuario {formatear_rut(rut)} creado. Invitación enviada a {email}; el usuario definirá su contraseña.')
                return redirect('admin_usuarios')

    from control_gestion.reportes import usuarios_filtrados
    listado_usuarios = usuarios_filtrados(request)
    from core.paginacion import paginar
    pagina_usuarios,paginacion=paginar(request,listado_usuarios)
    roles_qs = Rol.objects.order_by("nombre")
    roles = list((roles_qs if es_super else roles_qs.exclude(codigo="superusuario")).values_list("codigo", "nombre"))
    contexto = {
        "usuarios": [
            _usuario_a_fila(item)
            for item in pagina_usuarios
        ],
        "funcionarios": [
            {"id_funcionario": fun.codigo, "nombre": fun.nombre_mostrado}
            # Solo fichas sin cuenta: elegir una que ya tiene usuario terminaba en error.
            for fun in (Funcionario.objects.filter(usuario__isnull=True).order_by("nombre") if es_super else
                        Funcionario.objects.filter(delegacion_id=perfil.delegacion_id, usuario__isnull=True).order_by("nombre"))
        ],
        "cargos": Cargo.objects.order_by("nombre"),
        "roles": roles,
        "delegaciones": nombres_delegaciones() if es_super else ([perfil.delegacion.nombre] if perfil.delegacion_id else []),
        "errores": errores,
        "valores": valores,
        "seccion": "usuarios",
        "q": request.GET.get("q", ""),
        "consulta_usuarios": request.GET.urlencode(),
        **paginacion,
    }
    return render(request, "cuentas/usuarios.html", contexto)


def administracion_cargos_view(request):
    bloqueo = requerir_modulo(request, "administracion") or _solo_superusuario(request)
    if bloqueo:
        return bloqueo
    errores = {}
    valores = {}
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        descripcion = (request.POST.get("descripcion") or "").strip()
        modulo = (request.POST.get("modulo_principal") or "").strip()
        valores = {"nombre": nombre, "descripcion": descripcion, "modulo_principal": modulo}
        if len(nombre) < 4:
            errores["nombre"] = "Ingrese el nombre del cargo (mínimo 4 caracteres)."
        elif Cargo.objects.filter(nombre__iexact=nombre).exists():
            errores["nombre"] = "Ya existe un cargo con ese nombre."
        if len(descripcion) < 10:
            errores["descripcion"] = "Describa el cargo con al menos 10 caracteres."
        if not modulo:
            errores["modulo_principal"] = "Indique el módulo principal asociado."
        if errores:
            messages.error(request, "Complete los campos obligatorios del cargo.")
        else:
            Cargo.objects.create(
                codigo=siguiente_codigo(Cargo, "codigo", "CARGO-", 2),
                nombre=nombre,
                descripcion=descripcion,
                modulo_principal=modulo,
            )
            messages.success(request, f"Cargo «{nombre}» agregado.")
            return redirect("admin_cargos")
    cargos = [
        {
            "id_cargo": cargo.codigo or f"CARGO-{cargo.pk}",
            "nombre": cargo.nombre,
            "descripcion": cargo.descripcion,
            "modulo_principal": cargo.modulo_principal,
        }
        for cargo in Cargo.objects.order_by("nombre")
    ]
    contexto = {"cargos": cargos, "errores": errores, "valores": valores, "seccion": "cargos"}
    return render(request, "cuentas/cargos.html", contexto)


def _medicion_actual():
    return Medicion.objects.select_related("delegacion_piloto").order_by("-fecha_inicio").first()


def _medicion_dict(medicion):
    if medicion is None:
        return {"periodo": "", "fecha_inicio": "", "fecha_termino": ""}
    return {
        "periodo": medicion.periodo,
        "fecha_inicio": medicion.fecha_inicio.isoformat(),
        "fecha_termino": medicion.fecha_termino.isoformat(),
    }


def administracion_parametros_view(request):
    bloqueo = requerir_modulo(request, "administracion") or _solo_superusuario(request)
    if bloqueo:
        return bloqueo
    parametros = obtener_parametros()
    medicion_vista = _medicion_dict(_medicion_actual())
    errores = {}
    if request.method == "POST":
        nombre_sistema = (request.POST.get("nombre_sistema") or "").strip()
        comuna = (request.POST.get("comuna") or "").strip()
        try:
            sla_verde = int(request.POST.get("sla_verde_max_dias") or 0)
            sla_amarillo = int(request.POST.get("sla_amarillo_max_dias") or 0)
            meta_tubo = int(request.POST.get("meta_tubo_porcentaje") or 0)
            max_atenciones = int(request.POST.get("max_atenciones_mismo_usuario") or 0)
        except (TypeError, ValueError):
            sla_verde = sla_amarillo = meta_tubo = max_atenciones = 0
        encuesta = request.POST.get("encuesta_habilitada") == "on"
        if len(nombre_sistema) < 8:
            errores["nombre_sistema"] = "Ingrese el nombre del sistema."
        if not comuna:
            errores["comuna"] = "Ingrese la comuna."
        if sla_verde < 1 or sla_verde > 10:
            errores["sla_verde_max_dias"] = "El semáforo verde debe estar entre 1 y 10 días."
        if sla_amarillo <= sla_verde or sla_amarillo > 15:
            errores["sla_amarillo_max_dias"] = "El semáforo amarillo debe ser mayor que el verde y hasta 15 días."
        if meta_tubo < 50 or meta_tubo > 100:
            errores["meta_tubo_porcentaje"] = "La meta del tubo debe estar entre 50% y 100%."
        if max_atenciones < 1 or max_atenciones > 10:
            errores["max_atenciones_mismo_usuario"] = "Indique un máximo entre 1 y 10 atenciones."
        if errores:
            messages.error(request, "Hay errores de formato en los parámetros. No se guardaron los cambios.")
            parametros = {
                **parametros,
                "nombre_sistema": nombre_sistema,
                "comuna": comuna,
                "sla_verde_max_dias": sla_verde,
                "sla_amarillo_max_dias": sla_amarillo,
                "meta_tubo_porcentaje": meta_tubo,
                "encuesta_habilitada": encuesta,
                "max_atenciones_mismo_usuario": max_atenciones,
            }
        else:
            registro = ParametroSistema.objects.order_by("pk").first() or ParametroSistema()
            registro.nombre_sistema = nombre_sistema
            registro.comuna = comuna
            registro.sla_verde_max_dias = sla_verde
            registro.sla_amarillo_max_dias = sla_amarillo
            registro.meta_tubo_porcentaje = meta_tubo
            registro.encuesta_habilitada = encuesta
            registro.max_atenciones_mismo_usuario = max_atenciones
            registro.save()
            from cuentas.servicios import CACHE_PETICION
            (CACHE_PETICION.get() or {}).pop("parametros", None)
            messages.success(request, "Parámetros actualizados.")
            return redirect("admin_parametros")
    contexto = {
        "parametros": parametros,
        "medicion": medicion_vista,
        "errores": errores,
        "seccion": "parametros",
    }
    return render(request, "cuentas/parametros.html", contexto)


def activar_cuenta_view(request):
    try:
        datos = signing.loads(request.GET.get('token', ''), salt='siged-activar-cuenta', max_age=600)
        usuario = Usuario.objects.select_related('user').get(pk=datos['usuario'], estado=EstadoRegistro.ACTIVO, user__is_active=True)
        if usuario.user.has_usable_password():
            raise ValueError('Cuenta ya activada')
    except (signing.BadSignature, Usuario.DoesNotExist, KeyError, ValueError, TypeError):
        messages.error(request, 'La invitación no es válida o expiró. Solicite un código nuevo en Recuperar contraseña.')
        return redirect('recuperar_contrasena')
    request.session.cycle_key()
    _sesion_recuperacion(request, usuario, verificado=False)
    messages.info(request, 'Ingrese el código de 6 dígitos recibido por correo para crear su contraseña.')
    return redirect('validar_codigo')


class RestablecerEnlaceView(PasswordResetConfirmView):
    template_name='cuentas/restablecer_enlace.html'
    form_class=RestablecerEnlaceForm
    post_reset_login=False

    def get_user(self, uidb64):
        user=super().get_user(uidb64)
        if user is None or not user.is_active:
            return None
        if not Usuario.objects.filter(user=user,estado=EstadoRegistro.ACTIVO).exists():
            return None
        return user

    def form_valid(self, form):
        with transaction.atomic():
            response=super().form_valid(form)
            from cuentas.models import CodigoUnUso
            from django.utils import timezone
            CodigoUnUso.objects.filter(usuario__user=self.user,usado_en__isnull=True,anulado_en__isnull=True).update(anulado_en=timezone.now())
        self.request.session.pop('recuperacion',None)
        messages.success(self.request,'Su contraseña fue actualizada. Ya puede ingresar con su nueva contraseña.')
        return response

    def get_success_url(self):
        return reverse('login')
