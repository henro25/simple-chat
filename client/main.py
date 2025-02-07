"""
Module Name: main.py
Description: The main GUI for the chat service
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from configs.config import *

from .pages.main_menu import MainMenu
from .pages.login_page import LoginPage
from .pages.register_page import RegisterPage
from .pages.messaging_page import MessagingPage
from .pages.list_convos_page import ListConvosPage
from .client import Client

class ChatApp(QMainWindow):
    def __init__(self):
        super(ChatApp, self).__init__()
        self.setWindowTitle("Simple Chat")
        self.setStyleSheet("background-color: #DBEBED;")
        self.resize(600, 400)
        
        # Initialize the client
        self.Client = Client(SERVER_HOST, SERVER_PORT)
        
        # List to hold other users and unread messages; elements are tuples (user, num_unreads)
        self.chat_conversations = [
            ("Alice", 2),
            ("Bob", 0),
            ("Charlie", 5),
            ("Dave", 1),
            ("Eve", 0),
            ("Faythe", 3)
        ]

        # QStackedWidget to hold different pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Create pages
        self.mainMenu = MainMenu()
        self.loginPage = LoginPage(self.Client)
        self.registerPage = RegisterPage(self.Client)
        self.listConvosPage = ListConvosPage(self.chat_conversations)
        self.messagingPage = MessagingPage(self.Client)

        # Add pages to stack
        self.stack.addWidget(self.mainMenu)
        self.stack.addWidget(self.loginPage)
        self.stack.addWidget(self.registerPage)
        self.stack.addWidget(self.listConvosPage)
        self.stack.addWidget(self.messagingPage)

        # Connect buttons to change pages
        self.mainMenu.btnLogin.clicked.connect(lambda: self.stack.setCurrentWidget(self.loginPage))
        self.mainMenu.btnRegister.clicked.connect(lambda: self.stack.setCurrentWidget(self.registerPage))
        self.loginPage.btnBack.clicked.connect(lambda: self.stack.setCurrentWidget(self.mainMenu))
        self.registerPage.btnBack.clicked.connect(lambda: self.stack.setCurrentWidget(self.mainMenu))
        
        # Connect the custom signals to switch to either Conversation List or Chat Page when signaled
        self.loginPage.loginSuccessful.connect(lambda: self.stack.setCurrentWidget(self.listConvosPage))
        self.registerPage.registerSuccessful.connect(lambda: self.stack.setCurrentWidget(self.listConvosPage))
        self.listConvosPage.conversationSelected.connect(lambda user: self.stack.setCurrentWidget(self.messagingPage))
    
    def closeEvent(self, event):
        # Make sure to close the network connection when the app closes
        self.Client.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Load the external stylesheet (if the file exists)
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qss_file = os.path.join(base_dir, "pages/style.qss")
        debug(f"Loading QSS file: {qss_file}")
        with open(qss_file, "r") as f:
            style = f.read()
            app.setStyleSheet(style)
    except Exception as e:
        print("Could not load style sheet:", e)

    window = ChatApp()
    window.show()
    sys.exit(app.exec_())
