"""
Module Name: register_page.py
Description: The create account (registration) form page
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sys
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QMessageBox,
    QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

from client.protocols.protocol_interface import *
from configs.config import *

class RegisterPage(QWidget):
    # Define a custom signal that will be emitted when registration is successful
    registerSuccessful = pyqtSignal(str, list)
    
    def __init__(self, Client, parent=None):
        super(RegisterPage, self).__init__(parent)
        self.Client = Client
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

        # Username row
        username_label = QLabel("Username:")
        # Set a top margin of 3 pixels to push the label text down a bit
        username_label.setContentsMargins(0, 3, 0, 0)
        self.usernameEdit = QLineEdit()
        self.usernameEdit.setPlaceholderText("Choose a username")
        self.usernameEdit.setFixedHeight(40)
        form_layout.addRow(username_label, self.usernameEdit)

        # Password row
        password_label = QLabel("Password:")
        # Set a top margin of 3 pixels to push the label text down a bit
        password_label.setContentsMargins(0, 3, 0, 0)
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setPlaceholderText("Choose a password")
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.passwordEdit.setFixedHeight(40)
        form_layout.addRow(password_label, self.passwordEdit)

        main_layout.addLayout(form_layout)

        # Register button with fixed width and centered
        self.btnRegister = QPushButton("Register")
        self.btnRegister.setFixedHeight(45)
        self.btnRegister.setFixedWidth(200)
        self.btnRegister.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        main_layout.addWidget(self.btnRegister, alignment=Qt.AlignHCenter)

        # Back button with fixed width and centered
        self.btnBack = QPushButton("Back")
        self.btnBack.setFixedHeight(45)
        self.btnBack.setFixedWidth(200)
        self.btnBack.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        main_layout.addWidget(self.btnBack, alignment=Qt.AlignHCenter)

        main_layout.addStretch(1)
        self.setLayout(main_layout)
        
        # Connect the register button to attempt a registration
        self.btnRegister.clicked.connect(self.attemptRegister)

    def attemptRegister(self):
        debug("Attempting to register...")
        username = self.usernameEdit.text().strip()
        valid_username = (username) and (username.count(" ") < 1)
        password = self.passwordEdit.text().strip()
        if valid_username and password:
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            request = create_registration_request(username, hashed_password)
            self.Client.send_request(request)
        elif not valid_username:
            QMessageBox.critical(self, "Registration Error", "Please enter username without white space.")
        else:
            QMessageBox.critical(self, "Registration Error", "Please enter both username and password.")
