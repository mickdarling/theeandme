#!/usr/bin/env python3
"""
Gaze Detection Web Interface
Complete working system for monitoring and testing gaze detection capabilities

This provides a real-time web interface for visualizing gaze detection status,
statistics, and testing the foundation for multi-modal voice interaction.
"""

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import json
import time
import threading
from gaze_detection_foundation import GazeDetectionEngine, GazeState

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'gaze_detection_2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global gaze detection engine
gaze_engine = None
monitoring_active = False
monitoring_thread = None


def start_gaze_monitoring():
    """Start continuous gaze monitoring for web interface"""
    global monitoring_active, gaze_engine
    monitoring_active = True

    while monitoring_active:
        try:
            if gaze_engine:
                context = gaze_engine.get_current_context()
                stats = gaze_engine.get_statistics()

                # Emit gaze status to web interface
                socketio.emit('gaze_update', {
                    'state': context.state.value,
                    'confidence': round(context.confidence, 3),
                    'duration': round(context.duration, 1),
                    'looking_probability': round(context.looking_at_screen_probability, 3),
                    'face_detected': context.face_detected,
                    'gaze_vector': {
                        'x': round(context.gaze_vector.x, 3),
                        'y': round(context.gaze_vector.y, 3),
                        'z': round(context.gaze_vector.z, 3),
                    },
                    'statistics': {
                        'total_detections': stats['total_detections'],
                        'looking_at_count': stats['looking_at_count'],
                        'looking_away_count': stats['looking_away_count'],
                        'uncertain_count': stats['uncertain_count'],
                        'no_face_count': stats['no_face_count'],
                        'average_confidence': round(stats['average_confidence'], 3),
                        'looking_at_percentage': round(stats.get('looking_at_percentage', 0), 1),
                        'looking_away_percentage': round(stats.get('looking_away_percentage', 0), 1),
                        'detection_accuracy': round(stats.get('detection_accuracy', 0), 1)
                    }
                })

            time.sleep(0.1)  # 10 FPS updates

        except Exception as e:
            print(f"⚠️  Gaze monitoring error: {e}")
            time.sleep(0.5)


