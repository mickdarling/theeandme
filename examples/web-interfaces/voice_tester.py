#!/usr/bin/env python3
"""
Quick Voice Tester for macOS Voices
Test different voices to find the most natural sounding one
"""

import os
import time

def test_voice(voice_name, text="Hello, this is a test of the voice quality for natural conversation."):
    """Test a specific voice"""
    print(f"🔊 Testing voice: {voice_name}")
    if voice_name == "default":
        os.system(f'say "{text}"')
    else:
        os.system(f'say -v "{voice_name}" "{text}"')
    time.sleep(1)

def main():
    print("🎤 macOS Voice Quality Tester")
    print("=" * 50)

    # Test sample text
    test_text = "Hello Mick, this is a test of the voice quality for our enhanced conversation system."

    # Popular English voices to test
    voices_to_test = [
        ("default", "Default macOS Voice"),
        ("Alex", "Alex - Classic male voice"),
        ("Daniel", "Daniel - British male voice"),
        ("Fiona", "Fiona - Scottish female voice"),
        ("Victoria", "Victoria - Female voice"),
        ("Allison", "Allison - Female voice"),
        ("Ava", "Ava - Female voice"),
        ("Susan", "Susan - Female voice"),
        ("Vicki", "Vicki - Female voice")
    ]

    print(f"Testing with text: '{test_text}'\n")

    for voice_code, voice_description in voices_to_test:
        print(f"{voice_description}")
        try:
            test_voice(voice_code, test_text)
            print("✅ Voice tested successfully")
        except Exception as e:
            print(f"❌ Error testing voice: {e}")
        print("-" * 30)
        time.sleep(0.5)

    print("\n🎯 Recommendation: Use the voice that sounds most natural to you!")
    print("The 'default' voice is typically the most natural sounding.")

if __name__ == "__main__":
    main()