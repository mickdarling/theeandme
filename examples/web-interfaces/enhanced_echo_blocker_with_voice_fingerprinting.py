#!/usr/bin/env python3
"""
Enhanced Echo Blocker with Voice Fingerprinting - Triple Detection System
Combines:
1. Time correlation (when did AI speak?)
2. Content correlation (what did AI say?)
3. Voice fingerprinting (is this AI synthetic voice?)

This solves the core problem from session notes: AI voice being transcribed as user input.
"""

import time
import os
from datetime import datetime
from typing import Optional, Tuple
import re
from pathlib import Path

# Import our calibrated voice spectral analyzer
from voice_spectral_analyzer import VoiceSpectralAnalyzer

class EnhancedEchoBlocker:
    """Triple-layer echo blocking: Time + Content + Voice Fingerprinting"""

    def __init__(self, enable_voice_fingerprinting: bool = True):
        # Time + Content layers (existing)
        self.last_ai_response: str = ""
        self.ai_response_time: float = 0
        self.ai_speaking_start: float = 0
        self.ai_speaking_duration: float = 0

        # Time + Content thresholds
        self.time_window = 5.0  # 5 seconds after AI stops speaking
        self.word_overlap_threshold = 0.25  # 25% word overlap
        self.char_similarity_threshold = 0.35  # 35% character similarity

        # Voice Fingerprinting layer (NEW)
        self.enable_voice_fingerprinting = enable_voice_fingerprinting
        if self.enable_voice_fingerprinting:
            self.voice_analyzer = VoiceSpectralAnalyzer()
        else:
            self.voice_analyzer = None

        # Detection statistics
        self.stats = {
            'total_checks': 0,
            'blocked_time_content': 0,
            'blocked_voice_fingerprint': 0,
            'blocked_combined': 0,
            'passed_all_layers': 0
        }

        # Simple words for enhanced detection
        self.simple_words = {'yes', 'no', 'ok', 'what', 'sure', 'good', 'bad', 'class', 'ready', 'bye', 'hi', 'hello', 'thanks', 'sorry'}

    def set_ai_response(self, text: str, speaking_duration: float = 2.0):
        """Record AI response and timing"""
        self.last_ai_response = text.strip()
        self.ai_response_time = time.time()
        self.ai_speaking_duration = speaking_duration

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text

    def calculate_word_overlap(self, text1: str, text2: str) -> float:
        """Calculate word overlap ratio between two texts"""
        words1 = set(self.normalize_text(text1).split())
        words2 = set(self.normalize_text(text2).split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        return intersection / union if union > 0 else 0.0

    def calculate_char_similarity(self, text1: str, text2: str) -> float:
        """Calculate character-level similarity"""
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)

        if not norm1 or not norm2:
            return 0.0

        chars1 = set(norm1.replace(' ', ''))
        chars2 = set(norm2.replace(' ', ''))

        if not chars1 or not chars2:
            return 0.0

        intersection = len(chars1.intersection(chars2))
        union = len(chars1.union(chars2))
        return intersection / union if union > 0 else 0.0

    def check_time_content_correlation(self, transcribed_text: str) -> Tuple[bool, str, dict]:
        """Layer 1 & 2: Time and Content Correlation (existing logic)"""
        if not transcribed_text.strip() or not self.last_ai_response:
            return False, "no_data", {}

        current_time = time.time()
        time_since_ai = current_time - self.ai_response_time

        # Time window check
        if time_since_ai > self.time_window:
            return False, "time_window_passed", {"time_since_ai": time_since_ai}

        # Calculate similarities
        word_overlap = self.calculate_word_overlap(transcribed_text, self.last_ai_response)
        char_similarity = self.calculate_char_similarity(transcribed_text, self.last_ai_response)

        reasons = []

        # Word overlap detection
        if word_overlap > self.word_overlap_threshold:
            reasons.append(f"word_overlap_{word_overlap:.2f}")

        # Character similarity detection
        if char_similarity > self.char_similarity_threshold:
            reasons.append(f"char_similarity_{char_similarity:.2f}")

        # Substring detection
        norm_transcribed = self.normalize_text(transcribed_text)
        norm_ai = self.normalize_text(self.last_ai_response)

        if len(norm_transcribed) > 3 and len(norm_ai) > 3:
            if norm_transcribed in norm_ai or norm_ai in norm_transcribed:
                reasons.append("substring_match")

        # Recent timing
        if time_since_ai < 3.0:
            reasons.append(f"recent_ai_{time_since_ai:.1f}s")

        # Simple word detection
        transcribed_words = set(self.normalize_text(transcribed_text).split())
        ai_words = set(self.normalize_text(self.last_ai_response).split())
        ai_simple = ai_words.intersection(self.simple_words)

        if ai_simple and time_since_ai < 3.0:
            reasons.append("simple_word_timing")

        # Short response timing
        if len(self.last_ai_response.split()) <= 2 and time_since_ai < 2.5:
            reasons.append("short_response_timing")

        # Decision logic
        is_echo = (
            len(reasons) >= 2 or
            word_overlap > 0.6 or
            char_similarity > 0.7 or
            (time_since_ai < 1.5 and (word_overlap > 0.15 or char_similarity > 0.25)) or
            (time_since_ai < 2.0 and len(self.last_ai_response.split()) <= 2)
        )

        detection_data = {
            "time_since_ai": time_since_ai,
            "word_overlap": word_overlap,
            "char_similarity": char_similarity,
            "reasons": reasons
        }

        reason = f"time_content[{', '.join(reasons)}]" if reasons else "no_time_content_match"
        return is_echo, reason, detection_data

    def check_voice_fingerprinting(self, audio_file_path: str) -> Tuple[bool, str, dict]:
        """Layer 3: Voice Fingerprinting - NEW BREAKTHROUGH FEATURE"""
        if not self.enable_voice_fingerprinting or not self.voice_analyzer:
            return False, "voice_fingerprinting_disabled", {}

        if not audio_file_path or not Path(audio_file_path).exists():
            return False, "no_audio_file", {"audio_path": audio_file_path}

        try:
            # Analyze the audio for AI vs Human voice characteristics
            analysis = self.voice_analyzer.analyze_audio_file(audio_file_path)

            if "error" in analysis:
                return False, f"voice_analysis_error: {analysis['error']}", {"error": analysis["error"]}

            voice_type = analysis.get("voice_type", "UNCERTAIN")
            ai_confidence = analysis.get("ai_confidence", 0.0)
            human_confidence = analysis.get("human_confidence", 0.0)
            ai_indicators = analysis.get("ai_indicators", [])

            # If voice analyzer detects AI synthetic voice, it's likely an echo
            is_ai_voice = (voice_type == "AI_SYNTHETIC" and ai_confidence > 0.6)

            detection_data = {
                "voice_type": voice_type,
                "ai_confidence": ai_confidence,
                "human_confidence": human_confidence,
                "ai_indicators": ai_indicators,
                "audio_path": audio_file_path
            }

            reason = f"voice_fingerprint[{voice_type}_confidence_{ai_confidence:.1%}]"

            return is_ai_voice, reason, detection_data

        except Exception as e:
            return False, f"voice_fingerprinting_error: {str(e)}", {"error": str(e)}

    def is_likely_echo(self, transcribed_text: str, audio_file_path: str = None) -> Tuple[bool, str, dict]:
        """
        TRIPLE-LAYER Echo Detection:
        1. Time correlation (when did AI speak?)
        2. Content correlation (what did AI say?)
        3. Voice fingerprinting (is this AI synthetic voice?)

        Returns: (is_echo, reason, detection_data)
        """
        self.stats['total_checks'] += 1

        all_detection_data = {
            "timestamp": datetime.now().isoformat(),
            "transcribed_text": transcribed_text[:100] + "..." if len(transcribed_text) > 100 else transcribed_text,
            "audio_file": audio_file_path
        }

        # Layer 1 & 2: Time + Content Correlation
        time_content_echo, time_content_reason, time_content_data = self.check_time_content_correlation(transcribed_text)
        all_detection_data["time_content"] = time_content_data

        # Layer 3: Voice Fingerprinting
        voice_echo, voice_reason, voice_data = self.check_voice_fingerprinting(audio_file_path)
        all_detection_data["voice_fingerprinting"] = voice_data

        # Decision Logic: ANY layer can trigger echo detection
        is_echo = False
        reasons = []

        if time_content_echo:
            is_echo = True
            reasons.append(time_content_reason)
            self.stats['blocked_time_content'] += 1

        if voice_echo:
            is_echo = True
            reasons.append(voice_reason)
            self.stats['blocked_voice_fingerprint'] += 1

        # If both detected, it's very likely an echo
        if time_content_echo and voice_echo:
            self.stats['blocked_combined'] += 1

        if not is_echo:
            self.stats['passed_all_layers'] += 1

        final_reason = " + ".join(reasons) if reasons else "passed_all_layers"
        all_detection_data["final_decision"] = {
            "is_echo": is_echo,
            "reason": final_reason,
            "detection_layers": {
                "time_content": time_content_echo,
                "voice_fingerprinting": voice_echo
            }
        }

        return is_echo, final_reason, all_detection_data

    def get_stats(self) -> dict:
        """Get detection statistics and current state"""
        current_time = time.time()

        stats = {
            "detection_stats": self.stats.copy(),
            "current_state": {
                "last_ai_response": self.last_ai_response[:50] + "..." if len(self.last_ai_response) > 50 else self.last_ai_response,
                "time_since_ai": current_time - self.ai_response_time if self.ai_response_time > 0 else -1,
                "in_danger_zone": (current_time - self.ai_response_time) < self.time_window if self.ai_response_time > 0 else False,
                "voice_fingerprinting_enabled": self.enable_voice_fingerprinting
            }
        }

        # Calculate success rates
        total = self.stats['total_checks']
        if total > 0:
            stats["detection_rates"] = {
                "time_content_blocks": f"{(self.stats['blocked_time_content'] / total) * 100:.1f}%",
                "voice_fingerprint_blocks": f"{(self.stats['blocked_voice_fingerprint'] / total) * 100:.1f}%",
                "combined_blocks": f"{(self.stats['blocked_combined'] / total) * 100:.1f}%",
                "pass_rate": f"{(self.stats['passed_all_layers'] / total) * 100:.1f}%"
            }

        return stats

