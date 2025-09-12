#!/usr/bin/env python3
"""
Audio Feedback Analyzer - Test and calibrate voice interface for specific acoustic environment

This tool helps identify:
1. Speaker-to-microphone feedback characteristics
2. User voice signature vs system audio
3. Optimal VAD thresholds for the environment
4. Echo patterns and cancellation effectiveness
"""

import asyncio
import sys
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from scipy import signal
from scipy.fft import fft, fftfreq
import subprocess

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.stt import WhisperSTT
from audio.vad import SileroVAD

class AudioFeedbackAnalyzer:
    def __init__(self):
        self.sample_rate = 16000
        self.device_id = 2  # Live Streamer CAM 513
        self.recordings = {}
        self.analysis_results = {}
        self.stt = None
        self.vad = None
        
    async def initialize(self):
        """Initialize audio components"""
        print("🔧 Initializing Audio Feedback Analyzer...")
        
        # Initialize STT for transcription testing
        stt_config = {'sample_rate': 16000, 'whisper_model': 'base'}
        self.stt = WhisperSTT(stt_config)
        await self.stt.initialize()
        print("✅ Whisper STT ready")
        
        # Initialize VAD for voice detection testing
        vad_config = {
            'sample_rate': 16000,
            'vad_threshold': 0.7,
            'min_speech_duration_ms': 300,
            'silence_timeout_seconds': 2.0
        }
        self.vad = SileroVAD(vad_config)
        await self.vad.initialize()
        print("✅ Silero VAD ready")
        
        print("🎯 Audio Feedback Analyzer initialized!")
    
    def record_audio(self, duration, label, description=""):
        """Record audio sample with label"""
        print(f"\n🎤 Recording {label}: {description}")
        print(f"🔴 Recording {duration} seconds...")
        
        audio_data = sd.rec(
            int(duration * self.sample_rate), 
            samplerate=self.sample_rate, 
            channels=1, 
            dtype=np.float32,
            device=self.device_id
        )
        sd.wait()
        
        self.recordings[label] = {
            'audio': audio_data.flatten(),
            'timestamp': datetime.now(),
            'description': description,
            'duration': duration
        }
        
        print(f"✅ {label} recorded ({len(audio_data)} samples)")
        return audio_data.flatten()
    
    def generate_test_tones(self):
        """Generate various test tones for speaker output"""
        print("\n🔊 Generating Test Tones...")
        
        test_tones = {
            'sine_440hz': self._generate_sine_wave(440, 2.0),      # A4 note
            'sine_1000hz': self._generate_sine_wave(1000, 2.0),    # 1kHz test tone
            'white_noise': np.random.normal(0, 0.1, int(2 * self.sample_rate)),
            'chirp': signal.chirp(np.linspace(0, 2, int(2 * self.sample_rate)), 
                                 200, 2, 2000, method='linear')
        }
        
        for tone_name, tone_data in test_tones.items():
            print(f"🎵 Playing {tone_name}...")
            input(f"Press ENTER to play {tone_name} (prepare to record feedback)")
            
            # Play tone and record simultaneously
            play_thread = threading.Thread(target=self._play_audio, args=(tone_data,))
            play_thread.start()
            
            # Record the feedback
            feedback = self.record_audio(3.0, f"{tone_name}_feedback", 
                                       f"Microphone pickup of {tone_name}")
            
            play_thread.join()
            
            # Analyze the feedback
            self._analyze_feedback(tone_data, feedback, tone_name)
    
    def _generate_sine_wave(self, frequency, duration):
        """Generate sine wave of specified frequency and duration"""
        t = np.linspace(0, duration, int(duration * self.sample_rate), False)
        return 0.3 * np.sin(2 * np.pi * frequency * t)  # 30% amplitude
    
    def _play_audio(self, audio_data):
        """Play audio through speakers"""
        sd.play(audio_data, samplerate=self.sample_rate)
        sd.wait()
    
    def _analyze_feedback(self, original, feedback, label):
        """Analyze feedback characteristics"""
        print(f"🔍 Analyzing {label} feedback...")
        
        # Calculate RMS levels
        original_rms = np.sqrt(np.mean(original ** 2))
        feedback_rms = np.sqrt(np.mean(feedback ** 2))
        feedback_ratio = feedback_rms / original_rms if original_rms > 0 else 0
        
        # Frequency analysis
        original_fft = fft(original)
        feedback_fft = fft(feedback)
        freqs = fftfreq(len(original), 1/self.sample_rate)
        
        # Find dominant frequencies
        original_peak_freq = freqs[np.argmax(np.abs(original_fft))]
        feedback_peak_freq = freqs[np.argmax(np.abs(feedback_fft))]
        
        # Cross-correlation for delay detection
        correlation = signal.correlate(feedback, original, mode='full')
        delay_samples = np.argmax(correlation) - len(original) + 1
        delay_ms = (delay_samples / self.sample_rate) * 1000
        
        analysis = {
            'feedback_ratio': feedback_ratio,
            'original_rms': original_rms,
            'feedback_rms': feedback_rms,
            'original_peak_freq': original_peak_freq,
            'feedback_peak_freq': feedback_peak_freq,
            'estimated_delay_ms': delay_ms,
            'correlation_peak': np.max(correlation)
        }
        
        self.analysis_results[label] = analysis
        
        print(f"   📊 Feedback ratio: {feedback_ratio:.4f}")
        print(f"   📊 Delay: {delay_ms:.2f}ms")
        print(f"   📊 Original peak: {original_peak_freq:.1f}Hz")
        print(f"   📊 Feedback peak: {feedback_peak_freq:.1f}Hz")
    
    async def test_voice_recognition(self):
        """Test voice recognition with current setup"""
        print("\n🗣️ Voice Recognition Testing...")
        
        # Record baseline silence
        input("Press ENTER to record 3 seconds of silence (no speaking)")
        silence = self.record_audio(3.0, "silence", "Background noise baseline")
        
        # Calculate noise floor
        noise_floor = np.sqrt(np.mean(silence ** 2))
        print(f"📊 Noise floor: {noise_floor:.6f}")
        
        # Test voice recognition at different distances/volumes
        distances = ["close", "normal", "far"]
        
        for distance in distances:
            input(f"\nPress ENTER to record your voice from {distance} distance")
            print("🎤 Say: 'This is a test of my voice recognition system'")
            
            voice_audio = self.record_audio(5.0, f"voice_{distance}", 
                                          f"User voice from {distance} distance")
            
            # Analyze voice characteristics
            voice_rms = np.sqrt(np.mean(voice_audio ** 2))
            snr = voice_rms / noise_floor if noise_floor > 0 else float('inf')
            
            # Test VAD detection
            vad_result = self.vad.detect_voice_activity(voice_audio)
            
            # Test transcription
            transcription = await self.stt.transcribe_audio(voice_audio)
            
            print(f"   📊 Voice RMS: {voice_rms:.6f}")
            print(f"   📊 SNR: {snr:.2f}")
            print(f"   📊 VAD confidence: {vad_result.confidence:.3f}")
            print(f"   📊 VAD detected: {vad_result.has_voice}")
            print(f"   📊 Transcription: '{transcription.text}'")
            print(f"   📊 Transcription confidence: {transcription.confidence:.3f}")
            
            # Store analysis
            self.analysis_results[f"voice_{distance}"] = {
                'voice_rms': voice_rms,
                'snr': snr,
                'vad_confidence': vad_result.confidence,
                'vad_detected': vad_result.has_voice,
                'transcription': transcription.text,
                'transcription_confidence': transcription.confidence
            }
    
    def test_echo_cancellation_effectiveness(self):
        """Test current echo cancellation system"""
        print("\n🛡️ Testing Echo Cancellation Effectiveness...")
        
        # Test different TTS phrases
        test_phrases = [
            "Hello, this is a test of the text to speech system",
            "The quick brown fox jumps over the lazy dog",
            "I am an artificial intelligence assistant",
        ]
        
        for i, phrase in enumerate(test_phrases):
            print(f"\n🤖 Testing phrase {i+1}: '{phrase}'")
            input("Press ENTER to start TTS + microphone recording test")
            
            # Start recording before TTS
            recording_thread = threading.Thread(
                target=self._record_during_tts, 
                args=(phrase, 5.0)
            )
            recording_thread.start()
            
            # Small delay then start TTS
            time.sleep(0.5)
            subprocess.run(['say', phrase])
            
            recording_thread.join()
    
    def _record_during_tts(self, phrase, duration):
        """Record microphone during TTS playback"""
        audio = self.record_audio(duration, f"tts_test_{hash(phrase)}", 
                                f"Mic during TTS: '{phrase[:30]}...'")
        
        # Analyze if we're picking up the TTS
        rms = np.sqrt(np.mean(audio ** 2))
        print(f"   📊 Microphone RMS during TTS: {rms:.6f}")
        
        # Quick VAD check
        if hasattr(self, 'vad') and self.vad:
            vad_result = self.vad.detect_voice_activity(audio)
            print(f"   📊 VAD detected voice during TTS: {vad_result.has_voice}")
            print(f"   📊 VAD confidence during TTS: {vad_result.confidence:.3f}")
    
    def optimize_vad_thresholds(self):
        """Suggest optimal VAD thresholds based on analysis"""
        print("\n⚙️ Optimizing VAD Thresholds...")
        
        if not self.analysis_results:
            print("❌ No analysis data available. Run tests first.")
            return
        
        # Analyze voice vs noise characteristics
        noise_floor = self.analysis_results.get('silence', {}).get('voice_rms', 0)
        
        voice_levels = []
        for key in self.analysis_results:
            if key.startswith('voice_'):
                voice_levels.append(self.analysis_results[key].get('voice_rms', 0))
        
        if voice_levels:
            min_voice = min(voice_levels)
            avg_voice = np.mean(voice_levels)
            
            # Suggest threshold between noise floor and minimum voice
            suggested_threshold = noise_floor + (min_voice - noise_floor) * 0.3
            
            print(f"📊 Noise floor: {noise_floor:.6f}")
            print(f"📊 Min voice level: {min_voice:.6f}")
            print(f"📊 Avg voice level: {avg_voice:.6f}")
            print(f"🎯 Suggested VAD threshold: {suggested_threshold:.6f}")
            print(f"🎯 Current VAD threshold: 0.7 (confidence)")
        
        # Suggest optimal settings based on feedback ratios
        feedback_ratios = []
        for key in self.analysis_results:
            if 'feedback' in key:
                ratio = self.analysis_results[key].get('feedback_ratio', 0)
                feedback_ratios.append(ratio)
        
        if feedback_ratios:
            avg_feedback = np.mean(feedback_ratios)
            print(f"📊 Average feedback ratio: {avg_feedback:.4f}")
            
            if avg_feedback > 0.1:
                print("⚠️  High feedback detected - recommend:")
                print("   • Increase silence timeout (currently 3s)")
                print("   • Lower volume threshold for echo detection")
                print("   • Consider physical microphone repositioning")
            else:
                print("✅ Feedback levels acceptable")
    
    def generate_calibration_report(self):
        """Generate comprehensive calibration report"""
        print("\n📄 Generating Calibration Report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'device_info': {
                'microphone': 'Live Streamer CAM 513 (Device #2)',
                'sample_rate': self.sample_rate,
                'system': 'macOS'
            },
            'analysis_results': self.analysis_results,
            'recordings_summary': {
                name: {
                    'duration': data['duration'],
                    'timestamp': data['timestamp'].isoformat(),
                    'description': data['description']
                } for name, data in self.recordings.items()
            }
        }
        
        # Save report
        report_path = Path(__file__).parent / f"audio_calibration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Report saved: {report_path}")
        return report
    
    def plot_frequency_analysis(self):
        """Create frequency analysis plots"""
        print("\n📊 Creating Frequency Analysis Plots...")
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Audio Feedback Analysis')
        
        # Plot 1: Silence spectrum
        if 'silence' in self.recordings:
            silence = self.recordings['silence']['audio']
            freqs = fftfreq(len(silence), 1/self.sample_rate)[:len(silence)//2]
            fft_silence = np.abs(fft(silence))[:len(silence)//2]
            
            axes[0,0].semilogy(freqs, fft_silence)
            axes[0,0].set_title('Silence/Noise Floor Spectrum')
            axes[0,0].set_xlabel('Frequency (Hz)')
            axes[0,0].set_ylabel('Magnitude')
        
        # Plot 2: Voice spectra comparison
        voice_data = [(k, v) for k, v in self.recordings.items() if k.startswith('voice_')]
        if voice_data:
            for name, data in voice_data:
                audio = data['audio']
                freqs = fftfreq(len(audio), 1/self.sample_rate)[:len(audio)//2]
                fft_voice = np.abs(fft(audio))[:len(audio)//2]
                axes[0,1].semilogy(freqs, fft_voice, label=name)
            
            axes[0,1].set_title('Voice Spectra Comparison')
            axes[0,1].set_xlabel('Frequency (Hz)')
            axes[0,1].set_ylabel('Magnitude')
            axes[0,1].legend()
        
        # Plot 3: Feedback comparison
        feedback_data = [(k, v) for k, v in self.recordings.items() if 'feedback' in k]
        if feedback_data:
            for name, data in feedback_data:
                audio = data['audio']
                freqs = fftfreq(len(audio), 1/self.sample_rate)[:len(audio)//2]
                fft_feedback = np.abs(fft(audio))[:len(audio)//2]
                axes[1,0].semilogy(freqs, fft_feedback, label=name.replace('_feedback', ''))
            
            axes[1,0].set_title('Feedback Spectra')
            axes[1,0].set_xlabel('Frequency (Hz)')
            axes[1,0].set_ylabel('Magnitude')
            axes[1,0].legend()
        
        # Plot 4: RMS levels comparison
        rms_data = {}
        for name, analysis in self.analysis_results.items():
            if 'voice_rms' in analysis:
                rms_data[name] = analysis['voice_rms']
            elif 'feedback_rms' in analysis:
                rms_data[name] = analysis['feedback_rms']
        
        if rms_data:
            names = list(rms_data.keys())
            values = list(rms_data.values())
            axes[1,1].bar(names, values)
            axes[1,1].set_title('RMS Levels Comparison')
            axes[1,1].set_ylabel('RMS Level')
            axes[1,1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plot_path = Path(__file__).parent / f"audio_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(plot_path)
        print(f"✅ Plots saved: {plot_path}")
        plt.show()

async def main():
    """Main test sequence"""
    print("🎯 Audio Feedback Analyzer - Voice Interface Calibration Tool")
    print("=" * 60)
    
    analyzer = AudioFeedbackAnalyzer()
    await analyzer.initialize()
    
    while True:
        print("\n" + "=" * 60)
        print("🎛️ Audio Analysis Menu:")
        print("1. Generate test tones and analyze feedback")
        print("2. Test voice recognition at different distances")
        print("3. Test echo cancellation effectiveness")
        print("4. Optimize VAD thresholds")
        print("5. Generate calibration report")
        print("6. Create frequency analysis plots")
        print("7. Run complete analysis suite")
        print("8. Exit")
        
        choice = input("\nSelect test (1-8): ").strip()
        
        if choice == '1':
            analyzer.generate_test_tones()
        elif choice == '2':
            await analyzer.test_voice_recognition()
        elif choice == '3':
            analyzer.test_echo_cancellation_effectiveness()
        elif choice == '4':
            analyzer.optimize_vad_thresholds()
        elif choice == '5':
            analyzer.generate_calibration_report()
        elif choice == '6':
            analyzer.plot_frequency_analysis()
        elif choice == '7':
            print("🚀 Running complete analysis suite...")
            analyzer.generate_test_tones()
            await analyzer.test_voice_recognition()
            analyzer.test_echo_cancellation_effectiveness()
            analyzer.optimize_vad_thresholds()
            analyzer.generate_calibration_report()
            analyzer.plot_frequency_analysis()
            print("✅ Complete analysis finished!")
        elif choice == '8':
            print("👋 Exiting analyzer...")
            break
        else:
            print("❌ Invalid choice. Please select 1-8.")
    
    # Cleanup
    if analyzer.stt:
        analyzer.stt.cleanup()

if __name__ == "__main__":
    asyncio.run(main())