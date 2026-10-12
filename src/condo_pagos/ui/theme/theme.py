from condo_pagos.ui.theme.tokens import (
    COLOR_BACKGROUND,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_TEXT,
)


def generar_qss() -> str:
    return f"""
    QWidget {{
        background-color: {COLOR_BACKGROUND};
        color: {COLOR_TEXT};
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        font-size: 10.5pt;
    }}

    /* Tarjetas y contenedores */
    QFrame[card="true"], QGroupBox {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        margin-top: 8px;
        padding: 12px;
    }}

    /* Botones genéricos (Secundarios) */
    QPushButton {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 16px;
        font-weight: 600;
        color: {COLOR_TEXT};
        min-height: 24px;
    }}

    QPushButton:hover {{
        background-color: {COLOR_BACKGROUND};
        border-color: {COLOR_PRIMARY};
    }}

    QPushButton:pressed {{
        background-color: {COLOR_BORDER};
    }}

    /* Variantes de Botón */
    QPushButton[variant="primary"] {{
        background-color: {COLOR_PRIMARY};
        color: #FFFFFF;
        border: none;
    }}
    QPushButton[variant="primary"]:hover {{
        background-color: #172b46;
    }}

    QPushButton[variant="danger"] {{
        background-color: {COLOR_DANGER};
        color: #FFFFFF;
        border: none;
    }}
    QPushButton[variant="danger"]:hover {{
        background-color: #a72222;
    }}

    QPushButton[variant="text"] {{
        background-color: transparent;
        border: none;
        color: {COLOR_PRIMARY};
    }}
    QPushButton[variant="text"]:hover {{
        background-color: {COLOR_BORDER};
    }}

    /* Entradas de texto y controles */
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