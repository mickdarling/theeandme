# The E and Me - Always-On Voice Interface System

An always-on, context-aware voice interface system for Mac Studios using camera-based attention detection, voice activity detection, and local LLM processing.

## 🎯 Project Overview

This system creates an intelligent voice interface that:
- **No wake words required** - Uses camera-based attention detection to determine which Mac Studio should respond
- **Context-aware routing** - Intelligently routes conversations based on visual cues like which direction you're facing
- **Local processing** - All voice recognition and LLM processing happens locally for privacy
- **Multi-Mac coordination** - Seamlessly coordinates between multiple Mac Studios in your workspace

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│ USER INTERACTION LAYER                          │
├─────────────────────────────────────────────────┤
│ Vision Context (Camera) + Voice Activity (Mic)  │
├─────────────────────────────────────────────────┤
│ PROCESSING LAYER                                │
│ • Person Detection (Apple Vision Framework)     │
│ • Voice Activity Detection (Silero VAD)         │
│ • Speech Recognition (OpenAI Whisper)           │
│ • LLM Processing (Ollama/LM Studio)             │
│ • Audio Synthesis (System TTS)                  │
├─────────────────────────────────────────────────┤
│ ROUTING & COORDINATION LAYER                    │
│ • Multi-Mac Communication (Network Protocol)    │
│ • Audio Routing (System Integration)            │
│ • Session Management                            │
├─────────────────────────────────────────────────┤
│ HARDWARE LAYER                                  │
│ Mac Studio M1 Max (32GB) + Mac Studio M4 Max (128GB)│
└─────────────────────────────────────────────────┘
```

## 🚀 Key Features

### Context-Aware Activation
- **Face Detection**: Uses Apple Vision Framework for real-time person detection
- **Attention Detection**: Determines which Mac Studio you're facing
- **Voice Activity Detection**: Neural network-based VAD (Silero) for accurate speech detection
- **Smart Coordination**: Automatic handoff between Mac Studios based on context

### Local AI Processing
- **Speech-to-Text**: OpenAI Whisper running locally
- **LLM Integration**: Support for Ollama and LM Studio
- **Text-to-Speech**: System TTS for responses
- **Privacy First**: No cloud dependencies, all processing local

### Multi-Mac Coordination
- **Intelligent Routing**: Conversation context preserved across devices
- **Session Management**: Seamless handoff between Mac Studios
- **Network Protocol**: Secure communication between devices
- **Resource Optimization**: Automatic load balancing

## 📁 Project Structure

```
theeandme/
├── src/
│   ├── core/           # Main system orchestration
│   ├── audio/          # Voice Activity Detection, STT, TTS
│   ├── vision/         # Camera-based attention detection
│   ├── llm/            # Local LLM integration (Ollama/LM Studio)
│   ├── coordination/   # Multi-Mac communication
│   └── utils/          # Shared utilities
├── config/             # Configuration files
├── examples/           # Usage examples and demos
├── docs/               # Documentation
└── tests/              # Test suites
```

## 💻 Hardware Requirements

### Mac Studio M1 Max (32GB RAM)
- **Optimal Models**: Llama 3.1 8B, Mistral 7B, DeepSeek Coder 6.7B
- **Performance**: ~15 tokens/sec for 8B models
- **Real-time**: Excellent for voice interface applications

### Mac Studio M4 Max (128GB RAM)
- **Optimal Models**: Llama 3.1 70B, DeepSeek R1 32B
- **Performance**: ~8 tokens/sec for 70B models
- **Capability**: Can handle largest open-source models

## 🛠️ Technology Stack

- **Vision Processing**: Apple Vision Framework + OpenCV
- **Audio Processing**: Silero VAD + OpenAI Whisper
- **LLM Integration**: Ollama / LM Studio with local models
- **Network Communication**: TCP/IP with secure coordination protocol
- **Languages**: Python for AI/ML, Swift for Vision Framework
- **Platform**: macOS optimized for Apple Silicon

## 🔧 Installation & Setup

### Prerequisites
```bash
# Install Python dependencies
pip install torch torchaudio openai-whisper opencv-python pyaudio numpy requests

# Install Whisper for better Mac performance
brew install ffmpeg
pip install whisper-cpp-python

# Install audio libraries
brew install portaudio
pip install sounddevice
```

### LLM Setup (Choose one)

#### Option A: Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
ollama pull mistral:7b
```

#### Option B: LM Studio
- Download from https://lmstudio.ai
- Install via GUI and download models

### Network Configuration
- Ensure both Mac Studios are on same network
- Configure static IPs or note current IPs
- Open firewall port 8888 for coordination

## 🏁 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/mickdarling/theeandme.git
   cd theeandme
   git checkout develop
   ```

2. **Install dependencies**
   ```bash
   npm install  # For project management
   pip install -r requirements.txt  # AI/ML dependencies
   ```

3. **Configure system**
   ```bash
   cp config/config.example.json config/config.json
   # Edit config.json with your Mac Studio IPs and preferences
   ```

4. **Start the system**
   ```bash
   python src/main.py
   ```

## 📋 Development Workflow

This project uses Git Flow branching strategy:

- **main**: Production-ready releases
- **develop**: Integration branch for features
- **feature/**: Feature development branches off develop
- **hotfix/**: Emergency fixes branch off main

### Contributing
1. Create feature branch: `git checkout -b feature/your-feature-name develop`
2. Develop and test your feature
3. Create PR to develop branch
4. After review and testing, changes are merged to develop
5. Releases are merged from develop to main

## 🔒 Security & Privacy

- **Local Processing**: All voice data processed locally
- **Network Security**: Encrypted communication between Mac Studios
- **No Cloud Dependencies**: Complete offline capability
- **Privacy Controls**: User control over all data and processing

## 📊 Performance Expectations

### Mac Studio M1 Max
- **Face Detection**: 30+ FPS real-time
- **Voice Processing**: <2 second response times
- **LLM Models**: 15+ tokens/sec for 8B models

### Mac Studio M4 Max
- **Face Detection**: 60+ FPS real-time
- **Voice Processing**: <1.5 second response times
- **LLM Models**: 8+ tokens/sec for 70B models

## 🤝 Community & Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Join conversations in GitHub Discussions
- **Documentation**: Comprehensive docs in `/docs` directory

## 📄 License

This project is licensed under the ISC License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI Whisper**: Local speech recognition
- **Silero VAD**: Advanced voice activity detection
- **Apple Vision Framework**: Real-time person detection
- **Ollama/LM Studio**: Local LLM deployment
- **DollhouseMCP**: AI agent orchestration system

---

**Built with ❤️ for private, intelligent voice interaction**

🤖 Generated with [Claude Code](https://claude.ai/code)