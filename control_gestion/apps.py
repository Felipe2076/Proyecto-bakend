from django.apps import AppConfig


class ControlGestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "control_gestion"
    verbose_name = "Control de Gestión y Monitoreo Estratégico"

    def ready(self):
        # Las bajas físicas de modelos sincronizables quedan registradas para la app móvil.
        from django.db.models.signals import post_delete

        from control_gestion.models import OrganizacionComunitaria, TerritorioDelegacion
        from core.sincronizacion import registrar_baja
        from cuentas.models import Delegacion, Funcionario, Usuario

        def al_eliminar(sender, instance, **kwargs):
            registrar_baja(instance)

        for modelo in (Usuario, Funcionario, Delegacion, TerritorioDelegacion, OrganizacionComunitaria):
            post_delete.connect(al_eliminar, sender=modelo, weak=False,
                                dispatch_uid=f"siged-baja-{modelo._meta.label_lower}")
