#!/usr/bin/env python3
"""
Autonomous Voice Interface Test
Tests complete voice pipeline: TTS → Voice Interface → Claude Code → System
"""

import time
import subprocess
import threading
import signal
import sys
from claude_code_voice_bridge import ClaudeCodeVoiceBridge

def test_complete_pipeline():
    """Test the complete voice automation pipeline autonomously"""

    print("🧪 AUTONOMOUS VOICE PIPELINE TEST")
    print("=" * 50)

    # Test the Claude Code bridge directly first
    print("\n1. Testing Claude Code Bridge Directly...")
    bridge = ClaudeCodeVoiceBridge()

    direct_result = bridge.process_voice_command("Open Calculator application")
    print(f"   Direct Test: {direct_result['success']} - {direct_result['response']}")

    # Check if Calculator actually opened
    time.sleep(2)
    calc_check = subprocess.run(['pgrep', 'Calculator'], capture_output=True)
    calculator_running = calc_check.returncode == 0
    print(f"   Calculator Running: {calculator_running}")

    if calculator_running:
        print("✅ DIRECT PIPELINE WORKING: Claude Code → System automation successful")

        # Kill calculator for next test
        subprocess.run(['pkill', 'Calculator'])
        time.sleep(1)
    else:
        print("❌ DIRECT PIPELINE FAILING: Claude Code not executing commands")
        return

    print("\n2. Testing Voice Interface with TTS...")

    # Start voice interface if not running
    voice_processes = subprocess.run(['pgrep', '-f', 'claude_code_voice_interface'], capture_output=True)
    if voice_processes.returncode != 0:
        print("   Starting voice interface...")
        subprocess.Popen([
            'python', 'claude_code_voice_interface.py'
        ], cwd='/Users/mick/Developer/theeandme/examples/web-interfaces')
        time.sleep(5)  # Give it time to start

    print("   Voice interface should be at http://localhost:8089")
    print("   Manual step required: Click 'Start Listening' button")
    print("   Then run TTS test...")

    # Generate TTS command after user starts interface
    print("\n3. Generating TTS Voice Command...")
    subprocess.run(['say', 'Open TextEdit application'])

    time.sleep(5)  # Wait for processing

    # Check if TextEdit opened
    textedit_check = subprocess.run(['pgrep', 'TextEdit'], capture_output=True)
    textedit_running = textedit_check.returncode == 0

    print(f"   TextEdit Running After TTS: {textedit_running}")

    if textedit_running:
        print("✅ COMPLETE PIPELINE WORKING: TTS → Voice Interface → Claude Code → System")
    else:
        print("❌ COMPLETE PIPELINE BROKEN: TTS voice not triggering automation")

    print("\n📊 Test Summary:")
    print(f"   Direct Claude Code: {'✅ Working' if direct_result['success'] else '❌ Broken'}")
    print(f"   Calculator Test: {'✅ Opened' if calculator_running else '❌ Failed'}")
    print(f"   TTS → Voice → Claude Code: {'✅ Working' if textedit_running else '❌ Broken'}")

if __name__ == "__main__":
    test_complete_pipeline()