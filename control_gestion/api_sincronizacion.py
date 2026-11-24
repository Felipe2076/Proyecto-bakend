"""API v1 para la app móvil: perfil, foto, usuarios, organizaciones, catálogos y sincronización.

Protocolo (detalle en docs/API_MOVIL.md):
- El teléfono guarda en SQLite lo que recibe, identificado por ``uuid``.
- ``GET sync/?desde=<servidor_ahora anterior>`` devuelve lo cambiado desde esa marca y las bajas.
- Altas: ``POST organizaciones/`` con ``client_id`` (UUID del teléfono): reintentar es seguro.
- Cambios: ``PATCH organizaciones/<codigo>/`` con ``version``; si otro cambió antes, 409 y la ficha vigente.
Todo queda acotado a la delegación del perfil (el superusuario ve todas).
"""
import hashlib
import json
import uuid as _uuid
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from control_gestion.api_movil import api, datos, perfil_json, respuesta
from control_gestion.models import (EnvioOrganizacionMovil, OrganizacionComunitaria, RegistroBaja, SesionMovil,
                                    TerritorioDelegacion)
from control_gestion.revision import ErrorRevision
from core.fechas import rut_formato
from cuentas.fotos import FotoInvalida, guardar_foto, puede_ver_foto, quitar_foto, respuesta_foto, url_foto
from cuentas.models import Delegacion, Usuario

LIMITE = 500
CAMPOS_ORG = ['nombre', 'tipo', 'telefono', 'correo', 'descripcion', 'domicilio_legal', 'delegacion', 'territorio',
              'presidente_nombre', 'presidente_rut', 'tesorero_nombre', 'tesorero_rut', 'secretario_nombre',
              'secretario_rut', 'vigencia_directiva_hasta', 'socios_activos', 'fecha_constitucion',
              'registro_personalidad_juridica', 'fecha_inscripcion', 'registro_directiva', 'verificada', 'activa']


def _iso(valor):
    return valor.isoformat() if valor else None


def _es_super(perfil):
    return perfil.rol.codigo == 'superusuario'


def _desde(request):
    texto = (request.GET.get('desde') or '').strip()
    if not texto:
        return None
    marca = parse_datetime(texto.replace(' ', '+'))
    if marca is None:
        raise ErrorRevision('El parámetro «desde» debe ser una fecha ISO 8601 (use servidor_ahora).', 400)
    return marca if timezone.is_aware(marca) else timezone.make_aware(marca)


def _cambiados(qs, desde):
    return qs.filter(actualizado__gte=desde) if desde else qs


# ---------------------------------------------------------------- serializadores
def usuario_json(u, request=None):
    foto = url_foto(u)
    if foto:
        foto = f'/api/v1/usuarios/{u.codigo}/foto/?{foto.split("?", 1)[1]}'
    return {
        'uuid': str(u.uuid) if u.uuid else None, 'codigo': u.codigo, 'nombre': u.nombre_mostrado,
        'correo': u.correo, 'rol': u.rol.codigo if u.rol_id else '', 'rol_nombre': u.rol.nombre if u.rol_id else '',
        'cargo': u.cargo.nombre if u.cargo_id else '', 'delegacion': u.delegacion.nombre if u.delegacion_id else '',
        'delegacion_uuid': str(u.delegacion.uuid) if u.delegacion_id and u.delegacion.uuid else None,
        'activo': u.activo, 'foto_url': foto, 'version': u.version, 'actualizado': _iso(u.actualizado),
    }


