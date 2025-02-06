"""
Module Name: main_menu.py
Description: The main landing page with Create Account and Login buttons
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class MainMenu(QWidget):
    def __init__(self, parent=None):
        super(MainMenu, self).__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)

        # Title label
        title_label = QLabel("Welcome to Chat Service")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Helvetica", 24, QFont.Bold)
        title_label.setFont(title_font)
        # Use a QSS style for a modern look:
        title_label.setStyleSheet("background-color: transparent; color: #2c3e50;")
        layout.addWidget(title_label)

        # Create Account button
        self.btnRegister = QPushButton("Create Account")
        self.btnRegister.setFixedHeight(45)
        self.btnRegister.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        layout.addWidget(self.btnRegister)

        # Login button
        self.btnLogin = QPushButton("Login")
        self.btnLogin.setFixedHeight(45)
        self.btnLogin.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        layout.addWidget(self.btnLogin)

        layout.addStretch(1)
        self.setLayout(layout)
    