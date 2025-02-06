import tkinter as tk
from tkinter import font as tkfont

root = tk.Tk()
root.geometry("400x200")

# Create a font object
test_font = tkfont.Font(family='Helvetica', size=18, weight="bold")

# Create a label with very distinct colors
test_label = tk.Label(root, text="Welcome to Chat Service", font=test_font,
                      bg="yellow", fg="red", bd=2, relief="solid")
test_label.pack(expand=True, fill="both")

root.mainloop()
