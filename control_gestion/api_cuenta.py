"""API v1 para la app móvil del funcionario: recuperar contraseña con código, «mi trabajo» y evidencias.

Recuperación en dos pasos (igual que la web):
1. ``POST recuperar/ {correo}``: si el correo es de una cuenta activa, llega un código de 6 dígitos (10 min).
   La respuesta es siempre la misma, exista o no la cuenta (Ley 19.628: no confirmar titulares).
2. ``POST recuperar/verificar/ {correo, codigo}``: si el código es correcto, entrega un permiso de un solo uso.
3. ``POST recuperar/nueva/ {permiso, password, confirmacion}``: define la contraseña. Cambiarla cierra todas
   las sesiones móviles abiertas (el token guarda la huella de la clave anterior).
"""
import re
from datetime import timedelta
from pathlib import PurePosixPath

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse
from django.utils import timezone

from control_gestion.api_movil import api, datos, respuesta
from control_gestion.evidencias import validar_archivo
from control_gestion.models import Actividad, Compromiso, EvidenciaCompromiso
from control_gestion.revision import ErrorRevision
from cuentas.models import EstadoRegistro, Usuario
from cuentas.recuperacion import emitir_codigo, enviar_codigo, verificar_codigo
from cuentas.servicios import errores_clave

SAL_PERMISO = 'siged-recuperar-movil'
ESTADOS_APP = ('INGRESADO', 'PENDIENTE', 'EN PROCESO', 'REALIZADO', 'VENCIDO')
MENSAJE_ENVIO = ('Si el correo corresponde a una cuenta activa, enviamos un código de 6 dígitos. '
                 'Vence en 10 minutos y sirve una sola vez.')


def _correo(d):
    correo = str(d.get('correo', '')).strip()[:254]
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', correo):
        raise ErrorRevision('Ingrese un correo electrónico válido.', 422)
    return correo


def _cuota(request, correo):
    from core.seguridad import LimiteExcedido, clave_limite, consumir, ip_cliente
    try:
        consumir({
            clave_limite('recuperar-ip', ip_cliente(request)): settings.SIGED_LIMITE_RECUPERAR_IP,
            clave_limite('recuperar-correo', correo.lower()): settings.SIGED_LIMITE_RECUPERAR_CORREO,
        })
    except LimiteExcedido:
        raise ErrorRevision('Demasiadas solicitudes. Espere unos minutos antes de pedir otro código.', 429)


def _cuenta(correo):
    return Usuario.objects.select_related('user').filter(
        correo__iexact=correo, estado=EstadoRegistro.ACTIVO, user__isnull=False, user__is_active=True).first()


@api(['POST'], publica=True)
def recuperar(request):
    correo = _correo(datos(request))
    _cuota(request, correo)
    usuario = _cuenta(correo)
    if usuario is not None:
        try:
            with transaction.atomic():
                codigo = emitir_codigo(usuario, ip=(request.META.get('REMOTE_ADDR') or '')[:45])
                enviar_codigo(usuario, codigo)
        except (OSError, RuntimeError):
            return respuesta({'error': 'No se pudo enviar el correo. Inténtelo más tarde.'}, 503)
    return respuesta({'ok': True, 'mensaje': MENSAJE_ENVIO, 'vigencia_minutos': 10})


@api(['POST'], publica=True)
def verificar(request):
    d = datos(request)
    correo = _correo(d)
    codigo = str(d.get('codigo', '')).strip()
    if not re.fullmatch(r'\d{6}', codigo):
        return respuesta({'error': 'Ingrese los 6 dígitos del código.', 'campos': {'codigo': ['Seis dígitos.']}}, 422)
    usuario = _cuenta(correo)
    resultado = verificar_codigo(usuario, codigo) if usuario else 'invalido'
    mensajes = {'agotado': 'Demasiados intentos. Solicite un código nuevo.',
                'expirado': 'El código expiró. Solicite uno nuevo.',
                'ausente': 'Ese código ya no es válido. Solicite uno nuevo.',
                'invalido': 'El código no coincide. Revíselo e intente de nuevo.'}
    if resultado != 'ok':
        return respuesta({'error': mensajes[resultado], 'motivo': resultado}, 422)
    permiso = signing.dumps({'u': usuario.pk, 'c': usuario.user.password[-12:]}, salt=SAL_PERMISO)
    return respuesta({'ok': True, 'permiso': permiso, 'vigencia_minutos': 10})


@api(['POST'], publica=True)
def nueva_clave(request):
    d = datos(request)
    try:
        carga = signing.loads(str(d.get('permiso', '')), salt=SAL_PERMISO, max_age=600)
        usuario = Usuario.objects.select_related('user').get(pk=carga['u'], estado=EstadoRegistro.ACTIVO)
        if usuario.user.password[-12:] != carga['c']:
            raise ValueError  # el permiso ya se usó: la clave cambió
    except (signing.BadSignature, Usuario.DoesNotExist, KeyError, ValueError, TypeError):
        return respuesta({'error': 'El permiso venció o ya se usó. Solicite un código nuevo.'}, 401)
    password = str(d.get('password', ''))[:256]
    if password != str(d.get('confirmacion', ''))[:256]:
        return respuesta({'error': 'Las contraseñas no coinciden.', 'campos': {'confirmacion': ['No coincide.']}}, 422)
    errores = list(errores_clave(password))
    try:
        validate_password(password, user=usuario.user)
    except ValidationError as e:
        errores += [m for m in e.messages if m not in errores]
    if errores:
        return respuesta({'error': 'La contraseña no cumple los requisitos.', 'campos': {'password': errores}}, 422)
    usuario.user.set_password(password)
    usuario.user.save(update_fields=['password'])
    return respuesta({'ok': True, 'mensaje': 'Contraseña actualizada. Ya puede ingresar con su RUT.'})


