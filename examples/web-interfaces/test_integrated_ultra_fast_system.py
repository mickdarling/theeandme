#!/usr/bin/env python3
"""
Test Script for Integrated Ultra-Fast Voice Interface
Validates all integration points and performance metrics
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# Import the components to test
try:
    from ultra_fast_voice_automation import UltraFastVoiceAutomation, FastVoiceResponse
    from enhanced_voice_automation import EnhancedVoiceAutomation
    from enhanced_echo_blocker_with_voice_fingerprinting import EnhancedEchoBlocker
    from voice_calibration_persistence import VoiceCalibrationManager
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_ultra_fast_processing():
    """Test ultra-fast processing performance"""
    print("\n⚡ TESTING ULTRA-FAST PROCESSING")
    print("-" * 50)

    automation = UltraFastVoiceAutomation()

    test_commands = [
        "Hi there!",
        "How are you?",
        "Open Chrome",
        "Launch Safari browser",
        "Search for Python tutorials",
        "Open the Notes app",
        "Thanks for your help",
        "Some complex command that won't match patterns"
    ]

    fast_responses = 0
    total_time = 0

    for i, cmd in enumerate(test_commands, 1):
        print(f"  Test {i}: '{cmd}'")

        response = automation.process_voice_command(cmd, execute=False)
        total_time += response.processing_time_ms

        print(f"    Response: \"{response.conversational_text}\"")
        print(f"    Time: {response.processing_time_ms:.0f}ms")
        print(f"    Method: {response.method_used}")
        print(f"    Intent: {response.intent_type}")

        if response.processing_time_ms < 100:
            print(f"    ⚡ LIGHTNING FAST!")
            fast_responses += 1
        elif response.processing_time_ms < 500:
            print(f"    ✅ FAST ENOUGH")
        else:
            print(f"    ⚠️  Slower than target")
        print()

    avg_time = total_time / len(test_commands)
    stats = automation.get_performance_stats()

    print(f"📊 Ultra-Fast Results:")
    print(f"  Average time: {avg_time:.0f}ms")
    print(f"  Lightning fast (<100ms): {fast_responses}/{len(test_commands)}")
    print(f"  Pattern efficiency: {stats['pattern_efficiency']:.1f}%")

    return avg_time < 200, fast_responses >= len(test_commands) * 0.6  # 60% should be ultra-fast


def test_enhanced_fallback():
    """Test enhanced automation fallback"""
    print("\n🧠 TESTING ENHANCED FALLBACK AUTOMATION")
    print("-" * 50)

    automation = EnhancedVoiceAutomation()

    test_commands = [
        "Open Chrome and search for machine learning",
        "Create a note about today's meeting",
        "This is a complex multi-step workflow command"
    ]

    results = []

    for cmd in test_commands:
        print(f"  Testing: '{cmd}'")
        start_time = time.time()

        result = automation.execute_voice_command(cmd)
        processing_time = (time.time() - start_time) * 1000

        print(f"    Intent: {result['intent']['intent_type']}")
        print(f"    Success: {'✅' if result['success'] else '❌'}")
        print(f"    Time: {processing_time:.0f}ms")
        print(f"    Message: {result['message']}")

        results.append(result['success'])
        print()

    success_rate = sum(results) / len(results)
    print(f"📊 Enhanced Fallback Results:")
    print(f"  Success rate: {success_rate * 100:.1f}%")
    print(f"  Semantic parser: {'Available' if automation.automation_stats['semantic_parser_available'] else 'Unavailable'}")

    return success_rate > 0.5  # At least 50% should succeed


def test_echo_blocking():
    """Test echo blocking functionality"""
    print("\n🔇 TESTING ECHO BLOCKING")
    print("-" * 50)

    echo_blocker = EnhancedEchoBlocker(enable_voice_fingerprinting=True)

    # Simulate some AI responses first
    echo_blocker.set_ai_response("I understand what you're saying.", speaking_duration=2.0)
    time.sleep(0.1)  # Brief pause
    echo_blocker.set_ai_response("That's very interesting.", speaking_duration=2.0)
    time.sleep(0.1)

    test_cases = [
        ("Hello there!", False, "New human input"),
        ("I understand what you're saying", True, "Recent AI response echo"),
        ("That's very interesting", True, "Another AI response echo"),
        ("This is completely different", False, "Different human input"),
        ("I understand", True, "Partial AI response match")
    ]

    correct_detections = 0

    for text, should_be_blocked, description in test_cases:
        is_echo, reason, detection_data = echo_blocker.is_likely_echo(text)

        correct = (is_echo == should_be_blocked)
        if correct:
            correct_detections += 1

        status = "✅ CORRECT" if correct else "❌ WRONG"
        block_status = "BLOCKED" if is_echo else "PASSED"

        print(f"  '{text}' -> {block_status} {status}")
        print(f"    Expected: {'BLOCKED' if should_be_blocked else 'PASSED'}")
        print(f"    Reason: {reason}")
        print()

    accuracy = correct_detections / len(test_cases)
    print(f"📊 Echo Blocking Results:")
    print(f"  Accuracy: {accuracy * 100:.1f}%")
    print(f"  Correct: {correct_detections}/{len(test_cases)}")

    return accuracy > 0.7  # 70% accuracy minimum


def test_voice_calibration():
    """Test voice calibration manager"""
    print("\n🎯 TESTING VOICE CALIBRATION")
    print("-" * 50)

    try:
        calibration = VoiceCalibrationManager()
        config = calibration.get_recorder_config()

        print(f"  Calibration available: ✅")
        print(f"  Config keys: {list(config.keys())}")

        return True

    except Exception as e:
        print(f"  Calibration error: ❌ {e}")
        return False


def test_integration_performance():
    """Test the complete integration performance"""
    print("\n⚡ TESTING INTEGRATION PERFORMANCE")
    print("-" * 50)

    # Initialize both systems
    ultra_fast = UltraFastVoiceAutomation()
    enhanced = EnhancedVoiceAutomation()

    test_scenarios = [
        ("Hi there!", "ultra-fast", "Simple greeting"),
        ("Open Chrome", "ultra-fast", "Simple app command"),
        ("Create a detailed note about machine learning with multiple sections", "enhanced", "Complex command"),
        ("Search for Python tutorials", "ultra-fast", "Simple search"),
        ("Open Chrome and search for AI then create a note about it", "enhanced", "Multi-step workflow")
    ]

    performance_results = []

    for text, expected_handler, description in test_scenarios:
        print(f"  Scenario: {description}")
        print(f"    Command: '{text}'")

        # Try ultra-fast first
        start_time = time.time()
        ultra_response = ultra_fast.process_voice_command(text, execute=False)
        ultra_time = (time.time() - start_time) * 1000

        # Check if ultra-fast should handle it
        ultra_success = (ultra_response.method_used == "pattern" and
                        ultra_response.confidence > 0.5 and
                        ultra_response.intent_type != "unknown")

        if ultra_success:
            actual_handler = "ultra-fast"
            response_time = ultra_time
            response_text = ultra_response.conversational_text
        else:
            # Fall back to enhanced
            start_time = time.time()
            enhanced_result = enhanced.execute_voice_command(text)
            enhanced_time = (time.time() - start_time) * 1000

            actual_handler = "enhanced"
            response_time = ultra_time + enhanced_time  # Total time including fallback
            response_text = enhanced_result.get('message', 'No response')

        correct_routing = (actual_handler == expected_handler)
        performance_results.append({
            'scenario': description,
            'expected': expected_handler,
            'actual': actual_handler,
            'correct': correct_routing,
            'time': response_time,
            'response': response_text
        })

        status = "✅ CORRECT" if correct_routing else "⚠️  DIFFERENT"
        print(f"    Handler: {actual_handler} {status}")
        print(f"    Time: {response_time:.0f}ms")
        print(f"    Response: \"{response_text}\"")
        print()

    correct_routing = sum(1 for r in performance_results if r['correct'])
    avg_time = sum(r['time'] for r in performance_results) / len(performance_results)

    print(f"📊 Integration Performance:")
    print(f"  Correct routing: {correct_routing}/{len(test_scenarios)}")
    print(f"  Average response time: {avg_time:.0f}ms")

    return correct_routing >= len(test_scenarios) * 0.6, avg_time < 1000


def run_complete_test_suite():
    """Run the complete test suite"""
    print("🧪 INTEGRATED ULTRA-FAST VOICE INTERFACE TEST SUITE")
    print("=" * 80)
    print("Testing all integration points and performance metrics...")
    print()

    tests = [
        ("Ultra-Fast Processing", test_ultra_fast_processing),
        ("Enhanced Fallback", test_enhanced_fallback),
        ("Echo Blocking", test_echo_blocking),
        ("Voice Calibration", test_voice_calibration),
        ("Integration Performance", test_integration_performance)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name.upper()} {'=' * 20}")

        try:
            start_time = time.time()
            result = test_func()
            test_time = time.time() - start_time

            if isinstance(result, tuple):
                # Multiple criteria
                success = all(result)
                results[test_name] = {'success': success, 'time': test_time, 'details': result}
            else:
                # Single criterion
                success = result
                results[test_name] = {'success': success, 'time': test_time}

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results[test_name] = {'success': False, 'time': 0, 'error': str(e)}

    # Print final results
    print(f"\n{'=' * 80}")
    print("🏁 FINAL TEST RESULTS")
    print(f"{'=' * 80}")

    passed = 0
    total = len(tests)

    for test_name, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        time_str = f"({result['time']:.1f}s)"

        print(f"  {test_name:<25} {status:<10} {time_str}")

        if result['success']:
            passed += 1
        elif 'error' in result:
            print(f"    Error: {result['error']}")

    print()
    print(f"Overall Result: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 ALL TESTS PASSED! Integration is ready for production.")
    elif passed >= total * 0.8:
        print("✅ Most tests passed. System is functional with minor issues.")
    elif passed >= total * 0.6:
        print("⚠️  Some issues detected. Review failed tests before deployment.")
    else:
        print("❌ Major issues detected. Integration needs debugging.")

    return passed >= total * 0.8


if __name__ == "__main__":
    success = run_complete_test_suite()
    sys.exit(0 if success else 1)