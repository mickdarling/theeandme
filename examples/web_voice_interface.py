#!/usr/bin/env python3
"""
Web-based Voice Interface - Visual conversation in browser
"""

import asyncio
import sys
import os
import json
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from audio.audio_manager import AudioManager
from llm.local_llm import LocalLLM
from core.config_manager import ConfigManager

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'voice_interface_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global voice assistant instance
voice_assistant = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Interface - The E and Me</title>
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
            max-width: 800px;
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
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            font-weight: bold;
            font-size: 1.2em;
            transition: all 0.3s ease;
        }
        .status.idle {
            background: rgba(108, 117, 125, 0.3);
            border: 2px solid #6c757d;
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
        .status.responding {
            background: rgba(40, 167, 69, 0.3);
            border: 2px solid #28a745;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .conversation {
            max-height: 400px;
            overflow-y: auto;
            margin: 20px 0;
            padding: 20px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .message {
            margin: 15px 0;
            padding: 12px 18px;
            border-radius: 15px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background: rgba(0, 123, 255, 0.3);
            border: 1px solid #007bff;
            margin-left: auto;
            text-align: right;
        }
        .ai-message {
            background: rgba(40, 167, 69, 0.3);
            border: 1px solid #28a745;
            margin-right: auto;
        }
        .timestamp {
            font-size: 0.8em;
            opacity: 0.7;
            margin-top: 5px;
        }
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 0 10px;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            font-size: 0.9em;
        }
        .stat {
            text-align: center;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 Voice Interface</h1>
            <p>Real-time voice conversation with AI</p>
        </div>
        
        <div id="status" class="status idle">
            🟢 Ready - Click "Start Listening" to begin
        </div>
        
        <div class="controls">
            <button id="startBtn" class="btn" onclick="startListening()">🎤 Start Listening</button>
            <button id="stopBtn" class="btn" onclick="stopListening()" disabled>⏹️ Stop</button>
            <button id="clearBtn" class="btn" onclick="clearConversation()">🗑️ Clear</button>
        </div>
        
        <div id="conversation" class="conversation">
            <div style="text-align: center; opacity: 0.6; font-style: italic;">
                Voice conversation will appear here...
            </div>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="interactionCount">0</div>
                <div>Interactions</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="avgResponseTime">0.0s</div>
                <div>Avg Response</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="systemStatus">🟢</div>
                <div>System Status</div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let isListening = false;
        let interactionCount = 0;
        let totalResponseTime = 0;

        // Socket event handlers
        socket.on('status_update', function(data) {
            updateStatus(data.status, data.message);
        });

        socket.on('conversation_update', function(data) {
            addMessage(data.type, data.content, data.timestamp, data.metadata);
        });

        socket.on('system_stats', function(data) {
            updateStats(data);
        });

        function updateStatus(status, message) {
            const statusEl = document.getElementById('status');
            statusEl.className = `status ${status}`;
            statusEl.innerHTML = message;
        }

        function addMessage(type, content, timestamp, metadata) {
            const conversation = document.getElementById('conversation');
            
            // Clear placeholder if this is first message
            if (conversation.children.length === 1 && conversation.children[0].style.textAlign === 'center') {
                conversation.innerHTML = '';
            }
            
            const messageEl = document.createElement('div');
            messageEl.className = `message ${type}-message`;
            
            let icon = type === 'user' ? '🗣️' : '🤖';
            let metaText = '';
            if (metadata) {
                if (metadata.confidence) metaText += ` (${(metadata.confidence * 100).toFixed(0)}% confidence)`;
                if (metadata.processing_time) metaText += ` • ${metadata.processing_time.toFixed(2)}s`;
            }
            
            messageEl.innerHTML = `
                ${icon} ${content}
                <div class="timestamp">${timestamp}${metaText}</div>
            `;
            
            conversation.appendChild(messageEl);
            conversation.scrollTop = conversation.scrollHeight;
        }

        function updateStats(stats) {
            document.getElementById('interactionCount').textContent = stats.interactions || 0;
            document.getElementById('avgResponseTime').textContent = (stats.avg_response_time || 0).toFixed(1) + 's';
            document.getElementById('systemStatus').textContent = stats.system_healthy ? '🟢' : '🔴';
        }

        function startListening() {
            if (!isListening) {
                socket.emit('start_listening');
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                isListening = true;
            }
        }

        function stopListening() {
            if (isListening) {
                socket.emit('stop_listening');
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                isListening = false;
            }
        }

        function clearConversation() {
            document.getElementById('conversation').innerHTML = `
                <div style="text-align: center; opacity: 0.6; font-style: italic;">
                    Voice conversation will appear here...
                </div>
            `;
            interactionCount = 0;
            totalResponseTime = 0;
            updateStats({interactions: 0, avg_response_time: 0, system_healthy: true});
        }

        // Initialize connection
        socket.on('connect', function() {
            console.log('Connected to voice interface server');
            updateStatus('idle', '🟢 Connected - Ready for voice interaction');
        });

        socket.on('disconnect', function() {
            updateStatus('idle', '🔴 Disconnected from server');
        });
    </script>
</body>
</html>
'''

class WebVoiceAssistant:
    def __init__(self):
        config_path = Path(__file__).parent.parent / "config" / "config.example.json"
        
        # Use simple config dict instead of ConfigManager for compatibility
        self.config = {
            'sample_rate': 16000,
            'vad_threshold': 0.7,
            'buffer_duration_seconds': 3.0,
            'min_speech_duration_ms': 300,
            'silence_timeout_seconds': 2.0,
            'whisper_model': 'base'
        }
        
        # Initialize components with simple config
        self.audio_manager = None
        self.llm = None
        self.stats = {
            'interactions': 0,
            'total_response_time': 0,
            'system_healthy': True
        }
    
    async def initialize(self):
        """Initialize the voice assistant components"""
        try:
            # Initialize LLM
            from llm.local_llm import LocalLLM
            self.llm = LocalLLM(None)  # Pass None for now, will handle internally
            
            # Test LLM connection
            test_response = await self.llm.generate("Say hello", max_tokens=10)
            if test_response.error:
                raise Exception(f"LLM error: {test_response.error}")
            
            # For now, we'll use a simplified audio approach
            print("✅ Voice assistant initialized")
            return True
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            self.stats['system_healthy'] = False
            return False
    
    async def process_voice_interaction(self):
        """Process one complete voice interaction"""
        try:
            # Emit status updates
            socketio.emit('status_update', {
                'status': 'listening',
                'message': '🔴 Listening - Please speak now...'
            })
            
            # Import and use simplified audio recording
            import sounddevice as sd
            import numpy as np
            from audio.stt import WhisperSTT
            
            # Record 5 seconds of audio
            duration = 5
            sample_rate = 16000
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
            sd.wait()
            
            socketio.emit('status_update', {
                'status': 'processing',
                'message': '📝 Processing your speech...'
            })
            
            # Transcribe audio
            stt = WhisperSTT(self.config)
            await stt.initialize()
            
            audio_array = audio_data.flatten()
            transcription_result = await stt.transcribe_audio(audio_array)
            
            if not transcription_result.text.strip():
                socketio.emit('conversation_update', {
                    'type': 'system',
                    'content': '❌ No speech detected. Please try again.',
                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                    'metadata': None
                })
                return
            
            # Add user message to conversation
            socketio.emit('conversation_update', {
                'type': 'user',
                'content': transcription_result.text,
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'metadata': {
                    'confidence': transcription_result.confidence,
                    'processing_time': transcription_result.processing_time
                }
            })
            
            # Generate AI response
            socketio.emit('status_update', {
                'status': 'responding',
                'message': '🤖 AI is thinking...'
            })
            
            prompt = f"You are a helpful voice assistant. Respond naturally and conversationally to: {transcription_result.text}"
            response = await self.llm.generate(prompt, max_tokens=100)
            
            if response.error:
                socketio.emit('conversation_update', {
                    'type': 'system',
                    'content': f'❌ AI Error: {response.error}',
                    'timestamp': datetime.now().strftime("%H:%M:%S"),
                    'metadata': None
                })
                return
            
            # Add AI response to conversation
            socketio.emit('conversation_update', {
                'type': 'ai',
                'content': response.content,
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'metadata': {
                    'generation_time': getattr(response, 'generation_time', 0)
                }
            })
            
            # Speak the response
            os.system(f'say "{response.content}"')
            
            # Update stats
            self.stats['interactions'] += 1
            total_time = transcription_result.processing_time + getattr(response, 'generation_time', 0)
            self.stats['total_response_time'] += total_time
            
            socketio.emit('system_stats', {
                'interactions': self.stats['interactions'],
                'avg_response_time': self.stats['total_response_time'] / self.stats['interactions'],
                'system_healthy': self.stats['system_healthy']
            })
            
            stt.cleanup()
            
        except Exception as e:
            socketio.emit('conversation_update', {
                'type': 'system',
                'content': f'❌ Error: {str(e)}',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'metadata': None
            })
        finally:
            socketio.emit('status_update', {
                'status': 'idle',
                'message': '🟢 Ready - Click "Start Listening" for next interaction'
            })

# Initialize global assistant
voice_assistant = WebVoiceAssistant()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('start_listening')
def handle_start_listening():
    """Handle request to start voice interaction"""
    asyncio.create_task(voice_assistant.process_voice_interaction())

@socketio.on('stop_listening')
def handle_stop_listening():
    """Handle request to stop listening"""
    emit('status_update', {
        'status': 'idle',
        'message': '⏹️ Stopped - Ready for next interaction'
    })

if __name__ == '__main__':
    print("🚀 Starting Web Voice Interface...")
    print("🌐 Open your browser to: http://localhost:5000")
    print("🎤 Click 'Start Listening' to begin voice interaction")
    
    # Initialize voice assistant in background
    async def init_assistant():
        await voice_assistant.initialize()
    
    # Run initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_assistant())
    
    # Start Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)