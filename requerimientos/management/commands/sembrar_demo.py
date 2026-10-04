"""Datos de demostración para el panel personal (idempotente, fechas relativas a hoy).

Uso:
    python manage.py sembrar_demo
    python manage.py sembrar_demo --usuarios funcionario jefatura

Para cada rol de prueba (administrador, jefatura, funcionario, ventanilla):
  1. Asegura un Funcionario enlazado (Usuario.funcionario). Si no tiene, reutiliza
     uno libre con el mismo nombre o crea "FUN-DEMO-<USUARIO>" en su delegación.
  2. Deja asignados a ese funcionario 4 tickets marcados como demo
     (código DEMO-<USUARIO>-N, descripción "[DEMO] ..."):
       - 3 abiertos ingresados hace 2, 4 y 7 días  -> verde, ámbar y rojo
       - 1 resuelto ingresado hace 3 días (el panel colorea por días, también los resueltos)
     Las fechas se recalculan en cada ejecución, así que puede correrse cualquier día.
     No se modifican los tickets reales del sistema.
  3. Si el funcionario no tiene metas (ItemFuncionario), le asigna 3 ítems.

Volver a ejecutarlo no duplica nada: actualiza los mismos registros.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from control_gestion.models import ItemFuncionario, Meta
from cuentas.models import Cargo, Delegacion, Funcionario, Usuario
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino

USUARIOS_DEMO = ["administrador", "jefatura", "funcionario", "ventanilla"]

# (días desde el ingreso, estado, texto)
TICKETS_DEMO = [
    (2, Requerimiento.Estado.PENDIENTE, "Solicitud de poda de árbol frente a sede vecinal"),
    (4, Requerimiento.Estado.EN_PROCESO, "Reclamo por luminaria apagada en pasaje"),
    (7, Requerimiento.Estado.PENDIENTE, "Retiro de escombros en área verde del sector"),
    (3, Requerimiento.Estado.RESUELTO, "Consulta por horario de atención de la delegación"),
]

# Metas por defecto si el funcionario no tiene ninguna: (nombre, ponderador, meta trimestre, avance)
METAS_DEMO = [("Cobertura", 40, 30, 22), ("Tiempos", 30, 20, 13), ("Satisfacción", 30, 10, 8)]

VECINO_DEMO = "Vecino demo SIGED-SGR (ficticio)"


class Command(BaseCommand):
    help = "Siembra tickets y metas de demostración para el panel personal (idempotente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuarios", nargs="+", default=USUARIOS_DEMO, metavar="USERNAME",
            help="Usuarios a sembrar (por defecto: %s)." % " ".join(USUARIOS_DEMO),
        )

    def handle(self, *args, **opts):
        hoy = timezone.localdate()
        catalogo = self._catalogo()
        resumen = []
        with transaction.atomic():
            for username in opts["usuarios"]:
                usuario = self._resolver_usuario(username)
                if usuario is None:
                    self.stdout.write(self.style.WARNING(f"- {username}: no existe, se omite."))
                    continue
                funcionario, origen = self._asegurar_funcionario(usuario)
                tickets = self._sembrar_tickets(usuario, funcionario, catalogo, hoy)
                metas = self._asegurar_metas(funcionario)
                resumen.append((usuario, funcionario, origen, tickets, metas))

        self.stdout.write(self.style.SUCCESS(f"Datos demo al {hoy:%d-%m-%Y}:"))
        for usuario, funcionario, origen, tickets, metas in resumen:
            self.stdout.write(
                f"- {usuario.username} ({usuario.rol.codigo}) -> {funcionario.codigo} {funcionario.nombre}"
                f" · {funcionario.delegacion.nombre} [{origen}]"
            )
            for codigo, dias, estado, accion in tickets:
                self.stdout.write(f"    {codigo:<20} día {dias:>2} · {estado:<11} ({accion})")
            self.stdout.write(f"    metas: {metas}")

    # ------------------------------------------------------------------
    def _catalogo(self):
        canal = CanalIngreso.objects.filter(activo=True).order_by("pk").first() or CanalIngreso.objects.order_by("pk").first()
        tipo = TipoGestion.objects.order_by("pk").first()
        area = AreaSoporte.objects.order_by("pk").first()
        faltan = [n for n, v in (("CanalIngreso", canal), ("TipoGestion", tipo), ("AreaSoporte", area)) if v is None]
        if faltan:
            raise CommandError(
                "Faltan catálogos (%s). Cargue primero: python manage.py loaddata fixtures/01_catalogos.json"
                % ", ".join(faltan)
            )
        return {"canal": canal, "tipo": tipo, "area": area}

    def _resolver_usuario(self, identificador):
        from core.validaciones import rut_normalizado_valido

        usuario = (
            Usuario.objects.select_related("funcionario", "delegacion", "cargo", "rol")
            .filter(username=identificador)
            .first()
        )
        if usuario is not None:
            return usuario
        rut = rut_normalizado_valido(identificador)
        if rut:
            usuario = (
                Usuario.objects.select_related("funcionario", "delegacion", "cargo", "rol")
                .filter(funcionario__rut=rut)
                .first()
            )
            if usuario is not None:
                return usuario
        return (
            Usuario.objects.select_related("funcionario", "delegacion", "cargo", "rol")
            .filter(rol__codigo=identificador)
            .order_by("pk")
            .first()
        )

    def _delegacion_de(self, usuario):
        return (
            usuario.delegacion
            or Delegacion.objects.filter(nombre="Delegación Centro").first()
            or Delegacion.objects.order_by("pk").first()
        )

    def _asegurar_funcionario(self, usuario):
        if usuario.funcionario_id:
            return usuario.funcionario, "ya enlazado"
        libre = Funcionario.objects.filter(nombre=usuario.nombre, usuario__isnull=True).first()
        if libre is not None:
            funcionario, origen = libre, "reutilizado"
        else:
            delegacion = self._delegacion_de(usuario)
            cargo = usuario.cargo or Cargo.objects.order_by("pk").first()
            if delegacion is None or cargo is None:
                raise CommandError("Se necesitan al menos una Delegación y un Cargo (loaddata fixtures/01_catalogos.json).")
            from cuentas.simulacion import identidad, nombre_visible, rut_trabajador

            indice = 800 + Funcionario.objects.count()
            nombres, paterno, materno = identidad(indice)
            funcionario, creado = Funcionario.objects.get_or_create(
                codigo=f"FUN-DEMO-{usuario.pk}"[:20],
                defaults={
                    "nombre": nombre_visible(nombres, paterno, materno, True),
                    "nombres": nombres,
                    "apellido_paterno": paterno,
                    "apellido_materno": materno,
                    "rut": rut_trabajador(indice),
                    "es_simulacion": True,
                    "cargo": cargo,
                    "delegacion": delegacion,
                },
            )
            origen = "creado" if creado else "reutilizado"
            otro = getattr(funcionario, "usuario", None) if not creado else None
            if otro is not None and otro.pk != usuario.pk:
                raise CommandError(f"{funcionario.codigo} ya está enlazado a {otro.username}.")
        usuario.funcionario = funcionario
        usuario.save(update_fields=["funcionario"])
        return funcionario, origen

    def _vecino(self, delegacion):
        from cuentas.simulacion import rut_vecino

        vecino, _ = Vecino.objects.get_or_create(
            nombre=VECINO_DEMO,
            defaults={
                "delegacion": delegacion,
                "territorio": "Demo",
                "direccion": "Calle Ficticia 900",
                "rut": rut_vecino(900),
                "telefono": "+56900000900",
                "correo": "vecinodemo@siged.test",
                "es_simulacion": True,
            },
        )
        return vecino

    def _sembrar_tickets(self, usuario, funcionario, catalogo, hoy):
        filas = []
        vecino = self._vecino(funcionario.delegacion)
        prefijo = f"DEMO-{usuario.username.upper()[:12]}"
        for n, (dias, estado, texto) in enumerate(TICKETS_DEMO, start=1):
            resuelto = estado == Requerimiento.Estado.RESUELTO
            _, creado = Requerimiento.objects.update_or_create(
                codigo=f"{prefijo}-{n}",
                defaults={
                    "vecino": vecino,
                    "delegacion": funcionario.delegacion,
                    "canal_ingreso": catalogo["canal"],
                    "tipo_gestion": catalogo["tipo"],
                    "area": catalogo["area"],
                    "descripcion": f"[DEMO] {texto}.",
                    "fecha_ingreso": hoy - timedelta(days=dias),
                    "funcionario": funcionario,
                    "asignado_a": funcionario.nombre,
                    "estado": estado,
                    "evaluacion_satisfaccion": 5 if resuelto else None,
                    "comentario_satisfaccion": "Ticket de demostración." if resuelto else "",
                },
            )
            filas.append((f"{prefijo}-{n}", dias, estado, "creado" if creado else "actualizado"))
        return filas

    def _asegurar_metas(self, funcionario):
        existentes = ItemFuncionario.objects.filter(funcionario=funcionario).count()
        if existentes:
            return f"{existentes} existentes (sin cambios)"
        creadas = 0
        for nombre, ponderador, meta_trim, avance in METAS_DEMO:
            meta, _ = Meta.objects.get_or_create(nombre=nombre)
            ItemFuncionario.objects.get_or_create(
                funcionario=funcionario, meta=meta,
                defaults={"ponderador": ponderador, "meta_trimestre": meta_trim, "avance_actual": avance},
            )
            creadas += 1
        return f"{creadas} creadas"
