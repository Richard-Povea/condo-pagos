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

DO $$ BEGIN
    CREATE TYPE gc.metodo_pago_enum AS ENUM ('EFECTIVO', 'TRANSFERENCIA', 'TARJETA');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Control de versión del esquema: v2 no se ha desplegado y solo se usa en desarrollo.
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
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_unidades_id_condominio UNIQUE (id, condominio_id)
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
    condominio_id UUID NOT NULL,
    monto NUMERIC(12, 0) NOT NULL,
    metodo_pago gc.metodo_pago_enum NOT NULL,
    referencia VARCHAR(100),
    residente_nombre VARCHAR(255) NOT NULL,
    registrado_por VARCHAR(80) NOT NULL,
    fecha DATE NOT NULL,
    folio VARCHAR(20) NOT NULL,
    exceso NUMERIC(12, 0) NOT NULL DEFAULT 0,
    estado gc.estado_pago_enum NOT NULL DEFAULT 'VIGENTE',
    anulado_en TIMESTAMPTZ,
    anulado_por VARCHAR(80),
    motivo_anulacion VARCHAR(300),
    CONSTRAINT fk_pagos_unidad_condominio
        FOREIGN KEY (unidad_id, condominio_id)
        REFERENCES gc.unidades (id, condominio_id),
    CONSTRAINT uq_pagos_id_condominio UNIQUE (id, condominio_id),
    CONSTRAINT ck_pagos_referencia_requerida CHECK (
        metodo_pago <> 'TRANSFERENCIA' OR referencia IS NOT NULL
    ),
    CONSTRAINT ck_pagos_referencia_no_vacia CHECK (
        referencia IS NULL OR length(btrim(referencia)) > 0
    ),
    CONSTRAINT ck_pagos_anulacion CHECK (
        (estado = 'ANULADO'
            AND anulado_en IS NOT NULL
            AND anulado_por IS NOT NULL
            AND length(btrim(motivo_anulacion)) >= 10)
        OR
        (estado <> 'ANULADO'
            AND anulado_en IS NULL
            AND anulado_por IS NULL
            AND motivo_anulacion IS NULL)
    )
);

-- La referencia es única por condominio y método, solo entre pagos vigentes.
CREATE UNIQUE INDEX uq_pagos_referencia
    ON gc.pagos (condominio_id, metodo_pago, referencia)
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
    hash_anterior CHAR(64),
    hash_sha256 CHAR(64) NOT NULL,
    pdf_ruta TEXT,
    datos_json JSONB NOT NULL
);

-- El snapshot y los hashes del comprobante son inmutables.
-- pdf_ruta puede actualizarse para registrar la ubicación del PDF regenerado.
CREATE OR REPLACE FUNCTION gc.fn_prevenir_modificacion_comprobante()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.folio IS DISTINCT FROM OLD.folio
       OR NEW.fecha_emision IS DISTINCT FROM OLD.fecha_emision
       OR NEW.unidad_id IS DISTINCT FROM OLD.unidad_id
       OR NEW.residente_nombre IS DISTINCT FROM OLD.residente_nombre
       OR NEW.monto_pagado IS DISTINCT FROM OLD.monto_pagado
       OR NEW.metodo_pago IS DISTINCT FROM OLD.metodo_pago
       OR NEW.exceso IS DISTINCT FROM OLD.exceso
       OR NEW.hash_anterior IS DISTINCT FROM OLD.hash_anterior
       OR NEW.hash_sha256 IS DISTINCT FROM OLD.hash_sha256
       OR NEW.datos_json IS DISTINCT FROM OLD.datos_json THEN
        RAISE EXCEPTION 'El folio, snapshot y hashes del comprobante son inmutables.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_comprobantes_inmutables ON gc.comprobantes;
CREATE TRIGGER trg_comprobantes_inmutables
BEFORE UPDATE ON gc.comprobantes
FOR EACH ROW
EXECUTE FUNCTION gc.fn_prevenir_modificacion_comprobante();

COMMIT;
