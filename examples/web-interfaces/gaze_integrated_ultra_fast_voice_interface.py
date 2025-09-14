#!/usr/bin/env python3
"""
Gaze-Integrated Ultra-Fast Voice Interface 2025
Revolutionary multi-modal voice interface with gaze detection integration

BREAKTHROUGH FEATURES:
✅ Real-time gaze detection integration
✅ Multi-modal intent routing (Execute/Ignore/Respond/Minimal)
✅ Ultra-fast pattern matching preserved
✅ Gaze-filtered voice processing
✅ Enhanced web interface with gaze state display
✅ Complete performance monitoring
✅ Graceful fallbacks when gaze detection unavailable

REVOLUTIONARY INTENT MATRIX:
| Gaze State     | Voice Input      | Intent Decision | System Action        |
|----------------|------------------|-----------------|----------------------|
| AT_SCREEN      | Command          | **Execute**     | Process & execute    |
| LOOKING_AWAY   | Command          | **Ignore**      | No action (thinking) |
| AT_SCREEN      | Conversational   | **Respond**     | Engage conversation  |
| LOOKING_AWAY   | Conversational   | **Minimal**     | Natural disengagement|
"""

import asyncio
import sys
import os
import json
import threading
import aiohttp
import time
import wave
from threading import Lock
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import numpy as np
import re

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from RealtimeSTT import AudioToTextRecorder

# Import our breakthrough components
from enhanced_echo_blocker_with_voice_fingerprinting import EnhancedEchoBlocker
from enhanced_voice_automation import EnhancedVoiceAutomation  # Fallback system
from ultra_fast_voice_automation import UltraFastVoiceAutomation, FastVoiceResponse  # Primary system
from voice_calibration_persistence import VoiceCalibrationManager

# Import multi-modal integration system
from multi_modal_voice_integration import MultiModalVoiceIntegration
from gaze_detection_foundation import GazeState, IntentDecision

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'gaze_integrated_ultra_fast_voice_interface_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global components
recorder = None
echo_blocker = None
ultra_fast_automation = None  # Primary processor
enhanced_automation = None   # Fallback processor
voice_calibration = None
multi_modal_integration = None  # NEW: Multi-modal integration system
always_listening_active = False
session_dir = None
text_processing_lock = Lock()

# Enhanced performance metrics with multi-modal integration
performance_metrics = {
    'session_start': datetime.now().isoformat(),
    'total_transcriptions': 0,
    'blocked_echoes': 0,
    'passed_inputs': 0,
    'ai_responses': 0,
    'perfect_captures': 0,
    'voice_fingerprint_blocks': 0,
    'time_content_blocks': 0,
    'combined_blocks': 0,

    # Ultra-fast metrics
    'ultra_fast_responses': 0,
    'enhanced_fallbacks': 0,
    'pattern_hits': 0,
    'average_processing_time': 0.0,
    'fastest_response': float('inf'),
    'slowest_response': 0.0,

    # NEW: Multi-modal metrics
    'gaze_filtered_inputs': 0,
    'execute_decisions': 0,
    'ignore_decisions': 0,
    'respond_decisions': 0,
    'minimal_decisions': 0,
    'gaze_detection_active': False,
    'current_gaze_state': 'system_disabled',
    'gaze_state_changes': 0,

    'pipeline_times': {
        'stt_to_processing': [],
        'processing_time': [],
        'processing_to_tts': [],
        'total_pipeline': [],
        'intent_classification_time': []  # NEW
    }
}

def setup_session_directory():
    """Setup session directory for audio recordings"""
    global session_dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(f"gaze_integrated_session_{timestamp}")
    session_dir.mkdir(exist_ok=True)
    print(f"📁 Session directory: {session_dir}")
    return session_dir

def record_ai_voice(text: str, response_strategy: dict) -> str:
    """Record AI voice generation with intent-based TTS customization"""
    if not session_dir:
        setup_session_directory()

    timestamp = datetime.now().strftime("%H%M%S")
    ai_audio_file = f"ai_voice_{timestamp}.wav"
    ai_filepath = session_dir / ai_audio_file

    try:
        # Customize TTS based on intent decision
        safe_text = text.replace('"', '\\"').replace("'", "\\'")

        # Different TTS settings based on response strategy
        if not response_strategy.get('tts_enabled', True):
            # No TTS for ignored commands
            print(f"🔇 TTS disabled for ignored command: {text}")
            return None

        tts_voice = response_strategy.get('tts_voice', 'normal')
        if tts_voice == 'quiet':
            # Lower volume for minimal responses
            os.system(f'say "{safe_text}" -o "{ai_filepath}" --data-format=LEI16@16000 -r 180')
        elif tts_voice == 'friendly':
            # Slightly higher pitch for conversational
            os.system(f'say "{safe_text}" -o "{ai_filepath}" --data-format=LEI16@16000 -r 200')
        else:
            # Normal voice for commands
            os.system(f'say "{safe_text}" -o "{ai_filepath}" --data-format=LEI16@16000')

        # Play the AI response through speakers if TTS enabled
        if response_strategy.get('tts_enabled', True):
            import subprocess
            subprocess.run(['afplay', str(ai_filepath)], check=True)
            print(f"🔊 AI Voice played ({tts_voice} voice): {ai_audio_file}")

        return str(ai_filepath)

    except Exception as e:
        print(f"❌ Failed to record/play AI voice: {e}")
        return None

