import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import threading
from .uploader_batch import start_batch_upload

def start_gui():
    root = tk.Tk()
    root.title("ShadowPlay Batch Uploader")
    root.geometry("600x500")

    folder_var = tk.StringVar()
    channel_var = tk.StringVar()
    video_count_var = tk.StringVar()
    progress_var = tk.IntVar()

    # UI Callbacks
    def select_folder():
        folder = filedialog.askdirectory()
        folder_var.set(folder)

    def start_uploading():
        folder = folder_var.get()
        if not folder:
            messagebox.showwarning("Select Folder", "Please select a folder.")
            return

        log_box.delete("1.0", tk.END)
        progress_var.set(0)
        threading.Thread(
            target=start_batch_upload,
            args=(folder, log_box, channel_var, video_count_var, progress_var),
            daemon=True
        ).start()

    # GUI Layout
    tk.Label(root, text="Select Folder with .mp4 clips:").pack(pady=5)
    tk.Entry(root, textvariable=folder_var, width=50).pack()
    tk.Button(root, text="Browse", command=select_folder).pack(pady=5)
    tk.Button(root, text="Start Uploading", command=start_uploading).pack(pady=10)

    # Status
    tk.Label(root, textvariable=channel_var, fg="blue").pack()
    tk.Label(root, textvariable=video_count_var, fg="green").pack()

    # Progress bar
    progress = Progressbar(root, orient="horizontal", length=400, mode="determinate", variable=progress_var)
    progress.pack(pady=10)

    # Log output
    log_box = tk.Text(root, height=15, width=70)
    log_box.pack(pady=10)

    root.mainloop()
