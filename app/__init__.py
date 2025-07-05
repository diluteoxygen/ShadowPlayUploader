"""
ShadowPlay Batch Uploader - Main Application Package

This package contains all the core modules for the ShadowPlay Batch Uploader application.
"""

__version__ = "2.0.0"
__author__ = "ShadowPlay Uploader Team"

# Import main components for easy access
from .main_enhanced import main
from .uploader_batch import start_batch_upload
from .upload_queue import UploadQueue, UploadItem, UploadStatus
from .channel_manager import ChannelManager, ChannelInfo, ChannelSettings
from .upload_presets import PresetManager, UploadPreset, DescriptionTemplate
from .config import Config, get_config
from .logger import get_logger
from .exceptions import *

__all__ = [
    'main',
    'start_batch_upload',
    'UploadQueue',
    'UploadItem', 
    'UploadStatus',
    'ChannelManager',
    'ChannelInfo',
    'ChannelSettings',
    'PresetManager',
    'UploadPreset',
    'DescriptionTemplate',
    'Config',
    'get_config',
    'get_logger'
] 