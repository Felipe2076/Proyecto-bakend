-- Versión     : D003
-- Descripción : Reemplaza identidades de demostración por datos ficticios
-- Autor       : Bakend pipi       Revisor: ramoncito
-- Rollback    : restaurar el respaldo mysqldump previo (no hay script inverso)
-- Requiere    : V017. También se puede repetir después de V018: no escribe NULL.
-- Nota        : no contiene claves en texto plano ni hashes utilizables.
--               auth_user.password queda en '!' (Django la trata como
--               inutilizable). importar_json asigna una clave distinta por
--               cuenta y la escribe solo en .demo_credentials.local.
--               Los nombres se guardan sin la marca; es_simulacion la pinta.
--               Los UPDATE de vecino por id 1 a 21 cubren el fixture.
--               No alcanzan para una base real: el id 22, FUN-DEMO-ADMIN u
--               otra fila quedan para el cierre de este script, que recorre
--               cualquier fila fuera del rango 33.xxx.xxx. No hay una lista
--               cerrada de id.
--               Después: sql/verificacion/B7__rut_simulacion.sql debe dar 0.
START TRANSACTION;

-- Suelta el RUT canónico que tenga una fila ajena al catálogo, sin dejar NULL
-- (V018 ya puede haber marcado la columna como obligatoria). 338xxxxx es un
-- estacionamiento: el cierre de este script lo cambia por un RUT 33.100.xxx libre.
UPDATE cuentas_funcionario f
JOIN (
  SELECT id, cuerpo,
         11 - MOD(
             (cuerpo DIV 1 % 10) * 2
           + (cuerpo DIV 10 % 10) * 3
           + (cuerpo DIV 100 % 10) * 4
           + (cuerpo DIV 1000 % 10) * 5
           + (cuerpo DIV 10000 % 10) * 6
           + (cuerpo DIV 100000 % 10) * 7
           + (cuerpo DIV 1000000 % 10) * 2
           + (cuerpo DIV 10000000 % 10) * 3
         , 11) AS resto
  FROM (
    SELECT id, 33800000 + id AS cuerpo
    FROM cuentas_funcionario
    WHERE codigo IS NULL OR codigo NOT IN ('FUN-001','FUN-002','FUN-003','FUN-004','FUN-005','FUN-006','FUN-007','FUN-008','FUN-009','FUN-010','FUN-011','FUN-012','FUN-013','FUN-014','FUN-015','FUN-016','FUN-017','FUN-018','FUN-019','FUN-020','FUN-021','FUN-022','FUN-023','FUN-024','FUN-025','FUN-026','FUN-027','FUN-028','FUN-029','FUN-030','FUN-031','FUN-032')
  ) nums
) x ON x.id = f.id
SET f.rut = CONCAT(x.cuerpo, '-', CASE x.resto WHEN 11 THEN '0' WHEN 10 THEN 'K' ELSE CAST(x.resto AS UNSIGNED) END)
WHERE f.rut IS NULL OR TRIM(f.rut) = ''
   OR CAST(SUBSTRING_INDEX(REPLACE(f.rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33100001 AND 33100032
   OR CAST(SUBSTRING_INDEX(REPLACE(f.rut, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999;

UPDATE cuentas_usuario
SET username = CONCAT('reserva-', id),
    correo = CONCAT('reserva-', id, '@siged.test')
WHERE codigo IS NULL OR codigo NOT IN ('USR-001','USR-002','USR-003','USR-004','USR-005','USR-006','USR-007','USR-008','USR-009','USR-010','USR-011','USR-012','USR-013','USR-014','USR-015','USR-016','USR-017','USR-018','USR-019','USR-020','USR-021','USR-022','USR-023','USR-024','USR-025');

UPDATE auth_user au
JOIN cuentas_usuario u ON u.user_id = au.id
SET au.username = CONCAT('reserva-auth-', au.id),
    au.email = u.correo
WHERE u.codigo IS NULL OR u.codigo NOT IN ('USR-001','USR-002','USR-003','USR-004','USR-005','USR-006','USR-007','USR-008','USR-009','USR-010','USR-011','USR-012','USR-013','USR-014','USR-015','USR-016','USR-017','USR-018','USR-019','USR-020','USR-021','USR-022','USR-023','USR-024','USR-025');

UPDATE cuentas_funcionario SET rut='33100001-9', nombres='Alba', apellido_paterno='Alamo', apellido_materno='Herrera', nombre='Alba Alamo Herrera', es_simulacion=1 WHERE codigo='FUN-001';
UPDATE cuentas_funcionario SET rut='33100002-7', nombres='Bruno', apellido_paterno='Alamo', apellido_materno='Keller', nombre='Bruno Alamo Keller', es_simulacion=1 WHERE codigo='FUN-002';
UPDATE cuentas_funcionario SET rut='33100003-5', nombres='Celia', apellido_paterno='Alamo', apellido_materno='Nieto', nombre='Celia Alamo Nieto', es_simulacion=1 WHERE codigo='FUN-003';
UPDATE cuentas_funcionario SET rut='33100004-3', nombres='Dario', apellido_paterno='Alamo', apellido_materno='Quilo', nombre='Dario Alamo Quilo', es_simulacion=1 WHERE codigo='FUN-004';
UPDATE cuentas_funcionario SET rut='33100005-1', nombres='Elena', apellido_paterno='Alamo', apellido_materno='Toro', nombre='Elena Alamo Toro', es_simulacion=1 WHERE codigo='FUN-005';
UPDATE cuentas_funcionario SET rut='33100006-K', nombres='Felix', apellido_paterno='Alamo', apellido_materno='Castro', nombre='Felix Alamo Castro', es_simulacion=1 WHERE codigo='FUN-006';
UPDATE cuentas_funcionario SET rut='33100007-8', nombres='Greta', apellido_paterno='Alamo', apellido_materno='Flores', nombre='Greta Alamo Flores', es_simulacion=1 WHERE codigo='FUN-007';
UPDATE cuentas_funcionario SET rut='33100008-6', nombres='Hugo', apellido_paterno='Alamo', apellido_materno='Ibanez', nombre='Hugo Alamo Ibanez', es_simulacion=1 WHERE codigo='FUN-008';
UPDATE cuentas_funcionario SET rut='33100009-4', nombres='Iris', apellido_paterno='Alamo', apellido_materno='Lago', nombre='Iris Alamo Lago', es_simulacion=1 WHERE codigo='FUN-009';
UPDATE cuentas_funcionario SET rut='33100010-8', nombres='Julio', apellido_paterno='Alamo', apellido_materno='Olmo', nombre='Julio Alamo Olmo', es_simulacion=1 WHERE codigo='FUN-010';
-- Si FUN-011…FUN-032 ya existen (no solo el fixture 1 a 10), el RUT sigue al JSON.
UPDATE cuentas_funcionario f
JOIN (
  SELECT 'FUN-011' AS codigo, '33100011-6' AS rut, 'Kael' AS nombres, 'Alamo' AS apellido_paterno, 'Rios' AS apellido_materno, 'Kael Alamo Rios' AS nombre
  UNION ALL SELECT 'FUN-012', '33100012-4', 'Luna', 'Alamo', 'Bravo', 'Luna Alamo Bravo'
  UNION ALL SELECT 'FUN-013', '33100013-2', 'Milo', 'Alamo', 'Diaz', 'Milo Alamo Diaz'
  UNION ALL SELECT 'FUN-014', '33100014-0', 'Nora', 'Alamo', 'Guerra', 'Nora Alamo Guerra'
  UNION ALL SELECT 'FUN-015', '33100015-9', 'Omar', 'Alamo', 'Jara', 'Omar Alamo Jara'
  UNION ALL SELECT 'FUN-016', '33100016-7', 'Pia', 'Alamo', 'Mora', 'Pia Alamo Mora'
  UNION ALL SELECT 'FUN-017', '33100017-5', 'Quique', 'Alamo', 'Paz', 'Quique Alamo Paz'
  UNION ALL SELECT 'FUN-018', '33100018-3', 'Rita', 'Alamo', 'Solis', 'Rita Alamo Solis'
  UNION ALL SELECT 'FUN-019', '33100019-1', 'Sael', 'Alamo', 'Bravo', 'Sael Alamo Bravo'
  UNION ALL SELECT 'FUN-020', '33100020-5', 'Tomas', 'Alamo', 'Espinosa', 'Tomas Alamo Espinosa'
  UNION ALL SELECT 'FUN-021', '33100021-3', 'Alba', 'Bravo', 'Herrera', 'Alba Bravo Herrera'
  UNION ALL SELECT 'FUN-022', '33100022-1', 'Bruno', 'Bravo', 'Keller', 'Bruno Bravo Keller'
  UNION ALL SELECT 'FUN-023', '33100023-K', 'Celia', 'Bravo', 'Nieto', 'Celia Bravo Nieto'
  UNION ALL SELECT 'FUN-024', '33100024-8', 'Dario', 'Bravo', 'Quilo', 'Dario Bravo Quilo'
  UNION ALL SELECT 'FUN-025', '33100025-6', 'Elena', 'Bravo', 'Toro', 'Elena Bravo Toro'
  UNION ALL SELECT 'FUN-026', '33100026-4', 'Felix', 'Bravo', 'Castro', 'Felix Bravo Castro'
  UNION ALL SELECT 'FUN-027', '33100027-2', 'Greta', 'Bravo', 'Flores', 'Greta Bravo Flores'
  UNION ALL SELECT 'FUN-028', '33100028-0', 'Hugo', 'Bravo', 'Ibanez', 'Hugo Bravo Ibanez'
  UNION ALL SELECT 'FUN-029', '33100029-9', 'Iris', 'Bravo', 'Lago', 'Iris Bravo Lago'
  UNION ALL SELECT 'FUN-030', '33100030-2', 'Julio', 'Bravo', 'Olmo', 'Julio Bravo Olmo'
  UNION ALL SELECT 'FUN-031', '33100031-0', 'Kael', 'Bravo', 'Rios', 'Kael Bravo Rios'
  UNION ALL SELECT 'FUN-032', '33100032-9', 'Luna', 'Bravo', 'Alamo', 'Luna Bravo Alamo'
) canonico ON canonico.codigo = f.codigo
SET f.rut = canonico.rut,
    f.nombres = canonico.nombres,
    f.apellido_paterno = canonico.apellido_paterno,
    f.apellido_materno = canonico.apellido_materno,
    f.nombre = canonico.nombre,
    f.es_simulacion = 1;
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-011', '33100011-6', 'Kael', 'Alamo', 'Rios', 'Kael Alamo Rios', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-011');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-012', '33100012-4', 'Luna', 'Alamo', 'Bravo', 'Luna Alamo Bravo', 1, (SELECT id FROM cuentas_cargo WHERE id=2 OR nombre='Gestor Social' ORDER BY id=2 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-012');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-013', '33100013-2', 'Milo', 'Alamo', 'Diaz', 'Milo Alamo Diaz', 1, (SELECT id FROM cuentas_cargo WHERE id=3 OR nombre='Gestor Social' ORDER BY id=3 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-013');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-014', '33100014-0', 'Nora', 'Alamo', 'Guerra', 'Nora Alamo Guerra', 1, (SELECT id FROM cuentas_cargo WHERE id=4 OR nombre='Gestor Social' ORDER BY id=4 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-014');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-015', '33100015-9', 'Omar', 'Alamo', 'Jara', 'Omar Alamo Jara', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Rural' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-015');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-016', '33100016-7', 'Pia', 'Alamo', 'Mora', 'Pia Alamo Mora', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-016');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-017', '33100017-5', 'Quique', 'Alamo', 'Paz', 'Quique Alamo Paz', 1, (SELECT id FROM cuentas_cargo WHERE id=2 OR nombre='Gestor Social' ORDER BY id=2 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-017');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-018', '33100018-3', 'Rita', 'Alamo', 'Solis', 'Rita Alamo Solis', 1, (SELECT id FROM cuentas_cargo WHERE id=3 OR nombre='Gestor Social' ORDER BY id=3 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-018');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-019', '33100019-1', 'Sael', 'Alamo', 'Bravo', 'Sael Alamo Bravo', 1, (SELECT id FROM cuentas_cargo WHERE id=4 OR nombre='Gestor Social' ORDER BY id=4 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-019');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-020', '33100020-5', 'Tomas', 'Alamo', 'Espinosa', 'Tomas Alamo Espinosa', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-020');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-021', '33100021-3', 'Alba', 'Bravo', 'Herrera', 'Alba Bravo Herrera', 1, (SELECT id FROM cuentas_cargo WHERE id=2 OR nombre='Gestor Social' ORDER BY id=2 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-021');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-022', '33100022-1', 'Bruno', 'Bravo', 'Keller', 'Bruno Bravo Keller', 1, (SELECT id FROM cuentas_cargo WHERE id=3 OR nombre='Gestor Social' ORDER BY id=3 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-022');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-023', '33100023-K', 'Celia', 'Bravo', 'Nieto', 'Celia Bravo Nieto', 1, (SELECT id FROM cuentas_cargo WHERE id=4 OR nombre='Gestor Social' ORDER BY id=4 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-023');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-024', '33100024-8', 'Dario', 'Bravo', 'Quilo', 'Dario Bravo Quilo', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-024');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-025', '33100025-6', 'Elena', 'Bravo', 'Toro', 'Elena Bravo Toro', 1, (SELECT id FROM cuentas_cargo WHERE id=2 OR nombre='Gestor Social' ORDER BY id=2 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-025');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-026', '33100026-4', 'Felix', 'Bravo', 'Castro', 'Felix Bravo Castro', 1, (SELECT id FROM cuentas_cargo WHERE id=3 OR nombre='Gestor Social' ORDER BY id=3 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-026');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-027', '33100027-2', 'Greta', 'Bravo', 'Flores', 'Greta Bravo Flores', 1, (SELECT id FROM cuentas_cargo WHERE id=4 OR nombre='Gestor Social' ORDER BY id=4 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-027');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-028', '33100028-0', 'Hugo', 'Bravo', 'Ibanez', 'Hugo Bravo Ibanez', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-028');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-029', '33100029-9', 'Iris', 'Bravo', 'Lago', 'Iris Bravo Lago', 1, (SELECT id FROM cuentas_cargo WHERE id=2 OR nombre='Gestor Social' ORDER BY id=2 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-029');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-030', '33100030-2', 'Julio', 'Bravo', 'Olmo', 'Julio Bravo Olmo', 1, (SELECT id FROM cuentas_cargo WHERE id=3 OR nombre='Gestor Social' ORDER BY id=3 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-030');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-031', '33100031-0', 'Kael', 'Bravo', 'Rios', 'Kael Bravo Rios', 1, (SELECT id FROM cuentas_cargo WHERE id=4 OR nombre='Gestor Social' ORDER BY id=4 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-031');
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, apellido_materno, nombre, es_simulacion, cargo_id, delegacion_id, estado) SELECT 'FUN-032', '33100032-9', 'Luna', 'Bravo', 'Alamo', 'Luna Bravo Alamo', 1, (SELECT id FROM cuentas_cargo WHERE id=1 OR nombre='Gestor Social' ORDER BY id=1 DESC LIMIT 1), (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo' FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM cuentas_funcionario WHERE codigo='FUN-032');

UPDATE cuentas_usuario u JOIN cuentas_funcionario f ON f.codigo='FUN-011' JOIN cuentas_rol r ON r.codigo='administrador' SET u.username=f.rut, u.nombre=f.nombre, u.correo='fun-011@siged.test', u.funcionario_id=f.id, u.delegacion_id=f.delegacion_id, u.rol_id=r.id WHERE u.codigo='USR-001';
UPDATE auth_user au JOIN cuentas_usuario u ON u.user_id=au.id SET au.username=u.username, au.email=u.correo, au.password='!', au.first_name='Kael', au.last_name='Alamo' WHERE u.codigo='USR-001';
UPDATE cuentas_usuario u JOIN cuentas_funcionario f ON f.codigo='FUN-001' JOIN cuentas_rol r ON r.codigo='jefatura' SET u.username=f.rut, u.nombre=f.nombre, u.correo='fun-001@siged.test', u.funcionario_id=f.id, u.delegacion_id=f.delegacion_id, u.rol_id=r.id WHERE u.codigo='USR-002';
UPDATE auth_user au JOIN cuentas_usuario u ON u.user_id=au.id SET au.username=u.username, au.email=u.correo, au.password='!', au.first_name='Alba', au.last_name='Alamo' WHERE u.codigo='USR-002';
UPDATE cuentas_usuario u JOIN cuentas_funcionario f ON f.codigo='FUN-002' JOIN cuentas_rol r ON r.codigo='funcionario' SET u.username=f.rut, u.nombre=f.nombre, u.correo='fun-002@siged.test', u.funcionario_id=f.id, u.delegacion_id=f.delegacion_id, u.rol_id=r.id WHERE u.codigo='USR-003';
UPDATE auth_user au JOIN cuentas_usuario u ON u.user_id=au.id SET au.username=u.username, au.email=u.correo, au.password='!', au.first_name='Bruno', au.last_name='Alamo' WHERE u.codigo='USR-003';
UPDATE cuentas_usuario u JOIN cuentas_funcionario f ON f.codigo='FUN-004' JOIN cuentas_rol r ON r.codigo='ventanilla' SET u.username=f.rut, u.nombre=f.nombre, u.correo='fun-004@siged.test', u.funcionario_id=f.id, u.delegacion_id=f.delegacion_id, u.rol_id=r.id WHERE u.codigo='USR-004';
UPDATE auth_user au JOIN cuentas_usuario u ON u.user_id=au.id SET au.username=u.username, au.email=u.correo, au.password='!', au.first_name='Dario', au.last_name='Alamo' WHERE u.codigo='USR-004';
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100012-4', 'Luna', 'Alamo', 'fun-012@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100012-4');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-005', au.id, f.rut, f.nombre, 'fun-012@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-012' JOIN cuentas_rol r ON r.codigo='jefatura' WHERE au.username='33100012-4' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-005');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100013-2', 'Milo', 'Alamo', 'fun-013@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100013-2');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-006', au.id, f.rut, f.nombre, 'fun-013@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-013' JOIN cuentas_rol r ON r.codigo='funcionario' WHERE au.username='33100013-2' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-006');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100014-0', 'Nora', 'Alamo', 'fun-014@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100014-0');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-007', au.id, f.rut, f.nombre, 'fun-014@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-014' JOIN cuentas_rol r ON r.codigo='ventanilla' WHERE au.username='33100014-0' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-007');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100015-9', 'Omar', 'Alamo', 'fun-015@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100015-9');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-008', au.id, f.rut, f.nombre, 'fun-015@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-015' JOIN cuentas_rol r ON r.codigo='administrador' WHERE au.username='33100015-9' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-008');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100016-7', 'Pia', 'Alamo', 'fun-016@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100016-7');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-009', au.id, f.rut, f.nombre, 'fun-016@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-016' JOIN cuentas_rol r ON r.codigo='administrador' WHERE au.username='33100016-7' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-009');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100017-5', 'Quique', 'Alamo', 'fun-017@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100017-5');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-010', au.id, f.rut, f.nombre, 'fun-017@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-017' JOIN cuentas_rol r ON r.codigo='jefatura' WHERE au.username='33100017-5' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-010');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100018-3', 'Rita', 'Alamo', 'fun-018@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100018-3');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-011', au.id, f.rut, f.nombre, 'fun-018@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-018' JOIN cuentas_rol r ON r.codigo='funcionario' WHERE au.username='33100018-3' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-011');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100019-1', 'Sael', 'Alamo', 'fun-019@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100019-1');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-012', au.id, f.rut, f.nombre, 'fun-019@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-019' JOIN cuentas_rol r ON r.codigo='ventanilla' WHERE au.username='33100019-1' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-012');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100020-5', 'Tomas', 'Alamo', 'fun-020@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100020-5');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-013', au.id, f.rut, f.nombre, 'fun-020@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-020' JOIN cuentas_rol r ON r.codigo='administrador' WHERE au.username='33100020-5' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-013');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100021-3', 'Alba', 'Bravo', 'fun-021@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100021-3');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-014', au.id, f.rut, f.nombre, 'fun-021@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-021' JOIN cuentas_rol r ON r.codigo='jefatura' WHERE au.username='33100021-3' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-014');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100022-1', 'Bruno', 'Bravo', 'fun-022@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100022-1');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-015', au.id, f.rut, f.nombre, 'fun-022@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-022' JOIN cuentas_rol r ON r.codigo='funcionario' WHERE au.username='33100022-1' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-015');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100023-K', 'Celia', 'Bravo', 'fun-023@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100023-K');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-016', au.id, f.rut, f.nombre, 'fun-023@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-023' JOIN cuentas_rol r ON r.codigo='ventanilla' WHERE au.username='33100023-K' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-016');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100024-8', 'Dario', 'Bravo', 'fun-024@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100024-8');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-017', au.id, f.rut, f.nombre, 'fun-024@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-024' JOIN cuentas_rol r ON r.codigo='administrador' WHERE au.username='33100024-8' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-017');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100025-6', 'Elena', 'Bravo', 'fun-025@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100025-6');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-018', au.id, f.rut, f.nombre, 'fun-025@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-025' JOIN cuentas_rol r ON r.codigo='jefatura' WHERE au.username='33100025-6' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-018');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100026-4', 'Felix', 'Bravo', 'fun-026@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100026-4');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-019', au.id, f.rut, f.nombre, 'fun-026@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-026' JOIN cuentas_rol r ON r.codigo='funcionario' WHERE au.username='33100026-4' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-019');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100027-2', 'Greta', 'Bravo', 'fun-027@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100027-2');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-020', au.id, f.rut, f.nombre, 'fun-027@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-027' JOIN cuentas_rol r ON r.codigo='ventanilla' WHERE au.username='33100027-2' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-020');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100028-0', 'Hugo', 'Bravo', 'fun-028@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100028-0');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-021', au.id, f.rut, f.nombre, 'fun-028@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-028' JOIN cuentas_rol r ON r.codigo='administrador' WHERE au.username='33100028-0' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-021');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100029-9', 'Iris', 'Bravo', 'fun-029@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100029-9');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-022', au.id, f.rut, f.nombre, 'fun-029@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-029' JOIN cuentas_rol r ON r.codigo='jefatura' WHERE au.username='33100029-9' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-022');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100030-2', 'Julio', 'Bravo', 'fun-030@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100030-2');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-023', au.id, f.rut, f.nombre, 'fun-030@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-030' JOIN cuentas_rol r ON r.codigo='funcionario' WHERE au.username='33100030-2' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-023');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100031-0', 'Kael', 'Bravo', 'fun-031@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100031-0');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-024', au.id, f.rut, f.nombre, 'fun-031@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-031' JOIN cuentas_rol r ON r.codigo='ventanilla' WHERE au.username='33100031-0' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-024');
INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) SELECT '!', 0, '33100032-9', 'Luna', 'Bravo', 'fun-032@siged.test', 0, 1, UTC_TIMESTAMP() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM auth_user WHERE username='33100032-9');
INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado) SELECT 'USR-025', au.id, f.rut, f.nombre, 'fun-032@siged.test', r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP() FROM auth_user au JOIN cuentas_funcionario f ON f.codigo='FUN-032' JOIN cuentas_rol r ON r.codigo='administrador' WHERE au.username='33100032-9' AND NOT EXISTS (SELECT 1 FROM cuentas_usuario WHERE codigo='USR-025');

