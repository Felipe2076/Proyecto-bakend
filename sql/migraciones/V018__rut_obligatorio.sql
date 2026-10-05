-- Versión     : V018
-- Descripción : RUT obligatorio, único y con formato; toda cuenta tiene funcionario
-- Autor       : Bakend pipi       Revisor: ramoncito
-- MER         : v1.13 (pendiente de aporte gráfico)
-- Rollback    : sql/rollback/R018__rut_obligatorio.sql
-- Requiere    : V017 y D003 (cero funcionarios sin RUT; ver B7)
-- Equivale a  : cuentas/migrations/0003_rut_obligatorio.py
-- Nota        : el índice de Django se llama idx_fun_deleg_apellido (límite de 30
--               caracteres del ORM). En MySQL el script conserva el nombre del plan.
-- Reejecución : si el migrate de Django se cortó a la mitad, el UNIQUE o el CHECK
--               pueden existir. Este script no vuelve a crearlos.
-- Corrección  : no se abre otro número. D004 (EQ-47) es el último de la bitácora.
--               V018 no había quedado aplicado en las bases con datos.

ALTER TABLE cuentas_funcionario
  MODIFY rut VARCHAR(10) NOT NULL,
  MODIFY nombres VARCHAR(60) NOT NULL,
  MODIFY apellido_paterno VARCHAR(60) NOT NULL;

SET @hay_uq := (
  SELECT COUNT(*) FROM (
    SELECT CONSTRAINT_NAME AS nombre
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'cuentas_funcionario'
      AND CONSTRAINT_NAME = 'uq_funcionario_rut'
    UNION
    SELECT INDEX_NAME
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'cuentas_funcionario'
      AND INDEX_NAME = 'uq_funcionario_rut'
  ) existentes
);
SET @sql_uq := IF(
  @hay_uq = 0,
  'ALTER TABLE cuentas_funcionario ADD CONSTRAINT uq_funcionario_rut UNIQUE (rut)',
  'SELECT 1'
);
PREPARE siged_v018_uq FROM @sql_uq;
EXECUTE siged_v018_uq;
DEALLOCATE PREPARE siged_v018_uq;

SET @hay_ck := (
  SELECT COUNT(*)
  FROM information_schema.TABLE_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND TABLE_NAME = 'cuentas_funcionario'
    AND CONSTRAINT_NAME = 'ck_funcionario_rut'
);
SET @sql_ck := IF(
  @hay_ck = 0,
  'ALTER TABLE cuentas_funcionario ADD CONSTRAINT ck_funcionario_rut CHECK (REGEXP_LIKE(rut, ''^[0-9]{7,8}-[0-9K]$'', ''c''))',
  'SELECT 1'
);
PREPARE siged_v018_ck FROM @sql_ck;
EXECUTE siged_v018_ck;
DEALLOCATE PREPARE siged_v018_ck;

ALTER TABLE cuentas_usuario
  MODIFY funcionario_id BIGINT NOT NULL;
