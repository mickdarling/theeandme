#!/usr/bin/env python3
"""
Microphone level test - check if audio input is working.
"""

import numpy as np
import sounddevice as sd
import time

def test_microphone():
    """Test microphone input levels."""
    print("🎤 Microphone Input Test")
    print("=" * 40)
    
    # List audio devices
    print("Available audio devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            default = " [DEFAULT]" if device == sd.query_devices(kind='input') else ""
            print(f"  [{i}] {device['name']}{default}")
    
    print(f"\nUsing default input device: {sd.query_devices(kind='input')['name']}")
    
    print("\n🔴 Recording 5 seconds - speak or make noise...")
    
    # Record 5 seconds of audio
    duration = 5  # seconds
    sample_rate = 16000
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    
    # Analyze the audio
    audio_array = audio_data.flatten()
    
    print("🟢 Recording complete!")
    print("\nAudio Analysis:")
    print(f"  Samples recorded: {len(audio_array)}")
    print(f"  Duration: {len(audio_array) / sample_rate:.1f} seconds")
    print(f"  Min value: {np.min(audio_array):.4f}")
    print(f"  Max value: {np.max(audio_array):.4f}")
    print(f"  RMS level: {np.sqrt(np.mean(audio_array ** 2)):.4f}")
    print(f"  Peak amplitude: {np.max(np.abs(audio_array)):.4f}")
    
    # Check if we got meaningful audio
    rms_level = np.sqrt(np.mean(audio_array ** 2))
    peak_amplitude = np.max(np.abs(audio_array))
    
    if rms_level > 0.001:
        print("✅ Audio input detected - microphone is working!")
    elif peak_amplitude > 0.0001:
        print("⚠️  Very quiet audio detected - try speaking louder")
    else:
        print("❌ No audio detected - check microphone connection")
    
    return rms_level > 0.001

if __name__ == "__main__":
    try:
        working = test_microphone()
        if working:
            print(f"\n🎉 Microphone test passed! Ready for voice recognition.")
        else:
            print(f"\n⚠️  Microphone may need adjustment.")
    except Exception as e:
        print(f"❌ Error: {e}")