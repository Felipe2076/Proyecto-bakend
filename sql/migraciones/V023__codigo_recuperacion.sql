-- Versión     : V023
-- Descripción : Tabla del código de recuperación (solo hash, un solo uso)
-- Autor       : Bakend pipi       Revisor: ramoncito
-- Rollback    : sql/rollback/R023__codigo_recuperacion.sql
-- Requiere    : cuentas_usuario ya creada (migraciones Django 0001 o posterior)
-- Equivale a  : cuentas/migrations/0004_codigo_recuperacion.py
--
-- V019, V019b, V019c y V021 están reservados. V020 (cuenta de vecino) y
-- V022 (MFA) ya están asignados en el plan. Este script usa V023 para no
-- ocupar esos números.

CREATE TABLE cuentas_codigorecuperacion (
  id           BIGINT       NOT NULL AUTO_INCREMENT,
  codigo_hash  VARCHAR(128) NOT NULL,
  expira       DATETIME(6)  NOT NULL,
  intentos     SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  usado        TINYINT(1)   NOT NULL DEFAULT 0,
  creado       DATETIME(6)  NOT NULL,
  usuario_id   BIGINT       NOT NULL,
  PRIMARY KEY (id),
  KEY idx_recup_usuario_usado (usuario_id, usado),
  CONSTRAINT fk_recup_usuario FOREIGN KEY (usuario_id) REFERENCES cuentas_usuario (id)
);
