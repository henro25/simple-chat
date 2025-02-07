"""
Module Name: list_convos_page.py
Description: Displays the list of conversations (and other accounts) and the number of unread messages for each conversation, as well as the total number of unread messages. It also enables the user to select a conversation to view and search for conversations.
Author: Henry Huang and Bridget Ma (adapted)
Date: 2024-02-06
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QHBoxLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

class ListConvosPage(QWidget):
    # Signal emitted when a conversation is selected.
    # The signal sends the username (str) of the selected conversation.
    conversationSelected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        Initializes the ListConvosPage.
        
        :param chat_conversations: List of tuples (user, num_unreads). Most recent conversation first.
        :param parent: Parent widget.
        """
        super(ListConvosPage, self).__init__(parent)
        self.chat_conversations = []  # List of tuples (user, num_unreads)
        self.filtered_conversations = []  # Copy used for filtering
        self.initUI()
    
    def initUI(self):
        """Sets up the UI elements."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title label: "Conversations"
        title_label = QLabel("Conversations")
        title_font = QFont("Helvetica", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Unread messages label: "n unread messages"
        self.unread_label = QLabel()
        small_font = QFont("Helvetica", 12)
        self.unread_label.setFont(small_font)
        self.unread_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.unread_label)
        self.updateUnreadCount()
        
        # Search bar for filtering conversations
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search conversations...")
        self.search_bar.setFixedHeight(30)
        main_layout.addWidget(self.search_bar)
        self.search_bar.textChanged.connect(self.filterConversations)
        
        # Scroll area to hold the conversation buttons
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)
        
        # Container widget and layout for the conversation buttons
        self.convo_container = QWidget()
        self.convo_layout = QVBoxLayout(self.convo_container)
        self.convo_layout.setSpacing(10)
        self.convo_layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll_area.setWidget(self.convo_container)
        
        # Initially populate the conversation buttons
        self.populateConversations()
    
    def updateConversations(self, new_conversations):
        """Update the conversation list and refresh the UI."""
        self.chat_conversations = new_conversations
        self.filtered_conversations = new_conversations[:]  # Update filtered list as well
        self.updateUnreadCount()    # Update the unread messages label
        self.populateConversations()  # Recreate the buttons
    
    def updateUnreadCount(self):
        """Updates the label showing the total number of unread messages."""
        total_unreads = sum(unreads for _, unreads in self.chat_conversations)
        self.unread_label.setText(f"{total_unreads} unread message{'s' if total_unreads != 1 else ''}")
    
    def populateConversations(self):
        """
        Clears the current conversation buttons and repopulates them based on the current
        filtered conversations.
        """
        # Remove any existing conversation buttons
        while self.convo_layout.count():
            child = self.convo_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add a button for each conversation
        for convo in self.filtered_conversations:
            user, num_unreads = convo
            if num_unreads > 0:
                button_text = f"{user} ({num_unreads} unread)"
            else:
                button_text = user
            button = QPushButton(button_text)
            button.setFixedHeight(40)
            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 10px;
                    padding-right: 10px;    /* Ensure text doesn't run into the right edge */
                    margin-right: 20px;     /* Reserve extra space so the button appears narrower */
                    font-size: 14px;
                    background-color: #bdc3c7;       
                    border: 1px solid #95a5a6;       
                    border-radius: 5px;
                    color: #2C3E50;
                }
                QPushButton:hover {
                    background-color: #95a5a6;
                }
                QPushButton:pressed {
                    background-color: #7f8c8d;
                }
                """)
            # Use a lambda with default argument to capture the current user
            button.clicked.connect(lambda checked, user=user: self.onConversationSelected(user))
            self.convo_layout.addWidget(button)
        
        # Add a stretch to push the buttons to the top of the scroll area
        self.convo_layout.addStretch(1)
    
    def filterConversations(self, text):
        """
        Filters the conversation list based on the search bar input.
        
        :param text: The current text in the search bar.
        """
        search_text = text.strip().lower()
        if not search_text:
            self.filtered_conversations = self.chat_conversations[:]
        else:
            self.filtered_conversations = [
                convo for convo in self.chat_conversations
                if search_text in convo[0].lower()
            ]
        self.populateConversations()
    
    def onConversationSelected(self, user):
        """
        Called when a conversation button is clicked.
        
        :param user: The username of the conversation selected.
        """
        # Emit the signal to notify that a conversation was selected.
        self.conversationSelected.emit(user)
        # Transition logic to the messaging_page can be handled in the main window.

