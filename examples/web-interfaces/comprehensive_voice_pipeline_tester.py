#!/usr/bin/env python3
"""
Comprehensive Voice Pipeline Performance Testing Framework
FULL END-TO-END VOICE AUTOMATION TESTING

Tests the complete voice-to-response pipeline:
1. STT (Speech-to-Text) - RealtimeSTT with pre-recording buffer
2. Processing - Semantic parser + Voice automation
3. TTS (Text-to-Speech) - macOS say command
4. Echo Prevention - Advanced echo blocking

Measures:
- Total response time (voice in → voice out)
- Component breakdown (STT time, processing time, TTS time)
- Success/failure rates
- User experience metrics
- Performance under different conditions
"""

import time
import json
import threading
import subprocess
import asyncio
import statistics
import wave
import tempfile
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# Import pipeline components
try:
    from RealtimeSTT import AudioToTextRecorder
    STT_AVAILABLE = True
except ImportError:
    print("⚠️  RealtimeSTT not available - will use mock STT for testing")
    STT_AVAILABLE = False

from semantic_voice_parser import SemanticVoiceParser, CommandIntent
from enhanced_voice_automation import EnhancedVoiceAutomation
from ultra_fast_voice_automation import UltraFastVoiceAutomation


@dataclass
class PipelineMetrics:
    """Comprehensive metrics for voice pipeline performance"""
    # Test identification
    test_id: str
    test_command: str
    test_category: str
    timestamp: str

    # Component timing (milliseconds)
    stt_time_ms: float = 0.0
    processing_time_ms: float = 0.0
    tts_time_ms: float = 0.0
    total_response_time_ms: float = 0.0

    # Quality metrics
    stt_accuracy: Optional[float] = None  # Transcription accuracy if known
    processing_success: bool = False
    intent_confidence: float = 0.0
    automation_success: bool = False
    tts_success: bool = False

    # Pipeline status
    overall_success: bool = False
    error_occurred: bool = False
    error_message: str = ""

    # Performance classification
    response_speed_class: str = ""  # "excellent" (<500ms), "good" (<1000ms), "slow" (>1000ms)
    meets_target: bool = False  # Whether meets <500ms target for simple commands

    # Additional context
    processor_used: str = ""  # "standard" or "ultra_fast"
    test_conditions: Dict[str, Any] = None


@dataclass
class TestScenario:
    """Test scenario configuration"""
    name: str
    commands: List[str]
    expected_intent_types: List[str]
    category: str
    target_time_ms: int = 1000  # Default target response time
    description: str = ""


class MockSTTRecorder:
    """Mock STT recorder for testing when RealtimeSTT not available"""

    def __init__(self, test_phrases: List[str]):
        self.test_phrases = test_phrases
        self.current_index = 0

    def get_next_transcription(self, simulate_delay_ms: int = 300) -> str:
        """Get next test phrase with simulated STT delay"""
        if self.current_index >= len(self.test_phrases):
            self.current_index = 0  # Loop back

        phrase = self.test_phrases[self.current_index]
        self.current_index += 1

        # Simulate STT processing time
        time.sleep(simulate_delay_ms / 1000.0)

        return phrase


