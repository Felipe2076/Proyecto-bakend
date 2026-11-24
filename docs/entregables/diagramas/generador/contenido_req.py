"""Catálogo de requerimientos SIGED-SGR (Unidades 1, 2 y 3) para el diagrama SysML.

Estado entre corchetes: [I] implementado y probado, [P] parcial, [X] propuesto (no implementado).
nuevo=True marca lo que agregó el cliente en la Unidad 3 o lo codificado después del informe de la Etapa 2.
"""

# (id, nombre, texto épica, nuevo, [HU...]) ; HU = (id, nombre, texto, [(id, texto, estado)], nuevo)
EPICAS = [
    ('EP-01', 'Registro y gestión de actividades', 'El sistema debe registrar las actividades, servicios y compromisos de cada funcionario.', False, [
        ('HU-01', 'Registro de actividades', 'Como funcionario, quiero registrar mis actividades diarias para evidenciar mi gestión.', [
            ('HU-01.1', 'Debe registrar fecha, contacto, servicio, ítem/meta y tipo de registro.', 'I'),
            ('HU-01.2', 'Debe generar código ACT y código verificador al guardar.', 'I')], False),
        ('HU-02', 'Registro de compromisos ciudadanos', 'Como funcionario, quiero registrar compromisos con vecinos para darles seguimiento.', [
            ('HU-02.1', 'Debe registrar vecino, responsable, delegación, origen, territorio y fecha comprometida.', 'I')], False),
        ('HU-03', 'Registro de servicios entregados', 'Como funcionario, quiero registrar el servicio entregado para medir mi aporte.', [
            ('HU-03.1', 'Debe asociar cada actividad a un ítem de la matriz SGR.', 'I')], False),
        ('HU-04', 'Funciones por cargo', 'Como administrador, quiero asociar funciones e ítems al cargo según el descriptor de funciones.', [
            ('HU-04.1', 'Debe mantener cargos (Delegado, Gestor social, Apoyo administrativo, Organizaciones comunitarias, etc.).', 'I')], False),
    ]),
    ('EP-02', 'Medición y desempeño', 'El sistema debe definir metas por período y calcular el cumplimiento sin doble conteo.', False, [
        ('HU-05', 'Definición de metas', 'Como administrador, quiero definir metas por funcionario y trimestre.', [
            ('HU-05.1', 'Debe definir ítem, ponderador (%) y meta del trimestre por funcionario.', 'I')], False),
        ('HU-06', 'Seguimiento de avance', 'Como funcionario, quiero ver mi avance por ítem.', [
            ('HU-06.1', 'Debe mostrar avance actual / meta por ítem.', 'I')], False),
        ('HU-07', 'Cálculo automático de cumplimiento', 'Como jefatura, quiero que el cumplimiento se calcule solo.', [
            ('HU-07.1', 'Debe calcular cumplimiento ponderado con tope de 120 % por ítem.', 'I')], False),
        ('HU-08', 'Desempeño organizacional', 'Como jefatura, quiero ver el desempeño de la delegación.', [
            ('HU-08.1', 'Debe resumir el desempeño por delegación.', 'I')], False),
        ('HU-65', 'Configuración trimestral automática', 'Como superusuario, quiero crear el trimestre sin calcular a mano nombre ni días.', [
            ('HU-65.1', 'Debe proponer el nombre del trimestre y calcular los días desde las fechas.', 'I'),
            ('HU-65.2', 'Debe mostrar siempre arriba el trimestre vigente y su % de días transcurridos.', 'I')], True),
    ]),
    ('EP-03', 'Evidencias y verificación', 'El sistema debe guardar evidencias y registrar su revisión por un verificador autorizado.', False, [
        ('HU-09', 'Registro de evidencia', 'Como funcionario, quiero adjuntar la evidencia de mi actividad.', [
            ('HU-09.1', 'Debe validar tipo y tamaño del archivo (máx. 10 MB) y guardarlo.', 'I')], False),
        ('HU-10', 'Códigos verificadores', 'Como jefatura, quiero un código verificador por actividad.', [
            ('HU-10.1', 'Debe generar un código verificador único.', 'I')], False),
        ('HU-11', 'Validación de actividades', 'Como delegado, quiero aprobar, rechazar o pedir corrección.', [
            ('HU-11.1', 'Debe registrar autor, comentario, fecha y versión de cada revisión.', 'I'),
            ('HU-11.2', 'No debe permitir autoaprobación; una aprobación suma una sola vez.', 'I')], False),
    ]),
    ('EP-04', 'Agenda colectiva y compromisos', 'El sistema debe compartir agenda y dar continuidad a los compromisos.', False, [
        ('HU-12', 'Agenda compartida', 'Como funcionario, quiero ver eventos, compromisos y actividades por fecha.', [
            ('HU-12.1', 'Debe mostrar vista calendario y lista por mes.', 'I')], False),
        ('HU-13', 'Actualización de estados', 'Como funcionario, quiero cambiar el estado de un compromiso.', [
            ('HU-13.1', 'Estados: Ingresado, Pendiente, En proceso, Realizado; vencido se calcula por fecha.', 'I')], False),
        ('HU-14', 'Seguimiento de compromisos', 'Como jefatura, quiero ver vencidos y pendientes.', [
            ('HU-14.1', 'Debe destacar compromisos vencidos no realizados.', 'I')], False),
        ('HU-15', 'Continuidad operativa', 'Como jefatura, quiero reasignar por ausencia con historial.', [
            ('HU-15.1', 'Debe registrar reasignación con motivo y aprobación.', 'X')], False),
    ]),
    ('EP-05', 'Monitoreo y control de gestión', 'El sistema debe comparar avance esperado y real con semáforo.', False, [
        ('HU-16', 'Semáforo de cumplimiento', 'Como jefatura, quiero un semáforo verde/amarillo/rojo.', [
            ('HU-16.1', 'Debe comparar cumplimiento con el % esperado según días del trimestre.', 'I')], False),
        ('HU-17', 'Avance esperado vs real', 'Como jefatura, quiero ver la brecha en días.', [
            ('HU-17.1', 'Debe convertir la brecha a días equivalentes.', 'I')], False),
        ('HU-18', 'Resumen ejecutivo', 'Como jefatura, quiero un resumen de la delegación.', [
            ('HU-18.1', 'Debe resumir actividades, compromisos y desempeño.', 'I')], False),
        ('HU-19', 'Control de actividad de usuarios', 'Como jefatura, quiero ver quién registra.', [
            ('HU-19.1', 'Debe mostrar fecha de último ingreso por funcionario.', 'P')], False),
        ('HU-31', 'Alertas operativas', 'Como jefatura, quiero alertas según umbrales.', [
            ('HU-31.1', 'Debe generar avisos internos (Notificación).', 'P')], False),
    ]),
    ('EP-06', 'Reportabilidad y toma de decisiones', 'El sistema debe emitir informes y cerrar períodos conservando históricos.', False, [
        ('HU-20', 'Generación de informes', 'Como jefatura, quiero informes con filtros.', [
            ('HU-20.1', 'Debe exportar a Excel el filtro aplicado en todas sus páginas.', 'I')], False),
        ('HU-21', 'Funcionarios rezagados', 'Como jefatura, quiero identificar rezagos.', [
            ('HU-21.1', 'Debe ordenar funcionarios por semáforo.', 'I')], False),
        ('HU-22', 'Brechas de productividad', 'Como coordinación, quiero ver brechas.', [
            ('HU-22.1', 'Debe mostrar ítems con bajo puntaje.', 'P')], False),
        ('HU-42', 'Cierre mensual', 'Como jefatura, quiero cerrar el mes con observaciones.', [
            ('HU-42.1', 'Debe congelar resultados del período cerrado.', 'X')], False),
        ('HU-67', 'Excel propio del funcionario', 'Como funcionario, quiero exportar solo mi trabajo.', [
            ('HU-67.1', 'Debe exportar solo registros del alcance autorizado, sin datos internos.', 'I')], True),
    ]),
    ('EP-07', 'Plataforma colaborativa', 'El sistema debe permitir trabajo en línea entre funcionarios y delegaciones.', False, [
        ('HU-23', 'Trabajo colaborativo en línea', 'Como funcionario, quiero trabajar en la misma información.', [
            ('HU-23.1', 'Debe evitar sobrescribir cambios concurrentes (aviso "recargue la página").', 'I')], False),
        ('HU-24', 'Comunicación entre delegaciones', 'Como coordinación, quiero avisos entre delegaciones.', [
            ('HU-24.1', 'Debe publicar avisos internos.', 'P')], False),
        ('HU-25', 'Adaptación continua', 'Como administrador, quiero ajustar catálogos sin programar.', [
            ('HU-25.1', 'Debe administrar catálogos desde mantenedores propios (sin Django Admin).', 'I')], False),
        ('HU-66', 'Uso desde aplicación móvil', 'Como funcionario, quiero registrar desde el teléfono.', [
            ('HU-66.1', 'Debe exponer API v1 (sesión, actividades, evidencia, compromisos, Excel); la app nunca accede a MySQL.', 'P')], True),
    ]),
    ('EP-08', 'Administración, seguridad y trazabilidad', 'El sistema debe administrar delegaciones, usuarios, roles y catálogos con auditoría.', False, [
        ('HU-26', 'Delegaciones, usuarios y roles', 'Como superusuario, quiero administrar cuentas y roles.', [
            ('HU-26.1', 'Debe crear usuarios con rol, cargo y delegación.', 'I')], False),
        ('HU-27', 'Administración de catálogos', 'Como superusuario, quiero mantener catálogos globales.', [
            ('HU-27.1', 'Solo el superusuario crea/modifica delegaciones, roles, metas, cargos y tipos.', 'I')], False),
        ('HU-28', 'Administración de períodos', 'Como superusuario, quiero definir trimestres.', [
            ('HU-28.1', 'Debe impedir períodos solapados.', 'I')], False),
        ('HU-29', 'Búsqueda y filtros', 'Como usuario, quiero buscar por coincidencia parcial.', [
            ('HU-29.1', 'Debe buscar en varios campos sin distinguir mayúsculas y paginar 10/20/50/100.', 'I')], False),
        ('HU-30', 'Auditoría de cambios', 'Como auditor, quiero consultar cambios.', [
            ('HU-30.1', 'Debe registrar autor y estados en revisiones y cambios de compromiso.', 'P')], False),
    ]),
    ('EP-09', 'Captura ciudadana multicanal', 'El sistema debe registrar requerimientos y atenciones ciudadanas por cualquier canal.', False, [
        ('HU-32', 'Registro presencial', 'Como operador, quiero registrar un requerimiento en ventanilla.', [
            ('HU-32.1', 'Debe crear ticket TK con vecino, delegación, canal, tipo y área.', 'I')], False),
        ('HU-33', 'Bandeja unificada', 'Como jefatura, quiero ver todos los canales juntos.', [
            ('HU-33.1', 'Debe listar tickets de todos los canales con filtros.', 'I')], False),
        ('HU-34', 'Ingreso por WhatsApp', 'Como operador, quiero registrar lo recibido por WhatsApp.', [
            ('HU-34.1', 'Captura manual del canal; la integración automática es propuesta.', 'P')], False),
        ('HU-35', 'Ingreso por correo', 'Como operador, quiero registrar lo recibido por correo.', [
            ('HU-35.1', 'Debe exigir correo válido cuando el canal es correo.', 'I')], False),
        ('HU-36', 'Tipificación', 'Como operador, quiero clasificar el tipo de gestión.', [
            ('HU-36.1', 'Reclamo, solicitud, consulta, sugerencia o felicitación.', 'I')], False),
        ('HU-64', 'Registro de atención ciudadana', 'Como operador, quiero registrar una atención con tipo y subatención.', [
            ('HU-64.1', 'La subatención depende del tipo elegido; la delegación sale del contexto del usuario.', 'I')], True),
    ]),
    ('EP-10', 'Enrutamiento territorial y asignación', 'El sistema debe asociar cada ticket a delegación, área y responsable.', False, [
        ('HU-37', 'Área estratégica territorial', 'Como operador, quiero clasificar por área de soporte.', [
            ('HU-37.1', 'Debe asociar el ticket a un Área de soporte.', 'I')], False),
        ('HU-38', 'Asignación a funcionario o cuadrilla', 'Como jefatura, quiero asignar un responsable.', [
            ('HU-38.1', 'Debe permitir funcionario o texto de cuadrilla.', 'I')], False),
        ('HU-39', 'Asociación a delegación', 'Como operador, quiero asociar la delegación.', [
            ('HU-39.1', 'La delegación se toma del contexto autorizado.', 'I')], False),
    ]),
    ('EP-11', 'Semáforo de tickets y cuellos de botella', 'El sistema debe mostrar antigüedad de tickets y permitir intervenir.', False, [
        ('HU-40', 'Semáforo diario de tickets', 'Como jefatura, quiero ver la antigüedad de tickets.', [
            ('HU-40.1', 'Verde hasta 3 días, amarillo hasta 5, rojo sobre 5 (parametrizable).', 'I')], False),
        ('HU-41', 'Cuellos de botella', 'Como jefatura, quiero detectar tickets estancados.', [
            ('HU-41.1', 'Estado "Cuello Botella Central" y dashboard.', 'I')], False),
        ('HU-43', 'Tablero Kanban', 'Como funcionario, quiero mover tickets entre columnas.', [
            ('HU-43.1', 'Debe mover tickets con control de permisos.', 'I')], False),
        ('HU-44', 'Intervención jerárquica', 'Como jefatura, quiero intervenir tickets en rojo.', [
            ('HU-44.1', 'Debe registrar instrucción y plazo de desbloqueo.', 'X')], False),
    ]),
    ('EP-12', 'Notificaciones y satisfacción', 'El sistema debe informar al vecino y medir su satisfacción.', False, [
        ('HU-45', 'Notificación al vecino', 'Como operador, quiero avisar el estado al vecino.', [
            ('HU-45.1', 'Envío automático por mensajería: propuesto.', 'X')], False),
        ('HU-46', 'Encuesta express', 'Como vecino, quiero evaluar la atención de 1 a 5.', [
            ('HU-46.1', 'Enlace firmado (30 días) para responder sin cuenta, solo con ticket resuelto.', 'I')], False),
        ('HU-47', 'Dashboard de 6 delegaciones', 'Como coordinación, quiero KPI de las seis delegaciones.', [
            ('HU-47.1', 'Debe mostrar tickets, semáforos y satisfacción por delegación.', 'I')], False),
        ('HU-48', 'Parámetros del semáforo', 'Como superusuario, quiero configurar umbrales.', [
            ('HU-48.1', 'Debe editar SLA verde/amarillo y meta del tubo.', 'I')], False),
    ]),
    ('EP-13', 'Organizaciones comunitarias', 'El sistema debe mantener el catálogo de organizaciones (JJVV y funcionales) por delegación y territorio.', True, [
        ('HU-49', 'Catálogo de organizaciones', 'Como encargado OOCC, quiero cargar la base de JJVV y organizaciones.', [
            ('HU-49.1', 'Debe importar sin duplicar (clave de origen) y generar código ORG.', 'I'),
            ('HU-49.2', 'Debe buscar por nombre, territorio, registro jurídico o directiva.', 'I')], True),
        ('HU-50', 'Directiva y datos legales', 'Como encargado OOCC, quiero registrar la directiva.', [
            ('HU-50.1', 'Presidencia, tesorería y secretaría con nombre y RUT; PJ, socios y fechas.', 'I')], True),
        ('HU-51', 'Verificación y territorio', 'Como administrador de delegación, quiero verificar y asignar delegación.', [
            ('HU-51.1', 'El territorio se elige solo entre los de la delegación; "verificada" tras revisar.', 'I')], True),
        ('HU-52', 'Agenda de organizaciones', 'Como funcionario, quiero registrar actividades con organizaciones.', [
            ('HU-52.1', 'Debe registrar actividad, fecha, hora, lugar y organización, visible en la agenda.', 'I')], True),
    ]),
    ('EP-14', 'Reglas de puntaje de la matriz SGR', 'El sistema debe aplicar las reglas enviadas por la Coordinación de Delegaciones (oct. 2026).', True, [
        ('HU-53', 'Ingreso diario controlado', 'Como coordinación, quiero que se registre a diario.', [
            ('HU-53.1', 'Máximo 7 actividades por día y funcionario.', 'I'),
            ('HU-53.2', 'La semana cierra el martes siguiente; no se admiten fechas futuras.', 'I')], True),
        ('HU-54', 'Puntaje solo por resultado', 'Como coordinación, quiero puntuar la acción realizada.', [
            ('HU-54.1', 'Solo suma un "Resultado" aprobado; coordinación y gestión del delegado no suman.', 'I'),
            ('HU-54.2', 'Exigir nombre y teléfono del usuario para puntuar (hoy solo se exige el contacto).', 'P')], True),
        ('HU-55', 'Tope y felicitaciones', 'Como coordinación, quiero evitar puntaje inflado.', [
            ('HU-55.1', 'Tope 120 % por ítem; felicitación válida solo si la valida el delegado.', 'I')], True),
        ('HU-56', 'Ausencias y ajuste de metas', 'Como delegado, quiero ingresar licencias y vacaciones.', [
            ('HU-56.1', 'Licencia, vacaciones, administrativo, emergencia o compensatorio ajustan la meta.', 'I')], True),
    ]),
    ('EP-15', 'Tubo de compromisos en tarjetas', 'El sistema debe mostrar el tubo en formato Card / Canvas por estado.', True, [
        ('HU-57', 'Tablero de tarjetas', 'Como funcionario, quiero ver mis compromisos por columna.', [
            ('HU-57.1', 'Columnas Ingresado, Pendiente, En proceso, Realizado y KPI superiores.', 'I')], True),
        ('HU-58', 'Mover tarjetas', 'Como funcionario, quiero arrastrar o elegir el nuevo estado.', [
            ('HU-58.1', 'Debe guardar autor y estado anterior; control de concurrencia.', 'I')], True),
        ('HU-59', 'Vencido como distintivo', 'Como jefatura, quiero ver lo vencido sin perder el estado.', [
            ('HU-59.1', 'Vencido es un distintivo calculado, no una columna ni un estado.', 'I')], True),
        ('HU-60', 'Atenciones en el tubo', 'Como funcionario, quiero ver atenciones junto a compromisos.', [
            ('HU-60.1', 'Las atenciones se muestran y mueven en las mismas columnas.', 'I')], True),
    ]),
    ('EP-16', 'Acceso, perfiles y alcance por delegación', 'El sistema debe autenticar, autorizar por rol y encapsular cada delegación.', True, [
        ('HU-61', 'Ingreso y recuperación', 'Como usuario, quiero entrar con RUT y recuperar mi clave.', [
            ('HU-61.1', 'Código de un uso por correo con vigencia, intentos y respuesta genérica.', 'I')], True),
        ('HU-62', 'Perfiles y permisos', 'Como superusuario, quiero permisos por grupo de rol.', [
            ('HU-62.1', 'Roles: superusuario, administrador de delegación, jefatura, funcionario y ventanilla.', 'I')], True),
        ('HU-63', 'Encapsulamiento por delegación', 'Como superusuario, quiero que cada administrador vea solo su delegación.', [
            ('HU-63.1', 'Validación en servidor; otra delegación por URL se rechaza.', 'I'),
            ('HU-63.2', 'Solo el superusuario ve todas las delegaciones y lo global.', 'I')], True),
    ]),
]

