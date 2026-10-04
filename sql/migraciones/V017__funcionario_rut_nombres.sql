-- Versión     : V017
-- Descripción : Columnas anulables de RUT, nombres y marca de simulación
-- Autor       : Bakend pipi       Revisor: ramoncito
-- MER         : v1.12 (pendiente de aporte gráfico)
-- Rollback    : sql/rollback/R017__funcionario_rut_nombres.sql
-- Requiere    : esquema creado por las migraciones Django 0001 (baseline ORM)
-- Equivale a  : cuentas/migrations/0002_funcionario_rut.py
--               requerimientos/migrations/0002_vecino_es_simulacion.py

ALTER TABLE cuentas_funcionario
  ADD COLUMN rut              VARCHAR(10) NULL AFTER codigo,
  ADD COLUMN nombres          VARCHAR(60) NULL AFTER rut,
  ADD COLUMN apellido_paterno VARCHAR(60) NULL AFTER nombres,
  ADD COLUMN apellido_materno VARCHAR(60) NULL AFTER apellido_paterno,
  ADD COLUMN es_simulacion    TINYINT(1)  NOT NULL DEFAULT 0,
  ADD INDEX idx_funcionario_delegacion_apellido (delegacion_id, apellido_paterno, nombres);

ALTER TABLE requerimientos_vecino
  ADD COLUMN es_simulacion TINYINT(1) NOT NULL DEFAULT 0;
