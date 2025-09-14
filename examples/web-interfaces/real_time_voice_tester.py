#!/usr/bin/env python3
"""
Real-Time Voice Pipeline Tester
LIVE TESTING with actual voice input and audio output

This provides real-time testing of the complete voice pipeline:
- Live microphone input (STT)
- Real-time processing
- Audio output (TTS)
- Performance measurement during live interaction

Measures actual user experience with real voice commands.
"""

import time
import json
import threading
import queue
import sys
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# Import pipeline components
try:
    from RealtimeSTT import AudioToTextRecorder
    STT_AVAILABLE = True
except ImportError:
    print("⚠️  RealtimeSTT not available - install with: pip install RealtimeSTT")
    STT_AVAILABLE = False

from semantic_voice_parser import SemanticVoiceParser
from enhanced_voice_automation import EnhancedVoiceAutomation
from ultra_fast_voice_automation import UltraFastVoiceAutomation
import subprocess
import tempfile
import os


@dataclass
class LiveTestMetrics:
    """Metrics for a single live voice test interaction"""
    test_id: str
    timestamp: str
    user_speech: str

    # Pipeline timing
    stt_start_time: float
    stt_end_time: float
    processing_start_time: float
    processing_end_time: float
    tts_start_time: float
    tts_end_time: float

    # Calculated times
    stt_duration_ms: float = 0.0
    processing_duration_ms: float = 0.0
    tts_duration_ms: float = 0.0
    total_response_time_ms: float = 0.0

    # Quality metrics
    intent_type: str = ""
    confidence_score: float = 0.0
    automation_success: bool = False
    tts_success: bool = False
    overall_success: bool = False

    # User experience
    meets_target_time: bool = False
    response_quality: str = ""  # excellent, good, poor
    processor_used: str = ""


