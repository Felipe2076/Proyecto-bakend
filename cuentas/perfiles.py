"""Grupos de Django que respaldan los perfiles municipales existentes."""
from django.apps import apps
from django.db import transaction

MODULOS = {
    'requerimientos': 'Atención ciudadana y tickets',
    'matriz_sgr': 'Indicadores y metas',
    'control_gestion': 'Panel de gestión',
    'actividades': 'Actividad y evidencia',
    'agenda': 'Agenda colectiva',
    'compromisos': 'Compromisos ciudadanos',
    'notificaciones': 'Avisos',
    'encuestas': 'Encuestas',
    'administracion': 'Administración del sistema',
    'mantenedores': 'Mantenedores autorizados',
}
MODULOS_BASE = {
    'superusuario': set(MODULOS),
    'administrador': set(MODULOS),
    'jefatura': set(MODULOS) - {'administracion'},
    'funcionario': {'requerimientos','matriz_sgr','actividades','agenda','compromisos','notificaciones','encuestas'},
    'ventanilla': {'requerimientos','agenda','notificaciones','encuestas'},
}
APPS_NEGOCIO = {'cuentas','requerimientos','control_gestion'}
# Configuración que afecta a todas las delegaciones: solo el superusuario la crea, modifica o elimina.
MODELOS_GLOBALES = {'delegacion','rol','meta','tipoatencion','subatencion','tipogestion','medicion','cargo'}
CATALOGOS_SUPERVISOR = {'delegacion','meta','tipogestion','tipoatencion','subatencion'}
OPERACIONES_SUPERVISOR = {'vecino','atencion'}

def permisos_iniciales(codigo, registry=apps, using='default'):
    Permission = registry.get_model('auth','Permission')
    ContentType = registry.get_model('contenttypes','ContentType')
    permisos = []
    for model in registry.get_models():
        if model._meta.app_label not in APPS_NEGOCIO:
            continue
        ct,_ = ContentType.objects.using(using).get_or_create(
            app_label=model._meta.app_label,model=model._meta.model_name)
        for accion in ('view','add','change','delete'):
            perm,_ = Permission.objects.using(using).get_or_create(
                content_type=ct,codename=f'{accion}_{model._meta.model_name}',
                defaults={'name':f'Can {accion} {model._meta.verbose_name}'})
            if codigo=='superusuario' or (codigo=='administrador' and (accion=='view' or model._meta.model_name not in MODELOS_GLOBALES)) or (
                codigo=='jefatura' and (
                    (accion=='view' and model._meta.model_name in CATALOGOS_SUPERVISOR)
                    or (accion in ('view','add','change') and model._meta.model_name in OPERACIONES_SUPERVISOR)
                )
            ):
                permisos.append(perm.pk)
    ct,_ = ContentType.objects.using(using).get_or_create(app_label='cuentas',model='rol')
    for modulo,nombre in MODULOS.items():
        perm,_ = Permission.objects.using(using).get_or_create(
            content_type=ct,codename='acceso_'+modulo,defaults={'name':'Acceder a '+nombre})
        if modulo in MODULOS_BASE.get(codigo,set()):
            permisos.append(perm.pk)
    return permisos

def asegurar_grupo(rol, using=None):
    from django.contrib.auth.models import Group
    using=using or rol._state.db or 'default'
    if rol.grupo_id:
        return rol.grupo
    with transaction.atomic(using=using):
        grupo,creado=Group.objects.using(using).get_or_create(name='SIGED: '+rol.codigo)
        if creado:
            grupo.permissions.set(permisos_iniciales(rol.codigo,using=using))
        type(rol).objects.using(using).filter(pk=rol.pk,grupo__isnull=True).update(grupo=grupo)
        rol.grupo=grupo
    return grupo

def sincronizar_usuario(perfil):
    if not perfil.user_id:
        return
    from cuentas.models import Rol
    grupo=asegurar_grupo(perfil.rol,perfil._state.db)
    usuario=perfil.user
    gestionados=Rol.objects.exclude(grupo__isnull=True).values_list('grupo_id',flat=True)
    anteriores=list(usuario.groups.filter(pk__in=gestionados).exclude(pk=grupo.pk))
    if anteriores:
        usuario.groups.remove(*anteriores)
    usuario.groups.add(grupo)
    for nombre in ('_perm_cache','_group_perm_cache','_user_perm_cache'):
        usuario.__dict__.pop(nombre,None)

def preparar_perfiles(registry, schema_editor):
    """Población inicial, sin cambiar cuentas, claves, roles ni territorios."""
    using=schema_editor.connection.alias
    Rol=registry.get_model('cuentas','Rol')
    Group=registry.get_model('auth','Group')
    Usuario=registry.get_model('cuentas','Usuario')
    for rol in Rol.objects.using(using).all():
        grupo,creado=Group.objects.using(using).get_or_create(name='SIGED: '+rol.codigo)
        if creado:
            grupo.permissions.set(permisos_iniciales(rol.codigo,registry,using))
        rol.grupo_id=grupo.pk
        rol.save(using=using,update_fields=['grupo'])
        for perfil in Usuario.objects.using(using).filter(rol=rol).exclude(user__isnull=True):
            perfil.user.groups.add(grupo)
