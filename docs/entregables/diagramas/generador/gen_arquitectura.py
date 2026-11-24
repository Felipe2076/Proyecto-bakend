"""Componentes y despliegue de SIGED-SGR (según el código y la configuración del servidor)."""
from drawio import Pagina, DEPENDE, ASOC, FLUJO

AZUL, NAR, VERDE, ROSA, LILA, GRIS = '#EAF1FB', '#FFF4E0', '#EAF6EA', '#FBE3E6', '#F1ECF8', '#F2F2F2'
USA = DEPENDE + 'edgeStyle=orthogonalEdgeStyle;rounded=0;'


def franja(p, titulo, y, h, color, ancho=1560):
    p.vertice('', 30, y, ancho, h, f'rounded=0;fillColor={color};strokeColor=none;opacity=60;', obst=False)
    p.vertice(f'<b>{titulo}</b>', 36, y + 6, 100, h - 12, 'text;html=1;fontSize=11;align=left;verticalAlign=top;whiteSpace=wrap;fontColor=#555555;')


def pagina_componentes():
    p = Pagina('01 Componentes lógicos', 1960, 1000)
    p.titulo('Diagrama de componentes · SIGED-SGR (aplicación Django modular)', 30, 10,
             sub='Componentes de una misma aplicación (no microservicios), ordenados por capa. Flecha punteada = dependencia «use»; todo acceso a datos pasa por el ORM.')
    marco = p.marco('[component] SIGED-SGR', 20, 70, 1920, 900, tipo='cmp')
    franja(p, 'Clientes', 100, 120, '#F4F4F4')
    franja(p, 'Presentación', 230, 130, '#EEF4FB')
    franja(p, 'Negocio (apps Django)', 370, 150, '#F3F9F1')
    franja(p, 'Servicios transversales', 530, 130, '#F7F3FA')
    franja(p, 'Datos y servicios externos', 670, 280, '#FBF6EE')
    X0, X1, X2, W = 150, 620, 1090, 420
    nav = p.nodo('Navegador web (funcionarios y vecino)', 385, 120, 420, 80, GRIS, 'device')
    app = p.nodo('App Android SIGED (en desarrollo)', X2, 120, W, 80, GRIS, 'device')
    pub = p.componente('publico', 'portal informativo: inicio, servicios, delegaciones, contacto', X0, 250, W, 90, GRIS)
    tpl = p.componente('templates / static', 'base.html con barra del trimestre, menú por rol, Bootstrap 5, SweetAlert2, normas gráficas La Serena',
                       X1, 250, W, 90, AZUL)
    api = p.componente('API móvil v1', '/api/v1/: sesión, actividades, evidencia, revisión, compromisos, Excel', X2, 250, W, 90, LILA)
    req = p.componente('requerimientos', 'tickets TK, listado con semáforo, Kanban, encuestas con enlace firmado, atenciones', X0, 395, W, 100, NAR)
    cue = p.componente('cuentas', 'login, recuperación por código, usuarios, grupos y permisos, mantenedores, alcance por delegación',
                       X1, 395, W, 100, AZUL)
    cg = p.componente('control_gestion', 'dashboard, tubo (tabla y tarjetas), actividades y revisión, agenda, semáforo SGR, organizaciones, '
                      'ausencias, reportes Excel', X2, 395, W, 100, VERDE)
    core = p.componente('core', 'validación de RUT, códigos correlativos, búsqueda, paginación, Excel, seguridad', 385, 550, W, 90, GRIS)
    auth = p.componente('django.contrib.auth', 'User, Group, Permission, sesiones, CSRF', 855, 550, W, 90, GRIS)
    orm = p.componente('Django ORM + migraciones', 'modelos de cuentas, requerimientos y control_gestion', X1, 690, W, 80, GRIS)
    smtp = p.nodo('Servidor de correo (SMTP)', X0, 700, 300, 70, GRIS, 'external')
    bd = p.bd('MySQL 8.4\nsiged_frontend', X1 + 110, 830, 200, 100)
    evi = p.bd('Almacenamiento de evidencias\n(volumen privado)', X2 + 110, 690, 200, 100)
    for a, b, et in [(nav, pub, 'HTTPS'), (nav, tpl, 'HTTPS'), (app, api, 'HTTPS / JSON'),
                     (req, tpl, '«render»'), (cue, tpl, '«render»'), (cg, tpl, '«render»'), (api, cg, '«use»'),
                     (req, cue, '«use» ámbito'), (cg, cue, '«use» ámbito y perfiles'),
                     (req, core, '«use»'), (cue, core, '«use»'), (cg, core, '«use»'), (cue, auth, '«use»'), (cg, auth, '«use»'),
                     (req, orm, ''), (cue, orm, ''), (cg, orm, ''), (orm, bd, 'SQL · usuario con mínimo privilegio'),
                     (cg, evi, 'archivos validados'), (cue, smtp, 'códigos y activación')]:
        p.arista(a, b, et, USA, rutear=True)
    p.nota('Reglas de diseño aplicadas:\n• El permiso y la delegación se validan en el servidor (cuentas.ambito / alcance), no ocultando botones.\n'
           '• La app móvil usa la misma lógica por la API; nunca se conecta a MySQL.\n'
           '• Las evidencias no se publican como estáticos: se sirven por una vista que verifica permisos.', 1610, 395, 310)
    return p


