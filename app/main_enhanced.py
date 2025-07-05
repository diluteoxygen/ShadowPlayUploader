import os
import threading
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, ttk, Menu, Toplevel
from typing import Optional, Dict, Any
import requests
from PIL import Image, ImageTk
from io import BytesIO

from .uploader_batch import start_batch_upload
from .logger import get_logger
from .config import get_config
from .exceptions import ShadowPlayUploaderError, format_error_for_user
from .upload_queue import UploadQueue, UploadItem, UploadStatus
from .channel_manager import ChannelManager, ChannelInfo
from .upload_presets import PresetManager, UploadPreset

logger = get_logger()
config = get_config()

class ProfileDropdown:
    """Profile dropdown component with channel logo and authentication controls."""
    
    def __init__(self, parent, channel_manager, on_auth_change):
        self.parent = parent
        self.channel_manager = channel_manager
        self.on_auth_change = on_auth_change
        self.dropdown_open = False
        self.profile_photo = None
        self.dropdown_logo_photo = None
        self.dropdown_win = None
        self.login_btn = None
        self.logout_btn = None
        self.refresh_btn = None
        # Create profile button
        self.profile_frame = ttkb.Frame(parent)
        self.profile_frame.pack(side=RIGHT, padx=(10, 0))
        self.profile_btn = ttkb.Button(
            self.profile_frame, 
            text="👤", 
            bootstyle=SECONDARY,
            width=3,
            command=self._toggle_dropdown
        )
        self.profile_btn.pack(side=TOP)
        # Show logo if available
        self._update_profile_button_logo()
    
    def _toggle_dropdown(self):
        if self.dropdown_open:
            self._hide_dropdown()
        else:
            self._show_dropdown()
    
    def _show_dropdown(self):
        if self.dropdown_open:
            return
        self.dropdown_win = Toplevel(self.parent)
        self.dropdown_win.overrideredirect(True)
        self.dropdown_win.attributes("-topmost", True)
        self.dropdown_win.configure(bg="white")
        x = self.profile_frame.winfo_rootx()
        y = self.profile_frame.winfo_rooty() + self.profile_frame.winfo_height()
        self.dropdown_win.geometry(f"220x180+{x}+{y}")
        self.dropdown_open = True
        self.dropdown_win.bind("<FocusOut>", lambda e: self._hide_dropdown())
        self.dropdown_win.grab_set()
        frame = ttkb.Frame(self.dropdown_win, padding=10)
        frame.pack(fill=BOTH, expand=True)
        self.status_label = ttkb.Label(
            frame, 
            text="Not authenticated", 
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.status_label.pack(pady=(0, 5), padx=0)
        channel_info_frame = ttkb.Frame(frame)
        channel_info_frame.pack(fill=X, padx=0, pady=5)
        self.logo_label = ttkb.Label(channel_info_frame, text="")
        self.logo_label.pack(side=LEFT, padx=(0, 10))
        self.channel_name_label = ttkb.Label(
            channel_info_frame, 
            text="", 
            font=("Segoe UI", 10, "bold")
        )
        self.channel_name_label.pack(side=LEFT, fill=X, expand=True)
        buttons_frame = ttkb.Frame(frame)
        buttons_frame.pack(fill=X, padx=0, pady=(5, 0))
        self.login_btn = ttkb.Button(
            buttons_frame,
            text="🔑 Login",
            bootstyle=SUCCESS
        )
        self.login_btn.pack(fill=X, pady=2)
        
        # Use bind instead of command for Toplevel windows
        self.login_btn.bind("<Button-1>", lambda e: self._login())
        self.logout_btn = ttkb.Button(
            buttons_frame,
            text="🚪 Logout",
            bootstyle=DANGER,
            state=DISABLED
        )
        self.logout_btn.pack(fill=X, pady=2)
        self.logout_btn.bind("<Button-1>", lambda e: self._logout())
        
        self.refresh_btn = ttkb.Button(
            buttons_frame,
            text="🔄 Refresh",
            bootstyle=INFO,
            state=DISABLED
        )
        self.refresh_btn.pack(fill=X, pady=2)
        self.refresh_btn.bind("<Button-1>", lambda e: self._refresh())
        self._update_state()
    
    def _hide_dropdown(self):
        if self.dropdown_open and self.dropdown_win:
            self.dropdown_win.grab_release()
            self.dropdown_win.destroy()
            self.dropdown_win = None
            self.dropdown_open = False
            self.login_btn = None
            self.logout_btn = None
            self.refresh_btn = None
    
    def _login(self):
        logger.debug("[ProfileDropdown] Login button clicked.")
        
        # Store the callback before hiding dropdown
        callback = self.on_auth_change
        
        if callback:
            logger.debug("[ProfileDropdown] Calling on_auth_change('login').")
            callback("login")
        else:
            logger.error("[ProfileDropdown] on_auth_change callback is None!")
        
        # Hide dropdown after callback
        self.dropdown_win.after(100, self._hide_dropdown)
    
    def _logout(self):
        self._hide_dropdown()
        if self.on_auth_change:
            self.on_auth_change("logout")
    
    def _refresh(self):
        self._hide_dropdown()
        if self.on_auth_change:
            self.on_auth_change("refresh")
    
    def _load_profile_image(self, url: str):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGBA")
            image = image.resize((32, 32), Image.Resampling.LANCZOS)
            self.profile_photo = ImageTk.PhotoImage(image)
            self.dropdown_logo_photo = ImageTk.PhotoImage(image)
            self.profile_btn.configure(image=self.profile_photo, text="")
            
            # Only update logo_label if dropdown is open and widget exists
            if hasattr(self, 'logo_label') and self.dropdown_open and self.logo_label.winfo_exists():
                try:
                    self.logo_label.configure(image=self.dropdown_logo_photo, text="")
                except Exception as e:
                    logger.debug(f"Could not update logo_label: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to load profile image: {e}")
            self.profile_btn.configure(image="", text="👤")
            
            # Only update logo_label if dropdown is open and widget exists
            if hasattr(self, 'logo_label') and self.dropdown_open and self.logo_label.winfo_exists():
                try:
                    self.logo_label.configure(image="", text="👤")
                except Exception as e:
                    logger.debug(f"Could not update logo_label: {e}")
    
    def _update_profile_button_logo(self):
        active_channel = self.channel_manager.get_active_channel()
        if active_channel and active_channel.thumbnail_url:
            self._load_profile_image(active_channel.thumbnail_url)
        else:
            self.profile_btn.configure(image="", text="👤")
    
    def _update_state(self):
        active_channel = self.channel_manager.get_active_channel()
        if active_channel:
            self.status_label.configure(text="Authenticated", foreground="green")
            self.channel_name_label.configure(text=active_channel.channel_title)
            if active_channel.thumbnail_url:
                self._load_profile_image(active_channel.thumbnail_url)
            else:
                self.profile_btn.configure(image="", text="👤")
                # Only update logo_label if dropdown is open and widget exists
                if hasattr(self, 'logo_label') and self.dropdown_open and self.logo_label.winfo_exists():
                    try:
                        self.logo_label.configure(image="", text="👤")
                    except Exception as e:
                        logger.debug(f"Could not update logo_label: {e}")
            self.login_btn.configure(state=DISABLED)
            self.logout_btn.configure(state=NORMAL)
            self.refresh_btn.configure(state=NORMAL)
        else:
            self.status_label.configure(text="Not authenticated", foreground="gray")
            self.channel_name_label.configure(text="")
            self.profile_btn.configure(image="", text="👤")
            # Only update logo_label if dropdown is open and widget exists
            if hasattr(self, 'logo_label') and self.dropdown_open and self.logo_label.winfo_exists():
                try:
                    self.logo_label.configure(image="", text="👤")
                except Exception as e:
                    logger.debug(f"Could not update logo_label: {e}")
            self.login_btn.configure(state=NORMAL)
            self.logout_btn.configure(state=DISABLED)
            self.refresh_btn.configure(state=DISABLED)
    
    def update_display(self):
        self._update_profile_button_logo()
        if self.dropdown_open:
            self._update_state()

class EnhancedShadowPlayUploader:
    """Enhanced GUI with queue management, multiple channels, and presets."""
    
    def __init__(self):
        """Initialize the enhanced GUI."""
        # Initialize managers
        self.channel_manager = ChannelManager()
        self.preset_manager = PresetManager()
        self.upload_queue = UploadQueue(max_concurrent=1)
        
        # Set up queue callbacks
        self.upload_queue.on_progress = self._on_upload_progress
        self.upload_queue.on_status_change = self._on_upload_status_change
        self.upload_queue.on_complete = self._on_upload_complete
        self.upload_queue.on_error = self._on_upload_error
        
        # Get UI settings from config
        ui_settings = config.get_ui_settings()
        theme = ui_settings["theme"]
        window_width = ui_settings["window_width"]
        window_height = ui_settings["window_height"]
        
        # Create main window
        self.app = ttkb.Window(themename=theme)
        self.app.title("ShadowPlay Batch Uploader - Enhanced")
        self.app.geometry(f"{window_width}x{window_height}")
        self.app.resizable(True, True)
        
        # Variables
        self.folder_var = ttkb.StringVar()
        self.channel_var = ttkb.StringVar()
        self.preset_var = ttkb.StringVar()
        self.progress_var = ttkb.IntVar()
        self.file_progress_var = ttkb.StringVar()
        self.mb_progress_var = ttkb.StringVar()
        self.auto_delete_var = ttkb.BooleanVar(value=ui_settings["auto_delete"])
        self.dark_mode_var = ttkb.BooleanVar(value=ui_settings["dark_mode"])
        
        # Create GUI
        self._create_gui()
        self._setup_preset_selector()
        self._setup_queue_display()
        
        # Set up logger
        logger.set_gui_log_box(self.log_box)
        
        # Check authentication status
        self._check_auth_status()
        
        logger.info("Enhanced ShadowPlay Uploader started")
    
    def _create_gui(self):
        """Create the main GUI layout."""
        # Main container
        main_frame = ttkb.Frame(self.app, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Header with profile dropdown
        header_frame = ttkb.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 10))
        
        # Title
        title_label = ttkb.Label(
            header_frame, 
            text="ShadowPlay Batch Uploader", 
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(side=LEFT)
        
        # Profile dropdown
        self.profile_dropdown = ProfileDropdown(
            header_frame, 
            self.channel_manager, 
            self._on_auth_action
        )
        
        # Channel selector
        channel_frame = ttkb.LabelFrame(main_frame, text="📺 YouTube Channel", padding=10)
        channel_frame.pack(fill=X, pady=(0, 10))
        
        ttkb.Label(channel_frame, text="Select Channel:").pack(anchor=W)
        self.channel_combobox = ttkb.Combobox(channel_frame, textvariable=self.channel_var, state="readonly")
        self.channel_combobox.pack(fill=X, pady=2)
        
        # Top section - Folder and Preset selection
        top_frame = ttkb.LabelFrame(main_frame, text="Upload Configuration", padding=10)
        top_frame.pack(fill=X, pady=(0, 10))
        
        # Folder selection
        folder_frame = ttkb.Frame(top_frame)
        folder_frame.pack(fill=X, pady=(0, 10))
        
        ttkb.Label(folder_frame, text="Select Folder with .mp4 clips:", font=("Segoe UI", 10, "bold")).pack(anchor=W)
        
        folder_input_frame = ttkb.Frame(folder_frame)
        folder_input_frame.pack(fill=X, pady=5)
        
        self.folder_entry = ttkb.Entry(folder_input_frame, textvariable=self.folder_var, width=50)
        self.folder_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        ttkb.Button(folder_input_frame, text="Browse", bootstyle=SECONDARY, 
                   command=self._browse_folder).pack(side=LEFT, padx=(0, 10))
        
        # Preset selection
        preset_frame = ttkb.Frame(top_frame)
        preset_frame.pack(fill=X, pady=(0, 10))
        
        ttkb.Label(preset_frame, text="Upload Preset:").pack(anchor=W)
        self.preset_combobox = ttkb.Combobox(preset_frame, textvariable=self.preset_var, state="readonly")
        self.preset_combobox.pack(fill=X, pady=2)
        
        # Control buttons
        button_frame = ttkb.Frame(top_frame)
        button_frame.pack(fill=X, pady=10)
        
        self.start_btn = ttkb.Button(button_frame, text="Start Upload", bootstyle=PRIMARY, 
                                    command=self._start_upload)
        self.start_btn.pack(side=LEFT, padx=(0, 10))
        
        self.pause_btn = ttkb.Button(button_frame, text="Pause All", bootstyle=WARNING, 
                                   command=self._pause_all, state=DISABLED)
        self.pause_btn.pack(side=LEFT, padx=(0, 10))
        
        self.resume_btn = ttkb.Button(button_frame, text="Resume All", bootstyle=SUCCESS, 
                                    command=self._resume_all, state=DISABLED)
        self.resume_btn.pack(side=LEFT, padx=(0, 10))
        
        self.cancel_btn = ttkb.Button(button_frame, text="Cancel All", bootstyle=DANGER, 
                                    command=self._cancel_all, state=DISABLED)
        self.cancel_btn.pack(side=LEFT)
        
        # Settings section
        settings_frame = ttkb.LabelFrame(main_frame, text="Settings", padding=10)
        settings_frame.pack(fill=X, pady=(0, 10))
        
        auto_delete_check = ttkb.Checkbutton(settings_frame, text="Auto-delete after upload", 
                                           variable=self.auto_delete_var)
        auto_delete_check.pack(side=LEFT, padx=(5, 20))
        
        def toggle_theme():
            new_theme = "superhero" if self.dark_mode_var.get() else "flatly"
            self.app.style.theme_use(new_theme)
            config.set("ui.theme", new_theme)
            config.set("ui.dark_mode", self.dark_mode_var.get())
            config.save_config()
            logger.debug(f"Theme changed to: {new_theme}")
        
        dark_mode_check = ttkb.Checkbutton(settings_frame, text="Dark Mode", 
                                         variable=self.dark_mode_var, command=toggle_theme)
        dark_mode_check.pack(side=LEFT)
        
        # Progress section
        progress_frame = ttkb.LabelFrame(main_frame, text="Upload Progress", padding=10)
        progress_frame.pack(fill=X, pady=(0, 10))
        
        # Overall progress
        self.overall_progress = ttkb.Progressbar(progress_frame, orient="horizontal", 
                                               mode="determinate", variable=self.progress_var)
        self.overall_progress.pack(fill=X, pady=(0, 5))
        
        # Status labels
        self.status_frame = ttkb.Frame(progress_frame)
        self.status_frame.pack(fill=X)
        
        self.channel_label = ttkb.Label(self.status_frame, textvariable=self.channel_var, 
                                       font=("Segoe UI", 9))
        self.channel_label.pack(anchor=W)
        
        self.file_progress_label = ttkb.Label(self.status_frame, textvariable=self.file_progress_var)
        self.file_progress_label.pack(anchor=W)
        
        self.mb_progress_label = ttkb.Label(self.status_frame, textvariable=self.mb_progress_var)
        self.mb_progress_label.pack(anchor=W)
        
        # Queue display
        queue_frame = ttkb.LabelFrame(main_frame, text="Upload Queue", padding=10)
        queue_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # Queue controls
        queue_controls = ttkb.Frame(queue_frame)
        queue_controls.pack(fill=X, pady=(0, 10))
        
        ttkb.Button(queue_controls, text="Clear Completed", bootstyle=SECONDARY,
                   command=self._clear_completed).pack(side=LEFT, padx=(0, 10))
        
        ttkb.Button(queue_controls, text="Pause Selected", bootstyle=WARNING,
                   command=self._pause_selected).pack(side=LEFT, padx=(0, 10))
        
        ttkb.Button(queue_controls, text="Resume Selected", bootstyle=SUCCESS,
                   command=self._resume_selected).pack(side=LEFT, padx=(0, 10))
        
        ttkb.Button(queue_controls, text="Cancel Selected", bootstyle=DANGER,
                   command=self._cancel_selected).pack(side=LEFT)
        
        # Queue treeview
        columns = ("File", "Status", "Progress", "Size")
        self.queue_tree = ttkb.Treeview(queue_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.queue_tree.heading("File", text="File")
        self.queue_tree.heading("Status", text="Status")
        self.queue_tree.heading("Progress", text="Progress")
        self.queue_tree.heading("Size", text="Size")
        
        self.queue_tree.column("File", width=300, anchor=W)
        self.queue_tree.column("Status", width=100, anchor=CENTER)
        self.queue_tree.column("Progress", width=100, anchor=CENTER)
        self.queue_tree.column("Size", width=80, anchor=E)
        
        # Scrollbar
        queue_scrollbar = ttkb.Scrollbar(queue_frame, orient=VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)
        
        self.queue_tree.pack(side=LEFT, fill=BOTH, expand=True)
        queue_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Context menu for queue
        self.queue_context_menu = Menu(self.app, tearoff=0)
        self.queue_context_menu.add_command(label="Pause", command=self._pause_selected)
        self.queue_context_menu.add_command(label="Resume", command=self._resume_selected)
        self.queue_context_menu.add_command(label="Cancel", command=self._cancel_selected)
        self.queue_context_menu.add_separator()
        self.queue_context_menu.add_command(label="Remove from Queue", command=self._remove_selected)
        
        self.queue_tree.bind("<Button-3>", self._show_queue_context_menu)
        
        # Log section
        log_frame = ttkb.LabelFrame(main_frame, text="Logs", padding=10)
        log_frame.pack(fill=BOTH, expand=True)
        
        # Log text widget
        self.log_box = ttkb.Text(log_frame, height=6, wrap=WORD)
        log_scrollbar = ttkb.Scrollbar(log_frame, orient=VERTICAL, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_box.pack(side=LEFT, fill=BOTH, expand=True)
        log_scrollbar.pack(side=RIGHT, fill=Y)
    
    def _on_auth_action(self, action: str):
        logger.debug(f"[EnhancedShadowPlayUploader] _on_auth_action called with action: {action}")
        if action == "login":
            self._authenticate_user()
        elif action == "logout":
            self._logout_user()
        elif action == "refresh":
            self._refresh_channels()
    
    def _setup_channel_selector(self):
        """Set up the channel selector combobox."""
        channels = self.channel_manager.get_all_channels()
        
        # Clear existing items
        self.channel_combobox['values'] = []
        
        if channels:
            # Add channels to combobox
            channel_names = [f"{channel.channel_title} ({channel.channel_id})" for channel in channels]
            self.channel_combobox['values'] = channel_names
            
            # Select active channel if available
            active_channel = self.channel_manager.get_active_channel()
            if active_channel:
                active_name = f"{active_channel.channel_title} ({active_channel.channel_id})"
                if active_name in channel_names:
                    self.channel_combobox.set(active_name)
                    self.channel_var.set(active_name)
            
            # Bind selection change
            self.channel_combobox.bind("<<ComboboxSelected>>", self._on_channel_changed)
            
            logger.info(f"Loaded {len(channels)} channels into selector")
        else:
            logger.info("No channels available")
    
    def _setup_preset_selector(self):
        """Set up the preset selector combobox."""
        presets = self.preset_manager.get_all_presets()
        
        # Clear existing items
        self.preset_combobox['values'] = []
        
        if presets:
            # Add presets to combobox
            preset_names = [preset.name for preset in presets]
            self.preset_combobox['values'] = preset_names
            
            # Select first preset if available
            if preset_names:
                self.preset_combobox.set(preset_names[0])
                self.preset_var.set(preset_names[0])
            
            # Bind selection change
            self.preset_combobox.bind("<<ComboboxSelected>>", self._on_preset_changed)
            
            logger.info(f"Loaded {len(presets)} presets into selector")
        else:
            logger.info("No presets available")
    
    def _setup_queue_display(self):
        """Set up the upload queue display."""
        # This is already done in _create_gui
        pass
    
    def _browse_folder(self):
        """Browse for folder selection."""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
    
    def _on_channel_changed(self, event):
        """Handle channel selection change."""
        try:
            selection = self.channel_var.get()
            if selection:
                # Extract channel ID from selection
                channel_id = selection.split("(")[-1].rstrip(")")
                self.channel_manager.set_active_channel(channel_id)
                logger.info(f"Switched to channel: {selection}")
        except Exception as e:
            logger.error(f"Failed to change channel: {e}")
    
    def _on_preset_changed(self, event):
        """Handle preset selection change."""
        try:
            preset_name = self.preset_var.get()
            if preset_name:
                preset = self.preset_manager.get_preset(preset_name)
                if preset:
                    # Update auto-delete setting
                    self.auto_delete_var.set(preset.auto_delete)
                    logger.info(f"Switched to preset: {preset_name}")
        except Exception as e:
            logger.error(f"Failed to change preset: {e}")
    
    def _start_upload(self):
        """Start the upload process."""
        folder = self.folder_var.get()
        if not folder:
            messagebox.showwarning("Select Folder", "Please select a folder.")
            return
        
        # Get selected channel and preset
        active_channel = self.channel_manager.get_active_channel()
        if not active_channel:
            messagebox.showerror("No Channel", "Please select a YouTube channel.")
            return
        
        preset_name = self.preset_var.get()
        preset = self.preset_manager.get_preset(preset_name) if preset_name else None
        
        # Save settings
        config.set("ui.auto_delete", self.auto_delete_var.get())
        config.save_config()
        
        # Disable start button, enable control buttons
        self.start_btn.config(state=DISABLED)
        self.pause_btn.config(state=NORMAL)
        self.resume_btn.config(state=NORMAL)
        self.cancel_btn.config(state=NORMAL)
        
        # Clear log
        self.log_box.delete("1.0", "end")
        logger.clear_gui_log()
        
        # Reset progress
        self.progress_var.set(0)
        self.file_progress_var.set("")
        self.mb_progress_var.set("")
        
        # Start upload in thread
        def upload_thread():
            try:
                # Use the enhanced uploader with queue management
                self._start_enhanced_upload(folder, active_channel, preset)
            except Exception as e:
                logger.log_exception("Upload failed", e)
                messagebox.showerror("Upload Error", f"Upload failed: {e}")
            finally:
                self.start_btn.config(state=NORMAL)
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def _start_enhanced_upload(self, folder: str, channel: ChannelInfo, preset: Optional[UploadPreset]):
        """Start enhanced upload with queue management."""
        # This is a placeholder - you would integrate the queue system here
        # For now, we'll use the existing uploader
        start_batch_upload(
            folder,
            log_box=self.log_box,
            channel_var=self.channel_var,
            video_count_var=None,
            progress_var=self.progress_var,
            file_progress_var=self.file_progress_var,
            mb_progress_var=self.mb_progress_var
        )
    
    def _pause_all(self):
        """Pause all uploads."""
        self.upload_queue.pause_all()
        logger.info("Paused all uploads")
    
    def _resume_all(self):
        """Resume all uploads."""
        self.upload_queue.resume_all()
        logger.info("Resumed all uploads")
    
    def _cancel_all(self):
        """Cancel all uploads."""
        if messagebox.askyesno("Cancel All", "Are you sure you want to cancel all uploads?"):
            self.upload_queue.cancel_all()
            logger.info("Cancelled all uploads")
    
    def _pause_selected(self):
        """Pause selected uploads."""
        selected_items = self.queue_tree.selection()
        for item_id in selected_items:
            # Get upload item and pause it
            # This would need to be implemented with the queue system
            pass
    
    def _resume_selected(self):
        """Resume selected uploads."""
        selected_items = self.queue_tree.selection()
        for item_id in selected_items:
            # Get upload item and resume it
            # This would need to be implemented with the queue system
            pass
    
    def _cancel_selected(self):
        """Cancel selected uploads."""
        selected_items = self.queue_tree.selection()
        if selected_items and messagebox.askyesno("Cancel Selected", "Cancel selected uploads?"):
            for item_id in selected_items:
                # Get upload item and cancel it
                # This would need to be implemented with the queue system
                pass
    
    def _remove_selected(self):
        """Remove selected uploads from queue."""
        selected_items = self.queue_tree.selection()
        if selected_items and messagebox.askyesno("Remove Selected", "Remove selected uploads from queue?"):
            for item_id in selected_items:
                # Get upload item and remove it
                # This would need to be implemented with the queue system
                pass
    
    def _clear_completed(self):
        """Clear completed uploads from queue display."""
        self.upload_queue.clear_completed()
        self._update_queue_display()
        logger.info("Cleared completed uploads")
    
    def _show_queue_context_menu(self, event):
        """Show context menu for queue items."""
        # This would show a context menu with pause/resume/cancel options
        pass
    
    def _update_queue_display(self):
        """Update the queue display."""
        # Clear existing items
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Add queue items
        for upload_item in self.upload_queue.queue:
            size_mb = upload_item.file_size / (1024 * 1024)
            self.queue_tree.insert("", "end", text=upload_item.file_name,
                                 values=(upload_item.status.value, 
                                        f"{upload_item.progress:.1f}%",
                                        f"{size_mb:.1f} MB"))
        
        # Schedule next update
        self.app.after(1000, self._update_queue_display)
    
    def _on_upload_progress(self, upload_item: UploadItem):
        """Handle upload progress updates."""
        # Update progress display
        pass
    
    def _on_upload_status_change(self, upload_item: UploadItem):
        """Handle upload status changes."""
        # Update queue display
        pass
    
    def _on_upload_complete(self, upload_item: UploadItem):
        """Handle upload completion."""
        logger.info(f"Upload completed: {upload_item.file_name}")
    
    def _on_upload_error(self, upload_item: UploadItem, error: Exception):
        """Handle upload errors."""
        logger.error(f"Upload failed: {upload_item.file_name} - {error}")
    
    def _check_auth_status(self):
        """Check if user is authenticated and update UI accordingly."""
        try:
            # Check if we have any channels (indicates authentication)
            channels = self.channel_manager.get_all_channels()
            if channels:
                # User is authenticated
                self.profile_dropdown.update_display()
                self._setup_channel_selector()
                logger.info("User is authenticated")
            else:
                # User is not authenticated
                self.profile_dropdown.update_display()
                self.channel_combobox['values'] = []
                self.channel_var.set("")
                logger.info("User is not authenticated")
        except Exception as e:
            logger.error(f"Error checking auth status: {e}")
            self.profile_dropdown.update_display()
    
    def _authenticate_user(self):
        logger.debug("[EnhancedShadowPlayUploader] _authenticate_user called.")
        try:
            active_channel = self.channel_manager.get_active_channel()
            if active_channel:
                logger.debug("[EnhancedShadowPlayUploader] User is already authenticated, logging out.")
                self._logout_user()
            else:
                logger.info("Starting authentication process...")
                self.profile_dropdown.update_display()
                def auth_thread():
                    logger.debug("[EnhancedShadowPlayUploader] Starting OAuth thread for authentication.")
                    try:
                        channels = self.channel_manager.discover_channels()
                        if channels:
                            self.app.after(0, lambda: self._auth_success(channels))
                        else:
                            self.app.after(0, lambda: self._auth_failed("No channels found"))
                    except Exception as auth_error:
                        self.app.after(0, lambda err=auth_error: self._auth_failed(str(err)))
                threading.Thread(target=auth_thread, daemon=True).start()
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self._auth_failed(str(e))
    
    def _auth_success(self, channels):
        """Handle successful authentication."""
        try:
            logger.info(f"Authentication successful. Found {len(channels)} channels.")
            
            # Set first channel as active if none selected
            if channels:
                first_channel = channels[0]
                self.channel_manager.set_active_channel(first_channel.channel_id)
                channel_name = f"{first_channel.channel_title} ({first_channel.channel_id})"
                self.channel_var.set(channel_name)
            
            # Update UI components
            self.profile_dropdown.update_display()
            self._setup_channel_selector()
            
            # Show success message
            messagebox.showinfo("Success", f"Authentication successful!\nFound {len(channels)} YouTube channel(s).")
            
            # Re-open dropdown to show updated state
            if not self.profile_dropdown.dropdown_open:
                self.profile_dropdown._show_dropdown()
            
        except Exception as e:
            logger.error(f"Error in auth success: {e}")
            self._auth_failed(str(e))
    
    def _auth_failed(self, error_msg):
        """Handle failed authentication."""
        self.profile_dropdown.update_display()
        logger.error(f"Authentication failed: {error_msg}")
        messagebox.showerror("Authentication Failed", f"Failed to authenticate:\n{error_msg}")
    
    def _logout_user(self):
        """Handle user logout."""
        try:
            # Clear channels
            self.channel_manager.channels.clear()
            self.channel_manager.channel_settings.clear()
            self.channel_manager.active_channel_id = None
            
            # Update UI
            self.profile_dropdown.update_display()
            self.channel_combobox['values'] = []
            self.channel_var.set("")
            
            logger.info("User logged out")
            messagebox.showinfo("Logged Out", "Successfully logged out.")
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
    
    def _refresh_channels(self):
        """Refresh the list of available channels."""
        try:
            logger.info("Refreshing channels...")
            self.profile_dropdown.update_display()
            
            def refresh_thread():
                try:
                    channels = self.channel_manager.discover_channels()
                    self.app.after(0, lambda: self._refresh_success(channels))
                except Exception as refresh_error:
                    self.app.after(0, lambda err=refresh_error: self._refresh_failed(str(err)))
            
            threading.Thread(target=refresh_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error refreshing channels: {e}")
            self.profile_dropdown.update_display()
    
    def _refresh_success(self, channels):
        """Handle successful channel refresh."""
        try:
            self._setup_channel_selector()
            logger.info(f"Refreshed {len(channels)} channels")
            messagebox.showinfo("Success", f"Refreshed {len(channels)} channels.")
        except Exception as e:
            logger.error(f"Error in refresh success: {e}")
            self.profile_dropdown.update_display()
    
    def _refresh_failed(self, error_msg):
        """Handle failed channel refresh."""
        self.profile_dropdown.update_display()
        logger.error(f"Channel refresh failed: {error_msg}")
        messagebox.showerror("Refresh Failed", f"Failed to refresh channels:\n{error_msg}")
    
    def run(self):
        """Run the application."""
        self.app.mainloop()

def main():
    """Main entry point."""
    try:
        app = EnhancedShadowPlayUploader()
        app.run()
    except Exception as e:
        logger.log_exception("Application failed to start", e)
        messagebox.showerror("Startup Error", f"Failed to start application: {e}")

if __name__ == "__main__":
    main() 