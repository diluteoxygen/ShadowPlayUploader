import os
import time
import pickle
import hashlib
import shutil
from typing import Optional, Dict, Any
import tkinter as tk

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

from .logger import get_logger
from .config import get_config
from .exceptions import (
    AuthenticationError, YouTubeAPIError, FileOperationError, 
    UploadError, QuotaExceededError, FileIncompleteError, DuplicateFileError
)
from .retry import retry_operation, FILE_OPERATION_RETRY_CONFIG, API_RETRY_CONFIG

logger = get_logger()
config = get_config()

# Get configuration values
SCOPES = config.get("api.scopes")
TOKEN_FILE = config.get("api.token_file")
HASH_LOG = config.get("paths.hash_log")

def get_authenticated_service():
    """Get authenticated YouTube service with proper error handling."""
    try:
        creds = None
        client_secrets_file = config.get("api.client_secrets_file")
        
        if not os.path.exists(client_secrets_file):
            raise AuthenticationError(f"Client secrets file not found: {client_secrets_file}")
        
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
                logger.debug("Loaded existing credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                logger.info("Starting OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            try:
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Credentials saved successfully")
            except Exception as e:
                logger.error(f"Failed to save credentials: {e}")

        return build("youtube", "v3", credentials=creds)
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise AuthenticationError(f"Failed to authenticate: {e}")

def is_file_complete(path: str) -> bool:
    """Check if a file is complete (not being written to)."""
    try:
        prev = -1
        max_checks = 5
        check_interval = 1
        
        for check in range(max_checks):
            if not os.path.exists(path):
                logger.warning(f"File no longer exists: {path}")
                return False
            
            size = os.path.getsize(path)
            if size == prev:
                logger.debug(f"File appears complete: {path} (size: {size} bytes)")
                return True
            
            prev = size
            if check < max_checks - 1:  # Don't sleep on last iteration
                logger.debug(f"File still being written: {path} (size: {size} bytes), checking again...")
                time.sleep(check_interval)
        
        logger.warning(f"File may still be incomplete after {max_checks} checks: {path}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking file completion: {path} - {e}")
        return False

def hash_file(filepath: str) -> str:
    """Generate MD5 hash of a file."""
    try:
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read(65536)  # 64KB chunks
            while buf:
                hasher.update(buf)
                buf = f.read(65536)
        file_hash = hasher.hexdigest()
        logger.debug(f"Generated hash for {filepath}: {file_hash}")
        return file_hash
    except Exception as e:
        logger.error(f"Failed to hash file {filepath}: {e}")
        raise FileOperationError(f"Failed to hash file: {e}", filepath, "hash")

def handle_file_after_upload(file_path: str, file_name: str, auto_delete: bool = True) -> bool:
    """Handle file after successful upload (delete or move)."""
    try:
        if auto_delete:
            # Delete file with retry logic
            def delete_file():
                os.remove(file_path)
                return True
            
            retry_operation(delete_file, "Delete File", config=FILE_OPERATION_RETRY_CONFIG)
            logger.log_file_operation("Deleted", file_name, True)
            return True
        else:
            # Move file to uploaded folder
            uploaded_folder = config.get("file_management.uploaded_folder")
            if not os.path.exists(uploaded_folder):
                os.makedirs(uploaded_folder)
            
            destination = os.path.join(uploaded_folder, file_name)
            
            def move_file():
                shutil.move(file_path, destination)
                return True
            
            retry_operation(move_file, "Move File", config=FILE_OPERATION_RETRY_CONFIG)
            logger.log_file_operation("Moved", file_name, True)
            return True
            
    except Exception as e:
        logger.log_file_operation("File Operation", file_name, False, str(e))
        return False

def upload_video(file_path: str, youtube, channel_id: str, file_progress_var=None) -> bool:
    """Upload a video to YouTube with proper error handling and progress tracking."""
    try:
        # Get upload settings from config
        upload_settings = config.get_upload_settings()
        
        title = os.path.splitext(os.path.basename(file_path))[0]
        body = {
            "snippet": {
                "title": title,
                "description": upload_settings["description_template"],
                "categoryId": upload_settings["category_id"]
            },
            "status": {"privacyStatus": upload_settings["privacy_status"]}
        }

        file_size = os.path.getsize(file_path)
        chunk_size = upload_settings["chunk_size_mb"] * 1024 * 1024  # Convert MB to bytes
        media = MediaFileUpload(file_path, chunksize=chunk_size, resumable=True)

        logger.info(f"Starting upload: {title} ({file_size / (1024*1024):.1f} MB)")

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        uploaded_bytes = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    uploaded_bytes = status.resumable_progress
                    percent = int((uploaded_bytes / file_size) * 100)
                    uploaded_mb = round(uploaded_bytes / (1024 * 1024), 1)
                    total_mb = round(file_size / (1024 * 1024), 1)
                    
                    # Log progress
                    logger.log_upload_progress(title, percent, uploaded_mb, total_mb)
                    
                    # Update GUI progress
                    if file_progress_var:
                        msg = f"⏫ Uploading {title}: {percent}% ({uploaded_mb} MB / {total_mb} MB)"
                        file_progress_var.set(msg)
                        
            except HttpError as e:
                error_details = e.error_details[0] if e.error_details else {}
                reason = error_details.get('reason', 'Unknown')
                
                if 'quota' in reason.lower():
                    raise QuotaExceededError(f"YouTube API quota exceeded: {reason}")
                else:
                    raise YouTubeAPIError(f"YouTube API error: {reason}", str(e))
            except Exception as e:
                raise UploadError(f"Upload failed: {e}", file_path)

        logger.log_upload_success(title)
        return True
        
    except Exception as e:
        logger.log_upload_failure(os.path.basename(file_path), str(e))
        raise

def start_batch_upload(folder_path: str, log_box=None, channel_var=None, video_count_var=None, progress_var=None, file_progress_var=None, mb_progress_var=None):
    """Start batch upload process with comprehensive error handling and logging."""
    try:
        # Set up logger with GUI
        if log_box:
            logger.set_gui_log_box(log_box)
            logger.clear_gui_log()
        
        logger.info(f"=== Starting Batch Upload ===")
        logger.info(f"📂 Folder: {folder_path}")
        
        # Validate folder
        if not os.path.exists(folder_path):
            raise FileOperationError(f"Folder does not exist: {folder_path}", folder_path, "validate")
        
        if not os.path.isdir(folder_path):
            raise FileOperationError(f"Path is not a directory: {folder_path}", folder_path, "validate")
        
        # Get authenticated service
        logger.info("🔐 Authenticating with YouTube...")
        youtube = get_authenticated_service()
        
        # Get channel information
        try:
            response = retry_operation(
                youtube.channels().list(part="snippet", mine=True).execute,
                "Get Channel Info",
                config=API_RETRY_CONFIG
            )
            active_channel = response["items"][0]
            channel_id = active_channel["id"]
            channel_title = active_channel["snippet"]["title"]
            
            logger.info(f"📺 Channel: {channel_title}")
            if channel_var:
                channel_var.set(f"📺 Channel: {channel_title}")
                
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            raise YouTubeAPIError(f"Failed to get channel information: {e}")
        
        # Get file management settings
        file_settings = config.get_file_management_settings()
        auto_delete = config.get("ui.auto_delete", True)
        
        # Find MP4 files
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(".mp4")]
        total = len(files)
        
        logger.info(f"🎮 Found {total} MP4 file(s)")
        if video_count_var:
            video_count_var.set(f"🎮 Detected {total} video(s)")
        
        if total == 0:
            logger.warning("No MP4 files found in the selected folder")
            return
        
        # Load uploaded hashes
        uploaded_hashes = set()
        if os.path.exists(HASH_LOG):
            try:
                with open(HASH_LOG, 'r') as f:
                    uploaded_hashes = set(line.strip() for line in f if line.strip())
                logger.debug(f"Loaded {len(uploaded_hashes)} existing upload hashes")
            except Exception as e:
                logger.warning(f"Failed to load hash log: {e}")
        
        # Process files
        uploaded = 0
        skipped = 0
        failed = 0
        
        logger.info("🔄 Starting upload process...")
        
        for i, fname in enumerate(files, 1):
            fpath = os.path.join(folder_path, fname)
            
            try:
                # Check file size limits
                file_size_mb = os.path.getsize(fpath) / (1024 * 1024)
                min_size = file_settings["min_file_size_mb"]
                max_size = file_settings["max_file_size_mb"]
                
                if min_size > 0 and file_size_mb < min_size:
                    logger.info(f"⏭️ Skipping {fname} (too small: {file_size_mb:.1f} MB < {min_size} MB)")
                    skipped += 1
                    continue
                
                if max_size > 0 and file_size_mb > max_size:
                    logger.info(f"⏭️ Skipping {fname} (too large: {file_size_mb:.1f} MB > {max_size} MB)")
                    skipped += 1
                    continue
                
                # Check if file is complete
                if not is_file_complete(fpath):
                    logger.warning(f"⏳ Skipping {fname} (file incomplete)")
                    skipped += 1
                    continue
                
                # Check for duplicates
                file_hash = hash_file(fpath)
                if file_hash in uploaded_hashes:
                    logger.info(f"⏭️ Skipping {fname} (already uploaded)")
                    skipped += 1
                    continue
                
                # Upload video
                logger.info(f"📤 Uploading {fname} ({i}/{total})")
                if upload_video(fpath, youtube, channel_id, file_progress_var=file_progress_var):
                    uploaded += 1
                    
                    # Save hash
                    try:
                        with open(HASH_LOG, "a") as f:
                            f.write(file_hash + "\n")
                    except Exception as e:
                        logger.warning(f"Failed to save hash for {fname}: {e}")
                    
                    # Handle file after upload
                    handle_file_after_upload(fpath, fname, auto_delete)
                    
                    # Update progress
                    if progress_var:
                        progress_var.set(int((uploaded / total) * 100))
                    
                    if mb_progress_var:
                        mb_progress_var.set(f"Uploaded: {uploaded}/{total}")
                
            except Exception as e:
                failed += 1
                logger.log_exception(f"Failed to process {fname}", e)
                
                # Update progress even on failure
                if progress_var:
                    progress_var.set(int((uploaded / total) * 100))
        
        # Final summary
        logger.info("=== Upload Summary ===")
        logger.info(f"✅ Successfully uploaded: {uploaded}")
        logger.info(f"⏭️ Skipped: {skipped}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📊 Total processed: {uploaded + skipped + failed}")
        
        if failed > 0:
            logger.warning(f"Some uploads failed. Check the log for details.")
        
        logger.info("🎉 Batch upload process completed!")
        
    except Exception as e:
        logger.log_exception("Batch upload failed", e)
        raise
