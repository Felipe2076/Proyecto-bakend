"""ModelForm del mantenedor de metas."""

import re

from django import forms
from django.urls import reverse
from django.utils import timezone

from core.validaciones import MENSAJE_NOMBRE, normalizar_rut, rut_canonico, validar_nombre, validar_rut

from control_gestion.models import Meta
from cuentas.forms import FormularioBootstrap, NombreMinimoMixin


class MetaForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = Meta
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


from control_gestion.models import Ausencia, Medicion

class AusenciaForm(FormularioBootstrap):
    class Meta:
        model=Ausencia
        fields=['funcionario','delegacion','tipo','fecha_inicio','fecha_termino','observacion']
        widgets={'fecha_inicio':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),'fecha_termino':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}

class MedicionForm(FormularioBootstrap):
    class Meta:
        model=Medicion
        fields=['periodo','fecha_inicio','fecha_termino','meta_cumplimiento_tubo','descripcion']
        widgets={'fecha_inicio':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),'fecha_termino':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El nombre y los días se calculan solos a partir de las fechas; el nombre puede escribirse si se desea otro.
        self.fields['periodo'].required = False
        self.fields['periodo'].label = 'Nombre del período'
        self.fields['periodo'].widget.attrs['placeholder'] = 'Automático (ej.: Trimestre 4 de 2026)'
        self.fields['periodo'].help_text = 'Déjelo vacío y se genera con las fechas.'
        dias = f' Hoy: {self.instance.dias_totales} días.' if self.instance.pk else ''
        self.fields['fecha_termino'].help_text = 'Los días del período se calculan solos con las fechas.' + dias

    def _nombre_automatico(self, inicio, fin):
        dias = (fin - inicio).days + 1
        if 80 <= dias <= 100:
            base = f'Trimestre {(inicio.month - 1) // 3 + 1} de {inicio.year}'
        else:
            base = f'Período {inicio:%d/%m/%y} al {fin:%d/%m/%y}'
        existentes = set(Medicion.objects.exclude(pk=self.instance.pk).values_list('periodo', flat=True))
        nombre, n = base, 1
        while nombre in existentes:
            n += 1
            nombre = f'{base} ({n})'
        return nombre

    def save(self, commit=True):
        # El trimestre rige para todas las delegaciones: la delegación piloto ya no se elige, solo se conserva
        # (o se completa con una existente) porque la tabla la exige.
        medicion = super().save(commit=False)
        if not medicion.delegacion_piloto_id:
            from control_gestion.models import Medicion as _M
            from cuentas.models import Delegacion
            previa = _M.objects.exclude(delegacion_piloto__isnull=True).order_by('-fecha_inicio').first()
            medicion.delegacion_piloto = (previa.delegacion_piloto if previa else
                Delegacion.objects.filter(nombre__icontains='Rural').first() or Delegacion.objects.order_by('pk').first())
        if commit:
            medicion.save()
            self.save_m2m()
        return medicion

    def clean(self):
        data=super().clean()
        inicio=data.get('fecha_inicio');fin=data.get('fecha_termino')
        if inicio and fin and fin<inicio:
            self.add_error('fecha_termino','La fecha de término debe ser posterior al inicio.')
        elif inicio and fin and Medicion.objects.exclude(pk=self.instance.pk).filter(
                fecha_inicio__lte=fin, fecha_termino__gte=inicio).exists():
            self.add_error('fecha_inicio', 'Estas fechas se superponen con otro período configurado.')
        if inicio and fin and fin>=inicio:
            self.instance.dias_totales=(fin-inicio).days+1
            if not data.get('periodo'):
                data['periodo']=self._nombre_automatico(inicio,fin)
        return data


from control_gestion.models import EventoAgenda, OrganizacionComunitaria, TerritorioDelegacion
from control_gestion.territorios import territorios_de


