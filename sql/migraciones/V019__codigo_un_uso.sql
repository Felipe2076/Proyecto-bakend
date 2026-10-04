-- Versión     : V019
-- Descripción : Tabla codigo_un_uso (hash HMAC de un código de un solo uso)
-- Autor       : Bakend pipi       Revisor: ramoncito
-- MER         : v1.15 (pendiente de aporte gráfico)
-- Rollback    : sql/rollback/R019__codigo_un_uso.sql
-- Requiere    : V018
-- Equivale a  : cuentas/migrations/0004_codigo_un_uso.py

CREATE TABLE codigo_un_uso (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  proposito VARCHAR(20) NOT NULL,
  usuario_id BIGINT NULL,
  cuenta_vecino_id BIGINT UNSIGNED NULL,
  codigo_hash CHAR(64) NOT NULL,
  canal VARCHAR(10) NOT NULL DEFAULT 'CORREO',
  destino_mascara VARCHAR(80) NULL,
  expira_en DATETIME NOT NULL,
  intentos TINYINT UNSIGNED NOT NULL DEFAULT 0,
  usado_en DATETIME NULL,
  anulado_en DATETIME NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ip_origen VARCHAR(45) NULL,
  INDEX idx_codigo_dueno (usuario_id, proposito, creado_en),
  INDEX idx_codigo_vecino (cuenta_vecino_id, proposito, creado_en),
  INDEX idx_codigo_expira (expira_en),
  CONSTRAINT fk_codigo_usuario FOREIGN KEY (usuario_id) REFERENCES cuentas_usuario(id) ON DELETE CASCADE,
  CONSTRAINT ck_codigo_intentos CHECK (intentos <= 5),
  CONSTRAINT ck_codigo_proposito CHECK (proposito IN ('RECUPERAR_CLAVE','MFA_EMAIL','LOGIN_VECINO','VERIFICAR_CORREO')),
  CONSTRAINT ck_codigo_canal CHECK (canal IN ('CORREO','SMS'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
