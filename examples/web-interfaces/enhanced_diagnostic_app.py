#!/usr/bin/env python3
"""
Enhanced Diagnostic Voice Interface
Building on the "top tier" click-to-record with pre-buffer enhancement

Key Enhancement:
- Pre-buffer capture to fix missing sentence beginnings
- Keep everything else that was working perfectly
"""

import asyncio
import sys
import os
import json
import threading
import time
import wave
import subprocess
from pathlib import Path
from datetime import datetime
from collections import deque
import sounddevice as sd
import numpy as np
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import re

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'enhanced_diagnostic_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
stt = None
always_listening_active = False
listening_thread = None
is_speaking = False
last_response_time = 0

# PRE-BUFFER ENHANCEMENT: Rolling buffer to capture sentence beginnings
PRE_BUFFER_SIZE = 16000 * 2  # 2 seconds at 16kHz
audio_pre_buffer = deque(maxlen=PRE_BUFFER_SIZE)
pre_buffer_thread = None
pre_buffer_active = False

# Diagnostic settings
DIAGNOSTICS_DIR = Path("/Users/mick/Developer/theeandme/audio_diagnostics")
DIAGNOSTICS_DIR.mkdir(exist_ok=True)

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
session_dir = DIAGNOSTICS_DIR / f"enhanced_session_{session_id}"
session_dir.mkdir(exist_ok=True)

interaction_count = 0

# Enhanced Semantic Scoring (from autonomous v2.0)
number_words = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    'ten': '10', 'eleven': '11', 'twelve': '12'
}
digit_words = {v: k for k, v in number_words.items()}

def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for semantic comparison"""
    text = text.lower().strip()
    words = text.split()
    normalized_words = []

    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word in number_words:
            normalized_words.append(number_words[clean_word])
        elif clean_word in digit_words:
            normalized_words.append(digit_words[clean_word])
        else:
            normalized_words.append(clean_word)

    return ' '.join(normalized_words)

def calculate_semantic_similarity(original: str, transcribed: str) -> float:
    """Enhanced similarity calculation with semantic awareness"""
    orig_norm = normalize_text_for_comparison(original)
    trans_norm = normalize_text_for_comparison(transcribed)

    orig_words = set(orig_norm.split())
    trans_words = set(trans_norm.split())

    if not orig_words:
        return 0.0

    intersection = orig_words.intersection(trans_words)
    word_similarity = len(intersection) / len(orig_words)

    orig_sequence = orig_norm.split()
    trans_sequence = trans_norm.split()

    sequence_bonus = 0.0
    if len(orig_sequence) == len(trans_sequence):
        matches = sum(1 for o, t in zip(orig_sequence, trans_sequence) if o == t)
        sequence_bonus = (matches / len(orig_sequence)) * 0.2

    return min(1.0, word_similarity + sequence_bonus)

def calculate_enhanced_confidence(whisper_conf: float, audio_quality: float, text_length: int) -> float:
    """Enhanced confidence scoring using multiple factors"""
    base_conf = whisper_conf if whisper_conf > 0 else 0.3
    quality_factor = min(1.0, audio_quality * 3.5)
    length_factor = min(1.0, text_length / 20.0)
    enhanced_conf = (base_conf * 0.5) + (quality_factor * 0.3) + (length_factor * 0.2)
    return min(1.0, enhanced_conf)

def calculate_audio_quality(audio_data: np.ndarray) -> float:
    """Calculate basic audio quality metric"""
    if audio_data is None or len(audio_data) == 0:
        return 0.0
    rms = np.sqrt(np.mean(audio_data**2))
    quality = min(1.0, rms * 10.0)
    return quality

def classify_error_pattern(original: str, transcribed: str) -> str:
    """Classify the type of transcription error"""
    if not transcribed.strip():
        return "no_transcription"

    orig_words = original.lower().split()
    trans_words = transcribed.lower().split()

    if any(word in number_words for word in orig_words) or any(word.isdigit() for word in orig_words):
        if any(word.isdigit() for word in trans_words) or any(word in number_words for word in trans_words):
            return "number_format_conversion"

    if len(orig_words) == len(trans_words):
        return "word_substitution"
    elif len(trans_words) < len(orig_words):
        return "word_omission"
    else:
        return "word_insertion"

def continuous_pre_buffer():
    """Continuously capture audio to pre-buffer for sentence beginning capture"""
    global pre_buffer_active, audio_pre_buffer

    sample_rate = 16000
    device_id = 2  # Live Streamer CAM 513
    chunk_size = 1024

    socketio.emit('system_status', {'message': 'Pre-buffer recording started (captures sentence beginnings)'})

    try:
        while pre_buffer_active:
            # Record small chunks continuously
            audio_chunk = sd.rec(chunk_size, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
            sd.wait()
            audio_array = audio_chunk.flatten()

            # Add to rolling pre-buffer
            audio_pre_buffer.extend(audio_array)

            time.sleep(0.01)  # Small delay

    except Exception as e:
        print(f"Pre-buffer error: {e}")
        socketio.emit('system_status', {'message': f'Pre-buffer error: {e}'})

# Context-aware AI prompt
CONTEXT_PROMPT = """You are participating in a voice interface testing session. The user (Mick) is working on improving an always-listening voice interface system with enhanced capture of sentence beginnings.

