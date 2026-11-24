#!/usr/bin/env bash
# Corrige el 403 de /static/: collectstatic copió los estáticos con 0640 (heredado de
# FILE_UPLOAD_PERMISSIONS) y Apache, que lee como "otros", no puede abrirlos.
# Uso:  SOLO_REVISAR=1 bash ~/corregir-estaticos.sh   -> solo diagnóstico, sin cambios
#       bash ~/corregir-estaticos.sh                  -> corrige con respaldo
# Solo cambia: config/settings.py (+ su prueba) y los permisos dentro de la carpeta del Alias /static/.
# No toca evidencias, .env, MySQL ni la configuración de Apache.
set -euo pipefail

PARCHE="${PARCHE:-$HOME/siged-estaticos.diff}"
URL_PUBLICA="${URL_PUBLICA:-https://54.205.69.94}"
FECHA="$(date +%Y%m%d-%H%M%S)"
RESPALDOS="$HOME/respaldos-siged/estaticos-$FECHA"
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo"
paso() { printf '\n==> %s\n' "$*"; }
alto() { printf '\nDETENIDO: %s\nNo se cambió nada en este paso.\n' "$*" >&2; exit 1; }
codigo() { curl -sk -o /dev/null -w '%{http_code} %{content_type}' "$URL_PUBLICA$1" || true; }

paso "1/7 Proyecto y servicio web"
ULTIMO="$(ls -1dt "$HOME"/respaldos-siged/2*/datos.env 2>/dev/null | head -1 || true)"
if [ -z "${APP:-}" ] && [ -n "$ULTIMO" ]; then . "$ULTIMO"; echo "  Datos del despliegue anterior: $ULTIMO"; fi
[ -n "${APP:-}" ] && [ -n "${COMPOSE_DIR:-}" ] && [ -n "${WEB:-}" ] || alto "Defina APP=, COMPOSE_DIR= y WEB= (no encontré datos del despliegue anterior)."
echo "  APP=$APP  COMPOSE_DIR=$COMPOSE_DIR  WEB=$WEB"

paso "2/7 Alias /static/ de Apache"
ALIAS="${ALIAS:-}"
[ -n "$ALIAS" ] && echo "  Alias indicado: $ALIAS"
for conf in /etc/httpd /etc/apache2; do
    [ -n "$ALIAS" ] && break
    [ -d "$conf" ] || continue
    ALIAS="$(sudo grep -RhiE '^[[:space:]]*Alias[[:space:]]+"?/static/?"?[[:space:]]' "$conf" 2>/dev/null | head -1 | awk '{print $3}' | tr -d '"' || true)"
    [ -n "$ALIAS" ] && echo "  Apache del host ($conf): Alias /static/ -> $ALIAS" && break
done
if [ -z "$ALIAS" ]; then
    # Apache en contenedor: se busca el Alias dentro y se traduce al origen del volumen en el host.
    for c in $($SUDO docker ps --format '{{.Names}} {{.Image}}' | awk 'tolower($2) ~ /httpd|apache/ {print $1}'); do
        dentro="$($SUDO docker exec "$c" sh -c "grep -RhiE '^[[:space:]]*Alias[[:space:]]+\"?/static/?\"?[[:space:]]' /usr/local/apache2/conf /etc/apache2 /etc/httpd 2>/dev/null | head -1" | awk '{print $3}' | tr -d '"' || true)"
        [ -n "$dentro" ] || continue
        ALIAS="$($SUDO docker inspect "$c" --format '{{range .Mounts}}{{.Destination}}|{{.Source}}{{"\n"}}{{end}}' \
            | awk -F'|' -v p="$dentro" 'index(p,$1)==1 {print $2 substr(p,length($1)+1); exit}')"
        echo "  Apache en contenedor $c: $dentro -> host $ALIAS"; break
    done
fi
[ -n "$ALIAS" ] || alto "No encontré el Alias /static/. Indique ALIAS=/ruta/real y vuelva a ejecutar."
ALIAS="${ALIAS%/}"
sudo test -f "$ALIAS/css/bootstrap.min.css" || alto "$ALIAS no contiene css/bootstrap.min.css: no parece la carpeta de estáticos."
case "$ALIAS" in *evidencia*|*media*|*archivos-privados*) alto "La ruta $ALIAS parece de evidencias; no se modifica." ;; esac
sudo test ! -e "$ALIAS/evidencias" || alto "$ALIAS contiene evidencias/; no se modifica."

