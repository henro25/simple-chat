"""
Module Name: main.py
Description: The main GUI for the chat service
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import QTimer
from configs.config import *

from .pages.main_menu import MainMenu
from .pages.login_page import LoginPage
from .pages.register_page import RegisterPage
from .pages.messaging_page import MessagingPage
from .pages.list_convos_page import ListConvosPage
from .client import Client

import configs.config as config

class ChatApp(QMainWindow):
    def __init__(self):
        super(ChatApp, self).__init__()
        self.setWindowTitle("Simple Chat")
        self.setStyleSheet("background-color: #DBEBED;")
        self.resize(250, 400)
        
        # Initialize the client
        self.Client = Client(SERVER_HOST, SERVER_PORT)

        # QStackedWidget to hold different pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Create pages
        self.mainMenu = MainMenu()
        self.loginPage = LoginPage(self.Client)
        self.registerPage = RegisterPage(self.Client)
        self.listConvosPage = ListConvosPage(self.Client)
        self.messagingPage = MessagingPage(self.Client)

        # Connect pages to client
        self.Client.register_page = self.registerPage
        self.Client.login_page = self.loginPage
        self.Client.list_convos_page = self.listConvosPage
        self.Client.messaging_page = self.messagingPage

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
        self.loginPage.loginSuccessful.connect(
            lambda username, convo_list: (
                self.resize(600, 400),
                self.listConvosPage.updateConversations(convo_list),
                self.listConvosPage.setUsername(username),
                self.stack.setCurrentWidget(self.listConvosPage),
                self.setWindowTitle(f"{username}'s Conversations")
            )
        )
        self.registerPage.registerSuccessful.connect(
            lambda username, convo_list: (
                self.resize(600, 400),
                self.listConvosPage.updateConversations(convo_list),
                self.listConvosPage.setUsername(username),
                self.stack.setCurrentWidget(self.listConvosPage),
                self.setWindowTitle(f"{username}'s Conversations")
            )
        )
        self.listConvosPage.conversationSelected.connect(
            lambda chat_history, new_unread: (
                self.messagingPage.populateChatHistory(chat_history),
                self.messagingPage.updateUnreadCount(new_unread),
                self.stack.setCurrentWidget(self.messagingPage),
                self.listConvosPage.updateAfterRead(new_unread)
            )
        )
        self.messagingPage.backClicked.connect(
            lambda: (
                self.listConvosPage.refresh(1),
                self.stack.setCurrentWidget(self.listConvosPage)
            )
        )
        self.listConvosPage.accountDeleted.connect(
            lambda: (
                self.Client.reset(),
                self.stack.setCurrentWidget(self.mainMenu),
            )
        )
    
    def closeEvent(self, event):
        # Make sure to close the network connection when the app closes
        self.Client.close()
        event.accept()

if __name__ == '__main__':
    # Expecting three command-line arguments: protocol_version, server_ip, server_port.
    if len(sys.argv) != 4:
        print("Usage: python -m client.main <protocol_version> <server_ip> <server_port>")
        sys.exit(1)

    config.CUR_PROTO_VERSION = sys.argv[1]
    SERVER_HOST = sys.argv[2]
    try:
        SERVER_PORT = int(sys.argv[3])
    except ValueError:
        print("Error: Server port must be an integer.")
        sys.exit(1)

    print(f"Starting ChatApp with protocol version: {config.CUR_PROTO_VERSION}, server IP: {SERVER_HOST}, server port: {SERVER_PORT}")

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

    # Pass the command-line parameters to ChatApp.
    window = ChatApp()
    window.show()
    timer = QTimer()
    timer.timeout.connect(window.Client.run)
    timer.start(10)
    sys.exit(app.exec_())
