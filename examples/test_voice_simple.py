#!/usr/bin/env python3
"""
Simple voice test - just VAD + STT without complex device management.
"""

import sys
import asyncio
import numpy as np
import sounddevice as sd
from pathlib import Path
import time

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from audio.vad import SileroVAD
from audio.stt import WhisperSTT

async def simple_voice_test():
    """Simple test of voice components without full AudioManager."""
    print("🎤 Simple Voice Activity + Speech Recognition Test")
    print("=" * 60)
    print("Instructions:")
    print("• This will record 5 seconds of audio")
    print("• Speak clearly during the recording")
    print("• The system will detect voice activity and transcribe")
    print()
    
    # Initialize components
    config = {
        'sample_rate': 16000,
        'vad_threshold': 0.7,
        'min_speech_duration_ms': 300,
        'silence_timeout_seconds': 2.0,
        'whisper_model': 'base'
    }
    
    print("1. Initializing VAD...")
    vad = SileroVAD(config)
    await vad.initialize()
    print("✅ VAD ready")
    
    print("2. Initializing STT...")
    stt = WhisperSTT(config)
    await stt.initialize()
    print("✅ STT ready")
    
    # Record audio
    print("\n3. Recording audio for 5 seconds...")
    print("🔴 Recording... Speak now!")
    
    duration = 5  # seconds
    sample_rate = 16000
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()  # Wait until recording is finished
    
    print("🟢 Recording complete!")
    
    # Flatten audio data
    audio_array = audio_data.flatten()
    
    # Test VAD
    print("\n4. Testing Voice Activity Detection...")
    vad_result = vad.detect_voice_activity(audio_array)
    
    print(f"   Voice detected: {'✅ YES' if vad_result.has_voice else '❌ NO'}")
    print(f"   Confidence: {vad_result.confidence:.2f}")
    print(f"   Speech segments: {len(vad_result.speech_segments) if vad_result.speech_segments else 0}")
    
    # Test STT if voice was detected
    if vad_result.has_voice:
        print("\n5. Testing Speech Recognition...")
        transcription_result = await stt.transcribe_audio(audio_array)
        
        if transcription_result.error:
            print(f"❌ Transcription error: {transcription_result.error}")
        else:
            print(f"📝 Transcription: \"{transcription_result.text}\"")
            print(f"   Confidence: {transcription_result.confidence:.2f}")
            print(f"   Processing time: {transcription_result.processing_time:.2f}s")
            print(f"   Model: {transcription_result.model_used}")
    else:
        print("\n5. Skipping transcription (no voice detected)")
    
    print(f"\n🎉 Voice test complete!")
    
    # Cleanup
    stt.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(simple_voice_test())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)