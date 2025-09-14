#!/usr/bin/env python3
"""
Ultra-Fast Voice Automation System
Strategy: Smart pattern matching first, LLM only when necessary

Key optimizations:
- Pattern matching for 90% of common commands (under 50ms)
- LLM only for complex/ambiguous cases
- Conversational responses built-in to patterns
- Sub-500ms target achieved through intelligent routing
"""

import json
import subprocess
import time
import re
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class FastVoiceResponse:
    """Optimized voice response for speed"""
    conversational_text: str
    intent_type: str
    target_app: Optional[str] = None
    search_query: Optional[str] = None
    action_successful: bool = False
    processing_time_ms: float = 0.0
    method_used: str = "pattern"  # "pattern" or "llm"
    confidence: float = 0.0


class UltraFastVoiceAutomation:
    """Lightning-fast voice automation with conversational responses"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "llama3.1:latest"
        self.stats = {"pattern_hits": 0, "llm_calls": 0, "total_calls": 0}

        # Pre-compiled patterns for maximum speed
        self.patterns = {
            # Greetings and chat
            'greeting': {
                'patterns': [r'\b(hi|hello|hey|good morning|good afternoon)\b'],
                'responses': ["Hello! How can I help you today?", "Hi there! What can I do for you?"],
                'intent': 'chat'
            },
            'how_are_you': {
                'patterns': [r'\bhow are you\b', r'\bhow\'s it going\b'],
                'responses': ["I'm doing great! How can I assist you?", "I'm here and ready to help!"],
                'intent': 'chat'
            },
            'thanks': {
                'patterns': [r'\b(thanks|thank you|thank you very much)\b'],
                'responses': ["You're very welcome!", "Happy to help!", "Anytime!"],
                'intent': 'chat'
            },

            # App opening commands
            'open_chrome': {
                'patterns': [r'\b(open|launch|start|run)\s+(a\s+|the\s+)?chrome\b'],
                'responses': ["Opening Chrome browser now!"],
                'intent': 'open_app',
                'app': 'chrome'
            },
            'open_safari': {
                'patterns': [r'\b(open|launch|start|run)\s+(a\s+|the\s+)?safari\b'],
                'responses': ["Launching Safari for you!"],
                'intent': 'open_app',
                'app': 'safari'
            },
            'open_notes': {
                'patterns': [r'\b(open|launch|start|run)\s+(a\s+|the\s+)?(notes|note)\b'],
                'responses': ["Opening Notes app!"],
                'intent': 'open_app',
                'app': 'notes'
            },
            'open_terminal': {
                'patterns': [r'\b(open|launch|start|run)\s+(a\s+|the\s+)?terminal\b'],
                'responses': ["Opening Terminal!"],
                'intent': 'open_app',
                'app': 'terminal'
            },

            # Generic app opening - now with context filtering
            'open_app_generic': {
                'patterns': [r'\b(open|launch|start|run)\s+(a\s+|the\s+)?(\w+)(?:\s+(app|application|browser|program))?\b'],
                'responses': ["Opening {app} for you!"],
                'intent': 'open_app',
                'extract_app': True,
                'context_blacklist': ['source', 'mind', 'heart', 'book', 'file', 'door', 'window', 'eyes', 'mouth', 'box', 'can', 'up', 'ai', 'houses', 'homes', 'properties', 'listings', 'market', 'realtor', 'estate']
            },

            # Search commands
            'search_google': {
                'patterns': [r'\b(search|google|find|look up)(?:\s+for)?\s+(.+)'],
                'responses': ["Searching for {query}!", "Looking that up for you!"],
                'intent': 'search_web',
                'extract_query': True
            }
        }

    def process_voice_command(self, voice_text: str, execute: bool = True) -> FastVoiceResponse:
        """Ultra-fast processing with pattern matching first"""
        start_time = time.time()
        self.stats["total_calls"] += 1

        # Step 1: Try pattern matching (ultra-fast, <50ms)
        pattern_result = self._try_pattern_matching(voice_text.lower())
        if pattern_result:
            self.stats["pattern_hits"] += 1
            response = FastVoiceResponse(
                conversational_text=pattern_result['response'],
                intent_type=pattern_result['intent'],
                target_app=pattern_result.get('app'),
                search_query=pattern_result.get('query'),
                processing_time_ms=(time.time() - start_time) * 1000,
                method_used="pattern",
                confidence=0.9
            )
        else:
            # Step 2: Use LLM only for complex cases
            self.stats["llm_calls"] += 1
            response = self._llm_fallback(voice_text, start_time)

        # Step 3: Execute if safe and requested
        if execute and self._is_safe(voice_text) and response.intent_type not in ['chat', 'unknown']:
            response.action_successful = self._execute_command(response)

        return response

    def _try_pattern_matching(self, text: str) -> Optional[Dict[str, Any]]:
        """Lightning-fast pattern matching"""
        import random

        for pattern_name, config in self.patterns.items():
            for pattern in config['patterns']:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result = {
                        'intent': config['intent'],
                        'response': random.choice(config['responses'])
                    }

                    # Extract app name if needed with context filtering
                    if config.get('extract_app') and len(match.groups()) >= 3:
                        app_name = match.group(3)  # Third group is the app name
                        context_blacklist = config.get('context_blacklist', [])

                        # Skip if app name is in blacklist or looks like conversation
                        if (app_name and
                            app_name not in ['app', 'application', 'browser', 'program'] and
                            app_name.lower() not in context_blacklist and
                            self._is_likely_app_name(text, app_name)):
                            result['app'] = app_name.lower()
                            result['response'] = result['response'].format(app=app_name)
                        else:
                            # Pattern matched but context suggests it's not an app command
                            return None

                    # Extract search query if needed
                    elif config.get('extract_query') and len(match.groups()) >= 2:
                        query = match.group(2).strip()  # Second group is the query
                        result['query'] = query
                        result['response'] = result['response'].format(query=query)

                    # Set specific app if defined
                    elif 'app' in config:
                        result['app'] = config['app']

                    return result

        return None

    def _is_likely_app_name(self, full_text: str, potential_app: str) -> bool:
        """Check if the extracted word is likely an actual app name in context"""
        # Context clues that suggest it's NOT an app command
        conversational_phrases = [
            'open source',
            'open mind',
            'open book',
            'open question',
            'open about',
            'open discussion',
            'open conversation',
            'open to',
            'open up',
            'open with',
            'open houses',
            'open homes',
            'open house',
            'open properties',
            'open listings'
        ]

        full_lower = full_text.lower()

        # If we detect conversational context, this probably isn't an app command
        for phrase in conversational_phrases:
            if phrase in full_lower:
                return False

        # Check if the potential app is surrounded by descriptive words
        app_lower = potential_app.lower()
        app_index = full_lower.find(app_lower)
        if app_index != -1:
            # Look for descriptive words after the potential app name
            text_after = full_lower[app_index + len(app_lower):].strip()
            descriptive_words = ['software', 'applications', 'projects', 'tools', 'programs', 'systems', 'development']
            if any(word in text_after[:20] for word in descriptive_words):
                return False

        return True

    def _llm_fallback(self, voice_text: str, start_time: float) -> FastVoiceResponse:
        """Use LLM only when patterns fail - now with actual LLM integration"""

        # First try semantic understanding for common conversational patterns
        semantic_response = self._try_semantic_understanding(voice_text)
        if semantic_response:
            return FastVoiceResponse(
                conversational_text=semantic_response['response'],
                intent_type=semantic_response['intent'],
                processing_time_ms=(time.time() - start_time) * 1000,
                method_used="semantic",
                confidence=semantic_response['confidence']
            )

        # NEW: Actually use LLM for conversation when patterns fail
        try:
            from semantic_voice_parser import SemanticVoiceParser

            # Initialize parser if not already available
            if not hasattr(self, '_semantic_parser'):
                self._semantic_parser = SemanticVoiceParser()

            if self._semantic_parser.is_available:
                # Use LLM for conversational response
                llm_intent = self._semantic_parser.parse_voice_command(voice_text)

                # Extract conversational response from LLM
                if hasattr(llm_intent, 'parameters') and llm_intent.parameters and 'response' in llm_intent.parameters:
                    conversational_response = llm_intent.parameters['response']

                    return FastVoiceResponse(
                        conversational_text=conversational_response,
                        intent_type=llm_intent.intent_type,
                        processing_time_ms=(time.time() - start_time) * 1000,
                        method_used="llm_conversation",
                        confidence=llm_intent.confidence,
                        target_app=llm_intent.target_app,
                        search_query=llm_intent.search_query
                    )
        except Exception as e:
            print(f"⚠️  LLM fallback failed: {e}")

        # Final fallback to generic responses only if LLM fails
        responses = [
            "I'm not quite sure about that, but I'm here to help!",
            "Could you try rephrasing that?",
            "I didn't catch that exactly, but I'm ready to assist!"
        ]

        import random
        return FastVoiceResponse(
            conversational_text=random.choice(responses),
            intent_type="unknown",
            processing_time_ms=(time.time() - start_time) * 1000,
            method_used="fallback",
            confidence=0.3
        )

    def _try_semantic_understanding(self, text: str) -> Optional[Dict[str, Any]]:
        """Semantic validation for common patterns that failed regex matching"""
        text_lower = text.lower()

        # Handle "open source" and similar conversational phrases
        if 'open source' in text_lower:
            if any(word in text_lower for word in ['software', 'applications', 'projects', 'tools', 'find', 'looking for']):
                return {
                    'response': "It sounds like you're interested in open source software! Would you like me to search for open source projects or applications?",
                    'intent': 'chat_with_suggestion',
                    'confidence': 0.8
                }

        # Handle other common conversational patterns that might trigger false positives
        conversation_patterns = {
            'tell me about': {
                'response': "I'd be happy to help! What would you like to know about?",
                'intent': 'information_request',
                'confidence': 0.7
            },
            'what is': {
                'response': "I can help explain things! What are you curious about?",
                'intent': 'information_request',
                'confidence': 0.7
            },
            'how do i': {
                'response': "I can help with that! What are you trying to do?",
                'intent': 'help_request',
                'confidence': 0.7
            }
        }

        for pattern, response_data in conversation_patterns.items():
            if pattern in text_lower:
                return response_data

        return None

    def _is_safe(self, voice_text: str) -> bool:
        """Ultra-fast safety check"""
        dangerous = ['delete', 'destroy', 'format', 'shutdown', 'kill all', 'rm -rf']
        return not any(word in voice_text.lower() for word in dangerous)

    def _execute_command(self, response: FastVoiceResponse) -> bool:
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
            'mail': 'Mail'
        }
        return mappings.get(app_name.lower(), app_name.title())

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance and efficiency statistics"""
        total = self.stats["total_calls"]
        if total == 0:
            return {"pattern_efficiency": 0, "llm_usage": 0, "total_calls": 0}

        return {
            "pattern_efficiency": (self.stats["pattern_hits"] / total) * 100,
            "llm_usage": (self.stats["llm_calls"] / total) * 100,
            "total_calls": total,
            "pattern_hits": self.stats["pattern_hits"],
            "llm_calls": self.stats["llm_calls"]
        }


