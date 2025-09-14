#!/usr/bin/env python3
"""
Performance Benchmark for Voice Automation System
Tests streaming vs non-streaming response times
"""

import subprocess
import json
import time
import statistics
from typing import List, Tuple


def test_ollama_performance(test_phrase: str, streaming: bool = False) -> Tuple[float, bool]:
    """Test Ollama response time with a given phrase"""

    prompt = f"""Parse this voice command into JSON format: "{test_phrase}"
Respond with only JSON:
{{"intent_type": "open_app", "primary_action": "open", "target_app": "chrome", "confidence": 0.9}}"""

    payload = {
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": streaming,
        "options": {
            "temperature": 0.1,
            "num_predict": 100 if streaming else 150
        }
    }

    start_time = time.time()

    try:
        # Use curl to test the API
        curl_cmd = [
            'curl', '-s',
            'http://localhost:11434/api/generate',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ]

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        end_time = time.time()

        if result.returncode == 0 and result.stdout:
            return end_time - start_time, True
        else:
            return end_time - start_time, False

    except subprocess.TimeoutExpired:
        return 10.0, False
    except Exception as e:
        return 10.0, False


def benchmark_voice_commands():
    """Benchmark various voice commands for performance"""

    test_commands = [
        "Open Chrome",
        "Search for Python tutorials",
        "Launch Safari",
        "Open a Chrome browser",
        "Find machine learning resources"
    ]

    print("🚀 Voice Automation Performance Benchmark")
    print("=" * 60)
    print(f"⚡ Testing {len(test_commands)} commands with streaming and non-streaming")
    print()

    streaming_times = []
    non_streaming_times = []

    for cmd in test_commands:
        print(f"🎤 Testing: '{cmd}'")

        # Test streaming
        stream_time, stream_success = test_ollama_performance(cmd, streaming=True)
        streaming_times.append(stream_time)

        # Test non-streaming
        non_stream_time, non_stream_success = test_ollama_performance(cmd, streaming=False)
        non_streaming_times.append(non_stream_time)

        print(f"  📡 Streaming: {stream_time*1000:.0f}ms {'✅' if stream_success else '❌'}")
        print(f"  📄 Standard: {non_stream_time*1000:.0f}ms {'✅' if non_stream_success else '❌'}")
        print(f"  🏃 Improvement: {((non_stream_time - stream_time) / non_stream_time * 100):+.1f}%")
        print()

    # Calculate statistics
    if streaming_times and non_streaming_times:
        avg_streaming = statistics.mean(streaming_times) * 1000
        avg_standard = statistics.mean(non_streaming_times) * 1000
        improvement = ((avg_standard - avg_streaming) / avg_standard) * 100

        print("📊 PERFORMANCE SUMMARY")
        print("-" * 30)
        print(f"Average Streaming:     {avg_streaming:.0f}ms")
        print(f"Average Standard:      {avg_standard:.0f}ms")
        print(f"Performance Improvement: {improvement:+.1f}%")
        print(f"Target (<500ms):       {'✅ ACHIEVED' if avg_streaming < 500 else '❌ NEEDS WORK'}")


def test_system_status():
    """Test if the voice automation system is ready"""
    print("🔍 System Status Check")
    print("-" * 30)

    # Check Ollama
    try:
        result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama: Running")
            models = json.loads(result.stdout).get('models', [])
            print(f"📚 Models: {len(models)} available")
            for model in models:
                print(f"   - {model.get('name', 'Unknown')}")
        else:
            print("❌ Ollama: Not responding")
    except Exception:
        print("❌ Ollama: Connection failed")

    print()


if __name__ == "__main__":
    test_system_status()
    print()
    benchmark_voice_commands()