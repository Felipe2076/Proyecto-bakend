#!/usr/bin/env bash
# Deshace desplegar-alta-usuarios.sh. Uso: bash ~/revertir-alta-usuarios.sh ~/respaldos-siged/alta-usuarios-FECHA
set -euo pipefail
R="${1:?Indique la carpeta de respaldo}"
. "$R/datos.env"
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo"
echo "==> Restaurando archivos"
cd "$APP"
sudo patch -R -E -p1 -s --forward < "$R/siged-alta-usuarios.diff" || { echo "  Parche inverso no calzó; restauro desde archivos.tgz"; sudo tar -xzf "$R/archivos.tgz" -C "$APP"; }
echo "==> Reconstruyendo y reiniciando $WEB"
cd "$COMPOSE_DIR"
if $SUDO $DC config | awk -v s="  $WEB:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:/{found=1} END{exit !found}'; then $SUDO $DC build "$WEB"; fi
$SUDO $DC up -d --no-deps "$WEB"
$SUDO $DC run --rm --no-deps "$WEB" python manage.py collectstatic --noinput -v0 || true
sleep 8
curl -sk -o /dev/null -w '  /login/ -> %{http_code}\n' "${URL_PUBLICA:-https://54.205.69.94}/login/"
echo "Listo. Esta versión no cambió datos: no hace falta restaurar MySQL (respaldo en $R/mysql.sql.gz si se quisiera)."
