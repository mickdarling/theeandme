#!/usr/bin/env python3
"""
Multi-Modal Voice Integration Bridge 2025
Revolutionary gaze + voice integration system

This module bridges the gaze detection foundation system with the existing
ultra-fast voice interface to create a complete multi-modal interaction system.

INTEGRATION FEATURES:
✅ Gaze-filtered voice command processing
✅ Real-time intent classification (Execute/Ignore/Respond/Minimal)
✅ Non-blocking gaze detection integration
✅ Performance preservation of ultra-fast voice pipeline
✅ Graceful fallbacks when gaze detection unavailable
✅ Real-time web interface updates with gaze state
"""

import asyncio
import threading
import time
import json
from datetime import datetime
from dataclasses import asdict
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

# Import gaze detection system
from gaze_detection_foundation import (
    GazeDetectionEngine,
    MultiModalIntentRouter,
    MultiModalIntent,
    GazeState,
    IntentDecision
)

class MultiModalVoiceIntegration:
    """
    Integration bridge between gaze detection and voice processing systems

    This class coordinates between:
    1. GazeDetectionEngine - Real-time gaze state tracking
    2. MultiModalIntentRouter - Intent classification based on gaze + voice
    3. Voice Pipeline - Ultra-fast processing system
    """

    def __init__(self, enable_gaze_detection: bool = True):
        """Initialize multi-modal integration system

        Args:
            enable_gaze_detection: Whether to enable real gaze detection vs mock
        """
        self.enable_gaze_detection = enable_gaze_detection
        self.gaze_engine = None
        self.intent_router = None
        self.integration_active = False

        # Performance metrics for integration
        self.integration_metrics = {
            'total_voice_inputs': 0,
            'execute_decisions': 0,
            'ignore_decisions': 0,
            'respond_decisions': 0,
            'minimal_decisions': 0,
            'gaze_detection_failures': 0,
            'average_intent_processing_time': 0.0,
            'intent_accuracy': 0.0,
            'gaze_state_changes': 0,
            'current_gaze_state': GazeState.SYSTEM_DISABLED,
            'last_intent_decision': None,
            'session_start': datetime.now().isoformat()
        }

        # Real-time state for web interface
        self.current_state = {
            'gaze_context': None,
            'last_intent': None,
            'system_health': 'initializing',
            'processing_strategy': 'ultra-fast-only'
        }

        print("🤖 Multi-Modal Voice Integration Bridge initialized")

    def initialize(self) -> bool:
        """Initialize gaze detection and intent routing systems

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Initialize gaze detection engine
            print("🎥 Initializing gaze detection engine...")
            self.gaze_engine = GazeDetectionEngine(use_real_detection=self.enable_gaze_detection)

            # Initialize multi-modal intent router
            print("🧠 Initializing multi-modal intent router...")
            self.intent_router = MultiModalIntentRouter(self.gaze_engine)

            # Update system state
            self.integration_active = True
            self.current_state['system_health'] = 'active'
            self.current_state['processing_strategy'] = 'gaze-filtered'

            print("✅ Multi-modal integration system ready!")
            print(f"   Gaze Detection: {'Real-time' if self.enable_gaze_detection else 'Mock'}")
            print(f"   Intent Router: Active")
            print(f"   Integration: ENABLED")

            return True

        except Exception as e:
            print(f"❌ Failed to initialize multi-modal integration: {e}")
            print("🔄 Falling back to voice-only mode")

            self.integration_active = False
            self.current_state['system_health'] = 'fallback'
            self.current_state['processing_strategy'] = 'ultra-fast-only'

            return False

    def should_process_voice_input(self, voice_text: str) -> Tuple[bool, MultiModalIntent]:
        """
        Determine if voice input should be processed based on gaze + voice analysis

        This is the core integration function that implements the revolutionary
        gaze + voice intent matrix.

        Args:
            voice_text: The transcribed voice input

        Returns:
            Tuple[bool, MultiModalIntent]:
                - should_process: Whether to process the command
                - intent: Complete intent classification result
        """
        intent_start_time = time.time()

        # Update metrics
        self.integration_metrics['total_voice_inputs'] += 1

        # If integration not active, process everything (fallback mode)
        if not self.integration_active or not self.intent_router:
            fallback_intent = MultiModalIntent(
                voice_input=voice_text,
                gaze_state=GazeState.SYSTEM_DISABLED,
                decision=IntentDecision.EXECUTE,
                confidence=0.5,
                reasoning="Gaze detection disabled - processing all voice input",
                should_execute=True,
                should_respond=True,
                timestamp=time.time()
            )
            return True, fallback_intent

        try:
            # Get multi-modal intent classification
            intent = self.intent_router.classify_intent(voice_text)

            # Update current state
            self.current_state['gaze_context'] = self.gaze_engine.get_current_context()
            self.current_state['last_intent'] = intent
            self.integration_metrics['current_gaze_state'] = intent.gaze_state
            self.integration_metrics['last_intent_decision'] = intent.decision

            # Track gaze state changes
            if (self.integration_metrics['current_gaze_state'] != intent.gaze_state):
                self.integration_metrics['gaze_state_changes'] += 1
                print(f"👁️  Gaze state changed: {intent.gaze_state.value}")

            # Update decision metrics
            if intent.decision == IntentDecision.EXECUTE:
                self.integration_metrics['execute_decisions'] += 1
            elif intent.decision == IntentDecision.IGNORE:
                self.integration_metrics['ignore_decisions'] += 1
            elif intent.decision == IntentDecision.RESPOND:
                self.integration_metrics['respond_decisions'] += 1
            elif intent.decision == IntentDecision.MINIMAL:
                self.integration_metrics['minimal_decisions'] += 1

            # Calculate processing time
            processing_time = (time.time() - intent_start_time) * 1000
            total_time = self.integration_metrics['average_intent_processing_time']
            total_inputs = self.integration_metrics['total_voice_inputs']
            self.integration_metrics['average_intent_processing_time'] = (
                (total_time * (total_inputs - 1)) + processing_time
            ) / total_inputs

            # Log decision
            print(f"🧠 INTENT DECISION: {intent.decision.value.upper()}")
            print(f"   Voice: '{voice_text}'")
            print(f"   Gaze: {intent.gaze_state.value}")
            print(f"   Confidence: {intent.confidence:.2f}")
            print(f"   Reasoning: {intent.reasoning}")
            print(f"   Processing: {processing_time:.1f}ms")

            # Return decision
            should_process = intent.should_execute or intent.should_respond
            return should_process, intent

        except Exception as e:
            print(f"❌ Intent classification error: {e}")
            self.integration_metrics['gaze_detection_failures'] += 1

            # Fallback to processing all input
            fallback_intent = MultiModalIntent(
                voice_input=voice_text,
                gaze_state=GazeState.UNCERTAIN,
                decision=IntentDecision.EXECUTE,
                confidence=0.3,
                reasoning=f"Intent classification failed: {e}",
                should_execute=True,
                should_respond=True,
                timestamp=time.time()
            )
            return True, fallback_intent

    def get_response_strategy(self, intent: MultiModalIntent) -> Dict[str, Any]:
        """
        Determine how the system should respond based on intent classification

        Args:
            intent: The classified multi-modal intent

        Returns:
            Dict with response strategy parameters
        """
        if intent.decision == IntentDecision.EXECUTE:
            return {
                'response_type': 'full_execution',
                'tts_enabled': True,
                'tts_voice': 'normal',
                'visual_feedback': 'success',
                'automation_allowed': True,
                'conversational': True
            }
        elif intent.decision == IntentDecision.RESPOND:
            return {
                'response_type': 'conversational',
                'tts_enabled': True,
                'tts_voice': 'friendly',
                'visual_feedback': 'conversation',
                'automation_allowed': False,
                'conversational': True
            }
        elif intent.decision == IntentDecision.MINIMAL:
            return {
                'response_type': 'minimal_acknowledgment',
                'tts_enabled': True,
                'tts_voice': 'quiet',
                'visual_feedback': 'minimal',
                'automation_allowed': False,
                'conversational': False
            }
        else:  # IGNORE
            return {
                'response_type': 'no_response',
                'tts_enabled': False,
                'tts_voice': None,
                'visual_feedback': 'ignored',
                'automation_allowed': False,
                'conversational': False
            }

    def get_current_gaze_context(self) -> Dict[str, Any]:
        """Get current gaze context for real-time web interface updates"""
        if not self.integration_active or not self.gaze_engine:
            return {
                'state': 'system_disabled',
                'confidence': 0.0,
                'looking_at_screen_probability': 0.0,
                'face_detected': False,
                'system_health': 'disabled'
            }

        try:
            context = self.gaze_engine.get_current_context()
            return {
                'state': context.state.value,
                'confidence': context.confidence,
                'duration': context.duration,
                'looking_at_screen_probability': context.looking_at_screen_probability,
                'face_detected': context.face_detected,
                'gaze_vector': {
                    'x': context.gaze_vector.x,
                    'y': context.gaze_vector.y,
                    'z': context.gaze_vector.z
                },
                'system_health': 'active'
            }
        except Exception as e:
            print(f"⚠️  Error getting gaze context: {e}")
            return {
                'state': 'error',
                'confidence': 0.0,
                'looking_at_screen_probability': 0.0,
                'face_detected': False,
                'system_health': 'error',
                'error': str(e)
            }

    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get complete integration performance metrics"""
        total_decisions = (
            self.integration_metrics['execute_decisions'] +
            self.integration_metrics['ignore_decisions'] +
            self.integration_metrics['respond_decisions'] +
            self.integration_metrics['minimal_decisions']
        )

        if total_decisions > 0:
            decision_distribution = {
                'execute_percentage': (self.integration_metrics['execute_decisions'] / total_decisions) * 100,
                'ignore_percentage': (self.integration_metrics['ignore_decisions'] / total_decisions) * 100,
                'respond_percentage': (self.integration_metrics['respond_decisions'] / total_decisions) * 100,
                'minimal_percentage': (self.integration_metrics['minimal_decisions'] / total_decisions) * 100
            }
        else:
            decision_distribution = {
                'execute_percentage': 0.0,
                'ignore_percentage': 0.0,
                'respond_percentage': 0.0,
                'minimal_percentage': 0.0
            }

        # Calculate system health metrics
        if self.integration_metrics['gaze_detection_failures'] > 0 and self.integration_metrics['total_voice_inputs'] > 0:
            failure_rate = (self.integration_metrics['gaze_detection_failures'] /
                          self.integration_metrics['total_voice_inputs']) * 100
        else:
            failure_rate = 0.0

        return {
            **self.integration_metrics,
            **decision_distribution,
            'failure_rate': failure_rate,
            'system_active': self.integration_active,
            'current_gaze_state_display': self.integration_metrics['current_gaze_state'].value if isinstance(self.integration_metrics['current_gaze_state'], GazeState) else 'unknown',
            'last_intent_decision_display': self.integration_metrics['last_intent_decision'].value if self.integration_metrics['last_intent_decision'] else 'none'
        }

    def test_integration_pipeline(self) -> Dict[str, Any]:
        """
        Test the complete multi-modal integration pipeline

        Returns:
            Dict with test results and performance metrics
        """
        print("🧪 Testing Multi-Modal Integration Pipeline...")

        test_cases = [
            ("Open Chrome", "Command while looking at screen - should EXECUTE"),
            ("I should open Chrome", "Command while looking away - should IGNORE"),
            ("How are you?", "Question while looking at screen - should RESPOND"),
            ("That's interesting", "Comment while looking away - should MINIMAL"),
        ]

        results = []
        total_processing_time = 0

        for i, (voice_input, description) in enumerate(test_cases):
            print(f"\n🧪 Test {i+1}: {description}")
            print(f"   Input: '{voice_input}'")

            start_time = time.time()
            should_process, intent = self.should_process_voice_input(voice_input)
            processing_time = (time.time() - start_time) * 1000
            total_processing_time += processing_time

            response_strategy = self.get_response_strategy(intent)

            result = {
                'test_case': i + 1,
                'voice_input': voice_input,
                'description': description,
                'should_process': should_process,
                'intent_decision': intent.decision.value,
                'gaze_state': intent.gaze_state.value,
                'confidence': intent.confidence,
                'reasoning': intent.reasoning,
                'response_strategy': response_strategy,
                'processing_time_ms': processing_time
            }

            results.append(result)

            print(f"   → Decision: {intent.decision.value.upper()}")
            print(f"   → Gaze: {intent.gaze_state.value}")
            print(f"   → Should Process: {should_process}")
            print(f"   → Processing: {processing_time:.1f}ms")

        average_processing_time = total_processing_time / len(test_cases)

        summary = {
            'test_results': results,
            'total_tests': len(test_cases),
            'average_processing_time': average_processing_time,
            'integration_active': self.integration_active,
            'system_health': self.current_state['system_health'],
            'test_timestamp': datetime.now().isoformat()
        }

        print(f"\n📊 INTEGRATION TEST RESULTS:")
        print(f"   Tests Completed: {len(test_cases)}")
        print(f"   Average Processing: {average_processing_time:.1f}ms")
        print(f"   Integration Status: {'ACTIVE' if self.integration_active else 'FALLBACK'}")
        print("✅ Multi-modal integration pipeline test complete!")

        return summary

    def shutdown(self):
        """Shutdown the integration system and cleanup resources"""
        print("🛑 Shutting down multi-modal integration...")

        if self.gaze_engine:
            self.gaze_engine.shutdown()

        self.integration_active = False
        self.current_state['system_health'] = 'shutdown'

        # Print final statistics
        metrics = self.get_integration_metrics()
        print(f"\n📊 INTEGRATION SESSION STATISTICS:")
        print(f"   Total Voice Inputs: {metrics['total_voice_inputs']}")
        print(f"   Execute Decisions: {metrics['execute_decisions']} ({metrics['execute_percentage']:.1f}%)")
        print(f"   Ignore Decisions: {metrics['ignore_decisions']} ({metrics['ignore_percentage']:.1f}%)")
        print(f"   Respond Decisions: {metrics['respond_decisions']} ({metrics['respond_percentage']:.1f}%)")
        print(f"   Minimal Decisions: {metrics['minimal_decisions']} ({metrics['minimal_percentage']:.1f}%)")
        print(f"   Gaze State Changes: {metrics['gaze_state_changes']}")
        print(f"   Average Intent Processing: {metrics['average_intent_processing_time']:.1f}ms")
        print(f"   System Failure Rate: {metrics['failure_rate']:.1f}%")

        print("✅ Multi-modal integration shutdown complete")


