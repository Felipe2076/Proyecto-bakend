#!/usr/bin/env bash
# Deshace desplegar-alta-docker.sh. Uso: bash ~/revertir-alta-docker.sh ~/respaldos-siged/alta-FECHA
# Si existe env.bak en la carpeta de respaldo (copia del .env hecha antes de fijar APP_IMAGE), también lo restaura.
set -euo pipefail
R="${1:?Indique la carpeta de respaldo}"
. "$R/datos.env"
cd "$DD"
dc() { sudo env APP_IMAGE="$IMG_ACTUAL" docker compose --env-file .env "$@"; }
echo "==> Restaurando archivos de source/"
tar -xzf "$R/archivos.tgz" -C "$DD/source"
rm -f "$DD/source/cuentas/management/commands/cuentas_huerfanas.py"
if [ -f "$R/env.bak" ]; then
    cp -p "$R/env.bak" "$DD/.env"
    echo "==> .env restaurado desde la copia (APP_IMAGE vuelve a la imagen anterior)"
fi
echo "==> Volviendo a la imagen anterior: $IMG_ACTUAL"
dc up -d --no-deps --wait --wait-timeout 120 app
sleep 5
curl -sk -o /dev/null -w '  /login/ -> %{http_code}\n' --max-time 15 "${URL_PUBLICA:-https://54.205.69.94}/login/"
sudo docker ps --format '  {{.Names}} | {{.Image}} | {{.Status}}'
echo "Listo. No cambió datos; MySQL no se restaura (respaldo en $R/mysql.sql.gz si se quisiera)."
