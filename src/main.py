#!/usr/bin/env python3
"""
The E and Me - Always-On Voice Interface System
Main application entry point

This is the primary entry point for the voice interface system that coordinates
between camera-based attention detection, voice activity detection, and local LLM processing.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Core system imports
from core.system_manager import SystemManager
from core.config_manager import ConfigManager
from utils.logger import setup_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="The E and Me - Always-On Voice Interface System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start with default config
  python main.py --debug           # Start with debug logging
  python main.py --config custom.json  # Use custom config file
  python main.py --mac-id studio_2     # Override MAC ID
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=Path('config/config.example.json'),
        help='Configuration file path (default: config/config.example.json)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--mac-id',
        type=str,
        help='Override MAC ID from config'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode (no actual hardware access)'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='The E and Me v1.0.0'
    )
    
    return parser.parse_args()


async def main():
    """Main application entry point."""
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("🎙️ Starting The E and Me - Always-On Voice Interface System")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Configuration file: {args.config}")
    
    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        config = config_manager.load_config()
        
        # Override MAC ID if provided
        if args.mac_id:
            config['system']['mac_id'] = args.mac_id
            logger.info(f"MAC ID overridden to: {args.mac_id}")
        
        # Set test mode if requested
        if args.test_mode:
            config['features']['debug_mode'] = True
            logger.info("Running in test mode")
        
        # Validate configuration
        config_manager.validate_config(config)
        logger.info("✅ Configuration validated successfully")
        
        # Initialize system manager
        system_manager = SystemManager(config)
        
        # Start the system
        await system_manager.initialize()
        logger.info("✅ System initialized successfully")
        
        # Run the main system loop
        await system_manager.run()
        
    except FileNotFoundError as e:
        logger.error(f"❌ Configuration file not found: {e}")
        logger.error("Create config file: cp config/config.example.json config/config.json")
        sys.exit(1)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal, shutting down...")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # Cleanup
        try:
            if 'system_manager' in locals():
                await system_manager.shutdown()
                logger.info("✅ System shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Application terminated by user")
        sys.exit(0)