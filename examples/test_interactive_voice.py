#!/usr/bin/env python3
"""
Interactive Voice Assistant Test - Full Pipeline with Clear Indicators
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from audio.audio_manager import AudioManager
from llm.local_llm import LocalLLM
from core.config_manager import ConfigManager

class InteractiveVoiceDemo:
    def __init__(self):
        config_path = Path(__file__).parent.parent / "config" / "config.example.json"
        self.config = ConfigManager(config_path)
        self.audio_manager = AudioManager(self.config)
        self.llm = LocalLLM(self.config)
    
    async def initialize(self):
        """Initialize all components"""
        print("🤖 INTERACTIVE VOICE ASSISTANT")
        print("=" * 50)
        print("🎯 Testing complete voice pipeline:")
        print("   1. Voice Input Detection")
        print("   2. Speech-to-Text Processing") 
        print("   3. AI Response Generation")
        print("   4. Text-to-Speech Output")
        print("=" * 50)
        
        # Initialize LLM
        print("🧠 Connecting to local AI...")
        test_response = await self.llm.generate("Say hello briefly", max_tokens=20)
        if test_response.error:
            raise Exception(f"LLM error: {test_response.error}")
        print(f"✅ AI ready: \"{test_response.content.strip()}\"")
        
        # Initialize audio
        print("🎤 Setting up audio systems...")
        await self.audio_manager.initialize()
        print("✅ Audio ready")
        
        print("\n🎉 System fully operational!")
        return True
    
    def show_listening_prompt(self):
        """Show clear visual indicator that system is listening"""
        print("\n" + "🎤" * 25)
        print("🔴 LISTENING MODE ACTIVATED")
        print("💬 Please speak your question or comment now...")
        print("⏱️  I'll record for 5 seconds")
        print("🎯 Speak clearly and wait for processing")
        print("🎤" * 25)
        print()
    
    async def capture_voice_input(self):
        """Capture and process voice input with clear status"""
        self.show_listening_prompt()
        
        # Record audio
        print("🔴 Recording started...")
        audio_data = await self.audio_manager.record_audio(duration_seconds=5)
        print("🟢 Recording finished!")
        
        # Process audio
        print("🔄 Processing your speech...")
        transcription = await self.audio_manager.transcribe_audio(audio_data)
        
        if transcription:
            print(f"📝 You said: \"{transcription}\"")
            return transcription
        else:
            print("❌ No speech detected. Please try again.")
            return None
    
    async def generate_ai_response(self, user_input):
        """Generate AI response with status updates"""
        print("🤔 AI is thinking...")
        
        prompt = f"""You are a helpful voice assistant. Respond naturally and conversationally to this user input: "{user_input}"
        
        Keep your response under 50 words and friendly."""
        
        response = await self.llm.generate(prompt, max_tokens=100)
        
        if response.error:
            print(f"❌ AI error: {response.error}")
            return None
        
        print(f"💭 AI response: \"{response.content}\"")
        return response.content
    
    def speak_response(self, text):
        """Convert text to speech with status"""
        print("🔊 Speaking response...")
        
        # Use macOS say command for text-to-speech
        os.system(f'say "{text}"')
        
        print("✅ Response spoken!")
    
    async def run_single_interaction(self):
        """Run one complete voice interaction cycle"""
        print("\n" + "🔄" * 20)
        print("STARTING VOICE INTERACTION CYCLE")
        print("🔄" * 20)
        
        # Step 1: Get voice input
        user_speech = await self.capture_voice_input()
        
        if not user_speech:
            return False
        
        # Step 2: Generate AI response
        ai_response = await self.generate_ai_response(user_speech)
        
        if not ai_response:
            return False
        
        # Step 3: Speak the response
        self.speak_response(ai_response)
        
        print("\n✅ Interaction cycle complete!")
        return True
    
    async def demo_conversation(self):
        """Run a demonstration conversation"""
        try:
            # Initialize system
            await self.initialize()
            
            print("\n" + "🗣️ " * 15)
            print("VOICE CONVERSATION DEMO")
            print("🗣️ " * 15)
            print("📋 Instructions:")
            print("   • Wait for the 🔴 LISTENING indicator")
            print("   • Speak when prompted")
            print("   • System will respond with voice")
            print("   • Press Ctrl+C anytime to exit")
            print("🗣️ " * 15)
            
            # Run conversation loop
            interaction_count = 0
            while True:
                interaction_count += 1
                print(f"\n📍 INTERACTION #{interaction_count}")
                
                success = await self.run_single_interaction()
                
                if success:
                    print("\n" + "─" * 50)
                    print("✅ Ready for next interaction!")
                    print("Press Enter to continue, or Ctrl+C to exit...")
                    input()
                else:
                    print("❌ Interaction failed. Trying again...")
                    await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            print("\n\n👋 Voice Assistant Demo Complete!")
            print("Thanks for testing the voice interface!")
        except Exception as e:
            print(f"\n❌ Demo error: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Main demonstration function"""
    demo = InteractiveVoiceDemo()
    await demo.demo_conversation()

if __name__ == "__main__":
    print("🚀 Starting Interactive Voice Assistant Demo...")
    asyncio.run(main())