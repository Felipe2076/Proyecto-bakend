"""Igual que servidor.py pero con DEBUG apagado (como AWS), puerto 8766. Solo para capturas y pruebas de seguridad locales."""
import os, pathlib, sys
AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'web'))
os.environ['SIGED_DB'] = 'sqlite'
os.environ['SIGED_SQLITE_PATH'] = str(AQUI / 'demo.sqlite3')
os.environ['DEBUG'] = '0'
os.environ['SIGED_COOKIES_SEGURAS'] = '0'   # sin HTTPS en local
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
exec((AQUI / 'entorno_local.py').read_text(encoding='utf-8'))
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8766', '--noreload', '--insecure'])
