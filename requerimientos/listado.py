"""Listado paginado y exportación XLSX con el mismo ámbito y filtros."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
import re

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from control_gestion.kanban import perfil_actual, tickets_visibles
from cuentas.auth import puede_ver
from cuentas.servicios import nombres_delegaciones


def datos(request):
    from requerimientos.views import _tickets_con_semaforo
    perfil = perfil_actual(request)
    if perfil is None:
        return None, redirect('login')
    if not puede_ver(perfil, 'requerimientos'):
        return None, HttpResponseForbidden('Su perfil no tiene acceso.')
    qs = tickets_visibles(perfil)
    filtros = {key: request.GET.get(key, '').strip() for key in ('delegacion','estado','busqueda','semaforo')}
    if filtros['delegacion']:
        qs = qs.filter(delegacion__nombre__iexact=filtros['delegacion'])
    if filtros['estado']:
        qs = qs.filter(estado__iexact=filtros['estado'])
    if filtros['busqueda']:
        q = filtros['busqueda']
        qs = qs.filter(Q(codigo__icontains=q) | Q(vecino__nombre__icontains=q)
            | Q(descripcion__icontains=q) | Q(tipo_gestion__nombre__icontains=q)
            | Q(area__nombre__icontains=q) | Q(asignado_a__icontains=q)
            | Q(funcionario__nombre__icontains=q)).distinct()
    rows = _tickets_con_semaforo(qs.order_by('-fecha_ingreso','-codigo'))
    if filtros['semaforo']:
        rows = [r for r in rows if r['semaforo_nivel'].casefold() == filtros['semaforo'].casefold()]
    delegaciones = nombres_delegaciones() if perfil.rol.codigo == 'administrador' else [perfil.delegacion.nombre] if perfil.delegacion_id else []
    return (rows, filtros, delegaciones), None


@never_cache
def lista(request):
    perfil=perfil_actual(request)
    delegacion=request.GET.get('delegacion','').strip()
    if perfil and perfil.rol.codigo!='administrador' and delegacion and (
        not perfil.delegacion_id or delegacion.casefold()!=perfil.delegacion.nombre.casefold()):
        from django.contrib import messages
        messages.error(request,'Su perfil solo puede consultar su delegación.')
        return redirect('inicio')
    result, error = datos(request)
    if error is not None:
        return error
    rows, filtros, delegaciones = result
    from core.paginacion import paginar
    page,paginacion=paginar(request,rows)
    paginator=paginacion["paginator"]
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'requerimientos/lista.html', {
        'requerimientos': page, 'page_obj': page, 'paginator': paginator,
        'paginas': paginator.get_elided_page_range(page.number, on_each_side=2, on_ends=1),
        'consulta_filtros': query.urlencode(), 'total_resultados': len(rows),
        'delegaciones': delegaciones, 'niveles_semaforo': ['Verde','Amarillo','Rojo'],
        'estados_proceso': ['Pendiente','En Proceso','Cuello Botella Central','Resuelto'],
        'filtros_activos': any(filtros.values()),
        **{'filtro_'+key: value for key,value in filtros.items()},
        **paginacion,
    })


def workbook(rows):
    """OOXML real: datos siempre como texto, nunca fórmulas ejecutables."""
    headers = ['Ticket','Ciudadano','Delegación','Canal','Tipo de gestión','Área',
               'Descripción','Fecha de ingreso','Días','Semáforo','Estado','Asignado a']
    fields = ['id_ticket','vecino_nombre','delegacion','canal_ingreso','tipo_entrada',
              'area_tematica','descripcion','fecha_ingreso','dias_transcurridos',
              'semaforo_nivel','estado_proceso','funcionario_asignado']
    def col(index):
        value = ''
        while index:
            index, rem = divmod(index-1,26)
            value = chr(65+rem)+value
        return value
    xmlrows = []
    for n,values in enumerate([headers]+[[r.get(f,'') for f in fields] for r in rows],1):
        cells = []
        for i,value in enumerate(values,1):
            ref = f'{col(i)}{n}'
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value or ''))[:32767])
                style = ' s="1"' if n == 1 else ''
                cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>')
        xmlrows.append(f'<row r="{n}">'+''.join(cells)+'</row>')
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    prefix = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    sheet = f'<worksheet xmlns="{ns}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="12" width="24" customWidth="1"/><col min="7" max="7" width="60" customWidth="1"/></cols><sheetData>'+''.join(xmlrows)+f'</sheetData><autoFilter ref="A1:L{len(rows)+1}"/></worksheet>'
    files = {
        '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Tickets" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        'xl/styles.xml': f'<styleSheet xmlns="{ns}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF8B1524"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        'xl/worksheets/sheet1.xml': sheet,
    }
    output = BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name,xml in files.items():
            archive.writestr(name,(prefix+xml).encode('utf-8'))
    return output.getvalue()


@never_cache
def exportar(request):
    result, error = datos(request)
    if error is not None:
        return error
    rows, _, _ = result
    response = HttpResponse(workbook(rows),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="tickets-{timezone.localdate().isoformat()}.xlsx"'
    return response
