import os
import tempfile
from pathlib import Path


class FileSystemStorage:
    """Almacenamiento en sistema de archivos con escritura atómica 
    y organización en carpetas por año."""

    def __init__(self, base_dir: str | Path = "storage") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def guardar(self, folio: str, contenido_pdf: bytes) -> str:
        # Extraer el año del folio (ej. '2026-000001' -> '2026')
        anio = folio.split("-")[0] if "-" in folio else "general"
        
        # Crear directorio por año de manera segura
        dir_anio = self.base_dir / anio
        dir_anio.mkdir(parents=True, exist_ok=True)

        nombre_archivo = f"comprobante_{folio}.pdf"
        ruta_destino = dir_anio / nombre_archivo

        # Escritura atómica: Escribir en un archivo temporal
        # En el mismo directorio y luego reemplazar
        dir_padre = ruta_destino.parent
        with tempfile.NamedTemporaryFile(dir=dir_padre, delete=False, suffix=".tmp") as tmp_file:
            tmp_file.write(contenido_pdf)
            tmp_path = Path(tmp_file.name)

        try:
            # os.replace es atómico en sistemas operativos modernos
            os.replace(tmp_path, ruta_destino)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

        # Retornar la ruta relativa normalizada
        return str(ruta_destino.relative_to(self.base_dir))