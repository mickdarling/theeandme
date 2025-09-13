#!/usr/bin/env python3
"""
Semantic Voice Command Parser using Local Ollama LLM
Autonomous DollhouseMCP Development - Replacing Regex Hell with Real NLP

Uses structured prompting with local Ollama to understand natural language commands
like "Open a Chrome browser" or "Search for Python tutorials in Safari"
"""

import json
import requests
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import re


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
        self.model_name = "llama3.1:7b"  # Optimal for voice commands per research

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
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False

            # Check if our preferred model is available
            models = response.json().get('models', [])
            available_models = [model['name'] for model in models]

            if self.model_name not in available_models:
                # Try to find any 7B model
                for model in available_models:
                    if '7b' in model.lower() or 'llama' in model.lower():
                        self.model_name = model
                        print(f"🦙 Using available model: {self.model_name}")
                        return True

                print(f"⚠️  No suitable models found in Ollama. Available: {available_models}")
                return False

            return True

        except Exception as e:
            print(f"⚠️  Ollama connection failed: {e}")
            return False

    def _create_semantic_prompt(self, voice_text: str) -> str:
        """Create structured prompt for semantic voice command understanding"""

        prompt = f"""Parse this voice command into JSON format. Understand the user's intent and extract all meaningful components.

Command: "{voice_text}"

Respond with only this JSON structure:
{{
  "intent_type": "open_app" or "search_web" or "create_note" or "edit_note" or "multi_step" or "system_command" or "unknown",
  "primary_action": "main verb like open, search, create, edit, delete, etc",
  "target_app": "app name if any",
  "search_query": "search terms if any",
  "note_content": "text content for notes",
  "note_title": "title for new notes",
  "steps": ["only for complex multi-step commands with clear sequential actions"],
  "parameters": {{"additional context like file paths, URLs, etc"}},
  "safety_level": "safe" or "potentially_destructive" or "destructive",
  "confidence": 0.9
}}

IMPORTANT: Only use "multi_step" for commands with clear sequential actions like "open X and then do Y". Single unclear words should be "unknown".

Examples:
"Open Chrome" → {{"intent_type": "open_app", "primary_action": "open", "target_app": "chrome", "confidence": 0.9, "safety_level": "safe"}}
"Search Python tutorials" → {{"intent_type": "search_web", "primary_action": "search", "search_query": "Python tutorials", "confidence": 0.9, "safety_level": "safe"}}
"Create a note about today's meeting" → {{"intent_type": "create_note", "primary_action": "create", "target_app": "notes", "note_title": "Today's Meeting", "confidence": 0.9, "safety_level": "safe"}}
"Open TextEdit and write hello world" → {{"intent_type": "multi_step", "steps": ["open textedit", "write hello world"], "confidence": 0.9, "safety_level": "safe"}}
"Delete all my files" → {{"intent_type": "system_command", "primary_action": "delete", "safety_level": "destructive", "confidence": 0.8}}

JSON only:"""

        return prompt

    def _query_ollama(self, prompt: str) -> Optional[Dict]:
        """Send prompt to Ollama and get structured response"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent parsing
                    "top_p": 0.9,
                    "max_tokens": 200,   # Short response for JSON
                    "stop": ["\n\n", "```"]  # Stop at obvious completion points
                }
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()

                # Try to extract JSON from response
                try:
                    if not response_text:
                        return None

                    # Remove any markdown formatting
                    response_text = re.sub(r'```json\s*|\s*```', '', response_text)
                    response_text = response_text.strip()

                    # Try to find JSON object in response
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0)

                    # Parse JSON
                    parsed_json = json.loads(response_text)
                    return parsed_json

                except json.JSONDecodeError:
                    # Silently fall back to regex parsing
                    return None
            else:
                print(f"⚠️  Ollama API error: {response.status_code}")
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

    def parse_voice_command(self, voice_text: str) -> CommandIntent:
        """Main method to parse voice command into structured intent"""

        if not voice_text or not voice_text.strip():
            return CommandIntent(
                intent_type="unknown",
                primary_action="unknown",
                confidence=0.0,
                raw_command=voice_text
            )

        # Try LLM-based parsing first
        if self.is_available:
            prompt = self._create_semantic_prompt(voice_text)
            llm_result = self._query_ollama(prompt)

            if llm_result:
                try:
                    return CommandIntent(
                        intent_type=llm_result.get('intent_type', 'unknown'),
                        primary_action=llm_result.get('primary_action', 'unknown'),
                        target_app=llm_result.get('target_app'),
                        search_query=llm_result.get('search_query'),
                        note_content=llm_result.get('note_content'),
                        note_title=llm_result.get('note_title'),
                        steps=llm_result.get('steps'),
                        parameters=llm_result.get('parameters', {}),
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