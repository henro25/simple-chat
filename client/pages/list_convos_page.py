"""
Module Name: list_convos_page.py
Description: Displays the list of conversations (and other accounts) and the number of unread messages for each conversation, as well as the total number of unread messages. It also enables the user to select a conversation to view and search for conversations.
Author: Henry Huang and Bridget Ma (adapted)
Date: 2024-02-06
"""

import sys
import fnmatch
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QHBoxLayout, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, pyqtSignal

from client.protocols.protocol_interface import *
from configs.config import *

class ListConvosPage(QWidget):
    # Signal emitted when a conversation is selected.
    conversationSelected = pyqtSignal(list, int)
    accountDeleted = pyqtSignal()  # Signal to trigger main menu navigation
    
    def __init__(self, Client, parent=None):
        """
        Initializes the ListConvosPage.
        
        :param chat_conversations: List of tuples (user, num_unreads). Most recent conversation first.
        :param parent: Parent widget.
        """
        super(ListConvosPage, self).__init__(parent)
        self.Client = Client
        self.convo_order = []  # Order to display conversation
        self.filtered_convo_order = []  # Copy used for filtering
        self.num_unreads = {} # Maps user to number of unreads from that user
        self.initUI()
    
    def initUI(self):
        """Sets up the UI elements."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Top bar layout (Title + Delete Button)
        top_bar_layout = QHBoxLayout()

        # Title label: "Conversations"
        title_label = QLabel("Conversations")
        title_font = QFont("Helvetica", 24, QFont.Bold)
        title_label.setFont(title_font)

        # Delete Account Button (Top Right)
        self.delete_account_button = QPushButton("Delete Account")
        self.delete_account_button.setFixedHeight(30)
        self.delete_account_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 12px;
                padding: 5px 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.delete_account_button.clicked.connect(lambda _: self.confirmDeleteAccount())

        # Add title to the left, push delete button to the right
        top_bar_layout.addWidget(title_label)
        top_bar_layout.addStretch()  # Pushes button to the right
        top_bar_layout.addWidget(self.delete_account_button)

        # Add top bar layout to main layout
        main_layout.addLayout(top_bar_layout)

        # Unread messages label
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

        # Scroll area to hold conversation buttons
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)

        # Container for conversation buttons
        self.convo_container = QWidget()
        self.convo_layout = QVBoxLayout(self.convo_container)
        self.convo_layout.setSpacing(10)
        self.convo_layout.setContentsMargins(10, 10, 10, 10)
        self.convo_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.convo_container)

        # Populate conversations
        self.populateConversations()

    
    def updateConversations(self, new_chat_conversations):
        """Update the conversation list and refresh the UI."""
        # reset all the data stored
        self.convo_order = []
        self.filtered_convo_order = []
        self.num_unreads = {}
        for user, num_unreads in new_chat_conversations:
            self.convo_order.append(user)
            self.num_unreads[user] = num_unreads

        self.filtered_convo_order = self.convo_order[:]  # Update filtered list as well
        self.refresh()
    
    def refresh(self):
        """refresh the UI"""
        self.updateUnreadCount()    # Update the unread messages label
        self.populateConversations(0)  # Recreate the buttons
    
    def updateUnreadCount(self):
        """Updates the label showing the total number of unread messages."""
        total_unreads = sum(self.num_unreads[user] for user in self.convo_order)
        self.unread_label.setText(f"{total_unreads} unread message{'s' if total_unreads != 1 else ''}")
    
    def updateAfterRead(self, new_unread):
        # update num_unreads and reorder convos so that current convo is at top of convo list
        debug(f"Curr convo: {self.Client.cur_convo}")
        user = self.Client.cur_convo
        ind = self.convo_order.index(user)
        debug(f"updated num unreads for {user} to {new_unread}")
        self.num_unreads[user] = new_unread
        del self.convo_order[ind]
        self.convo_order.insert(0, user)
    
    def populateConversations(self, filtered=1):
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
        cur_convo = self.filtered_convo_order if filtered else self.convo_order
        for user in cur_convo:
            self.displayConvo(user, self.num_unreads[user])
        
        # Add a stretch to push the buttons to the top of the scroll area
        # self.convo_layout.addStretch(1)
    
    def filterConversations(self, text):
        """
        Filters the conversation list based on the search bar input using wildcard patterns.
        
        :param text: The current text in the search bar.
        """
        search_text = text.strip().lower()
        if not search_text:
            self.filtered_convo_order = self.convo_order[:]
        else:
            # Use fnmatch to match wildcard patterns.
            self.filtered_convo_order = [
                convo for convo in self.convo_order
                if fnmatch.fnmatch(convo.lower(), search_text)
            ]
        self.populateConversations()

    
    def setUsername(self, username):
        """
        Stores the username of current client.
        
        :param username: The username of client.
        """
        self.Client.username = username
    
    def onConversationSelected(self, user):
        """
        Called when a conversation button is clicked.
        
        :param user: The username of the conversation selected.
        """
        self.Client.cur_convo = user
        request = create_chat_history_request(self.Client.username, user)
        self.Client.send_request(request)

    def connectClient(self):
        """
        Called to connect current list convos page to client
        """
        self.Client.list_convos_page = self
        
    def disconnectClient(self):
        """
        Called to disconnect current list convos page to client
        """
        self.Client.list_convos_page = None

    def displayConvo(self, user, num_unreads=0):
        """
        Called to display a newly created user in real time
        """
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
        button.clicked.connect(lambda _, user=user: self.onConversationSelected(user))
        self.convo_layout.addWidget(button)

    def confirmDeleteAccount(self):
        """Shows a confirmation dialog before deleting the account."""
        reply = QMessageBox.question(self, "Confirm Deletion",
                                    "Are you sure you want to delete your account? This action cannot be undone.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.deleteAccount()

    def deleteAccount(self):
        """Handles the account deletion process."""
        # Send a request to the server to delete the account
        request = create_delete_account_request(self.Client.username)
        self.Client.send_request(request)

    def successfulAccountDel(self):
        """Called after received confirmation of account deletion"""
        # Show a message that the account is deleted
        QMessageBox.information(self, "Account Deleted", "Your account has been successfully deleted.")
        # redirect back to main_menu
        self.accountDeleted.emit()
