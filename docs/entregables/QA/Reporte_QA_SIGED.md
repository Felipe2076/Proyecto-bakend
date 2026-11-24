# Reporte de QA exhaustivo — SIGED web

**Fecha:** 22-11-2026 · **Alcance:** `SIGED-colaboracion/web` (Django 6.1), API móvil, scripts de despliegue y cliente Android (solo lectura).
**Método:** tres auditorías independientes en paralelo, leyendo el código completo:
1. organizaciones comunitarias, usuarios y datos simulados;
2. vistas, rutas, plantillas, JavaScript y CSS;
3. API móvil, configuración, archivos, despliegue y Android.

**Línea base de pruebas:** 222 pruebas, 214 aprobadas. Las 8 que fallan leen `web/data/*.json`, que no existe en esta copia.

**Resultado general:**
- Todas las rutas `{% url %}` / `reverse()` existen (0 enlaces rotos).
- Todos los formularios POST llevan `{% csrf_token %}`.
- Los problemas reales son de otra clase: errores 500 reproducibles, fugas entre delegaciones, indicadores que no salen de datos reales, datos de relleno en producción, búsquedas que recorren tablas completas y deuda visual.

**Severidad:** Alta = error 500, pérdida o falsificación de datos, fuga de información. Media = funciona mal o confunde. Baja = detalle.
**Estado:** `Pendiente` → `Corregido (prueba)` o `No aplica (motivo)`. La columna Fase remite al plan de trabajo.

---

## 1. Hallazgos de severidad alta

