from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt


class BaseTableModel(QAbstractTableModel):
    def __init__(
            self, 
            headers: list[str], 
            datos: list[list], 
            alinear_derecha: set[int] | None = None) -> None:
        super().__init__()
        self._headers = headers
        self._datos = datos
        self._alinear_derecha = alinear_derecha or set()

    def rowCount(
            self, 
            parent: QModelIndex | QPersistentModelIndex | None = None
            ) -> int:
        return len(self._datos)

    def columnCount(
            self,
            parent: QModelIndex | QPersistentModelIndex | None = None
            ) -> int:
        return len(self._headers)

    def headerData(
            self, 
            section: int, 
            orientation: Qt.Orientation, 
            role: int = Qt.ItemDataRole.DisplayRole
            ):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return None

    def data(
            self, 
            index: QModelIndex | QPersistentModelIndex, 
            role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        fila, col = index.row(), index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._datos[fila][col]
        
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in self._alinear_derecha:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            
        return None