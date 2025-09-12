#!/usr/bin/env python3
"""
Simple Transcription Web App - Direct Ollama integration
"""

import asyncio
import sys
import os
import json
import threading
import aiohttp
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import sounddevice as sd
import numpy as np

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from audio.stt import WhisperSTT

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'transcription_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
stt = None
always_listening_active = False
listening_thread = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Transcription - The E and Me</title>
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
            min-width: 180px;
            display: inline-block;
        }
        .click-record {
            background: rgba(220, 53, 69, 0.8);
            border: 3px solid #dc3545;
        }
        .click-record:hover:not(:disabled) {
            background: rgba(220, 53, 69, 1);
            transform: scale(1.05);
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
        .mode-info {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 12px;
            margin: 15px 0;
            font-size: 0.9em;
            text-align: center;
        }
        .conversation {
            max-height: 500px;
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
        .microphone-info {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 Voice Transcription</h1>
            <p>Click button → Speak → Get AI response</p>
        </div>
        
        <div id="status" class="status ready">
            🟢 Ready to transcribe
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
        
        <div id="modeInfo" class="mode-info">
            <strong>Mode:</strong> <span id="currentMode">Click to Record</span><br>
            <span id="modeDescription">Click the red button to record a 5-second voice message</span>
        </div>
        
        <div class="microphone-info">
            <strong>🎙️ Using:</strong> Live Streamer CAM 513 (Device #2)<br>
            <strong>🤖 AI:</strong> Ollama Llama 3.1 8B
        </div>
        
        <div id="conversation" class="conversation">
            <div class="system-message">
                Click "Start Transcription" to begin voice interaction...
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let isTranscribing = false;
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

        socket.on('voice_detected', function(data) {
            if (alwaysListening) {
                addMessage('system', `🎯 Voice detected (${data.confidence}% confidence) - Processing...`, data.timestamp);
            }
        });

        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = `status ${status}`;
            statusEl.innerHTML = message;
            
            const clickBtn = document.getElementById('clickRecordBtn');
            const listenBtn = document.getElementById('alwaysListenBtn');
            const stopBtn = document.getElementById('stopBtn');
            
            if (status === 'listening' || status === 'processing') {
                clickBtn.disabled = true;
                if (!alwaysListening) {
                    listenBtn.disabled = true;
                }
            } else {
                clickBtn.disabled = false;
                if (!alwaysListening) {
                    listenBtn.disabled = false;
                }
            }
        }

        function updateModeDisplay(mode, description) {
            document.getElementById('currentMode').textContent = mode;
            document.getElementById('modeDescription').textContent = description;
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
                
                updateModeDisplay('Always Listening', 'Continuously monitoring for voice activity');
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
                
                updateModeDisplay('Click to Record', 'Click the red button to record a 5-second voice message');
            }
        }

        socket.on('connect', function() {
            console.log('Connected to transcription server');
            updateStatus('ready', '🟢 Connected and ready');
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

@socketio.on('start_click_record')
def handle_click_record():
    """Handle transcription request"""
    
    def transcription_task():
        try:
            # Update status
            socketio.emit('status_update', {
                'status': 'listening',
                'message': '🔴 Recording for 5 seconds - SPEAK NOW!'
            })
            
            # Record audio using device #2
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
            
            # Update status
            socketio.emit('status_update', {
                'status': 'processing',
                'message': '📝 Processing speech...'
            })
            
            # Transcribe audio
            audio_array = audio_data.flatten()
            
            # Run transcription
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            transcription_result = loop.run_until_complete(stt.transcribe_audio(audio_array))
            
            if not transcription_result.text.strip():
                socketio.emit('error_message', {
                    'message': '❌ No speech detected. Please try again.',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                socketio.emit('status_update', {
                    'status': 'ready',
                    'message': '🟢 Ready to transcribe'
                })
                socketio.emit('transcription_complete')
                loop.close()
                return
            
            # Send transcription result
            socketio.emit('transcription_result', {
                'text': transcription_result.text,
                'confidence': transcription_result.confidence,
                'processing_time': transcription_result.processing_time,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Generate AI response
            socketio.emit('status_update', {
                'status': 'processing',
                'message': '🤖 AI generating response...'
            })
            
            prompt = f"You are a helpful assistant. Respond naturally and conversationally to: {transcription_result.text}"
            
            # Call Ollama directly
            ai_response = loop.run_until_complete(call_ollama(prompt, max_tokens=100))
            loop.close()
            
            if "Error" in ai_response:
                socketio.emit('error_message', {
                    'message': f'❌ AI Error: {ai_response}',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
            else:
                socketio.emit('ai_response', {
                    'text': ai_response,
                    'generation_time': 1.0,  # Approximate
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                
                # Speak the response
                os.system(f'say "{ai_response}" &')
            
            # Reset status
            socketio.emit('status_update', {
                'status': 'ready',
                'message': '🟢 Ready for next transcription'
            })
            
        except Exception as e:
            socketio.emit('error_message', {
                'message': f'❌ Error: {str(e)}',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            socketio.emit('status_update', {
                'status': 'ready',
                'message': '🟢 Ready to transcribe'
            })
        finally:
            socketio.emit('transcription_complete')
    
    # Run in background thread
    thread = threading.Thread(target=transcription_task)
    thread.daemon = True
    thread.start()

@socketio.on('start_always_listening')
def handle_always_listening():
    """Start continuous voice monitoring"""
    global always_listening_active, listening_thread
    
    if always_listening_active:
        return
    
    always_listening_active = True
    
    def continuous_listening():
        """Continuous voice monitoring loop"""
        global always_listening_active
        
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
                'message': '🔄 Always listening - Speak anytime!'
            })
            
            # Continuous monitoring
            chunk_duration = 0.5  # 500ms chunks
            sample_rate = 16000
            device_id = 2
            chunk_frames = int(chunk_duration * sample_rate)
            
            while always_listening_active:
                try:
                    # Record small chunk
                    audio_chunk = sd.rec(chunk_frames, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                    sd.wait()
                    
                    audio_array = audio_chunk.flatten()
                    
                    # Check for voice activity
                    vad_result = vad.detect_voice_activity(audio_array)
                    
                    if vad_result.has_voice and vad_result.confidence > 0.8:
                        # Voice detected! Record longer segment
                        socketio.emit('voice_detected', {
                            'confidence': int(vad_result.confidence * 100),
                            'timestamp': datetime.now().strftime("%H:%M:%S")
                        })
                        
                        socketio.emit('status_update', {
                            'status': 'listening',
                            'message': '🔴 Voice detected - Recording...'
                        })
                        
                        # Record 3 seconds for transcription
                        full_audio = sd.rec(int(3 * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        
                        # Process the audio
                        process_detected_speech(full_audio.flatten())
                        
                        # Brief pause before resuming monitoring
                        time.sleep(1)
                        
                        if always_listening_active:
                            socketio.emit('status_update', {
                                'status': 'listening',
                                'message': '🔄 Always listening - Speak anytime!'
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

def process_detected_speech(audio_array):
    """Process speech detected during always listening"""
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
            socketio.emit('ai_response', {
                'text': ai_response,
                'generation_time': 1.0,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
            # Speak response
            os.system(f'say "{ai_response}" &')
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
    global always_listening_active
    always_listening_active = False
    
    socketio.emit('status_update', {
        'status': 'ready',
        'message': '🟢 Always listening stopped - Ready for click recording'
    })
    
    socketio.emit('always_listening_stopped')

if __name__ == '__main__':
    print("🚀 Starting Simple Transcription Web App...")
    
    # Initialize components
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(initialize_components())
    loop.close()
    
    if not success:
        print("❌ Failed to initialize components")
        sys.exit(1)
    
    print("🌐 Web interface: http://localhost:8080")
    print("🎤 Ready for voice transcription!")
    
    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)