-- Versión     : R018
-- Descripción : Revierte la obligación de RUT y de funcionario en la cuenta
-- Autor       : Bakend pipi       Revisor: ramoncito
-- Requiere    : V018 aplicado
-- Advertencia : no restaura identidades anteriores. Eso solo lo hace el respaldo.

ALTER TABLE cuentas_usuario
  MODIFY funcionario_id BIGINT NULL;

ALTER TABLE cuentas_funcionario
  DROP CHECK ck_funcionario_rut,
  DROP INDEX uq_funcionario_rut,
  MODIFY rut VARCHAR(10) NULL,
  MODIFY nombres VARCHAR(60) NULL,
  MODIFY apellido_paterno VARCHAR(60) NULL;
