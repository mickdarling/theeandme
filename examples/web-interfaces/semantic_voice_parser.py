#!/usr/bin/env python3
"""
Semantic Voice Command Parser using Local Ollama LLM
Autonomous DollhouseMCP Development - Replacing Regex Hell with Real NLP

Uses structured prompting with local Ollama to understand natural language commands
like "Open a Chrome browser" or "Search for Python tutorials in Safari"
"""

import json
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import re
import urllib.request
import urllib.parse


@dataclass
class CommandIntent:
    """Structured representation of parsed voice command intent"""
    intent_type: str  # "open_app", "search_web", "create_note", "multi_step", etc.
    primary_action: str  # "open", "search", "create", "edit", "delete", etc.
    target_app: Optional[str] = None  # "chrome", "safari", "notes", "textedit"
    search_query: Optional[str] = None  # "Python tutorials"
    note_content: Optional[str] = None  # Text content for notes
    note_title: Optional[str] = None  # Title for new notes
    steps: Optional[List[str]] = None  # Multi-step command breakdown
    parameters: Dict[str, Any] = None  # Additional context
    safety_level: str = "safe"  # "safe", "potentially_destructive", "destructive"
    confidence: float = 0.0  # Parser confidence (0-1)
    raw_command: str = ""  # Original voice text


