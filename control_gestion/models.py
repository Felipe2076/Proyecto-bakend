"""Modelos de control de gestión: metas, matriz SGR, actividades, compromisos, agenda y notificaciones."""
import uuid

from django.core.validators import MaxValueValidator
from django.db import models
from core.sincronizacion import SincronizableMixin
from core.codigos import CodigoAutomaticoMixin
from django.utils import timezone

from cuentas.models import Delegacion, Funcionario
from requerimientos.models import Vecino


def validar_evidencia_modelo(archivo):
    from django.core.exceptions import ValidationError
    from control_gestion.evidencias import validar_archivo
    try:
        validar_archivo(archivo)
    except ValueError as error:
        raise ValidationError(str(error))


def ruta_evidencia(instance, filename):
    """Nombre aleatorio: el nombre original del archivo puede contener RUT o nombres."""
    import uuid
    from pathlib import Path
    return f"evidencias/{timezone.localdate():%Y/%m}/{uuid.uuid4().hex}{Path(filename).suffix.lower()[:5]}"


class Meta(CodigoAutomaticoMixin, models.Model):
    """Meta o ítem de gestión (mantenedor Metas del mockup; también ítems de la Matriz SGR)."""

    prefijo_codigo = "META-"
    codigo = models.CharField("código", max_length=20, unique=True, null=True, blank=True, editable=False)
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.CharField("descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "meta"
        verbose_name_plural = "metas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ItemFuncionario(CodigoAutomaticoMixin, models.Model):
    """Meta asignada a un funcionario en el trimestre (ex funcionarios.json -> items)."""

    prefijo_codigo = "ITEM-"
    codigo = models.CharField("código", max_length=20, unique=True, null=True, blank=True, editable=False)
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="items")
    meta = models.ForeignKey(Meta, on_delete=models.PROTECT, related_name="items_funcionario")
    ponderador = models.PositiveSmallIntegerField("ponderador (%)", validators=[MaxValueValidator(100)])
    meta_trimestre = models.PositiveIntegerField("meta del trimestre")
    avance_actual = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "ítem de la matriz SGR"
        verbose_name_plural = "ítems de la matriz SGR"
        ordering = ["funcionario__codigo", "-ponderador"]
        constraints = [
            models.UniqueConstraint(fields=["funcionario", "meta"], name="uniq_item_funcionario_meta"),
        ]

    def __str__(self):
        return f"{self.funcionario.nombre_mostrado}: {self.meta}"

    @property
    def porcentaje_avance(self):
        return min(120.0, round(self.avance_actual * 100 / self.meta_trimestre, 1)) if self.meta_trimestre else 0


