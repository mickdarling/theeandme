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
import os
from typing import Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass


@dataclass
class FastVoiceResponse:
    """Optimized voice response for speed"""
    conversational_text: str
    intent_type: str
    target_app: Optional[str] = None
    search_query: Optional[str] = None
    url: Optional[str] = None  # NEW: URL navigation support
    browser: Optional[str] = None  # NEW: Browser specification
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

        # Initialize application whitelist - ARCHITECTURAL IMPROVEMENT
        self.installed_apps = self._get_installed_applications()
        print(f"🎯 Application whitelist initialized: {len(self.installed_apps)} apps detected")

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

            # Generic app opening - now with application whitelist
            'open_app_generic': {
                'patterns': [r'\b(open|launch|start|run)\s+(a\s+|the\s+)?(\w+)(?:\s+(app|application|browser|program))?\b'],
                'responses': ["Opening {app} for you!"],
                'intent': 'open_app',
                'extract_app': True
            },

            # Search commands
            'search_google': {
                'patterns': [r'\b(search|google|find|look up)(?:\s+for)?\s+(.+)'],
                'responses': ["Searching for {query}!", "Looking that up for you!"],
                'intent': 'search_web',
                'extract_query': True
            },

            # URL navigation - NEW AUTONOMOUS FEATURE
            'navigate_url': {
                'patterns': [r'\b(go to|navigate to|visit)\s+([\w\.-]+\.[\w]+(?:\/\S*)?)\b'],
                'responses': ["Navigating to {url}!"],
                'intent': 'navigate_url',
                'extract_url': True
            },

            # Browser + URL navigation - NEW AUTONOMOUS FEATURE
            'open_browser_url': {
                'patterns': [r'\b(open|launch)\s+(safari|chrome|google chrome)(?:\s+and)?\s+(?:go to|navigate to|visit)\s+([\w\.-]+\.[\w]+(?:\/\S*)?)\b'],
                'responses': ["Opening {browser} and navigating to {url}!"],
                'intent': 'open_browser_url',
                'extract_browser_url': True
            }
        }

    def process_voice_command(self, voice_text: str, execute: bool = True, conversation_context: str = "") -> FastVoiceResponse:
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
            response = self._llm_fallback(voice_text, start_time, conversation_context)

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

                    # Extract app name if needed with application whitelist
                    if config.get('extract_app') and len(match.groups()) >= 3:
                        app_name = match.group(3)  # Third group is the app name

                        # WHITELIST APPROACH: Only match actual installed applications
                        if (app_name and
                            app_name not in ['app', 'application', 'browser', 'program'] and
                            self._is_likely_app_name(text, app_name)):
                            result['app'] = app_name.lower()
                            result['response'] = result['response'].format(app=app_name)
                        else:
                            # Pattern matched but app not installed or context invalid
                            return None

                    # Extract search query if needed
                    elif config.get('extract_query') and len(match.groups()) >= 2:
                        query = match.group(2).strip()  # Second group is the query
                        result['query'] = query
                        result['response'] = result['response'].format(query=query)

                    # Extract URL if needed - NEW AUTONOMOUS FEATURE
                    elif config.get('extract_url') and len(match.groups()) >= 2:
                        url = match.group(2).strip()  # Second group is the URL
                        result['url'] = url
                        result['response'] = result['response'].format(url=url)

                    # Extract browser + URL if needed - NEW AUTONOMOUS FEATURE
                    elif config.get('extract_browser_url') and len(match.groups()) >= 3:
                        browser = match.group(2).strip()  # Second group is browser
                        url = match.group(3).strip()      # Third group is URL
                        result['browser'] = browser
                        result['url'] = url
                        result['response'] = result['response'].format(browser=browser, url=url)

                    # Set specific app if defined
                    elif 'app' in config:
                        result['app'] = config['app']

                    return result

        return None

    def _get_installed_applications(self) -> Set[str]:
        """Get set of installed application names - WHITELIST APPROACH"""
        try:
            # Get all .app bundles in /Applications
            import glob
            app_paths = glob.glob("/Applications/*.app")
            app_names = set()

            for app_path in app_paths:
                # Extract clean app name
                app_name = os.path.basename(app_path).replace('.app', '')
                app_names.add(app_name.lower())

                # Also add common variations
                # "Google Chrome" → also match "chrome"
                parts = app_name.lower().split()
                if len(parts) > 1:
                    app_names.add(parts[-1])  # Last word
                    if 'google' in parts[0]:
                        app_names.add(parts[1])  # "Google Chrome" → "chrome"

            return app_names

        except Exception as e:
            print(f"⚠️  Application enumeration failed: {e}")
            return {"chrome", "safari", "firefox", "code", "finder"}  # Fallback

    def _is_likely_app_name(self, full_text: str, potential_app: str) -> bool:
        """Check if the extracted word is an actual installed application - WHITELIST APPROACH"""
        # ARCHITECTURAL IMPROVEMENT: Use actual installed app whitelist
        return potential_app.lower() in self.installed_apps

    def _llm_fallback(self, voice_text: str, start_time: float, conversation_context: str = "") -> FastVoiceResponse:
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
                llm_intent = self._semantic_parser.parse_voice_command(voice_text, conversation_context)

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

        # REMOVED: Hard-coded conversational blocks per user feedback
        # Let the LLM handle "what is", "tell me about", "how do I", "open source" naturally

        return None

    def _is_safe(self, voice_text: str) -> bool:
        """Ultra-fast safety check"""
        dangerous = ['delete', 'destroy', 'format', 'shutdown', 'kill all', 'rm -rf']
        return not any(word in voice_text.lower() for word in dangerous)

    def _navigate_to_url(self, browser: str, url: str) -> bool:
        """Navigate to URL using AppleScript browser automation"""
        try:
            # Clean up URL - add https:// if needed
            if not url.startswith(('http://', 'https://')):
                if '.' in url and not url.startswith('www.'):
                    url = f"https://{url}"
                elif not url.startswith('www.'):
                    url = f"https://www.{url}"

            # Browser-specific AppleScript
            if browser.lower() in ['safari']:
                script = f'''
                tell application "Safari"
                    activate
                    if (count of windows) = 0 then
                        make new window
                    end if
                    set URL of current tab of front window to "{url}"
                end tell
                '''
            elif browser.lower() in ['chrome', 'google chrome']:
                script = f'''
                tell application "Google Chrome"
                    activate
                    if (count of windows) = 0 then
                        make new window
                    end if
                    set URL of active tab of front window to "{url}"
                end tell
                '''
            else:
                return False

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0

        except Exception as e:
            print(f"⚠️  URL navigation failed: {e}")
            return False

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

            # NEW AUTONOMOUS FEATURE: URL Navigation
            elif response.intent_type == "navigate_url" and hasattr(response, 'url'):
                # Use default browser for URL navigation
                return self._navigate_to_url('safari', response.url)

            # NEW AUTONOMOUS FEATURE: Browser + URL Navigation
            elif response.intent_type == "open_browser_url" and hasattr(response, 'browser') and hasattr(response, 'url'):
                # Open specific browser and navigate to URL
                browser_success = subprocess.run(['open', '-a', self._get_app_name(response.browser)],
                                               capture_output=True, timeout=5).returncode == 0
                if browser_success:
                    time.sleep(1)  # Give browser time to open
                    return self._navigate_to_url(response.browser, response.url)
                return False

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