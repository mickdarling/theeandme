#!/usr/bin/env python3
"""
Revolutionary Voice Automation
Local RealtimeSTT + Direct Claude Code Integration

ARCHITECTURE: Voice → Local STT → Claude Code → Conversational Response
"""

import sys
import os
import time
import subprocess
import threading
import signal
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from RealtimeSTT import AudioToTextRecorder
from enhanced_echo_blocker_with_voice_fingerprinting import EnhancedEchoBlocker

class RevolutionaryVoiceAutomation:
    def __init__(self):
        self.echo_blocker = None
        self.recorder = None
        self.listening = False

    def process_voice_with_claude(self, text: str):
        """Send voice directly to Claude Code"""
        # Echo blocking
        is_echo, reason, _ = self.echo_blocker.is_likely_echo(text, audio_file_path=None)
        if is_echo:
            print(f"\n🔇 BLOCKED: '{text}' ({reason})")
            return

        print(f"\n🎤 YOU: '{text}'")
        print("🎙️ Claude Code processing...")

        # Direct Claude Code execution
        result = subprocess.run([
            'claude',
            '--allowed-tools', 'Bash(open:*,touch:*,mkdir:*,ls:*),Read,Write,Edit,WebSearch',
            '--', f"Help with: {text}. Be conversational and explain what you're doing."
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            response = result.stdout.strip()
            print(f"\n🎙️ CLAUDE: {response}")

            # TTS summary
            summary = response.split('.')[0] + '.' if '.' in response else response[:80]
            os.system(f'say "{summary.replace(chr(34), chr(39))}"')
        else:
            print(f"\n❌ ERROR: {result.stderr}")

    def start_automation(self):
        """Start revolutionary voice automation"""
        print("🚀 REVOLUTIONARY VOICE AUTOMATION")
        print("=" * 50)
        print("✅ Local RealtimeSTT + Direct Claude Code")
        print("✅ No web interface complexity")
        print("✅ Full conversational responses")
        print("=" * 50)

        # Initialize components
        self.echo_blocker = EnhancedEchoBlocker()
        self.recorder = AudioToTextRecorder(
            model="base.en",
            language="en",
            spinner=False,
            use_microphone=True,
            level=20
        )

        self.listening = True
        print("\n🎯 LISTENING ACTIVE - Speak naturally")

        # Voice loop
        def voice_loop():
            while self.listening:
                try:
                    text = self.recorder.text()
                    if text and text.strip():
                        self.process_voice_with_claude(text.strip())
                    time.sleep(0.1)
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    break

        threading.Thread(target=voice_loop, daemon=True).start()

        # Keep alive
        try:
            while self.listening:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_automation()

    def stop_automation(self):
        """Stop automation"""
        self.listening = False
        if self.recorder:
            self.recorder.shutdown()
        print("\n🛑 STOPPED")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    revolutionary = RevolutionaryVoiceAutomation()
    revolutionary.start_automation()