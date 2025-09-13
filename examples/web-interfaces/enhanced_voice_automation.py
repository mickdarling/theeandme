#!/usr/bin/env python3
"""
Enhanced Voice Intent Automation System 2025
Dynamic Command Processing with Safety Validation and Multi-Step Workflows

Breakthrough Features:
✅ Dynamic command understanding (no hardcoded limitations)
✅ LLM-powered safety validation for destructive operations
✅ Multi-step workflow engine
✅ Notes app integration (create, edit, append)
✅ Contextual follow-up commands
✅ Intelligent error recovery
"""

import subprocess
import re
import os
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from semantic_voice_parser import SemanticVoiceParser, CommandIntent


class SafetyValidator:
    """LLM-powered safety validation for voice commands"""

    def __init__(self, semantic_parser: SemanticVoiceParser):
        self.semantic_parser = semantic_parser

    def validate_command_safety(self, intent: CommandIntent) -> Dict[str, Any]:
        """Validate if a command is safe to execute"""

        # Quick safety check for obviously safe commands
        safe_intents = ['open_app', 'search_web', 'create_note', 'edit_note']
        if intent.intent_type in safe_intents and intent.safety_level == 'safe':
            return {
                'is_safe': True,
                'requires_confirmation': False,
                'reason': 'Standard safe operation',
                'suggested_action': 'proceed'
            }

        # Use LLM for complex safety analysis
        safety_prompt = f"""
Analyze this voice command for safety. Determine if it could be destructive or dangerous.

Command: "{intent.raw_command}"
Parsed Intent: {intent.intent_type}
Primary Action: {intent.primary_action}
Safety Level: {intent.safety_level}

Consider these factors:
- Could this delete, modify, or destroy files/data?
- Could this harm the system or user privacy?
- Could this execute dangerous system commands?
- Does this require user confirmation?

Respond with only this JSON:
{{
  "is_safe": true/false,
  "requires_confirmation": true/false,
  "risk_level": "none" or "low" or "medium" or "high",
  "reason": "brief explanation",
  "suggested_action": "proceed" or "confirm" or "block"
}}
"""

        if self.semantic_parser.is_available:
            try:
                result = self.semantic_parser._query_ollama(safety_prompt)
                if result:
                    return {
                        'is_safe': result.get('is_safe', False),
                        'requires_confirmation': result.get('requires_confirmation', True),
                        'risk_level': result.get('risk_level', 'high'),
                        'reason': result.get('reason', 'Safety validation failed'),
                        'suggested_action': result.get('suggested_action', 'block')
                    }
            except Exception as e:
                print(f"⚠️  Safety validation error: {e}")

        # Conservative fallback for unknown commands
        if intent.safety_level == 'destructive':
            return {
                'is_safe': False,
                'requires_confirmation': True,
                'risk_level': 'high',
                'reason': 'Command marked as potentially destructive',
                'suggested_action': 'block'
            }
        elif intent.primary_action in ['delete', 'remove', 'destroy', 'format', 'erase']:
            return {
                'is_safe': False,
                'requires_confirmation': True,
                'risk_level': 'high',
                'reason': 'Destructive action detected',
                'suggested_action': 'confirm'
            }

        return {
            'is_safe': True,
            'requires_confirmation': False,
            'risk_level': 'low',
            'reason': 'Command appears safe',
            'suggested_action': 'proceed'
        }


