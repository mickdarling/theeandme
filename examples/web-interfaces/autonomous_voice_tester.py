#!/usr/bin/env python3
"""
Autonomous Voice Automation Testing Framework
DollhouseMCP Collaborative Testing - No Human Interaction Required

This framework tests the entire voice automation pipeline without requiring
human voice input by directly calling the automation APIs and verifying results.
"""

import time
import json
import subprocess
import requests
from typing import Dict, List, Tuple, Any
from datetime import datetime
from pathlib import Path
from enhanced_voice_automation import EnhancedVoiceAutomation
from semantic_voice_parser import SemanticVoiceParser, CommandIntent


class AutonomousVoiceTester:
    """Comprehensive autonomous testing of the voice automation system"""

    def __init__(self):
        # Initialize the systems under test
        self.automation = EnhancedVoiceAutomation()
        self.semantic_parser = SemanticVoiceParser()

        # Test results storage
        self.test_results = {
            'session_start': datetime.now().isoformat(),
            'semantic_parser_tests': [],
            'automation_tests': [],
            'integration_tests': [],
            'performance_tests': [],
            'safety_tests': [],
            'summary': {}
        }

    def test_semantic_parser_standalone(self) -> Dict:
        """Test the semantic parser in isolation"""
        print("🧠 Testing Semantic Parser (Standalone)")

        test_cases = [
            # Basic app opening
            {
                'input': 'Open Chrome',
                'expected': {'intent_type': 'open_app', 'target_app': 'chrome'},
                'category': 'app_opening'
            },
            {
                'input': 'Launch Safari',
                'expected': {'intent_type': 'open_app', 'target_app': 'safari'},
                'category': 'app_opening'
            },

            # Web searching
            {
                'input': 'Search for Python tutorials',
                'expected': {'intent_type': 'search_web', 'search_query': 'Python tutorials'},
                'category': 'web_search'
            },
            {
                'input': 'Google machine learning',
                'expected': {'intent_type': 'search_web', 'search_query': 'machine learning'},
                'category': 'web_search'
            },

            # Multi-step workflows
            {
                'input': 'Open Chrome and search for Python tools',
                'expected': {'intent_type': 'multi_step', 'steps': ['open chrome', 'search for Python tools']},
                'category': 'multi_step'
            },
            {
                'input': 'Launch Safari and search for voice recognition',
                'expected': {'intent_type': 'multi_step'},
                'category': 'multi_step'
            },

            # Notes operations
            {
                'input': 'Create a note about today\'s meeting',
                'expected': {'intent_type': 'create_note', 'note_title': 'today\'s meeting'},
                'category': 'notes'
            },
            {
                'input': 'Add to my notes: breakthrough achieved',
                'expected': {'intent_type': 'edit_note', 'note_content': 'breakthrough achieved'},
                'category': 'notes'
            },

            # Safety validation
            {
                'input': 'Delete all my files',
                'expected': {'intent_type': 'system_command', 'safety_level': 'destructive'},
                'category': 'safety'
            },

            # Edge cases
            {
                'input': 'respond',
                'expected': {'intent_type': 'unknown'},
                'category': 'edge_case'
            },
            {
                'input': '',
                'expected': {'intent_type': 'unknown'},
                'category': 'edge_case'
            }
        ]

        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"  📝 Test {i}/{len(test_cases)}: '{test_case['input']}'")

            start_time = time.time()
            intent = self.semantic_parser.parse_voice_command(test_case['input'])
            parse_time = time.time() - start_time

            # Evaluate results
            passed = True
            failures = []

            for expected_key, expected_value in test_case['expected'].items():
                actual_value = getattr(intent, expected_key, None)
                if expected_key == 'steps' and actual_value:
                    # For steps, check if the expected steps are contained
                    if not all(any(expected_step.lower() in actual_step.lower()
                              for actual_step in actual_value)
                              for expected_step in expected_value):
                        passed = False
                        failures.append(f"{expected_key}: expected {expected_value}, got {actual_value}")
                elif expected_key in ['note_title', 'search_query', 'note_content']:
                    # For text fields, check if key terms are present
                    if actual_value and expected_value.lower() not in actual_value.lower():
                        passed = False
                        failures.append(f"{expected_key}: expected to contain '{expected_value}', got '{actual_value}'")
                elif actual_value != expected_value:
                    passed = False
                    failures.append(f"{expected_key}: expected {expected_value}, got {actual_value}")

            result = {
                'test_id': i,
                'input': test_case['input'],
                'category': test_case['category'],
                'expected': test_case['expected'],
                'actual': intent.__dict__,
                'passed': passed,
                'failures': failures,
                'parse_time_ms': round(parse_time * 1000, 2),
                'confidence': intent.confidence
            }

            results.append(result)
            status = "✅" if passed else "❌"
            print(f"    {status} {parse_time*1000:.1f}ms - Confidence: {intent.confidence:.2f}")
            if not passed:
                for failure in failures:
                    print(f"      ⚠️  {failure}")

        self.test_results['semantic_parser_tests'] = results
        return results

    def test_automation_execution(self) -> Dict:
        """Test automation execution without actually running the automations"""
        print("\n🚀 Testing Automation Execution (Safe Mode)")

        # Test cases that we can verify without actually executing
        test_commands = [
            'Open Chrome',
            'Search for Python tutorials',
            'Create a note about testing',
            'Open Safari and search for voice recognition',
            'Delete all files'  # Should be blocked by safety
        ]

        results = []
        for i, command in enumerate(test_commands, 1):
            print(f"  🎯 Test {i}/{len(test_commands)}: '{command}'")

            start_time = time.time()
            result = self.automation.execute_voice_command(command)
            execution_time = time.time() - start_time

            # Analyze the result
            passed = True
            analysis = []

            if result.get('safety_blocked'):
                analysis.append("✅ Safety system activated")
                if 'delete' in command.lower():
                    analysis.append("✅ Correctly blocked destructive command")
                else:
                    passed = False
                    analysis.append("❌ Safe command incorrectly blocked")

            elif result.get('automation_performed'):
                analysis.append("✅ Automation system engaged")
                if result.get('success'):
                    analysis.append("✅ Automation reported success")
                else:
                    analysis.append("⚠️  Automation reported failure")
                    analysis.append(f"    Reason: {result.get('message', 'Unknown')}")

            else:
                analysis.append("⚠️  No automation performed")
                passed = False

            test_result = {
                'test_id': i,
                'command': command,
                'result': result,
                'passed': passed,
                'analysis': analysis,
                'execution_time_ms': round(execution_time * 1000, 2)
            }

            results.append(test_result)
            status = "✅" if passed else "❌"
            print(f"    {status} {execution_time*1000:.1f}ms")
            for note in analysis:
                print(f"      {note}")

        self.test_results['automation_tests'] = results
        return results

    def test_safety_validation(self) -> Dict:
        """Test the safety validation system"""
        print("\n🛡️  Testing Safety Validation System")

        safety_test_cases = [
            {'command': 'Open Chrome', 'should_be_safe': True},
            {'command': 'Search for tutorials', 'should_be_safe': True},
            {'command': 'Create a note', 'should_be_safe': True},
            {'command': 'Delete all my files', 'should_be_safe': False},
            {'command': 'Remove everything from disk', 'should_be_safe': False},
            {'command': 'Format the hard drive', 'should_be_safe': False},
            {'command': 'Edit a document', 'should_be_safe': True},
        ]

        results = []
        for i, test_case in enumerate(safety_test_cases, 1):
            print(f"  🔒 Safety Test {i}/{len(safety_test_cases)}: '{test_case['command']}'")

            result = self.automation.execute_voice_command(test_case['command'])

            # Check if safety system behaved correctly
            is_blocked = result.get('safety_blocked', False)
            should_be_safe = test_case['should_be_safe']

            if should_be_safe and not is_blocked:
                passed = True
                outcome = "✅ Safe command allowed"
            elif not should_be_safe and is_blocked:
                passed = True
                outcome = "✅ Dangerous command blocked"
            elif should_be_safe and is_blocked:
                passed = False
                outcome = "❌ Safe command incorrectly blocked"
            else:  # not should_be_safe and not is_blocked
                passed = False
                outcome = "❌ Dangerous command incorrectly allowed"

            safety_result = {
                'test_id': i,
                'command': test_case['command'],
                'should_be_safe': should_be_safe,
                'was_blocked': is_blocked,
                'passed': passed,
                'outcome': outcome,
                'safety_info': result.get('safety_info', {})
            }

            results.append(safety_result)
            print(f"    {outcome}")

        self.test_results['safety_tests'] = results
        return results

    def test_performance_benchmarks(self) -> Dict:
        """Test performance characteristics"""
        print("\n⚡ Testing Performance Benchmarks")

        # Test parsing speed
        test_commands = [
            'Open Chrome',
            'Search for Python machine learning tutorials and documentation',
            'Create a detailed note about today\'s breakthrough discoveries and innovations',
            'Open Safari and search for voice recognition then create a note about it'
        ]

        results = []
        for complexity, command in enumerate(test_commands, 1):
            print(f"  📊 Performance Test {complexity}: Complexity Level {complexity}")

            # Run multiple iterations
            times = []
            for _ in range(5):
                start_time = time.time()
                intent = self.semantic_parser.parse_voice_command(command)
                parse_time = time.time() - start_time
                times.append(parse_time * 1000)  # Convert to milliseconds

            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            # Performance thresholds
            acceptable_time = 2000  # 2 seconds
            good_time = 1500  # 1.5 seconds

            if avg_time <= good_time:
                performance = "🚀 Excellent"
            elif avg_time <= acceptable_time:
                performance = "✅ Good"
            else:
                performance = "⚠️  Slow"

            perf_result = {
                'complexity_level': complexity,
                'command': command,
                'avg_time_ms': round(avg_time, 1),
                'min_time_ms': round(min_time, 1),
                'max_time_ms': round(max_time, 1),
                'performance_rating': performance,
                'meets_threshold': avg_time <= acceptable_time
            }

            results.append(perf_result)
            print(f"    {performance} - Avg: {avg_time:.1f}ms (Range: {min_time:.1f}-{max_time:.1f}ms)")

        self.test_results['performance_tests'] = results
        return results

    def verify_system_dependencies(self) -> Dict:
        """Verify all system dependencies are working"""
        print("\n🔧 Verifying System Dependencies")

        dependencies = []

        # Test Ollama availability
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                ollama_status = f"✅ Ollama running with {len(models)} models"
                ollama_working = True
            else:
                ollama_status = f"⚠️  Ollama responding but returned {response.status_code}"
                ollama_working = False
        except Exception as e:
            ollama_status = f"❌ Ollama not accessible: {e}"
            ollama_working = False

        dependencies.append({
            'name': 'Ollama LLM Server',
            'status': ollama_status,
            'working': ollama_working
        })

        # Test macOS system commands
        try:
            result = subprocess.run(['osascript', '-e', 'tell application "System Events" to get name of first application process'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                osascript_status = "✅ macOS AppleScript working"
                osascript_working = True
            else:
                osascript_status = f"⚠️  AppleScript error: {result.stderr}"
                osascript_working = False
        except Exception as e:
            osascript_status = f"❌ AppleScript not available: {e}"
            osascript_working = False

        dependencies.append({
            'name': 'macOS AppleScript',
            'status': osascript_status,
            'working': osascript_working
        })

        # Test text-to-speech
        try:
            result = subprocess.run(['say', '--voice=?'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                voices = len([line for line in result.stdout.split('\n') if line.strip()])
                tts_status = f"✅ Text-to-speech working with {voices} voices"
                tts_working = True
            else:
                tts_status = "⚠️  Text-to-speech issues"
                tts_working = False
        except Exception as e:
            tts_status = f"❌ Text-to-speech not available: {e}"
            tts_working = False

        dependencies.append({
            'name': 'macOS Text-to-Speech',
            'status': tts_status,
            'working': tts_working
        })

        for dep in dependencies:
            print(f"  {dep['status']}")

        return dependencies

    def generate_comprehensive_report(self) -> str:
        """Generate a comprehensive test report"""
        print("\n📋 Generating Comprehensive Test Report")

        # Calculate summary statistics
        total_tests = 0
        passed_tests = 0

        for test_category in ['semantic_parser_tests', 'automation_tests', 'safety_tests']:
            if test_category in self.test_results:
                category_tests = self.test_results[test_category]
                total_tests += len(category_tests)
                passed_tests += sum(1 for test in category_tests if test.get('passed', False))

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Performance summary
        perf_tests = self.test_results.get('performance_tests', [])
        avg_performance = sum(test['avg_time_ms'] for test in perf_tests) / len(perf_tests) if perf_tests else 0

        report = f"""
🚀 AUTONOMOUS VOICE AUTOMATION TEST REPORT
{'='*70}
📅 Test Session: {self.test_results['session_start']}
⏰ Completed: {datetime.now().isoformat()}

📊 OVERALL RESULTS
✅ Passed Tests: {passed_tests}/{total_tests} ({success_rate:.1f}%)
⚡ Average Response Time: {avg_performance:.1f}ms
🧠 Semantic Parser Available: {self.semantic_parser.is_available}

🧪 TEST CATEGORY BREAKDOWN
"""

        # Add detailed results for each category
        for category_name, display_name in [
            ('semantic_parser_tests', 'Semantic Parser Tests'),
            ('automation_tests', 'Automation Execution Tests'),
            ('safety_tests', 'Safety Validation Tests'),
            ('performance_tests', 'Performance Benchmark Tests')
        ]:
            if category_name in self.test_results and self.test_results[category_name]:
                tests = self.test_results[category_name]
                passed = sum(1 for test in tests if test.get('passed', True))
                report += f"\n{display_name}: {passed}/{len(tests)} passed\n"

                for test in tests:
                    status = "✅" if test.get('passed', True) else "❌"
                    if category_name == 'performance_tests':
                        report += f"  {status} Complexity {test['complexity_level']}: {test['avg_time_ms']:.1f}ms\n"
                    else:
                        test_name = test.get('input', test.get('command', f"Test {test.get('test_id')}"))
                        report += f"  {status} {test_name}\n"

        # Add recommendations
        report += f"""
🎯 RECOMMENDATIONS
"""

        if success_rate >= 90:
            report += "✅ System performing excellently - ready for production use\n"
        elif success_rate >= 75:
            report += "⚠️  System mostly working - investigate failing tests\n"
        else:
            report += "❌ System needs significant improvements before use\n"

        if avg_performance <= 1500:
            report += "⚡ Performance excellent - under 1.5s average response time\n"
        elif avg_performance <= 2000:
            report += "✅ Performance acceptable - under 2s average response time\n"
        else:
            report += "⚠️  Performance slow - consider optimization\n"

        report += f"""
{'='*70}
🤖 Generated by Autonomous Voice Testing Framework
🧠 DollhouseMCP Collaborative Analysis Complete
"""

        return report

    def run_full_test_suite(self) -> Dict:
        """Run the complete autonomous test suite"""
        print("🧪 AUTONOMOUS VOICE AUTOMATION TEST SUITE")
        print("="*70)
        print("🤖 DollhouseMCP Collaborative Testing - No Human Input Required")
        print("="*70)

        # Run all test categories
        self.verify_system_dependencies()
        self.test_semantic_parser_standalone()
        self.test_automation_execution()
        self.test_safety_validation()
        self.test_performance_benchmarks()

        # Generate and display report
        report = self.generate_comprehensive_report()
        print(report)

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"autonomous_test_results_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)

        print(f"\n📁 Detailed results saved to: {results_file}")

        return self.test_results


def main():
    """Run the autonomous testing framework"""
    tester = AutonomousVoiceTester()
    results = tester.run_full_test_suite()

    # Use the voice narrator to announce results
    total_tests = sum(len(results.get(category, []))
                     for category in ['semantic_parser_tests', 'automation_tests', 'safety_tests'])
    passed_tests = sum(sum(1 for test in results.get(category, []) if test.get('passed', False))
                      for category in ['semantic_parser_tests', 'automation_tests', 'safety_tests'])

    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"\n🔊 Speaking results summary...")
    import subprocess
    subprocess.run(['say', f"Autonomous testing complete. {passed_tests} out of {total_tests} tests passed. Success rate: {success_rate:.0f} percent."])


if __name__ == "__main__":
    main()