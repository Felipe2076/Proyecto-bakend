from django import forms
from django.core import signing
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from cuentas.servicios import obtener_parametros
from requerimientos.models import Requerimiento


class EncuestaVecinalForm(forms.Form):
    nota = forms.TypedChoiceField(
        label='¿Qué tan satisfecho quedó con el servicio recibido?',
        choices=[(1, '1 · Muy insatisfecho'), (2, '2 · Insatisfecho'), (3, '3 · Neutral'),
                 (4, '4 · Satisfecho'), (5, '5 · Muy satisfecho')],
        coerce=int, widget=forms.RadioSelect,
    )
    comentario = forms.CharField(label='¿Qué podríamos mejorar?', required=False, max_length=500,
                                 widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))


def enlace_encuesta(request, ticket):
    token = signing.dumps({'id': ticket.pk}, salt='siged.encuesta.vecinal.v1')
    return request.build_absolute_uri(reverse('encuesta_vecinal', args=[token]))


def guardar_respuesta(ticket_id, nota, comentario):
    return Requerimiento.objects.filter(
        pk=ticket_id, estado=Requerimiento.Estado.RESUELTO,
        evaluacion_satisfaccion__isnull=True,
    ).update(evaluacion_satisfaccion=nota, comentario_satisfaccion=comentario)


@never_cache
@require_http_methods(['GET', 'POST'])
def responder(request, token):
    template = 'requerimientos/encuesta_vecinal.html'
    try:
        data = signing.loads(token, salt='siged.encuesta.vecinal.v1', max_age=30 * 86400)
    except signing.BadSignature:
        return render(request, template, {'aviso': 'El enlace no es válido o expiró.'}, status=404)
    ticket = Requerimiento.objects.filter(pk=data['id']).first()
    if (not obtener_parametros().get('encuesta_habilitada', True)
            or not ticket or ticket.estado != Requerimiento.Estado.RESUELTO):
        return render(request, template, {'aviso': 'Esta encuesta no está disponible.'}, status=404)
    if ticket.evaluacion_satisfaccion is not None:
        return render(request, template, {'aviso': 'Gracias. La respuesta de este ticket ya quedó registrada.'})
    form = EncuestaVecinalForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        guardar_respuesta(ticket.pk, form.cleaned_data['nota'], form.cleaned_data['comentario'])
        return redirect('encuesta_vecinal', token=token)
    return render(request, template, {'form': form})
