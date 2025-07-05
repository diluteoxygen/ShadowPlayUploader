#!/usr/bin/env python3
"""
Simple test to verify button clicks work in Toplevel windows.
"""

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from tkinter import Toplevel

def test_button_click():
    print("Button clicked!")

def show_dropdown():
    # Create a Toplevel window
    dropdown_win = Toplevel(root)
    dropdown_win.overrideredirect(True)
    dropdown_win.attributes("-topmost", True)
    dropdown_win.geometry("200x150+100+100")
    
    # Create a button
    test_btn = ttkb.Button(
        dropdown_win,
        text="Test Login",
        bootstyle=SUCCESS,
        command=test_button_click
    )
    test_btn.pack(pady=20)
    
    print("Dropdown created with test button")

# Create main window
root = ttkb.Window()
root.title("Button Test")
root.geometry("300x200")

# Create button to show dropdown
show_btn = ttkb.Button(
    root,
    text="Show Dropdown",
    command=show_dropdown
)
show_btn.pack(pady=50)

root.mainloop() 