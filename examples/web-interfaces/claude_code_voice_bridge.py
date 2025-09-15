#!/usr/bin/env python3
"""
Claude Code Voice Bridge - Direct Pipeline Implementation
Autonomous DollhouseMCP Team Implementation

ARCHITECTURE: Voice → RealtimeSTT → Claude Code Terminal → System
PRINCIPLE: Use proven Claude Code tools instead of building custom automation
"""

import subprocess
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any

class ClaudeCodeVoiceBridge:
    """Direct voice-to-Claude Code automation bridge"""

    def __init__(self):
        self.claude_executable = "claude"
        self.safe_tools = [
            "Bash(open:*,ls:*,pwd:*,echo:*,touch:*,mkdir:*,which:*)",
            "Read", "Write", "Edit", "Grep", "Glob", "WebSearch"
        ]
        self.stats = {
            "commands_executed": 0,
            "successful_executions": 0,
            "average_response_time": 0.0
        }

    def process_voice_command(self, voice_text: str, conversation_context: str = "") -> Dict[str, Any]:
        """Send voice command directly to Claude Code for execution"""
        start_time = time.time()

        try:
            # Build Claude Code prompt with context
            prompt = self._build_claude_prompt(voice_text, conversation_context)

            # Execute via Claude Code CLI - CONVERSATIONAL MODE
            result = subprocess.run([
                self.claude_executable,
                '-p',  # Print mode but no JSON - natural conversation
                '--allowed-tools', ','.join(self.safe_tools),
                '--', prompt  # Prompt as final argument
            ], capture_output=True, text=True, timeout=30)

            execution_time = (time.time() - start_time) * 1000
            self.stats["commands_executed"] += 1

            if result.returncode == 0:
                self.stats["successful_executions"] += 1
                # Use Claude Code's natural conversational response
                claude_response = result.stdout.strip()

                # Summarize for TTS if response is long
                if len(claude_response) > 100:
                    # Simple summarization - take first sentence + action summary
                    sentences = claude_response.split('.')
                    summary = sentences[0] + "." if sentences else claude_response
                    tts_response = summary[:80] + "..." if len(summary) > 80 else summary
                else:
                    tts_response = claude_response

                return {
                    "success": True,
                    "response": tts_response,
                    "full_response": claude_response,
                    "execution_time_ms": execution_time,
                    "method": "claude-code-conversational",
                    "claude_output": claude_response
                }
            else:
                return {
                    "success": False,
                    "response": f"Claude Code execution failed: {result.stderr}",
                    "execution_time_ms": execution_time,
                    "method": "claude-code-error",
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "response": "Claude Code execution timed out",
                "execution_time_ms": 30000,
                "method": "claude-code-timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Bridge execution failed: {e}",
                "execution_time_ms": (time.time() - start_time) * 1000,
                "method": "bridge-error",
                "error": str(e)
            }

    def _build_claude_prompt(self, voice_text: str, context: str = "") -> str:
        """Build effective prompt for Claude Code automation"""

        context_section = ""
        if context:
            context_section = f"""
Recent conversation context:
{context}

"""

        prompt = f"""You are a helpful voice assistant with access to system automation tools. {context_section}The user said: "{voice_text}"

Please help with this request by:
1. Explaining what you understand they want
2. Using the appropriate tools to help them
3. Describing what you're doing as you do it
4. Confirming the results

Available tools:
- Bash: System commands (open apps, close apps, system info)
- Write/Read/Edit: File operations
- WebSearch: Find information online
- Grep/Glob: Search files

Be conversational and explain your actions. For example:

"Open TextEdit" → "I'll open TextEdit for you using the system command." → Execute bash: open -a TextEdit → "TextEdit is now open!"

"Close Calculator" → "I'll close the Calculator app." → Execute bash: pkill Calculator → "Calculator has been closed."

"Create a note" → "I'll create a new note file for you." → Execute Write tool → "I've created a new note at ~/Documents/voice_note.txt"

Please help with their request and explain what you're doing."""

        return prompt

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get bridge performance statistics"""
        if self.stats["commands_executed"] > 0:
            success_rate = self.stats["successful_executions"] / self.stats["commands_executed"]
        else:
            success_rate = 0.0

        return {
            "commands_executed": self.stats["commands_executed"],
            "success_rate": f"{success_rate:.1%}",
            "average_response_time": f"{self.stats['average_response_time']:.0f}ms"
        }


def test_claude_code_bridge():
    """Test the Claude Code voice bridge with safe commands"""
    bridge = ClaudeCodeVoiceBridge()

    test_commands = [
        "Open TextEdit",
        "Go to GitHub",
        "What's the weather today?",
        "Create a new note",
        "List files in Documents"
    ]

    print("🧪 Testing Claude Code Voice Bridge")
    print("=" * 50)

    for command in test_commands:
        print(f"\n🎤 Voice Command: '{command}'")
        result = bridge.process_voice_command(command)

        if result["success"]:
            print(f"✅ SUCCESS ({result['execution_time_ms']:.0f}ms): {result['response']}")
        else:
            print(f"❌ FAILED ({result['execution_time_ms']:.0f}ms): {result['response']}")

    print(f"\n📊 Performance: {bridge.get_performance_stats()}")


if __name__ == "__main__":
    test_claude_code_bridge()