#!/usr/bin/env python3
"""
Simple Working Voice Interface - Back to Basics
Based on user insight: "If it's close in time + close in content = AI echo, block it"

This implements the OBVIOUS solution that should have worked from the start.
"""

import asyncio
import sys
import os
import time
import threading
import aiohttp
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import re
from RealtimeSTT import AudioToTextRecorder
from simple_effective_echo_blocker import SimpleEchoBlocker

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple_working_voice_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
recorder = None
echo_blocker = SimpleEchoBlocker()
always_listening_active = False
is_speaking = False
last_response_time = 0
interaction_count = 0

# Performance tracking
stats = {
    'transcriptions': 0,
    'echo_blocked': 0,
    'user_voice_passed': 0,
    'accuracy': 0.0
}

# AI prompt - SLIGHTLY LONGER responses for better echo detection
CONTEXT_PROMPT = """You are testing a voice interface. Keep responses to 3-8 words maximum. Use complete short phrases. Examples: "I understand what you said", "That sounds good to me", "Let me think about that", "I can help you with this". This helps with echo cancellation accuracy."""

async def call_ollama(prompt, max_tokens=25):
    """Call Ollama with very short response limit"""
    try:
        full_prompt = f"{CONTEXT_PROMPT}\n\nUser: {prompt}\n\nAssistant:"

        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama3.1:8b",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.3
                }
            }

            async with session.post("http://localhost:11434/api/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "OK")
                else:
                    return "Error"
    except Exception as e:
        return f"Error: {str(e)}"

def transcription_callback(text):
    """Simple transcription callback with effective echo blocking"""
    global interaction_count, is_speaking, last_response_time, stats

    if not text.strip():
        return

    stats['transcriptions'] += 1
    interaction_count += 1

    print(f"[STT] Transcribed: '{text}'")

    # SIMPLE BUT EFFECTIVE: Check if this looks like an echo
    is_echo, reason = echo_blocker.is_likely_echo(text)

    if is_echo:
        stats['echo_blocked'] += 1
        print(f"🔇 ECHO BLOCKED: '{text}' - {reason}")

        socketio.emit('echo_blocked', {
            'text': text,
            'reason': reason,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        socketio.emit('status_update', {
            'status': 'listening',
            'message': '🔇 Echo blocked - Ready for your voice!'
        })
        return

    # User voice detected - process it
    stats['user_voice_passed'] += 1
    print(f"✅ USER VOICE: '{text}'")

    # Send transcription result
    socketio.emit('transcription_result', {
        'text': text,
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'interaction': interaction_count
    })

    # Generate AI response
    def ai_response_task():
        global is_speaking, last_response_time

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            socketio.emit('status_update', {
                'status': 'processing',
                'message': '🤖 AI thinking (short response)...'
            })

            ai_response = loop.run_until_complete(call_ollama(text, max_tokens=8))
            loop.close()

            if "Error" not in ai_response:
                # Clean up response (remove quotes, extra spaces)
                ai_response = ai_response.strip().strip('"\'').strip()

                # Update echo blocker with AI response and timing
                speaking_duration = len(ai_response.split()) * 0.5  # Estimate speaking time
                echo_blocker.set_ai_response(ai_response, speaking_duration)

                socketio.emit('ai_response', {
                    'text': ai_response,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })

                is_speaking = True

                def speak_and_track():
                    global is_speaking, last_response_time
                    try:
                        # Escape for shell
                        safe_response = ai_response.replace('"', '\\"').replace("'", "\\'")
                        os.system(f'say "{safe_response}"')
                    finally:
                        is_speaking = False
                        last_response_time = time.time()

                speak_thread = threading.Thread(target=speak_and_track)
                speak_thread.daemon = True
                speak_thread.start()

                # Update stats
                efficiency = stats['user_voice_passed'] / max(stats['transcriptions'], 1)
                stats['accuracy'] = efficiency

                socketio.emit('stats_update', {
                    'transcriptions': stats['transcriptions'],
                    'echo_blocked': stats['echo_blocked'],
                    'user_passed': stats['user_voice_passed'],
                    'efficiency': f"{efficiency:.1%}"
                })

                if always_listening_active:
                    socketio.emit('status_update', {
                        'status': 'listening',
                        'message': '👂 Listening - Simple echo blocking active'
                    })
                else:
                    socketio.emit('status_update', {
                        'status': 'ready',
                        'message': '🟢 Ready for next input'
                    })

            else:
                socketio.emit('error_message', {
                    'message': f'❌ AI Error: {ai_response}',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })

        except Exception as e:
            socketio.emit('error_message', {
                'message': f'❌ Response error: {str(e)}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })

    # Run AI response in background
    thread = threading.Thread(target=ai_response_task)
    thread.daemon = True
    thread.start()

def create_realtime_recorder():
    """Create RealtimeSTT recorder with proven settings"""
    print("🔧 Creating RealtimeSTT recorder...")

    recorder = AudioToTextRecorder(
        # Proven working settings
        model="base.en",
        language="en",
        silero_sensitivity=0.4,
        webrtc_sensitivity=2,
        post_speech_silence_duration=0.3,
        min_length_of_recording=0.1,
        min_gap_between_recordings=0.05,
        pre_recording_buffer_duration=0.3,  # The breakthrough feature
        input_device_index=2,  # Live Streamer CAM 513
        sample_rate=16000,
        enable_realtime_transcription=True,
        use_microphone=True,
        spinner=False,
        level=20,
    )

    print("✅ RealtimeSTT recorder created")
    return recorder

async def initialize_components():
    """Initialize simple components"""
    global recorder

    try:
        print("✅ Creating RealtimeSTT recorder...")
        recorder = create_realtime_recorder()

        # Test Ollama connection
        test_response = await call_ollama("Hello test", max_tokens=5)
        if "Error" in test_response:
            raise Exception(f"Ollama error: {test_response}")
        print("✅ Ollama connection verified")

        print("✅ Simple echo blocker ready")
        return True

    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Simple Working Voice Interface</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .simple-badge {
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            display: inline-block;
            margin: 10px 0;
            box-shadow: 0 4px 15px rgba(231,76,60,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .stat-panel {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.8;
            margin-top: 5px;
        }
        .status {
            text-align: center;
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            font-weight: bold;
            font-size: 1.3em;
            transition: all 0.3s ease;
        }
        .status.ready { background: rgba(40, 167, 69, 0.3); border: 2px solid #28a745; }
        .status.listening { background: rgba(220, 53, 69, 0.3); border: 2px solid #dc3545; animation: pulse 1s infinite; }
        .status.processing { background: rgba(255, 193, 7, 0.3); border: 2px solid #ffc107; }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        .big-button {
            color: white;
            padding: 15px 30px;
            border-radius: 40px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 0 10px;
            min-width: 200px;
            display: inline-block;
            border: none;
        }
        .start-btn { background: rgba(40, 167, 69, 0.8); border: 3px solid #28a745; }
        .start-btn.active { background: rgba(40, 167, 69, 1); animation: pulse 2s infinite; }
        .stop-btn { background: rgba(108, 117, 125, 0.8); border: 3px solid #6c757d; }

        .conversation {
            max-height: 400px;
            overflow-y: auto;
            margin: 20px 0;
            padding: 25px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            font-size: 1.1em;
            line-height: 1.6;
        }
        .message {
            margin: 15px 0;
            padding: 12px 18px;
            border-radius: 12px;
            max-width: 85%;
            word-wrap: break-word;
        }
        .user-message { background: rgba(0, 123, 255, 0.3); border: 2px solid #007bff; margin-left: auto; text-align: right; }
        .ai-message { background: rgba(40, 167, 69, 0.3); border: 2px solid #28a745; margin-right: auto; }
        .echo-blocked { background: rgba(231, 76, 60, 0.3); border: 2px solid #e74c3c; text-align: center; font-style: italic; }
        .system-message { background: rgba(108, 117, 125, 0.3); border: 2px solid #6c757d; text-align: center; font-style: italic; }

        .timestamp {
            font-size: 0.8em;
            opacity: 0.8;
            margin-top: 6px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Simple Working Voice Interface</h1>
            <div class="simple-badge">✨ Time + Content Echo Blocking</div>
            <p>Back to basics: If it's close in time AND close in content → it's an echo → block it!</p>
        </div>

        <div class="stats-grid">
            <div class="stat-panel">
                <div class="stat-number" id="totalTranscriptions">0</div>
                <div class="stat-label">Total Transcriptions</div>
            </div>
            <div class="stat-panel">
                <div class="stat-number" id="echoBlocked">0</div>
                <div class="stat-label">Echo Blocked</div>
            </div>
            <div class="stat-panel">
                <div class="stat-number" id="userPassed">0</div>
                <div class="stat-label">User Voice Passed</div>
            </div>
            <div class="stat-panel">
                <div class="stat-number" id="efficiency">0%</div>
                <div class="stat-label">System Efficiency</div>
            </div>
        </div>

        <div id="status" class="status ready">
            🟢 Simple working system ready - RealtimeSTT + Basic Echo Blocking
        </div>

        <div class="controls">
            <button id="startBtn" class="big-button start-btn" onclick="toggleListening()">
                🎯 Start Simple Listening
            </button>
            <button id="stopBtn" class="big-button stop-btn" onclick="stopListening()" style="display: none;">
                ⏹️ Stop
            </button>
        </div>

        <div id="conversation" class="conversation">
            <div class="system-message">
                🎯 Simple Working Voice Interface initialized
                <br>Ready to test time + content echo blocking!
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let listening = false;

        socket.on('status_update', function(data) {
            updateStatus(data.status, data.message);
        });

        socket.on('transcription_result', function(data) {
            addMessage('user', data.text, data.timestamp);
        });

        socket.on('ai_response', function(data) {
            addMessage('ai', data.text, data.timestamp);
        });

        socket.on('echo_blocked', function(data) {
            addMessage('echo', `ECHO BLOCKED: "${data.text}" - ${data.reason}`, data.timestamp);
        });

        socket.on('stats_update', function(data) {
            document.getElementById('totalTranscriptions').textContent = data.transcriptions;
            document.getElementById('echoBlocked').textContent = data.echo_blocked;
            document.getElementById('userPassed').textContent = data.user_passed;
            document.getElementById('efficiency').textContent = data.efficiency;
        });

        socket.on('error_message', function(data) {
            addMessage('system', data.message, data.timestamp);
        });

        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = `status ${status}`;
            statusEl.innerHTML = message;
        }

        function addMessage(type, content, timestamp) {
            const conversation = document.getElementById('conversation');

            if (conversation.children.length === 1 && conversation.children[0].classList.contains('system-message')) {
                conversation.innerHTML = '';
            }

            const messageEl = document.createElement('div');
            let className = 'message ';
            let icon = '';

            switch(type) {
                case 'user':
                    className += 'user-message';
                    icon = '🗣️';
                    break;
                case 'ai':
                    className += 'ai-message';
                    icon = '🤖';
                    break;
                case 'echo':
                    className += 'echo-blocked';
                    icon = '🔇';
                    break;
                default:
                    className += 'system-message';
                    icon = 'ℹ️';
            }

            messageEl.className = className;
            messageEl.innerHTML = `
                ${icon} ${content}
                <div class="timestamp">${timestamp}</div>
            `;

            conversation.appendChild(messageEl);
            conversation.scrollTop = conversation.scrollHeight;
        }

        function toggleListening() {
            if (!listening) {
                socket.emit('start_simple_listening');
                listening = true;

                document.getElementById('startBtn').classList.add('active');
                document.getElementById('startBtn').textContent = '👂 Simple Listening Active...';
                document.getElementById('stopBtn').style.display = 'inline-block';
            }
        }

        function stopListening() {
            if (listening) {
                socket.emit('stop_simple_listening');
                listening = false;

                document.getElementById('startBtn').classList.remove('active');
                document.getElementById('startBtn').textContent = '🎯 Start Simple Listening';
                document.getElementById('stopBtn').style.display = 'none';
            }
        }

        socket.on('connect', function() {
            console.log('Connected to simple working voice server');
            updateStatus('ready', '🟢 Connected - Simple system ready');
        });

        socket.on('simple_listening_stopped', function() {
            stopListening();
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('start_simple_listening')
def handle_simple_listening():
    """Handle simple always-listening"""
    global always_listening_active, recorder

    if always_listening_active or not recorder:
        return

    always_listening_active = True

    def simple_listening_task():
        """Simple listening with effective echo blocking"""
        global always_listening_active, is_speaking, last_response_time

        try:
            socketio.emit('status_update', {
                'status': 'listening',
                'message': '👂 Simple listening active - Time + content echo blocking'
            })

            print("🎯 Starting simple RealtimeSTT listening...")

            while always_listening_active:
                try:
                    # Basic cooldown to avoid immediate feedback
                    time_since_response = time.time() - last_response_time
                    if time_since_response < 0.5 or is_speaking:
                        if is_speaking:
                            socketio.emit('status_update', {
                                'status': 'processing',
                                'message': '🔊 AI speaking - waiting...'
                            })
                        time.sleep(0.1)
                        continue

                    # Ready to listen
                    socketio.emit('status_update', {
                        'status': 'listening',
                        'message': '👂 Listening - Simple echo blocking active'
                    })

                    # Get transcription from RealtimeSTT
                    transcribed_text = recorder.text()

                    if transcribed_text and transcribed_text.strip():
                        print(f"[Simple STT] Got: {transcribed_text}")
                        transcription_callback(transcribed_text)
                        time.sleep(0.2)  # Brief pause

                except Exception as e:
                    if always_listening_active:
                        print(f"Simple listening error: {e}")
                        time.sleep(1)

        except Exception as e:
            print(f"Simple listening task error: {e}")
        finally:
            always_listening_active = False
            print("🛑 Simple listening stopped")
            socketio.emit('simple_listening_stopped')

    # Start simple listening in background
    thread = threading.Thread(target=simple_listening_task)
    thread.daemon = True
    thread.start()

@socketio.on('stop_simple_listening')
def handle_stop_simple_listening():
    """Stop simple listening"""
    global always_listening_active, is_speaking

    always_listening_active = False
    is_speaking = False

    socketio.emit('status_update', {
        'status': 'ready',
        'message': '🟢 Simple listening stopped'
    })

    socketio.emit('simple_listening_stopped')

if __name__ == '__main__':
    print("🎯 Starting Simple Working Voice Interface...")
    print("💡 Based on user insight: Time + Content correlation")
    print("🎯 FEATURES:")
    print("   ✅ RealtimeSTT sentence capture (working)")
    print("   ⏰ Time-based echo detection")
    print("   📝 Content similarity matching")
    print("   🤖 Very short AI responses (1-3 words)")
    print("   📊 Real-time performance tracking")

    # Initialize components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()

    if not success:
        print("❌ Failed to initialize simple components")
        sys.exit(1)

    # Set up RealtimeSTT transcription callback
    if recorder:
        recorder.set_microphone(True)
        print("✅ RealtimeSTT callback configured")

    print("🌐 Simple interface: http://localhost:8084")
    print("🎯 Ready for SIMPLE but EFFECTIVE voice interface testing!")

    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=8084, debug=False, allow_unsafe_werkzeug=True)