class Actividad(CodigoAutomaticoMixin, models.Model):
    """Actividad diaria con verificador (ex actividades.json)."""

    class EstadoRevision(models.TextChoices):
        HISTORICA = 'HISTORICA', 'Registro anterior'
        PENDIENTE = 'PENDIENTE', 'Pendiente de revisión'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'
        CORRECCION = 'CORRECCION', 'Corrección solicitada'

    estado_revision = models.CharField(max_length=16,choices=EstadoRevision.choices,default=EstadoRevision.PENDIENTE,db_default=EstadoRevision.HISTORICA,db_index=True,editable=False)
    version_revision = models.PositiveIntegerField(default=0,db_default=0,editable=False)
    creado_por = models.ForeignKey('auth.User',on_delete=models.SET_NULL,null=True,blank=True,editable=False,related_name='actividades_registradas')
    prefijo_codigo = "ACT-"
    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: ACT-001")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="actividades")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="actividades",
                                   verbose_name="delegación")
    meta = models.ForeignKey(Meta, on_delete=models.PROTECT, related_name="actividades", verbose_name="ítem / meta")
    fecha_actividad = models.DateField(default=timezone.localdate)
    contacto = models.CharField(max_length=150, blank=True)
    servicio = models.CharField(max_length=200)
    codigo_verificador = models.CharField("código verificador", max_length=60, blank=True)
    imagen_verificadora = models.CharField("verificador (imagen/documento)", max_length=200, blank=True)
    tipo_registro = models.CharField(max_length=16, choices=[("RESULTADO","Resultado realizado"),("COORDINACION","Coordinación / seguimiento"),("DELEGADO","Gestión del delegado"),("FELICITACION","Felicitación pendiente de validar")], default="RESULTADO")
    validado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='evidencias_validadas', editable=False)
    fecha_validacion = models.DateTimeField(null=True, blank=True, editable=False)
    evidencia_archivo = models.FileField(upload_to=ruta_evidencia, blank=True, validators=[validar_evidencia_modelo])
    punto_validado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        ordering = ["-fecha_actividad", "codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.servicio}"


    @property
    def nombre_archivo_evidencia(self):
        from pathlib import PurePosixPath
        return PurePosixPath(self.evidencia_archivo.name or '').name


class Compromiso(CodigoAutomaticoMixin, models.Model):
    """Compromiso del tubo de trabajo (ex tubo_trabajo.json)."""

    class Estado(models.TextChoices):
        INGRESADO = "INGRESADO", "Ingresado"
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN PROCESO", "En proceso"
        REALIZADO = "REALIZADO", "Realizado"

    prefijo_codigo = "TUB-"
    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: TUB-001")
    descripcion = models.CharField("descripción", max_length=255)
    vecino = models.ForeignKey(Vecino, on_delete=models.PROTECT, related_name="compromisos")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name="compromisos")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="compromisos",
                                   verbose_name="delegación")
    origen = models.CharField(max_length=3, choices=[('INT','Interno'),('EXT','Externo')], default='EXT')
    territorio = models.CharField(max_length=150, blank=True)
    apoyo = models.CharField('Área o persona de apoyo', max_length=200, blank=True)
    observaciones = models.TextField('Avance y observaciones', blank=True)
    fecha_ingreso = models.DateField(default=timezone.localdate)
    fecha_compromiso = models.DateField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.INGRESADO)

    class Meta:
        verbose_name = "compromiso (tubo de trabajo)"
        verbose_name_plural = "compromisos (tubo de trabajo)"
        ordering = ["fecha_compromiso", "codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class EventoAgenda(CodigoAutomaticoMixin, models.Model):
    """Evento de la agenda colectiva (ex agenda.json)."""

    prefijo_codigo = "AG-"
    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: AG-001")
    titulo = models.CharField("título", max_length=150)
    tipo = models.CharField(max_length=60)
    fecha = models.DateField()
    hora = models.TimeField()
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="eventos",
                                   verbose_name="delegación")
    responsable = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="eventos")
    lugar = models.CharField(max_length=150, blank=True)
    organizacion = models.ForeignKey("OrganizacionComunitaria", on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="eventos", verbose_name="organización")

    class Meta:
        verbose_name = "evento de agenda"
        verbose_name_plural = "agenda"
        ordering = ["fecha", "hora"]

    def __str__(self):
        return f"{self.fecha} {self.hora:%H:%M} - {self.titulo}"


class Medicion(CodigoAutomaticoMixin, models.Model):
    """Periodo de medición trimestral de la Matriz SGR (ex medicion.json)."""

    prefijo_codigo = "MED-"
    codigo = models.CharField("código", max_length=20, unique=True, null=True, blank=True, editable=False)
    periodo = models.CharField(max_length=80, unique=True)
    delegacion_piloto = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="mediciones",
                                          verbose_name="delegación piloto")
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField("fecha término")
    dias_totales = models.PositiveSmallIntegerField(default=90)
    meta_cumplimiento_tubo = models.PositiveSmallIntegerField("meta cumplimiento tubo (%)", default=80,
                                                              validators=[MaxValueValidator(100)])
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "periodo de medición"
        verbose_name_plural = "periodos de medición"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.periodo


class Notificacion(CodigoAutomaticoMixin, models.Model):
    """Aviso interno del sistema (ex notificaciones.json)."""

    class Tipo(models.TextChoices):
        INFO = "info", "Información"
        AVISO = "aviso", "Aviso"
        AGENDA = "agenda", "Agenda"

    prefijo_codigo = "NTF-"
    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: NTF-001")
    titulo = models.CharField("título", max_length=150)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.INFO)
    fecha = models.DateField(default=timezone.localdate)
    enlace = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-fecha"]

    def __str__(self):
        return self.titulo


