#!/usr/bin/env python3
"""
Claude Code Voice Interface - Direct Pipeline Architecture
Autonomous DollhouseMCP Implementation

BREAKTHROUGH: Voice → RealtimeSTT → Claude Code → System
Eliminates all custom automation complexity - uses proven Claude Code tools
"""

import asyncio
import sys
import os
import json
import threading
import time
from threading import Lock
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import numpy as np

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from RealtimeSTT import AudioToTextRecorder
from enhanced_echo_blocker_with_voice_fingerprinting import EnhancedEchoBlocker
from claude_code_voice_bridge import ClaudeCodeVoiceBridge

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'claude_code_voice_interface_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables - SIMPLIFIED ARCHITECTURE
echo_blocker = None
claude_bridge = None
session_dir = None
always_listening_active = False
recorder = None
conversation_history = []
correction_lock = Lock()

def setup_session_directory():
    """Setup session directory for audio recordings"""
    global session_dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(f"claude_code_session_{timestamp}")
    session_dir.mkdir(exist_ok=True)
    print(f"📁 Session directory: {session_dir}")

def record_ai_voice(text: str) -> str:
    """Record AI voice using macOS TTS"""
    if not session_dir:
        setup_session_directory()

    timestamp = datetime.now().strftime("%H%M%S")
    ai_audio_file = f"ai_voice_{timestamp}.wav"
    ai_filepath = session_dir / ai_audio_file

    try:
        safe_text = text.replace('"', '\\"').replace("'", "\\'")
        os.system(f'say "{safe_text}" -o "{ai_filepath}" --data-format=LEI16@16000')
        os.system(f'afplay "{ai_filepath}"')
        print(f"🔊 AI Voice: {ai_audio_file}")
        return str(ai_filepath)
    except Exception as e:
        print(f"⚠️  AI voice failed: {e}")
        return ""

def add_to_conversation_history(user_text: str, ai_response: str):
    """Track conversation for context"""
    global conversation_history

    with correction_lock:
        conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_text': user_text,
            'ai_response': ai_response
        })

        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

def get_conversation_context(exchanges: int = 3) -> str:
    """Get recent conversation context"""
    global conversation_history

    with correction_lock:
        recent = conversation_history[-exchanges:] if conversation_history else []

    context_parts = []
    for exchange in recent:
        context_parts.append(f"User: {exchange['user_text']}")
        context_parts.append(f"Assistant: {exchange['ai_response']}")

    return "\\n".join(context_parts)

