# Sistema de Gestión de Gastos Comunes - Módulo de Pagos (Backend)

Este módulo implementa la lógica de negocio, persistencia, generación de comprobantes en PDF y almacenamiento atómico para el sistema de pagos de condominios, siguiendo los principios de **Clean Architecture**.

---

## 🏗️ Arquitectura y Estructura

El proyecto está organizado en capas estrictas para mantener el dominio desacoplado de los detalles de infraestructura:

```text
src/
└── condo_pagos/
    ├── domain/           # Entidades de negocio, reglas puras y Value Objects
    ├── use_cases/        # Casos de uso, puertos (interfaces) y DTOs de entrada/salida
    └── infrastructure/   # Adaptadores concretos (Base de datos SQLAlchemy, ReportLab, FileSystem)

📋 Contrato de Casos de Uso (API para la UI)
1. RegistrarPagoUseCase
Registra un nuevo pago, aplica los fondos a los cargos pendientes de una unidad, genera un snapshot inmutable, renderiza el comprobante PDF y lo almacena de forma atómica.

Entrada (RegistrarPagoCommand):

unidad_id (UUID): Identificador de la unidad inmobiliaria.

monto (Decimal): Monto total pagado.

metodo_pago (str): Método utilizado (ej. TRANSFERENCIA, EFECTIVO).

referencia (str): Código o número de comprob externo.

residente_nombre (str): Nombre de la persona que realiza el pago.

fecha (datetime): Fecha y hora del pago.

Salida (ComprobanteDTO / Snapshot):

folio (str): Identificador único del comprobante (ej. 2026-000001).

monto_pagado (Decimal): Monto registrado.

exceso (Decimal): Saldo a favor generado, si aplica.

pdf_ruta (str): Ruta relativa del archivo PDF almacenado.

Errores de Dominio Posibles:

DominioError: "Ya existe un pago registrado con esa referencia."

DominioError: "El monto excede la deuda pendiente de la unidad."

2. AnularPagoUseCase
Anula un pago registrado previamente y revierte la aplicación de los cargos asociados.

Entrada (AnularPagoCommand):

pago_id (UUID): Identificador único del pago a anular.

Salida: None

Errores de Dominio Posibles:

DominioError: "El pago no existe o ya se encuentra anulado."

🚀 Despliegue e Instalación en Servidor
1. Requisitos Previos
Python 3.11+ con gestor de paquetes uv.

PostgreSQL activo.

2. Base de Datos
Para inicializar el esquema en un servidor de producción o pruebas:

psql "$DATABASE_URL" -f docker/postgres/01-schema.sql
⚠️ IMPORTANTE: Los scripts de datos de prueba (02-seeds.sql) NUNCA deben cargarse en entornos de producción.

3. Entorno de Desarrollo con Docker
Para levantar los servicios de infraestructura necesarios localmente:

docker compose up -d db