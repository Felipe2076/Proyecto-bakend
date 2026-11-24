"""Alcance por delegación: solo el superusuario ve todas las delegaciones.

Los demás roles, incluido el administrador, quedan encapsulados en su propia delegación y sus territorios.
"""

ROL_SUPERUSUARIO = 'superusuario'


def es_superusuario(perfil):
    return bool(perfil is not None and getattr(perfil, 'rol_id', None) and perfil.rol.codigo == ROL_SUPERUSUARIO)
