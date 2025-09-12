# The E and Me - Setup Guide

## Prerequisites

### System Requirements
- **macOS**: 12.0+ (Monterey or later)
- **Apple Silicon**: M1 or newer (for optimal performance)
- **RAM**: 32GB+ recommended for larger models
- **Python**: 3.9+
- **Node.js**: 18+ (for package management)

### Hardware Setup
- **Mac Studio M1 Max (32GB)**: Optimal for 8B parameter models
- **Mac Studio M4 Max (128GB)**: Can handle 70B parameter models
- **Built-in cameras and microphones**: Used for vision and audio processing

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/mickdarling/theeandme.git
cd theeandme
git checkout develop
```

### 2. Install Python Dependencies
```bash
# Install Python requirements
pip install -r requirements.txt

# Or use npm script
npm run setup
```

### 3. Configure Local LLM Service

#### Option A: LM Studio (GUI - Recommended)
LM Studio is already installed on your system.

1. **Start LM Studio**
   ```bash
   open "/Applications/LM Studio.app"
   ```

2. **Download a Model**
   - Go to the "Discover" tab
   - Search for and download one of these models:
     - `llama-3.2-3b-instruct` (fast, good for testing)
     - `llama-3.1-8b-instruct` (balanced performance)
     - `mistral-7b-instruct` (alternative)

3. **Start Local Server**
   - Go to "Local Server" tab
   - Load your downloaded model
   - Click "Start Server"
   - Server will start at http://localhost:1234

#### Option B: Ollama (CLI - Alternative)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (choose one)
ollama pull llama3.1:8b        # 8B parameter model
ollama pull mistral:7b         # Alternative 7B model
ollama pull llama3.1:70b       # Large model (requires M4 Max with 128GB)

# Start Ollama server
ollama serve
# Server will start at http://localhost:11434
```

### 4. Configure System

#### Create Local Configuration
```bash
# Copy example config
cp config/config.example.json config/config.json

# Edit configuration (optional)
# Update MAC IDs, model names, etc.
```

#### Example Configuration for LM Studio
```json
{
  "llm": {
    "service": "lmstudio",
    "base_url": "http://localhost:1234",
    "model": "llama-3.2-3b-instruct"
  }
}
```

#### Example Configuration for Ollama
```json
{
  "llm": {
    "service": "ollama",
    "base_url": "http://localhost:11434", 
    "model": "llama3.1:8b"
  }
}
```

## Testing Installation

### 1. Test Basic Setup
```bash
python examples/test_basic_setup.py
```
Should show: ✅ All basic setup tests passed!

### 2. Test LLM Integration
```bash
# Make sure LM Studio local server is running OR Ollama is running
python examples/test_llm.py
```

Expected output for working LM Studio:
```
🧪 Testing LM Studio Integration
==================================================
1. Health Check...
   Status: ✅ Healthy

2. Available Models...
   📦 llama-3.2-3b-instruct

3. Test Generation...
   Model: llama-3.2-3b-instruct
   Response: I am an AI assistant created by Meta...
```

## Quick Start

### Start the System
```bash
# With default configuration
python src/main.py

# Or with npm
npm start

# With debug logging
python src/main.py --debug
```

### Development Mode
```bash
# Run with debug and test mode
npm run dev
```

## Troubleshooting

### LM Studio Issues
- **Server not responding**: Make sure Local Server is started in LM Studio
- **No models**: Download a model from the Discover tab first
- **Port conflicts**: Check if port 1234 is available

### Ollama Issues
- **Command not found**: Reinstall with `curl -fsSL https://ollama.com/install.sh | sh`
- **No models**: Pull a model with `ollama pull llama3.1:8b`
- **Server not running**: Start with `ollama serve`

### Python Issues
- **Module not found**: Run `pip install -r requirements.txt`
- **Permission errors**: Use virtual environment or `pip install --user`

### General Issues
- **Config errors**: Check `config/config.json` syntax
- **Port conflicts**: Change ports in configuration
- **Memory issues**: Use smaller models or increase RAM

## Next Steps

After successful setup:

1. **Test voice processing**: Implement audio components
2. **Configure cameras**: Set up computer vision
3. **Network setup**: Configure multi-Mac coordination
4. **Customize models**: Fine-tune for your use case

## Performance Optimization

### Mac Studio M1 Max (32GB)
- **Recommended models**: 8B parameters or smaller
- **Expected performance**: 15+ tokens/second
- **Memory usage**: ~6-8GB for 8B models

### Mac Studio M4 Max (128GB)
- **Recommended models**: Up to 70B parameters
- **Expected performance**: 8+ tokens/second for 70B
- **Memory usage**: ~45GB for 70B models

## Support

- **Issues**: https://github.com/mickdarling/theeandme/issues
- **Discussions**: https://github.com/mickdarling/theeandme/discussions
- **Documentation**: `/docs` directory