def organizacion_json(o, ver_ruts=False):
    directiva = []
    for cargo, nombre, rut in (('presidencia', o.presidente_nombre, o.presidente_rut),
                               ('tesoreria', o.tesorero_nombre, o.tesorero_rut),
                               ('secretaria', o.secretario_nombre, o.secretario_rut)):
        if nombre or rut:
            directiva.append({'cargo': cargo, 'nombre': nombre or '', 'rut': rut_formato(rut) if ver_ruts and rut else None})
    return {
        'uuid': str(o.uuid) if o.uuid else None, 'codigo': o.codigo, 'nombre': o.nombre, 'tipo': o.tipo,
        'tipo_nombre': o.get_tipo_display() if o.tipo else '', 'telefono': o.telefono, 'correo': o.correo,
        'descripcion': o.descripcion or '', 'domicilio_legal': o.domicilio_legal, 'territorio': o.territorio,
        'delegacion': o.delegacion.nombre if o.delegacion_id else None, 'delegacion_id': o.delegacion_id,
        'delegacion_uuid': str(o.delegacion.uuid) if o.delegacion_id and o.delegacion.uuid else None,
        'directiva': directiva, 'vigencia_directiva_hasta': _iso(o.vigencia_directiva_hasta),
        'socios_activos': o.socios_activos, 'fecha_constitucion': _iso(o.fecha_constitucion),
        'registro_personalidad_juridica': o.registro_personalidad_juridica, 'fecha_inscripcion': _iso(o.fecha_inscripcion),
        'registro_directiva': o.registro_directiva, 'verificada': o.verificada, 'activa': o.activa,
        'eliminado_en': _iso(o.eliminado_en), 'version': o.version, 'actualizado': _iso(o.actualizado),
    }


# ---------------------------------------------------------------- alcance
def usuarios_visibles(perfil):
    qs = Usuario.objects.select_related('rol', 'cargo', 'delegacion', 'funcionario')
    if not _es_super(perfil):
        qs = qs.filter(delegacion_id=perfil.delegacion_id).exclude(rol__codigo='superusuario') \
            if perfil.delegacion_id else qs.filter(pk=perfil.pk)
    return qs.order_by('nombre')


def organizaciones_visibles(perfil):
    qs = OrganizacionComunitaria.objects.select_related('delegacion')
    if not _es_super(perfil):
        qs = qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()
    return qs


def _permiso_org(request, accion):
    if not request.user.has_perm(f'control_gestion.{accion}_organizacioncomunitaria'):
        raise ErrorRevision('Su perfil no permite esta operación con organizaciones.', 403)


# ---------------------------------------------------------------- sesiones
@api(['GET'])
def sesiones(request):
    filas = SesionMovil.objects.filter(usuario=request.perfil_movil, expira__gt=timezone.now()).order_by('-ultimo_uso')
    return respuesta({'sesiones': [{'id': s.pk, 'dispositivo': s.dispositivo or 'Dispositivo sin nombre',
                                    'creado': _iso(s.creado), 'ultimo_uso': _iso(s.ultimo_uso), 'expira': _iso(s.expira),
                                    'actual': s.pk == request.sesion_movil.pk} for s in filas]})


@api(['DELETE', 'POST'])
def cerrar_sesion(request, pk):
    borradas, _ = SesionMovil.objects.filter(usuario=request.perfil_movil, pk=pk).delete()
    if not borradas:
        return respuesta({'error': 'No existe esa sesión.'}, 404)
    return respuesta({'ok': True})


# ---------------------------------------------------------------- perfil y fotos
@api(['GET'])
def perfil(request):
    p = request.perfil_movil
    return respuesta({**perfil_json(p), **usuario_json(p),
                      'permisos': {'organizaciones_crear': request.user.has_perm('control_gestion.add_organizacioncomunitaria'),
                                   'organizaciones_editar': request.user.has_perm('control_gestion.change_organizacioncomunitaria')}})


@api(['POST', 'DELETE'])
def foto_propia(request):
    p = request.perfil_movil
    if request.method == 'DELETE':
        quitar_foto(p)
        return respuesta({'ok': True, 'foto_url': ''})
    try:
        guardar_foto(p, request.FILES.get('foto'))
    except FotoInvalida as motivo:
        return respuesta({'error': str(motivo), 'campos': {'foto': [str(motivo)]}}, 422)
    p.refresh_from_db()
    return respuesta({'ok': True, 'foto_url': usuario_json(p)['foto_url']})


@api(['GET'])
def foto_usuario(request, codigo):
    usuario = Usuario.objects.select_related('rol').filter(codigo=codigo).first()
    if not puede_ver_foto(request.perfil_movil, usuario) or not usuario.foto:
        return respuesta({'error': 'Sin foto.'}, 404)
    r = respuesta_foto(request, usuario)
    r['Cache-Control'] = 'private, max-age=300'
    return r


# ---------------------------------------------------------------- listas
@api(['GET'])
def usuarios(request):
    qs = _cambiados(usuarios_visibles(request.perfil_movil), _desde(request))
    return respuesta({'servidor_ahora': _iso(timezone.now()), 'usuarios': [usuario_json(u) for u in qs[:2000]]})