| ID | Archivo:línea | Problema | Consecuencia | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-001 | requerimientos/views.py:299-322, templates/requerimientos/detalle.html:160-163 | "Días transcurridos" editable reescribe `fecha_ingreso = hoy - días`; sin tope en servidor | Cualquier funcionario rejuvenece tickets (falsea SLA e indicadores); `dias=800000` → OverflowError 500 | Eliminar el campo; la fecha de ingreso no se edita | 1 | Corregido |
| QA-002 | requerimientos/consultas.py:105-114; control_gestion/views_extra.py:344-349 | Vecino buscado por nombre exacto; `Vecino.save()` lanza ValidationError con "(" | 500 al crear ticket o compromiso para "Junta (Norte)"; homónimos fusionados; cada edición de un vecino simulado crea un duplicado | Validar nombre en el formulario, buscar por RUT o ID, transacción atómica | 1 | Corregido |
| QA-003 | control_gestion/views.py:164-217; indicadores.py:360-461 | Dashboard y panel SGR sin filtro de delegación | Administrador y jefatura ven tickets, vecinos y desempeño de las 6 delegaciones | Aplicar `ambito()` / `tickets_visibles` | 1 | Corregido |
| QA-004 | config/context_processors.py:10-41,69 | Notificaciones: todas las alertas y tickets críticos de todas las delegaciones, en cada página, también para anónimos | Fuga de nombres de vecinos (Ley 19.628) y consultas pesadas en `/login/` y portada | Salir si es anónimo; filtrar por delegación; contar con `.count()` | 1 | Corregido |
| QA-005 | cuentas/forms.py:95-109,148-167 | `UsuarioForm` no valida el `auth.User.username`; puede vincular un `auth.User` huérfano ajeno; guarda sin transacción | IntegrityError 500 con datos a medias; posible escalada de privilegios | Validar y rechazar reutilización; `atomic()` | 1 | Corregido |
| QA-006 | cuentas/views.py:683-687 | Pantalla Parámetros guarda `Medicion.periodo` (único) sin comprobar duplicado | IntegrityError 500 | Validar unicidad y fechas | 1 | Corregido |
| QA-007 | cuentas/management/commands/importar_json.py:200-214,345-358,526-528; cuentas/simulacion_bd.py:426-511 | Reescribe RUT, nombres y correos reales, reinicia contraseñas y desactiva el usuario `admin` sin ninguna protección | Destrucción irreversible de datos si alguien lo ejecuta en producción | Exigir DEBUG + bandera explícita | 1 | Corregido |
| QA-008 | cuentas/migrations/0004_codigo_un_uso.py:9-13 | En MySQL lee `sql/migraciones/V019__codigo_un_uso.sql`, que no existe y está excluido de Docker | `migrate` en una base MySQL nueva falla | DDL inline equivalente | 1 | Corregido |
| QA-009 | static/js/siged-motion.js:44-59 | El loader de pantalla completa se activa en todo submit/clic sin mirar `defaultPrevented` ni teclas modificadoras | Kanban, Tubo, agenda y búsqueda en vivo quedan tapados 8 s | Respetar `defaultPrevented`, botón y modificadores | 1 | Corregido |
| QA-010 | control_gestion/views.py:149-150,168-179; requerimientos/models.py:157-197 | No existe fecha de resolución; los tickets resueltos siguen envejeciendo | Tickets resueltos aparecen como "críticos"; el tiempo promedio crece cada día | `fecha_resolucion` y excluir resueltos | 2 | Corregido |
| QA-011 | control_gestion/views.py:225-284; requerimientos/models.py:139-144 | % cumplimiento, satisfacción, tiempo y casos/mes de las áreas son columnas escritas a mano | KPIs congelados presentados como vivos | Calcular desde `Requerimiento` y encuestas | 2 | Corregido |
| QA-012 | control_gestion/models.py:54; indicadores.py:152; panel_personal.py:127; api_movil.py:98 | `ItemFuncionario.avance_actual` nunca se actualiza con las actividades | El semáforo SGR no refleja el trabajo registrado | Calcular desde actividades del periodo | 2 | No aplica: el avance ya sube al aprobar cada actividad (revision.py:36); el auditor no lo vio |
| QA-013 | requerimientos/consultas.py:11-21,71-78 | `FUNCIONARIOS_REFERENCIA`: personas inventadas en la lista de asignación | Tickets asignados a personas inexistentes | Usar solo funcionarios reales | 2 | Corregido |
| QA-014 | control_gestion/forms.py:178-183 | RUT de la directiva aceptado con cualquier formato y dígito verificador | RUT inválidos guardados | `rut_canonico` y `motivo_rut_invalido` | 3 | Corregido |
| QA-015 | control_gestion/models.py:284; management/commands/importar_organizaciones.py:14; cuentas/mantenedores.py:96-101 | Las organizaciones importadas no tienen delegación y el alcance las excluye | Los administradores de delegación no ven ni editan las JJVV importadas | Asignar solo si el territorio coincide sin ambigüedad; bandeja "Sin delegación" | 3 | Corregido |
| QA-016 | control_gestion/consultas.py:202-204 | `Meta.get_or_create(nombre=texto libre)` | Cualquier funcionario crea metas SGR con errores de tipeo | Elegir solo ítems del funcionario | 4 | Corregido |
| QA-017 | core/busqueda.py:17-28,49-68; mejoras-listados.js:56-60 | La búsqueda recorre la tabla completa en Python en cada tecla | Escaneo de miles de filas por pulsación | Filtrar en SQL | 4 | Corregido |
| QA-018 | control_gestion/views.py:61-128; indicadores.py:414-418; kanban.py:49-51 | `obtener_parametros()`, ausencias y bonificación consultados por cada ticket o persona | 2N-4N consultas en dashboard, kanban y semáforo | Leer una vez y agregar | 4 | Corregido |
| QA-019 | templates/control_gestion/dashboard.html:138, semaforo_sgr.html:120, tubo_trabajo.html:135 | Decimales en `style="width:x%"` salen con coma (`es-cl`) | Barras de progreso vacías o mal dibujadas | `unlocalize` | 2 | Corregido |
| QA-020 | templates/control_gestion/_panel_calculos.html:61 | Muestra el % esperado global junto a colores calculados con el % esperado de cada persona | Columna contradictoria | `fila.pct_esperado` | 2 | Corregido |
| QA-021 | requerimientos/views.py:127-171,180 | Llamada HTTP de clima bloqueante (3,5 s) en cada carga de inicio, sin caché; respaldo con clima falso | Inicio lento y dato inventado | Caché de 15 min; "no disponible" | 2 | Corregido |
| QA-022 | publico/views.py:12-18 | `/` redirige anónimos a `/login/`; la portada pública nunca se muestra | Sitio público inaccesible | Mostrar `portada.html` a anónimos | 1 | No aplica: decisión del proyecto, el sistema parte en el login (prueba cuentas/tests.py:131) |
| QA-023 | templates/base.html:100-102 | `lottie.min.js` y `lordicon.js` (≈640 KB) cargados de forma bloqueante en todas las páginas | Primera carga lenta | `defer` y carga solo donde se usan | 4 | Corregido |
## 2. Organizaciones comunitarias

