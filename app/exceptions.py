"""
Custom exception classes for ShadowPlay Batch Uploader.
Provides specific exception types for different error scenarios.
"""

class ShadowPlayUploaderError(Exception):
    """Base exception class for all application errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

class AuthenticationError(ShadowPlayUploaderError):
    """Raised when authentication with YouTube API fails."""
    
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, "AUTH_ERROR", details)

class YouTubeAPIError(ShadowPlayUploaderError):
    """Raised when YouTube API operations fail."""
    
    def __init__(self, message: str, api_error: str = None, details: dict = None):
        super().__init__(message, "API_ERROR", details)
        self.api_error = api_error

class FileOperationError(ShadowPlayUploaderError):
    """Raised when file operations (read, write, delete) fail."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None, details: dict = None):
        super().__init__(message, "FILE_ERROR", details)
        self.file_path = file_path
        self.operation = operation

class ConfigurationError(ShadowPlayUploaderError):
    """Raised when configuration is invalid or cannot be loaded."""
    
    def __init__(self, message: str, config_key: str = None, details: dict = None):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key

class UploadError(ShadowPlayUploaderError):
    """Raised when video upload fails."""
    
    def __init__(self, message: str, video_path: str = None, retry_count: int = 0, details: dict = None):
        super().__init__(message, "UPLOAD_ERROR", details)
        self.video_path = video_path
        self.retry_count = retry_count

class NetworkError(ShadowPlayUploaderError):
    """Raised when network operations fail."""
    
    def __init__(self, message: str, url: str = None, status_code: int = None, details: dict = None):
        super().__init__(message, "NETWORK_ERROR", details)
        self.url = url
        self.status_code = status_code

class ValidationError(ShadowPlayUploaderError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None, value: any = None, details: dict = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value

class QuotaExceededError(YouTubeAPIError):
    """Raised when YouTube API quota is exceeded."""
    
    def __init__(self, message: str = "YouTube API quota exceeded", details: dict = None):
        super().__init__(message, "QUOTA_EXCEEDED", details)

class FileIncompleteError(FileOperationError):
    """Raised when a file is not complete (still being written)."""
    
    def __init__(self, file_path: str, message: str = None):
        if not message:
            message = f"File is incomplete or still being written: {file_path}"
        super().__init__(message, file_path, "check_completion")

class DuplicateFileError(FileOperationError):
    """Raised when attempting to upload a duplicate file."""
    
    def __init__(self, file_path: str, file_hash: str, message: str = None):
        if not message:
            message = f"File has already been uploaded: {file_path}"
        super().__init__(message, file_path, "duplicate_check")
        self.file_hash = file_hash

# Error code mappings for user-friendly messages
ERROR_MESSAGES = {
    "AUTH_ERROR": {
        "title": "Authentication Error",
        "description": "Failed to authenticate with YouTube. Please check your credentials and try again.",
        "solutions": [
            "Delete token.pickle and re-authenticate",
            "Check if client_secrets.json is valid",
            "Ensure YouTube Data API v3 is enabled"
        ]
    },
    "API_ERROR": {
        "title": "YouTube API Error",
        "description": "An error occurred while communicating with YouTube.",
        "solutions": [
            "Check your internet connection",
            "Verify YouTube API quota",
            "Try again in a few minutes"
        ]
    },
    "QUOTA_EXCEEDED": {
        "title": "API Quota Exceeded",
        "description": "You have exceeded your YouTube API quota for today.",
        "solutions": [
            "Wait until tomorrow for quota reset",
            "Check your Google Cloud Console for quota usage",
            "Consider upgrading your API quota"
        ]
    },
    "FILE_ERROR": {
        "title": "File Operation Error",
        "description": "An error occurred while processing files.",
        "solutions": [
            "Check file permissions",
            "Ensure files are not in use by other applications",
            "Verify disk space is available"
        ]
    },
    "UPLOAD_ERROR": {
        "title": "Upload Error",
        "description": "Failed to upload video to YouTube.",
        "solutions": [
            "Check file format (must be MP4)",
            "Verify file is not corrupted",
            "Try uploading a smaller file first"
        ]
    },
    "NETWORK_ERROR": {
        "title": "Network Error",
        "description": "Network connection failed.",
        "solutions": [
            "Check your internet connection",
            "Try again in a few minutes",
            "Check firewall settings"
        ]
    },
    "CONFIG_ERROR": {
        "title": "Configuration Error",
        "description": "Application configuration is invalid.",
        "solutions": [
            "Reset configuration to defaults",
            "Check config.json file format",
            "Reinstall the application"
        ]
    }
}

def get_error_info(error_code: str) -> dict:
    """Get user-friendly error information for an error code."""
    return ERROR_MESSAGES.get(error_code, {
        "title": "Unknown Error",
        "description": "An unexpected error occurred.",
        "solutions": ["Try restarting the application", "Check the log file for details"]
    })

def format_error_for_user(error: ShadowPlayUploaderError) -> str:
    """Format an error for user display."""
    error_info = get_error_info(error.error_code)
    
    message = f"{error_info['title']}\n\n"
    message += f"{error_info['description']}\n\n"
    
    if error.details:
        message += "Details:\n"
        for key, value in error.details.items():
            message += f"  {key}: {value}\n"
        message += "\n"
    
    message += "Possible solutions:\n"
    for i, solution in enumerate(error_info['solutions'], 1):
        message += f"  {i}. {solution}\n"
    
    return message 