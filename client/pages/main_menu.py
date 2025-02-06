"""
Module Name: main_menu.py
Description: The main landing page with Create Account and Login buttons
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import tkinter as tk
from config import *

class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="lightblue")
        
        debug("Showing Main Menu")
        
        self.controller = controller

        title_label = tk.Label(self, text="Welcome to Chat Service", font=controller.title_font, bg="lightblue", fg="white")
        title_label.pack(pady=30)
        
        # Create a frame to hold the buttons, so they can be centered
        button_frame = tk.Frame(self, bg="lightblue")
        button_frame.pack(pady=20)

        # Create Account button
        create_btn = tk.Button(button_frame, text="Create Account", font=controller.button_font,
                               width=20, command=lambda: controller.open_frame("RegisterPage"))
        create_btn.pack(pady=10)

        # Login button
        login_btn = tk.Button(button_frame, text="Login", font=controller.button_font,
                              width=20, command=lambda: controller.open_frame("LoginPage"))
        login_btn.pack(pady=10)
