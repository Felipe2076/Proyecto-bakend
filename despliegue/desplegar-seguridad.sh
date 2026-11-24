#!/usr/bin/env bash
# Despliega siged-seguridad-app.diff en el servidor con respaldo previo y reversión preparada.
# Uso (en la EC2):  bash ~/desplegar-seguridad.sh            -> despliega
#                   SOLO_REVISAR=1 bash ~/desplegar-seguridad.sh -> solo diagnostica y prueba el parche
# No modifica .env, volúmenes de evidencias ni la base, salvo las migraciones de Django.
set -euo pipefail

PARCHE="${PARCHE:-$HOME/siged-seguridad-app.diff}"
FECHA="$(date +%Y%m%d-%H%M%S)"
RESPALDOS="$HOME/respaldos-siged/$FECHA"
URL_PUBLICA="${URL_PUBLICA:-https://54.205.69.94}"
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo"

paso() { printf '\n==> %s\n' "$*"; }
alto() { printf '\nDETENIDO: %s\nNo se cambió nada del sistema en este paso.\n' "$*" >&2; exit 1; }

[ -f "$PARCHE" ] || alto "No encuentro $PARCHE. Súbelo primero."
command -v patch >/dev/null || alto "Falta el comando patch (Amazon Linux: sudo dnf install -y patch; Ubuntu: sudo apt-get install -y patch)."

paso "1/8 Buscando el proyecto SIGED"
if [ -n "${APP:-}" ]; then CANDIDATOS=("$APP"); else mapfile -t CANDIDATOS < <(sudo find / -xdev \( -path /proc -o -path /var/lib/docker -o -path '*/site-packages' -o -path "$HOME/respaldos-siged" \) -prune \
    -o -name manage.py -print 2>/dev/null | while read -r f; do d="$(dirname "$f")"; [ -f "$d/control_gestion/territorios.py" ] && echo "$d"; done); fi
[ "${#CANDIDATOS[@]}" -eq 1 ] || { printf '  %s\n' "${CANDIDATOS[@]:-ninguno}"; alto "Se esperaba exactamente un proyecto. Defina APP=/ruta y vuelva a ejecutar."; }
APP="${APP:-${CANDIDATOS[0]}}"
echo "  Proyecto: $APP"

COMPOSE_DIR=""
for d in "$APP" "$(dirname "$APP")"; do
    for n in docker-compose.yml docker-compose.yaml compose.yml compose.yaml; do [ -f "$d/$n" ] && COMPOSE_DIR="$d" && break 2; done
done
[ -n "$COMPOSE_DIR" ] || alto "No encuentro el archivo de Docker Compose junto al proyecto."
cd "$COMPOSE_DIR"
echo "  Compose: $COMPOSE_DIR"
$SUDO $DC ps

# Servicio web = el que se construye o monta el código; base = imagen mysql.
SERVICIOS="$($SUDO $DC config --services)"
WEB="${WEB:-$(for s in $SERVICIOS; do $SUDO $DC config | awk -v s="  $s:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:|manage.py|gunicorn/{print s; exit}' | head -1; done | head -1 | tr -d ' :')}"
DB="${DB:-$(for s in $SERVICIOS; do $SUDO $DC config | awk -v s="  $s:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/image: .*mysql/{print s; exit}'; done | head -1 | tr -d ' :')}"
[ -n "$WEB" ] || alto "No pude identificar el servicio web. Defina WEB=nombre_del_servicio."
echo "  Servicio web: $WEB   Servicio MySQL: ${DB:-no está en Compose}"

paso "2/8 Probando el parche sin aplicarlo"
cd "$APP"
if ! patch -p1 --dry-run --forward -s < "$PARCHE"; then
    alto "El parche no calza con el código del servidor (difiere de la copia revisada). Pase la salida anterior a Codex."
fi
echo "  El parche aplica limpio."
[ "${SOLO_REVISAR:-0}" = "1" ] && { echo; echo "SOLO_REVISAR=1: diagnóstico terminado, sin cambios."; exit 0; }

