# Voice Interface Examples

This directory contains various implementations and tests for the voice interface system.

## Directory Structure

### 📱 Web Interfaces (`web-interfaces/`)
Production-ready web-based voice interfaces:

- **`simple_transcription_app.py`** ⭐ - Main dual-mode web interface with echo cancellation
  - Click-to-record mode: Manual 5-second recording
  - Always-listening mode: Continuous voice detection with feedback loop prevention
  - **Echo cancellation features**: Audio ducking, volume gating, adaptive timeouts
  - Usage: `python web-interfaces/simple_transcription_app.py`
  - Access: http://localhost:8080

- **`echo_cancelled_voice_app.py`** - Enhanced version with comprehensive echo prevention
  - Advanced echo prevention system with visual indicators
  - Multiple feedback loop prevention strategies
  - Production-ready always-listening mode
  - Usage: `python web-interfaces/echo_cancelled_voice_app.py`

### 🧪 Testing (`testing/`)
Development and testing utilities:

- **`test_complete_pipeline.py`** - Full pipeline validation (Voice → STT → LLM → TTS)
- **`test_basic_setup.py`** - Basic system component verification
- **`test_audio.py`** - Audio system testing and device enumeration
- **`test_voice_simple.py`** - Simple VAD + STT testing
- **`test_interactive_voice.py`** - Interactive voice demo script
- **`test_mic_levels.py`** - Microphone level monitoring
- **`test_voice_debug.py`** - Voice processing debugging tools
- **`test_basic_audio.py`** - Basic audio recording tests
- **`test_llm.py`** - Local LLM connection testing
- **`check_dependencies.py`** - System dependency verification

### 📦 Archive (`archive/`)
Experimental and legacy implementations:

- **`transcription_web_app.py`** - Initial web interface attempt
- **`web_voice_interface.py`** - Complex SocketIO implementation
- **`simple_web_voice.py`** - Static web demo page

## Quick Start

### 1. Production Voice Interface (Recommended)
```bash
# Ensure Ollama is running
ollama serve

# Start the main web interface with echo cancellation
python web-interfaces/simple_transcription_app.py
```
Then open http://localhost:8080

### 2. Test System Components
```bash
# Check if all dependencies are installed
python testing/check_dependencies.py

# Test the complete pipeline
python testing/test_complete_pipeline.py

# Test just audio recording
python testing/test_basic_audio.py
```

## Technical Specifications

### Current Working Configuration
```json
{
  "microphone": "Live Streamer CAM 513 (Device #2)",
  "speech_recognition": "Whisper base model",
  "llm_backend": "Ollama Llama 3.1 8B",
  "voice_synthesis": "macOS built-in TTS",
  "vad_system": "Silero VAD (neural network)",
  "web_interface": "Flask + SocketIO on localhost:8080",
  "audio_sample_rate": "16kHz",
  "vad_threshold": "0.8 confidence",
  "recording_duration": "5s (click mode), 3s (always-listening)"
}
```

### Performance Metrics Achieved
- **Speech Recognition**: ~0.5-3 seconds processing time
- **LLM Response**: ~1-2 seconds generation time  
- **End-to-End**: ~2-5 seconds total interaction time
- **VAD Response**: Real-time voice detection (<500ms)

## Echo Cancellation Features ✅

The main interface (`simple_transcription_app.py`) includes production-ready echo cancellation:

1. **Audio Ducking**: Microphone muted during AI speech playback
2. **Adaptive Timeout**: 3-second silence period after AI responses
3. **Volume Gating**: Ignores very quiet audio (likely echo/feedback)
4. **Speaking State Tracking**: Prevents recording during TTS output

This **eliminates infinite feedback loops** that were the main issue in always-listening mode.

## Development Notes

- **Major Milestone**: Web-based voice interface with real-time conversation display ✅
- **Critical Fix**: Echo cancellation prevents production feedback loops ✅
- **User Experience**: Perfect visual feedback with confidence scores and timing ✅
- **Production Ready**: Always-listening mode now safe for deployment ✅

## Next Development Priorities

1. ✅ **Echo Cancellation** - COMPLETED
2. Repository cleanup and organization - IN PROGRESS
3. Enhanced mobile responsiveness
4. Conversation persistence and history
5. Multi-user voice recognition
6. Integration with existing pipeline components