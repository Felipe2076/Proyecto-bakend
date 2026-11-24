"""Revisión compartida por web y móvil. No reescribe puntajes históricos."""
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from control_gestion.models import Actividad, ItemFuncionario, RevisionActividad
from cuentas.models import Funcionario
from control_gestion.evidencias import puede_validar, validar_archivo
from core.busqueda import normalizar

class ErrorRevision(ValueError):
    def __init__(self,mensaje,status=422):
        super().__init__(mensaje);self.status=status

def alcance(qs,perfil,propio=False):
    if propio:return qs.filter(funcionario_id=perfil.funcionario_id) if perfil.funcionario_id else qs.none()
    return qs if perfil.rol.codigo=='superusuario' else qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()

@transaction.atomic
def revisar(perfil,codigo,decision,comentario,version):
    if not puede_validar(perfil):raise ErrorRevision('No tiene permiso de verificador.',403)
    previo=alcance(Actividad.objects.all(),perfil).filter(codigo=codigo).first()
    if not previo:raise ErrorRevision('Actividad no encontrada.',404)
    Funcionario.objects.select_for_update().get(pk=previo.funcionario_id)
    a=Actividad.objects.select_for_update().select_related('funcionario__cargo').get(pk=previo.pk)
    if a.funcionario_id==perfil.funcionario_id or a.creado_por_id==perfil.user_id:raise ErrorRevision('No puede revisar su propio trabajo.',403)
    if a.estado_revision=='HISTORICA':raise ErrorRevision('El registro histórico se conserva sin cambios.',409)
    if a.version_revision!=version or a.estado_revision!='PENDIENTE':raise ErrorRevision('El registro cambió. Actualice antes de revisar.',409)
    if decision not in ('APROBADA','RECHAZADA','CORRECCION'):raise ErrorRevision('Seleccione una decisión válida.')
    if not comentario.strip() or len(comentario)>2000:raise ErrorRevision('Ingrese una observación de 1 a 2000 caracteres.')
    if decision=='APROBADA':
        if not a.evidencia_archivo or not a.evidencia_archivo.storage.exists(a.evidencia_archivo.name):raise ErrorRevision('Debe existir un archivo de respaldo antes de aprobar.')
        cargo=normalizar(a.funcionario.cargo.nombre if a.funcionario.cargo_id else '')
        suma=a.tipo_registro=='RESULTADO' and bool(a.funcionario.nombre.strip()) and 'delegado' not in cargo
        item=ItemFuncionario.objects.filter(funcionario_id=a.funcionario_id,meta_id=a.meta_id)
        if suma and not item.exists():raise ErrorRevision('El funcionario no tiene este ítem asignado.')
        if suma:item.update(avance_actual=F('avance_actual')+1)
        a.punto_validado=suma or a.tipo_registro=='FELICITACION'
        a.validado_por=perfil.user;a.fecha_validacion=timezone.now()
    a.estado_revision=decision;a.version_revision+=1
    a.save(update_fields=['estado_revision','version_revision','punto_validado','validado_por','fecha_validacion'])
    RevisionActividad.objects.create(actividad=a,autor=perfil.user,estado_anterior='PENDIENTE',estado_nuevo=decision,comentario=comentario.strip(),version=a.version_revision)
    return a

@transaction.atomic
def corregir(perfil,codigo,datos,archivos,version):
    previo=Actividad.objects.filter(codigo=codigo,funcionario_id=perfil.funcionario_id).first()
    if not previo:raise ErrorRevision('Actividad no encontrada.',404)
    Funcionario.objects.select_for_update().get(pk=previo.funcionario_id)
    a=Actividad.objects.select_for_update().get(pk=previo.pk)
    if a.estado_revision!='CORRECCION' or a.version_revision!=version:raise ErrorRevision('La actividad no está disponible para corrección. Actualice.',409)
    servicio=(datos.get('servicio') or '').strip();contacto=(datos.get('contacto') or '').strip()
    if not 5<=len(servicio)<=200 or not 3<=len(contacto)<=150:raise ErrorRevision('Revise el servicio (5-200 caracteres) y contacto (3-150).')
    archivo=archivos.get('evidencia')
    if archivo:
        try:validar_archivo(archivo)
        except ValueError as error:raise ErrorRevision(str(error)) from error
    a.servicio=servicio;a.contacto=contacto
    if archivo:a.evidencia_archivo=archivo;a.imagen_verificadora=f"Archivo {archivo.name.rsplit('.',1)[-1].upper() if '.' in archivo.name else 'adjunto'} adjunto"
    a.estado_revision='PENDIENTE';a.version_revision+=1
    a.save()
    RevisionActividad.objects.create(actividad=a,autor=perfil.user,estado_anterior='CORRECCION',estado_nuevo='PENDIENTE',comentario='Funcionario envía corrección; fecha e ítem originales conservados.',version=a.version_revision)
    return a
