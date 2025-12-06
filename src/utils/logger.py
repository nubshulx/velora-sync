"""
Centralized logging configuration for Velora Sync
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import functools
import time


class GitHubActionsFormatter(logging.Formatter):
    """Custom formatter for GitHub Actions annotations"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with GitHub Actions annotations"""
        msg = super().format(record)
        
        # Add GitHub Actions annotations for warnings and errors
        if record.levelno >= logging.ERROR:
            return f"::error::{msg}"
        elif record.levelno >= logging.WARNING:
            return f"::warning::{msg}"
        elif record.levelno >= logging.INFO:
            return f"::notice::{msg}"
        
        return msg


def setup_logger(
    name: str = "velora_sync",
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    github_actions: bool = False
) -> logging.Logger:
    """
    Setup and configure logger
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        github_actions: Whether to use GitHub Actions formatting
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if github_actions:
        formatter = GitHubActionsFormatter(
            '%(levelname)s - %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_execution_time(logger: logging.Logger):
    """
    Decorator to log function execution time
    
    Args:
        logger: Logger instance to use
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.debug(f"Starting {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                logger.info(f"Completed {func.__name__} in {elapsed_time:.2f}s")
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Failed {func.__name__} after {elapsed_time:.2f}s: {str(e)}")
                raise
                
        return wrapper
    return decorator


def get_logger(name: str = "velora_sync") -> logging.Logger:
    """
    Get existing logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