@app.route('/')
def index():
    """Main gaze detection web interface"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👁️ Gaze Detection Foundation System</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            color: #333;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
            margin-top: 10px;
        }

        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .panel h2 {
            margin: 0 0 20px 0;
            color: #4a5568;
            font-size: 1.4em;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }

        .gaze-status {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            min-height: 150px;
        }

        .gaze-indicator {
            font-size: 4em;
            margin-bottom: 15px;
        }

        .gaze-state {
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .gaze-confidence {
            font-size: 1.2em;
            color: #666;
        }

        .at-screen { color: #48bb78; }
        .away { color: #ed8936; }
        .uncertain { color: #4299e1; }
        .no-face { color: #e53e3e; }
        .disabled { color: #a0aec0; }

        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }

        .metric:last-child {
            border-bottom: none;
        }

        .metric-label {
            font-weight: 500;
            color: #4a5568;
        }

        .metric-value {
            font-weight: 600;
            color: #2d3748;
            font-size: 1.1em;
        }

        .gaze-vector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }

        .vector-component {
            text-align: center;
            padding: 15px;
            background: #f7fafc;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
        }

        .vector-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }

        .vector-value {
            font-size: 1.3em;
            font-weight: 600;
            color: #2d3748;
        }

        .controls {
            margin-top: 20px;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-right: 10px;
            margin-bottom: 10px;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        button:active {
            transform: translateY(0);
        }

        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status-connected { background-color: #48bb78; }
        .status-disconnected { background-color: #e53e3e; }

        .footer {
            text-align: center;
            margin-top: 40px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9em;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .pulsing {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>👁️ Gaze Detection Foundation</h1>
        <div class="subtitle">
            Real-time gaze tracking for natural voice interaction
            <div style="margin-top: 10px;">
                <span class="status-indicator" id="connectionStatus"></span>
                <span id="connectionText">Connecting...</span>
            </div>
        </div>
    </div>

    <div class="dashboard">
        <div class="panel">
            <h2>🎯 Current Gaze Status</h2>
            <div class="gaze-status" id="gazeStatus">
                <div class="gaze-indicator pulsing" id="gazeIndicator">👁️</div>
                <div class="gaze-state" id="gazeState">Initializing...</div>
                <div class="gaze-confidence">Confidence: <span id="gazeConfidence">0%</span></div>
                <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    Duration: <span id="gazeDuration">0.0s</span>
                </div>
            </div>
        </div>

        <div class="panel">
            <h2>📊 Detection Statistics</h2>
            <div class="metric">
                <span class="metric-label">Total Detections</span>
                <span class="metric-value" id="totalDetections">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">Looking At Screen</span>
                <span class="metric-value">
                    <span id="lookingAtCount">0</span>
                    (<span id="lookingAtPercentage">0%</span>)
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">Looking Away</span>
                <span class="metric-value">
                    <span id="lookingAwayCount">0</span>
                    (<span id="lookingAwayPercentage">0%</span>)
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">Average Confidence</span>
                <span class="metric-value" id="averageConfidence">0.000</span>
            </div>
            <div class="metric">
                <span class="metric-label">Detection Accuracy</span>
                <span class="metric-value" id="detectionAccuracy">0%</span>
            </div>
        </div>

        <div class="panel">
            <h2>📐 Gaze Vector</h2>
            <div class="gaze-vector">
                <div class="vector-component">
                    <div class="vector-label">Horizontal (X)</div>
                    <div class="vector-value" id="gazeVectorX">0.000</div>
                </div>
                <div class="vector-component">
                    <div class="vector-label">Vertical (Y)</div>
                    <div class="vector-value" id="gazeVectorY">0.000</div>
                </div>
                <div class="vector-component">
                    <div class="vector-label">Depth (Z)</div>
                    <div class="vector-value" id="gazeVectorZ">0.000</div>
                </div>
            </div>
            <div class="metric" style="margin-top: 20px; padding-top: 20px; border-top: 2px solid #e2e8f0;">
                <span class="metric-label">Screen Probability</span>
                <span class="metric-value" id="screenProbability">0%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Face Detected</span>
                <span class="metric-value" id="faceDetected">❓</span>
            </div>
        </div>

        <div class="panel">
            <h2>🔧 System Controls</h2>
            <div class="controls">
                <button onclick="resetStatistics()">🔄 Reset Statistics</button>
                <button onclick="testGazeDetection()">🧪 Run Test Sequence</button>
                <button onclick="calibrateSystem()">⚙️ Calibrate System</button>
                <button onclick="toggleDetection()">⏯️ Toggle Detection</button>
            </div>

            <div style="margin-top: 20px; padding: 15px; background: #f7fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                <h4 style="margin: 0 0 10px 0; color: #4a5568;">Intent Detection Preview</h4>
                <div class="metric">
                    <span class="metric-label">Current Intent</span>
                    <span class="metric-value" id="currentIntent">UNKNOWN</span>
                </div>
                <div style="font-size: 0.9em; color: #666; margin-top: 10px;">
                    This shows how gaze state would affect voice command processing
                </div>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>Gaze Detection Foundation System v1.0 - Phase 1 Complete Working System</p>
        <p>Ready for integration with voice automation for natural intent detection</p>
    </div>

    <script>
        const socket = io();
        let isConnected = false;

        // Connection status handling
        socket.on('connect', function() {
            isConnected = true;
            updateConnectionStatus(true);
            console.log('Connected to gaze detection server');
        });

        socket.on('disconnect', function() {
            isConnected = false;
            updateConnectionStatus(false);
            console.log('Disconnected from gaze detection server');
        });

        // Gaze update handling
        socket.on('gaze_update', function(data) {
            updateGazeStatus(data);
            updateStatistics(data.statistics);
            updateGazeVector(data);
            updateIntentPreview(data.state);
        });

        function updateConnectionStatus(connected) {
            const statusIndicator = document.getElementById('connectionStatus');
            const statusText = document.getElementById('connectionText');

            if (connected) {
                statusIndicator.className = 'status-indicator status-connected';
                statusText.textContent = 'Connected';
            } else {
                statusIndicator.className = 'status-indicator status-disconnected';
                statusText.textContent = 'Disconnected';
            }
        }

        function updateGazeStatus(data) {
            const indicator = document.getElementById('gazeIndicator');
            const state = document.getElementById('gazeState');
            const confidence = document.getElementById('gazeConfidence');
            const duration = document.getElementById('gazeDuration');
            const status = document.getElementById('gazeStatus');

            // Update indicator icon and class
            const stateIcons = {
                'at_screen': '👀',
                'away': '👁️',
                'uncertain': '🤔',
                'no_face': '❓',
                'disabled': '🔇'
            };

            indicator.textContent = stateIcons[data.state] || '❔';
            state.textContent = data.state.toUpperCase().replace('_', ' ');
            confidence.textContent = `${(data.confidence * 100).toFixed(1)}%`;
            duration.textContent = `${data.duration}s`;

            // Update status class
            status.className = `gaze-status ${data.state.replace('_', '-')}`;

            // Add pulsing animation for active detection
            if (data.state === 'at_screen') {
                indicator.classList.add('pulsing');
            } else {
                indicator.classList.remove('pulsing');
            }
        }

        function updateStatistics(stats) {
            document.getElementById('totalDetections').textContent = stats.total_detections;
            document.getElementById('lookingAtCount').textContent = stats.looking_at_count;
            document.getElementById('lookingAwayCount').textContent = stats.looking_away_count;
            document.getElementById('lookingAtPercentage').textContent = `${stats.looking_at_percentage}%`;
            document.getElementById('lookingAwayPercentage').textContent = `${stats.looking_away_percentage}%`;
            document.getElementById('averageConfidence').textContent = stats.average_confidence;
            document.getElementById('detectionAccuracy').textContent = `${stats.detection_accuracy}%`;
        }

        function updateGazeVector(data) {
            document.getElementById('gazeVectorX').textContent = data.gaze_vector.x;
            document.getElementById('gazeVectorY').textContent = data.gaze_vector.y;
            document.getElementById('gazeVectorZ').textContent = data.gaze_vector.z;
            document.getElementById('screenProbability').textContent = `${(data.looking_probability * 100).toFixed(1)}%`;
            document.getElementById('faceDetected').textContent = data.face_detected ? '✅' : '❌';
        }

        function updateIntentPreview(gazeState) {
            const intent = document.getElementById('currentIntent');

            // Simulate intent detection logic
            let intentText = 'UNKNOWN';
            if (gazeState === 'at_screen') {
                intentText = 'READY TO INTERACT';
            } else if (gazeState === 'away') {
                intentText = 'IGNORE VOICE INPUT';
            } else if (gazeState === 'uncertain') {
                intentText = 'REQUEST CLARIFICATION';
            } else if (gazeState === 'no_face') {
                intentText = 'FACE NOT DETECTED';
            }

            intent.textContent = intentText;
        }

        // Control functions
        function resetStatistics() {
            socket.emit('reset_statistics');
            console.log('Statistics reset requested');
        }

        function testGazeDetection() {
            alert('Test sequence: Look at the screen for 3 seconds, then look away for 3 seconds. Watch the detection status change!');
        }

        function calibrateSystem() {
            alert('Calibration: Look directly at the center of the screen and click OK when ready.');
            socket.emit('calibrate_system');
        }

        function toggleDetection() {
            socket.emit('toggle_detection');
            console.log('Detection toggle requested');
        }

        // Initialize connection status as disconnected
        updateConnectionStatus(false);
    </script>
</body>
</html>
    ''')


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("🌐 Web interface client connected")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print("🌐 Web interface client disconnected")


@socketio.on('reset_statistics')
def handle_reset_statistics():
    """Handle statistics reset request"""
    global gaze_engine
    if gaze_engine:
        # Reinitialize statistics
        gaze_engine.stats = {
            'total_detections': 0,
            'looking_at_count': 0,
            'looking_away_count': 0,
            'uncertain_count': 0,
            'no_face_count': 0,
            'average_confidence': 0.0
        }
        print("📊 Gaze detection statistics reset")


@socketio.on('toggle_detection')
def handle_toggle_detection():
    """Handle detection toggle request"""
    global gaze_engine, monitoring_active
    if gaze_engine:
        monitoring_active = not monitoring_active
        status = "enabled" if monitoring_active else "disabled"
        print(f"🎥 Gaze detection {status}")


@socketio.on('calibrate_system')
def handle_calibrate_system():
    """Handle system calibration request"""
    print("⚙️ Gaze detection calibration requested")
    # In a real implementation, this would trigger calibration procedures
    emit('calibration_status', {'message': 'Calibration simulation complete'})


def main():
    """Main application entry point"""
    global gaze_engine, monitoring_thread

    print("🎯 GAZE DETECTION WEB INTERFACE")
    print("=" * 60)

    try:
        # Initialize gaze detection engine
        gaze_engine = GazeDetectionEngine()

        # Start monitoring thread
        monitoring_thread = threading.Thread(target=start_gaze_monitoring, daemon=True)
        monitoring_thread.start()

        print("🎥 Gaze detection engine initialized")
        print("🌐 Starting web interface...")
        print("📡 Access at: http://localhost:8088")
        print("👁️ Watch real-time gaze detection status")
        print()
        print("⚡ Features:")
        print("   - Real-time gaze state monitoring")
        print("   - Detection statistics and metrics")
        print("   - Gaze vector visualization")
        print("   - Intent detection preview")
        print("   - System controls and calibration")
        print()
        print("🧪 Test by looking at and away from the screen!")

        # Start Flask-SocketIO server
        socketio.run(app, host='0.0.0.0', port=8088, debug=False)

    except KeyboardInterrupt:
        print("\n⚠️  Shutting down gaze detection web interface...")
    except Exception as e:
        print(f"❌ Error starting gaze detection web interface: {e}")
    finally:
        # Cleanup
        global monitoring_active
        monitoring_active = False
        if gaze_engine:
            gaze_engine.shutdown()
        print("✅ Gaze detection web interface shutdown complete")


if __name__ == "__main__":
    main()