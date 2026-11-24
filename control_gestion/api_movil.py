"""API v1, autenticación Bearer exclusiva; nunca usa cookies como credencial."""
import hashlib,json,secrets,uuid
from datetime import timedelta
from functools import wraps
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse,FileResponse
from django.core.exceptions import RequestDataTooBig,ValidationError
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.crypto import salted_hmac
from cuentas.models import Usuario,EstadoRegistro
from cuentas.servicios import autenticar,sesion_desde_usuario
from cuentas.auth import puede_ver
from control_gestion.models import Actividad,Compromiso,ItemFuncionario,SesionMovil,IntentosMovil,EnvioMovil,CambioCompromiso
from control_gestion.consultas import registrar_actividad_desde_formulario
from control_gestion.evidencias import puede_validar
from control_gestion.revision import alcance,revisar,corregir,ErrorRevision
from core.busqueda import buscar
from core.seguridad import ip_cliente

def respuesta(data,status=200):
    r=JsonResponse(data,safe=not isinstance(data,list),status=status)
    r['Cache-Control']='no-store';r['X-Content-Type-Options']='nosniff'
    return r

DIAS_TOKEN = int(getattr(settings, 'SIGED_TOKEN_MOVIL_DIAS', 30))
LIMITE_PETICIONES = 300  # por sesión cada 5 minutos


def _limite_peticiones(sesion):
    """Freno básico por sesión (caché local del proceso): evita que un cliente roto sature el servidor."""
    from django.core.cache import cache
    clave = f'siged:api:{sesion.pk}:{int(timezone.now().timestamp() // 300)}'
    try:
        total = cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, 310)
        total = 1
    return total > LIMITE_PETICIONES


def datos(request):
    if request.content_type=='application/json':
        try:
            d=json.loads(request.body)
            if not isinstance(d,dict):raise ValueError()
            return d
        except (ValueError,UnicodeDecodeError):raise ErrorRevision('JSON inválido.')
    return request.POST

def api(methods,modulo='actividades',publica=False):
    def decorate(fn):
        @csrf_exempt
        @wraps(fn)
        def wrap(request,*args,**kwargs):
            try:
                if request.method not in methods:return respuesta({'error':'Método no permitido.'},405)
                if not request.is_secure() and not settings.DEBUG:return respuesta({'error':'Use una conexión HTTPS.'},400)
                if not publica:
                    header=request.headers.get('Authorization','')
                    if not header.startswith('Bearer ') or len(header)>200:return respuesta({'error':'Inicie sesión nuevamente.'},401)
                    digest=hashlib.sha256(header[7:].encode()).hexdigest()
                    sesion=SesionMovil.objects.select_related('usuario__user','usuario__rol','usuario__cargo','usuario__delegacion','usuario__funcionario__cargo').filter(huella=digest,expira__gt=timezone.now()).first()
                    if not sesion:return respuesta({'error':'La sesión terminó. Ingrese nuevamente.'},401)
                    p=sesion.usuario
                    if p.estado!=EstadoRegistro.ACTIVO or not p.user_id or not p.user.is_active or sesion.clave_version!=hashlib.sha256(p.user.password.encode()).hexdigest():return respuesta({'error':'La cuenta o sesión no está disponible.'},401)
                    if not puede_ver(p,modulo):return respuesta({'error':'Su perfil no permite esta operación.'},403)
                    if _limite_peticiones(sesion):return respuesta({'error':'Demasiadas solicitudes. Espere unos minutos.'},429)
                    ahora=timezone.now()
                    if not sesion.ultimo_uso or ahora-sesion.ultimo_uso>timedelta(minutes=5):
                        SesionMovil.objects.filter(pk=sesion.pk).update(ultimo_uso=ahora)
                    request.perfil_movil=p;request.sesion_movil=sesion;request.user=p.user;request._perfil_siged=p
                return fn(request,*args,**kwargs)
            except ErrorRevision as e:return respuesta({'error':str(e)},e.status)
            except RequestDataTooBig:
                return respuesta({'error':'El envío supera el tamaño permitido. Divida la sincronización en partes.'},413)
            except ValidationError as e:
                campos=getattr(e,'message_dict',None) or {'__all__':e.messages}
                return respuesta({'error':'Hay datos inválidos.','campos':campos},422)
            except Exception:
                # Nunca HTML en la API: el teléfono necesita JSON para mostrar el error.
                import logging
                logging.getLogger('siged.api').exception('api_error %s %s', request.method, request.path)
                return respuesta({'error':'Ocurrió un error inesperado en el servidor. Intente nuevamente.'},500)
        return wrap
    return decorate

