"""
Speech-to-Text (STT) using OpenAI Whisper for local transcription.

This module provides local speech recognition using Whisper models,
optimized for real-time voice interface applications.
"""

import whisper
import torch
import numpy as np
import logging
import asyncio
import tempfile
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import time
import io
import wave
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)


class WhisperModelSize(Enum):
    """Available Whisper model sizes with trade-offs."""
    TINY = "tiny"      # ~39 MB, fast but less accurate
    BASE = "base"      # ~74 MB, balanced performance
    SMALL = "small"    # ~244 MB, good accuracy
    MEDIUM = "medium"  # ~769 MB, better accuracy
    LARGE = "large"    # ~1550 MB, best accuracy


@dataclass
class TranscriptionResult:
    """Result from speech-to-text transcription."""
    text: str
    confidence: float
    language: str
    processing_time: float
    model_used: str
    segments: List[Dict[str, Any]] = None
    error: Optional[str] = None


class WhisperSTT:
    """
    Local Speech-to-Text using OpenAI Whisper.
    
    Provides real-time speech recognition with configurable model sizes
    and optimization for voice interface applications.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Whisper STT."""
        self.config = config
        self.model_size = WhisperModelSize(config.get('whisper_model', 'base'))
        self.device = config.get('whisper_device', 'cpu')
        self.language = config.get('language', 'en')
        self.sample_rate = config.get('sample_rate', 16000)
        
        # Model and processing
        self.model = None
        self.is_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Performance tracking
        self.transcription_count = 0
        self.total_processing_time = 0.0
        
        logger.info(f"Initializing Whisper STT with model={self.model_size.value}")
        
    async def initialize(self):
        """Initialize the Whisper model (async to avoid blocking)."""
        try:
            logger.info(f"Loading Whisper {self.model_size.value} model...")
            
            # Load model in thread pool to avoid blocking
            def load_model():
                return whisper.load_model(
                    self.model_size.value,
                    device=self.device,
                    download_root=None  # Use default cache location
                )
            
            self.model = await asyncio.get_event_loop().run_in_executor(
                self.executor, load_model
            )
            
            self.is_initialized = True
            logger.info(f"✅ Whisper {self.model_size.value} model loaded successfully")
            
            # Log model details
            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(f"Model parameters: {total_params:,}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            raise
    
    async def transcribe_audio(self, audio_data: np.ndarray) -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio data as numpy array (mono, float32, 16kHz)
            
        Returns:
            TranscriptionResult with transcription and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Whisper model not initialized. Call initialize() first.")
        
        start_time = time.time()
        
        try:
            # Ensure audio is in correct format for Whisper
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Normalize audio
            if np.abs(audio_data).max() > 1.0:
                audio_data = audio_data / np.abs(audio_data).max()
            
            # Check for sufficient audio length (Whisper works best with >1 second)
            duration = len(audio_data) / self.sample_rate
            if duration < 0.5:
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    language=self.language,
                    processing_time=time.time() - start_time,
                    model_used=self.model_size.value,
                    error="Audio too short for transcription"
                )
            
            # Transcribe in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._transcribe_sync, audio_data
            )
            
            processing_time = time.time() - start_time
            
            # Update statistics
            self.transcription_count += 1
            self.total_processing_time += processing_time
            
            # Calculate confidence from segments if available
            confidence = self._calculate_confidence(result)
            
            return TranscriptionResult(
                text=result["text"].strip(),
                confidence=confidence,
                language=result.get("language", self.language),
                processing_time=processing_time,
                model_used=self.model_size.value,
                segments=result.get("segments", [])
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Transcription failed: {e}")
            
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language=self.language,
                processing_time=processing_time,
                model_used=self.model_size.value,
                error=str(e)
            )
    
    def _transcribe_sync(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Synchronous transcription (runs in thread pool)."""
        # Use Whisper's transcribe method
        result = self.model.transcribe(
            audio_data,
            language=self.language if self.language != 'auto' else None,
            task="transcribe",  # vs "translate"
            fp16=False,  # Use fp32 for better compatibility
            verbose=False
        )
        
        return result
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate overall confidence from segment probabilities."""
        segments = result.get("segments", [])
        if not segments:
            return 0.5  # Default confidence when no segments
        
        # Average the confidence scores from segments
        confidences = []
        for segment in segments:
            # Whisper doesn't directly provide confidence, but we can estimate
            # from the number of tokens and other factors
            if "avg_logprob" in segment:
                # Convert log probability to confidence estimate
                log_prob = segment["avg_logprob"]
                confidence = min(max((log_prob + 1.0) / 1.0, 0.0), 1.0)
                confidences.append(confidence)
        
        if confidences:
            return sum(confidences) / len(confidences)
        
        # Fallback: estimate from text length and content
        text = result.get("text", "").strip()
        if not text:
            return 0.0
        
        # Simple heuristic: longer, more complete sentences = higher confidence
        word_count = len(text.split())
        if word_count == 0:
            return 0.0
        elif word_count < 3:
            return 0.3
        elif word_count < 8:
            return 0.6
        else:
            return 0.8
    
    async def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """
        Transcribe audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            TranscriptionResult with transcription
        """
        if not self.is_initialized:
            raise RuntimeError("Whisper model not initialized. Call initialize() first.")
        
        try:
            # Load audio file
            audio_data = whisper.load_audio(file_path)
            return await self.transcribe_audio(audio_data)
            
        except Exception as e:
            logger.error(f"Failed to transcribe file {file_path}: {e}")
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language=self.language,
                processing_time=0.0,
                model_used=self.model_size.value,
                error=str(e)
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        avg_time = (self.total_processing_time / self.transcription_count 
                   if self.transcription_count > 0 else 0.0)
        
        return {
            "model_size": self.model_size.value,
            "device": self.device,
            "transcription_count": self.transcription_count,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_time,
            "transcriptions_per_minute": (60.0 / avg_time) if avg_time > 0 else 0.0
        }
    
    def cleanup(self):
        """Cleanup resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
        
        # Clear model from memory
        self.model = None
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
        logger.info("Whisper STT cleaned up")


class STTProcessor:
    """
    High-level STT processor that handles audio buffering and provides callbacks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize STT processor."""
        self.config = config
        self.stt = WhisperSTT(config)
        self.callbacks = {
            'transcription_ready': [],
            'transcription_error': []
        }
        
        # Audio buffering
        self.audio_buffer = []
        self.buffer_duration_seconds = config.get('buffer_duration_seconds', 3.0)
        self.sample_rate = config.get('sample_rate', 16000)
        self.max_buffer_samples = int(self.buffer_duration_seconds * self.sample_rate)
        
        # Processing state
        self.is_processing = False
        
    async def initialize(self):
        """Initialize the STT processor."""
        await self.stt.initialize()
    
    def add_callback(self, event: str, callback):
        """
        Add callback for STT events.
        
        Args:
            event: 'transcription_ready' or 'transcription_error'
            callback: Function to call on event
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            raise ValueError(f"Unknown callback event: {event}")
    
    def add_audio_chunk(self, audio_chunk: np.ndarray):
        """
        Add audio chunk to buffer for processing.
        
        Args:
            audio_chunk: Audio data to add
        """
        self.audio_buffer.extend(audio_chunk)
        
        # Keep buffer within size limits
        if len(self.audio_buffer) > self.max_buffer_samples:
            excess = len(self.audio_buffer) - self.max_buffer_samples
            self.audio_buffer = self.audio_buffer[excess:]
    
    async def process_buffered_audio(self) -> Optional[TranscriptionResult]:
        """
        Process currently buffered audio for transcription.
        
        Returns:
            TranscriptionResult or None if buffer is empty
        """
        if not self.audio_buffer:
            return None
        
        try:
            # Convert buffer to numpy array
            audio_data = np.array(self.audio_buffer, dtype=np.float32)
            
            # Transcribe
            result = await self.stt.transcribe_audio(audio_data)
            
            # Trigger callbacks
            if result.error:
                self._trigger_callbacks('transcription_error', result)
            else:
                self._trigger_callbacks('transcription_ready', result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing buffered audio: {e}")
            error_result = TranscriptionResult(
                text="",
                confidence=0.0,
                language=self.config.get('language', 'en'),
                processing_time=0.0,
                model_used=self.stt.model_size.value,
                error=str(e)
            )
            self._trigger_callbacks('transcription_error', error_result)
            return error_result
    
    def clear_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()
        
    def get_buffer_duration(self) -> float:
        """Get current buffer duration in seconds."""
        return len(self.audio_buffer) / self.sample_rate
    
    def _trigger_callbacks(self, event: str, result: TranscriptionResult):
        """Trigger callbacks for the specified event."""
        for callback in self.callbacks[event]:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in STT callback for {event}: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.stt.get_performance_stats()
    
    def cleanup(self):
        """Cleanup resources."""
        self.clear_buffer()
        self.stt.cleanup()