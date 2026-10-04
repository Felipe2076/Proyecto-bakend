"""Identidades ficticias de la prioridad 1 (rango 33.xxx.xxx).

Las claves no viven en el repositorio. ``importar_json`` genera una distinta
por cuenta y la escribe solo en ``.demo_credentials.local``. La variable
``SIGED_DEMO_PASSWORD`` es opcional y solo para pruebas locales: si está
definida, todas las cuentas de esa ejecución usan ese único valor, y tampoco
se imprime.
"""

import os
import secrets

from core.validaciones import dv_rut

ARCHIVO_CLAVES_LOCAL = ".demo_credentials.local"

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
    """Nombres genéricos y estables. No incluyen la marca de simulación."""
    nombres = NOMBRES[(indice - 1) % len(NOMBRES)]
    paterno = APELLIDOS[((indice - 1) // len(NOMBRES)) % len(APELLIDOS)]
    materno = APELLIDOS[(indice * 3 + 4) % len(APELLIDOS)]
    if materno == paterno:
        materno = APELLIDOS[(APELLIDOS.index(materno) + 1) % len(APELLIDOS)]
    return nombres, paterno, materno


def nombre_almacenado(nombres: str, paterno: str, materno: str = "") -> str:
    """Texto que se guarda: sin paréntesis y sin la marca de simulación."""
    base = " ".join(parte for parte in (nombres, paterno, materno) if parte)
    return base.replace("(ficticio)", "").strip()[:120]


def nombre_visible(nombres: str, paterno: str, materno: str = "", ficticio: bool = False) -> str:
    """Compatibilidad: el nombre almacenado. La marca se agrega al mostrar."""
    return nombre_almacenado(nombres, paterno, materno)


def con_marca(nombre: str, es_simulacion: bool = False) -> str:
    """Nombre para pantalla, admin o exportación. No se persiste así."""
    base = " ".join((nombre or "").replace("(ficticio)", "").split())
    if es_simulacion and base:
        return f"{base} (ficticio)"[:120]
    return base[:120]


def clave_compartida_de_prueba() -> str:
    """Valor opcional de ``SIGED_DEMO_PASSWORD``. Vacío si no está definida."""
    return os.environ.get("SIGED_DEMO_PASSWORD", "").strip()


def nueva_clave_simulacion(compartida: str = "") -> str:
    """Una clave por cuenta, o la de prueba si el entorno la definió."""
    if compartida:
        return compartida
    return secrets.token_urlsafe(18)


def escribir_claves_locales(filas) -> str:
    """Escribe RUT, código y clave en un archivo local modo 0600. No imprime valores."""
    from pathlib import Path

    from django.conf import settings

    ruta = Path(settings.BASE_DIR) / ARCHIVO_CLAVES_LOCAL
    lineas = [
        "# Generado por importar_json. No versionar y no imprimir.",
        "rut\tcodigo\tclave",
    ]
    for rut, codigo, clave in filas:
        lineas.append(f"{rut}\t{codigo}\t{clave}")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.chmod(ruta, 0o600)
    return ruta.name


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