paso "3/8 Respaldos en $RESPALDOS"
mkdir -p "$RESPALDOS"
sudo tar --exclude='./media' --exclude='./staticfiles' --exclude='*/__pycache__' -czf "$RESPALDOS/codigo.tgz" -C "$APP" .
cd "$COMPOSE_DIR"
IMG="$($SUDO $DC images -q "$WEB" 2>/dev/null | head -1 || true)"
if [ -n "$IMG" ]; then $SUDO docker tag "$IMG" "siged-web:respaldo-$FECHA"; echo "  Imagen: siged-web:respaldo-$FECHA"; fi
if [ -n "$DB" ]; then
    $SUDO $DC exec -T "$DB" sh -c 'MYSQL_PWD="${MYSQL_PASSWORD:-}" mysqldump --single-transaction --routines --no-tablespaces -u"${MYSQL_USER:-root}" "${MYSQL_DATABASE}"' \
        | gzip > "$RESPALDOS/mysql.sql.gz"
    [ "$(gzip -dc "$RESPALDOS/mysql.sql.gz" | head -c 2000 | grep -c 'MySQL dump')" -ge 1 ] || alto "El respaldo de MySQL quedó vacío o inválido."
    echo "  MySQL: $(du -h "$RESPALDOS/mysql.sql.gz" | cut -f1)"
elif [ "${SIN_RESPALDO_BD:-0}" != "1" ]; then
    alto "MySQL no está en Compose. Respalde la base a mano y ejecute con SIN_RESPALDO_BD=1."
fi
printf 'APP=%q\nCOMPOSE_DIR=%q\nWEB=%q\nIMG_RESPALDO=%q\n' "$APP" "$COMPOSE_DIR" "$WEB" "${IMG:+siged-web:respaldo-$FECHA}" > "$RESPALDOS/datos.env"
cp "$PARCHE" "$RESPALDOS/siged-seguridad-app.diff"
sudo chown -R "$(id -u):$(id -g)" "$RESPALDOS"
chmod -R go-rwx "$RESPALDOS"

paso "4/8 Aplicando el parche"
cd "$APP"
sudo patch -p1 --forward -s --no-backup-if-mismatch < "$PARCHE"
echo "  Aplicado."

paso "5/8 Construyendo y aplicando migraciones"
cd "$COMPOSE_DIR"
if $SUDO $DC config | awk -v s="  $WEB:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:/{found=1} END{exit !found}'; then
    $SUDO $DC build "$WEB"
fi
$SUDO $DC run --rm --no-deps "$WEB" python manage.py migrate --noinput
$SUDO $DC run --rm --no-deps "$WEB" python manage.py check

paso "6/8 Reiniciando el servicio web (evidencias y MySQL no se tocan)"
$SUDO $DC up -d --no-deps "$WEB"
sleep 8

paso "7/8 Verificación"
FALLO=0
salud="$(curl -sk -o /dev/null -w '%{http_code}' "$URL_PUBLICA/salud/" || true)"
login="$(curl -sk -o /dev/null -w '%{http_code}' "$URL_PUBLICA/login/" || true)"
protegido="$(curl -sk -o /dev/null -w '%{http_code}' "$URL_PUBLICA/control/funcionarios/" || true)"
cookie="$(curl -sk -D - -o /dev/null "$URL_PUBLICA/login/" | grep -i '^set-cookie: csrftoken' || true)"
echo "  /salud/ -> $salud (esperado 200)"; [ "$salud" = 200 ] || FALLO=1
echo "  /login/ -> $login (esperado 200)"; [ "$login" = 200 ] || FALLO=1
echo "  /control/funcionarios/ sin sesión -> $protegido (esperado 302)"; [ "$protegido" = 302 ] || FALLO=1
echo "  Cookie CSRF: $cookie"; echo "$cookie" | grep -qi httponly || FALLO=1
$SUDO $DC ps "$WEB"

paso "8/8 Resultado"
if [ "$FALLO" = 0 ]; then
    echo "  Despliegue verificado."
else
    echo "  Hay verificaciones fallidas. Para volver atrás:  bash ~/revertir-seguridad.sh $RESPALDOS"
fi
cat <<EOF

Respaldo y datos para revertir: $RESPALDOS
Reversión:  bash ~/revertir-seguridad.sh $RESPALDOS

Recordatorio: los usuarios deben iniciar sesión de nuevo (la sesión pasó a la base).
Si Apache u otro proxy está delante, defina en el .env SIGED_PROXY_CONFIABLE (IP de ese proxy
vista desde el contenedor) para que la cuota por IP no sea compartida por todos.
EOF
