import tkinter as tk
from tkinter import ttk
import sv_ttk
from tkinter import filedialog, messagebox, Menu, Toplevel
from typing import Optional, Dict, Any
import requests
from PIL import Image, ImageTk, ImageDraw
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
        self.profile_frame = ttk.Frame(parent)
        self.profile_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create circular profile button
        self.profile_btn = ttk.Button(
            self.profile_frame, 
            text="👤", 
            width=3,
            command=self._toggle_dropdown
        )
        self.profile_btn.pack(side=tk.TOP, pady=5)
        
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
        
        # Add rounded corners and shadow effect
        self.dropdown_win.attributes("-alpha", 0.95)
        
        x = self.profile_frame.winfo_rootx()
        y = self.profile_frame.winfo_rooty() + self.profile_frame.winfo_height()
        # Let Tkinter size the window, only set position after packing
        self.dropdown_win.minsize(240, 220)
        self.dropdown_open = True
        # --- NEW: Bind a global click to close dropdown if click is outside ---
        def close_if_outside(event):
            # If click is not inside dropdown_win, close it
            if not (self.dropdown_win.winfo_rootx() <= event.x_root <= self.dropdown_win.winfo_rootx() + self.dropdown_win.winfo_width() and
                    self.dropdown_win.winfo_rooty() <= event.y_root <= self.dropdown_win.winfo_rooty() + self.dropdown_win.winfo_height()):
                self._hide_dropdown()
        self._dropdown_click_binding = self.parent.bind_all("<Button-1>", close_if_outside, add="+")
        # --- END NEW ---
        self.dropdown_win.bind("<FocusOut>", lambda e: self._hide_dropdown())
        self.dropdown_win.grab_set()
        
        # Main frame with increased padding and rounded styling
        frame = ttk.Frame(self.dropdown_win, padding=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.status_label = ttk.Label(
            frame, 
            text="Not authenticated", 
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.status_label.pack(pady=(0, 10), padx=0)
        channel_info_frame = ttk.Frame(frame)
        channel_info_frame.pack(fill=tk.X, padx=0, pady=10)
        self.logo_label = ttk.Label(channel_info_frame, text="")
        self.logo_label.pack(side=tk.LEFT, padx=(0, 10))
        self.channel_name_label = ttk.Label(
            channel_info_frame, 
            text="", 
            font=("Segoe UI", 10, "bold")
        )
        self.channel_name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 0))
        self.login_btn = ttk.Button(
            buttons_frame,
            text="🔑 Login"
        )
        self.login_btn.pack(fill=tk.X, pady=4, padx=4)
        self.login_btn.bind("<Button-1>", lambda e: self._login())
        
        self.logout_btn = ttk.Button(
            buttons_frame,
            text="🚪 Logout",
            state=tk.DISABLED
        )
        self.logout_btn.pack(fill=tk.X, pady=4, padx=4)
        self.logout_btn.bind("<Button-1>", lambda e: self._logout())
        
        self.refresh_btn = ttk.Button(
            buttons_frame,
            text="🔄 Refresh",
            state=tk.DISABLED
        )
        self.refresh_btn.pack(fill=tk.X, pady=4, padx=4)
        self.refresh_btn.bind("<Button-1>", lambda e: self._refresh())
        self._update_state()
        self.dropdown_win.update_idletasks()
        self.dropdown_win.geometry(f"+{x}+{y}")
    
    def _hide_dropdown(self):
        if self.dropdown_open and self.dropdown_win:
            self.dropdown_win.grab_release()
            self.dropdown_win.destroy()
            self.dropdown_win = None
            self.dropdown_open = False
            self.login_btn = None
            self.logout_btn = None
            self.refresh_btn = None
            # --- NEW: Unbind the global click handler ---
            if hasattr(self, '_dropdown_click_binding'):
                self.parent.unbind_all("<Button-1>")
                del self._dropdown_click_binding
            # --- END NEW ---
    
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
            
            # Create circular mask for profile image
            size = (32, 32)
            mask = Image.new('L', size, 0)
            
            # Create circular mask
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size[0], size[1]), fill=255)
            
            # Apply mask to create circular image
            output = Image.new('RGBA', size, (0, 0, 0, 0))
            output.paste(image.resize(size, Image.Resampling.LANCZOS), (0, 0))
            output.putalpha(mask)
            
            self.profile_photo = ImageTk.PhotoImage(output)
            self.dropdown_logo_photo = ImageTk.PhotoImage(output)
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
            self.login_btn.configure(state=tk.DISABLED)
            self.logout_btn.configure(state=tk.NORMAL)
            self.refresh_btn.configure(state=tk.NORMAL)
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
            self.login_btn.configure(state=tk.NORMAL)
            self.logout_btn.configure(state=tk.DISABLED)
            self.refresh_btn.configure(state=tk.DISABLED)
    
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
        window_width = ui_settings["window_width"]
        window_height = ui_settings["window_height"]
        
        # Create main window
        self.app = tk.Tk()
        sv_ttk.set_theme("dark")  # Apply Sun Valley theme (dark by default)
        self.app.title("ShadowPlay Batch Uploader - Enhanced")
        self.app.geometry(f"{window_width}x{window_height}")
        self.app.resizable(True, True)
        
        # Variables
        self.folder_var = tk.StringVar()
        self.channel_var = tk.StringVar()
        self.preset_var = tk.StringVar()
        self.progress_var = tk.IntVar()
        self.file_progress_var = tk.StringVar()
        self.mb_progress_var = tk.StringVar()
        self.auto_delete_var = tk.BooleanVar(value=ui_settings["auto_delete"])
        self.dark_mode_var = tk.BooleanVar(value=ui_settings["dark_mode"])
        
        # Create GUI
        self._create_gui()
        self._setup_preset_selector()
        
        # Set up logger
        logger.set_gui_log_box(self.log_box)
        
        # --- NEW: Auto-authenticate if token exists ---
        self._auto_authenticate_on_startup()
        # --- END NEW ---
        
        logger.info("Enhanced ShadowPlay Uploader started")
    
    def _create_gui(self):
        """Create the minimal GUI layout."""
        main_frame = ttk.Frame(self.app, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Header: App title and profile icon
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        title_label = ttk.Label(header_frame, text="ShadowPlay Batch Uploader", font=("Segoe UI", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        self.profile_dropdown = ProfileDropdown(header_frame, self.channel_manager, self._on_auth_action)
        # Folder selection
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(fill=tk.X, pady=(10, 10))
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=50)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(folder_frame, text="Browse", command=self._browse_folder).pack(side=tk.LEFT)
        # Preset dropdown
        preset_frame = ttk.Frame(main_frame)
        preset_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(preset_frame, text="Upload Preset:").pack(anchor=tk.W)
        self.preset_combobox = ttk.Combobox(preset_frame, textvariable=self.preset_var, state="readonly")
        self.preset_combobox.pack(fill=tk.X, pady=2)
        # Start Upload button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        self.start_btn = ttk.Button(button_frame, text="Start Upload", command=self._start_upload)
        self.start_btn.pack(side=tk.LEFT)
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.overall_progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", variable=self.progress_var)
        self.overall_progress.pack(fill=tk.X)
        # Collapsible log output
        self.log_visible = False
        self.log_toggle_btn = ttk.Button(main_frame, text="Show Logs ▼", command=self._toggle_log)
        self.log_toggle_btn.pack(fill=tk.X, pady=(5, 0))
        self.log_frame = ttk.Frame(main_frame)
        self.log_box = tk.Text(self.log_frame, height=8, state="normal", wrap="word")
        self.log_box.pack(fill=tk.BOTH, expand=True)
        # Hide log frame by default
        self.log_frame.pack_forget()
    
    def _on_auth_action(self, action: str):
        logger.debug(f"[EnhancedShadowPlayUploader] _on_auth_action called with action: {action}")
        if action == "login":
            self._authenticate_user()
        elif action == "logout":
            self._logout_user()
        elif action == "refresh":
            self._refresh_channels()
    
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
    
    def _browse_folder(self):
        """Browse for folder selection."""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
    
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
        """Start uploading videos in the selected folder using the selected preset and the currently authenticated channel."""
        folder = self.folder_var.get()
        # Use the currently authenticated channel
        channel = self.channel_manager.get_active_channel()
        preset = self.preset_manager.get_preset(self.preset_var.get())
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder with .mp4 files.")
            return
        if not channel:
            messagebox.showerror("Error", "Please log in to a YouTube channel first.")
            return
        self._start_enhanced_upload(folder, channel, preset)
    
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
                logger.info("User is authenticated")
            else:
                # User is not authenticated
                self.profile_dropdown.update_display()
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
            # Call channel_manager logout to delete all tokens and clear state
            self.channel_manager.logout()
            # Update UI
            self.profile_dropdown.update_display()
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
    
    def _auto_authenticate_on_startup(self):
        """Automatically authenticate user if a valid token exists."""
        try:
            # Try to discover channels (will use token if present)
            channels = self.channel_manager.discover_channels()
            if channels:
                # Set first channel as active if not already
                if not self.channel_manager.active_channel_id:
                    self.channel_manager.set_active_channel(channels[0].channel_id)
                self.profile_dropdown.update_display()
                logger.info("Auto-authenticated user on startup.")
            else:
                self.profile_dropdown.update_display()
                logger.info("No channels found on startup; user not authenticated.")
        except Exception as e:
            logger.warning(f"Auto-authentication failed: {e}")
            self.profile_dropdown.update_display()
    
    def _toggle_log(self):
        if self.log_visible:
            self.log_frame.pack_forget()
            self.log_toggle_btn.config(text="Show Logs ▼")
            self.log_visible = False
        else:
            self.log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            self.log_toggle_btn.config(text="Hide Logs ▲")
            self.log_visible = True
    
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