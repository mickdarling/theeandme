#!/usr/bin/env python3
"""
Automated Audio Test - Run comprehensive testing with user prompts
"""

import asyncio
import sys
import os
import numpy as np
import sounddevice as sd
from pathlib import Path
import time
import subprocess
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.vad import SileroVAD
from audio.stt import WhisperSTT

class AutomatedAudioTester:
    def __init__(self):
        self.device_id = 2  # Live Streamer CAM 513
        self.sample_rate = 16000
        self.vad = None
        self.stt = None
        self.results = {}
        
    async def initialize(self):
        print("🔧 Initializing automated audio testing system...")
        
        # Initialize VAD
        vad_config = {
            'sample_rate': self.sample_rate,
            'vad_threshold': 0.7,
            'min_speech_duration_ms': 300,
            'silence_timeout_seconds': 2.0
        }
        
        self.vad = SileroVAD(vad_config)
        await self.vad.initialize()
        print("✅ VAD ready")
        
        # Initialize STT
        stt_config = {'sample_rate': self.sample_rate, 'whisper_model': 'base'}
        self.stt = WhisperSTT(stt_config)
        await self.stt.initialize()
        print("✅ STT ready")
        
    def say_instruction(self, message):
        """Use TTS to give voice instructions"""
        print(f"🤖 {message}")
        subprocess.run(['say', message], check=True)
        time.sleep(1)
        
    async def record_and_analyze(self, duration, label, instruction=None):
        """Record audio and analyze it"""
        if instruction:
            self.say_instruction(instruction)
            
        print(f"🎤 Recording {duration}s for {label}...")
        
        audio_data = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            device=self.device_id
        )
        sd.wait()
        
        audio_array = audio_data.flatten()
        
        # Basic analysis
        rms = np.sqrt(np.mean(audio_array ** 2))
        
        # VAD analysis
        vad_result = self.vad.detect_voice_activity(audio_array)
        
        # STT analysis if voice detected
        transcription = None
        if vad_result.has_voice:
            transcription_result = await self.stt.transcribe_audio(audio_array)
            transcription = transcription_result.text
            
        result = {
            'rms': rms,
            'vad_confidence': vad_result.confidence,
            'vad_decision': vad_result.has_voice,
            'transcription': transcription,
            'audio_length': len(audio_array),
            'timestamp': datetime.now()
        }
        
        self.results[label] = result
        return result
        
    async def run_comprehensive_test(self):
        """Run the full automated test suite"""
        print("🚀 STARTING COMPREHENSIVE AUDIO TEST")
        print("=" * 60)
        
        # Test 1: Baseline noise
        print("\n📊 TEST 1: Measuring baseline noise")
        self.say_instruction("Please remain completely silent for 5 seconds while I measure background noise")
        await asyncio.sleep(2)
        
        baseline = await self.record_and_analyze(5, "baseline_noise", None)
        print(f"   Noise floor RMS: {baseline['rms']:.6f}")
        
        # Test 2: Close voice
        print("\n📊 TEST 2: Testing voice at close range")
        await asyncio.sleep(1)
        
        close_voice = await self.record_and_analyze(
            5, "close_voice", 
            "Please say clearly: This is a test of my voice recognition system at close range"
        )
        print(f"   Close voice RMS: {close_voice['rms']:.6f}")
        print(f"   VAD confidence: {close_voice['vad_confidence']:.3f}")
        print(f"   Transcription: '{close_voice['transcription']}'")
        
        # Test 3: Normal voice  
        print("\n📊 TEST 3: Testing voice at normal distance")
        await asyncio.sleep(1)
        
        normal_voice = await self.record_and_analyze(
            5, "normal_voice",
            "Please speak at your normal distance and volume: The quick brown fox jumps over the lazy dog"
        )
        print(f"   Normal voice RMS: {normal_voice['rms']:.6f}")
        print(f"   VAD confidence: {normal_voice['vad_confidence']:.3f}")
        print(f"   Transcription: '{normal_voice['transcription']}'")
        
        # Test 4: Far voice
        print("\n📊 TEST 4: Testing voice from farther away")
        await asyncio.sleep(1)
        
        far_voice = await self.record_and_analyze(
            5, "far_voice",
            "Please step back or speak more quietly: I am testing the voice interface from a distance"
        )
        print(f"   Far voice RMS: {far_voice['rms']:.6f}")
        print(f"   VAD confidence: {far_voice['vad_confidence']:.3f}")
        print(f"   Transcription: '{far_voice['transcription']}'")
        
        # Test 5: Echo test
        print("\n📊 TEST 5: Testing echo cancellation effectiveness")
        await asyncio.sleep(1)
        
        self.say_instruction("I will now play text to speech while recording the microphone to test echo cancellation")
        await asyncio.sleep(1)
        
        # Start recording
        print("🎤 Recording during TTS playback...")
        audio_data = sd.rec(
            int(6 * self.sample_rate),
            samplerate=self.sample_rate, 
            channels=1,
            dtype=np.float32,
            device=self.device_id
        )
        
        # Play TTS after 1 second
        await asyncio.sleep(1)
        subprocess.run(['say', 'This is a test of the text to speech echo cancellation system'], check=False)
        
        sd.wait()
        
        echo_audio = audio_data.flatten()
        echo_rms = np.sqrt(np.mean(echo_audio ** 2))
        echo_vad = self.vad.detect_voice_activity(echo_audio)
        
        self.results['echo_test'] = {
            'rms': echo_rms,
            'vad_confidence': echo_vad.confidence, 
            'vad_decision': echo_vad.has_voice
        }
        
        print(f"   Echo pickup RMS: {echo_rms:.6f}")
        print(f"   Echo VAD confidence: {echo_vad.confidence:.3f}")
        print(f"   Echo detected as voice: {echo_vad.has_voice}")
        
        # Analysis and recommendations
        await self.analyze_results()
        
    async def analyze_results(self):
        """Analyze all test results and provide recommendations"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE ANALYSIS RESULTS")
        print("=" * 60)
        
        if not self.results:
            print("❌ No test results available")
            return
            
        baseline_rms = self.results.get('baseline_noise', {}).get('rms', 0)
        close_rms = self.results.get('close_voice', {}).get('rms', 0)
        normal_rms = self.results.get('normal_voice', {}).get('rms', 0)
        far_rms = self.results.get('far_voice', {}).get('rms', 0)
        echo_rms = self.results.get('echo_test', {}).get('rms', 0)
        
        print(f"📊 AUDIO LEVELS:")
        print(f"   Baseline noise:    {baseline_rms:.6f}")
        print(f"   Close voice:       {close_rms:.6f}")
        print(f"   Normal voice:      {normal_rms:.6f}")
        print(f"   Far voice:         {far_rms:.6f}")
        print(f"   Echo pickup:       {echo_rms:.6f}")
        
        # Calculate SNR
        if baseline_rms > 0:
            close_snr = close_rms / baseline_rms
            normal_snr = normal_rms / baseline_rms
            far_snr = far_rms / baseline_rms
            
            print(f"\n📊 SIGNAL-TO-NOISE RATIOS:")
            print(f"   Close voice SNR:   {close_snr:.2f}")
            print(f"   Normal voice SNR:  {normal_snr:.2f}")
            print(f"   Far voice SNR:     {far_snr:.2f}")
            
        # Voice detection analysis
        print(f"\n📊 VOICE DETECTION ANALYSIS:")
        for test_name in ['close_voice', 'normal_voice', 'far_voice']:
            if test_name in self.results:
                result = self.results[test_name]
                print(f"   {test_name.replace('_', ' ').title()}:")
                print(f"     VAD Confidence: {result['vad_confidence']:.3f}")
                print(f"     Voice Detected: {result['vad_decision']}")
                print(f"     Transcription:  '{result['transcription']}'")
        
        # Echo analysis
        if 'echo_test' in self.results:
            echo_result = self.results['echo_test']
            echo_feedback_ratio = echo_rms / normal_rms if normal_rms > 0 else 0
            
            print(f"\n📊 ECHO CANCELLATION ANALYSIS:")
            print(f"   Echo feedback ratio: {echo_feedback_ratio:.4f}")
            print(f"   Echo detected as voice: {echo_result['vad_decision']}")
            
            if echo_feedback_ratio > 0.3:
                print("⚠️  HIGH ECHO FEEDBACK - Recommendations:")
                print("     • Increase silence timeout after TTS")
                print("     • Lower volume threshold for echo detection")
                print("     • Consider microphone repositioning")
            elif echo_result['vad_decision']:
                print("⚠️  ECHO DETECTED AS VOICE - May cause feedback loops")
            else:
                print("✅ GOOD ECHO CANCELLATION")
        
        # Overall recommendations
        print(f"\n📊 OPTIMIZATION RECOMMENDATIONS:")
        
        # VAD threshold recommendations
        if normal_rms > 0 and baseline_rms > 0:
            suggested_threshold = baseline_rms + (normal_rms - baseline_rms) * 0.2
            print(f"   Suggested RMS threshold: {suggested_threshold:.6f}")
            print(f"   Current noise floor + margin: {baseline_rms * 3:.6f}")
            
        # Voice detection recommendations
        normal_result = self.results.get('normal_voice', {})
        if normal_result.get('vad_confidence', 0) < 0.7:
            print("   • Consider lowering VAD confidence threshold")
            print("   • Check microphone positioning and distance")
            
        if not normal_result.get('vad_decision', False):
            print("   • Voice detection failing at normal distance")
            print("   • Increase microphone sensitivity or move closer")
            
        # Transcription quality
        transcription = normal_result.get('transcription', '')
        expected = "the quick brown fox jumps over the lazy dog"
        if transcription and expected.lower() not in transcription.lower():
            print("   • Transcription quality issues detected")
            print("   • Consider noise reduction or better microphone positioning")
        
        print(f"\n✅ AUTOMATED TESTING COMPLETE")
        self.say_instruction("Audio testing complete. Check the terminal for detailed results and recommendations.")

async def main():
    tester = AutomatedAudioTester()
    
    try:
        await tester.initialize()
        await tester.run_comprehensive_test()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tester.stt:
            tester.stt.cleanup()

if __name__ == "__main__":
    asyncio.run(main())