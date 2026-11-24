"""Crea una base SQLite local con usuarios y datos FICTICIOS para probar la web y la app móvil.

Uso (desde cualquier carpeta):
    C:\\Users\\aixav\\gestion_municipal_serena\\venv\\Scripts\\python.exe pruebas_locales\\crear_demo.py
No toca MySQL ni AWS. Borra y recrea pruebas_locales\\demo.sqlite3.
"""
import os
import pathlib
import sys
from datetime import timedelta

AQUI = pathlib.Path(__file__).resolve().parent
WEB = AQUI.parent / 'web'
BD = AQUI / 'demo.sqlite3'
sys.path.insert(0, str(WEB))
os.environ['SIGED_DB'] = 'sqlite'
os.environ['SIGED_SQLITE_PATH'] = str(BD)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
exec((AQUI / 'entorno_local.py').read_text(encoding='utf-8'))

if BD.exists():
    BD.unlink()

import django  # noqa: E402
django.setup()
from django.core.management import call_command  # noqa: E402
from django.utils import timezone  # noqa: E402

call_command('migrate', verbosity=0)

from control_gestion.models import Actividad, Compromiso, ItemFuncionario, Meta  # noqa: E402
from cuentas.fabrica_pruebas import crear_cuenta  # noqa: E402
from cuentas.models import Cargo, Delegacion  # noqa: E402
from requerimientos.models import Vecino  # noqa: E402

CLAVE = 'PruebaLocal#2026'
centro = Delegacion.objects.create(nombre='Delegación Centro (ficticia)')
rural = Delegacion.objects.create(nombre='Delegación Rural (ficticia)')
cargo_del = Cargo.objects.create(nombre='Delegado territorial')
cargo_ter = Cargo.objects.create(nombre='Gestor territorial')

# RUT ficticios con dígito verificador válido (serie 33.100.xxx de pruebas).
CUENTAS = [
    ('super', '33100011-6', 'superusuario', centro, cargo_del, 'Sofía Superusuaria (ficticio)'),
    ('admin', '33100013-2', 'administrador', centro, cargo_del, 'Andrés Administrador (ficticio)'),
    ('jefe', '33100021-3', 'jefatura', centro, cargo_del, 'Julia Jefatura (ficticio)'),
    ('fun', '33100032-9', 'funcionario', centro, cargo_ter, 'Felipe Funcionario (ficticio)'),
    ('vent', '33100045-0', 'ventanilla', rural, cargo_ter, 'Valentina Ventanilla (ficticio)'),
]
creadas = {}
for codigo, rut, rol, deleg, cargo, nombre in CUENTAS:
    creadas[codigo] = crear_cuenta(codigo=codigo.upper(), rut=rut, password=CLAVE, rol_codigo=rol, correo=f'{codigo}@siged.test',
                                   nombre=nombre, delegacion=deleg, cargo=cargo)

meta = Meta.objects.create(nombre='Visitas territoriales (ficticia)')
for u in creadas.values():
    ItemFuncionario.objects.create(funcionario=u.funcionario, meta=meta, ponderador=100, meta_trimestre=20)

hoy = timezone.localdate()
vecino = Vecino.objects.create(nombre='Vecino ficticio', delegacion=centro)
# Para probar el autocompletado por RUT y la búsqueda con faltas de ortografía.
Vecino.objects.create(nombre='María José González Pérez', rut='33500001-3', telefono='+56 9 1234 5678',
                      correo='maria.gonzalez@siged.test', direccion='Pasaje Los Aromos 123', delegacion=centro,
                      es_extranjero=True, nacionalidad='Venezuela')
from control_gestion.models import OrganizacionComunitaria  # noqa: E402
OrganizacionComunitaria.objects.create(nombre='Junta de Vecinos Los Aromos (ficticia)', delegacion=centro, territorio='Sector Centro',
                                       vigencia_directiva_hasta=hoy - timedelta(days=10), socios_activos=40)
