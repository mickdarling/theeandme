#!/usr/bin/env python3
"""
Pure Naturalistic Voice Interface - LLM-Only Architecture
Autonomous DollhouseMCP Implementation - September 14, 2025

ARCHITECTURAL PRINCIPLE: Let the LLM do ALL the work
- No hard-coded patterns
- Natural language understanding for everything
- Direct execution of LLM-interpreted commands
- Single processing path for reliability
"""

import asyncio
import sys
import os
import json
import threading
import time
import wave
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
from semantic_voice_parser import SemanticVoiceParser
from voice_calibration_persistence import VoiceCalibrationManager

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'naturalistic_voice_interface_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables - SIMPLIFIED ARCHITECTURE
echo_blocker = None
semantic_parser = None
voice_calibration = None
session_dir = None
always_listening_active = False
recorder = None
conversation_history = []
correction_lock = Lock()

# Performance metrics
performance_metrics = {
    'session_start': time.time(),
    'total_interactions': 0,
    'successful_commands': 0,
    'llm_response_times': [],
    'pipeline_times': []
}

def setup_session_directory():
    """Setup session directory for audio recordings"""
    global session_dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(f"naturalistic_session_{timestamp}")
    session_dir.mkdir(exist_ok=True)
    print(f"📁 Session directory: {session_dir}")

def record_ai_voice(text: str, volume_reduction: float = 0.0) -> str:
    """Record AI voice generation using macOS TTS and PLAY it through speakers"""
    if not session_dir:
        setup_session_directory()

    timestamp = datetime.now().strftime("%H%M%S")
    ai_audio_file = f"ai_voice_{timestamp}.wav"
    ai_filepath = session_dir / ai_audio_file

    try:
        # Use macOS say command for TTS generation
        safe_text = text.replace('"', '\\"').replace("'", "\\'")
        os.system(f'say "{safe_text}" -o "{ai_filepath}" --data-format=LEI16@16000')

        # Audio optimization during calibration
        volume_args = []
        if volume_reduction > 0.0:
            volume_level = max(0.1, 1.0 - volume_reduction)
            volume_args = ['-v', str(volume_level)]
            print(f"🔉 Audio optimization: Volume reduced to {volume_level:.1f} during calibration")

        # Play the AI response through speakers
        play_cmd = ['afplay'] + volume_args + [str(ai_filepath)]
        os.system(' '.join(play_cmd))

        print(f"🔊 AI Voice recorded AND PLAYED: {ai_audio_file}")
        return str(ai_filepath)

    except Exception as e:
        print(f"⚠️  AI voice recording failed: {e}")
        return ""

def add_to_conversation_history(user_text: str, ai_response: str, response_type: str = "normal"):
    """Track conversation for context-aware processing"""
    global conversation_history

    with correction_lock:
        conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user_text': user_text,
            'ai_response': ai_response,
            'response_type': response_type
        })

        # Keep last 10 exchanges for context
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