def pagina_control_gestion():
    p = Pagina('02 Componentes · control_gestion por dentro', 1960, 980)
    p.titulo('Diagrama de componentes · módulos internos de control_gestion', 30, 10,
             sub='Cada archivo Python agrupa una responsabilidad. Las flechas muestran las importaciones reales entre módulos: las vistas coordinan y las reglas viven en módulos propios.')
    p.marco('[component] control_gestion', 20, 70, 1920, 860, tipo='cmp')
    franja(p, 'Entrada', 100, 140, '#F4F4F4', 1890)
    franja(p, 'Reglas de operación', 250, 170, '#F3F9F1', 1890)
    franja(p, 'Cálculo y período', 430, 160, '#EEF4FB', 1890)
    franja(p, 'Apoyo', 600, 160, '#F7F3FA', 1890)
    franja(p, 'Datos', 770, 140, '#FBF6EE', 1890)
    c = [150, 500, 850, 1200, 1550]
    W = 300
    vistas = p.componente('vistas web', 'views · views_extra · web_revision: rutas /control/…', 330, 125, 520, 90, VERDE)
    api = p.componente('api_movil + urls_movil', '/api/v1/: sesión con vencimiento, cuotas de intentos, envíos idempotentes', 1200, 125, 520, 90, LILA)
    mov = p.componente('movimientos', 'mover compromisos y atenciones del tubo; reprogramar agenda (409 si otro cambió)', c[0], 290, W, 100)
    con = p.componente('consultas', 'registro de actividad: 7 por día, cierre el martes, sin fechas futuras', c[1], 290, W, 100)
    rev = p.componente('revision', 'aprobar, rechazar o pedir corrección; sin autoaprobación; suma una vez', c[2], 290, W, 100)
    evi = p.componente('evidencias', 'validación de archivo (10 MB), vista protegida, felicitaciones', c[3], 290, W, 100)
    kan = p.componente('kanban', 'mover tickets del tablero con control de concurrencia', c[4], 290, W, 100)
    pan = p.componente('panel_personal', 'pestaña personal por cargo del funcionario', c[2], 460, W, 100)
    ind = p.componente('indicadores', 'cumplimiento ponderado, tope 120 %, % esperado por días', c[3], 460, W, 100)
    tri = p.componente('trimestres', 'trimestre vigente, nombre y días automáticos', c[4], 460, W, 100)
    rep = p.componente('reportes', 'ámbito por delegación, perfil de acceso y Excel', c[0], 630, W, 100)
    frm = p.componente('forms', 'validación de formularios: RUT de creación, períodos, agenda', c[1], 630, W, 100)
    ter = p.componente('territorios', 'territorios por delegación para organizaciones', c[2], 630, W, 100)
    aus = p.componente('ausencias', 'descuento de días por licencias y vacaciones', c[4], 630, W, 100)
    mod = p.componente('models.py', '17 modelos: Actividad, Compromiso, Medicion, OrganizacionComunitaria, Ausencia, …', 500, 800, 1000, 80, GRIS)
    for a, b in [(vistas, mov), (vistas, con), (vistas, rev), (vistas, evi), (vistas, kan), (vistas, ind), (vistas, rep),
                 (api, con), (api, rev), (api, evi), (rev, evi), (con, evi), (mov, con), (mov, rep), (con, rep),
                 (ind, tri), (ind, aus), (ind, evi), (pan, ind), (frm, ter)]:
        p.arista(a, b, '', USA, rutear=True)
    p.nota('Todos los módulos usan models.py; se omiten esas flechas para que el diagrama se lea.\n'
           'reportes concentra el filtro por delegación (ámbito) que usan las vistas, consultas y movimientos.', 1550, 800, 370)
    return p


