# Variables SOLO para pruebas locales con datos ficticios (nunca se usan en AWS).
import os as _os
for _k, _v in {
    'SECRET_KEY': 'solo-pruebas-locales-siged-no-usar-en-produccion-7d2f',
    'DEBUG': '1',
    'ALLOWED_HOSTS': '*',
    'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend',
}.items():
    _os.environ.setdefault(_k, _v)
