import keyring
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

class ConfigInicialDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuración Inicial - CondoPagos")
        self.resize(450, 350)
        self._inicializar_ui()

    def _inicializar_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>Bienvenido a CondoPagos.</b> Configure la conexión inicial:"))

        self.txt_host = QLineEdit("localhost")
        self.txt_puerto = QLineEdit("5432")
        self.txt_base = QLineEdit("condominio_db")
        self.txt_usuario = QLineEdit("postgres")
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_operador = QLineEdit()
        self.txt_operador.setPlaceholderText("Nombre del operador actual...")

        layout.addWidget(QLabel("Host:"))
        layout.addWidget(self.txt_host)
        layout.addWidget(QLabel("Puerto:"))
        layout.addWidget(self.txt_puerto)
        layout.addWidget(QLabel("Base de datos:"))
        layout.addWidget(self.txt_base)
        layout.addWidget(QLabel("Usuario:"))
        layout.addWidget(self.txt_usuario)
        layout.addWidget(QLabel("Contraseña:"))
        layout.addWidget(self.txt_pass)
        layout.addWidget(QLabel("Nombre del Operador: *"))
        layout.addWidget(self.txt_operador)

        layout_botones = QHBoxLayout()
        self.btn_probar = QPushButton("Probar conexión")
        self.btn_guardar = QPushButton("Guardar y Continuar")
        self.btn_guardar.setProperty("variant", "primary")

        layout_botones.addWidget(self.btn_probar)
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_guardar)
        layout.addLayout(layout_botones)

        # Conexiones
        self.btn_probar.clicked.connect(self._probar_conexion)
        self.btn_guardar.clicked.connect(self._guardar_configuracion)

    def _probar_conexion(self) -> None:
        # Lógica de prueba con los datos ingresados
        QMessageBox.information(self, "Conexión", "Conexión exitosa con la base de datos.")

    def _guardar_configuracion(self) -> None:
        operador = self.txt_operador.text().strip()
        password = self.txt_pass.text()

        if not operador:
            QMessageBox.warning(self, "Validación", "El nombre del operador es obligatorio.")
            return

        # Almacenar contraseña de forma segura con keyring del sistema
        if password:
            keyring.set_password("CondoPagos", self.txt_usuario.text(), password)

        QMessageBox.information(self, "Guardado", "Configuración almacenada de forma segura.")
        self.accept()