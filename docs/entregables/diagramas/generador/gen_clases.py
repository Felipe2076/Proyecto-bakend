"""Diagrama de clases SIGED-SGR por módulo. Atributos, enumeraciones y relaciones tomados de los models.py.

Los conectores se trazan con ruteo.py: salen perpendiculares de cada clase y nunca atraviesan otra caja.
"""
from drawio import Pagina, ASOC_NAV, DEPENDE

# paquete -> (cabecera, borde)
PAQ = {
    'cuentas': ('#DAE8FC', '#6C8EBF'), 'requerimientos': ('#FFE6CC', '#D79B00'), 'control_gestion': ('#D5E8D4', '#82B366'),
    'territorio': ('#F8CECC', '#B85450'), 'api': ('#E1D5E7', '#9673A6'), 'django': ('#F5F5F5', '#666666'), 'enum': ('#FFF2CC', '#D6B656'),
}

# nombre: (paquete, atributos, métodos)
CLASES = {
    'User (Django)': ('django', ['- username: str', '- password: hash', '- is_active: bool'], []),
    'Group (Django)': ('django', ['- name: str', '- permissions: Permission [*]'], []),
    'Rol': ('cuentas', ['- codigo: slug {único}', '- nombre: str {único}', '- descripcion: str'], []),
    'Delegacion': ('cuentas', ['- nombre: str {único}', '- direccion: str', '- comuna: str = "La Serena"'], []),
    'Cargo': ('cuentas', ['- codigo: str (CAR-)', '- nombre: str {único}', '- descripcion: str', '- modulo_principal: str'], []),
    'Funcionario': ('cuentas', ['- codigo: str (FUN-)', '- rut: str {único}', '- nombres: str', '- apellido_paterno: str', '- apellido_materno: str',
                                '- fecha_ultimo_ingreso: date', '- estado: activo | inactivo', '- es_simulacion: bool'],
                    ['+ nombre_completo(): str', '+ nombre_mostrado(): str']),
    'Usuario': ('cuentas', ['- codigo: str (USR-)', '- username: str {único, RUT}', '- nombre: str', '- correo: email {único}',
                            '- estado: activo | inactivo', '- creado: datetime'], ['+ nombre_mostrado(): str', '+ activo(): bool']),
    'ParametroSistema': ('cuentas', ['- nombre_sistema: str', '- sla_verde_max_dias: int = 3', '- sla_amarillo_max_dias: int = 5',
                                     '- meta_tubo_porcentaje: int = 80', '- encuesta_habilitada: bool', '- max_atenciones_mismo_usuario: int = 3'], []),
    'CodigoUnUso': ('cuentas', ['- proposito: str', '- codigo_hash: HMAC-SHA256', '- canal: correo', '- expira_en: datetime', '- intentos: int',
                                '- usado_en: datetime', '- anulado_en: datetime', '- ip_origen: str'], []),
    'SecuenciaCodigo': ('cuentas', ['- clave: str {único}', '- ultimo: int'], []),
    'Vecino': ('requerimientos', ['- nombre: str', '- rut: str {único, opcional}', '- direccion: str', '- telefono: str', '- correo: email',
                                  '- territorio: str', '- estado: activo | inactivo'], ['+ nombre_mostrado(): str']),
    'TipoGestion': ('requerimientos', ['- nombre: str {único}', '- descripcion: str'], []),
    'CanalIngreso': ('requerimientos', ['- nombre: str {único}', '- activo: bool'], []),
    'AreaSoporte': ('requerimientos', ['- codigo: str (AREA-)', '- nombre: str {único}', '- tiempo_promedio_dias: decimal',
                                       '- porcentaje_cumplimiento: int', '- satisfaccion_promedio: decimal'], []),
    'Requerimiento': ('requerimientos', ['- codigo: str (TK-)', '- descripcion: text', '- fecha_ingreso: date', '- asignado_a: str (cuadrilla)',
                                         '- estado: EstadoTicket', '- evaluacion_satisfaccion: 1..5', '- comentario_satisfaccion: text'],
                      ['+ dias_transcurridos(): int']),
    'TipoAtencion': ('requerimientos', ['- nombre: str {único}', '- descripcion: str'], []),
    'SubAtencion': ('requerimientos', ['- nombre: str', '- descripcion: str'], []),
    'Atencion': ('requerimientos', ['- fecha: datetime', '- estado: pendiente | en_proceso | cerrada', '- observacion: text'], []),
    'Meta': ('control_gestion', ['- codigo: str', '- nombre: str {único}', '- descripcion: str'], []),
    'ItemFuncionario': ('control_gestion', ['- codigo: str', '- ponderador: 0..100 %', '- meta_trimestre: int', '- avance_actual: int'],
                        ['+ porcentaje_avance(): float  {tope 120}']),
    'Actividad': ('control_gestion', ['- codigo: str (ACT-)', '- fecha_actividad: date', '- contacto: str', '- servicio: str',
                                      '- codigo_verificador: str', '- evidencia_archivo: File  {≤ 10 MB}', '- tipo_registro: TipoRegistro',
                                      '- estado_revision: EstadoRevision', '- version_revision: int', '- punto_validado: bool',
                                      '- fecha_validacion: datetime'], ['+ nombre_archivo_evidencia(): str']),
    'RevisionActividad': ('control_gestion', ['- estado_anterior: EstadoRevision', '- estado_nuevo: EstadoRevision', '- comentario: text',
                                              '- fecha: datetime', '- version: int'], []),
    'Compromiso': ('control_gestion', ['- codigo: str (TUB-)', '- descripcion: str', '- origen: INT | EXT', '- territorio: str', '- apoyo: str',
                                       '- observaciones: text', '- fecha_ingreso: date', '- fecha_compromiso: date', '- estado: EstadoCompromiso'],
                   ['+ vencido(): bool  {calculado}']),
    'CambioCompromiso': ('control_gestion', ['- estado_anterior: str', '- estado_nuevo: str', '- observacion_anterior: text',
                                             '- observacion_nueva: text', '- fecha: datetime'], []),
    'Medicion': ('control_gestion', ['- codigo: str', '- periodo: str {único, automático}', '- fecha_inicio: date', '- fecha_termino: date',
                                     '- dias_totales: int {automático}', '- meta_cumplimiento_tubo: int = 80', '- descripcion: text'], []),
    'Ausencia': ('control_gestion', ['- tipo: TipoAusencia', '- fecha_inicio: date', '- fecha_termino: date', '- observacion: str'], []),
    'Notificacion': ('control_gestion', ['- codigo: str (NTF-)', '- titulo: str', '- mensaje: text', '- tipo: info | aviso | agenda',
                                         '- fecha: date', '- enlace: str'], []),
    'TerritorioDelegacion': ('territorio', ['- nombre: str'], []),
    'OrganizacionComunitaria': ('territorio', ['- codigo: str (ORG-)', '- clave_origen: str {único}', '- nombre: str', '- descripcion: text',
                                               '- presidente_nombre / _rut: str', '- tesorero_nombre / _rut: str', '- secretario_nombre / _rut: str',
                                               '- domicilio_legal: str', '- territorio: str', '- socios_activos: int', '- fecha_constitucion: date',
                                               '- registro_personalidad_juridica: str', '- verificada: bool', '- activa: bool'],
                                ['+ directiva(): list']),
    'EventoAgenda': ('territorio', ['- codigo: str (AG-)', '- titulo: str', '- tipo: str', '- fecha: date', '- hora: time', '- lugar: str'], []),
    'SesionMovil': ('api', ['- huella: sha256 {único}', '- clave_version: str', '- expira: datetime'], []),
    'IntentosMovil': ('api', ['- clave: str {PK, hash de IP o cuenta}', '- inicio: datetime', '- intentos: int'], []),
    'EnvioMovil': ('api', ['- client_id: UUID', '- huella: str'], []),
    # Enumeraciones (TextChoices de Django)
    'EstadoTicket': ('enum', ['Pendiente', 'En Proceso', 'Cuello Botella Central', 'Resuelto'], []),
    'TipoRegistro': ('enum', ['RESULTADO', 'COORDINACION', 'DELEGADO', 'FELICITACION'], []),
    'EstadoRevision': ('enum', ['HISTORICA', 'PENDIENTE', 'APROBADA', 'RECHAZADA', 'CORRECCION'], []),
    'EstadoCompromiso': ('enum', ['INGRESADO', 'PENDIENTE', 'EN PROCESO', 'REALIZADO'], []),
    'TipoAusencia': ('enum', ['LICENCIA', 'VACACIONES', 'ADMINISTRATIVO', 'EMERGENCIA', 'COMPENSATORIO'], []),
}

