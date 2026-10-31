# Evaluación Sumativa 3: evolución del sistema municipal

El alcance corresponde a la pauta «Aplicación web con CRUD». Se conserva el sistema de gestión de delegaciones de La Serena, sus datos y sus módulos. Las funciones se ejecutan desde Django Templates, Bootstrap, formularios Django y ORM; la revisión no necesita Django Admin.

## Perfiles y grupos

Cada registro Rol se vincula con un Group de django.contrib.auth. Cada Usuario pertenece al grupo de su rol. La contraseña sigue almacenada en auth.User mediante el sistema de hash de Django. El acceso conserva RUT y contraseña.

- Administrador: acceso global, mantenedores completos, usuarios, cargos, parámetros y gestión de grupos.
- Jefatura: corresponde a Supervisor en la pauta. Conserva los módulos operacionales y accede a mantenedores autorizados: consulta de catálogos y creación/modificación de vecinos y atenciones de su delegación. No elimina registros críticos ni administra usuarios o grupos.
- Funcionario: conserva el trabajo territorial, actividades, compromisos, agenda e indicadores según su perfil original.
- Ventanilla: corresponde a Administrativo en la pauta. Conserva atención ciudadana, agenda, avisos y encuestas, con las restricciones del sistema original.

La pantalla Administración > Grupos y permisos permite consultar los permisos de cada grupo, modificar los autorizados y asignar perfiles a usuarios existentes. La selección de rol al crear una cuenta también asigna su grupo de Django. Se conserva la protección del administrador general y se impide que quien está administrando se quite su propio acceso.

Las restricciones se verifican en las vistas. Ocultar un enlace no sustituye la autorización. Cada petición vuelve a consultar la cuenta activa y sus permisos, por lo que las revocaciones se aplican sin esperar a que el usuario vuelva a iniciar sesión. Los mantenedores autorizados de Jefatura limitan datos y opciones relacionadas a su delegación.

## Recuperación de contraseña

1. El funcionario solicita la recuperación con el correo registrado.
2. El sistema genera un token de PasswordResetTokenGenerator de Django, vinculado a la cuenta y su contraseña actual.
3. Se envía un enlace al destinatario mediante el SMTP configurado. Se mantiene el código de seis dígitos como alternativa compatible con el flujo anterior.
4. El enlace lleva a una pantalla propia para establecer y confirmar la nueva contraseña.
5. El token vence a los diez minutos, se rechaza si está alterado o la cuenta está inactiva y deja de ser válido después del cambio.
6. El sistema confirma el resultado y permite iniciar sesión con la nueva contraseña.

Las invitaciones de cuentas nuevas siguen siendo enviadas al correo del funcionario. El administrador no escoge su contraseña. Las claves existentes no se cambian durante la actualización.

## Mantenedores y transacciones existentes

Se conservan los mantenedores de delegaciones, usuarios, roles, metas, tipos de atención, subatenciones, tipos de gestión y vecinos. Atenciones relaciona vecino, tipo/subtipo, delegación y usuario que registra.

Para una presentación con tres integrantes, la pauta pide seis mantenedores y tres transacciones. Se pueden demostrar los mantenedores anteriores y los flujos de ingreso/asignación de tickets, registro de atenciones y gestión de compromisos. Las relaciones se almacenan mediante ForeignKey y las validaciones se aplican al guardar. Excel, búsqueda, códigos automáticos, Kanban y paginadores superiores se conservan.

## Persistencia y despliegue

MySQL continúa como base de trabajo; SQLite se usa exclusivamente en las pruebas aisladas. La migración de esta evaluación agrega la relación Rol-Group y asigna los grupos a las cuentas existentes. No elimina registros de negocio ni reemplaza las contraseñas.

El despliegue mantiene EC2, Docker, Gunicorn y Apache con HTTPS. Las credenciales permanecen en variables de entorno y no se incluyen en Git. Antes de migrar se respalda la base y el código; los permisos de esquema se habilitan solo durante la migración y luego se retiran del usuario de la aplicación.

## Guion de revisión presencial

1. Entrar con el administrador y mostrar el panel global.
2. Crear una cuenta con un correo real del evaluador o del funcionario autorizado, seleccionar su rol y mostrar la invitación recibida.
3. Mostrar grupos, permisos y asignación desde las pantallas propias.
4. Entrar con Jefatura y Ventanilla para contrastar paneles y accesos; intentar una dirección restringida.
5. Demostrar crear, buscar, listar, modificar y eliminar en los mantenedores elegidos, utilizando registros de prueba identificados.
6. Demostrar tickets, atenciones y compromisos con sus relaciones y persistencia.
7. Solicitar recuperación, mostrar el mensaje recibido, abrir el enlace, definir la nueva contraseña e iniciar sesión con ella. El titular introduce personalmente la contraseña durante la demostración.
8. Mostrar EC2, migraciones, tablas/relaciones, GitHub y commits. Presentar el documento técnico y la evidencia de uso de IA.

## Evidencia de uso de IA

Solicitud del usuario: implementar únicamente lo exigido por la evaluación sobre los requisitos originales del sistema municipal.

Apoyo aplicado: comparación de la pauta con el código, integración de grupos y permisos de Django, enlace seguro de recuperación, pruebas de permisos y tokens, preparación del despliegue y documentación de los cambios. La evidencia debe identificar herramienta, solicitudes, respuestas y el código o resultado donde se aplicaron. No se deben adjuntar contraseñas, claves de aplicación, archivos privados ni conversaciones completas que contengan secretos.