Context:
- We're testing pre-buffer enhancements to catch missing sentence starts
- The system uses Whisper STT, Ollama LLM, and high-quality Samantha TTS
- We're focused on natural conversation flow
- This is a development/testing environment
- Respond naturally and help with testing by acknowledging what you hear clearly

Keep responses concise but helpful for testing purposes."""

# HTML Template (simplified, focusing on what works)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Diagnostic Voice Interface</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .panel {
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { margin: 0 0 20px 0; font-size: 2.5em; font-weight: 300; }
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .record-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 20px 40px;
            border-radius: 15px;
            font-size: 1.4em;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
            margin: 10px 0;
        }
        .record-btn:hover { background: #45a049; transform: translateY(-2px); }
        .listening-btn { background: #ff9800; }
        .listening-btn:hover { background: #e68900; }
        .messages {
            height: 400px;
            overflow-y: auto;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 10px;
            background: rgba(0,0,0,0.1);
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 8px;
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .user-message { background: rgba(76, 175, 80, 0.3); }
        .ai-message { background: rgba(33, 150, 243, 0.3); }
        .system-message { background: rgba(255, 193, 7, 0.3); }
        .metrics { font-size: 0.9em; color: rgba(255,255,255,0.8); margin-top: 5px; }
        .pre-buffer-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
    </style>
</head>
<body>
    <div class="pre-buffer-indicator">🔄 Pre-Buffer Active</div>

    <div class="container">
        <div class="panel">
            <h1>🎙️ Enhanced Diagnostic</h1>
            <h3>✨ Pre-Buffer Sentence Capture</h3>

            <div class="status-card">
                <h3>🤖 System Status</h3>
                <div id="systemStatus">Initializing...</div>
            </div>

            <div class="status-card">
                <h3>📊 Enhanced Metrics</h3>
                <div id="metrics">
                    <div>Confidence: <span id="confidence">--</span></div>
                    <div>Enhanced: <span id="enhancedConf">--</span></div>
                    <div>Audio Quality: <span id="audioQuality">--</span></div>
                    <div>Processing: <span id="processing">--</span></div>
                </div>
            </div>

            <button id="recordBtn" class="record-btn" onclick="recordAudio()">
                🎙️ Click to Record (5s) + Pre-Buffer
            </button>

            <button id="listenBtn" class="record-btn listening-btn" onclick="toggleAlwaysListening()">
                🔄 Start Enhanced Always-Listening
            </button>
        </div>

        <div class="panel">
            <h2>💬 Conversation</h2>
            <div class="messages" id="messages"></div>
        </div>
    </div>

    <script>
        const socket = io();
        let alwaysListeningActive = false;

        socket.on('system_status', function(data) {
            document.getElementById('systemStatus').textContent = data.message;
        });

        socket.on('transcription_result', function(data) {
            addMessage('user', data.text, data.timestamp, {
                confidence: data.confidence,
                enhanced_confidence: data.enhanced_confidence,
                audio_quality: data.audio_quality,
                processing_time: data.processing_time
            });

            document.getElementById('confidence').textContent = (data.confidence * 100).toFixed(0) + '%';
            document.getElementById('enhancedConf').textContent = (data.enhanced_confidence * 100).toFixed(0) + '%';
            document.getElementById('audioQuality').textContent = (data.audio_quality * 100).toFixed(0) + '%';
            document.getElementById('processing').textContent = data.processing_time.toFixed(2) + 's';
        });

        socket.on('ai_response', function(data) {
            addMessage('ai', data.text, data.timestamp, {
                generation_time: data.generation_time
            });
        });

        function recordAudio() {
            socket.emit('record_with_prebuffer');
        }

        function toggleAlwaysListening() {
            const btn = document.getElementById('listenBtn');
            if (!alwaysListeningActive) {
                socket.emit('start_enhanced_listening');
                btn.textContent = '⏹️ Stop Enhanced Always-Listening';
                alwaysListeningActive = true;
            } else {
                socket.emit('stop_enhanced_listening');
                btn.textContent = '🔄 Start Enhanced Always-Listening';
                alwaysListeningActive = false;
            }
        }

        function addMessage(type, text, timestamp, metadata) {
            const messagesEl = document.getElementById('messages');
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
            }

            messageEl.innerHTML = `
                <strong>${icon} ${timestamp}</strong><br>
                ${text}
                ${metaText ? `<div class="metrics">${metaText}</div>` : ''}
            `;

            messagesEl.appendChild(messageEl);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('record_with_prebuffer')
def handle_record_with_prebuffer():
    """Enhanced 5-second recording with 2-second pre-buffer"""
    global interaction_count

    try:
        interaction_count += 1

        socketio.emit('system_status', {
            'status': 'recording',
            'message': '🔴 Recording 5 seconds + pre-buffer...'
        })

        # Record new 5-second audio (same as working click-to-record)
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

        # ENHANCEMENT: Combine pre-buffer with new recording
        if len(audio_pre_buffer) > 0:
            prebuffer_audio = np.array(list(audio_pre_buffer))
            # Combine last 1 second of pre-buffer with 5-second recording
            combined_audio = np.concatenate([prebuffer_audio[-16000:], audio_data.flatten()])
        else:
            combined_audio = audio_data.flatten()

        # Save combined audio
        audio_filename = f"enhanced_record_{interaction_count:03d}.wav"
        audio_path = session_dir / audio_filename

        with wave.open(str(audio_path), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            audio_int16 = (combined_audio * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())

        socketio.emit('system_status', {
            'status': 'processing',
            'message': '📝 Processing enhanced audio...'
        })

        # Transcribe combined audio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        transcription_result = loop.run_until_complete(stt.transcribe_audio(combined_audio))

        if not transcription_result.text.strip():
            socketio.emit('system_status', {
                'status': 'ready',
                'message': '❌ No speech detected'
            })
            loop.close()
            return

        # Enhanced semantic scoring
        audio_quality = calculate_audio_quality(combined_audio)
        enhanced_confidence = calculate_enhanced_confidence(
            transcription_result.confidence,
            audio_quality,
            len(transcription_result.text)
        )

        # Send enhanced transcription result
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
            # Generate AI voice (simple approach)
            socketio.emit('ai_response', {
                'text': ai_response,
                'generation_time': 1.0,  # Placeholder
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })

            # Play AI voice
            os.system(f'say "{ai_response}" &')

        socketio.emit('system_status', {
            'status': 'ready',
            'message': '✅ Enhanced recording complete'
        })

    except Exception as e:
        socketio.emit('system_status', {
            'status': 'error',
            'message': f'❌ Recording error: {e}'
        })

async def call_ollama(prompt, max_tokens=150):
    """Call Ollama LLM with context-aware prompting"""
    try:
        import aiohttp

        full_prompt = f"{CONTEXT_PROMPT}\n\nUser: {prompt}\nAssistant:"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.1:8b",
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('response', 'No response generated')
                else:
                    return f"Error: Ollama returned status {response.status}"

    except Exception as e:
        return f"Error calling Ollama: {e}"

async def initialize_components():
    """Initialize STT and start pre-buffer"""
    global stt, pre_buffer_active, pre_buffer_thread

    try:
        # Initialize Whisper STT
        whisper_config = {
            'whisper_model': 'base',
            'whisper_device': 'cpu',
            'language': 'en',
            'sample_rate': 16000
        }
        stt = WhisperSTT(whisper_config)
        await stt.initialize()

        # Start pre-buffer thread
        pre_buffer_active = True
        pre_buffer_thread = threading.Thread(target=continuous_pre_buffer, daemon=True)
        pre_buffer_thread.start()

        socketio.emit('system_status', {'message': 'Enhanced system ready with pre-buffer'})
        return True

    except Exception as e:
        socketio.emit('system_status', {'message': f'Initialization failed: {e}'})
        return False

if __name__ == '__main__':
    print("🚀 Starting Enhanced Diagnostic Voice Interface...")
    print("✨ Key Enhancement: Pre-buffer captures sentence beginnings")
    print("🎯 Building on the 'top tier' click-to-record functionality")

    # Initialize components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()

    if not success:
        print("❌ Failed to initialize components")
        sys.exit(1)

    print("🌐 Enhanced diagnostic interface: http://localhost:8083")
    print("🎤 Ready for enhanced sentence-beginning capture!")

    socketio.run(app, host='0.0.0.0', port=8083, debug=False, allow_unsafe_werkzeug=True)