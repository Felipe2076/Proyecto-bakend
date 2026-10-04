"""Regenera fixtures, data/*.json y D003 con identidades ficticias.

Uso (desde la raíz del repo, con el entorno de Django)::

    python manage.py generar_simulacion

No escribe claves utilizables. D003 y el fixture dejan la contraseña en ``!``.
``importar_json`` asigna una distinta por cuenta. Es idempotente en los RUT.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from cuentas.simulacion import (
    CARGO_POR_ROL,
    CODIGO_ADMIN_GLOBAL,
    ROLES_ORDEN,
    correo_funcionario,
    correo_vecino,
    direccion_ficticia,
    es_organizacion,
    identidad,
    nombre_visible,
    rut_trabajador,
    rut_vecino,
    telefono_ficticio,
)
from cuentas.vocabulario import DELEGACIONES_OFICIALES

MARCA_INICIO = "<!-- cuentas-simulacion:inicio -->"
MARCA_FIN = "<!-- cuentas-simulacion:fin -->"


def _sql(valor):
    if valor is None:
        return "NULL"
    return "'" + str(valor).replace("\\", "\\\\").replace("'", "''") + "'"


def _cargar(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def _guardar(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


class Command(BaseCommand):
    help = "Regenera datos de simulación (fixtures, data/*.json y D003) sin claves en claro."

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR)
        fixture_ruta = base / "fixtures" / "02_datos_sistema.json"
        data_dir = base / "data"
        sql_ruta = base / "sql" / "datos" / "D003__datos_simulacion.sql"
        sql_ruta.parent.mkdir(parents=True, exist_ok=True)

        fixture = _cargar(fixture_ruta)
        resultado = _transformar_fixture(fixture)
        _guardar(fixture_ruta, fixture)
        _reescribir_json(data_dir, resultado)
        sql_ruta.write_text(_sql_d003(resultado), encoding="utf-8")
        tabla = _tabla_markdown(resultado["cuentas"])
        (base / "sql" / "datos" / "TABLA_CUENTAS.md").write_text(tabla, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"Simulación regenerada: {len(resultado['cuentas'])} cuentas, "
            f"{resultado['vecinos']} vecinos, D003 en {sql_ruta.name}."
        ))
        self.stdout.write(tabla)


def _por_modelo(fixture, modelo):
    return [obj for obj in fixture if obj["model"] == modelo]


def _transformar_fixture(fixture):
    delegaciones = {obj["pk"]: obj["fields"]["nombre"] for obj in _por_modelo(fixture, "cuentas.delegacion")}
    delegacion_pk = {nombre: pk for pk, nombre in delegaciones.items()}
    roles = {obj["pk"]: obj["fields"]["codigo"] for obj in _por_modelo(fixture, "cuentas.rol")}
    rol_pk = {codigo: pk for pk, codigo in roles.items()}
    cargos = {obj["fields"]["nombre"]: obj["pk"] for obj in _por_modelo(fixture, "cuentas.cargo")}

    funcionarios = sorted(_por_modelo(fixture, "cuentas.funcionario"), key=lambda obj: obj["fields"]["codigo"])
    mapa = {}
    fun_por_pk = {}
    indice = 0
    for obj in funcionarios:
        indice += 1
        campos = obj["fields"]
        viejo = campos.get("nombre") or ""
        nombres, paterno, materno = identidad(indice)
        campos["rut"] = rut_trabajador(indice)
        campos["nombres"] = nombres
        campos["apellido_paterno"] = paterno
        campos["apellido_materno"] = materno
        campos["es_simulacion"] = True
        campos["nombre"] = nombre_visible(nombres, paterno, materno, True)
        if viejo and viejo != campos["nombre"]:
            mapa[viejo] = campos["nombre"]
        fun_por_pk[obj["pk"]] = obj

    usuarios = _por_modelo(fixture, "cuentas.usuario")
    max_fun_pk = max((obj["pk"] for obj in funcionarios), default=0)
    max_usr_pk = max((obj["pk"] for obj in usuarios), default=0)
    cuentas = []

    def agregar_funcionario(deleg_nombre, cargo_nombre, rol_codigo):
        nonlocal indice, max_fun_pk
        indice += 1
        max_fun_pk += 1
        nombres, paterno, materno = identidad(indice)
        codigo = f"FUN-{max_fun_pk:03d}"
        # El código sigue el pk para no chocar con FUN-001.. ya usados; si el pk no
        # coincide con el número libre, se busca el siguiente código libre.
        usados = {obj["fields"]["codigo"] for obj in _por_modelo(fixture, "cuentas.funcionario")}
        n = 1
        while codigo in usados:
            n += 1
            codigo = f"FUN-{n:03d}"
        cargo_id = cargos.get(cargo_nombre) or cargos.get(CARGO_POR_ROL.get(rol_codigo)) or next(iter(cargos.values()))
        obj = {
            "model": "cuentas.funcionario",
            "pk": max_fun_pk,
            "fields": {
                "codigo": codigo,
                "rut": rut_trabajador(indice),
                "nombres": nombres,
                "apellido_paterno": paterno,
                "apellido_materno": materno,
                "nombre": nombre_visible(nombres, paterno, materno, True),
                "es_simulacion": True,
                "cargo": cargo_id,
                "delegacion": delegacion_pk[deleg_nombre],
                "fecha_ultimo_ingreso": None,
                "estado": "activo",
            },
        }
        fixture.append(obj)
        fun_por_pk[obj["pk"]] = obj
        return obj

    def ficha(usuario_obj, fun_obj, rol_codigo, nuevo=False):
        fun = fun_obj["fields"]
        campos = usuario_obj["fields"]
        campos["username"] = fun["rut"]
        campos["nombre"] = fun["nombre"]
        campos["correo"] = correo_funcionario(fun["codigo"])
        campos["funcionario"] = fun_obj["pk"]
        campos["delegacion"] = fun["delegacion"]
        campos["rol"] = rol_pk[rol_codigo]
        if not campos.get("cargo"):
            campos["cargo"] = fun["cargo"]
        campos["estado"] = campos.get("estado") or "activo"
        return {
            "codigo_usuario": campos.get("codigo") or f"USR-{usuario_obj['pk']:03d}",
            "codigo_funcionario": fun["codigo"],
            "rut": fun["rut"],
            "nombre": fun["nombre"],
            "correo": campos["correo"],
            "rol": rol_codigo,
            "delegacion": delegaciones[fun["delegacion"]],
            "cargo_id": campos.get("cargo") or fun["cargo"],
            "nuevo_usuario": nuevo,
            "nuevo_funcionario": fun["codigo"] not in _codigos_originales,
            "nombres": fun["nombres"],
            "apellido_paterno": fun["apellido_paterno"],
            "global": campos.get("codigo") == CODIGO_ADMIN_GLOBAL,
        }

    _codigos_originales = {obj["fields"]["codigo"] for obj in funcionarios}

    for usuario in usuarios:
        campos = usuario["fields"]
        rol_codigo = roles[campos["rol"]]
        if campos.get("funcionario"):
            fun_obj = fun_por_pk[campos["funcionario"]]
        else:
            deleg_nombre = delegaciones.get(campos.get("delegacion")) or "Delegación Centro"
            cargo_nombre = next((n for n, pk in cargos.items() if pk == campos.get("cargo")), CARGO_POR_ROL[rol_codigo])
            fun_obj = agregar_funcionario(deleg_nombre, cargo_nombre, rol_codigo)
        cuentas.append(ficha(usuario, fun_obj, rol_codigo, nuevo=False))

    cubiertos = {(c["rol"], c["delegacion"]) for c in cuentas}

    def agregar_usuario(rol_codigo, deleg_nombre, codigo_usuario=None):
        nonlocal max_usr_pk
        fun_obj = agregar_funcionario(deleg_nombre, CARGO_POR_ROL[rol_codigo], rol_codigo)
        max_usr_pk += 1
        codigo = codigo_usuario or f"USR-{max_usr_pk:03d}"
        usuario = {
            "model": "cuentas.usuario",
            "pk": max_usr_pk,
            "fields": {
                "codigo": codigo,
                "user": None,
                "username": fun_obj["fields"]["rut"],
                "nombre": fun_obj["fields"]["nombre"],
                "correo": correo_funcionario(fun_obj["fields"]["codigo"]),
                "rol": rol_pk[rol_codigo],
                "cargo": fun_obj["fields"]["cargo"],
                "delegacion": fun_obj["fields"]["delegacion"],
                "funcionario": fun_obj["pk"],
                "estado": "activo",
                "creado": "2026-10-04T12:00:00Z",
            },
        }
        fixture.append(usuario)
        cuentas.append(ficha(usuario, fun_obj, rol_codigo, nuevo=True))

    for deleg_nombre in DELEGACIONES_OFICIALES:
        if deleg_nombre not in delegacion_pk:
            continue
        for rol_codigo in ROLES_ORDEN:
            if (rol_codigo, deleg_nombre) not in cubiertos:
                agregar_usuario(rol_codigo, deleg_nombre)
                cubiertos.add((rol_codigo, deleg_nombre))

    if not any(c["codigo_usuario"] == CODIGO_ADMIN_GLOBAL for c in cuentas):
        agregar_usuario("administrador", "Delegación Centro", codigo_usuario=CODIGO_ADMIN_GLOBAL)

    # Auth: una fila por cuenta. La clave queda inutilizable hasta importar_json.
    password_hash = "!"
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    auth_existentes = {obj["pk"] for obj in _por_modelo(fixture, "auth.user")}
    for usuario in _por_modelo(fixture, "cuentas.usuario"):
        pk = usuario["pk"]
        campos = usuario["fields"]
        first, _, last = campos["nombre"].partition(" ")
        auth = {
            "model": "auth.user",
            "pk": pk,
            "fields": {
                "password": password_hash,
                "last_login": None,
                "is_superuser": False,
                "username": campos["username"],
                "first_name": first.replace("(ficticio)", "").strip()[:150],
                "last_name": last.replace("(ficticio)", "").strip()[:150],
                "email": campos["correo"],
                "is_staff": False,
                "is_active": campos.get("estado", "activo") == "activo",
                "date_joined": ahora,
                "groups": [],
                "user_permissions": [],
            },
        }
        if pk in auth_existentes:
            for obj in fixture:
                if obj["model"] == "auth.user" and obj["pk"] == pk:
                    obj["fields"] = auth["fields"]
        else:
            fixture.append(auth)
        campos["user"] = pk

    # Vecinos.
    vecinos = sorted(_por_modelo(fixture, "requerimientos.vecino"), key=lambda obj: obj["pk"])
    indice_v = 0
    for obj in vecinos:
        indice_v += 1
        campos = obj["fields"]
        viejo = campos.get("nombre") or ""
        if es_organizacion(viejo):
            campos["nombre"] = f"Organización Ficticia {indice_v:02d}"
        else:
            nombres, paterno, materno = identidad(indice_v + 40)
            campos["nombre"] = nombre_visible(nombres, paterno, materno, True)
        campos["rut"] = rut_vecino(indice_v)
        campos["telefono"] = telefono_ficticio(indice_v)
        campos["correo"] = correo_vecino(indice_v)
        campos["direccion"] = direccion_ficticia(indice_v)
        campos["es_simulacion"] = True
        if viejo and viejo != campos["nombre"]:
            mapa[viejo] = campos["nombre"]

    max_vec_pk = max((obj["pk"] for obj in vecinos), default=0)
    for deleg_pk, deleg_nombre in delegaciones.items():
        cantidad = sum(
            1 for obj in _por_modelo(fixture, "requerimientos.vecino") if obj["fields"].get("delegacion") == deleg_pk
        )
        while cantidad < 10:
            indice_v += 1
            max_vec_pk += 1
            nombres, paterno, materno = identidad(indice_v + 40)
            fixture.append({
                "model": "requerimientos.vecino",
                "pk": max_vec_pk,
                "fields": {
                    "nombre": nombre_visible(nombres, paterno, materno, True),
                    "rut": rut_vecino(indice_v),
                    "direccion": direccion_ficticia(indice_v),
                    "telefono": telefono_ficticio(indice_v),
                    "correo": correo_vecino(indice_v),
                    "territorio": "Simulación",
                    "delegacion": deleg_pk,
                    "tipo_gestion": None,
                    "es_simulacion": True,
                    "estado": "activo",
                },
            })
            cantidad += 1

    fun_nombre_por_pk = {pk: obj["fields"]["nombre"] for pk, obj in fun_por_pk.items()}
    for obj in fixture:
        campos = obj["fields"]
        if obj["model"] == "requerimientos.areasoporte":
            encargado = campos.get("encargado")
            if encargado in fun_nombre_por_pk:
                campos["encargado_nombre"] = fun_nombre_por_pk[encargado]
            else:
                campos["encargado_nombre"] = _reemplazar(campos.get("encargado_nombre") or "", mapa)
        if obj["model"] == "requerimientos.requerimiento" and campos.get("funcionario") in fun_nombre_por_pk:
            campos["asignado_a"] = fun_nombre_por_pk[campos["funcionario"]]
        if obj["model"] == "control_gestion.actividad" and campos.get("contacto"):
            campos["contacto"] = f"Contacto ficticio {obj['pk']}"
        for clave, valor in list(campos.items()):
            if isinstance(valor, str):
                campos[clave] = _reemplazar(valor, mapa)

    return {
        "cuentas": cuentas,
        "mapa": mapa,
        "funcionarios": _por_modelo(fixture, "cuentas.funcionario"),
        "vecinos": len(_por_modelo(fixture, "requerimientos.vecino")),
        "vecinos_objs": _por_modelo(fixture, "requerimientos.vecino"),
        "delegaciones": delegaciones,
        "password_hash": password_hash,
        "fixture": fixture,
    }


def _reemplazar(texto, mapa):
    if not texto:
        return texto
    for viejo, nuevo in sorted(mapa.items(), key=lambda item: -len(item[0])):
        if viejo and len(viejo) >= 5 and viejo in texto:
            texto = texto.replace(viejo, nuevo)
    return texto


def _reescribir_json(data_dir, resultado):
    fun_por_codigo = {obj["fields"]["codigo"]: obj["fields"] for obj in resultado["funcionarios"]}
    deleg_nombre = resultado["delegaciones"]
    cargos_inv = {}
    for obj in resultado["fixture"]:
        if obj["model"] == "cuentas.cargo":
            cargos_inv[obj["pk"]] = obj["fields"]["nombre"]

    ruta_fun = data_dir / "funcionarios.json"
    if ruta_fun.exists():
        crudos = _cargar(ruta_fun)
        por_codigo = {item["id_funcionario"]: item for item in crudos}
        nuevos = []
        for obj in sorted(resultado["funcionarios"], key=lambda item: item["fields"]["codigo"]):
            campos = obj["fields"]
            base = por_codigo.get(campos["codigo"], {"items": []})
            base.update({
                "id_funcionario": campos["codigo"],
                "nombre": campos["nombre"],
                "nombres": campos["nombres"],
                "apellido_paterno": campos["apellido_paterno"],
                "apellido_materno": campos["apellido_materno"] or "",
                "rut": campos["rut"],
                "es_simulacion": True,
                "cargo": cargos_inv.get(campos["cargo"], base.get("cargo", "")),
                "delegacion": deleg_nombre[campos["delegacion"]],
                "fecha_ultimo_ingreso": campos.get("fecha_ultimo_ingreso") or base.get("fecha_ultimo_ingreso"),
            })
            base.setdefault("items", [])
            nuevos.append(base)
        _guardar(ruta_fun, nuevos)

    usuarios = []
    for cuenta in resultado["cuentas"]:
        usuarios.append({
            "id_usuario": cuenta["codigo_usuario"],
            "username": cuenta["rut"],
            "nombre": cuenta["nombre"],
            "email": cuenta["correo"],
            "rol": cuenta["rol"],
            "cargo": cargos_inv.get(cuenta["cargo_id"], CARGO_POR_ROL[cuenta["rol"]]),
            "delegacion": cuenta["delegacion"],
            "id_funcionario": cuenta["codigo_funcionario"],
            "rut": cuenta["rut"],
            "activo": True,
        })
    _guardar(data_dir / "usuarios.json", usuarios)

    mapa = resultado["mapa"]
    for nombre in ("requerimientos.json", "tubo_trabajo.json", "actividades.json", "agenda.json", "areas_soporte.json"):
        ruta = data_dir / nombre
        if not ruta.exists():
            continue
        datos = _cargar(ruta)
        if nombre == "actividades.json":
            for i, item in enumerate(datos, start=1):
                if item.get("contacto"):
                    item["contacto"] = f"Contacto ficticio {i}"
                codigo = item.get("id_funcionario")
                if codigo in fun_por_codigo:
                    item["funcionario_nombre"] = fun_por_codigo[codigo]["nombre"]
        if nombre == "areas_soporte.json":
            for item in datos:
                item["encargado"] = _reemplazar(item.get("encargado") or "", mapa)
        if nombre == "agenda.json":
            for item in datos:
                item["responsable"] = _reemplazar(item.get("responsable") or "", mapa)
        if nombre == "tubo_trabajo.json":
            for item in datos:
                codigo = item.get("id_funcionario")
                if codigo in fun_por_codigo:
                    item["funcionario"] = fun_por_codigo[codigo]["nombre"]
                item["vecino"] = _reemplazar(item.get("vecino") or "", mapa)
                item["descripcion"] = _reemplazar(item.get("descripcion") or "", mapa)
        if nombre == "requerimientos.json":
            for item in datos:
                item["vecino_nombre"] = _reemplazar(item.get("vecino_nombre") or "", mapa)
                item["funcionario_asignado"] = _reemplazar(item.get("funcionario_asignado") or "", mapa)
                item["email"] = "correo@siged.test" if item.get("email") else ""
                if item.get("telefono_whatsapp"):
                    item["telefono_whatsapp"] = "+56900000000"
                item["descripcion"] = _reemplazar(item.get("descripcion") or "", mapa)
        _guardar(ruta, datos)


def _sql_d003(resultado):
    lineas = [
        "-- Versión     : D003",
        "-- Descripción : Reemplaza identidades de demostración por datos ficticios",
        "-- Autor       : Bakend pipi       Revisor: ramoncito",
        "-- Rollback    : restaurar el respaldo mysqldump previo (no hay script inverso)",
        "-- Requiere    : V017 aplicado y todavía sin V018 (columnas anulables)",
        "-- Nota        : no contiene claves en texto plano. El hash es PBKDF2 de la",
        "--               convención de demostración documentada en el README.",
        "--               Los id de vecino son los del fixture 02_datos_sistema.",
        "--               Si la base no nació de ese fixture, use python manage.py migrate",
        "--               (la migración 0003 recorre las filas y no depende del id).",
        "START TRANSACTION;",
        "",
    ]
    originales = {c["codigo_funcionario"] for c in resultado["cuentas"] if not c["nuevo_funcionario"]}
    for obj in sorted(resultado["funcionarios"], key=lambda item: item["fields"]["codigo"]):
        campos = obj["fields"]
        if campos["codigo"] in originales or not campos["codigo"].startswith("FUN-"):
            # Los FUN-00x históricos se actualizan. Los creados para cubrir roles se insertan.
            pass
        if not any(c["codigo_funcionario"] == campos["codigo"] and c["nuevo_funcionario"] for c in resultado["cuentas"]) and campos["codigo"] in {
            c["codigo_funcionario"] for c in resultado["cuentas"] if not c["nuevo_funcionario"]
        } or campos["codigo"] in {obj2["fields"]["codigo"] for obj2 in resultado["funcionarios"] if obj2["pk"] <= 10}:
            lineas.append(
                "UPDATE cuentas_funcionario SET "
                f"rut={_sql(campos['rut'])}, nombres={_sql(campos['nombres'])}, "
                f"apellido_paterno={_sql(campos['apellido_paterno'])}, "
                f"apellido_materno={_sql(campos['apellido_materno'])}, "
                f"nombre={_sql(campos['nombre'])}, es_simulacion=1 "
                f"WHERE codigo={_sql(campos['codigo'])};"
            )
        else:
            deleg = resultado["delegaciones"][campos["delegacion"]]
            lineas.append(
                "INSERT INTO cuentas_funcionario "
                "(codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) "
                "SELECT "
                f"{_sql(campos['codigo'])}, {_sql(campos['rut'])}, {_sql(campos['nombres'])}, "
                f"{_sql(campos['apellido_paterno'])}, {_sql(campos['apellido_materno'])}, {_sql(campos['nombre'])}, 1, "
                f"(SELECT id FROM cuentas_cargo WHERE id={int(campos['cargo'])} OR nombre={_sql(CARGO_POR_ROL['funcionario'])} ORDER BY id={int(campos['cargo'])} DESC LIMIT 1), "
                f"(SELECT id FROM cuentas_delegacion WHERE nombre={_sql(deleg)} LIMIT 1), 'activo' "
                f"FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo={_sql(campos['codigo'])});"
            )

    lineas.append("")
    hash_clave = resultado["password_hash"]
    for cuenta in resultado["cuentas"]:
        if not cuenta["nuevo_usuario"]:
            lineas.append(
                "UPDATE cuentas_usuario u "
                "JOIN cuentas_funcionario f ON f.codigo=" + _sql(cuenta["codigo_funcionario"]) + " "
                "JOIN cuentas_rol r ON r.codigo=" + _sql(cuenta["rol"]) + " "
                "SET u.username=f.rut, u.nombre=f.nombre, u.correo=" + _sql(cuenta["correo"]) + ", "
                "u.funcionario_id=f.id, u.delegacion_id=f.delegacion_id, u.rol_id=r.id "
                "WHERE u.codigo=" + _sql(cuenta["codigo_usuario"]) + ";"
            )
            lineas.append(
                "UPDATE auth_user au "
                "JOIN cuentas_usuario u ON u.user_id=au.id "
                "SET au.username=u.username, au.email=u.correo, au.password=" + _sql(hash_clave) + ", "
                "au.first_name=" + _sql(cuenta["nombres"]) + ", au.last_name=" + _sql(cuenta["apellido_paterno"]) + " "
                "WHERE u.codigo=" + _sql(cuenta["codigo_usuario"]) + ";"
            )
        else:
            deleg = cuenta["delegacion"]
            lineas.append(
                "INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) "
                "SELECT " + _sql(hash_clave) + ", 0, " + _sql(cuenta["rut"]) + ", "
                + _sql(cuenta["nombres"]) + ", " + _sql(cuenta["apellido_paterno"]) + ", "
                + _sql(cuenta["correo"]) + ", 0, 1, UTC_TIMESTAMP() FROM DUAL "
                "WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username=" + _sql(cuenta["rut"]) + ");"
            )
            lineas.append(
                "INSERT INTO cuentas_usuario "
                "(codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) "
                "SELECT " + _sql(cuenta["codigo_usuario"]) + ", au.id, f.rut, f.nombre, " + _sql(cuenta["correo"]) + ", "
                "r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() "
                "FROM auth_user au "
                "JOIN cuentas_funcionario f ON f.codigo=" + _sql(cuenta["codigo_funcionario"]) + " "
                "JOIN cuentas_rol r ON r.codigo=" + _sql(cuenta["rol"]) + " "
                "WHERE au.username=" + _sql(cuenta["rut"]) + " "
                "AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo=" + _sql(cuenta["codigo_usuario"]) + ");"
            )

    lineas.append("")
    for obj in sorted(resultado["vecinos_objs"], key=lambda item: item["pk"]):
        campos = obj["fields"]
        if obj["pk"] <= 21:
            lineas.append(
                "UPDATE requerimientos_vecino SET "
                f"nombre={_sql(campos['nombre'])}, rut={_sql(campos['rut'])}, "
                f"telefono={_sql(campos['telefono'])}, correo={_sql(campos['correo'])}, "
                f"direccion={_sql(campos['direccion'])}, es_simulacion=1 "
                f"WHERE id={int(obj['pk'])};"
            )
        else:
            deleg = resultado["delegaciones"][campos["delegacion"]]
            lineas.append(
                "INSERT INTO requerimientos_vecino "
                "(nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) "
                "SELECT "
                f"{_sql(campos['nombre'])}, {_sql(campos['rut'])}, {_sql(campos['direccion'])}, "
                f"{_sql(campos['telefono'])}, {_sql(campos['correo'])}, 'Simulación', "
                f"(SELECT id FROM cuentas_delegacion WHERE nombre={_sql(deleg)} LIMIT 1), 'activo', 1 "
                "FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut=" + _sql(campos["rut"]) + ");"
            )

    lineas.extend([
        "",
        "UPDATE control_gestion_actividad",
        "SET contacto = CONCAT('Contacto ficticio ', id)",
        "WHERE contacto IS NOT NULL AND contacto <> '';",
        "",
        "UPDATE requerimientos_requerimiento r",
        "JOIN cuentas_funcionario f ON f.id = r.funcionario_id",
        "SET r.asignado_a = f.nombre",
        "WHERE r.funcionario_id IS NOT NULL;",
        "",
        "UPDATE requerimientos_areasoporte a",
        "JOIN cuentas_funcionario f ON f.id = a.encargado_id",
        "SET a.encargado_nombre = f.nombre",
        "WHERE a.encargado_id IS NOT NULL;",
        "",
        "COMMIT;",
        "",
    ])
    return "\n".join(lineas) + "\n"


def _tabla_markdown(cuentas):
    lineas = [
        "| RUT | Rol | Delegación | Código |",
        "| --- | --- | --- | --- |",
    ]
    for cuenta in sorted(cuentas, key=lambda item: (item["delegacion"], item["rol"], item["rut"])):
        rol = cuenta["rol"] + (" (global)" if cuenta.get("global") else "")
        lineas.append(f"| `{cuenta['rut']}` | {rol} | {cuenta['delegacion']} | {cuenta['codigo_usuario']} |")
    return "\n".join(lineas) + "\n"
