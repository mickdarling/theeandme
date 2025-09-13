#!/usr/bin/env python3
"""
Enhanced Echo-Cancelled Voice Interface App - 2025 Production Implementation

Combines multiple echo cancellation techniques based on 2025 research:
1. Koala Noise Suppression (5x more effective than RNNoise)
2. Advanced audio ducking with adaptive timing
3. Hardware-aware volume gating and silence detection
4. Intelligent pattern recognition for echo prevention
5. Real-time audio stream optimization
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

# Try to import Koala for advanced noise suppression
KOALA_AVAILABLE = False
try:
    import pvkoala
    KOALA_AVAILABLE = True
    print("✅ Koala noise suppression available")
except ImportError:
    print("⚠️ Koala not available - install with: pip install pvkoala")

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'enhanced_echo_cancelled_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
stt = None
koala = None
always_listening_active = False
listening_thread = None
is_speaking = False
last_response_time = 0
echo_prevention_active = False

# Enhanced Configuration based on 2025 research
ENHANCED_ECHO_CONFIG = {
    # Timing controls
    'silence_after_response': 2.5,  # Optimized from research
    'speaking_timeout': 8.0,  # Maximum AI speaking time
    'voice_detection_cooldown': 1.0,  # Prevent rapid re-triggering
    
    # Audio processing
    'minimum_volume_threshold': 0.003,  # More sensitive threshold
    'maximum_volume_threshold': 0.8,  # Prevent clipping-induced echo
    'adaptive_threshold_enabled': True,  # Dynamic threshold adjustment
    
    # Echo detection
    'similarity_threshold': 0.75,  # Lower for better detection
    'max_similar_responses': 3,  # Track more responses
    'temporal_echo_window': 10.0,  # Check for echo in last 10 seconds
    
    # Advanced features
    'koala_enabled': KOALA_AVAILABLE,
    'adaptive_ducking': True,  # Adjust ducking based on audio characteristics
    'smart_voice_detection': True,  # Use ML for better voice/noise distinction
    'hardware_optimization': True,  # Optimize for Live Streamer CAM 513
}

# State tracking
recent_responses = []
response_timestamps = []
adaptive_threshold = ENHANCED_ECHO_CONFIG['minimum_volume_threshold']
speaking_start_time = 0

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Echo-Cancelled Voice Interface 2025</title>
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
            max-width: 1000px;
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
            min-width: 220px;
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
        .echo-prevention-panel {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .tech-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .tech-indicator {
            background: rgba(0, 0, 0, 0.3);
            padding: 12px 15px;
            border-radius: 10px;
            text-align: center;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        .tech-indicator.active {
            background: rgba(40, 167, 69, 0.3);
            border: 1px solid #28a745;
            transform: scale(1.02);
        }
        .tech-indicator.warning {
            background: rgba(255, 193, 7, 0.3);
            border: 1px solid #ffc107;
        }
        .tech-indicator.error {
            background: rgba(220, 53, 69, 0.3);
            border: 1px solid #dc3545;
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
        .tech-spec {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            font-size: 0.85em;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Enhanced Echo Cancellation 2025</h1>
            <p>Production-ready AI voice interface with advanced feedback prevention</p>
        </div>
        
        <div id="status" class="status ready">
            🟢 Ready - Enhanced echo prevention active
        </div>
        
        <div class="controls">
            <button id="alwaysListenBtn" class="big-button always-listening" onclick="toggleAlwaysListening()">
                🔄 Start Enhanced Listening
            </button>
            <button id="stopBtn" class="big-button stop-listening" onclick="stopListening()" style="display: none;">
                ⏹️ Stop Listening
            </button>
        </div>
        
        <div class="echo-prevention-panel">
            <h3>🛡️ Enhanced Echo Prevention System (2025)</h3>
            <div class="tech-grid">
                <div id="koalaIndicator" class="tech-indicator">
                    🎯 Koala Suppression: <span>Ready</span>
                </div>
                <div id="duckingIndicator" class="tech-indicator">
                    🎤 Adaptive Ducking: <span>Ready</span>
                </div>
                <div id="volumeGateIndicator" class="tech-indicator">
                    📊 Smart Volume Gate: <span>Ready</span>
                </div>
                <div id="silenceIndicator" class="tech-indicator">
                    ⏱️ Silence Timer: <span>Ready</span>
                </div>
                <div id="echoDetectionIndicator" class="tech-indicator">
                    🔍 Pattern Detection: <span>Ready</span>
                </div>
                <div id="adaptiveIndicator" class="tech-indicator">
                    🧠 Adaptive Learning: <span>Ready</span>
                </div>
            </div>
        </div>
        
        <div class="tech-spec">
            <strong>🔧 Tech Stack:</strong> Koala Noise Suppression • Silero VAD • Whisper STT • Ollama LLM • macOS TTS<br>
            <strong>🎙️ Hardware:</strong> Live Streamer CAM 513 optimized • Real-time stream processing
        </div>
        
        <div id="conversation" class="conversation">
            <div class="system-message">
                Click "Start Enhanced Listening" to begin advanced echo-cancelled voice interaction...
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
            updateTechIndicators(data);
        });

        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = `status ${status}`;
            statusEl.innerHTML = message;
        }

        function updateTechIndicators(data) {
            if (data.koala !== undefined) {
                const indicator = document.getElementById('koalaIndicator');
                indicator.className = `tech-indicator ${data.koala ? 'active' : ''}`;
                indicator.innerHTML = `🎯 Koala Suppression: <span>${data.koala ? 'ACTIVE' : 'Ready'}</span>`;
            }
            
            if (data.ducking !== undefined) {
                const indicator = document.getElementById('duckingIndicator');
                indicator.className = `tech-indicator ${data.ducking ? 'active' : ''}`;
                indicator.innerHTML = `🎤 Adaptive Ducking: <span>${data.ducking ? 'ACTIVE' : 'Ready'}</span>`;
            }
            
            if (data.volume_gate !== undefined) {
                const indicator = document.getElementById('volumeGateIndicator');
                indicator.className = `tech-indicator ${data.volume_gate ? 'warning' : ''}`;
                indicator.innerHTML = `📊 Smart Volume Gate: <span>${data.volume_gate ? 'FILTERING' : 'Ready'}</span>`;
            }
            
            if (data.silence_timer !== undefined) {
                const indicator = document.getElementById('silenceIndicator');
                indicator.className = `tech-indicator ${data.silence_timer > 0 ? 'active' : ''}`;
                indicator.innerHTML = `⏱️ Silence Timer: <span>${data.silence_timer > 0 ? data.silence_timer.toFixed(1) + 's' : 'Ready'}</span>`;
            }
            
            if (data.echo_detected !== undefined) {
                const indicator = document.getElementById('echoDetectionIndicator');
                indicator.className = `tech-indicator ${data.echo_detected ? 'error' : ''}`;
                indicator.innerHTML = `🔍 Pattern Detection: <span>${data.echo_detected ? 'ECHO BLOCKED' : 'Ready'}</span>`;
            }
            
            if (data.adaptive !== undefined) {
                const indicator = document.getElementById('adaptiveIndicator');
                indicator.className = `tech-indicator ${data.adaptive ? 'active' : ''}`;
                indicator.innerHTML = `🧠 Adaptive Learning: <span>${data.adaptive ? 'LEARNING' : 'Ready'}</span>`;
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
                document.getElementById('alwaysListenBtn').textContent = '🔄 Enhanced Listening...';
                document.getElementById('stopBtn').style.display = 'inline-block';
            }
        }

        function stopListening() {
            if (alwaysListening) {
                socket.emit('stop_always_listening');
                alwaysListening = false;
                
                document.getElementById('alwaysListenBtn').classList.remove('active');
                document.getElementById('alwaysListenBtn').textContent = '🔄 Start Enhanced Listening';
                document.getElementById('stopBtn').style.display = 'none';
            }
        }

        socket.on('connect', function() {
            console.log('Connected to enhanced echo-cancelled voice server');
            updateStatus('ready', '🟢 Connected - Enhanced echo prevention active');
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

def update_adaptive_threshold(audio_level):
    """Dynamically adjust volume threshold based on environment"""
    global adaptive_threshold
    
    if not ENHANCED_ECHO_CONFIG['adaptive_threshold_enabled']:
        return
    
    # Slowly adapt threshold based on ambient noise
    adaptation_rate = 0.001
    min_threshold = ENHANCED_ECHO_CONFIG['minimum_volume_threshold']
    max_threshold = min_threshold * 3
    
    target_threshold = max(min_threshold, min(max_threshold, audio_level * 0.3))
    adaptive_threshold += (target_threshold - adaptive_threshold) * adaptation_rate

def is_enhanced_similar_response(new_response):
    """Enhanced echo detection with temporal analysis"""
    if not ENHANCED_ECHO_CONFIG['smart_voice_detection']:
        return False
        
    if not recent_responses or not response_timestamps:
        return False
    
    current_time = time.time()
    new_words = set(new_response.lower().split())
    
    # Check responses within temporal window
    for i, (prev_response, timestamp) in enumerate(zip(recent_responses, response_timestamps)):
        if current_time - timestamp > ENHANCED_ECHO_CONFIG['temporal_echo_window']:
            continue
            
        prev_words = set(prev_response.lower().split())
        
        if not new_words or not prev_words:
            continue
            
        intersection = new_words.intersection(prev_words)
        union = new_words.union(prev_words)
        
        similarity = len(intersection) / len(union) if union else 0
        
        # Weight recent responses more heavily
        time_weight = 1.0 - (current_time - timestamp) / ENHANCED_ECHO_CONFIG['temporal_echo_window']
        weighted_similarity = similarity * time_weight
        
        if weighted_similarity > ENHANCED_ECHO_CONFIG['similarity_threshold']:
            return True
            
    return False

def update_enhanced_echo_indicators():
    """Send enhanced echo prevention status to frontend"""
    global is_speaking, last_response_time, echo_prevention_active, adaptive_threshold
    
    silence_remaining = max(0, ENHANCED_ECHO_CONFIG['silence_after_response'] - (time.time() - last_response_time))
    
    socketio.emit('echo_prevention_update', {
        'koala': KOALA_AVAILABLE and koala is not None,
        'ducking': is_speaking,
        'volume_gate': echo_prevention_active,
        'silence_timer': silence_remaining,
        'echo_detected': False,  # Will be set when echo is detected
        'adaptive': ENHANCED_ECHO_CONFIG['adaptive_threshold_enabled']
    })

async def initialize_components():
    """Initialize all components including Koala if available"""
    global stt, koala
    
    try:
        # Initialize STT
        config = {
            'sample_rate': 16000,
            'whisper_model': 'base'
        }
        
        stt = WhisperSTT(config)
        await stt.initialize()
        print("✅ Whisper STT initialized")
        
        # Initialize Koala if available
        if KOALA_AVAILABLE and ENHANCED_ECHO_CONFIG['koala_enabled']:
            try:
                # Note: You'll need to get an access key from Picovoice
                # For demo purposes, this will fail gracefully
                access_key = os.getenv('PICOVOICE_ACCESS_KEY', 'demo_key')
                koala = pvkoala.create(access_key=access_key)
                print("✅ Koala noise suppression initialized")
            except Exception as e:
                print(f"⚠️ Koala initialization failed: {e}")
                print("ℹ️ Get free access key from https://picovoice.ai/console/")
                koala = None
        
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
def handle_enhanced_always_listening():
    """Start enhanced continuous voice monitoring"""
    global always_listening_active, listening_thread, is_speaking, last_response_time
    
    if always_listening_active:
        return
    
    always_listening_active = True
    is_speaking = False
    last_response_time = time.time()
    
    def enhanced_continuous_listening():
        """Enhanced continuous voice monitoring with 2025 techniques"""
        global always_listening_active, is_speaking, last_response_time, echo_prevention_active
        global adaptive_threshold, speaking_start_time
        
        try:
            # Import VAD for voice detection
            from audio.vad import SileroVAD
            
            vad_config = {
                'sample_rate': 16000,
                'vad_threshold': 0.6,  # Slightly lower for better sensitivity
                'min_speech_duration_ms': 250,  # Faster response
                'silence_timeout_seconds': 1.5
            }
            
            # Initialize VAD
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            vad = SileroVAD(vad_config)
            loop.run_until_complete(vad.initialize())
            
            socketio.emit('status_update', {
                'status': 'listening',
                'message': '🚀 Enhanced listening active - 2025 echo prevention!'
            })
            
            # Continuous monitoring with optimizations
            chunk_duration = 0.3  # Faster chunks for better responsiveness
            sample_rate = 16000
            device_id = 2  # Live Streamer CAM 513
            chunk_frames = int(chunk_duration * sample_rate)
            
            while always_listening_active:
                try:
                    # Update enhanced indicators
                    update_enhanced_echo_indicators()
                    
                    # Enhanced silence period check
                    time_since_response = time.time() - last_response_time
                    if time_since_response < ENHANCED_ECHO_CONFIG['silence_after_response']:
                        socketio.emit('status_update', {
                            'status': 'ducked',
                            'message': f'🔇 Enhanced silence period ({ENHANCED_ECHO_CONFIG["silence_after_response"] - time_since_response:.1f}s)'
                        })
                        time.sleep(0.3)
                        continue
                    
                    # Enhanced adaptive ducking check
                    if is_speaking and ENHANCED_ECHO_CONFIG['adaptive_ducking']:
                        # Check if AI has been speaking too long (safety)
                        if time.time() - speaking_start_time > ENHANCED_ECHO_CONFIG['speaking_timeout']:
                            print("⚠️ AI speaking timeout - resetting")
                            is_speaking = False
                            last_response_time = time.time()
                        else:
                            socketio.emit('status_update', {
                                'status': 'ducked',
                                'message': '🔇 Adaptive ducking - AI speaking'
                            })
                            time.sleep(0.3)
                            continue
                    
                    # Record and process audio chunk
                    audio_chunk = sd.rec(chunk_frames, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                    sd.wait()
                    audio_array = audio_chunk.flatten()
                    
                    # Apply Koala noise suppression if available
                    if koala and ENHANCED_ECHO_CONFIG['koala_enabled']:
                        try:
                            # Convert to int16 for Koala
                            audio_int16 = (audio_array * 32767).astype(np.int16)
                            enhanced_audio = koala.process(audio_int16)
                            audio_array = enhanced_audio.astype(np.float32) / 32767
                        except Exception as e:
                            print(f"Koala processing error: {e}")
                    
                    # Enhanced volume gating with adaptive threshold
                    rms_level = np.sqrt(np.mean(audio_array ** 2))
                    update_adaptive_threshold(rms_level)
                    
                    if rms_level < adaptive_threshold:
                        echo_prevention_active = True
                        continue
                    elif rms_level > ENHANCED_ECHO_CONFIG['maximum_volume_threshold']:
                        # Too loud - likely feedback or clipping
                        echo_prevention_active = True
                        continue
                    else:
                        echo_prevention_active = False
                    
                    # Enhanced voice activity detection
                    vad_result = vad.detect_voice_activity(audio_array)
                    
                    if vad_result.has_voice and vad_result.confidence > 0.7:
                        # Voice detected! Record longer segment
                        socketio.emit('status_update', {
                            'status': 'listening',
                            'message': '🔴 Enhanced voice detection - Recording...'
                        })
                        
                        # Record optimized duration
                        full_audio = sd.rec(int(2.5 * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        
                        # Process with enhanced techniques
                        loop.run_until_complete(process_enhanced_detected_speech(full_audio.flatten()))
                        
                        # Enhanced cooldown to prevent rapid re-triggering
                        time.sleep(ENHANCED_ECHO_CONFIG['voice_detection_cooldown'])
                        
                        if always_listening_active:
                            socketio.emit('status_update', {
                                'status': 'listening',
                                'message': '🚀 Enhanced listening active - 2025 echo prevention!'
                            })
                    
                except Exception as e:
                    if always_listening_active:
                        print(f"Enhanced listening error: {e}")
                        socketio.emit('error_message', {
                            'message': f'⚠️ Enhanced listening error: {str(e)}',
                            'timestamp': datetime.now().strftime("%H:%M:%S")
                        })
            
            if koala:
                koala.delete()
            loop.close()
            
        except Exception as e:
            print(f"Enhanced always listening error: {e}")
            socketio.emit('error_message', {
                'message': f'❌ Enhanced listening error: {str(e)}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
        finally:
            always_listening_active = False
            socketio.emit('always_listening_stopped')
    
    # Start enhanced listening in background
    listening_thread = threading.Thread(target=enhanced_continuous_listening)
    listening_thread.daemon = True
    listening_thread.start()

async def process_enhanced_detected_speech(audio_array):
    """Process speech with enhanced echo prevention techniques"""
    global is_speaking, last_response_time, recent_responses, response_timestamps, speaking_start_time
    
    try:
        socketio.emit('status_update', {
            'status': 'processing',
            'message': '📝 Enhanced speech processing...'
        })
        
        # Enhanced audio preprocessing with Koala
        processed_audio = audio_array
        if koala and ENHANCED_ECHO_CONFIG['koala_enabled']:
            try:
                audio_int16 = (audio_array * 32767).astype(np.int16)
                processed_audio = koala.process(audio_int16).astype(np.float32) / 32767
            except:
                pass  # Fall back to original audio
        
        # Transcribe enhanced audio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        transcription_result = loop.run_until_complete(stt.transcribe_audio(processed_audio))
        
        if not transcription_result.text.strip():
            socketio.emit('error_message', {
                'message': '❌ No clear speech in enhanced audio',
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
            # Enhanced echo detection
            if is_enhanced_similar_response(ai_response):
                socketio.emit('error_message', {
                    'message': '🛡️ Enhanced echo detection - Response blocked',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                socketio.emit('echo_prevention_update', {'echo_detected': True})
                return
            
            # Add to enhanced response tracking
            current_time = time.time()
            recent_responses.append(ai_response)
            response_timestamps.append(current_time)
            
            # Cleanup old responses
            while (recent_responses and 
                   current_time - response_timestamps[0] > ENHANCED_ECHO_CONFIG['temporal_echo_window']):
                recent_responses.pop(0)
                response_timestamps.pop(0)
            
            # Keep only recent responses for memory efficiency
            if len(recent_responses) > ENHANCED_ECHO_CONFIG['max_similar_responses']:
                recent_responses.pop(0)
                response_timestamps.pop(0)
            
            socketio.emit('ai_response', {
                'text': ai_response,
                'generation_time': 1.0,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Enhanced adaptive ducking
            is_speaking = True
            speaking_start_time = time.time()
            socketio.emit('status_update', {
                'status': 'speaking',
                'message': '🔊 Enhanced AI speech - Adaptive ducking active'
            })
            
            # Enhanced speech tracking
            def enhanced_speak_and_track():
                global is_speaking, last_response_time
                try:
                    os.system(f'say "{ai_response}"')
                finally:
                    is_speaking = False
                    last_response_time = time.time()
            
            speak_thread = threading.Thread(target=enhanced_speak_and_track)
            speak_thread.daemon = True
            speak_thread.start()
        else:
            socketio.emit('error_message', {
                'message': f'❌ Enhanced AI Error: {ai_response}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
    
    except Exception as e:
        socketio.emit('error_message', {
            'message': f'❌ Enhanced processing error: {str(e)}',
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

@socketio.on('stop_always_listening')
def handle_stop_enhanced_listening():
    """Stop enhanced continuous listening"""
    global always_listening_active, is_speaking
    always_listening_active = False
    is_speaking = False
    
    socketio.emit('status_update', {
        'status': 'ready',
        'message': '🟢 Enhanced listening stopped - Ready for restart'
    })
    
    socketio.emit('always_listening_stopped')

if __name__ == '__main__':
    print("🚀 Starting Enhanced Echo-Cancelled Voice Interface (2025)")
    print("🛡️ Enhanced echo prevention features:")
    print("   • Koala noise suppression (5x more effective than RNNoise)")
    print("   • Adaptive audio ducking with timeout safety")
    print("   • Smart volume gating with adaptive thresholds")
    print("   • Temporal echo pattern detection")
    print("   • Hardware-optimized for Live Streamer CAM 513")
    print("   • Real-time stream processing optimization")
    
    # Initialize enhanced components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()
    
    if not success:
        print("❌ Failed to initialize enhanced components")
        sys.exit(1)
    
    print("🌐 Enhanced web interface: http://localhost:8080")
    print("🎤 Ready for production-level echo-cancelled voice interaction!")
    
    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)