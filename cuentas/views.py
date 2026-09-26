import re
import secrets
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.utils import timezone

from cuentas.auth import requerir_modulo, usuario_sesion
from cuentas.forms import NuevaContrasenaForm
from cuentas.models import Cargo, Delegacion, EstadoRegistro, Funcionario, ParametroSistema, Rol, Usuario
from cuentas.servicios import autenticar, nombres_delegaciones, obtener_parametros, sesion_desde_usuario, siguiente_codigo
from control_gestion.models import Medicion

CLAVES_DEMOSTRACION = {
    "admin": "admin123",
    "jefatura": "jefatura123",
    "funcionario": "funcionario123",
    "ventanilla": "ventanilla123",
}

ROLES_DISPONIBLES = [
    ("administrador", "Administrador"),
    ("jefatura", "Jefatura / Control de gestión"),
    ("funcionario", "Funcionario territorial"),
    ("ventanilla", "Ventanilla ciudadana"),
]


def _next_seguro(valor):
    if valor and valor.startswith("/") and not valor.startswith("//"):
        return valor
    return "/"


def _demos():
    demos = []
    usuarios = Usuario.objects.filter(estado=EstadoRegistro.ACTIVO).select_related("rol", "cargo", "user")
    for usuario in usuarios:
        clave = CLAVES_DEMOSTRACION.get(usuario.username)
        if clave and usuario.user_id and usuario.user.check_password(clave):
            visible = clave
        elif usuario.user_id:
            visible = "actualizada"
        else:
            visible = "sin clave"
        demos.append(
            {
                "username": usuario.username,
                "password": visible,
                "nombre": usuario.nombre,
                "rol": usuario.rol.codigo if usuario.rol_id else "",
                "cargo": usuario.cargo.nombre if usuario.cargo_id else "",
            }
        )
    return demos


def login_view(request):
    if request.user.is_authenticated and usuario_sesion(request):
        return redirect("inicio")
    errores = {}
    valores = {"username": ""}
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        valores["username"] = username
        if not username:
            errores["username"] = "Ingrese el usuario."
        if not password:
            errores["password"] = "Ingrese la contraseña."
        if not errores:
            encontrado = autenticar(username, password)
            if encontrado is None:
                errores["password"] = "Usuario o contraseña incorrectos."
                messages.error(request, "No fue posible iniciar sesión. Revise sus credenciales.")
            else:
                auth_login(request, encontrado.user)
                request.session["usuario"] = sesion_desde_usuario(encontrado)
                request.session["notificaciones_leidas"] = []
                messages.success(
                    request,
                    f"Bienvenido/a, {encontrado.nombre}. Perfil: {encontrado.cargo.nombre if encontrado.cargo_id else encontrado.rol.nombre}.",
                )
                return redirect(_next_seguro(request.POST.get("next") or request.GET.get("next")))
    contexto = {
        "demos": _demos(),
        "errores": errores,
        "valores": valores,
        "next_url": _next_seguro(request.GET.get("next") or request.POST.get("next")),
    }
    return render(request, "cuentas/login.html", contexto)


def logout_view(request):
    auth_logout(request)
    messages.info(request, "Sesión cerrada. Puede ingresar con otro perfil de demostración.")
    return redirect("login")


def _guardar_recuperacion(request, usuario, codigo):
    request.session["recuperacion"] = {
        "usuario_id": usuario.pk,
        "codigo": codigo,
        "expira": (timezone.now() + timedelta(minutes=10)).isoformat(),
        "correo": usuario.correo,
        "verificado": False,
    }
    request.session.modified = True


def _recuperacion_vigente(request):
    datos = request.session.get("recuperacion") or {}
    if not datos.get("usuario_id") or not datos.get("codigo"):
        return None
    try:
        expira = datetime.fromisoformat(datos["expira"])
        if timezone.is_naive(expira):
            expira = timezone.make_aware(expira, timezone.get_current_timezone())
    except (TypeError, ValueError):
        return None
    if timezone.now() > expira:
        return None
    return datos


def recuperar_contrasena_view(request):
    errores = {}
    correo = ""
    if request.method == "POST":
        correo = (request.POST.get("correo") or "").strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            errores["correo"] = "Ingrese un correo electrónico válido."
        else:
            usuario = (
                Usuario.objects.select_related("user")
                .filter(correo__iexact=correo, estado=EstadoRegistro.ACTIVO)
                .first()
            )
            if usuario is None or usuario.user_id is None:
                errores["correo"] = "No encontramos un usuario activo con ese correo."
            else:
                codigo = f"{secrets.randbelow(1_000_000):06d}"
                _guardar_recuperacion(request, usuario, codigo)
                messages.success(
                    request,
                    "Generamos un código de 6 dígitos, vigente por 10 minutos. "
                    f"En esta demostración (sin servidor de correo) el código es {codigo}.",
                )
                return redirect("validar_codigo")
    return render(request, "cuentas/recuperar.html", {"errores": errores, "correo": correo})


