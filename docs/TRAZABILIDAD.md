# Trazabilidad Primera Entrega — SIGED-SGR

Equipo **Los watones PC** (Felipe, Aixa, Gabriel) · Prof. Jorge Cortés  
Prototipo web en Django + JSON. **No hay MySQL ni APIs de negocio** en esta entrega.

Sirve para el informe: pantalla del mockup → caso de uso → entidades del DER.

## Módulos del menú

| Módulo | Casos de uso | Idea |
| --- | --- | --- |
| Atención ciudadana | CU-E02, E03, E04, E05, E12 | Ticket del ciudadano |
| Gestión interna | CU-E06, E07, E08, E09 | Trabajo diario del equipo |
| Desempeño | CU-E10 | Indicador, meta, semáforo |
| Administración | CU-E11 | Usuarios, cargos, parámetros |
| Ingreso | CU-E01 | Sesión mock |

## Pantalla → CU → tablas del DER

| Pantalla | Ruta | CU | Tablas / entidades (conceptuales) |
| --- | --- | --- | --- |
| Login | `/login/` | CU-E01 | `usuario`, `cargo`, `delegacion` |
| Inicio / tablero | `/` | CU-E01 + vista de `indicador` | `ticket`, `delegacion` |
| Ingresar ticket | `/requerimientos/nuevo/` | CU-E02 | `ticket`, `ciudadano`, `delegacion` |
| Listado de tickets | `/lista/` | CU-E03 | `ticket`, `ciudadano`, `delegacion` |
| Ficha del ticket | `/requerimientos/<id>/` | CU-E04 | `ticket`, `ciudadano`, semáforo |
| Tablero Kanban | `/control/kanban/` | CU-E05 | `ticket` (estado) |
| Actividad y evidencia | `/control/actividades/` | CU-E06, CU-E07 | `actividad`, `evidencia`, `funcionario` |
| Compromisos | `/control/tubo-trabajo/` | CU-E08 | `compromiso`, `ciudadano`, `delegacion` |
| Agenda | `/control/agenda/` | CU-E09 | `agenda`, `compromiso`, `actividad` |
| Semáforo SGR / KPIs | `/control/semaforo-sgr/`, `/control/` | CU-E10 | `indicador`, `meta`, `funcionario` |
| Usuarios / cargos / parámetros | `/administracion/...` | CU-E11 | `usuario`, `cargo`, parámetros |
| Encuesta y avisos | `/encuestas/`, `/control/notificaciones/` | CU-E12 | `ticket` (nota 1–5), avisos |

## Vocabulario que debe verse igual que en el DER

- `ticket` (no “caso genérico”)
- `ciudadano`
- `delegacion` — Centro, Rural, La Antena, La Pampa, Av. del Mar, Las Compañías
- tipificación: RECLAMO, SOLICITUD, CONSULTA, SUGERENCIA, FELICITACIÓN
- canal: ventanilla, WhatsApp, correo
- `actividad`, `evidencia`, `compromiso`, `agenda`
- `indicador`, `meta`, semáforo

Los archivos JSON en `data/` simulan esas tablas. Cuando exista el script SQL / MySQL de la siguiente entrega, este mapa se reutiliza.
