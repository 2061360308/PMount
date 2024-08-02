import tkinter as tk
import ttkbootstrap as ttk

from ttkbootstrap import Style
from ttkbootstrap.constants import *


def add_label():
    global label_counter
    label = ttk.Label(root, text=f"Label {label_counter}")
    label.pack(pady=5)
    labels.append(label)
    label_counter += 1


def remove_label():
    if labels:
        label = labels.pop()
        label.destroy()


root = tk.Tk()
style = Style(theme='cosmo')  # 选择一个现代主题
root.title("Dynamic Widgets with Tkinter and ttkbootstrap")

label_counter = 1
labels = []

add_button = ttk.Button(root, text="Add Label", command=add_label, bootstyle=SUCCESS)
add_button.pack(pady=10)

remove_button = ttk.Button(root, text="Remove Label", command=remove_label, bootstyle=DANGER)
remove_button.pack(pady=10)

root.mainloop()