def perfil_json(p):
    return {'id':p.pk,'nombre':p.nombre_mostrado,'rut':p.funcionario.rut if p.funcionario_id else p.username,'funcionario':p.funcionario.codigo if p.funcionario_id else '',
        'delegacion':p.delegacion.nombre if p.delegacion_id else '', 'rol':p.rol.codigo,'puede_revisar':puede_validar(p)}

@api(['POST'],publica=True)
def login(request):
    d=datos(request);rut=str(d.get('rut',''))[:32];password=str(d.get('password',''))[:256]
    # X-Forwarded-For solo cuenta si llega desde el proxy declarado (SIGED_PROXY_CONFIABLE). Cuota por IP y cuenta normalizada.
    ip_key=salted_hmac('login-movil-ip',ip_cliente(request)).hexdigest()
    account_key=salted_hmac('login-movil-cuenta',''.join(c for c in rut.upper() if c.isalnum())).hexdigest()
    quotas={ip_key:120,account_key:8}
    ahora=timezone.now()
    with transaction.atomic():
        for key in sorted(quotas):
            IntentosMovil.objects.get_or_create(clave=key,defaults={'inicio':ahora})
            b=IntentosMovil.objects.select_for_update().get(clave=key)
            if ahora-b.inicio>timedelta(minutes=15):b.inicio=ahora;b.intentos=0
            if b.intentos>=quotas[key]:raise ErrorRevision('Espere quince minutos antes de volver a intentar.',429)
            b.intentos+=1;b.save()
    p=autenticar(rut,password)
    if not p:return respuesta({'error':'RUT o contraseña incorrectos. Si es su primer ingreso, active su cuenta desde el enlace del correo.','activacion':'/login/'},401)
    if not p.funcionario_id or not puede_ver(p,'actividades'):return respuesta({'error':'Esta cuenta no tiene acceso móvil de funcionario.'},403)
    IntentosMovil.objects.filter(clave=account_key).delete()
    # Token de dispositivo: dura DIAS_TOKEN y se renueva con sesion/renovar/ sin volver a pedir la clave.
    # Cambiar la contraseña o desactivar la cuenta lo invalida igual (clave_version).
    token=secrets.token_urlsafe(48);expira=ahora+timedelta(days=DIAS_TOKEN)
    SesionMovil.objects.filter(usuario=p,expira__lte=ahora).delete()
    dispositivo=' '.join(str(d.get('dispositivo') or request.headers.get('User-Agent',''))[:120].split()) or None
    SesionMovil.objects.create(usuario=p,huella=hashlib.sha256(token.encode()).hexdigest(),expira=expira,
        clave_version=hashlib.sha256(p.user.password.encode()).hexdigest(),dispositivo=dispositivo,creado=ahora,ultimo_uso=ahora)
    return respuesta({'token':token,'expira':expira,'perfil':perfil_json(p)})

@api(['POST'])
def renovar(request):
    """Entrega un token nuevo y anula el anterior (rotación); conserva el dispositivo."""
    anterior=request.sesion_movil;ahora=timezone.now()
    token=secrets.token_urlsafe(48);expira=ahora+timedelta(days=DIAS_TOKEN)
    with transaction.atomic():
        SesionMovil.objects.create(usuario=anterior.usuario,huella=hashlib.sha256(token.encode()).hexdigest(),expira=expira,
            clave_version=anterior.clave_version,dispositivo=anterior.dispositivo,creado=anterior.creado or ahora,ultimo_uso=ahora)
        anterior.delete()
    return respuesta({'token':token,'expira':expira})

@api(['POST'])
def logout(request):
    request.sesion_movil.delete();return respuesta({'ok':True})