# (origen, destino, multiplicidad origen, multiplicidad destino, rol)  — ForeignKey/OneToOne de origen hacia destino
RELACIONES = [
    ('Usuario', 'User (Django)', '0..1', '0..1', 'user'), ('Usuario', 'Rol', '0..*', '1', 'rol'), ('Rol', 'Group (Django)', '0..1', '0..1', 'grupo'),
    ('Usuario', 'Funcionario', '0..1', '1', 'funcionario'), ('Usuario', 'Delegacion', '0..*', '0..1', 'delegacion'),
    ('Usuario', 'Cargo', '0..*', '0..1', 'cargo'), ('Funcionario', 'Cargo', '0..*', '1', 'cargo'),
    ('Funcionario', 'Delegacion', '0..*', '1', 'delegacion'), ('CodigoUnUso', 'Usuario', '0..*', '0..1', 'usuario'),
    ('Vecino', 'Delegacion', '0..*', '0..1', 'delegacion'), ('Vecino', 'TipoGestion', '0..*', '0..1', 'tipo_gestion'),
    ('Requerimiento', 'Vecino', '0..*', '1', 'vecino'), ('Requerimiento', 'Delegacion', '0..*', '1', 'delegacion'),
    ('Requerimiento', 'CanalIngreso', '0..*', '1', 'canal_ingreso'), ('Requerimiento', 'TipoGestion', '0..*', '1', 'tipo_gestion'),
    ('Requerimiento', 'AreaSoporte', '0..*', '1', 'area'), ('Requerimiento', 'Funcionario', '0..*', '0..1', 'funcionario'),
    ('AreaSoporte', 'Funcionario', '0..*', '0..1', 'encargado'), ('SubAtencion', 'TipoAtencion', '0..*', '1', 'tipo_atencion'),
    ('Atencion', 'Vecino', '0..*', '1', 'vecino'), ('Atencion', 'TipoAtencion', '0..*', '1', 'tipo_atencion'),
    ('Atencion', 'SubAtencion', '0..*', '1', 'sub_atencion'), ('Atencion', 'Delegacion', '0..*', '1', 'delegacion'),
    ('Atencion', 'Usuario', '0..*', '1', 'usuario'),
    ('ItemFuncionario', 'Funcionario', '0..*', '1', 'funcionario'), ('ItemFuncionario', 'Meta', '0..*', '1', 'meta'),
    ('Actividad', 'Funcionario', '0..*', '1', 'funcionario'), ('Actividad', 'Delegacion', '0..*', '1', 'delegacion'),
    ('Actividad', 'Meta', '0..*', '1', 'meta (ítem)'), ('Actividad', 'User (Django)', '0..*', '0..1', 'creado_por / validado_por'),
    ('RevisionActividad', 'Actividad', '0..*', '1', 'actividad'), ('RevisionActividad', 'User (Django)', '0..*', '1', 'autor'),
    ('Compromiso', 'Vecino', '0..*', '1', 'vecino'), ('Compromiso', 'Funcionario', '0..*', '1', 'funcionario'),
    ('Compromiso', 'Delegacion', '0..*', '1', 'delegacion'), ('CambioCompromiso', 'Compromiso', '0..*', '1', 'compromiso'),
    ('CambioCompromiso', 'User (Django)', '0..*', '1', 'autor'),
    ('EventoAgenda', 'Delegacion', '0..*', '1', 'delegacion'), ('EventoAgenda', 'Funcionario', '0..*', '0..1', 'responsable'),
    ('EventoAgenda', 'OrganizacionComunitaria', '0..*', '0..1', 'organizacion'), ('Medicion', 'Delegacion', '0..*', '1', 'delegacion_piloto'),
    ('Ausencia', 'Funcionario', '0..*', '1', 'funcionario'), ('Ausencia', 'Delegacion', '0..*', '1', 'delegacion'),
    ('TerritorioDelegacion', 'Delegacion', '0..*', '1', 'delegacion'), ('OrganizacionComunitaria', 'Delegacion', '0..*', '0..1', 'delegacion'),
    ('SesionMovil', 'Usuario', '0..*', '1', 'usuario'), ('EnvioMovil', 'User (Django)', '0..*', '1', 'usuario'),
    ('EnvioMovil', 'Actividad', '0..*', '1', 'actividad'),
]
USOS_ENUM = [('Requerimiento', 'EstadoTicket'), ('Actividad', 'TipoRegistro'), ('Actividad', 'EstadoRevision'),
             ('RevisionActividad', 'EstadoRevision'), ('Compromiso', 'EstadoCompromiso'), ('Ausencia', 'TipoAusencia')]

