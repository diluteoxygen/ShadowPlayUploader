import os
import threading
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Dict, Any

from .uploader_batch import start_batch_upload
from .logger import get_logger
from .config import get_config
from .exceptions import ShadowPlayUploaderError, format_error_for_user
from .upload_queue import UploadQueue, UploadItem, UploadStatus
from .channel_manager import ChannelManager, ChannelInfo
from .upload_presets import PresetManager, UploadPreset

logger = get_logger()
config = get_config()

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
        
        # Authentication section
        auth_frame = ttkb.LabelFrame(main_frame, text="🔐 Authentication & Channel", padding=10)
        auth_frame.pack(fill=X, pady=(0, 10))
        
        # Authentication status and login
        auth_status_frame = ttkb.Frame(auth_frame)
        auth_status_frame.pack(fill=X, pady=(0, 10))
        
        # Status label
        self.auth_status_var = ttkb.StringVar(value="Not authenticated")
        self.auth_status_label = ttkb.Label(auth_status_frame, textvariable=self.auth_status_var, 
                                           font=("Segoe UI", 9))
        self.auth_status_label.pack(side=LEFT, padx=(0, 10))
        
        # Login/Logout button
        self.auth_btn = ttkb.Button(auth_status_frame, text="🔑 Login", bootstyle=SUCCESS, 
                                   command=self._authenticate_user)
        self.auth_btn.pack(side=LEFT, padx=(0, 10))
        
        # Refresh channels button
        self.refresh_btn = ttkb.Button(auth_status_frame, text="🔄 Refresh Channels", bootstyle=INFO, 
                                     command=self._refresh_channels, state=DISABLED)
        self.refresh_btn.pack(side=LEFT)
        
        # Channel selector
        channel_frame = ttkb.Frame(auth_frame)
        channel_frame.pack(fill=X, pady=(0, 10))
        
        ttkb.Label(channel_frame, text="YouTube Channel:").pack(anchor=W)
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
        
        # Queue treeview
        self.queue_tree = ttk.Treeview(queue_frame, columns=("Status", "Progress", "Size"), 
                                      show="tree headings", height=8)
        self.queue_tree.heading("#0", text="File Name")
        self.queue_tree.heading("Status", text="Status")
        self.queue_tree.heading("Progress", text="Progress")
        self.queue_tree.heading("Size", text="Size")
        
        self.queue_tree.column("#0", width=300)
        self.queue_tree.column("Status", width=100)
        self.queue_tree.column("Progress", width=100)
        self.queue_tree.column("Size", width=100)
        
        # Scrollbar for queue
        queue_scrollbar = ttk.Scrollbar(queue_frame, orient=VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)
        
        self.queue_tree.pack(side=LEFT, fill=BOTH, expand=True)
        queue_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Queue control buttons
        queue_control_frame = ttkb.Frame(queue_frame)
        queue_control_frame.pack(fill=X, pady=(10, 0))
        
        ttkb.Button(queue_control_frame, text="Pause Selected", bootstyle=WARNING, 
                   command=self._pause_selected).pack(side=LEFT, padx=(0, 5))
        
        ttkb.Button(queue_control_frame, text="Resume Selected", bootstyle=SUCCESS, 
                   command=self._resume_selected).pack(side=LEFT, padx=(0, 5))
        
        ttkb.Button(queue_control_frame, text="Cancel Selected", bootstyle=DANGER, 
                   command=self._cancel_selected).pack(side=LEFT, padx=(0, 5))
        
        ttkb.Button(queue_control_frame, text="Clear Completed", bootstyle=SECONDARY, 
                   command=self._clear_completed).pack(side=LEFT)
        
        # Log section
        log_frame = ttkb.LabelFrame(main_frame, text="Upload Logs", padding=10)
        log_frame.pack(fill=BOTH, expand=True)
        
        self.log_box = ttkb.Text(log_frame, height=10, width=85)
        self.log_box.pack(expand=True, fill=BOTH)
    
    def _setup_channel_selector(self):
        """Set up the channel selector combobox."""
        try:
            # Get available channels
            channels = self.channel_manager.get_all_channels()
            
            if channels:
                # Populate combobox
                channel_names = [f"{ch.channel_title} ({ch.channel_id})" for ch in channels]
                self.channel_combobox['values'] = channel_names
                
                # Set active channel
                active_channel = self.channel_manager.get_active_channel()
                if active_channel:
                    active_name = f"{active_channel.channel_title} ({active_channel.channel_id})"
                    self.channel_var.set(active_name)
                elif channels:
                    # Set first channel as active if none selected
                    self.channel_manager.set_active_channel(channels[0].channel_id)
                    first_name = f"{channels[0].channel_title} ({channels[0].channel_id})"
                    self.channel_var.set(first_name)
                
                # Bind selection change
                self.channel_combobox.bind('<<ComboboxSelected>>', self._on_channel_changed)
                
                logger.info(f"Channel selector set up with {len(channels)} channels")
            else:
                # No channels available
                self.channel_combobox['values'] = []
                self.channel_var.set("")
                logger.info("No channels available for selection")
            
        except Exception as e:
            logger.error(f"Failed to setup channel selector: {e}")
            self.channel_combobox['values'] = []
            self.channel_var.set("")
    
    def _setup_preset_selector(self):
        """Set up the preset selector combobox."""
        try:
            # Get all presets
            presets = self.preset_manager.get_all_presets()
            preset_names = [preset.name for preset in presets]
            
            self.preset_combobox['values'] = preset_names
            
            # Set default preset
            default_preset = self.preset_manager.get_default_preset()
            if default_preset:
                self.preset_var.set(default_preset.name)
            
            # Bind selection change
            self.preset_combobox.bind('<<ComboboxSelected>>', self._on_preset_changed)
            
        except Exception as e:
            logger.error(f"Failed to setup preset selector: {e}")
    
    def _setup_queue_display(self):
        """Set up the queue display."""
        # Bind right-click menu
        self.queue_tree.bind("<Button-3>", self._show_queue_context_menu)
        
        # Update queue display periodically
        self._update_queue_display()
    
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
                self.auth_status_var.set("✅ Authenticated")
                self.auth_btn.config(text="🔓 Logout", bootstyle=DANGER)
                self.refresh_btn.config(state=NORMAL)
                self._setup_channel_selector()
                logger.info("User is authenticated")
            else:
                # User is not authenticated
                self.auth_status_var.set("❌ Not authenticated")
                self.auth_btn.config(text="🔑 Login", bootstyle=SUCCESS)
                self.refresh_btn.config(state=DISABLED)
                self.channel_combobox['values'] = []
                self.channel_var.set("")
                logger.info("User is not authenticated")
        except Exception as e:
            logger.error(f"Error checking auth status: {e}")
            self.auth_status_var.set("❌ Authentication error")
    
    def _authenticate_user(self):
        """Handle user authentication/login."""
        try:
            if self.auth_btn.cget("text") == "🔑 Login":
                # User wants to login
                logger.info("Starting authentication process...")
                self.auth_status_var.set("🔄 Authenticating...")
                self.auth_btn.config(state=DISABLED)
                
                # Start authentication in a separate thread
                def auth_thread():
                    try:
                        # Try to discover channels (this will trigger OAuth if needed)
                        channels = self.channel_manager.discover_channels()
                        if channels:
                            # Authentication successful
                            self.app.after(0, lambda: self._auth_success(channels))
                        else:
                            # Authentication failed
                            self.app.after(0, lambda: self._auth_failed("No channels found"))
                    except Exception as auth_error:
                        self.app.after(0, lambda err=auth_error: self._auth_failed(str(err)))
                
                threading.Thread(target=auth_thread, daemon=True).start()
                
            else:
                # User wants to logout
                self._logout_user()
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            self._auth_failed(str(e))
    
    def _auth_success(self, channels):
        """Handle successful authentication."""
        try:
            self.auth_status_var.set("✅ Authenticated")
            self.auth_btn.config(text="🔓 Logout", bootstyle=DANGER, state=NORMAL)
            self.refresh_btn.config(state=NORMAL)
            
            # Set up channel selector
            self._setup_channel_selector()
            
            # Set first channel as active if none selected
            if not self.channel_var.get() and channels:
                first_channel = channels[0]
                self.channel_manager.set_active_channel(first_channel.channel_id)
                channel_name = f"{first_channel.channel_title} ({first_channel.channel_id})"
                self.channel_var.set(channel_name)
            
            logger.info(f"Authentication successful. Found {len(channels)} channels.")
            messagebox.showinfo("Success", f"Authentication successful!\nFound {len(channels)} YouTube channel(s).")
            
        except Exception as e:
            logger.error(f"Error in auth success: {e}")
            self._auth_failed(str(e))
    
    def _auth_failed(self, error_msg):
        """Handle failed authentication."""
        self.auth_status_var.set("❌ Authentication failed")
        self.auth_btn.config(text="🔑 Login", bootstyle=SUCCESS, state=NORMAL)
        self.refresh_btn.config(state=DISABLED)
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
            self.auth_status_var.set("❌ Not authenticated")
            self.auth_btn.config(text="🔑 Login", bootstyle=SUCCESS)
            self.refresh_btn.config(state=DISABLED)
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
            self.refresh_btn.config(state=DISABLED)
            
            def refresh_thread():
                try:
                    channels = self.channel_manager.discover_channels()
                    self.app.after(0, lambda: self._refresh_success(channels))
                except Exception as refresh_error:
                    self.app.after(0, lambda err=refresh_error: self._refresh_failed(str(err)))
            
            threading.Thread(target=refresh_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error refreshing channels: {e}")
            self.refresh_btn.config(state=NORMAL)
    
    def _refresh_success(self, channels):
        """Handle successful channel refresh."""
        try:
            self._setup_channel_selector()
            self.refresh_btn.config(state=NORMAL)
            logger.info(f"Refreshed {len(channels)} channels")
            messagebox.showinfo("Success", f"Refreshed {len(channels)} channels.")
        except Exception as e:
            logger.error(f"Error in refresh success: {e}")
            self.refresh_btn.config(state=NORMAL)
    
    def _refresh_failed(self, error_msg):
        """Handle failed channel refresh."""
        self.refresh_btn.config(state=NORMAL)
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