def validar_codigo_view(request):
    datos = _recuperacion_vigente(request)
    if datos is None:
        messages.error(request, "El código expiró o no hay una recuperación en curso. Solicite uno nuevo.")
        return redirect("recuperar_contrasena")
    errores = {}
    if request.method == "POST":
        if (request.POST.get("accion") or "") == "reenviar":
            usuario = Usuario.objects.filter(pk=datos["usuario_id"]).first()
            if usuario is None:
                messages.error(request, "No fue posible reenviar el código.")
                return redirect("recuperar_contrasena")
            codigo = f"{secrets.randbelow(1_000_000):06d}"
            _guardar_recuperacion(request, usuario, codigo)
            messages.success(request, f"Enviamos un código nuevo. En esta demostración el código es {codigo}.")
            return redirect("validar_codigo")
        ingresado = "".join((request.POST.get(f"d{i}") or "").strip() for i in range(1, 7))
        if not re.fullmatch(r"\d{6}", ingresado):
            errores["codigo"] = "Ingrese los 6 dígitos del código."
        elif not secrets.compare_digest(ingresado, datos["codigo"]):
            errores["codigo"] = "El código no coincide. Revíselo e intente de nuevo."
        else:
            datos["verificado"] = True
            request.session["recuperacion"] = datos
            request.session.modified = True
            messages.success(request, "Código verificado. Defina su nueva contraseña.")
            return redirect("nueva_contrasena")
        messages.error(request, "No pudimos validar el código.")
    return render(
        request,
        "cuentas/validar_codigo.html",
        {"errores": errores, "correo": datos.get("correo", "")},
    )


def nueva_contrasena_view(request):
    datos = _recuperacion_vigente(request)
    if datos is None or not datos.get("verificado"):
        messages.error(request, "Primero debe validar el código enviado a su correo.")
        return redirect("validar_codigo" if datos else "recuperar_contrasena")
    form = NuevaContrasenaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = Usuario.objects.select_related("user").filter(pk=datos["usuario_id"]).first()
        if usuario is None or usuario.user_id is None:
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
    return {
        "id_usuario": usuario.codigo or str(usuario.pk),
        "username": usuario.username,
        "nombre": usuario.nombre,
        "email": usuario.correo,
        "rol": usuario.rol.nombre if usuario.rol_id else "",
        "cargo": usuario.cargo.nombre if usuario.cargo_id else "",
        "activo": usuario.activo,
    }