UPDATE requerimientos_vecino SET nombre='Alba Castro Herrera', rut='33500001-3', telefono='+56900000001', correo='vecino001@siged.test', direccion='Calle Ficticia 1', es_simulacion=1 WHERE id=1;
UPDATE requerimientos_vecino SET nombre='Bruno Castro Keller', rut='33500002-1', telefono='+56900000002', correo='vecino002@siged.test', direccion='Calle Ficticia 2', es_simulacion=1 WHERE id=2;
UPDATE requerimientos_vecino SET nombre='Celia Castro Nieto', rut='33500003-K', telefono='+56900000003', correo='vecino003@siged.test', direccion='Calle Ficticia 3', es_simulacion=1 WHERE id=3;
UPDATE requerimientos_vecino SET nombre='Dario Castro Quilo', rut='33500004-8', telefono='+56900000004', correo='vecino004@siged.test', direccion='Calle Ficticia 4', es_simulacion=1 WHERE id=4;
UPDATE requerimientos_vecino SET nombre='Elena Castro Toro', rut='33500005-6', telefono='+56900000005', correo='vecino005@siged.test', direccion='Calle Ficticia 5', es_simulacion=1 WHERE id=5;
UPDATE requerimientos_vecino SET nombre='Felix Castro Diaz', rut='33500006-4', telefono='+56900000006', correo='vecino006@siged.test', direccion='Calle Ficticia 6', es_simulacion=1 WHERE id=6;
UPDATE requerimientos_vecino SET nombre='Greta Castro Flores', rut='33500007-2', telefono='+56900000007', correo='vecino007@siged.test', direccion='Calle Ficticia 7', es_simulacion=1 WHERE id=7;
UPDATE requerimientos_vecino SET nombre='Hugo Castro Ibanez', rut='33500008-0', telefono='+56900000008', correo='vecino008@siged.test', direccion='Calle Ficticia 8', es_simulacion=1 WHERE id=8;
UPDATE requerimientos_vecino SET nombre='Iris Castro Lago', rut='33500009-9', telefono='+56900000009', correo='vecino009@siged.test', direccion='Calle Ficticia 9', es_simulacion=1 WHERE id=9;
UPDATE requerimientos_vecino SET nombre='Julio Castro Olmo', rut='33500010-2', telefono='+56900000010', correo='vecino010@siged.test', direccion='Calle Ficticia 10', es_simulacion=1 WHERE id=10;
UPDATE requerimientos_vecino SET nombre='Kael Castro Rios', rut='33500011-0', telefono='+56900000011', correo='vecino011@siged.test', direccion='Calle Ficticia 11', es_simulacion=1 WHERE id=11;
UPDATE requerimientos_vecino SET nombre='Luna Castro Alamo', rut='33500012-9', telefono='+56900000012', correo='vecino012@siged.test', direccion='Calle Ficticia 12', es_simulacion=1 WHERE id=12;
UPDATE requerimientos_vecino SET nombre='Milo Castro Diaz', rut='33500013-7', telefono='+56900000013', correo='vecino013@siged.test', direccion='Calle Ficticia 13', es_simulacion=1 WHERE id=13;
UPDATE requerimientos_vecino SET nombre='Organización Ficticia 14', rut='33500014-5', telefono='+56900000014', correo='vecino014@siged.test', direccion='Calle Ficticia 14', es_simulacion=1 WHERE id=14;
UPDATE requerimientos_vecino SET nombre='Organización Ficticia 15', rut='33500015-3', telefono='+56900000015', correo='vecino015@siged.test', direccion='Calle Ficticia 15', es_simulacion=1 WHERE id=15;
UPDATE requerimientos_vecino SET nombre='Organización Ficticia 16', rut='33500016-1', telefono='+56900000016', correo='vecino016@siged.test', direccion='Calle Ficticia 16', es_simulacion=1 WHERE id=16;
UPDATE requerimientos_vecino SET nombre='Organización Ficticia 17', rut='33500017-K', telefono='+56900000017', correo='vecino017@siged.test', direccion='Calle Ficticia 17', es_simulacion=1 WHERE id=17;
UPDATE requerimientos_vecino SET nombre='Rita Castro Solis', rut='33500018-8', telefono='+56900000018', correo='vecino018@siged.test', direccion='Calle Ficticia 18', es_simulacion=1 WHERE id=18;
UPDATE requerimientos_vecino SET nombre='Sael Castro Bravo', rut='33500019-6', telefono='+56900000019', correo='vecino019@siged.test', direccion='Calle Ficticia 19', es_simulacion=1 WHERE id=19;
UPDATE requerimientos_vecino SET nombre='Tomas Castro Espinosa', rut='33500020-K', telefono='+56900000020', correo='vecino020@siged.test', direccion='Calle Ficticia 20', es_simulacion=1 WHERE id=20;
UPDATE requerimientos_vecino SET nombre='Alba Diaz Herrera', rut='33500021-8', telefono='+56900000021', correo='vecino021@siged.test', direccion='Calle Ficticia 21', es_simulacion=1 WHERE id=21;
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Bruno Diaz Keller', '33500022-6', 'Calle Ficticia 22', '+56900000022', 'vecino022@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500022-6');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Celia Diaz Nieto', '33500023-4', 'Calle Ficticia 23', '+56900000023', 'vecino023@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500023-4');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Dario Diaz Quilo', '33500024-2', 'Calle Ficticia 24', '+56900000024', 'vecino024@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500024-2');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Elena Diaz Toro', '33500025-0', 'Calle Ficticia 25', '+56900000025', 'vecino025@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500025-0');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Felix Diaz Castro', '33500026-9', 'Calle Ficticia 26', '+56900000026', 'vecino026@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500026-9');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Greta Diaz Flores', '33500027-7', 'Calle Ficticia 27', '+56900000027', 'vecino027@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Centro' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500027-7');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Hugo Diaz Ibanez', '33500028-5', 'Calle Ficticia 28', '+56900000028', 'vecino028@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Rural' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500028-5');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Iris Diaz Lago', '33500029-3', 'Calle Ficticia 29', '+56900000029', 'vecino029@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Rural' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500029-3');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Julio Diaz Olmo', '33500030-7', 'Calle Ficticia 30', '+56900000030', 'vecino030@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Rural' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500030-7');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Kael Diaz Rios', '33500031-5', 'Calle Ficticia 31', '+56900000031', 'vecino031@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Rural' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500031-5');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Luna Diaz Alamo', '33500032-3', 'Calle Ficticia 32', '+56900000032', 'vecino032@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Rural' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500032-3');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Milo Diaz Espinosa', '33500033-1', 'Calle Ficticia 33', '+56900000033', 'vecino033@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500033-1');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Nora Diaz Guerra', '33500034-K', 'Calle Ficticia 34', '+56900000034', 'vecino034@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500034-K');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Omar Diaz Jara', '33500035-8', 'Calle Ficticia 35', '+56900000035', 'vecino035@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500035-8');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Pia Diaz Mora', '33500036-6', 'Calle Ficticia 36', '+56900000036', 'vecino036@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500036-6');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Quique Diaz Paz', '33500037-4', 'Calle Ficticia 37', '+56900000037', 'vecino037@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500037-4');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Rita Diaz Solis', '33500038-2', 'Calle Ficticia 38', '+56900000038', 'vecino038@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500038-2');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Sael Diaz Bravo', '33500039-0', 'Calle Ficticia 39', '+56900000039', 'vecino039@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Antena' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500039-0');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Tomas Diaz Espinosa', '33500040-4', 'Calle Ficticia 40', '+56900000040', 'vecino040@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500040-4');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Alba Espinosa Herrera', '33500041-2', 'Calle Ficticia 41', '+56900000041', 'vecino041@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500041-2');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Bruno Espinosa Keller', '33500042-0', 'Calle Ficticia 42', '+56900000042', 'vecino042@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500042-0');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Celia Espinosa Nieto', '33500043-9', 'Calle Ficticia 43', '+56900000043', 'vecino043@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500043-9');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Dario Espinosa Quilo', '33500044-7', 'Calle Ficticia 44', '+56900000044', 'vecino044@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500044-7');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Elena Espinosa Toro', '33500045-5', 'Calle Ficticia 45', '+56900000045', 'vecino045@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500045-5');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Felix Espinosa Castro', '33500046-3', 'Calle Ficticia 46', '+56900000046', 'vecino046@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación La Pampa' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500046-3');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Greta Espinosa Flores', '33500047-1', 'Calle Ficticia 47', '+56900000047', 'vecino047@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500047-1');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Hugo Espinosa Ibanez', '33500048-K', 'Calle Ficticia 48', '+56900000048', 'vecino048@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500048-K');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Iris Espinosa Lago', '33500049-8', 'Calle Ficticia 49', '+56900000049', 'vecino049@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500049-8');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Julio Espinosa Olmo', '33500050-1', 'Calle Ficticia 50', '+56900000050', 'vecino050@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500050-1');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Kael Espinosa Rios', '33500051-K', 'Calle Ficticia 51', '+56900000051', 'vecino051@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500051-K');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Luna Espinosa Alamo', '33500052-8', 'Calle Ficticia 52', '+56900000052', 'vecino052@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500052-8');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Milo Espinosa Diaz', '33500053-6', 'Calle Ficticia 53', '+56900000053', 'vecino053@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Av. del Mar' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500053-6');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Nora Espinosa Guerra', '33500054-4', 'Calle Ficticia 54', '+56900000054', 'vecino054@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500054-4');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Omar Espinosa Jara', '33500055-2', 'Calle Ficticia 55', '+56900000055', 'vecino055@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500055-2');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Pia Espinosa Mora', '33500056-0', 'Calle Ficticia 56', '+56900000056', 'vecino056@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500056-0');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Quique Espinosa Paz', '33500057-9', 'Calle Ficticia 57', '+56900000057', 'vecino057@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500057-9');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Rita Espinosa Solis', '33500058-7', 'Calle Ficticia 58', '+56900000058', 'vecino058@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500058-7');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Sael Espinosa Bravo', '33500059-5', 'Calle Ficticia 59', '+56900000059', 'vecino059@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500059-5');
INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, delegacion_id, estado, es_simulacion) SELECT 'Tomas Espinosa Flores', '33500060-9', 'Calle Ficticia 60', '+56900000060', 'vecino060@siged.test', 'Simulación', (SELECT id FROM cuentas_delegacion WHERE nombre='Delegación Las Compañías' LIMIT 1), 'activo', 1 FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM requerimientos_vecino WHERE rut='33500060-9');

