import threading
import time
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import queue

from .logger import get_logger
from .config import get_config
from .exceptions import UploadError

logger = get_logger()
config = get_config()

class UploadStatus(Enum):
    """Status of an upload in the queue."""
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class UploadItem:
    """Represents a single upload item in the queue."""
    file_path: str
    file_name: str
    file_size: int
    file_hash: str
    status: UploadStatus = UploadStatus.PENDING
    progress: float = 0.0  # 0.0 to 100.0
    uploaded_bytes: int = 0
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """Get upload duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None
    
    @property
    def upload_speed(self) -> Optional[float]:
        """Get upload speed in MB/s."""
        duration = self.duration
        if duration and duration > 0 and self.uploaded_bytes > 0:
            return (self.uploaded_bytes / (1024 * 1024)) / duration
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_hash': self.file_hash,
            'status': self.status.value,
            'progress': self.progress,
            'uploaded_bytes': self.uploaded_bytes,
            'error_message': self.error_message,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }

class UploadQueue:
    """Manages a queue of uploads with pause/resume/cancel functionality."""
    
    def __init__(self, max_concurrent: int = 1):
        """
        Initialize the upload queue.
        
        Args:
            max_concurrent: Maximum number of concurrent uploads
        """
        self.queue: List[UploadItem] = []
        self.max_concurrent = max_concurrent
        self.active_uploads: Dict[str, UploadItem] = {}
        self.completed_uploads: List[UploadItem] = []
        self.failed_uploads: List[UploadItem] = []
        
        # Threading
        self.lock = threading.RLock()
        self.worker_threads: List[threading.Thread] = []
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # Callbacks
        self.on_progress: Optional[Callable[[UploadItem], None]] = None
        self.on_status_change: Optional[Callable[[UploadItem], None]] = None
        self.on_complete: Optional[Callable[[UploadItem], None]] = None
        self.on_error: Optional[Callable[[UploadItem, Exception], None]] = None
        
        # Statistics
        self.total_uploads = 0
        self.successful_uploads = 0
        self.failed_uploads_count = 0
        
        logger.info(f"Upload queue initialized with max {max_concurrent} concurrent uploads")
    
    def add_upload(self, file_path: str, file_name: str, file_size: int, file_hash: str) -> UploadItem:
        """Add a new upload to the queue."""
        with self.lock:
            upload_item = UploadItem(
                file_path=file_path,
                file_name=file_name,
                file_size=file_size,
                file_hash=file_hash
            )
            self.queue.append(upload_item)
            self.total_uploads += 1
            
            logger.info(f"Added upload to queue: {file_name}")
            
            # Start worker if not already running
            if not self.worker_threads:
                self._start_workers()
            
            return upload_item
    
    def remove_upload(self, upload_item: UploadItem) -> bool:
        """Remove an upload from the queue."""
        with self.lock:
            if upload_item in self.queue:
                self.queue.remove(upload_item)
                logger.info(f"Removed upload from queue: {upload_item.file_name}")
                return True
            return False
    
    def move_upload(self, upload_item: UploadItem, new_index: int) -> bool:
        """Move an upload to a new position in the queue."""
        with self.lock:
            if upload_item in self.queue:
                self.queue.remove(upload_item)
                self.queue.insert(new_index, upload_item)
                logger.info(f"Moved upload {upload_item.file_name} to position {new_index}")
                return True
            return False
    
    def pause_upload(self, upload_item: UploadItem) -> bool:
        """Pause a specific upload."""
        with self.lock:
            if upload_item.status == UploadStatus.UPLOADING:
                upload_item.status = UploadStatus.PAUSED
                logger.info(f"Paused upload: {upload_item.file_name}")
                if self.on_status_change:
                    self.on_status_change(upload_item)
                return True
            return False
    
    def resume_upload(self, upload_item: UploadItem) -> bool:
        """Resume a paused upload."""
        with self.lock:
            if upload_item.status == UploadStatus.PAUSED:
                upload_item.status = UploadStatus.PENDING
                logger.info(f"Resumed upload: {upload_item.file_name}")
                if self.on_status_change:
                    self.on_status_change(upload_item)
                return True
            return False
    
    def cancel_upload(self, upload_item: UploadItem) -> bool:
        """Cancel an upload."""
        with self.lock:
            if upload_item.status in [UploadStatus.PENDING, UploadStatus.UPLOADING, UploadStatus.PAUSED]:
                upload_item.status = UploadStatus.CANCELLED
                upload_item.end_time = datetime.now()
                logger.info(f"Cancelled upload: {upload_item.file_name}")
                if self.on_status_change:
                    self.on_status_change(upload_item)
                return True
            return False
    
    def pause_all(self):
        """Pause all uploads."""
        with self.lock:
            self.pause_event.set()
            for item in self.queue:
                if item.status == UploadStatus.UPLOADING:
                    item.status = UploadStatus.PAUSED
            logger.info("Paused all uploads")
    
    def resume_all(self):
        """Resume all uploads."""
        with self.lock:
            self.pause_event.clear()
            for item in self.queue:
                if item.status == UploadStatus.PAUSED:
                    item.status = UploadStatus.PENDING
            logger.info("Resumed all uploads")
    
    def cancel_all(self):
        """Cancel all uploads."""
        with self.lock:
            self.stop_event.set()
            for item in self.queue:
                if item.status in [UploadStatus.PENDING, UploadStatus.UPLOADING, UploadStatus.PAUSED]:
                    item.status = UploadStatus.CANCELLED
                    item.end_time = datetime.now()
            logger.info("Cancelled all uploads")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        with self.lock:
            pending = len([item for item in self.queue if item.status == UploadStatus.PENDING])
            uploading = len([item for item in self.queue if item.status == UploadStatus.UPLOADING])
            paused = len([item for item in self.queue if item.status == UploadStatus.PAUSED])
            completed = len(self.completed_uploads)
            failed = len(self.failed_uploads)
            cancelled = len([item for item in self.queue if item.status == UploadStatus.CANCELLED])
            
            return {
                'pending': pending,
                'uploading': uploading,
                'paused': paused,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled,
                'total': self.total_uploads,
                'queue_length': len(self.queue)
            }
    
    def _start_workers(self):
        """Start worker threads."""
        for i in range(self.max_concurrent):
            worker = threading.Thread(target=self._worker, name=f"UploadWorker-{i}")
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)
            logger.debug(f"Started upload worker thread {i}")
    
    def _worker(self):
        """Worker thread that processes uploads from the queue."""
        while not self.stop_event.is_set():
            try:
                # Get next upload item
                upload_item = None
                with self.lock:
                    for item in self.queue:
                        if item.status == UploadStatus.PENDING:
                            upload_item = item
                            break
                
                if upload_item is None:
                    time.sleep(1)
                    continue
                
                # Check if paused
                if self.pause_event.is_set():
                    time.sleep(0.5)
                    continue
                
                # Start upload
                with self.lock:
                    upload_item.status = UploadStatus.UPLOADING
                    upload_item.start_time = datetime.now()
                    self.active_uploads[upload_item.file_hash] = upload_item
                
                if self.on_status_change:
                    self.on_status_change(upload_item)
                
                logger.info(f"Starting upload: {upload_item.file_name}")
                
                # Process upload (this will be implemented by the caller)
                # For now, we'll just simulate the upload process
                self._process_upload(upload_item)
                
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                time.sleep(1)
    
    def _process_upload(self, upload_item: UploadItem):
        """Process a single upload item."""
        try:
            # This is a placeholder - the actual upload logic will be provided
            # by the caller through a callback or by overriding this method
            logger.warning("Upload processing not implemented - override _process_upload")
            
            # Simulate upload completion
            upload_item.status = UploadStatus.COMPLETED
            upload_item.progress = 100.0
            upload_item.uploaded_bytes = upload_item.file_size
            upload_item.end_time = datetime.now()
            
        except Exception as e:
            upload_item.status = UploadStatus.FAILED
            upload_item.error_message = str(e)
            upload_item.end_time = datetime.now()
            self.failed_uploads.append(upload_item)
            logger.error(f"Upload failed: {upload_item.file_name} - {e}")
            
            if self.on_error:
                self.on_error(upload_item, e)
        finally:
            # Cleanup
            with self.lock:
                if upload_item.file_hash in self.active_uploads:
                    del self.active_uploads[upload_item.file_hash]
                
                if upload_item.status == UploadStatus.COMPLETED:
                    self.completed_uploads.append(upload_item)
                    self.successful_uploads += 1
                elif upload_item.status == UploadStatus.FAILED:
                    self.failed_uploads_count += 1
                
                # Remove from queue
                if upload_item in self.queue:
                    self.queue.remove(upload_item)
            
            if self.on_status_change:
                self.on_status_change(upload_item)
            
            if self.on_complete:
                self.on_complete(upload_item)
    
    def update_progress(self, upload_item: UploadItem, progress: float, uploaded_bytes: int):
        """Update progress for an upload item."""
        with self.lock:
            upload_item.progress = progress
            upload_item.uploaded_bytes = uploaded_bytes
            
            if self.on_progress:
                self.on_progress(upload_item)
    
    def get_upload_by_hash(self, file_hash: str) -> Optional[UploadItem]:
        """Get upload item by file hash."""
        with self.lock:
            # Check active uploads
            if file_hash in self.active_uploads:
                return self.active_uploads[file_hash]
            
            # Check queue
            for item in self.queue:
                if item.file_hash == file_hash:
                    return item
            
            # Check completed
            for item in self.completed_uploads:
                if item.file_hash == file_hash:
                    return item
            
            # Check failed
            for item in self.failed_uploads:
                if item.file_hash == file_hash:
                    return item
            
            return None
    
    def clear_completed(self):
        """Clear completed uploads from memory."""
        with self.lock:
            self.completed_uploads.clear()
            logger.info("Cleared completed uploads from memory")
    
    def clear_failed(self):
        """Clear failed uploads from memory."""
        with self.lock:
            self.failed_uploads.clear()
            self.failed_uploads_count = 0
            logger.info("Cleared failed uploads from memory")
    
    def export_queue(self) -> List[Dict[str, Any]]:
        """Export queue state for persistence."""
        with self.lock:
            return [item.to_dict() for item in self.queue + self.completed_uploads + self.failed_uploads]
    
    def import_queue(self, queue_data: List[Dict[str, Any]]):
        """Import queue state from persistence."""
        with self.lock:
            self.queue.clear()
            self.completed_uploads.clear()
            self.failed_uploads.clear()
            
            for item_data in queue_data:
                # Recreate upload items from data
                # This is a simplified version - you might want to add more validation
                upload_item = UploadItem(
                    file_path=item_data['file_path'],
                    file_name=item_data['file_name'],
                    file_size=item_data['file_size'],
                    file_hash=item_data['file_hash']
                )
                
                # Restore status and other properties
                upload_item.status = UploadStatus(item_data['status'])
                upload_item.progress = item_data['progress']
                upload_item.uploaded_bytes = item_data['uploaded_bytes']
                upload_item.error_message = item_data['error_message']
                upload_item.retry_count = item_data['retry_count']
                upload_item.max_retries = item_data['max_retries']
                
                # Add to appropriate list
                if upload_item.status == UploadStatus.COMPLETED:
                    self.completed_uploads.append(upload_item)
                elif upload_item.status == UploadStatus.FAILED:
                    self.failed_uploads.append(upload_item)
                elif upload_item.status in [UploadStatus.PENDING, UploadStatus.PAUSED]:
                    self.queue.append(upload_item)
            
            logger.info(f"Imported {len(queue_data)} upload items") 