GAP_X, GAP_Y, X0, Y0 = 130, 100, 60, 130


def dibujar(p, filas, paquete_propio, referencias=()):
    """filas: listas de nombres (None = hueco). Las columnas se alinean por el ancho máximo de cada columna."""
    def datos(n):
        paq, atrs, mets = CLASES[n]
        ref = n in referencias
        if ref:
            atrs, mets = atrs[:2] + (['…'] if len(atrs) > 2 else []), []
        return paq, atrs, mets, ref

    ncol = max(len(f) for f in filas)
    anchos = [0] * ncol
    altos = []
    for f in filas:
        alto = 0
        for c, n in enumerate(f):
            if n:
                paq, atrs, mets, ref = datos(n)
                w, h, _ = Pagina.medida_clase(n, atrs, mets, 'enumeration' if paq == 'enum' else '')
                anchos[c] = max(anchos[c], w)
                alto = max(alto, h)
        altos.append(alto)
    ids, y = {}, Y0
    for f, alto in zip(filas, altos):
        x = X0
        for c, n in enumerate(f):
            if n:
                paq, atrs, mets, ref = datos(n)
                cab, borde = PAQ['django'] if ref and paq != 'django' else PAQ[paq]
                w, h, _ = Pagina.medida_clase(n, atrs, mets, 'enumeration' if paq == 'enum' else '')
                ids[n], _, _ = p.clase_uml(n, atrs, x + (anchos[c] - w) / 2, y, mets, cab, borde,
                                           'enumeration' if paq == 'enum' else '')
            x += anchos[c] + GAP_X
        y += alto + GAP_Y
    for a, b, ma, mb, rol in RELACIONES:
        if a in ids and b in ids and not (a in referencias and b in referencias):
            p.arista(ids[a], ids[b], rol, ASOC_NAV + 'fontSize=10;', ext_a=ma, ext_b=mb, rutear=True)
    for a, b in USOS_ENUM:
        if a in ids and b in ids:
            p.arista(ids[a], ids[b], '', DEPENDE + 'strokeColor=#B09030;', rutear=True)
    return ids, X0 + sum(anchos) + GAP_X * (ncol - 1), y


