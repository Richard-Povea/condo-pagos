-- Migración manual para bases creadas antes de que fecha y fecha_emision fueran DATE.
-- Conserva el día calendario de Chile al convertir valores TIMESTAMPTZ existentes.
-- Ejecutar una sola vez contra la base de datos correspondiente.

BEGIN;

ALTER TABLE gc.pagos
    ALTER COLUMN fecha TYPE DATE
    USING (fecha AT TIME ZONE 'America/Santiago')::date;

ALTER TABLE gc.comprobantes
    ALTER COLUMN fecha_emision TYPE DATE
    USING (fecha_emision AT TIME ZONE 'America/Santiago')::date;

COMMIT;
