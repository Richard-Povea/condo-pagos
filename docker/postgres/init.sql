-- Esquema + seeds de desarrollo. RUT y datos ficticios.
BEGIN;
CREATE SCHEMA IF NOT EXISTS gc;
SET search_path TO gc, public;

-- ───────── Tipos ─────────
CREATE TYPE metodo_pago        AS ENUM ('EFECTIVO','TRANSFERENCIA','CHEQUE','TARJETA','OTRO');
CREATE TYPE estado_pago        AS ENUM ('REGISTRADO','ANULADO');
CREATE TYPE estado_cargo       AS ENUM ('PENDIENTE','PARCIAL','PAGADO','ANULADO');
CREATE TYPE estado_periodo     AS ENUM ('ABIERTO','EMITIDO','CERRADO');
CREATE TYPE estado_comprobante AS ENUM ('EMITIDO','ANULADO');

-- ───────── Maestros ─────────
CREATE TABLE condominios (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rut       VARCHAR(12)  NOT NULL UNIQUE,
    nombre    VARCHAR(120) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    moneda    CHAR(3)      NOT NULL DEFAULT 'CLP',
    creado_en TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE unidades (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    condominio_id BIGINT      NOT NULL REFERENCES condominios(id),
    codigo        VARCHAR(20) NOT NULL,
    tipo          VARCHAR(20) NOT NULL DEFAULT 'DEPARTAMENTO'
                  CHECK (tipo IN ('DEPARTAMENTO','CASA','BODEGA','ESTACIONAMIENTO','LOCAL')),
    alicuota      NUMERIC(8,6) NOT NULL CHECK (alicuota > 0 AND alicuota <= 1),
    activa        BOOLEAN     NOT NULL DEFAULT TRUE,
    UNIQUE (condominio_id, codigo),
    UNIQUE (id, condominio_id)
);

CREATE TABLE personas (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rut             VARCHAR(12) UNIQUE,
    nombre_completo VARCHAR(160) NOT NULL,
    email           VARCHAR(160),
    telefono        VARCHAR(30),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE unidad_personas (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unidad_id        BIGINT NOT NULL REFERENCES unidades(id),
    persona_id       BIGINT NOT NULL REFERENCES personas(id),
    rol              VARCHAR(15) NOT NULL CHECK (rol IN ('PROPIETARIO','ARRENDATARIO','RESIDENTE')),
    responsable_pago BOOLEAN NOT NULL DEFAULT FALSE,
    vigente_desde    DATE NOT NULL DEFAULT CURRENT_DATE,
    vigente_hasta    DATE,
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde)
);
CREATE UNIQUE INDEX uq_unidad_responsable_vigente
    ON unidad_personas (unidad_id) WHERE responsable_pago AND vigente_hasta IS NULL;
CREATE INDEX ix_unidad_personas_persona ON unidad_personas (persona_id);

-- ───────── Emisión de gastos comunes ─────────
CREATE TABLE periodos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    condominio_id     BIGINT   NOT NULL REFERENCES condominios(id),
    anio              SMALLINT NOT NULL CHECK (anio BETWEEN 2000 AND 2100),
    mes               SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    fecha_emision     DATE     NOT NULL,
    fecha_vencimiento DATE     NOT NULL,
    estado            estado_periodo NOT NULL DEFAULT 'ABIERTO',
    CHECK (fecha_vencimiento >= fecha_emision),
    UNIQUE (condominio_id, anio, mes)
);

CREATE TABLE gastos_periodo (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    periodo_id BIGINT NOT NULL REFERENCES periodos(id),
    concepto   VARCHAR(120) NOT NULL,
    tipo       VARCHAR(15)  NOT NULL CHECK (tipo IN ('ORDINARIO','EXTRAORDINARIO','FONDO_RESERVA')),
    monto      NUMERIC(14,2) NOT NULL CHECK (monto >= 0)
);

