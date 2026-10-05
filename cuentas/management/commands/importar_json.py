"""Migra los datos de data/*.json (mockup Sumativa 1) a la base de datos MySQL.

Uso:
    python manage.py importar_json            # importa todo y crea usuarios Django (claves hasheadas)
    python manage.py importar_json --sin-auth # no crea/enlaza usuarios de django.contrib.auth

Es idempotente: se puede ejecutar varias veces (usa update_or_create por código).
"""

import json
import re
from datetime import date, time
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from control_gestion.models import Actividad, Compromiso, EventoAgenda, ItemFuncionario, Medicion, Meta, Notificacion
from cuentas.auth import ROLES_ETIQUETA
from cuentas.models import Cargo, Delegacion, EstadoRegistro, Funcionario, ParametroSistema, Rol, Usuario
from cuentas.vocabulario import normalizar_canal, normalizar_delegacion, normalizar_tipo
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino

NOMBRE_ROL = {
    "administrador": "Administrador",
    "jefatura": "Jefatura",
    "funcionario": "Funcionario",
    "ventanilla": "Ventanilla",
}


def _fecha(valor):
    return date.fromisoformat(valor) if valor else None


def _hora(valor):
    return time.fromisoformat(valor) if valor else time(0, 0)


class Command(BaseCommand):
    help = "Importa los archivos data/*.json del mockup a la base de datos (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument("--sin-auth", action="store_true",
                            help="No crear ni enlazar usuarios de django.contrib.auth.")
        parser.add_argument("--data-dir", default=None, help="Carpeta con los JSON (por defecto BASE_DIR/data).")

    # ------------------------------------------------------------------ utilidades
    def _leer(self, nombre, fallback):
        ruta = self.data_dir / nombre
        if not ruta.exists():
            self.stdout.write(self.style.WARNING(f"  (omitido) no existe {ruta}"))
            return fallback
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)

    def _delegacion(self, nombre):
        nombre = normalizar_delegacion((nombre or "").strip()) or "Delegación Centro"
        obj, _ = Delegacion.objects.get_or_create(nombre=nombre, defaults={"comuna": "La Serena"})
        return obj

    def _cargo(self, nombre):
        obj, _ = Cargo.objects.get_or_create(nombre=(nombre or "Sin cargo").strip())
        return obj

    def _meta(self, nombre):
        obj, _ = Meta.objects.get_or_create(nombre=nombre.strip(),
                                            defaults={"descripcion": "Ítem de la Matriz SGR"})
        return obj

    def _funcionario_por_nombre(self, texto):
        """Busca un funcionario por nombre completo o por 'Nombre Apellido (Área)'."""
        if not texto:
            return None
        limpio = re.sub(r"\(.*?\)", "", texto).strip()
        if not limpio:
            return None
        return (Funcionario.objects.filter(nombre__iexact=limpio).first()
                or Funcionario.objects.filter(nombre__istartswith=limpio).first())

    def _vecino(self, nombre, telefono="", correo="", delegacion=None):
        marca = "(ficticio)" in (nombre or "") or (correo or "").endswith("@siged.test")
        nombre = " ".join((nombre or "Vecino sin nombre").replace("(ficticio)", "").split())
        vecino = Vecino.objects.filter(nombre=nombre).first()
        if vecino is None:
            vecino = Vecino.objects.create(
                nombre=nombre,
                telefono=telefono or "",
                correo=correo or "",
                delegacion=delegacion,
                es_simulacion=marca,
            )
        else:
            cambios = False
            if marca and not vecino.es_simulacion:
                vecino.es_simulacion = True
                cambios = True
            for campo, valor in (("telefono", telefono), ("correo", correo), ("delegacion", delegacion)):
                if valor and not getattr(vecino, campo):
                    setattr(vecino, campo, valor)
                    cambios = True
            if cambios:
                vecino.save()
        return vecino

    # ------------------------------------------------------------------ importadores
    def importar_parametros(self):
        datos = self._leer("parametros.json", {})
        if not datos:
            return
        campos = {c: datos[c] for c in ("nombre_sistema", "comuna", "region", "sla_verde_max_dias",
                                        "sla_amarillo_max_dias", "meta_tubo_porcentaje", "encuesta_habilitada",
                                        "max_atenciones_mismo_usuario") if c in datos}
        ParametroSistema.objects.update_or_create(pk=1, defaults=campos)
        for canal in datos.get("canales_ingreso", []):
            CanalIngreso.objects.get_or_create(nombre=normalizar_canal(canal))

    def importar_cargos(self):
        for c in self._leer("cargos.json", []):
            obj = Cargo.objects.filter(codigo=c["id_cargo"]).first() or \
                Cargo.objects.filter(nombre=c["nombre"]).first() or Cargo()
            obj.codigo = c["id_cargo"]
            obj.nombre = c["nombre"]
            obj.descripcion = c.get("descripcion", "")
            obj.modulo_principal = c.get("modulo_principal", "")
            obj.save()

    def _rut_libre(self, excepto_pk=None):
        from cuentas.simulacion import fichas_funcionario, rut_libre_trabajador

        usados = {ficha["rut"] for ficha in fichas_funcionario().values()}
        consulta = Funcionario.objects.exclude(rut__isnull=True).exclude(rut="")
        if excepto_pk:
            consulta = consulta.exclude(pk=excepto_pk)
        usados.update(consulta.values_list("rut", flat=True))
        _indice, rut = rut_libre_trabajador(usados, 33)
        return rut

    def _liberar_rut(self, rut, codigo_dueno):
        if not rut:
            return
        for otro in list(Funcionario.objects.filter(rut=rut).exclude(codigo=codigo_dueno)):
            otro.rut = self._rut_libre(otro.pk)
            otro.es_simulacion = True
            otro.save(update_fields=["rut", "es_simulacion"])

    def _liberar_cuenta(self, username, correo, propio_pk, propio_user_id):
        User = get_user_model()
        ajenos = Usuario.objects.filter(username=username)
        if propio_pk:
            ajenos = ajenos.exclude(pk=propio_pk)
        for otro in list(ajenos):
            reserva = f"reserva-{otro.pk}"
            otro.username = reserva
            if otro.correo == correo:
                otro.correo = f"{reserva}@siged.test"
            otro.save(update_fields=["username", "correo"])
        ajenos = Usuario.objects.filter(correo=correo)
        if propio_pk:
            ajenos = ajenos.exclude(pk=propio_pk)
        for otro in list(ajenos):
            otro.correo = f"reserva-{otro.pk}@siged.test"
            otro.save(update_fields=["correo"])
        auth = User.objects.filter(username=username)
        if propio_user_id:
            auth = auth.exclude(pk=propio_user_id)
        for user in list(auth):
            user.username = f"reserva-auth-{user.pk}"
            user.save(update_fields=["username"])

    def importar_funcionarios(self):
        from core.validaciones import cuerpo_en_rango_ficticio
        from cuentas.simulacion import nombre_almacenado

        for f in self._leer("funcionarios.json", []):
            nombres = (f.get("nombres") or "").strip()
            paterno = (f.get("apellido_paterno") or "").strip()
            materno = (f.get("apellido_materno") or "").strip() or None
            if not nombres or not paterno:
                partes = (f.get("nombre") or "").replace("(ficticio)", "").split()
                nombres = nombres or (partes[0] if partes else "Sin")
                paterno = paterno or (partes[1] if len(partes) > 1 else "Registro")
                if materno is None and len(partes) > 2:
                    materno = " ".join(partes[2:])
            ficticio = (
                bool(f.get("es_simulacion"))
                or "(ficticio)" in (f.get("nombre") or "")
                or cuerpo_en_rango_ficticio(f.get("rut") or "")
            )
            self._liberar_rut(f.get("rut"), f["id_funcionario"])
            funcionario, _ = Funcionario.objects.update_or_create(
                codigo=f["id_funcionario"],
                defaults={
                    "rut": f.get("rut"),
                    "nombres": nombres[:60],
                    "apellido_paterno": paterno[:60],
                    "apellido_materno": (materno[:60] if materno else None),
                    "nombre": nombre_almacenado(nombres, paterno, materno or ""),
                    "es_simulacion": ficticio,
                    "cargo": self._cargo(f.get("cargo")),
                    "delegacion": self._delegacion(f.get("delegacion")),
                    "fecha_ultimo_ingreso": _fecha(f.get("fecha_ultimo_ingreso")),
                },
            )
            for item in f.get("items", []):
                ItemFuncionario.objects.update_or_create(
                    funcionario=funcionario,
                    meta=self._meta(item["item"]),
                    defaults={
                        "ponderador": item.get("ponderador", 0),
                        "meta_trimestre": item.get("meta_trimestre", 0),
                        "avance_actual": item.get("avance_actual", 0),
                    },
                )

    def importar_usuarios(self, crear_auth):
        from cuentas.simulacion import (
            clave_compartida_de_prueba,
            escribir_claves_locales,
            nueva_clave_simulacion,
        )

        User = get_user_model()
        compartida = clave_compartida_de_prueba()
        credenciales = []
        for u in self._leer("usuarios.json", []):
            codigo_rol = u.get("rol", "funcionario")
            rol, _ = Rol.objects.get_or_create(
                codigo=codigo_rol,
                defaults={"nombre": NOMBRE_ROL.get(codigo_rol, codigo_rol.title()),
                          "descripcion": ROLES_ETIQUETA.get(codigo_rol, "")},
            )
            funcionario = Funcionario.objects.filter(codigo=u.get("id_funcionario") or None).first()
            username = (u.get("username") or (funcionario.rut if funcionario else "")).strip()
            if funcionario is not None and funcionario.rut:
                username = funcionario.rut
            correo = u.get("email") or (f"{funcionario.codigo.lower()}@siged.test" if funcionario else f"{username}@siged.test")
            nombre = u.get("nombre") or (funcionario.nombre if funcionario else username)
            codigo = u.get("id_usuario")
            usuario = Usuario.objects.filter(codigo=codigo).first() if codigo else None
            if usuario is None and funcionario is not None:
                usuario = Usuario.objects.filter(funcionario=funcionario).first()
            self._liberar_cuenta(
                username,
                correo,
                usuario.pk if usuario is not None else None,
                usuario.user_id if usuario is not None else None,
            )
            if usuario is None:
                usuario = Usuario.objects.filter(username=username).first()
            campos = {
                "username": username,
                "nombre": nombre,
                "correo": correo,
                "rol": rol,
                "cargo": self._cargo(u["cargo"]) if u.get("cargo") else (funcionario.cargo if funcionario else None),
                "delegacion": self._delegacion(u.get("delegacion")) if u.get("delegacion") else (
                    funcionario.delegacion if funcionario else None
                ),
                "funcionario": funcionario,
                "estado": EstadoRegistro.ACTIVO if u.get("activo", True) else EstadoRegistro.INACTIVO,
            }
            if usuario is None:
                usuario = Usuario.objects.create(codigo=codigo, **campos)
            else:
                if codigo:
                    usuario.codigo = codigo
                for campo, valor in campos.items():
                    setattr(usuario, campo, valor)
                usuario.save()
            if not crear_auth:
                continue
            # El JSON no trae clave. Cada cuenta recibe una distinta, salvo que
            # SIGED_DEMO_PASSWORD esté definida para una prueba local.
            clave = nueva_clave_simulacion(compartida)
            user = usuario.user or User.objects.filter(username=username).first()
            partes = usuario.nombre.split(" ", 1)
            if user is None:
                user = User(username=username, email=usuario.correo, first_name=partes[0][:150],
                            last_name=(partes[1].strip() if len(partes) > 1 else "")[:150],
                            is_active=usuario.activo)
                self.auth_creados += 1
            user.username = username
            user.email = usuario.correo
            user.first_name = partes[0][:150]
            user.last_name = (partes[1].strip() if len(partes) > 1 else "")[:150]
            user.is_active = usuario.activo
            user.set_password(clave)
            user.save()
            if usuario.user_id != user.pk:
                usuario.user = user
                usuario.save(update_fields=["user"])
            rut = funcionario.rut if funcionario is not None and funcionario.rut else username
            credenciales.append((rut, usuario.codigo or "", clave))
        if crear_auth and credenciales:
            nombre_archivo = escribir_claves_locales(credenciales)
            self.stdout.write(
                f"Claves de simulación escritas en {nombre_archivo}. No se imprimen."
            )

    def importar_areas(self):
        for a in self._leer("areas_soporte.json", []):
            AreaSoporte.objects.update_or_create(
                codigo=a["id_area"],
                defaults={
                    "nombre": a["nombre_area"],
                    "encargado": self._funcionario_por_nombre(a.get("encargado")),
                    "encargado_nombre": a.get("encargado", ""),
                    "tiempo_promedio_dias": a.get("tiempo_promedio_dias", 0),
                    "total_casos_mes": a.get("total_casos_mes", 0),
                    "porcentaje_cumplimiento": a.get("porcentaje_cumplimiento", 0),
                    "satisfaccion_promedio": a.get("satisfaccion_promedio", 0),
                    "icono": a.get("icono", ""),
                    "descripcion": a.get("descripcion", ""),
                },
            )

    def importar_requerimientos(self):
        vistos = set()
        for r in self._leer("requerimientos.json", []):
            codigo = r["id_ticket"]
            if codigo in vistos:
                self.duplicados.append(codigo)
            vistos.add(codigo)
            delegacion = self._delegacion(r.get("delegacion"))
            tipo_nombre = normalizar_tipo(r.get("tipo_entrada") or "Consulta").capitalize()
            tipo, _ = TipoGestion.objects.get_or_create(nombre=tipo_nombre)
            canal, _ = CanalIngreso.objects.get_or_create(nombre=normalizar_canal(r.get("canal_ingreso") or "ventanilla"))
            area = AreaSoporte.objects.filter(nombre=r.get("area_tematica")).first()
            if area is None:
                siguiente = AreaSoporte.objects.count() + 1
                area = AreaSoporte.objects.create(codigo=f"AREA-{siguiente:03d}", nombre=r.get("area_tematica") or "Sin área")
            asignado = r.get("funcionario_asignado", "")
            Requerimiento.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "vecino": self._vecino(r.get("vecino_nombre"), r.get("telefono_whatsapp"), r.get("email"),
                                           delegacion),
                    "delegacion": delegacion,
                    "canal_ingreso": canal,
                    "tipo_gestion": tipo,
                    "area": area,
                    "descripcion": r.get("descripcion", ""),
                    "fecha_ingreso": _fecha(r.get("fecha_ingreso")) or date.today(),
                    "funcionario": self._funcionario_por_nombre(asignado),
                    "asignado_a": asignado,
                    "estado": r.get("estado_proceso") or Requerimiento.Estado.PENDIENTE,
                    "evaluacion_satisfaccion": r.get("evaluacion_satisfaccion"),
                    "comentario_satisfaccion": r.get("comentario_satisfaccion") or "",
                },
            )

    def importar_compromisos(self):
        for c in self._leer("tubo_trabajo.json", []):
            delegacion = self._delegacion(c.get("delegacion"))
            funcionario = Funcionario.objects.filter(codigo=c.get("id_funcionario")).first() or \
                self._funcionario_por_nombre(c.get("funcionario"))
            if funcionario is None:
                self.stdout.write(self.style.WARNING(f"  compromiso {c.get('id_compromiso')} sin funcionario, omitido"))
                continue
            Compromiso.objects.update_or_create(
                codigo=c["id_compromiso"],
                defaults={
                    "descripcion": c.get("descripcion", ""),
                    "vecino": self._vecino(c.get("vecino"), delegacion=delegacion),
                    "funcionario": funcionario,
                    "delegacion": delegacion,
                    "fecha_ingreso": _fecha(c.get("fecha_ingreso")) or date.today(),
                    "fecha_compromiso": _fecha(c.get("fecha_compromiso")) or date.today(),
                    "estado": c.get("estado") or Compromiso.Estado.INGRESADO,
                },
            )

    def importar_actividades(self):
        for a in self._leer("actividades.json", []):
            funcionario = Funcionario.objects.filter(codigo=a.get("id_funcionario")).first()
            if funcionario is None:
                self.stdout.write(self.style.WARNING(f"  actividad {a.get('id_actividad')} sin funcionario, omitida"))
                continue
            Actividad.objects.update_or_create(
                codigo=a["id_actividad"],
                defaults={
                    "funcionario": funcionario,
                    "delegacion": self._delegacion(a.get("delegacion")),
                    "meta": self._meta(a.get("item") or "Sin ítem"),
                    "fecha_actividad": _fecha(a.get("fecha_actividad")) or date.today(),
                    "contacto": a.get("contacto", ""),
                    "servicio": a.get("servicio", ""),
                    "codigo_verificador": a.get("codigo_verificador", ""),
                    "imagen_verificadora": a.get("imagen_verificadora", ""),
                    "punto_validado": bool(a.get("punto_validado")),
                },
            )

    def importar_agenda(self):
        for e in self._leer("agenda.json", []):
            EventoAgenda.objects.update_or_create(
                codigo=e["id_evento"],
                defaults={
                    "titulo": e.get("titulo", ""),
                    "tipo": e.get("tipo", ""),
                    "fecha": _fecha(e.get("fecha")),
                    "hora": _hora(e.get("hora")),
                    "delegacion": self._delegacion(e.get("delegacion")),
                    "responsable": self._funcionario_por_nombre(e.get("responsable")),
                    "lugar": e.get("lugar", ""),
                },
            )

    def importar_medicion(self):
        m = self._leer("medicion.json", {})
        if not m:
            return
        Medicion.objects.update_or_create(
            periodo=m["periodo"],
            defaults={
                "delegacion_piloto": self._delegacion(m.get("delegacion_piloto")),
                "fecha_inicio": _fecha(m.get("fecha_inicio")),
                "fecha_termino": _fecha(m.get("fecha_termino")),
                "dias_totales": m.get("dias_totales", 90),
                "meta_cumplimiento_tubo": m.get("meta_cumplimiento_tubo", 80),
                "descripcion": m.get("descripcion", ""),
            },
        )

    def importar_notificaciones(self):
        for n in self._leer("notificaciones.json", []):
            Notificacion.objects.update_or_create(
                codigo=n["id"],
                defaults={
                    "titulo": n.get("titulo", ""),
                    "mensaje": n.get("mensaje", ""),
                    "tipo": n.get("tipo", "info"),
                    "fecha": _fecha(n.get("fecha")) or date.today(),
                    "enlace": n.get("enlace", ""),
                },
            )

    # ------------------------------------------------------------------ main
    def handle(self, *args, **opciones):
        self.data_dir = Path(opciones["data_dir"] or Path(settings.BASE_DIR) / "data")
        if not self.data_dir.is_dir():
            raise CommandError(f"No existe la carpeta {self.data_dir}")
        self.auth_creados = 0
        self.duplicados = []

        with transaction.atomic():
            for paso in ("parametros", "cargos", "funcionarios"):
                getattr(self, f"importar_{paso}")()
            self.importar_usuarios(crear_auth=not opciones["sin_auth"])
            for paso in ("areas", "requerimientos", "compromisos", "actividades", "agenda", "medicion",
                         "notificaciones"):
                getattr(self, f"importar_{paso}")()
            from cuentas.simulacion_bd import normalizar_filas_sueltas

            normalizar_filas_sueltas()

        modelos = [Rol, Delegacion, Cargo, Funcionario, Usuario, ParametroSistema, Meta, ItemFuncionario,
                   AreaSoporte, CanalIngreso, TipoGestion, Vecino, Requerimiento, Compromiso, Actividad,
                   EventoAgenda, Medicion, Notificacion]
        for modelo in modelos:
            self.stdout.write(f"  {modelo._meta.verbose_name_plural}: {modelo.objects.count()}")
        if self.duplicados:
            self.stdout.write(self.style.WARNING(
                f"  Tickets repetidos en requerimientos.json (se conservó el último): {', '.join(self.duplicados)}"))
        self.stdout.write(self.style.SUCCESS(
            f"Importación completa. Usuarios Django creados en esta ejecución: {self.auth_creados}"))