UPDATE control_gestion_actividad
SET contacto = CONCAT('Contacto ficticio ', id, '')
WHERE contacto IS NOT NULL AND contacto <> '';

UPDATE requerimientos_requerimiento r
JOIN cuentas_funcionario f ON f.id = r.funcionario_id
SET r.asignado_a = f.nombre
WHERE r.funcionario_id IS NOT NULL;

UPDATE requerimientos_areasoporte a
JOIN cuentas_funcionario f ON f.id = a.encargado_id
SET a.encargado_nombre = f.nombre
WHERE a.encargado_id IS NOT NULL;

-- Cualquier cuenta sin funcionario (no depende del id).
INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, nombre, es_simulacion, cargo_id, delegacion_id, estado)
SELECT CONCAT('FUN-X', u.id), NULL, 'Extra', 'Simulado', 'Extra Simulado', 1,
       COALESCE(u.cargo_id, (SELECT id FROM cuentas_cargo ORDER BY id LIMIT 1)),
       COALESCE(u.delegacion_id, (SELECT id FROM cuentas_delegacion ORDER BY id LIMIT 1)),
       'activo'
FROM cuentas_usuario u
WHERE u.funcionario_id IS NULL
  AND COALESCE(u.cargo_id, (SELECT id FROM cuentas_cargo ORDER BY id LIMIT 1)) IS NOT NULL
  AND COALESCE(u.delegacion_id, (SELECT id FROM cuentas_delegacion ORDER BY id LIMIT 1)) IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM cuentas_funcionario f WHERE f.codigo = CONCAT('FUN-X', u.id));

