BEGIN;

CREATE SCHEMA IF NOT EXISTS gc;

-- Enums del dominio
DO $$ BEGIN
    CREATE TYPE gc.estado_cargo_enum AS ENUM ('PENDIENTE', 'PAGADO', 'ANULADO');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE gc.estado_pago_enum AS ENUM ('VIGENTE', 'ANULADO');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Control de versión del esquema
CREATE TABLE IF NOT EXISTS gc.schema_info (
    version INT NOT NULL
);

INSERT INTO gc.schema_info (version)
SELECT 2 WHERE NOT EXISTS (SELECT 1 FROM gc.schema_info);
UPDATE gc.schema_info SET version = 2;

-- Tablas del sistema
CREATE TABLE IF NOT EXISTS gc.unidades (
    id UUID PRIMARY KEY,
    condominio_id UUID NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    condominio_nombre VARCHAR(255) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS gc.cargos (
    id UUID PRIMARY KEY,
    unidad_id UUID NOT NULL REFERENCES gc.unidades(id),
    periodo VARCHAR(7) NOT NULL,
    monto_original NUMERIC(12, 0) NOT NULL,
    saldo NUMERIC(12, 0) NOT NULL,
    vencimiento DATE NOT NULL,
    estado gc.estado_cargo_enum NOT NULL DEFAULT 'PENDIENTE'
);

CREATE INDEX IF NOT EXISTS idx_cargos_unidad_saldo ON gc.cargos(unidad_id, saldo);

CREATE TABLE IF NOT EXISTS gc.pagos (
    id UUID PRIMARY KEY,
    unidad_id UUID NOT NULL REFERENCES gc.unidades(id),
    monto NUMERIC(12, 0) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    referencia VARCHAR(100),
    residente_nombre VARCHAR(255) NOT NULL,
    registrado_por VARCHAR(80) NOT NULL,
    fecha DATE NOT NULL,
    folio VARCHAR(20) NOT NULL,
    exceso NUMERIC(12, 0) NOT NULL DEFAULT 0,
    estado gc.estado_pago_enum NOT NULL DEFAULT 'VIGENTE'
);

-- La referencia solo debe ser única entre pagos vigentes y no nulos.
ALTER TABLE gc.pagos DROP CONSTRAINT IF EXISTS uq_pagos_referencia;
DROP INDEX IF EXISTS gc.uq_pagos_referencia;
CREATE UNIQUE INDEX uq_pagos_referencia
    ON gc.pagos (unidad_id, metodo_pago, referencia)
    WHERE referencia IS NOT NULL AND estado = 'VIGENTE';

CREATE TABLE IF NOT EXISTS gc.folios_secuencia (
    anio VARCHAR(4) PRIMARY KEY,
    ultimo_numero INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gc.comprobantes (
    folio VARCHAR(20) PRIMARY KEY,
    fecha_emision DATE NOT NULL,
    unidad_id UUID NOT NULL,
    residente_nombre VARCHAR(255) NOT NULL,
    monto_pagado NUMERIC(12, 0) NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    exceso NUMERIC(12, 0) NOT NULL,
    hash_anterior VARCHAR(64),
    hash_sha256 VARCHAR(64) NOT NULL,
    pdf_ruta TEXT,
    datos_json JSONB NOT NULL
);

-- Trigger para garantizar la inmutabilidad de los comprobantes
CREATE OR REPLACE FUNCTION gc.fn_prevenir_modificacion_comprobante()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Los comprobantes emitidos son inmutables y no pueden ser modificados.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_comprobantes_inmutables ON gc.comprobantes;
CREATE TRIGGER trg_comprobantes_inmutables
BEFORE UPDATE ON gc.comprobantes
FOR EACH ROW
EXECUTE FUNCTION gc.fn_prevenir_modificacion_comprobante();

COMMIT;