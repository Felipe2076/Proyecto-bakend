from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from control_gestion.models import CambioCompromiso, Compromiso, EventoAgenda
from control_gestion.reportes import ambito, perfil_acceso


def respuesta(request, mensaje, destino, status=200):
    if 'application/json' in request.headers.get('Accept', ''):
        if status != 200:
            return JsonResponse({'error': mensaje}, status=status)
        return JsonResponse({'mensaje': mensaje, 'destino': destino})
    (messages.success if status == 200 else messages.error)(request, mensaje)
    return redirect(destino)


def _mover_atencion(request, perfil, codigo, nuevo, anterior, destino):
    """Cambia el estado de una atención desde el Tubo (Pendiente / En proceso / Realizado = Cerrada)."""
    from control_gestion.consultas import ATENCION_DESDE_TUBO, ESTADO_ATENCION_EN_TUBO
    from requerimientos.models import Atencion

    if not request.user.has_perm('requerimientos.change_atencion'):
        return respuesta(request, 'Su perfil no puede modificar atenciones.', destino, 403)
    if nuevo not in ATENCION_DESDE_TUBO:
        return respuesta(request, 'Una atención no tiene el estado «Ingresado»; use Pendiente, En proceso o Realizado.', destino, 422)
    try:
        pk = int(codigo.split('-', 1)[1])
    except (IndexError, ValueError):
        return respuesta(request, 'La atención no está disponible.', destino, 404)
    with transaction.atomic():
        atencion = ambito(Atencion.objects.select_for_update(), perfil).filter(pk=pk).first()
        if atencion is None:
            return respuesta(request, 'La atención no está disponible.', destino, 404)
        actual = ESTADO_ATENCION_EN_TUBO.get(atencion.estado, 'PENDIENTE')
        if anterior is not None and anterior != actual:
            return respuesta(request, 'Otra persona cambió esta atención. Recargue la página.', destino, 409)
        if nuevo != actual:
            atencion.estado = ATENCION_DESDE_TUBO[nuevo]
            atencion.save(update_fields=['estado'])
    return respuesta(request, f'Atención {codigo}: {atencion.get_estado_display()}.', destino)


def mover_compromiso(request, perfil, ruta_vista='tubo_trabajo'):
    destino = reverse(ruta_vista)
    filtros = request.GET.copy()
    filtros.pop('vista', None)
    if filtros:
        destino += '?' + filtros.urlencode()
    codigo = request.POST.get('id_compromiso', '').strip()
    nuevo = request.POST.get('estado', '').strip().upper()
    anterior = request.POST.get('estado_anterior')
    if nuevo not in Compromiso.Estado.values:
        return respuesta(request, 'Seleccione un estado válido.', destino, 422)
    if codigo.upper().startswith('ATN-'):
        return _mover_atencion(request, perfil, codigo.upper(), nuevo, anterior, destino)
    with transaction.atomic():
        compromiso = ambito(Compromiso.objects.select_for_update(), perfil).filter(codigo=codigo).first()
        if compromiso is None:
            return respuesta(request, 'El compromiso no está disponible.', destino, 404)
        if anterior is not None and anterior != compromiso.estado:
            return respuesta(request, 'Otra persona cambió este compromiso. Recargue la página.', destino, 409)
        if nuevo != compromiso.estado:
            CambioCompromiso.objects.create(
                compromiso=compromiso, autor=request.user, estado_anterior=compromiso.estado,
                estado_nuevo=nuevo, observacion_anterior=compromiso.observaciones,
                observacion_nueva=compromiso.observaciones,
            )
            compromiso.estado = nuevo
            compromiso.save(update_fields=['estado'])
    return respuesta(request, f'Compromiso {codigo}: {compromiso.get_estado_display()}.', destino)


@require_POST
def mover_agenda(request, origen, codigo):
    perfil, error = perfil_acceso(request, 'agenda')
    if error is not None:
        return error
    destino = reverse('agenda')
    vista = 'lista' if request.POST.get('vista') == 'lista' else 'calendario'
    filtros = {'vista': vista, 'q': request.POST.get('q', '')[:250]}
    try:
        nueva = date.fromisoformat(request.POST.get('fecha', ''))
        anterior = date.fromisoformat(request.POST.get('fecha_anterior', ''))
        if not 2 <= nueva.year <= 9998:
            raise ValueError
    except ValueError:
        return respuesta(request, 'Seleccione una fecha válida.', destino, 422)
    destino_original = destino + '?' + urlencode({'anio': anterior.year, 'mes': anterior.month, **filtros})
    if origen == 'agenda':
        if not request.user.has_perm('control_gestion.change_eventoagenda'):
            return respuesta(request, 'Su perfil no permite reprogramar actividades de la agenda.', destino, 403)
        modelo, campo = EventoAgenda, 'fecha'
    elif origen == 'compromiso':
        _, error = perfil_acceso(request, 'compromisos')
        if error is not None:
            return error
        modelo, campo = Compromiso, 'fecha_compromiso'
    else:
        return respuesta(request, 'Solo se pueden reprogramar eventos y compromisos.', destino_original, 422)
    with transaction.atomic():
        registro = ambito(modelo.objects.select_for_update(), perfil).filter(codigo=codigo).first()
        if registro is None:
            return respuesta(request, 'El registro no está disponible.', destino_original, 404)
        if getattr(registro, campo) != anterior:
            return respuesta(request, 'La fecha cambió. Recargue la agenda para continuar.', destino_original, 409)
        setattr(registro, campo, nueva)
        registro.save(update_fields=[campo])
    destino += '?' + urlencode({'anio': nueva.year, 'mes': nueva.month, **filtros})
    return respuesta(request, f'{codigo} se movió al {nueva:%d/%m/%y}.', destino)
