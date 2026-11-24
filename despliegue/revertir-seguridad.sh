#!/usr/bin/env bash
# Revierte el despliegue de seguridad usando el respaldo que creó desplegar-seguridad.sh.
# Uso: bash ~/revertir-seguridad.sh ~/respaldos-siged/AAAAMMDD-HHMMSS
set -euo pipefail
RESPALDOS="${1:?Indique la carpeta de respaldo, p. ej. ~/respaldos-siged/20261112-220000}"
[ -f "$RESPALDOS/datos.env" ] || { echo "No encuentro $RESPALDOS/datos.env" >&2; exit 1; }
# shellcheck disable=SC1091
. "$RESPALDOS/datos.env"
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo"
cd "$COMPOSE_DIR"

echo "==> 1/4 Deshaciendo la migración 0013 (solo cambia upload_to, no borra datos)"
$SUDO $DC run --rm --no-deps "$WEB" python manage.py migrate control_gestion 0012 --noinput || \
    echo "    Aviso: no se pudo deshacer 0013; no impide restaurar el código."

echo "==> 2/4 Restaurando el código desde $RESPALDOS/codigo.tgz"
cd "$APP"
sudo patch -R -E -p1 -s --forward < "$RESPALDOS/siged-seguridad-app.diff" || {
    echo "    El parche inverso no aplicó limpio; restaurando el archivo completo del respaldo."
    sudo tar -xzf "$RESPALDOS/codigo.tgz" -C "$APP"
}

echo "==> 3/4 Reconstruyendo y reiniciando el servicio web"
cd "$COMPOSE_DIR"
if $SUDO $DC config | awk -v s="  $WEB:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:/{found=1} END{exit !found}'; then
    $SUDO $DC build "$WEB"
fi
$SUDO $DC up -d --no-deps "$WEB"
sleep 8

echo "==> 4/4 Verificación"
curl -sk -o /dev/null -w '  /login/ -> %{http_code}\n' "${URL_PUBLICA:-https://54.205.69.94}/login/"
$SUDO $DC ps "$WEB"
cat <<EOF

Código revertido. La base no se restauró porque el despliegue no cambió datos.
Si hiciera falta: gzip -dc $RESPALDOS/mysql.sql.gz | $SUDO $DC exec -T <servicio_mysql> mysql -u... <base>
Imagen anterior disponible: ${IMG_RESPALDO:-sin etiqueta}
EOF