class RealTimeVoiceTester:
    """Real-time voice pipeline testing with live audio"""

    def __init__(self, target_response_time_ms: int = 1000):
        self.target_response_time_ms = target_response_time_ms
        self.is_running = False
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Output directory
        self.output_dir = Path(f"realtime_voice_tests_{self.test_session_id}")
        self.output_dir.mkdir(exist_ok=True)

        # Components
        self.semantic_parser = SemanticVoiceParser()
        self.standard_automation = EnhancedVoiceAutomation()
        self.ultra_fast_automation = UltraFastVoiceAutomation()

        # STT setup
        self.stt_recorder = None
        self.setup_stt()

        # Test results
        self.live_test_results: List[LiveTestMetrics] = []
        self.current_test_count = 0

        # Performance targets
        self.performance_thresholds = {
            "excellent": 500,
            "good": 1000,
            "acceptable": 2000
        }

        # Threading for real-time processing
        self.test_queue = queue.Queue()
        self.result_queue = queue.Queue()

        print(f"🚀 Real-Time Voice Tester initialized")
        print(f"📁 Session directory: {self.output_dir}")
        print(f"🎯 Target response time: {self.target_response_time_ms}ms")

    def setup_stt(self):
        """Setup real-time STT recorder"""
        if not STT_AVAILABLE:
            print("❌ Cannot run real-time testing without RealtimeSTT")
            return False

        try:
            print("🔧 Setting up RealtimeSTT for live testing...")
            self.stt_recorder = AudioToTextRecorder(
                model="base.en",
                language="en",
                pre_recording_buffer_duration=0.3,  # 300ms buffer for complete sentences
                silero_sensitivity=0.4,
                webrtc_sensitivity=2,
                post_speech_silence_duration=0.7,  # Longer pause for real-time use
                min_length_of_recording=0.3,
                min_gap_between_recordings=0.1,
                sample_rate=16000,
                use_microphone=True,
                enable_realtime_transcription=True,
                spinner=False,
                level=20
            )
            print("✅ RealtimeSTT configured for live testing")
            return True
        except Exception as e:
            print(f"❌ Failed to setup STT: {e}")
            return False

    def generate_test_response(self, intent_type: str, command: str) -> str:
        """Generate appropriate TTS response based on intent"""
        responses = {
            "open_app": f"Opening the application as requested",
            "search_web": f"Searching for that information now",
            "create_note": "Creating a new note for you",
            "chat": "I'm here to help! What can I do for you?",
            "unknown": "I didn't quite understand that. Could you try again?",
            "error": "Sorry, I encountered an error processing that request"
        }

        return responses.get(intent_type, "Processing your request")

    def speak_response(self, text: str, metrics: LiveTestMetrics) -> bool:
        """Generate and play TTS response"""
        metrics.tts_start_time = time.time()

        try:
            # Create temporary file for TTS
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name

            # Generate TTS
            safe_text = text.replace('"', '\\"').replace("'", "\\'")
            tts_cmd = f'say "{safe_text}" -o "{temp_path}" --data-format=LEI16@16000'

            result = subprocess.run(tts_cmd, shell=True, capture_output=True, timeout=5)

            if result.returncode == 0:
                # Play the generated audio
                play_cmd = ['afplay', temp_path]
                subprocess.run(play_cmd, check=True, timeout=10)

                metrics.tts_end_time = time.time()
                metrics.tts_duration_ms = (metrics.tts_end_time - metrics.tts_start_time) * 1000

                # Clean up
                os.unlink(temp_path)
                return True
            else:
                metrics.tts_end_time = time.time()
                metrics.tts_duration_ms = (metrics.tts_end_time - metrics.tts_start_time) * 1000
                print(f"❌ TTS generation failed: {result.stderr}")
                return False

        except Exception as e:
            metrics.tts_end_time = time.time()
            metrics.tts_duration_ms = (metrics.tts_end_time - metrics.tts_start_time) * 1000
            print(f"❌ TTS error: {e}")
            return False

    def process_voice_command(self, voice_text: str, use_ultra_fast: bool = False) -> LiveTestMetrics:
        """Process a single voice command and measure performance"""

        self.current_test_count += 1
        test_id = f"live_test_{self.current_test_count:03d}"

        # Initialize metrics
        metrics = LiveTestMetrics(
            test_id=test_id,
            timestamp=datetime.now().isoformat(),
            user_speech=voice_text,
            stt_start_time=time.time(),  # STT already completed
            stt_end_time=time.time(),
            processing_start_time=0,
            processing_end_time=0,
            tts_start_time=0,
            tts_end_time=0,
            processor_used="ultra_fast" if use_ultra_fast else "standard"
        )

        # STT is already done, so duration is 0 for this measurement
        metrics.stt_duration_ms = 0  # We measure STT separately in the main loop

        try:
            # Semantic processing and automation
            metrics.processing_start_time = time.time()

            if use_ultra_fast:
                # Ultra-fast processing
                response = self.ultra_fast_automation.process_voice_command(voice_text, execute=False)
                metrics.intent_type = response.intent_type
                metrics.confidence_score = response.confidence
                metrics.automation_success = response.intent_type != "unknown"

                response_text = response.conversational_text

            else:
                # Standard processing
                intent = self.semantic_parser.parse_voice_command(voice_text)
                result = self.standard_automation.execute_voice_command(voice_text)

                metrics.intent_type = intent.intent_type
                metrics.confidence_score = intent.confidence
                metrics.automation_success = result.get('success', False)

                response_text = self.generate_test_response(intent.intent_type, voice_text)

            metrics.processing_end_time = time.time()
            metrics.processing_duration_ms = (metrics.processing_end_time - metrics.processing_start_time) * 1000

            # TTS response
            metrics.tts_success = self.speak_response(response_text, metrics)

            # Calculate total response time
            total_start = metrics.processing_start_time  # We don't include STT time here
            total_end = metrics.tts_end_time
            metrics.total_response_time_ms = (total_end - total_start) * 1000

            # Quality assessment
            metrics.overall_success = (
                metrics.automation_success and
                metrics.tts_success and
                metrics.confidence_score > 0.5
            )

            metrics.meets_target_time = metrics.total_response_time_ms <= self.target_response_time_ms

            # Response quality classification
            if metrics.total_response_time_ms <= self.performance_thresholds["excellent"]:
                metrics.response_quality = "excellent"
            elif metrics.total_response_time_ms <= self.performance_thresholds["good"]:
                metrics.response_quality = "good"
            elif metrics.total_response_time_ms <= self.performance_thresholds["acceptable"]:
                metrics.response_quality = "acceptable"
            else:
                metrics.response_quality = "poor"

        except Exception as e:
            metrics.processing_end_time = time.time()
            metrics.processing_duration_ms = (metrics.processing_end_time - metrics.processing_start_time) * 1000
            metrics.overall_success = False
            metrics.response_quality = "error"
            print(f"❌ Processing error: {e}")

        return metrics

    def run_live_testing_session(self, use_ultra_fast: bool = False, max_tests: int = None) -> List[LiveTestMetrics]:
        """Run an interactive live testing session"""

        if not self.stt_recorder:
            print("❌ Cannot run live testing - STT not available")
            return []

        processor_type = "Ultra-Fast" if use_ultra_fast else "Standard"
        print(f"\n🎙️  STARTING LIVE VOICE TESTING SESSION")
        print("="*60)
        print(f"🔧 Processor: {processor_type}")
        print(f"🎯 Target Response Time: {self.target_response_time_ms}ms")
        print(f"📊 Max Tests: {max_tests if max_tests else 'Unlimited'}")
        print("="*60)
        print()
        print("🎤 INSTRUCTIONS:")
        print("• Speak naturally into your microphone")
        print("• Wait for the system to respond before speaking again")
        print("• Try various commands: 'Open Chrome', 'Search for Python'")
        print("• Press Ctrl+C to end the session")
        print()
        print("🚀 Starting live voice recognition...")
        print("💡 Speak now!")
        print("-"*60)

        self.is_running = True
        test_count = 0

        # Setup signal handler for graceful exit
        def signal_handler(sig, frame):
            print("\n🛑 Stopping live testing session...")
            self.is_running = False

        signal.signal(signal.SIGINT, signal_handler)

        try:
            while self.is_running and (max_tests is None or test_count < max_tests):
                try:
                    print(f"\n[Test {test_count + 1}] 🎤 Listening...")

                    # Measure STT time
                    stt_start_time = time.time()
                    voice_text = self.stt_recorder.text()
                    stt_end_time = time.time()
                    stt_duration = (stt_end_time - stt_start_time) * 1000

                    if voice_text and voice_text.strip():
                        test_count += 1
                        print(f"📝 Heard: '{voice_text}' (STT: {stt_duration:.0f}ms)")

                        # Process the command and measure performance
                        metrics = self.process_voice_command(voice_text, use_ultra_fast)

                        # Update STT timing in metrics
                        metrics.stt_duration_ms = stt_duration
                        metrics.total_response_time_ms += stt_duration  # Add STT to total

                        # Store results
                        self.live_test_results.append(metrics)

                        # Display real-time results
                        print(f"🧠 Intent: {metrics.intent_type} (confidence: {metrics.confidence_score:.2f})")
                        print(f"⚡ Times: STT={metrics.stt_duration_ms:.0f}ms | "
                              f"Processing={metrics.processing_duration_ms:.0f}ms | "
                              f"TTS={metrics.tts_duration_ms:.0f}ms")
                        print(f"🏁 Total: {metrics.total_response_time_ms:.0f}ms "
                              f"({metrics.response_quality.upper()})")
                        print(f"🎯 Target: {'✅ MET' if metrics.meets_target_time else '❌ MISSED'} "
                              f"({self.target_response_time_ms}ms)")

                        # Live statistics
                        if len(self.live_test_results) > 1:
                            recent_times = [r.total_response_time_ms for r in self.live_test_results[-5:]]
                            avg_recent = sum(recent_times) / len(recent_times)
                            print(f"📊 Recent Avg: {avg_recent:.0f}ms (last {len(recent_times)} tests)")

                        print("-"*60)

                        # Brief pause before next test
                        time.sleep(1)

                except Exception as e:
                    print(f"❌ Error during live test: {e}")
                    continue

        except KeyboardInterrupt:
            print("\n🛑 Live testing interrupted by user")

        self.is_running = False

        # Generate session summary
        if self.live_test_results:
            self.display_session_summary()
            self.save_live_test_results()

        return self.live_test_results

    def display_session_summary(self):
        """Display summary of live testing session"""
        if not self.live_test_results:
            return

        print(f"\n📊 LIVE TESTING SESSION SUMMARY")
        print("="*50)
        print(f"Session ID: {self.test_session_id}")
        print(f"Total Tests: {len(self.live_test_results)}")

        # Calculate summary statistics
        total_times = [r.total_response_time_ms for r in self.live_test_results]
        stt_times = [r.stt_duration_ms for r in self.live_test_results]
        processing_times = [r.processing_duration_ms for r in self.live_test_results]
        tts_times = [r.tts_duration_ms for r in self.live_test_results]

        successful_tests = [r for r in self.live_test_results if r.overall_success]
        target_met_tests = [r for r in self.live_test_results if r.meets_target_time]

        print(f"Success Rate: {len(successful_tests)}/{len(self.live_test_results)} "
              f"({len(successful_tests)/len(self.live_test_results)*100:.1f}%)")
        print(f"Target Met: {len(target_met_tests)}/{len(self.live_test_results)} "
              f"({len(target_met_tests)/len(self.live_test_results)*100:.1f}%)")

        print(f"\nTIMING BREAKDOWN:")
        print(f"  Average Total: {sum(total_times)/len(total_times):.0f}ms")
        print(f"  Average STT: {sum(stt_times)/len(stt_times):.0f}ms")
        print(f"  Average Processing: {sum(processing_times)/len(processing_times):.0f}ms")
        print(f"  Average TTS: {sum(tts_times)/len(tts_times):.0f}ms")

        print(f"\nPERFORMAN DISTRIBUTION:")
        excellent = sum(1 for r in self.live_test_results if r.response_quality == "excellent")
        good = sum(1 for r in self.live_test_results if r.response_quality == "good")
        acceptable = sum(1 for r in self.live_test_results if r.response_quality == "acceptable")
        poor = sum(1 for r in self.live_test_results if r.response_quality == "poor")

        print(f"  Excellent (<500ms): {excellent}")
        print(f"  Good (<1000ms): {good}")
        print(f"  Acceptable (<2000ms): {acceptable}")
        print(f"  Poor (>2000ms): {poor}")

        # Best and worst tests
        best_test = min(self.live_test_results, key=lambda x: x.total_response_time_ms)
        worst_test = max(self.live_test_results, key=lambda x: x.total_response_time_ms)

        print(f"\nBEST TEST: '{best_test.user_speech}' - {best_test.total_response_time_ms:.0f}ms")
        print(f"WORST TEST: '{worst_test.user_speech}' - {worst_test.total_response_time_ms:.0f}ms")

    def save_live_test_results(self):
        """Save live test results to files"""

        # Save detailed JSON results
        results_file = self.output_dir / "live_test_results.json"
        results_data = {
            "session_info": {
                "session_id": self.test_session_id,
                "start_time": self.live_test_results[0].timestamp if self.live_test_results else None,
                "end_time": self.live_test_results[-1].timestamp if self.live_test_results else None,
                "total_tests": len(self.live_test_results),
                "target_response_time_ms": self.target_response_time_ms
            },
            "test_results": [asdict(result) for result in self.live_test_results]
        }

        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        # Save CSV summary
        csv_file = self.output_dir / "live_test_summary.csv"
        with open(csv_file, 'w') as f:
            f.write("test_id,timestamp,command,intent_type,confidence,stt_ms,processing_ms,tts_ms,total_ms,success,meets_target,quality,processor\n")
            for result in self.live_test_results:
                f.write(f"{result.test_id},{result.timestamp},{result.user_speech},{result.intent_type},")
                f.write(f"{result.confidence_score},{result.stt_duration_ms},{result.processing_duration_ms},")
                f.write(f"{result.tts_duration_ms},{result.total_response_time_ms},{result.overall_success},")
                f.write(f"{result.meets_target_time},{result.response_quality},{result.processor_used}\n")

        print(f"\n💾 Live test results saved:")
        print(f"📊 Detailed results: {results_file}")
        print(f"📈 CSV summary: {csv_file}")

    def run_comparative_live_test(self, tests_per_processor: int = 10) -> Dict[str, List[LiveTestMetrics]]:
        """Run comparative testing between standard and ultra-fast processors"""

        print(f"\n🔬 COMPARATIVE LIVE TESTING")
        print("="*60)
        print(f"Testing both processors with {tests_per_processor} tests each")
        print("This will help determine which processor performs better in real-world use")
        print("="*60)

        results = {}

        # Test standard processor
        print(f"\n📋 PHASE 1: Testing Standard Processor")
        input("Press Enter when ready to begin standard processor testing...")
        results['standard'] = self.run_live_testing_session(use_ultra_fast=False, max_tests=tests_per_processor)

        if results['standard']:
            # Reset for next phase
            time.sleep(2)

            # Test ultra-fast processor
            print(f"\n📋 PHASE 2: Testing Ultra-Fast Processor")
            input("Press Enter when ready to begin ultra-fast processor testing...")
            results['ultra_fast'] = self.run_live_testing_session(use_ultra_fast=True, max_tests=tests_per_processor)

        # Generate comparison
        if results['standard'] and results['ultra_fast']:
            self.display_comparative_results(results['standard'], results['ultra_fast'])

        return results

    def display_comparative_results(self, standard_results: List[LiveTestMetrics],
                                  ultra_fast_results: List[LiveTestMetrics]):
        """Display comparison between standard and ultra-fast results"""

        def calculate_stats(results):
            times = [r.total_response_time_ms for r in results]
            successes = sum(1 for r in results if r.overall_success)
            targets_met = sum(1 for r in results if r.meets_target_time)

            return {
                'avg_time': sum(times) / len(times) if times else 0,
                'min_time': min(times) if times else 0,
                'max_time': max(times) if times else 0,
                'success_rate': successes / len(results) if results else 0,
                'target_rate': targets_met / len(results) if results else 0,
                'total_tests': len(results)
            }

        standard_stats = calculate_stats(standard_results)
        ultra_fast_stats = calculate_stats(ultra_fast_results)

        print(f"\n🔍 COMPARATIVE RESULTS ANALYSIS")
        print("="*60)
        print(f"{'Metric':<25} {'Standard':<15} {'Ultra-Fast':<15} {'Improvement'}")
        print("-"*60)

        # Response time comparison
        time_improvement = ((standard_stats['avg_time'] - ultra_fast_stats['avg_time']) /
                          standard_stats['avg_time']) * 100 if standard_stats['avg_time'] > 0 else 0
        print(f"{'Average Response Time':<25} {standard_stats['avg_time']:<15.0f} {ultra_fast_stats['avg_time']:<15.0f} {time_improvement:+.1f}%")

        # Success rate comparison
        success_improvement = (ultra_fast_stats['success_rate'] - standard_stats['success_rate']) * 100
        print(f"{'Success Rate':<25} {standard_stats['success_rate']*100:<15.1f} {ultra_fast_stats['success_rate']*100:<15.1f} {success_improvement:+.1f}%")

        # Target achievement comparison
        target_improvement = (ultra_fast_stats['target_rate'] - standard_stats['target_rate']) * 100
        print(f"{'Target Achievement':<25} {standard_stats['target_rate']*100:<15.1f} {ultra_fast_stats['target_rate']*100:<15.1f} {target_improvement:+.1f}%")

        print("\n📊 RECOMMENDATION:")
        if time_improvement > 15 and ultra_fast_stats['success_rate'] >= standard_stats['success_rate']:
            print("✅ ULTRA-FAST PROCESSOR RECOMMENDED: Significant speed improvement with maintained reliability")
        elif time_improvement > 5 and ultra_fast_stats['success_rate'] >= 0.8:
            print("⚡ ULTRA-FAST PROCESSOR BENEFICIAL: Moderate improvement, good for production")
        elif ultra_fast_stats['success_rate'] < standard_stats['success_rate'] - 0.1:
            print("⚠️  ULTRA-FAST PROCESSOR NOT RECOMMENDED: Reliability concerns outweigh speed gains")
        else:
            print("🔍 RESULTS INCONCLUSIVE: More testing needed to determine best processor")


