import logging
import os
import sys
from typing import Optional


class UTFStreamHandler(logging.StreamHandler):
    """Custom stream handler ensuring UTF-8 encoding support on console output."""
    
    def __init__(self, stream=None):
        super().__init__(stream)
        if hasattr(self.stream, 'reconfigure'):
            try:
                self.stream.reconfigure(encoding='utf-8')
            except Exception:
                pass


def setup_logging(log_file: str = 'telegram_messenger.log', level: int = logging.INFO) -> logging.Logger:
    """Set up application logging with UTF-8 support for both file and console."""
    # Ensure log directory exists
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    
    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = UTFStreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        
        root_logger.setLevel(level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
    return logging.getLogger('BulkMessenger')