| ID | Archivo:línea | Sev. | Problema | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-030 | control_gestion/models.py:263-296 | Media | No hay teléfono, correo, tipo (JJVV/funcional) ni vigencia de directiva | Campos nuevos nullable | 3 | Corregido |
| QA-031 | control_gestion/models.py:283 | Media | `territorio` es texto libre | Validar contra el catálogo y conservar el valor anterior | 3 | Corregido |
| QA-032 | control_gestion/models.py:284-289 | Media | Etiquetas sin tilde ("Delegacion", "Fecha constitucion") | `verbose_name` / labels | 3 | Corregido |
| QA-033 | control_gestion/models.py:292-295 | Media | Sin control de duplicados por nombre y delegación | Aviso de duplicado en `clean()` | 3 | Corregido |
| QA-034 | control_gestion/models.py:164 | Media | `EventoAgenda.organizacion` SET_NULL: borrar una organización desvincula la agenda | Desactivar en vez de borrar | 3 | Corregido |
| QA-035 | control_gestion/forms.py:183; core/validaciones.py:38-45 | Media | Un RUT sin guion se guarda distinto; el control de directiva duplicada falla | Normalizar con `rut_canonico` | 3 | Corregido |
| QA-036 | control_gestion/forms.py:193-196 | Media | Sin labels, ayudas, placeholders ni máscara de RUT | Agregar y cargar `validaciones.js` | 3 | Corregido |
| QA-037 | control_gestion/forms.py:168-192 | Media | Fechas futuras, inscripción anterior a la constitución, socios en 0 y nombres con dígitos aceptados | Validaciones en `clean()` | 3 | Corregido |
| QA-038 | control_gestion/forms.py:164-165; static/js/territorios-organizacion.js:6-21 | Media | El territorio anterior se pierde al cambiar de delegación o al recargar el catálogo | Conservar siempre la opción anterior | 3 | Corregido |
| QA-039 | control_gestion/forms.py:138; cuentas/mantenedores.py:145 | Baja | `configurar_territorios()` se ejecuta dos veces | Una sola vez | 3 | Corregido |
| QA-040 | control_gestion/forms.py:105 | Media | Agenda: `<select>` con unas 2.709 organizaciones; editar un evento con organización inactiva falla | Autocompletar e incluir la instancia actual | 3 | Corregido |
| QA-041 | control_gestion/forms.py:111-118 | Baja | No se valida que la organización pertenezca a la delegación del evento | Validar | 3 | Corregido |
| QA-042 | cuentas/mantenedores.py:139-144 | Media | Administrador sin delegación: lista obligatoria vacía, imposible guardar | Mensaje claro y bloqueo | 3 | Corregido |
| QA-043 | cuentas/mantenedores.py:275 | Media | Lista sin filtros ni columna "Activa" | Filtros por delegación, territorio, tipo, verificada y activa | 3 | Corregido |
| QA-044 | cuentas/mantenedores.py:195,218 | Media | Tras guardar se pierden la búsqueda y la página | Conservar la consulta | 3 | Corregido |
| QA-045 | cuentas/mantenedores.py:232-251; templates/mantenedores/eliminar.html:22 | Media | Borrado físico y texto engañoso ("no lo eliminará") | Desactivar y avisar los eventos vinculados | 3 | Corregido |
| QA-046 | templates/mantenedores/formulario.html:28-39 | Media | 18 campos en una sola columna sin secciones; checkboxes mal envueltos | Plantilla propia con secciones | 3 | Corregido |
| QA-047 | templates/mantenedores/formulario.html:33; cuentas/forms.py:12-29 | Media | Sin `is-invalid` en errores del servidor | Agregar al renderizar | 4 | Corregido |
| QA-048 | templates/mantenedores/formulario.html:26; base.html:108-118 | Media | El navegador bloquea el envío sin explicar por qué | Mensaje genérico de validación | 4 | Corregido |
| QA-049 | templates/mantenedores/_ficha_organizacion.html:10 | Baja | RUT sin formato y visible para roles de solo lectura | Formatear y enmascarar | 3 | Corregido |
| QA-050 | management/commands/importar_organizaciones.py:13-25 | Media | Códigos que pueden colisionar; sin errores por fila; no actualiza | Validación por fila, `--actualizar`, códigos únicos | 3 | Corregido |
| QA-051 | cuentas/urls_mantenedores.py:7; control_gestion/territorios.py:25 | Baja | Vista de territorios sin `login_required` explícito; mensaje 403 poco claro | Decorador y mensaje | 3 | Corregido |
## 3. Usuarios y cuentas

