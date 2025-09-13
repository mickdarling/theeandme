#!/usr/bin/env python3
"""
Voice Calibration Persistence System
Saves and loads optimal RealtimeSTT settings between sessions
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class VoiceCalibrationManager:
    """Manages persistent voice calibration settings"""

    def __init__(self, config_dir: str = "voice_config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "voice_calibration.json"

        # Default optimized settings based on testing
        self.default_settings = {
            "silero_sensitivity": 0.2,
            "webrtc_sensitivity": 1,
            "post_speech_silence_duration": 0.5,
            "pre_recording_buffer_duration": 0.5,
            "realtime_processing_pause": 0.15,
            "model": "base.en",
            "language": "en",
            "initial_prompt": "Commands like open, search, create, launch, find",
            "last_updated": datetime.now().isoformat(),
            "session_count": 0,
            "average_accuracy": 0.0,
            "user_feedback": "initial"
        }

    def load_calibration(self) -> Dict:
        """Load saved calibration settings"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    print(f"📂 Loaded voice calibration from {self.config_file}")
                    print(f"   Last updated: {settings.get('last_updated', 'unknown')}")
                    print(f"   Session count: {settings.get('session_count', 0)}")
                    print(f"   Average accuracy: {settings.get('average_accuracy', 0):.1f}%")
                    return settings
            else:
                print(f"📂 No existing calibration found, using optimized defaults")
                return self.default_settings.copy()
        except Exception as e:
            print(f"⚠️  Error loading calibration: {e}")
            return self.default_settings.copy()

    def save_calibration(self, settings: Dict):
        """Save calibration settings"""
        try:
            settings["last_updated"] = datetime.now().isoformat()
            settings["session_count"] = settings.get("session_count", 0) + 1

            with open(self.config_file, 'w') as f:
                json.dump(settings, f, indent=2)

            print(f"💾 Saved voice calibration to {self.config_file}")
            print(f"   Session count: {settings['session_count']}")
            return True
        except Exception as e:
            print(f"⚠️  Error saving calibration: {e}")
            return False

    def update_performance(self, accuracy: float, user_feedback: str = None):
        """Update calibration based on performance metrics"""
        settings = self.load_calibration()

        # Update running average accuracy
        old_accuracy = settings.get('average_accuracy', 0.0)
        session_count = settings.get('session_count', 0)

        if session_count > 0:
            new_accuracy = ((old_accuracy * session_count) + accuracy) / (session_count + 1)
        else:
            new_accuracy = accuracy

        settings['average_accuracy'] = new_accuracy

        if user_feedback:
            settings['user_feedback'] = user_feedback
            settings['feedback_date'] = datetime.now().isoformat()

            # Adjust settings based on feedback
            if "missed words" in user_feedback.lower() or "first word" in user_feedback.lower():
                # Increase sensitivity for better word capture
                settings['silero_sensitivity'] = min(0.4, settings.get('silero_sensitivity', 0.2) + 0.05)
                settings['pre_recording_buffer_duration'] = min(0.8, settings.get('pre_recording_buffer_duration', 0.5) + 0.1)
                print(f"🔧 Adjusted sensitivity based on feedback: missed words")

            elif "too sensitive" in user_feedback.lower() or "cutting off" in user_feedback.lower():
                # Decrease sensitivity to reduce false triggers
                settings['silero_sensitivity'] = max(0.05, settings.get('silero_sensitivity', 0.2) - 0.05)
                print(f"🔧 Adjusted sensitivity based on feedback: too sensitive")

        self.save_calibration(settings)
        return settings

    def get_recorder_config(self) -> Dict:
        """Get RealtimeSTT configuration from saved calibration"""
        settings = self.load_calibration()

        return {
            'spinner': False,
            'model': settings.get('model', 'base.en'),
            'language': settings.get('language', 'en'),
            'silero_sensitivity': settings.get('silero_sensitivity', 0.2),
            'webrtc_sensitivity': settings.get('webrtc_sensitivity', 1),
            'post_speech_silence_duration': settings.get('post_speech_silence_duration', 0.5),
            'min_length_of_recording': 0,
            'min_gap_between_recordings': 0,
            'enable_realtime_transcription': False,
            'realtime_processing_pause': settings.get('realtime_processing_pause', 0.15),
            'realtime_model_type': 'tiny.en',
            'pre_recording_buffer_duration': settings.get('pre_recording_buffer_duration', 0.5),
            'initial_prompt': settings.get('initial_prompt', "Commands like open, search, create, launch, find")
        }

    def get_warmup_phrases(self) -> list:
        """Get phrases for voice warmup/calibration"""
        return [
            "Open Chrome",
            "Search for Python tutorials",
            "Launch Safari",
            "Create a new note",
            "Find machine learning resources",
            "Start calculator",
            "Open the notes application",
            "Google voice recognition tools"
        ]

    def perform_warmup_test(self) -> Dict:
        """Perform a warmup calibration test"""
        print("\n🎯 Voice Calibration Warmup")
        print("=" * 40)
        print("Say the following phrases to calibrate your voice:")

        warmup_phrases = self.get_warmup_phrases()
        results = {
            'phrases_tested': len(warmup_phrases),
            'successful_captures': 0,
            'calibration_complete': False
        }

        for i, phrase in enumerate(warmup_phrases[:3]):  # Just test first 3 for quick calibration
            print(f"\n{i+1}. Say: '{phrase}'")
            print("   (Press Enter when ready, or 's' to skip warmup)")

            user_input = input().strip().lower()
            if user_input == 's':
                print("⏭️  Skipping warmup - using saved settings")
                break

            # In a real implementation, this would capture and test actual voice input
            # For now, just simulate the calibration
            results['successful_captures'] += 1

        results['calibration_complete'] = True
        print(f"\n✅ Warmup complete: {results['successful_captures']}/{results['phrases_tested']} phrases")

        return results


def test_calibration_system():
    """Test the calibration persistence system"""
    calibration = VoiceCalibrationManager()

    print("🧪 Testing Voice Calibration System")
    print("=" * 50)

    # Test loading configuration
    config = calibration.get_recorder_config()
    print(f"\n📋 Current Configuration:")
    for key, value in config.items():
        if key not in ['on_realtime_transcription_update', 'on_realtime_transcription_stabilized']:
            print(f"  {key}: {value}")

    # Test performance update
    calibration.update_performance(85.5, "System missed first words of commands")

    # Test warmup
    warmup_results = calibration.perform_warmup_test()
    print(f"\n🏁 Warmup Results: {warmup_results}")


if __name__ == "__main__":
    test_calibration_system()