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
        nombre = (nombre or "Vecino sin nombre").strip()
        vecino = Vecino.objects.filter(nombre=nombre).first()
        if vecino is None:
            vecino = Vecino.objects.create(nombre=nombre, telefono=telefono or "", correo=correo or "",
                                           delegacion=delegacion)
        else:
            cambios = False
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

    def importar_funcionarios(self):
        for f in self._leer("funcionarios.json", []):
            funcionario, _ = Funcionario.objects.update_or_create(
                codigo=f["id_funcionario"],
                defaults={
                    "nombre": f["nombre"],
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
        User = get_user_model()
        for u in self._leer("usuarios.json", []):
            codigo_rol = u.get("rol", "funcionario")
            rol, _ = Rol.objects.get_or_create(
                codigo=codigo_rol,
                defaults={"nombre": NOMBRE_ROL.get(codigo_rol, codigo_rol.title()),
                          "descripcion": ROLES_ETIQUETA.get(codigo_rol, "")},
            )
            funcionario = Funcionario.objects.filter(codigo=u.get("id_funcionario") or None).first()
            usuario, _ = Usuario.objects.update_or_create(
                username=u["username"],
                defaults={
                    "codigo": u.get("id_usuario"),
                    "nombre": u.get("nombre", u["username"]),
                    "correo": u.get("email") or f"{u['username']}@laserena.cl",
                    "rol": rol,
                    "cargo": self._cargo(u["cargo"]) if u.get("cargo") else None,
                    "delegacion": self._delegacion(u.get("delegacion")),
                    "funcionario": funcionario,
                    "estado": EstadoRegistro.ACTIVO if u.get("activo", True) else EstadoRegistro.INACTIVO,
                },
            )
            if not crear_auth:
                continue
            user = usuario.user or User.objects.filter(username=u["username"]).first()
            if user is None:
                partes = usuario.nombre.split(" ", 1)
                user = User(username=u["username"], email=usuario.correo, first_name=partes[0][:150],
                            last_name=(partes[1] if len(partes) > 1 else "")[:150],
                            is_active=usuario.activo)
                # Se guarda solo el hash (PBKDF2), nunca la clave en texto plano.
                if u.get("password"):
                    user.set_password(u["password"])
                else:
                    user.set_unusable_password()
                user.save()
                self.auth_creados += 1
            if usuario.user_id != user.pk:
                usuario.user = user
                usuario.save(update_fields=["user"])

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
