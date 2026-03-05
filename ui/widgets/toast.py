"""Toast notification widget."""
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class Toast(QFrame):
    """Toast notification with fade-in."""

    def __init__(self, message: str, parent=None, duration: int = 3000):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet("""
            QFrame#toast {
                background-color: #2d2d30;
                border: 1px solid #8b3a3a;
                border-radius: 10px;
                padding: 14px 20px;
            }
            QLabel { color: #e8e8e8; font-size: 13px; }
        """)

        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(duration)