class Ausencia(models.Model):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='ausencias')
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=[('LICENCIA','Licencia'),('VACACIONES','Vacaciones'),('ADMINISTRATIVO','Día administrativo'),('EMERGENCIA','Emergencia'),('COMPENSATORIO','Compensatorio')])
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    observacion = models.CharField(max_length=255, blank=True)
    class Meta:
        ordering=['-fecha_inicio','funcionario']
        verbose_name='ausencia del funcionario'
        verbose_name_plural='ausencias de funcionarios'
    def __str__(self):
        return f'{self.funcionario}: {self.fecha_inicio} a {self.fecha_termino}'
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fecha_inicio and self.fecha_termino and self.fecha_termino < self.fecha_inicio:
            raise ValidationError({'fecha_termino':'La fecha de término debe ser igual o posterior al inicio.'})
        if self.funcionario_id and self.delegacion_id and self.funcionario.delegacion_id != self.delegacion_id:
            raise ValidationError({'delegacion':'La ausencia debe pertenecer a la delegación del funcionario.'})
        if self.funcionario_id and self.fecha_inicio and self.fecha_termino:
            if Ausencia.objects.filter(funcionario_id=self.funcionario_id,fecha_inicio__lte=self.fecha_termino,fecha_termino__gte=self.fecha_inicio).exclude(pk=self.pk).exists():
                raise ValidationError('Las fechas se superponen con otra ausencia del funcionario.')


class TerritorioDelegacion(SincronizableMixin, models.Model):
    nombre = models.CharField(max_length=150)
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='territorios')

    # Control de sincronización con la app móvil (ver core/sincronizacion.py).
    uuid = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    actualizado = models.DateTimeField("actualizado", null=True, blank=True, editable=False, db_index=True)
    version = models.PositiveIntegerField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'territorio de delegación'
        verbose_name_plural = 'territorios de delegación'
        constraints = [models.UniqueConstraint(fields=['delegacion', 'nombre'], name='territorio_unico_delegacion')]

    def __str__(self):
        return self.nombre


class OrganizacionComunitaria(SincronizableMixin, CodigoAutomaticoMixin, models.Model):
    class Tipo(models.TextChoices):
        JUNTA_VECINOS = 'JJVV', 'Junta de vecinos'
        FUNCIONAL = 'FUNCIONAL', 'Organización funcional'
        CLUB_DEPORTIVO = 'DEPORTIVA', 'Club deportivo'
        ADULTO_MAYOR = 'ADULTO_MAYOR', 'Club de adulto mayor'
        CULTURAL = 'CULTURAL', 'Agrupación cultural'
        OTRA = 'OTRA', 'Otra'

    prefijo_codigo='ORG-'
    codigo=models.CharField("código",max_length=30,unique=True,blank=True,editable=False)
    clave_origen=models.CharField(max_length=100,unique=True,null=True,blank=True,editable=False)
    nombre=models.CharField("nombre de la organización",max_length=255)
    tipo = models.CharField("tipo de organización", max_length=20, choices=Tipo.choices, null=True, blank=True)
    telefono = models.CharField("teléfono de contacto", max_length=20, null=True, blank=True)
    correo = models.EmailField("correo de contacto", max_length=254, null=True, blank=True)
    vigencia_directiva_hasta = models.DateField("directiva vigente hasta", null=True, blank=True)
    eliminado_en = models.DateTimeField("dada de baja el", null=True, blank=True, editable=False)
    descripcion = models.TextField("actividades y descripción", blank=True, null=True, max_length=4000)
    presidente_nombre = models.CharField('nombre de presidencia', max_length=150, blank=True, null=True)
    presidente_rut = models.CharField('RUT de presidencia', max_length=12, blank=True, null=True)
    tesorero_nombre = models.CharField('nombre de tesorería', max_length=150, blank=True, null=True)
    tesorero_rut = models.CharField('RUT de tesorería', max_length=12, blank=True, null=True)
    secretario_nombre = models.CharField('nombre de secretaría', max_length=150, blank=True, null=True)
    secretario_rut = models.CharField('RUT de secretaría', max_length=12, blank=True, null=True)

    @property
    def directiva(self):
        cargos = (('Presidente/a', self.presidente_nombre, self.presidente_rut),
                  ('Tesorero/a', self.tesorero_nombre, self.tesorero_rut),
                  ('Secretario/a', self.secretario_nombre, self.secretario_rut))
        return [cargo for cargo in cargos if cargo[1] or cargo[2]]
    domicilio_legal=models.CharField("domicilio legal",max_length=255,blank=True)
    territorio=models.CharField("territorio",max_length=150,blank=True)
    delegacion=models.ForeignKey(Delegacion,on_delete=models.PROTECT,null=True,blank=True,verbose_name="delegación")
    socios_activos=models.PositiveIntegerField("socios activos",null=True,blank=True)
    fecha_constitucion=models.DateField("fecha de constitución",null=True,blank=True)
    registro_personalidad_juridica=models.CharField("N° de personalidad jurídica",max_length=60,blank=True)
    fecha_inscripcion=models.DateField("fecha de inscripción",null=True,blank=True)
    registro_directiva=models.CharField("N° de registro de la directiva",max_length=60,blank=True)
    verificada=models.BooleanField("datos verificados",default=False)
    activa=models.BooleanField("activa",default=True)
    # Control de sincronización con la app móvil (ver core/sincronizacion.py).
    uuid = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    actualizado = models.DateTimeField("actualizado", null=True, blank=True, editable=False, db_index=True)
    version = models.PositiveIntegerField(null=True, blank=True, editable=False)

    class Meta:
        ordering=['nombre','pk']
        verbose_name='organización comunitaria'
        verbose_name_plural='organizaciones comunitarias'
    def __str__(self):return self.nombre


