"""
Module Name: register_page.py
Description: The create account (registration) form page
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import tkinter as tk
from tkinter import messagebox
from config import *

class RegisterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        
        debug("Showing Register Page")
        
        self.controller = controller

        title_label = tk.Label(self, text="Create Account", font=controller.title_font, bg="white")
        title_label.pack(pady=10)

        form_frame = tk.Frame(self, bg="white")
        form_frame.pack(pady=10)

        tk.Label(form_frame, text="Username:", font=controller.label_font,
                 bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.username_entry = tk.Entry(form_frame, font=controller.entry_font)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Password:", font=controller.label_font,
                 bg="white").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = tk.Entry(form_frame, show="*", font=controller.entry_font)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        submit_btn = tk.Button(self, text="Create Account", font=controller.button_font, width=15, command=self.register)
        submit_btn.pack(pady=10)

        back_btn = tk.Button(self, text="Back", font=controller.button_font, width=10, command=lambda: controller.open_frame("MainMenu"))
        back_btn.pack(pady=5)

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        # Here, insert logic to send registration details to the server.
        # For now, simulate registration:
        if username and password:
            messagebox.showinfo("Registration", f"Account created for {username}!")
            self.controller.open_frame("LoginPage")
        else:
            messagebox.showerror("Registration Error", "Please enter both username and password.")

    def reset_fields(self):
        """Clear the text in the username and password fields."""
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
