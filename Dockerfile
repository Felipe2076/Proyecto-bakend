# SIGED web: imagen sin root, sin herramientas de compilación y con healthcheck propio.
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Usuario sin privilegios, sin shell de ingreso y con UID fijo (coincide con el volumen de evidencias).
RUN groupadd --system --gid 10001 siged \
    && useradd --system --uid 10001 --gid siged --home-dir /app --shell /usr/sbin/nologin siged

COPY requirements.txt docker/requirements-docker.txt /tmp/
RUN pip install -r /tmp/requirements.txt -r /tmp/requirements-docker.txt && rm -f /tmp/requirements*.txt

COPY --chown=root:root . /app
# El código queda de solo lectura para el proceso web; solo los volúmenes son escribibles.
RUN mkdir -p /app/staticfiles /srv/siged/evidencias \
    && chown siged:siged /app/staticfiles /srv/siged/evidencias \
    && chmod 0750 /srv/siged/evidencias \
    && chmod 0755 /app/docker/entrypoint.sh

USER siged
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import sys,urllib.request as u; r=u.urlopen(u.Request('http://127.0.0.1:8000/salud/', headers={'Host': 'localhost'}), timeout=4); sys.exit(0 if r.status == 200 else 1)"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "-c", "/app/docker/gunicorn.conf.py"]