CREATE TABLE cargos (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    periodo_id   BIGINT NOT NULL REFERENCES periodos(id),
    unidad_id    BIGINT NOT NULL REFERENCES unidades(id),
    monto_total  NUMERIC(14,2) NOT NULL CHECK (monto_total >= 0),
    monto_pagado NUMERIC(14,2) NOT NULL DEFAULT 0,
    estado       estado_cargo  NOT NULL DEFAULT 'PENDIENTE',
    UNIQUE (periodo_id, unidad_id),
    CHECK (monto_pagado >= 0 AND monto_pagado <= monto_total)
);
CREATE INDEX ix_cargos_unidad_pendiente
    ON cargos (unidad_id) WHERE estado IN ('PENDIENTE','PARCIAL');

CREATE TABLE cargo_detalles (            -- snapshot del prorrateo por concepto
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cargo_id         BIGINT NOT NULL REFERENCES cargos(id),
    gasto_periodo_id BIGINT REFERENCES gastos_periodo(id),
    concepto         VARCHAR(120) NOT NULL,
    monto            NUMERIC(14,2) NOT NULL
);
CREATE INDEX ix_cargo_detalles_cargo ON cargo_detalles (cargo_id);

-- ───────── Pagos y comprobantes ─────────
CREATE TABLE pagos (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    condominio_id      BIGINT NOT NULL,
    unidad_id          BIGINT NOT NULL,
    persona_id         BIGINT REFERENCES personas(id),
    fecha_pago         DATE   NOT NULL,
    monto              NUMERIC(14,2) NOT NULL CHECK (monto > 0),
    metodo             metodo_pago NOT NULL,
    referencia         VARCHAR(60),
    estado             estado_pago NOT NULL DEFAULT 'REGISTRADO',
    observacion        VARCHAR(300),
    registrado_por     VARCHAR(80) NOT NULL,
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
    anulado_en         TIMESTAMPTZ,
    motivo_anulacion   VARCHAR(300),
    FOREIGN KEY (unidad_id, condominio_id) REFERENCES unidades (id, condominio_id),
    UNIQUE (id, condominio_id),
    CHECK ((estado = 'ANULADO') = (anulado_en IS NOT NULL))
);
CREATE INDEX ix_pagos_unidad_fecha ON pagos (unidad_id, fecha_pago DESC);
CREATE UNIQUE INDEX uq_pagos_referencia
    ON pagos (condominio_id, metodo, referencia)
    WHERE referencia IS NOT NULL AND estado = 'REGISTRADO';

CREATE TABLE pago_aplicaciones (          -- a qué cargos se imputó cada pago
    pago_id  BIGINT NOT NULL REFERENCES pagos(id),
    cargo_id BIGINT NOT NULL REFERENCES cargos(id),
    monto    NUMERIC(14,2) NOT NULL CHECK (monto > 0),
    PRIMARY KEY (pago_id, cargo_id)
);
CREATE INDEX ix_aplicaciones_cargo ON pago_aplicaciones (cargo_id);

CREATE TABLE folio_secuencias (
    condominio_id BIGINT   NOT NULL REFERENCES condominios(id),
    anio          SMALLINT NOT NULL,
    ultimo_folio  INTEGER  NOT NULL DEFAULT 0 CHECK (ultimo_folio >= 0),
    PRIMARY KEY (condominio_id, anio)
);

CREATE TABLE comprobantes (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pago_id        BIGINT   NOT NULL UNIQUE,
    condominio_id  BIGINT   NOT NULL,
    anio           SMALLINT NOT NULL,
    folio          INTEGER  NOT NULL CHECK (folio > 0),
    estado         estado_comprobante NOT NULL DEFAULT 'EMITIDO',
    emitido_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    datos_snapshot JSONB    NOT NULL,
    hash_sha256    CHAR(64) NOT NULL,
    pdf_ruta       TEXT,
    FOREIGN KEY (pago_id, condominio_id) REFERENCES pagos (id, condominio_id),
    UNIQUE (condominio_id, anio, folio)
);

CREATE FUNCTION trg_comprobante_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.folio <> OLD.folio OR NEW.anio <> OLD.anio
       OR NEW.datos_snapshot <> OLD.datos_snapshot OR NEW.hash_sha256 <> OLD.hash_sha256 THEN
        RAISE EXCEPTION 'Folio, snapshot y hash de un comprobante son inmutables';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER comprobante_inmutable BEFORE UPDATE ON comprobantes
    FOR EACH ROW EXECUTE FUNCTION trg_comprobante_inmutable();

