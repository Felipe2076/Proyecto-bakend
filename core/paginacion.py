from django.core.paginator import Paginator

def paginar(request,elementos,por_defecto=10):
    try: cantidad=int(request.GET.get('per_page',por_defecto))
    except (ValueError,TypeError): cantidad=por_defecto
    if cantidad not in (10,25,50,100): cantidad=por_defecto
    paginator=Paginator(elementos,cantidad)
    page=paginator.get_page(request.GET.get('page'))
    base=request.GET.copy()
    base.pop('page',None)
    base.pop('per_page',None)
    controles=[(key,value) for key in base for value in base.getlist(key)]
    base['per_page']=cantidad
    datos={'page_obj':page,'paginator':paginator,'paginas':paginator.get_elided_page_range(page.number,on_each_side=2,on_ends=1),
        'consulta_pagina':base.urlencode(),'filtros_pagina':controles,'por_pagina':cantidad,'opciones_pagina':(10,25,50,100)}
    return page,datos
