"""Lista (y, si se pide, elimina) cuentas de acceso sin perfil de usuario.

Una cuenta así bloquea el alta de ese RUT. Por defecto solo informa; no muestra contraseñas
ni correos. No toca cuentas de personal técnico (staff o superusuario).

    python manage.py cuentas_huerfanas              # solo informe
    python manage.py cuentas_huerfanas --eliminar   # borra las huérfanas que no sean staff
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.validaciones import enmascarar_rut


class Command(BaseCommand):
    help = "Informa las cuentas de acceso sin perfil asociado; --eliminar las borra (excepto staff)."

    def add_arguments(self, parser):
        parser.add_argument("--eliminar", action="store_true", help="Borra las huérfanas que no sean staff.")

    def handle(self, *args, **opciones):
        User = get_user_model()
        huerfanas = User.objects.filter(perfil__isnull=True).order_by("pk")
        if not huerfanas.exists():
            self.stdout.write("Sin cuentas huérfanas.")
            return
        borrables = []
        for u in huerfanas:
            tecnica = u.is_staff or u.is_superuser
            etiqueta = enmascarar_rut(u.username) or "(usuario no RUT)"
            self.stdout.write(f"  id={u.pk} usuario={etiqueta} activa={u.is_active} "
                              f"{'TÉCNICA: se conserva' if tecnica else 'huérfana'}")
            if not tecnica:
                borrables.append(u.pk)
        self.stdout.write(f"Total: {huerfanas.count()}; eliminables: {len(borrables)}.")
        if opciones["eliminar"] and borrables:
            with transaction.atomic():
                User.objects.filter(pk__in=borrables).delete()
            self.stdout.write(self.style.WARNING(f"Eliminadas {len(borrables)} cuentas huérfanas."))
        elif borrables:
            self.stdout.write("Informe solamente. Para borrarlas: --eliminar")