-- ───────── Seeds ─────────
DO $$
DECLARE
    v_condo BIGINT;
    v_per   BIGINT;
    r       RECORD;
BEGIN
    INSERT INTO condominios (rut, nombre, direccion)
    VALUES ('76.123.456-7', 'Condominio Los Alerces', 'Av. Los Robles 1234, Valdivia')
    RETURNING id INTO v_condo;

    INSERT INTO unidades (condominio_id, codigo, alicuota) VALUES
        (v_condo, '101', 0.150000), (v_condo, '102', 0.150000),
        (v_condo, '201', 0.180000), (v_condo, '202', 0.180000),
        (v_condo, '301', 0.170000), (v_condo, '302', 0.170000);   -- Σ = 1.000000

    INSERT INTO personas (rut, nombre_completo, email) VALUES
        ('11.111.111-1', 'María Fernández Soto',  'maria.fernandez@example.com'),
        ('12.345.678-5', 'Jorge Alvarado Pérez',  'jorge.alvarado@example.com'),
        ('14.222.333-4', 'Camila Rojas Muñoz',    'camila.rojas@example.com'),
        ('15.444.555-6', 'Andrés Navarro Díaz',   'andres.navarro@example.com'),
        ('16.666.777-8', 'Valentina Soto Vera',   'valentina.soto@example.com'),
        ('17.888.999-0', 'Felipe Contreras Gil',  'felipe.contreras@example.com');

    INSERT INTO unidad_personas (unidad_id, persona_id, rol, responsable_pago)
    SELECT u.id, p.id, 'PROPIETARIO', TRUE
    FROM (VALUES ('101','11.111.111-1'), ('102','12.345.678-5'), ('201','14.222.333-4'),
                 ('202','15.444.555-6'), ('301','16.666.777-8'), ('302','17.888.999-0'))
         AS m(codigo, rut)
    JOIN unidades u ON u.codigo = m.codigo AND u.condominio_id = v_condo
    JOIN personas p ON p.rut = m.rut;

    -- Dos períodos emitidos (sep y oct 2026) para probar imputación al cargo más antiguo
    FOR r IN SELECT * FROM (VALUES
                (9,  DATE '2026-09-01', DATE '2026-09-10', 1.00),
                (10, DATE '2026-10-01', DATE '2026-10-10', 1.02)
             ) AS t(mes, emi, ven, factor)
    LOOP
        INSERT INTO periodos (condominio_id, anio, mes, fecha_emision, fecha_vencimiento, estado)
        VALUES (v_condo, 2026, r.mes, r.emi, r.ven, 'EMITIDO')
        RETURNING id INTO v_per;

        INSERT INTO gastos_periodo (periodo_id, concepto, tipo, monto)
        SELECT v_per, g.concepto, g.tipo, round(g.monto * r.factor, 0)
        FROM (VALUES ('Remuneraciones personal',      'ORDINARIO',     1200000),
                     ('Consumo de agua',              'ORDINARIO',      450000),
                     ('Electricidad áreas comunes',   'ORDINARIO',      180000),
                     ('Mantención ascensor',          'ORDINARIO',      220000),
                     ('Fondo de reserva',             'FONDO_RESERVA',  102500))
             AS g(concepto, tipo, monto);

        INSERT INTO cargos (periodo_id, unidad_id, monto_total)
        SELECT v_per, u.id, 0 FROM unidades u WHERE u.condominio_id = v_condo;

        INSERT INTO cargo_detalles (cargo_id, gasto_periodo_id, concepto, monto)
        SELECT c.id, g.id, g.concepto, round(g.monto * u.alicuota, 0)
        FROM cargos c
        JOIN unidades u       ON u.id = c.unidad_id
        JOIN gastos_periodo g ON g.periodo_id = c.periodo_id
        WHERE c.periodo_id = v_per;

        UPDATE cargos c
        SET monto_total = (SELECT COALESCE(sum(d.monto), 0) FROM cargo_detalles d WHERE d.cargo_id = c.id)
        WHERE c.periodo_id = v_per;
    END LOOP;
END $$;

COMMIT;