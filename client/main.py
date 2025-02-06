"""
Module Name: main.py
Description: The main GUI for the chat service
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import tkinter as tk
from tkinter import font as tkfont
from config import *

import os
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# Import the UI pages
from pages.main_menu import MainMenu
from pages.login_page import LoginPage
from pages.register_page import RegisterPage

class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple Chat")
        self.geometry("600x400")
        self.resizable(False, False)

        # Fonts for styling
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold")
        self.button_font = tkfont.Font(family='Helvetica', size=12)
        self.label_font = tkfont.Font(family='Helvetica', size=12)
        self.entry_font = tkfont.Font(family='Helvetica', size=12)

        # Container holds all the frames
        self.container = tk.Frame(self)
        self.container.pack(expand=True, fill="both")
        
        self.current_frame = None

        # Start with the Main Menu
        self.open_frame("MainMenu")
    
    def open_frame(self, frame_name):
        """Destroys the current frame and creates a new one based on frame_name."""
        # Destroy current frame if it exists
        if self.current_frame is not None:
            self.current_frame.destroy()
        
        # Create the new frame
        if frame_name == "MainMenu":
            debug("Opening Main Menu")
            self.current_frame = MainMenu(self.container, self)
        elif frame_name == "LoginPage":
            debug("Opening Login Page")
            self.current_frame = LoginPage(self.container, self)
        elif frame_name == "RegisterPage":
            debug("Opening Register Page")
            self.current_frame = RegisterPage(self.container, self)
        else:
            raise ValueError("Unknown frame requested")
    
        # Pack the new frame to fill the container
        self.current_frame.pack(expand=True, fill="both")

if __name__ == "__main__":
    try:
        app = ChatApp()
        app.mainloop()
    except Exception as e:
        print("Error loading app:", e)