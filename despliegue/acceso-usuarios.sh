#!/usr/bin/env bash
# Diagnóstico y restablecimiento de acceso en el servidor (se ejecuta en la EC2).
#   bash ~/acceso-usuarios.sh diagnostico 33.100.001-9    -> solo lectura: por qué no entra ese RUT
#   bash ~/acceso-usuarios.sh clave todos                 -> misma clave a TODAS las cuentas con perfil
#   bash ~/acceso-usuarios.sh clave 33.100.001-9          -> clave solo a ese RUT
# La clave se escribe en la terminal (oculta). No se guarda en archivos, historial ni argumentos.
# Con "clave" primero muestra un resumen y pide escribir SI antes de cambiar nada.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"  # antes de cualquier cd: $0 puede ser relativo
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo -E"  # -E: sudo limpia el entorno y la clave llega por variable
MODO="${1:-}"; ALCANCE="${2:-}"
[ -n "$MODO" ] && [ -n "$ALCANCE" ] || { sed -n 2,8p "$0"; exit 1; }

ULTIMO="$(ls -1dt "$HOME"/respaldos-siged/*/datos.env 2>/dev/null | head -1 || true)"
if [ -z "${COMPOSE_DIR:-}" ] && [ -n "$ULTIMO" ]; then . "$ULTIMO"; fi
[ -n "${COMPOSE_DIR:-}" ] && [ -n "${WEB:-}" ] || { echo "Defina COMPOSE_DIR= y WEB= (no hay despliegue previo con datos guardados)." >&2; exit 1; }
cd "$COMPOSE_DIR"
ejecutar() { # $1 = archivo .py ; variables ya exportadas
    $SUDO $DC exec -T -e RUT_DIAG -e NUEVA_CLAVE -e APLICAR -e SOLO_RUT "$WEB" python manage.py shell -c "$(cat "$1")" 2>&1 | grep -v "objects imported automatically"
}

case "$MODO" in
  diagnostico)
    export RUT_DIAG="$ALCANCE"; ejecutar "$AQUI/diagnostico_acceso.py" ;;
  clave)
    if [ "$ALCANCE" = "todos" ]; then unset SOLO_RUT; else export SOLO_RUT="$ALCANCE"; fi
    read -rsp "Nueva clave (no se verá): " NUEVA_CLAVE; echo
    read -rsp "Repítala: " REPETIDA; echo
    [ "$NUEVA_CLAVE" = "$REPETIDA" ] || { echo "No coinciden. No se cambió nada." >&2; exit 1; }
    unset REPETIDA; export NUEVA_CLAVE
    APLICAR=0; export APLICAR
    echo; ejecutar "$AQUI/clave_prototipo.py"
    echo
    read -rp "Escriba SI (en mayúsculas) para aplicar el cambio: " OK
    [ "$OK" = "SI" ] || { echo "Cancelado. No se cambió nada."; unset NUEVA_CLAVE; exit 0; }
    APLICAR=1; export APLICAR
    ejecutar "$AQUI/clave_prototipo.py"
    unset NUEVA_CLAVE ;;
  *) sed -n 2,8p "$0"; exit 1 ;;
esac
