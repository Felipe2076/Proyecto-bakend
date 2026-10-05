-- Verificación B7 (bitácora §26.2.5 e, más el acceso por RUT).
-- Corrida de ensayo sobre una COPIA de la base. No es un script de esquema:
-- no cambia filas y no lleva número V/D. El siguiente número de datos sigue a D004 (EQ-47).
--
-- Cada consulta debe devolver 0 (la de rol × delegación, 0 filas).
-- No hay RUT de personas: solo se mide el rango de simulación 33.xxx.xxx
-- (cuerpo entre 33000000 y 33999999) en funcionario, usuario y vecino.
--
--   mysql gestion_muni_ensayo < sql/verificacion/B7__rut_simulacion.sql

-- Funcionarios sin RUT de simulación, o sin la marca.
SELECT COUNT(*) AS funcionarios_fuera
FROM cuentas_funcionario
WHERE rut IS NULL
   OR TRIM(rut) = ''
   OR es_simulacion = 0
   OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999;

-- Vecinos sin RUT de simulación, o sin la marca. Cualquier id, no solo 1 a 21.
SELECT COUNT(*) AS vecinos_fuera
FROM requerimientos_vecino
WHERE rut IS NULL
   OR TRIM(rut) = ''
   OR es_simulacion = 0
   OR CAST(SUBSTRING_INDEX(REPLACE(rut, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999;

-- El nombre de acceso del usuario es el RUT. Ninguno puede quedar fuera del rango.
SELECT COUNT(*) AS usuarios_fuera
FROM cuentas_usuario
WHERE username IS NULL
   OR TRIM(username) = ''
   OR correo NOT LIKE '%@siged.test'
   OR CAST(SUBSTRING_INDEX(REPLACE(username, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999;

-- La cuenta Django enlazada usa el mismo RUT.
SELECT COUNT(*) AS auth_fuera
FROM auth_user au
JOIN cuentas_usuario u ON u.user_id = au.id
WHERE CAST(SUBSTRING_INDEX(REPLACE(au.username, '.', ''), '-', 1) AS UNSIGNED) NOT BETWEEN 33000000 AND 33999999
   OR au.username <> u.username;

-- Combinaciones rol × delegación sin cuenta. Debe devolver 0 filas.
SELECT r.codigo, d.nombre, COUNT(u.id) AS cuentas
FROM cuentas_rol r
CROSS JOIN cuentas_delegacion d
LEFT JOIN (cuentas_usuario u JOIN cuentas_funcionario f ON f.id = u.funcionario_id)
       ON u.rol_id = r.id AND f.delegacion_id = d.id
GROUP BY r.codigo, d.nombre
HAVING cuentas = 0;

-- RUT de funcionario repetido. Debe devolver 0 filas.
SELECT rut, COUNT(*) AS repeticiones
FROM cuentas_funcionario
GROUP BY rut
HAVING COUNT(*) > 1;
