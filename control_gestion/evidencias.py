"""Validación y entrega de archivos privados de actividades."""
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from control_gestion.models import Actividad

MAX_PIXELES = 40_000_000  # ~ 8000 x 5000; mayor que eso no aporta como evidencia.

def validar_archivo(archivo):
    if archivo.size > 10 * 1024 * 1024:
        raise ValueError("La evidencia supera el máximo de 10 MB.")
    extension = Path(archivo.name).suffix.lower()
    try:
        if extension == '.pdf':
            if archivo.read(5) != b'%PDF-':
                raise ValueError("El archivo no es un PDF válido.")
        elif extension in ('.png', '.jpg', '.jpeg'):
            image = Image.open(archivo)
            # Las cámaras de celular suelen grabar JPEG como «MPO» (varias vistas): es JPEG válido.
            esperados = {'PNG'} if extension == '.png' else {'JPEG', 'MPO'}
            if image.format not in esperados:
                raise ValueError("El contenido de la imagen no coincide con su extensión.")
            ancho, alto = image.size
            if ancho * alto > MAX_PIXELES:
                raise ValueError("La imagen supera la resolución máxima permitida.")
            image.verify()
        else:
            raise ValueError("Adjunte una imagen JPG, PNG o un PDF.")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("La imagen está dañada o no es válida.")
    finally:
        archivo.seek(0)

@never_cache
@require_safe
def ver_evidencia(request, codigo):
    from control_gestion.reportes import perfil_acceso, ambito
    if request.user.is_authenticated and request.user.is_staff and request.user.has_perm('control_gestion.view_actividad'):
        qs = Actividad.objects.all()
    else:
        perfil, error = perfil_acceso(request, 'actividades')
        if error is not None:
            return error
        qs = ambito(Actividad.objects.all(), perfil)
    actividad = get_object_or_404(qs, codigo=codigo)
    if not actividad.evidencia_archivo:
        raise Http404("Esta actividad no tiene un archivo adjunto.")
    try:
        stream = actividad.evidencia_archivo.open('rb')
    except FileNotFoundError:
        raise Http404("El archivo de evidencia no está disponible.")
    extension = Path(actividad.evidencia_archivo.name).suffix.lower()
    mime = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.pdf':'application/pdf'}.get(extension,'application/octet-stream')
    response = FileResponse(stream, content_type=mime, as_attachment=mime=='application/octet-stream', filename=Path(actividad.evidencia_archivo.name).name)
    response['X-Content-Type-Options']='nosniff'
    response['Content-Security-Policy']="default-src 'none'; sandbox"
    return response


def puede_validar(perfil):
    """Revisa evidencias: administrador, superusuario o quien tiene el cargo de delegado/a.

    Se compara la palabra completa («delegado», «delegada»), no un trozo del texto:
    «subdelegado» o «asistente de delegación» ya no obtienen permiso de revisión.
    """
    import re

    from core.busqueda import normalizar
    if perfil.rol.codigo in ('administrador', 'superusuario'):
        return True
    cargos = [perfil.cargo.nombre if perfil.cargo_id else '']
    if perfil.funcionario_id and perfil.funcionario.cargo_id:
        cargos.append(perfil.funcionario.cargo.nombre)
    return any(re.search(r'(^|[^a-z])delegad[oa]s?([^a-z]|$)', normalizar(c)) for c in cargos)

from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

@require_POST
@transaction.atomic
def validar_felicitacion(request, codigo):
    from control_gestion.reportes import perfil_acceso, ambito
    perfil,error=perfil_acceso(request,'actividades')
    if error is not None:return error
    if not puede_validar(perfil):return HttpResponseForbidden('La validación corresponde al delegado o al administrador autorizado.')
    actividad=get_object_or_404(ambito(Actividad.objects.select_for_update(),perfil),codigo=codigo)
    if actividad.estado_revision!='HISTORICA':
        return redirect('actividad_revision',codigo=codigo)
    if actividad.tipo_registro != 'FELICITACION' or not actividad.evidencia_archivo:
        messages.error(request,'Debe adjuntar el respaldo formal de la felicitación antes de validarla.')
    elif actividad.funcionario_id == perfil.funcionario_id:
        messages.error(request,'La felicitación debe validarla otra persona autorizada.')
    elif actividad.fecha_validacion is None:
        actividad.punto_validado=True
        actividad.validado_por=request.user
        actividad.fecha_validacion=timezone.now()
        actividad.save(update_fields=['punto_validado','validado_por','fecha_validacion'])
        messages.success(request,'Felicitación validada con respaldo y registro de aprobación.')
    else:
        messages.info(request,'Esta felicitación ya fue validada.')
    return redirect('actividades_diarias')

def bonificacion(funcionario, periodo):
    cantidad=Actividad.objects.filter(funcionario=funcionario,tipo_registro='FELICITACION',punto_validado=True,fecha_validacion__isnull=False,fecha_actividad__gte=periodo['fecha_inicio'],fecha_actividad__lte=periodo['fecha_termino']).count()
    return cantidad*10
