"""
Audio Manager for coordinating VAD, STT, and audio I/O.

This module provides the central audio processing pipeline that coordinates
voice activity detection, speech recognition, and audio device management.
"""

import asyncio
import logging
import numpy as np
import pyaudio
import sounddevice as sd
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time
import queue

from .vad import VADProcessor, VADResult, VADState
from .stt import STTProcessor, TranscriptionResult


logger = logging.getLogger(__name__)


class AudioState(Enum):
    """Audio processing states."""
    STOPPED = "stopped"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class AudioDeviceInfo:
    """Information about an audio device."""
    index: int
    name: str
    channels: int
    sample_rate: float
    is_input: bool
    is_default: bool


@dataclass
class AudioEvent:
    """Audio processing event."""
    event_type: str  # 'voice_start', 'voice_end', 'transcription_ready'
    timestamp: float
    data: Any
    confidence: float


class AudioManager:
    """
    Central audio manager coordinating VAD, STT, and audio I/O.
    
    Manages the complete audio processing pipeline from microphone input
    through voice activity detection to speech transcription.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize audio manager."""
        self.config = config
        self.sample_rate = config.get('sample_rate', 16000)
        self.chunk_size = config.get('chunk_size', 1024)
        self.channels = 1  # Mono input for voice processing
        
        # Audio device configuration
        self.input_device = config.get('input_device')  # None = default
        self.output_device = config.get('output_device')  # None = default
        
        # Processing components
        self.vad_processor = VADProcessor(config)
        self.stt_processor = STTProcessor(config)
        
        # Audio I/O
        self.audio_stream = None
        self.pyaudio_instance = None
        
        # State management
        self.state = AudioState.STOPPED
        self.is_running = False
        self.processing_thread = None
        self.audio_queue = queue.Queue()
        
        # Callbacks
        self.callbacks = {
            'voice_start': [],
            'voice_end': [],
            'transcription_ready': [],
            'audio_error': [],
            'state_changed': []
        }
        
        # Performance tracking
        self.processed_chunks = 0
        self.dropped_chunks = 0
        self.total_processing_time = 0.0
        
        logger.info("Audio Manager initialized")
    
    async def initialize(self):
        """Initialize all audio components."""
        try:
            logger.info("Initializing audio components...")
            
            # Initialize audio processing components
            await self.vad_processor.initialize()
            await self.stt_processor.initialize()
            
            # Set up callbacks between components
            self._setup_callbacks()
            
            # Initialize audio devices
            self._initialize_audio_devices()
            
            logger.info("✅ Audio Manager initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Audio Manager initialization failed: {e}")
            raise
    
    def _setup_callbacks(self):
        """Set up callbacks between VAD and STT processors."""
        # VAD callbacks
        self.vad_processor.add_callback('voice_start', self._on_voice_start)
        self.vad_processor.add_callback('voice_end', self._on_voice_end)
        self.vad_processor.add_callback('voice_activity', self._on_voice_activity)
        
        # STT callbacks
        self.stt_processor.add_callback('transcription_ready', self._on_transcription_ready)
        self.stt_processor.add_callback('transcription_error', self._on_transcription_error)
    
    def _initialize_audio_devices(self):
        """Initialize PyAudio and detect available devices."""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Log available devices
            self._log_audio_devices()
            
            # Validate selected devices
            self._validate_audio_devices()
            
        except Exception as e:
            logger.error(f"Failed to initialize audio devices: {e}")
            raise
    
    def _log_audio_devices(self):
        """Log information about available audio devices."""
        logger.info("Available audio devices:")
        
        for i in range(self.pyaudio_instance.get_device_count()):
            info = self.pyaudio_instance.get_device_info_by_index(i)
            device_type = []
            if info['maxInputChannels'] > 0:
                device_type.append("input")
            if info['maxOutputChannels'] > 0:
                device_type.append("output")
            
            logger.info(f"  [{i}] {info['name']} ({', '.join(device_type)}) - {info['defaultSampleRate']}Hz")
    
    def _validate_audio_devices(self):
        """Validate that selected audio devices are available."""
        if self.input_device is not None:
            try:
                info = self.pyaudio_instance.get_device_info_by_index(self.input_device)
                if info['maxInputChannels'] == 0:
                    raise ValueError(f"Device {self.input_device} has no input channels")
                logger.info(f"Using input device: {info['name']}")
            except Exception as e:
                logger.warning(f"Invalid input device {self.input_device}: {e}")
                self.input_device = None
        
        if self.input_device is None:
            default_input = self.pyaudio_instance.get_default_input_device_info()
            logger.info(f"Using default input device: {default_input['name']}")
    
    def get_available_devices(self) -> List[AudioDeviceInfo]:
        """Get list of available audio devices."""
        devices = []
        
        if not self.pyaudio_instance:
            return devices
        
        for i in range(self.pyaudio_instance.get_device_count()):
            try:
                info = self.pyaudio_instance.get_device_info_by_index(i)
                
                # Add as input device if it has input channels
                if info['maxInputChannels'] > 0:
                    devices.append(AudioDeviceInfo(
                        index=i,
                        name=info['name'],
                        channels=info['maxInputChannels'],
                        sample_rate=info['defaultSampleRate'],
                        is_input=True,
                        is_default=(i == self.pyaudio_instance.get_default_input_device_info()['index'])
                    ))
                
                # Add as output device if it has output channels
                if info['maxOutputChannels'] > 0:
                    devices.append(AudioDeviceInfo(
                        index=i,
                        name=info['name'],
                        channels=info['maxOutputChannels'],
                        sample_rate=info['defaultSampleRate'],
                        is_input=False,
                        is_default=(i == self.pyaudio_instance.get_default_output_device_info()['index'])
                    ))
            
            except Exception as e:
                logger.warning(f"Error getting info for device {i}: {e}")
        
        return devices
    
    def add_callback(self, event: str, callback: Callable):
        """
        Add callback for audio events.
        
        Args:
            event: Event type ('voice_start', 'voice_end', 'transcription_ready', 'audio_error', 'state_changed')
            callback: Function to call on event
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)
        else:
            raise ValueError(f"Unknown callback event: {event}")
    
    def _trigger_callbacks(self, event: str, data: Any):
        """Trigger callbacks for the specified event."""
        for callback in self.callbacks[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in audio callback for {event}: {e}")
    
    def _set_state(self, new_state: AudioState):
        """Change audio processing state and notify callbacks."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            logger.info(f"Audio state changed: {old_state.value} → {new_state.value}")
            
            event = AudioEvent(
                event_type='state_changed',
                timestamp=time.time(),
                data={'old_state': old_state, 'new_state': new_state},
                confidence=1.0
            )
            self._trigger_callbacks('state_changed', event)
    
    async def start_listening(self):
        """Start audio processing."""
        if self.is_running:
            logger.warning("Audio processing is already running")
            return
        
        try:
            logger.info("Starting audio processing...")
            self._set_state(AudioState.LISTENING)
            
            # Start audio stream
            self._start_audio_stream()
            
            # Start processing thread
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._audio_processing_loop, daemon=True)
            self.processing_thread.start()
            
            # Start VAD processing
            self.vad_processor.start_processing()
            
            logger.info("✅ Audio processing started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start audio processing: {e}")
            self._set_state(AudioState.ERROR)
            raise
    
    def _start_audio_stream(self):
        """Start PyAudio stream for microphone input."""
        try:
            self.audio_stream = self.pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
                start=True
            )
            
            logger.info(f"Audio stream started: {self.sample_rate}Hz, {self.chunk_size} samples/chunk")
            
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for incoming audio data."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            # Convert audio data to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Add to processing queue (non-blocking)
            try:
                self.audio_queue.put_nowait(audio_data.copy())
            except queue.Full:
                self.dropped_chunks += 1
                logger.warning("Audio queue full, dropping chunk")
        
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def _audio_processing_loop(self):
        """Main audio processing loop (runs in separate thread)."""
        logger.info("Audio processing loop started")
        
        while self.is_running:
            try:
                # Get audio chunk from queue (with timeout)
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                start_time = time.time()
                
                # Process with VAD
                vad_result = self.vad_processor.process_audio_chunk(audio_chunk)
                
                # Add to STT buffer if voice is active
                if vad_result.has_voice:
                    self.stt_processor.add_audio_chunk(audio_chunk)
                
                # Update statistics
                self.processed_chunks += 1
                self.total_processing_time += time.time() - start_time
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")
                self._set_state(AudioState.ERROR)
                break
        
        logger.info("Audio processing loop ended")
    
    def stop_listening(self):
        """Stop audio processing."""
        if not self.is_running:
            logger.warning("Audio processing is not running")
            return
        
        try:
            logger.info("Stopping audio processing...")
            
            # Stop processing
            self.is_running = False
            self.vad_processor.stop_processing()
            
            # Stop audio stream
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            
            # Wait for processing thread to finish
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)
            
            # Clear queues
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            self._set_state(AudioState.STOPPED)
            logger.info("✅ Audio processing stopped")
            
        except Exception as e:
            logger.error(f"Error stopping audio processing: {e}")
    
    # Event handlers
    def _on_voice_start(self, vad_result: VADResult):
        """Handle voice activity start."""
        logger.debug("Voice activity started")
        self._set_state(AudioState.PROCESSING)
        
        event = AudioEvent(
            event_type='voice_start',
            timestamp=vad_result.timestamp,
            data=vad_result,
            confidence=vad_result.confidence
        )
        self._trigger_callbacks('voice_start', event)
    
    def _on_voice_end(self, vad_result: VADResult):
        """Handle voice activity end."""
        logger.debug("Voice activity ended")
        self._set_state(AudioState.LISTENING)
        
        # Trigger transcription of buffered audio
        asyncio.create_task(self._process_voice_segment())
        
        event = AudioEvent(
            event_type='voice_end',
            timestamp=vad_result.timestamp,
            data=vad_result,
            confidence=vad_result.confidence
        )
        self._trigger_callbacks('voice_end', event)
    
    def _on_voice_activity(self, vad_result: VADResult):
        """Handle voice activity updates."""
        # This is called for every audio chunk, so we don't log it
        pass
    
    async def _process_voice_segment(self):
        """Process the voice segment for transcription."""
        try:
            result = await self.stt_processor.process_buffered_audio()
            if result and result.text.strip():
                logger.info(f"Transcription: '{result.text}' (confidence: {result.confidence:.2f})")
        except Exception as e:
            logger.error(f"Error processing voice segment: {e}")
    
    def _on_transcription_ready(self, transcription_result: TranscriptionResult):
        """Handle transcription completion."""
        logger.debug(f"Transcription ready: '{transcription_result.text}'")
        
        event = AudioEvent(
            event_type='transcription_ready',
            timestamp=time.time(),
            data=transcription_result,
            confidence=transcription_result.confidence
        )
        self._trigger_callbacks('transcription_ready', event)
    
    def _on_transcription_error(self, transcription_result: TranscriptionResult):
        """Handle transcription errors."""
        logger.error(f"Transcription error: {transcription_result.error}")
        
        event = AudioEvent(
            event_type='audio_error',
            timestamp=time.time(),
            data=transcription_result,
            confidence=0.0
        )
        self._trigger_callbacks('audio_error', event)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        avg_processing_time = (self.total_processing_time / self.processed_chunks 
                             if self.processed_chunks > 0 else 0.0)
        
        return {
            "state": self.state.value,
            "processed_chunks": self.processed_chunks,
            "dropped_chunks": self.dropped_chunks,
            "drop_rate": (self.dropped_chunks / max(self.processed_chunks + self.dropped_chunks, 1)),
            "average_processing_time": avg_processing_time,
            "chunks_per_second": (1.0 / avg_processing_time) if avg_processing_time > 0 else 0.0,
            "vad_stats": self.vad_processor.vad.get_voice_activity_rate(),
            "stt_stats": self.stt_processor.get_performance_stats(),
            "buffer_duration": self.stt_processor.get_buffer_duration(),
            "queue_size": self.audio_queue.qsize()
        }
    
    def reset(self):
        """Reset audio processing state."""
        self.vad_processor.reset()
        self.stt_processor.clear_buffer()
        
        # Reset statistics
        self.processed_chunks = 0
        self.dropped_chunks = 0
        self.total_processing_time = 0.0
        
        logger.info("Audio processing state reset")
    
    def cleanup(self):
        """Cleanup all resources."""
        self.stop_listening()
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        self.stt_processor.cleanup()
        
        logger.info("Audio Manager cleanup complete")