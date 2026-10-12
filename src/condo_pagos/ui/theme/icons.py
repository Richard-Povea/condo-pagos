from pathlib import Path

from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer


def obtener_icono(nombre: str, color: str = "#1B2430", tamaño: int = 20) -> QIcon:
    """Carga un archivo SVG desde recursos y aplica un color dinámico."""
    ruta_svg = Path(__file__).parent.parent / "assets" / "icons" / f"{nombre}.svg"
    
    if not ruta_svg.exists():
        # Retorna un icono vacío o por defecto si no existe el archivo físico aún
        return QIcon()

    xml_bytes = ruta_svg.read_bytes()
    # Reemplazo básico de color en SVG si se requiere tintar
    xml_str = xml_bytes.decode("utf-8").replace("currentColor", color)
    
    renderer = QSvgRenderer(QByteArray(xml_str.encode("utf-8")))
    pixmap = QPixmap(QSize(tamaño, tamaño))
    pixmap.fill(QColor("transparent"))
    
    from PySide6.QtGui import QPainter
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)