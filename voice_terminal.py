#!/usr/bin/env python3
"""
Voice Terminal - Standalone Voice Automation
Run directly in your terminal for full control

SIMPLE ARCHITECTURE:
- Local RealtimeSTT (your excellent voice recognition)
- Direct Claude Code calls (proven automation)
- Terminal output (full visibility)
- No web interface complexity

USAGE:
cd /Users/mick/Developer/theeandme
python voice_terminal.py
"""

import sys
import os
import time
import subprocess
import threading
import signal
from pathlib import Path

# Add paths for imports
sys.path.append(str(Path(__file__).parent / "src"))
sys.path.append(str(Path(__file__).parent / "examples/web-interfaces"))

try:
    from RealtimeSTT import AudioToTextRecorder
    STT_AVAILABLE = True
    print("✅ RealtimeSTT imported successfully")
except ImportError as e:
    STT_AVAILABLE = False
    print(f"❌ RealtimeSTT import failed: {e}")

try:
    from enhanced_echo_blocker_with_voice_fingerprinting import EnhancedEchoBlocker
    ECHO_BLOCKER_AVAILABLE = True
    print("✅ Echo blocker imported successfully")
except ImportError as e:
    ECHO_BLOCKER_AVAILABLE = False
    print(f"⚠️ Echo blocker import failed: {e} - continuing without")