class VoicePipelineTester:
    """Comprehensive testing framework for the complete voice pipeline"""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else Path(f"voice_pipeline_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.output_dir.mkdir(exist_ok=True)

        # Initialize components
        self.semantic_parser = SemanticVoiceParser()
        self.standard_automation = EnhancedVoiceAutomation()
        self.ultra_fast_automation = UltraFastVoiceAutomation()

        # STT setup
        self.stt_recorder = None
        self.mock_stt = None
        self.setup_stt()

        # Test results storage
        self.test_results: List[PipelineMetrics] = []
        self.session_start = datetime.now()

        # Performance targets
        self.performance_targets = {
            "excellent": 500,  # <500ms for simple commands
            "good": 1000,      # <1000ms for complex commands
            "acceptable": 2000  # <2s for very complex commands
        }

        print(f"🧪 Voice Pipeline Tester initialized")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🦙 Semantic parser available: {self.semantic_parser.is_available}")
        print(f"🎤 STT available: {STT_AVAILABLE}")

    def setup_stt(self):
        """Setup STT component (real or mock)"""
        if STT_AVAILABLE:
            try:
                print("🔧 Setting up RealtimeSTT...")
                self.stt_recorder = AudioToTextRecorder(
                    model="base.en",
                    language="en",
                    pre_recording_buffer_duration=0.3,  # 300ms buffer
                    silero_sensitivity=0.4,
                    webrtc_sensitivity=2,
                    post_speech_silence_duration=0.3,
                    min_length_of_recording=0.1,
                    sample_rate=16000,
                    use_microphone=True,
                    enable_realtime_transcription=True,
                    spinner=False,
                    level=20
                )
                print("✅ RealtimeSTT ready for live testing")
            except Exception as e:
                print(f"⚠️  RealtimeSTT setup failed: {e}")
                self.setup_mock_stt()
        else:
            self.setup_mock_stt()

    def setup_mock_stt(self):
        """Setup mock STT for testing without microphone"""
        test_phrases = [
            "Open Chrome",
            "Search for Python tutorials",
            "Launch Safari browser",
            "Create a note about today's meeting",
            "Open Chrome and search for machine learning",
            "Start Terminal application",
            "Search for voice recognition tools",
            "Open the Notes app",
            "Find documentation for React",
            "Launch the calculator"
        ]
        self.mock_stt = MockSTTRecorder(test_phrases)
        print("✅ Mock STT ready for testing")

    def measure_stt_performance(self, test_phrase: Optional[str] = None) -> Tuple[str, float]:
        """Measure STT performance - either live or mock"""
        start_time = time.time()

        try:
            if self.stt_recorder and test_phrase is None:
                # Live STT transcription
                print("🎤 Listening for voice input...")
                transcribed_text = self.stt_recorder.text()
            else:
                # Mock STT or predefined phrase
                if self.mock_stt:
                    transcribed_text = self.mock_stt.get_next_transcription()
                else:
                    transcribed_text = test_phrase or "Open Chrome"
                    time.sleep(0.3)  # Simulate STT delay

            stt_time = (time.time() - start_time) * 1000
            return transcribed_text, stt_time

        except Exception as e:
            stt_time = (time.time() - start_time) * 1000
            print(f"❌ STT error: {e}")
            return "", stt_time

    def measure_processing_performance(self, text: str, use_ultra_fast: bool = False) -> Tuple[CommandIntent, float, bool]:
        """Measure semantic processing and automation performance"""
        start_time = time.time()

        try:
            # Parse voice command
            intent = self.semantic_parser.parse_voice_command(text)
            parse_time = (time.time() - start_time) * 1000

            # Execute automation (safe mode for testing)
            if use_ultra_fast:
                automation_start = time.time()
                response = self.ultra_fast_automation.process_voice_command(text, execute=False)
                automation_success = response.intent_type != "unknown"
                processor = "ultra_fast"
            else:
                automation_start = time.time()
                result = self.standard_automation.execute_voice_command(text)
                automation_success = result.get('success', False)
                processor = "standard"

            automation_time = (time.time() - automation_start) * 1000
            total_processing_time = parse_time + automation_time

            # Add processor info to intent
            intent.parameters = intent.parameters or {}
            intent.parameters['processor_used'] = processor
            intent.parameters['automation_success'] = automation_success
            intent.parameters['automation_time_ms'] = automation_time

            return intent, total_processing_time, automation_success

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            print(f"❌ Processing error: {e}")

            # Return failed intent
            failed_intent = CommandIntent(
                intent_type="error",
                primary_action="error",
                raw_command=text,
                confidence=0.0,
                parameters={'error': str(e)}
            )
            return failed_intent, processing_time, False

    def measure_tts_performance(self, response_text: str) -> Tuple[bool, float]:
        """Measure TTS performance"""
        start_time = time.time()

        try:
            # Create temporary file for TTS output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name

            # Generate TTS without playing (for testing speed)
            safe_text = response_text.replace('"', '\\"').replace("'", "\\'")
            cmd = f'say "{safe_text}" -o "{temp_path}" --data-format=LEI16@16000'

            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)

            tts_time = (time.time() - start_time) * 1000
            success = result.returncode == 0

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

            return success, tts_time

        except subprocess.TimeoutExpired:
            tts_time = (time.time() - start_time) * 1000
            print("⏰ TTS timeout")
            return False, tts_time
        except Exception as e:
            tts_time = (time.time() - start_time) * 1000
            print(f"❌ TTS error: {e}")
            return False, tts_time

    def run_single_pipeline_test(self,
                                test_command: Optional[str] = None,
                                test_category: str = "general",
                                use_ultra_fast: bool = False,
                                target_time_ms: int = 1000) -> PipelineMetrics:
        """Run a complete end-to-end pipeline test"""

        test_id = f"test_{len(self.test_results) + 1}_{int(time.time() * 1000)}"
        overall_start_time = time.time()

        print(f"\n🚀 Running Pipeline Test: {test_id}")
        print(f"📝 Command: {test_command or 'Live voice input'}")
        print(f"⚡ Processor: {'Ultra-Fast' if use_ultra_fast else 'Standard'}")

        # Initialize metrics
        metrics = PipelineMetrics(
            test_id=test_id,
            test_command=test_command or "live_input",
            test_category=test_category,
            timestamp=datetime.now().isoformat(),
            processor_used="ultra_fast" if use_ultra_fast else "standard",
            test_conditions={"target_time_ms": target_time_ms}
        )

        try:
            # Step 1: STT (Speech-to-Text)
            print("🎤 Step 1: Speech-to-Text")
            transcribed_text, stt_time = self.measure_stt_performance(test_command)
            metrics.stt_time_ms = stt_time

            if not transcribed_text:
                raise Exception("STT failed - no transcription")

            print(f"   ✅ STT: '{transcribed_text}' ({stt_time:.0f}ms)")
            metrics.test_command = transcribed_text  # Update with actual transcription

            # Step 2: Processing (Semantic parsing + Automation)
            print("🧠 Step 2: Semantic Processing + Automation")
            intent, processing_time, automation_success = self.measure_processing_performance(
                transcribed_text, use_ultra_fast
            )
            metrics.processing_time_ms = processing_time
            metrics.processing_success = intent.intent_type != "error"
            metrics.intent_confidence = intent.confidence
            metrics.automation_success = automation_success

            print(f"   ✅ Processing: {intent.intent_type} (confidence: {intent.confidence:.2f}, {processing_time:.0f}ms)")

            # Step 3: TTS (Text-to-Speech)
            print("🔊 Step 3: Text-to-Speech")
            response_text = self.generate_response_text(intent)
            tts_success, tts_time = self.measure_tts_performance(response_text)
            metrics.tts_time_ms = tts_time
            metrics.tts_success = tts_success

            print(f"   ✅ TTS: '{response_text}' ({tts_time:.0f}ms)")

            # Calculate total metrics
            total_time = (time.time() - overall_start_time) * 1000
            metrics.total_response_time_ms = total_time
            metrics.overall_success = (
                metrics.processing_success and
                metrics.automation_success and
                metrics.tts_success
            )

            # Performance classification
            metrics.response_speed_class = self.classify_response_speed(total_time)
            metrics.meets_target = total_time <= target_time_ms

            print(f"🏁 Total Pipeline Time: {total_time:.0f}ms")
            print(f"🎯 Performance: {metrics.response_speed_class.upper()}")
            print(f"📊 Target Met: {'✅' if metrics.meets_target else '❌'} ({target_time_ms}ms)")

        except Exception as e:
            metrics.error_occurred = True
            metrics.error_message = str(e)
            metrics.overall_success = False
            total_time = (time.time() - overall_start_time) * 1000
            metrics.total_response_time_ms = total_time

            print(f"❌ Pipeline test failed: {e}")

        # Store results
        self.test_results.append(metrics)
        return metrics

    def generate_response_text(self, intent: CommandIntent) -> str:
        """Generate appropriate response text based on intent"""
        if intent.parameters and 'response' in intent.parameters:
            return intent.parameters['response']

        response_templates = {
            "open_app": f"Opening {intent.target_app or 'application'}",
            "search_web": f"Searching for {intent.search_query or 'information'}",
            "create_note": "Creating a new note",
            "chat": "I'm here to help!",
            "unknown": "I didn't understand that command",
            "error": "Sorry, there was an error processing your request"
        }

        return response_templates.get(intent.intent_type, "Command processed")

    def classify_response_speed(self, total_time_ms: float) -> str:
        """Classify response speed"""
        if total_time_ms <= self.performance_targets["excellent"]:
            return "excellent"
        elif total_time_ms <= self.performance_targets["good"]:
            return "good"
        elif total_time_ms <= self.performance_targets["acceptable"]:
            return "acceptable"
        else:
            return "slow"

    def run_test_scenario(self, scenario: TestScenario, use_ultra_fast: bool = False) -> Dict[str, Any]:
        """Run a complete test scenario with multiple commands"""
        print(f"\n🧪 Running Test Scenario: {scenario.name}")
        print(f"📋 Description: {scenario.description}")
        print(f"📝 Commands: {len(scenario.commands)}")
        print(f"⏱️  Target: {scenario.target_time_ms}ms")

        scenario_results = []

        for i, command in enumerate(scenario.commands):
            print(f"\n--- Command {i+1}/{len(scenario.commands)} ---")

            # Use expected intent type for validation if available
            expected_intent = scenario.expected_intent_types[i] if i < len(scenario.expected_intent_types) else None

            metrics = self.run_single_pipeline_test(
                test_command=command,
                test_category=scenario.category,
                use_ultra_fast=use_ultra_fast,
                target_time_ms=scenario.target_time_ms
            )

            scenario_results.append(metrics)

            # Validate against expected intent if provided
            if expected_intent and metrics.processing_success:
                intent_match = expected_intent in [metrics.test_command]  # Simple validation
                print(f"🎯 Expected intent validation: {'✅' if intent_match else '❌'}")

        # Calculate scenario summary
        successful_tests = sum(1 for m in scenario_results if m.overall_success)
        avg_response_time = statistics.mean([m.total_response_time_ms for m in scenario_results])
        target_met_count = sum(1 for m in scenario_results if m.meets_target)

        scenario_summary = {
            "scenario_name": scenario.name,
            "total_commands": len(scenario.commands),
            "successful_commands": successful_tests,
            "success_rate": (successful_tests / len(scenario.commands)) * 100,
            "average_response_time_ms": avg_response_time,
            "targets_met": target_met_count,
            "target_success_rate": (target_met_count / len(scenario.commands)) * 100,
            "results": scenario_results
        }

        print(f"\n📊 Scenario Summary: {scenario.name}")
        print(f"   Success Rate: {scenario_summary['success_rate']:.1f}%")
        print(f"   Avg Response: {avg_response_time:.0f}ms")
        print(f"   Targets Met: {target_met_count}/{len(scenario.commands)}")

        return scenario_summary

    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete comprehensive test suite"""
        print("\n🚀 COMPREHENSIVE VOICE PIPELINE TEST SUITE")
        print("="*80)
        print("🎯 Testing complete voice-to-response pipeline")
        print("📊 Measuring STT, Processing, TTS, and Total Response Time")
        print("="*80)

        # Define test scenarios
        scenarios = [
            TestScenario(
                name="Basic App Commands",
                commands=[
                    "Open Chrome",
                    "Launch Safari",
                    "Start Terminal",
                    "Open Calculator"
                ],
                expected_intent_types=["open_app", "open_app", "open_app", "open_app"],
                category="app_opening",
                target_time_ms=500,  # Fast target for simple commands
                description="Simple app opening commands - should be very fast"
            ),

            TestScenario(
                name="Web Search Commands",
                commands=[
                    "Search for Python tutorials",
                    "Google machine learning",
                    "Find React documentation",
                    "Look up voice recognition tools"
                ],
                expected_intent_types=["search_web", "search_web", "search_web", "search_web"],
                category="web_search",
                target_time_ms=800,
                description="Web search commands with query processing"
            ),

            TestScenario(
                name="Complex Multi-Step Commands",
                commands=[
                    "Open Chrome and search for Python tutorials",
                    "Launch Safari and find machine learning courses",
                    "Create a note about today's meeting and add agenda items"
                ],
                expected_intent_types=["multi_step", "multi_step", "multi_step"],
                category="multi_step",
                target_time_ms=1500,
                description="Complex commands requiring multiple operations"
            ),

            TestScenario(
                name="Conversational Commands",
                commands=[
                    "Hello, how are you?",
                    "Thank you for your help",
                    "Can you help me with something?",
                    "What can you do for me?"
                ],
                expected_intent_types=["chat", "chat", "chat", "chat"],
                category="conversation",
                target_time_ms=600,
                description="Natural conversation and chat interactions"
            ),

            TestScenario(
                name="Edge Cases and Error Handling",
                commands=[
                    "",  # Empty command
                    "asdkfjaoisdfjaosidjf",  # Gibberish
                    "Delete all my files",  # Should be blocked by safety
                    "This is a very long and complex sentence with many words that might challenge the processing system"
                ],
                expected_intent_types=["unknown", "unknown", "system_command", "unknown"],
                category="edge_cases",
                target_time_ms=1000,
                description="Testing edge cases and error handling"
            )
        ]

        # Run baseline tests with standard processor
        print(f"\n📋 PHASE 1: BASELINE TESTING (Standard Processor)")
        print("-"*60)

        baseline_results = {}
        for scenario in scenarios:
            baseline_results[scenario.name] = self.run_test_scenario(scenario, use_ultra_fast=False)

        # Run comparison tests with ultra-fast processor
        print(f"\n📋 PHASE 2: ULTRA-FAST PROCESSOR TESTING")
        print("-"*60)

        ultra_fast_results = {}
        for scenario in scenarios:
            ultra_fast_results[scenario.name] = self.run_test_scenario(scenario, use_ultra_fast=True)

        # Generate comprehensive analysis
        analysis = self.generate_comprehensive_analysis(baseline_results, ultra_fast_results)

        # Save detailed results
        self.save_test_results(analysis)

        return analysis

    def generate_comprehensive_analysis(self, baseline_results: Dict, ultra_fast_results: Dict) -> Dict[str, Any]:
        """Generate comprehensive analysis comparing baseline vs ultra-fast performance"""

        analysis = {
            "test_session": {
                "start_time": self.session_start.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_tests": len(self.test_results),
                "output_directory": str(self.output_dir)
            },
            "system_info": {
                "stt_available": STT_AVAILABLE,
                "semantic_parser_available": self.semantic_parser.is_available,
                "ollama_model": getattr(self.semantic_parser, 'model_name', 'Unknown')
            },
            "baseline_results": baseline_results,
            "ultra_fast_results": ultra_fast_results,
            "performance_comparison": {},
            "recommendations": []
        }

        # Calculate overall performance metrics
        baseline_times = []
        ultra_fast_times = []
        baseline_success = 0
        ultra_fast_success = 0
        total_baseline = 0
        total_ultra_fast = 0

        for scenario_name in baseline_results.keys():
            if scenario_name in ultra_fast_results:
                baseline_scenario = baseline_results[scenario_name]
                ultra_fast_scenario = ultra_fast_results[scenario_name]

                # Collect timing data
                for result in baseline_scenario['results']:
                    baseline_times.append(result.total_response_time_ms)
                    if result.overall_success:
                        baseline_success += 1
                    total_baseline += 1

                for result in ultra_fast_scenario['results']:
                    ultra_fast_times.append(result.total_response_time_ms)
                    if result.overall_success:
                        ultra_fast_success += 1
                    total_ultra_fast += 1

        # Calculate comparison metrics
        if baseline_times and ultra_fast_times:
            avg_baseline = statistics.mean(baseline_times)
            avg_ultra_fast = statistics.mean(ultra_fast_times)
            improvement_pct = ((avg_baseline - avg_ultra_fast) / avg_baseline) * 100

            analysis["performance_comparison"] = {
                "average_baseline_ms": avg_baseline,
                "average_ultra_fast_ms": avg_ultra_fast,
                "speed_improvement_percent": improvement_pct,
                "baseline_success_rate": (baseline_success / total_baseline) * 100 if total_baseline > 0 else 0,
                "ultra_fast_success_rate": (ultra_fast_success / total_ultra_fast) * 100 if total_ultra_fast > 0 else 0,
                "performance_targets_met": {
                    "excellent_baseline": sum(1 for t in baseline_times if t <= 500),
                    "excellent_ultra_fast": sum(1 for t in ultra_fast_times if t <= 500),
                    "good_baseline": sum(1 for t in baseline_times if t <= 1000),
                    "good_ultra_fast": sum(1 for t in ultra_fast_times if t <= 1000)
                }
            }

        # Generate recommendations
        if improvement_pct > 20:
            analysis["recommendations"].append("✅ Ultra-fast processor shows significant improvement - recommended for production")
        elif improvement_pct > 0:
            analysis["recommendations"].append("⚡ Ultra-fast processor shows some improvement - consider based on use case")
        else:
            analysis["recommendations"].append("⚠️  Ultra-fast processor shows minimal improvement - investigate bottlenecks")

        if avg_baseline > 1000:
            analysis["recommendations"].append("🔧 Baseline performance is slow - investigate STT/TTS optimization")

        if baseline_success / total_baseline < 0.8:
            analysis["recommendations"].append("🐛 Success rate is below 80% - investigate processing reliability")

        return analysis

    def save_test_results(self, analysis: Dict[str, Any]):
        """Save comprehensive test results to files"""

        # Save main analysis report
        analysis_file = self.output_dir / "comprehensive_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)

        # Save detailed metrics CSV
        metrics_file = self.output_dir / "detailed_metrics.csv"
        with open(metrics_file, 'w') as f:
            f.write("test_id,command,category,processor,stt_time_ms,processing_time_ms,tts_time_ms,total_time_ms,overall_success,meets_target,response_speed_class\n")

            for metrics in self.test_results:
                f.write(f"{metrics.test_id},{metrics.test_command},{metrics.test_category},{metrics.processor_used},")
                f.write(f"{metrics.stt_time_ms},{metrics.processing_time_ms},{metrics.tts_time_ms},{metrics.total_response_time_ms},")
                f.write(f"{metrics.overall_success},{metrics.meets_target},{metrics.response_speed_class}\n")

        # Save summary report
        summary_file = self.output_dir / "test_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("COMPREHENSIVE VOICE PIPELINE TEST RESULTS\n")
            f.write("="*80 + "\n\n")

            f.write(f"Test Session: {analysis['test_session']['start_time']} to {analysis['test_session']['end_time']}\n")
            f.write(f"Total Tests: {analysis['test_session']['total_tests']}\n\n")

            if 'performance_comparison' in analysis:
                comp = analysis['performance_comparison']
                f.write("PERFORMANCE COMPARISON\n")
                f.write("-"*40 + "\n")
                f.write(f"Baseline Average: {comp['average_baseline_ms']:.0f}ms\n")
                f.write(f"Ultra-Fast Average: {comp['average_ultra_fast_ms']:.0f}ms\n")
                f.write(f"Speed Improvement: {comp['speed_improvement_percent']:.1f}%\n")
                f.write(f"Baseline Success Rate: {comp['baseline_success_rate']:.1f}%\n")
                f.write(f"Ultra-Fast Success Rate: {comp['ultra_fast_success_rate']:.1f}%\n\n")

            f.write("RECOMMENDATIONS\n")
            f.write("-"*40 + "\n")
            for rec in analysis['recommendations']:
                f.write(f"• {rec}\n")

        print(f"\n💾 Test results saved to: {self.output_dir}")
        print(f"📊 Main analysis: {analysis_file}")
        print(f"📈 Detailed metrics: {metrics_file}")
        print(f"📋 Summary report: {summary_file}")

    def display_live_results_summary(self):
        """Display live summary of test results"""
        if not self.test_results:
            print("No test results available")
            return

        print(f"\n📊 LIVE RESULTS SUMMARY ({len(self.test_results)} tests)")
        print("="*60)

        # Calculate summary stats
        successful_tests = [m for m in self.test_results if m.overall_success]
        response_times = [m.total_response_time_ms for m in self.test_results]

        print(f"✅ Success Rate: {len(successful_tests)}/{len(self.test_results)} ({len(successful_tests)/len(self.test_results)*100:.1f}%)")

        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)

            print(f"⚡ Response Time - Avg: {avg_time:.0f}ms | Min: {min_time:.0f}ms | Max: {max_time:.0f}ms")

        # Performance classification
        excellent = sum(1 for m in self.test_results if m.response_speed_class == "excellent")
        good = sum(1 for m in self.test_results if m.response_speed_class == "good")
        acceptable = sum(1 for m in self.test_results if m.response_speed_class == "acceptable")
        slow = sum(1 for m in self.test_results if m.response_speed_class == "slow")

        print(f"🚀 Performance: Excellent({excellent}) Good({good}) Acceptable({acceptable}) Slow({slow})")

        # Component breakdown
        if successful_tests:
            avg_stt = statistics.mean([m.stt_time_ms for m in successful_tests])
            avg_processing = statistics.mean([m.processing_time_ms for m in successful_tests])
            avg_tts = statistics.mean([m.tts_time_ms for m in successful_tests])

            print(f"🔧 Component Times - STT: {avg_stt:.0f}ms | Processing: {avg_processing:.0f}ms | TTS: {avg_tts:.0f}ms")


def main():
    """Main test execution"""
    print("🧪 COMPREHENSIVE VOICE PIPELINE PERFORMANCE TESTER")
    print("="*80)
    print("🎯 Testing complete voice-to-response pipeline")
    print("📊 Generating real performance data and metrics")
    print("⚡ Comparing standard vs ultra-fast processing")
    print("="*80)

    # Initialize tester
    tester = VoicePipelineTester()

    try:
        # Run comprehensive test suite
        analysis_results = tester.run_comprehensive_test_suite()

        # Display final summary
        print("\n🏁 TESTING COMPLETE!")
        print("="*80)

        if 'performance_comparison' in analysis_results:
            comp = analysis_results['performance_comparison']
            print(f"📊 FINAL RESULTS:")
            print(f"   Baseline Performance: {comp['average_baseline_ms']:.0f}ms average")
            print(f"   Ultra-Fast Performance: {comp['average_ultra_fast_ms']:.0f}ms average")
            print(f"   Speed Improvement: {comp['speed_improvement_percent']:.1f}%")
            print(f"   Success Rates: {comp['baseline_success_rate']:.1f}% vs {comp['ultra_fast_success_rate']:.1f}%")

        print(f"\n📋 RECOMMENDATIONS:")
        for rec in analysis_results.get('recommendations', []):
            print(f"   • {rec}")

        print(f"\n💾 Detailed results saved to: {tester.output_dir}")

        return analysis_results

    except KeyboardInterrupt:
        print("\n\n🛑 Testing interrupted by user")
        tester.display_live_results_summary()
        return None
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        tester.display_live_results_summary()
        raise


if __name__ == "__main__":
    main()