@api(['GET'])
def panel(request):
    from control_gestion.panel_personal import construir_panel_personal
    p=request.perfil_movil;personal=construir_panel_personal(p)
    items=ItemFuncionario.objects.filter(funcionario_id=p.funcionario_id).select_related('meta')
    return respuesta({'perfil':perfil_json(p),'semaforo':personal['semaforo'],'metas':[{'codigo':i.meta.codigo,'nombre':i.meta.nombre,'meta':i.meta_trimestre,'avance':i.avance_actual,'ponderador':i.ponderador,'cumplimiento':i.porcentaje_avance} for i in items],
        'compromisos':Compromiso.objects.filter(funcionario_id=p.funcionario_id).count(),'pendientes_revision':alcance(Actividad.objects.filter(estado_revision='PENDIENTE'),p).exclude(funcionario_id=p.funcionario_id).count() if puede_validar(p) else 0})

def actividad_json(a):
    return {'codigo':a.codigo,'fecha':a.fecha_actividad,'servicio':a.servicio,'contacto':a.contacto,'meta':a.meta.nombre,'meta_codigo':a.meta.codigo,'funcionario':a.funcionario.nombre_mostrado,'funcionario_codigo':a.funcionario.codigo,
        'tipo':a.tipo_registro,'estado':a.estado_revision,'version':a.version_revision,'validada':a.punto_validado,'verificador':a.codigo_verificador,
        'evidencia':f'/api/v1/actividades/{a.codigo}/evidencia/' if a.evidencia_archivo else '',
        'historial':[{'estado':r.estado_nuevo,'comentario':r.comentario,'fecha':r.fecha,'autor':r.autor.get_full_name() or 'Verificador','version':r.version} for r in a.revisiones.select_related('autor').all()]}

def paginado(request,qs,serialize):
    try:size=int(request.GET.get('per_page','10'))
    except ValueError:size=10
    if size not in (10,20,50,100):size=10
    page=Paginator(qs,size).get_page(request.GET.get('page'))
    return respuesta({'total':page.paginator.count,'pagina':page.number,'paginas':page.paginator.num_pages,'resultados':[serialize(a) for a in page]})

@api(['GET','POST'])
def actividades(request):
    p=request.perfil_movil
    if request.method=='GET':
        equipo=request.GET.get('equipo')=='1'
        if equipo and not puede_validar(p):raise ErrorRevision('Sin permiso de revisión.',403)
        qs=alcance(Actividad.objects.select_related('funcionario','meta').prefetch_related('revisiones__autor'),p,propio=not equipo)
        if request.GET.get('estado'):qs=qs.filter(estado_revision=request.GET['estado'])
        qs=buscar(qs,request.GET.get('q',''),['codigo','servicio','contacto','funcionario__nombre','funcionario__rut'])
        return paginado(request,qs,actividad_json)
    d=datos(request)
    try:client_id=uuid.UUID(str(d.get('client_id','')))
    except ValueError:raise ErrorRevision('Falta el identificador del borrador.')
    meta=ItemFuncionario.objects.select_related('meta').filter(funcionario_id=p.funcionario_id,meta__codigo=d.get('meta')).first()
    if not meta:raise ErrorRevision('Seleccione uno de sus ítems asignados.')
    post={k:str(d.get(k,'')) for k in ('contacto','servicio','fecha_actividad','tipo_registro')};post['item']=meta.meta.nombre
    payload=json.dumps(post,sort_keys=True,ensure_ascii=False).encode();archivo=request.FILES.get('evidencia')
    h=hashlib.sha256(payload)
    if archivo:
        for chunk in archivo.chunks():h.update(chunk)
        archivo.seek(0)
    digest=h.hexdigest()
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=p.user_id)
        previo=EnvioMovil.objects.filter(usuario=p.user,client_id=client_id).select_related('actividad__meta','actividad__funcionario').first()
        if previo:
            if previo.huella!=digest:raise ErrorRevision('El borrador ya se envió con otros datos.',409)
            return respuesta({'actividad':actividad_json(previo.actividad),'repetido':True})
        registro,errores=registrar_actividad_desde_formulario(p.funcionario.codigo,post,request.FILES,autor=p.user)
        if errores:return respuesta({'error':'Revise los datos indicados.','campos':errores},422)
        a=Actividad.objects.get(codigo=registro['id_actividad'])
        EnvioMovil.objects.create(usuario=p.user,client_id=client_id,huella=digest,actividad=a)
    return respuesta({'actividad':actividad_json(a),'repetido':False},201)