def leyenda(p, x, y):
    items = [('cuentas', 'cuentas'), ('requerimientos', 'requerimientos'), ('control_gestion', 'control_gestion'),
             ('territorio', 'control_gestion · territorio y organizaciones'), ('api', 'control_gestion · API móvil'),
             ('enum', '«enumeration» (TextChoices)'), ('django', 'clase de otro paquete o de Django (resumida)')]
    p.vertice('<b>Leyenda</b>', x, y, 200, 18, 'text;html=1;fontSize=11;align=left;')
    for i, (k, txt) in enumerate(items):
        cab, borde = PAQ[k]
        p.vertice('', x, y + 24 + i * 20, 22, 14, f'fillColor={cab};strokeColor={borde};')
        p.vertice(txt, x + 30, y + 21 + i * 20, 320, 20, 'text;html=1;fontSize=10;align=left;')
    p.vertice('→ referencia (ForeignKey) hacia la clase apuntada · ⇢ usa el tipo enumerado', x, y + 24 + len(items) * 20, 420, 20,
              'text;html=1;fontSize=10;align=left;')


def pagina(nombre, titulo, sub, marco, filas, paquete, referencias=(), nota=None):
    p = Pagina(nombre, 1800, 1400)
    p.titulo(titulo, 30, 10, sub=sub)
    ids, ancho, alto = dibujar(p, filas, paquete, referencias)
    ancho_total = max(ancho + 420, 1300)
    leyenda(p, ancho + 20, Y0)
    fondo = alto - GAP_Y + 40
    if nota:
        n = p.nota(nota, ancho + 20, Y0 + 230, 380)
        fondo = max(fondo, p.cajas[n][1] + p.cajas[n][3] + 30)
    p.marco(marco, 20, 70, ancho_total, fondo - 70, tipo='class')
    p.ancho, p.alto = ancho_total + 60, fondo + 40
    return p