paso "3/7 Diagnóstico (solo lectura)"
echo "  Respuesta pública: style.css -> $(codigo /static/css/style.css) | bootstrap.min.css -> $(codigo /static/css/bootstrap.min.css)"
command -v namei >/dev/null && sudo namei -l "$ALIAS/css/style.css" | sed 's/^/  /'
sudo stat -c '  %A %U:%G %n' "$ALIAS/css/style.css" "$ALIAS/css/bootstrap.min.css" "$ALIAS"
echo "  Archivos sin lectura para otros: $(sudo find "$ALIAS" -type f ! -perm -o=r | wc -l) de $(sudo find "$ALIAS" -type f | wc -l)"
echo "  Carpetas sin acceso para otros:  $(sudo find "$ALIAS" -type d ! -perm -o=rx | wc -l)"
command -v getenforce >/dev/null && echo "  SELinux: $(getenforce)" || echo "  SELinux: no instalado"
cd "$APP"
if grep -q 'file_permissions_mode' config/settings.py; then echo "  settings.py ya tiene permisos propios para estáticos."; YA=1; else
    patch -p1 --dry-run --forward -s < "$PARCHE" || alto "El parche de settings no calza; pase esta salida a Codex."; YA=0; echo "  El parche de settings aplica limpio."; fi
[ "${SOLO_REVISAR:-0}" = "1" ] && { echo; echo "SOLO_REVISAR=1: diagnóstico terminado, sin cambios."; exit 0; }

paso "4/7 Respaldo en $RESPALDOS"
mkdir -p "$RESPALDOS"
sudo find "$ALIAS" -printf '%m\t%p\n' > "$RESPALDOS/permisos-estaticos.tsv"
sudo cp -p "$APP/config/settings.py" "$RESPALDOS/settings.py"
[ -f "$APP/core/tests_seguridad.py" ] && sudo cp -p "$APP/core/tests_seguridad.py" "$RESPALDOS/tests_seguridad.py"
cp "$PARCHE" "$RESPALDOS/siged-estaticos.diff"
printf 'APP=%q\nCOMPOSE_DIR=%q\nWEB=%q\nALIAS=%q\nPARCHE_APLICADO=%q\n' "$APP" "$COMPOSE_DIR" "$WEB" "$ALIAS" "$((1-YA))" > "$RESPALDOS/datos.env"
sudo chown -R "$(id -u):$(id -g)" "$RESPALDOS"; chmod -R go-rwx "$RESPALDOS"
echo "  $(wc -l < "$RESPALDOS/permisos-estaticos.tsv") rutas con sus permisos anteriores."

paso "5/7 Corrección de código (próximos collectstatic con 0644/0755) y reinicio web"
if [ "$YA" = 0 ]; then cd "$APP" && sudo patch -p1 --forward -s --no-backup-if-mismatch < "$PARCHE"; fi
cd "$COMPOSE_DIR"
if $SUDO $DC config | awk -v s="  $WEB:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:/{found=1} END{exit !found}'; then $SUDO $DC build "$WEB"; fi
$SUDO $DC up -d --no-deps "$WEB"
sleep 10

paso "6/7 Permisos de lectura solo dentro de $ALIAS"
sudo find "$ALIAS" -type d ! -perm 0755 -exec chmod 0755 {} +
sudo find "$ALIAS" -type f ! -perm 0644 -exec chmod 0644 {} +
echo "  Sin lectura para otros ahora: $(sudo find "$ALIAS" -type f ! -perm -o=r | wc -l)"

paso "7/7 Verificación"
FALLO=0
for r in /static/css/style.css /static/css/bootstrap.min.css /static/css/app.css /static/js/bootstrap.bundle.min.js; do
    res="$(codigo "$r")"; echo "  $r -> $res"
    case "$r" in *.css) [[ "$res" == "200 text/css"* ]] || FALLO=1 ;; *) [[ "$res" == 200* ]] || FALLO=1 ;; esac
done
for r in /media/ /archivos-privados/ /control/actividades/ACT-001/evidencia/; do
    res="$(codigo "$r")"; echo "  $r (debe seguir privado) -> $res"; [[ "$res" == 200* ]] && FALLO=1
done
echo "  /login/ -> $(codigo /login/)   /salud/ -> $(codigo /salud/)"
if [ "$FALLO" = 0 ]; then echo; echo "  Estilos restaurados y evidencias privadas."; else echo; echo "  Hay verificaciones fallidas."; fi
cat <<EOF

Respaldo: $RESPALDOS
Revertir: bash ~/revertir-estaticos.sh $RESPALDOS
EOF