class RevisionActividad(models.Model):
    actividad = models.ForeignKey(Actividad,on_delete=models.PROTECT,related_name='revisiones')
    autor = models.ForeignKey('auth.User',on_delete=models.PROTECT)
    estado_anterior = models.CharField(max_length=16,choices=Actividad.EstadoRevision.choices)
    estado_nuevo = models.CharField(max_length=16,choices=Actividad.EstadoRevision.choices)
    comentario = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField()
    class Meta:
        ordering=['version']
        constraints=[models.UniqueConstraint(fields=['actividad','version'],name='revision_actividad_version')]


class SesionMovil(models.Model):
    usuario = models.ForeignKey('cuentas.Usuario',on_delete=models.CASCADE)
    huella = models.CharField(max_length=64,unique=True)
    clave_version = models.CharField(max_length=64)
    expira = models.DateTimeField(db_index=True)
    # Datos del dispositivo para que la persona vea y cierre sus sesiones abiertas.
    dispositivo = models.CharField(max_length=120, null=True, blank=True)
    creado = models.DateTimeField(null=True, blank=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)


class IntentosMovil(models.Model):
    clave = models.CharField(max_length=64,primary_key=True)
    inicio = models.DateTimeField(db_index=True)
    intentos = models.PositiveSmallIntegerField(default=0)


class EnvioMovil(models.Model):
    usuario = models.ForeignKey('auth.User',on_delete=models.CASCADE)
    client_id = models.UUIDField()
    huella = models.CharField(max_length=64)
    actividad = models.ForeignKey(Actividad,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['usuario','client_id'],name='envio_movil_idempotente')]


class EnvioOrganizacionMovil(models.Model):
    """Alta de organización desde el teléfono: el mismo client_id nunca crea dos fichas."""
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    client_id = models.UUIDField()
    huella = models.CharField(max_length=64)
    organizacion = models.ForeignKey('OrganizacionComunitaria', on_delete=models.CASCADE)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'client_id'], name='envio_organizacion_idempotente')]


def ruta_evidencia_compromiso(instancia, nombre):
    from pathlib import PurePosixPath
    ext = PurePosixPath(nombre).suffix.lower()[:6]
    return f"evidencias/compromisos/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class EvidenciaCompromiso(models.Model):
    """Foto o documento que respalda el avance de un compromiso (subido desde la web o la app)."""
    compromiso = models.ForeignKey(Compromiso, on_delete=models.CASCADE, related_name='evidencias')
    archivo = models.FileField(upload_to=ruta_evidencia_compromiso, max_length=150)
    tipo = models.CharField(max_length=10)  # FOTO o DOCUMENTO
    descripcion = models.CharField(max_length=200, blank=True)
    subido_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'evidencia de compromiso'
        verbose_name_plural = 'evidencias de compromisos'


class CambioCompromiso(models.Model):
    compromiso = models.ForeignKey(Compromiso,on_delete=models.CASCADE,related_name='cambios_movil')
    autor = models.ForeignKey('auth.User',on_delete=models.PROTECT)
    estado_anterior = models.CharField(max_length=12)
    estado_nuevo = models.CharField(max_length=12)
    observacion_anterior = models.TextField(blank=True)
    observacion_nueva = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)


class RegistroBaja(models.Model):
    """Constancia de una fila eliminada, para que la app móvil también la quite de su SQLite."""

    modelo = models.CharField(max_length=60, db_index=True)
    uuid = models.UUIDField()
    codigo = models.CharField(max_length=40, blank=True)
    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'registro de baja'
        verbose_name_plural = 'registros de baja'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.modelo} {self.codigo}'