def pagina_paquetes():
    p = Pagina('01 Clases · vista de paquetes', 1700, 900)
    p.titulo('Diagrama de paquetes del modelo de dominio', 30, 10,
             sub='33 clases persistentes en 3 aplicaciones Django + autenticación de Django. Las flechas indican qué paquete referencia a cuál.')
    p.marco('[package] Modelo de dominio SIGED-SGR', 20, 70, 1660, 810, tipo='pkg')
    contenido = {
        'cuentas': ['Rol', 'Usuario', 'Funcionario', 'Cargo', 'Delegacion', 'ParametroSistema', 'CodigoUnUso', 'SecuenciaCodigo'],
        'requerimientos': ['Vecino', 'Requerimiento', 'TipoGestion', 'CanalIngreso', 'AreaSoporte', 'Atencion', 'TipoAtencion', 'SubAtencion'],
        'control_gestion': ['Meta', 'ItemFuncionario', 'Actividad', 'RevisionActividad', 'Compromiso', 'CambioCompromiso', 'Medicion',
                            'Ausencia', 'Notificacion'],
        'territorio': ['TerritorioDelegacion', 'OrganizacionComunitaria', 'EventoAgenda'],
        'api': ['SesionMovil', 'IntentosMovil', 'EnvioMovil'],
        'django': ['User', 'Group', 'Permission', 'Session'],
    }
    pos = {'cuentas': (640, 120, 'cuentas'), 'requerimientos': (100, 120, 'requerimientos'), 'control_gestion': (1180, 120, 'control_gestion'),
           'territorio': (1180, 520, 'control_gestion · territorio y organizaciones'), 'api': (640, 520, 'control_gestion · API móvil'),
           'django': (100, 520, 'django.contrib.auth')}
    ids = {}
    for k, (x, y, titulo) in pos.items():
        cab, borde = PAQ[k]
        lista = '<br>'.join(contenido[k])
        ids[k] = p.vertice(f'<b>{titulo}</b><hr size="1"><div style="text-align:left;padding-left:10px">{lista}</div>', x, y, 420,
                           60 + 17 * len(contenido[k]),
                           f'shape=folder;tabWidth=150;tabHeight=22;tabPosition=left;html=1;whiteSpace=wrap;verticalAlign=top;'
                           f'spacingTop=26;fontSize=11;fillColor={cab};strokeColor={borde};')
    deps = [('requerimientos', 'cuentas', 'Delegacion, Funcionario, Usuario'), ('control_gestion', 'cuentas', 'Funcionario, Delegacion'),
            ('control_gestion', 'requerimientos', 'Vecino'), ('control_gestion', 'django', 'User (autor de revisiones y cambios)'),
            ('territorio', 'cuentas', 'Delegacion, Funcionario'), ('api', 'cuentas', 'Usuario'), ('api', 'control_gestion', 'Actividad'),
            ('cuentas', 'django', 'User, Group')]
    for a, b, et in deps:
        p.arista(ids[a], ids[b], f'«import» {et}', DEPENDE + 'fontSize=9;', rutear=True)
    return p


