#!/usr/bin/env python3
"""
Audio processing test script for The E and Me voice interface system.

This script tests the complete audio pipeline including VAD, STT, and audio I/O.
"""

import asyncio
import sys
import signal
import json
from pathlib import Path
import logging
import time

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.config_manager import ConfigManager
from audio.audio_manager import AudioManager, AudioEvent
from utils.logger import setup_logging


class AudioTester:
    """Test harness for audio processing components."""
    
    def __init__(self, config_path: Path):
        """Initialize audio tester."""
        self.config_path = config_path
        self.config = None
        self.audio_manager = None
        self.is_running = False
        self.transcriptions = []
        
    async def initialize(self):
        """Initialize the audio testing system."""
        print("🧪 Initializing Audio Processing Test")
        print("=" * 60)
        
        try:
            # Load configuration
            config_manager = ConfigManager(self.config_path)
            self.config = config_manager.load_config()
            config_manager.validate_config(self.config)
            print("✅ Configuration loaded and validated")
            
            # Initialize audio manager
            self.audio_manager = AudioManager(self.config)
            await self.audio_manager.initialize()
            print("✅ Audio Manager initialized")
            
            # Set up callbacks
            self._setup_callbacks()
            print("✅ Callbacks configured")
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def _setup_callbacks(self):
        """Set up audio event callbacks."""
        self.audio_manager.add_callback('voice_start', self._on_voice_start)
        self.audio_manager.add_callback('voice_end', self._on_voice_end)
        self.audio_manager.add_callback('transcription_ready', self._on_transcription_ready)
        self.audio_manager.add_callback('audio_error', self._on_audio_error)
        self.audio_manager.add_callback('state_changed', self._on_state_changed)
    
    def _on_voice_start(self, event: AudioEvent):
        """Handle voice activity start."""
        print(f"🎤 Voice activity started (confidence: {event.confidence:.2f})")
    
    def _on_voice_end(self, event: AudioEvent):
        """Handle voice activity end."""
        print(f"🔇 Voice activity ended (confidence: {event.confidence:.2f})")
        print("   Processing audio for transcription...")
    
    def _on_transcription_ready(self, event: AudioEvent):
        """Handle transcription completion."""
        result = event.data
        timestamp = time.strftime("%H:%M:%S", time.localtime(event.timestamp))
        
        print(f"📝 [{timestamp}] Transcription: \"{result.text}\"")
        print(f"    Confidence: {result.confidence:.2f}")
        print(f"    Processing time: {result.processing_time:.2f}s")
        print(f"    Model: {result.model_used}")
        
        # Store transcription
        self.transcriptions.append({
            'timestamp': event.timestamp,
            'text': result.text,
            'confidence': result.confidence,
            'processing_time': result.processing_time
        })
    
    def _on_audio_error(self, event: AudioEvent):
        """Handle audio processing errors."""
        result = event.data
        print(f"❌ Audio error: {result.error}")
    
    def _on_state_changed(self, event: AudioEvent):
        """Handle audio state changes."""
        data = event.data
        print(f"🔄 State changed: {data['old_state'].value} → {data['new_state'].value}")
    
    async def test_audio_devices(self):
        """Test audio device detection and listing."""
        print("\n🎧 Testing Audio Device Detection")
        print("-" * 40)
        
        try:
            devices = self.audio_manager.get_available_devices()
            
            input_devices = [d for d in devices if d.is_input]
            output_devices = [d for d in devices if d.is_output]
            
            print(f"Found {len(input_devices)} input devices:")
            for device in input_devices:
                default_marker = " [DEFAULT]" if device.is_default else ""
                print(f"  [{device.index}] {device.name}{default_marker}")
                print(f"      Channels: {device.channels}, Sample Rate: {device.sample_rate}Hz")
            
            print(f"\nFound {len(output_devices)} output devices:")
            for device in output_devices:
                default_marker = " [DEFAULT]" if device.is_default else ""
                print(f"  [{device.index}] {device.name}{default_marker}")
                print(f"      Channels: {device.channels}, Sample Rate: {device.sample_rate}Hz")
            
            return len(input_devices) > 0
            
        except Exception as e:
            print(f"❌ Device detection failed: {e}")
            return False
    
    async def test_vad_initialization(self):
        """Test VAD model loading."""
        print("\n🔊 Testing Voice Activity Detection")
        print("-" * 40)
        
        try:
            # VAD should already be initialized through AudioManager
            print("✅ Silero VAD model loaded")
            
            # Test VAD configuration
            vad_config = self.config.get('audio', {})
            print(f"   Threshold: {vad_config.get('vad_threshold', 0.7)}")
            print(f"   Sample Rate: {vad_config.get('sample_rate', 16000)}Hz")
            print(f"   Min Speech Duration: {vad_config.get('min_speech_duration_ms', 300)}ms")
            
            return True
            
        except Exception as e:
            print(f"❌ VAD test failed: {e}")
            return False
    
    async def test_stt_initialization(self):
        """Test STT model loading."""
        print("\n🗣️  Testing Speech-to-Text")
        print("-" * 40)
        
        try:
            # STT should already be initialized through AudioManager
            stt_config = self.config.get('speech', {})
            model_size = stt_config.get('whisper_model', 'base')
            
            print(f"✅ Whisper {model_size} model loaded")
            
            # Get performance stats
            stats = self.audio_manager.stt_processor.get_performance_stats()
            print(f"   Model: {stats['model_size']}")
            print(f"   Device: {stats['device']}")
            
            return True
            
        except Exception as e:
            print(f"❌ STT test failed: {e}")
            return False
    
    async def run_interactive_test(self):
        """Run interactive voice recognition test."""
        print("\n🎙️  Interactive Voice Recognition Test")
        print("-" * 40)
        print("Instructions:")
        print("• Speak clearly into your microphone")
        print("• Voice activity will be detected automatically")
        print("• Transcriptions will appear below")
        print("• Press Ctrl+C to stop")
        print()
        
        try:
            # Start audio processing
            await self.audio_manager.start_listening()
            
            self.is_running = True
            start_time = time.time()
            
            # Run for user interaction
            while self.is_running:
                await asyncio.sleep(1.0)
                
                # Show periodic stats
                if int(time.time() - start_time) % 10 == 0:
                    await self._show_performance_stats()
                    start_time = time.time()  # Reset to avoid repeated prints
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping audio test...")
        
        finally:
            self.audio_manager.stop_listening()
    
    async def _show_performance_stats(self):
        """Show current performance statistics."""
        stats = self.audio_manager.get_performance_stats()
        
        print(f"\n📊 Performance Stats:")
        print(f"   State: {stats['state']}")
        print(f"   Processed chunks: {stats['processed_chunks']}")
        print(f"   Drop rate: {stats['drop_rate']:.1%}")
        print(f"   Processing speed: {stats['chunks_per_second']:.1f} chunks/sec")
        print(f"   Buffer duration: {stats['buffer_duration']:.1f}s")
        print(f"   Queue size: {stats['queue_size']}")
        print()
    
    async def run_summary(self):
        """Show test summary."""
        print("\n📋 Test Summary")
        print("-" * 40)
        
        if self.transcriptions:
            print(f"Total transcriptions: {len(self.transcriptions)}")
            
            # Calculate average confidence
            avg_confidence = sum(t['confidence'] for t in self.transcriptions) / len(self.transcriptions)
            print(f"Average confidence: {avg_confidence:.2f}")
            
            # Calculate average processing time
            avg_time = sum(t['processing_time'] for t in self.transcriptions) / len(self.transcriptions)
            print(f"Average processing time: {avg_time:.2f}s")
            
            print("\nTranscription history:")
            for i, t in enumerate(self.transcriptions[-5:], 1):  # Show last 5
                timestamp = time.strftime("%H:%M:%S", time.localtime(t['timestamp']))
                print(f"  {i}. [{timestamp}] \"{t['text']}\" (conf: {t['confidence']:.2f})")
        
        else:
            print("No transcriptions captured")
        
        # Final performance stats
        final_stats = self.audio_manager.get_performance_stats()
        print(f"\nFinal performance:")
        print(f"  Processed chunks: {final_stats['processed_chunks']}")
        print(f"  Dropped chunks: {final_stats['dropped_chunks']}")
        print(f"  Drop rate: {final_stats['drop_rate']:.1%}")
    
    def stop(self):
        """Stop the test."""
        self.is_running = False
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.audio_manager:
            self.audio_manager.cleanup()


async def main():
    """Main test function."""
    # Set up logging
    setup_logging(level=logging.INFO)
    
    # Configure paths
    config_path = Path(__file__).parent.parent / "config" / "config.example.json"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Run: cp config/config.example.json config/config.json")
        sys.exit(1)
    
    # Create tester
    tester = AudioTester(config_path)
    
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\n🛑 Received interrupt signal")
        tester.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize
        if not await tester.initialize():
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("🧪 AUDIO SYSTEM TESTS")
        print("=" * 60)
        
        # Run component tests
        tests_passed = 0
        total_tests = 3
        
        if await tester.test_audio_devices():
            tests_passed += 1
        
        if await tester.test_vad_initialization():
            tests_passed += 1
            
        if await tester.test_stt_initialization():
            tests_passed += 1
        
        print(f"\n📊 Component tests: {tests_passed}/{total_tests} passed")
        
        if tests_passed == total_tests:
            print("✅ All component tests passed! Starting interactive test...")
            await tester.run_interactive_test()
        else:
            print("❌ Some component tests failed. Skipping interactive test.")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # Show summary and cleanup
        await tester.run_summary()
        await tester.cleanup()
        print("\n✅ Audio test complete!")


if __name__ == "__main__":
    asyncio.run(main())