class EventoAgendaForm(FormularioBootstrap):
    """Actividad de una organización (o evento de agenda) que se refleja en el calendario."""

    class Meta:
        model = EventoAgenda
        fields = ['titulo', 'tipo', 'fecha', 'hora', 'organizacion', 'delegacion', 'responsable', 'lugar']
        labels = {'titulo': 'Actividad', 'tipo': 'Tipo (reunión, asamblea, capacitación…)'}
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'hora': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Activas, más la ya elegida aunque después se haya desactivado (si no, editar el evento fallaba).
        activas = OrganizacionComunitaria.objects.filter(activa=True)
        if self.instance.organizacion_id:
            activas = activas | OrganizacionComunitaria.objects.filter(pk=self.instance.organizacion_id)
        self.fields['organizacion'].queryset = activas.order_by('nombre')
        self.fields['organizacion'].widget = SelectSoloElegido(attrs={
            'class': 'form-select', 'data-buscar-url': reverse('buscar_organizaciones')})
        self.fields['organizacion'].widget.choices = self.fields['organizacion'].choices
        self.fields['organizacion'].empty_label = 'Ninguna (no es de una organización)'
        self.fields['organizacion'].help_text = 'Elija la organización; la actividad aparecerá en el calendario con su nombre.'
        self.fields['delegacion'].help_text = 'Si deja la delegación vacía se usa la de la organización, cuando la tiene.'
        self.fields['delegacion'].required = False

    def clean(self):
        data = super().clean()
        organizacion, delegacion = data.get('organizacion'), data.get('delegacion')
        if not delegacion and organizacion is not None and organizacion.delegacion_id:
            data['delegacion'] = organizacion.delegacion
        if not data.get('delegacion'):
            self.add_error('delegacion', 'Seleccione la delegación de la actividad.')
        elif organizacion is not None and organizacion.delegacion_id and organizacion.delegacion_id != data['delegacion'].pk:
            self.add_error('organizacion', f'«{organizacion.nombre}» pertenece a {organizacion.delegacion}; '
                                           'elija esa delegación o deje la delegación vacía.')
        return data


class TerritorioForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = TerritorioDelegacion
        fields = ['delegacion', 'nombre']


class SelectSoloElegido(forms.Select):
    """Dibuja solo la opción elegida: la lista completa (≈2.700 organizaciones) la trae el
    buscador por JavaScript. La validación sigue usando el queryset completo del campo."""

    def optgroups(self, name, value, attrs=None):
        elegidos = {str(v) for v in value if v not in (None, '')}
        grupos = []
        for indice, (grupo, opciones, i) in enumerate(super().optgroups(name, value, attrs)):
            visibles = [o for o in opciones if str(o['value']) in elegidos or o['value'] in ('', None)]
            if visibles:
                grupos.append((grupo, visibles, i))
        return grupos


def normalizar_telefono(valor):
    """Devuelve ``+56 9 1234 5678`` (celular) o ``+56 51 234 5678`` (fijo), o None si no sirve."""
    digitos = re.sub(r'\D', '', valor or '')
    if digitos.startswith('56'):
        digitos = digitos[2:]
    if len(digitos) != 9:
        return None
    if digitos.startswith('9'):
        return f'+56 9 {digitos[1:5]} {digitos[5:]}'
    if digitos[0] in '234567':
        return f'+56 {digitos[:2]} {digitos[2:5]} {digitos[5:]}'
    return None


