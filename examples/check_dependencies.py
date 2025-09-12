#!/usr/bin/env python3
"""
Dependency checker for The E and Me voice interface system.

This script validates that all required dependencies are available
before running the full audio processing tests.
"""

import sys
import importlib
from typing import List, Tuple

def check_dependency(module_name: str, package_name: str = None) -> Tuple[bool, str]:
    """
    Check if a dependency is available.
    
    Args:
        module_name: Name of module to import
        package_name: Display name (if different from module)
        
    Returns:
        (success, message)
    """
    display_name = package_name or module_name
    
    try:
        importlib.import_module(module_name)
        return True, f"✅ {display_name}"
    except ImportError as e:
        return False, f"❌ {display_name}: {e}"

def main():
    """Check all dependencies."""
    print("🔍 Checking Dependencies for The E and Me")
    print("=" * 50)
    
    # Core dependencies
    core_deps = [
        ("torch", "PyTorch"),
        ("torchaudio", "TorchAudio"),
        ("numpy", "NumPy"),
        ("requests", "Requests"),
        ("asyncio", "AsyncIO"),
    ]
    
    # Audio dependencies
    audio_deps = [
        ("pyaudio", "PyAudio"),
        ("sounddevice", "SoundDevice"),
        ("librosa", "LibROSA"),
    ]
    
    # LLM dependencies  
    llm_deps = [
        ("whisper", "OpenAI Whisper"),
        ("aiohttp", "AIOHTTP"),
    ]
    
    # Optional computer vision
    vision_deps = [
        ("cv2", "OpenCV"),
    ]
    
    all_passed = True
    
    print("\n🧠 Core Dependencies:")
    for module, display in core_deps:
        success, message = check_dependency(module, display)
        print(f"  {message}")
        if not success:
            all_passed = False
    
    print("\n🎵 Audio Dependencies:")  
    for module, display in audio_deps:
        success, message = check_dependency(module, display)
        print(f"  {message}")
        if not success:
            all_passed = False
    
    print("\n🤖 LLM Dependencies:")
    for module, display in llm_deps:
        success, message = check_dependency(module, display)
        print(f"  {message}")
        if not success:
            all_passed = False
    
    print("\n👁️ Vision Dependencies (Optional):")
    for module, display in vision_deps:
        success, message = check_dependency(module, display)
        print(f"  {message}")
    
    # Test specific functionality
    print("\n🧪 Functionality Tests:")
    
    # Test Torch Hub for Silero VAD
    try:
        import torch
        # Just check if hub is accessible, don't download
        torch.hub.list('snakers4/silero-vad', force_reload=False)
        print("  ✅ Torch Hub accessible (Silero VAD)")
    except Exception as e:
        print(f"  ⚠️ Torch Hub issue: {e}")
    
    # Test Whisper model loading
    try:
        import whisper
        # Check if tiny model can be referenced (don't download)
        whisper.available_models()
        print("  ✅ Whisper models accessible")
    except Exception as e:
        print(f"  ❌ Whisper models issue: {e}")
        all_passed = False
    
    # Test audio device access
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        print(f"  ✅ Audio devices: {len(input_devices)} input devices found")
    except Exception as e:
        print(f"  ❌ Audio device access issue: {e}")
        all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All core dependencies are available!")
        print("You can now run: python examples/test_audio.py")
        return 0
    else:
        print("❌ Some dependencies are missing.")
        print("Install missing packages with: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())