class SemanticVoiceParser:
    """Local LLM-powered semantic parser for voice commands"""

    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.model_name = "llama3.1:latest"  # Use latest model, often optimized
        self.backup_model = "llama3.1:8b"   # Fallback to 8b model

        # Verify Ollama is available
        self.is_available = self._check_ollama_availability()
        if not self.is_available:
            print("⚠️  Ollama not available, falling back to regex patterns")

        # FIXED: Improved fallback regex patterns for better semantic understanding
        self.fallback_patterns = {
            'open_app': [
                r'(?:open|launch|start|run)\s+(?:a\s+|the\s+|up\s+)?(\w+)(?:\s+(?:browser|app|application|tab|window))?',
                r'(?:open|launch)\s+(?:the\s+)?(\w+)\s+(?:app|application)',
                r'(?:start|run)\s+(?:the\s+)?(\w+)',
            ],
            'search_web': [
                r'(?:search|google|look\s+up|find)(?:\s+for)?\s+(.+?)(?:\s+in\s+\w+)?$',
                r'(?:search|google)\s+(.+)',
            ]
        }

    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            # Check if Ollama is running
            req = urllib.request.Request(f"{self.ollama_base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    return False

                # Check if our preferred model is available
                response_data = json.loads(response.read().decode('utf-8'))
                models = response_data.get('models', [])
                available_models = [model['name'] for model in models]

            if self.model_name not in available_models:
                # Try backup model first
                if self.backup_model in available_models:
                    self.model_name = self.backup_model
                    print(f"🦙 Using backup model: {self.model_name}")
                    return True

                # Try to find any suitable fast model
                for model in available_models:
                    if 'instruct' in model.lower() and ('7b' in model.lower() or '8b' in model.lower()):
                        self.model_name = model
                        print(f"🦙 Using fast instruct model: {self.model_name}")
                        return True
                    elif '7b' in model.lower() or '8b' in model.lower():
                        self.model_name = model
                        print(f"🦙 Using available model: {self.model_name}")
                        return True

                print(f"⚠️  No suitable models found in Ollama. Available: {available_models}")
                return False

            return True

        except Exception as e:
            print(f"⚠️  Ollama connection failed: {e}")
            return False

    def _create_conversational_prompt(self, voice_text: str, conversation_context: str = "") -> str:
        """Create conversational prompt that responds naturally AND parses commands"""

        context_section = ""
        if conversation_context and conversation_context.strip():
            context_section = f"""
Recent conversation context:
{conversation_context}

"""

        prompt = f"""You are a voice assistant. {context_section}The user said: "{voice_text}"

Respond with ONLY a JSON object in this exact format:

{{"response": "natural conversational response", "intent_type": "open_app|search_web|create_note|chat|unknown", "target_app": "app_name or null", "search_query": "query or null", "confidence": 0.9}}

Examples:
"Open Chrome" → {{"response":"Opening Chrome for you!","intent_type":"open_app","target_app":"chrome","confidence":0.9}}
"How are you?" → {{"response":"I'm doing great, thanks for asking!","intent_type":"chat","confidence":0.9}}
"What is open source software?" → {{"response":"Open source software is software with source code that anyone can inspect, modify, and enhance. Popular examples include Linux, Python, and WordPress.","intent_type":"chat","confidence":0.9}}
"Can you remember 77°F?" → {{"response":"I'll remember that the temperature is 77°F.","intent_type":"chat","confidence":0.9}}
"What's the temperature?" → {{"response":"You mentioned it's 77°F.","intent_type":"chat","confidence":0.9}} (if 77°F was mentioned in context)

Use conversation context to provide accurate, contextual responses. Respond with ONLY the JSON object, no other text:"""

        return prompt

    def _query_ollama(self, prompt: str) -> Optional[Dict]:
        """Send prompt to Ollama with optimized streaming response"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,  # Non-streaming is actually faster for short responses
                "options": {
                    "temperature": 0.3,  # Slightly higher for natural conversation
                    "top_p": 0.8,      # Allow more creativity for responses
                    "num_predict": 120, # Enough tokens for conversational response + JSON
                    "stop": ["\n\n"],   # Stop at double newline
                    "repeat_penalty": 1.1
                }
            }

            # Convert payload to JSON and encode
            json_data = json.dumps(payload).encode('utf-8')

            # Create request
            req = urllib.request.Request(
                f"{self.ollama_base_url}/api/generate",
                data=json_data,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    response_text = response_data.get('response', '').strip()

                    # Try to parse as JSON directly first
                    if response_text:
                        try:
                            # Try direct JSON parsing first
                            parsed_json = json.loads(response_text.strip())
                            return parsed_json
                        except json.JSONDecodeError:
                            # If that fails, try to extract JSON from text
                            try:
                                start_idx = response_text.find('{')
                                if start_idx != -1:
                                    # Find the matching closing brace
                                    brace_count = 0
                                    end_idx = start_idx
                                    for i, char in enumerate(response_text[start_idx:], start_idx):
                                        if char == '{':
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                end_idx = i + 1
                                                break

                                    if end_idx > start_idx:
                                        json_str = response_text[start_idx:end_idx]
                                        parsed_json = json.loads(json_str)
                                        return parsed_json
                            except json.JSONDecodeError:
                                pass
                    return None
                else:
                    print(f"⚠️  Ollama API error: {response.status}")
                    return None

        except Exception as e:
            print(f"⚠️  Ollama query failed: {e}")
            return None

    def _fallback_parse(self, voice_text: str) -> CommandIntent:
        """Fallback regex-based parsing when LLM is unavailable"""
        voice_text = voice_text.lower().strip()

        # Try to match patterns
        for intent_type, patterns in self.fallback_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, voice_text, re.IGNORECASE)
                if match:
                    if intent_type == 'open_app':
                        return CommandIntent(
                            intent_type=intent_type,
                            primary_action="open",
                            target_app=match.group(1).lower(),
                            confidence=0.7,
                            raw_command=voice_text
                        )
                    elif intent_type == 'search_web':
                        return CommandIntent(
                            intent_type=intent_type,
                            primary_action="search",
                            search_query=match.group(1),
                            confidence=0.6,
                            raw_command=voice_text
                        )

        return CommandIntent(
            intent_type="unknown",
            primary_action="unknown",
            confidence=0.1,
            raw_command=voice_text
        )

    def parse_voice_command(self, voice_text: str, conversation_context: str = "") -> CommandIntent:
        """Main method to parse voice command into structured intent"""

        if not voice_text or not voice_text.strip():
            return CommandIntent(
                intent_type="unknown",
                primary_action="unknown",
                confidence=0.0,
                raw_command=voice_text
            )

        # Try conversational LLM parsing first
        if self.is_available:
            prompt = self._create_conversational_prompt(voice_text, conversation_context)
            llm_result = self._query_ollama(prompt)

            if llm_result:
                try:
                    return CommandIntent(
                        intent_type=llm_result.get('intent_type', 'unknown'),
                        primary_action=llm_result.get('intent_type', 'unknown'),  # Use intent_type as action for simplicity
                        target_app=llm_result.get('target_app'),
                        search_query=llm_result.get('search_query'),
                        note_content=llm_result.get('note_content'),
                        note_title=llm_result.get('note_title'),
                        parameters={'response': llm_result.get('response', '')},  # Store conversational response
                        safety_level=llm_result.get('safety_level', 'safe'),
                        confidence=float(llm_result.get('confidence', 0.0)),
                        raw_command=voice_text
                    )
                except Exception as e:
                    print(f"⚠️  Error processing LLM result: {e}")

        # Fall back to regex patterns
        print("🔄 Using fallback regex parsing")
        return self._fallback_parse(voice_text)

    def get_app_mapping(self, app_name: str) -> str:
        """Map common app names to actual macOS application names"""
        mappings = {
            'chrome': 'Google Chrome',
            'safari': 'Safari',
            'firefox': 'Firefox',
            'notes': 'Notes',
            'textedit': 'TextEdit',
            'terminal': 'Terminal',
            'calculator': 'Calculator',
            'calendar': 'Calendar',
            'mail': 'Mail',
            'finder': 'Finder'
        }
        return mappings.get(app_name.lower(), app_name)


def test_semantic_parser():
    """Test the semantic voice parser with various commands"""
    parser = SemanticVoiceParser()

    test_commands = [
        "Open a Chrome browser",
        "Launch the Safari app",
        "Search for Python tutorials",
        "Open Chrome and search for machine learning",
        "Create a new note",
        "Find voice recognition tools in Safari",
        "Start the calculator",
        "Open up TextEdit",
        "Google natural language processing",
        "This is not a valid command"
    ]

    print("🧪 Testing Semantic Voice Command Parser")
    print("=" * 60)
    print(f"🦙 Ollama Available: {'Yes' if parser.is_available else 'No'}")
    print(f"🎯 Model: {parser.model_name}")
    print()

    for cmd in test_commands:
        print(f"🎤 Testing: '{cmd}'")

        start_time = time.time()
        intent = parser.parse_voice_command(cmd)
        end_time = time.time()

        print(f"  Intent Type: {intent.intent_type}")
        print(f"  Primary Action: {intent.primary_action}")
        print(f"  Target App: {intent.target_app}")
        print(f"  Search Query: {intent.search_query}")
        print(f"  Parameters: {intent.parameters}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"  Parse Time: {(end_time - start_time)*1000:.1f}ms")
        print()


if __name__ == "__main__":
    test_semantic_parser()