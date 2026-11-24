"""Campos de control para sincronizar con la app móvil (SQLite en el teléfono ↔ MySQL).

Cada modelo sincronizable lleva:

- ``uuid``: identificador estable que no cambia aunque cambie el código o el nombre.
- ``actualizado``: fecha y hora de la última escritura; el teléfono pide «cambios desde».
- ``version``: contador que sube en cada guardado; permite detectar conflictos (409).

Las columnas son nulas en la base (se agregan sin DEFAULT para que la migración pase el
filtro del script de despliegue) y se completan al guardar o con
``manage.py completar_sincronizacion``. Las bajas físicas quedan en ``RegistroBaja``.
"""
import uuid as _uuid

from django.utils import timezone


class SincronizableMixin:
    """Se pone antes de ``models.Model`` en las bases del modelo."""

    def marcar_sincronizacion(self):
        self.actualizado = timezone.now()
        self.version = (self.version or 0) + 1
        if not self.uuid:
            self.uuid = _uuid.uuid4()

    def save(self, *args, **kwargs):
        self.marcar_sincronizacion()
        campos = kwargs.get("update_fields")
        if campos is not None:
            kwargs["update_fields"] = set(campos) | {"actualizado", "version", "uuid"}
        return super().save(*args, **kwargs)


def registrar_baja(instancia):
    """Deja constancia de una eliminación física para que el teléfono también la borre."""
    from control_gestion.models import RegistroBaja

    if getattr(instancia, "uuid", None):
        RegistroBaja.objects.create(
            modelo=instancia._meta.label_lower,
            uuid=instancia.uuid,
            codigo=str(getattr(instancia, "codigo", "") or instancia.pk)[:40],
        )