OrganizacionComunitaria.objects.create(nombre='Club Deportivo Las Compañías (ficticio)', delegacion=centro, territorio='Sector Centro',
                                       vigencia_directiva_hasta=hoy + timedelta(days=12), socios_activos=25)
fun = creadas['fun'].funcionario
tareas = [
    ('Reparar luminaria en pasaje Los Aromos', 5, 'INGRESADO'),
    ('Coordinar operativo de limpieza con la JJVV', 2, 'PENDIENTE'),
    ('Seguimiento de poda de árboles en plaza', 8, 'EN PROCESO'),
    ('Entregar respuesta por bache en calle Colón', -1, 'REALIZADO'),
    ('Visita a adulto mayor por solicitud de ayuda', -4, 'PENDIENTE'),  # vencido
]
for desc, dias, estado in tareas:
    Compromiso.objects.create(vecino=vecino, funcionario=fun, delegacion=centro, descripcion=desc,
                              fecha_compromiso=hoy + timedelta(days=dias), estado=estado, territorio='Sector Centro (ficticio)')
maria = Vecino.objects.get(rut='33500001-3')
for desc, dias, estado in [('Gestionar ayuda social por arriendo', 6, 'EN PROCESO'), ('Orientación para trámite de residencia', -30, 'REALIZADO'),
                           ('Solicitud de luminaria frente a su domicilio', -2, 'PENDIENTE')]:
    Compromiso.objects.create(vecino=maria, funcionario=fun, delegacion=centro, descripcion=desc, fecha_ingreso=hoy - timedelta(days=max(0, -dias) + 5),
                              fecha_compromiso=hoy + timedelta(days=dias), estado=estado, territorio='Sector Centro (ficticio)')
for d in range(0, 20, 2):
    dia = hoy - timedelta(days=d)
    if dia.weekday() < 5:
        Actividad.objects.create(funcionario=fun, delegacion=centro, meta=meta, servicio='Visita ficticia', fecha_actividad=dia)

# Actividades de organizaciones (para ver el orden: lo último creado primero) y un ticket de ejemplo.
from datetime import time  # noqa: E402
from control_gestion.models import EventoAgenda  # noqa: E402
jjvv = OrganizacionComunitaria.objects.get(nombre__startswith='Junta de Vecinos Los Aromos')
for titulo, tipo, dias in [('Asamblea mensual de la junta', 'Reunión', 3), ('Operativo de limpieza del pasaje', 'Operativo', 8),
                           ('Entrega de proyecto de luminarias', 'Gestión', 1)]:
    EventoAgenda.objects.create(titulo=titulo, tipo=tipo, fecha=hoy + timedelta(days=dias), hora=time(18), delegacion=centro, organizacion=jjvv,
                                lugar='Sede social Los Aromos')
EventoAgenda.objects.create(titulo='Reunión interna de equipo', tipo='Reunión', fecha=hoy, hora=time(9), delegacion=centro)
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion  # noqa: E402
for i, (desc, estado) in enumerate([('Luminaria apagada en pasaje Los Aromos', 'Pendiente'), ('Microbasural en la esquina de la plaza', 'En Proceso'),
                                    ('Solicitud de poda de árbol que tapa el semáforo', 'Resuelto')]):
    Requerimiento.objects.create(codigo=f'TK-{1001 + i}', vecino=maria, delegacion=centro,
                                 canal_ingreso=CanalIngreso.objects.get_or_create(nombre='Ventanilla')[0],
                                 tipo_gestion=TipoGestion.objects.get_or_create(nombre='Reclamo')[0],
                                 area=AreaSoporte.objects.get_or_create(codigo='AREA-001', defaults={'nombre': 'Alumbrado y aseo'})[0],
                                 descripcion=desc, fecha_ingreso=hoy - timedelta(days=2 + i * 3), estado=estado)

print(f'Base creada: {BD}')
print(f'Contraseña de todas las cuentas: {CLAVE}')
for codigo, rut, rol, deleg, _, nombre in CUENTAS:
    print(f'  {rol:13} RUT {rut}  {nombre}')
