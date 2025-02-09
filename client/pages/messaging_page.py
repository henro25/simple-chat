"""
Module Name: messaging_page.py
Description: The messaging page, where the user can view and delete their messages,
             see the unread count, navigate back, and load the chat (which shows a pop-up).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QScrollArea, QSizePolicy, QMessageBox, QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal
from client.protocols.custom_protocol import *
from configs.config import *

class ChatMessageWidget(QWidget):
    def __init__(self, message_text, message_id, is_client, parent=None):
        super(ChatMessageWidget, self).__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Message label
        self.message_label = QLabel(message_text)
        self.message_label.setWordWrap(True)
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.message_label, stretch=1)
        
        # Delete button with trash can icon (unicode) only if message was sent by client
        if is_client:
            self.delete_button = QPushButton("🗑")
            self.delete_button.setFixedSize(30, 30)
            self.delete_button.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(self.delete_button)
        
        self.message_id = message_id
        self.setLayout(layout)

class MessagingPage(QWidget):
    backClicked = pyqtSignal()  # Signal emitted when the Back button is pressed.
    
    def __init__(self, Client, parent=None):
        super(MessagingPage, self).__init__(parent)
        self.Client = Client
        self.anim = None  # Keep a reference to the current animation.
        self.chat_history = []  # List to store chat history
        self.message_info = {} # Dict that maps message id to sender and text
        self.client_username = None # Username of client
        self.other_user = None # Username of other user
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header layout: Back button on left; unread count and Load Chat button on right.
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setFixedHeight(30)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        header_layout.addWidget(self.back_button)
        self.back_button.clicked.connect(self.goBack)
        
        header_layout.addStretch()  # Spacer between left and right items.
        
        self.unread_label = QLabel("0 unread")
        unread_font = QFont("Helvetica", 12)
        self.unread_label.setFont(unread_font)
        header_layout.addWidget(self.unread_label)
        
        # "Load Chat" button instead of an up arrow.
        self.load_chat_button = QPushButton("Load Chat")
        self.load_chat_button.setFixedHeight(30)
        self.load_chat_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.load_chat_button.clicked.connect(self.loadChat)
        header_layout.addWidget(self.load_chat_button)
        main_layout.addLayout(header_layout)

        # Chat area: QScrollArea with a widget using a QVBoxLayout for messages.
        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        # Align messages to the bottom so they appear anchored when there are few.
        self.chat_layout.setAlignment(Qt.AlignBottom)
        self.chat_area.setWidget(self.chat_widget)
        main_layout.addWidget(self.chat_area, stretch=1)
        
        # Message input area: QLineEdit and Send button.
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
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        input_layout.addWidget(self.btnSend)
        main_layout.addLayout(input_layout)
        
        self.setLayout(main_layout)
        
        # Connect the Send button and Return key to sendMessage.
        self.btnSend.clicked.connect(self.sendMessage)
        self.messageEdit.returnPressed.connect(self.sendMessage)
    
    def setUsers(self, client, other_user):
        self.client_username = client
        self.other_user = other_user

    def sendMessage(self):
        message = self.messageEdit.text().strip()
        if message:
            user = self.client_username
            # Create and send request to server to send message
            request = create_send_message_request(user, self.other_user, message)
            response = self.Client.send_request(request)
            _, command, args = parse_message(response)
            if command == "ERROR":
                errno = int(args[0])
                QMessageBox.critical(self, "Send Message Error", f"Error: {ERROR_MSGS[errno]}")
            else:
                # get message id
                msg_id = deserialize_message_acknowledgement(args)
                # Add message to chat history
                self.chat_history.append(msg_id)
                self.message_info[msg_id] = (user, message)
                # Create a new message widget.
                widget = ChatMessageWidget(f"<b>You:</b> {message}", message_id=msg_id, is_client=1)
                widget.delete_button.clicked.connect(lambda: self.deleteMessage(widget))
                self.chat_layout.addWidget(widget)
                self.messageEdit.clear()
                # Use a slight delay before scrolling so the widget is fully added.
                QTimer.singleShot(50, self.scrollToBottom)

    def deleteMessage(self, widget):
        """Deletes the message and sends a request to server to delete the message from 
        chat history."""
        user = self.client_username
        message = widget.message_label.text()
        msg_id = widget.message_id
        # Create and send request to server to delete a message
        request = create_delete_message_request(msg_id)
        response = self.Client.send_request(request)
        _, command, args = parse_message(response)
        if command == "ERROR":
            errno = int(args[0])
            QMessageBox.critical(self, "Delete Message Error", f"Error: {ERROR_MSGS[errno]}")
        else:
            # Remove from local chat history
            self.chat_history.remove(msg_id)
            del self.message_info[msg_id]
            self.chat_layout.removeWidget(widget)
            widget.deleteLater()
            QTimer.singleShot(50, self.scrollToBottom)

    def scrollToBottom(self):
        """Smoothly scrolls the chat area to the bottom using QPropertyAnimation."""
        # Process pending events to update the layout fully.
        QApplication.processEvents()
        scroll_bar = self.chat_area.verticalScrollBar()
        self.anim = QPropertyAnimation(scroll_bar, b"value", self)
        self.anim.setDuration(300)  # Duration in milliseconds.
        self.anim.setStartValue(scroll_bar.value())
        self.anim.setEndValue(scroll_bar.maximum())
        self.anim.start()

    def populateChatHistory(self, chat_history):
        """Populate the message box with chat history between the users"""
        # Clear the current chat area before populating
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.chat_history = [] # Reset stored chat history
        # Populate chat messages in the UI
        for sender, msg_id, message in chat_history:
            is_client = 1 if sender==self.client_username else 0
            sender = "You" if is_client else sender
            formatted_msg = f"<b>{sender}:</b> {message}"
            widget = ChatMessageWidget(formatted_msg, message_id=msg_id, is_client=is_client)
            if is_client:
                widget.delete_button.clicked.connect(lambda: self.deleteMessage(widget))
            self.chat_layout.addWidget(widget)
            self.chat_history.append(msg_id)
            self.message_info[msg_id] = (sender, message)

        # Scroll to bottom after loading chat history
        QTimer.singleShot(50, self.scrollToBottom)

    def loadChat(self):
        """Show a pop-up message indicating that Load Chat is not yet implemented."""
        QMessageBox.information(self, "Load Chat", "Will be implemented in a theatre near you")

    def goBack(self):
        """Clear all message widgets and emit the backClicked signal."""
        # Remove and delete all items from the chat layout.
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.backClicked.emit()

    def updateUnreadCount(self, count):
        """Update the unread count label in the header."""
        self.unread_label.setText(f"{count} unread")
