"""Comprehensive logging setup for StreamTV with file and console output"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file_name: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True
) -> logging.Logger:
    """
    Set up comprehensive logging for StreamTV application.
    
    This configures logging to write to:
    - Console (stdout) with colored output if available
    - File in ~/Library/Logs/StreamTV/ with rotation
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file_name: Name of log file (default: streamtv-YYYY-MM-DD.log)
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        
    Returns:
        Configured root logger
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logs directory in ~/Library/Logs/StreamTV/
    log_dir = Path.home() / "Library" / "Logs" / "StreamTV"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log file name with timestamp if not provided
    if log_file_name is None:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        log_file_name = f"streamtv-{timestamp}.log"
    
    log_file_path = log_dir / log_file_name
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create detailed formatter with timestamp, name, level, and message
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create simpler formatter for console (optional)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Set up console handler (stdout)
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Set up file handler with rotation (max 10 MB per file, keep 10 backup files)
    if log_to_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    # Log the initialization
    root_logger.info("=" * 80)
    root_logger.info(f"StreamTV Logging initialized - Level: {log_level}")
    root_logger.info(f"Log directory: {log_dir}")
    root_logger.info(f"Log file: {log_file_path}")
    root_logger.info(f"Console logging: {'enabled' if log_to_console else 'disabled'}")
    root_logger.info(f"File logging: {'enabled' if log_to_file else 'disabled'}")
    root_logger.info("=" * 80)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Name of the logger (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_system_info():
    """Log system and environment information at startup"""
    import platform
    import sys
    from pathlib import Path
    
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("SYSTEM INFORMATION")
    logger.info("-" * 80)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Machine: {platform.machine()}")
    logger.info(f"Processor: {platform.processor()}")
    logger.info(f"Working directory: {Path.cwd()}")
    logger.info("=" * 80)


def log_exception(logger: logging.Logger, exception: Exception, message: str = "Exception occurred"):
    """
    Log an exception with full traceback.
    
    Args:
        logger: Logger instance to use
        exception: Exception to log
        message: Additional context message
    """
    logger.error(f"{message}: {str(exception)}", exc_info=True)


# Convenience function for quick setup
def quick_setup(log_level: str = "INFO") -> logging.Logger:
    """
    Quick logging setup with sensible defaults.
    
    Args:
        log_level: Logging level
        
    Returns:
        Configured root logger
    """
    return setup_logging(
        log_level=log_level,
        log_to_console=True,
        log_to_file=True
    )

