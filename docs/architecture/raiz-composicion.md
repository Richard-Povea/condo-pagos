# Raíz única de composición

La construcción del contenedor de producción vive en
`src/condo_pagos/bootstrap.py`. El punto de entrada `main.py` selecciona
el contenedor real o el de demostración; la UI consume los contratos definidos
en `condo_pagos.ui.ports` y no construye infraestructura.

## Protecciones conservadas

| Protección | Implementación | Verificación esperada |
| --- | --- | --- |
| Validación de esquema | `verificar_esquema(self._engine)` durante la construcción | La app falla temprano ante un esquema incompatible y libera el engine |
| Pool y timeout | `crear_engine` configura pool, `pool_pre_ping` y `connect_timeout=5` | Pruebas de fábrica de engine y revisión de configuración |
| Reloj y zona horaria | `Settings.zona_horaria` se configura con `CONDO_TIMEZONE`; el reloj se inyecta al repositorio de folios | Prueba determinista de zona horaria y año del folio |
| Adaptadores de UI | `PostgresContainer` expone consultas, registro, historial, anulación y emisión de PDF | Contrato compartido para registrar pago y consultar historial |
| Cierre de recursos | `PostgresContainer.cerrar()` llama a `Engine.dispose()`; el arranque lo ejecuta en `finally` | Pruebas de ciclo de vida y contenedor de integración |
| Directorio PDF | Se crea y se comprueba al construir el contenedor; si no se puede escribir se registra una advertencia | Prueba de emisión PDF en directorio temporal |
| Contraseña en logs | La URL se registra con `render_as_string(hide_password=True)` | Revisión del mensaje de logging: la contraseña no debe aparecer |

## Reglas de arquitectura

- Solo `src/condo_pagos/main.py` importa la raíz `condo_pagos.bootstrap`.
  Los tests pueden importarla para construir el contenedor real.
- Existe una sola definición de `build_container` dentro de `src`.
- Las vistas y componentes de UI no importan infraestructura ni la raíz de
  composición; usan ViewModels y contratos.
- Los tests que necesitan el contenedor real usan el fixture `container_real`,
  que construye la composición pública sobre una base de datos privada y cierra
  el contenedor al finalizar.
- El contrato común de registro e historial se ejecuta contra `InMemoryContainer`
  y contra el contenedor PostgreSQL real.
