"""Identidades ficticias de la prioridad 1 (rango 33.xxx.xxx).

La clave de demostración no es un secreto de producción: es la convención
documentada en el README para que cada rol pueda entrar a su panel.
No se escribe en ``data/usuarios.json`` ni en texto plano dentro de D003.
"""

from core.validaciones import dv_rut

CLAVE_DEMO = "Simulacion#2026"
SALT_DEMO = "sigedsim2026"

# Trabajadores 33.100.001–33.100.999; vecinos 33.500.001–33.509.999.
BASE_TRABAJADOR = 33_100_000
BASE_VECINO = 33_500_000

ROLES_ORDEN = ("administrador", "jefatura", "funcionario", "ventanilla")

CARGO_POR_ROL = {
    "administrador": "Administrador del sistema",
    "jefatura": "Delegada Territorial",
    "funcionario": "Gestor Social",
    "ventanilla": "Apoyo Administrativo",
}

NOMBRES = (
    "Alba", "Bruno", "Celia", "Dario", "Elena", "Felix", "Greta", "Hugo", "Iris", "Julio",
    "Kael", "Luna", "Milo", "Nora", "Omar", "Pia", "Quique", "Rita", "Sael", "Tomas",
)
APELLIDOS = (
    "Alamo", "Bravo", "Castro", "Diaz", "Espinosa", "Flores", "Guerra", "Herrera", "Ibanez", "Jara",
    "Keller", "Lago", "Mora", "Nieto", "Olmo", "Paz", "Quilo", "Rios", "Solis", "Toro",
)

CODIGO_ADMIN_GLOBAL = "USR-025"


def rut_de(base: int, indice: int) -> str:
    """``indice`` parte en 1. El cuerpo queda dentro de 33.000.000–33.999.999."""
    numero = base + indice
    if not 33_000_000 <= numero <= 33_999_999:
        raise ValueError(f"RUT de simulación fuera de rango: {numero}")
    return f"{numero}-{dv_rut(str(numero))}"


def rut_trabajador(indice: int) -> str:
    return rut_de(BASE_TRABAJADOR, indice)


def rut_vecino(indice: int) -> str:
    return rut_de(BASE_VECINO, indice)


def identidad(indice: int) -> tuple[str, str, str]:
    """Nombres genéricos, estables, sin azar. El sufijo «(ficticio)» lo agrega el llamador."""
    nombres = NOMBRES[(indice - 1) % len(NOMBRES)]
    paterno = APELLIDOS[((indice - 1) // len(NOMBRES)) % len(APELLIDOS)]
    materno = APELLIDOS[(indice * 3 + 4) % len(APELLIDOS)]
    if materno == paterno:
        materno = APELLIDOS[(APELLIDOS.index(materno) + 1) % len(APELLIDOS)]
    return nombres, paterno, materno


def nombre_visible(nombres: str, paterno: str, materno: str = "", ficticio: bool = True) -> str:
    base = " ".join(parte for parte in (nombres, paterno, materno) if parte)
    if ficticio and "(ficticio)" not in base:
        base = f"{base} (ficticio)"
    return base[:120]


def telefono_ficticio(indice: int) -> str:
    return f"+5690000{indice:04d}"


def correo_funcionario(codigo: str) -> str:
    return f"{codigo.lower()}@siged.test"


def correo_vecino(indice: int) -> str:
    return f"vecino{indice:03d}@siged.test"


def direccion_ficticia(indice: int) -> str:
    return f"Calle Ficticia {indice}"


def es_organizacion(nombre: str) -> bool:
    texto = (nombre or "").strip().lower()
    return texto.startswith(("jjvv", "junta ", "mesa ", "organización", "organizacion"))
