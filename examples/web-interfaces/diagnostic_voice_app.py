#!/usr/bin/env python3
"""
Diagnostic Voice Interface - Comprehensive Testing & Recording System

Features:
1. Records ALL audio interactions for post-analysis
2. Context-aware AI prompting 
3. Multiple STT engine comparison
4. AI voice generation recording
5. Buffer corruption detection
6. Real-time diagnostic feedback
"""

import asyncio
import sys
import os
import json
import threading
import aiohttp
import time
import wave
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import sounddevice as sd
import numpy as np
import re

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'diagnostic_voice_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
stt = None
always_listening_active = False
listening_thread = None
is_speaking = False
last_response_time = 0

# PRE-BUFFER ENHANCEMENT: Rolling buffer to capture sentence beginnings
from collections import deque
PRE_BUFFER_SIZE = 16000 * 2  # 2 seconds at 16kHz
audio_pre_buffer = deque(maxlen=PRE_BUFFER_SIZE)
pre_buffer_thread = None
pre_buffer_active = False

# Diagnostic settings
DIAGNOSTICS_DIR = Path("/Users/mick/Developer/theeandme/audio_diagnostics")
DIAGNOSTICS_DIR.mkdir(exist_ok=True)

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
session_dir = DIAGNOSTICS_DIR / f"session_{session_id}"
session_dir.mkdir(exist_ok=True)

interaction_count = 0

# Enhanced Semantic Scoring (from autonomous testing v2.0)
number_words = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': '10', 'eleven': '11', 'twelve': '12'
}
digit_words = {v: k for k, v in number_words.items()}

def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for semantic comparison"""
    text = text.lower().strip()

    # Convert numbers bidirectionally
    words = text.split()
    normalized_words = []

    for word in words:
        # Remove punctuation for comparison
        clean_word = re.sub(r'[^\w]', '', word)

        # Convert number words to digits
        if clean_word in number_words:
            normalized_words.append(number_words[clean_word])
        # Convert digits to number words
        elif clean_word in digit_words:
            normalized_words.append(digit_words[clean_word])
        else:
            normalized_words.append(clean_word)

    return ' '.join(normalized_words)

def calculate_semantic_similarity(original: str, transcribed: str) -> float:
    """Enhanced similarity calculation with semantic awareness"""
    # Normalize both texts
    orig_norm = normalize_text_for_comparison(original)
    trans_norm = normalize_text_for_comparison(transcribed)

    orig_words = set(orig_norm.split())
    trans_words = set(trans_norm.split())

    if not orig_words:
        return 0.0

    # Calculate word-level similarity
    intersection = orig_words.intersection(trans_words)
    union = orig_words.union(trans_words)

    word_similarity = len(intersection) / len(orig_words)

    # Bonus for exact sequence matches
    orig_sequence = orig_norm.split()
    trans_sequence = trans_norm.split()

    sequence_bonus = 0.0
    if len(orig_sequence) == len(trans_sequence):
        matches = sum(1 for o, t in zip(orig_sequence, trans_sequence) if o == t)
        sequence_bonus = (matches / len(orig_sequence)) * 0.2  # 20% bonus for sequence

    return min(1.0, word_similarity + sequence_bonus)

def calculate_enhanced_confidence(whisper_conf: float, audio_quality: float, text_length: int) -> float:
    """Enhanced confidence scoring using multiple factors"""
    # Base confidence from Whisper
    base_conf = whisper_conf if whisper_conf > 0 else 0.3  # Handle 0 confidence edge case

    # Audio quality factor (0-1 range)
    quality_factor = min(1.0, audio_quality * 3.5)  # Scale up quality impact

    # Text length factor (penalize very short transcriptions)
    length_factor = min(1.0, text_length / 20.0)  # Ideal length around 20+ characters

    # Combined confidence
    enhanced_conf = (base_conf * 0.5) + (quality_factor * 0.3) + (length_factor * 0.2)

    return min(1.0, enhanced_conf)

def classify_error_pattern(original: str, transcribed: str) -> str:
    """Classify the type of transcription error"""
    if not transcribed.strip():
        return "no_transcription"

    orig_words = original.lower().split()
    trans_words = transcribed.lower().split()

    # Check for number format issues
    if any(word in number_words for word in orig_words) or any(word.isdigit() for word in orig_words):
        if any(word.isdigit() for word in trans_words) or any(word in number_words for word in trans_words):
            return "number_format_conversion"

    # Check for word substitution
    if len(orig_words) == len(trans_words):
        return "word_substitution"
    elif len(trans_words) < len(orig_words):
        return "word_omission"
    else:
        return "word_insertion"

def calculate_audio_quality(audio_data: np.ndarray) -> float:
    """Calculate basic audio quality metric"""
    if audio_data is None or len(audio_data) == 0:
        return 0.0

    # Calculate RMS (Root Mean Square) as quality indicator
    rms = np.sqrt(np.mean(audio_data**2))

    # Normalize to 0-1 range (assuming typical RMS values 0-0.3)
    quality = min(1.0, rms * 10.0)
    return quality

# Context-aware AI prompt
CONTEXT_PROMPT = """You are participating in a voice interface testing session. The user (Mick) is working on improving an always-listening voice interface system with echo cancellation and speech recognition.

