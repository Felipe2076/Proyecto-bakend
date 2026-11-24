# Solo lectura. Se ejecuta con: manage.py shell -c "$(cat diagnostico_acceso.py)"  (RUT en RUT_DIAG).
# Autosuficiente: no depende de funciones nuevas del proyecto, así funciona con el código publicado.
# No imprime contraseñas, hashes, correos ni el RUT completo.
import os
import re

from django.contrib.auth import get_user_model

from cuentas.models import Funcionario, Usuario


def _dv(cuerpo):
    suma, factor = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    return {11: "0", 10: "K"}.get(11 - suma % 11, str(11 - suma % 11))


def _canonico(texto):
    limpio = re.sub(r"[.\s-]", "", texto or "").upper()
    if not re.fullmatch(r"\d{7,8}[\dK]", limpio):
        return None
    return f"{limpio[:-1]}-{limpio[-1]}" if _dv(limpio[:-1]) == limpio[-1] else None


def _mask(rut):
    cuerpo, dv = rut.split("-")
    return f"{cuerpo[:2]}.{cuerpo[2]}XX.XXX-{dv}"


entrada = os.environ.get("RUT_DIAG", "")
rut = _canonico(entrada)
if rut is None:
    print("RUT no válido (formato o dígito verificador incorrecto).")
    raise SystemExit
User = get_user_model()
print("RUT:", _mask(rut))

ficha = Funcionario.objects.filter(rut=rut).first()
print("1) Ficha (Funcionario) con ese RUT:", f"sí, estado={ficha.estado}" if ficha else "NO existe  <- el login la exige")

perfil = Usuario.objects.select_related("user", "rol", "delegacion").filter(funcionario__rut=rut).first()
if perfil is None:
    print("2) Perfil de usuario enlazado a esa ficha: NO existe  <- el login falla aquí")
    print("   Perfiles con ese username pero sin esa ficha:", Usuario.objects.filter(username=rut).count())
else:
    print(f"2) Perfil: estado={perfil.estado}, rol={perfil.rol.codigo if perfil.rol_id else 'SIN ROL'}, "
          f"delegación={'sí' if perfil.delegacion_id else 'NO'}")
    if perfil.user_id is None:
        print("3) Cuenta de acceso (auth_user): NO está enlazada  <- el login falla aquí")
    else:
        u = perfil.user
        ultimo = u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "nunca"
        print(f"3) Cuenta de acceso: activa={u.is_active}, clave utilizable={u.has_usable_password()}, "
              f"usuario coincide con el RUT={u.username == rut}, staff={u.is_staff}, último ingreso={ultimo}")
        if not u.has_usable_password():
            print("   -> La cuenta no tiene clave definida (invitación sin activar): hay que fijar una.")
        if not u.is_active or perfil.estado != "activo":
            print("   -> Cuenta inactiva: aunque la clave sea correcta, el login la rechaza.")
print("4) Cuentas de acceso con ese nombre de usuario:", User.objects.filter(username=rut).count())
