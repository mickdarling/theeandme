#!/usr/bin/env python3
"""
Gaze-Integrated Voice System Launcher 2025
One-click deployment script for the revolutionary multi-modal voice interface

DEPLOYMENT OPTIONS:
✅ Full system with real gaze detection (requires MediaPipe/OpenCV)
✅ Mock system for development (no camera required)
✅ Performance testing and validation
✅ System health monitoring
✅ Graceful shutdown handling
"""

import sys
import os
import subprocess
import threading
import time
import json
from pathlib import Path
from datetime import datetime

def check_dependencies():
    """Check if required dependencies are available"""
    dependencies = {
        'mediapipe': False,
        'opencv': False,
        'realtimestt': False,
        'flask': False,
        'flask_socketio': False
    }

    try:
        import mediapipe
        dependencies['mediapipe'] = True
    except ImportError:
        pass

    try:
        import cv2
        dependencies['opencv'] = True
    except ImportError:
        pass

    try:
        from RealtimeSTT import AudioToTextRecorder
        dependencies['realtimestt'] = True
    except ImportError:
        pass

    try:
        from flask import Flask
        dependencies['flask'] = True
    except ImportError:
        pass

    try:
        from flask_socketio import SocketIO
        dependencies['flask_socketio'] = True
    except ImportError:
        pass

    return dependencies

def check_system_status():
    """Check if the original voice interface is running"""
    try:
        import requests
        response = requests.get('http://localhost:8087', timeout=2)
        return True, "Original voice interface is running at localhost:8087"
    except:
        return False, "Port 8087 is available for gaze-integrated system"

def print_system_info():
    """Print comprehensive system information"""
    print("🧠⚡ GAZE-INTEGRATED ULTRA-FAST VOICE INTERFACE 2025")
    print("=" * 80)

    # Check dependencies
    deps = check_dependencies()
    print("📦 DEPENDENCY STATUS:")
    for dep, available in deps.items():
        status = "✅" if available else "❌"
        print(f"   {status} {dep}: {'Available' if available else 'Missing'}")

    # Check system status
    running, status_msg = check_system_status()
    print(f"\n🔍 SYSTEM STATUS:")
    print(f"   {status_msg}")

    # Determine deployment mode
    can_use_real_gaze = deps['mediapipe'] and deps['opencv']
    can_run_system = deps['realtimestt'] and deps['flask'] and deps['flask_socketio']

    print(f"\n🚀 DEPLOYMENT OPTIONS:")
    if can_run_system:
        if can_use_real_gaze:
            print("   ✅ Full System: Real gaze detection + ultra-fast voice processing")
        else:
            print("   🎭 Mock System: Simulated gaze detection + ultra-fast voice processing")
        print("   🧪 Test Suite: Comprehensive validation testing")
    else:
        print("   ❌ Cannot run system - missing critical dependencies")

    return {
        'dependencies': deps,
        'can_use_real_gaze': can_use_real_gaze,
        'can_run_system': can_run_system,
        'port_available': not running
    }

