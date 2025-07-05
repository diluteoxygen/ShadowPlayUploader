import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from typing import Optional, Any
import tkinter as tk

class AppLogger:
    """
    Comprehensive logging system for ShadowPlay Batch Uploader.
    Handles file logging, console output, and GUI log display.
    """
    
    def __init__(self, log_file: str = "app.log", max_bytes: int = 1024*1024, backup_count: int = 5):
        """
        Initialize the logger with file rotation and multiple handlers.
        
        Args:
            log_file: Path to the log file
            max_bytes: Maximum size of log file before rotation (1MB default)
            backup_count: Number of backup log files to keep
        """
        self.log_file = log_file
        self.logger = logging.getLogger('ShadowPlayUploader')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler with rotation
        self.file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
        )
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(detailed_formatter)
        
        # Console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(logging.INFO)
        self.console_handler.setFormatter(simple_formatter)
        
        # Add handlers
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)
        
        # GUI log box (will be set later)
        self.gui_log_box: Optional[tk.Text] = None
        
        self.logger.info("=== ShadowPlay Batch Uploader Started ===")
        self.logger.info(f"Log file: {os.path.abspath(log_file)}")
    
    def close(self):
        """Close all handlers and cleanup."""
        try:
            if hasattr(self, 'file_handler'):
                self.file_handler.close()
            if hasattr(self, 'console_handler'):
                self.console_handler.close()
            self.logger.handlers.clear()
        except Exception as e:
            print(f"Error closing logger: {e}")
    
    def __del__(self):
        """Destructor to ensure handlers are closed."""
        self.close()
    
    def set_gui_log_box(self, log_box: tk.Text):
        """Set the GUI text widget for log display."""
        self.gui_log_box = log_box
    
    def _format_gui_message(self, level: str, message: str) -> str:
        """Format message for GUI display with emojis and colors."""
        emoji_map = {
            'DEBUG': '🔍',
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        emoji = emoji_map.get(level, '📝')
        return f"{emoji} {message}"
    
    def _update_gui(self, level: str, message: str):
        """Update GUI log box if available."""
        if self.gui_log_box:
            try:
                formatted_msg = self._format_gui_message(level, message)
                self.gui_log_box.insert(tk.END, formatted_msg + "\n")
                self.gui_log_box.see(tk.END)
                # Force GUI update
                self.gui_log_box.update_idletasks()
            except Exception as e:
                # Fallback to console if GUI update fails
                print(f"GUI log update failed: {e}")
    
    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)
        self._update_gui('DEBUG', message)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
        self._update_gui('INFO', message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)
        self._update_gui('WARNING', message)
    
    def error(self, message: str, exc_info: Optional[Exception] = None):
        """Log error message with optional exception info."""
        if exc_info:
            self.logger.error(f"{message}: {exc_info}", exc_info=True)
            self._update_gui('ERROR', f"{message}: {exc_info}")
        else:
            self.logger.error(message)
            self._update_gui('ERROR', message)
    
    def critical(self, message: str, exc_info: Optional[Exception] = None):
        """Log critical error message."""
        if exc_info:
            self.logger.critical(f"{message}: {exc_info}", exc_info=True)
            self._update_gui('CRITICAL', f"{message}: {exc_info}")
        else:
            self.logger.critical(message)
            self._update_gui('CRITICAL', message)
    
    def log_exception(self, message: str, exception: Exception):
        """Log exception with full traceback."""
        self.logger.exception(f"{message}: {exception}")
        self._update_gui('ERROR', f"{message}: {exception}")
    
    def log_upload_progress(self, filename: str, percent: int, uploaded_mb: float, total_mb: float):
        """Log upload progress with formatted message."""
        message = f"Uploading {filename}: {percent}% ({uploaded_mb:.1f} MB / {total_mb:.1f} MB)"
        self.info(message)
    
    def log_upload_success(self, filename: str):
        """Log successful upload."""
        self.info(f"✅ Successfully uploaded: {filename}")
    
    def log_upload_failure(self, filename: str, error: str):
        """Log upload failure."""
        self.error(f"❌ Upload failed for {filename}: {error}")
    
    def log_file_operation(self, operation: str, filename: str, success: bool, error: str = None):
        """Log file operations (delete, move, etc.)."""
        if success:
            self.info(f"🗑️ {operation}: {filename}")
        else:
            self.error(f"❌ {operation} failed for {filename}: {error}")
    
    def log_api_operation(self, operation: str, success: bool, error: str = None):
        """Log API operations."""
        if success:
            self.info(f"🔗 API {operation}: Success")
        else:
            self.error(f"🔗 API {operation} failed: {error}")
    
    def clear_gui_log(self):
        """Clear the GUI log display."""
        if self.gui_log_box:
            try:
                self.gui_log_box.delete("1.0", tk.END)
            except Exception as e:
                print(f"Failed to clear GUI log: {e}")

# Global logger instance
app_logger = AppLogger()

def get_logger() -> AppLogger:
    """Get the global logger instance."""
    return app_logger 