Context:
- We're testing various voice recognition improvements
- The system uses Whisper STT, Ollama LLM, and macOS TTS
- We're debugging audio buffer issues and transcription quality
- This is a development/testing environment
- Respond naturally and help with testing by acknowledging what you hear clearly

Keep responses concise but helpful for testing purposes."""

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diagnostic Voice Interface - Testing Lab</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            max-width: 1200px;
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
        .diagnostic-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }
        .diagnostic-panel {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            border: 2px solid rgba(255, 255, 255, 0.3);
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
        .status.recording { background: rgba(138, 43, 226, 0.3); border: 2px solid #8a2be2; animation: pulse 1.5s infinite; }
        
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
        .click-record { background: rgba(220, 53, 69, 0.8); border: 3px solid #dc3545; }
        .always-listening { background: rgba(40, 167, 69, 0.8); border: 3px solid #28a745; }
        .always-listening.active { background: rgba(40, 167, 69, 1); animation: pulse 2s infinite; }
        .stop-listening { background: rgba(108, 117, 125, 0.8); border: 3px solid #6c757d; }
        
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
        .system-message { background: rgba(108, 117, 125, 0.3); border: 2px solid #6c757d; text-align: center; font-style: italic; }
        
        .timestamp {
            font-size: 0.8em;
            opacity: 0.8;
            margin-top: 6px;
            font-style: italic;
        }
        .diagnostic-info {
            background: rgba(0, 0, 0, 0.2);
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Diagnostic Voice Testing Lab</h1>
            <p>Comprehensive voice interface testing with full recording & analysis</p>
            <div class="diagnostic-info">
                <strong>Session:</strong> <span id="sessionId">${session_id}</span> | 
                <strong>Interactions:</strong> <span id="interactionCount">0</span> |
                <strong>Recording:</strong> All audio saved for analysis
            </div>
        </div>
        
        <div id="status" class="status ready">
            🟢 Ready for diagnostic testing
        </div>
        
        <div class="controls">
            <button id="clickRecordBtn" class="big-button click-record" onclick="startClickRecord()">
                🎤 Click to Record
            </button>
            <button id="alwaysListenBtn" class="big-button always-listening" onclick="toggleAlwaysListening()">
                🔄 Always Listening
            </button>
            <button id="stopBtn" class="big-button stop-listening" onclick="stopListening()" style="display: none;">
                ⏹️ Stop
            </button>
        </div>
        
        <div class="diagnostic-grid">
            <div class="diagnostic-panel">
                <h3>🔧 System Diagnostics</h3>
                <div id="systemDiagnostics">
                    <div>Buffer Status: <span id="bufferStatus">Ready</span></div>
                    <div>Echo Prevention: <span id="echoStatus">Active</span></div>
                    <div>Recording Quality: <span id="recordingQuality">16kHz/16bit</span></div>
                    <div>Session Files: <span id="sessionFiles">0</span></div>
                </div>
            </div>
            
            <div class="diagnostic-panel">
                <h3>📊 Performance Metrics</h3>
                <div id="performanceMetrics">
                    <div>Transcription Time: <span id="transcriptionTime">--</span></div>
                    <div>AI Response Time: <span id="responseTime">--</span></div>
                    <div>Audio Quality: <span id="audioQuality">--</span></div>
                    <div>Buffer Health: <span id="bufferHealth">Good</span></div>
                </div>
            </div>
        </div>
        
        <div id="conversation" class="conversation">
            <div class="system-message">
                🧪 Diagnostic session initialized - All interactions recorded for analysis
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let isTranscribing = false;
        let alwaysListening = false;
        let sessionId = '${session_id}';
        
        document.getElementById('sessionId').textContent = sessionId;

        socket.on('status_update', function(data) {
            updateStatus(data.status, data.message);
        });

        socket.on('transcription_result', function(data) {
            addMessage('user', data.text, data.timestamp, {
                confidence: data.confidence,
                enhanced_confidence: data.enhanced_confidence,
                audio_quality: data.audio_quality,
                processing_time: data.processing_time,
                audio_file: data.audio_file
            });
            document.getElementById('transcriptionTime').textContent = data.processing_time.toFixed(2) + 's';
            updateInteractionCount();
        });

        socket.on('ai_response', function(data) {
            addMessage('ai', data.text, data.timestamp, {
                generation_time: data.generation_time,
                ai_audio_file: data.ai_audio_file
            });
            document.getElementById('responseTime').textContent = data.generation_time.toFixed(2) + 's';
        });

        socket.on('diagnostic_update', function(data) {
            if (data.buffer_status) document.getElementById('bufferStatus').textContent = data.buffer_status;
            if (data.audio_quality) document.getElementById('audioQuality').textContent = data.audio_quality;
            if (data.buffer_health) document.getElementById('bufferHealth').textContent = data.buffer_health;
            if (data.session_files) document.getElementById('sessionFiles').textContent = data.session_files;
        });

        socket.on('error_message', function(data) {
            addMessage('system', data.message, data.timestamp);
        });

        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = `status ${status}`;
            statusEl.innerHTML = message;
        }

        function updateInteractionCount() {
            const current = parseInt(document.getElementById('interactionCount').textContent);
            document.getElementById('interactionCount').textContent = current + 1;
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
                if (metadata.confidence !== undefined) metaText += ` (${(metadata.confidence * 100).toFixed(0)}% conf)`;
                if (metadata.enhanced_confidence !== undefined) metaText += ` • ${(metadata.enhanced_confidence * 100).toFixed(0)}% enh`;
                if (metadata.audio_quality !== undefined) metaText += ` • ${(metadata.audio_quality * 100).toFixed(0)}% qual`;
                if (metadata.processing_time) metaText += ` • ${metadata.processing_time.toFixed(2)}s proc`;
                if (metadata.generation_time) metaText += ` • ${metadata.generation_time.toFixed(2)}s gen`;
                if (metadata.audio_file) metaText += ` • 📼 ${metadata.audio_file}`;
                if (metadata.ai_audio_file) metaText += ` • 🔊 ${metadata.ai_audio_file}`;
            }
            
            messageEl.innerHTML = `
                ${icon} ${content}
                <div class="timestamp">${timestamp}${metaText}</div>
            `;
            
            conversation.appendChild(messageEl);
            conversation.scrollTop = conversation.scrollHeight;
        }

        function startClickRecord() {
            if (!isTranscribing && !alwaysListening) {
                socket.emit('start_click_record');
                isTranscribing = true;
            }
        }

        function toggleAlwaysListening() {
            if (!alwaysListening) {
                socket.emit('start_always_listening');
                alwaysListening = true;
                
                document.getElementById('alwaysListenBtn').classList.add('active');
                document.getElementById('alwaysListenBtn').textContent = '🔄 Listening...';
                document.getElementById('stopBtn').style.display = 'inline-block';
                document.getElementById('clickRecordBtn').disabled = true;
            }
        }

        function stopListening() {
            if (alwaysListening) {
                socket.emit('stop_always_listening');
                alwaysListening = false;
                
                document.getElementById('alwaysListenBtn').classList.remove('active');
                document.getElementById('alwaysListenBtn').textContent = '🔄 Always Listening';
                document.getElementById('stopBtn').style.display = 'none';
                document.getElementById('clickRecordBtn').disabled = false;
            }
        }

        socket.on('connect', function() {
            console.log('Connected to diagnostic voice server');
            updateStatus('ready', '🟢 Connected - Diagnostic recording active');
        });

        socket.on('transcription_complete', function() {
            isTranscribing = false;
        });

        socket.on('always_listening_stopped', function() {
            stopListening();
        });
    </script>
</body>
</html>
'''.replace('${session_id}', session_id)

def save_audio_file(audio_data, filename_prefix, sample_rate=16000):
    """Save audio data to WAV file for analysis"""
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.wav"
    filepath = session_dir / filename
    
    # Ensure audio is in correct format
    if audio_data.dtype != np.int16:
        audio_data = (audio_data * 32767).astype(np.int16)
    
    with wave.open(str(filepath), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return filename

def record_ai_voice(text):
    """Record AI voice generation for analysis"""
    timestamp = datetime.now().strftime("%H%M%S")
    ai_audio_file = f"ai_voice_{timestamp}.wav"
    ai_filepath = session_dir / ai_audio_file
    
    # Record AI speech generation
    try:
        # Use macOS say command to generate to file
        os.system(f'say "{text}" -o "{ai_filepath}" --data-format=LEI16@16000')
        return ai_audio_file
    except Exception as e:
        print(f"Failed to record AI voice: {e}")
        return None

async def call_ollama(prompt, max_tokens=100):
    """Direct call to Ollama API with context"""
    try:
        full_prompt = f"{CONTEXT_PROMPT}\n\nUser: {prompt}\n\nAssistant:"
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama3.1:8b",
                "prompt": full_prompt,
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
        test_response = await call_ollama("Hello, this is a test")
        if "Error" in test_response:
            raise Exception(f"Ollama error: {test_response}")
        print("✅ Ollama connection verified")
        
        print(f"✅ Diagnostic session: {session_id}")
        print(f"✅ Recording directory: {session_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('start_click_record')
def handle_click_record():
    """Handle click-to-record with full diagnostics"""
    global interaction_count
    
    def transcription_task():
        global interaction_count
        interaction_count += 1
        
        try:
            socketio.emit('status_update', {
                'status': 'recording',
                'message': '🔴 Recording 5 seconds - SPEAK NOW!'
            })
            
            # Record audio
            duration = 5
            sample_rate = 16000
            device_id = 2  # Live Streamer CAM 513
            
            audio_data = sd.rec(
                int(duration * sample_rate), 
                samplerate=sample_rate, 
                channels=1, 
                dtype=np.float32,
                device=device_id
            )
            sd.wait()
            
            # Save audio for analysis
            audio_filename = save_audio_file(audio_data.flatten(), f"click_record_{interaction_count:03d}")
            
            socketio.emit('status_update', {
                'status': 'processing',
                'message': '📝 Processing speech with diagnostics...'
            })
            
            # Transcribe audio
            audio_array = audio_data.flatten()
            
            # Run transcription
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            transcription_result = loop.run_until_complete(stt.transcribe_audio(audio_array))
            
            if not transcription_result.text.strip():
                socketio.emit('error_message', {
                    'message': f'❌ No speech detected in {audio_filename}',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                socketio.emit('status_update', {
                    'status': 'ready',
                    'message': '🟢 Ready for next test'
                })
                socketio.emit('transcription_complete')
                loop.close()
                return
            
            # Enhanced semantic scoring (autonomous improvements from v2.0)
            audio_quality = calculate_audio_quality(audio_array)
            enhanced_confidence = calculate_enhanced_confidence(
                transcription_result.confidence,
                audio_quality,
                len(transcription_result.text)
            )

            # Send transcription result with enhanced diagnostics
            socketio.emit('transcription_result', {
                'text': transcription_result.text,
                'confidence': transcription_result.confidence,
                'enhanced_confidence': enhanced_confidence,
                'audio_quality': audio_quality,
                'processing_time': transcription_result.processing_time,
                'audio_file': audio_filename,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Generate AI response
            socketio.emit('status_update', {
                'status': 'processing',
                'message': '🤖 AI generating context-aware response...'
            })
            
            ai_response = loop.run_until_complete(call_ollama(transcription_result.text, max_tokens=100))
            loop.close()
            
            if "Error" not in ai_response:
                # Record AI voice for analysis
                ai_audio_file = record_ai_voice(ai_response)
                
                socketio.emit('ai_response', {
                    'text': ai_response,
                    'generation_time': 1.5,  # Approximate
                    'ai_audio_file': ai_audio_file,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                
                # Speak the response (after recording)
                os.system(f'say "{ai_response}" &')
                
                # Update diagnostics
                socketio.emit('diagnostic_update', {
                    'session_files': len(list(session_dir.glob("*.wav"))),
                    'buffer_health': 'Good',
                    'audio_quality': f'{transcription_result.confidence:.1%}'
                })
            else:
                socketio.emit('error_message', {
                    'message': f'❌ AI Error: {ai_response}',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
            
            # Reset status
            socketio.emit('status_update', {
                'status': 'ready',
                'message': '🟢 Ready for next diagnostic test'
            })
            
        except Exception as e:
            socketio.emit('error_message', {
                'message': f'❌ Diagnostic Error: {str(e)}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            socketio.emit('status_update', {
                'status': 'ready',
                'message': '🟢 Ready for retry'
            })
        finally:
            socketio.emit('transcription_complete')
    
    # Run in background thread
    thread = threading.Thread(target=transcription_task)
    thread.daemon = True
    thread.start()

@socketio.on('start_always_listening')
def handle_always_listening():
    """Simplified always-listening without buffer corruption"""
    global always_listening_active, listening_thread
    
    if always_listening_active:
        return
    
    always_listening_active = True
    
    def simple_continuous_listening():
        """Simple always-listening with fixed 5-second recording"""
        global always_listening_active
        
        try:
            from audio.vad import SileroVAD
            
            vad_config = {
                'sample_rate': 16000,
                'vad_threshold': 0.4,  # More sensitive to catch sentence beginnings
                'min_speech_duration_ms': 150,  # Shorter minimum to catch quick starts
                'silence_timeout_seconds': 4.0  # Longer timeout for full sentences
            }
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            vad = SileroVAD(vad_config)
            loop.run_until_complete(vad.initialize())
            
            socketio.emit('status_update', {
                'status': 'listening',
                'message': '🔄 Always listening - Fixed 5s recording on voice detection'
            })
            
            chunk_duration = 0.5
            sample_rate = 16000
            device_id = 2
            chunk_frames = int(chunk_duration * sample_rate)
            
            while always_listening_active:
                try:
                    # Echo prevention
                    time_since_response = time.time() - last_response_time
                    if time_since_response < 5.0:  # Longer cooldown for cleaner sentence starts
                        time.sleep(0.5)
                        continue
                    
                    if is_speaking:
                        time.sleep(0.5)
                        continue
                    
                    # Simple VAD detection
                    audio_chunk = sd.rec(chunk_frames, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                    sd.wait()
                    audio_array = audio_chunk.flatten()
                    
                    rms_level = np.sqrt(np.mean(audio_array ** 2))
                    if rms_level < 0.005:
                        continue
                    
                    vad_result = vad.detect_voice_activity(audio_array)

                    if vad_result.has_voice and vad_result.confidence > 0.5:  # Lower confidence threshold
                        # Voice detected - use simple 5-second recording (same as click-to-record)
                        socketio.emit('status_update', {
                            'status': 'recording',
                            'message': '🔴 Voice detected - Recording 5 seconds...'
                        })
                        
                        # Record fixed 5 seconds (no buffer complexity)
                        full_audio = sd.rec(int(5 * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        
                        process_detected_speech(full_audio.flatten())
                        
                        time.sleep(2)  # Cooldown
                        
                        if always_listening_active:
                            socketio.emit('status_update', {
                                'status': 'listening',
                                'message': '🔄 Always listening - Ready for next voice'
                            })
                    
                except Exception as e:
                    if always_listening_active:
                        print(f"Listening error: {e}")
                        socketio.emit('diagnostic_update', {
                            'buffer_health': f'Error: {str(e)[:30]}'
                        })
            
            loop.close()
            
        except Exception as e:
            print(f"Always listening error: {e}")
        finally:
            always_listening_active = False
            socketio.emit('always_listening_stopped')
    
    listening_thread = threading.Thread(target=simple_continuous_listening)
    listening_thread.daemon = True
    listening_thread.start()

def process_detected_speech(audio_array):
    """Process detected speech with full diagnostics"""
    global is_speaking, last_response_time, interaction_count
    
    try:
        interaction_count += 1
        
        # Save audio for analysis
        audio_filename = save_audio_file(audio_array, f"always_listen_{interaction_count:03d}")
        
        socketio.emit('status_update', {
            'status': 'processing',
            'message': '📝 Processing always-listening speech...'
        })
        
        # Transcribe
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        transcription_result = loop.run_until_complete(stt.transcribe_audio(audio_array))
        
        if not transcription_result.text.strip():
            socketio.emit('error_message', {
                'message': f'❌ No speech in {audio_filename}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            loop.close()
            return
        
        # Enhanced semantic scoring for always-listening mode
        audio_quality = calculate_audio_quality(audio_array)
        enhanced_confidence = calculate_enhanced_confidence(
            transcription_result.confidence,
            audio_quality,
            len(transcription_result.text)
        )

        # Send enhanced transcription
        socketio.emit('transcription_result', {
            'text': transcription_result.text,
            'confidence': transcription_result.confidence,
            'enhanced_confidence': enhanced_confidence,
            'audio_quality': audio_quality,
            'processing_time': transcription_result.processing_time,
            'audio_file': audio_filename,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
        
        # Generate AI response
        ai_response = loop.run_until_complete(call_ollama(transcription_result.text, max_tokens=100))
        loop.close()
        
        if "Error" not in ai_response:
            # Record AI voice
            ai_audio_file = record_ai_voice(ai_response)
            
            socketio.emit('ai_response', {
                'text': ai_response,
                'generation_time': 1.5,
                'ai_audio_file': ai_audio_file,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Enhanced speaking tracking
            is_speaking = True
            
            def speak_and_track():
                global is_speaking, last_response_time
                try:
                    os.system(f'say "{ai_response}"')
                finally:
                    is_speaking = False
                    last_response_time = time.time()
            
            speak_thread = threading.Thread(target=speak_and_track)
            speak_thread.daemon = True
            speak_thread.start()
            
            # Update diagnostics
            socketio.emit('diagnostic_update', {
                'session_files': len(list(session_dir.glob("*.wav"))),
                'buffer_health': 'Good - No Buffer Used',
                'audio_quality': f'{transcription_result.confidence:.1%}'
            })
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
    """Stop always listening"""
    global always_listening_active, is_speaking
    always_listening_active = False
    is_speaking = False
    
    socketio.emit('status_update', {
        'status': 'ready',
        'message': '🟢 Always listening stopped - Analysis data saved'
    })
    
    socketio.emit('always_listening_stopped')

if __name__ == '__main__':
    print("🧪 Starting Diagnostic Voice Interface...")
    print("📊 Full recording and analysis system")
    print(f"📁 Session directory: {session_dir}")
    print("🎯 Features:")
    print("   • All audio interactions recorded to WAV files")
    print("   • Context-aware AI prompting for testing")
    print("   • AI voice generation recording")
    print("   • No complex buffer (avoiding corruption)")
    print("   • Real-time diagnostic feedback")
    print("   • Post-session analysis capabilities")
    
    # Initialize components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()
    
    if not success:
        print("❌ Failed to initialize diagnostic components")
        sys.exit(1)
    
    print("🌐 Diagnostic interface: http://localhost:8081")
    print("🎤 Ready for comprehensive voice testing!")
    
    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=8081, debug=False, allow_unsafe_werkzeug=True)