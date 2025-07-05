import os
import pickle
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

from .logger import get_logger
from .config import get_config
from .exceptions import AuthenticationError, YouTubeAPIError

logger = get_logger()
config = get_config()

@dataclass
class ChannelInfo:
    """Information about a YouTube channel."""
    channel_id: str
    channel_title: str
    channel_description: str = ""
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    custom_url: str = ""
    country: str = ""
    language: str = ""
    is_verified: bool = False
    is_brand_account: bool = False
    thumbnail_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelInfo':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class ChannelSettings:
    """Channel-specific upload settings."""
    channel_id: str
    privacy_status: str = "unlisted"
    category_id: str = "20"
    description_template: str = "Auto-uploaded ShadowPlay clip"
    tags: List[str] = None
    playlist_id: Optional[str] = None
    auto_thumbnail: bool = False
    custom_thumbnail_path: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelSettings':
        """Create from dictionary."""
        return cls(**data)

class ChannelManager:
    """Manages multiple YouTube channels and their settings."""
    
    def __init__(self, client_secrets_file: str = None):
        """
        Initialize the channel manager.
        
        Args:
            client_secrets_file: Path to the client secrets file (uses config if None)
        """
        if client_secrets_file is None:
            self.client_secrets_file = config.get("api.client_secrets_file")
        else:
            self.client_secrets_file = client_secrets_file
        self.channels: Dict[str, ChannelInfo] = {}
        self.channel_settings: Dict[str, ChannelSettings] = {}
        self.active_channel_id: Optional[str] = None
        self.credentials_cache: Dict[str, Any] = {}
        
        # File paths
        self.channels_file = "resources/channels.json"
        self.settings_file = "resources/channel_settings.json"
        self.tokens_dir = "tokens"
        
        # Create tokens directory if it doesn't exist
        os.makedirs(self.tokens_dir, exist_ok=True)
        
        # Load existing data
        self._load_channels()
        self._load_settings()
        
        logger.info("Channel manager initialized")
    
    def _load_channels(self):
        """Load channel information from file."""
        try:
            if os.path.exists(self.channels_file):
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.channels = {
                        channel_id: ChannelInfo.from_dict(channel_data)
                        for channel_id, channel_data in data.items()
                    }
                logger.info(f"Loaded {len(self.channels)} channels from {self.channels_file}")
        except Exception as e:
            logger.warning(f"Failed to load channels: {e}")
    
    def _save_channels(self):
        """Save channel information to file."""
        try:
            data = {
                channel_id: channel.to_dict()
                for channel_id, channel in self.channels.items()
            }
            with open(self.channels_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.channels)} channels to {self.channels_file}")
        except Exception as e:
            logger.error(f"Failed to save channels: {e}")
    
    def _load_settings(self):
        """Load channel settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.channel_settings = {
                        channel_id: ChannelSettings.from_dict(settings_data)
                        for channel_id, settings_data in data.items()
                    }
                logger.info(f"Loaded settings for {len(self.channel_settings)} channels")
        except Exception as e:
            logger.warning(f"Failed to load channel settings: {e}")
    
    def _save_settings(self):
        """Save channel settings to file."""
        try:
            data = {
                channel_id: settings.to_dict()
                for channel_id, settings in self.channel_settings.items()
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved settings for {len(self.channel_settings)} channels")
        except Exception as e:
            logger.error(f"Failed to save channel settings: {e}")
    
    def _get_token_file(self, channel_id: str) -> str:
        """Get the token file path for a channel."""
        return os.path.join(self.tokens_dir, f"token_{channel_id}.pickle")
    
    def discover_channels(self) -> List[ChannelInfo]:
        """
        Discover available YouTube channels for the authenticated user.
        
        Returns:
            List of available channels
        """
        logger.debug("[ChannelManager] discover_channels called. About to authenticate and get service.")
        try:
            youtube = self._authenticate_and_get_service()
            logger.debug("[ChannelManager] Got YouTube service, requesting channel list.")
            response = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                mine=True
            ).execute()
            logger.debug(f"[ChannelManager] Channel list response: {response}")
            channels = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                statistics = item.get('statistics', {})
                branding = item.get('brandingSettings', {})
                channel_info = ChannelInfo(
                    channel_id=item['id'],
                    channel_title=snippet.get('title', ''),
                    channel_description=snippet.get('description', ''),
                    subscriber_count=int(statistics.get('subscriberCount', 0)),
                    video_count=int(statistics.get('videoCount', 0)),
                    view_count=int(statistics.get('viewCount', 0)),
                    custom_url=snippet.get('customUrl', ''),
                    country=snippet.get('country', ''),
                    language=snippet.get('defaultLanguage', ''),
                    is_verified=snippet.get('verified', False),
                    is_brand_account=snippet.get('brandingSettings', {}).get('channel', {}).get('isDefaultBrandAccount', False),
                    thumbnail_url=snippet.get('thumbnails', {}).get('default', {}).get('url', '')
                )
                channels.append(channel_info)
                
                # Add to internal storage
                self.channels[channel_info.channel_id] = channel_info
                
                # Create default settings if not exists
                if channel_info.channel_id not in self.channel_settings:
                    self.channel_settings[channel_info.channel_id] = ChannelSettings(
                        channel_id=channel_info.channel_id
                    )
            
            # Save discovered channels
            self._save_channels()
            self._save_settings()
            
            logger.debug(f"[ChannelManager] Discovered and saved {len(channels)} channels.")
            return channels
        except Exception as e:
            logger.error(f"[ChannelManager] Failed to discover channels: {e}")
            raise
    
    def get_channel(self, channel_id: str) -> Optional[ChannelInfo]:
        """Get channel information by ID."""
        return self.channels.get(channel_id)
    
    def get_all_channels(self) -> List[ChannelInfo]:
        """Get all available channels."""
        return list(self.channels.values())
    
    def set_active_channel(self, channel_id: str) -> bool:
        """
        Set the active channel for uploads.
        
        Args:
            channel_id: ID of the channel to activate
            
        Returns:
            True if successful, False otherwise
        """
        if channel_id in self.channels:
            self.active_channel_id = channel_id
            logger.info(f"Set active channel: {self.channels[channel_id].channel_title}")
            return True
        else:
            logger.warning(f"Channel not found: {channel_id}")
            return False
    
    def get_active_channel(self) -> Optional[ChannelInfo]:
        """Get the currently active channel."""
        if self.active_channel_id:
            return self.channels.get(self.active_channel_id)
        return None
    
    def get_channel_settings(self, channel_id: str) -> Optional[ChannelSettings]:
        """Get settings for a specific channel."""
        return self.channel_settings.get(channel_id)
    
    def update_channel_settings(self, channel_id: str, settings: ChannelSettings):
        """Update settings for a specific channel."""
        self.channel_settings[channel_id] = settings
        self._save_settings()
        logger.info(f"Updated settings for channel: {channel_id}")
    
    def get_active_channel_settings(self) -> Optional[ChannelSettings]:
        """Get settings for the active channel."""
        if self.active_channel_id:
            return self.channel_settings.get(self.active_channel_id)
        return None
    
    def logout(self):
        """Log out the user by deleting all token files and clearing state."""
        # Delete all token files in tokens/
        for fname in os.listdir(self.tokens_dir):
            if fname.startswith("token_") and fname.endswith(".pickle"):
                try:
                    os.remove(os.path.join(self.tokens_dir, fname))
                except Exception as e:
                    logger.warning(f"Failed to delete token file {fname}: {e}")
        # Also delete the main token file if it exists
        main_token = config.get("api.token_file")
        if os.path.exists(main_token):
            try:
                os.remove(main_token)
            except Exception as e:
                logger.warning(f"Failed to delete main token file: {e}")
        # Clear in-memory state
        self.channels.clear()
        self.channel_settings.clear()
        self.active_channel_id = None
        self.credentials_cache.clear()
    
    def _authenticate_and_get_service(self):
        logger.debug("[ChannelManager] _authenticate_and_get_service called. This is where OAuth browser should launch if needed.")
        try:
            # Use the main token file in tokens/ for initial authentication
            token_file = config.get("api.token_file")
            creds = None
            if os.path.exists(token_file):
                try:
                    with open(token_file, 'rb') as token:
                        creds = pickle.load(token)
                    logger.debug("Loaded existing credentials from main token file")
                except Exception as e:
                    logger.warning(f"Failed to load existing token: {e}")
                    creds = None

            # Refresh or authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired credentials")
                        creds.refresh(Request())
                    except RefreshError:
                        logger.warning("Failed to refresh credentials, re-authenticating")
                        creds = None
                
                if not creds:
                    # Start OAuth flow
                    logger.info("Starting OAuth flow for channel discovery")
                    scopes = config.get("api.scopes")
                    flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, scopes)
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth authentication completed")
                
                # Save credentials
                try:
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info("Credentials saved successfully")
                except Exception as e:
                    logger.error(f"Failed to save credentials: {e}")

            return build("youtube", "v3", credentials=creds)
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationError(f"Failed to authenticate: {e}")

    def _get_authenticated_service(self, channel_id: Optional[str] = None):
        """Get authenticated YouTube service for a specific channel."""
        try:
            # Use active channel if none specified
            if channel_id is None:
                channel_id = self.active_channel_id
            
            if not channel_id:
                raise AuthenticationError("No active channel selected")
            
            # Check if we have cached credentials
            if channel_id in self.credentials_cache:
                creds = self.credentials_cache[channel_id]
                if creds and creds.valid:
                    return build("youtube", "v3", credentials=creds)
            
            # Load credentials from file
            token_file = self._get_token_file(channel_id)
            creds = None
            
            if os.path.exists(token_file):
                try:
                    with open(token_file, 'rb') as token:
                        creds = pickle.load(token)
                    logger.debug(f"Loaded credentials for channel: {channel_id}")
                except Exception as e:
                    logger.warning(f"Failed to load credentials for {channel_id}: {e}")
            
            # Refresh or authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info(f"Refreshed credentials for channel: {channel_id}")
                    except RefreshError:
                        logger.warning(f"Failed to refresh credentials for {channel_id}, re-authenticating")
                        creds = None
                
                if not creds:
                    # Start OAuth flow
                    scopes = config.get("api.scopes")
                    flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, scopes)
                    creds = flow.run_local_server(port=0)
                    logger.info(f"Authenticated for channel: {channel_id}")
                
                # Save credentials
                try:
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.debug(f"Saved credentials for channel: {channel_id}")
                except Exception as e:
                    logger.warning(f"Failed to save credentials for {channel_id}: {e}")
            
            # Cache credentials
            self.credentials_cache[channel_id] = creds
            
            return build("youtube", "v3", credentials=creds)
            
        except Exception as e:
            logger.error(f"Authentication failed for channel {channel_id}: {e}")
            raise AuthenticationError(f"Failed to authenticate for channel {channel_id}: {e}")
    
    def upload_to_channel(self, channel_id: str, video_path: str, title: str = None, 
                         description: str = None, privacy: str = None) -> str:
        """
        Upload a video to a specific channel.
        
        Args:
            channel_id: ID of the channel to upload to
            video_path: Path to the video file
            title: Video title (uses filename if None)
            description: Video description
            privacy: Privacy status (private, unlisted, public)
            
        Returns:
            Video ID of the uploaded video
        """
        try:
            # Get channel settings
            settings = self.get_channel_settings(channel_id)
            if not settings:
                settings = ChannelSettings(channel_id=channel_id)
            
            # Get authenticated service for this channel
            youtube = self._get_authenticated_service(channel_id)
            
            # Prepare upload parameters
            if title is None:
                title = os.path.splitext(os.path.basename(video_path))[0]
            
            if description is None:
                description = settings.description_template
            
            if privacy is None:
                privacy = settings.privacy_status
            
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": settings.category_id,
                    "tags": settings.tags
                },
                "status": {"privacyStatus": privacy}
            }
            
            # Add to playlist if specified
            if settings.playlist_id:
                # Note: This would require additional API calls after upload
                logger.info(f"Video will be added to playlist: {settings.playlist_id}")
            
            # Upload video
            chunk_size = config.get("upload.chunk_size_mb", 1) * 1024 * 1024
            media = MediaFileUpload(video_path, chunksize=chunk_size, resumable=True)
            
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.debug(f"Upload progress: {status.resumable_progress}")
            
            video_id = response['id']
            logger.info(f"Successfully uploaded video {video_id} to channel {channel_id}")
            
            return video_id
            
        except Exception as e:
            logger.error(f"Failed to upload to channel {channel_id}: {e}")
            raise UploadError(f"Upload failed for channel {channel_id}: {e}")
    
    def remove_channel(self, channel_id: str) -> bool:
        """Remove a channel from the manager."""
        try:
            # Remove from storage
            if channel_id in self.channels:
                del self.channels[channel_id]
            
            if channel_id in self.channel_settings:
                del self.channel_settings[channel_id]
            
            if channel_id in self.credentials_cache:
                del self.credentials_cache[channel_id]
            
            # Remove token file
            token_file = self._get_token_file(channel_id)
            if os.path.exists(token_file):
                os.remove(token_file)
            
            # Update active channel if needed
            if self.active_channel_id == channel_id:
                self.active_channel_id = None
                if self.channels:
                    # Set first available channel as active
                    self.active_channel_id = next(iter(self.channels.keys()))
            
            # Save changes
            self._save_channels()
            self._save_settings()
            
            logger.info(f"Removed channel: {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove channel {channel_id}: {e}")
            return False
    
    def get_channel_statistics(self) -> Dict[str, Any]:
        """Get statistics for all channels."""
        stats = {
            'total_channels': len(self.channels),
            'active_channel': self.active_channel_id,
            'total_subscribers': 0,
            'total_videos': 0,
            'total_views': 0
        }
        
        for channel in self.channels.values():
            stats['total_subscribers'] += channel.subscriber_count
            stats['total_videos'] += channel.video_count
            stats['total_views'] += channel.view_count
        
        return stats 