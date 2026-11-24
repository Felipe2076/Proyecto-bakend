"""Completa uuid, actualizado y version en filas antiguas (las columnas nacen vacías).

En producción las migraciones se registran con ``--fake`` y no ejecutan código de datos;
este comando hace ese relleno con la cuenta de la aplicación (solo UPDATE). Es idempotente:
solo toca filas con ``uuid`` vacío. Por defecto simula; para guardar: ``--aplicar``.
"""
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


def modelos_sincronizables():
    from control_gestion.models import OrganizacionComunitaria, TerritorioDelegacion
    from cuentas.models import Delegacion, Funcionario, Usuario

    return (Delegacion, TerritorioDelegacion, Funcionario, Usuario, OrganizacionComunitaria)


class Command(BaseCommand):
    help = "Rellena los campos de sincronización (uuid, actualizado, version) de filas existentes."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Guarda los cambios (sin esto solo cuenta).")

    def handle(self, *args, **opciones):
        ahora = timezone.now()
        for modelo in modelos_sincronizables():
            pendientes = list(modelo.objects.filter(uuid__isnull=True).values_list("pk", flat=True))
            if opciones["aplicar"]:
                # update() no pasa por save(): no reescribe códigos ni dispara otras reglas.
                for i in range(0, len(pendientes), 500):
                    with transaction.atomic():
                        for pk in pendientes[i:i + 500]:
                            modelo.objects.filter(pk=pk, uuid__isnull=True).update(
                                uuid=uuid.uuid4(), actualizado=ahora, version=1)
            verbo = "completadas" if opciones["aplicar"] else "por completar"
            self.stdout.write(f"{modelo._meta.verbose_name_plural}: {len(pendientes)} {verbo}.")
        if not opciones["aplicar"]:
            self.stdout.write("Simulación: no se guardó nada. Repita con --aplicar para guardar.")
