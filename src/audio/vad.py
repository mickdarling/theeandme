"""
Voice Activity Detection (VAD) using Silero VAD.

This module provides real-time voice activity detection using the Silero VAD model,
which uses neural networks for superior accuracy compared to traditional VAD methods.
"""

import torch
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import time


logger = logging.getLogger(__name__)


class VADState(Enum):
    """Voice activity states."""
    SILENCE = "silence"
    VOICE = "voice"
    UNCERTAIN = "uncertain"


@dataclass
class VADResult:
    """Result from voice activity detection."""
    has_voice: bool
    confidence: float
    state: VADState
    timestamp: float
    speech_segments: List[Tuple[float, float]] = None  # (start, end) in seconds


class SileroVAD:
    """
    Silero VAD implementation for real-time voice activity detection.
    
    Uses the Silero VAD neural network model for accurate speech detection
    with configurable sensitivity and temporal smoothing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Silero VAD."""
        self.config = config
        self.sample_rate = config.get('sample_rate', 16000)
        self.threshold = config.get('vad_threshold', 0.7)
        self.min_speech_duration_ms = config.get('min_speech_duration_ms', 300)
        self.silence_timeout_seconds = config.get('silence_timeout_seconds', 2.0)
        
        # Model and utilities
        self.model = None
        self.utils = None
        self.get_speech_timestamps = None
        
        # State tracking
        self.last_voice_time = 0
        self.current_state = VADState.SILENCE
        self.voice_buffer = []  # Recent voice activity history
        self.is_initialized = False
        
        logger.info(f"Initializing Silero VAD with threshold={self.threshold}")
        
    async def initialize(self):
        """Initialize the VAD model (async to avoid blocking)."""
        try:
            logger.info("Loading Silero VAD model...")
            
            # Load Silero VAD model
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False  # Use PyTorch version for better performance on Apple Silicon
            )
            
            # Extract utility functions
            (self.get_speech_timestamps, 
             self.save_audio, 
             self.read_audio, 
             self.VADIterator, 
             self.collect_chunks) = self.utils
            
            self.is_initialized = True
            logger.info("✅ Silero VAD model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Silero VAD model: {e}")
            raise
    
    def detect_voice_activity(self, audio_chunk: np.ndarray) -> VADResult:
        """
        Detect voice activity in a single audio chunk.
        
        Args:
            audio_chunk: Audio data as numpy array (mono, float32, normalized)
            
        Returns:
            VADResult with detection results
        """
        if not self.is_initialized:
            raise RuntimeError("VAD model not initialized. Call initialize() first.")
            
        timestamp = time.time()
        
        try:
            # Ensure audio is in correct format
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)
                
            # Normalize if needed
            if np.abs(audio_chunk).max() > 1.0:
                audio_chunk = audio_chunk / np.abs(audio_chunk).max()
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio_chunk)
            
            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                threshold=self.threshold,
                sampling_rate=self.sample_rate,
                min_speech_duration_ms=self.min_speech_duration_ms,
                return_seconds=True
            )
            
            # Determine voice activity
            has_voice = len(speech_timestamps) > 0
            confidence = self._calculate_confidence(audio_chunk, speech_timestamps)
            
            # Update state tracking
            if has_voice:
                self.last_voice_time = timestamp
                self.current_state = VADState.VOICE
                self.voice_buffer.append(timestamp)
            else:
                # Check if we should transition to silence
                time_since_voice = timestamp - self.last_voice_time
                if time_since_voice > self.silence_timeout_seconds:
                    self.current_state = VADState.SILENCE
                else:
                    self.current_state = VADState.UNCERTAIN
            
            # Clean old entries from voice buffer (keep last 10 seconds)
            cutoff_time = timestamp - 10.0
            self.voice_buffer = [t for t in self.voice_buffer if t > cutoff_time]
            
            # Convert timestamps to relative time within chunk
            duration_seconds = len(audio_chunk) / self.sample_rate
            relative_timestamps = []
            for start, end in speech_timestamps:
                # Timestamps from Silero are already in seconds
                relative_timestamps.append((start, end))
            
            return VADResult(
                has_voice=has_voice,
                confidence=confidence,
                state=self.current_state,
                timestamp=timestamp,
                speech_segments=relative_timestamps
            )
            
        except Exception as e:
            logger.error(f"VAD detection failed: {e}")
            return VADResult(
                has_voice=False,
                confidence=0.0,
                state=VADState.UNCERTAIN,
                timestamp=timestamp,
                speech_segments=[]
            )
    
    def _calculate_confidence(self, audio_chunk: np.ndarray, speech_timestamps: List) -> float:
        """Calculate confidence score for voice activity detection."""
        if not speech_timestamps:
            return 0.0
        
        try:
            # Calculate percentage of chunk that contains speech
            chunk_duration = len(audio_chunk) / self.sample_rate
            speech_duration = 0.0
            
            for segment in speech_timestamps:
                if isinstance(segment, dict):
                    # Handle dict format: {'start': ..., 'end': ...}
                    start = float(segment.get('start', 0))
                    end = float(segment.get('end', 0))
                elif len(segment) == 2:
                    # Handle tuple format: (start, end)
                    start = float(segment[0])
                    end = float(segment[1])
                else:
                    continue
                
                speech_duration += (end - start)
            
            speech_ratio = min(speech_duration / chunk_duration, 1.0) if chunk_duration > 0 else 0.0
            
            # Factor in audio energy
            rms_energy = np.sqrt(np.mean(audio_chunk ** 2))
            energy_factor = min(rms_energy * 10, 1.0)  # Scale RMS to 0-1 range
            
            # Combined confidence score
            confidence = (speech_ratio * 0.7) + (energy_factor * 0.3)
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.warning(f"Error calculating VAD confidence: {e}")
            # Fallback to energy-based confidence
            rms_energy = np.sqrt(np.mean(audio_chunk ** 2))
            return min(rms_energy * 5, 1.0)
    
    def is_voice_active(self) -> bool:
        """Check if voice is currently active (convenience method)."""
        return self.current_state == VADState.VOICE
    
    def get_voice_activity_rate(self, window_seconds: float = 5.0) -> float:
        """
        Get the rate of voice activity over recent history.
        
        Args:
            window_seconds: Time window to analyze
            
        Returns:
            Voice activity rate (0.0 to 1.0)
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        recent_voice = [t for t in self.voice_buffer if t > cutoff_time]
        
        if not recent_voice:
            return 0.0
        
        # Estimate activity rate based on frequency of voice detections
        return min(len(recent_voice) / (window_seconds * 10), 1.0)  # Assume ~10 detections/sec max
    
    def reset_state(self):
        """Reset VAD state (useful for new conversation)."""
        self.last_voice_time = 0
        self.current_state = VADState.SILENCE
        self.voice_buffer.clear()
        logger.debug("VAD state reset")


class VADProcessor:
    """
    High-level VAD processor that handles streaming audio and provides callbacks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize VAD processor."""
        self.config = config
        self.vad = SileroVAD(config)
        self.callbacks = {
            'voice_start': [],
            'voice_end': [],
            'voice_activity': []
        }
        
        # Processing state
        self.is_processing = False
        self.last_state = VADState.SILENCE
        
    async def initialize(self):
        """Initialize the VAD processor."""
        await self.vad.initialize()
        
    def add_callback(self, event: str, callback):
        """
        Add callback for VAD events.
        
        Args:
            event: 'voice_start', 'voice_end', or 'voice_activity'
            callback: Function to call on event
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            raise ValueError(f"Unknown callback event: {event}")
    
    def process_audio_chunk(self, audio_chunk: np.ndarray) -> VADResult:
        """
        Process a single audio chunk and trigger callbacks.
        
        Args:
            audio_chunk: Audio data to process
            
        Returns:
            VADResult with detection results
        """
        result = self.vad.detect_voice_activity(audio_chunk)
        
        # Trigger state change callbacks
        if result.state != self.last_state:
            if result.state == VADState.VOICE and self.last_state == VADState.SILENCE:
                self._trigger_callbacks('voice_start', result)
            elif result.state == VADState.SILENCE and self.last_state == VADState.VOICE:
                self._trigger_callbacks('voice_end', result)
        
        # Always trigger activity callback
        self._trigger_callbacks('voice_activity', result)
        
        self.last_state = result.state
        return result
    
    def _trigger_callbacks(self, event: str, result: VADResult):
        """Trigger callbacks for the specified event."""
        for callback in self.callbacks[event]:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in VAD callback for {event}: {e}")
    
    def start_processing(self):
        """Start VAD processing."""
        self.is_processing = True
        logger.info("VAD processing started")
    
    def stop_processing(self):
        """Stop VAD processing."""
        self.is_processing = False
        logger.info("VAD processing stopped")
    
    def reset(self):
        """Reset VAD processor state."""
        self.vad.reset_state()
        self.last_state = VADState.SILENCE