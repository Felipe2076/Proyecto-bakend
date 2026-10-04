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
    """Persona trabajadora: RUT, nombre y delegación viven en esta fila.

    ``nombre`` se conserva como texto compuesto para las pantallas actuales.
    El identificador de acceso es ``rut`` (normalizado, sin puntos).
    """

    codigo = models.CharField("código", max_length=20, unique=True, help_text="Ej: FUN-001")
    rut = models.CharField(
        "RUT",
        max_length=10,
        help_text="Normalizado, sin puntos. Ejemplo visible: 33.100.001-9.",
    )
    nombres = models.CharField(max_length=60)
    apellido_paterno = models.CharField("apellido paterno", max_length=60)
    apellido_materno = models.CharField("apellido materno", max_length=60, null=True, blank=True)
    nombre = models.CharField(max_length=120)
    es_simulacion = models.BooleanField("dato de simulación", default=False)
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name="funcionarios")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="funcionarios",
                                   verbose_name="delegación")
    fecha_ultimo_ingreso = models.DateField("fecha último ingreso", null=True, blank=True)
    estado = models.CharField(max_length=10, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)

    class Meta:
        verbose_name = "funcionario"
        verbose_name_plural = "funcionarios"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(fields=["rut"], name="uq_funcionario_rut"),
        ]
        indexes = [
            models.Index(
                fields=["delegacion", "apellido_paterno", "nombres"],
                name="idx_fun_deleg_apellido",
            ),
        ]

    def __str__(self):
        return f"{self.nombre_mostrado} ({self.codigo})"

    @property
    def nombre_completo(self):
        """Nombre compuesto que se guarda, sin la marca de simulación."""
        from cuentas.simulacion import nombre_almacenado

        return nombre_almacenado(self.nombres, self.apellido_paterno, self.apellido_materno or "")

    @property
    def nombre_mostrado(self):
        from cuentas.simulacion import con_marca

        return con_marca(self.nombre, self.es_simulacion)

    def clean(self):
        from django.core.exceptions import ValidationError

        from core.validaciones import MENSAJE_NOMBRE, MENSAJE_RUT, normalizar_rut, validar_nombre, validar_rut

        self.rut = normalizar_rut(self.rut or "")
        if not validar_rut(self.rut):
            raise ValidationError({"rut": MENSAJE_RUT})
        self.nombres = " ".join((self.nombres or "").split())
        self.apellido_paterno = " ".join((self.apellido_paterno or "").split())
        if self.apellido_materno:
            self.apellido_materno = " ".join(self.apellido_materno.split()) or None
        errores = {}
        for campo in ("nombres", "apellido_paterno", "apellido_materno"):
            valor = getattr(self, campo) or ""
            if valor and not validar_nombre(valor):
                errores[campo] = MENSAJE_NOMBRE
        if self.nombre and not validar_nombre(" ".join(self.nombre.replace("(ficticio)", "").split())):
            errores["nombre"] = MENSAJE_NOMBRE
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from core.validaciones import MENSAJE_NOMBRE

        if not (self.nombres or "").strip() and self.nombre:
            limpio = self.nombre.replace("(ficticio)", "").strip()
            partes = limpio.split()
            self.nombres = (partes[0] if partes else "Sin")[:60]
            self.apellido_paterno = (partes[1] if len(partes) > 1 else "Registro")[:60]
            if len(partes) > 2 and not self.apellido_materno:
                self.apellido_materno = " ".join(partes[2:])[:60]
        if (self.nombres or "").strip() and (self.apellido_paterno or "").strip():
            self.nombre = self.nombre_completo[:120]
        else:
            self.nombre = " ".join((self.nombre or "").replace("(ficticio)", "").split())[:120]
        if "(" in (self.nombre or "") or ")" in (self.nombre or ""):
            raise ValidationError({"nombre": MENSAJE_NOMBRE})
        super().save(*args, **kwargs)


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
    funcionario = models.OneToOneField(Funcionario, on_delete=models.PROTECT, related_name="usuario")
    estado = models.CharField(max_length=10, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre_mostrado} ({self.username})"

    @property
    def nombre_mostrado(self):
        """La marca sale del funcionario. Esta tabla no tiene columna propia."""
        from cuentas.simulacion import con_marca

        es_simulacion = bool(self.funcionario_id and self.funcionario.es_simulacion)
        return con_marca(self.nombre, es_simulacion)

    @property
    def activo(self):
        return self.estado == EstadoRegistro.ACTIVO

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        from core.validaciones import MENSAJE_NOMBRE

        self.nombre = " ".join((self.nombre or "").replace("(ficticio)", "").split())[:120]
        if "(" in self.nombre or ")" in self.nombre:
            raise ValidationError({"nombre": MENSAJE_NOMBRE})
        super().save(*args, **kwargs)


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


class CodigoRecuperacion(models.Model):
    """Código de un solo uso para recuperar la clave. Solo se guarda el hash."""

    MAX_INTENTOS = 5
    VIGENCIA_MINUTOS = 10

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="codigos_recuperacion", db_index=False,
    )
    codigo_hash = models.CharField("hash del código", max_length=128)
    expira = models.DateTimeField()
    intentos = models.PositiveSmallIntegerField(default=0)
    usado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "código de recuperación"
        verbose_name_plural = "códigos de recuperación"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["usuario", "usado"], name="idx_recup_usuario_usado"),
        ]

    def __str__(self):
        estado = "usado" if self.usado else "vigente"
        return f"recuperación {self.usuario_id} ({estado})"
