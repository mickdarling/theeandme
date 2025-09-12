"""
Configuration management for The E and Me voice interface system.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages system configuration loading and validation."""
    
    def __init__(self, config_path: Path):
        """Initialize configuration manager."""
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return self.config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in config file: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure and values."""
        # TODO: Implement comprehensive validation
        required_sections = ['system', 'llm', 'audio', 'vision']
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
        
        logger.info("Configuration validation passed")
        return True