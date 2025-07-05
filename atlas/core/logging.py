"""
Logging utilities for the ATLAS system.

This module provides centralized logging configuration and utilities
for consistent logging across all ATLAS components.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .config import get_config
from .exceptions import ConfigurationError


class AtlasFormatter(logging.Formatter):
    """Custom formatter for ATLAS log messages."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, use_colors: bool = True):
        """Initialize formatter.
        
        Args:
            use_colors: Whether to use colored output
        """
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record."""
        # Create timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine log level color
        level_color = ""
        reset_color = ""
        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, "")
            reset_color = self.RESET
        
        # Format message
        message = record.getMessage()
        
        # Add exception info if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        # Create formatted log line
        log_line = (
            f"{timestamp} | "
            f"{level_color}{record.levelname:8}{reset_color} | "
            f"{record.name:20} | "
            f"{message}"
        )
        
        return log_line


class AtlasLogHandler:
    """Manages log handlers for the ATLAS system."""
    
    def __init__(self):
        """Initialize log handler manager."""
        self._handlers: Dict[str, logging.Handler] = {}
        self._configured = False
    
    def configure_logging(self, force: bool = False) -> None:
        """Configure logging based on current configuration.
        
        Args:
            force: Force reconfiguration even if already configured
        """
        if self._configured and not force:
            return
        
        try:
            config = get_config()
        except Exception:
            # Fallback to default configuration if config not available
            self._configure_default_logging()
            return
        
        # Clear existing handlers
        self._clear_handlers()
        
        # Get root logger
        root_logger = logging.getLogger('atlas')
        root_logger.setLevel(getattr(logging, config.system.log_level.upper()))
        
        # Configure console handler
        self._add_console_handler(root_logger)
        
        # Configure file handler if specified
        if config.system.log_file:
            self._add_file_handler(root_logger, config.system.log_file)
        
        # Configure rotating file handler for work directory
        work_log_file = config.system.work_dir / "atlas.log"
        self._add_rotating_file_handler(root_logger, work_log_file)
        
        self._configured = True
    
    def _configure_default_logging(self) -> None:
        """Configure default logging when config is not available."""
        root_logger = logging.getLogger('atlas')
        root_logger.setLevel(logging.INFO)
        
        # Only console handler with default settings
        if not root_logger.handlers:
            self._add_console_handler(root_logger)
        
        self._configured = True
    
    def _clear_handlers(self) -> None:
        """Remove all existing handlers."""
        root_logger = logging.getLogger('atlas')
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
        
        # Clear our handler registry
        for handler in self._handlers.values():
            handler.close()
        self._handlers.clear()
    
    def _add_console_handler(self, logger: logging.Logger) -> None:
        """Add console handler to logger."""
        if 'console' in self._handlers:
            return
        
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(AtlasFormatter(use_colors=True))
        handler.setLevel(logging.INFO)
        
        logger.addHandler(handler)
        self._handlers['console'] = handler
    
    def _add_file_handler(self, logger: logging.Logger, log_file: Path) -> None:
        """Add file handler to logger."""
        handler_key = f'file_{log_file}'
        if handler_key in self._handlers:
            return
        
        try:
            # Ensure directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.FileHandler(log_file)
            handler.setFormatter(AtlasFormatter(use_colors=False))
            handler.setLevel(logging.DEBUG)
            
            logger.addHandler(handler)
            self._handlers[handler_key] = handler
            
        except Exception as e:
            # Log to console if file handler fails
            logger.warning(f"Could not create file handler for {log_file}: {e}")
    
    def _add_rotating_file_handler(self, logger: logging.Logger, log_file: Path) -> None:
        """Add rotating file handler to logger."""
        handler_key = f'rotating_{log_file}'
        if handler_key in self._handlers:
            return
        
        try:
            # Ensure directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            handler.setFormatter(AtlasFormatter(use_colors=False))
            handler.setLevel(logging.DEBUG)
            
            logger.addHandler(handler)
            self._handlers[handler_key] = handler
            
        except Exception as e:
            # Log to console if rotating handler fails
            logger.warning(f"Could not create rotating file handler for {log_file}: {e}")


# Global log handler manager
_log_handler = AtlasLogHandler()


def setup_logging(force: bool = False) -> None:
    """Setup ATLAS logging system.
    
    Args:
        force: Force reconfiguration
    """
    _log_handler.configure_logging(force=force)


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name. If None, uses 'atlas' as root logger
        
    Returns:
        Configured logger instance
    """
    if name is None:
        logger_name = 'atlas'
    elif not name.startswith('atlas'):
        logger_name = f'atlas.{name}'
    else:
        logger_name = name
    
    # Ensure logging is configured
    setup_logging()
    
    return logging.getLogger(logger_name)


def log_function_call(logger: logging.Logger = None):
    """Decorator to log function calls.
    
    Args:
        logger: Logger to use. If None, creates one based on function module
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            # Log function entry
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed with error: {e}")
                raise
        
        return wrapper
    return decorator


def log_performance(logger: logging.Logger = None):
    """Decorator to log function performance.
    
    Args:
        logger: Logger to use. If None, creates one based on function module
    """
    import time
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{func.__name__} completed in {duration:.3f} seconds")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func.__name__} failed after {duration:.3f} seconds: {e}")
                raise
        
        return wrapper
    return decorator


class LogContext:
    """Context manager for adding extra context to log messages."""
    
    def __init__(self, logger: logging.Logger, **context):
        """Initialize log context.
        
        Args:
            logger: Logger to add context to
            **context: Key-value pairs to add as context
        """
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        """Enter context and set up record factory."""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original record factory."""
        logging.setLogRecordFactory(self.old_factory)


# Pre-configure some common loggers
def _setup_common_loggers():
    """Setup commonly used loggers."""
    # Suppress some noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('paramiko').setLevel(logging.WARNING)


# Initialize common loggers when module is imported
_setup_common_loggers()
