from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from control_gestion.models import TerritorioDelegacion


def territorios_de(delegacion_id):
    return TerritorioDelegacion.objects.filter(delegacion_id=delegacion_id).order_by('nombre').values_list('nombre', flat=True)


@never_cache
@require_GET
def opciones_territorios(request):
    perfil = getattr(request, '_perfil_siged', None)
    permisos = ('control_gestion.add_organizacioncomunitaria', 'control_gestion.change_organizacioncomunitaria')
    if not perfil or not any(request.user.has_perm(perm) for perm in permisos):
        return JsonResponse({'error': 'No tiene acceso a este catálogo.'}, status=403)
    try:
        delegacion_id = int(request.GET.get('delegacion', ''))
        if not 0 < delegacion_id < 2 ** 63:
            raise ValueError
    except ValueError:
        return JsonResponse({'territorios': []})
    if perfil.rol.codigo != 'superusuario' and delegacion_id != perfil.delegacion_id:
        return JsonResponse({'error': 'La delegación está fuera de su ámbito.'}, status=403)
    return JsonResponse({'territorios': list(territorios_de(delegacion_id))})


@never_cache
@require_GET
def buscar_organizaciones(request):
    """Autocompletar de organizaciones (agenda): máximo 20 resultados del alcance del perfil."""
    from django.db.models import Q

    from control_gestion.models import OrganizacionComunitaria

    perfil = getattr(request, '_perfil_siged', None)
    if not perfil or not request.user.has_perm('control_gestion.view_organizacioncomunitaria'):
        return JsonResponse({'error': 'No tiene acceso a las organizaciones.'}, status=403)
    texto = ' '.join((request.GET.get('q') or '').split())[:80]
    if len(texto) < 2:
        return JsonResponse({'resultados': []})
    qs = OrganizacionComunitaria.objects.filter(activa=True).select_related('delegacion')
    if perfil.rol.codigo != 'superusuario':
        qs = qs.filter(delegacion_id=perfil.delegacion_id) if perfil.delegacion_id else qs.none()
    for palabra in texto.split():
        qs = qs.filter(Q(nombre__icontains=palabra) | Q(codigo__icontains=palabra) | Q(territorio__icontains=palabra))
    resultados = [
        {'id': o.pk, 'texto': o.nombre, 'detalle': ' · '.join(x for x in (o.codigo, o.territorio, str(o.delegacion or '')) if x),
         'delegacion': o.delegacion_id}
        for o in qs.order_by('nombre')[:20]
    ]
    return JsonResponse({'resultados': resultados})