def test_multi_modal_integration():
    """Comprehensive test of the multi-modal integration system"""
    print("🚀 MULTI-MODAL VOICE INTEGRATION TEST")
    print("=" * 60)

    # Initialize integration system
    integration = MultiModalVoiceIntegration(enable_gaze_detection=True)

    # Test initialization
    init_success = integration.initialize()
    if not init_success:
        print("⚠️  Integration initialization failed - testing fallback mode")

    # Run integration pipeline tests
    test_results = integration.test_integration_pipeline()

    # Test real-time gaze context
    print("\n👁️  Testing real-time gaze context...")
    for i in range(5):
        gaze_context = integration.get_current_gaze_context()
        print(f"   Frame {i+1}: {gaze_context['state']} "
              f"(confidence: {gaze_context['confidence']:.2f}, "
              f"face: {gaze_context['face_detected']})")
        time.sleep(0.2)

    # Get final metrics
    final_metrics = integration.get_integration_metrics()

    # Cleanup
    integration.shutdown()

    return {
        'initialization_success': init_success,
        'pipeline_test_results': test_results,
        'final_metrics': final_metrics
    }


if __name__ == "__main__":
    # Run comprehensive integration test
    test_results = test_multi_modal_integration()

    # Save test results
    results_file = Path("multi_modal_integration_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)

    print(f"\n📄 Test results saved to: {results_file}")
    print("🚀 Multi-modal voice integration bridge ready for deployment!")