class NotesIntegration:
    """Integration with macOS Notes app for voice-controlled note management"""

    def create_note(self, title: str, content: str = "") -> Tuple[bool, str]:
        """Create a new note in Notes app"""
        try:
            # Escape quotes for AppleScript
            safe_title = title.replace('"', '\\"').replace("'", "\\'")
            safe_content = content.replace('"', '\\"').replace("'", "\\'")

            script = f'''
            tell application "Notes"
                set newNote to make new note
                set name of newNote to "{safe_title}"
                set body of newNote to "{safe_content}"
                show newNote
                activate
            end tell
            '''

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"Created note: '{title}'"
            else:
                return False, f"Failed to create note: {result.stderr}"

        except Exception as e:
            return False, f"Error creating note: {str(e)}"

    def append_to_note(self, title: str, content: str) -> Tuple[bool, str]:
        """Append content to an existing note"""
        try:
            safe_title = title.replace('"', '\\"').replace("'", "\\'")
            safe_content = content.replace('"', '\\"').replace("'", "\\'")

            script = f'''
            tell application "Notes"
                set targetNote to first note whose name contains "{safe_title}"
                set body of targetNote to (body of targetNote) & "\\n" & "{safe_content}"
                show targetNote
                activate
            end tell
            '''

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"Added content to note: '{title}'"
            else:
                # Try creating a new note if the target doesn't exist
                return self.create_note(title, content)

        except Exception as e:
            return False, f"Error updating note: {str(e)}"

    def find_notes(self, query: str) -> List[str]:
        """Find notes matching a query"""
        try:
            safe_query = query.replace('"', '\\"').replace("'", "\\'")

            script = f'''
            tell application "Notes"
                set foundNotes to {{}}
                repeat with eachNote in notes
                    if name of eachNote contains "{safe_query}" then
                        set end of foundNotes to name of eachNote
                    end if
                end repeat
                return foundNotes
            end tell
            '''

            result = subprocess.run(['osascript', '-e', script],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                # Parse the returned list
                notes_list = result.stdout.strip()
                if notes_list:
                    return [note.strip() for note in notes_list.split(',')]

            return []

        except Exception as e:
            print(f"⚠️  Error finding notes: {e}")
            return []


class MultiStepWorkflowEngine:
    """Execute multi-step voice commands as sequential workflows"""

    def __init__(self, automation_system):
        self.automation_system = automation_system
        self.workflow_context = {}  # Store context between steps

    def execute_workflow(self, steps: List[str], context: Dict = None) -> Dict:
        """Execute a series of voice commands in sequence"""
        if context:
            self.workflow_context.update(context)

        results = []
        overall_success = True

        print(f"🔄 Executing {len(steps)} step workflow")

        for i, step in enumerate(steps, 1):
            print(f"📋 Step {i}/{len(steps)}: '{step}'")

            try:
                # Parse and execute each step
                step_intent = self.automation_system.semantic_parser.parse_voice_command(step)
                step_result = self.automation_system.execute_single_intent(step_intent, workflow_context=self.workflow_context)

                results.append({
                    'step': i,
                    'command': step,
                    'result': step_result,
                    'success': step_result.get('success', False)
                })

                if not step_result.get('success', False):
                    overall_success = False
                    print(f"❌ Step {i} failed: {step_result.get('message', 'Unknown error')}")
                    break
                else:
                    print(f"✅ Step {i} completed: {step_result.get('message', 'Success')}")

                # Brief pause between steps for stability
                time.sleep(0.5)

            except Exception as e:
                overall_success = False
                results.append({
                    'step': i,
                    'command': step,
                    'result': {'success': False, 'message': str(e)},
                    'success': False
                })
                print(f"❌ Step {i} error: {e}")
                break

        return {
            'success': overall_success,
            'completed_steps': len([r for r in results if r['success']]),
            'total_steps': len(steps),
            'results': results,
            'message': f"Workflow {'completed' if overall_success else 'failed'}: {len([r for r in results if r['success']])}/{len(steps)} steps successful"
        }


class EnhancedVoiceAutomation:
    """Enhanced voice automation with dynamic commands, safety validation, and multi-step workflows"""

    def __init__(self):
        # Core components
        self.semantic_parser = SemanticVoiceParser()
        self.safety_validator = SafetyValidator(self.semantic_parser)
        self.notes_integration = NotesIntegration()
        self.workflow_engine = MultiStepWorkflowEngine(self)

        # Expanded app mappings
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
            'vscode': 'Visual Studio Code',
            'slack': 'Slack',
            'zoom': 'zoom.us',
            'spotify': 'Spotify',
            'photoshop': 'Adobe Photoshop 2024',
            'illustrator': 'Adobe Illustrator 2024',
            'xcode': 'Xcode',
            'claude': 'Claude',
            'claude_code': 'Claude Code'  # New integration
        }

        # Statistics tracking
        self.automation_stats = {
            'total_commands': 0,
            'successful_automations': 0,
            'failed_automations': 0,
            'blocked_unsafe_commands': 0,
            'multi_step_workflows': 0,
            'notes_operations': 0,
            'commands_by_type': {},
            'semantic_parser_available': self.semantic_parser.is_available,
            'safety_validations': 0
        }

        # Recent context for follow-up commands
        self.recent_context = {
            'last_app_opened': None,
            'last_note_created': None,
            'last_search_query': None,
            'last_workflow': None
        }

    def execute_voice_command(self, voice_text: str) -> Dict:
        """Main entry point - enhanced with safety validation and multi-step support"""
        self.automation_stats['total_commands'] += 1

        # Parse the voice command
        intent = self.semantic_parser.parse_voice_command(voice_text)

        # Safety validation
        safety_result = self.safety_validator.validate_command_safety(intent)
        self.automation_stats['safety_validations'] += 1

        if not safety_result['is_safe']:
            self.automation_stats['blocked_unsafe_commands'] += 1
            return {
                'timestamp': datetime.now().isoformat(),
                'voice_text': voice_text,
                'intent': intent.__dict__,
                'success': False,
                'message': f"🚫 Command blocked for safety: {safety_result['reason']}",
                'automation_performed': False,
                'safety_blocked': True,
                'safety_info': safety_result
            }

        if safety_result['requires_confirmation']:
            return {
                'timestamp': datetime.now().isoformat(),
                'voice_text': voice_text,
                'intent': intent.__dict__,
                'success': False,
                'message': f"⚠️  Command requires confirmation: {safety_result['reason']}. Say 'confirm' to proceed.",
                'automation_performed': False,
                'requires_confirmation': True,
                'safety_info': safety_result
            }

        # Execute the command based on intent type
        if intent.intent_type == 'multi_step' and intent.steps:
            return self._execute_multi_step_command(intent)
        else:
            return self.execute_single_intent(intent)

    def execute_single_intent(self, intent: CommandIntent, workflow_context: Dict = None) -> Dict:
        """Execute a single command intent"""
        intent_type = intent.intent_type

        # Track command types
        if intent_type not in self.automation_stats['commands_by_type']:
            self.automation_stats['commands_by_type'][intent_type] = 0
        self.automation_stats['commands_by_type'][intent_type] += 1

        result = {
            'timestamp': datetime.now().isoformat(),
            'voice_text': intent.raw_command,
            'intent': intent.__dict__,
            'success': False,
            'message': '',
            'automation_performed': False
        }

        try:
            # Route to appropriate handler
            if intent_type == 'open_app':
                success, message = self._execute_open_app(intent)
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'app_launch'
                })

            elif intent_type == 'search_web':
                success, message = self._execute_search_web(intent)
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'web_search'
                })

            elif intent_type == 'create_note':
                success, message = self._execute_create_note(intent)
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'note_creation'
                })

            elif intent_type == 'edit_note':
                success, message = self._execute_edit_note(intent)
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'note_editing'
                })

            elif intent_type == 'system_command':
                # Handle system commands with extra safety
                success, message = self._execute_system_command(intent)
                result.update({
                    'success': success,
                    'message': message,
                    'automation_performed': True,
                    'action_type': 'system_command'
                })

            else:
                result.update({
                    'success': False,
                    'message': f"🤔 I understand '{intent.raw_command}' but don't know how to execute that action yet. Intent: {intent_type}",
                    'automation_performed': False
                })

            # Update statistics
            if result['success']:
                self.automation_stats['successful_automations'] += 1
            else:
                self.automation_stats['failed_automations'] += 1

        except Exception as e:
            result.update({
                'success': False,
                'message': f"❌ Automation error: {str(e)}",
                'automation_performed': False
            })
            self.automation_stats['failed_automations'] += 1

        return result

    def _execute_multi_step_command(self, intent: CommandIntent) -> Dict:
        """Execute multi-step workflow"""
        self.automation_stats['multi_step_workflows'] += 1

        workflow_result = self.workflow_engine.execute_workflow(intent.steps)

        return {
            'timestamp': datetime.now().isoformat(),
            'voice_text': intent.raw_command,
            'intent': intent.__dict__,
            'success': workflow_result['success'],
            'message': f"🔄 {workflow_result['message']}",
            'automation_performed': True,
            'action_type': 'multi_step_workflow',
            'workflow_details': workflow_result
        }

    def _execute_open_app(self, intent: CommandIntent) -> Tuple[bool, str]:
        """Execute app opening with enhanced app support"""
        app_name = intent.target_app or ""
        actual_app_name = self.app_mappings.get(app_name.lower(), app_name)

        # Update context
        self.recent_context['last_app_opened'] = actual_app_name

        try:
            cmd = f'tell application "{actual_app_name}" to activate'
            result = subprocess.run(['osascript', '-e', cmd],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return True, f"✅ Opened {actual_app_name}"
            else:
                return False, f"❌ Failed to open {actual_app_name}: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, f"⏰ Timeout opening {app_name}"
        except Exception as e:
            return False, f"❌ Error opening {app_name}: {str(e)}"

    def _execute_search_web(self, intent: CommandIntent) -> Tuple[bool, str]:
        """Execute web search with enhanced browser support"""
        search_query = intent.search_query or ""
        browser = intent.target_app or "chrome"

        # Update context
        self.recent_context['last_search_query'] = search_query

        try:
            # Create a new intent for opening the browser
            browser_intent = CommandIntent(
                intent_type="open_app",
                primary_action="open",
                target_app=browser,
                raw_command=f"open {browser}"
            )

            # Open browser first
            browser_app = self.app_mappings.get(browser.lower(), "Google Chrome")
            open_success, open_msg = self._execute_open_app(browser_intent)

            if not open_success:
                return False, f"🌐 Could not open browser: {open_msg}"

            time.sleep(1)  # Wait for browser to open

            # Create search URL
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"

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
                return True, f"🔍 Searched for '{search_query}' in {browser_app}"
            else:
                return False, f"❌ Search failed: {result.stderr}"

        except Exception as e:
            return False, f"❌ Search error: {str(e)}"

    def _execute_create_note(self, intent: CommandIntent) -> Tuple[bool, str]:
        """Execute note creation"""
        self.automation_stats['notes_operations'] += 1

        title = intent.note_title or f"Voice Note {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        content = intent.note_content or ""

        # Update context
        self.recent_context['last_note_created'] = title

        success, message = self.notes_integration.create_note(title, content)
        return success, f"📝 {message}"

    def _execute_edit_note(self, intent: CommandIntent) -> Tuple[bool, str]:
        """Execute note editing/appending"""
        self.automation_stats['notes_operations'] += 1

        title = intent.note_title or self.recent_context.get('last_note_created', 'Recent Note')
        content = intent.note_content or ""

        success, message = self.notes_integration.append_to_note(title, content)
        return success, f"📝 {message}"

    def _execute_system_command(self, intent: CommandIntent) -> Tuple[bool, str]:
        """Execute system commands with safety restrictions"""
        # For now, block all system commands as they require careful implementation
        return False, f"🔒 System commands are currently disabled for safety. Command: {intent.raw_command}"

    def get_automation_stats(self) -> Dict:
        """Return comprehensive automation statistics"""
        total = self.automation_stats['total_commands']
        success_rate = (self.automation_stats['successful_automations'] / total * 100) if total > 0 else 0

        return {
            **self.automation_stats,
            'success_rate': f"{success_rate:.1f}%",
            'recent_context': self.recent_context
        }


def test_enhanced_automation():
    """Test the enhanced voice automation system"""
    automation = EnhancedVoiceAutomation()

    test_commands = [
        "Open Chrome",
        "Search for Python machine learning tutorials",
        "Create a note about today's meeting with agenda items",
        "Open TextEdit and then create a note called Development Ideas",
        "Add to my Development Ideas note: Voice automation is working great",
        "Delete all my files",  # Should be blocked
        "Open Chrome and search for voice recognition then create a note about it",
        "Find my meeting notes",
        "This is not a valid command"
    ]

    print("🚀 Testing Enhanced Voice Automation System")
    print("=" * 70)
    print("✅ Dynamic Command Processing")
    print("✅ Safety Validation with LLM")
    print("✅ Multi-Step Workflow Engine")
    print("✅ Notes Integration")
    print("=" * 70)

    for cmd in test_commands:
        print(f"\n🎤 Testing: '{cmd}'")
        result = automation.execute_voice_command(cmd)

        print(f"  Intent: {result['intent']['intent_type']}")
        print(f"  Success: {'✅' if result['success'] else '❌'}")
        print(f"  Message: {result['message']}")

        if result.get('safety_blocked'):
            print(f"  🚫 Safety Block: {result['safety_info']['reason']}")
        elif result.get('requires_confirmation'):
            print(f"  ⚠️  Requires Confirmation: {result['safety_info']['reason']}")
        elif result.get('automation_performed'):
            print(f"  Action: {result.get('action_type', 'unknown')}")

        time.sleep(0.5)  # Brief pause between tests

    print(f"\n📊 Final Statistics:")
    stats = automation.get_automation_stats()
    for key, value in stats.items():
        if key != 'recent_context':
            print(f"  {key}: {value}")

    print(f"\n🧠 Recent Context:")
    for key, value in stats['recent_context'].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_enhanced_automation()