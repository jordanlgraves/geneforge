import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from src.geneforge_config import Config

def setup_logging(config: Config, log_level: str = "INFO") -> None:
    """
    Set up logging configuration for the project.
    
    Args:
        config: Project configuration instance
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = config.project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Set up logging format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "geneforge.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # Set OpenAI/API client logging to WARNING to reduce noise
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log initial setup
    root_logger.info("Logging configured with level: %s", log_level)
    root_logger.info("Log file location: %s", log_dir / "geneforge.log") 