@api(['GET','POST'])
def detalle_actividad(request,codigo):
    p=request.perfil_movil
    if request.method=='POST':
        d=datos(request)
        try:version=int(d.get('version',-1))
        except (ValueError,TypeError):raise ErrorRevision('Versión inválida.')
        a=corregir(p,codigo,d,request.FILES,version)
    else:
        a=alcance(Actividad.objects.select_related('meta','funcionario'),p,propio=not puede_validar(p)).filter(codigo=codigo).first()
        if not a:raise ErrorRevision('Actividad no encontrada.',404)
    return respuesta(actividad_json(a))

@api(['POST'])
def revision(request,codigo):
    d=datos(request)
    try:version=int(d.get('version',-1))
    except (ValueError,TypeError):raise ErrorRevision('Versión inválida.')
    return respuesta(actividad_json(revisar(request.perfil_movil,codigo,str(d.get('decision','')),str(d.get('comentario','')),version)))

@api(['GET'])
def evidencia(request,codigo):
    p=request.perfil_movil;a=alcance(Actividad.objects.all(),p,propio=not puede_validar(p)).filter(codigo=codigo).first()
    if not a or not a.evidencia_archivo:raise ErrorRevision('Archivo no encontrado.',404)
    try:f=a.evidencia_archivo.open('rb')
    except FileNotFoundError:raise ErrorRevision('El archivo original no está disponible.',404)
    r=FileResponse(f,as_attachment=True,filename=Path(a.evidencia_archivo.name).name)
    r['Cache-Control']='no-store';r['X-Content-Type-Options']='nosniff';return r

def compromiso_json(c):
    return {'codigo':c.codigo,'descripcion':c.descripcion,'solicitante':c.vecino.nombre_mostrado,'responsable':c.funcionario.nombre_mostrado,'fecha':c.fecha_compromiso,'estado':c.estado,'observaciones':c.observaciones,'territorio':c.territorio,'apoyo':c.apoyo}

@api(['GET'],modulo='compromisos')
def compromisos(request):
    p=request.perfil_movil;equipo=request.GET.get('equipo')=='1'
    if equipo and not puede_validar(p):raise ErrorRevision('Sin permiso de consulta de equipo.',403)
    qs=alcance(Compromiso.objects.select_related('vecino','funcionario'),p,propio=not equipo)
    qs=buscar(qs,request.GET.get('q',''),['codigo','descripcion','vecino__nombre','funcionario__nombre'])
    if request.GET.get('estado'):qs=qs.filter(estado=request.GET['estado'])
    return paginado(request,qs,compromiso_json)

@api(['POST'],modulo='compromisos')
def cambiar_compromiso(request,codigo):
    p=request.perfil_movil;d=datos(request);nuevo=d.get('estado');anterior=d.get('estado_anterior');obs=str(d.get('observaciones','')).strip()
    if nuevo not in Compromiso.Estado.values or len(obs)>5000:raise ErrorRevision('Estado u observaciones inválidos.')
    with transaction.atomic():
        c=alcance(Compromiso.objects.select_for_update(),p,propio=not puede_validar(p)).filter(codigo=codigo).first()
        if not c:raise ErrorRevision('Compromiso no encontrado.',404)
        # Comparar estado y texto para impedir sobrescritura de otra edición.
        if c.estado!=anterior or c.observaciones!=str(d.get('observaciones_anteriores','')):raise ErrorRevision('El compromiso cambió. Actualice y revise sus datos.',409)
        CambioCompromiso.objects.create(compromiso=c,autor=p.user,estado_anterior=c.estado,estado_nuevo=nuevo,observacion_anterior=c.observaciones,observacion_nueva=obs)
        c.estado=nuevo;c.observaciones=obs;c.save(update_fields=['estado','observaciones'])
    return respuesta(compromiso_json(c))

@api(['GET'],modulo='compromisos')
def excel(request):
    from control_gestion.reportes import exportar_tubo
    # Exportación móvil siempre propia, incluso cuando un delegado revisa su equipo.
    request._exportacion_movil_propia=True
    return exportar_tubo(request)
