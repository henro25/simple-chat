"""
Module Name: main_menu.py
Description: The login form page
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

from client.protocols.protocol_interface import *
from configs.config import *

class LoginPage(QWidget):
    # Define a custom signal that will be emitted when login is successful
    loginSuccessful = pyqtSignal(str, list)
    
    def __init__(self, Client, parent=None):
        super(LoginPage, self).__init__(parent)
        self.Client = Client
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(30)

        # Title label
        title_label = QLabel("Login")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Helvetica", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50;")
        main_layout.addWidget(title_label)

        # Form layout for login fields
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignCenter)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(15)

        # Username row
        username_label = QLabel("Username:")
        username_label.setStyleSheet("color: #2C3E50;")
        # Manually push the label text down
        username_label.setContentsMargins(0, 3, 0, 0)
        self.usernameEdit = QLineEdit()
        self.usernameEdit.setPlaceholderText("Enter your username")
        self.usernameEdit.setFixedHeight(40)
        form_layout.addRow(username_label, self.usernameEdit)
        
        # Password row
        password_label = QLabel("Password:")
        password_label.setStyleSheet("color: #2C3E50;")
        # Manually push the label text down
        password_label.setContentsMargins(0, 3, 0, 0)
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setPlaceholderText("Enter your password")
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.passwordEdit.setFixedHeight(40)
        form_layout.addRow(password_label, self.passwordEdit)

        main_layout.addLayout(form_layout)

        # Login button with reduced width and centered
        self.btnLogin = QPushButton("Login")
        self.btnLogin.setFixedHeight(45)
        self.btnLogin.setFixedWidth(200)  # Adjust width as needed
        self.btnLogin.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        main_layout.addWidget(self.btnLogin, alignment=Qt.AlignHCenter)

        # Back button with reduced width and centered
        self.btnBack = QPushButton("Back")
        self.btnBack.setFixedHeight(45)
        self.btnBack.setFixedWidth(200)  # Adjust width as needed
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
        
        # Connect the login button to attempt a login
        self.btnLogin.clicked.connect(self.attemptLogin)
    
    def attemptLogin(self):
        username = self.usernameEdit.text().strip()
        password = self.passwordEdit.text().strip()
        if username and password:
            request = create_login_request(username, password)
            self.Client.send_request(request)
        else:
            QMessageBox.critical(self, "Login Error", "Please enter both username and password.")
    
    def displayLoginErrors(self, errno):
        """Displays login error"""
        QMessageBox.critical(self, "Login Error", ERROR_MSGS[errno])