def pagina_despliegue():
    p = Pagina('03 Despliegue en AWS', 1800, 1120)
    p.titulo('Diagrama de despliegue · producción en AWS EC2 con Docker', 30, 10,
             sub='Topología verificada en el servidor: un EC2 con proxy HTTPS en el host y dos contenedores Docker (app y db) en una red interna. '
                 'Solo el puerto 443 es público.')
    marco = p.marco('[deployment] SIGED-SGR producción', 20, 70, 1760, 1030, tipo='dep')
    # Clientes y administración (fuera de AWS)
    pc = p.nodo('PC del funcionario\nNavegador web', 50, 170, 250, 90, GRIS, 'device')
    cel = p.nodo('Teléfono Android\nApp SIGED (en desarrollo)', 50, 330, 250, 90, GRIS, 'device')
    adm = p.nodo('Administrador técnico\nAWS CloudShell', 50, 690, 250, 90, GRIS, 'device')
    # Nodo EC2
    ec2 = p.nodo('AWS EC2 · Amazon Linux (us-east-1) · IP pública', 380, 110, 1080, 830, '#FFFFFF', 'node', contenedor=True)
    apache = p.nodo('Apache 2.4 (host)\nTLS :443 → proxy 127.0.0.1:8000', 420, 230, 290, 110, AZUL, 'executionEnvironment')
    docker = p.nodo('Docker Engine + Compose', 770, 170, 660, 500, '#FAFAFA', 'executionEnvironment', contenedor=True)
    appc = p.nodo('Contenedor app (siged-app-1)\nGunicorn + Django 6.1', 800, 240, 280, 220, VERDE, 'container')
    p.artefacto('siged-app:cambio-AAAAMMDD-HHMMSS', 815, 330, 250, 38, '#FFFFFF')
    p.artefacto('.env (secretos, fuera de Git)', 815, 378, 250, 36, '#FFFFFF')
    dbc = p.nodo('Contenedor db (siged-db-1)\nMySQL 8.4 · sin puerto publicado', 1120, 240, 280, 220, NAR, 'container')
    p.artefacto('BD siged_frontend', 1135, 340, 250, 38, '#FFFFFF')
    vol2 = p.bd('volumen\nevidencias', 865, 540, 150, 90)
    vol1 = p.bd('volumen\nmysql-datos', 1185, 540, 150, 90)
    resp = p.bd('~/respaldos-siged\n(MySQL, .env, archivos)', 465, 520, 200, 110)
    smtp = p.nodo('Servidor de correo SMTP', 1510, 330, 240, 80, GRIS, 'external')
    for a, b, et in [(pc, apache, 'HTTPS :443'), (cel, apache, 'HTTPS :443 · /api/v1/'), (apache, appc, 'HTTP 127.0.0.1:8000'),
                     (appc, dbc, 'TCP 3306 (red interna)'), (dbc, vol1, ''), (appc, vol2, ''), (appc, smtp, 'SMTP'),
                     (adm, resp, 'EC2 Instance Connect'), (adm, docker, 'docker compose · scripts de despliegue')]:
        p.arista(a, b, et, ASOC, rutear=True)
    nota = p.nota('Controles de seguridad desplegados (OWASP):\n'
           '• Solo el puerto 443 es público; MySQL no publica puertos y solo lo alcanza el contenedor app.\n'
           '• El usuario MySQL de la aplicación solo tiene SELECT/INSERT/UPDATE/DELETE; los cambios de esquema se aplican aparte, con respaldo.\n'
           '• DEBUG=False, cookies de sesión y CSRF seguras, X-Frame-Options DENY y cabeceras de seguridad de Django.\n'
           '• Las evidencias viven en un volumen privado y se entregan por una vista que verifica permisos.\n'
           '• Cada despliegue: verificación SHA-256, respaldo, imagen nueva y reversión automática si falla.', 420, 720, 1010)
    fondo = p.cajas[nota][1] + p.cajas[nota][3] + 30
    p.redimensionar(ec2, h=fondo - 110)
    p.redimensionar(marco, h=fondo - 40)
    p.alto = fondo + 60
    return p


def paginas():
    return [pagina_componentes(), pagina_control_gestion(), pagina_despliegue()]