| ID | Archivo:línea | Sev. | Problema | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-060 | cuentas/forms.py:86-87,136-139 | Media | Username, nombre y delegación se muestran editables pero se sobrescriben con la ficha | Solo lectura | 1 | Corregido |
| QA-061 | cuentas/forms.py:12-29 | Media | `required` se fija al construir, así que los campos opcionales quedan obligatorios en el navegador (agenda, periodo) | Calcular al renderizar | 4 | Corregido |
| QA-062 | cuentas/views.py:452-458 | Media | Nombre completo partido por palabras; si el nombre es "Registro" se reemplaza por una identidad ficticia | Respetar el nombre ingresado; sin identidad ficticia | 4 | Pendiente: separar nombres y apellidos en el alta de usuarios |
| QA-063 | cuentas/views.py:405-408,467-475 | Media | Elegir una ficha existente sobrescribe sus datos sin aviso | Precargar desde la ficha | 4 | Pendiente: precargar la ficha elegida en el alta de usuarios |
| QA-064 | cuentas/views.py:175-180,429-430 | Media | Con DEBUG (backend consola) no se pueden crear usuarios ni recuperar la clave | Permitir consola con DEBUG | 4 | Corregido |
| QA-065 | cuentas/views.py:361-379,330 | Media | Activar/desactivar busca por código (falla sin código), permite autodesactivarse y no pide confirmación | Usar pk, bloquear la propia cuenta, confirmar | 1 | Corregido |
| QA-066 | cuentas/views.py:699-711 | Media | La invitación vence en 10 minutos | 72 horas | 4 | No aplica: política documentada de 10 minutos; se pide un código nuevo en Recuperar |
| QA-067 | cuentas/views.py:497-500 | Baja | El correo se envía dentro de la transacción | `on_commit` | 4 | No aplica: el correo va dentro de la transacción a propósito (si falla, no se crea el usuario) |
| QA-068 | cuentas/views.py:525-529,519 | Baja | Se ofrecen fichas que ya tienen cuenta y roles inexistentes | Filtrar | 4 | Corregido |
| QA-069 | cuentas/views.py:151-154; auth.py:92 | Baja | Logout por GET; textos de "perfil de demostración" | POST y textos reales | 1 | Corregido |
| QA-070 | cuentas/mantenedores.py:47-55 | Baja | Un usuario puede eliminar su propia cuenta | Bloquear | 1 | Corregido |
| QA-071 | templates/cuentas/usuarios.html:63-79 | Media | Errores de delegación y ficha invisibles; `validaciones.js` no se carga | Mostrar errores y cargar el script | 4 | Corregido |
| QA-072 | templates/cuentas/usuarios.html:114-119 | Baja | Activar/desactivar sin texto claro ni confirmación | Botón explícito | 1 | Corregido |
| QA-073 | templates/cuentas/login.html:42 | Baja | `minlength=4` contra una política de 8 | Alinear | 4 | Corregido |
| QA-074 | cuentas/forms.py:170-206 | Baja | Las dos vías de recuperación aplican políticas de clave distintas | `validate_password` en ambas | 4 | Corregido |
| QA-075 | cuentas/models.py:160-178,219-229 | Media | `save()` lanza ValidationError, lo que da 500 en llamadas fuera de formularios | Capturar en los puntos de entrada | 4 | Parcial: los formularios validan antes; queda el save() como última barrera |
| QA-076 | cuentas/perfiles.py:43-48 | Media | El administrador de delegación tiene todos los permisos no globales | Revisar la matriz | 4 | Pendiente: revisar la matriz de permisos del administrador con el cliente |
| QA-077 | config/context_processors.py:60-67,76 | Baja | Un mantenedor sin entrada en `presentacion` da KeyError, 500 en todas las páginas | `.get()` con valor por defecto | 1 | Corregido |
| QA-078 | (todo el proyecto) | Alta | No existe foto de perfil (ni `ImageField` ni avatar) | Fase 5 | 5 | Corregido |
## 4. Datos simulados o fijos en código

