# Colores del sistema basados en la paleta solicitada
COLOR_PRIMARY = "#1F3A5F"     # Azul principal (mismo del PDF)
COLOR_BACKGROUND = "#F5F7FA"  # Fondo general
COLOR_SURFACE = "#FFFFFF"     # Tarjetas y contenedores
COLOR_TEXT = "#1B2430"        # Texto principal
COLOR_SECONDARY = "#6B7785"   # Texto secundario / subtítulos
COLOR_BORDER = "#E1E6EC"      # Bordes suaves
COLOR_SUCCESS = "#2E7D32"     # Éxito
COLOR_WARNING = "#B26A00"     # Advertencia
COLOR_DANGER = "#C62828"      # Peligro / acciones destructivas

# Estilos globales y hoja de estilos de la aplicación (QSS)
GLOBAL_STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT};
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 10.5pt;
}}

/* Tarjetas y contenedores con esquinas redondeadas de 8px */
QFrame[card="true"], QGroupBox {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    margin-top: 8px;
    padding: 12px;
}}

/* Botones genéricos */
QPushButton {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
    color: {COLOR_TEXT};
}}

QPushButton:hover {{
    background-color: {COLOR_BACKGROUND};
    border-color: {COLOR_PRIMARY};
}}

QPushButton:pressed {{
    background-color: {COLOR_BORDER};
}}

/* Botón Variante Primaria */
QPushButton[variant="primary"] {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: none;
}}

QPushButton[variant="primary"]:hover {{
    background-color: #172b46;
}}

/* Botón Variante Peligro (acciones destructivas) */
QPushButton[variant="danger"] {{
    background-color: {COLOR_DANGER};
    color: #FFFFFF;
    border: none;
}}

QPushButton[variant="danger"]:hover {{
    background-color: #a72222;
}}

/* Entradas de texto */
QLineEdit, QComboBox, QDateEdit {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {COLOR_PRIMARY};
}}

QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}
"""