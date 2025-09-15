#!/usr/bin/env python3
"""
Voice Intent Automation System 2025
Autonomous DollhouseMCP Development - App Automation Prototype

Extends the breakthrough voice interface with app automation capabilities.
Implements voice commands like "Open Chrome" and "Search for Python tutorials"
"""

import subprocess
import re
import os
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from semantic_voice_parser import SemanticVoiceParser


class VoiceIntentAutomation:
    """Intent recognition and macOS app automation for voice commands"""

    def __init__(self):
        # Initialize semantic parser for intelligent command understanding
        self.semantic_parser = SemanticVoiceParser()

        self.automation_stats = {
            'total_commands': 0,
            'successful_automations': 0,
            'failed_automations': 0,
            'commands_by_type': {},
            'semantic_parser_available': self.semantic_parser.is_available
        }

        # App name mappings for macOS - CRITICAL FIX: Handle space-separated names
        self.app_mappings = {
            'chrome': 'Google Chrome',
            'safari': 'Safari',
            'firefox': 'Firefox',
            'terminal': 'Terminal',
            'finder': 'Finder',
            'calculator': 'Calculator',
            'notes': 'Notes',
            'calendar': 'Calendar',
            'mail': 'Mail',
            'textedit': 'TextEdit',
            'text edit': 'TextEdit',  # CRITICAL: Handle "Text Edit" with space
            'text editor': 'TextEdit',
            'code': 'Visual Studio Code',
            'vscode': 'Visual Studio Code',
            'visual studio code': 'Visual Studio Code',
            'photoshop': 'Adobe Photoshop',
            'adobe photoshop': 'Adobe Photoshop'
        }

    def parse_intent(self, voice_text: str) -> Dict:
        """Parse voice text using semantic understanding (Ollama LLM) with regex fallback"""
        # Use semantic parser for intelligent understanding
        intent = self.semantic_parser.parse_voice_command(voice_text)

        # Convert semantic parser result to our expected format
        result = {
            'intent': intent.intent_type,
            'raw_text': voice_text,
            'confidence': intent.confidence,
            'target_app': intent.target_app,
            'search_query': intent.search_query,
            'primary_action': intent.primary_action,
            'parameters': intent.parameters or {}
        }

        # Add specific matches based on intent type for backward compatibility
        if intent.intent_type == 'open_app' and intent.target_app:
            result['matches'] = [intent.target_app]
        elif intent.intent_type == 'search_web' and intent.search_query:
            result['matches'] = [intent.search_query]
        elif intent.intent_type == 'browser_navigate':
            # For complex commands like "open Chrome and search for X"
            if intent.target_app and intent.search_query:
                result['matches'] = [intent.target_app, intent.search_query]
        else:
            result['matches'] = []

        return result

    def execute_open_app(self, app_name: str) -> Tuple[bool, str]:
        """Execute app opening command via osascript with improved error handling"""
        try:
            # CRITICAL FIX: Normalize app name by removing extra spaces and converting to lowercase
            normalized_name = ' '.join(app_name.lower().split())

            # Map common names to actual app names
            actual_app_name = self.app_mappings.get(normalized_name, app_name.title())

            print(f"🚀 Opening app: '{app_name}' -> '{actual_app_name}'")

            # Use osascript to open the application
            cmd = f'tell application "{actual_app_name}" to activate'
            result = subprocess.run(['osascript', '-e', cmd],
                                  capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                return True, f"Successfully opened {actual_app_name}"
            else:
                # FALLBACK: Try using 'open' command if osascript fails
                try:
                    fallback_result = subprocess.run(['open', '-a', actual_app_name],
                                                   capture_output=True, text=True, timeout=10)
                    if fallback_result.returncode == 0:
                        return True, f"Successfully opened {actual_app_name} (fallback method)"
                    else:
                        return False, f"App not found: '{actual_app_name}'. Try: {list(self.app_mappings.keys())[:5]}"
                except Exception:
                    return False, f"Failed to open {actual_app_name}: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"Timeout opening {app_name}"
        except Exception as e:
            return False, f"Error opening {app_name}: {str(e)}"

    def execute_search_web(self, search_query: str, browser: str = "chrome") -> Tuple[bool, str]:
        """Execute web search in specified browser"""
        try:
            # First open the browser
            browser_app = self.app_mappings.get(browser.lower(), "Google Chrome")

            # Open browser
            open_success, open_msg = self.execute_open_app(browser.lower())
            if not open_success:
                return False, f"Could not open browser: {open_msg}"

            # Brief delay for app to open
            time.sleep(1)

            # Create Google search URL
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"

            # Use osascript to navigate to search
            script = f'''
            tell application "{browser_app}"
                tell window 1
                    set URL of active tab to "{search_url}"
                end tell
            end tell
            '''

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"Successfully searched for '{search_query}' in {browser_app}"
            else:
                return False, f"Failed to execute search: {result.stderr}"

        except Exception as e:
            return False, f"Error executing search: {str(e)}"

    def execute_browser_navigate(self, browser: str, search_query: str) -> Tuple[bool, str]:
        """Execute browser opening and navigation in one command"""
        return self.execute_search_web(search_query, browser)

    def execute_url_navigation(self, browser: str, url: str) -> Tuple[bool, str]:
        """Navigate to a specific URL in the specified browser"""
        try:
            # Normalize browser name
            browser = browser.lower()
            if browser not in ['chrome', 'safari', 'firefox']:
                browser = 'safari'  # Default fallback

            # Clean up URL
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"

            # Open browser first
            open_success, _ = self.execute_open_app(browser)
            if not open_success:
                return False, f"Could not open {browser}"

            time.sleep(1)  # Brief delay

            # Use system open command for URL
            result = subprocess.run(['open', url], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"Successfully navigated to {url} in {browser}"
            else:
                return False, f"Failed to navigate to URL: {result.stderr}"

        except Exception as e:
            return False, f"Error navigating to URL: {str(e)}"

    def execute_create_note(self, content: str = "", title: str = "Voice Note") -> Tuple[bool, str]:
        """Create a new note using Notes app"""
        try:
            # First open Notes app
            open_success, _ = self.execute_open_app("notes")
            if not open_success:
                return False, "Could not open Notes app"

            time.sleep(1)  # Brief delay for app to open

            # Use AppleScript to create the note
            safe_title = title.replace('"', '\\"')
            safe_content = content.replace('"', '\\"')

            script = f'''
            tell application "Notes"
                activate
                make new note with properties {{name:"{safe_title}", body:"{safe_content}"}}
            end tell
            '''

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"Created note '{title}' successfully"
            else:
                return False, f"Failed to create note: {result.stderr}"

        except Exception as e:
            return False, f"Error creating note: {str(e)}"

    def execute_claude_code(self, query: str) -> Tuple[bool, str]:
        """Execute Claude Code command via Terminal"""
        try:
            # First activate Terminal
            terminal_success, _ = self.execute_open_app("terminal")
            if not terminal_success:
                return False, "Could not open Terminal for Claude Code"

            # Brief delay for Terminal to open
            time.sleep(2)

            # Use osascript to run Claude Code command in Terminal
            claude_cmd = f"claude {query}"
            script = f'''
            tell application "Terminal"
                if not (exists window 1) then
                    do script ""
                end if
                do script "{claude_cmd}" in window 1
                activate
            end tell
            '''

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"Claude Code command executed: '{claude_cmd}'"
            else:
                return False, f"Failed to execute Claude Code command: {result.stderr}"

        except Exception as e:
            return False, f"Error executing Claude Code command: {str(e)}"

    def execute_voice_command(self, voice_text: str) -> Dict:
        """Main entry point - parse intent and execute automation"""
        self.automation_stats['total_commands'] += 1

        # Parse the intent
        intent_data = self.parse_intent(voice_text)
        intent_type = intent_data['intent']

        # Track command types
        if intent_type not in self.automation_stats['commands_by_type']:
            self.automation_stats['commands_by_type'][intent_type] = 0
        self.automation_stats['commands_by_type'][intent_type] += 1

        result = {
            'timestamp': datetime.now().isoformat(),
            'voice_text': voice_text,
            'intent': intent_data,
            'success': False,
            'message': '',
            'automation_performed': False
        }

        try:
            # CRITICAL FIX: Handle complex commands with better intent processing
            if intent_type == 'open_app' and intent_data['target_app']:
                success, message = self.execute_open_app(intent_data['target_app'])
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'app_launch'
                })

            elif intent_type == 'search_web' and intent_data['search_query']:
                success, message = self.execute_search_web(intent_data['search_query'])
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'web_search'
                })

            elif intent_type == 'browser_navigate':
                # Handle "Open Chrome and search for X" type commands
                if intent_data['target_app'] and intent_data['search_query']:
                    success, message = self.execute_browser_navigate(intent_data['target_app'], intent_data['search_query'])
                elif intent_data['search_query']:
                    # If no specific app mentioned, use default browser
                    success, message = self.execute_search_web(intent_data['search_query'])
                else:
                    success, message = False, "Browser navigate command missing details"

                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'browser_navigate'
                })

            elif intent_type == 'navigate_url' and intent_data.get('browser') and intent_data.get('url'):
                # Handle URL navigation
                browser = intent_data['browser']
                url = intent_data['url']
                success, message = self.execute_url_navigation(browser, url)
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'url_navigation'
                })

            elif intent_type == 'create_note':
                success, message = self.execute_create_note(
                    intent_data.get('note_content', 'Voice note'),
                    intent_data.get('note_title', 'Voice Note')
                )
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'note_creation'
                })

            elif intent_type == 'chat':
                # Handle conversational responses - no automation needed
                conversational_response = intent_data.get('parameters', {}).get('response', 'I heard you!')
                result.update({
                    'success': True,
                    'message': conversational_response,
                    'automation_performed': False,
                    'action_type': 'conversation'
                })

            else:
                # Handle unknown commands with helpful response
                if intent_data.get('parameters', {}).get('response'):
                    response = intent_data['parameters']['response']
                else:
                    response = f"I understood you said '{voice_text}', but I'm not sure how to help with that yet."

                result.update({
                    'success': False,
                    'message': response,
                    'automation_performed': False,
                    'action_type': 'unknown'
                })

            # Update statistics
            if result['success']:
                self.automation_stats['successful_automations'] += 1
            else:
                self.automation_stats['failed_automations'] += 1

        except Exception as e:
            result.update({
                'success': False,
                'message': f"Automation error: {str(e)}",
                'automation_performed': False
            })
            self.automation_stats['failed_automations'] += 1

        return result

    def get_automation_stats(self) -> Dict:
        """Return automation statistics"""
        success_rate = 0
        if self.automation_stats['total_commands'] > 0:
            success_rate = (self.automation_stats['successful_automations'] /
                          self.automation_stats['total_commands']) * 100

        return {
            **self.automation_stats,
            'success_rate': f"{success_rate:.1f}%"
        }


def test_voice_automation():
    """Test the voice automation system"""
    automation = VoiceIntentAutomation()

    test_commands = [
        "Open Chrome",
        "Launch Safari",
        "Search for Python tutorials",
        "Go to Chrome and search for voice recognition",
        "Ask Claude Code about functions",
        "This is not a valid command"
    ]

    print("🚀 Testing Voice Intent Automation System")
    print("=" * 60)

    for cmd in test_commands:
        print(f"\n🎤 Testing: '{cmd}'")
        result = automation.execute_voice_command(cmd)

        print(f"  Intent: {result['intent']['intent']}")
        print(f"  Success: {'✅' if result['success'] else '❌'}")
        print(f"  Message: {result['message']}")

        if result['automation_performed']:
            print(f"  Action: {result['action_type']}")

    print(f"\n📊 Final Statistics:")
    stats = automation.get_automation_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_voice_automation()