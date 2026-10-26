# Evidencia de aislamiento y arranque

## Inventario de conexiones

- `src/condo_pagos/infrastructure/database/engine.py`: contiene fábricas explícitas; no crea un engine ni una fábrica de sesiones global al importar el módulo.
- `SqlAlchemyUnitOfWork`: recibe la fábrica de sesiones por constructor.
- `src/condo_pagos/infrastructure/bootstrap.py`: raíz de composición usada por la UI real; crea y valida el engine y ofrece `cerrar()`.
- `src/condo_pagos/bootstrap.py`: raíz de composición de compatibilidad usada por pruebas del caso de uso; también inyecta sesiones y dispone el engine.
- `tests/conftest.py`: requiere `CONDO_TEST_DATABASE_URL`; crea una plantilla por sesión y una base `condo_t_<uuid>` por prueba. No tiene URL fija de respaldo.
- `.github/workflows/tests.yml`: configura `CONDO_DATABASE_URL` con una dirección deliberadamente inválida y bloquea las conexiones a `condo_test` antes de la suite. La restauración se ejecuta incluso si una etapa falla.

## Pruebas migradas y garantías

- Prueba unitaria de fábricas: verifica que el módulo no expone `engine` ni `SessionLocal` globales.
- Smoke test E2E: construye el contenedor de compatibilidad con la base privada de la prueba y lo cierra en `finally`.
- Pruebas de concurrencia: cada hilo usa una UoW/sesión independiente; las operaciones simultáneas se sincronizan con `Barrier`.
- Smoke tests de arranque: verifican que las rutas real y `--demo` muestran la ventana y cierran el contenedor al finalizar.
- El workflow repite la suite con cinco semillas aleatorias, ejecuta seeds → concurrencia → seeds, repite concurrencia 20 veces, ejecuta los archivos de integración individualmente y comprueba que no queden bases temporales.
- Ruff, mypy estricto y lint-imports se ejecutan en CI.

## Medición de duración

El workflow usa la salida de pytest para registrar duración total por comando. Para consultar los casos más lentos localmente:

```powershell
uv run pytest --durations=20
```

Las duraciones de referencia deben tomarse de la ejecución de GitHub Actions de cada commit; no se fija un umbral de tiempo porque depende del runner y de la carga del servicio PostgreSQL.

## Comprobación local de arranque

- Demo: `uv run python -m condo_pagos.main --demo`
- Aplicación real: `uv run python -m condo_pagos.main`

El modo real requiere que `CONDO_DATABASE_URL` apunte a una base con el esquema esperado. El modo demo usa datos ficticios en memoria y no necesita PostgreSQL.