UPDATE cuentas_usuario u
JOIN cuentas_funcionario f ON f.codigo = CONCAT('FUN-X', u.id)
SET u.funcionario_id = f.id
WHERE u.funcionario_id IS NULL;

-- Funcionarios que siguieron sin RUT 33.xxx.xxx (FUN-DEMO-ADMIN u otro código).
UPDATE cuentas_funcionario
SET nombres = IF(nombres IS NULL OR TRIM(nombres) = '', 'Extra', nombres),
    apellido_paterno = IF(apellido_paterno IS NULL OR TRIM(apellido_paterno) = '', 'Simulado', apellido_paterno)
WHERE rut IS NULL OR TRIM(rut) = ''
   OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999
   OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33800000 AND 33899999;

UPDATE cuentas_funcionario
SET nombre = TRIM(CONCAT(nombres, ' ', apellido_paterno))
WHERE nombre IS NULL OR TRIM(nombre) = '';

UPDATE cuentas_funcionario f
JOIN (
  SELECT id, cuerpo,
         11 - MOD(
             (cuerpo DIV 1 % 10) * 2
           + (cuerpo DIV 10 % 10) * 3
           + (cuerpo DIV 100 % 10) * 4
           + (cuerpo DIV 1000 % 10) * 5
           + (cuerpo DIV 10000 % 10) * 6
           + (cuerpo DIV 100000 % 10) * 7
           + (cuerpo DIV 1000000 % 10) * 2
           + (cuerpo DIV 10000000 % 10) * 3
         , 11) AS resto
  FROM (
    SELECT id, 33100032 + ROW_NUMBER() OVER (ORDER BY codigo, id) AS cuerpo
    FROM cuentas_funcionario
    WHERE rut IS NULL OR TRIM(rut) = ''
       OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999
       OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33800000 AND 33899999
  ) nums
) x ON x.id = f.id
SET f.rut = CONCAT(x.cuerpo, '-', CASE x.resto WHEN 11 THEN '0' WHEN 10 THEN 'K' ELSE CAST(x.resto AS CHAR) END),
    f.es_simulacion = 1;