RNF = [
    ('RNF-01', 'Autorización por rol y territorio', 'Toda operación verifica sesión, rol y delegación; el superusuario ve las seis.', False),
    ('RNF-02', 'Integridad y consistencia', 'Sin doble conteo; operaciones atómicas; período cerrado no se modifica.', False),
    ('RNF-03', 'Usabilidad móvil', 'Flujos críticos usables a 360 px sin desplazamiento horizontal.', False),
    ('RNF-04', 'Rendimiento', 'p95 <= 3 s con 30 usuarios simultáneos (meta por medir).', False),
    ('RNF-05', 'Privacidad de datos', 'Datos del vecino solo a perfiles autorizados y por HTTPS.', False),
    ('RNF-06', 'Configurabilidad', 'Catálogos y umbrales se cambian sin editar código.', False),
    ('RNF-07', 'Respaldo y recuperación', 'Respaldo antes de cada cambio y restauración probada (RPO 24 h, RTO 4 h).', False),
    ('RNF-08', 'Trazabilidad y concurrencia', 'Actor, fecha y cambio en operaciones críticas; sin sobrescritura silenciosa.', False),
    ('RNF-09', 'Identidad gráfica institucional', 'Template con normas gráficas de La Serena; delegación, usuario y rol visibles.', True),
    ('RNF-10', 'Seguridad OWASP', 'CSRF, sesiones seguras, contraseñas con hash, archivos validados, MySQL con mínimo privilegio.', True),
]