def administracion_usuarios_view(request):
    bloqueo = requerir_modulo(request, "administracion")
    if bloqueo:
        return bloqueo
    errores = {}
    valores = {}
    if request.method == "POST":
        accion = (request.POST.get("accion") or "crear").strip()
        if accion == "toggle":
            user_id = (request.POST.get("id_usuario") or "").strip()
            usuario = Usuario.objects.select_related("user").filter(codigo=user_id).first()
            if usuario is None:
                messages.error(request, "No fue posible actualizar el usuario.")
            elif usuario.username == "admin":
                messages.error(request, "El usuario administrador de demostración no puede desactivarse.")
            else:
                usuario.estado = (
                    EstadoRegistro.INACTIVO if usuario.estado == EstadoRegistro.ACTIVO else EstadoRegistro.ACTIVO
                )
                usuario.save(update_fields=["estado"])
                if usuario.user_id:
                    usuario.user.is_active = usuario.activo
                    usuario.user.save(update_fields=["is_active"])
                messages.success(request, "Estado del usuario actualizado.")
            return redirect("admin_usuarios")

        username = (request.POST.get("username") or "").strip().lower()
        password = (request.POST.get("password") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        email = (request.POST.get("email") or "").strip()
        rol_codigo = (request.POST.get("rol") or "").strip()
        cargo_nombre = (request.POST.get("cargo") or "").strip()
        delegacion_nombre = (request.POST.get("delegacion") or "").strip()
        id_funcionario = (request.POST.get("id_funcionario") or "").strip()
        valores = {
            "username": username,
            "nombre": nombre,
            "email": email,
            "rol": rol_codigo,
            "cargo": cargo_nombre,
            "delegacion": delegacion_nombre,
            "id_funcionario": id_funcionario,
        }
        if not re.fullmatch(r"[a-z0-9._-]{3,20}", username or ""):
            errores["username"] = "Usuario de 3 a 20 caracteres (letras minúsculas, números, punto o guion)."
        elif Usuario.objects.filter(username=username).exists():
            errores["username"] = "Ese nombre de usuario ya existe."
        if len(password) < 6:
            errores["password"] = "La contraseña de demostración debe tener al menos 6 caracteres."
        if len(nombre) < 5:
            errores["nombre"] = "Ingrese el nombre completo (mínimo 5 caracteres)."
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errores["email"] = "Ingrese un correo válido."
        if email and Usuario.objects.filter(correo__iexact=email).exists():
            errores["email"] = "Ese correo ya está registrado."
        rol = Rol.objects.filter(codigo=rol_codigo).first()
        if rol is None:
            errores["rol"] = "Seleccione un rol válido."
        cargo = Cargo.objects.filter(nombre=cargo_nombre).first() if cargo_nombre else None
        if not cargo_nombre or cargo is None:
            errores["cargo"] = "Seleccione o indique un cargo."
        if errores:
            messages.error(request, "Revise los campos marcados antes de guardar el usuario.")
        else:
            delegacion = None
            if delegacion_nombre:
                delegacion, _ = Delegacion.objects.get_or_create(
                    nombre=delegacion_nombre, defaults={"comuna": "La Serena"}
                )
            funcionario = Funcionario.objects.filter(codigo=id_funcionario).first() if id_funcionario else None
            correo = email or f"{username}@laserena.cl"
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User(username=username, email=correo, is_active=True)
            partes = nombre.split(" ", 1)
            user.first_name = partes[0][:150]
            user.last_name = (partes[1] if len(partes) > 1 else "")[:150]
            user.set_password(password)
            user.save()
            Usuario.objects.create(
                codigo=siguiente_codigo(Usuario, "codigo", "USR-", 3),
                user=user,
                username=username,
                nombre=nombre,
                correo=correo,
                rol=rol,
                cargo=cargo,
                delegacion=delegacion,
                funcionario=funcionario,
                estado=EstadoRegistro.ACTIVO,
            )
            messages.success(request, f"Usuario {username} creado.")
            return redirect("admin_usuarios")

    roles = list(Rol.objects.order_by("nombre").values_list("codigo", "nombre")) or ROLES_DISPONIBLES
    contexto = {
        "usuarios": [
            _usuario_a_fila(item)
            for item in Usuario.objects.select_related("rol", "cargo").order_by("nombre")
        ],
        "funcionarios": [
            {"id_funcionario": fun.codigo, "nombre": fun.nombre}
            for fun in Funcionario.objects.order_by("nombre")
        ],
        "cargos": Cargo.objects.order_by("nombre"),
        "roles": roles,
        "delegaciones": nombres_delegaciones(),
        "errores": errores,
        "valores": valores,
        "seccion": "usuarios",
    }
    return render(request, "cuentas/usuarios.html", contexto)


def administracion_cargos_view(request):
    bloqueo = requerir_modulo(request, "administracion")
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
    bloqueo = requerir_modulo(request, "administracion")
    if bloqueo:
        return bloqueo
    parametros = obtener_parametros()
    medicion = _medicion_actual()
    medicion_vista = _medicion_dict(medicion)
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
        periodo = (request.POST.get("periodo") or "").strip()
        fecha_inicio = (request.POST.get("fecha_inicio") or "").strip()
        fecha_termino = (request.POST.get("fecha_termino") or "").strip()
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
        if not periodo:
            errores["periodo"] = "Indique el periodo de medición."
        try:
            inicio = date.fromisoformat(fecha_inicio)
            termino = date.fromisoformat(fecha_termino)
        except ValueError:
            inicio = termino = None
            errores["fecha_inicio"] = "Ingrese fecha de inicio y término del periodo."
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
            medicion_vista = {"periodo": periodo, "fecha_inicio": fecha_inicio, "fecha_termino": fecha_termino}
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
            piloto = medicion.delegacion_piloto if medicion else None
            if piloto is None:
                piloto = (
                    Delegacion.objects.filter(nombre__icontains="Rural").first()
                    or Delegacion.objects.order_by("pk").first()
                )
            if piloto is None:
                piloto = Delegacion.objects.create(nombre="Delegación Centro", comuna=comuna or "La Serena")
            if medicion is None:
                Medicion.objects.create(
                    periodo=periodo,
                    delegacion_piloto=piloto,
                    fecha_inicio=inicio,
                    fecha_termino=termino,
                    dias_totales=max((termino - inicio).days, 1),
                    meta_cumplimiento_tubo=meta_tubo,
                )
            else:
                medicion.periodo = periodo
                medicion.fecha_inicio = inicio
                medicion.fecha_termino = termino
                medicion.meta_cumplimiento_tubo = meta_tubo
                medicion.save()
            messages.success(request, "Parámetros actualizados.")
            return redirect("admin_parametros")
    contexto = {
        "parametros": parametros,
        "medicion": medicion_vista,
        "errores": errores,
        "seccion": "parametros",
    }
    return render(request, "cuentas/parametros.html", contexto)
