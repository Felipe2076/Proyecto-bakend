-- Versión     : R017
-- Descripción : Revierte V017 (columnas de RUT y marca de simulación)
-- Autor       : Bakend pipi       Revisor: ramoncito
-- Requiere    : R018 aplicado antes, si V018 ya se ejecutó
-- Advertencia : borrar estas columnas elimina los RUT cargados. Respalde antes.
--
-- MySQL 1553: el índice compuesto (delegacion_id, apellido_paterno, nombres)
-- es el que sostiene la llave foránea de delegacion_id. Hay que dejar un
-- índice de una sola columna antes de borrarlo. El nombre largo es el de
-- V017; idx_fun_deleg_apellido es el de la migración Django (límite de 30).
-- La bitácora adjunta con la corrección no estaba en el workspace: este
-- script aplica el arreglo habitual de ese error.

SET @existe := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'cuentas_funcionario'
    AND index_name = 'idx_funcionario_delegacion_id'
);
SET @sql := IF(
  @existe = 0,
  'ALTER TABLE cuentas_funcionario ADD INDEX idx_funcionario_delegacion_id (delegacion_id)',
  'SELECT 1'
);
PREPARE siged_r017 FROM @sql;
EXECUTE siged_r017;
DEALLOCATE PREPARE siged_r017;

SET @existe := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'cuentas_funcionario'
    AND index_name = 'idx_funcionario_delegacion_apellido'
);
SET @sql := IF(
  @existe > 0,
  'ALTER TABLE cuentas_funcionario DROP INDEX idx_funcionario_delegacion_apellido',
  'SELECT 1'
);
PREPARE siged_r017 FROM @sql;
EXECUTE siged_r017;
DEALLOCATE PREPARE siged_r017;

SET @existe := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'cuentas_funcionario'
    AND index_name = 'idx_fun_deleg_apellido'
);
SET @sql := IF(
  @existe > 0,
  'ALTER TABLE cuentas_funcionario DROP INDEX idx_fun_deleg_apellido',
  'SELECT 1'
);
PREPARE siged_r017 FROM @sql;
EXECUTE siged_r017;
DEALLOCATE PREPARE siged_r017;

ALTER TABLE cuentas_funcionario
  DROP COLUMN es_simulacion,
  DROP COLUMN apellido_materno,
  DROP COLUMN apellido_paterno,
  DROP COLUMN nombres,
  DROP COLUMN rut;

ALTER TABLE requerimientos_vecino
  DROP COLUMN es_simulacion;
