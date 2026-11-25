"""Levanta la web local (datos ficticios) en el puerto 8765, visible en el Wi-Fi para el teléfono."""
import os, pathlib, sys
AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str((AQUI.parent / 'web' if (AQUI.parent / 'web').is_dir() else AQUI.parent)))
os.environ['SIGED_DB'] = 'sqlite'
os.environ['SIGED_SQLITE_PATH'] = str(AQUI / 'demo.sqlite3')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
exec((AQUI / 'entorno_local.py').read_text(encoding='utf-8'))
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8765', '--noreload'])