class VoiceTerminal:
    """Simple terminal-based voice automation"""

    def __init__(self):
        self.echo_blocker = None
        self.recorder = None
        self.listening = False
        self.command_count = 0
        self.pending_permission_process = None
        self.waiting_for_permission = False

        # Persistent Claude Code session
        self.claude_session = None
        self.session_token_count = 0
        self.session_interactions = []
        self.token_threshold = 50000  # Compress when reaching token limit

    def print_banner(self):
        """Terminal banner"""
        os.system('clear')  # Clear terminal
        print("🎙️ " + "═" * 70)
        print("   VOICE TERMINAL - Local STT + Claude Code Automation")
        print("═" * 72)
        print("✅ Local speech recognition (no network required)")
        print("✅ Direct Claude Code integration (proven automation)")
        print("✅ Full conversational responses (complete visibility)")
        print("✅ Terminal interface (no web complexity)")
        print("═" * 72)
        print("🎮 Controls: CTRL+C to stop")
        print("🎯 Ready for voice commands...")
        print("═" * 72)

    def process_voice_command(self, text: str):
        """Process voice through Claude Code with full visibility"""
        try:
            # Check if we're waiting for permission response
            if self.waiting_for_permission and self.pending_permission_process:
                return self.handle_permission_response(text)

            # Echo blocking
            if self.echo_blocker:
                is_echo, reason, _ = self.echo_blocker.is_likely_echo(text, audio_file_path=None)
                if is_echo:
                    print(f"🔇 Echo blocked: '{text}' ({reason})")
                    return

            self.command_count += 1
            timestamp = time.strftime("%H:%M:%S")

            print(f"\n[{timestamp}] 🎤 YOU: '{text}'")
            print("🎙️ Claude Code processing...")

            # Execute with persistent Claude Code session
            response = self._execute_claude_command(text)

            # Display and speak response
            print("─" * 50)
            print(f"🎙️ CLAUDE: {response}")

            # Dynamic TTS based on user request
            if any(word in text.lower() for word in ['verbose', 'detailed', 'more', 'explain', 'longer']):
                # Detailed TTS for verbose requests
                sentences = response.split('.')[:3]
                tts_text = '. '.join(sentences) + '.' if len(sentences) > 1 else response[:200]
            else:
                # Standard TTS
                tts_text = response.split('.')[0] + '.' if '.' in response else response[:80]

            # Clean and speak
            import re
            tts_clean = re.sub(r'[^\w\s\.,!?\-]', '', tts_text.replace('"', "'"))
            os.system(f'say "{tts_clean}"')
            print(f"🔊 TTS: {tts_text}")
            print("─" * 50)

        except Exception as e:
            print(f"⚠️ Processing error: {e}")
            os.system('say "Voice processing error"')

    def handle_permission_response(self, voice_response: str):
        """Handle voice response to Claude Code permission requests"""
        if not self.pending_permission_process:
            return

        response_mapping = {
            'yes': 'y\n',
            'yeah': 'y\n',
            'okay': 'y\n',
            'approve': 'y\n',
            'allow': 'y\n',
            'go ahead': 'y\n',
            'no': 'n\n',
            'deny': 'n\n',
            'cancel': 'n\n',
            'stop': 'n\n',
            'always': 'a\n',
            'never': 'v\n'
        }

        voice_lower = voice_response.lower().strip()
        permission_granted = None

        for voice_pattern, response in response_mapping.items():
            if voice_pattern in voice_lower:
                permission_granted = response
                break

        if permission_granted:
            print(f"🎤 PERMISSION RESPONSE: '{voice_response}' → {permission_granted.strip()}")

            try:
                self.pending_permission_process.stdin.write(permission_granted)
                self.pending_permission_process.stdin.flush()

                # Continue monitoring the process
                remaining_stdout, remaining_stderr = self.pending_permission_process.communicate()

                print("─" * 50)
                if remaining_stdout:
                    print(f"🎙️ CLAUDE: {remaining_stdout.strip()}")
                if remaining_stderr:
                    print(f"⚠️ STDERR: {remaining_stderr.strip()}")
                print("─" * 50)

                # TTS response
                if remaining_stdout:
                    first_sentence = remaining_stdout.split('.')[0] + '.' if '.' in remaining_stdout else remaining_stdout[:80]
                    os.system(f'say "{first_sentence.replace(chr(34), chr(39))}"')

            except Exception as e:
                print(f"⚠️ Permission response error: {e}")

        else:
            print(f"⚠️ Permission response not recognized: '{voice_response}'")
            print("📢 Please say 'yes', 'no', 'always', or 'never'")
            os.system('say "Please say yes, no, always, or never"')
            return  # Stay in permission waiting mode

        # Reset permission state
        self.pending_permission_process = None
        self.waiting_for_permission = False

    def _execute_claude_command(self, text: str):
        """Execute Claude Code with session continuity"""
        try:
            # Use Claude Code --continue for session persistence (simpler approach)
            result = subprocess.run([
                'claude',
                '--continue',  # Maintain session context
                '-p',
                '--allowed-tools', 'Bash(open:*,touch:*,mkdir:*,ls:*,ps:*),Read,Write,Edit,WebSearch,Grep',
                '--',
                f"""Voice command: "{text}"

Please help with this request. Be conversational and explain what you're doing. If I ask for verbose responses, provide detailed explanations."""
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Claude Code error: {result.stderr.strip() or 'Unknown error'}"

        except subprocess.TimeoutExpired:
            return "Claude Code timed out"
        except Exception as e:
            return f"Execution error: {e}"

    def _start_persistent_claude_session(self):
        """Start persistent Claude Code session"""
        print("🔄 Starting persistent Claude Code session...")

        self.claude_session = subprocess.Popen([
            'claude',
            '--allowed-tools', 'Bash(open:*,touch:*,mkdir:*,ls:*,ps:*),Read,Write,Edit,WebSearch,Grep'
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Initialize with context
        init_prompt = """You are a helpful voice assistant for system automation. I'll be sending you multiple voice commands in this session. Please:

1. Maintain context from previous commands in this conversation
2. Be conversational and explain what you're doing
3. Remember user preferences (like verbosity level)
4. Use tools as needed for automation

Ready for voice commands."""

        self.claude_session.stdin.write(init_prompt + "\n")
        self.claude_session.stdin.flush()

        # Read initial response
        initial_response = self._read_claude_response_with_timeout(10)
        print(f"🎙️ Claude session initialized: {initial_response[:100]}...")

    def _read_claude_response_with_timeout(self, timeout_seconds: int) -> str:
        """Read Claude Code response with timeout"""
        import select

        response_lines = []
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            # Check if data is available to read
            ready, _, _ = select.select([self.claude_session.stdout], [], [], 0.1)

            if ready:
                line = self.claude_session.stdout.readline()
                if line:
                    response_lines.append(line)
                    if line.strip() == "":  # Empty line often indicates end of response
                        break
            else:
                time.sleep(0.1)

        return ''.join(response_lines).strip()

    def _compress_session_context(self):
        """Compress session context when token threshold reached"""
        print("🗜️ Compressing session context...")

        # Create session summary
        summary = f"""Session Summary ({len(self.session_interactions)} interactions):
Key commands: {', '.join([i['user'][:30] + '...' for i in self.session_interactions[-5:]])}
Context: Voice automation session with user preference for detailed responses.
Status: Session compressed to preserve memory."""

        # Save current session and restart
        self._save_session_notes()
        self._restart_claude_session_with_summary(summary)

        print(f"✅ Session compressed: {self.session_token_count:.0f} tokens → {len(summary)} chars")

    def _save_session_notes(self):
        """Save session notes for reference"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        notes_path = Path(f"voice_session_notes_{timestamp}.md")

        notes_content = f"""# Voice Session Notes - {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Session Statistics
- Duration: {(time.time() - self.session_start)/60:.1f} minutes
- Commands: {len(self.session_interactions)}
- Estimated tokens: {self.session_token_count:.0f}

## Key Interactions
"""

        for interaction in self.session_interactions[-10:]:  # Last 10 interactions
            notes_content += f"- **\"{interaction['user']}\"**\n"
            notes_content += f"  Response: {interaction['claude'][:100]}...\n\n"

        notes_path.write_text(notes_content)
        print(f"📝 Session notes saved: {notes_path}")

    def _restart_claude_session_with_summary(self, summary: str):
        """Restart Claude Code session with compressed context"""
        if self.claude_session:
            self.claude_session.terminate()

        # Reset counters
        self.session_token_count = len(summary)
        self.session_interactions = [{"user": "Context", "claude": summary, "tokens": len(summary)}]

        # Start new session with summary
        self._start_persistent_claude_session()

    def _fallback_single_shot(self, text: str) -> str:
        """Fallback to single-shot Claude Code if persistent session fails"""
        try:
            result = subprocess.run([
                'claude', '-p',
                '--allowed-tools', 'Bash(open:*,touch:*,mkdir:*)',
                '--', f"Help with: {text}"
            ], capture_output=True, text=True, timeout=30)

            return result.stdout.strip() if result.returncode == 0 else "Fallback failed"

        except Exception as e:
            return f"Error: {e}"

    def start_listening(self):
        """Start voice automation"""
        if not STT_AVAILABLE:
            print("❌ RealtimeSTT not available. Install requirements:")
            print("   pip install RealtimeSTT")
            return

        try:
            self.print_banner()

            # Initialize echo blocker if available
            if ECHO_BLOCKER_AVAILABLE:
                self.echo_blocker = EnhancedEchoBlocker()
                print("✅ Echo blocker initialized")
            else:
                print("⚠️ Echo blocker not available - continuing without")

            # Initialize RealtimeSTT
            print("🎤 Initializing voice recognition...")
            self.recorder = AudioToTextRecorder(
                model="base.en",
                language="en",
                spinner=False,
                use_microphone=True,
                level=20
            )

            self.listening = True
            print("🎯 VOICE TERMINAL ACTIVE - Speak your commands!")

            # Voice processing loop
            def voice_loop():
                while self.listening:
                    try:
                        text = self.recorder.text()
                        if text and text.strip():
                            self.process_voice_command(text.strip())
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"⚠️ Voice error: {e}")
                        break

            voice_thread = threading.Thread(target=voice_loop, daemon=True)
            voice_thread.start()

            # Keep main thread alive
            while self.listening:
                time.sleep(0.5)

        except KeyboardInterrupt:
            self.stop_listening()
        except Exception as e:
            print(f"❌ Initialization failed: {e}")

    def stop_listening(self):
        """Clean shutdown of voice automation"""
        self.listening = False

        if self.recorder:
            try:
                print("🔄 Shutting down voice recognition...")
                self.recorder.shutdown()
                time.sleep(0.5)  # Give time for clean shutdown
            except Exception as e:
                pass  # Suppress shutdown errors

        print(f"\n🛑 Voice Terminal stopped cleanly")
        print(f"📊 Commands processed: {self.command_count}")


def main():
    """Main entry point"""
    # Handle CTRL+C gracefully
    def signal_handler(sig, frame):
        print(f"\n\n👋 Voice Terminal terminated")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Check if Claude Code is available
    try:
        subprocess.run(['claude', '--version'], capture_output=True, check=True)
        print("✅ Claude Code available")
    except:
        print("❌ Claude Code not found. Install from: https://claude.ai/download")
        return

    # Start voice terminal
    terminal = VoiceTerminal()
    terminal.start_listening()


if __name__ == "__main__":
    main()