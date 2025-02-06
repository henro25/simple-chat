"""
Module Name: messaging_page.py
Description: The messsaging page, where the user can view number of unread messages, select conversations to open, and send and receive messages
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QLineEdit, QPushButton, QLabel
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class MessagingPage(QWidget):
    def __init__(self, parent=None):
        super(MessagingPage, self).__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title / header area
        header = QLabel("Chat")
        header.setAlignment(Qt.AlignCenter)
        header_font = QFont("Helvetica", 24, QFont.Bold)
        header.setFont(header_font)
        header.setStyleSheet("color: #2C3E50;")
        layout.addWidget(header)

        # Chat history area: Using QTextEdit for simplicity (read-only)
        self.chatHistory = QTextEdit()
        self.chatHistory.setReadOnly(True)
        self.chatHistory.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #CCCCCC;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.chatHistory, stretch=1)

        # Message input area: Horizontal layout with QLineEdit and Send button
        input_layout = QHBoxLayout()
        self.messageEdit = QLineEdit()
        self.messageEdit.setPlaceholderText("Type your message here...")
        self.messageEdit.setFixedHeight(40)
        self.messageEdit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #CCCCCC;
                padding: 5px;
            }
        """)
        input_layout.addWidget(self.messageEdit, stretch=1)

        self.btnSend = QPushButton("Send")
        self.btnSend.setFixedHeight(40)
        self.btnSend.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        input_layout.addWidget(self.btnSend)
        layout.addLayout(input_layout)

        self.setLayout(layout)

        # (Optional) Connect send button to a method that processes the message
        self.btnSend.clicked.connect(self.sendMessage)

    def sendMessage(self):
        message = self.messageEdit.text().strip()
        if message:
            # For now, append message to chat history (in a real app, send it to the server)
            self.chatHistory.append(f"<b>You:</b> {message}")
            self.messageEdit.clear()
