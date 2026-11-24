"""Controles defensivos transversales: IP de cliente, cuotas de intentos, tamaño de petición,
cabeceras y filtro de datos personales en los logs (ISO 27002 8.15/8.16, Ley 19.628/21.719)."""
import ipaddress
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.crypto import salted_hmac


def ip_cliente(request):
    """IP del cliente. X-Forwarded-For solo se usa si el despliegue declara un proxy de confianza
    (SIGED_PROXY_CONFIABLE) y la petición llega desde él; se toma la entrada que agregó ese proxy."""
    remota = request.META.get('REMOTE_ADDR', '')
    redes = getattr(settings, 'SIGED_PROXIES_CONFIABLES', [])
    if redes and remota:
        try:
            origen = ipaddress.ip_address(remota)
            confiable = any(origen in red for red in redes)
        except ValueError:
            confiable = False
        if confiable:
            ultima = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[-1].strip()
            try:
                return str(ipaddress.ip_address(ultima))
            except ValueError:
                pass
    return remota


class LimiteExcedido(Exception):
    pass


def _modelo():
    from control_gestion.models import IntentosMovil
    return IntentosMovil


def clave_limite(ambito, valor):
    # Solo se guarda un HMAC: la tabla de cuotas no contiene IP, RUT ni correo en claro.
    return salted_hmac('siged-limite-' + ambito, str(valor)).hexdigest()


def consumir(cuotas, ventana=timedelta(minutes=15)):
    """Suma un intento a cada clave {clave: máximo}. Lanza LimiteExcedido si alguna ya llegó al tope."""
    Intentos = _modelo()
    ahora = timezone.now()
    with transaction.atomic():
        for clave in sorted(cuotas):
            Intentos.objects.get_or_create(clave=clave, defaults={'inicio': ahora})
            fila = Intentos.objects.select_for_update().get(clave=clave)
            if ahora - fila.inicio > ventana:
                fila.inicio, fila.intentos = ahora, 0
            if fila.intentos >= cuotas[clave]:
                raise LimiteExcedido()
            fila.intentos += 1
            fila.save(update_fields=['inicio', 'intentos'])


def liberar(*claves):
    _modelo().objects.filter(clave__in=claves).delete()


class PeticionAcotadaMiddleware:
    """Rechaza cuerpos más grandes que SIGED_MAX_PETICION antes de leerlos y agrega cabeceras
    que Django no pone por defecto. El proxy (Apache) debe aplicar el mismo límite."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            largo = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            largo = 0
        if largo > settings.SIGED_MAX_PETICION:
            return HttpResponse('La solicitud supera el tamaño permitido.', status=413,
                                content_type='text/plain; charset=utf-8')
        response = self.get_response(request)
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()')
        if request.path.startswith(('/login', '/recuperar', '/activar', '/archivos-privados', '/api/')):
            response.headers.setdefault('Cache-Control', 'no-store')
        return response


_RUT = re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b')
_CORREO = re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+')
_TOKEN = re.compile(r'(?i)(token|password|clave|codigo|bearer)([=:\s/]+)[^\s&/]+')
_QUERY = re.compile(r'\?[^\s"\']*')


def enmascarar(texto):
    texto = _TOKEN.sub(r'\1\2[oculto]', texto)
    texto = _QUERY.sub('?[consulta oculta]', texto)
    texto = _CORREO.sub('[correo oculto]', texto)
    return _RUT.sub('[rut oculto]', texto)


class FiltroDatosPersonales(logging.Filter):
    """Quita RUT, correos, tokens y parámetros de consulta antes de escribir un registro."""

    def filter(self, record):
        try:
            mensaje = record.getMessage()
        except Exception:  # Un registro mal formado no debe detener la aplicación.
            mensaje = str(record.msg)
        record.msg, record.args = enmascarar(mensaje), ()
        if record.exc_info and not settings.DEBUG:
            # El traceback puede incluir valores de formulario; se conserva solo el tipo de error.
            record.msg += f' [{record.exc_info[0].__name__}]'
            record.exc_info = record.exc_text = None
        if hasattr(record, 'request'):
            record.request = None
        return True


def salud(request):
    """Healthcheck de Docker: confirma que Django responde y que la base acepta una consulta."""
    from django.db import connection
    from django.http import JsonResponse
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:  # El detalle del error queda fuera de la respuesta pública.
        logging.getLogger('siged.seguridad').error('salud_bd_no_disponible')
        return JsonResponse({'estado': 'error'}, status=503)
    return JsonResponse({'estado': 'ok'})


def exigir_modo_demo(opciones, nombre_comando):
    """Detiene un comando que reescribe datos si no se pidió explícitamente sobre una base de demostración.

    Requiere la bandera ``--demo`` y, además, ``DEBUG=True`` o la variable de entorno
    ``SIGED_PERMITIR_DEMO=1``. En producción (DEBUG=False y sin la variable) nunca corre.
    """
    import os

    from django.conf import settings
    from django.core.management.base import CommandError

    if not opciones.get("demo"):
        raise CommandError(
            f"{nombre_comando} reescribe datos y solo sirve para una base de demostración. "
            "Si es eso lo que quiere, agregue --demo."
        )
    if not (settings.DEBUG or os.environ.get("SIGED_PERMITIR_DEMO") == "1"):
        raise CommandError(
            f"{nombre_comando} está bloqueado con DEBUG=False. Para una base de demostración "
            "defina SIGED_PERMITIR_DEMO=1 en ese entorno; nunca en producción."
        )


def agregar_bandera_demo(parser):
    parser.add_argument("--demo", action="store_true",
                        help="Confirma que la base es de demostración (obligatorio).")
