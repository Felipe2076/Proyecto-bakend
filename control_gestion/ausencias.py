"""Días naturales excluidos del período, sin duplicar fechas superpuestas."""
from datetime import timedelta
from control_gestion.models import Ausencia

def ajustar_periodo(funcionario, periodo):
    if not funcionario:
        return periodo
    inicio=periodo['fecha_inicio'];fin=periodo['fecha_termino'];hoy=periodo['fecha_hoy']
    fechas=set()
    for a in Ausencia.objects.filter(funcionario=funcionario,fecha_inicio__lte=fin,fecha_termino__gte=inicio):
        d=max(a.fecha_inicio,inicio);ultimo=min(a.fecha_termino,fin)
        while d<=ultimo:
            fechas.add(d);d+=timedelta(days=1)
    total=max(0,periodo['dias_totales']-len(fechas))
    transcurridos=max(0,periodo['dias_avance']-sum(d<=hoy for d in fechas))
    esperado=round(min(100,transcurridos*100/total),1) if total else 0
    return {**periodo,'dias_totales':total,'dias_avance':transcurridos,'pct_esperado':esperado,'dias_ausencia':len(fechas)}
