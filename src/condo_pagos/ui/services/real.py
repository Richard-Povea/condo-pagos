from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox


class ServicioDialogosReal:
    def confirmar(self, titulo: str, texto: str, peligro: bool = False) -> bool:
        msg = QMessageBox()
        msg.setWindowTitle(titulo)
        msg.setText(texto)
        msg.setIcon(QMessageBox.Icon.Warning if peligro else QMessageBox.Icon.Question)
        btn_si = msg.addButton("Sí", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        return msg.clickedButton() == btn_si

class AbridorArchivosReal:
    def abrir(self, ruta: Path | str) -> None:
        url = QUrl.fromLocalFile(str(ruta))
        QDesktopServices.openUrl(url)