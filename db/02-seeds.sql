BEGIN;

-- Datos de ejemplo para desarrollo y pruebas locales
INSERT INTO gc.unidades (id, condominio_id, codigo, condominio_nombre, activa)
VALUES 
    ('11111111-1111-1111-1111-111111111111', '99999999-9999-9999-9999-999999999999', '101', 'Condominio Los Alerces', TRUE),
    ('22222222-2222-2222-2222-222222222222', '99999999-9999-9999-9999-999999999999', '102', 'Condominio Los Alerces', TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO gc.cargos (id, unidad_id, periodo, monto_original, saldo, vencimiento, estado)
VALUES 
    ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '2026-10', 50000, 50000, '2026-10-10', 'PENDIENTE')
ON CONFLICT (id) DO NOTHING;

COMMIT;