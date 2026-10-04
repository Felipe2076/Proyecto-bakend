-- Versión     : R017
-- Descripción : Revierte V017 (columnas de RUT y marca de simulación)
-- Autor       : Bakend pipi       Revisor: ramoncito
-- Requiere    : R018 aplicado antes, si V018 ya se ejecutó
-- Advertencia : borrar estas columnas elimina los RUT cargados. Respalde antes.

ALTER TABLE cuentas_funcionario
  DROP INDEX idx_funcionario_delegacion_apellido,
  DROP COLUMN es_simulacion,
  DROP COLUMN apellido_materno,
  DROP COLUMN apellido_paterno,
  DROP COLUMN nombres,
  DROP COLUMN rut;

ALTER TABLE requerimientos_vecino
  DROP COLUMN es_simulacion;
