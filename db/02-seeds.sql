BEGIN;

-- Datos ficticios de ejemplo; este archivo solo se carga en desarrollo/pruebas.
INSERT INTO gc.unidades (id, condominio_id, codigo, condominio_nombre, activa)
VALUES
    ('11111111-1111-1111-1111-111111111111', '99999999-9999-9999-9999-999999999999', '101', 'Condominio Los Alerces', TRUE),
    ('22222222-2222-2222-2222-222222222222', '99999999-9999-9999-9999-999999999999', '102', 'Condominio Los Alerces', TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO gc.cargos (id, unidad_id, periodo, monto_original, saldo, vencimiento, estado)
VALUES
    ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', '2026-10', 50000, 50000, '2026-10-10', 'PENDIENTE')
ON CONFLICT (id) DO NOTHING;

-- Pagos ficticios: efectivo sin referencia, transferencia vigente con referencia y pago anulado.
INSERT INTO gc.pagos (
    id, unidad_id, condominio_id, monto, metodo_pago, referencia, residente_nombre,
    registrado_por, fecha, folio, exceso, estado,
    anulado_en, anulado_por, motivo_anulacion
)
VALUES
    (
        '44444444-4444-4444-4444-444444444444',
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999999',
        20000, 'EFECTIVO', NULL, 'Residente Demo 101',
        'ADMIN_DEMO', '2026-10-18', 'DEMO-2026-0001', 0, 'VIGENTE',
        NULL, NULL, NULL
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '11111111-1111-1111-1111-111111111111',
        '99999999-9999-9999-9999-999999999999',
        15000, 'EFECTIVO', NULL, 'Residente Demo 101',
        'ADMIN_DEMO', '2026-10-19', 'DEMO-2026-0002', 0, 'VIGENTE',
        NULL, NULL, NULL
    ),
    (
        '66666666-6666-6666-6666-666666666666',
        '22222222-2222-2222-2222-222222222222',
        '99999999-9999-9999-9999-999999999999',
        10000, 'TRANSFERENCIA', 'DEMO-REF-ANULADA', 'Residente Demo 102',
        'ADMIN_DEMO', '2026-10-20', 'DEMO-2026-0003', 0, 'ANULADO',
        '2026-10-20 12:00:00-03', 'ADMIN_DEMO', 'Anulación de demostración válida'
    ),
    (
        '77777777-7777-7777-7777-777777777777',
        '22222222-2222-2222-2222-222222222222',
        '99999999-9999-9999-9999-999999999999',
        8000, 'TRANSFERENCIA', 'DEMO-REF-VIGENTE', 'Residente Demo 102',
        'ADMIN_DEMO', '2026-10-21', 'DEMO-2026-0004', 0, 'VIGENTE',
        NULL, NULL, NULL
    )
ON CONFLICT (id) DO NOTHING;

COMMIT;
