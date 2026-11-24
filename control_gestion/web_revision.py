from django.contrib import messages
from django.shortcuts import get_object_or_404,render,redirect
from django.views.decorators.http import require_http_methods
from control_gestion.models import Actividad
from control_gestion.reportes import perfil_acceso
from control_gestion.evidencias import puede_validar
from control_gestion.revision import alcance,revisar,corregir,ErrorRevision

@require_http_methods(['GET','POST'])
def revision_web(request,codigo):
    p,error=perfil_acceso(request,'actividades')
    if error is not None:return error
    a=get_object_or_404(alcance(Actividad.objects.select_related('funcionario','meta'),p,propio=not puede_validar(p)),codigo=codigo)
    propio=a.funcionario_id==p.funcionario_id
    if request.method=='POST':
        try:
            version=int(request.POST.get('version','-1'))
            if request.POST.get('accion')=='corregir':corregir(p,codigo,request.POST,request.FILES,version)
            else:revisar(p,codigo,request.POST.get('decision',''),request.POST.get('comentario',''),version)
            messages.success(request,'Se guardó el cambio y quedó en el historial.')
            return redirect('actividad_revision',codigo=codigo)
        except ValueError as e:messages.error(request,str(e) if isinstance(e,ErrorRevision) else 'No se guardó el cambio. Revise los datos y el archivo.')
    return render(request,'control_gestion/revision_actividad.html',{'actividad':a,'historial':a.revisiones.select_related('autor').all(),
        'puede_revisar':puede_validar(p) and not propio and a.estado_revision=='PENDIENTE','puede_corregir':propio and a.estado_revision=='CORRECCION'})
