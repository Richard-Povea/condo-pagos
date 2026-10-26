# App de gestión de pagos de condominios

Primera etapa funcional del módulo de pagos: consulta de unidades y deuda, registro y anulación de pagos, y emisión o regeneración de comprobantes PDF desde un snapshot persistido.

## Alcance funcional

- Consultar unidades y cargos pendientes.
- Registrar pagos y aplicar el monto a los cargos pendientes.
- Emitir y regenerar el comprobante PDF desde el snapshot guardado.
- Anular pagos con operador, fecha y motivo de auditoría; la anulación revierte la aplicación del pago.
- Persistir pagos y comprobantes en PostgreSQL.

## Reglas de pagos

- Los valores admitidos por el esquema son `EFECTIVO`, `TRANSFERENCIA` y `TARJETA`.
- En esta primera etapa de operación solo están habilitados `EFECTIVO` y `TRANSFERENCIA`; `TARJETA` queda reservado para una etapa posterior.
- El pago en efectivo puede registrarse sin referencia.
- La transferencia debe tener una referencia no vacía (por ejemplo, el número de operación).
- La referencia de una transferencia debe ser única para el mismo condominio y método entre pagos vigentes. Una referencia puede reutilizarse tras anular el pago, y puede existir en otro condominio.
- Antes de registrar una transferencia, el operador debe confirmar que el abono aparece en la cuenta bancaria. Esta aplicación no realiza conciliación bancaria.
- Cada pago registra quién lo ingresó. Las anulaciones conservan quién la realizó, cuándo y el motivo.
- Los comprobantes conservan su folio, snapshot y hashes. El archivo PDF puede regenerarse desde el snapshot; no se adjunta evidencia bancaria.
- No se eliminan pagos para corregir errores: se anulan con un motivo justificable.

## Arquitectura

El código se organiza por capas: `domain/` para entidades y reglas de negocio, `use_cases/` para casos de uso y puertos, `infrastructure/` para PostgreSQL, PDF y adaptadores, y `ui/` para la interfaz de escritorio. La composición de producción se centraliza en `condo_pagos.bootstrap`.

## Requisitos

- Python 3.13 (configurado en CI).
- `uv`.
- Docker y Docker Compose.
- PostgreSQL 16 (se proporciona mediante Compose).

## Desarrollo local

Levantar la base de desarrollo:

```powershell
docker compose up -d --wait db
```

Levantar la base de integración:

```powershell
docker compose --profile test up -d --wait db_test
```

Las bases se inicializan con `db/01-schema.sql` y `db/02-seeds.sql`. Los seeds contienen datos ficticios y solo deben usarse en desarrollo y pruebas, nunca en producción.

Ejecutar las pruebas y verificaciones:

```powershell
uv run pytest
uv run ruff check .
uv run mypy --strict src
uv run lint-imports
```

Para probar la integración PostgreSQL, configurar `CONDO_TEST_DATABASE_URL` según las variables de entorno del servicio `db_test`.

## Estado de esta entrega

Esta etapa no incluye habilitar pagos con tarjeta, adjuntar comprobantes bancarios, conciliar movimientos bancarios ni administrar todos los aspectos del condominio. La entrega se considera candidata a primera versión cuando CI complete satisfactoriamente las pruebas y verificaciones descritas.
