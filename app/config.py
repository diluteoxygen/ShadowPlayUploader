import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from .logger import get_logger

logger = get_logger()

class Config:
    """
    Configuration management system for ShadowPlay Batch Uploader.
    Handles loading, saving, and validation of app settings.
    """
    
    DEFAULT_CONFIG = {
        "ui": {
            "theme": "flatly",
            "dark_mode": False,
            "window_width": 720,
            "window_height": 640,
            "auto_delete": True
        },
        "upload": {
            "privacy_status": "unlisted",
            "category_id": "20",
            "description_template": "Auto-uploaded ShadowPlay clip",
            "chunk_size_mb": 1,
            "max_retries": 3,
            "retry_delay": 2
        },
        "file_management": {
            "move_instead_of_delete": False,
            "uploaded_folder": "uploaded",
            "archive_old_files": False,
            "min_file_size_mb": 0,
            "max_file_size_mb": 0  # 0 means no limit
        },
        "logging": {
            "log_level": "INFO",
            "max_log_size_mb": 1,
            "backup_count": 5,
            "log_file": "app.log"
        },
        "api": {
            "scopes": [
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly"
            ],
            "token_file": "token.pickle",
            "client_secrets_file": "resources/client_secrets.json"
        },
        "paths": {
            "hash_log": "uploaded_hashes.txt",
            "config_file": "resources/config.json"
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize configuration system.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load configuration from file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self._merge_config(self.config, loaded_config)
                logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                logger.info("No configuration file found, using defaults")
                self.save_config()  # Save default config
                return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.debug(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]):
        """Recursively merge loaded config with defaults."""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., "ui.theme")
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        Set configuration value using dot notation.
        
        Args:
            key_path: Configuration key path (e.g., "ui.theme")
            value: Value to set
            
        Returns:
            True if set successfully, False otherwise
        """
        try:
            keys = key_path.split('.')
            config = self.config
            
            # Navigate to the parent of the target key
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # Set the value
            config[keys[-1]] = value
            logger.debug(f"Configuration updated: {key_path} = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set configuration {key_path}: {e}")
            return False
    
    def validate_config(self) -> Dict[str, list]:
        """
        Validate current configuration.
        
        Returns:
            Dictionary of validation errors by category
        """
        errors = {}
        
        # Validate UI settings
        ui_errors = []
        theme = self.get("ui.theme")
        if theme not in ["flatly", "superhero", "cosmo", "cyborg", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "simplex", "sketchy", "slate", "solar", "spacelab", "united", "yeti"]:
            ui_errors.append(f"Invalid theme: {theme}")
        
        if ui_errors:
            errors["ui"] = ui_errors
        
        # Validate upload settings
        upload_errors = []
        privacy = self.get("upload.privacy_status")
        if privacy not in ["private", "unlisted", "public"]:
            upload_errors.append(f"Invalid privacy status: {privacy}")
        
        chunk_size = self.get("upload.chunk_size_mb")
        if not isinstance(chunk_size, (int, float)) or chunk_size <= 0:
            upload_errors.append(f"Invalid chunk size: {chunk_size}")
        
        if upload_errors:
            errors["upload"] = upload_errors
        
        # Validate file management settings
        file_errors = []
        min_size = self.get("file_management.min_file_size_mb")
        max_size = self.get("file_management.max_file_size_mb")
        
        if not isinstance(min_size, (int, float)) or min_size < 0:
            file_errors.append(f"Invalid minimum file size: {min_size}")
        
        if not isinstance(max_size, (int, float)) or max_size < 0:
            file_errors.append(f"Invalid maximum file size: {max_size}")
        
        if min_size > 0 and max_size > 0 and min_size > max_size:
            file_errors.append("Minimum file size cannot be greater than maximum file size")
        
        if file_errors:
            errors["file_management"] = file_errors
        
        return errors
    
    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values.
        
        Returns:
            True if reset successfully, False otherwise
        """
        try:
            self.config = self.DEFAULT_CONFIG.copy()
            self.save_config()
            logger.info("Configuration reset to defaults")
            return True
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")
            return False
    
    def get_upload_settings(self) -> Dict[str, Any]:
        """Get upload-related configuration."""
        return {
            "privacy_status": self.get("upload.privacy_status"),
            "category_id": self.get("upload.category_id"),
            "description_template": self.get("upload.description_template"),
            "chunk_size_mb": self.get("upload.chunk_size_mb"),
            "max_retries": self.get("upload.max_retries"),
            "retry_delay": self.get("upload.retry_delay")
        }
    
    def get_ui_settings(self) -> Dict[str, Any]:
        """Get UI-related configuration."""
        return {
            "theme": self.get("ui.theme"),
            "dark_mode": self.get("ui.dark_mode"),
            "window_width": self.get("ui.window_width"),
            "window_height": self.get("ui.window_height"),
            "auto_delete": self.get("ui.auto_delete")
        }
    
    def get_file_management_settings(self) -> Dict[str, Any]:
        """Get file management configuration."""
        return {
            "move_instead_of_delete": self.get("file_management.move_instead_of_delete"),
            "uploaded_folder": self.get("file_management.uploaded_folder"),
            "archive_old_files": self.get("file_management.archive_old_files"),
            "min_file_size_mb": self.get("file_management.min_file_size_mb"),
            "max_file_size_mb": self.get("file_management.max_file_size_mb")
        }

# Global configuration instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config 