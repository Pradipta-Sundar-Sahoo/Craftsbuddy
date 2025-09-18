"""Logging configuration for CraftBuddy bot"""
import logging
import os
from typing import Optional

def setup_logger(
    name: str = "craftbuddy_bot",
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Set up logger with console and optionally file output
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name
        log_dir: Directory for log files
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if file logging is enabled
    if log_file and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_path = os.path.join(log_dir, log_file)
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Default logger instance
default_logger = setup_logger()

def get_logger(name: str = "craftbuddy_bot") -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)

# Convenience functions
def log_info(message: str, logger: Optional[logging.Logger] = None) -> None:
    """Log info message"""
    (logger or default_logger).info(message)

def log_error(message: str, logger: Optional[logging.Logger] = None) -> None:
    """Log error message"""
    (logger or default_logger).error(message)

def log_warning(message: str, logger: Optional[logging.Logger] = None) -> None:
    """Log warning message"""
    (logger or default_logger).warning(message)

def log_debug(message: str, logger: Optional[logging.Logger] = None) -> None:
    """Log debug message"""
    (logger or default_logger).debug(message)
