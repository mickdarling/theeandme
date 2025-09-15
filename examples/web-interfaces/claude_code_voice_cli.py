#!/usr/bin/env python3
"""
Claude Code Voice CLI - Simple Terminal Interface
Direct Pipeline: Voice → Claude Code → System

ADVANTAGES:
- Full response visibility (no truncation)
- Simple on/off control
- Real-time Claude Code output
- No web interface complexity
"""

import sys
import os
import time
import threading
import signal
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from RealtimeSTT import AudioToTextRecorder
from enhanced_echo_blocker_with_voice_fingerprinting import EnhancedEchoBlocker
from claude_code_voice_bridge import ClaudeCodeVoiceBridge

class ClaudeCodeVoiceCLI:
    """Command line interface for Claude Code voice automation"""

    def __init__(self):
        self.echo_blocker = None
        self.claude_bridge = None
        self.recorder = None
        self.listening = False
        self.session_dir = None

        # Setup session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path(f"claude_code_cli_session_{timestamp}")
        self.session_dir.mkdir(exist_ok=True)

    def print_header(self):
        """Print CLI header"""
        print("\n" + "=" * 80)
        print("🎙️  CLAUDE CODE VOICE CLI")
        print("=" * 80)
        print("✅ Direct Pipeline: Voice → Claude Code → System")
        print("✅ Full Response Visibility (No Truncation)")
        print("✅ Simple Terminal Control")
        print("✅ Real-time Claude Code Output")
        print("=" * 80)
        print(f"📁 Session: {self.session_dir}")
        print("🎮 Controls: CTRL+C to stop | 's' + Enter to toggle listening")
        print("=" * 80)

    def print_status(self, status: str, details: str = ""):
        """Print status with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {status}")
        if details:
            print(f"         {details}")

    def process_voice_command(self, text: str):
        """Process voice command through Claude Code"""
        try:
            # Echo blocking
            is_echo, reason, _ = self.echo_blocker.is_likely_echo(text, audio_file_path=None)

            if is_echo:
                self.print_status(f"🔇 BLOCKED ECHO: '{text}'", f"Reason: {reason}")
                return

            self.print_status(f"🎤 VOICE INPUT: '{text}'", "Processing with Claude Code...")

            # Send to Claude Code
            start_time = time.time()
            result = self.claude_bridge.process_voice_command(text)
            execution_time = time.time() - start_time

            # Print full Claude Code response
            print(f"\n{'─' * 60}")
            print(f"🎙️ CLAUDE CODE RESPONSE ({result['execution_time_ms']:.0f}ms):")
            print(f"{'─' * 60}")

            # Show full response (no truncation)
            full_response = result.get("full_response", result["response"])
            print(full_response)

            print(f"{'─' * 60}")
            print(f"✅ Status: {'SUCCESS' if result['success'] else 'FAILED'}")
            print(f"⚡ Execution: {result['execution_time_ms']:.0f}ms")
            print(f"🔧 Method: {result['method']}")
            print(f"{'─' * 60}")

            # TTS for short summary
            summary = result["response"]
            if len(summary) > 100:
                summary = summary[:80] + "..."

            # Simple TTS without file complexity
            safe_summary = summary.replace('"', '\\"').replace("'", "\\'")
            os.system(f'say "{safe_summary}"')

            self.print_status("🔊 TTS Response Played", f"Summary: {summary}")

        except Exception as e:
            self.print_status(f"⚠️  PROCESSING ERROR: {e}")
            os.system('say "Processing error occurred"')

    def start_listening(self):
        """Start voice automation"""
        try:
            self.print_status("🎙️ INITIALIZING CLAUDE CODE VOICE AUTOMATION...")

            # Initialize components
            self.echo_blocker = EnhancedEchoBlocker()
            self.claude_bridge = ClaudeCodeVoiceBridge()
            self.print_status("✅ Components initialized")

            # Initialize RealtimeSTT
            self.recorder = AudioToTextRecorder(
                model="base.en",
                language="en",
                spinner=False,
                use_microphone=True,
                level=20
            )

            self.listening = True
            self.print_status("🎯 VOICE AUTOMATION ACTIVE", "Speak naturally - Claude Code will respond")

            # Voice processing loop
            def voice_loop():
                while self.listening:
                    try:
                        text = self.recorder.text()
                        if text and text.strip():
                            self.process_voice_command(text.strip())
                        else:
                            time.sleep(0.1)
                    except Exception as e:
                        self.print_status(f"⚠️  Voice loop error: {e}")
                        break

            voice_thread = threading.Thread(target=voice_loop, daemon=True)
            voice_thread.start()

            # Keep main thread alive
            try:
                while self.listening:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop_listening()

        except Exception as e:
            self.print_status(f"⚠️  INITIALIZATION FAILED: {e}")

    def stop_listening(self):
        """Stop voice automation"""
        self.listening = False

        if self.recorder:
            try:
                self.recorder.shutdown()
            except:
                pass
            self.recorder = None

        self.print_status("🛑 VOICE AUTOMATION STOPPED")

    def run(self):
        """Run the CLI interface"""
        self.print_header()

        print("\n🎮 CONTROLS:")
        print("   • ENTER = Start voice automation")
        print("   • CTRL+C = Stop and exit")

        try:
            print("\n🚀 Auto-starting Claude Code voice automation in 3 seconds...")
            time.sleep(3)
            self.start_listening()
        except KeyboardInterrupt:
            print("\n\n👋 Claude Code Voice CLI terminated")
            sys.exit(0)


if __name__ == "__main__":
    # Handle CTRL+C gracefully
    def signal_handler(sig, frame):
        print("\n\n👋 Claude Code Voice CLI terminated")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Run the CLI
    cli = ClaudeCodeVoiceCLI()
    cli.run()