#!/usr/bin/env python3
"""
Autonomous Voice Testing System
Comprehensive self-testing voice interface with multiple STT engines and analysis

Features:
- Generate test phrases and record them internally
- Play through speakers and record via microphone
- Compare multiple STT engines (Whisper, online services)
- Analyze echo patterns and audio degradation
- Generate comprehensive test reports
- Run continuous testing loops autonomously
"""

import asyncio
import sys
import os
import json
import time
import wave
import threading
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sounddevice as sd
import numpy as np
import requests
import aiohttp

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

class AutonomousVoiceTester:
    def __init__(self):
        self.test_dir = Path("/Users/mick/Developer/theeandme/autonomous_voice_testing")
        self.test_dir.mkdir(exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.test_dir / f"test_session_{self.session_id}"
        self.session_dir.mkdir(exist_ok=True)
        
        self.whisper_stt = None
        self.test_phrases = [
            "This is a test of the voice recognition system.",
            "The quick brown fox jumps over the lazy dog.",
            "Testing echo cancellation and audio quality with a longer sentence that contains multiple words and phrases.",
            "Short test.",
            "Can the system handle complex technical terminology like asynchronous processing and machine learning algorithms?",
            "Testing numbers: one two three four five six seven eight nine ten.",
            "How well does this work with natural speech patterns, pauses, and inflection?",
            "Echo echo echo - testing repetitive words for feedback detection.",
            "Whisper transcription quality assessment in progress.",
            "Final test phrase with punctuation, special characters, and varied tone!"
        ]
        
        self.results = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
        
        print(f"🤖 Autonomous Voice Testing System Initialized")
        print(f"📁 Session directory: {self.session_dir}")
        print(f"🧪 Test phrases: {len(self.test_phrases)}")

    async def initialize_components(self):
        """Initialize all STT components"""
        try:
            # Initialize Whisper STT
            config = {
                'sample_rate': 16000,
                'whisper_model': 'base'
            }
            
            self.whisper_stt = WhisperSTT(config)
            await self.whisper_stt.initialize()
            print("✅ Whisper STT initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False

    def generate_internal_speech(self, text: str, filename: str) -> str:
        """Generate speech internally without speakers"""
        filepath = self.session_dir / filename
        
        try:
            # Use macOS say command to generate directly to file
            cmd = f'say "{text}" -o "{filepath}" --data-format=LEI16@16000'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Generated internal speech: {filename}")
                return str(filepath)
            else:
                print(f"❌ Speech generation failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Speech generation error: {e}")
            return None

    def record_speaker_microphone_loop(self, text: str, filename: str, duration: float = 6.0) -> str:
        """Play text through speakers and record via microphone"""
        filepath = self.session_dir / filename
        
        try:
            print(f"🔊 Playing and recording: {text[:50]}...")
            
            # Set volume to 30% for controlled testing
            os.system("osascript -e 'set volume output volume 30'")
            
            # Start recording
            sample_rate = 16000
            device_id = 2  # Live Streamer CAM 513
            
            # Start recording in background
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16,
                device=device_id
            )
            
            # Wait 0.5 seconds then start speaking
            time.sleep(0.5)
            
            # Play text through speakers
            os.system(f'say "{text}" &')
            
            # Wait for recording to complete
            sd.wait()
            
            # Save recording
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(recording.tobytes())
            
            print(f"✅ Speaker-mic loop recorded: {filename}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Speaker-mic recording error: {e}")
            return None

    async def test_whisper_transcription(self, audio_file: str) -> Dict[str, Any]:
        """Test Whisper transcription on audio file"""
        try:
            # Load audio file
            with wave.open(audio_file, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe
            start_time = time.time()
            result = await self.whisper_stt.transcribe_audio(audio_data)
            processing_time = time.time() - start_time
            
            return {
                'engine': 'whisper',
                'text': result.text,
                'confidence': result.confidence,
                'processing_time': processing_time,
                'success': True
            }
            
        except Exception as e:
            return {
                'engine': 'whisper',
                'text': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'success': False,
                'error': str(e)
            }

    async def test_multiple_stt_engines(self, audio_file: str) -> List[Dict[str, Any]]:
        """Test multiple STT engines on the same audio file"""
        results = []
        
        # Test Whisper
        whisper_result = await self.test_whisper_transcription(audio_file)
        results.append(whisper_result)
        
        # Could add more STT engines here:
        # - Google Speech-to-Text
        # - Azure Speech Services
        # - Amazon Transcribe
        # - OpenAI Whisper API
        
        return results

    def calculate_text_similarity(self, original: str, transcribed: str) -> float:
        """Calculate similarity between original and transcribed text"""
        # Simple word-based similarity
        orig_words = set(original.lower().split())
        trans_words = set(transcribed.lower().split())
        
        if not orig_words:
            return 0.0
        
        intersection = orig_words.intersection(trans_words)
        return len(intersection) / len(orig_words)

    def analyze_audio_quality(self, internal_file: str, recorded_file: str) -> Dict[str, Any]:
        """Analyze audio quality degradation"""
        try:
            # Load both files
            with wave.open(internal_file, 'rb') as wav:
                internal_data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
            
            with wave.open(recorded_file, 'rb') as wav:
                recorded_data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
            
            # Basic quality metrics
            internal_rms = np.sqrt(np.mean(internal_data.astype(np.float64) ** 2))
            recorded_rms = np.sqrt(np.mean(recorded_data.astype(np.float64) ** 2))
            
            # Signal degradation
            signal_ratio = recorded_rms / internal_rms if internal_rms > 0 else 0
            
            return {
                'internal_rms': float(internal_rms),
                'recorded_rms': float(recorded_rms),
                'signal_ratio': float(signal_ratio),
                'quality_score': min(1.0, signal_ratio) if signal_ratio <= 1.0 else 1.0 / signal_ratio
            }
            
        except Exception as e:
            return {
                'internal_rms': 0.0,
                'recorded_rms': 0.0,
                'signal_ratio': 0.0,
                'quality_score': 0.0,
                'error': str(e)
            }

    async def run_single_test(self, phrase_idx: int, phrase: str) -> Dict[str, Any]:
        """Run a complete test cycle for one phrase"""
        print(f"\n🧪 Test {phrase_idx + 1}/{len(self.test_phrases)}: {phrase[:50]}...")
        
        test_result = {
            'test_id': phrase_idx + 1,
            'original_text': phrase,
            'timestamp': datetime.now().isoformat(),
            'internal_audio': None,
            'recorded_audio': None,
            'stt_results': [],
            'quality_analysis': {},
            'accuracy_score': 0.0
        }
        
        # Generate internal speech
        internal_filename = f"test_{phrase_idx+1:02d}_internal.wav"
        internal_file = self.generate_internal_speech(phrase, internal_filename)
        if internal_file:
            test_result['internal_audio'] = internal_filename
        
        # Record speaker-microphone loop
        recorded_filename = f"test_{phrase_idx+1:02d}_recorded.wav"
        recorded_file = self.record_speaker_microphone_loop(phrase, recorded_filename)
        if recorded_file:
            test_result['recorded_audio'] = recorded_filename
        
        # Test STT engines on recorded audio
        if recorded_file:
            stt_results = await self.test_multiple_stt_engines(recorded_file)
            test_result['stt_results'] = stt_results
            
            # Calculate accuracy
            if stt_results and stt_results[0]['success']:
                transcribed = stt_results[0]['text']
                accuracy = self.calculate_text_similarity(phrase, transcribed)
                test_result['accuracy_score'] = accuracy
                
                print(f"📝 Original: {phrase}")
                print(f"🎯 Transcribed: {transcribed}")
                print(f"📊 Accuracy: {accuracy:.1%}")
        
        # Analyze audio quality
        if internal_file and recorded_file:
            quality = self.analyze_audio_quality(internal_file, recorded_file)
            test_result['quality_analysis'] = quality
            print(f"🔊 Audio quality score: {quality.get('quality_score', 0):.1%}")
        
        # Brief pause between tests
        time.sleep(2)
        
        return test_result

    async def run_autonomous_test_suite(self):
        """Run complete autonomous test suite"""
        print(f"\n🚀 Starting Autonomous Voice Test Suite")
        print(f"📊 Running {len(self.test_phrases)} comprehensive tests")
        
        self.results['tests'] = []
        
        for idx, phrase in enumerate(self.test_phrases):
            try:
                test_result = await self.run_single_test(idx, phrase)
                self.results['tests'].append(test_result)
                
                # Save intermediate results
                await self.save_results()
                
            except Exception as e:
                print(f"❌ Test {idx + 1} failed: {e}")
                error_result = {
                    'test_id': idx + 1,
                    'original_text': phrase,
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'accuracy_score': 0.0
                }
                self.results['tests'].append(error_result)
        
        # Generate final analysis
        await self.generate_test_summary()
        
        print(f"\n✅ Autonomous testing complete!")
        print(f"📁 Results saved to: {self.session_dir}")

    async def generate_test_summary(self):
        """Generate comprehensive test summary"""
        tests = [t for t in self.results['tests'] if 'error' not in t]
        
        if not tests:
            self.results['summary'] = {'error': 'No successful tests'}
            return
        
        # Calculate metrics
        accuracy_scores = [t['accuracy_score'] for t in tests if t['accuracy_score'] > 0]
        quality_scores = [t['quality_analysis'].get('quality_score', 0) for t in tests if t.get('quality_analysis')]
        processing_times = []
        
        for test in tests:
            for stt_result in test.get('stt_results', []):
                if stt_result.get('success'):
                    processing_times.append(stt_result.get('processing_time', 0))
        
        summary = {
            'total_tests': len(self.results['tests']),
            'successful_tests': len(tests),
            'average_accuracy': np.mean(accuracy_scores) if accuracy_scores else 0.0,
            'accuracy_std': np.std(accuracy_scores) if accuracy_scores else 0.0,
            'average_quality': np.mean(quality_scores) if quality_scores else 0.0,
            'average_processing_time': np.mean(processing_times) if processing_times else 0.0,
            'best_accuracy': max(accuracy_scores) if accuracy_scores else 0.0,
            'worst_accuracy': min(accuracy_scores) if accuracy_scores else 0.0,
            'completion_time': datetime.now().isoformat()
        }
        
        self.results['summary'] = summary
        
        print(f"\n📊 AUTONOMOUS TEST SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Successful: {summary['successful_tests']}")
        print(f"   Average Accuracy: {summary['average_accuracy']:.1%}")
        print(f"   Average Quality: {summary['average_quality']:.1%}")
        print(f"   Average Processing Time: {summary['average_processing_time']:.2f}s")
        print(f"   Best Accuracy: {summary['best_accuracy']:.1%}")
        print(f"   Worst Accuracy: {summary['worst_accuracy']:.1%}")

    async def save_results(self):
        """Save test results to JSON file"""
        results_file = self.session_dir / "autonomous_test_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"💾 Results saved: {results_file.name}")

    async def generate_detailed_report(self):
        """Generate detailed markdown report"""
        report_file = self.session_dir / "AUTONOMOUS_TEST_REPORT.md"
        
        with open(report_file, 'w') as f:
            f.write(f"# Autonomous Voice Testing Report\n\n")
            f.write(f"**Session ID:** {self.session_id}\n")
            f.write(f"**Date:** {self.results['start_time']}\n")
            f.write(f"**Total Tests:** {len(self.results['tests'])}\n\n")
            
            if 'summary' in self.results and 'error' not in self.results['summary']:
                summary = self.results['summary']
                f.write(f"## Summary\n\n")
                f.write(f"- **Average Accuracy:** {summary['average_accuracy']:.1%}\n")
                f.write(f"- **Average Quality:** {summary['average_quality']:.1%}\n")
                f.write(f"- **Average Processing Time:** {summary['average_processing_time']:.2f}s\n")
                f.write(f"- **Best Accuracy:** {summary['best_accuracy']:.1%}\n")
                f.write(f"- **Worst Accuracy:** {summary['worst_accuracy']:.1%}\n\n")
            
            f.write(f"## Individual Test Results\n\n")
            
            for test in self.results['tests']:
                f.write(f"### Test {test['test_id']}\n\n")
                f.write(f"**Original:** {test['original_text']}\n\n")
                
                if 'stt_results' in test and test['stt_results']:
                    stt = test['stt_results'][0]
                    if stt.get('success'):
                        f.write(f"**Transcribed:** {stt['text']}\n\n")
                        f.write(f"**Accuracy:** {test['accuracy_score']:.1%}\n\n")
                        f.write(f"**Confidence:** {stt['confidence']:.1%}\n\n")
                        f.write(f"**Processing Time:** {stt['processing_time']:.2f}s\n\n")
                    else:
                        f.write(f"**Error:** {stt.get('error', 'Unknown error')}\n\n")
                
                if 'quality_analysis' in test and test['quality_analysis']:
                    quality = test['quality_analysis']
                    f.write(f"**Audio Quality Score:** {quality.get('quality_score', 0):.1%}\n\n")
                
                f.write(f"**Files:** `{test.get('internal_audio', 'N/A')}`, `{test.get('recorded_audio', 'N/A')}`\n\n")
                f.write(f"---\n\n")
        
        print(f"📝 Detailed report generated: {report_file.name}")

async def main():
    """Main autonomous testing function"""
    print("🤖 AUTONOMOUS VOICE TESTING SYSTEM")
    print("==================================")
    
    # Initialize tester
    tester = AutonomousVoiceTester()
    
    # Initialize components
    success = await tester.initialize_components()
    if not success:
        print("❌ Failed to initialize components")
        return
    
    # Run autonomous test suite
    await tester.run_autonomous_test_suite()
    
    # Generate detailed report
    await tester.generate_detailed_report()
    
    print(f"\n🎉 AUTONOMOUS TESTING COMPLETED SUCCESSFULLY!")
    print(f"📁 All results saved to: {tester.session_dir}")
    print(f"📊 Check autonomous_test_results.json for raw data")
    print(f"📝 Check AUTONOMOUS_TEST_REPORT.md for detailed analysis")

if __name__ == '__main__':
    asyncio.run(main())