UPDATE cuentas_funcionario
SET es_simulacion = 1
WHERE es_simulacion = 0
  AND CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33000000 AND 33999999;

-- Vecinos fuera del rango, sea cual sea su id (el 22 y cualquier otro).
SET @base_vecino := (
  SELECT GREATEST(33500060, COALESCE(MAX(CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED)), 33500060))
  FROM requerimientos_vecino
  WHERE CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33500000 AND 33599999
);

UPDATE requerimientos_vecino v
JOIN (
  SELECT id, cuerpo,
         11 - MOD(
             (cuerpo DIV 1 % 10) * 2
           + (cuerpo DIV 10 % 10) * 3
           + (cuerpo DIV 100 % 10) * 4
           + (cuerpo DIV 1000 % 10) * 5
           + (cuerpo DIV 10000 % 10) * 6
           + (cuerpo DIV 100000 % 10) * 7
           + (cuerpo DIV 1000000 % 10) * 2
           + (cuerpo DIV 10000000 % 10) * 3
         , 11) AS resto
  FROM (
    SELECT id, CAST(@base_vecino AS UNSIGNED) + ROW_NUMBER() OVER (ORDER BY id) AS cuerpo
    FROM requerimientos_vecino
    WHERE rut IS NULL OR TRIM(rut) = ''
       OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999
  ) nums
) x ON x.id = v.id
SET v.nombre = CONCAT('Vecino Simulado ', x.cuerpo - 33500000),
    v.rut = CONCAT(x.cuerpo, '-', CASE x.resto WHEN 11 THEN '0' WHEN 10 THEN 'K' ELSE CAST(x.resto AS CHAR) END),
    v.telefono = CONCAT('+569', LPAD(x.cuerpo - 33500000, 8, '0')),
    v.correo = CONCAT('vecino', x.cuerpo - 33500000, '@siged.test'),
    v.direccion = CONCAT('Calle Ficticia ', x.cuerpo - 33500000),
    v.territorio = 'Simulacion',
    v.es_simulacion = 1;

