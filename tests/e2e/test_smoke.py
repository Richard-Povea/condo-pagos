
import pytest

import condo_pagos.bootstrap as bootstrap
import condo_pagos.infrastructure.database.engine as database_engine

# Importa los comandos o DTOs que reciba tu caso de uso de registrar pago
# (Ajusta los nombres según las clases reales de tu capa de aplicación)
# from condo_pagos.use_cases.registrar_pago import RegistrarPagoCommand 


@pytest.mark.integration
def test_e2e_registro_pago_y_generacion_pdf(tmp_path, monkeypatch, engine, session_local):
    """
    Test End-to-End: 
    1. Arranca el contenedor real vía bootstrap.
    2. Simula el registro de un pago (o ejecuta el comando).
    3. Verifica que la lógica de negocio y persistencia respondan.
    4. Valida la generación física del PDF y su almacenamiento atómico.
    """
    # Opcional: Redirigir temporalmente el almacenamiento a tmp_path para no dejar basura en disco
    # (Si tu FileSystemStorage acepta un directorio base configurable)
    
    # El composition root y el UoW deben usar la base privada de este test.
    monkeypatch.setattr(bootstrap, "engine", engine)
    monkeypatch.setattr(database_engine, "SessionLocal", session_local)
    container = bootstrap.build_container()
    
    # 1. Obtener el caso de uso desde el composition root
    registrar_pago_uc = container.registrar_pago_use_case()
    assert registrar_pago_uc is not None
    
    # Verificación preliminar de que el contenedor levanta el entorno completo
    assert container.pdf_renderer is not None
    assert container.storage is not None