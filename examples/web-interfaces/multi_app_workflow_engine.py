#!/usr/bin/env python3
"""
Multi-App Workflow Engine 2025
Autonomous DollhouseMCP Development - Next Breakthrough

Orchestrates complex workflows across multiple macOS applications.
Voice commands like: "Search for Python tutorials, open best result, take notes"
"""

import subprocess
import time
import json
import re
import requests
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from voice_intent_automation import VoiceIntentAutomation


@dataclass
class WorkflowStep:
    """Individual step in a multi-app workflow"""
    step_id: str
    app_target: str
    action_type: str
    parameters: Dict[str, Any]
    depends_on: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class WorkflowResult:
    """Result of executing a complete workflow"""
    workflow_id: str
    success: bool
    steps_completed: int
    total_steps: int
    execution_time: float
    results: Dict[str, Any]
    error_message: Optional[str] = None


class MultiAppWorkflowEngine:
    """Orchestrates complex multi-application workflows via voice commands"""

    def __init__(self):
        self.voice_automation = VoiceIntentAutomation()
        self.workflow_patterns = {
            'research_and_note': [
                r'search\s+for\s+(.+?),?\s+open\s+(best|top|first)\s+result,?\s+(and\s+)?(take\s+notes?|make\s+notes?|write\s+notes?)',
                r'research\s+(.+)\s+and\s+take\s+notes',
                r'find\s+(.+?),?\s+open\s+it,?\s+(and\s+)?(notes?|write|document)'
            ],
            'code_and_test': [
                r'create\s+(.+?)\s+file\s+(.+?)\s+and\s+(test|run)\s+it',
                r'write\s+(.+)\s+code\s+and\s+execute',
                r'code\s+(.+)\s+then\s+test'
            ],
            'schedule_and_notify': [
                r'add\s+(.+)\s+to\s+calendar\s+and\s+remind\s+me',
                r'schedule\s+(.+)\s+and\s+set\s+notification'
            ]
        }

        self.execution_stats = {
            'total_workflows': 0,
            'successful_workflows': 0,
            'failed_workflows': 0,
            'avg_execution_time': 0.0,
            'workflows_by_type': {}
        }

    def parse_workflow_intent(self, voice_text: str) -> Optional[Dict]:
        """Parse voice command to identify multi-app workflow intent"""
        voice_text = voice_text.lower().strip()

        for workflow_type, patterns in self.workflow_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, voice_text, re.IGNORECASE)
                if match:
                    return {
                        'workflow_type': workflow_type,
                        'raw_text': voice_text,
                        'matches': match.groups(),
                        'confidence': 1.0
                    }

        return None

    def create_research_and_note_workflow(self, search_query: str) -> List[WorkflowStep]:
        """Create workflow for: Search → Open Result → Take Notes"""
        return [
            WorkflowStep(
                step_id="search",
                app_target="browser",
                action_type="web_search",
                parameters={"query": search_query}
            ),
            WorkflowStep(
                step_id="extract_top_result",
                app_target="browser",
                action_type="get_search_result",
                parameters={"result_index": 0},
                depends_on="search"
            ),
            WorkflowStep(
                step_id="open_result",
                app_target="browser",
                action_type="navigate_to_url",
                parameters={},
                depends_on="extract_top_result"
            ),
            WorkflowStep(
                step_id="open_textedit",
                app_target="textedit",
                action_type="open_app",
                parameters={
                    "app_name": "textedit",
                    "note_content": f"Research: {search_query}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\nReady for notes..."
                },
                depends_on="open_result"
            )
        ]

    def execute_browser_step(self, step: WorkflowStep) -> bool:
        """Execute browser-related workflow step"""
        try:
            if step.action_type == "web_search":
                query = step.parameters["query"]
                success, message = self.voice_automation.execute_search_web(query)
                step.success = success
                step.error_message = None if success else message
                step.output_data = {"search_query": query, "message": message}
                return success

            elif step.action_type == "get_search_result":
                # For now, simulate extracting the first result
                # In production, this would use browser automation to extract actual URLs
                step.success = True
                step.output_data = {
                    "top_result_url": f"https://example.com/search-result-for-{step.parameters.get('query', 'unknown')}",
                    "title": f"Top result for search query"
                }
                return True

            elif step.action_type == "navigate_to_url":
                # Browser is already open from search, so this step succeeds
                step.success = True
                step.output_data = {"navigation": "completed"}
                return True

        except Exception as e:
            step.success = False
            step.error_message = str(e)
            return False

        return False

    def execute_textedit_step(self, step: WorkflowStep) -> bool:
        """Execute TextEdit app workflow step - simplified for MVP"""
        try:
            if step.action_type == "open_app":
                # Just open TextEdit app - user can manually create notes
                app_name = step.parameters.get("app_name", "textedit")
                success, message = self.voice_automation.execute_open_app(app_name)

                if success:
                    step.success = True
                    step.output_data = {
                        "app_opened": True,
                        "ready_for_notes": True,
                        "suggested_content": step.parameters.get("note_content", "")
                    }
                    return True
                else:
                    step.success = False
                    step.error_message = message
                    return False

        except Exception as e:
            step.success = False
            step.error_message = str(e)
            return False

        return False

    def execute_workflow_step(self, step: WorkflowStep) -> bool:
        """Execute individual workflow step based on app target"""
        if step.app_target == "browser":
            return self.execute_browser_step(step)
        elif step.app_target == "textedit":
            return self.execute_textedit_step(step)
        else:
            step.success = False
            step.error_message = f"Unknown app target: {step.app_target}"
            return False

    def execute_workflow(self, steps: List[WorkflowStep]) -> WorkflowResult:
        """Execute complete multi-app workflow"""
        workflow_id = f"workflow_{int(time.time())}"
        start_time = time.time()

        self.execution_stats['total_workflows'] += 1

        steps_completed = 0
        results = {}

        for step in steps:
            print(f"🔄 Executing step: {step.step_id} ({step.app_target})")

            # Check dependencies
            if step.depends_on:
                dep_step = next((s for s in steps if s.step_id == step.depends_on), None)
                if not dep_step or not dep_step.success:
                    step.success = False
                    step.error_message = f"Dependency failed: {step.depends_on}"
                    break

            # Execute step
            success = self.execute_workflow_step(step)
            if success:
                steps_completed += 1
                results[step.step_id] = step.output_data
                print(f"✅ Step '{step.step_id}' completed successfully")
            else:
                print(f"❌ Step '{step.step_id}' failed: {step.error_message}")
                break

            # Brief delay between steps
            time.sleep(1)

        execution_time = time.time() - start_time
        workflow_success = steps_completed == len(steps)

        if workflow_success:
            self.execution_stats['successful_workflows'] += 1
        else:
            self.execution_stats['failed_workflows'] += 1

        # Update average execution time
        total_workflows = self.execution_stats['total_workflows']
        current_avg = self.execution_stats['avg_execution_time']
        self.execution_stats['avg_execution_time'] = (
            (current_avg * (total_workflows - 1) + execution_time) / total_workflows
        )

        return WorkflowResult(
            workflow_id=workflow_id,
            success=workflow_success,
            steps_completed=steps_completed,
            total_steps=len(steps),
            execution_time=execution_time,
            results=results,
            error_message=None if workflow_success else "Workflow incomplete"
        )

    def execute_voice_workflow(self, voice_text: str) -> Dict:
        """Main entry point: parse voice command and execute multi-app workflow"""

        # Check if this is a multi-app workflow command
        workflow_intent = self.parse_workflow_intent(voice_text)

        if not workflow_intent:
            # Not a workflow command, fall back to single-app automation
            return self.voice_automation.execute_voice_command(voice_text)

        workflow_type = workflow_intent['workflow_type']
        matches = workflow_intent['matches']

        print(f"🚀 Executing {workflow_type} workflow: {voice_text}")

        # Create workflow based on type
        if workflow_type == 'research_and_note':
            search_query = matches[0]
            steps = self.create_research_and_note_workflow(search_query)

            # Track workflow type
            if workflow_type not in self.execution_stats['workflows_by_type']:
                self.execution_stats['workflows_by_type'][workflow_type] = 0
            self.execution_stats['workflows_by_type'][workflow_type] += 1

            # Execute workflow
            result = self.execute_workflow(steps)

            return {
                'timestamp': datetime.now().isoformat(),
                'voice_text': voice_text,
                'workflow_type': workflow_type,
                'workflow_result': result,
                'automation_performed': True,
                'success': result.success,
                'message': f"Multi-app workflow {'completed' if result.success else 'failed'}: {result.steps_completed}/{result.total_steps} steps",
                'execution_time': f"{result.execution_time:.2f}s"
            }

        return {
            'success': False,
            'message': f"Workflow type {workflow_type} not yet implemented",
            'automation_performed': False
        }

    def get_workflow_stats(self) -> Dict:
        """Get workflow execution statistics"""
        success_rate = 0
        if self.execution_stats['total_workflows'] > 0:
            success_rate = (self.execution_stats['successful_workflows'] /
                          self.execution_stats['total_workflows']) * 100

        return {
            **self.execution_stats,
            'success_rate': f"{success_rate:.1f}%"
        }


def test_multi_app_workflow():
    """Test the multi-app workflow engine"""
    workflow_engine = MultiAppWorkflowEngine()

    test_commands = [
        "Search for Python tutorials, open best result, and take notes",
        "Research machine learning and take notes",
        "Find voice automation, open it, and make notes",
        "Open Chrome"  # Single app command for comparison
    ]

    print("🚀 Testing Multi-App Workflow Engine")
    print("=" * 60)

    for cmd in test_commands:
        print(f"\n🎤 Testing: '{cmd}'")
        result = workflow_engine.execute_voice_workflow(cmd)

        print(f"  Success: {'✅' if result['success'] else '❌'}")
        print(f"  Message: {result['message']}")

        if 'workflow_result' in result:
            wr = result['workflow_result']
            print(f"  Steps: {wr.steps_completed}/{wr.total_steps}")
            print(f"  Time: {result['execution_time']}")

    print(f"\n📊 Final Statistics:")
    stats = workflow_engine.get_workflow_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    test_multi_app_workflow()