UPDATE requerimientos_vecino
SET es_simulacion = 1
WHERE es_simulacion = 0
  AND CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33000000 AND 33999999;

-- Cada rol presente × cada delegación presente. No es una lista fija de id.
SET @base_fun := (
  SELECT GREATEST(33100032, COALESCE(MAX(CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED)), 33100032))
  FROM cuentas_funcionario
  WHERE CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) BETWEEN 33100000 AND 33100999
);

INSERT INTO cuentas_funcionario (codigo, rut, nombres, apellido_paterno, nombre, es_simulacion, cargo_id, delegacion_id, estado)
SELECT codigo, CONCAT(cuerpo, '-', CASE resto WHEN 11 THEN '0' WHEN 10 THEN 'K' ELSE CAST(resto AS UNSIGNED) END),
       'Extra', 'Simulado', 'Extra Simulado', 1, cargo_id, delegacion_id, 'activo'
FROM (
  SELECT codigo, cargo_id, delegacion_id, cuerpo,
         11 - MOD(
             (cuerpo DIV 1 % 10) * 2
           + (cuerpo DIV 10 % 10) * 3
           + (cuerpo DIV 100 % 10) * 4
           + (cuerpo DIV 1000 % 10) * 5
           + (cuerpo DIV 10000 % 10) * 6
           + (cuerpo DIV 100000 % 10) * 7
           + (cuerpo DIV 1000000 % 10) * 2
           + (cuerpo DIV 10000000 % 10) * 3
         , 11) AS resto
  FROM (
    SELECT CONCAT('FG', letra, '-', d.id) AS codigo,
           COALESCE(
             (SELECT c.id FROM cuentas_cargo c WHERE c.nombre = CASE letra
                WHEN 'a' THEN 'Administrador del sistema'
                WHEN 'j' THEN 'Delegada Territorial'
                WHEN 'f' THEN 'Gestor Social'
                WHEN 'v' THEN 'Apoyo Administrativo'
              END LIMIT 1),
             (SELECT id FROM cuentas_cargo ORDER BY id LIMIT 1)
           ) AS cargo_id,
           d.id AS delegacion_id,
           CAST(@base_fun AS UNSIGNED) + ROW_NUMBER() OVER (ORDER BY letra, d.id) AS cuerpo
    FROM (
      SELECT r.id AS rol_id, CASE r.codigo
        WHEN 'administrador' THEN 'a'
        WHEN 'jefatura' THEN 'j'
        WHEN 'funcionario' THEN 'f'
        WHEN 'ventanilla' THEN 'v'
      END AS letra
      FROM cuentas_rol r
      WHERE r.codigo IN ('administrador', 'jefatura', 'funcionario', 'ventanilla')
    ) roles
    JOIN cuentas_delegacion d
    WHERE NOT EXISTS (
      SELECT 1 FROM cuentas_usuario u
      JOIN cuentas_funcionario f ON f.id = u.funcionario_id
      WHERE u.rol_id = roles.rol_id AND f.delegacion_id = d.id
    )
  ) nums
) listo
WHERE cargo_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM cuentas_funcionario f WHERE f.codigo = listo.codigo);

INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
SELECT '!', 0, f.rut, 'Extra', 'Simulado', CONCAT(LOWER(f.codigo), '@siged.test'), 0, 1, UTC_TIMESTAMP()
FROM cuentas_funcionario f
WHERE f.codigo LIKE 'FG_-%'
  AND NOT EXISTS (SELECT 1 FROM cuentas_usuario u WHERE u.funcionario_id = f.id)
  AND NOT EXISTS (SELECT 1 FROM auth_user au WHERE au.username = f.rut);

INSERT INTO cuentas_usuario (codigo, user_id, username, nombre, correo, rol_id, cargo_id, delegacion_id, funcionario_id, estado, creado)
SELECT CONCAT('UG', SUBSTRING(f.codigo, 3)), au.id, f.rut, f.nombre, CONCAT(LOWER(f.codigo), '@siged.test'),
       r.id, f.cargo_id, f.delegacion_id, f.id, 'activo', UTC_TIMESTAMP()
FROM cuentas_funcionario f
JOIN auth_user au ON au.username = f.rut
JOIN cuentas_rol r ON r.codigo = CASE SUBSTRING(f.codigo, 3, 1)
  WHEN 'a' THEN 'administrador'
  WHEN 'j' THEN 'jefatura'
  WHEN 'f' THEN 'funcionario'
  WHEN 'v' THEN 'ventanilla'
