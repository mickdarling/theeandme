#!/usr/bin/env python3
"""
Natural Conversation Voice Interface
Revolutionary approach with echo cancellation, pre-buffering, and interrupt detection

Key Features:
1. Real-time echo cancellation during AI speech
2. Pre-buffer capture (3-second rolling buffer)
3. Interrupt detection with AI pause capability
4. Natural conversation flow
5. Enhanced semantic scoring from autonomous v2.0
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
from typing import Dict, Any, Optional
import sounddevice as sd
import numpy as np
from collections import deque
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import pyaec
import re

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'natural_conversation_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
stt = None
conversation_active = False
conversation_thread = None
ai_speaking = False
interrupt_detected = False

# Echo cancellation setup
echo_canceller = None
reference_buffer = deque(maxlen=16000 * 3)  # 3-second reference buffer

# Pre-buffer system (3-second rolling buffer)
PRE_BUFFER_SIZE = 16000 * 3  # 3 seconds at 16kHz
audio_pre_buffer = deque(maxlen=PRE_BUFFER_SIZE)

# Enhanced semantic scoring (from autonomous v2.0)
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

def detect_interrupt_phrases(text: str) -> bool:
    """Detect natural interrupt phrases"""
    interrupt_phrases = [
        "wait", "hold on", "stop", "excuse me", "sorry", "actually",
        "oh wait", "let me", "can i", "i want to", "but", "however"
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in interrupt_phrases)

# HTML Template for Natural Conversation
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Natural Conversation Interface</title>
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
            height: calc(100vh - 40px);
        }
        .control-panel {
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        .conversation-area {
            background: rgba(255, 255, 255, 0.05);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            display: flex;
            flex-direction: column;
        }
        h1 { margin: 0 0 20px 0; font-size: 2.5em; font-weight: 300; }
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .start-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1.2em;
            cursor: pointer;
            transition: all 0.3s;
        }
        .start-btn:hover { background: #45a049; transform: translateY(-2px); }
        .stop-btn { background: #f44336; }
        .stop-btn:hover { background: #da190b; }
        .messages {
            flex: 1;
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
        .interrupt-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            display: none;
            animation: pulse 1s infinite;
        }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
    </style>
</head>
<body>
    <div class="interrupt-indicator" id="interruptIndicator">🛑 INTERRUPT DETECTED</div>

    <div class="container">
        <div class="control-panel">
            <h1>🎙️ Natural Conversation</h1>

            <div class="status-card">
                <h3>🤖 System Status</h3>
                <div id="systemStatus">Initializing...</div>
            </div>

            <div class="status-card">
                <h3>🎵 Audio Status</h3>
                <div id="audioStatus">Ready</div>
            </div>

            <div class="status-card">
                <h3>📊 Performance Metrics</h3>
                <div id="performanceMetrics">
                    <div>Echo Cancellation: <span id="echoCancellation">Inactive</span></div>
                    <div>Pre-buffer: <span id="preBuffer">Ready</span></div>
                    <div>Interrupt Detection: <span id="interruptDetection">Active</span></div>
                </div>
            </div>

            <button id="startBtn" class="start-btn" onclick="startConversation()">
                Start Natural Conversation
            </button>
        </div>

        <div class="conversation-area">
            <h2>💬 Conversation Flow</h2>
            <div class="messages" id="messages"></div>
        </div>
    </div>

    <script>
        const socket = io();
        let conversationActive = false;

        socket.on('system_status', function(data) {
            document.getElementById('systemStatus').textContent = data.message;
        });

        socket.on('audio_status', function(data) {
            document.getElementById('audioStatus').textContent = data.message;
        });

        socket.on('performance_metrics', function(data) {
            document.getElementById('echoCancellation').textContent = data.echo_cancellation;
            document.getElementById('preBuffer').textContent = data.pre_buffer;
            document.getElementById('interruptDetection').textContent = data.interrupt_detection;
        });

        socket.on('user_speech', function(data) {
            addMessage('user', data.text, data.timestamp, {
                confidence: data.confidence,
                enhanced_confidence: data.enhanced_confidence,
                audio_quality: data.audio_quality,
                semantic_accuracy: data.semantic_accuracy
            });
        });

        socket.on('ai_response', function(data) {
            addMessage('ai', data.text, data.timestamp, {
                generation_time: data.generation_time
            });
        });

        socket.on('interrupt_detected', function(data) {
            const indicator = document.getElementById('interruptIndicator');
            indicator.style.display = 'block';
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 2000);
            addMessage('system', '🛑 Interrupt detected - AI paused', data.timestamp);
        });

        function startConversation() {
            const btn = document.getElementById('startBtn');
            if (!conversationActive) {
                socket.emit('start_natural_conversation');
                btn.textContent = 'Stop Conversation';
                btn.className = 'start-btn stop-btn';
                conversationActive = true;
            } else {
                socket.emit('stop_natural_conversation');
                btn.textContent = 'Start Natural Conversation';
                btn.className = 'start-btn';
                conversationActive = false;
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
                if (metadata.semantic_accuracy !== undefined) metaText += ` • ${(metadata.semantic_accuracy * 100).toFixed(0)}% sem`;
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

async def initialize_components():
    """Initialize STT and echo cancellation"""
    global stt, echo_canceller

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

        # Initialize echo canceller
        echo_canceller = pyaec.Aec(sample_rate=16000, frame_size=512, filter_length=1024)

        socketio.emit('system_status', {'message': 'All components initialized successfully'})
        return True

    except Exception as e:
        print(f"Initialization error details: {e}")
        import traceback
        traceback.print_exc()
        socketio.emit('system_status', {'message': f'Initialization failed: {e}'})
        return False

def natural_conversation_loop():
    """Main conversation loop with echo cancellation and interrupt detection"""
    global conversation_active, ai_speaking, interrupt_detected, reference_buffer, audio_pre_buffer

    sample_rate = 16000
    device_id = 2  # Live Streamer CAM 513
    chunk_size = 512

    socketio.emit('audio_status', {'message': 'Natural conversation started'})
    socketio.emit('performance_metrics', {
        'echo_cancellation': 'Active',
        'pre_buffer': 'Recording',
        'interrupt_detection': 'Monitoring'
    })

    try:
        while conversation_active:
            # Continuous audio capture
            audio_chunk = sd.rec(chunk_size, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
            sd.wait()
            audio_array = audio_chunk.flatten()

            # Add to pre-buffer
            audio_pre_buffer.extend(audio_array)

            if ai_speaking:
                # During AI speech - apply echo cancellation
                if len(reference_buffer) > 0:
                    # Get reference signal (AI output)
                    ref_signal = np.array(list(reference_buffer)[-chunk_size:])

                    # Apply echo cancellation
                    try:
                        cancelled_audio = echo_canceller.process(audio_array, ref_signal)

                        # Check for interrupt in cancelled audio
                        if detect_speech_in_cancelled_audio(cancelled_audio):
                            # Quick transcription for interrupt detection
                            interrupt_text = quick_transcribe_interrupt(cancelled_audio)

                            if interrupt_text and detect_interrupt_phrases(interrupt_text):
                                interrupt_detected = True
                                ai_speaking = False
                                socketio.emit('interrupt_detected', {
                                    'text': interrupt_text,
                                    'timestamp': datetime.now().strftime("%H:%M:%S")
                                })
                                # Process the full pre-buffer as user speech
                                process_full_speech_from_prebuffer()

                    except Exception as e:
                        print(f"Echo cancellation error: {e}")
            else:
                # Not during AI speech - normal speech detection
                rms_level = np.sqrt(np.mean(audio_array ** 2))

                if rms_level > 0.01:  # Speech detected
                    # Wait for complete speech, then process with pre-buffer
                    complete_speech = capture_complete_speech(rms_level)
                    if complete_speech is not None:
                        process_speech_with_prebuffer(complete_speech)

            time.sleep(0.01)  # Small delay to prevent CPU overload

    except Exception as e:
        socketio.emit('system_status', {'message': f'Conversation error: {e}'})

    socketio.emit('audio_status', {'message': 'Natural conversation stopped'})

def detect_speech_in_cancelled_audio(cancelled_audio):
    """Detect speech in echo-cancelled audio"""
    rms = np.sqrt(np.mean(cancelled_audio ** 2))
    return rms > 0.005  # Threshold for cancelled audio

def quick_transcribe_interrupt(audio_data):
    """Quick transcription for interrupt detection"""
    try:
        # Simple approach - just check if there's meaningful audio
        if len(audio_data) > 1600:  # At least 0.1 seconds
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(stt.transcribe_audio(audio_data))
            loop.close()
            return result.text
        return None
    except:
        return None

def process_full_speech_from_prebuffer():
    """Process speech using the full pre-buffer"""
    if len(audio_pre_buffer) > 0:
        full_audio = np.array(list(audio_pre_buffer))
        process_transcribed_speech(full_audio)

def capture_complete_speech(initial_rms):
    """Capture complete speech until silence"""
    sample_rate = 16000
    device_id = 2
    silence_threshold = 0.005
    max_silence_duration = 2.0  # 2 seconds of silence ends speech

    speech_audio = []
    silence_count = 0
    max_silence_chunks = int(max_silence_duration * sample_rate / 512)

    while conversation_active and not ai_speaking:
        chunk = sd.rec(512, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
        sd.wait()
        audio_chunk = chunk.flatten()

        rms = np.sqrt(np.mean(audio_chunk ** 2))

        if rms > silence_threshold:
            speech_audio.extend(audio_chunk)
            silence_count = 0
        else:
            silence_count += 1
            if silence_count > max_silence_chunks:
                break
            speech_audio.extend(audio_chunk)

    return np.array(speech_audio) if len(speech_audio) > 1600 else None

def process_speech_with_prebuffer(speech_audio):
    """Process speech including pre-buffer data"""
    # Combine pre-buffer with current speech
    prebuffer_audio = np.array(list(audio_pre_buffer)[-PRE_BUFFER_SIZE//2:])  # Last 1.5 seconds
    full_audio = np.concatenate([prebuffer_audio, speech_audio])

    process_transcribed_speech(full_audio)

def process_transcribed_speech(audio_data):
    """Transcribe and process speech with enhanced metrics"""
    try:
        # Transcribe
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(stt.transcribe_audio(audio_data))
        loop.close()

        if not result.text.strip():
            return

        # Calculate enhanced metrics
        audio_quality = calculate_audio_quality(audio_data)
        enhanced_confidence = calculate_enhanced_confidence(
            result.confidence, audio_quality, len(result.text)
        )

        # Emit user speech
        socketio.emit('user_speech', {
            'text': result.text,
            'confidence': result.confidence,
            'enhanced_confidence': enhanced_confidence,
            'audio_quality': audio_quality,
            'semantic_accuracy': 1.0,  # Could compare with expected if available
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        # Generate AI response
        generate_ai_response(result.text)

    except Exception as e:
        socketio.emit('system_status', {'message': f'Speech processing error: {e}'})

def generate_ai_response(user_text):
    """Generate AI response with high-quality voice"""
    global ai_speaking, reference_buffer

    ai_speaking = True
    start_time = time.time()

    try:
        # Simple echo response for testing - replace with actual AI
        response_text = f"I heard you say: {user_text}. This is a natural conversation test."

        generation_time = time.time() - start_time

        # Emit AI response
        socketio.emit('ai_response', {
            'text': response_text,
            'generation_time': generation_time,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        # Generate and play AI voice (with reference tracking)
        speak_with_reference_tracking(response_text)

    except Exception as e:
        socketio.emit('system_status', {'message': f'AI response error: {e}'})
    finally:
        ai_speaking = False

def speak_with_reference_tracking(text):
    """Speak text while tracking reference signal for echo cancellation"""
    global reference_buffer

    try:
        # Generate speech to temporary file
        temp_file = f"/tmp/ai_speech_{int(time.time())}.wav"
        subprocess.run(['say', '-v', 'Samantha', '-o', temp_file, text], check=True)

        # Play audio while tracking reference
        with wave.open(temp_file, 'rb') as wav_file:
            frames = wav_file.readframes(-1)
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0

            # Add to reference buffer for echo cancellation
            reference_buffer.extend(audio_data)

            # Play audio
            sd.play(audio_data, samplerate=16000)
            sd.wait()

        # Clean up
        os.remove(temp_file)

    except Exception as e:
        print(f"Speech generation error: {e}")

@socketio.on('start_natural_conversation')
def handle_start_conversation():
    """Start natural conversation with echo cancellation"""
    global conversation_active, conversation_thread

    if not conversation_active:
        conversation_active = True
        conversation_thread = threading.Thread(target=natural_conversation_loop, daemon=True)
        conversation_thread.start()
        socketio.emit('system_status', {'message': 'Natural conversation started'})

@socketio.on('stop_natural_conversation')
def handle_stop_conversation():
    """Stop natural conversation"""
    global conversation_active

    conversation_active = False
    socketio.emit('system_status', {'message': 'Natural conversation stopped'})

if __name__ == '__main__':
    print("🚀 Starting Natural Conversation Interface...")
    print("🎯 Features: Echo cancellation, Pre-buffer, Interrupt detection")

    # Initialize components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()

    if not success:
        print("❌ Failed to initialize components")
        sys.exit(1)

    print("🌐 Natural conversation interface: http://localhost:8082")
    print("🎤 Ready for natural conversation with interrupt support!")

    socketio.run(app, host='0.0.0.0', port=8082, debug=False, allow_unsafe_werkzeug=True)