#!/usr/bin/env python3
"""
Optimized Voice Automation System - Production Ready
Combines conversational AI with fast performance and safety validation

Key optimizations:
- Shortened prompts for faster LLM processing
- Conversational responses with command parsing
- Parallel safety validation (keyword-based for speed)
- Smart fallback mechanisms
- Performance monitoring
"""

import json
import subprocess
import time
import re
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


@dataclass
class VoiceResponse:
    """Complete voice response with conversation and command execution"""
    conversational_text: str = "I'm here to help!"
    intent_type: str = "unknown"
    target_app: Optional[str] = None
    search_query: Optional[str] = None
    action_successful: bool = False
    processing_time_ms: float = 0.0
    confidence: float = 0.0
    safety_level: str = "safe"


class OptimizedVoiceAutomation:
    """Production-ready voice automation with conversational AI"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "llama3.1:latest"
        self.performance_stats = []

    def process_voice_command(self, voice_text: str, execute: bool = True) -> VoiceResponse:
        """Main method: Process voice command with conversation + execution"""
        start_time = time.time()

        # Parallel processing: LLM parsing + safety validation
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            llm_future = executor.submit(self._parse_with_llm, voice_text)
            safety_future = executor.submit(self._validate_safety, voice_text)

            # Get results
            try:
                llm_result = llm_future.result(timeout=3.0)  # Short timeout
                safety_result = safety_future.result(timeout=0.5)  # Very fast safety check
            except Exception:
                return self._fallback_response(voice_text, time.time() - start_time)

        # Create response
        response = VoiceResponse(
            conversational_text=llm_result.get('response', 'I can help with that!'),
            intent_type=llm_result.get('intent', 'unknown'),
            target_app=llm_result.get('app'),
            search_query=llm_result.get('query'),
            confidence=llm_result.get('confidence', 0.8),
            safety_level=safety_result,
            processing_time_ms=(time.time() - start_time) * 1000
        )

        # Execute command if requested and safe
        if execute and safety_result == "safe" and response.intent_type != "chat":
            response.action_successful = self._execute_command(response)

        # Track performance
        self.performance_stats.append(response.processing_time_ms)
        if len(self.performance_stats) > 50:  # Keep last 50 measurements
            self.performance_stats.pop(0)

        return response

    def _parse_with_llm(self, voice_text: str) -> Dict[str, Any]:
        """Fast LLM parsing with minimal prompt"""

        # Ultra-short prompt for speed
        prompt = f'User: "{voice_text}"\nReply + parse JSON:\n{{"response":"friendly reply","intent":"open_app/search_web/chat","app":"name","query":"terms","confidence":0.9}}\nJSON:'

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 80,  # Very short for speed
                "stop": ["}"],
                "top_p": 0.8
            }
        }

        try:
            import urllib.request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    text = result.get('response', '').strip()

                    # Fast JSON extraction
                    start = text.find('{')
                    end = text.find('}', start) + 1
                    if start != -1 and end > start:
                        try:
                            return json.loads(text[start:end])
                        except json.JSONDecodeError:
                            pass

        except Exception:
            pass

        # Fast fallback parsing
        return self._regex_fallback_parse(voice_text)

    def _regex_fallback_parse(self, voice_text: str) -> Dict[str, Any]:
        """Fast regex-based parsing when LLM fails"""
        text_lower = voice_text.lower()

        # Quick intent detection
        if any(word in text_lower for word in ['hi', 'hello', 'how', 'what', 'why', 'thanks']):
            responses = {
                'hi': 'Hello! How can I help?',
                'hello': 'Hi there! What can I do for you?',
                'how': "I'm doing great! How can I assist?",
                'what': "I'm your voice assistant. What would you like to do?",
                'thanks': "You're very welcome!"
            }
            response = next((resp for word, resp in responses.items() if word in text_lower), "Hi!")
            return {"response": response, "intent": "chat", "confidence": 0.7}

        elif any(word in text_lower for word in ['open', 'launch', 'start', 'run']):
            # Extract app name
            patterns = [r'(?:open|launch|start|run)\s+(?:a\s+|the\s+)?(\w+)', r'(?:open|launch)\s+(.+?)(?:\s|$)']
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    app = match.group(1).strip()
                    return {"response": f"Opening {app}!", "intent": "open_app", "app": app, "confidence": 0.8}

        elif any(word in text_lower for word in ['search', 'find', 'google', 'look']):
            # Extract search query
            patterns = [r'(?:search|find|google|look)(?:\s+for)?\s+(.+)', r'(?:search|find)\s+(.+)']
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    query = match.group(1).strip()
                    return {"response": f"Searching for {query}!", "intent": "search_web", "query": query, "confidence": 0.8}

        return {"response": "I'm not sure about that, but I'm here to help!", "intent": "unknown", "confidence": 0.3}

    def _validate_safety(self, voice_text: str) -> str:
        """Ultra-fast safety validation using keywords"""
        dangerous = ['delete', 'destroy', 'format', 'shutdown', 'kill', 'remove all', 'rm -rf']
        risky = ['sudo', 'admin', 'password', 'install', 'download']

        text_lower = voice_text.lower()
        if any(word in text_lower for word in dangerous):
            return "destructive"
        elif any(word in text_lower for word in risky):
            return "potentially_destructive"
        return "safe"

    def _execute_command(self, response: VoiceResponse) -> bool:
        """Execute the parsed command"""
        try:
            if response.intent_type == "open_app" and response.target_app:
                app_name = self._get_app_name(response.target_app)
                subprocess.run(['open', '-a', app_name], check=True, timeout=5)
                return True

            elif response.intent_type == "search_web" and response.search_query:
                search_url = f"https://www.google.com/search?q={response.search_query.replace(' ', '+')}"
                subprocess.run(['open', search_url], check=True, timeout=5)
                return True

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

        return False

    def _get_app_name(self, app_name: str) -> str:
        """Map common names to macOS app names"""
        mappings = {
            'chrome': 'Google Chrome',
            'safari': 'Safari',
            'firefox': 'Firefox',
            'notes': 'Notes',
            'textedit': 'TextEdit',
            'terminal': 'Terminal',
            'calculator': 'Calculator',
            'mail': 'Mail',
            'calendar': 'Calendar'
        }
        return mappings.get(app_name.lower(), app_name.title())

    def _fallback_response(self, voice_text: str, processing_time: float) -> VoiceResponse:
        """Fallback when all parsing fails"""
        return VoiceResponse(
            conversational_text="I didn't quite catch that, but I'm here to help!",
            intent_type="unknown",
            processing_time_ms=processing_time * 1000,
            confidence=0.1
        )

    def get_performance_stats(self) -> Dict[str, float]:
        """Get current performance statistics"""
        if not self.performance_stats:
            return {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "count": 0}

        return {
            "avg_ms": sum(self.performance_stats) / len(self.performance_stats),
            "min_ms": min(self.performance_stats),
            "max_ms": max(self.performance_stats),
            "count": len(self.performance_stats),
            "target_achieved": sum(self.performance_stats) / len(self.performance_stats) < 500
        }


def interactive_test():
    """Interactive test of the optimized system"""
    automation = OptimizedVoiceAutomation()

    test_commands = [
        "Hello there!",
        "How are you today?",
        "Open Chrome browser",
        "Search for Python tutorials",
        "Launch Safari",
        "What's the weather like?",
        "Thanks for your help"
    ]

    print("🚀 OPTIMIZED VOICE AUTOMATION SYSTEM")
    print("=" * 60)
    print("🎯 Target: <500ms response time + conversational responses")
    print()

    for i, cmd in enumerate(test_commands, 1):
        print(f"🎤 Test {i}: '{cmd}'")

        # Process command
        response = automation.process_voice_command(cmd, execute=False)  # Don't execute for testing

        # Display results
        print(f"  💬 Response: \"{response.conversational_text}\"")
        print(f"  🎯 Intent: {response.intent_type}")
        print(f"  📱 App: {response.target_app or 'None'}")
        print(f"  🔍 Query: {response.search_query or 'None'}")
        print(f"  ⚡ Time: {response.processing_time_ms:.0f}ms")
        print(f"  🛡️  Safety: {response.safety_level}")
        print(f"  📊 Confidence: {response.confidence:.1f}")

        # Performance indicator
        if response.processing_time_ms < 500:
            print("  ✅ PERFORMANCE TARGET ACHIEVED")
        else:
            print("  ⚠️  Performance needs improvement")
        print()

    # Final stats
    stats = automation.get_performance_stats()
    print("📊 PERFORMANCE SUMMARY")
    print("-" * 30)
    print(f"Average: {stats['avg_ms']:.0f}ms")
    print(f"Range: {stats['min_ms']:.0f}ms - {stats['max_ms']:.0f}ms")
    print(f"Tests: {stats['count']}")
    print(f"Target (<500ms): {'✅ ACHIEVED' if stats['target_achieved'] else '❌ NEEDS WORK'}")


if __name__ == "__main__":
    interactive_test()