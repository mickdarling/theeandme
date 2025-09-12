#!/usr/bin/env python3
"""
Echo-Cancelled Voice Interface App - Production-Ready Always-Listening Mode

Solves the audio feedback loop problem through:
1. Audio ducking: Mute microphone during AI speech
2. Adaptive timeouts: Brief silence after responses
3. Volume gating: Ignore low-level audio during TTS
4. Echo detection: Pattern recognition for loop prevention
"""

import asyncio
import sys
import os
import json
import threading
import aiohttp
import time
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import sounddevice as sd
import numpy as np

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'echo_cancelled_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
stt = None
always_listening_active = False
listening_thread = None
is_speaking = False  # New: Track if AI is currently speaking
last_response_time = 0  # New: Track when last response finished
echo_prevention_active = False  # New: Echo prevention state

# Configuration
ECHO_PREVENTION_CONFIG = {
    'silence_after_response': 3.0,  # Seconds of silence after AI response
    'minimum_volume_threshold': 0.005,  # Ignore very quiet audio
    'ducking_enabled': True,  # Enable audio ducking
    'echo_detection_enabled': True,  # Enable echo pattern detection
    'max_similar_responses': 2,  # Prevent similar responses in sequence
}

# Recent responses for echo detection
recent_responses = []

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Echo-Cancelled Voice Interface</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
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
        .status {
            text-align: center;
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            font-weight: bold;
            font-size: 1.3em;
            transition: all 0.3s ease;
        }
        .status.ready {
            background: rgba(40, 167, 69, 0.3);
            border: 2px solid #28a745;
        }
        .status.listening {
            background: rgba(220, 53, 69, 0.3);
            border: 2px solid #dc3545;
            animation: pulse 1s infinite;
        }
        .status.processing {
            background: rgba(255, 193, 7, 0.3);
            border: 2px solid #ffc107;
        }
        .status.speaking {
            background: rgba(138, 43, 226, 0.3);
            border: 2px solid #8a2be2;
            animation: pulse 1.5s infinite;
        }
        .status.ducked {
            background: rgba(108, 117, 125, 0.3);
            border: 2px solid #6c757d;
        }
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
        .always-listening {
            background: rgba(40, 167, 69, 0.8);
            border: 3px solid #28a745;
        }
        .always-listening:hover:not(:disabled) {
            background: rgba(40, 167, 69, 1);
            transform: scale(1.05);
        }
        .always-listening.active {
            background: rgba(40, 167, 69, 1);
            animation: pulse 2s infinite;
        }
        .stop-listening {
            background: rgba(108, 117, 125, 0.8);
            border: 3px solid #6c757d;
        }
        .stop-listening:hover:not(:disabled) {
            background: rgba(108, 117, 125, 1);
            transform: scale(1.05);
        }
        .big-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .echo-prevention-panel {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .echo-indicators {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .indicator {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px 15px;
            border-radius: 10px;
            text-align: center;
            font-size: 0.9em;
        }
        .indicator.active {
            background: rgba(40, 167, 69, 0.3);
            border: 1px solid #28a745;
        }
        .conversation {
            max-height: 400px;
            overflow-y: auto;
            margin: 20px 0;
            padding: 25px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            font-size: 1.1em;
            line-height: 1.6;
        }
        .message {
            margin: 20px 0;
            padding: 15px 20px;
            border-radius: 15px;
            max-width: 85%;
            word-wrap: break-word;
        }
        .user-message {
            background: rgba(0, 123, 255, 0.3);
            border: 2px solid #007bff;
            margin-left: auto;
            text-align: right;
        }
        .ai-message {
            background: rgba(40, 167, 69, 0.3);
            border: 2px solid #28a745;
            margin-right: auto;
        }
        .system-message {
            background: rgba(108, 117, 125, 0.3);
            border: 2px solid #6c757d;
            text-align: center;
            font-style: italic;
        }
        .timestamp {
            font-size: 0.85em;
            opacity: 0.8;
            margin-top: 8px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚫🔊 Echo-Cancelled Voice Interface</h1>
            <p>Production-ready always-listening with feedback loop prevention</p>
        </div>
        
        <div id="status" class="status ready">
            🟢 Ready - Echo prevention active
        </div>
        
        <div class="controls">
            <button id="alwaysListenBtn" class="big-button always-listening" onclick="toggleAlwaysListening()">
                🔄 Start Always Listening
            </button>
            <button id="stopBtn" class="big-button stop-listening" onclick="stopListening()" style="display: none;">
                ⏹️ Stop Listening
            </button>
        </div>
        
        <div class="echo-prevention-panel">
            <h3>🛡️ Echo Prevention System</h3>
            <div class="echo-indicators">
                <div id="duckingIndicator" class="indicator">
                    🎤 Audio Ducking: <span>Ready</span>
                </div>
                <div id="volumeGateIndicator" class="indicator">
                    📊 Volume Gate: <span>Ready</span>
                </div>
                <div id="silenceIndicator" class="indicator">
                    ⏱️ Silence Timer: <span>Ready</span>
                </div>
                <div id="echoDetectionIndicator" class="indicator">
                    🔍 Echo Detection: <span>Ready</span>
                </div>
            </div>
        </div>
        
        <div id="conversation" class="conversation">
            <div class="system-message">
                Click "Start Always Listening" to begin echo-cancelled voice interaction...
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let alwaysListening = false;

        socket.on('status_update', function(data) {
            updateStatus(data.status, data.message);
        });

        socket.on('transcription_result', function(data) {
            addMessage('user', data.text, data.timestamp, {
                confidence: data.confidence,
                processing_time: data.processing_time
            });
        });

        socket.on('ai_response', function(data) {
            addMessage('ai', data.text, data.timestamp, {
                generation_time: data.generation_time
            });
        });

        socket.on('error_message', function(data) {
            addMessage('system', data.message, data.timestamp);
        });

        socket.on('echo_prevention_update', function(data) {
            updateEchoIndicators(data);
        });

        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = `status ${status}`;
            statusEl.innerHTML = message;
        }

        function updateEchoIndicators(data) {
            if (data.ducking !== undefined) {
                const indicator = document.getElementById('duckingIndicator');
                indicator.className = `indicator ${data.ducking ? 'active' : ''}`;
                indicator.innerHTML = `🎤 Audio Ducking: <span>${data.ducking ? 'ACTIVE' : 'Ready'}</span>`;
            }
            
            if (data.volume_gate !== undefined) {
                const indicator = document.getElementById('volumeGateIndicator');
                indicator.className = `indicator ${data.volume_gate ? 'active' : ''}`;
                indicator.innerHTML = `📊 Volume Gate: <span>${data.volume_gate ? 'BLOCKING' : 'Ready'}</span>`;
            }
            
            if (data.silence_timer !== undefined) {
                const indicator = document.getElementById('silenceIndicator');
                indicator.className = `indicator ${data.silence_timer > 0 ? 'active' : ''}`;
                indicator.innerHTML = `⏱️ Silence Timer: <span>${data.silence_timer > 0 ? data.silence_timer.toFixed(1) + 's' : 'Ready'}</span>`;
            }
            
            if (data.echo_detected !== undefined) {
                const indicator = document.getElementById('echoDetectionIndicator');
                indicator.className = `indicator ${data.echo_detected ? 'active' : ''}`;
                indicator.innerHTML = `🔍 Echo Detection: <span>${data.echo_detected ? 'ECHO BLOCKED' : 'Ready'}</span>`;
            }
        }

        function addMessage(type, content, timestamp, metadata) {
            const conversation = document.getElementById('conversation');
            
            if (conversation.children.length === 1 && conversation.children[0].classList.contains('system-message')) {
                conversation.innerHTML = '';
            }
            
            const messageEl = document.createElement('div');
            messageEl.className = `message ${type}-message`;
            
            let icon = type === 'user' ? '🗣️' : (type === 'ai' ? '🤖' : 'ℹ️');
            let metaText = '';
            if (metadata) {
                if (metadata.confidence !== undefined) metaText += ` (${(metadata.confidence * 100).toFixed(0)}% confidence)`;
                if (metadata.processing_time) metaText += ` • ${metadata.processing_time.toFixed(2)}s`;
                if (metadata.generation_time) metaText += ` • ${metadata.generation_time.toFixed(2)}s generation`;
            }
            
            messageEl.innerHTML = `
                ${icon} ${content}
                <div class="timestamp">${timestamp}${metaText}</div>
            `;
            
            conversation.appendChild(messageEl);
            conversation.scrollTop = conversation.scrollHeight;
        }

        function toggleAlwaysListening() {
            if (!alwaysListening) {
                socket.emit('start_always_listening');
                alwaysListening = true;
                
                document.getElementById('alwaysListenBtn').classList.add('active');
                document.getElementById('alwaysListenBtn').textContent = '🔄 Listening...';
                document.getElementById('stopBtn').style.display = 'inline-block';
            }
        }

        function stopListening() {
            if (alwaysListening) {
                socket.emit('stop_always_listening');
                alwaysListening = false;
                
                document.getElementById('alwaysListenBtn').classList.remove('active');
                document.getElementById('alwaysListenBtn').textContent = '🔄 Start Always Listening';
                document.getElementById('stopBtn').style.display = 'none';
            }
        }

        socket.on('connect', function() {
            console.log('Connected to echo-cancelled voice server');
            updateStatus('ready', '🟢 Connected - Echo prevention active');
        });

        socket.on('always_listening_stopped', function() {
            stopListening();
        });
    </script>
</body>
</html>
'''

async def call_ollama(prompt, max_tokens=100):
    """Direct call to Ollama API"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens
                }
            }
            
            async with session.post("http://localhost:11434/api/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "No response received")
                else:
                    return f"Error: HTTP {response.status}"
    except Exception as e:
        return f"Error calling Ollama: {str(e)}"

def is_similar_response(new_response, threshold=0.8):
    """Check if response is too similar to recent responses (echo detection)"""
    if not ECHO_PREVENTION_CONFIG['echo_detection_enabled']:
        return False
        
    if not recent_responses:
        return False
        
    new_words = set(new_response.lower().split())
    
    for prev_response in recent_responses[-ECHO_PREVENTION_CONFIG['max_similar_responses']:]:
        prev_words = set(prev_response.lower().split())
        
        if not new_words or not prev_words:
            continue
            
        intersection = new_words.intersection(prev_words)
        union = new_words.union(prev_words)
        
        similarity = len(intersection) / len(union) if union else 0
        
        if similarity > threshold:
            return True
            
    return False

def update_echo_indicators():
    """Send current echo prevention status to frontend"""
    global is_speaking, last_response_time, echo_prevention_active
    
    silence_remaining = max(0, ECHO_PREVENTION_CONFIG['silence_after_response'] - (time.time() - last_response_time))
    
    socketio.emit('echo_prevention_update', {
        'ducking': is_speaking,
        'volume_gate': echo_prevention_active,
        'silence_timer': silence_remaining,
        'echo_detected': False  # Will be set when echo is detected
    })

async def initialize_components():
    """Initialize STT component"""
    global stt
    
    try:
        # Initialize STT
        config = {
            'sample_rate': 16000,
            'whisper_model': 'base'
        }
        
        stt = WhisperSTT(config)
        await stt.initialize()
        print("✅ Whisper STT initialized")
        
        # Test Ollama connection
        test_response = await call_ollama("Say hello", max_tokens=5)
        if "Error" in test_response:
            raise Exception(f"Ollama error: {test_response}")
        print("✅ Ollama connection verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('start_always_listening')
def handle_always_listening():
    """Start continuous voice monitoring with echo cancellation"""
    global always_listening_active, listening_thread, is_speaking, last_response_time
    
    if always_listening_active:
        return
    
    always_listening_active = True
    is_speaking = False
    last_response_time = time.time()
    
    def continuous_listening():
        """Continuous voice monitoring loop with echo prevention"""
        global always_listening_active, is_speaking, last_response_time, echo_prevention_active
        
        try:
            # Import VAD for voice detection
            from audio.vad import SileroVAD
            
            vad_config = {
                'sample_rate': 16000,
                'vad_threshold': 0.7,
                'min_speech_duration_ms': 300,
                'silence_timeout_seconds': 2.0
            }
            
            # Initialize VAD
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            vad = SileroVAD(vad_config)
            loop.run_until_complete(vad.initialize())
            
            socketio.emit('status_update', {
                'status': 'listening',
                'message': '🔄 Always listening - Echo prevention active!'
            })
            
            # Continuous monitoring
            chunk_duration = 0.5  # 500ms chunks
            sample_rate = 16000
            device_id = 2
            chunk_frames = int(chunk_duration * sample_rate)
            
            while always_listening_active:
                try:
                    # Update echo prevention indicators
                    update_echo_indicators()
                    
                    # Check if we're in a silence period after AI response
                    time_since_response = time.time() - last_response_time
                    if time_since_response < ECHO_PREVENTION_CONFIG['silence_after_response']:
                        socketio.emit('status_update', {
                            'status': 'ducked',
                            'message': f'🔇 Silence period active ({ECHO_PREVENTION_CONFIG["silence_after_response"] - time_since_response:.1f}s remaining)'
                        })
                        time.sleep(0.5)
                        continue
                    
                    # Check if AI is currently speaking (audio ducking)
                    if is_speaking and ECHO_PREVENTION_CONFIG['ducked_enabled']:
                        socketio.emit('status_update', {
                            'status': 'ducked',
                            'message': '🔇 Audio ducked - AI is speaking'
                        })
                        time.sleep(0.5)
                        continue
                    
                    # Record small chunk
                    audio_chunk = sd.rec(chunk_frames, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                    sd.wait()
                    
                    audio_array = audio_chunk.flatten()
                    
                    # Volume gating - ignore very quiet audio
                    rms_level = np.sqrt(np.mean(audio_array ** 2))
                    if rms_level < ECHO_PREVENTION_CONFIG['minimum_volume_threshold']:
                        echo_prevention_active = True
                        continue
                    else:
                        echo_prevention_active = False
                    
                    # Check for voice activity
                    vad_result = vad.detect_voice_activity(audio_array)
                    
                    if vad_result.has_voice and vad_result.confidence > 0.8:
                        # Voice detected! Record longer segment
                        socketio.emit('status_update', {
                            'status': 'listening',
                            'message': '🔴 Voice detected - Recording...'
                        })
                        
                        # Record 3 seconds for transcription
                        full_audio = sd.rec(int(3 * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        
                        # Process the audio
                        await process_detected_speech_with_echo_prevention(full_audio.flatten())
                        
                        # Brief pause before resuming monitoring
                        time.sleep(1)
                        
                        if always_listening_active:
                            socketio.emit('status_update', {
                                'status': 'listening',
                                'message': '🔄 Always listening - Echo prevention active!'
                            })
                    
                except Exception as e:
                    if always_listening_active:  # Only log if we're still supposed to be listening
                        print(f"Listening error: {e}")
                        socketio.emit('error_message', {
                            'message': f'⚠️ Listening error: {str(e)}',
                            'timestamp': datetime.now().strftime("%H:%M:%S")
                        })
            
            loop.close()
            
        except Exception as e:
            print(f"Always listening error: {e}")
            socketio.emit('error_message', {
                'message': f'❌ Always listening error: {str(e)}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
        finally:
            always_listening_active = False
            socketio.emit('always_listening_stopped')
    
    # Start continuous listening in background
    listening_thread = threading.Thread(target=continuous_listening)
    listening_thread.daemon = True
    listening_thread.start()

async def process_detected_speech_with_echo_prevention(audio_array):
    """Process speech detected during always listening with echo prevention"""
    global is_speaking, last_response_time, recent_responses
    
    try:
        socketio.emit('status_update', {
            'status': 'processing',
            'message': '📝 Processing detected speech...'
        })
        
        # Transcribe
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        transcription_result = loop.run_until_complete(stt.transcribe_audio(audio_array))
        
        if not transcription_result.text.strip():
            socketio.emit('error_message', {
                'message': '❌ No clear speech in detected audio',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            loop.close()
            return
        
        # Send transcription
        socketio.emit('transcription_result', {
            'text': transcription_result.text,
            'confidence': transcription_result.confidence,
            'processing_time': transcription_result.processing_time,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
        
        # Generate AI response
        prompt = f"You are a helpful assistant. Respond naturally and conversationally to: {transcription_result.text}"
        ai_response = loop.run_until_complete(call_ollama(prompt, max_tokens=100))
        loop.close()
        
        if "Error" not in ai_response:
            # Check for echo/similarity before responding
            if is_similar_response(ai_response):
                socketio.emit('error_message', {
                    'message': '🛡️ Echo detected - Response blocked to prevent loop',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                socketio.emit('echo_prevention_update', {'echo_detected': True})
                return
            
            # Add response to recent responses for echo detection
            recent_responses.append(ai_response)
            if len(recent_responses) > ECHO_PREVENTION_CONFIG['max_similar_responses']:
                recent_responses.pop(0)
            
            socketio.emit('ai_response', {
                'text': ai_response,
                'generation_time': 1.0,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Enable audio ducking during speech
            is_speaking = True
            socketio.emit('status_update', {
                'status': 'speaking',
                'message': '🔊 AI is speaking - Microphone ducked'
            })
            
            # Speak response
            def speak_and_track():
                global is_speaking, last_response_time
                try:
                    os.system(f'say "{ai_response}"')
                finally:
                    # Re-enable listening after speech
                    is_speaking = False
                    last_response_time = time.time()
            
            speak_thread = threading.Thread(target=speak_and_track)
            speak_thread.daemon = True
            speak_thread.start()
        else:
            socketio.emit('error_message', {
                'message': f'❌ AI Error: {ai_response}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
    
    except Exception as e:
        socketio.emit('error_message', {
            'message': f'❌ Processing error: {str(e)}',
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

@socketio.on('stop_always_listening')
def handle_stop_always_listening():
    """Stop continuous listening"""
    global always_listening_active, is_speaking
    always_listening_active = False
    is_speaking = False
    
    socketio.emit('status_update', {
        'status': 'ready',
        'message': '🟢 Always listening stopped - Echo prevention ready'
    })
    
    socketio.emit('always_listening_stopped')

if __name__ == '__main__':
    print("🚀 Starting Echo-Cancelled Voice Interface...")
    print("🛡️ Echo prevention features:")
    print("   • Audio ducking during AI speech")
    print("   • Adaptive silence periods")
    print("   • Volume gating for quiet audio")
    print("   • Echo pattern detection")
    
    # Initialize components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()
    
    if not success:
        print("❌ Failed to initialize components")
        sys.exit(1)
    
    print("🌐 Web interface: http://localhost:8080")
    print("🎤 Ready for echo-cancelled voice interaction!")
    
    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)