#!/usr/bin/env python3
"""
TTS vs Human Voice Analysis Comparison
Analyze the actual differences between macOS TTS and human voice
"""

import json
import numpy as np
from pathlib import Path
import statistics

def analyze_voice_patterns(report_path):
    """Analyze patterns in voice analysis report"""
    with open(report_path, 'r') as f:
        data = json.load(f)

    ai_files = []
    human_files = []

    for filename, analysis in data['files'].items():
        if 'error' not in analysis:
            features = analysis['features']
            if filename.startswith('ai_voice_'):
                ai_files.append(features)
            elif filename.startswith('always_listen_') or filename.startswith('click_record_'):
                human_files.append(features)

    print(f"📊 Analysis: {len(ai_files)} TTS samples, {len(human_files)} human samples")

    # Analyze key differentiating features
    features_to_compare = [
        'pitch_variation', 'energy_stability', 'spectral_stability',
        'rhythm_regularity', 'harmonicity', 'zcr_mean', 'zcr_std'
    ]

    print("\n🔍 FEATURE COMPARISON:")
    print(f"{'Feature':<20} {'TTS Mean':<12} {'Human Mean':<12} {'Difference':<12} {'Potential?'}")
    print("-" * 70)

    distinguishing_features = []

    for feature in features_to_compare:
        ai_values = [f.get(feature, 0) for f in ai_files if f.get(feature) is not None]
        human_values = [f.get(feature, 0) for f in human_files if f.get(feature) is not None]

        if ai_values and human_values:
            ai_mean = statistics.mean(ai_values)
            human_mean = statistics.mean(human_values)
            difference = abs(ai_mean - human_mean)

            # Consider features with significant difference (>0.05 or >20% relative)
            relative_diff = difference / max(abs(ai_mean), abs(human_mean), 0.001)
            potential = "YES" if (difference > 0.05 or relative_diff > 0.2) else "no"

            if potential == "YES":
                distinguishing_features.append({
                    'feature': feature,
                    'ai_mean': ai_mean,
                    'human_mean': human_mean,
                    'difference': difference,
                    'ai_values': ai_values,
                    'human_values': human_values
                })

            print(f"{feature:<20} {ai_mean:<12.3f} {human_mean:<12.3f} {difference:<12.3f} {potential}")

    print(f"\n🎯 DISTINGUISHING FEATURES FOUND: {len(distinguishing_features)}")

    if distinguishing_features:
        print("\n📋 RECOMMENDED NEW THRESHOLDS:")
        for feat in distinguishing_features:
            ai_mean = feat['ai_mean']
            human_mean = feat['human_mean']

            # Calculate threshold that separates them
            if ai_mean > human_mean:
                threshold = (ai_mean + human_mean) / 2
                condition = f"> {threshold:.3f}"
                print(f"  if features['{feat['feature']}'] {condition}: ai_indicators.append('{feat['feature']}_high')")
            else:
                threshold = (ai_mean + human_mean) / 2
                condition = f"< {threshold:.3f}"
                print(f"  if features['{feat['feature']}'] {condition}: ai_indicators.append('{feat['feature']}_low')")

    return distinguishing_features

if __name__ == "__main__":
    report_path = "/Users/mick/Developer/theeandme/audio_diagnostics/session_20250913_101946/voice_analysis_report.json"

    if Path(report_path).exists():
        features = analyze_voice_patterns(report_path)

        if not features:
            print("\n❌ NO CLEAR DISTINGUISHING FEATURES FOUND")
            print("🔬 Modern neural TTS is very sophisticated - may need different approach")
            print("💡 Consider: temporal patterns, formant analysis, or ensemble methods")
        else:
            print(f"\n✅ Found {len(features)} potential distinguishing features")
            print("🚀 Update voice_spectral_analyzer.py with new thresholds")
    else:
        print(f"❌ Report not found: {report_path}")