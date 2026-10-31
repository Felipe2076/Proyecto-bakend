"""Generador XLSX sin dependencias nuevas; los textos no se ejecutan como fórmulas."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from xml.sax.saxutils import escape
import re
from datetime import date,datetime
from decimal import Decimal
from django.http import HttpResponse

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
def texto(v):
    return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]','',str(v or ''))[:32767])
def columna(n):
    out=''
    while n:
        n,r=divmod(n-1,26)
        out=chr(65+r)+out
    return out
def libro(hojas):
    # Conservar los estilos ya utilizados por la exportación de tickets.
    from requerimientos.listado import workbook
    with ZipFile(BytesIO(workbook([]))) as anterior:
        estilos=anterior.read('xl/styles.xml')
    out=BytesIO()
    tipos=['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>','<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    sheets=[]
    relaciones=[]
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        z.writestr('xl/styles.xml',estilos)
        for index,(nombre,headers,rows) in enumerate(hojas,1):
            xml=[]
            for n,values in enumerate([headers]+list(rows),1):
                cells=[]
                for i,value in enumerate(values,1):
                    ref=f'{columna(i)}{n}'
                    if isinstance(value,bool): value='Sí' if value else 'No'
                    if isinstance(value,(int,float,Decimal)):
                        cells.append(f'<c r="{ref}"><v>{value}</v></c>')
                    else:
                        if isinstance(value,(date,datetime)): value=value.isoformat()
                        cells.append(f'<c r="{ref}" t="inlineStr"'+(' s="1"' if n==1 else '')+f'><is><t xml:space="preserve">{texto(value)}</t></is></c>')
                xml.append(f'<row r="{n}">'+''.join(cells)+'</row>')
            sheet=f'<worksheet xmlns="{NS}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen" activePane="bottomLeft"/></sheetView></sheetViews><cols><col min="1" max="{len(headers)}" width="26" customWidth="1"/></cols><sheetData>'+''.join(xml)+f'</sheetData><autoFilter ref="A1:{columna(len(headers))}{len(xml)}"/></worksheet>'
            z.writestr(f'xl/worksheets/sheet{index}.xml',sheet)
            sheets.append(f'<sheet name="{texto(nombre)}" sheetId="{index}" r:id="rId{index}"/>')
            relaciones.append(f'<Relationship Id="rId{index}" Type="{REL}/worksheet" Target="worksheets/sheet{index}.xml"/>')
            tipos.append(f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        relaciones.append(f'<Relationship Id="rId{len(hojas)+1}" Type="{REL}/styles" Target="styles.xml"/>')
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+''.join(tipos)+'</Types>')
        z.writestr('_rels/.rels',f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{NS}" xmlns:r="{REL}"><sheets>'+''.join(sheets)+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(relaciones)+'</Relationships>')
    return out.getvalue()
def descargar(nombre,hojas):
    response=HttpResponse(libro(hojas),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition']=f'attachment; filename="{nombre}.xlsx"'
    response['Cache-Control']='no-store, private'
    return response
