"""Asigna delegación a organizaciones que no la tienen, solo cuando no hay duda.

Regla: el texto de ``territorio`` de la organización debe coincidir (sin distinguir
mayúsculas, tildes ni espacios) con un territorio del catálogo, y ese nombre debe
pertenecer a **una sola** delegación. Si no coincide o coincide con varias, no se
toca: queda para revisión manual en la lista («Sin delegación»). No se inventan
asociaciones territoriales.

Por defecto solo muestra lo que haría. Para guardar: ``--aplicar``.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from control_gestion.models import OrganizacionComunitaria, TerritorioDelegacion
from core.busqueda import normalizar


def clave(texto):
    return " ".join(normalizar(texto).split())


class Command(BaseCommand):
    help = "Asigna delegación a organizaciones sin delegación cuando su territorio calza con un único catálogo."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true", help="Guarda los cambios (sin esto solo simula).")

    def handle(self, *args, **opciones):
        catalogo = defaultdict(set)
        for nombre, delegacion_id in TerritorioDelegacion.objects.values_list("nombre", "delegacion_id"):
            catalogo[clave(nombre)].add(delegacion_id)
        asignables, sin_territorio, sin_catalogo, ambiguas = [], 0, 0, 0
        for org in OrganizacionComunitaria.objects.filter(delegacion__isnull=True).only("pk", "territorio"):
            texto = clave(org.territorio)
            if not texto:
                sin_territorio += 1
            elif texto not in catalogo:
                sin_catalogo += 1
            elif len(catalogo[texto]) > 1:
                ambiguas += 1
            else:
                asignables.append((org.pk, next(iter(catalogo[texto]))))
        if opciones["aplicar"] and asignables:
            with transaction.atomic():
                for pk, delegacion_id in asignables:
                    org = OrganizacionComunitaria.objects.select_for_update().get(pk=pk)
                    if org.delegacion_id is None:
                        org.delegacion_id = delegacion_id
                        org.save(update_fields=["delegacion"])
        accion = "asignadas" if opciones["aplicar"] else "se asignarían"
        self.stdout.write(
            f"Organizaciones sin delegación: {len(asignables) + sin_territorio + sin_catalogo + ambiguas}. "
            f"{accion.capitalize()}: {len(asignables)}. Quedan para revisión manual: sin territorio {sin_territorio}, "
            f"territorio fuera del catálogo {sin_catalogo}, territorio en varias delegaciones {ambiguas}."
        )
        if not opciones["aplicar"]:
            self.stdout.write("Simulación: no se guardó nada. Repita con --aplicar para guardar.")