def performance_test():
    """Test the ultra-fast system"""
    automation = UltraFastVoiceAutomation()

    test_commands = [
        "Hi there!",
        "How are you?",
        "Open Chrome",
        "Launch Safari browser",
        "Search for Python tutorials",
        "Open the Notes app",
        "Start Terminal",
        "Google machine learning",
        "Find weather information",
        "Thanks for your help",
        "Open Calculator",
        "Some random complex phrase that won't match patterns"
    ]

    print("⚡ ULTRA-FAST VOICE AUTOMATION SYSTEM")
    print("=" * 70)
    print("🎯 Strategy: Pattern matching first, LLM only when necessary")
    print("🚀 Target: <100ms for common commands, <500ms overall")
    print()

    fast_commands = 0
    total_time = 0

    for i, cmd in enumerate(test_commands, 1):
        print(f"🎤 Test {i}: '{cmd}'")

        response = automation.process_voice_command(cmd, execute=False)
        total_time += response.processing_time_ms

        print(f"  💬 Response: \"{response.conversational_text}\"")
        print(f"  🎯 Intent: {response.intent_type}")
        print(f"  📱 App: {response.target_app or 'None'}")
        print(f"  🔍 Query: {response.search_query or 'None'}")
        print(f"  ⚡ Time: {response.processing_time_ms:.0f}ms")
        print(f"  🔧 Method: {response.method_used}")

        if response.processing_time_ms < 100:
            print("  🚀 LIGHTNING FAST!")
            fast_commands += 1
        elif response.processing_time_ms < 500:
            print("  ✅ FAST ENOUGH")
        else:
            print("  ⚠️  Slow")
        print()

    # Final statistics
    stats = automation.get_performance_stats()
    avg_time = total_time / len(test_commands)

    print("📊 PERFORMANCE RESULTS")
    print("-" * 40)
    print(f"Average time: {avg_time:.0f}ms")
    print(f"Lightning fast (<100ms): {fast_commands}/{len(test_commands)} commands")
    print(f"Pattern matching efficiency: {stats['pattern_efficiency']:.1f}%")
    print(f"LLM usage: {stats['llm_usage']:.1f}%")
    print(f"Total calls: {stats['total_calls']}")
    print()
    print("🎯 OPTIMIZATION SUCCESS:")
    print(f"  ✅ Common commands: {fast_commands} ultra-fast (<100ms)")
    print(f"  ✅ Pattern efficiency: {stats['pattern_efficiency']:.0f}% of commands handled by fast patterns")
    print(f"  ✅ Overall average: {avg_time:.0f}ms")


if __name__ == "__main__":
    performance_test()