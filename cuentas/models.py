"""Modelos de cuentas: roles, usuarios, cargos, delegaciones, funcionarios y parámetros."""

from django.conf import settings
from django.db import models


class EstadoRegistro(models.TextChoices):
    ACTIVO = "activo", "Activo"
    INACTIVO = "inactivo", "Inactivo"


class Rol(models.Model):
    """Perfil de acceso al sistema (Administrador, Jefatura, Funcionario, Ventanilla)."""

    codigo = models.SlugField("código", max_length=30, unique=True,
                              help_text="Clave usada por el sistema (ej: administrador).")
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField("descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Delegacion(models.Model):
    """Delegación municipal territorial."""

    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    comuna = models.CharField(max_length=80, default="La Serena")

    class Meta:
        verbose_name = "delegación municipal"
        verbose_name_plural = "delegaciones municipales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    """Cargo o función de un funcionario municipal."""

    codigo = models.CharField("código", max_length=20, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField("descripción", max_length=255, blank=True)
    modulo_principal = models.CharField("módulo principal", max_length=80, blank=True)

    class Meta:
        verbose_name = "cargo"
        verbose_name_plural = "cargos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Funcionario(models.Model):
    """Funcionario municipal medido en la Matriz SGR."""

    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: FUN-001")
    nombre = models.CharField(max_length=120)
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name="funcionarios")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="funcionarios",
                                   verbose_name="delegación")
    fecha_ultimo_ingreso = models.DateField("fecha último ingreso", null=True, blank=True)
    estado = models.CharField(max_length=10, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)

    class Meta:
        verbose_name = "funcionario"
        verbose_name_plural = "funcionarios"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Usuario(models.Model):
    """Usuario del sistema. Se enlaza (opcional) con el User de django.contrib.auth."""

    codigo = models.CharField("código", max_length=20, unique=True, null=True, blank=True,
                              help_text="Ej: USR-001")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="perfil", verbose_name="usuario Django")
    username = models.CharField("nombre de usuario", max_length=150, unique=True)
    nombre = models.CharField(max_length=120)
    correo = models.EmailField(unique=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="usuarios")
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="usuarios", verbose_name="delegación")
    funcionario = models.OneToOneField(Funcionario, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="usuario")
    estado = models.CharField(max_length=10, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.username})"

    @property
    def activo(self):
        return self.estado == EstadoRegistro.ACTIVO


class ParametroSistema(models.Model):
    """Parámetros generales del sistema (un solo registro)."""

    nombre_sistema = models.CharField(max_length=120, default="SIGED-SGR Delegaciones La Serena")
    comuna = models.CharField(max_length=80, default="La Serena")
    region = models.CharField("región", max_length=80, default="Región de Coquimbo")
    sla_verde_max_dias = models.PositiveSmallIntegerField("SLA verde (máx. días)", default=3)
    sla_amarillo_max_dias = models.PositiveSmallIntegerField("SLA amarillo (máx. días)", default=5)
    meta_tubo_porcentaje = models.PositiveSmallIntegerField("meta tubo (%)", default=80)
    encuesta_habilitada = models.BooleanField(default=True)
    max_atenciones_mismo_usuario = models.PositiveSmallIntegerField(default=3)

    class Meta:
        verbose_name = "parámetro del sistema"
        verbose_name_plural = "parámetros del sistema"
        ordering = ["id"]

    def __str__(self):
        return self.nombre_sistema