# Test the enhanced blocker
if __name__ == "__main__":
    print("🚀 Testing Enhanced Echo Blocker with Voice Fingerprinting")

    blocker = EnhancedEchoBlocker(enable_voice_fingerprinting=True)

    # Simulate AI response
    blocker.set_ai_response("I am ready to assist you today.")

    print(f"\nAI Response Set: '{blocker.last_ai_response}'")
    print(f"Testing with voice fingerprinting: {blocker.enable_voice_fingerprinting}")

    # Test cases without audio (time+content only)
    text_test_cases = [
        "I am ready to assist you",  # Should be blocked - high similarity
        "Hello, how can I help?",    # Should pass - different content
        "Ready to assist",           # Should be blocked - substring
        "What's the weather today?", # Should pass - completely different
        "I am ready",                # Should be blocked - partial match
    ]

    print("\n📝 Text-Only Tests (Time + Content Layers):")
    for i, test_text in enumerate(text_test_cases):
        is_echo, reason, data = blocker.is_likely_echo(test_text)
        status = "🔇 BLOCKED" if is_echo else "✅ PASSED"
        print(f"{i+1}. {status}: '{test_text}' - {reason}")

    # Test with actual audio file (if available)
    test_audio_path = "/Users/mick/Developer/theeandme/audio_diagnostics/session_20250913_101946/ai_voice_102113.wav"
    if Path(test_audio_path).exists():
        print(f"\n🎤 Voice Fingerprinting Test:")
        print(f"Audio file: {Path(test_audio_path).name}")

        is_echo, reason, data = blocker.is_likely_echo("I am ready to assist you today", test_audio_path)
        status = "🔇 BLOCKED" if is_echo else "✅ PASSED"
        print(f"Result: {status} - {reason}")

        voice_data = data.get("voice_fingerprinting", {})
        if voice_data:
            print(f"Voice Type: {voice_data.get('voice_type', 'Unknown')}")
            print(f"AI Confidence: {voice_data.get('ai_confidence', 0):.1%}")
            print(f"AI Indicators: {', '.join(voice_data.get('ai_indicators', []))}")
    else:
        print(f"\n❌ Audio file not found for voice fingerprinting test: {test_audio_path}")

    print(f"\n📊 Detection Statistics:")
    stats = blocker.get_stats()
    for key, value in stats.get("detection_rates", {}).items():
        print(f"  {key}: {value}")

    print("\n✅ Enhanced Echo Blocker test complete!")