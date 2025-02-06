"""
Module Name: main.py
Description: The main GUI for the chat service
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
from config import *

# Import the UI pages
from pages.main_menu import MainMenu
from pages.login_page import LoginPage
from pages.register_page import RegisterPage
from pages.messaging_page import MessagingPage

class ChatApp(QMainWindow):
    def __init__(self):
        super(ChatApp, self).__init__()
        self.setWindowTitle("Simple Chat")
        self.setStyleSheet("background-color: #DBEBED;")
        self.resize(600, 400)

        # QStackedWidget to hold different pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Create pages
        self.mainMenu = MainMenu()
        self.loginPage = LoginPage()
        self.registerPage = RegisterPage()
        self.messagingPage = MessagingPage()

        # Add pages to stack
        self.stack.addWidget(self.mainMenu)        # index 0
        self.stack.addWidget(self.loginPage)       # index 1
        self.stack.addWidget(self.registerPage)    # index 2
        self.stack.addWidget(self.messagingPage)   # index 3

        # Connect buttons to change pages
        self.mainMenu.btnLogin.clicked.connect(lambda: self.stack.setCurrentWidget(self.loginPage))
        self.mainMenu.btnRegister.clicked.connect(lambda: self.stack.setCurrentWidget(self.registerPage))
        self.loginPage.btnBack.clicked.connect(lambda: self.stack.setCurrentWidget(self.mainMenu))
        self.registerPage.btnBack.clicked.connect(lambda: self.stack.setCurrentWidget(self.mainMenu))
        
        # Connect the custom signals to switch to MessagingPage after success
        self.loginPage.loginSuccessful.connect(lambda: self.stack.setCurrentWidget(self.messagingPage))
        self.registerPage.registerSuccessful.connect(lambda: self.stack.setCurrentWidget(self.messagingPage))
        
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Load the external stylesheet (if the file exists)
    try:
        with open("pages/style.qss", "r") as f:
            style = f.read()
            app.setStyleSheet(style)
    except Exception as e:
        print("Could not load style sheet:", e)

    window = ChatApp()
    window.show()
    sys.exit(app.exec_())
