#!/usr/bin/env python3
"""
Simple Effective Echo Blocker - Back to Basics
Your suggestion: If it's close in time + close in content = AI echo, block it.

This approach is much simpler and more effective than the complex NLMS system.
"""

import time
from datetime import datetime
from typing import Optional
import re

class SimpleEchoBlocker:
    """Simple but effective echo blocking using time + content correlation"""

    def __init__(self):
        self.last_ai_response: str = ""
        self.ai_response_time: float = 0
        self.ai_speaking_start: float = 0
        self.ai_speaking_duration: float = 0

        # Improved thresholds based on testing
        self.time_window = 5.0  # 5 seconds after AI stops speaking
        self.word_overlap_threshold = 0.25  # 25% word overlap (lowered for better detection)
        self.char_similarity_threshold = 0.35  # 35% character similarity (lowered)

        # Mistranslation tolerance - if words are too short/simple, be more aggressive
        self.simple_words = {'yes', 'no', 'ok', 'what', 'sure', 'good', 'bad', 'class', 'ready', 'bye', 'hi', 'hello', 'thanks', 'sorry'}
        self.mistranslation_phrases = []  # Track common mistranslations

    def set_ai_response(self, text: str, speaking_duration: float = 2.0):
        """Record AI response and timing"""
        self.last_ai_response = text.strip()
        self.ai_response_time = time.time()
        self.ai_speaking_duration = speaking_duration

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Convert to lowercase, remove punctuation, extra spaces
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

        # Simple character overlap
        chars1 = set(norm1.replace(' ', ''))
        chars2 = set(norm2.replace(' ', ''))

        if not chars1 or not chars2:
            return 0.0

        intersection = len(chars1.intersection(chars2))
        union = len(chars1.union(chars2))

        return intersection / union if union > 0 else 0.0

    def is_likely_echo(self, transcribed_text: str) -> tuple[bool, str]:
        """
        Improved echo detection with mistranslation tolerance
        Returns: (is_echo, reason)
        """
        if not transcribed_text.strip() or not self.last_ai_response:
            return False, "no_data"

        current_time = time.time()
        time_since_ai = current_time - self.ai_response_time

        # Check if we're in the danger zone (AI just spoke)
        if time_since_ai > self.time_window:
            return False, "time_window_passed"

        # Calculate similarities
        word_overlap = self.calculate_word_overlap(transcribed_text, self.last_ai_response)
        char_similarity = self.calculate_char_similarity(transcribed_text, self.last_ai_response)

        # Simple decision logic
        reasons = []

        # Word overlap detection (lowered threshold)
        if word_overlap > self.word_overlap_threshold:
            reasons.append(f"word_overlap_{word_overlap:.2f}")

        # Character similarity detection (lowered threshold)
        if char_similarity > self.char_similarity_threshold:
            reasons.append(f"char_similarity_{char_similarity:.2f}")

        # Substring detection
        norm_transcribed = self.normalize_text(transcribed_text)
        norm_ai = self.normalize_text(self.last_ai_response)

        if len(norm_transcribed) > 3 and len(norm_ai) > 3:  # Lowered from 5
            if norm_transcribed in norm_ai or norm_ai in norm_transcribed:
                reasons.append("substring_match")

        # Very close timing (AI just finished speaking)
        if time_since_ai < 3.0:  # Extended window
            reasons.append(f"recent_ai_{time_since_ai:.1f}s")

        # IMPROVED: Simple word echo detection (for mistranslation tolerance)
        transcribed_words = set(self.normalize_text(transcribed_text).split())
        ai_words = set(self.normalize_text(self.last_ai_response).split())

        # If AI used simple words and we get simple words back, be more aggressive
        ai_simple = ai_words.intersection(self.simple_words)
        transcribed_simple = transcribed_words.intersection(self.simple_words)

        if ai_simple and time_since_ai < 3.0:
            reasons.append(f"simple_word_timing")

        # Length-based echo detection (very short responses are prone to mistranslation)
        if len(self.last_ai_response.split()) <= 2 and time_since_ai < 2.5:
            reasons.append(f"short_response_timing")

        # Enhanced decision logic - more aggressive for recent short responses
        is_echo = (
            len(reasons) >= 2 or  # Multiple factors
            word_overlap > 0.6 or  # High word overlap
            char_similarity > 0.7 or  # High character similarity
            (time_since_ai < 1.5 and (word_overlap > 0.15 or char_similarity > 0.25)) or  # Recent + any similarity
            (time_since_ai < 2.0 and len(self.last_ai_response.split()) <= 2)  # Recent short AI response
        )

        reason = f"[{', '.join(reasons)}]" if reasons else "no_match"

        return is_echo, reason

    def get_stats(self) -> dict:
        """Get current state for debugging"""
        current_time = time.time()
        return {
            "last_ai_response": self.last_ai_response[:50] + "..." if len(self.last_ai_response) > 50 else self.last_ai_response,
            "time_since_ai": current_time - self.ai_response_time if self.ai_response_time > 0 else -1,
            "in_danger_zone": (current_time - self.ai_response_time) < self.time_window if self.ai_response_time > 0 else False
        }

# Test the blocker
if __name__ == "__main__":
    print("🧪 Testing Simple Effective Echo Blocker")

    blocker = SimpleEchoBlocker()

    # Simulate AI response
    blocker.set_ai_response("I am functioning well, thank you for asking!")

    # Test cases
    test_cases = [
        "I am functioning well",  # Should be blocked - direct match
        "Hello, how are you?",    # Should pass - different content
        "Thank you for asking",   # Should be blocked - substring
        "What's the weather?",    # Should pass - different content
        "I am function",          # Should be blocked - high similarity
        "Yes, I understand",      # Should pass - different content
    ]

    print("\nTest Results:")
    for i, test_text in enumerate(test_cases):
        is_echo, reason = blocker.is_likely_echo(test_text)
        status = "🔇 BLOCKED" if is_echo else "✅ PASSED"
        print(f"{i+1}. {status}: '{test_text}' - {reason}")

    print(f"\nCurrent state: {blocker.get_stats()}")