def install_dependencies():
    """Install missing dependencies"""
    print("\n📦 INSTALLING MISSING DEPENDENCIES...")

    # Core dependencies
    core_packages = [
        "flask",
        "flask-socketio",
        "numpy",
        "requests"
    ]

    # Optional but recommended for full functionality
    full_packages = [
        "mediapipe",
        "opencv-python"
    ]

    try:
        # Install core packages
        print("Installing core packages...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--break-system-packages"
        ] + core_packages, check=True)

        # Ask about full packages
        install_full = input("\nInstall MediaPipe and OpenCV for real gaze detection? (y/N): ").lower() == 'y'
        if install_full:
            print("Installing full packages (this may take a few minutes)...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--break-system-packages"
            ] + full_packages, check=True)

        print("✅ Dependencies installed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_system_tests():
    """Run comprehensive system tests"""
    print("\n🧪 RUNNING SYSTEM TESTS...")

    try:
        result = subprocess.run([
            sys.executable, "test_gaze_voice_integration.py"
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ All tests passed!")

            # Extract key metrics from output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'Overall Grade:' in line:
                    print(f"   {line.strip()}")
                elif 'System Status:' in line:
                    print(f"   {line.strip()}")

            return True
        else:
            print("❌ Some tests failed:")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def start_gaze_integrated_system(use_real_gaze=True):
    """Start the gaze-integrated voice system"""
    print(f"\n🚀 STARTING GAZE-INTEGRATED VOICE SYSTEM...")
    print(f"   Mode: {'Real Gaze Detection' if use_real_gaze else 'Mock Gaze Detection'}")
    print(f"   URL: http://localhost:8087")
    print(f"   Features: Multi-modal intent detection, ultra-fast processing")

    try:
        # Start the system
        subprocess.run([
            sys.executable, "gaze_integrated_ultra_fast_voice_interface.py"
        ], check=True)

    except KeyboardInterrupt:
        print("\n🛑 System shutdown requested by user")
    except Exception as e:
        print(f"❌ Error starting system: {e}")

def show_usage_guide():
    """Show usage guide for the integrated system"""
    print("\n📖 GAZE-INTEGRATED VOICE INTERFACE USAGE GUIDE")
    print("=" * 60)
    print("🧠 REVOLUTIONARY FEATURES:")
    print("   • Real-time gaze detection determines intent")
    print("   • Natural 'thinking aloud' filtering")
    print("   • Ultra-fast pattern matching preserved")
    print("   • Context-aware TTS responses")
    print("   • Complete performance monitoring")

    print("\n👁️ INTENT MATRIX:")
    print("   Looking AT screen + Command   → ✅ EXECUTE (immediate action)")
    print("   Looking AWAY + Command        → 🔇 IGNORE (thinking aloud)")
    print("   Looking AT screen + Question  → 💬 RESPOND (full conversation)")
    print("   Looking AWAY + Comment        → 🔹 MINIMAL (brief acknowledgment)")

    print("\n🎤 EXAMPLE COMMANDS:")
    print("   While looking at screen:")
    print("     • 'Open Chrome' → Opens browser")
    print("     • 'What time is it?' → Full conversational response")
    print("   While looking away:")
    print("     • 'Open Chrome' → Ignored (thinking aloud)")
    print("     • 'That's interesting' → Brief acknowledgment")

    print("\n🌐 WEB INTERFACE FEATURES:")
    print("   • Real-time gaze state display")
    print("   • Intent decision visualization")
    print("   • Performance metrics monitoring")
    print("   • Pipeline timing analysis")

    print("\n💡 TIPS FOR BEST EXPERIENCE:")
    print("   • Ensure good lighting for gaze detection")
    print("   • Position camera at eye level")
    print("   • Speak naturally - system adapts to your behavior")
    print("   • Watch the web interface for real-time feedback")

def interactive_menu():
    """Interactive menu for system deployment"""
    while True:
        print("\n🎯 GAZE-INTEGRATED VOICE SYSTEM LAUNCHER")
        print("=" * 50)
        print("1. 🔍 Check System Status")
        print("2. 📦 Install Dependencies")
        print("3. 🧪 Run System Tests")
        print("4. 🚀 Start Full System (Real Gaze Detection)")
        print("5. 🎭 Start Mock System (Development Mode)")
        print("6. 📖 Show Usage Guide")
        print("7. ❌ Exit")

        try:
            choice = input("\nSelect option (1-7): ").strip()

            if choice == '1':
                system_info = print_system_info()

            elif choice == '2':
                if install_dependencies():
                    input("\nPress Enter to return to menu...")

            elif choice == '3':
                if run_system_tests():
                    input("\nPress Enter to return to menu...")

            elif choice == '4':
                system_info = print_system_info()
                if system_info['can_run_system']:
                    if not system_info['can_use_real_gaze']:
                        print("⚠️  Warning: MediaPipe/OpenCV not available, will use mock gaze detection")
                        if input("Continue anyway? (y/N): ").lower() != 'y':
                            continue
                    start_gaze_integrated_system(use_real_gaze=system_info['can_use_real_gaze'])
                else:
                    print("❌ Cannot start system - missing dependencies (option 2 to install)")

            elif choice == '5':
                system_info = print_system_info()
                if system_info['can_run_system']:
                    start_gaze_integrated_system(use_real_gaze=False)
                else:
                    print("❌ Cannot start system - missing dependencies (option 2 to install)")

            elif choice == '6':
                show_usage_guide()
                input("\nPress Enter to return to menu...")

            elif choice == '7':
                print("👋 Thank you for using the Gaze-Integrated Voice Interface!")
                break

            else:
                print("❌ Invalid option. Please select 1-7.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main launcher function"""
    # Check if running with command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == 'status':
            print_system_info()
        elif command == 'test':
            run_system_tests()
        elif command == 'start':
            start_gaze_integrated_system(use_real_gaze=True)
        elif command == 'mock':
            start_gaze_integrated_system(use_real_gaze=False)
        elif command == 'install':
            install_dependencies()
        elif command == 'guide':
            show_usage_guide()
        else:
            print("❌ Unknown command. Available commands:")
            print("   status  - Check system status")
            print("   test    - Run system tests")
            print("   start   - Start full system")
            print("   mock    - Start mock system")
            print("   install - Install dependencies")
            print("   guide   - Show usage guide")
    else:
        # Interactive mode
        interactive_menu()

if __name__ == "__main__":
    main()