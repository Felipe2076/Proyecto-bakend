#!/bin/sh
# Arranque del contenedor web. No aplica migraciones: se ejecutan a mano, tras respaldar MySQL:
#   docker compose run --rm web python manage.py migrate
set -eu

if [ -z "${SECRET_KEY:-}" ]; then
    echo "Falta SECRET_KEY en el entorno." >&2
    exit 1
fi

# Los estáticos se copian al volumen que el proxy publica. Las evidencias nunca se copian ahí.
python manage.py collectstatic --noinput --verbosity 0
python manage.py check --deploy --fail-level ERROR

exec "$@"
