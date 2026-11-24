# Fija una misma clave a las cuentas de acceso con perfil de usuario (solo para prototipos).
# Se ejecuta con: manage.py shell -c "$(cat clave_prototipo.py)"
# Variables: NUEVA_CLAVE (obligatoria), APLICAR=1 para escribir (sin eso solo informa), SOLO_RUT (opcional).
# Autosuficiente: no depende de funciones nuevas del proyecto. La clave nunca se imprime ni se escribe
# en un archivo; solo se guarda su hash.
import os
import re
from collections import Counter

from django.contrib.auth.hashers import make_password
from django.db import transaction

from control_gestion.models import IntentosMovil
from cuentas.models import Usuario


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


clave = os.environ.get("NUEVA_CLAVE", "")
aplicar = os.environ.get("APLICAR") == "1"
solo = os.environ.get("SOLO_RUT", "").strip()
if len(clave) < 8:
    raise SystemExit("La clave debe tener al menos 8 caracteres. No se cambió nada.")

perfiles = Usuario.objects.select_related("user", "rol").filter(user__isnull=False)
if solo:
    rut = _canonico(solo)
    if rut is None:
        raise SystemExit("RUT no válido (formato o dígito verificador incorrecto).")
    perfiles = perfiles.filter(funcionario__rut=rut)
perfiles = list(perfiles)
if not perfiles:
    raise SystemExit("Ninguna cuenta coincide. No se cambió nada.")

por_rol = Counter(p.rol.codigo if p.rol_id else "sin rol" for p in perfiles)
inactivas = sum(1 for p in perfiles if not p.user.is_active or p.estado != "activo")
sin_clave = sum(1 for p in perfiles if not p.user.has_usable_password())
print(f"Cuentas a modificar: {len(perfiles)}  (alcance: {'solo ' + _mask(rut) if solo else 'todas'})")
print("  por rol:", dict(por_rol))
print(f"  inactivas (seguirán sin poder entrar): {inactivas}; sin clave definida (quedarán con clave): {sin_clave}")
if not aplicar:
    print("INFORME SOLAMENTE: no se cambió nada.")
else:
    nuevo_hash = make_password(clave)  # un solo hash; la clave en claro no se guarda
    with transaction.atomic():
        for p in perfiles:
            p.user.password = nuevo_hash
        type(perfiles[0].user).objects.bulk_update([p.user for p in perfiles], ["password"])
        borrados = IntentosMovil.objects.all().delete()[0]  # libera cuentas bloqueadas por intentos fallidos
    print(f"LISTO: clave fijada en {len(perfiles)} cuentas; contadores de intentos reiniciados ({borrados}).")
