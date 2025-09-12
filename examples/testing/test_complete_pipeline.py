#!/usr/bin/env python3
"""
Complete voice interface pipeline test: Voice → STT → LLM → TTS

Tests the full workflow:
1. Record voice input
2. Transcribe speech to text
3. Send to local LLM (Ollama)
4. Get AI response
5. Convert response to speech (TTS)
"""

import sys
import asyncio
import numpy as np
import sounddevice as sd
import subprocess
from pathlib import Path
import time

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from audio.stt import WhisperSTT
from llm.local_llm import LocalLLM
from core.config_manager import ConfigManager

class VoiceAssistant:
    """Complete voice assistant pipeline."""
    
    def __init__(self, config_path: Path):
        """Initialize voice assistant."""
        # Load configuration
        config_manager = ConfigManager(config_path)
        self.config = config_manager.load_config()
        
        # Initialize components
        self.stt = None
        self.llm = None
        
    async def initialize(self):
        """Initialize all components."""
        print("🤖 Initializing Voice Assistant...")
        print("=" * 50)
        
        # Initialize STT
        print("1. Loading speech recognition...")
        self.stt = WhisperSTT(self.config)
        await self.stt.initialize()
        print("✅ Whisper STT ready")
        
        # Initialize LLM
        print("2. Connecting to local LLM...")
        self.llm = LocalLLM(self.config['llm'])
        
        # Test LLM connection
        try:
            async with self.llm:
                test_response = await self.llm.generate_response("Hello, are you working?")
                if test_response.error:
                    raise Exception(f"LLM error: {test_response.error}")
                print(f"✅ Ollama LLM ready (test response: '{test_response.content[:50]}...')")
        except Exception as e:
            print(f"❌ LLM connection failed: {e}")
            raise
    
    def record_audio(self, duration=5):
        """Record audio from microphone."""
        print(f"🎤 Recording {duration} seconds of audio...")
        print("🔴 Speak now!")
        
        sample_rate = 16000
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.float32)
        sd.wait()
        
        print("🟢 Recording complete!")
        return audio_data.flatten()
    
    async def transcribe_speech(self, audio_array):
        """Transcribe speech to text."""
        print("📝 Transcribing speech...")
        
        result = await self.stt.transcribe_audio(audio_array)
        
        if result.error:
            raise Exception(f"Transcription failed: {result.error}")
        
        print(f"   Transcribed: \"{result.text}\"")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        
        return result.text
    
    async def get_ai_response(self, user_text):
        """Get response from LLM."""
        print("🧠 Getting AI response...")
        
        # Create a system prompt for voice assistant
        system_prompt = self.config['llm'].get('system_prompt', 
            "You are a helpful voice assistant. Respond naturally and concisely to voice queries.")
        
        async with self.llm:
            response = await self.llm.generate_response(
                user_text, 
                system_prompt=system_prompt
            )
            
            if response.error:
                raise Exception(f"LLM failed: {response.error}")
            
            print(f"   AI Response: \"{response.content}\"")
            if response.inference_time:
                print(f"   Generation time: {response.inference_time:.2f}s")
            
            return response.content
    
    def speak_response(self, text):
        """Convert text to speech using macOS TTS."""
        print("🔊 Converting to speech...")
        
        try:
            # Use macOS built-in 'say' command
            subprocess.run(['say', text], check=True)
            print("✅ Speech playback complete")
        except subprocess.CalledProcessError as e:
            print(f"❌ TTS failed: {e}")
        except FileNotFoundError:
            print("❌ macOS 'say' command not available")
    
    async def run_conversation_loop(self):
        """Run interactive conversation loop."""
        print("\n🎙️ Voice Assistant Ready!")
        print("=" * 50)
        print("Commands:")
        print("  - Press ENTER to start recording")
        print("  - Type 'quit' to exit")
        print()
        
        conversation_count = 0
        
        while True:
            try:
                user_input = input("Press ENTER to speak (or 'quit' to exit): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                conversation_count += 1
                print(f"\n🗣️ Conversation {conversation_count}")
                print("-" * 30)
                
                # Step 1: Record audio
                audio = self.record_audio(duration=5)
                
                # Check if we got meaningful audio
                rms_level = np.sqrt(np.mean(audio ** 2))
                if rms_level < 0.001:
                    print("⚠️  No audio detected. Try speaking louder or check microphone.")
                    continue
                
                # Step 2: Speech to text
                user_text = await self.transcribe_speech(audio)
                
                if not user_text.strip():
                    print("⚠️  No speech detected. Try again.")
                    continue
                
                # Step 3: Get AI response
                ai_response = await self.get_ai_response(user_text)
                
                # Step 4: Text to speech
                self.speak_response(ai_response)
                
                print(f"✅ Conversation {conversation_count} complete!\n")
                
            except KeyboardInterrupt:
                print("\n🛑 Interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error in conversation: {e}")
                continue
    
    def cleanup(self):
        """Cleanup resources."""
        if self.stt:
            self.stt.cleanup()


async def main():
    """Main function."""
    print("🎯 Complete Voice Interface Pipeline Test")
    print("=" * 60)
    
    # Check configuration
    config_path = Path(__file__).parent.parent / "config" / "config.example.json"
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    # Initialize assistant
    assistant = VoiceAssistant(config_path)
    
    try:
        # Initialize components
        await assistant.initialize()
        
        # Test single interaction first
        print("\n🧪 Testing Single Interaction...")
        print("=" * 40)
        
        # Record test audio
        audio = assistant.record_audio(duration=5)
        
        # Check audio quality
        rms_level = np.sqrt(np.mean(audio ** 2))
        print(f"Audio quality check - RMS: {rms_level:.4f}")
        
        if rms_level < 0.001:
            print("❌ No audio detected. Check microphone setup.")
            return
        
        # Test transcription
        text = await assistant.transcribe_speech(audio)
        
        if not text.strip():
            print("❌ No speech transcribed. Try speaking more clearly.")
            return
        
        # Test LLM response
        response = await assistant.get_ai_response(text)
        
        # Test TTS
        assistant.speak_response(response)
        
        print("\n✅ Single interaction test passed!")
        
        # Ask if user wants to continue with conversation loop
        continue_choice = input("\nRun interactive conversation loop? (y/N): ").strip().lower()
        
        if continue_choice in ['y', 'yes']:
            await assistant.run_conversation_loop()
        else:
            print("🎉 Pipeline test complete!")
    
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        assistant.cleanup()


if __name__ == "__main__":
    asyncio.run(main())