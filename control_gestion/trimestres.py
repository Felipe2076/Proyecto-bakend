from calendar import monthrange
from datetime import date

from django.utils import timezone

from control_gestion.models import Medicion


def trimestre_calendario(fecha):
    numero = (fecha.month - 1) // 3 + 1
    mes = numero * 3
    inicio = date(fecha.year, mes - 2, 1)
    fin = date(fecha.year, mes, monthrange(fecha.year, mes)[1])
    return {
        'clave': f't-{fecha.year}-{numero}', 'codigo': '',
        'periodo': f'Trimestre {numero} de {fecha.year}',
        'fecha_inicio': inicio, 'fecha_termino': fin, 'dias_totales': (fin - inicio).days + 1,
    }


def datos_medicion(medicion):
    return {
        'clave': f'm-{medicion.pk}', 'codigo': medicion.codigo or '', 'periodo': medicion.periodo,
        'fecha_inicio': medicion.fecha_inicio, 'fecha_termino': medicion.fecha_termino,
        'dias_totales': medicion.dias_totales, 'delegacion_piloto': medicion.delegacion_piloto.nombre,
        'meta_cumplimiento_tubo': medicion.meta_cumplimiento_tubo,
    }


def trimestre_actual(hoy=None):
    hoy = hoy or timezone.localdate()
    medicion = Medicion.objects.select_related('delegacion_piloto').filter(
        fecha_inicio__lte=hoy, fecha_termino__gte=hoy,
    ).order_by('-fecha_inicio', '-pk').first()
    return datos_medicion(medicion) if medicion else trimestre_calendario(hoy)


def resumen_trimestre_vigente(hoy=None):
    """Trimestre vigente, único para todas las delegaciones, listo para mostrar en la bienvenida."""
    hoy = hoy or timezone.localdate()
    periodo = trimestre_actual(hoy)
    inicio, fin = periodo['fecha_inicio'], periodo['fecha_termino']
    total = max((fin - inicio).days + 1, 1)
    dia = min(max((hoy - inicio).days + 1, 0), total)
    return {
        'periodo': periodo['periodo'], 'inicio': inicio.strftime('%d/%m/%y'), 'termino': fin.strftime('%d/%m/%y'),
        'dia': dia, 'dias_total': total, 'restantes': max((fin - hoy).days, 0),
        'porcentaje': round(dia * 100 / total), 'configurado': periodo['clave'].startswith('m-'),
    }


def seleccionar_trimestre(clave, hoy=None):
    hoy = hoy or timezone.localdate()
    actual = trimestre_actual(hoy)
    if clave == 'todos':
        return None, actual
    if clave.startswith('m-') and clave[2:].isascii() and clave[2:].isdigit() and len(clave) <= 21:
        pk = int(clave[2:])
        medicion = Medicion.objects.select_related('delegacion_piloto').filter(pk=pk).first() if 0 < pk < 2 ** 63 else None
        if medicion:
            return datos_medicion(medicion), actual
    if clave.startswith('t-'):
        try:
            _, anio, numero = clave.split('-')
            numero = int(numero)
            if not 1 <= numero <= 4:
                raise ValueError
            return trimestre_calendario(date(int(anio), numero * 3, 1)), actual
        except (ValueError, OverflowError):
            pass
    return actual, actual


def opciones_trimestres(actividades, seleccionado, actual):
    opciones = {actual['clave']: actual}
    if seleccionado:
        opciones[seleccionado['clave']] = seleccionado
    for fecha in actividades.dates('fecha_actividad', 'month', order='DESC'):
        periodo = trimestre_calendario(fecha)
        opciones.setdefault(periodo['clave'], periodo)
    for medicion in Medicion.objects.select_related('delegacion_piloto'):
        periodo = datos_medicion(medicion)
        opciones[periodo['clave']] = periodo
    return sorted(opciones.values(), key=lambda p: (p['fecha_inicio'], p['clave']), reverse=True)