class OrganizacionForm(NombreMinimoMixin, FormularioBootstrap):
    """Ficha de organización comunitaria en secciones, con validaciones explicadas en español.

    Regla del cliente: un RUT de la directiva con dígito verificador incorrecto **no**
    bloquea el guardado (hay fichas en papel con errores); se guarda tal cual y se avisa.
    Un RUT válido se normaliza (``12345678-5``).
    """

    SECCIONES = (
        ('Identificación', 'Nombre, tipo y contacto de la organización.',
         ('nombre', 'tipo', 'telefono', 'correo', 'descripcion')),
        ('Ubicación', 'Delegación municipal y territorio donde funciona.',
         ('delegacion', 'territorio', 'domicilio_legal')),
        ('Directiva', 'Si registra un cargo, ingrese nombre y RUT de la persona.',
         ('presidente_nombre', 'presidente_rut', 'tesorero_nombre', 'tesorero_rut',
          'secretario_nombre', 'secretario_rut', 'vigencia_directiva_hasta')),
        ('Antecedentes legales', 'Datos del registro de personalidad jurídica.',
         ('registro_personalidad_juridica', 'fecha_constitucion', 'fecha_inscripcion',
          'registro_directiva', 'socios_activos')),
        ('Estado', '', ('verificada', 'activa')),
    )

    territorio = forms.ChoiceField(required=False, label='Territorio')
    presidente_rut = forms.CharField(label='RUT de presidencia', required=False, max_length=14)
    tesorero_rut = forms.CharField(label='RUT de tesorería', required=False, max_length=14)
    secretario_rut = forms.CharField(label='RUT de secretaría', required=False, max_length=14)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.avisos = []
        self.fields['territorio'].widget.attrs.update({
            'class': 'form-select', 'data-territorios-url': reverse('territorios_delegacion'),
        })
        ayudas = {
            'nombre': 'Nombre completo, como figura en el registro. Ej.: Junta de Vecinos Villa El Faro.',
            'tipo': 'Clasifique la organización para filtrar y reportar.',
            'telefono': 'Celular o fijo de contacto. Ej.: +56 9 1234 5678.',
            'correo': 'Correo de contacto de la directiva (opcional).',
            'descripcion': 'Qué hace la organización: talleres, proyectos, horarios de reunión.',
            'delegacion': 'La delegación municipal que atiende el sector.',
            'territorio': 'Depende de la delegación elegida.',
            'domicilio_legal': 'Dirección de la sede o del domicilio legal.',
            'vigencia_directiva_hasta': 'Fecha en que vence el periodo de la directiva.',
            'registro_personalidad_juridica': 'Número del registro de personalidad jurídica (Ley 19.418).',
            'socios_activos': 'Cantidad de socios al día.',
            'verificada': 'Márquelo solo después de revisar los datos con documentos.',
            'activa': 'Desmárquelo si la organización dejó de funcionar.',
        }
        for campo, texto in ayudas.items():
            if campo in self.fields:
                self.fields[campo].help_text = texto
        marcas = {
            'nombre': {'placeholder': 'Junta de Vecinos …', 'autocomplete': 'organization', 'maxlength': '255'},
            'telefono': {'placeholder': '+56 9 1234 5678', 'inputmode': 'tel', 'autocomplete': 'tel',
                         'data-regla': 'telefono-libre', 'maxlength': '20'},
            'correo': {'placeholder': 'directiva@correo.cl', 'autocomplete': 'email'},
            'domicilio_legal': {'placeholder': 'Calle, número, villa o población'},
            'registro_personalidad_juridica': {'placeholder': 'Ej.: 1234'},
            'registro_directiva': {'placeholder': 'Ej.: 5678'},
            'socios_activos': {'min': '1', 'inputmode': 'numeric'},
        }
        for cargo in ('presidente', 'tesorero', 'secretario'):
            marcas[f'{cargo}_nombre'] = {'placeholder': 'Nombre y apellido', 'autocomplete': 'off'}
            marcas[f'{cargo}_rut'] = {'placeholder': '12.345.678-5', 'data-regla': 'rut-aviso',
                                      'inputmode': 'text', 'autocomplete': 'off', 'maxlength': '14'}
        for campo, attrs in marcas.items():
            if campo in self.fields:
                self.fields[campo].widget.attrs.update(attrs)
        self.fields['tipo'].empty_label = None
        self.fields['tipo'].choices = [('', 'Seleccione el tipo…')] + list(OrganizacionComunitaria.Tipo.choices)
        hoy = timezone.localdate().isoformat()
        for campo in ('fecha_constitucion', 'fecha_inscripcion'):
            self.fields[campo].widget.attrs['max'] = hoy
        self.configurar_territorios()

    def secciones(self):
        for titulo, ayuda, campos in self.SECCIONES:
            yield {'titulo': titulo, 'ayuda': ayuda, 'campos': [self[c] for c in campos if c in self.fields]}

    def configurar_territorios(self):
        delegacion = self.fields['delegacion']
        if self.is_bound:
            id_delegacion = self.data.get(self.add_prefix('delegacion'))
        else:
            id_delegacion = self.instance.delegacion_id or self.initial.get('delegacion')
        try:
            id_delegacion = int(id_delegacion)
            if not 0 < id_delegacion < 2 ** 63 or not delegacion.queryset.filter(pk=id_delegacion).exists():
                id_delegacion = None
        except (TypeError, ValueError):
            id_delegacion = None
        opciones = list(territorios_de(id_delegacion)) if id_delegacion else []
        # Mismos textos que territorios-organizacion.js para que el estado vacío no cambie al recargar.
        if not id_delegacion:
            vacio = 'Seleccione una delegación'
        elif opciones:
            vacio = 'Seleccione un territorio'
        else:
            vacio = 'Esta delegación aún no tiene territorios'
        choices = [('', vacio)]
        choices.extend((nombre, nombre) for nombre in opciones)
        actual = (self.instance.territorio or '').strip()
        # Un texto importado que no está en ningún catálogo se conserva siempre (no se pierde al
        # corregir otro campo). Un territorio del catálogo solo vale en su propia delegación.
        legado = bool(actual) and not TerritorioDelegacion.objects.filter(nombre=actual).exists()
        misma = id_delegacion == self.instance.delegacion_id
        if self.instance.pk and actual and actual not in opciones and (legado or misma):
            choices.append((actual, f'{actual} (registro anterior)'))
        self.fields['territorio'].choices = choices
        self.fields['territorio'].widget.attrs['data-actual'] = actual if legado else ''

    def clean_nombre(self):
        nombre = ' '.join((self.cleaned_data.get('nombre') or '').split())
        if len(nombre) < 3:
            raise forms.ValidationError('Ingrese el nombre de la organización (al menos 3 caracteres).')
        return nombre

    def clean_telefono(self):
        valor = (self.cleaned_data.get('telefono') or '').strip()
        if not valor:
            return None
        normal = normalizar_telefono(valor)
        if not normal:
            raise forms.ValidationError('Ingrese un teléfono chileno de 9 dígitos. Ej.: +56 9 1234 5678 o +56 51 234 5678.')
        return normal

    def clean_correo(self):
        return (self.cleaned_data.get('correo') or '').strip().lower() or None

    def clean_socios_activos(self):
        socios = self.cleaned_data.get('socios_activos')
        if socios is not None and socios < 1:
            raise forms.ValidationError('Si informa socios activos, debe ser al menos 1.')
        return socios

    def clean(self):
        data = super().clean()
        hoy = timezone.localdate()
        constitucion, inscripcion = data.get('fecha_constitucion'), data.get('fecha_inscripcion')
        if constitucion and constitucion > hoy:
            self.add_error('fecha_constitucion', 'La fecha de constitución no puede ser futura.')
        if inscripcion and inscripcion > hoy:
            self.add_error('fecha_inscripcion', 'La fecha de inscripción no puede ser futura.')
        if constitucion and inscripcion and inscripcion < constitucion:
            self.add_error('fecha_inscripcion', 'La inscripción no puede ser anterior a la constitución.')
        vigencia = data.get('vigencia_directiva_hasta')
        if vigencia and vigencia < hoy:
            self.avisos.append(f'La directiva figura vencida desde el {vigencia:%d/%m/%Y}.')

        nombre, delegacion = data.get('nombre'), data.get('delegacion')
        if nombre:
            repetida = OrganizacionComunitaria.objects.filter(nombre__iexact=nombre, delegacion=delegacion)
            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)
            cambio = not self.instance.pk or {'nombre', 'delegacion'} & set(self.changed_data)
            otra = repetida.first() if cambio else None
            if otra is not None:
                self.add_error('nombre', f'Ya existe «{otra.nombre}» ({otra.codigo}) en esa delegación. '
                                         'Revise si es la misma organización antes de crear otra.')

        ruts = set()
        for cargo, etiqueta in (('presidente', 'presidencia'), ('tesorero', 'tesorería'), ('secretario', 'secretaría')):
            nombre_key, rut_key = f'{cargo}_nombre', f'{cargo}_rut'
            persona = ' '.join((data.get(nombre_key) or '').split())
            rut = (data.get(rut_key) or '').strip()
            data[nombre_key] = persona or None
            if bool(persona) != bool(rut):
                self.add_error(rut_key if persona else nombre_key, 'Ingrese el nombre y el RUT de la persona.')
            if persona and not validar_nombre(persona):
                self.add_error(nombre_key, MENSAJE_NOMBRE)
            if not rut:
                data[rut_key] = None
                continue
            if not re.fullmatch(r'[0-9kK.\-\s]{1,14}', rut) or not any(c.isdigit() for c in rut):
                self.add_error(rut_key, 'Ingrese un RUT (solo números, puntos, guion y K).')
                continue
            canonico = rut_canonico(rut)
            if canonico:
                rut = canonico
            else:
                rut = re.sub(r'[.\s]', '', rut).upper()
                self.avisos.append(f'El RUT de {etiqueta} ({rut}) no tiene un dígito verificador válido; '
                                   'se guardó tal cual, revíselo con la ficha.')
            if len(rut) > 12:  # largo del campo en la base de datos
                self.add_error(rut_key, 'El RUT es demasiado largo (máximo 12 caracteres sin puntos).')
                continue
            if rut in ruts:
                self.add_error(rut_key, 'Esta persona ya tiene un cargo en la directiva.')
                continue
            ruts.add(rut)
            data[rut_key] = rut
        return data

    class Meta:
        model = OrganizacionComunitaria
        fields = ['nombre', 'tipo', 'telefono', 'correo', 'descripcion', 'domicilio_legal', 'delegacion', 'territorio',
                  'presidente_nombre', 'presidente_rut', 'tesorero_nombre', 'tesorero_rut', 'secretario_nombre',
                  'secretario_rut', 'vigencia_directiva_hasta', 'socios_activos', 'fecha_constitucion',
                  'registro_personalidad_juridica', 'fecha_inscripcion', 'registro_directiva', 'verificada', 'activa']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_constitucion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_inscripcion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'vigencia_directiva_hasta': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'correo': forms.EmailInput(),
        }
