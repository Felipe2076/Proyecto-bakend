"""Cuentas mínimas para la suite: RUT válido, funcionario y usuario Django."""

from django.contrib.auth import get_user_model

from cuentas.models import Cargo, EstadoRegistro, Funcionario, Rol, Usuario


def crear_cuenta(
    *,
    codigo,
    rut,
    password,
    rol_codigo,
    correo,
    nombre,
    delegacion,
    cargo=None,
    nombres="",
    apellido_paterno="",
):
    """Crea rol, cargo, funcionario y usuario enlazados. El acceso es el RUT."""
    User = get_user_model()
    rol, _creado = Rol.objects.get_or_create(
        codigo=rol_codigo,
        defaults={"nombre": rol_codigo.capitalize(), "descripcion": rol_codigo},
    )
    if cargo is None:
        cargo, _creado = Cargo.objects.get_or_create(nombre="Cargo de prueba")
    partes = nombre.replace("(ficticio)", "").split()
    funcionario = Funcionario.objects.create(
        codigo=f"FUN-{codigo}",
        rut=rut,
        nombres=nombres or (partes[0] if partes else "Persona"),
        apellido_paterno=apellido_paterno or (partes[1] if len(partes) > 1 else "Prueba"),
        nombre=nombre,
        cargo=cargo,
        delegacion=delegacion,
    )
    user = User.objects.create_user(rut, correo, password)
    usuario = Usuario.objects.create(
        codigo=codigo,
        user=user,
        username=rut,
        nombre=funcionario.nombre,
        correo=correo,
        rol=rol,
        cargo=cargo,
        delegacion=delegacion,
        funcionario=funcionario,
        estado=EstadoRegistro.ACTIVO,
    )
    return usuario