def update_pipeline_metrics(stt_time: float, processing_time: float, tts_time: float, total_time: float, intent_time: float = 0.0):
    """Update pipeline timing metrics with multi-modal integration timing"""
    global performance_metrics

    performance_metrics['pipeline_times']['stt_to_processing'].append(stt_time)
    performance_metrics['pipeline_times']['processing_time'].append(processing_time)
    performance_metrics['pipeline_times']['processing_to_tts'].append(tts_time)
    performance_metrics['pipeline_times']['total_pipeline'].append(total_time)
    performance_metrics['pipeline_times']['intent_classification_time'].append(intent_time)

    # Update running averages (keep last 50 entries)
    for key in performance_metrics['pipeline_times']:
        if len(performance_metrics['pipeline_times'][key]) > 50:
            performance_metrics['pipeline_times'][key] = performance_metrics['pipeline_times'][key][-50:]

# Enhanced HTML Template with gaze detection display
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🧠⚡ Gaze-Integrated Ultra-Fast Voice Interface 2025</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .revolutionary-badge {
            background: #ff6b35;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin: 5px;
        }

        .gaze-badge {
            background: #9c27b0;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin: 5px;
        }

        .lightning-badge {
            background: #ffeb3b;
            color: #333;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin: 5px;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 20px;
        }

        .panel {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .gaze-panel {
            border: 2px solid #9c27b0;
            background: rgba(156, 39, 176, 0.1);
        }

        .controls {
            text-align: center;
            margin-bottom: 20px;
        }

        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 15px 30px;
            margin: 10px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }

        button:hover {
            background: #45a049;
            transform: translateY(-2px);
        }

        button.danger {
            background: #f44336;
        }

        button:disabled {
            background: #cccccc;
            cursor: not-allowed;
            transform: none;
        }

        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
        }

        .status.listening {
            background: rgba(76, 175, 80, 0.3);
            border: 2px solid #4CAF50;
        }

        .status.processing {
            background: rgba(255, 193, 7, 0.3);
            border: 2px solid #FFC107;
        }

        .status.ultra-fast {
            background: rgba(255, 235, 59, 0.3);
            border: 2px solid #FFEB3B;
        }

        .status.gaze-active {
            background: rgba(156, 39, 176, 0.3);
            border: 2px solid #9c27b0;
        }

        .status.idle {
            background: rgba(158, 158, 158, 0.3);
            border: 2px solid #9E9E9E;
        }

        .chat {
            height: 300px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
        }

        .message {
            margin: 10px 0;
            padding: 10px 15px;
            border-radius: 15px;
            max-width: 80%;
        }

        .user-message {
            background: #2196F3;
            margin-left: auto;
            text-align: right;
        }

        .ai-message {
            background: #4CAF50;
            margin-right: auto;
        }

        .ultra-fast-message {
            background: #FFEB3B;
            color: #333;
            margin-right: auto;
        }

        .ignored-message {
            background: #9E9E9E;
            margin-right: auto;
            opacity: 0.7;
            font-style: italic;
        }

        .minimal-message {
            background: #607D8B;
            margin-right: auto;
            opacity: 0.8;
            font-size: 14px;
        }

        .blocked-message {
            background: #f44336;
            margin-right: auto;
            opacity: 0.7;
            font-style: italic;
        }

        .metrics {
            font-size: 14px;
            line-height: 1.6;
        }

        .metric-value {
            font-weight: bold;
            color: #4CAF50;
        }

        .gaze-value {
            font-weight: bold;
            color: #9c27b0;
        }

        .ultra-fast-value {
            font-weight: bold;
            color: #FFEB3B;
        }

        .gaze-indicator {
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
        }

        .gaze-at-screen {
            background: rgba(76, 175, 80, 0.3);
            border: 2px solid #4CAF50;
        }

        .gaze-looking-away {
            background: rgba(255, 193, 7, 0.3);
            border: 2px solid #FFC107;
        }

        .gaze-uncertain {
            background: rgba(158, 158, 158, 0.3);
            border: 2px solid #9E9E9E;
        }

        .gaze-disabled {
            background: rgba(244, 67, 54, 0.3);
            border: 2px solid #f44336;
        }

        .intent-matrix {
            margin-top: 15px;
            font-size: 12px;
        }

        .intent-row {
            margin: 8px 0;
            padding: 8px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .intent-execute {
            background: rgba(76, 175, 80, 0.3);
            border-left: 4px solid #4CAF50;
        }

        .intent-ignore {
            background: rgba(158, 158, 158, 0.3);
            border-left: 4px solid #9E9E9E;
        }

        .intent-respond {
            background: rgba(33, 150, 243, 0.3);
            border-left: 4px solid #2196F3;
        }

        .intent-minimal {
            background: rgba(96, 125, 139, 0.3);
            border-left: 4px solid #607D8B;
        }

        .layer {
            margin: 5px 0;
            padding: 8px;
            border-radius: 5px;
            font-size: 12px;
        }

        .layer.active {
            background: rgba(244, 67, 54, 0.3);
            border-left: 4px solid #f44336;
        }

        .layer.inactive {
            background: rgba(76, 175, 80, 0.3);
            border-left: 4px solid #4CAF50;
        }

        .layer.ultra-fast {
            background: rgba(255, 235, 59, 0.3);
            border-left: 4px solid #FFEB3B;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        @keyframes gazeGlow {
            0% { box-shadow: 0 0 5px #9c27b0; }
            50% { box-shadow: 0 0 20px #9c27b0; }
            100% { box-shadow: 0 0 5px #9c27b0; }
        }

        @keyframes lightning {
            0% { background: #FFEB3B; }
            50% { background: #FFC107; }
            100% { background: #FFEB3B; }
        }

        .listening button {
            animation: pulse 2s infinite;
        }

        .gaze-active-animation {
            animation: gazeGlow 3s infinite;
        }

        .ultra-fast-processing {
            animation: lightning 0.5s infinite;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠⚡ Gaze-Integrated Ultra-Fast Voice Interface 2025</h1>
        <span class="revolutionary-badge">REVOLUTIONARY</span>
        <span class="gaze-badge">🧠 GAZE-AWARE</span>
        <span class="lightning-badge">⚡ ULTRA-FAST</span>
        <p>Multi-Modal Intent Detection • Gaze + Voice Integration • Revolutionary UX</p>
    </div>

    <div class="container">
        <div class="panel">
            <h2>🎤 Voice Interface</h2>

            <div class="controls">
                <button id="startListening" onclick="startListening()">Start Gaze-Integrated Listening</button>
                <button id="stopListening" onclick="stopListening()" disabled>Stop Listening</button>
            </div>

            <div id="status" class="status idle">Status: Ready for Multi-Modal Processing</div>

            <div class="chat" id="chatArea">
                <div class="message ai-message">
                    🧠⚡ Gaze-Integrated Ultra-Fast Voice Interface loaded! Now with revolutionary multi-modal intent detection.
                </div>
            </div>

            <div style="text-align: center; font-size: 12px; opacity: 0.7; margin-top: 10px;">
                💡 Try looking at/away from screen while saying:<br>
                "Open Chrome" • "How are you?" • "I should search for something"
            </div>
        </div>

        <div class="panel gaze-panel">
            <h2>👁️ Gaze Detection</h2>

            <div id="gazeIndicator" class="gaze-indicator gaze-disabled">
                🔇 Gaze Detection Initializing...
            </div>

            <div class="metrics">
                <div>Current State: <span id="gazeState" class="gaze-value">Initializing</span></div>
                <div>Confidence: <span id="gazeConfidence" class="gaze-value">0.0</span></div>
                <div>Looking Probability: <span id="lookingProbability" class="gaze-value">0.0%</span></div>
                <div>Face Detected: <span id="faceDetected" class="gaze-value">No</span></div>
                <div>State Duration: <span id="stateDuration" class="gaze-value">0.0s</span></div>
                <div>State Changes: <span id="stateChanges" class="metric-value">0</span></div>
            </div>

            <div class="intent-matrix">
                <h3>🧠 Intent Matrix</h3>
                <div class="intent-row intent-execute">
                    <span>👁️ At Screen + 🗣️ Command</span>
                    <span>→ ✅ EXECUTE</span>
                </div>
                <div class="intent-row intent-ignore">
                    <span>👁️ Away + 🗣️ Command</span>
                    <span>→ 🔇 IGNORE</span>
                </div>
                <div class="intent-row intent-respond">
                    <span>👁️ At Screen + 💬 Question</span>
                    <span>→ 💬 RESPOND</span>
                </div>
                <div class="intent-row intent-minimal">
                    <span>👁️ Away + 💬 Comment</span>
                    <span>→ 🔹 MINIMAL</span>
                </div>
            </div>
        </div>

        <div class="panel">
            <h2>📊 Performance Metrics</h2>

            <div class="metrics">
                <div>Session Duration: <span id="sessionDuration" class="metric-value">0:00</span></div>
                <div>Total Transcriptions: <span id="totalTranscriptions" class="metric-value">0</span></div>
                <div>Ultra-Fast Responses: <span id="ultraFastResponses" class="ultra-fast-value">0</span></div>
                <div>Enhanced Fallbacks: <span id="enhancedFallbacks" class="metric-value">0</span></div>
                <div>Gaze-Filtered Inputs: <span id="gazeFilteredInputs" class="gaze-value">0</span></div>
                <div>Pattern Hit Rate: <span id="patternHitRate" class="ultra-fast-value">0%</span></div>
                <div>Avg Processing Time: <span id="avgProcessingTime" class="ultra-fast-value">0ms</span></div>
                <div>Fastest Response: <span id="fastestResponse" class="ultra-fast-value">∞ms</span></div>
                <div>Blocked Echoes: <span id="blockedEchoes" class="metric-value">0</span></div>
            </div>

            <div style="margin-top: 15px;">
                <h3>🧠 Intent Decisions</h3>
                <div class="metrics">
                    <div>Execute: <span id="executeDecisions" class="gaze-value">0</span></div>
                    <div>Ignore: <span id="ignoreDecisions" class="gaze-value">0</span></div>
                    <div>Respond: <span id="respondDecisions" class="gaze-value">0</span></div>
                    <div>Minimal: <span id="minimalDecisions" class="gaze-value">0</span></div>
                </div>
            </div>
        </div>

        <div class="panel">
            <h2>⚡ Pipeline Timing</h2>

            <div class="metrics">
                <h4>Latest Response Times:</h4>
                <div>Intent Classification: <span id="intentClassificationTime" class="gaze-value">0ms</span></div>
                <div>STT → Processing: <span id="sttToProcessing" class="ultra-fast-value">0ms</span></div>
                <div>Processing Time: <span id="processingTime" class="ultra-fast-value">0ms</span></div>
                <div>Processing → TTS: <span id="processingToTTS" class="ultra-fast-value">0ms</span></div>
                <div>Total Pipeline: <span id="totalPipeline" class="ultra-fast-value">0ms</span></div>
            </div>

            <div style="margin-top: 15px;">
                <h3>🚀 Processing Strategy</h3>
                <div id="processingStrategy" class="layer ultra-fast">
                    ⚡ Ultra-Fast Pattern Matching Ready
                </div>
                <div id="fallbackStrategy" class="layer inactive">
                    🧠 Enhanced LLM Fallback Ready
                </div>
                <div id="gazeIntegration" class="layer inactive">
                    👁️ Multi-Modal Integration Ready
                </div>
            </div>

            <div style="margin-top: 20px; font-size: 12px; opacity: 0.7;">
                <h4>🧠 Multi-Modal Features:</h4>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    <li>Real-time gaze state detection</li>
                    <li>Intent matrix: gaze + voice → action</li>
                    <li>Context-aware TTS responses</li>
                    <li>Natural "thinking aloud" filtering</li>
                    <li>Performance preservation</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let sessionStartTime = new Date();
        let isListening = false;
        let currentGazeState = 'system_disabled';

        function updateSessionDuration() {
            const now = new Date();
            const duration = Math.floor((now - sessionStartTime) / 1000);
            const minutes = Math.floor(duration / 60);
            const seconds = duration % 60;
            document.getElementById('sessionDuration').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }

        setInterval(updateSessionDuration, 1000);

        function startListening() {
            socket.emit('start_listening');
            document.getElementById('startListening').disabled = true;
            document.getElementById('stopListening').disabled = false;
            document.getElementById('status').className = 'status listening';
            document.getElementById('status').textContent = 'Status: Gaze-Integrated Listening Active 🧠⚡';
            isListening = true;
        }

        function stopListening() {
            socket.emit('stop_listening');
            document.getElementById('startListening').disabled = false;
            document.getElementById('stopListening').disabled = true;
            document.getElementById('status').className = 'status idle';
            document.getElementById('status').textContent = 'Status: Listening Stopped';
            isListening = false;
        }

        function updateGazeIndicator(gazeState, confidence) {
            const indicator = document.getElementById('gazeIndicator');
            let className = 'gaze-indicator ';
            let text = '';

            switch(gazeState) {
                case 'at_screen':
                    className += 'gaze-at-screen gaze-active-animation';
                    text = '👀 LOOKING AT SCREEN';
                    break;
                case 'away':
                    className += 'gaze-looking-away';
                    text = '👁️ LOOKING AWAY';
                    break;
                case 'uncertain':
                    className += 'gaze-uncertain';
                    text = '🤔 UNCERTAIN GAZE';
                    break;
                case 'no_face':
                    className += 'gaze-uncertain';
                    text = '❓ NO FACE DETECTED';
                    break;
                default:
                    className += 'gaze-disabled';
                    text = '🔇 GAZE DETECTION OFF';
            }

            indicator.className = className;
            indicator.textContent = text;
            currentGazeState = gazeState;
        }

        function addMessage(type, text, timestamp, extra = {}) {
            const chatArea = document.getElementById('chatArea');
            const messageDiv = document.createElement('div');

            let className = 'message ';
            let prefix = '';

            if (type === 'user') {
                className += 'user-message';
                prefix = '👤';
            } else if (type === 'ai') {
                className += 'ai-message';
                prefix = '🤖';
            } else if (type === 'ultra-fast') {
                className += 'ultra-fast-message';
                prefix = '⚡';
            } else if (type === 'ignored') {
                className += 'ignored-message';
                prefix = '🔇 IGNORED';
            } else if (type === 'minimal') {
                className += 'minimal-message';
                prefix = '🔹 MINIMAL';
            } else if (type === 'blocked') {
                className += 'blocked-message';
                prefix = '🔇 BLOCKED';
            }

            messageDiv.className = className;
            let content = `${prefix} ${text}`;

            if (extra.processing_time && extra.processing_time < 100) {
                content += ` <small style="color: #FFEB3B;">[⚡${extra.processing_time}ms]</small>`;
            } else if (extra.processing_time) {
                content += ` <small style="opacity: 0.7;">[${extra.processing_time}ms]</small>`;
            }

            if (extra.intent_decision) {
                const intentBadge = {
                    'execute': '✅',
                    'ignore': '🔇',
                    'respond': '💬',
                    'minimal': '🔹'
                }[extra.intent_decision] || '❔';
                content += ` <small style="opacity: 0.7;">[${intentBadge}${extra.intent_decision.toUpperCase()}]</small>`;
            }

            if (extra.method) {
                const methodBadge = extra.method === 'pattern' ? '⚡Pattern' : '🧠LLM';
                content += ` <small style="opacity: 0.7;">[${methodBadge}]</small>`;
            }

            if (extra.reason) {
                content += ` <br><small>(${extra.reason})</small>`;
            }

            if (timestamp) {
                content += ` <small style="opacity: 0.7;">[${timestamp}]</small>`;
            }

            messageDiv.innerHTML = content;
            chatArea.appendChild(messageDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }

        function updateMetrics(metrics) {
            for (const [key, value] of Object.entries(metrics)) {
                const element = document.getElementById(key);
                if (element) {
                    element.textContent = value;
                }
            }
        }

        function updatePipelineMetrics(pipeline) {
            document.getElementById('sttToProcessing').textContent = `${pipeline.stt_to_processing}ms`;
            document.getElementById('processingTime').textContent = `${pipeline.processing_time}ms`;
            document.getElementById('processingToTTS').textContent = `${pipeline.processing_to_tts}ms`;
            document.getElementById('totalPipeline').textContent = `${pipeline.total_pipeline}ms`;

            if (pipeline.intent_classification_time !== undefined) {
                document.getElementById('intentClassificationTime').textContent = `${pipeline.intent_classification_time}ms`;
            }

            // Update processing strategy indicators
            if (pipeline.method === 'pattern') {
                document.getElementById('processingStrategy').className = 'layer ultra-fast';
                document.getElementById('processingStrategy').textContent = '⚡ Ultra-Fast Pattern Match ACTIVE';
                document.getElementById('fallbackStrategy').className = 'layer inactive';
            } else {
                document.getElementById('processingStrategy').className = 'layer inactive';
                document.getElementById('fallbackStrategy').className = 'layer ultra-fast';
                document.getElementById('fallbackStrategy').textContent = '🧠 Enhanced LLM Fallback ACTIVE';
            }

            // Update gaze integration status
            if (pipeline.gaze_integrated) {
                document.getElementById('gazeIntegration').className = 'layer ultra-fast';
                document.getElementById('gazeIntegration').textContent = '👁️ Multi-Modal Integration ACTIVE';
            }

            // Visual feedback for ultra-fast responses
            if (pipeline.processing_time < 100) {
                const statusDiv = document.getElementById('status');
                statusDiv.classList.add('ultra-fast-processing');
                setTimeout(() => statusDiv.classList.remove('ultra-fast-processing'), 1000);
            }
        }

        // Socket event handlers
        socket.on('user_transcription', function(data) {
            addMessage('user', data.text, data.timestamp);
        });

        socket.on('ai_response', function(data) {
            addMessage('ai', data.text, data.timestamp, {
                processing_time: data.processing_time,
                generation_time: data.generation_time,
                intent_decision: data.intent_decision
            });
        });

        socket.on('ultra_fast_response', function(data) {
            addMessage('ultra-fast', data.text, data.timestamp, {
                processing_time: Math.round(data.processing_time),
                method: data.method,
                intent_decision: data.intent_decision
            });
        });

        socket.on('ignored_input', function(data) {
            addMessage('ignored', data.text, data.timestamp, {
                reason: data.reason,
                intent_decision: 'ignore'
            });
        });

        socket.on('minimal_response', function(data) {
            addMessage('minimal', data.text, data.timestamp, {
                intent_decision: 'minimal'
            });
        });

        socket.on('blocked_echo', function(data) {
            addMessage('blocked', data.text, data.timestamp, {
                reason: data.reason
            });
        });

        socket.on('gaze_state_update', function(data) {
            document.getElementById('gazeState').textContent = data.state.replace('_', ' ').toUpperCase();
            document.getElementById('gazeConfidence').textContent = data.confidence.toFixed(2);
            document.getElementById('lookingProbability').textContent = `${(data.looking_at_screen_probability * 100).toFixed(1)}%`;
            document.getElementById('faceDetected').textContent = data.face_detected ? 'Yes' : 'No';
            document.getElementById('stateDuration').textContent = `${data.duration.toFixed(1)}s`;

            updateGazeIndicator(data.state, data.confidence);
        });

        socket.on('metrics_update', function(data) {
            updateMetrics(data);
        });

        socket.on('pipeline_update', function(data) {
            updatePipelineMetrics(data);
        });

        socket.on('status_update', function(data) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = data.message;

            if (data.status === 'listening') {
                statusDiv.className = 'status listening';
            } else if (data.status === 'processing') {
                statusDiv.className = 'status processing';
            } else if (data.status === 'ultra-fast') {
                statusDiv.className = 'status ultra-fast';
            } else if (data.status === 'gaze-active') {
                statusDiv.className = 'status gaze-active';
            } else {
                statusDiv.className = 'status idle';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def text_detected(text):
    """Enhanced text processing with multi-modal gaze integration"""
    global performance_metrics, multi_modal_integration

    pipeline_start = time.time()

    # Thread-safe text processing
    with text_processing_lock:
        performance_metrics['total_transcriptions'] += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n🎤 Transcribed: '{text}' at {timestamp}")

        # Echo detection (preserve existing breakthrough logic)
        is_echo, reason, detection_data = echo_blocker.is_likely_echo(text, audio_file_path=None)

        if is_echo:
            performance_metrics['blocked_echoes'] += 1

            # Track echo detection layers
            layers = detection_data.get("final_decision", {}).get("detection_layers", {})
            if layers.get("time_content") and layers.get("voice_fingerprinting"):
                performance_metrics['combined_blocks'] += 1
            elif layers.get("voice_fingerprinting"):
                performance_metrics['voice_fingerprint_blocks'] += 1
            elif layers.get("time_content"):
                performance_metrics['time_content_blocks'] += 1

            print(f"🔇 BLOCKED ECHO: '{text}' - {reason}")
            socketio.emit('blocked_echo', {
                'text': text,
                'reason': reason,
                'timestamp': timestamp,
                'detection_layers': layers
            })
            return

        performance_metrics['passed_inputs'] += 1
        performance_metrics['perfect_captures'] += 1

        print(f"✅ PASSED: '{text}' - Human voice detected")
        socketio.emit('user_transcription', {
            'text': text,
            'timestamp': timestamp
        })

        # REVOLUTIONARY MULTI-MODAL INTEGRATION POINT
        intent_start_time = time.time()

        # Get intent classification from multi-modal system
        should_process, intent = multi_modal_integration.should_process_voice_input(text)
        intent_processing_time = (time.time() - intent_start_time) * 1000

        performance_metrics['gaze_filtered_inputs'] += 1
        performance_metrics['current_gaze_state'] = intent.gaze_state.value

        # Update intent decision metrics
        if intent.decision == IntentDecision.EXECUTE:
            performance_metrics['execute_decisions'] += 1
        elif intent.decision == IntentDecision.IGNORE:
            performance_metrics['ignore_decisions'] += 1
        elif intent.decision == IntentDecision.RESPOND:
            performance_metrics['respond_decisions'] += 1
        elif intent.decision == IntentDecision.MINIMAL:
            performance_metrics['minimal_decisions'] += 1

        # Emit real-time gaze state update
        gaze_context = multi_modal_integration.get_current_gaze_context()
        socketio.emit('gaze_state_update', {
            'state': gaze_context['state'],
            'confidence': gaze_context['confidence'],
            'looking_at_screen_probability': gaze_context['looking_at_screen_probability'],
            'face_detected': gaze_context['face_detected'],
            'duration': gaze_context.get('duration', 0.0)
        })

        # Handle ignored inputs (revolutionary breakthrough)
        if not should_process:
            print(f"🔇 IGNORING INPUT: '{text}' - {intent.reasoning}")
            socketio.emit('ignored_input', {
                'text': text,
                'reason': intent.reasoning,
                'gaze_state': intent.gaze_state.value,
                'timestamp': timestamp
            })
            return

        # Get response strategy based on intent
        response_strategy = multi_modal_integration.get_response_strategy(intent)

        # Continue with voice processing
        processing_start = time.time()
        stt_to_processing_time = (processing_start - pipeline_start) * 1000

        try:
            # Step 1: Try ultra-fast processing first
            print("⚡ Attempting ultra-fast processing...")
            ultra_fast_response = ultra_fast_automation.process_voice_command(text, execute=True)

            processing_end = time.time()
            processing_time = (processing_end - processing_start) * 1000

            # Check if ultra-fast processing was successful
            if (ultra_fast_response.method_used == "pattern" and
                ultra_fast_response.confidence > 0.5 and
                ultra_fast_response.intent_type != "unknown"):

                # Ultra-fast success!
                performance_metrics['ultra_fast_responses'] += 1
                performance_metrics['pattern_hits'] += 1

                ai_response = ultra_fast_response.conversational_text
                method_used = "ultra-fast-pattern"

                print(f"⚡ ULTRA-FAST SUCCESS: {processing_time:.0f}ms - {ai_response}")

                # Emit appropriate response based on intent
                if intent.decision == IntentDecision.MINIMAL:
                    # Minimal response
                    minimal_response = "Noted." if "thank" not in text.lower() else "You're welcome."
                    socketio.emit('minimal_response', {
                        'text': minimal_response,
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'intent_decision': intent.decision.value,
                        'original_response': ai_response
                    })
                    ai_response = minimal_response
                else:
                    # Full or conversational response
                    socketio.emit('ultra_fast_response', {
                        'text': ai_response,
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'processing_time': processing_time,
                        'method': 'pattern',
                        'intent': ultra_fast_response.intent_type,
                        'confidence': ultra_fast_response.confidence,
                        'intent_decision': intent.decision.value
                    })

            else:
                # Fall back to enhanced automation for complex commands
                print(f"🧠 Falling back to enhanced automation (reason: {ultra_fast_response.method_used})")
                performance_metrics['enhanced_fallbacks'] += 1

                enhanced_result = enhanced_automation.execute_voice_command(text)

                processing_end = time.time()
                processing_time = (processing_end - processing_start) * 1000

                if enhanced_result['automation_performed']:
                    # Enhanced automation handled it
                    if enhanced_result['success']:
                        ai_response = f"✅ {enhanced_result['message']}"
                    else:
                        ai_response = f"❌ {enhanced_result['message']}"
                    method_used = "enhanced-automation"

                    socketio.emit('automation_executed', {
                        'text': text,
                        'automation_result': enhanced_result,
                        'timestamp': timestamp,
                        'intent_decision': intent.decision.value
                    })
                else:
                    # Regular conversation response
                    ai_response = ultra_fast_response.conversational_text
                    method_used = "enhanced-fallback"

                    # Handle minimal responses
                    if intent.decision == IntentDecision.MINIMAL:
                        ai_response = "I see." if "?" not in text else "Mmm-hmm."
                        socketio.emit('minimal_response', {
                            'text': ai_response,
                            'timestamp': datetime.now().strftime("%H:%M:%S"),
                            'intent_decision': intent.decision.value
                        })

                print(f"🧠 ENHANCED FALLBACK: {processing_time:.0f}ms - {ai_response}")

        except Exception as e:
            print(f"❌ Processing error: {e}")
            # Final fallback to simple response
            if intent.decision == IntentDecision.MINIMAL:
                ai_response = "Okay."
            else:
                ai_response = "I heard you, but I'm having trouble processing that right now."
            method_used = "error-fallback"
            processing_end = time.time()
            processing_time = (processing_end - processing_start) * 1000

        performance_metrics['ai_responses'] += 1

        # TTS generation with intent-based customization
        tts_start = time.time()
        ai_audio_path = record_ai_voice(ai_response, response_strategy)
        echo_blocker.set_ai_response(ai_response, speaking_duration=3.0)
        tts_end = time.time()

        processing_to_tts_time = (tts_end - processing_end) * 1000
        total_pipeline_time = (tts_end - pipeline_start) * 1000

        # Update performance metrics
        update_pipeline_metrics(
            stt_to_processing_time,
            processing_time,
            processing_to_tts_time,
            total_pipeline_time,
            intent_processing_time
        )

        # Update running average processing time
        times = performance_metrics['pipeline_times']['processing_time']
        if times:
            performance_metrics['average_processing_time'] = sum(times) / len(times)
            performance_metrics['fastest_response'] = min(performance_metrics['fastest_response'], processing_time)
            performance_metrics['slowest_response'] = max(performance_metrics['slowest_response'], processing_time)

        # Emit AI response (only if not already emitted as minimal/ignored)
        if intent.decision not in [IntentDecision.MINIMAL, IntentDecision.IGNORE]:
            socketio.emit('ai_response', {
                'text': ai_response,
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'processing_time': total_pipeline_time,
                'generation_time': processing_time,
                'ai_audio_file': ai_audio_path,
                'method': method_used,
                'intent_decision': intent.decision.value
            })

        # Emit pipeline metrics
        socketio.emit('pipeline_update', {
            'stt_to_processing': round(stt_to_processing_time),
            'processing_time': round(processing_time),
            'processing_to_tts': round(processing_to_tts_time),
            'total_pipeline': round(total_pipeline_time),
            'intent_classification_time': round(intent_processing_time),
            'method': method_used.split('-')[0],
            'gaze_integrated': True
        })

        print(f"🤖 AI Response: '{ai_response}' (Pipeline: {total_pipeline_time:.0f}ms, Intent: {intent.decision.value})")

        # Update and emit metrics
        total = performance_metrics['total_transcriptions']
        success_rate = (performance_metrics['passed_inputs'] / total * 100) if total > 0 else 100
        pattern_hit_rate = (performance_metrics['pattern_hits'] / performance_metrics['passed_inputs'] * 100) if performance_metrics['passed_inputs'] > 0 else 0

        socketio.emit('metrics_update', {
            'totalTranscriptions': performance_metrics['total_transcriptions'],
            'ultraFastResponses': performance_metrics['ultra_fast_responses'],
            'enhancedFallbacks': performance_metrics['enhanced_fallbacks'],
            'gazeFilteredInputs': performance_metrics['gaze_filtered_inputs'],
            'executeDecisions': performance_metrics['execute_decisions'],
            'ignoreDecisions': performance_metrics['ignore_decisions'],
            'respondDecisions': performance_metrics['respond_decisions'],
            'minimalDecisions': performance_metrics['minimal_decisions'],
            'stateChanges': performance_metrics['gaze_state_changes'],
            'patternHitRate': f"{pattern_hit_rate:.1f}%",
            'avgProcessingTime': f"{performance_metrics['average_processing_time']:.0f}ms",
            'fastestResponse': f"{performance_metrics['fastest_response']:.0f}ms" if performance_metrics['fastest_response'] != float('inf') else "∞ms",
            'blockedEchoes': performance_metrics['blocked_echoes']
        })

@socketio.on('start_listening')
def start_listening():
    global recorder, always_listening_active, multi_modal_integration

    # Prevent multiple listening sessions
    if always_listening_active:
        print("⚠️  Already listening - ignoring duplicate start request")
        emit('status_update', {
            'status': 'listening',
            'message': 'Already Listening - Gaze-Integrated Mode 🧠⚡'
        })
        return

    if recorder is None:
        print("🎤 Initializing RealtimeSTT with calibrated settings...")

        # Load saved calibration settings
        config = voice_calibration.get_recorder_config()
        print(f"📊 Using calibrated settings from previous sessions")

        recorder = AudioToTextRecorder(
            on_realtime_transcription_update=lambda x: None,
            on_realtime_transcription_stabilized=lambda x: None,
            **config  # Use all saved calibration settings
        )

    print("🧠 Starting Gaze-Integrated Ultra-Fast Listening mode")
    always_listening_active = True
    performance_metrics['gaze_detection_active'] = multi_modal_integration.integration_active

    emit('status_update', {
        'status': 'gaze-active',
        'message': 'Gaze-Integrated Listening Active 🧠⚡'
    })

    # Start listening in separate thread
    def listen_continuously():
        global always_listening_active
        while always_listening_active:
            try:
                # Use RealtimeSTT correctly - just call .text() directly
                text = recorder.text()
                if text and text.strip():
                    text_detected(text.strip())
                else:
                    time.sleep(0.1)  # Brief pause if no text
            except Exception as e:
                print(f"❌ Recording error: {e}")
                socketio.emit('status_update', {
                    'status': 'error',
                    'message': f'Recording Error: {e}'
                })
                break

    threading.Thread(target=listen_continuously, daemon=True).start()

    # Start gaze state update thread
    def update_gaze_state_continuously():
        while always_listening_active:
            try:
                gaze_context = multi_modal_integration.get_current_gaze_context()
                socketio.emit('gaze_state_update', {
                    'state': gaze_context['state'],
                    'confidence': gaze_context['confidence'],
                    'looking_at_screen_probability': gaze_context['looking_at_screen_probability'],
                    'face_detected': gaze_context['face_detected'],
                    'duration': gaze_context.get('duration', 0.0)
                })
                time.sleep(0.5)  # Update every 500ms
            except Exception as e:
                print(f"⚠️  Gaze state update error: {e}")
                time.sleep(1.0)

    threading.Thread(target=update_gaze_state_continuously, daemon=True).start()

@socketio.on('stop_listening')
def stop_listening():
    global always_listening_active, recorder
    always_listening_active = False
    performance_metrics['gaze_detection_active'] = False

    # Clean shutdown of recorder
    if recorder:
        try:
            recorder.shutdown()
        except:
            pass
        recorder = None

    emit('status_update', {
        'status': 'idle',
        'message': 'Listening Stopped'
    })

    print("🛑 Gaze-Integrated Listening stopped")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection - CRITICAL for proper cleanup"""
    global always_listening_active, recorder, multi_modal_integration

    print("🔌 Client disconnected - cleaning up gaze-integrated voice interface")

    # Stop all voice processing
    always_listening_active = False

    # Clean shutdown of recorder
    if recorder:
        try:
            recorder.shutdown()
        except Exception as e:
            print(f"⚠️  Error shutting down recorder: {e}")
        recorder = None

    print("✅ Gaze-integrated voice interface cleanup complete")

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("🔌 Client connected to gaze-integrated ultra-fast voice interface")

    emit('status_update', {
        'status': 'idle',
        'message': 'Connected - Ready for Multi-Modal Processing 🧠⚡'
    })

def main():
    global echo_blocker, ultra_fast_automation, enhanced_automation, voice_calibration, session_dir, multi_modal_integration

    print("🧠⚡ GAZE-INTEGRATED ULTRA-FAST VOICE INTERFACE 2025")
    print("=" * 90)
    print("✅ Real-time Gaze Detection Integration")
    print("✅ Revolutionary Multi-Modal Intent Matrix")
    print("✅ Ultra-Fast Pattern Matching (Primary)")
    print("✅ Enhanced LLM Automation (Fallback)")
    print("✅ Context-Aware TTS Responses")
    print("✅ Complete Pipeline Performance Monitoring")
    print("✅ Natural 'Thinking Aloud' Filtering")
    print("✅ Production-Ready Web Interface with Gaze Display")
    print("=" * 90)

    # Setup session directory
    session_dir = setup_session_directory()

    # Initialize all components
    echo_blocker = EnhancedEchoBlocker(enable_voice_fingerprinting=True)
    ultra_fast_automation = UltraFastVoiceAutomation()  # Primary processor
    enhanced_automation = EnhancedVoiceAutomation()    # Fallback processor
    voice_calibration = VoiceCalibrationManager()

    # Initialize multi-modal integration system
    print("🧠 Initializing Multi-Modal Voice Integration...")
    multi_modal_integration = MultiModalVoiceIntegration(enable_gaze_detection=True)
    integration_success = multi_modal_integration.initialize()

    print(f"🧠 Enhanced Echo Blocker initialized")
    print(f"🎵 Voice Fingerprinting: {'ENABLED' if echo_blocker.enable_voice_fingerprinting else 'DISABLED'}")
    print(f"⚡ Ultra-Fast Automation initialized (Primary)")
    print(f"🚀 Enhanced Voice Automation initialized (Fallback)")
    print(f"🦙 Semantic Understanding: {'ENABLED (Ollama)' if enhanced_automation.automation_stats['semantic_parser_available'] else 'DISABLED (Regex fallback)'}")
    print(f"🧠 Multi-Modal Integration: {'ACTIVE' if integration_success else 'FALLBACK (Voice-Only)'}")

    # Test systems
    test_response = ultra_fast_automation.process_voice_command("Hi there!", execute=False)
    print(f"⚡ Ultra-Fast Test: {test_response.processing_time_ms:.0f}ms - '{test_response.conversational_text}'")

    if integration_success:
        print("🧪 Running Multi-Modal Integration Test...")
        integration_test_results = multi_modal_integration.test_integration_pipeline()
        print(f"✅ Integration test complete - Average processing: {integration_test_results['average_processing_time']:.1f}ms")

    # Start server
    print(f"\n🌐 Starting Gaze-Integrated Ultra-Fast Voice Interface...")
    print(f"🔗 Access at: http://localhost:8087")
    print(f"📁 Session files: {session_dir}")
    print(f"🧠 Strategy: Multi-modal gaze + voice integration with ultra-fast processing")

    try:
        socketio.run(app, host='0.0.0.0', port=8087, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Gaze-Integrated Ultra-Fast Voice Interface")

        # Shutdown multi-modal integration
        if multi_modal_integration:
            multi_modal_integration.shutdown()

        # Print final statistics
        echo_stats = echo_blocker.get_stats()
        ultra_fast_stats = ultra_fast_automation.get_performance_stats()
        enhanced_stats = enhanced_automation.get_automation_stats()
        integration_stats = multi_modal_integration.get_integration_metrics() if multi_modal_integration else {}

        print("\n📊 FINAL STATISTICS:")
        print(f"  Echo Detection:")
        print(f"    Total Checks: {echo_stats['detection_stats']['total_checks']}")
        print(f"    Blocked Echoes: {performance_metrics['blocked_echoes']}")
        print(f"    Perfect Captures: {performance_metrics['perfect_captures']}")

        print(f"\n  Ultra-Fast Processing:")
        print(f"    Ultra-Fast Responses: {performance_metrics['ultra_fast_responses']}")
        print(f"    Enhanced Fallbacks: {performance_metrics['enhanced_fallbacks']}")
        print(f"    Pattern Hit Rate: {ultra_fast_stats['pattern_efficiency']:.1f}%")
        print(f"    Average Processing: {performance_metrics['average_processing_time']:.0f}ms")
        print(f"    Fastest Response: {performance_metrics['fastest_response']:.0f}ms")

        if integration_stats:
            print(f"\n  Multi-Modal Integration:")
            print(f"    Gaze-Filtered Inputs: {integration_stats['total_voice_inputs']}")
            print(f"    Execute Decisions: {integration_stats['execute_decisions']} ({integration_stats.get('execute_percentage', 0):.1f}%)")
            print(f"    Ignore Decisions: {integration_stats['ignore_decisions']} ({integration_stats.get('ignore_percentage', 0):.1f}%)")
            print(f"    Respond Decisions: {integration_stats['respond_decisions']} ({integration_stats.get('respond_percentage', 0):.1f}%)")
            print(f"    Minimal Decisions: {integration_stats['minimal_decisions']} ({integration_stats.get('minimal_percentage', 0):.1f}%)")
            print(f"    Gaze State Changes: {integration_stats['gaze_state_changes']}")
            print(f"    Integration Active: {'YES' if integration_stats['system_active'] else 'NO'}")
            print(f"    System Failure Rate: {integration_stats.get('failure_rate', 0):.1f}%")

        print(f"\n  Enhanced Automation:")
        print(f"    Total Commands: {enhanced_stats['total_commands']}")
        print(f"    Success Rate: {enhanced_stats['success_rate']}")
        print(f"    Semantic Parser: {'Available' if enhanced_stats['semantic_parser_available'] else 'Unavailable'}")

if __name__ == "__main__":
    main()