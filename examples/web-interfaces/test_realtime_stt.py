#!/usr/bin/env python3
"""
Simple RealtimeSTT Test Script
Test the sentence beginning capture capability
"""

import os
import time
from RealtimeSTT import AudioToTextRecorder

def create_test_recorder():
    """Create RealtimeSTT recorder for testing"""
    print("🔧 Creating RealtimeSTT test recorder...")

    recorder = AudioToTextRecorder(
        # Core settings
        model="base.en",
        language="en",

        # Pre-recording buffer - the key feature!
        pre_recording_buffer_duration=0.3,  # 300ms buffer

        # VAD settings for sentence capture
        silero_sensitivity=0.4,
        webrtc_sensitivity=2,
        post_speech_silence_duration=0.3,
        min_length_of_recording=0.1,
        min_gap_between_recordings=0.05,

        # Hardware settings
        input_device_index=2,  # Live Streamer CAM 513
        sample_rate=16000,

        # Performance
        use_microphone=True,
        enable_realtime_transcription=True,
        spinner=False,
        level=20
    )

    return recorder

def test_sentence_capture():
    """Test sentence beginning capture"""
    print("\n🚀 TESTING REALTIMESTT SENTENCE BEGINNING CAPTURE")
    print("=" * 60)
    print("✨ Key Feature: 300ms pre-recording buffer")
    print("🎯 Goal: Capture complete sentences from the very beginning")
    print("🎤 Hardware: Live Streamer CAM 513 (Device #2)")
    print("=" * 60)

    try:
        recorder = create_test_recorder()
        print("✅ RealtimeSTT recorder created successfully")

        print("\n🎤 Starting sentence capture test...")
        print("📢 Speak naturally - the system will capture sentence beginnings!")
        print("💡 Try phrases like: 'Hello, how are you today?'")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 40)

        test_count = 0
        while True:
            try:
                # This will block until speech is detected and transcribed
                text = recorder.text()

                if text and text.strip():
                    test_count += 1
                    print(f"\n[Test #{test_count}] 🎯 CAPTURED: '{text}'")
                    print(f"📏 Length: {len(text)} chars")

                    # Check if sentence beginning was captured
                    starts_properly = text[0].isupper() if text else False
                    print(f"✅ Sentence start: {'CAPTURED' if starts_properly else 'MISSED'}")

                    # Simple quality assessment
                    if len(text) > 5 and starts_properly:
                        print("🌟 QUALITY: Excellent - Complete sentence captured!")
                    elif len(text) > 5:
                        print("⚠️  QUALITY: Good - Content captured but may be missing start")
                    else:
                        print("❌ QUALITY: Poor - Very short transcription")

                    print("-" * 40)

                    # Brief pause between captures
                    time.sleep(0.5)

            except KeyboardInterrupt:
                print("\n\n🛑 Test stopped by user")
                break
            except Exception as e:
                print(f"❌ Error during capture: {e}")
                time.sleep(1)

    except Exception as e:
        print(f"❌ Failed to create recorder: {e}")
        return False

    print(f"\n📊 Test completed - {test_count} captures processed")
    print("🔬 Analysis complete!")
    return True

if __name__ == '__main__':
    test_sentence_capture()