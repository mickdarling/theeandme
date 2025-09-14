#!/bin/bash

# Startup script for Integrated Ultra-Fast Voice Interface 2025
# This script handles dependencies and starts the integrated voice system

echo "🚀 INTEGRATED ULTRA-FAST VOICE INTERFACE 2025"
echo "=============================================="

# Check if we're in the right directory
if [[ ! -f "integrated_ultra_fast_voice_interface.py" ]]; then
    echo "❌ Error: integrated_ultra_fast_voice_interface.py not found"
    echo "Please run this script from the web-interfaces directory"
    exit 1
fi

echo "✅ Found integrated voice interface file"

# Check Python availability
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✅ Python 3 available"

# Check if Ollama is running (optional but recommended)
if command -v curl &> /dev/null; then
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "✅ Ollama service detected (enhanced features available)"
    else
        echo "⚠️  Ollama service not detected (will use basic features)"
        echo "   To enable enhanced features, start Ollama: 'ollama serve'"
    fi
fi

# Check for required dependencies
echo "📦 Checking dependencies..."

MISSING_DEPS=()

# Check for key Python packages
python3 -c "import flask, flask_socketio" 2>/dev/null || MISSING_DEPS+=("flask flask-socketio")
python3 -c "import numpy" 2>/dev/null || MISSING_DEPS+=("numpy")

# Check for RealtimeSTT (in src directory)
if [[ ! -d "../../src/RealtimeSTT" ]]; then
    echo "⚠️  RealtimeSTT not found in src directory"
    echo "   Make sure you're running from the correct project structure"
fi

if [[ ${#MISSING_DEPS[@]} -gt 0 ]]; then
    echo "❌ Missing dependencies: ${MISSING_DEPS[*]}"
    echo "Install with: pip install ${MISSING_DEPS[*]}"
    exit 1
fi

echo "✅ All dependencies available"

# Check for microphone permissions (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🎤 Note: Microphone permissions may be required"
    echo "   Grant permissions when prompted by macOS"
fi

# Create session directory if it doesn't exist
mkdir -p sessions
echo "📁 Session directory ready"

echo ""
echo "🌐 Starting Integrated Ultra-Fast Voice Interface..."
echo "📱 Access the interface at: http://localhost:8087"
echo "⚡ Features: Ultra-fast pattern matching + Enhanced fallback"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Start the integrated voice interface
python3 integrated_ultra_fast_voice_interface.py

echo ""
echo "🛑 Integrated Voice Interface stopped"
echo "📊 Check session files in the sessions directory for audio recordings"