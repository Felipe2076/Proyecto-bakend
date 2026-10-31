"""Mantenedores CRUD (listado, búsqueda, alta, edición y eliminación) sobre el ORM."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import FieldDoesNotExist
from django.urls import reverse
from django.utils.safestring import mark_safe

from control_gestion.forms import MetaForm
from control_gestion.models import Meta
from cuentas.auth import requerir_modulo
from cuentas.forms import DelegacionForm, RolForm, UsuarioForm
from cuentas.models import Delegacion, Rol, Usuario
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


def _estado(obj):
    if getattr(obj, "estado", "") == "activo":
        return mark_safe('<span class="badge text-bg-success">Activo</span>')
    return mark_safe('<span class="badge text-bg-danger">Inactivo</span>')


def _fecha_atencion(obj):
    from django.utils import timezone

    if not obj.fecha:
        return ""
    return timezone.localtime(obj.fecha).strftime("%d-%m-%Y %H:%M")


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

    def _qs(self, request=None):
        qs = self.modelo.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if request is not None and request._perfil_siged.rol.codigo != 'administrador':
            try:
                self.modelo._meta.get_field('delegacion')
            except FieldDoesNotExist:
                pass
            else:
                qs=qs.filter(delegacion_id=request._perfil_siged.delegacion_id) if request._perfil_siged.delegacion_id else qs.none()
        return qs

    def permiso(self, request, accion):
        return request.user.has_perm(f'{self.modelo._meta.app_label}.{accion}_{self.modelo._meta.model_name}')

    def bloqueo(self, request, accion):
        if self.permiso(request,accion):
            return None
        messages.error(request,'Su perfil no tiene acceso a esta operación.')
        return redirect('inicio')

    def formulario(self, request, instance=None):
        form=self.form_class(request.POST or None,instance=instance)
        perfil=request._perfil_siged
        if perfil.rol.codigo!='administrador':
            for nombre in ('delegacion','vecino','usuario','funcionario'):
                campo=form.fields.get(nombre)
                if campo is None or not hasattr(campo,'queryset'):
                    continue
                if nombre=='delegacion':
                    campo.queryset=campo.queryset.filter(pk=perfil.delegacion_id)
                elif nombre=='usuario':
                    campo.queryset=campo.queryset.filter(pk=perfil.pk)
                else:
                    campo.queryset=campo.queryset.filter(delegacion_id=perfil.delegacion_id)
        return form

    def lista(self, request):
        bloqueo = self.bloqueo(request, 'view')
        if bloqueo:
            return bloqueo
        q = (request.GET.get("q") or "").strip()
        qs = self._qs(request)
        from core.busqueda import buscar
        qs = buscar(qs,q,self.campos_busqueda)

        from core.paginacion import paginar
        pagina,paginacion=paginar(request,qs)
        filas = []
        for obj in pagina:
            filas.append(
                {
                    "celdas": [_valor(obj, spec) for _, spec in self.columnas],
                    "editar": reverse(f"{self.nombre}_editar", args=[obj.pk]) if self.permiso(request,'change') else None,
                    "eliminar": reverse(f"{self.nombre}_eliminar", args=[obj.pk]) if self.permiso(request,'delete') else None,
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
            "url_crear": reverse(f"{self.nombre}_crear") if self.permiso(request,'add') else None,
            "url_lista": reverse(self.nombre),
        }
        return render(request, "mantenedores/lista.html", contexto)

    def crear(self, request):
        bloqueo = self.bloqueo(request, 'add')
        if bloqueo:
            return bloqueo
        if self.modelo is Usuario:
            return redirect("admin_usuarios")
        form = self.formulario(request)
        if request.method == "POST":
            if form.is_valid():
                obj = form.save()
                messages.success(request, f"Se guardó {self.articulo} «{obj}».")
                return redirect(self.nombre)
            messages.error(request, "Revise los campos marcados antes de guardar.")
        return render(
            request,
            "mantenedores/formulario.html",
            {
                "titulo": f"Agregar {self.titulo.lower()}",
                "form": form,
                "url_lista": reverse(self.nombre),
                "titulo_lista": self.titulo,
            },
        )

    def editar(self, request, pk):
        bloqueo = self.bloqueo(request, 'change')
        if bloqueo:
            return bloqueo
        obj = get_object_or_404(self._qs(request), pk=pk)
        form = self.formulario(request, instance=obj)
        if request.method == "POST":
            if form.is_valid():
                obj = form.save()
                messages.success(request, f"Se guardó {self.articulo} «{obj}».")
                return redirect(self.nombre)
            messages.error(request, "Revise los campos marcados antes de guardar.")
        return render(
            request,
            "mantenedores/formulario.html",
            {
                "titulo": f"Modificar {self.titulo.lower()}",
                "form": form,
                "url_lista": reverse(self.nombre),
                "titulo_lista": self.titulo,
                "objeto": obj,
            },
        )

    def eliminar(self, request, pk):
        bloqueo = self.bloqueo(request, 'delete')
        if bloqueo:
            return bloqueo
        obj = get_object_or_404(self._qs(request), pk=pk)
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
                return redirect(self.nombre)
            messages.success(request, f"Se eliminó {self.articulo}.")
            return redirect(self.nombre)
        return render(
            request,
            "mantenedores/eliminar.html",
            {
                "titulo": self.titulo,
                "articulo": self.articulo,
                "objeto": obj,
                "url_lista": reverse(self.nombre),
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
