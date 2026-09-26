"""Paquete de configuración principal para SIGED La Serena.

Usa PyMySQL como reemplazo de mysqlclient (driver puro Python, sin compilar
en Windows ni en la instancia EC2).
"""

try:
    import pymysql

    # Django 6.x exige mysqlclient >= 2.2.1; PyMySQL es compatible con esa API.
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover - si se instala mysqlclient no hace falta
    pass
