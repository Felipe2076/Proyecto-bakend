#!/usr/bin/env bash
# Deshace desplegar-cambios-docker.sh. Uso: bash ~/siged-cambios/revertir-cambios-docker.sh ~/respaldos-siged/cambios-FECHA
# Restaura los archivos, quita los que se agregaron, restaura el .env (APP_IMAGE) y vuelve a la imagen anterior.
set -euo pipefail
R="${1:?Indique la carpeta de respaldo}"
. "$R/datos.env"
cd "$DD"
dc() { sudo env APP_IMAGE="$IMG_ACTUAL" docker compose --env-file .env "$@" </dev/null; }
if [ -f "$R/migracion_previa.txt" ]; then
    if [ -s "$R/migracion_atras.sql" ]; then
        echo "==> Deshaciendo el cambio de estructura (SQL inverso, cuenta administradora dentro del contenedor db)"
        sudo docker compose --env-file .env exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE"' < "$R/migracion_atras.sql" 2> >(grep -v 'Using a password' >&2)
    else
        echo "==> No hay SQL inverso: solo se desregistra la migración (la columna opcional queda sin uso)."
    fi
    # Una línea «app migración» por cada app tocada.
    while IFS= read -r linea; do
        [ -n "$linea" ] || continue
        echo "==> Desregistrando migraciones con la imagen nueva (que conoce los archivos): $linea"
        # shellcheck disable=SC2086
        sudo env APP_IMAGE="$NUEVA" docker compose --env-file .env run --rm --no-deps app python manage.py migrate $linea --fake --noinput </dev/null
    done < "$R/migracion_previa.txt"
fi
echo "==> Restaurando archivos de source/"
tar -xzf "$R/archivos.tgz" -C "$DD/source"
while IFS= read -r f; do [ -n "$f" ] && rm -f "$DD/source/$f"; done < "$R/solo_nuevos.txt"
if [ -f "$R/env.bak" ]; then cp -p "$R/env.bak" "$DD/.env"; echo "==> .env restaurado (APP_IMAGE vuelve a la imagen anterior)"; fi
echo "==> Volviendo a la imagen anterior: $IMG_ACTUAL"
dc up -d --no-deps --wait --wait-timeout 120 app
sleep 5
curl -sk -o /dev/null -w '  /login/ -> %{http_code}\n' --max-time 15 "${URL_PUBLICA:-https://54.205.69.94}/login/"
sudo docker ps --format '  {{.Names}} | {{.Image}} | {{.Status}}'
echo "Listo. Si hubo migraciones, se deshicieron con el SQL inverso (las columnas y tablas nuevas se quitan). MySQL no se restaura; respaldo en $R/mysql.sql.gz y archivos privados en $R/archivos-privados.tgz."