@api(['GET'])
def catalogos(request):
    return respuesta({
        'servidor_ahora': _iso(timezone.now()),
        'delegaciones': [{'id': d.pk, 'uuid': str(d.uuid) if d.uuid else None, 'nombre': d.nombre,
                          'direccion': d.direccion, 'actualizado': _iso(d.actualizado)} for d in Delegacion.objects.order_by('nombre')],
        'territorios': [{'id': t.pk, 'uuid': str(t.uuid) if t.uuid else None, 'nombre': t.nombre, 'delegacion_id': t.delegacion_id,
                         'actualizado': _iso(t.actualizado)} for t in TerritorioDelegacion.objects.order_by('nombre')],
        'tipos_organizacion': [{'valor': v, 'nombre': n} for v, n in OrganizacionComunitaria.Tipo.choices],
    })


def _pagina_organizaciones(request, qs):
    """Paginación por cursor (actualizado, id): estable aunque haya cambios entre páginas."""
    qs = qs.order_by('actualizado', 'pk')
    cursor = (request.GET.get('cursor') or '').strip()
    if cursor:
        try:
            marca, pk = cursor.rsplit('_', 1)
            marca, pk = parse_datetime(marca), int(pk)
            if marca is None:
                raise ValueError
        except ValueError:
            raise ErrorRevision('Cursor inválido.', 400)
        from django.db.models import Q
        qs = qs.filter(Q(actualizado__gt=marca) | Q(actualizado=marca, pk__gt=pk))
    filas = list(qs[:LIMITE + 1])
    siguiente = None
    if len(filas) > LIMITE:
        filas = filas[:LIMITE]
        ultimo = filas[-1]
        siguiente = f'{_iso(ultimo.actualizado)}_{ultimo.pk}' if ultimo.actualizado else None
    return filas, siguiente


# ---------------------------------------------------------------- organizaciones
def _form_organizacion(request, valores, instancia=None):
    from control_gestion.forms import OrganizacionForm
    perfil = request.perfil_movil
    form = OrganizacionForm(data=valores, instance=instancia)
    if not _es_super(perfil):
        form.fields['delegacion'].queryset = form.fields['delegacion'].queryset.filter(pk=perfil.delegacion_id)
        form.fields['delegacion'].required = True
        form.configurar_territorios()
    return form


def _valores_desde(instancia):
    valores = {}
    for campo in CAMPOS_ORG:
        v = getattr(instancia, 'delegacion_id' if campo == 'delegacion' else campo)
        valores[campo] = v.isoformat() if hasattr(v, 'isoformat') else ('' if v is None else v)
    return valores


def _normalizar_entrada(d):
    valores = {}
    for campo in CAMPOS_ORG:
        if campo in d:
            v = d[campo]
            valores[campo] = '' if v is None else v
    if 'delegacion_id' in d and 'delegacion' not in d:
        valores['delegacion'] = d['delegacion_id'] or ''
    return valores


def _ver_ruts(request):
    return request.user.has_perm('control_gestion.change_organizacioncomunitaria')


@api(['GET', 'POST'])
def organizaciones(request):
    if request.method == 'GET':
        _permiso_org(request, 'view')
        qs = _cambiados(organizaciones_visibles(request.perfil_movil), _desde(request))
        filas, siguiente = _pagina_organizaciones(request, qs)
        ver = _ver_ruts(request)
        return respuesta({'servidor_ahora': _iso(timezone.now()), 'siguiente': siguiente,
                          'organizaciones': [organizacion_json(o, ver) for o in filas]})
    _permiso_org(request, 'add')
    d = datos(request)
    try:
        client_id = _uuid.UUID(str(d.get('client_id', '')))
    except ValueError:
        return respuesta({'error': 'Falta client_id (UUID generado en el teléfono).', 'campos': {'client_id': ['UUID inválido.']}}, 422)
    valores = _normalizar_entrada(d)
    valores.setdefault('activa', True)
    huella = hashlib.sha256(json.dumps(valores, sort_keys=True, default=str).encode()).hexdigest()
    previo = EnvioOrganizacionMovil.objects.select_related('organizacion__delegacion').filter(
        usuario=request.user, client_id=client_id).first()
    if previo:
        if previo.huella != huella:
            return respuesta({'error': 'Ese client_id ya se usó con otros datos.'}, 409)
        return respuesta({'organizacion': organizacion_json(previo.organizacion, _ver_ruts(request)), 'repetido': True})
    form = _form_organizacion(request, valores)
    if not form.is_valid():
        return respuesta({'error': 'Revise los datos de la organización.', 'campos': form.errors.get_json_data()}, 422)
    try:
        with transaction.atomic():
            org = form.save()
            EnvioOrganizacionMovil.objects.create(usuario=request.user, client_id=client_id, huella=huella, organizacion=org)
    except IntegrityError:
        previo = EnvioOrganizacionMovil.objects.filter(usuario=request.user, client_id=client_id).first()
        if previo:
            return respuesta({'organizacion': organizacion_json(previo.organizacion, _ver_ruts(request)), 'repetido': True})
        raise
    return respuesta({'organizacion': organizacion_json(org, _ver_ruts(request)), 'repetido': False,
                      'avisos': form.avisos}, 201)