def paginas():
    return [
        pagina_paquetes(),
        pagina('02 Clases · cuentas', 'Diagrama de clases · paquete cuentas (acceso, roles y delegaciones)',
               'Cada Usuario tiene un Rol (y su Group de permisos), una Delegación y un Funcionario. El rol «superusuario» ve todas las delegaciones.',
               '[package] cuentas',
               [['User (Django)', 'Usuario', 'Rol', 'Group (Django)'], ['CodigoUnUso', 'Funcionario', 'Cargo'],
                ['ParametroSistema', 'Delegacion', 'SecuenciaCodigo']], 'cuentas',
               nota='Roles: superusuario, administrador, jefatura, funcionario, ventanilla.\nEl Group «SIGED: rol» guarda los permisos; '
                    'los modelos globales solo los modifica el superusuario.\nCodigoUnUso guarda solo el hash del código, con vencimiento e intentos.\n'
                    'SecuenciaCodigo genera los correlativos (USR-, FUN-, TUB-, ACT-, ORG-…).'),
        pagina('03 Clases · requerimientos', 'Diagrama de clases · paquete requerimientos (atención ciudadana)',
               'Ticket (Requerimiento) y Atención comparten Vecino y Delegación. Tipo y Sub atención pertenecen a Atención, no al ticket.',
               '[package] requerimientos',
               [['TipoGestion', 'CanalIngreso', 'AreaSoporte', 'Funcionario'], ['Vecino', 'Requerimiento', 'EstadoTicket'],
                ['Delegacion', 'Atencion', 'Usuario'], [None, 'TipoAtencion', 'SubAtencion']], 'requerimientos',
               referencias=('Funcionario', 'Delegacion', 'Usuario'),
               nota='El semáforo del ticket usa dias_transcurridos() y los umbrales de ParametroSistema (verde ≤ 3, amarillo ≤ 5 días).\n'
                    'La encuesta 1–5 se guarda en el Requerimiento; el vecino responde por un enlace firmado de 30 días.'),
        pagina('04 Clases · actividades y revisión', 'Diagrama de clases · actividades, metas y revisión de evidencias',
               'Cada actividad aporta a un ítem del funcionario y solo suma cuando un revisor distinto del autor la aprueba (RevisionActividad).',
               '[package] control_gestion · actividades',
               [['Funcionario', 'ItemFuncionario', 'Meta'], ['Delegacion', 'Actividad', 'RevisionActividad'],
                ['TipoRegistro', 'EstadoRevision', 'User (Django)']], 'control_gestion', referencias=('Funcionario', 'Delegacion', 'User (Django)'),
               nota='Reglas de la matriz SGR en el código: máx. 7 actividades por día, semana cerrada el martes siguiente, sin fechas futuras; '
                    'solo un RESULTADO aprobado suma (una vez) y el avance por ítem tiene tope de 120 %.'),
        pagina('05 Clases · compromisos', 'Diagrama de clases · compromisos del tubo y su historial',
               '"Vencido" no se guarda: se calcula con fecha_compromiso y estado. Cada cambio de estado deja un CambioCompromiso con su autor.',
               '[package] control_gestion · compromisos',
               [['Vecino', 'Compromiso', 'EstadoCompromiso'], ['Delegacion', 'CambioCompromiso', 'Funcionario'], [None, 'User (Django)']],
               'control_gestion', referencias=('Vecino', 'Delegacion', 'Funcionario', 'User (Django)')),
        pagina('06 Clases · medición y ausencias', 'Diagrama de clases · período trimestral, ausencias y avisos',
               'Medicion define el trimestre vigente (nombre y días automáticos). Ausencia descuenta días de la meta. Notificacion es un aviso interno sin FK.',
               '[package] control_gestion · medición',
               [['Medicion', 'Delegacion', 'Ausencia', 'TipoAusencia'], ['Notificacion', None, 'Funcionario']], 'control_gestion',
               referencias=('Delegacion', 'Funcionario')),
        pagina('07 Clases · territorio y organizaciones', 'Diagrama de clases · territorio, organizaciones comunitarias y agenda (nuevo requerimiento)',
               'Responde al nuevo requerimiento del cliente: base de JJVV y organizaciones funcionales por delegación y territorio.',
               '[package] control_gestion · territorio y organizaciones',
               [['TerritorioDelegacion', 'Delegacion', 'OrganizacionComunitaria'], [None, 'Funcionario', 'EventoAgenda']], 'territorio',
               referencias=('Delegacion', 'Funcionario'),
               nota='OrganizacionComunitaria.territorio se elige entre los TerritorioDelegacion de su delegación (formulario).\n'
                    'La importación usa clave_origen para no duplicar.\nSin delegación, la organización solo la ve el superusuario.'),
        pagina('08 Clases · API móvil', 'Diagrama de clases · soporte de la aplicación móvil (API v1)',
               'Sesiones con vencimiento, límite de intentos y envíos idempotentes (client_id) para que un reintento no duplique actividades.',
               '[package] control_gestion · API móvil',
               [['Usuario', 'SesionMovil', 'IntentosMovil'], ['User (Django)', 'EnvioMovil', 'Actividad']], 'api',
               referencias=('Usuario', 'User (Django)', 'Actividad'),
               nota='IntentosMovil no tiene FK: su clave es un hash de IP o cuenta (cuotas de 120 por IP y 8 por cuenta).\n'
                    'La app nunca se conecta a MySQL: todo pasa por /api/v1/ con las mismas reglas de permisos que la web.'),
    ]