def get_conversation_context(exchanges: int = 3) -> str:
    """Get recent conversation context for LLM analysis"""
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
    """Serve the naturalistic voice interface"""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Naturalistic Voice Interface 2025</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.4/socket.io.js"></script>
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
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            font-size: 1.2em;
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

        .connection-status {
            padding: 8px 16px;
            border-radius: 6px;
            margin: 10px 0;
            font-weight: 500;
            text-align: center;
            font-size: 14px;
        }

        .connection-status.connected {
            background: linear-gradient(135deg, #2ECC71, #27AE60);
            color: white;
        }

        .connection-status.disconnected {
            background: linear-gradient(135deg, #E74C3C, #C0392B);
            color: white;
        }

        .capabilities {
            background: rgba(102, 126, 234, 0.1);
            border: 2px solid #667eea;
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
        }

        .capability-item {
            margin: 8px 0;
            padding: 5px 0;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        .conversation {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            max-height: 300px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🧠 Naturalistic Voice Interface</h1>
            <div class="subtitle">Pure LLM-Driven Computer Automation</div>
            <div class="subtitle">No Hard-Coded Patterns - Natural Language Understanding Only</div>
        </div>

        <div class="controls">
            <button id="startListening" onclick="startListening()">🎤 Start Naturalistic Listening</button>
            <button id="stopListening" onclick="stopListening()" disabled>Stop Listening</button>
        </div>

        <div id="status" class="status idle">Status: Ready for Naturalistic Processing</div>

        <div id="connectionStatus" class="connection-status connected">
            🟢 Connected - Naturalistic Voice Interface Active
        </div>

        <div class="capabilities">
            <h3>🌟 Naturalistic Capabilities</h3>
            <div class="capability-item">🌐 <strong>Browser Navigation:</strong> "Go to hackernews.com" → Actually navigates</div>
            <div class="capability-item">📝 <strong>Document Creation:</strong> "Make a new note in Notes" → Creates actual note</div>
            <div class="capability-item">💬 <strong>Natural Conversation:</strong> "What is open source software?" → Real explanations</div>
            <div class="capability-item">🧠 <strong>Context Memory:</strong> Remembers conversation context</div>
            <div class="capability-item">⚡ <strong>Command Execution:</strong> Actually performs requested actions</div>
        </div>

        <div id="conversation" class="conversation">
            <div class="conversation-item ai-message">
                🧠 Pure LLM interface ready. Try: "Open Safari and go to hackernews.com"
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let isListening = false;

        // Connection monitoring
        function updateConnectionStatus(status) {
            const statusEl = document.getElementById('connectionStatus');
            statusEl.className = `connection-status ${status}`;

            switch(status) {
                case 'connected':
                    statusEl.textContent = '🟢 Connected - Naturalistic Voice Interface Active';
                    break;
                case 'disconnected':
                    statusEl.textContent = '🔴 Disconnected - Reconnecting...';
                    break;
                case 'reconnecting':
                    statusEl.textContent = '🟡 Reconnecting - Please wait...';
                    break;
            }
        }

        socket.on('connect', () => {
            updateConnectionStatus('connected');
            console.log('🔌 Connected to naturalistic voice interface');
        });

        socket.on('disconnect', () => {
            updateConnectionStatus('disconnected');
            setTimeout(() => {
                if (socket.disconnected) {
                    updateConnectionStatus('reconnecting');
                    socket.connect();
                }
            }, 3000);
        });

        // Prevent accidental tab close
        window.addEventListener('beforeunload', (event) => {
            if (socket.connected && isListening) {
                event.preventDefault();
                event.returnValue = 'Naturalistic voice interface is active. Close anyway?';
            }
        });

        function startListening() {
            socket.emit('start_naturalistic_listening');
            document.getElementById('startListening').disabled = true;
            document.getElementById('stopListening').disabled = false;
            document.getElementById('status').textContent = 'Status: Listening with Pure LLM Processing';
            document.getElementById('status').className = 'status listening';
            isListening = true;
        }

        function stopListening() {
            socket.emit('stop_naturalistic_listening');
            document.getElementById('startListening').disabled = false;
            document.getElementById('stopListening').disabled = true;
            document.getElementById('status').textContent = 'Status: Ready for Naturalistic Processing';
            document.getElementById('status').className = 'status idle';
            isListening = false;
        }

        // Handle voice processing results
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
            aiDiv.innerHTML = `🧠 Assistant: ${data.ai_response}<br><small>⚡ ${data.processing_time}ms • ${data.method}</small>`;
            conversation.appendChild(aiDiv);

            // Scroll to bottom
            conversation.scrollTop = conversation.scrollHeight;
        });

        socket.on('status_update', function(data) {
            document.getElementById('status').textContent = `Status: ${data.message}`;
            document.getElementById('status').className = `status ${data.status}`;
        });
    </script>
</body>
</html>
    ''')

@socketio.on('start_naturalistic_listening')
def start_naturalistic_listening():
    """Start pure LLM voice processing"""
    global always_listening_active, recorder, echo_blocker, semantic_parser, voice_calibration

    print("🧠 Starting Naturalistic Voice Processing...")

    # Initialize echo blocker
    echo_blocker = EnhancedEchoBlocker()
    print("🧠 Enhanced Echo Blocker initialized")

    # Initialize semantic parser - SINGLE PROCESSING PATH
    semantic_parser = SemanticVoiceParser()
    print(f"🧠 Naturalistic LLM Parser: {'ENABLED' if semantic_parser.is_available else 'DISABLED'}")

    # Initialize voice calibration
    voice_calibration = VoiceCalibrationManager()
    print("🎵 Voice Calibration: ENABLED")

    always_listening_active = True

    def process_voice_command(text: str):
        """Pure LLM processing pipeline"""
        pipeline_start = time.time()
        performance_metrics['total_interactions'] += 1

        try:
            # Echo blocking
            is_echo, reason, detection_data = echo_blocker.is_likely_echo(text, audio_file_path=None)

            if is_echo:
                print(f"🔇 BLOCKED ECHO: '{text}' - {reason}")
                return

            print(f"✅ PASSED: '{text}' - Human voice detected")

            # PURE LLM PROCESSING
            processing_start = time.time()
            print("🧠 Processing with naturalistic LLM...")

            # Get conversation context
            context = get_conversation_context(3)

            # Parse with LLM
            intent = semantic_parser.parse_voice_command(text, context)

            processing_end = time.time()
            processing_time = (processing_end - processing_start) * 1000

            # Get conversational response
            ai_response = intent.parameters.get('response', 'I understand your request.') if intent.parameters else 'How can I help you?'

            # Execute if it's an action command
            execution_success = False
            if intent.intent_type not in ["chat", "unknown"]:
                execution_success = semantic_parser.execute_command(intent)
                if execution_success:
                    print(f"✅ NATURALISTIC EXECUTION: {intent.intent_type} successful")
                    performance_metrics['successful_commands'] += 1
                else:
                    print(f"⚠️  NATURALISTIC EXECUTION: {intent.intent_type} failed")

            print(f"🧠 NATURALISTIC SUCCESS: {processing_time:.0f}ms - {ai_response}")
            performance_metrics['llm_response_times'].append(processing_time)

            # TTS generation with audio optimization
            tts_start = time.time()
            calibration = voice_calibration.get_current_state()
            volume_reduction = 0.3 if calibration.get('learning_phase', False) else 0.0
            ai_audio_path = record_ai_voice(ai_response, volume_reduction=volume_reduction)

            tts_end = time.time()
            total_pipeline_time = (tts_end - pipeline_start) * 1000
            performance_metrics['pipeline_times'].append(total_pipeline_time)

            # Update conversation history
            add_to_conversation_history(text, ai_response, "naturalistic")

            # Emit result to web interface
            socketio.emit('voice_result', {
                'user_text': text,
                'ai_response': ai_response,
                'processing_time': f"{processing_time:.0f}ms",
                'total_time': f"{total_pipeline_time:.0f}ms",
                'method': 'naturalistic-llm',
                'execution_success': execution_success,
                'intent_type': intent.intent_type
            })

            print(f"🤖 AI Response: '{ai_response}' (Pipeline: {total_pipeline_time:.0f}ms)")

        except Exception as e:
            print(f"⚠️  Naturalistic processing failed: {e}")
            error_response = "I'm sorry, I encountered an error processing that request."
            ai_audio_path = record_ai_voice(error_response)

            socketio.emit('voice_result', {
                'user_text': text,
                'ai_response': error_response,
                'processing_time': 'Error',
                'method': 'error-fallback',
                'execution_success': False
            })

    # Start RealtimeSTT
    print("🎤 Initializing RealtimeSTT with calibrated settings...")

    try:
        recorder = AudioToTextRecorder(
            model="base.en",
            language="en",
            spinner=False,
            use_microphone=True,
            level=20,
            sample_rate=16000,
            channels=1,
            chunk_size=1024,
            compute_type="default"
        )

        recorder.start(process_voice_command)
        print("🎯 Naturalistic Voice Processing Active")

        emit('status_update', {
            'status': 'listening',
            'message': 'Naturalistic Listening Active - Pure LLM Processing'
        })

    except Exception as e:
        print(f"⚠️  RealtimeSTT initialization failed: {e}")
        emit('status_update', {
            'status': 'error',
            'message': f'Audio initialization failed: {e}'
        })

@socketio.on('stop_naturalistic_listening')
def stop_naturalistic_listening():
    """Stop naturalistic voice processing"""
    global always_listening_active, recorder

    always_listening_active = False

    if recorder:
        try:
            recorder.shutdown()
        except Exception as e:
            print(f"⚠️  Error shutting down recorder: {e}")
        recorder = None

    emit('status_update', {
        'status': 'idle',
        'message': 'Naturalistic Processing Stopped'
    })

    print("🛑 Naturalistic Voice Processing stopped")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    global always_listening_active, recorder

    print("🔌 Client disconnected - cleaning up naturalistic interface")
    always_listening_active = False

    if recorder:
        try:
            recorder.shutdown()
        except Exception as e:
            print(f"⚠️  Error shutting down recorder: {e}")
        recorder = None

    print("✅ Naturalistic interface cleanup complete")

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("🔌 Client connected to naturalistic voice interface")

    emit('status_update', {
        'status': 'idle',
        'message': 'Connected - Ready for Naturalistic Processing 🧠'
    })

if __name__ == '__main__':
    print("🧠 NATURALISTIC VOICE INTERFACE 2025")
    print("=" * 60)
    print("✅ Pure LLM Processing (No Pattern Matching)")
    print("✅ Natural Language Understanding")
    print("✅ Browser Navigation & Document Creation")
    print("✅ Conversation Memory & Context")
    print("✅ Real Command Execution")
    print("=" * 60)

    # Setup session directory
    setup_session_directory()

    # Start the naturalistic interface
    print("🌐 Starting Naturalistic Voice Interface...")
    print("🔗 Access at: http://localhost:8088")
    print("📁 Session files:", session_dir)
    print("🧠 Architecture: Pure LLM-driven naturalistic automation")

    socketio.run(app, host='0.0.0.0', port=8088, debug=False, allow_unsafe_werkzeug=True)