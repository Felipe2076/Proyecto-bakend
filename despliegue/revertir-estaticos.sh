#!/usr/bin/env bash
# Deshace corregir-estaticos.sh: devuelve permisos y settings.py tal como estaban.
# Uso: bash ~/revertir-estaticos.sh ~/respaldos-siged/estaticos-AAAAMMDD-HHMMSS
set -euo pipefail
R="${1:?Indique la carpeta de respaldo}"
. "$R/datos.env"
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo"

echo "==> Restaurando settings.py y la prueba"
sudo cp -p "$R/settings.py" "$APP/config/settings.py"
[ -f "$R/tests_seguridad.py" ] && sudo cp -p "$R/tests_seguridad.py" "$APP/core/tests_seguridad.py"

echo "==> Reconstruyendo y reiniciando $WEB"
cd "$COMPOSE_DIR"
if $SUDO $DC config | awk -v s="  $WEB:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:/{found=1} END{exit !found}'; then $SUDO $DC build "$WEB"; fi
$SUDO $DC up -d --no-deps "$WEB"
sleep 10

echo "==> Restaurando permisos anteriores dentro de $ALIAS"
while IFS=$'\t' read -r modo ruta; do
    case "$ruta" in "$ALIAS"|"$ALIAS"/*) [ -e "$ruta" ] && sudo chmod "$modo" "$ruta" ;; esac
done < "$R/permisos-estaticos.tsv"
echo "Listo. Ojo: con los permisos anteriores los estilos vuelven a responder 403."
