import re

from django.contrib import messages
from django.shortcuts import redirect, render

from cuentas.auth import public_user, requerir_modulo, usuario_sesion
from cuentas.store import cargar_json_seguro, cargar_parametros, guardar_json_seguro

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


def login_view(request):
    if usuario_sesion(request):
        return redirect("inicio")
    usuarios = cargar_json_seguro("usuarios.json", [])
    demos = [
        {
            "username": item.get("username"),
            "password": item.get("password"),
            "nombre": item.get("nombre"),
            "rol": item.get("rol"),
            "cargo": item.get("cargo"),
        }
        for item in usuarios
        if item.get("activo", True)
    ]
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
            encontrado = next(
                (
                    item
                    for item in usuarios
                    if item.get("username") == username and item.get("activo", True)
                ),
                None,
            )
            if encontrado is None or encontrado.get("password") != password:
                errores["password"] = "Usuario o contraseña incorrectos."
                messages.error(request, "No fue posible iniciar sesión. Revise las credenciales de demostración.")
            else:
                request.session["usuario"] = public_user(encontrado)
                request.session["notificaciones_leidas"] = []
                messages.success(
                    request,
                    f"Bienvenido/a, {encontrado.get('nombre')}. Perfil: {encontrado.get('cargo')}.",
                )
                return redirect(_next_seguro(request.POST.get("next") or request.GET.get("next")))
    contexto = {
        "demos": demos,
        "errores": errores,
        "valores": valores,
        "next_url": _next_seguro(request.GET.get("next") or request.POST.get("next")),
    }
    return render(request, "cuentas/login.html", contexto)


