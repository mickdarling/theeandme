#!/usr/bin/env python3
"""
Debug voice test - detailed analysis of VAD and STT.
"""

import sys
import asyncio
import numpy as np
import sounddevice as sd
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from audio.vad import SileroVAD
from audio.stt import WhisperSTT

async def debug_voice_test():
    """Debug test with detailed analysis."""
    print("🔬 Debug Voice Test - Detailed Analysis")
    print("=" * 60)
    
    # Lower threshold for testing
    config = {
        'sample_rate': 16000,
        'vad_threshold': 0.3,  # Much lower threshold
        'min_speech_duration_ms': 100,  # Shorter minimum duration
        'silence_timeout_seconds': 2.0,
        'whisper_model': 'base'
    }
    
    print("Configuration:")
    print(f"  VAD Threshold: {config['vad_threshold']} (lowered for testing)")
    print(f"  Min Speech Duration: {config['min_speech_duration_ms']}ms")
    print(f"  Sample Rate: {config['sample_rate']}Hz")
    
    # Initialize components
    print("\n1. Initializing components...")
    vad = SileroVAD(config)
    await vad.initialize()
    
    stt = WhisperSTT(config)
    await stt.initialize()
    print("✅ Components ready")
    
    # Record audio
    print("\n2. Recording 5 seconds of audio...")
    print("🔴 Recording... Please speak clearly!")
    
    duration = 5
    sample_rate = 16000
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
    sd.wait()
    
    audio_array = audio_data.flatten()
    print("🟢 Recording complete!")
    
    # Analyze raw audio
    print(f"\n3. Raw Audio Analysis:")
    rms_level = np.sqrt(np.mean(audio_array ** 2))
    peak_amplitude = np.max(np.abs(audio_array))
    print(f"   RMS Level: {rms_level:.4f}")
    print(f"   Peak Amplitude: {peak_amplitude:.4f}")
    print(f"   Audio Format: {audio_array.dtype}, Shape: {audio_array.shape}")
    
    # Test VAD with debugging
    print(f"\n4. Voice Activity Detection (threshold={config['vad_threshold']})...")
    try:
        vad_result = vad.detect_voice_activity(audio_array)
        
        print(f"   Voice Detected: {'✅ YES' if vad_result.has_voice else '❌ NO'}")
        print(f"   VAD Confidence: {vad_result.confidence:.4f}")
        print(f"   VAD State: {vad_result.state.value}")
        
        if vad_result.speech_segments:
            print(f"   Speech Segments: {len(vad_result.speech_segments)}")
            for i, (start, end) in enumerate(vad_result.speech_segments):
                print(f"     Segment {i+1}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")
        else:
            print("   Speech Segments: None")
            
    except Exception as e:
        print(f"❌ VAD Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test STT regardless of VAD result (for debugging)
    print(f"\n5. Speech Recognition (testing regardless of VAD)...")
    try:
        transcription_result = await stt.transcribe_audio(audio_array)
        
        if transcription_result.error:
            print(f"❌ STT Error: {transcription_result.error}")
        else:
            print(f"📝 Transcription: \"{transcription_result.text}\"")
            print(f"   STT Confidence: {transcription_result.confidence:.4f}")
            print(f"   Processing Time: {transcription_result.processing_time:.2f}s")
            print(f"   Language: {transcription_result.language}")
            
            if transcription_result.segments:
                print(f"   Whisper Segments: {len(transcription_result.segments)}")
                for i, segment in enumerate(transcription_result.segments[:3]):  # Show first 3
                    start = segment.get('start', 0)
                    end = segment.get('end', 0)
                    text = segment.get('text', '')
                    print(f"     Segment {i+1}: {start:.2f}s-{end:.2f}s \"{text.strip()}\"")
                    
    except Exception as e:
        print(f"❌ STT Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🔬 Debug test complete!")
    stt.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(debug_voice_test())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()