"""Modelos de atención ciudadana: vecinos, tipos de gestión/atención, requerimientos y atenciones."""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from cuentas.models import Delegacion, EstadoRegistro, Funcionario, Usuario


class TipoGestion(models.Model):
    """Tipo de gestión / entrada del vecino (Solicitud, Reclamo, Consulta, ...)."""

    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField("descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "tipo de gestión"
        verbose_name_plural = "tipos de gestión"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Vecino(models.Model):
    """Vecino o vecina (o junta de vecinos) atendido por la municipalidad."""

    nombre = models.CharField(max_length=120)
    rut = models.CharField("RUT", max_length=12, unique=True, null=True, blank=True,
                           help_text="Normalizado o con puntos. Ejemplo: 33.500.001-3. Vacío si no se registró.")
    direccion = models.CharField("dirección", max_length=200, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    territorio = models.CharField(max_length=60, blank=True, help_text="Sector (Centro, Norte, Sur...)")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="vecinos", verbose_name="delegación")
    tipo_gestion = models.ForeignKey(TipoGestion, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="vecinos", verbose_name="tipo de gestión")
    es_simulacion = models.BooleanField("dato de simulación", default=False)
    estado = models.CharField(max_length=10, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    # Nacionalidad: se pregunta al registrar. Vacío = no se preguntó (fichas antiguas).
    es_extranjero = models.BooleanField("¿es extranjero/a?", null=True, blank=True)
    nacionalidad = models.CharField("país de origen", max_length=60, null=True, blank=True,
                                    help_text="Solo si es extranjero/a. Ej.: Venezuela, Perú, Haití.")

    class Meta:
        verbose_name = "vecino"
        verbose_name_plural = "vecinos"
        ordering = ["nombre"]

    def __str__(self):
        visible = self.nombre_mostrado
        return f"{visible} ({self.rut})" if self.rut else visible

    @property
    def nombre_mostrado(self):
        from cuentas.simulacion import con_marca

        return con_marca(self.nombre, self.es_simulacion)

    def clean(self):
        from django.core.exceptions import ValidationError

        from core.validaciones import MENSAJE_NOMBRE

        # El nombre de una organización puede llevar dígitos. El patrón de persona
        # no aplica aquí; sí se rechazan los paréntesis de la marca de simulación.
        self.nombre = " ".join((self.nombre or "").replace("(ficticio)", "").split())
        if "(" in self.nombre or ")" in self.nombre:
            raise ValidationError({"nombre": MENSAJE_NOMBRE})

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from core.validaciones import MENSAJE_NOMBRE

        self.nombre = " ".join((self.nombre or "").replace("(ficticio)", "").split())[:120]
        if "(" in self.nombre or ")" in self.nombre:
            raise ValidationError({"nombre": MENSAJE_NOMBRE})
        super().save(*args, **kwargs)


class TipoAtencion(models.Model):
    """Tipo de atención (Social, Salud, Educación, Vivienda)."""

    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField("descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "tipo de atención"
        verbose_name_plural = "tipos de atención"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class SubAtencion(models.Model):
    """Sub-tipo de atención, pertenece a un tipo de atención."""

    nombre = models.CharField(max_length=100)
    tipo_atencion = models.ForeignKey(TipoAtencion, on_delete=models.CASCADE, related_name="sub_atenciones",
                                      verbose_name="tipo de atención")
    descripcion = models.CharField("descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "sub atención"
        verbose_name_plural = "sub atenciones"
        ordering = ["tipo_atencion__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["tipo_atencion", "nombre"], name="uniq_subatencion_por_tipo"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.tipo_atencion})"


class CanalIngreso(models.Model):
    """Canal por el que ingresa un requerimiento (ventanilla, WhatsApp, correo)."""

    nombre = models.CharField(max_length=40, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "canal de ingreso"
        verbose_name_plural = "canales de ingreso"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class AreaSoporte(models.Model):
    """Área temática / de soporte que resuelve requerimientos (ex areas_soporte.json)."""

    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: AREA-001")
    nombre = models.CharField(max_length=120, unique=True)
    encargado = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="areas_a_cargo")
    encargado_nombre = models.CharField("nombre encargado", max_length=120, blank=True,
                                        help_text="Texto libre si el encargado no es funcionario registrado.")
    tiempo_promedio_dias = models.DecimalField("tiempo promedio (días)", max_digits=5, decimal_places=1, default=0)
    total_casos_mes = models.PositiveIntegerField(default=0)
    porcentaje_cumplimiento = models.PositiveSmallIntegerField("% cumplimiento", default=0,
                                                               validators=[MaxValueValidator(100)])
    satisfaccion_promedio = models.DecimalField(max_digits=3, decimal_places=1, default=0,
                                                validators=[MinValueValidator(0), MaxValueValidator(5)])
    icono = models.CharField(max_length=60, blank=True, help_text="Clase Bootstrap Icons, ej: bi-people-fill")
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "área de soporte"
        verbose_name_plural = "áreas de soporte"
        ordering = ["codigo"]

    def __str__(self):
        return self.nombre


class Requerimiento(models.Model):
    """Ticket SGR ingresado por un vecino (ex requerimientos.json)."""

    class Estado(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        EN_PROCESO = "En Proceso", "En Proceso"
        CUELLO_BOTELLA = "Cuello Botella Central", "Cuello Botella Central"
        RESUELTO = "Resuelto", "Resuelto"

    codigo = models.CharField("ticket", max_length=20, unique=True, help_text="Ej: TK-1001")
    vecino = models.ForeignKey(Vecino, on_delete=models.PROTECT, related_name="requerimientos")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="requerimientos",
                                   verbose_name="delegación")
    canal_ingreso = models.ForeignKey(CanalIngreso, on_delete=models.PROTECT, related_name="requerimientos",
                                      verbose_name="canal de ingreso")
    tipo_gestion = models.ForeignKey(TipoGestion, on_delete=models.PROTECT, related_name="requerimientos",
                                     verbose_name="tipo de entrada")
    area = models.ForeignKey(AreaSoporte, on_delete=models.PROTECT, related_name="requerimientos",
                             verbose_name="área temática")
    descripcion = models.TextField("descripción")
    fecha_ingreso = models.DateField(default=timezone.localdate)
    funcionario = models.ForeignKey(Funcionario, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="requerimientos", verbose_name="funcionario asignado")
    asignado_a = models.CharField("asignado a (texto)", max_length=120, blank=True,
                                  help_text="Cuadrilla o equipo asignado tal como se registró.")
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PENDIENTE)
    evaluacion_satisfaccion = models.PositiveSmallIntegerField(
        "evaluación (1-5)", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario_satisfaccion = models.TextField("comentario satisfacción", blank=True)
    fecha_resolucion = models.DateField("fecha de resolución", null=True, blank=True,
                                        help_text="Se completa sola al pasar a Resuelto.")

    class Meta:
        verbose_name = "requerimiento"
        verbose_name_plural = "requerimientos"
        ordering = ["-fecha_ingreso", "-codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.vecino}"

    @property
    def dias_transcurridos(self):
        """Días de gestión: hasta hoy si sigue abierto; hasta la resolución si se cerró."""
        fin = self.fecha_resolucion if self.estado == self.Estado.RESUELTO and self.fecha_resolucion else timezone.localdate()
        return max(0, (fin - self.fecha_ingreso).days)

    @property
    def resuelto(self):
        return self.estado == self.Estado.RESUELTO

    def save(self, *args, **kwargs):
        # La fecha de resolución acompaña siempre al estado, venga del detalle,
        # del Kanban o de la API, para que un ticket cerrado deje de envejecer.
        if self.estado == self.Estado.RESUELTO and not self.fecha_resolucion:
            self.fecha_resolucion = timezone.localdate()
        elif self.estado != self.Estado.RESUELTO and self.fecha_resolucion:
            self.fecha_resolucion = None
        campos = kwargs.get("update_fields")
        if campos is not None and "estado" in campos and "fecha_resolucion" not in campos:
            kwargs["update_fields"] = list(campos) + ["fecha_resolucion"]
        super().save(*args, **kwargs)


class Atencion(models.Model):
    """Atención ciudadana registrada por un usuario del sistema (mantenedor Atenciones del mockup)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        CERRADA = "cerrada", "Cerrada"

    vecino = models.ForeignKey(Vecino, on_delete=models.PROTECT, related_name="atenciones")
    tipo_atencion = models.ForeignKey(TipoAtencion, on_delete=models.PROTECT, related_name="atenciones",
                                      verbose_name="tipo de atención")
    sub_atencion = models.ForeignKey(SubAtencion, on_delete=models.PROTECT, related_name="atenciones",
                                     verbose_name="sub atención")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="atenciones",
                                   verbose_name="delegación")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="atenciones",
                                verbose_name="registrada por")
    fecha = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    observacion = models.TextField("observación", blank=True)

    class Meta:
        verbose_name = "atención"
        verbose_name_plural = "atenciones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Atención #{self.pk} - {self.vecino} ({self.sub_atencion.nombre})"

    def clean(self):
        if self.sub_atencion_id and self.tipo_atencion_id and \
                self.sub_atencion.tipo_atencion_id != self.tipo_atencion_id:
            raise ValidationError({"sub_atencion": "La sub atención no pertenece al tipo de atención elegido."})


def ruta_evidencia_ticket(instancia, nombre):
    import uuid
    from pathlib import PurePosixPath

    ext = PurePosixPath(nombre).suffix.lower()[:6]
    return f"evidencias/tickets/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class EvidenciaRequerimiento(models.Model):
    """Foto o documento que respalda la gestión de un ticket (se sube desde el tablero o la ficha)."""

    requerimiento = models.ForeignKey(Requerimiento, on_delete=models.CASCADE, related_name="evidencias")
    archivo = models.FileField(upload_to=ruta_evidencia_ticket, max_length=150)
    tipo = models.CharField(max_length=10)  # FOTO o DOCUMENTO
    descripcion = models.CharField(max_length=200, blank=True)
    subido_por = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "evidencia de ticket"
        verbose_name_plural = "evidencias de tickets"
