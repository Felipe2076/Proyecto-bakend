#!/usr/bin/env bash
# Despliega siged-alta-usuarios.diff: alta de usuarios sin errores 500, RUT explicado, admin de Django
# más tolerante y herramienta para cuentas de acceso huérfanas.
#   SOLO_REVISAR=1 bash ~/desplegar-alta-usuarios.sh   -> diagnóstico + prueba del parche, sin cambios
#   bash ~/desplegar-alta-usuarios.sh                  -> despliega con respaldo
# No cambia el esquema de la base (sin migraciones), .env, evidencias ni la configuración de Apache.
# La versión anterior sigue sirviendo hasta que la nueva imagen se construye y pasa "manage.py check";
# si algo falla antes del reinicio, el script revierte solo.
set -euo pipefail

PARCHE="${PARCHE:-$HOME/siged-alta-usuarios.diff}"
URL_PUBLICA="${URL_PUBLICA:-https://54.205.69.94}"
FECHA="$(date +%Y%m%d-%H%M%S)"
RESPALDOS="$HOME/respaldos-siged/alta-usuarios-$FECHA"
DC="docker compose"; $DC version >/dev/null 2>&1 || DC="docker-compose"
SUDO=""; docker info >/dev/null 2>&1 || SUDO="sudo"
ARCHIVOS="core/validaciones.py cuentas/views.py cuentas/admin.py static/js/modulos/validaciones.js cuentas/tests_alta_usuarios.py cuentas/management/commands/cuentas_huerfanas.py"
paso() { printf '\n==> %s\n' "$*"; }
alto() { printf '\nDETENIDO: %s\nNo se cambió nada en este paso.\n' "$*" >&2; exit 1; }
codigo() { curl -sk -o /dev/null -w '%{http_code}' "$URL_PUBLICA$1" || true; }
[ -f "$PARCHE" ] || alto "No encuentro $PARCHE. Súbalo primero."
command -v patch >/dev/null || alto "Falta el comando patch (sudo dnf install -y patch  /  sudo apt-get install -y patch)."

paso "1/8 Proyecto y servicios"
ULTIMO="$(ls -1dt "$HOME"/respaldos-siged/*/datos.env 2>/dev/null | head -1 || true)"
if [ -z "${APP:-}" ] && [ -n "$ULTIMO" ]; then . "$ULTIMO"; echo "  Datos tomados de: $ULTIMO"; fi
[ -n "${APP:-}" ] && [ -n "${COMPOSE_DIR:-}" ] && [ -n "${WEB:-}" ] || alto "Defina APP=, COMPOSE_DIR= y WEB= (no hay despliegue previo con datos guardados)."
cd "$COMPOSE_DIR"
DB="${DB:-$(for s in $($SUDO $DC config --services); do $SUDO $DC config | awk -v s="  $s:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/image: .*mysql/{print s; exit}'; done | head -1 | tr -d ' :')}"
echo "  APP=$APP"; echo "  Servicio web: $WEB   MySQL: ${DB:-no está en Compose}"
echo "  Estado actual: login $(codigo /login/), salud $(codigo /salud/)"

paso "2/8 Probando el parche sin aplicarlo"
cd "$APP"
for f in $ARCHIVOS; do [ -e "$f" ] || [ "${f##*/}" = "tests_alta_usuarios.py" ] || [ "${f##*/}" = "cuentas_huerfanas.py" ] || alto "No existe $f en el servidor."; done
patch -p1 --dry-run --forward -s < "$PARCHE" || alto "El parche no calza con el código del servidor. Pase la salida a Codex."
echo "  El parche aplica limpio."
[ "${SOLO_REVISAR:-0}" = "1" ] && {
    echo; echo "SOLO_REVISAR=1: informe de cuentas de acceso huérfanas (solo lectura, RUT enmascarado):"
    cd "$COMPOSE_DIR"; $SUDO $DC exec -T "$WEB" python manage.py cuentas_huerfanas 2>&1 | head -20 || echo "  (el comando aún no existe en el servidor; sale tras el despliegue)"
    echo; echo "Diagnóstico terminado, sin cambios."; exit 0; }