@app.route('/')
def index():
    """Serve the Claude Code voice interface"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Claude Code Voice Interface</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .title {
            font-size: 2.2em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 20px;
        }

        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 20px;
        }

        button {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        #startListening {
            background: linear-gradient(135deg, #2ECC71, #27AE60);
            color: white;
        }

        #stopListening {
            background: linear-gradient(135deg, #E74C3C, #C0392B);
            color: white;
        }

        .status {
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            font-weight: 500;
        }

        .status.idle {
            background: linear-gradient(135deg, #3498DB, #2980B9);
            color: white;
        }

        .status.listening {
            background: linear-gradient(135deg, #2ECC71, #27AE60);
            color: white;
            animation: pulse 1.5s infinite;
        }

        .capabilities {
            background: rgba(102, 126, 234, 0.1);
            border: 2px solid #667eea;
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
        }

        .conversation {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            max-height: 400px;
            overflow-y: auto;
        }

        .conversation-item {
            margin: 10px 0;
            padding: 8px;
            border-radius: 8px;
        }

        .user-message {
            background: #e3f2fd;
            text-align: right;
        }

        .ai-message {
            background: #f1f8e9;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🎙️ Claude Code Voice Interface</h1>
            <div class="subtitle">Direct Pipeline: Voice → Claude Code → System Automation</div>
            <div class="subtitle">Eliminates Custom Complexity - Uses Proven Tools</div>
        </div>

        <div class="controls">
            <button id="startListening" onclick="startListening()">🎤 Start Claude Code Voice</button>
            <button id="stopListening" onclick="stopListening()" disabled>Stop Listening</button>
        </div>

        <div id="status" class="status idle">Status: Ready for Claude Code Automation</div>

        <div class="capabilities">
            <h3>🛠️ Claude Code Automation Capabilities</h3>
            <div><strong>Apps:</strong> "Open TextEdit", "Launch Safari", "Open VSCode"</div>
            <div><strong>URLs:</strong> "Go to hackernews.com", "Navigate to github.com"</div>
            <div><strong>Files:</strong> "Create new note", "List files", "Edit document"</div>
            <div><strong>Web:</strong> "Search for Python tutorials", "What's the weather?"</div>
            <div><strong>Chat:</strong> Natural conversation with memory</div>
        </div>

        <div id="conversation" class="conversation">
            <div class="conversation-item ai-message">
                🎙️ Claude Code voice interface ready. Try: "Open TextEdit and create a new note"
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let isListening = false;
        let sessionStartTime = Date.now();

        socket.on('connect', () => {
            console.log('🔌 Connected to Claude Code voice interface');
        });

        socket.on('disconnect', () => {
            console.log('🔌 Disconnected from Claude Code voice interface');
        });

        function startListening() {
            console.log('🎤 Starting Claude Code listening...');
            socket.emit('start_listening');
            document.getElementById('startListening').disabled = true;
            document.getElementById('stopListening').disabled = false;
            document.getElementById('status').textContent = 'Status: Listening - Claude Code Processing Active';
            document.getElementById('status').className = 'status listening';
            isListening = true;
        }

        function stopListening() {
            socket.emit('stop_listening');
            document.getElementById('startListening').disabled = false;
            document.getElementById('stopListening').disabled = true;
            document.getElementById('status').textContent = 'Status: Ready for Claude Code Automation';
            document.getElementById('status').className = 'status idle';
            isListening = false;
        }

        socket.on('voice_result', function(data) {
            const conversation = document.getElementById('conversation');

            // Add user message
            const userDiv = document.createElement('div');
            userDiv.className = 'conversation-item user-message';
            userDiv.textContent = `🎤 You: ${data.user_text}`;
            conversation.appendChild(userDiv);

            // Add AI response
            const aiDiv = document.createElement('div');
            aiDiv.className = 'conversation-item ai-message';
            aiDiv.innerHTML = `🎙️ Claude Code: ${data.ai_response}<br><small>⚡ ${data.execution_time}ms • ${data.success ? '✅ Executed' : '❌ Failed'}</small><br><details><summary>Full Response</summary><pre>${data.full_response || 'No additional details'}</pre></details>`;
            conversation.appendChild(aiDiv);

            conversation.scrollTop = conversation.scrollHeight;
        });
    </script>
</body>
</html>
    ''')

@socketio.on('start_listening')
def start_listening():
    """Start Claude Code voice automation"""
    global always_listening_active, recorder, echo_blocker, claude_bridge

    print("🎙️ Starting Claude Code Voice Automation...")

    # Initialize components
    echo_blocker = EnhancedEchoBlocker()
    claude_bridge = ClaudeCodeVoiceBridge()
    print("🎙️ Claude Code Bridge initialized")

    always_listening_active = True

    def process_voice_command(text: str):
        """Process voice through Claude Code pipeline"""
        try:
            # Echo blocking
            is_echo, reason, _ = echo_blocker.is_likely_echo(text, audio_file_path=None)
            if is_echo:
                print(f"🔇 BLOCKED ECHO: '{text}' - {reason}")
                return

            print(f"✅ VOICE INPUT: '{text}'")

            # Get conversation context
            context = get_conversation_context(3)

            # Send to Claude Code for processing
            result = claude_bridge.process_voice_command(text, context)

            ai_response = result["response"]
            execution_time = f"{result['execution_time_ms']:.0f}ms"

            print(f"🎙️ CLAUDE CODE: {execution_time} - {ai_response}")

            # TTS response
            record_ai_voice(ai_response)

            # Update conversation history
            add_to_conversation_history(text, ai_response)

            # Emit to web interface
            socketio.emit('voice_result', {
                'user_text': text,
                'ai_response': ai_response,
                'execution_time': execution_time,
                'success': result["success"],
                'method': result["method"]
            })

        except Exception as e:
            print(f"⚠️  Claude Code processing failed: {e}")
            error_response = "Claude Code processing error"
            record_ai_voice(error_response)

            socketio.emit('voice_result', {
                'user_text': text,
                'ai_response': error_response,
                'execution_time': 'Error',
                'success': False,
                'method': 'error'
            })

    # Start voice recording
    try:
        recorder = AudioToTextRecorder(
            model="base.en",
            language="en",
            spinner=False,
            use_microphone=True,
            level=20
        )

        # RealtimeSTT continuous listening loop
        def voice_loop():
            try:
                while always_listening_active:
                    text = recorder.text()
                    if text and text.strip():
                        process_voice_command(text)
                    time.sleep(0.1)
            except Exception as e:
                print(f"⚠️  Voice loop error: {e}")

        voice_thread = threading.Thread(target=voice_loop, daemon=True)
        voice_thread.start()
        print("🎯 Claude Code Voice Automation Active")

        emit('status_update', {
            'status': 'listening',
            'message': 'Claude Code Voice Processing Active'
        })

    except Exception as e:
        print(f"⚠️  Voice initialization failed: {e}")

@socketio.on('stop_listening')
def stop_listening():
    """Stop Claude Code voice automation"""
    global always_listening_active, recorder

    always_listening_active = False

    if recorder:
        try:
            recorder.shutdown()
        except:
            pass
        recorder = None

    print("🛑 Claude Code Voice Automation stopped")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle disconnect"""
    global always_listening_active, recorder
    print("🔌 Client disconnected")
    always_listening_active = False
    if recorder:
        try:
            recorder.shutdown()
        except:
            pass
        recorder = None

if __name__ == '__main__':
    print("🎙️ CLAUDE CODE VOICE INTERFACE 2025")
    print("=" * 60)
    print("✅ Direct Pipeline: Voice → Claude Code → System")
    print("✅ Proven Tools: Uses Claude Code's reliable automation")
    print("✅ No Custom Complexity: Eliminates Ollama/pattern failures")
    print("=" * 60)

    setup_session_directory()

    print("🌐 Starting Claude Code Voice Interface...")
    print("🔗 Access at: http://localhost:8089")
    print("🎙️ Architecture: Direct voice-to-Claude Code automation")

    socketio.run(app, host='0.0.0.0', port=8089, debug=False, allow_unsafe_werkzeug=True)