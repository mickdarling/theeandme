#!/usr/bin/env python3
"""
Camera-Based Attention Detection - Use camera to improve voice detection

This tool uses computer vision to:
1. Detect when user is facing the camera/microphone
2. Correlate visual attention with voice activity
3. Improve voice detection by using visual cues
4. Reduce false positives when user is not present
"""

import asyncio
import sys
import cv2
import time
import numpy as np
from pathlib import Path
from datetime import datetime
import threading
import queue
import json

# Add src to path for imports  
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from audio.vad import SileroVAD

class CameraAttentionDetector:
    def __init__(self):
        self.camera = None
        self.face_cascade = None
        self.eye_cascade = None
        self.sample_rate = 16000
        self.device_id = 2  # Audio device
        
        # Detection parameters
        self.face_detection_confidence = 0.3
        self.attention_score_threshold = 0.7
        self.face_size_threshold = 30  # Minimum face size
        
        # State tracking
        self.current_attention_score = 0.0
        self.face_detected = False
        self.eyes_detected = False
        self.face_direction = "unknown"
        self.distance_estimate = "unknown"
        
        # History for smoothing
        self.attention_history = []
        self.history_size = 10
        
        # Audio integration
        self.vad = None
        self.audio_queue = queue.Queue()
        self.is_monitoring = False
        
    async def initialize(self):
        """Initialize camera and audio systems"""
        print("🎥 Initializing Camera Attention Detection...")
        
        # Initialize camera
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            raise Exception("Could not open camera")
        
        # Set camera properties for better detection
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Load OpenCV cascades
        cascade_path = cv2.data.haarcascades
        self.face_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cascade_path + 'haarcascade_eye.xml')
        
        if self.face_cascade.empty() or self.eye_cascade.empty():
            raise Exception("Could not load face/eye detection cascades")
        
        print("✅ Camera initialized")
        
        # Initialize VAD for audio correlation
        vad_config = {
            'sample_rate': self.sample_rate,
            'vad_threshold': 0.7,
            'min_speech_duration_ms': 300,
            'silence_timeout_seconds': 2.0
        }
        
        self.vad = SileroVAD(vad_config)
        await self.vad.initialize()
        print("✅ VAD initialized")
        
        print("✅ Camera Attention Detector ready!")
    
    def detect_face_and_attention(self, frame):
        """Detect face and estimate attention level"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(self.face_size_threshold, self.face_size_threshold)
        )
        
        attention_score = 0.0
        face_info = None
        
        if len(faces) > 0:
            self.face_detected = True
            
            # Use the largest face (closest person)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            # Calculate face info
            face_center_x = x + w // 2
            face_center_y = y + h // 2
            face_area = w * h
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2
            
            # Estimate distance based on face size
            if face_area > 15000:
                self.distance_estimate = "close"
            elif face_area > 8000:
                self.distance_estimate = "normal"
            else:
                self.distance_estimate = "far"
            
            # Calculate attention score based on face position
            center_deviation_x = abs(face_center_x - frame_center_x) / frame_center_x
            center_deviation_y = abs(face_center_y - frame_center_y) / frame_center_y
            
            # Face centered in frame = higher attention
            position_score = 1.0 - (center_deviation_x + center_deviation_y) / 2
            
            # Detect eyes within face region
            face_roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(face_roi_gray, scaleFactor=1.1, minNeighbors=3)
            
            eye_score = 0.0
            if len(eyes) >= 2:
                self.eyes_detected = True
                eye_score = 0.5  # Bonus for eye detection
            else:
                self.eyes_detected = False
            
            # Determine face direction based on position
            if center_deviation_x < 0.2 and center_deviation_y < 0.2:
                self.face_direction = "forward"
                direction_score = 1.0
            elif center_deviation_x < 0.4:
                self.face_direction = "slightly_turned"
                direction_score = 0.7
            else:
                self.face_direction = "turned_away"
                direction_score = 0.3
            
            # Combined attention score
            attention_score = (position_score * 0.4 + 
                             direction_score * 0.4 + 
                             eye_score * 0.2)
            
            face_info = {
                'x': x, 'y': y, 'w': w, 'h': h,
                'center': (face_center_x, face_center_y),
                'area': face_area,
                'distance': self.distance_estimate,
                'direction': self.face_direction,
                'eyes_detected': self.eyes_detected
            }
            
        else:
            self.face_detected = False
            self.eyes_detected = False
            self.face_direction = "not_detected"
            self.distance_estimate = "unknown"
        
        # Smooth attention score with history
        self.attention_history.append(attention_score)
        if len(self.attention_history) > self.history_size:
            self.attention_history.pop(0)
        
        self.current_attention_score = np.mean(self.attention_history)
        
        return self.current_attention_score, face_info
    
    def draw_attention_overlay(self, frame, attention_score, face_info):
        """Draw attention detection overlay"""
        height, width = frame.shape[:2]
        
        # Draw face rectangle if detected
        if face_info:
            x, y, w, h = face_info['x'], face_info['y'], face_info['w'], face_info['h']
            
            # Color based on attention score
            if attention_score > 0.8:
                color = (0, 255, 0)  # Green - high attention
            elif attention_score > 0.5:
                color = (0, 255, 255)  # Yellow - medium attention
            else:
                color = (0, 0, 255)  # Red - low attention
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Draw face center
            center = face_info['center']
            cv2.circle(frame, center, 5, color, -1)
            
            # Draw eyes if detected
            if face_info['eyes_detected']:
                cv2.putText(frame, "Eyes", (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Draw frame center reference
        center_x, center_y = width // 2, height // 2
        cv2.circle(frame, (center_x, center_y), 3, (255, 255, 255), -1)
        
        # Status overlay
        status_y = 30
        cv2.putText(frame, f"Attention: {attention_score:.2f}", (10, status_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        status_y += 30
        cv2.putText(frame, f"Face: {self.face_direction}", (10, status_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        status_y += 25
        cv2.putText(frame, f"Distance: {self.distance_estimate}", (10, status_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        status_y += 25
        cv2.putText(frame, f"Eyes: {'Yes' if self.eyes_detected else 'No'}", (10, status_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Attention score bar
        bar_width = 200
        bar_height = 20
        bar_x = width - bar_width - 10
        bar_y = 10
        
        # Background bar
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (50, 50, 50), -1)
        
        # Attention level bar
        fill_width = int(bar_width * attention_score)
        if attention_score > 0.7:
            bar_color = (0, 255, 0)
        elif attention_score > 0.4:
            bar_color = (0, 255, 255)  
        else:
            bar_color = (0, 0, 255)
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), 
                     bar_color, -1)
        
        # Threshold line
        threshold_x = bar_x + int(bar_width * self.attention_score_threshold)
        cv2.line(frame, (threshold_x, bar_y), (threshold_x, bar_y + bar_height), 
                (255, 255, 255), 2)
        
        return frame
    
    def live_attention_monitoring(self):
        """Live camera monitoring with attention detection"""
        print("🎥 Starting live attention monitoring...")
        print("👀 Look at the camera to test attention detection")
        print("Press 'q' to quit, 's' to save calibration data")
        
        calibration_data = []
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                print("❌ Could not read from camera")
                break
            
            # Detect attention
            attention_score, face_info = self.detect_face_and_attention(frame)
            
            # Draw overlay
            display_frame = self.draw_attention_overlay(frame, attention_score, face_info)
            
            # Store calibration data
            calibration_data.append({
                'timestamp': datetime.now().isoformat(),
                'attention_score': attention_score,
                'face_detected': self.face_detected,
                'face_direction': self.face_direction,
                'distance_estimate': self.distance_estimate,
                'eyes_detected': self.eyes_detected
            })
            
            # Limit calibration data size
            if len(calibration_data) > 1000:
                calibration_data.pop(0)
            
            # Display frame
            cv2.imshow('Camera Attention Detection', display_frame)
            
            # Handle keypresses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save calibration data
                save_path = Path(__file__).parent / f"attention_calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(save_path, 'w') as f:
                    json.dump(calibration_data, f, indent=2)
                print(f"\n✅ Calibration data saved: {save_path}")
        
        cv2.destroyAllWindows()
    
    def test_attention_correlation_with_audio(self):
        """Test correlation between visual attention and voice activity"""
        print("🎤👀 Testing attention-voice correlation...")
        print("Speak while looking at different directions")
        print("Press 'q' to quit")
        
        import sounddevice as sd
        
        correlation_data = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            
            try:
                audio_chunk = indata[:, 0].copy()
                self.audio_queue.put(audio_chunk)
            except Exception as e:
                print(f"Audio error: {e}")
        
        # Start audio stream
        with sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=1024,
            callback=audio_callback
        ):
            
            while True:
                # Get camera frame
                ret, frame = self.camera.read()
                if not ret:
                    break
                
                # Detect attention
                attention_score, face_info = self.detect_face_and_attention(frame)
                
                # Process audio if available
                audio_rms = 0.0
                vad_confidence = 0.0
                vad_decision = False
                
                try:
                    audio_chunk = self.audio_queue.get_nowait()
                    audio_rms = np.sqrt(np.mean(audio_chunk ** 2))
                    
                    # VAD processing
                    vad_result = self.vad.detect_voice_activity(audio_chunk)
                    vad_confidence = vad_result.confidence
                    vad_decision = vad_result.has_voice
                    
                except queue.Empty:
                    pass
                
                # Store correlation data
                correlation_data.append({
                    'timestamp': datetime.now().isoformat(),
                    'attention_score': attention_score,
                    'face_detected': self.face_detected,
                    'face_direction': self.face_direction,
                    'audio_rms': audio_rms,
                    'vad_confidence': vad_confidence,
                    'vad_decision': vad_decision
                })
                
                # Enhanced display with audio info
                display_frame = self.draw_attention_overlay(frame, attention_score, face_info)
                
                # Add audio status
                status_y = 200
                cv2.putText(display_frame, f"Audio RMS: {audio_rms:.4f}", (10, status_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                status_y += 25  
                cv2.putText(display_frame, f"VAD Conf: {vad_confidence:.2f}", (10, status_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                status_y += 25
                cv2.putText(display_frame, f"Voice: {'Yes' if vad_decision else 'No'}", (10, status_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                cv2.imshow('Attention-Audio Correlation', display_frame)
                
                # Handle quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        cv2.destroyAllWindows()
        
        # Save correlation data
        save_path = Path(__file__).parent / f"attention_audio_correlation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(save_path, 'w') as f:
            json.dump(correlation_data, f, indent=2)
        print(f"✅ Correlation data saved: {save_path}")
        
        # Analyze correlation
        self.analyze_attention_audio_correlation(correlation_data)
    
    def analyze_attention_audio_correlation(self, data):
        """Analyze correlation between attention and voice activity"""
        print("\n📊 Analyzing Attention-Audio Correlation...")
        
        if not data:
            print("❌ No data to analyze")
            return
        
        # Extract arrays for analysis
        attention_scores = [d['attention_score'] for d in data]
        vad_confidences = [d['vad_confidence'] for d in data]
        audio_rms = [d['audio_rms'] for d in data]
        vad_decisions = [d['vad_decision'] for d in data]
        
        # Calculate correlations
        attention_array = np.array(attention_scores)
        vad_array = np.array(vad_confidences)
        rms_array = np.array(audio_rms)
        
        # Correlation coefficients
        attention_vad_corr = np.corrcoef(attention_array, vad_array)[0, 1]
        attention_rms_corr = np.corrcoef(attention_array, rms_array)[0, 1]
        
        print(f"📊 Attention-VAD correlation: {attention_vad_corr:.3f}")
        print(f"📊 Attention-RMS correlation: {attention_rms_corr:.3f}")
        
        # Analyze attention vs voice activity
        high_attention_voice = sum(1 for d in data if d['attention_score'] > 0.7 and d['vad_decision'])
        high_attention_total = sum(1 for d in data if d['attention_score'] > 0.7)
        
        low_attention_voice = sum(1 for d in data if d['attention_score'] < 0.3 and d['vad_decision'])
        low_attention_total = sum(1 for d in data if d['attention_score'] < 0.3)
        
        print(f"📊 Voice activity with high attention: {high_attention_voice}/{high_attention_total}")
        print(f"📊 Voice activity with low attention: {low_attention_voice}/{low_attention_total}")
        
        # Recommendations
        if attention_vad_corr > 0.5:
            print("✅ Strong correlation between attention and voice - good for combined detection")
        elif attention_vad_corr > 0.3:
            print("🟡 Moderate correlation - attention can help improve detection accuracy") 
        else:
            print("❌ Weak correlation - attention detection may not significantly help")
    
    def cleanup(self):
        """Clean up resources"""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()

async def main():
    """Main interface"""
    print("🎥 Camera Attention Detection for Voice Interface")
    print("=" * 60)
    
    detector = CameraAttentionDetector()
    
    try:
        await detector.initialize()
        
        while True:
            print("\n" + "=" * 60)
            print("👀 Camera Attention Detection Menu:")
            print("1. Live attention monitoring")
            print("2. Test attention-audio correlation")
            print("3. Calibrate attention thresholds")
            print("4. Exit")
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                detector.live_attention_monitoring()
            elif choice == '2':
                detector.test_attention_correlation_with_audio()
            elif choice == '3':
                print("🎯 Attention threshold calibration:")
                print(f"Current threshold: {detector.attention_score_threshold}")
                new_threshold = input("Enter new threshold (0.0-1.0): ").strip()
                try:
                    detector.attention_score_threshold = float(new_threshold)
                    print(f"✅ Threshold set to: {detector.attention_score_threshold}")
                except ValueError:
                    print("❌ Invalid threshold value")
            elif choice == '4':
                print("👋 Exiting...")
                break
            else:
                print("❌ Invalid choice. Please select 1-4.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        detector.cleanup()

if __name__ == "__main__":
    asyncio.run(main())