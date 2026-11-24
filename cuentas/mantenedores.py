"""Mantenedores CRUD (listado, búsqueda, alta, edición y eliminación) sobre el ORM."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import FieldDoesNotExist
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from urllib.parse import quote

from control_gestion.forms import EventoAgendaForm, MetaForm, AusenciaForm, MedicionForm, OrganizacionForm, TerritorioForm
from control_gestion.models import EventoAgenda, Meta, Ausencia, Medicion, OrganizacionComunitaria, TerritorioDelegacion
from cuentas.auth import requerir_modulo
from cuentas.forms import DelegacionForm, RolForm, UsuarioForm
from cuentas.models import Delegacion, Rol, Usuario
from cuentas.perfiles import MODELOS_GLOBALES
from requerimientos.forms import AtencionForm, SubAtencionForm, TipoAtencionForm, TipoGestionForm, VecinoForm
from requerimientos.models import Atencion, SubAtencion, TipoAtencion, TipoGestion, Vecino


def _valor(obj, spec):
    if callable(spec):
        return spec(obj)
    actual = obj
    for parte in str(spec).split("__"):
        if actual is None:
            return ""
        actual = getattr(actual, parte, "")
    return "" if actual is None else actual


def _insignia(valor, si, no, color_si, color_no):
    return format_html('<span class="badge text-bg-{}">{}</span>', color_si if valor else color_no, si if valor else no)


def exportar_organizaciones(qs):
    """Excel con las organizaciones de la lista filtrada (mismo alcance que la pantalla)."""
    from django.utils import timezone

    from core.excel import descargar
    from core.fechas import rut_formato

    filas = []
    for o in qs.select_related("delegacion").order_by("nombre")[:5000]:
        filas.append([o.codigo, o.nombre, o.get_tipo_display() if o.tipo else "", o.delegacion.nombre if o.delegacion_id else "",
                      o.territorio, o.domicilio_legal, o.telefono or "", o.correo or "", o.presidente_nombre or "",
                      rut_formato(o.presidente_rut or ""), o.socios_activos or "", o.registro_personalidad_juridica,
                      o.fecha_constitucion or "", "Sí" if o.verificada else "No", "Activa" if o.activa else "De baja"])
    return descargar("organizaciones-" + timezone.localdate().isoformat(), [("Organizaciones", [
        "Código", "Nombre", "Tipo", "Delegación", "Territorio", "Domicilio", "Teléfono", "Correo", "Presidencia",
        "RUT presidencia", "Socios activos", "Personalidad jurídica", "Constitución", "Verificada", "Estado"], filas)])


def _estado(obj):
    if getattr(obj, "estado", "") == "activo":
        return mark_safe('<span class="badge text-bg-success">Activo</span>')
    return mark_safe('<span class="badge text-bg-danger">Inactivo</span>')


def _fecha_atencion(obj):
    from django.utils import timezone

    if not obj.fecha:
        return ""
    return timezone.localtime(obj.fecha).strftime("%d/%m/%y %H:%M")


def desactivar_organizacion(obj):
    """Las organizaciones no se borran: quedan inactivas (la agenda conserva el vínculo y la
    app móvil recibe la baja por ``eliminado_en``)."""
    from django.utils import timezone

    obj.activa = False
    obj.eliminado_en = timezone.now()
    obj.save(update_fields=["activa", "eliminado_en"])


CLAVES_VOLVER = ("q", "page", "per_page", "delegacion", "territorio", "tipo", "verificada", "estado")


def consulta_volver(request):
    """Búsqueda, página y filtros de la lista, para regresar al mismo lugar tras guardar."""
    from django.http import QueryDict

    origen = QueryDict(request.POST.get("volver") or request.GET.get("volver") or "")
    limpio = QueryDict(mutable=True)
    for clave in CLAVES_VOLVER:
        valor = (origen.get(clave) or "")[:120]
        if valor:
            limpio[clave] = valor
    return limpio.urlencode()


def eliminar_usuario(obj):
    with transaction.atomic():
        user = obj.user
        if user is not None:
            obj.user = None
            obj.save(update_fields=["user"])
        obj.delete()
        if user is not None:
            user.delete()


class Mantenedor:
    def __init__(
        self,
        *,
        ruta,
        nombre,
        titulo,
        articulo,
        modelo,
        form_class,
        campos_busqueda,
        columnas,
        placeholder,
        select_related=(),
        al_eliminar=None,
        plantilla_form="mantenedores/formulario.html",
        baja_logica=False,
        orden=None,
        pestanas=None,
    ):
        self.ruta = ruta
        self.nombre = nombre
        self.titulo = titulo
        self.articulo = articulo
        self.modelo = modelo
        self.form_class = form_class
        self.campos_busqueda = campos_busqueda
        self.columnas = columnas
        self.placeholder = placeholder
        self.select_related = select_related
        self.al_eliminar = al_eliminar
        self.plantilla_form = plantilla_form
        self.baja_logica = baja_logica
        # orden: lista para order_by (si no, Meta.ordering). pestanas: [(clave, etiqueta, filtro)], la primera es la inicial.
        self.orden = orden
        self.pestanas = pestanas or []

    def _qs(self, request=None):
        qs = self.modelo.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if request is not None and request._perfil_siged.rol.codigo != 'superusuario':
            # Fuera del superusuario todo queda encapsulado en la delegación propia (y sus territorios).
            delegacion_id = request._perfil_siged.delegacion_id
            if self.modelo is Delegacion:
                qs = qs.filter(pk=delegacion_id) if delegacion_id else qs.none()
            else:
                try:
                    self.modelo._meta.get_field('delegacion')
                except FieldDoesNotExist:
                    pass
                else:
                    qs = qs.filter(delegacion_id=delegacion_id) if delegacion_id else qs.none()
            if self.modelo is Usuario:
                qs = qs.exclude(rol__codigo='superusuario')
        return qs

    def permiso(self, request, accion):
        perfil = getattr(request, '_perfil_siged', None)
        # La configuración que rige a todas las delegaciones solo la modifica el superusuario.
        if accion != 'view' and self.modelo._meta.model_name in MODELOS_GLOBALES and (
                perfil is None or perfil.rol.codigo != 'superusuario'):
            return False
        return request.user.has_perm(f'{self.modelo._meta.app_label}.{accion}_{self.modelo._meta.model_name}')

    def bloqueo(self, request, accion):
        if self.permiso(request,accion):
            return None
        messages.error(request,'Su perfil no tiene acceso a esta operación.')
        return redirect('inicio')

    def formulario(self, request, instance=None):
        form=self.form_class(request.POST or None,instance=instance)
        perfil=request._perfil_siged
        if perfil.rol.codigo!='superusuario':
            campo_rol=form.fields.get('rol')
            if campo_rol is not None and hasattr(campo_rol,'queryset'):
                campo_rol.queryset=campo_rol.queryset.exclude(codigo='superusuario')
            # «organizacion»: quien no es superusuario solo puede elegir organizaciones de su delegación.
            for nombre in ('delegacion','vecino','usuario','funcionario','responsable','organizacion'):
                campo=form.fields.get(nombre)
                if campo is None or not hasattr(campo,'queryset'):
                    continue
                if nombre=='delegacion':
                    campo.queryset=campo.queryset.filter(pk=perfil.delegacion_id)
                elif nombre=='usuario':
                    campo.queryset=campo.queryset.filter(pk=perfil.pk)
                else:
                    campo.queryset=campo.queryset.filter(delegacion_id=perfil.delegacion_id)
        if isinstance(form, OrganizacionForm):
            if perfil.rol.codigo != 'superusuario':
                # Sin delegación la ficha quedaría fuera del ámbito de quien la edita.
                form.fields['delegacion'].required = True
                form.fields['delegacion'].empty_label = None
                if not form.instance.delegacion_id and perfil.delegacion_id:
                    form.initial['delegacion'] = perfil.delegacion_id
            form.configurar_territorios()
        return form

    def _filtros_organizacion(self, request, qs):
        """Filtros de la lista de organizaciones: delegación, territorio, tipo, verificación y estado."""
        perfil = request._perfil_siged
        f = {clave: (request.GET.get(clave) or "").strip()[:120]
             for clave in ("delegacion", "territorio", "tipo", "verificada", "estado")}
        if f["delegacion"] == "sin":
            qs = qs.filter(delegacion__isnull=True)
        elif f["delegacion"].isdigit():
            qs = qs.filter(delegacion_id=int(f["delegacion"]))
        if f["territorio"]:
            qs = qs.filter(territorio__iexact=f["territorio"])
        if f["tipo"] == "sin":
            qs = qs.filter(tipo__isnull=True)
        elif f["tipo"]:
            qs = qs.filter(tipo=f["tipo"])
        if f["verificada"] in ("si", "no"):
            qs = qs.filter(verificada=f["verificada"] == "si")
        estado = f["estado"] or "activas"
        if estado == "activas":
            qs = qs.filter(activa=True)
        elif estado == "inactivas":
            qs = qs.filter(activa=False)
        delegaciones = Delegacion.objects.order_by("nombre")
        if perfil.rol.codigo != "superusuario":
            delegaciones = delegaciones.filter(pk=perfil.delegacion_id)
        territorios = TerritorioDelegacion.objects.order_by("nombre")
        if f["delegacion"].isdigit():
            territorios = territorios.filter(delegacion_id=int(f["delegacion"]))
        elif perfil.rol.codigo != "superusuario":
            territorios = territorios.filter(delegacion_id=perfil.delegacion_id)
        sin_delegacion = (OrganizacionComunitaria.objects.filter(delegacion__isnull=True).count()
                          if perfil.rol.codigo == "superusuario" else 0)
        return qs, {
            "filtros": {**f, "estado": estado},
            "opciones_delegacion": delegaciones,
            "opciones_territorio": sorted(set(territorios.values_list("nombre", flat=True))),
            "opciones_tipo": OrganizacionComunitaria.Tipo.choices,
            "sin_delegacion": sin_delegacion,
            "filtros_activos": any(v for k, v in f.items() if k != "estado") or estado != "activas",
        }

    def lista(self, request):
        bloqueo = self.bloqueo(request, 'view')
        if bloqueo:
            return bloqueo
        q = (request.GET.get("q") or "").strip()
        qs = self._qs(request)
        extra = {}
        if self.pestanas:
            claves = [clave for clave, _, _ in self.pestanas]
            actual = request.GET.get("ver") if request.GET.get("ver") in claves else claves[0]
            extra["pestanas"] = [{"clave": clave, "etiqueta": etiqueta, "activa": clave == actual,
                                  "cantidad": qs.filter(**filtro).count(),
                                  "url": reverse(self.nombre) + (f"?ver={clave}" if clave != claves[0] else "")}
                                 for clave, etiqueta, filtro in self.pestanas]
            extra["pestana_actual"] = actual
            qs = qs.filter(**dict((c, f) for c, _, f in self.pestanas)[actual])
        if self.orden:
            qs = qs.order_by(*self.orden)
        if self.modelo is OrganizacionComunitaria:
            qs, extra = self._filtros_organizacion(request, qs)
        from core.busqueda import buscar
        qs = buscar(qs,q,self.campos_busqueda)
        if self.modelo is OrganizacionComunitaria and request.GET.get("exportar") == "excel":
            return exportar_organizaciones(qs)

        from core.paginacion import paginar
        pagina,paginacion=paginar(request,qs)
        volver = request.GET.urlencode()
        sufijo = f"?volver={quote(volver)}" if volver else ""
        puede_editar, puede_eliminar = self.permiso(request,'change'), self.permiso(request,'delete')
        filas = []
        for obj in pagina:
            filas.append(
                {
                    "celdas": [_valor(obj, spec) for _, spec in self.columnas],
                    "organizacion": obj if self.modelo is OrganizacionComunitaria else None,
                    "editar": reverse(f"{self.nombre}_editar", args=[obj.pk]) + sufijo if puede_editar else None,
                    "eliminar": (reverse(f"{self.nombre}_eliminar", args=[obj.pk]) + sufijo
                                 if puede_eliminar and not (self.baja_logica and not getattr(obj, "activa", True)) else None),
                }
            )
        contexto = {
            "titulo": self.titulo,
            "q": q,
            "placeholder": self.placeholder,
            "encabezados": [titulo for titulo, _ in self.columnas],
            "filas": filas,
            "total": paginacion["paginator"].count,
            **paginacion,
            "exportar_usuarios": self.modelo is Usuario,
            "es_organizaciones": self.modelo is OrganizacionComunitaria,
            "url_crear": (reverse(f"{self.nombre}_crear") + sufijo) if self.permiso(request,'add') else None,
            "url_lista": reverse(self.nombre),
            "texto_eliminar": "Dar de baja" if self.baja_logica else "Eliminar",
            **extra,
        }
        return render(request, "mantenedores/lista.html", contexto)

    def crear(self, request):
        bloqueo = self.bloqueo(request, 'add')
        if bloqueo:
            return bloqueo
        if self.modelo is Usuario:
            return redirect("admin_usuarios")
        sin_delegacion = self._sin_delegacion(request)
        if sin_delegacion:
            return sin_delegacion
        form = self.formulario(request)
        if request.method == "POST":
            if form.is_valid():
                obj = form.save()
                self._avisar(request, form, f"Se guardó {self.articulo} «{obj}».")
                return redirect(self._url_volver(request))
            messages.error(request, "No se guardó: revise los campos marcados en rojo.")
        return render(
            request,
            self.plantilla_form,
            {
                "titulo": f"Agregar {self.titulo.lower()}",
                "form": form,
                "url_lista": self._url_volver(request),
                "titulo_lista": self.titulo,
                "volver": consulta_volver(request),
            },
        )

    def _url_volver(self, request):
        consulta = consulta_volver(request)
        return reverse(self.nombre) + (f"?{consulta}" if consulta else "")

    def _avisar(self, request, form, texto):
        messages.success(request, texto)
        for aviso in getattr(form, "avisos", []):
            messages.warning(request, aviso)

    def _sin_delegacion(self, request):
        """Quien no es superusuario necesita una delegación para crear registros acotados a ella."""
        perfil = request._perfil_siged
        try:
            self.modelo._meta.get_field("delegacion")
        except FieldDoesNotExist:
            return None
        if perfil.rol.codigo != "superusuario" and not perfil.delegacion_id:
            messages.error(request, "Su cuenta no tiene delegación asignada; pida a un superusuario que la asigne.")
            return redirect(self.nombre)
        return None

    def editar(self, request, pk):
        bloqueo = self.bloqueo(request, 'change')
        if bloqueo:
            return bloqueo
        obj = get_object_or_404(self._qs(request), pk=pk)
        form = self.formulario(request, instance=obj)
        if request.method == "POST":
            if form.is_valid():
                obj = form.save()
                self._avisar(request, form, f"Se guardó {self.articulo} «{obj}».")
                return redirect(self._url_volver(request))
            messages.error(request, "No se guardó: revise los campos marcados en rojo.")
        return render(
            request,
            self.plantilla_form,
            {
                "titulo": f"Modificar {self.titulo.lower()}",
                "form": form,
                "url_lista": self._url_volver(request),
                "titulo_lista": self.titulo,
                "objeto": obj,
                "volver": consulta_volver(request),
            },
        )

    def eliminar(self, request, pk):
        bloqueo = self.bloqueo(request, 'delete')
        if bloqueo:
            return bloqueo
        obj = get_object_or_404(self._qs(request), pk=pk)
        if self.modelo is Usuario and obj.user_id == request.user.pk:
            messages.error(request, "No puede eliminar su propia cuenta.")
            return redirect(self.nombre)
        if request.method == "POST":
            try:
                with transaction.atomic():
                    if self.al_eliminar:
                        self.al_eliminar(obj)
                    else:
                        obj.delete()
            except ProtectedError:
                messages.error(
                    request,
                    f"No se puede eliminar {self.articulo} porque otros registros lo utilizan.",
                )
                return redirect(self._url_volver(request))
            if self.baja_logica:
                messages.success(request, f"Se dio de baja {self.articulo} «{obj}». Puede reactivarla desde Modificar.")
            else:
                messages.success(request, f"Se eliminó {self.articulo}.")
            return redirect(self._url_volver(request))
        vinculados = obj.eventos.count() if hasattr(obj, "eventos") else 0
        return render(
            request,
            "mantenedores/eliminar.html",
            {
                "titulo": self.titulo,
                "articulo": self.articulo,
                "objeto": obj,
                "url_lista": self._url_volver(request),
                "volver": consulta_volver(request),
                "baja_logica": self.baja_logica,
                "vinculados": vinculados,
            },
        )

    def vistas(self):
        return (
            login_required(self.lista),
            login_required(self.crear),
            login_required(self.editar),
            login_required(self.eliminar),
        )


def _armar():
    definiciones = [
        Mantenedor(ruta='territorios', nombre='mant_territorios', titulo='Territorios por delegación', articulo='el territorio', modelo=TerritorioDelegacion, form_class=TerritorioForm, campos_busqueda=('nombre','delegacion__nombre'), columnas=[('Territorio','nombre'),('Delegación','delegacion')], placeholder='Buscar territorio o delegación', select_related=('delegacion',)),
        Mantenedor(ruta='organizaciones',nombre='mant_organizaciones',titulo='Organizaciones comunitarias',articulo='la organización',modelo=OrganizacionComunitaria,form_class=OrganizacionForm,campos_busqueda=('codigo','nombre','descripcion','territorio','domicilio_legal','registro_personalidad_juridica','presidente_nombre','presidente_rut','tesorero_nombre','tesorero_rut','secretario_nombre','secretario_rut','telefono','correo'),columnas=[('Código','codigo'),('Organización','nombre'),('Tipo',lambda obj: obj.get_tipo_display() if obj.tipo else ''),('Territorio','territorio'),('Delegación','delegacion'),('Verificación',lambda obj: _insignia(obj.verificada, 'Verificada', 'Pendiente', 'success', 'warning')),('Estado',lambda obj: _insignia(obj.activa, 'Activa', 'De baja', 'success', 'secondary'))],placeholder='Buscar nombre, RUT de la directiva, teléfono o registro',select_related=('delegacion',),al_eliminar=desactivar_organizacion,plantilla_form='mantenedores/organizacion_form.html',baja_logica=True),

        # Actividades de organizaciones: lo último creado va primero; las actividades sin organización quedan en su propia pestaña.
        Mantenedor(ruta='agenda',nombre='mant_agenda',titulo='Actividades de organizaciones',articulo='la actividad',modelo=EventoAgenda,form_class=EventoAgendaForm,campos_busqueda=('codigo','titulo','tipo','lugar','organizacion__nombre','delegacion__nombre'),columnas=[('Código','codigo'),('Actividad','titulo'),('Organización','organizacion'),('Fecha','fecha'),('Hora',lambda obj: f'{obj.hora:%H:%M}'),('Tipo','tipo'),('Delegación','delegacion')],placeholder='Buscar actividad, organización o delegación',select_related=('delegacion','organizacion','responsable'),orden=('-pk',),pestanas=[('', 'De organizaciones', {'organizacion__isnull': False}), ('generales', 'Sin organización', {'organizacion__isnull': True})]),
        Mantenedor(ruta='periodos',nombre='mant_periodos',titulo='Configuración trimestral',articulo='el período',modelo=Medicion,form_class=MedicionForm,campos_busqueda=('periodo','descripcion'),columnas=[('Período','periodo'),('Desde','fecha_inicio'),('Hasta','fecha_termino'),('Días base','dias_totales')],placeholder='Buscar período trimestral'),
        Mantenedor(ruta='ausencias',nombre='mant_ausencias',titulo='Ausencias y ajuste de metas',articulo='la ausencia',modelo=Ausencia,form_class=AusenciaForm,campos_busqueda=('funcionario__nombre','tipo','delegacion__nombre'),columnas=[('Funcionario','funcionario'),('Motivo','tipo'),('Desde','fecha_inicio'),('Hasta','fecha_termino')],placeholder='Buscar funcionario, motivo o delegación',select_related=('funcionario','delegacion')),

        Mantenedor(
            ruta="delegaciones",
            nombre="mant_delegaciones",
            titulo="Delegaciones municipales",
            articulo="la delegación",
            modelo=Delegacion,
            form_class=DelegacionForm,
            campos_busqueda=("nombre", "direccion", "comuna"),
            columnas=[
                ("Nombre", "nombre"),
                ("Dirección", "direccion"),
                ("Comuna", "comuna"),
            ],
            placeholder="Buscar por nombre, dirección o comuna",
        ),
        Mantenedor(
            ruta="usuarios",
            nombre="mant_usuarios",
            titulo="Usuarios",
            articulo="el usuario",
            modelo=Usuario,
            form_class=UsuarioForm,
            campos_busqueda=("nombre", "correo", "username", "rol__nombre", "rol__codigo"),
            columnas=[
                ("Nombre", "nombre"),
                ("Correo", "correo"),
                ("Rol", "rol__nombre"),
                ("Estado", _estado),
            ],
            placeholder="Buscar por nombre, correo o rol",
            select_related=("rol", "cargo", "delegacion", "funcionario"),
            al_eliminar=eliminar_usuario,
        ),
        Mantenedor(
            ruta="roles",
            nombre="mant_roles",
            titulo="Roles",
            articulo="el rol",
            modelo=Rol,
            form_class=RolForm,
            campos_busqueda=("nombre", "descripcion", "codigo"),
            columnas=[
                ("Nombre", "nombre"),
                ("Descripción", "descripcion"),
            ],
            placeholder="Buscar por nombre o descripción",
        ),
        Mantenedor(
            ruta="metas",
            nombre="mant_metas",
            titulo="Metas",
            articulo="la meta",
            modelo=Meta,
            form_class=MetaForm,
            campos_busqueda=("nombre", "descripcion"),
            columnas=[
                ("Código", "codigo"),
                ("Nombre", "nombre"),
                ("Descripción", "descripcion"),
            ],
            placeholder="Buscar por nombre o descripción",
        ),
        Mantenedor(
            ruta="tipos-atencion",
            nombre="mant_tipos_atencion",
            titulo="Tipo de atención",
            articulo="el tipo de atención",
            modelo=TipoAtencion,
            form_class=TipoAtencionForm,
            campos_busqueda=("nombre", "descripcion"),
            columnas=[
                ("Nombre", "nombre"),
                ("Descripción", "descripcion"),
            ],
            placeholder="Buscar por nombre o descripción",
        ),
        Mantenedor(
            ruta="sub-atenciones",
            nombre="mant_sub_atenciones",
            titulo="Sub atención",
            articulo="la sub atención",
            modelo=SubAtencion,
            form_class=SubAtencionForm,
            campos_busqueda=("nombre", "descripcion", "tipo_atencion__nombre"),
            columnas=[
                ("Nombre", "nombre"),
                ("Tipo de atención", "tipo_atencion__nombre"),
            ],
            placeholder="Buscar por nombre o tipo de atención",
            select_related=("tipo_atencion",),
        ),
        Mantenedor(
            ruta="atenciones",
            nombre="mant_atenciones",
            titulo="Atenciones",
            articulo="la atención",
            modelo=Atencion,
            form_class=AtencionForm,
            campos_busqueda=(
                "vecino__nombre",
                "vecino__rut",
                "tipo_atencion__nombre",
                "sub_atencion__nombre",
                "delegacion__nombre",
                "observacion",
                "usuario__nombre",
            ),
            columnas=[
                ("Vecino", "vecino__nombre"),
                ("RUT vecino", "vecino__rut"),
                ("Tipo", "tipo_atencion__nombre"),
                ("Sub atención", "sub_atencion__nombre"),
                ("Delegación", "delegacion__nombre"),
                ("Fecha", _fecha_atencion),
                ("Estado", lambda obj: obj.get_estado_display()),
            ],
            placeholder="Buscar por vecino, tipo, delegación u observación",
            select_related=("vecino", "tipo_atencion", "sub_atencion", "delegacion", "usuario"),
        ),
        Mantenedor(
            ruta="tipos-gestion",
            nombre="mant_tipos_gestion",
            titulo="Tipo de gestión",
            articulo="el tipo de gestión",
            modelo=TipoGestion,
            form_class=TipoGestionForm,
            campos_busqueda=("nombre", "descripcion"),
            columnas=[
                ("Nombre", "nombre"),
                ("Descripción", "descripcion"),
            ],
            placeholder="Buscar por nombre o descripción",
        ),
        Mantenedor(
            ruta="vecinos",
            nombre="mant_vecinos",
            titulo="Vecinos",
            articulo="el vecino",
            modelo=Vecino,
            form_class=VecinoForm,
            campos_busqueda=(
                "nombre",
                "rut",
                "direccion",
                "telefono",
                "correo",
                "territorio",
                "tipo_gestion__nombre",
                "delegacion__nombre",
            ),
            columnas=[
                ("Nombre", "nombre"),
                ("RUT", "rut"),
                ("Dirección", "direccion"),
                ("Teléfono", "telefono"),
                ("Territorio", "territorio"),
                ("Tipo de gestión", "tipo_gestion__nombre"),
                ("Estado", _estado),
            ],
            placeholder="Buscar por nombre, RUT, dirección o territorio",
            select_related=("delegacion", "tipo_gestion"),
        ),
    ]
    for item in definiciones:
        item.vista_lista, item.vista_crear, item.vista_editar, item.vista_eliminar = item.vistas()
    return definiciones


MANTENEDORES = _armar()
