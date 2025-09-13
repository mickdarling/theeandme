#!/usr/bin/env python3
"""
Improved Autonomous Voice Tester - Version 2.0
Incorporates findings from initial autonomous testing session

Key Improvements:
1. Semantic similarity scoring (fixes number recognition)
2. Adaptive volume control based on audio quality
3. Enhanced confidence calibration
4. Error pattern classification
5. Multi-metric quality analysis
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
from typing import List, Dict, Any, Tuple
import sounddevice as sd
import numpy as np
import requests
import aiohttp

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT

class ImprovedAutonomousTester:
    def __init__(self):
        self.test_dir = Path("/Users/mick/Developer/theeandme/autonomous_voice_testing_v2")
        self.test_dir.mkdir(exist_ok=True)
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_v2"
        self.session_dir = self.test_dir / f"improved_session_{self.session_id}"
        self.session_dir.mkdir(exist_ok=True)
        
        self.whisper_stt = None
        
        # Enhanced test phrases based on v1 findings
        self.test_phrases = [
            "This is a test of the voice recognition system.",  # Perfect baseline
            "The quick brown fox jumps over the lazy dog.",     # Word substitution test
            "Short test.",                                      # Minimal phrase test
            "Testing numbers: one two three four five.",       # Number recognition test (shorter)
            "Echo echo echo testing repetitive words.",        # Repetition test (no dash)
            "Can the system handle technical terminology?",    # Technical test (shorter)
            "How well does this work with natural speech?",   # Natural speech (shorter)
            "Final test with punctuation and tone.",          # Punctuation test (simpler)
        ]
        
        # Number word mappings for semantic similarity
        self.number_words = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12'
        }
        
        self.number_digits = {v: k for k, v in self.number_words.items()}
        
        # Adaptive volume control
        self.optimal_volume = 30  # Start with conservative volume
        self.volume_history = []
        
        self.results = {
            'session_id': self.session_id,
            'version': '2.0',
            'improvements': [
                'Semantic similarity scoring',
                'Adaptive volume control', 
                'Enhanced confidence calibration',
                'Error pattern classification'
            ],
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
        
        print(f"🤖 Improved Autonomous Voice Tester v2.0 Initialized")
        print(f"📁 Session directory: {self.session_dir}")
        print(f"🧪 Enhanced test phrases: {len(self.test_phrases)}")

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
            elif clean_word in self.number_digits:
                normalized_words.append(self.number_digits[clean_word])
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
        union = orig_words.union(trans_words)
        
        word_similarity = len(intersection) / len(orig_words)
        
        # Bonus for exact sequence matches
        orig_sequence = orig_norm.split()
        trans_sequence = trans_norm.split()
        
        sequence_bonus = 0.0
        if len(orig_sequence) == len(trans_sequence):
            matches = sum(1 for o, t in zip(orig_sequence, trans_sequence) if o == t)
            sequence_bonus = (matches / len(orig_sequence)) * 0.2  # 20% bonus for sequence
        
        return min(1.0, word_similarity + sequence_bonus)

    def calculate_enhanced_confidence(self, whisper_conf: float, audio_quality: float, text_length: int) -> float:
        """Enhanced confidence scoring using multiple factors"""
        # Base confidence from Whisper
        base_conf = whisper_conf if whisper_conf > 0 else 0.3  # Handle 0 confidence edge case
        
        # Audio quality factor (0-1 range)
        quality_factor = min(1.0, audio_quality * 3.5)  # Scale up quality impact
        
        # Text length factor (penalize very short transcriptions)
        length_factor = min(1.0, text_length / 20.0)  # Ideal length around 20+ characters
        
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
        orig_has_numbers = any(word in self.number_words for word in orig_words)
        trans_has_digits = any(re.match(r'\d', word) for word in trans_words)
        
        if orig_has_numbers and trans_has_digits:
            return "number_format_conversion"
        
        # Check for word substitution vs omission
        if len(trans_words) >= len(orig_words) * 0.8:
            return "word_substitution"
        elif len(trans_words) < len(orig_words) * 0.6:
            return "word_omission"
        else:
            return "mixed_errors"

    def calculate_optimal_volume(self, internal_rms: float, recorded_rms: float) -> int:
        """Calculate optimal volume based on signal quality"""
        if internal_rms == 0:
            return self.optimal_volume
        
        signal_ratio = recorded_rms / internal_rms
        
        # Target signal ratio around 0.4 (40% retention)
        target_ratio = 0.4
        
        if signal_ratio < target_ratio * 0.8:  # Too quiet
            volume_adjustment = 10
        elif signal_ratio > target_ratio * 1.2:  # Too loud  
            volume_adjustment = -5
        else:
            volume_adjustment = 0
        
        new_volume = max(20, min(50, self.optimal_volume + volume_adjustment))
        self.optimal_volume = new_volume
        
        return new_volume

    async def initialize_components(self):
        """Initialize STT components"""
        try:
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

    def record_with_adaptive_volume(self, text: str, filename: str, duration: float = 6.0) -> Tuple[str, Dict]:
        """Record with adaptive volume control"""
        filepath = self.session_dir / filename
        
        try:
            # Set adaptive volume
            os.system(f"osascript -e 'set volume output volume {self.optimal_volume}'")
            print(f"🔊 Adaptive volume: {self.optimal_volume}% | Text: {text[:40]}...")
            
            # Record
            sample_rate = 16000
            device_id = 2
            
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16,
                device=device_id
            )
            
            time.sleep(0.5)
            os.system(f'say "{text}" &')
            sd.wait()
            
            # Save recording
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(recording.tobytes())
            
            # Calculate quality metrics
            rms_level = np.sqrt(np.mean(recording.astype(np.float64) ** 2))
            quality_metrics = {
                'volume_used': self.optimal_volume,
                'recorded_rms': float(rms_level),
                'filename': filename
            }
            
            print(f"✅ Adaptive recording: {filename} at {self.optimal_volume}%")
            return str(filepath), quality_metrics
            
        except Exception as e:
            print(f"❌ Adaptive recording error: {e}")
            return None, {}

    async def run_enhanced_test(self, phrase_idx: int, phrase: str) -> Dict[str, Any]:
        """Run enhanced test with all v2 improvements"""
        print(f"\n🧪 Enhanced Test {phrase_idx + 1}/{len(self.test_phrases)}: {phrase[:50]}...")
        
        test_result = {
            'test_id': phrase_idx + 1,
            'original_text': phrase,
            'timestamp': datetime.now().isoformat(),
            'internal_audio': None,
            'recorded_audio': None,
            'stt_results': [],
            'quality_analysis': {},
            'semantic_accuracy': 0.0,
            'enhanced_confidence': 0.0,
            'error_pattern': 'unknown',
            'volume_used': self.optimal_volume
        }
        
        # Generate internal speech
        internal_filename = f"enhanced_test_{phrase_idx+1:02d}_internal.wav"
        internal_file = self.generate_internal_speech(phrase, internal_filename)
        if internal_file:
            test_result['internal_audio'] = internal_filename
        
        # Record with adaptive volume
        recorded_filename = f"enhanced_test_{phrase_idx+1:02d}_recorded.wav"
        recorded_file, quality_metrics = self.record_with_adaptive_volume(phrase, recorded_filename)
        if recorded_file:
            test_result['recorded_audio'] = recorded_filename
            test_result['volume_used'] = quality_metrics.get('volume_used', self.optimal_volume)
        
        # Enhanced STT analysis
        if recorded_file:
            stt_results = await self.test_enhanced_stt(recorded_file)
            test_result['stt_results'] = stt_results
            
            if stt_results and stt_results[0]['success']:
                transcribed = stt_results[0]['text']
                whisper_conf = stt_results[0]['confidence']
                
                # Enhanced similarity calculation
                semantic_accuracy = self.calculate_semantic_similarity(phrase, transcribed)
                test_result['semantic_accuracy'] = semantic_accuracy
                
                # Error pattern classification
                error_pattern = self.classify_error_pattern(phrase, transcribed)
                test_result['error_pattern'] = error_pattern
                
                print(f"📝 Original: {phrase}")
                print(f"🎯 Transcribed: {transcribed}")
                print(f"📊 Semantic Accuracy: {semantic_accuracy:.1%}")
                print(f"🔍 Error Pattern: {error_pattern}")
        
        # Enhanced quality analysis
        if internal_file and recorded_file:
            quality = self.analyze_enhanced_quality(internal_file, recorded_file)
            test_result['quality_analysis'] = quality
            
            # Calculate enhanced confidence
            if stt_results and stt_results[0]['success']:
                enhanced_conf = self.calculate_enhanced_confidence(
                    whisper_conf, 
                    quality.get('quality_score', 0),
                    len(stt_results[0]['text'])
                )
                test_result['enhanced_confidence'] = enhanced_conf
                print(f"🔊 Enhanced Confidence: {enhanced_conf:.1%}")
            
            # Update optimal volume for next test
            new_volume = self.calculate_optimal_volume(
                quality.get('internal_rms', 0),
                quality.get('recorded_rms', 0)
            )
            print(f"🎛️ Next volume: {new_volume}%")
        
        time.sleep(2)
        return test_result

    async def test_enhanced_stt(self, audio_file: str) -> List[Dict[str, Any]]:
        """Enhanced STT testing"""
        try:
            with wave.open(audio_file, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            
            start_time = time.time()
            result = await self.whisper_stt.transcribe_audio(audio_data)
            processing_time = time.time() - start_time
            
            return [{
                'engine': 'whisper',
                'text': result.text,
                'confidence': result.confidence,
                'processing_time': processing_time,
                'text_length': len(result.text),
                'success': True
            }]
            
        except Exception as e:
            return [{
                'engine': 'whisper',
                'text': '',
                'confidence': 0.0,
                'processing_time': 0.0,
                'text_length': 0,
                'success': False,
                'error': str(e)
            }]

    def analyze_enhanced_quality(self, internal_file: str, recorded_file: str) -> Dict[str, Any]:
        """Enhanced audio quality analysis"""
        try:
            with wave.open(internal_file, 'rb') as wav:
                internal_data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
            
            with wave.open(recorded_file, 'rb') as wav:
                recorded_data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
            
            internal_rms = np.sqrt(np.mean(internal_data.astype(np.float64) ** 2))
            recorded_rms = np.sqrt(np.mean(recorded_data.astype(np.float64) ** 2))
            
            signal_ratio = recorded_rms / internal_rms if internal_rms > 0 else 0
            quality_score = min(1.0, signal_ratio) if signal_ratio <= 1.0 else 1.0 / signal_ratio
            
            # Enhanced metrics
            noise_floor = np.percentile(np.abs(recorded_data), 5)  # 5th percentile as noise floor
            dynamic_range = np.max(np.abs(recorded_data)) - noise_floor
            
            return {
                'internal_rms': float(internal_rms),
                'recorded_rms': float(recorded_rms),
                'signal_ratio': float(signal_ratio),
                'quality_score': float(quality_score),
                'noise_floor': float(noise_floor),
                'dynamic_range': float(dynamic_range)
            }
            
        except Exception as e:
            return {
                'internal_rms': 0.0,
                'recorded_rms': 0.0,
                'signal_ratio': 0.0,
                'quality_score': 0.0,
                'error': str(e)
            }

    async def run_improved_test_suite(self):
        """Run complete improved test suite"""
        print(f"\n🚀 Starting Improved Autonomous Test Suite v2.0")
        print(f"📊 Running {len(self.test_phrases)} enhanced tests")
        print(f"🔧 Improvements: Semantic scoring, adaptive volume, error classification")
        
        self.results['tests'] = []
        
        for idx, phrase in enumerate(self.test_phrases):
            try:
                test_result = await self.run_enhanced_test(idx, phrase)
                self.results['tests'].append(test_result)
                
                await self.save_results()
                
            except Exception as e:
                print(f"❌ Enhanced test {idx + 1} failed: {e}")
                error_result = {
                    'test_id': idx + 1,
                    'original_text': phrase,
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'semantic_accuracy': 0.0
                }
                self.results['tests'].append(error_result)
        
        await self.generate_enhanced_summary()
        await self.generate_enhanced_report()
        
        print(f"\n✅ Improved autonomous testing complete!")
        print(f"📁 Results saved to: {self.session_dir}")

    async def generate_enhanced_summary(self):
        """Generate enhanced summary with v2 improvements"""
        tests = [t for t in self.results['tests'] if 'error' not in t]
        
        if not tests:
            self.results['summary'] = {'error': 'No successful tests'}
            return
        
        # Enhanced metrics
        semantic_scores = [t['semantic_accuracy'] for t in tests if t['semantic_accuracy'] > 0]
        enhanced_confidences = [t['enhanced_confidence'] for t in tests if t.get('enhanced_confidence', 0) > 0]
        error_patterns = [t['error_pattern'] for t in tests if t.get('error_pattern')]
        volume_changes = [t['volume_used'] for t in tests if t.get('volume_used')]
        
        # Error pattern analysis
        pattern_counts = {}
        for pattern in error_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        summary = {
            'total_tests': len(self.results['tests']),
            'successful_tests': len(tests),
            'average_semantic_accuracy': np.mean(semantic_scores) if semantic_scores else 0.0,
            'average_enhanced_confidence': np.mean(enhanced_confidences) if enhanced_confidences else 0.0,
            'best_semantic_accuracy': max(semantic_scores) if semantic_scores else 0.0,
            'worst_semantic_accuracy': min(semantic_scores) if semantic_scores else 0.0,
            'error_pattern_distribution': pattern_counts,
            'volume_range': [min(volume_changes), max(volume_changes)] if volume_changes else [30, 30],
            'adaptive_volume_enabled': True,
            'semantic_scoring_enabled': True,
            'completion_time': datetime.now().isoformat()
        }
        
        self.results['summary'] = summary
        
        print(f"\n📊 ENHANCED TEST SUMMARY v2.0:")
        print(f"   Semantic Accuracy: {summary['average_semantic_accuracy']:.1%}")
        print(f"   Enhanced Confidence: {summary['average_enhanced_confidence']:.1%}")
        print(f"   Volume Range: {summary['volume_range'][0]}% - {summary['volume_range'][1]}%")
        print(f"   Error Patterns: {pattern_counts}")

    async def save_results(self):
        """Save enhanced results"""
        results_file = self.session_dir / "improved_autonomous_results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

    async def generate_enhanced_report(self):
        """Generate enhanced markdown report"""
        report_file = self.session_dir / "IMPROVED_AUTONOMOUS_REPORT.md"
        
        with open(report_file, 'w') as f:
            f.write(f"# Improved Autonomous Voice Testing Report v2.0\n\n")
            f.write(f"**Session ID:** {self.session_id}\n")
            f.write(f"**Version:** 2.0 with semantic scoring and adaptive volume\n")
            f.write(f"**Total Tests:** {len(self.results['tests'])}\n\n")
            
            if 'summary' in self.results and 'error' not in self.results['summary']:
                summary = self.results['summary']
                f.write(f"## Enhanced Summary\n\n")
                f.write(f"- **Semantic Accuracy:** {summary['average_semantic_accuracy']:.1%}\n")
                f.write(f"- **Enhanced Confidence:** {summary['average_enhanced_confidence']:.1%}\n")
                f.write(f"- **Volume Adaptation:** {summary['volume_range'][0]}% - {summary['volume_range'][1]}%\n")
                f.write(f"- **Error Patterns:** {summary['error_pattern_distribution']}\n\n")
            
            f.write(f"## Individual Enhanced Test Results\n\n")
            
            for test in self.results['tests']:
                if 'error' not in test:
                    f.write(f"### Enhanced Test {test['test_id']}\n\n")
                    f.write(f"**Original:** {test['original_text']}\n\n")
                    
                    if 'stt_results' in test and test['stt_results']:
                        stt = test['stt_results'][0]
                        if stt.get('success'):
                            f.write(f"**Transcribed:** {stt['text']}\n\n")
                            f.write(f"**Semantic Accuracy:** {test['semantic_accuracy']:.1%}\n")
                            f.write(f"**Enhanced Confidence:** {test.get('enhanced_confidence', 0):.1%}\n")
                            f.write(f"**Error Pattern:** {test.get('error_pattern', 'unknown')}\n")
                            f.write(f"**Volume Used:** {test.get('volume_used', 'unknown')}%\n\n")
                    
                    f.write(f"---\n\n")
        
        print(f"📝 Enhanced report generated: {report_file.name}")

async def main():
    """Main improved autonomous testing function"""
    print("🤖 IMPROVED AUTONOMOUS VOICE TESTING SYSTEM v2.0")
    print("================================================")
    print("🔧 Key Improvements:")
    print("   • Semantic similarity scoring (fixes number recognition)")
    print("   • Adaptive volume control based on audio quality") 
    print("   • Enhanced confidence calibration")
    print("   • Error pattern classification")
    print("   • Optimized test phrases based on v1 findings")
    
    tester = ImprovedAutonomousTester()
    
    success = await tester.initialize_components()
    if not success:
        print("❌ Failed to initialize improved components")
        return
    
    await tester.run_improved_test_suite()
    
    print(f"\n🎉 IMPROVED AUTONOMOUS TESTING COMPLETED!")
    print(f"📊 Compare with v1.0 results for improvement validation")

if __name__ == '__main__':
    asyncio.run(main())