def logout_view(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada. Puede ingresar con otro perfil de demostración.")
    return redirect("login")


def administracion_usuarios_view(request):
    bloqueo = requerir_modulo(request, "administracion")
    if bloqueo:
        return bloqueo
    usuarios = cargar_json_seguro("usuarios.json", [])
    funcionarios = cargar_json_seguro("funcionarios.json", [])
    cargos = cargar_json_seguro("cargos.json", [])
    errores = {}
    valores = {}
    if request.method == "POST":
        accion = (request.POST.get("accion") or "crear").strip()
        if accion == "toggle":
            user_id = (request.POST.get("id_usuario") or "").strip()
            actualizado = False
            for item in usuarios:
                if item.get("id_usuario") == user_id:
                    if item.get("username") == "admin":
                        messages.error(request, "El usuario administrador de demostración no puede desactivarse.")
                        return redirect("admin_usuarios")
                    item["activo"] = not bool(item.get("activo", True))
                    actualizado = True
                    break
            if actualizado and guardar_json_seguro("usuarios.json", usuarios):
                messages.success(request, "Estado del usuario actualizado.")
            else:
                messages.error(request, "No fue posible actualizar el usuario.")
            return redirect("admin_usuarios")
        username = (request.POST.get("username") or "").strip().lower()
        password = (request.POST.get("password") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        email = (request.POST.get("email") or "").strip()
        rol = (request.POST.get("rol") or "").strip()
        cargo = (request.POST.get("cargo") or "").strip()
        delegacion = (request.POST.get("delegacion") or "").strip()
        id_funcionario = (request.POST.get("id_funcionario") or "").strip()
        valores = {
            "username": username,
            "nombre": nombre,
            "email": email,
            "rol": rol,
            "cargo": cargo,
            "delegacion": delegacion,
            "id_funcionario": id_funcionario,
        }
        if not re.fullmatch(r"[a-z0-9._-]{3,20}", username or ""):
            errores["username"] = "Usuario de 3 a 20 caracteres (letras minúsculas, números, punto o guion)."
        elif any(item.get("username") == username for item in usuarios):
            errores["username"] = "Ese nombre de usuario ya existe."
        if len(password) < 6:
            errores["password"] = "La contraseña de demostración debe tener al menos 6 caracteres."
        if len(nombre) < 5:
            errores["nombre"] = "Ingrese el nombre completo (mínimo 5 caracteres)."
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errores["email"] = "Ingrese un correo válido."
        if rol not in dict(ROLES_DISPONIBLES):
            errores["rol"] = "Seleccione un rol válido."
        if not cargo:
            errores["cargo"] = "Seleccione o indique un cargo."
        if errores:
            messages.error(request, "Revise los campos marcados antes de guardar el usuario.")
        else:
            correlativo = len(usuarios) + 1
            nuevo = {
                "id_usuario": f"USR-{correlativo:03d}",
                "username": username,
                "password": password,
                "nombre": nombre,
                "email": email or f"{username}@laserena.cl",
                "rol": rol,
                "cargo": cargo,
                "delegacion": delegacion,
                "id_funcionario": id_funcionario,
                "activo": True,
            }
            usuarios.append(nuevo)
            if guardar_json_seguro("usuarios.json", usuarios):
                messages.success(request, f"Usuario {username} creado en el mockup JSON.")
                return redirect("admin_usuarios")
            messages.error(request, "No fue posible guardar usuarios.json.")
    delegaciones = [
        "Delegación Central",
        "Delegación Rural",
        "Delegación La Antena",
        "Delegación La Pampa",
        "Delegación Avenida del Mar",
        "Delegación Las Compañías",
    ]

    contexto = {
        "usuarios": usuarios,
        "funcionarios": funcionarios,
        "cargos": cargos,
        "roles": ROLES_DISPONIBLES,
        "delegaciones": delegaciones,
        "errores": errores,
        "valores": valores,
        "seccion": "usuarios",
    }
    return render(request, "cuentas/usuarios.html", contexto)


def administracion_cargos_view(request):
    bloqueo = requerir_modulo(request, "administracion")
    if bloqueo:
        return bloqueo
    cargos = cargar_json_seguro("cargos.json", [])
    errores = {}
    valores = {}
    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        descripcion = (request.POST.get("descripcion") or "").strip()
        modulo = (request.POST.get("modulo_principal") or "").strip()
        valores = {"nombre": nombre, "descripcion": descripcion, "modulo_principal": modulo}
        if len(nombre) < 4:
            errores["nombre"] = "Ingrese el nombre del cargo (mínimo 4 caracteres)."
        if len(descripcion) < 10:
            errores["descripcion"] = "Describa el cargo con al menos 10 caracteres."
        if not modulo:
            errores["modulo_principal"] = "Indique el módulo principal asociado."
        if errores:
            messages.error(request, "Complete los campos obligatorios del cargo.")
        else:
            correlativo = len(cargos) + 1
            cargos.append(
                {
                    "id_cargo": f"CARGO-{correlativo:02d}",
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "modulo_principal": modulo,
                }
            )
            if guardar_json_seguro("cargos.json", cargos):
                messages.success(request, f"Cargo «{nombre}» agregado.")
                return redirect("admin_cargos")
            messages.error(request, "No fue posible guardar cargos.json.")
    contexto = {
        "cargos": cargos,
        "errores": errores,
        "valores": valores,
        "seccion": "cargos",
    }
    return render(request, "cuentas/cargos.html", contexto)


def administracion_parametros_view(request):
    bloqueo = requerir_modulo(request, "administracion")
    if bloqueo:
        return bloqueo
    parametros = cargar_json_seguro("parametros.json", {})
    medicion = cargar_json_seguro("medicion.json", {})
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
        if not fecha_inicio or not fecha_termino:
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
            medicion = {
                **medicion,
                "periodo": periodo,
                "fecha_inicio": fecha_inicio,
                "fecha_termino": fecha_termino,
            }
        else:
            parametros.update(
                {
                    "nombre_sistema": nombre_sistema,
                    "comuna": comuna,
                    "sla_verde_max_dias": sla_verde,
                    "sla_amarillo_max_dias": sla_amarillo,
                    "meta_tubo_porcentaje": meta_tubo,
                    "encuesta_habilitada": encuesta,
                    "max_atenciones_mismo_usuario": max_atenciones,
                }
            )
            medicion["periodo"] = periodo
            medicion["fecha_inicio"] = fecha_inicio
            medicion["fecha_termino"] = fecha_termino
            medicion["meta_cumplimiento_tubo"] = meta_tubo
            ok_params = guardar_json_seguro("parametros.json", parametros)
            ok_med = guardar_json_seguro("medicion.json", medicion)
            if ok_params and ok_med:
                messages.success(request, "Parámetros de demostración actualizados (JSON local).")
                return redirect("admin_parametros")
            messages.error(request, "No fue posible guardar los archivos JSON de parámetros.")
    contexto = {
        "parametros": parametros or cargar_parametros(),
        "medicion": medicion,
        "errores": errores,
        "seccion": "parametros",
    }
    return render(request, "cuentas/parametros.html", contexto)
