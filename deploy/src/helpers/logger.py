import logging
from logging.handlers import TimedRotatingFileHandler
from dataclasses import dataclass
from datetime import datetime
from typing import List
import os

@dataclass
class LogRecord:
    timestamp: datetime
    level: str
    message: str

class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs: List[LogRecord] = []
    
    def emit(self, record: logging.LogRecord):
        log_entry = LogRecord(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            message=record.getMessage()
        )
        self.logs.append(log_entry)
    
    def clear(self):
        """Clear all captured logs."""
        self.logs = []

def get_current_log_name(base_dir: str, base_name: str) -> str:
    """Generate current log filename with date."""
    base_filename, ext = os.path.splitext(base_name)
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Create a directory for the current year and month if it doesn't exist. For example, "logs/202310"
    year_month = datetime.now().strftime("%Y%m")
    year_month_dir = os.path.join(base_dir, year_month)
    os.makedirs(year_month_dir, exist_ok=True)
    
    return os.path.join(year_month_dir, f"{base_filename}_{date_str}{ext}")

class Logger:
    def __init__(self, log_dir="/tmp/logs", level=logging.DEBUG):
        """Initialize the enhanced logger with daily rotating file logging and capture capability."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)
        
        # Clear any existing handlers
        self.logger.handlers = []

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Get current log filename with date
        current_log_file = get_current_log_name(log_dir, "app.log")
        
        # Create a TimedRotatingFileHandler for daily log rotation
        file_handler = TimedRotatingFileHandler(
            filename=current_log_file,
            when='midnight',  # Rotate at midnight
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        
        # Custom rotation function
        def rotator(source, dest):
            # Don't need to do anything as we're already using dated filenames
            pass
        
        file_handler.rotator = rotator
        file_handler.namer = lambda x: x  # Identity namer as we handle naming elsewhere
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        self.log_capture = LogCapture()
        self.log_capture.setLevel(logging.DEBUG)

        # Create a logging format
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(self.log_capture)

    def get_logger(self) -> logging.Logger:
        """Return the logger instance."""
        return self.logger

    def get_captured_logs(self) -> List[LogRecord]:
        """Return all captured logs."""
        return self.log_capture.logs

    def refresh(self):
        """Clear captured logs while maintaining file logging."""
        self.log_capture.clear()