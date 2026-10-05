"""Código de recuperación en ``codigo_un_uso``.

El valor en claro existe solo para armar el correo. En la tabla queda el
HMAC-SHA256 (hex, 64 caracteres). La clave se lee de ``SIGED_CODE_HMAC_KEY``
y, si no está, de ``SECRET_KEY``. Las dos vienen del entorno. No es reversible
y no viaja en la sesión. Un acierto escribe ``usado_en``. Emitir otro escribe
``anulado_en`` en los anteriores que seguían vigentes.
"""

import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from cuentas.models import CodigoUnUso


def _clave_hmac() -> bytes:
    """``SIGED_CODE_HMAC_KEY`` del entorno (o de ``.env``), o ``SECRET_KEY`` si falta."""
    valor = os.environ.get("SIGED_CODE_HMAC_KEY", "").strip() or settings.SECRET_KEY
    return valor.encode("utf-8")


def hash_codigo(codigo: str) -> str:
    """HMAC-SHA256 en hexadecimal. Cabe en ``codigo_hash CHAR(64)``."""
    return hmac.new(
        _clave_hmac(),
        (codigo or "").encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_coincide(ingresado: str, almacenado: str) -> bool:
    if not almacenado or len(almacenado) != 64:
        return False
    return hmac.compare_digest(hash_codigo(ingresado), almacenado)


def _mascara_correo(correo: str) -> str:
    local, _, dominio = (correo or "").partition("@")
    if not dominio:
        return (correo or "")[:80]
    return f"{local[:1]}***@{dominio}"[:80]


def _vigentes(usuario):
    return CodigoUnUso.objects.filter(
        usuario=usuario,
        proposito=CodigoUnUso.PROPOSITO_RECUPERAR,
        usado_en__isnull=True,
        anulado_en__isnull=True,
    )


def emitir_codigo(usuario, ip: str | None = None) -> str:
    """Anula los códigos previos y devuelve el nuevo, solo para el correo."""
    ahora = timezone.now()
    _vigentes(usuario).update(anulado_en=ahora)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    CodigoUnUso.objects.create(
        proposito=CodigoUnUso.PROPOSITO_RECUPERAR,
        usuario=usuario,
        codigo_hash=hash_codigo(codigo),
        canal=CodigoUnUso.CANAL_CORREO,
        destino_mascara=_mascara_correo(usuario.correo),
        expira_en=ahora + timedelta(minutes=CodigoUnUso.VIGENCIA_MINUTOS),
        ip_origen=(ip or "")[:45] or None,
    )
    return codigo


def enviar_codigo(usuario, codigo) -> None:
    """Envía el código. Con DEBUG el backend de consola lo escribe en la salida del servidor."""
    send_mail(
        subject="Código de recuperación SIGED-SGR",
        message=(
            f"Su código de recuperación es {codigo}. "
            f"Vence en {CodigoUnUso.VIGENCIA_MINUTOS} minutos y solo puede usarse una vez."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.correo],
        fail_silently=False,
    )


def verificar_codigo(usuario, ingresado) -> str:
    """Comprueba el HMAC del código vigente.

    Devuelve ``ok``, ``invalido``, ``agotado``, ``expirado`` o ``ausente``.
    Un acierto escribe ``usado_en`` de inmediato.
    """
    fila = _vigentes(usuario).order_by("-creado_en").first()
    if fila is None:
        return "ausente"
    ahora = timezone.now()
    if ahora > fila.expira_en:
        fila.anulado_en = ahora
        fila.save(update_fields=["anulado_en"])
        return "expirado"
    if not hash_coincide(ingresado, fila.codigo_hash):
        fila.intentos += 1
        if fila.intentos >= CodigoUnUso.MAX_INTENTOS:
            fila.anulado_en = ahora
            fila.save(update_fields=["intentos", "anulado_en"])
            return "agotado"
        fila.save(update_fields=["intentos"])
        return "invalido"
    fila.usado_en = ahora
    fila.save(update_fields=["usado_en"])
    return "ok"
