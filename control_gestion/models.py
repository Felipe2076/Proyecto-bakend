"""Modelos de control de gestión: metas, matriz SGR, actividades, compromisos, agenda y notificaciones."""

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from cuentas.models import Delegacion, Funcionario
from requerimientos.models import Vecino


class Meta(models.Model):
    """Meta o ítem de gestión (mantenedor Metas del mockup; también ítems de la Matriz SGR)."""

    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.CharField("descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "meta"
        verbose_name_plural = "metas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ItemFuncionario(models.Model):
    """Meta asignada a un funcionario en el trimestre (ex funcionarios.json -> items)."""

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
        return round(self.avance_actual * 100 / self.meta_trimestre, 1) if self.meta_trimestre else 0


class Actividad(models.Model):
    """Actividad diaria con verificador (ex actividades.json)."""

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
    punto_validado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        ordering = ["-fecha_actividad", "codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.servicio}"


class Compromiso(models.Model):
    """Compromiso del tubo de trabajo (ex tubo_trabajo.json)."""

    class Estado(models.TextChoices):
        INGRESADO = "INGRESADO", "Ingresado"
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN PROCESO", "En proceso"
        REALIZADO = "REALIZADO", "Realizado"

    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: TUB-001")
    descripcion = models.CharField("descripción", max_length=255)
    vecino = models.ForeignKey(Vecino, on_delete=models.PROTECT, related_name="compromisos")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name="compromisos")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="compromisos",
                                   verbose_name="delegación")
    fecha_ingreso = models.DateField(default=timezone.localdate)
    fecha_compromiso = models.DateField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.INGRESADO)

    class Meta:
        verbose_name = "compromiso (tubo de trabajo)"
        verbose_name_plural = "compromisos (tubo de trabajo)"
        ordering = ["fecha_compromiso", "codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class EventoAgenda(models.Model):
    """Evento de la agenda colectiva (ex agenda.json)."""

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

    class Meta:
        verbose_name = "evento de agenda"
        verbose_name_plural = "agenda"
        ordering = ["fecha", "hora"]

    def __str__(self):
        return f"{self.fecha} {self.hora:%H:%M} - {self.titulo}"


class Medicion(models.Model):
    """Periodo de medición trimestral de la Matriz SGR (ex medicion.json)."""

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


class Notificacion(models.Model):
    """Aviso interno del sistema (ex notificaciones.json)."""

    class Tipo(models.TextChoices):
        INFO = "info", "Información"
        AVISO = "aviso", "Aviso"
        AGENDA = "agenda", "Agenda"

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
