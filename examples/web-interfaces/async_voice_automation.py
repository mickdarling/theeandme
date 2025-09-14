#!/usr/bin/env python3
"""
Async Voice Automation System
Parallel processing for voice commands, safety validation, and responses
Performance-optimized version with conversational capabilities
"""

import asyncio
import json
import time
import subprocess
import urllib.request
import urllib.parse
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor


@dataclass
class ConversationalIntent:
    """Enhanced intent with conversational response"""
    intent_type: str
    conversational_response: str = ""
    target_app: Optional[str] = None
    search_query: Optional[str] = None
    confidence: float = 0.0
    safety_level: str = "safe"
    processing_time: float = 0.0
    raw_command: str = ""


class AsyncVoiceProcessor:
    """High-performance async voice command processor"""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model_name = "llama3.1:latest"

    async def process_voice_command_parallel(self, voice_text: str) -> ConversationalIntent:
        """Process voice command with parallel safety validation and intent parsing"""
        start_time = time.time()

        # Run intent parsing and safety validation in parallel using thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [
                loop.run_in_executor(executor, self._parse_intent_sync, voice_text),
                loop.run_in_executor(executor, self._validate_safety_sync, voice_text)
            ]

            intent_result, safety_result = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results
            if isinstance(intent_result, Exception) or isinstance(safety_result, Exception):
                return ConversationalIntent(
                    intent_type="unknown",
                    conversational_response="I'm sorry, I didn't understand that.",
                    confidence=0.1,
                    processing_time=time.time() - start_time,
                    raw_command=voice_text
                )

            # Merge results
            intent_result.safety_level = safety_result.get('safety_level', 'safe')
            intent_result.processing_time = time.time() - start_time

            return intent_result

    def _parse_intent_sync(self, voice_text: str) -> ConversationalIntent:
        """Synchronous intent parsing optimized for threading"""

        prompt = f"""User: "{voice_text}"

Reply naturally and parse:
{{
  "response": "Natural friendly response",
  "intent": "open_app|search_web|chat|unknown",
  "app": "app_name",
  "query": "search_terms"
}}

Examples:
"Open Chrome" → {{"response":"Opening Chrome now!","intent":"open_app","app":"chrome"}}
"Hi there" → {{"response":"Hello! How can I help you?","intent":"chat"}}

JSON:"""

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 100,
                "stop": ["}"]
            }
        }

        try:
            # Use urllib for synchronous HTTP request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    response_text = result.get('response', '').strip()

                    # Quick JSON extraction
                    start = response_text.find('{')
                    end = response_text.find('}', start) + 1
                    if start != -1 and end > start:
                        try:
                            parsed = json.loads(response_text[start:end])
                            return ConversationalIntent(
                                intent_type=parsed.get('intent', 'unknown'),
                                conversational_response=parsed.get('response', 'Sure!'),
                                target_app=parsed.get('app'),
                                search_query=parsed.get('query'),
                                confidence=0.9,
                                raw_command=voice_text
                            )
                        except json.JSONDecodeError:
                            pass

        except Exception:
            pass

        # Fallback
        return ConversationalIntent(
            intent_type="unknown",
            conversational_response="I didn't quite catch that.",
            confidence=0.3,
            raw_command=voice_text
        )

    def _validate_safety_sync(self, voice_text: str) -> Dict[str, str]:
        """Synchronous safety validation (very fast)"""

        # Quick safety keywords check (much faster than LLM)
        dangerous_keywords = ['delete', 'remove', 'destroy', 'format', 'shutdown', 'kill']
        risky_keywords = ['install', 'download', 'sudo', 'admin', 'password']

        text_lower = voice_text.lower()

        if any(word in text_lower for word in dangerous_keywords):
            return {"safety_level": "destructive"}
        elif any(word in text_lower for word in risky_keywords):
            return {"safety_level": "potentially_destructive"}
        else:
            return {"safety_level": "safe"}

    def execute_command(self, intent: ConversationalIntent) -> bool:
        """Execute the parsed command safely"""

        if intent.safety_level == "destructive":
            print(f"🛡️  BLOCKED: Destructive command '{intent.raw_command}'")
            return False

        if intent.intent_type == "open_app" and intent.target_app:
            try:
                app_name = self._get_app_name(intent.target_app)
                subprocess.run(['open', '-a', app_name], check=True)
                return True
            except subprocess.CalledProcessError:
                return False

        elif intent.intent_type == "search_web" and intent.search_query:
            try:
                search_url = f"https://www.google.com/search?q={intent.search_query.replace(' ', '+')}"
                subprocess.run(['open', search_url], check=True)
                return True
            except subprocess.CalledProcessError:
                return False

        return intent.intent_type == "chat"  # Chat commands always "succeed"

    def _get_app_name(self, app_name: str) -> str:
        """Map common names to actual macOS app names"""
        mappings = {
            'chrome': 'Google Chrome',
            'safari': 'Safari',
            'firefox': 'Firefox',
            'notes': 'Notes',
            'textedit': 'TextEdit',
            'terminal': 'Terminal'
        }
        return mappings.get(app_name.lower(), app_name)


async def test_async_performance():
    """Test the async voice processor performance"""
    processor = AsyncVoiceProcessor()

    test_commands = [
        "Hello there",
        "Open Chrome browser",
        "Search for Python tutorials",
        "How are you doing today?",
        "Launch Safari please",
        "What's the weather like?"
    ]

    print("🚀 Async Voice Processor Performance Test")
    print("=" * 60)

    total_time = time.time()

    for cmd in test_commands:
        print(f"🎤 Testing: '{cmd}'")

        start_time = time.time()
        intent = await processor.process_voice_command_parallel(cmd)
        end_time = time.time()

        print(f"  💬 Response: \"{intent.conversational_response}\"")
        print(f"  🎯 Intent: {intent.intent_type}")
        print(f"  📱 App: {intent.target_app}")
        print(f"  🔍 Query: {intent.search_query}")
        print(f"  ⚡ Time: {(end_time - start_time)*1000:.0f}ms")
        print(f"  🛡️  Safety: {intent.safety_level}")
        print()

    total_elapsed = time.time() - total_time
    avg_time = (total_elapsed / len(test_commands)) * 1000

    print(f"📊 Average processing time: {avg_time:.0f}ms")
    print(f"🎯 Target achieved: {'✅' if avg_time < 500 else '❌'}")


if __name__ == "__main__":
    asyncio.run(test_async_performance())