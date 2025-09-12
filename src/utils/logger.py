"""
Logging utilities for The E and Me voice interface system.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_str: Optional[str] = None,
    include_timestamp: bool = True
) -> None:
    """Setup logging configuration."""
    
    if format_str is None:
        if include_timestamp:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            format_str = "%(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers to appropriate levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)