#!/usr/bin/env python3
"""
Real-time Audio Monitor - Monitor microphone levels and system behavior

This tool provides real-time visualization of:
1. Microphone input levels and activity
2. Voice Activity Detection (VAD) decisions
3. System echo cancellation status
4. Audio ducking behavior
"""

import asyncio
import sys
import time
from pathlib import Path
from collections import deque
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import threading
import queue

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.vad import SileroVAD

class RealTimeAudioMonitor:
    def __init__(self):
        self.sample_rate = 16000
        self.device_id = 2  # Live Streamer CAM 513
        self.chunk_size = 1024
        self.buffer_duration = 5.0  # 5 seconds of history
        self.buffer_size = int(self.buffer_duration * self.sample_rate / self.chunk_size)
        
        # Data buffers
        self.audio_buffer = deque(maxlen=self.buffer_size)
        self.rms_buffer = deque(maxlen=self.buffer_size)
        self.vad_confidence_buffer = deque(maxlen=self.buffer_size)
        self.vad_decision_buffer = deque(maxlen=self.buffer_size)
        self.timestamp_buffer = deque(maxlen=self.buffer_size)
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.vad = None
        self.is_monitoring = False
        self.is_speaking = False  # Simulate echo cancellation state
        
        # Thresholds
        self.noise_floor = 0.001
        self.voice_threshold = 0.005
        self.vad_threshold = 0.7
        
    async def initialize(self):
        """Initialize VAD system"""
        print("🔧 Initializing Real-time Audio Monitor...")
        
        vad_config = {
            'sample_rate': self.sample_rate,
            'vad_threshold': self.vad_threshold,
            'min_speech_duration_ms': 300,
            'silence_timeout_seconds': 2.0
        }
        
        self.vad = SileroVAD(vad_config)
        await self.vad.initialize()
        print("✅ VAD initialized")
        
    def audio_callback(self, indata, frames, time, status):
        """Audio stream callback"""
        if status:
            print(f"Audio status: {status}")
        
        try:
            # Put audio data in queue for processing
            audio_chunk = indata[:, 0].copy()  # Take first channel
            self.audio_queue.put((audio_chunk, time.inputBufferAdcTime))
        except Exception as e:
            print(f"Audio callback error: {e}")
    
    def process_audio_chunk(self, audio_chunk, timestamp):
        """Process single audio chunk"""
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        # VAD processing
        vad_result = self.vad.detect_voice_activity(audio_chunk)
        
        # Echo cancellation simulation
        is_ducked = self.is_speaking or rms < self.noise_floor
        
        # Store in buffers
        self.audio_buffer.append(audio_chunk)
        self.rms_buffer.append(rms)
        self.vad_confidence_buffer.append(vad_result.confidence)
        self.vad_decision_buffer.append(vad_result.has_voice)
        self.timestamp_buffer.append(timestamp)
        
        return {
            'rms': rms,
            'vad_confidence': vad_result.confidence,
            'vad_decision': vad_result.has_voice,
            'is_ducked': is_ducked,
            'timestamp': timestamp
        }
    
    def audio_processing_thread(self):
        """Background thread for audio processing"""
        while self.is_monitoring:
            try:
                # Get audio chunk with timeout
                audio_chunk, timestamp = self.audio_queue.get(timeout=1.0)
                
                # Process the chunk
                result = self.process_audio_chunk(audio_chunk, timestamp)
                
                # Print real-time status (optional)
                if len(self.rms_buffer) % 10 == 0:  # Every 10 chunks
                    self.print_status(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Processing error: {e}")
    
    def print_status(self, result):
        """Print current audio status"""
        rms = result['rms']
        vad_conf = result['vad_confidence']
        vad_decision = result['vad_decision']
        is_ducked = result['is_ducked']
        
        # Visual indicators
        level_bar = "█" * int(min(rms * 1000, 50))
        vad_bar = "█" * int(vad_conf * 20)
        
        status_line = f"\r"
        status_line += f"RMS: {rms:.4f} |{level_bar:<50}| "
        status_line += f"VAD: {vad_conf:.2f} |{vad_bar:<20}| "
        status_line += f"Voice: {'YES' if vad_decision else 'NO '} "
        status_line += f"Ducked: {'YES' if is_ducked else 'NO '}"
        
        print(status_line, end='', flush=True)
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        print("🎤 Starting real-time audio monitoring...")
        print("📊 Monitoring: RMS levels, VAD decisions, echo cancellation status")
        print("⚠️  Press Ctrl+C to stop")
        
        self.is_monitoring = True
        
        # Start audio processing thread
        processing_thread = threading.Thread(target=self.audio_processing_thread)
        processing_thread.daemon = True
        processing_thread.start()
        
        # Start audio stream
        with sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            callback=self.audio_callback
        ):
            try:
                while self.is_monitoring:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping monitoring...")
                self.is_monitoring = False
    
    def create_live_plot(self):
        """Create live updating plot"""
        print("📈 Starting live audio visualization...")
        print("Close the plot window to stop monitoring")
        
        self.is_monitoring = True
        
        # Start audio processing thread
        processing_thread = threading.Thread(target=self.audio_processing_thread)
        processing_thread.daemon = True
        processing_thread.start()
        
        # Start audio stream
        stream = sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size,
            callback=self.audio_callback
        )
        
        # Create matplotlib figure
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))
        fig.suptitle('Real-time Audio Monitor')
        
        # Initialize plots
        x_data = list(range(self.buffer_size))
        line1, = ax1.plot(x_data, [0] * self.buffer_size, 'b-')
        ax1.set_ylabel('RMS Level')
        ax1.set_ylim(0, 0.1)
        ax1.axhline(y=self.noise_floor, color='r', linestyle='--', label='Noise Floor')
        ax1.axhline(y=self.voice_threshold, color='g', linestyle='--', label='Voice Threshold')
        ax1.legend()
        
        line2, = ax2.plot(x_data, [0] * self.buffer_size, 'g-')
        ax2.set_ylabel('VAD Confidence')
        ax2.set_ylim(0, 1.0)
        ax2.axhline(y=self.vad_threshold, color='r', linestyle='--', label='VAD Threshold')
        ax2.legend()
        
        line3, = ax3.plot(x_data, [0] * self.buffer_size, 'r-', label='VAD Decision')
        ax3.set_ylabel('Voice Detected')
        ax3.set_xlabel('Time (chunks)')
        ax3.set_ylim(-0.1, 1.1)
        ax3.legend()
        
        def animate(frame):
            if len(self.rms_buffer) > 0:
                # Update data
                rms_data = list(self.rms_buffer)
                vad_conf_data = list(self.vad_confidence_buffer)
                vad_decision_data = [1.0 if x else 0.0 for x in self.vad_decision_buffer]
                
                # Pad with zeros if not enough data
                while len(rms_data) < self.buffer_size:
                    rms_data.insert(0, 0)
                while len(vad_conf_data) < self.buffer_size:
                    vad_conf_data.insert(0, 0)
                while len(vad_decision_data) < self.buffer_size:
                    vad_decision_data.insert(0, 0)
                
                # Update plots
                line1.set_ydata(rms_data)
                line2.set_ydata(vad_conf_data)
                line3.set_ydata(vad_decision_data)
                
                # Auto-scale RMS plot based on current max
                current_max_rms = max(rms_data) if rms_data else 0.1
                ax1.set_ylim(0, max(0.01, current_max_rms * 1.2))
            
            return line1, line2, line3
        
        # Start animation
        stream.start()
        ani = animation.FuncAnimation(fig, animate, interval=100, blit=False, cache_frame_data=False)
        
        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
            self.is_monitoring = False
            stream.stop()
            stream.close()
    
    def calibrate_thresholds(self):
        """Interactive threshold calibration"""
        print("🎯 Interactive Threshold Calibration")
        print("This will help optimize voice detection for your environment")
        
        # Step 1: Measure noise floor
        input("\nStep 1: Press ENTER and remain silent for 5 seconds")
        print("🤫 Measuring noise floor...")
        
        noise_samples = []
        with sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size
        ) as stream:
            for _ in range(int(5 * self.sample_rate / self.chunk_size)):
                audio_chunk, _ = stream.read(self.chunk_size)
                rms = np.sqrt(np.mean(audio_chunk[:, 0] ** 2))
                noise_samples.append(rms)
                time.sleep(0.01)
        
        self.noise_floor = np.mean(noise_samples) + 2 * np.std(noise_samples)
        print(f"✅ Noise floor: {self.noise_floor:.6f}")
        
        # Step 2: Measure voice levels
        input("\nStep 2: Press ENTER and speak normally for 5 seconds")
        print("🗣️ Measuring voice levels...")
        
        voice_samples = []
        with sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_size
        ) as stream:
            for _ in range(int(5 * self.sample_rate / self.chunk_size)):
                audio_chunk, _ = stream.read(self.chunk_size)
                rms = np.sqrt(np.mean(audio_chunk[:, 0] ** 2))
                voice_samples.append(rms)
                time.sleep(0.01)
        
        voice_mean = np.mean(voice_samples)
        voice_min = np.min([x for x in voice_samples if x > self.noise_floor])
        
        # Suggest optimal threshold
        suggested_threshold = self.noise_floor + (voice_min - self.noise_floor) * 0.3
        
        print(f"✅ Voice level (mean): {voice_mean:.6f}")
        print(f"✅ Voice level (min): {voice_min:.6f}")
        print(f"🎯 Suggested RMS threshold: {suggested_threshold:.6f}")
        
        self.voice_threshold = suggested_threshold
        
        print("\n📊 Calibration Results:")
        print(f"   Noise floor: {self.noise_floor:.6f}")
        print(f"   Voice threshold: {self.voice_threshold:.6f}")
        print(f"   SNR: {voice_mean/self.noise_floor:.2f}")

async def main():
    """Main interface"""
    print("🎛️ Real-time Audio Monitor")
    print("=" * 50)
    
    monitor = RealTimeAudioMonitor()
    await monitor.initialize()
    
    while True:
        print("\n" + "=" * 50)
        print("🎤 Audio Monitor Menu:")
        print("1. Real-time text monitoring")
        print("2. Live graphical visualization")
        print("3. Calibrate thresholds")
        print("4. Set echo cancellation state (simulate TTS)")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            monitor.start_monitoring()
        elif choice == '2':
            monitor.create_live_plot()
        elif choice == '3':
            monitor.calibrate_thresholds()
        elif choice == '4':
            current_state = "ON" if monitor.is_speaking else "OFF"
            print(f"Current echo cancellation simulation: {current_state}")
            toggle = input("Toggle state? (y/n): ").strip().lower()
            if toggle == 'y':
                monitor.is_speaking = not monitor.is_speaking
                new_state = "ON" if monitor.is_speaking else "OFF"
                print(f"Echo cancellation simulation: {new_state}")
        elif choice == '5':
            print("👋 Exiting monitor...")
            break
        else:
            print("❌ Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    asyncio.run(main())