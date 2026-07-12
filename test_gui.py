"""Simple test GUI to verify window displays"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)

window = QMainWindow()
window.setWindowTitle("MyCoin Test Window")
window.setGeometry(100, 100, 500, 300)

central = QWidget()
layout = QVBoxLayout()
layout.addWidget(QLabel("MyCoin GUI Test\n\nIf you see this, the GUI is working!"))
btn = QPushButton("Click Me")
btn.clicked.connect(lambda: print("Button clicked!"))
layout.addWidget(btn)
central.setLayout(layout)
window.setCentralWidget(central)

print("About to show window...")
window.show()
window.raise_()
window.activateWindow()
print("Window shown! Check your screen...")

sys.exit(app.exec())
