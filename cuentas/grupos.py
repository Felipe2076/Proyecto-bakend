"""Administración de grupos y asignaciones desde las pantallas municipales."""
from django import forms
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404,redirect,render
from cuentas.auth import requerir_modulo
from cuentas.forms import aplicar_bootstrap
from cuentas.models import Rol,Usuario
from cuentas.perfiles import MODULOS_BASE
from cuentas.simulacion import CODIGO_ADMIN_GLOBAL

class PermisosGrupoForm(forms.Form):
    permisos=forms.ModelMultipleChoiceField(queryset=Permission.objects.none(),required=False,
        widget=forms.CheckboxSelectMultiple,label='Permisos del grupo')

    def __init__(self,*args,rol,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['permisos'].queryset=Permission.objects.filter(content_type__app_label__in=(
            'cuentas','requerimientos','control_gestion')).exclude(content_type__model__in=(
                'codigounuso','secuenciacodigo')).select_related('content_type').order_by('content_type__app_label','content_type__model','codename')
        self.fields['permisos'].queryset=self.fields['permisos'].queryset.exclude(codename='acceso_administracion')
        from cuentas.mantenedores import MANTENEDORES
        self.fields['permisos'].queryset=self.fields['permisos'].queryset.filter(
            Q(codename__startswith='acceso_')|Q(content_type__model__in=[m.modelo._meta.model_name for m in MANTENEDORES]))
        self.fields['permisos'].label_from_instance=lambda p: self.etiqueta(p)

    @staticmethod
    def etiqueta(perm):
        accion,_,modelo=perm.codename.partition('_')
        if accion=='acceso':
            return perm.name
        verbo={'view':'Consultar','add':'Crear','change':'Modificar','delete':'Eliminar'}.get(accion,accion)
        return f'{verbo} · {perm.content_type.name}'

class AsignarGrupoForm(forms.Form):
    usuario=forms.ModelChoiceField(queryset=Usuario.objects.none(),label='Usuario')
    rol=forms.ModelChoiceField(queryset=Rol.objects.none(),label='Perfil y grupo')

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['usuario'].queryset=Usuario.objects.select_related('rol','funcionario').exclude(codigo=CODIGO_ADMIN_GLOBAL).order_by('nombre')
        self.fields['rol'].queryset=Rol.objects.select_related('grupo').order_by('nombre')
        aplicar_bootstrap(self)

def grupos_view(request,rol_id=None):
    bloqueo=requerir_modulo(request,'administracion')
    if bloqueo:
        return bloqueo
    # Los grupos y permisos afectan a todas las delegaciones: solo el superusuario.
    if request._perfil_siged.rol.codigo!='superusuario':
        messages.error(request,'Su perfil no puede administrar los grupos.')
        return redirect('inicio')
    rol=get_object_or_404(Rol.objects.select_related('grupo'),pk=rol_id) if rol_id else None
    asignacion=AsignarGrupoForm(request.POST if request.method=='POST' and request.POST.get('accion')=='asignar' else None)
    form=PermisosGrupoForm(request.POST if request.method=='POST' and request.POST.get('accion')=='permisos' else None,
        rol=rol,initial={'permisos':rol.grupo.permissions.all()} if rol and rol.grupo_id else None)
    if request.method=='POST':
        if request.POST.get('accion')=='asignar' and asignacion.is_valid():
            perfil=asignacion.cleaned_data['usuario']
            if perfil.pk==request._perfil_siged.pk:
                asignacion.add_error('usuario','Asigne los grupos a otra cuenta para conservar su acceso de superusuario.')
            else:
                with transaction.atomic():
                    perfil.rol=asignacion.cleaned_data['rol']
                    perfil.save(update_fields=['rol'])
                messages.success(request,'Grupo asignado. Los permisos se aplican en la siguiente petición del usuario.')
                return redirect('admin_grupos')
        elif request.POST.get('accion')=='permisos' and rol and rol.codigo!='superusuario' and form.is_valid():
            with transaction.atomic():
                rol.grupo.permissions.set(form.cleaned_data['permisos'])
            messages.success(request,'Permisos del grupo actualizados.')
            return redirect('admin_grupo',rol_id=rol.pk)
    return render(request,'cuentas/grupos.html',{'roles_grupos':Rol.objects.select_related('grupo').order_by('nombre'),
        'rol_grupo':rol,'form_permisos':form,'form_asignacion':asignacion,'seccion':'grupos'})