END
WHERE f.codigo LIKE 'FG_-%'
  AND NOT EXISTS (SELECT 1 FROM cuentas_usuario u WHERE u.funcionario_id = f.id OR u.codigo = CONCAT('UG', SUBSTRING(f.codigo, 3)));

-- El acceso de cualquier usuario queda en el RUT de su funcionario.
UPDATE cuentas_usuario u
JOIN cuentas_funcionario f ON f.id = u.funcionario_id
SET u.username = f.rut,
    u.nombre = f.nombre,
    u.correo = CONCAT(LOWER(f.codigo), '@siged.test')
WHERE u.codigo IS NULL
   OR u.codigo NOT IN ('USR-001','USR-002','USR-003','USR-004','USR-005','USR-006','USR-007','USR-008','USR-009','USR-010','USR-011','USR-012','USR-013','USR-014','USR-015','USR-016','USR-017','USR-018','USR-019','USR-020','USR-021','USR-022','USR-023','USR-024','USR-025')
   OR u.correo NOT LIKE '%@siged.test'
   OR CAST(SUBSTRING_INDEX(REPLACE(u.username, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999;

UPDATE auth_user au
JOIN cuentas_usuario u ON u.user_id = au.id
SET au.username = u.username,
    au.email = u.correo
WHERE au.username <> u.username OR au.email <> u.correo;

COMMIT;

