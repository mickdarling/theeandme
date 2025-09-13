#!/usr/bin/env python3
"""
Voice Spectral Analyzer - Distinguish AI vs Human Voice
Based on user insight: "You can probably tell by listening to the voices in the recordings to say,
and using something like a spectral analysis to figure out the tone of voice"

This analyzes audio recordings to identify voice characteristics and distinguish between:
- AI synthetic voice (consistent tone, specific frequency patterns)
- Human voice (natural variation, different pitch/timbre)
"""

import numpy as np
import librosa
import matplotlib.pyplot as plt
from scipy import signal
from pathlib import Path
import json
from datetime import datetime

class VoiceSpectralAnalyzer:
    """Analyze audio recordings to distinguish AI vs Human voice"""

    def __init__(self):
        self.sample_rate = 16000
        self.ai_voice_profile = None
        self.human_voice_profile = None

    def extract_voice_features(self, audio_path: str) -> dict:
        """Extract comprehensive voice features from audio file"""
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)

            # Remove silence
            y_trimmed, _ = librosa.effects.trim(y, top_db=20)

            if len(y_trimmed) == 0:
                return {"error": "No voice detected"}

            features = {}

            # 1. Fundamental Frequency (Pitch) Analysis
            f0 = librosa.yin(y_trimmed, fmin=80, fmax=400)  # Human voice range
            f0_clean = f0[f0 > 0]  # Remove unvoiced frames

            if len(f0_clean) > 0:
                features['pitch_mean'] = float(np.mean(f0_clean))
                features['pitch_std'] = float(np.std(f0_clean))
                features['pitch_range'] = float(np.max(f0_clean) - np.min(f0_clean))
                features['pitch_variation'] = features['pitch_std'] / features['pitch_mean']
            else:
                features['pitch_mean'] = 0
                features['pitch_std'] = 0
                features['pitch_range'] = 0
                features['pitch_variation'] = 0

            # 2. Spectral Features
            stft = librosa.stft(y_trimmed)
            magnitude = np.abs(stft)

            # Spectral centroid (brightness)
            spectral_centroids = librosa.feature.spectral_centroid(y=y_trimmed, sr=sr)[0]
            features['spectral_centroid_mean'] = float(np.mean(spectral_centroids))
            features['spectral_centroid_std'] = float(np.std(spectral_centroids))

            # Spectral rolloff (energy distribution)
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y_trimmed, sr=sr)[0]
            features['spectral_rolloff_mean'] = float(np.mean(spectral_rolloff))

            # Zero crossing rate (vocal roughness)
            zcr = librosa.feature.zero_crossing_rate(y_trimmed)[0]
            features['zcr_mean'] = float(np.mean(zcr))
            features['zcr_std'] = float(np.std(zcr))

            # 3. MFCC Features (voice timbre)
            mfcc = librosa.feature.mfcc(y=y_trimmed, sr=sr, n_mfcc=13)
            for i in range(13):
                features[f'mfcc_{i}_mean'] = float(np.mean(mfcc[i]))
                features[f'mfcc_{i}_std'] = float(np.std(mfcc[i]))

            # 4. Harmonic-Percussive Separation
            y_harmonic, y_percussive = librosa.effects.hpss(y_trimmed)
            harmonic_energy = np.sum(y_harmonic**2)
            percussive_energy = np.sum(y_percussive**2)
            total_energy = harmonic_energy + percussive_energy

            features['harmonicity'] = float(harmonic_energy / total_energy) if total_energy > 0 else 0

            # 5. Voice Stability Metrics (AI voices are more consistent)
            # Energy stability
            rms = librosa.feature.rms(y=y_trimmed)[0]
            features['energy_mean'] = float(np.mean(rms))
            features['energy_std'] = float(np.std(rms))
            features['energy_stability'] = 1.0 - (features['energy_std'] / max(features['energy_mean'], 1e-8))

            # Spectral stability
            features['spectral_stability'] = 1.0 - (features['spectral_centroid_std'] / max(features['spectral_centroid_mean'], 1e-8))

            # 6. Prosody Features
            # Tempo and rhythm
            onset_frames = librosa.onset.onset_detect(y=y_trimmed, sr=sr)
            if len(onset_frames) > 1:
                onset_times = librosa.frames_to_time(onset_frames, sr=sr)
                onset_intervals = np.diff(onset_times)
                features['rhythm_regularity'] = 1.0 - (np.std(onset_intervals) / max(np.mean(onset_intervals), 1e-8))
            else:
                features['rhythm_regularity'] = 1.0  # Very regular (no variation)

            # Audio duration and timing
            features['duration'] = float(len(y_trimmed) / sr)
            features['voice_activity_ratio'] = float(len(y_trimmed) / len(y)) if len(y) > 0 else 0

            return features

        except Exception as e:
            return {"error": str(e)}

    def analyze_voice_type(self, features: dict) -> dict:
        """Analyze features to determine if voice is likely AI or human"""
        if "error" in features:
            return features

        ai_indicators = []
        human_indicators = []

        # Updated thresholds based on macOS TTS vs Human analysis
        # macOS TTS has lower pitch variation (more consistent)
        if features.get('pitch_variation', 0) < 0.337:
            ai_indicators.append('pitch_variation_low')
        else:
            human_indicators.append('natural_pitch_variation')

        # macOS TTS has higher energy stability
        if features.get('energy_stability', 0) > 0.365:
            ai_indicators.append('energy_stability_high')
        else:
            human_indicators.append('natural_energy_variation')

        # macOS TTS has lower spectral stability
        if features.get('spectral_stability', 0) < 0.455:
            ai_indicators.append('spectral_stability_low')
        else:
            human_indicators.append('natural_spectral_variation')

        # macOS TTS has higher rhythm regularity
        if features.get('rhythm_regularity', 0) > 0.040:
            ai_indicators.append('rhythm_regularity_high')
        else:
            human_indicators.append('natural_rhythm_variation')

        # macOS TTS has lower harmonicity
        harmonicity = features.get('harmonicity', 0)
        if harmonicity < 0.359:
            ai_indicators.append('harmonicity_low')
        else:
            human_indicators.append('natural_harmonicity')

        # macOS TTS has higher zero-crossing rate
        if features.get('zcr_mean', 0) > 0.132:
            ai_indicators.append('zcr_mean_high')
        else:
            human_indicators.append('natural_zcr_mean')

        # macOS TTS has higher zero-crossing rate std
        if features.get('zcr_std', 0) > 0.111:
            ai_indicators.append('zcr_std_high')
        else:
            human_indicators.append('natural_zcr_std')

        # Calculate confidence scores
        total_indicators = len(ai_indicators) + len(human_indicators)
        if total_indicators > 0:
            ai_confidence = len(ai_indicators) / total_indicators
            human_confidence = len(human_indicators) / total_indicators
        else:
            ai_confidence = 0.5
            human_confidence = 0.5

        # Determine likely voice type
        if ai_confidence > 0.6:
            voice_type = "AI_SYNTHETIC"
        elif human_confidence > 0.6:
            voice_type = "HUMAN_NATURAL"
        else:
            voice_type = "UNCERTAIN"

        return {
            'voice_type': voice_type,
            'ai_confidence': ai_confidence,
            'human_confidence': human_confidence,
            'ai_indicators': ai_indicators,
            'human_indicators': human_indicators,
            'features': features
        }

    def analyze_audio_file(self, audio_path: str) -> dict:
        """Complete analysis of an audio file"""
        print(f"🔍 Analyzing: {audio_path}")

        features = self.extract_voice_features(audio_path)
        if "error" in features:
            print(f"❌ Error: {features['error']}")
            return features

        analysis = self.analyze_voice_type(features)

        # Summary
        voice_type = analysis['voice_type']
        ai_conf = analysis['ai_confidence']
        human_conf = analysis['human_confidence']

        print(f"🎤 Voice Type: {voice_type}")
        print(f"🤖 AI Confidence: {ai_conf:.1%}")
        print(f"👤 Human Confidence: {human_conf:.1%}")
        print(f"📊 Key Features:")
        print(f"   Pitch Variation: {features.get('pitch_variation', 0):.3f}")
        print(f"   Energy Stability: {features.get('energy_stability', 0):.3f}")
        print(f"   Spectral Stability: {features.get('spectral_stability', 0):.3f}")
        print(f"   Rhythm Regularity: {features.get('rhythm_regularity', 0):.3f}")
        print()

        return analysis

    def batch_analyze_directory(self, directory_path: str) -> dict:
        """Analyze all audio files in a directory"""
        directory = Path(directory_path)
        if not directory.exists():
            return {"error": f"Directory not found: {directory_path}"}

        results = {
            'directory': str(directory),
            'timestamp': datetime.now().isoformat(),
            'files': {},
            'summary': {
                'total_files': 0,
                'ai_voices': 0,
                'human_voices': 0,
                'uncertain': 0,
                'errors': 0
            }
        }

        # Find all audio files
        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(directory.glob(f"*{ext}"))

        print(f"🔍 Found {len(audio_files)} audio files in {directory}")

        for audio_file in sorted(audio_files):
            analysis = self.analyze_audio_file(str(audio_file))
            results['files'][audio_file.name] = analysis

            # Update summary
            results['summary']['total_files'] += 1

            if 'error' in analysis:
                results['summary']['errors'] += 1
            elif analysis['voice_type'] == 'AI_SYNTHETIC':
                results['summary']['ai_voices'] += 1
            elif analysis['voice_type'] == 'HUMAN_NATURAL':
                results['summary']['human_voices'] += 1
            else:
                results['summary']['uncertain'] += 1

        return results

    def save_analysis_report(self, results: dict, output_path: str):
        """Save analysis results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Analysis report saved: {output_path}")

# Test the analyzer
if __name__ == "__main__":
    print("🎤 Voice Spectral Analyzer - AI vs Human Voice Detection")
    print("Based on spectral analysis of voice characteristics")
    print()

    analyzer = VoiceSpectralAnalyzer()

    # Test on recent session directories
    test_directories = [
        "/Users/mick/Developer/theeandme/audio_diagnostics",
    ]

    for test_dir in test_directories:
        if Path(test_dir).exists():
            print(f"📁 Analyzing directory: {test_dir}")

            # Find session directories
            base_dir = Path(test_dir)
            session_dirs = [d for d in base_dir.iterdir() if d.is_dir() and 'session' in d.name]

            for session_dir in sorted(session_dirs)[-3:]:  # Analyze last 3 sessions
                print(f"\n🔍 Session: {session_dir.name}")
                results = analyzer.batch_analyze_directory(str(session_dir))

                if 'summary' in results:
                    summary = results['summary']
                    print(f"📊 Summary: {summary['ai_voices']} AI, {summary['human_voices']} Human, {summary['uncertain']} Uncertain, {summary['errors']} Errors")

                    # Save report
                    report_path = session_dir / "voice_analysis_report.json"
                    analyzer.save_analysis_report(results, str(report_path))

            break  # Only analyze first existing directory
        else:
            print(f"❌ Directory not found: {test_dir}")

    print("✅ Voice spectral analysis complete!")