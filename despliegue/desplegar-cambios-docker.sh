#!/usr/bin/env bash
# Despliega un paquete de archivos en el servidor Docker de SIGED (source/ + compose.yaml).
# Paquete (carpeta ~/siged-cambios o la que indique PAQUETE): nuevos.tgz (archivos nuevos) y base.sha
# (SHA-256 de los archivos que se REEMPLAZAN, tal como están hoy en el servidor). Opcional: migrar.txt (nombres de
# las migraciones que se esperan pendientes, una por línea) y migrar_atras.txt ("app migración" a la que se vuelve al revertir).
# Si hay migraciones: solo se aplican si el plan de Django coincide EXACTAMENTE con migrar.txt y el SQL es solo aditivo.
# El usuario de la aplicación en MySQL tiene solo SELECT/INSERT/UPDATE/DELETE (mínimo privilegio) y NO se amplía: el SQL
# exacto (sqlmigrate) se ejecuta con la cuenta administradora DENTRO del contenedor db y la migración se registra con --fake.
# El volcado de MySQL ya está hecho antes. La imagen nueva ya está verificada cuando se migra.
# Solo reemplaza si cada archivo actual coincide byte a byte con base.sha; si no, se detiene sin cambiar nada.
#   SOLO_REVISAR=1 bash ~/siged-cambios/desplegar-cambios-docker.sh   -> verifica hashes y muestra qué se tocaría
#   bash ~/siged-cambios/desplegar-cambios-docker.sh                -> respalda, aplica, construye imagen NUEVA sobre la actual,
#                                                          verifica, reinicia solo "app" y fija APP_IMAGE (con copia del .env)
# Reversión automática si falla antes o durante el reinicio; manual con revertir-cambios-docker.sh.
set -euo pipefail
DD="${DD:-/home/ec2-user/siged-docker/docker-deployment}"
SRC="$DD/source"
PAQUETE="${PAQUETE:-$HOME/siged-cambios}"
URL_PUBLICA="${URL_PUBLICA:-https://54.205.69.94}"
FECHA="$(date +%Y%m%d-%H%M%S)"
R="$HOME/respaldos-siged/cambios-$FECHA"
NUEVA="siged-app:cambio-$FECHA"
paso() { printf '\n==> %s\n' "$*"; }
alto() { printf '\nDETENIDO: %s\n' "$*" >&2; exit 1; }
dc() { sudo env APP_IMAGE="${IMG_USAR:-}" docker compose --env-file .env "$@" </dev/null; }
codigo() { curl -sk -o /dev/null -w '%{http_code}' --max-time 15 "$1" || true; }
[ -f "$PAQUETE/nuevos.tgz" ] && [ -f "$PAQUETE/base.sha" ] || alto "Falta $PAQUETE/nuevos.tgz o $PAQUETE/base.sha."
[ -f "$SRC/manage.py" ] || alto "No encuentro $SRC/manage.py."
cd "$DD"

paso "1/8 Estado actual"
IMG_ACTUAL="$(sudo docker inspect siged-app-1 --format '{{.Config.Image}}')"
echo "  Imagen en uso: $IMG_ACTUAL"
echo "  /salud/ -> $(codigo "$URL_PUBLICA/salud/")   /login/ -> $(codigo "$URL_PUBLICA/login/")"
IMG_USAR="$IMG_ACTUAL"
mapfile -t TODOS < <(tar -tzf "$PAQUETE/nuevos.tgz" | grep -v '/$')
mapfile -t EXISTENTES < <(awk '{print $2}' "$PAQUETE/base.sha" | sed 's/^\*//')
echo "  Archivos del paquete: ${#TODOS[@]} (reemplazan: ${#EXISTENTES[@]}, nuevos: $(( ${#TODOS[@]} - ${#EXISTENTES[@]} )))"

paso "2/8 Verificando que los archivos del servidor son exactamente la versión base"
(cd "$SRC" && sha256sum -c --quiet "$PAQUETE/base.sha") || alto "Algún archivo del servidor difiere de la versión base. No se cambió nada."
for f in "${TODOS[@]}"; do
    esta=0; for e in "${EXISTENTES[@]}"; do [ "$e" = "$f" ] && esta=1; done
    [ "$esta" = 1 ] || { [ ! -e "$SRC/$f" ] || alto "$f ya existe en el servidor y no está en base.sha."; }
done
echo "  Los ${#EXISTENTES[@]} archivos coinciden con la base (SHA-256)."
[ "${SOLO_REVISAR:-0}" = "1" ] && { echo; echo "SOLO_REVISAR=1: terminado, sin cambios."; exit 0; }