# ---------------------------------------------------------------- mi trabajo
def _estado_app(c, hoy):
    if c.estado != 'REALIZADO' and c.fecha_compromiso and c.fecha_compromiso < hoy:
        return 'VENCIDO'
    return c.estado


def _evidencia_json(e):
    fecha = timezone.localtime(e.fecha).strftime('%d/%m/%Y %H:%M')
    nombre = e.descripcion or f"{'Documento' if e.tipo == 'DOCUMENTO' else 'Foto'} del {fecha}"
    return {'id': e.pk, 'tipo': e.tipo, 'nombre': nombre,
            'fecha': e.fecha.isoformat(), 'url': f'/api/v1/evidencias/{e.pk}/'}


def compromiso_app_json(c, hoy):
    return {'codigo': c.codigo, 'descripcion': c.descripcion, 'solicitante': c.vecino.nombre_mostrado,
            'fecha_compromiso': c.fecha_compromiso.isoformat() if c.fecha_compromiso else None,
            'estado': _estado_app(c, hoy), 'estado_registrado': c.estado, 'observaciones': c.observaciones,
            'territorio': c.territorio, 'evidencias': [_evidencia_json(e) for e in c.evidencias.all()]}


def _asistencia(funcionario_id, inicio, hoy):
    """Días hábiles (lunes a viernes) del trimestre con al menos una actividad registrada."""
    fechas = set(Actividad.objects.filter(funcionario_id=funcionario_id, fecha_actividad__range=(inicio, hoy))
                 .values_list('fecha_actividad', flat=True))
    habiles = [inicio + timedelta(days=i) for i in range((hoy - inicio).days + 1)]
    habiles = [d for d in habiles if d.weekday() < 5]
    con_registro = sum(1 for d in habiles if d in fechas)
    return {'dias_habiles': len(habiles), 'dias_con_registro': con_registro,
            'porcentaje': round(con_registro * 100 / len(habiles)) if habiles else 0,
            'registro_hoy': hoy in fechas,
            'ultima_actividad': max(fechas).isoformat() if fechas else None}


@api(['GET'], modulo='compromisos')
def mi_trabajo(request):
    from control_gestion.api_sincronizacion import usuario_json
    from control_gestion.trimestres import resumen_trimestre_vigente, trimestre_actual
    p = request.perfil_movil
    hoy = timezone.localdate()
    periodo = trimestre_actual(hoy)
    inicio = periodo['fecha_inicio']
    compromisos = (Compromiso.objects.select_related('vecino').prefetch_related('evidencias')
                   .filter(funcionario_id=p.funcionario_id).order_by('fecha_compromiso', 'codigo'))
    filas = [compromiso_app_json(c, hoy) for c in compromisos]
    conteo = {estado: sum(1 for f in filas if f['estado'] == estado) for estado in ESTADOS_APP}
    return respuesta({
        'perfil': {**usuario_json(p), 'rut': p.funcionario.rut if p.funcionario_id else '',
                   'cargo': p.funcionario.cargo.nombre if p.funcionario_id and p.funcionario.cargo_id else ''},
        'trimestre': resumen_trimestre_vigente(hoy),
        'asistencia': _asistencia(p.funcionario_id, inicio, hoy) if p.funcionario_id else None,
        'conteo': conteo,
        'compromisos': filas,
        'servidor_ahora': timezone.now().isoformat(),
    })


@api(['POST'], modulo='compromisos')
def subir_evidencia(request, codigo):
    p = request.perfil_movil
    compromiso = Compromiso.objects.filter(codigo=codigo, funcionario_id=p.funcionario_id).first()
    if compromiso is None:
        return respuesta({'error': 'El compromiso no existe o no está asignado a usted.'}, 404)
    archivo = request.FILES.get('archivo')
    if archivo is None:
        return respuesta({'error': 'Adjunte una foto o un documento.', 'campos': {'archivo': ['Obligatorio.']}}, 422)
    try:
        validar_archivo(archivo)
    except ValueError as motivo:
        return respuesta({'error': str(motivo), 'campos': {'archivo': [str(motivo)]}}, 422)
    if compromiso.evidencias.count() >= 10:
        return respuesta({'error': 'Este compromiso ya tiene 10 evidencias.'}, 422)
    tipo = 'DOCUMENTO' if archivo.name.lower().endswith('.pdf') else 'FOTO'
    descripcion = ' '.join(str(request.POST.get('descripcion', '')).split())[:200]
    evidencia = EvidenciaCompromiso.objects.create(compromiso=compromiso, archivo=archivo, tipo=tipo,
                                                   descripcion=descripcion, subido_por=request.user)
    return respuesta({'evidencia': _evidencia_json(evidencia)}, 201)


@api(['GET'], modulo='compromisos')
def ver_evidencia_compromiso(request, pk):
    from control_gestion.reportes import ambito
    p = request.perfil_movil
    e = EvidenciaCompromiso.objects.select_related('compromiso').filter(pk=pk).first()
    visible = e is not None and (e.compromiso.funcionario_id == p.funcionario_id
                                 or ambito(Compromiso.objects.filter(pk=e.compromiso_id), p).exists())
    if not visible:
        return respuesta({'error': 'Sin acceso a esa evidencia.'}, 404)
    pdf = e.archivo.name.lower().endswith('.pdf')
    r = FileResponse(e.archivo.open('rb'), content_type='application/pdf' if pdf else 'image/' +
                     ('png' if e.archivo.name.lower().endswith('.png') else 'jpeg'))
    r['X-Content-Type-Options'] = 'nosniff'
    r['Content-Security-Policy'] = "default-src 'none'; sandbox"
    r['Cache-Control'] = 'private, no-store'
    return r