| ID | Archivo:línea | Sev. | Problema | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-080 | cuentas/store.py | Baja | Capa JSON de la maqueta; ninguna vista la usa | Retirar de producción | 2 | Pendiente: store.py no se usa; se puede borrar en la próxima limpieza |
| QA-081 | cuentas/migrations/0003_rut_obligatorio.py:11,95 | Media | Anonimiza bases heredadas y lee un JSON inexistente | Proteger la anonimización | 1 | Corregido |
| QA-082 | cuentas/management/commands/generar_simulacion.py | Media | Roto y con texto poco profesional en el SQL generado | Proteger con DEBUG + bandera | 1 | Corregido |
| QA-083 | requerimientos/management/commands/sembrar_demo.py | Media | Inyecta tickets DEMO- en paneles de personas reales | Proteger con DEBUG + bandera | 1 | Corregido |
| QA-084 | cuentas/simulacion.py:30-39; views.py:38,84,368; grupos.py:12,43 | Media | `USR-025` fijo en el código como cuenta protegida | Campo `protegido` | 2 | Corregido |
| QA-085 | requerimientos/models.py:40; cuentas/models.py:101 | Media | `es_simulacion` solo marca en pantalla; los KPIs y exportaciones lo incluyen | Excluir de indicadores | 2 | Corregido |
| QA-086 | control_gestion/indicadores.py:87; views.py:500-503; cuentas/views.py:666-672 | Media | "Delegación Rural / Centro" fijas; la pantalla Parámetros llega a crear una delegación | Elección explícita | 2 | Parcial: se quitó la creación de delegación y el «Rural» por defecto; la delegación piloto queda como dato heredado |
| QA-087 | templates/control_gestion/semaforo_sgr.html:19,107; dashboard.html:29,42 | Media | "90 días", "meta 80 %", "6 días" escritos en la plantilla | Leer de parámetros | 2 | Corregido |
| QA-088 | cuentas/vocabulario.py:3-10; publico/views.py:46-51 | Baja | Las delegaciones públicas son una lista fija | Leer de la BD | 2 | Corregido |
| QA-089 | publico/contenido.py:189-204 | Baja | 6 noticias fechadas a mano | Sin fechas falsas | 2 | No aplica: son noticias reales de laserena.cl con su fecha de publicación |
| QA-090 | control_gestion/consultas.py:180; requerimientos/consultas.py:36,44,147 | Baja | Textos de relleno guardados como datos ("no-registra@serena.cl", "Por Asignar…") | Dejar vacío y mostrar "—" | 2 | Corregido |
| QA-091 | templates/control_gestion/dashboard.html:45; _analitica.html | Media | Gráfico SVG decorativo con aspecto de dato real | Retirar | 2 | Corregido |
| QA-092 | templates/base.html:91; templates/_cu.html | Baja | Créditos del curso y chips CU-E en la interfaz de producción | Retirar | 2 | Corregido |
| QA-093 | templates/requerimientos/detalle.html:164; detalle_funcionario.html:129 | Media | "Guardar en JSON", "upload simulado" | Textos reales | 1 | Corregido |
## 5. Vistas, permisos e indicadores

