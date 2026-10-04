-- Versión     : V018
-- Descripción : RUT obligatorio, único y con formato; toda cuenta tiene funcionario
-- Autor       : Bakend pipi       Revisor: ramoncito
-- MER         : v1.13 (pendiente de aporte gráfico)
-- Rollback    : sql/rollback/R018__rut_obligatorio.sql
-- Requiere    : V017 y D003 (cero funcionarios sin RUT)
-- Equivale a  : cuentas/migrations/0003_rut_obligatorio.py
-- Nota        : el índice de Django se llama idx_fun_deleg_apellido (límite de 30
--               caracteres del ORM). En MySQL el script conserva el nombre del plan.

ALTER TABLE cuentas_funcionario
  MODIFY rut VARCHAR(10) NOT NULL,
  MODIFY nombres VARCHAR(60) NOT NULL,
  MODIFY apellido_paterno VARCHAR(60) NOT NULL,
  ADD CONSTRAINT uq_funcionario_rut UNIQUE (rut),
  ADD CONSTRAINT ck_funcionario_rut CHECK (REGEXP_LIKE(rut, '^[0-9]{7,8}-[0-9K]$', 'c'));

ALTER TABLE cuentas_usuario
  MODIFY funcionario_id BIGINT NOT NULL;
