#!/usr/bin/env python3
"""
Basic audio test for The E and Me voice interface system.

This script tests basic audio device access and model loading
without full pipeline complexity.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.config_manager import ConfigManager
from audio.vad import SileroVAD
from audio.stt import WhisperSTT


async def test_basic_setup():
    """Test basic audio setup without full pipeline."""
    print("🧪 Basic Audio Components Test")
    print("=" * 50)
    
    # Load config
    config_path = Path(__file__).parent.parent / "config" / "config.example.json"
    config_manager = ConfigManager(config_path)
    config = config_manager.load_config()
    
    # Test Silero VAD initialization
    print("\n1. Testing Silero VAD...")
    try:
        vad = SileroVAD(config['audio'])
        await vad.initialize()
        print("✅ Silero VAD initialized successfully")
    except Exception as e:
        print(f"❌ VAD initialization failed: {e}")
        return False
    
    # Test Whisper STT initialization
    print("\n2. Testing Whisper STT...")
    try:
        stt = WhisperSTT(config)
        await stt.initialize()
        
        stats = stt.get_performance_stats()
        print(f"✅ Whisper {stats['model_size']} initialized successfully")
        print(f"   Device: {stats['device']}")
    except Exception as e:
        print(f"❌ STT initialization failed: {e}")
        return False
    
    # Test audio device listing
    print("\n3. Testing audio device access...")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        print(f"✅ Found {len(input_devices)} input devices:")
        for i, device in enumerate(input_devices[:3], 1):  # Show first 3
            default = " [DEFAULT]" if device == sd.query_devices(kind='input') else ""
            print(f"   {i}. {device['name']}{default}")
            print(f"      Channels: {device['max_input_channels']}, Rate: {device['default_samplerate']:.0f}Hz")
        
        if len(input_devices) > 3:
            print(f"   ... and {len(input_devices) - 3} more")
            
    except Exception as e:
        print(f"❌ Audio device access failed: {e}")
        return False
    
    print(f"\n✅ All basic components initialized successfully!")
    print(f"🎉 System is ready for full audio processing.")
    
    # Cleanup
    stt.cleanup()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic_setup())
    sys.exit(0 if success else 1)