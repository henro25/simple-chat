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
        layout.setSpacing(20)

        # Add some top spacing
        layout.addSpacing(40)

        # Define a common font for the title labels
        title_font = QFont("Helvetica", 24, QFont.Bold)

        # First line of the title
        title_line1 = QLabel("Welcome to")
        title_line1.setAlignment(Qt.AlignCenter)
        title_line1.setFont(title_font)
        title_line1.setStyleSheet("background-color: transparent; color: #2c3e50;")
        layout.addWidget(title_line1)

        # Second line of the title
        title_line2 = QLabel("Simple Chat!")
        title_line2.setAlignment(Qt.AlignCenter)
        title_line2.setFont(title_font)
        title_line2.setStyleSheet("background-color: transparent; color: #2c3e50;")
        layout.addWidget(title_line2)

        layout.addSpacing(40)  # Extra padding below the title labels

        # Create Account button
        self.btnRegister = QPushButton("Create Account")
        self.btnRegister.setFixedHeight(45)
        self.btnRegister.setFixedWidth(200)  # Set the desired button width
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
        layout.addWidget(self.btnRegister, alignment=Qt.AlignHCenter)

        # Login button
        self.btnLogin = QPushButton("Login")
        self.btnLogin.setFixedHeight(45)
        self.btnLogin.setFixedWidth(200)  # Set the desired button width
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
        layout.addWidget(self.btnLogin, alignment=Qt.AlignHCenter)

        layout.addStretch(1)
        self.setLayout(layout)