| ID | Archivo:línea | Sev. | Problema | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-100 | control_gestion/views_extra.py:206-212 vs views.py:444-448 | Media | Desde Actividades se registran actividades a nombre de colegas | Misma regla: propio o administrador | 1 | Corregido |
| QA-101 | control_gestion/movimientos.py:189; views_extra.py:79 | Media | Mover eventos de agenda sin `change_eventoagenda` | Exigir el permiso | 1 | Corregido |
| QA-102 | control_gestion/kanban.py:44,72; _sidebar.html:23 | Media | El menú pide `control_gestion` y la vista `requerimientos` | Un solo permiso | 1 | Corregido |
| QA-103 | control_gestion/evidencias.py:62-84 | Media | Validador decidido por el texto "delegado" en el cargo | Permiso explícito | 1 | Corregido |
| QA-104 | requerimientos/inicio.html:41; _tabla_compromisos.html:15; consultas.py:62 | Baja | Botones que terminan en 403 | Ocultar con `perms` | 1 | Corregido |
| QA-105 | control_gestion/indicadores.py:274-300 vs panel_personal.py:19-46 | Media | Dos métodos de semáforo con etiquetas distintas | Unificar | 2 | No aplica: son dos reglas documentadas (HU-16 avance personal y Matriz SGR) |
| QA-106 | control_gestion/indicadores.py:245-254 vs trimestres.py:249 | Media | Desfase de un día en "días de avance" | Misma convención | 2 | Corregido |
| QA-107 | control_gestion/panel_personal.py:187-188 | Media | "Mis tickets" muestra resueltos como críticos y sin paginar | Excluir resueltos y paginar | 2 | Corregido |
| QA-108 | control_gestion/views.py:449-457 | Media | Formulario de actividad: al fallar pierde todo lo escrito | Re-renderizar con valores | 4 | Corregido |
| QA-109 | control_gestion/views_extra.py:350-359,399-402 | Media | Los cambios de compromiso por formulario no se auditan; borrar elimina el historial | Registrar `CambioCompromiso` | 4 | Corregido |
| QA-110 | control_gestion/views_extra.py:332-346; compromiso_form.html:37-53 | Media | Delegación independiente del funcionario | Derivarla | 4 | Corregido |
| QA-111 | control_gestion/forms.py:24-28,103-118 | Media | Ausencias y agenda: funcionario o responsable sin acotar | Acotar y validar | 4 | Corregido |
| QA-112 | requerimientos/views.py:316-321 | Media | Asignación por texto libre con coincidencia por prefijo | Selector acotado | 4 | Corregido |
| QA-113 | requerimientos/views.py:186-227 | Media | `lista_requerimientos_view` es código muerto sin control de permisos | Eliminar | 1 | Corregido |
| QA-114 | requerimientos/forms.py:102-123 | Media | "Registrada por" editable; vecino en un `<select>` gigante | Fijar en servidor | 4 | Corregido |
| QA-115 | (sin aplicación en el código) | Media | `max_atenciones_mismo_usuario` configurable pero nunca aplicado | Aplicar en `clean()` | 4 | Pendiente: falta definir con el cliente qué cuenta como «mismo usuario» |
| QA-116 | control_gestion/tubo_trabajo.html:76-110 | Media | Vista de tarjetas paginada de 10 en 10 repartidas en 4 columnas | Paginar por columna | 4 | Pendiente: paginación por columna en la vista de tarjetas |
| QA-117 | config/middleware.py:40-48,59-62 | Media | Escribe la sesión en cada request; el `next` no va codificado | Guardar solo si cambia; `redirect_to_login` | 4 | Corregido |
| QA-118 | control_gestion/reportes.py:226 | Media | 403 en texto plano; no hay plantillas 403/404/500 | Plantillas propias | 4 | Corregido |
| QA-119 | control_gestion/evidencias.py:38-41 | Baja | Fotos JPEG tipo MPO (celulares) rechazadas | Aceptar MPO | 4 | Corregido |
| QA-120 | config/urls.py:13,16 | Baja | Nombre `inicio` duplicado | Quitar la ruta sombreada | 1 | Corregido |
## 6. Interfaz, JavaScript y CSS

| ID | Archivo:línea | Sev. | Problema | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-130 | templates/base.html:33 | Media | `data-bs-toggle="offcanvas"` sin destino: TypeError en cada clic del menú móvil | Corregir el toggle | 1 | Corregido |
| QA-131 | templates/base.html:14-16; static/css/style.css + app.css | Media | Dos temas superpuestos (unos 124 `!important`) | Un solo tema | 4 | Pendiente: unificar style.css y app.css requiere revisión visual pantalla por pantalla |
| QA-132 | templates/base.html:11,103 | Media | Lenis desde CDN sin SRI | Retirar o servir local | 4 | Corregido |
| QA-133 | static/js/modulos/validacion.js, validaciones.js, base.html:108-126 | Media | Tres implementaciones de validación | Una sola | 4 | Corregido |
| QA-134 | templates/_sidebar.html:80-91 | Media | "Usuarios" aparece dos veces | Dejar una | 4 | Corregido |
| QA-135 | (varias plantillas) | Baja | Clases CSS no definidas (`accent-bar`, `card-calculo`, `shadow-xs`…) y archivos muertos | Definir o retirar | 4 | Corregido |
| QA-136 | areas.html:47-49 | Baja | "Ver descripción" sin acción en pantallas táctiles | Collapse | 4 | Corregido |
| QA-137 | notificaciones.html:42 | Baja | `enlace` sin validar el esquema | Validar | 4 | Corregido |
## 7. API móvil, sincronización y despliegue

