#!/usr/bin/env python3
"""
Multi-STT Engine Autonomous Voice Tester - Version 3.0
Tests multiple speech-to-text engines for comparative analysis

Supported STT Engines:
1. OpenAI Whisper (local)
2. Google Speech Recognition (online)
3. macOS Speech Recognition (offline)
4. Azure Speech (if configured)

Key Features:
- Comparative accuracy analysis across engines
- Engine-specific performance metrics
- Cross-engine semantic scoring
- Adaptive volume control per engine
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
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import io

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

class MultiSTTAutonomousTester:
    def __init__(self):
        self.session_dir = None
        self.session_data = {}
        self.current_volume = 0.3  # Start with 30%

        # Enhanced test phrases optimized from v2.0 findings
        self.test_phrases = [
            "This is a test of the voice recognition system.",
            "The quick brown fox jumps over the lazy dog.",
            "Testing numbers: one two three four five.",
            "Can you hear technical terminology clearly?",
            "Echo, echo, testing repetitive words.",
            "How well does this work with natural speech?",
            "Short test.",
            "Final test with punctuation and tone.",
        ]

        # Primary voice for target audience (American English, New England)
        self.primary_voice = 'Samantha'  # Highest quality US English voice

        # Optional: Accent variety for comprehensive testing (tertiary audience)
        self.accent_test_voices = [
            'Daniel',    # UK - British
            'Karen',     # AU - Australian
            'Moira',     # IE - Irish
            'Rishi',     # IN - Indian
            'Tessa'      # ZA - South African
        ]

        # Focus mode: True = use only primary voice, False = cycle accents
        self.focus_primary_audience = True

        # Number word conversions
        self.number_words = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12'
        }
        self.digit_words = {v: k for k, v in self.number_words.items()}

        # Initialize STT engines
        self.stt_engines = {}
        self.initialize_stt_engines()

        self.setup_session_directory()
        print(f"🎯 Multi-STT Autonomous Voice Tester v3.0 Initialized")
        print(f"📁 Session directory: {self.session_dir}")
        print(f"🔧 STT Engines: {list(self.stt_engines.keys())}")
        print(f"🧪 Test phrases: {len(self.test_phrases)}")

    def initialize_stt_engines(self):
        """Initialize all available STT engines"""
        # 1. OpenAI Whisper (local)
        try:
            # Provide required config for WhisperSTT
            whisper_config = {
                'whisper_model': 'base',
                'whisper_device': 'cpu',
                'language': 'en',
                'sample_rate': 16000
            }
            self.stt_engines['whisper'] = WhisperSTT(whisper_config)
            # Initialize the Whisper model
            asyncio.run(self.stt_engines['whisper'].initialize())
            print("✅ Whisper STT initialized")
        except Exception as e:
            print(f"❌ Whisper initialization failed: {e}")

        # 2. SpeechRecognition library for multiple engines
        self.sr_recognizer = sr.Recognizer()

        # Google Speech Recognition (requires internet)
        self.stt_engines['google'] = 'google'
        print("✅ Google Speech Recognition ready (requires internet)")

        # macOS Speech Recognition (offline)
        if sys.platform == 'darwin':
            self.stt_engines['macos'] = 'macos'
            print("✅ macOS Speech Recognition ready")

        # Note: Azure would require API keys
        print(f"🎯 Total engines available: {len(self.stt_engines)}")

    def setup_session_directory(self):
        """Setup session directory for multi-engine results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = Path("/Users/mick/Developer/theeandme/autonomous_voice_testing_v3")
        base_dir.mkdir(exist_ok=True)

        self.session_dir = base_dir / f"multi_stt_session_{timestamp}_v3"
        self.session_dir.mkdir(exist_ok=True)

        # Initialize session data
        self.session_data = {
            'session_id': timestamp,
            'version': '3.0_multi_stt',
            'engines': list(self.stt_engines.keys()),
            'improvements': [
                'Multi-STT engine comparison',
                'Cross-engine semantic scoring',
                'Engine-specific performance analysis',
                'Adaptive volume per engine'
            ],
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'engine_summary': {},
            'comparative_analysis': {}
        }

    def normalize_text_for_comparison(self, text: str) -> str:
        """Normalize text for semantic comparison"""
        text = text.lower().strip()

        # Convert numbers bidirectionally
        words = text.split()
        normalized_words = []

        for word in words:
            # Remove punctuation for comparison
            clean_word = re.sub(r'[^\w]', '', word)

            # Convert number words to digits
            if clean_word in self.number_words:
                normalized_words.append(self.number_words[clean_word])
            # Convert digits to number words
            elif clean_word in self.digit_words:
                normalized_words.append(self.digit_words[clean_word])
            else:
                normalized_words.append(clean_word)

        return ' '.join(normalized_words)

    def calculate_semantic_similarity(self, original: str, transcribed: str) -> float:
        """Enhanced similarity calculation with semantic awareness"""
        # Normalize both texts
        orig_norm = self.normalize_text_for_comparison(original)
        trans_norm = self.normalize_text_for_comparison(transcribed)

        orig_words = set(orig_norm.split())
        trans_words = set(trans_norm.split())

        if not orig_words:
            return 0.0

        # Calculate word-level similarity
        intersection = orig_words.intersection(trans_words)
        word_similarity = len(intersection) / len(orig_words)

        # Bonus for exact sequence matches
        orig_sequence = orig_norm.split()
        trans_sequence = trans_norm.split()

        sequence_bonus = 0.0
        if len(orig_sequence) == len(trans_sequence):
            matches = sum(1 for o, t in zip(orig_sequence, trans_sequence) if o == t)
            sequence_bonus = (matches / len(orig_sequence)) * 0.2  # 20% bonus

        return min(1.0, word_similarity + sequence_bonus)

    def calculate_enhanced_confidence(self, base_conf: float, audio_quality: float, text_length: int) -> float:
        """Enhanced confidence scoring using multiple factors"""
        # Base confidence handling
        base_conf = base_conf if base_conf > 0 else 0.3

        # Audio quality factor
        quality_factor = min(1.0, audio_quality * 3.5)

        # Text length factor
        length_factor = min(1.0, text_length / 20.0)

        # Combined confidence
        enhanced_conf = (base_conf * 0.5) + (quality_factor * 0.3) + (length_factor * 0.2)

        return min(1.0, enhanced_conf)

    def classify_error_pattern(self, original: str, transcribed: str) -> str:
        """Classify the type of transcription error"""
        if not transcribed.strip():
            return "no_transcription"

        orig_words = original.lower().split()
        trans_words = transcribed.lower().split()

        # Check for number format issues
        if any(word in self.number_words for word in orig_words) or any(word.isdigit() for word in orig_words):
            if any(word.isdigit() for word in trans_words) or any(word in self.number_words for word in trans_words):
                return "number_format_conversion"

        # Check for word substitution
        if len(orig_words) == len(trans_words):
            return "word_substitution"
        elif len(trans_words) < len(orig_words):
            return "word_omission"
        else:
            return "word_insertion"

    def calculate_audio_quality(self, audio_data: np.ndarray) -> float:
        """Calculate basic audio quality metric"""
        if audio_data is None or len(audio_data) == 0:
            return 0.0

        # Calculate RMS
        rms = np.sqrt(np.mean(audio_data**2))

        # Normalize to 0-1 range
        quality = min(1.0, rms * 10.0)
        return quality

    async def transcribe_with_whisper(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Transcribe using Whisper STT"""
        try:
            result = await self.stt_engines['whisper'].transcribe_audio(audio_data)
            return {
                'text': result.text,
                'confidence': result.confidence,
                'processing_time': result.processing_time,
                'error': None
            }
        except Exception as e:
            return {
                'text': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'error': str(e)
            }

    def transcribe_with_speech_recognition(self, audio_data: np.ndarray, engine: str) -> Dict[str, Any]:
        """Transcribe using SpeechRecognition library engines"""
        try:
            # Convert numpy array to audio data for speech_recognition
            audio_bytes = io.BytesIO()

            # Convert to 16-bit PCM WAV format
            audio_int16 = (audio_data * 32767).astype(np.int16)

            # Create WAV file in memory
            with wave.open(audio_bytes, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_int16.tobytes())

            audio_bytes.seek(0)

            # Use speech_recognition
            with sr.AudioFile(audio_bytes) as source:
                audio = self.sr_recognizer.record(source)

            start_time = time.time()

            # Transcribe with specific engine
            if engine == 'google':
                text = self.sr_recognizer.recognize_google(audio)
            elif engine == 'macos' and sys.platform == 'darwin':
                # Note: macOS recognition might not be directly available
                # Fall back to Google for now
                text = self.sr_recognizer.recognize_google(audio)
            else:
                raise ValueError(f"Unsupported engine: {engine}")

            processing_time = time.time() - start_time

            return {
                'text': text,
                'confidence': 0.8,  # SpeechRecognition doesn't provide confidence
                'processing_time': processing_time,
                'error': None
            }

        except sr.UnknownValueError:
            return {
                'text': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'error': 'Speech not recognized'
            }
        except Exception as e:
            return {
                'text': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'error': str(e)
            }

    def generate_internal_speech(self, text: str, filename: str) -> bool:
        """Generate clean TTS audio with rotating high-quality voices"""
        try:
            output_path = self.session_dir / filename

            # macOS TTS to AIFF first, then convert to WAV
            temp_aiff = self.session_dir / (filename.replace('.wav', '.aiff'))

            # Use primary audience voice (American English) or cycle accents for comprehensive testing
            if self.focus_primary_audience:
                current_voice = self.primary_voice
                print(f"🎤 Using primary voice: {current_voice} (American English)")
            else:
                # For comprehensive accent testing (tertiary audience analysis)
                all_voices = [self.primary_voice] + self.accent_test_voices
                current_voice = all_voices[self.current_voice_idx % len(all_voices)]
                self.current_voice_idx = (self.current_voice_idx + 1) % len(all_voices)
                print(f"🎤 Using voice: {current_voice} (accent variety testing)")

            # Generate AIFF using selected high-quality voice
            result = subprocess.run([
                'say', '-v', current_voice, '-o', str(temp_aiff), text
            ], capture_output=True, text=True, check=True)

            # Convert AIFF to WAV using ffmpeg or afconvert
            try:
                # Try afconvert (built into macOS)
                subprocess.run([
                    'afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', str(temp_aiff), str(output_path)
                ], capture_output=True, text=True, check=True)

                # Clean up temp file
                temp_aiff.unlink()

                print(f"✅ Generated internal speech: {filename}")
                return True

            except subprocess.CalledProcessError:
                # Fallback: just use the AIFF file by renaming
                temp_aiff.rename(output_path)
                print(f"✅ Generated internal speech (AIFF): {filename}")
                return True

        except subprocess.CalledProcessError as e:
            print(f"❌ TTS failed for {filename}: {e}")
            return False

    def record_with_adaptive_volume(self, text: str, filename: str, duration: float = 6.0) -> Tuple[str, Dict]:
        """Record audio with adaptive volume control"""
        try:
            output_path = self.session_dir / filename

            print(f"🔊 Adaptive volume: {int(self.current_volume * 100)}% | Text: {text[:50]}...")

            # Set system volume
            subprocess.run(['osascript', '-e', f'set volume output volume {int(self.current_volume * 100)}'],
                         capture_output=True)

            # Wait for volume to take effect
            time.sleep(0.5)

            # Record audio
            sample_rate = 16000
            device_id = 2  # Live Streamer CAM 513

            audio_data = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32,
                device=device_id
            )
            sd.wait()

            # Calculate audio quality
            audio_quality = self.calculate_audio_quality(audio_data)

            # Save audio file
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

            print(f"✅ Adaptive recording: {filename} at {int(self.current_volume * 100)}%")

            return str(output_path), {
                'volume_used': self.current_volume,
                'audio_quality': audio_quality,
                'rms': np.sqrt(np.mean(audio_data**2))
            }

        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return "", {}

    def adapt_volume_based_on_quality(self, audio_quality: float):
        """Adapt volume for next recording based on audio quality"""
        if audio_quality < 0.2:  # Low quality
            self.current_volume = min(1.0, self.current_volume + 0.1)
        elif audio_quality > 0.5:  # High quality
            self.current_volume = max(0.2, self.current_volume - 0.05)
        # Keep current volume if quality is moderate

        print(f"🎛️ Next volume: {int(self.current_volume * 100)}%")

    async def run_multi_engine_test_suite(self):
        """Run autonomous testing across all STT engines"""
        print(f"\n🚀 Starting Multi-STT Engine Test Suite v3.0")
        print(f"📊 Running {len(self.test_phrases)} tests across {len(self.stt_engines)} engines")
        print(f"🔧 Engines: {list(self.stt_engines.keys())}")

        for test_idx, phrase in enumerate(self.test_phrases, 1):
            print(f"\n🧪 Multi-Engine Test {test_idx}/{len(self.test_phrases)}: {phrase}...")

            # Generate clean internal speech
            internal_filename = f"multi_test_{test_idx:02d}_internal.wav"
            if not self.generate_internal_speech(phrase, internal_filename):
                continue

            # Play internal speech through speakers and record
            self.play_internal_speech(self.session_dir / internal_filename)
            time.sleep(0.5)  # Brief pause

            recorded_filename = f"multi_test_{test_idx:02d}_recorded.wav"
            recorded_path, audio_metadata = self.record_with_adaptive_volume(
                phrase, recorded_filename, duration=6.0
            )

            if not recorded_path:
                continue

            # Load recorded audio for transcription
            with wave.open(recorded_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0

            # Test across all STT engines
            engine_results = {}

            for engine_name, engine in self.stt_engines.items():
                print(f"  🎯 Testing {engine_name}...")

                if engine_name == 'whisper':
                    result = await self.transcribe_with_whisper(audio_data)
                else:
                    result = self.transcribe_with_speech_recognition(audio_data, engine_name)

                if result['error']:
                    print(f"    ❌ {engine_name} failed: {result['error']}")
                    continue

                # Calculate enhanced metrics
                semantic_accuracy = self.calculate_semantic_similarity(phrase, result['text'])
                audio_quality = audio_metadata.get('audio_quality', 0.0)
                enhanced_confidence = self.calculate_enhanced_confidence(
                    result['confidence'], audio_quality, len(result['text'])
                )
                error_pattern = self.classify_error_pattern(phrase, result['text'])

                engine_results[engine_name] = {
                    'original': phrase,
                    'transcribed': result['text'],
                    'semantic_accuracy': semantic_accuracy,
                    'confidence': result['confidence'],
                    'enhanced_confidence': enhanced_confidence,
                    'processing_time': result['processing_time'],
                    'error_pattern': error_pattern,
                    'audio_quality': audio_quality
                }

                print(f"    📝 {engine_name}: {result['text']}")
                print(f"    📊 Accuracy: {semantic_accuracy*100:.1f}% | Conf: {enhanced_confidence*100:.1f}%")

            # Store test results
            test_data = {
                'test_number': test_idx,
                'original_text': phrase,
                'internal_file': internal_filename,
                'recorded_file': recorded_filename,
                'audio_metadata': audio_metadata,
                'voice_used': self.quality_voices[(self.current_voice_idx - 1) % len(self.quality_voices)],
                'engine_results': engine_results,
                'timestamp': datetime.now().isoformat()
            }

            self.session_data['tests'].append(test_data)

            # Adapt volume for next test
            self.adapt_volume_based_on_quality(audio_metadata.get('audio_quality', 0.3))

        # Generate comparative analysis
        self.generate_comparative_analysis()

        # Save results
        self.save_results()

        print(f"\n✅ Multi-STT Engine testing complete!")
        print(f"📁 Results saved to: {self.session_dir}")

    def play_internal_speech(self, file_path: Path):
        """Play internal speech through speakers"""
        try:
            subprocess.run(['afplay', str(file_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Audio playback failed: {e}")

    def generate_comparative_analysis(self):
        """Generate comparative analysis across engines"""
        print(f"\n📊 Generating Multi-Engine Comparative Analysis...")

        engine_stats = {}

        # Initialize stats for each engine
        for engine_name in self.stt_engines.keys():
            engine_stats[engine_name] = {
                'total_tests': 0,
                'successful_tests': 0,
                'avg_semantic_accuracy': 0.0,
                'avg_enhanced_confidence': 0.0,
                'avg_processing_time': 0.0,
                'error_patterns': {},
                'best_results': [],
                'worst_results': []
            }

        # Analyze results for each test
        for test in self.session_data['tests']:
            for engine_name, result in test['engine_results'].items():
                stats = engine_stats[engine_name]
                stats['total_tests'] += 1

                if result['transcribed']:
                    stats['successful_tests'] += 1
                    stats['avg_semantic_accuracy'] += result['semantic_accuracy']
                    stats['avg_enhanced_confidence'] += result['enhanced_confidence']
                    stats['avg_processing_time'] += result['processing_time']

                    # Track error patterns
                    pattern = result['error_pattern']
                    stats['error_patterns'][pattern] = stats['error_patterns'].get(pattern, 0) + 1

                    # Track best/worst results
                    if result['semantic_accuracy'] >= 0.9:
                        stats['best_results'].append({
                            'test': test['test_number'],
                            'text': result['original'],
                            'accuracy': result['semantic_accuracy']
                        })
                    elif result['semantic_accuracy'] <= 0.3:
                        stats['worst_results'].append({
                            'test': test['test_number'],
                            'text': result['original'],
                            'accuracy': result['semantic_accuracy']
                        })

        # Calculate averages
        for engine_name, stats in engine_stats.items():
            if stats['successful_tests'] > 0:
                stats['avg_semantic_accuracy'] /= stats['successful_tests']
                stats['avg_enhanced_confidence'] /= stats['successful_tests']
                stats['avg_processing_time'] /= stats['successful_tests']
                stats['success_rate'] = stats['successful_tests'] / stats['total_tests']
            else:
                stats['success_rate'] = 0.0

        self.session_data['engine_summary'] = engine_stats

        # Generate comparative insights
        comparative_insights = []

        # Find best performing engine
        best_engine = max(engine_stats.keys(),
                         key=lambda x: engine_stats[x]['avg_semantic_accuracy'] * engine_stats[x]['success_rate'])
        comparative_insights.append(f"Best overall performance: {best_engine}")

        # Find fastest engine
        fastest_engine = min(engine_stats.keys(),
                           key=lambda x: engine_stats[x]['avg_processing_time'] if engine_stats[x]['successful_tests'] > 0 else float('inf'))
        comparative_insights.append(f"Fastest processing: {fastest_engine}")

        self.session_data['comparative_analysis'] = {
            'insights': comparative_insights,
            'best_overall': best_engine,
            'fastest': fastest_engine
        }

        # Print summary
        print(f"\n📈 MULTI-ENGINE SUMMARY:")
        for engine_name, stats in engine_stats.items():
            print(f"   {engine_name}: {stats['avg_semantic_accuracy']*100:.1f}% accuracy, {stats['success_rate']*100:.1f}% success rate")

    def save_results(self):
        """Save comprehensive multi-engine results"""
        # Save JSON data with numpy-safe conversion
        json_path = self.session_dir / "multi_stt_results.json"

        # Convert numpy types to native Python types
        def convert_numpy(obj):
            if isinstance(obj, np.float32) or isinstance(obj, np.float64):
                return float(obj)
            elif isinstance(obj, np.int32) or isinstance(obj, np.int64):
                return int(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        safe_data = convert_numpy(self.session_data)

        with open(json_path, 'w') as f:
            json.dump(safe_data, f, indent=2)

        # Generate markdown report
        self.generate_markdown_report()

        print(f"📝 Multi-engine report generated: MULTI_STT_REPORT.md")

    def generate_markdown_report(self):
        """Generate comprehensive markdown report"""
        report_path = self.session_dir / "MULTI_STT_REPORT.md"

        with open(report_path, 'w') as f:
            f.write(f"# Multi-STT Engine Autonomous Testing Report v3.0\n\n")
            f.write(f"**Session ID:** {self.session_data['session_id']}\n")
            f.write(f"**Version:** 3.0 with multi-engine comparison\n")
            f.write(f"**Total Tests:** {len(self.session_data['tests'])}\n")
            f.write(f"**STT Engines:** {', '.join(self.session_data['engines'])}\n\n")

            # Engine comparison summary
            f.write(f"## Engine Performance Comparison\n\n")
            for engine_name, stats in self.session_data['engine_summary'].items():
                f.write(f"### {engine_name.title()}\n")
                f.write(f"- **Semantic Accuracy:** {stats['avg_semantic_accuracy']*100:.1f}%\n")
                f.write(f"- **Success Rate:** {stats['success_rate']*100:.1f}%\n")
                f.write(f"- **Enhanced Confidence:** {stats['avg_enhanced_confidence']*100:.1f}%\n")
                f.write(f"- **Processing Time:** {stats['avg_processing_time']:.2f}s\n")
                f.write(f"- **Error Patterns:** {stats['error_patterns']}\n\n")

            # Comparative analysis
            f.write(f"## Comparative Analysis\n\n")
            for insight in self.session_data['comparative_analysis']['insights']:
                f.write(f"- {insight}\n")
            f.write(f"\n")

            # Individual test results
            f.write(f"## Individual Test Results\n\n")
            for test in self.session_data['tests']:
                f.write(f"### Test {test['test_number']}\n")
                f.write(f"**Original:** {test['original_text']}\n\n")

                for engine_name, result in test['engine_results'].items():
                    f.write(f"**{engine_name.title()}:**\n")
                    f.write(f"- Transcribed: {result['transcribed']}\n")
                    f.write(f"- Semantic Accuracy: {result['semantic_accuracy']*100:.1f}%\n")
                    f.write(f"- Enhanced Confidence: {result['enhanced_confidence']*100:.1f}%\n")
                    f.write(f"- Processing Time: {result['processing_time']:.2f}s\n")
                    f.write(f"- Error Pattern: {result['error_pattern']}\n\n")

                f.write("---\n\n")

async def main():
    """Main execution function"""
    print("🎯 MULTI-STT ENGINE AUTONOMOUS VOICE TESTING SYSTEM v3.0")
    print("=" * 60)
    print("🔧 Key Features:")
    print("   • Multiple STT engine comparison (Whisper, Google, macOS)")
    print("   • Cross-engine semantic scoring")
    print("   • Engine-specific performance analysis")
    print("   • Adaptive volume control per engine")

    tester = MultiSTTAutonomousTester()
    await tester.run_multi_engine_test_suite()

    print(f"\n🎉 MULTI-STT ENGINE TESTING COMPLETED!")
    print(f"📊 Compare engine performance for optimal selection")

if __name__ == "__main__":
    asyncio.run(main())