@api(['GET', 'PATCH'])
def organizacion(request, codigo):
    _permiso_org(request, 'view')
    org = organizaciones_visibles(request.perfil_movil).filter(codigo=codigo).first()
    if org is None:
        return respuesta({'error': 'No existe o está fuera de su delegación.'}, 404)
    if request.method == 'GET':
        return respuesta({'organizacion': organizacion_json(org, _ver_ruts(request))})
    _permiso_org(request, 'change')
    d = datos(request)
    try:
        version = int(d.get('version'))
    except (TypeError, ValueError):
        return respuesta({'error': 'Envíe la «version» que tiene el teléfono.', 'campos': {'version': ['Obligatoria.']}}, 422)
    with transaction.atomic():
        org = OrganizacionComunitaria.objects.select_for_update().select_related('delegacion').get(pk=org.pk)
        if (org.version or 0) != version:
            return respuesta({'error': 'Otra persona modificó esta organización. Revise la versión vigente.',
                              'servidor': organizacion_json(org, _ver_ruts(request))}, 409)
        valores = {**_valores_desde(org), **_normalizar_entrada(d)}
        form = _form_organizacion(request, valores, instancia=org)
        if not form.is_valid():
            return respuesta({'error': 'Revise los datos de la organización.', 'campos': form.errors.get_json_data()}, 422)
        org = form.save()
    return respuesta({'organizacion': organizacion_json(org, _ver_ruts(request)), 'avisos': form.avisos})


# ---------------------------------------------------------------- sincronización completa
@api(['GET'])
def sincronizar(request):
    """Todo lo cambiado desde «desde» (o todo si falta): usuarios, organizaciones, catálogos y bajas."""
    perfil = request.perfil_movil
    ahora = timezone.now()
    desde = _desde(request)
    puede_orgs = request.user.has_perm('control_gestion.view_organizacioncomunitaria')
    orgs, siguiente = ([], None)
    if puede_orgs:
        orgs, siguiente = _pagina_organizaciones(request, _cambiados(organizaciones_visibles(perfil), desde))
    bajas = RegistroBaja.objects.all()
    if desde:
        bajas = bajas.filter(fecha__gte=desde)
    ver = _ver_ruts(request)
    return respuesta({
        'servidor_ahora': _iso(ahora),
        'desde': _iso(desde),
        'perfil': usuario_json(perfil),
        'usuarios': [usuario_json(u) for u in _cambiados(usuarios_visibles(perfil), desde)[:2000]],
        'delegaciones': [{'id': x.pk, 'uuid': str(x.uuid) if x.uuid else None, 'nombre': x.nombre, 'direccion': x.direccion}
                         for x in _cambiados(Delegacion.objects.order_by('nombre'), desde)],
        'territorios': [{'id': x.pk, 'uuid': str(x.uuid) if x.uuid else None, 'nombre': x.nombre, 'delegacion_id': x.delegacion_id}
                        for x in _cambiados(TerritorioDelegacion.objects.order_by('nombre'), desde)],
        'organizaciones': [organizacion_json(o, ver) for o in orgs],
        'organizaciones_siguiente': siguiente,
        'bajas': [{'modelo': b.modelo, 'uuid': str(b.uuid), 'codigo': b.codigo, 'fecha': _iso(b.fecha)} for b in bajas[:5000]],
    })