def main():
    """Main function for real-time voice testing"""
    print("🎙️  Real-Time Voice Pipeline Tester")
    print("="*50)
    print("This tool provides live testing of the complete voice pipeline")
    print("with actual microphone input and audio output.")
    print("")

    if not STT_AVAILABLE:
        print("❌ RealtimeSTT not available. Install with:")
        print("   pip install RealtimeSTT")
        return

    print("Available testing modes:")
    print("1. Single processor live testing")
    print("2. Comparative testing (standard vs ultra-fast)")
    print("3. Custom testing session")
    print("")

    choice = input("Select testing mode (1/2/3): ").strip()

    tester = RealTimeVoiceTester(target_response_time_ms=1000)

    try:
        if choice == "1":
            processor_choice = input("Use ultra-fast processor? (y/N): ").strip().lower()
            use_ultra_fast = processor_choice == 'y'

            max_tests_input = input("Maximum tests (Enter for unlimited): ").strip()
            max_tests = int(max_tests_input) if max_tests_input else None

            tester.run_live_testing_session(use_ultra_fast=use_ultra_fast, max_tests=max_tests)

        elif choice == "2":
            tests_per_processor = input("Tests per processor (default 5): ").strip()
            tests_per_processor = int(tests_per_processor) if tests_per_processor else 5

            tester.run_comparative_live_test(tests_per_processor=tests_per_processor)

        elif choice == "3":
            print("Custom testing options:")
            target_time = input("Target response time ms (default 1000): ").strip()
            target_time = int(target_time) if target_time else 1000

            tester.target_response_time_ms = target_time

            processor_choice = input("Use ultra-fast processor? (y/N): ").strip().lower()
            use_ultra_fast = processor_choice == 'y'

            max_tests_input = input("Maximum tests (Enter for unlimited): ").strip()
            max_tests = int(max_tests_input) if max_tests_input else None

            tester.run_live_testing_session(use_ultra_fast=use_ultra_fast, max_tests=max_tests)

        else:
            print("Invalid choice. Exiting.")
            return

    except KeyboardInterrupt:
        print("\n🛑 Testing stopped by user")
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")

    print("\n✅ Real-time testing complete!")


if __name__ == "__main__":
    main()