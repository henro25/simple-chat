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

class ChatMessageWidget(QWidget):
    def __init__(self, message_text, parent=None):
        super(ChatMessageWidget, self).__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Message label
        self.message_label = QLabel(message_text)
        self.message_label.setWordWrap(True)
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.message_label, stretch=1)
        
        # Delete button with trash can icon (unicode)
        self.delete_button = QPushButton("🗑")
        self.delete_button.setFixedSize(30, 30)
        self.delete_button.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.delete_button)
        
        self.setLayout(layout)

class MessagingPage(QWidget):
    backClicked = pyqtSignal()  # Signal emitted when the Back button is pressed.
    
    def __init__(self, Client, parent=None):
        super(MessagingPage, self).__init__(parent)
        self.Client = Client
        self.anim = None  # Keep a reference to the current animation.
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

    def sendMessage(self):
        message = self.messageEdit.text().strip()
        if message:
            # Create a new message widget.
            widget = ChatMessageWidget(f"<b>You:</b> {message}")
            widget.delete_button.clicked.connect(lambda: self.deleteMessage(widget))
            self.chat_layout.addWidget(widget)
            self.messageEdit.clear()
            # Use a slight delay before scrolling so the widget is fully added.
            QTimer.singleShot(50, self.scrollToBottom)

    def deleteMessage(self, widget):
        """Remove the given message widget from the chat layout."""
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
