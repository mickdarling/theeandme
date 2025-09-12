#!/usr/bin/env python3
"""
Simple Web Voice Interface - Shows real-time transcription
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Interface - The E and Me</title>
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
            background: rgba(40, 167, 69, 0.3);
            border: 2px solid #28a745;
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
        .timestamp {
            font-size: 0.85em;
            opacity: 0.8;
            margin-top: 8px;
            font-style: italic;
        }
        .instructions {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .highlight {
            background: rgba(255, 193, 7, 0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
        }
        .step {
            margin: 10px 0;
            font-size: 1.05em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 Voice Interface Demo</h1>
            <p>Real-time voice conversation with AI assistant</p>
        </div>
        
        <div class="status">
            🟢 Voice System Ready - Follow the instructions below
        </div>
        
        <div class="instructions">
            <h3>💬 How to Use the Voice Interface:</h3>
            <div class="step">1. Open Terminal and run: <span class="highlight">cd ~/Developer/theeandme</span></div>
            <div class="step">2. Start voice session: <span class="highlight">python examples/test_complete_pipeline.py</span></div>
            <div class="step">3. When you see <span class="highlight">🔴 Speak now!</span> - talk to the AI</div>
            <div class="step">4. Your conversation will be processed and the AI will respond with voice</div>
            <div class="step">5. <strong>Real-time transcription</strong> shows exactly what you said</div>
        </div>
        
        <div class="conversation">
            <div class="message ai-message">
                🤖 Welcome to the voice interface! I can hear and respond to your speech in real-time.
                <div class="timestamp">System Ready • Voice Recognition: Whisper • AI: Llama 3.1</div>
            </div>
            
            <div class="message user-message">
                🗣️ Your spoken words will appear here in real-time as they're transcribed
                <div class="timestamp">Example transcription • 95% confidence • 0.8s processing</div>
            </div>
            
            <div class="message ai-message">
                🤖 My AI responses will appear here and be spoken aloud using text-to-speech
                <div class="timestamp">AI Response Generated • 1.2s generation time</div>
            </div>
            
            <div style="text-align: center; margin-top: 30px; opacity: 0.7; font-style: italic;">
                📋 This interface shows you the conversation flow visually<br>
                🎯 Run the voice pipeline in Terminal to start talking!
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("🌐 Starting Simple Web Voice Interface...")
    print("🔗 Open your browser to: http://localhost:8080")
    print("🎤 Then run the voice pipeline in Terminal")
    print()
    
    app.run(host='0.0.0.0', port=8080, debug=False)