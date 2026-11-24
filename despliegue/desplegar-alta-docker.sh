#!/usr/bin/env bash
# Despliega la corrección del alta de usuarios en el servidor Docker de SIGED (source/ + compose.yaml).
# Reemplaza 4 archivos y agrega 1, SOLO si los 4 actuales son byte a byte la versión base esperada
# (hash SHA-256); así no depende de "patch" ni de los saltos de línea CRLF del servidor.
#   SOLO_REVISAR=1 bash ~/desplegar-alta-docker.sh   -> verifica hashes sin cambiar nada
#   bash ~/desplegar-alta-docker.sh                  -> respalda, aplica, construye imagen NUEVA, verifica y reinicia solo "app"
# No edita .env ni compose.yaml. La imagen actual queda como respaldo y como destino de reversión.
# La imagen nueva se pasa con APP_IMAGE por línea de comandos; para dejarla permanente, cambie APP_IMAGE en .env.
set -euo pipefail
DD="${DD:-/home/ec2-user/siged-docker/docker-deployment}"
SRC="$DD/source"
NUEVOS="${NUEVOS:-$HOME/alta-nuevos.tgz}"
URL_PUBLICA="${URL_PUBLICA:-https://54.205.69.94}"
FECHA="$(date +%Y%m%d-%H%M%S)"
R="$HOME/respaldos-siged/alta-$FECHA"
NUEVA="siged-app:alta-$FECHA"
paso() { printf '\n==> %s\n' "$*"; }
alto() { printf '\nDETENIDO: %s\n' "$*" >&2; exit 1; }
dc() { sudo env APP_IMAGE="${IMG_USAR:-}" docker compose --env-file .env "$@"; }
codigo() { curl -sk -o /dev/null -w '%{http_code}' --max-time 15 "$1" || true; }
[ -f "$NUEVOS" ] || alto "No encuentro $NUEVOS."
[ -f "$SRC/manage.py" ] || alto "No encuentro $SRC/manage.py."
cd "$DD"

paso "1/8 Estado actual"
IMG_ACTUAL="$(sudo docker inspect siged-app-1 --format '{{.Config.Image}}')"
echo "  Imagen en uso: $IMG_ACTUAL"
echo "  /salud/ -> $(codigo "$URL_PUBLICA/salud/")   /login/ -> $(codigo "$URL_PUBLICA/login/")"
IMG_USAR="$IMG_ACTUAL"

paso "2/8 Verificando que los archivos del servidor son exactamente la versión base"
cat > "${TMPDIR:-/tmp}/base-$FECHA.sha" <<'HASHES'
b4db7ea202d935c4ca0ac7e61cb734e681e654781298560793deb29be1039c39  cuentas/views.py
9bbccb8b80e52620fb69c65750b2aca0f0b3ef4474da8a694850e799e42e01ff  core/validaciones.py
204d10a7fe24c3ad07342e5bc7e04640d4c1622c31a8ea300895683a7c666923  cuentas/admin.py
832bca89455e42cd26f63e04bf90b054ec46d3b15a6927878fa90f13843e71a2  static/js/modulos/validaciones.js
HASHES
(cd "$SRC" && sha256sum -c --quiet "${TMPDIR:-/tmp}/base-$FECHA.sha") || alto "Algún archivo del servidor difiere de la versión base. No se cambió nada."
rm -f "${TMPDIR:-/tmp}/base-$FECHA.sha"
echo "  Los 4 archivos coinciden con la base (SHA-256)."
[ "${SOLO_REVISAR:-0}" = "1" ] && { echo; echo "SOLO_REVISAR=1: terminado, sin cambios."; exit 0; }

paso "3/8 Respaldos en $R"
mkdir -p "$R"
ARCHIVOS="core/validaciones.py cuentas/views.py cuentas/admin.py static/js/modulos/validaciones.js"
(cd "$SRC" && tar -czf "$R/archivos.tgz" $ARCHIVOS)
cp "$NUEVOS" "$R/alta-nuevos.tgz"
sudo docker tag "$IMG_ACTUAL" "siged-app:respaldo-alta-$FECHA"
echo "  Imagen respaldada como siged-app:respaldo-alta-$FECHA (la etiqueta original no se toca)"
dc exec -T db sh -c 'MYSQL_PWD="${MYSQL_PASSWORD:-}" mysqldump --single-transaction --routines --no-tablespaces -u"${MYSQL_USER:-root}" "${MYSQL_DATABASE}"' 2>/dev/null | gzip > "$R/mysql.sql.gz" || true
# Se cuenta con grep -c dentro de $(...): "head" cierra la tubería antes de tiempo y con pipefail un grep -q directo falla en volcados grandes.
if [ "$(gzip -dc "$R/mysql.sql.gz" 2>/dev/null | head -c 3000 | grep -c 'MySQL dump')" -ge 1 ] && [ "$(stat -c %s "$R/mysql.sql.gz")" -gt 500 ]; then echo "  MySQL: $(du -h "$R/mysql.sql.gz" | cut -f1)"
elif [ "${SIN_RESPALDO_BD:-0}" = "1" ]; then echo "  Aviso: sin volcado de MySQL (SIN_RESPALDO_BD=1)"
else alto "El volcado de MySQL salió vacío. Respalde a mano o use SIN_RESPALDO_BD=1 (este parche no cambia datos). No se cambió nada del código."; fi
printf 'DD=%q\nIMG_ACTUAL=%q\nNUEVA=%q\n' "$DD" "$IMG_ACTUAL" "$NUEVA" > "$R/datos.env"
sudo chown -R "$(id -u):$(id -g)" "$R"; chmod -R go-rwx "$R"