paso "3/8 Respaldos en $R"
mkdir -p "$R"
(cd "$SRC" && tar -czf "$R/archivos.tgz" "${EXISTENTES[@]}")
: > "$R/solo_nuevos.txt"
for f in "${TODOS[@]}"; do
    esta=0; for e in "${EXISTENTES[@]}"; do [ "$e" = "$f" ] && esta=1; done
    [ "$esta" = 1 ] || echo "$f" >> "$R/solo_nuevos.txt"
done
cp "$PAQUETE/nuevos.tgz" "$R/nuevos.tgz"; cp "$PAQUETE/base.sha" "$R/base.sha"
sudo docker tag "$IMG_ACTUAL" "siged-app:respaldo-cambios-$FECHA"
echo "  Imagen respaldada como siged-app:respaldo-cambios-$FECHA (la etiqueta original no se toca)"
dc exec -T db sh -c 'MYSQL_PWD="${MYSQL_PASSWORD:-}" mysqldump --single-transaction --routines --no-tablespaces -u"${MYSQL_USER:-root}" "${MYSQL_DATABASE}"' 2>/dev/null | gzip > "$R/mysql.sql.gz" || true
# grep -c dentro de $(...): "head" cierra la tubería antes de tiempo y con pipefail un grep -q directo falla en volcados grandes.
if [ "$(gzip -dc "$R/mysql.sql.gz" 2>/dev/null | head -c 3000 | grep -c 'MySQL dump')" -ge 1 ] && [ "$(stat -c %s "$R/mysql.sql.gz")" -gt 500 ]; then echo "  MySQL: $(du -h "$R/mysql.sql.gz" | cut -f1)"
elif [ "${SIN_RESPALDO_BD:-0}" = "1" ]; then echo "  Aviso: sin volcado de MySQL (SIN_RESPALDO_BD=1)"
else alto "El volcado de MySQL salió vacío. No se cambió nada del código."; fi
# Archivos privados (evidencias y fotos de perfil): no están en MySQL, se respaldan aparte.
if dc exec -T app sh -c 'cd "${SIGED_MEDIA_ROOT:-/app/media}" 2>/dev/null && tar -czf - .' > "$R/archivos-privados.tgz" 2>/dev/null    && [ "$(stat -c %s "$R/archivos-privados.tgz")" -gt 20 ]; then echo "  Archivos privados: $(du -h "$R/archivos-privados.tgz" | cut -f1)"
else echo "  Aviso: no se pudo respaldar la carpeta de evidencias/fotos (revise SIGED_MEDIA_ROOT)."; fi
cp -p .env "$R/env.bak" && chmod 600 "$R/env.bak"
printf 'DD=%q\nIMG_ACTUAL=%q\nNUEVA=%q\n' "$DD" "$IMG_ACTUAL" "$NUEVA" > "$R/datos.env"
sudo chown -R "$(id -u):$(id -g)" "$R"; chmod -R go-rwx "$R"

restaurar() {  # devuelve los archivos originales y quita los que se agregaron
    tar -xzf "$R/archivos.tgz" -C "$SRC"
    while IFS= read -r f; do [ -n "$f" ] && rm -f "$SRC/$f"; done < "$R/solo_nuevos.txt"
}
volver() { echo "  FALLÓ: revirtiendo; el servicio anterior sigue en marcha." >&2; restaurar; exit 1; }

paso "4/8 Copiando los archivos nuevos a source/"
tar -xzf "$PAQUETE/nuevos.tgz" -C "$SRC" || volver
echo "  Copiados ${#TODOS[@]} archivos."