| ID | Archivo:línea | Sev. | Problema | Corrección | Fase | Estado |
|---|---|---|---|---|---|---|
| QA-150 | control_gestion/api_movil.py:84 | Media | Token de 8 h sin renovación, incompatible con uso sin conexión | Token de dispositivo renovable | 6 | Corregido |
| QA-151 | control_gestion/models.py:312-316 | Media | `SesionMovil` sin dispositivo, creación ni último uso | Campos nuevos | 6 | Corregido |
| QA-152 | control_gestion/api_movil.py:57 | Media | Excepciones no previstas devuelven HTML 500 | Todo en JSON | 6 | Corregido |
| QA-153 | (todos los modelos) | Alta | No hay `actualizado`, versión, UUID ni bajas lógicas, así que no se puede sincronizar | Campos de control | 6 | Corregido |
| QA-154 | (API) | Alta | No hay endpoints de usuarios ni organizaciones | Fase 6 | 6 | Corregido |
| QA-155 | control_gestion/api_movil.py:69-79 | Baja | Límites de login fijos en el código | Documentado | 6 | Corregido |
| QA-156 | despliegue/desplegar-cambios-docker.sh:94-107 | Alta | El script rechaza `DROP DEFAULT` y finge (`--fake`) las RunPython | Migraciones nullable o `db_default`; rellenos por comando | 5-6 | Corregido |
| QA-157 | despliegue/desplegar-cambios-docker.sh:60-64 | Media | El respaldo no incluye el volumen de evidencias y fotos | Agregar respaldo del volumen | 7 | Corregido |
| QA-158 | web/.env.example | Baja | Faltan variables usadas por el código | Completar | 7 | Corregido |
| QA-159 | (despliegue) | Media | phpMyAdmin no existe | Servicio cerrado en 127.0.0.1 | 7 | Corregido |
---

## Registro de correcciones (22-11-2026)

Pruebas automáticas: **269 pruebas, todas aprobadas** (10 omitidas porque requieren `web/data/*.json` de la simulación,
que no viene en esta copia). Archivos de prueba nuevos: `control_gestion/tests_qa_fase1.py`,
`tests_qa_organizaciones.py`, `tests_api_sincronizacion.py`, `cuentas/tests_fotos.py`.

Revisión en navegador (servidor local con datos ficticios): 30 pantallas responden sin error 500; alta de organización
con errores provocados (teléfono, fecha futura, RUT con dígito incorrecto) y luego exitosa; buscador de organizaciones
en la agenda; vista a 360 px corregida (barra superior compacta).

| Fase | Qué se corrigió | Pruebas |
|---|---|---|
| 1 | QA-001 a 009, 060, 065, 069, 070, 072, 077, 081-083, 093, 100-104, 113, 120, 130 | tests_qa_fase1 |
| 2 | QA-010, 011, 013, 019-021, 084, 085, 087, 088, 090-092, 106, 107 | tests_qa_fase1, suite completa |
| 3 | QA-014, 015, 030-046, 049-051 | tests_qa_organizaciones |
| 4 | QA-016-018, 023, 047, 048, 061, 064, 068, 071, 073, 074, 108-112, 114, 117-119, 132-137 | suite completa |
| 5 | QA-078 (foto de perfil) | tests_fotos |
| 6 | QA-150-156 (API móvil y sincronización) | tests_api_sincronizacion |
| 7 | QA-157-159 (respaldo de fotos, .env.example, phpMyAdmin cerrado) | revisión de sintaxis del script |

Migraciones nuevas (`cuentas` 0008, `control_gestion` 0015-0016, `requerimientos` 0003): su SQL para MySQL 8.4 es solo
`ADD COLUMN … NULL`, `CREATE TABLE` y `CREATE INDEX`; pasa el filtro de `desplegar-cambios-docker.sh`.
