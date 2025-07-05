import time
import random
from typing import Callable, Any, Optional, Type, Union, Tuple
from functools import wraps
from .logger import get_logger
from .exceptions import ShadowPlayUploaderError

logger = get_logger()

class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True,
                 retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retry_exceptions: Tuple of exceptions to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_exceptions = retry_exceptions

def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        config: Retry configuration, uses default if None
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

def retry_operation(operation: Callable,
                   operation_name: str,
                   *args,
                   config: Optional[RetryConfig] = None,
                   **kwargs) -> Any:
    """
    Retry an operation with configurable retry behavior.
    
    Args:
        operation: Function to retry
        operation_name: Name of the operation for logging
        *args: Arguments to pass to the operation
        config: Retry configuration
        **kwargs: Keyword arguments to pass to the operation
        
    Returns:
        Result of the operation
        
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.debug(f"Attempting {operation_name} (attempt {attempt}/{config.max_attempts})")
            result = operation(*args, **kwargs)
            logger.debug(f"{operation_name} completed successfully on attempt {attempt}")
            return result
            
        except config.retry_exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(f"{operation_name} failed after {config.max_attempts} attempts: {e}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay
            )
            
            # Add jitter if enabled
            if config.jitter:
                delay *= (0.5 + random.random() * 0.5)
            
            logger.warning(
                f"{operation_name} failed on attempt {attempt}: {e}. "
                f"Retrying in {delay:.1f} seconds..."
            )
            
            time.sleep(delay)
    
    # This should never be reached
    raise last_exception

class RetryableOperation:
    """Context manager for retryable operations."""
    
    def __init__(self, 
                 operation_name: str,
                 config: Optional[RetryConfig] = None,
                 on_retry: Optional[Callable[[int, Exception], None]] = None):
        """
        Initialize retryable operation.
        
        Args:
            operation_name: Name of the operation for logging
            config: Retry configuration
            on_retry: Callback called before each retry
        """
        self.operation_name = operation_name
        self.config = config or RetryConfig()
        self.on_retry = on_retry
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self):
        """Enter the retry context."""
        self.attempt = 0
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the retry context."""
        if exc_val:
            self.last_exception = exc_val
            return False  # Don't suppress the exception
        return True
    
    def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
        """
        for attempt in range(1, self.config.max_attempts + 1):
            self.attempt = attempt
            
            try:
                logger.debug(f"Executing {self.operation_name} (attempt {attempt}/{self.config.max_attempts})")
                result = operation(*args, **kwargs)
                logger.debug(f"{self.operation_name} completed successfully on attempt {attempt}")
                return result
                
            except self.config.retry_exceptions as e:
                self.last_exception = e
                
                if attempt == self.config.max_attempts:
                    logger.error(f"{self.operation_name} failed after {self.config.max_attempts} attempts: {e}")
                    raise
                
                # Call retry callback if provided
                if self.on_retry:
                    try:
                        self.on_retry(attempt, e)
                    except Exception as callback_error:
                        logger.warning(f"Retry callback failed: {callback_error}")
                
                # Calculate delay with exponential backoff
                delay = min(
                    self.config.base_delay * (self.config.exponential_base ** (attempt - 1)),
                    self.config.max_delay
                )
                
                # Add jitter if enabled
                if self.config.jitter:
                    delay *= (0.5 + random.random() * 0.5)
                
                logger.warning(
                    f"{self.operation_name} failed on attempt {attempt}: {e}. "
                    f"Retrying in {delay:.1f} seconds..."
                )
                
                time.sleep(delay)
        
        # This should never be reached
        raise self.last_exception

# Predefined retry configurations for common scenarios
UPLOAD_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retry_exceptions=(Exception,)
)

FILE_OPERATION_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=1.5,
    jitter=True,
    retry_exceptions=(OSError, IOError)
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=5.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retry_exceptions=(Exception,)
)

# Convenience functions for common retry scenarios
def retry_upload(operation: Callable, *args, **kwargs) -> Any:
    """Retry an upload operation with appropriate configuration."""
    return retry_operation(operation, "Upload", *args, config=UPLOAD_RETRY_CONFIG, **kwargs)

def retry_file_operation(operation: Callable, *args, **kwargs) -> Any:
    """Retry a file operation with appropriate configuration."""
    return retry_operation(operation, "File Operation", *args, config=FILE_OPERATION_RETRY_CONFIG, **kwargs)

def retry_api_call(operation: Callable, *args, **kwargs) -> Any:
    """Retry an API call with appropriate configuration."""
    return retry_operation(operation, "API Call", *args, config=API_RETRY_CONFIG, **kwargs) 