paso "3/8 Respaldos en $RESPALDOS"
mkdir -p "$RESPALDOS"
sudo tar -czf "$RESPALDOS/archivos.tgz" -C "$APP" $(cd "$APP" && for f in $ARCHIVOS; do [ -e "$f" ] && echo "$f"; done)
cp "$PARCHE" "$RESPALDOS/siged-alta-usuarios.diff"
cd "$COMPOSE_DIR"
IMG="$($SUDO $DC images -q "$WEB" 2>/dev/null | head -1 || true)"
[ -n "$IMG" ] && $SUDO docker tag "$IMG" "siged-web:respaldo-alta-$FECHA" && echo "  Imagen: siged-web:respaldo-alta-$FECHA"
if [ -n "$DB" ]; then
    $SUDO $DC exec -T "$DB" sh -c 'MYSQL_PWD="${MYSQL_PASSWORD:-}" mysqldump --single-transaction --routines --no-tablespaces -u"${MYSQL_USER:-root}" "${MYSQL_DATABASE}"' | gzip > "$RESPALDOS/mysql.sql.gz"
    gzip -dc "$RESPALDOS/mysql.sql.gz" | head -c 2000 | grep -q 'MySQL dump' || alto "El respaldo de MySQL quedó vacío o inválido."
    echo "  MySQL: $(du -h "$RESPALDOS/mysql.sql.gz" | cut -f1)"
elif [ "${SIN_RESPALDO_BD:-0}" != "1" ]; then alto "MySQL no está en Compose; respalde a mano y use SIN_RESPALDO_BD=1."; fi
printf 'APP=%q\nCOMPOSE_DIR=%q\nWEB=%q\nIMG_RESPALDO=%q\n' "$APP" "$COMPOSE_DIR" "$WEB" "${IMG:+siged-web:respaldo-alta-$FECHA}" > "$RESPALDOS/datos.env"
sudo chown -R "$(id -u):$(id -g)" "$RESPALDOS"; chmod -R go-rwx "$RESPALDOS"

volver() {  # reversión automática si algo falla antes de reiniciar
    echo "  FALLÓ: revirtiendo código; el servicio anterior sigue en marcha." >&2
    cd "$APP" && sudo patch -R -E -p1 -s --forward < "$RESPALDOS/siged-alta-usuarios.diff" || sudo tar -xzf "$RESPALDOS/archivos.tgz" -C "$APP"
    exit 1
}

paso "4/8 Aplicando el parche"
cd "$APP"; sudo patch -p1 --forward -s --no-backup-if-mismatch < "$PARCHE" || volver
echo "  Aplicado."

paso "5/8 Construyendo y verificando la imagen NUEVA (el servicio actual sigue atendiendo)"
cd "$COMPOSE_DIR"
if $SUDO $DC config | awk -v s="  $WEB:" '$0==s{f=1;next} /^  [^ ]/{f=0} f&&/build:/{found=1} END{exit !found}'; then $SUDO $DC build "$WEB" || volver; fi
$SUDO $DC run --rm --no-deps "$WEB" python manage.py check || volver
$SUDO $DC run --rm --no-deps "$WEB" python manage.py makemigrations --check --dry-run || volver
echo "  Imagen nueva verificada (sin migraciones pendientes)."

paso "6/8 Reiniciando solo el servicio web"
$SUDO $DC up -d --no-deps "$WEB"
$SUDO $DC run --rm --no-deps "$WEB" python manage.py collectstatic --noinput -v0 || echo "  Aviso: collectstatic no pudo ejecutarse; el JS nuevo puede tardar en verse."
sleep 8

paso "7/8 Verificación"
FALLO=0
l="$(codigo /login/)"; s="$(codigo /salud/)"; p="$(codigo /administracion/usuarios/)"; c="$(codigo /static/css/style.css)"
echo "  /login/ -> $l (200)  /salud/ -> $s (200)  /administracion/usuarios/ sin sesión -> $p (302)  style.css -> $c (200)"
[ "$l" = 200 ] && [ "$s" = 200 ] && [ "$p" = 302 ] && [ "$c" = 200 ] || FALLO=1
js="$(curl -sk "$URL_PUBLICA/static/js/modulos/validaciones.js" | grep -c rutCanonico || true)"
echo "  JS nuevo servido: $([ "$js" -ge 1 ] && echo sí || echo 'no todavía (no afecta el alta)')"
echo "  Cuentas de acceso huérfanas (solo informe, RUT enmascarado):"
$SUDO $DC exec -T "$WEB" python manage.py cuentas_huerfanas 2>&1 | head -25 | sed 's/^/    /' || true

paso "8/8 Resultado"
if [ "$FALLO" = 0 ]; then echo "  Desplegado y verificado."; else echo "  Verificaciones fallidas: revierta con el comando de abajo."; fi
cat <<EOF

Respaldo: $RESPALDOS
Revertir: bash ~/revertir-alta-usuarios.sh $RESPALDOS
Para liberar un RUT bloqueado por una cuenta huérfana (tras revisar el informe):
  cd $COMPOSE_DIR && $SUDO $DC exec $WEB python manage.py cuentas_huerfanas --eliminar
EOF
