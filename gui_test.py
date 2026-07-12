"""Simple test GUI to verify PyQt6 is working."""

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
)
from PyQt6.QtGui import QFont

print("[GUI Test] Starting...")

app = QApplication(sys.argv)
print("[GUI Test] QApplication created")

window = QMainWindow()
window.setWindowTitle("MyCoin GUI Test")
window.setGeometry(100, 100, 500, 400)

central = QWidget()
window.setCentralWidget(central)
layout = QVBoxLayout()

title = QLabel("MyCoin Desktop GUI Test")
title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
layout.addWidget(title)

status = QTextEdit()
status.setReadOnly(True)
status.setText("""
If you see this window, PyQt6 is working!

MyCoin Desktop GUI is operational.

Next steps:
1. Make sure shared_state.py is running
2. Close this test window
3. Run: python gui_shared.py
""")
layout.addWidget(status)

btn_close = QPushButton("Close")
btn_close.clicked.connect(window.close)
layout.addWidget(btn_close)

central.setLayout(layout)

print("[GUI Test] Window created, showing...")
window.show()
print("[GUI Test] Window shown, starting event loop...")

sys.exit(app.exec())
