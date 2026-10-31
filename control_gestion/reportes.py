"""Datos comunes del tubo y exportación del trabajo ya registrado."""
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from control_gestion.kanban import perfil_actual
from cuentas.auth import puede_ver
from cuentas.models import Usuario
from cuentas.servicios import obtener_parametros
from core.busqueda import buscar
from core.excel import descargar
from control_gestion.consultas import queryset_compromisos,queryset_actividades
from control_gestion.models import ItemFuncionario

def perfil_acceso(request,modulo):
    perfil=perfil_actual(request)
    if perfil is None: return None,redirect('login')
    if not puede_ver(perfil,modulo):
        return None,HttpResponseForbidden('Su perfil no tiene acceso a este módulo.')
    return perfil,None

def ambito(qs,perfil):
    if perfil.rol.codigo=='administrador': return qs
    return qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()

def tubo_filtrado(request,perfil,filtrar=True):
    qs=ambito(queryset_compromisos(),perfil)
    if not filtrar: return qs
    if request.GET.get('delegacion'): qs=qs.filter(delegacion__nombre=request.GET['delegacion'])
    if request.GET.get('estado'): qs=qs.filter(estado=request.GET['estado'].upper())
    return buscar(qs,request.GET.get('q',''),['codigo','descripcion','estado','vecino__nombre','vecino__rut',
        'funcionario__nombre','funcionario__rut','funcionario__codigo','funcionario__cargo__nombre','delegacion__nombre'])

def usuarios_filtrados(request):
    qs=Usuario.objects.select_related('rol','cargo','delegacion','funcionario').order_by('nombre','codigo')
    return buscar(qs,request.GET.get('q',''),['codigo','username','nombre','correo','rol__nombre',
        'rol__codigo','cargo__nombre','delegacion__nombre','funcionario__rut','estado'])

@never_cache
def exportar_usuarios(request):
    perfil,error=perfil_acceso(request,'administracion')
    if error is not None: return error
    rows=[]
    for u in usuarios_filtrados(request):
        rows.append([u.pk,u.codigo,u.funcionario.codigo,u.funcionario.rut,u.username,u.nombre,u.correo,u.rol.nombre,
            u.cargo.codigo if u.cargo else '',u.cargo.nombre if u.cargo else '',
            u.delegacion.nombre if u.delegacion else '',u.get_estado_display(),timezone.localtime(u.creado)])
    return descargar('usuarios-'+timezone.localdate().isoformat(),[('Usuarios',
        ['ID interno','Código usuario','Código funcionario','RUT','Usuario de acceso','Nombre','Correo','Rol','Código cargo','Cargo','Delegación','Estado','Fecha de creación'],rows)])

@never_cache
def exportar_tubo(request):
    perfil,error=perfil_acceso(request,'compromisos')
    if error is not None: return error
    compromisos=list(tubo_filtrado(request,perfil))
    meta=float(obtener_parametros()['meta_tubo_porcentaje'])
    total=len(compromisos)
    realizados=sum(c.estado=='REALIZADO' for c in compromisos)
    porcentaje=round(realizados*100/total,2) if total else 0
    resumen=[['Generado',timezone.localtime().isoformat()],['Búsqueda',request.GET.get('q','')],
        ['Delegación',request.GET.get('delegacion','') or (perfil.delegacion.nombre if perfil.rol.codigo!='administrador' and perfil.delegacion else 'Todas las autorizadas')],
        ['Estado',request.GET.get('estado','') or 'Todos'],['Total compromisos',total],['Realizados',realizados],
        ['Por realizar',total-realizados],['Realizado (%)',porcentaje],['Meta (%)',meta],['Cumple meta',bool(total and porcentaje>=meta)],
        ['Alcance de actividades y metas','Funcionarios de los compromisos seleccionados, en las delegaciones autorizadas. Sin relación directa entre actividad y compromiso.']]
    for estado in ('INGRESADO','PENDIENTE','EN PROCESO','REALIZADO'):
        resumen.append([estado,sum(c.estado==estado for c in compromisos)])
    detalle=[]
    grupos_fun={}
    grupos_del={}
    for c in compromisos:
        detalle.append([c.codigo,c.descripcion,c.vecino.rut or '',c.vecino.nombre_mostrado,
            c.funcionario.codigo,c.funcionario.rut,c.funcionario.nombre_mostrado,
            c.funcionario.cargo.nombre if c.funcionario.cargo_id else '',c.delegacion.nombre,
            c.fecha_ingreso,c.fecha_compromiso,c.estado,c.estado!='REALIZADO' and c.fecha_compromiso<timezone.localdate()])
        for groups,key,label in ((grupos_fun,c.funcionario_id,c.funcionario.nombre_mostrado),
                                  (grupos_del,c.delegacion_id,c.delegacion.nombre)):
            values=groups.setdefault(key,[label,0,0])
            values[1]+=1
            values[2]+=c.estado=='REALIZADO'
    def consolidar(groups):
        rows=[]
        for name,n,r in groups.values():
            pct=round(r*100/n,2) if n else 0
            rows.append([name,n,r,n-r,pct,meta,pct>=meta])
        return rows
    responsables={c.funcionario_id for c in compromisos}
    delegaciones={c.delegacion_id for c in compromisos}
    actividades=ambito(queryset_actividades(),perfil).filter(funcionario_id__in=responsables,delegacion_id__in=delegaciones)
    actividades_rows=[[a.codigo,a.fecha_actividad,a.funcionario.codigo,a.funcionario.nombre_mostrado,
        a.delegacion.nombre,a.meta.codigo,a.meta.nombre,a.servicio,a.contacto,a.codigo_verificador,
        a.imagen_verificadora,a.punto_validado] for a in actividades]
    items=ItemFuncionario.objects.select_related('funcionario__delegacion','meta').filter(
        funcionario_id__in=responsables,funcionario__delegacion_id__in=delegaciones)
    metas=[]
    for i in items:
        pct=i.porcentaje_avance
        metas.append([i.codigo,i.funcionario.codigo,i.funcionario.nombre_mostrado,i.funcionario.delegacion.nombre,
            i.meta.codigo,i.meta.nombre,i.ponderador,i.meta_trimestre,i.avance_actual,pct,round(pct*i.ponderador/100,2)])
    return descargar('tubo-trabajo-'+timezone.localdate().isoformat(),[
        ('Resumen',['Indicador','Valor'],resumen),
        ('Tubo de trabajo',['Código','Compromiso','RUT vecino','Vecino','Código funcionario','RUT funcionario',
            'Funcionario','Cargo','Delegación','Fecha ingreso','Fecha compromiso','Estado','Vencido'],detalle),
        ('Por funcionario',['Funcionario','Total','Realizados','Por realizar','Realizado (%)','Meta (%)','Cumple meta'],consolidar(grupos_fun)),
        ('Por delegación',['Delegación','Total','Realizados','Por realizar','Realizado (%)','Meta (%)','Cumple meta'],consolidar(grupos_del)),
        ('Actividades',['Código','Fecha','Código funcionario','Funcionario','Delegación','Código meta','Meta',
            'Servicio','Contacto','Código evidencia','Evidencia','Validada'],actividades_rows),
        ('Metas',['Código asignación','Código funcionario','Funcionario','Delegación','Código meta','Meta',
            'Ponderador (%)','Meta trimestre','Avance','Cumplimiento (%)','Puntaje ponderado'],metas),
    ])