paso "5/8 Construyendo la imagen NUEVA ($NUEVA) sobre la actual; el servicio actual sigue atendiendo"
IMG_USAR="$NUEVA"
# Sobre la imagen en uso (no desde el Dockerfile): conserva exactamente las dependencias actuales (incl. Pillow).
mkdir -p "$R/ctx" && tar -xzf "$PAQUETE/nuevos.tgz" -C "$R/ctx"
printf 'FROM %s\nCOPY --chown=0:0 . /app/\n' "$IMG_ACTUAL" > "$R/Dockerfile.cambios"
sudo docker build -f "$R/Dockerfile.cambios" -t "$NUEVA" "$R/ctx" || volver
dc run --rm --no-deps app python manage.py check || volver
dc run --rm --no-deps app python manage.py makemigrations --check --dry-run || volver
if [ -f "$PAQUETE/migrar.txt" ]; then
    echo "  Plan de migraciones (Django):"
    PLAN="$(dc run --rm --no-deps app python manage.py migrate --plan 2>&1 | grep -E '^[a-z_]+\.[0-9]{4}_' | sort || true)"
    ESPERADO="$(sort "$PAQUETE/migrar.txt")"
    echo "$PLAN" | sed 's/^/    /'
    [ "$PLAN" = "$ESPERADO" ] || { echo "  El plan no coincide con lo esperado ($ESPERADO)." >&2; volver; }
    : > "$R/migracion.sql"
    while IFS= read -r m; do
        [ -n "$m" ] || continue
        dc run --rm --no-deps -T app python manage.py sqlmigrate "${m%%.*}" "${m#*.}" 2>"$R/sqlmigrate.err" >> "$R/migracion.sql" \
            || { cat "$R/sqlmigrate.err" >&2; volver; }
    done < "$PAQUETE/migrar.txt"
    echo "  SQL que se ejecutará (guardado en $R/migracion.sql):"
    sed 's/^/    /' "$R/migracion.sql"
    if grep -Eiq '\b(DROP|DELETE|TRUNCATE|UPDATE|RENAME)\b' "$R/migracion.sql" || ! grep -Eiq '^(ALTER TABLE|CREATE )' "$R/migracion.sql"; then
        echo "  El SQL no es solo aditivo (o está vacío): no se ejecuta." >&2; volver
    fi
    sudo docker compose --env-file .env exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE"' < "$R/migracion.sql" 2> >(grep -v 'Using a password' >&2) \
        || { echo "  El SQL falló. Si alcanzó a agregar la columna, es opcional y el código anterior la ignora." >&2; volver; }
    dc run --rm --no-deps app python manage.py migrate --fake --noinput \
        || { echo "  La columna quedó creada pero no se pudo registrar la migración." >&2; volver; }
    # SQL inverso (se genera ahora, con la estructura ya creada, para que incluya el nombre real de la clave foránea).
    : > "$R/migracion_atras.sql"
    tac "$PAQUETE/migrar.txt" | while IFS= read -r m; do
        [ -n "$m" ] || continue
        dc run --rm --no-deps -T app python manage.py sqlmigrate --backwards "${m%%.*}" "${m#*.}" 2>/dev/null >> "$R/migracion_atras.sql" || true
    done
    [ -s "$R/migracion_atras.sql" ] && echo "  SQL inverso guardado en $R/migracion_atras.sql" || echo "  Aviso: no se pudo generar el SQL inverso."
    [ -f "$PAQUETE/migrar_atras.txt" ] && cp "$PAQUETE/migrar_atras.txt" "$R/migracion_previa.txt"
    echo "  Migraciones aplicadas."
else
    echo "  Imagen nueva verificada (sin migraciones pendientes)."
fi

paso "6/8 Reiniciando solo el servicio app"
dc up -d --no-deps --wait --wait-timeout 120 app || {
    echo "  El servicio nuevo no quedó sano: vuelvo a la imagen anterior." >&2
    IMG_USAR="$IMG_ACTUAL"; dc up -d --no-deps --wait --wait-timeout 120 app || true
    restaurar || true
    exit 1; }
sleep 5

paso "7/8 Verificación"
FALLO=0
l="$(codigo "$URL_PUBLICA/login/")"; s="$(codigo "$URL_PUBLICA/salud/")"; p="$(codigo "$URL_PUBLICA/control/tubo-trabajo/")"; c="$(codigo "$URL_PUBLICA/static/css/style.css")"
echo "  /login/ -> $l (200)   /salud/ -> $s (200)   /control/tubo-trabajo/ sin sesión -> $p (302)   style.css -> $c (200)"
[ "$l" = 200 ] && [ "$s" = 200 ] && [ "$p" = 302 ] && [ "$c" = 200 ] || FALLO=1
sudo docker ps --format '  {{.Names}} | {{.Image}} | {{.Status}}'
if [ "$FALLO" = 0 ] && [ "${PIN_ENV:-1}" = "1" ]; then
    # Se fija la imagen nueva en el .env (con la copia hecha arriba): solo cambia la línea APP_IMAGE.
    sed -i "s|^APP_IMAGE=$IMG_ACTUAL\$|APP_IMAGE=$NUEVA|" .env
    echo "  .env: APP_IMAGE=$(grep '^APP_IMAGE=' .env | cut -d= -f2-)  (líneas distintas vs copia: $(diff "$R/env.bak" .env | grep -c '^[<>]'), esperado 2)"
fi

paso "8/8 Resultado"
if [ "$FALLO" = 0 ]; then echo "  Desplegado y verificado."; else echo "  Verificaciones fallidas: revierta con el comando de abajo."; fi
cat <<EOF

Respaldo: $R
Revertir:  bash ~/siged-cambios/revertir-cambios-docker.sh $R
Imagen nueva: $NUEVA   (anterior: $IMG_ACTUAL)
Los manifiestos (source.manifest.json) quedan desactualizados para los archivos tocados.
EOF