restaurar() {  # devuelve los 4 originales y quita el único archivo que se agregó
    tar -xzf "$R/archivos.tgz" -C "$SRC"
    rm -f "$SRC/cuentas/management/commands/cuentas_huerfanas.py"
}
volver() {
    echo "  FALLÓ: revirtiendo; el servicio anterior sigue en marcha." >&2
    restaurar
    exit 1
}

paso "4/8 Copiando los archivos nuevos a source/"
tar -xzf "$NUEVOS" -C "$SRC" || volver
echo "  Copiados 5 archivos (4 reemplazados, 1 nuevo)."

paso "5/8 Construyendo la imagen NUEVA ($NUEVA) sobre la actual; el servicio actual sigue atendiendo"
IMG_USAR="$NUEVA"
# La imagen nueva se arma SOBRE la imagen en uso, copiando solo los 5 archivos: conserva exactamente las
# dependencias actuales. Reconstruir desde el Dockerfile de docker-deployment hoy da una imagen SIN Pillow
# (los requirements no lo incluyen) y el sitio no arrancaría; eso queda informado aparte para Codex.
mkdir -p "$R/ctx" && tar -xzf "$NUEVOS" -C "$R/ctx"
printf 'FROM %s
COPY --chown=0:0 . /app/
' "$IMG_ACTUAL" > "$R/Dockerfile.alta"
sudo docker build -f "$R/Dockerfile.alta" -t "$NUEVA" "$R/ctx" || volver
dc run --rm --no-deps app python manage.py check || volver
dc run --rm --no-deps app python manage.py makemigrations --check --dry-run || volver
echo "  Imagen nueva verificada (sin migraciones pendientes)."

paso "6/8 Reiniciando solo el servicio app"
dc up -d --no-deps --wait --wait-timeout 120 app || {
    echo "  El servicio nuevo no quedó sano: vuelvo a la imagen anterior." >&2
    IMG_USAR="$IMG_ACTUAL"; dc up -d --no-deps --wait --wait-timeout 120 app || true
    restaurar || true
    exit 1; }
sleep 5

paso "7/8 Verificación"
FALLO=0
l="$(codigo "$URL_PUBLICA/login/")"; s="$(codigo "$URL_PUBLICA/salud/")"; p="$(codigo "$URL_PUBLICA/administracion/usuarios/")"; c="$(codigo "$URL_PUBLICA/static/css/style.css")"
echo "  /login/ -> $l (200)   /salud/ -> $s (200)   /administracion/usuarios/ sin sesión -> $p (302)   style.css -> $c (200)"
[ "$l" = 200 ] && [ "$s" = 200 ] && [ "$p" = 302 ] && [ "$c" = 200 ] || FALLO=1
js="$(curl -sk --max-time 15 "$URL_PUBLICA/static/js/modulos/validaciones.js" | grep -c rutCanonico || true)"
echo "  JS nuevo publicado: $([ "$js" -ge 1 ] && echo sí || echo 'todavía no (no afecta el alta)')"
echo "  Cuentas de acceso huérfanas (solo informe, RUT enmascarado):"
dc exec -T app python manage.py cuentas_huerfanas 2>&1 | head -25 | sed 's/^/    /' || true
sudo docker ps --format '  {{.Names}} | {{.Image}} | {{.Status}}'

paso "8/8 Resultado"
if [ "$FALLO" = 0 ]; then echo "  Desplegado y verificado."; else echo "  Verificaciones fallidas: revierta con el comando de abajo."; fi
cat <<EOF

Respaldo: $R
Revertir:  bash ~/revertir-alta-docker.sh $R
Imagen nueva: $NUEVA   (anterior: $IMG_ACTUAL)
Nota: no se editó .env; si alguien ejecuta "docker compose up" sin APP_IMAGE=$NUEVA, volvería la imagen anterior.
Los manifiestos (source.manifest.json) quedan desactualizados para los 5 archivos tocados.
EOF
