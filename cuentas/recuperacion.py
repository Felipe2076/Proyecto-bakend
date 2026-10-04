"""Código de recuperación: hash de un solo uso, enviado por correo.

El valor en claro existe solo en la memoria del proceso que arma el mensaje.
No se guarda en la sesión, no se cifra de forma reversible y no se muestra
en la página. Al emitir uno nuevo, los anteriores quedan inutilizados. Al
acertar, el código se marca usado antes de permitir cambiar la clave.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from cuentas.models import CodigoRecuperacion


def emitir_codigo(usuario) -> str:
    """Invalida los códigos previos y devuelve el nuevo, solo para el correo."""
    CodigoRecuperacion.objects.filter(usuario=usuario, usado=False).update(usado=True)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    CodigoRecuperacion.objects.create(
        usuario=usuario,
        codigo_hash=make_password(codigo),
        expira=timezone.now() + timedelta(minutes=CodigoRecuperacion.VIGENCIA_MINUTOS),
    )
    return codigo


def enviar_codigo(usuario, codigo) -> None:
    """Envía el código. Con DEBUG el backend de consola lo escribe en la salida del servidor."""
    send_mail(
        subject="Código de recuperación SIGED-SGR",
        message=(
            f"Su código de recuperación es {codigo}. "
            f"Vence en {CodigoRecuperacion.VIGENCIA_MINUTOS} minutos y solo puede usarse una vez."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.correo],
        fail_silently=False,
    )


def verificar_codigo(usuario, ingresado) -> str:
    """Comprueba el hash del código vigente.

    Devuelve ``ok``, ``invalido``, ``agotado``, ``expirado`` o ``ausente``.
    Un acierto marca la fila como usada de inmediato.
    """
    fila = (
        CodigoRecuperacion.objects.filter(usuario=usuario, usado=False)
        .order_by("-creado")
        .first()
    )
    if fila is None:
        return "ausente"
    if timezone.now() > fila.expira:
        fila.usado = True
        fila.save(update_fields=["usado"])
        return "expirado"
    if not check_password(ingresado, fila.codigo_hash):
        fila.intentos += 1
        if fila.intentos >= CodigoRecuperacion.MAX_INTENTOS:
            fila.usado = True
            fila.save(update_fields=["intentos", "usado"])
            return "agotado"
        fila.save(update_fields=["intentos"])
        return "invalido"
    fila.usado = True
    fila.save(update_fields=["usado"])
    return "ok"
