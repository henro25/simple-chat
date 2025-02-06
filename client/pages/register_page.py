"""
Module Name: register_page.py
Description: The create account (registration) form page
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QMessageBox,
    QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

class RegisterPage(QWidget):
    # Define a custom signal that will be emitted when registration is successful
    registerSuccessful = pyqtSignal()
    
    def __init__(self, parent=None):
        super(RegisterPage, self).__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(30)

        # Title label
        title_label = QLabel("Create Account")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Helvetica", 24, QFont.Bold)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Form layout for registration fields
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignCenter)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(15)

        self.usernameEdit = QLineEdit()
        self.usernameEdit.setPlaceholderText("Choose a username")
        self.usernameEdit.setFixedHeight(40)
        form_layout.addRow("Username:", self.usernameEdit)

        self.passwordEdit = QLineEdit()
        self.passwordEdit.setPlaceholderText("Choose a password")
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.passwordEdit.setFixedHeight(40)
        form_layout.addRow("Password:", self.passwordEdit)

        main_layout.addLayout(form_layout)

        # Register button
        self.btnRegister = QPushButton("Register")
        self.btnRegister.setFixedHeight(45)
        self.btnRegister.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        main_layout.addWidget(self.btnRegister)

        # Back button
        self.btnBack = QPushButton("Back")
        self.btnBack.setFixedHeight(45)
        self.btnBack.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        main_layout.addWidget(self.btnBack)

        main_layout.addStretch(1)
        self.setLayout(main_layout)
        
        # Connect the register button to attempt a registration
        self.btnRegister.clicked.connect(self.attemptRegister)

    def attemptRegister(self):
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text().strip()
        # For demonstration, assume registration is successful if both fields are nonempty.
        if username and password:
            # In a real app, insert the account into the SQLite database here.
            self.registerSuccessful.emit()  # Signal that registration was successful.
        else:
            QMessageBox.critical(self, "Registration Error", "Please enter both username and password.")
