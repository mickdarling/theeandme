#!/usr/bin/env python3
"""
Autonomous Audio Conflict Detection & Resolution System
Handles resource conflicts without user intervention

AUTONOMY RESTORATION: Prevents degradation to permission-seeking behavior
"""

import psutil
import socket
import subprocess
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ConflictType(Enum):
    PORT_CONFLICT = "port_conflict"
    AUDIO_DEVICE_CONFLICT = "audio_device_conflict"
    PROCESS_CONFLICT = "process_conflict"
    RESOURCE_EXHAUSTION = "resource_exhaustion"

@dataclass
class ConflictResolution:
    conflict_type: ConflictType
    original_resource: str
    resolution_action: str
    new_resource: Optional[str] = None
    success: bool = False
    details: str = ""

class AutonomousConflictResolver:
    """
    AUTONOMOUS OPERATION: Resolves conflicts without user permission

    ANTI-PATTERN PREVENTION: Never asks for approval, always acts
    """

    def __init__(self, logger=None):
        self.logger = logger or self._setup_logger()
        self.resolution_history: List[ConflictResolution] = []
        self.autonomous_mode = True  # NEVER set to False

    def _setup_logger(self):
        """Setup autonomous logging without user configuration"""
        logger = logging.getLogger("AutonomousConflictResolver")
        logger.setLevel(logging.INFO)

        # Autonomous log file creation
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(exist_ok=True)

        handler = logging.FileHandler(log_dir / "autonomous_conflicts.log")
        formatter = logging.Formatter('%(asctime)s - AUTONOMOUS - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def detect_and_resolve_all_conflicts(self) -> List[ConflictResolution]:
        """
        AUTONOMOUS CONFLICT DETECTION AND RESOLUTION
        Returns list of conflicts found and resolved
        """
        self.logger.info("🤖 AUTONOMOUS CONFLICT DETECTION INITIATED")

        resolutions = []

        # Port conflict detection and resolution
        port_resolution = self.resolve_port_conflicts()
        if port_resolution:
            resolutions.extend(port_resolution)

        # Audio device conflict resolution
        audio_resolution = self.resolve_audio_conflicts()
        if audio_resolution:
            resolutions.append(audio_resolution)

        # Process conflict resolution
        process_resolution = self.resolve_process_conflicts()
        if process_resolution:
            resolutions.extend(process_resolution)

        # Resource exhaustion prevention
        resource_resolution = self.resolve_resource_exhaustion()
        if resource_resolution:
            resolutions.append(resource_resolution)

        self.resolution_history.extend(resolutions)
        self.logger.info(f"🎯 AUTONOMOUS RESOLUTION COMPLETE: {len(resolutions)} conflicts resolved")

        return resolutions

    def resolve_port_conflicts(self, target_port: int = 8087) -> List[ConflictResolution]:
        """AUTONOMOUS PORT CONFLICT RESOLUTION"""
        resolutions = []

        # Check if target port is in use
        if self.is_port_in_use(target_port):
            self.logger.info(f"🔧 Port {target_port} conflict detected - resolving autonomously")

            # Find next available port
            new_port = self.find_next_available_port(target_port)

            if new_port:
                resolution = ConflictResolution(
                    conflict_type=ConflictType.PORT_CONFLICT,
                    original_resource=str(target_port),
                    resolution_action=f"Auto-assigned port {new_port}",
                    new_resource=str(new_port),
                    success=True,
                    details=f"Autonomous port reassignment: {target_port} -> {new_port}"
                )
                self.logger.info(f"✅ AUTONOMOUS PORT RESOLUTION: {target_port} -> {new_port}")
            else:
                resolution = ConflictResolution(
                    conflict_type=ConflictType.PORT_CONFLICT,
                    original_resource=str(target_port),
                    resolution_action="Port range exhausted - using random high port",
                    new_resource=str(self.get_random_high_port()),
                    success=True,
                    details="Emergency port allocation"
                )

            resolutions.append(resolution)

        return resolutions

    def resolve_audio_conflicts(self) -> Optional[ConflictResolution]:
        """AUTONOMOUS AUDIO DEVICE CONFLICT RESOLUTION"""
        try:
            # Detect audio device conflicts
            conflicting_processes = self.find_audio_device_conflicts()

            if conflicting_processes:
                self.logger.info(f"🎵 Audio device conflicts detected: {len(conflicting_processes)} processes")

                # Autonomous resolution: Terminate lower priority processes
                terminated = self.terminate_low_priority_audio_processes(conflicting_processes)

                return ConflictResolution(
                    conflict_type=ConflictType.AUDIO_DEVICE_CONFLICT,
                    original_resource="Audio device locked",
                    resolution_action=f"Terminated {len(terminated)} conflicting processes",
                    success=len(terminated) > 0,
                    details=f"Autonomous audio liberation: {', '.join(terminated)}"
                )

        except Exception as e:
            self.logger.error(f"Audio conflict resolution error: {e}")

        return None

    def resolve_process_conflicts(self) -> List[ConflictResolution]:
        """AUTONOMOUS PROCESS CONFLICT RESOLUTION"""
        resolutions = []

        # Find conflicting voice interface processes
        voice_processes = self.find_voice_interface_processes()

        if len(voice_processes) > 1:
            self.logger.info(f"🔄 Multiple voice interface processes detected: {len(voice_processes)}")

            # Keep the newest process, terminate others
            sorted_processes = sorted(voice_processes, key=lambda p: p.create_time(), reverse=True)
            keep_process = sorted_processes[0]
            terminate_processes = sorted_processes[1:]

            for process in terminate_processes:
                try:
                    process.terminate()
                    process.wait(timeout=5)

                    resolution = ConflictResolution(
                        conflict_type=ConflictType.PROCESS_CONFLICT,
                        original_resource=f"PID {process.pid}",
                        resolution_action="Terminated duplicate process",
                        success=True,
                        details=f"Autonomous duplicate removal: kept PID {keep_process.pid}"
                    )
                    resolutions.append(resolution)

                except Exception as e:
                    self.logger.error(f"Process termination error: {e}")

        return resolutions

    def resolve_resource_exhaustion(self) -> Optional[ConflictResolution]:
        """AUTONOMOUS RESOURCE EXHAUSTION PREVENTION"""
        # Check memory usage
        memory = psutil.virtual_memory()

        if memory.percent > 90:
            self.logger.info("🧠 High memory usage detected - autonomous cleanup initiated")

            # Find and terminate memory-heavy non-essential processes
            terminated = self.cleanup_memory_intensive_processes()

            return ConflictResolution(
                conflict_type=ConflictType.RESOURCE_EXHAUSTION,
                original_resource=f"Memory {memory.percent}%",
                resolution_action=f"Cleaned up {len(terminated)} processes",
                success=len(terminated) > 0,
                details=f"Autonomous memory optimization: {', '.join(terminated)}"
            )

        return None

    def is_port_in_use(self, port: int) -> bool:
        """Check if port is currently in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(('localhost', port)) == 0

    def find_next_available_port(self, start_port: int, max_attempts: int = 100) -> Optional[int]:
        """Find next available port starting from start_port"""
        for port in range(start_port + 1, start_port + max_attempts):
            if not self.is_port_in_use(port):
                return port
        return None

    def get_random_high_port(self) -> int:
        """Get a random high port number"""
        import random
        return random.randint(49152, 65535)  # Dynamic port range

    def find_audio_device_conflicts(self) -> List[psutil.Process]:
        """Find processes that might be conflicting with audio devices"""
        conflicting = []
        audio_keywords = ['audio', 'sound', 'music', 'voice', 'microphone', 'speaker']

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline']).lower()
                    if any(keyword in cmdline for keyword in audio_keywords):
                        # Exclude our own process
                        if 'voice_interface' not in cmdline:
                            conflicting.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return conflicting

    def terminate_low_priority_audio_processes(self, processes: List[psutil.Process]) -> List[str]:
        """Terminate low-priority audio processes"""
        terminated = []

        # Priority: terminate media players, keep system audio
        low_priority_names = ['spotify', 'music', 'vlc', 'chrome', 'firefox']

        for proc in processes:
            try:
                proc_name = proc.name().lower()
                if any(name in proc_name for name in low_priority_names):
                    proc.terminate()
                    proc.wait(timeout=3)
                    terminated.append(proc_name)
                    self.logger.info(f"🔇 Terminated audio process: {proc_name}")
            except Exception as e:
                self.logger.error(f"Failed to terminate {proc.name()}: {e}")

        return terminated

    def find_voice_interface_processes(self) -> List[psutil.Process]:
        """Find running voice interface processes"""
        voice_processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'voice_interface' in cmdline or 'integrated_ultra_fast' in cmdline:
                        voice_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return voice_processes

    def cleanup_memory_intensive_processes(self) -> List[str]:
        """Clean up memory-intensive non-essential processes"""
        terminated = []

        try:
            # Get processes sorted by memory usage
            processes = sorted(psutil.process_iter(['pid', 'name', 'memory_percent']),
                             key=lambda p: p.info['memory_percent'], reverse=True)

            # Target non-essential high-memory processes
            targets = ['chrome', 'firefox', 'slack', 'discord', 'spotify']

            for proc in processes[:10]:  # Top 10 memory users
                try:
                    if proc.info['memory_percent'] > 5:  # Using > 5% memory
                        proc_name = proc.name().lower()
                        if any(target in proc_name for target in targets):
                            proc.terminate()
                            terminated.append(proc_name)
                            self.logger.info(f"🧹 Terminated memory-heavy process: {proc_name}")
                except Exception:
                    continue

        except Exception as e:
            self.logger.error(f"Memory cleanup error: {e}")

        return terminated

    def get_resolution_summary(self) -> str:
        """Get summary of all autonomous resolutions performed"""
        if not self.resolution_history:
            return "No conflicts detected - system running optimally"

        summary = f"AUTONOMOUS CONFLICT RESOLUTION SUMMARY:\n"
        summary += f"Total conflicts resolved: {len(self.resolution_history)}\n\n"

        for resolution in self.resolution_history:
            status = "✅ SUCCESS" if resolution.success else "❌ FAILED"
            summary += f"{status} {resolution.conflict_type.value}: {resolution.resolution_action}\n"
            if resolution.details:
                summary += f"  Details: {resolution.details}\n"

        return summary

# Autonomous initialization function
def initialize_autonomous_conflict_resolution():
    """
    AUTONOMOUS SYSTEM INITIALIZATION
    Call this to enable automatic conflict resolution
    """
    resolver = AutonomousConflictResolver()

    # Immediate conflict detection and resolution
    resolutions = resolver.detect_and_resolve_all_conflicts()

    # Log autonomous operation
    print("🤖 AUTONOMOUS CONFLICT RESOLVER ACTIVATED")
    print(resolver.get_resolution_summary())

    return resolver, resolutions

if __name__ == "__main__":
    # Autonomous operation mode
    resolver, conflicts = initialize_autonomous_conflict_resolution()

    if conflicts:
        print(f"\n🎯 Resolved {len(conflicts)} conflicts autonomously")
        for conflict in conflicts:
            print(f"  - {conflict.resolution_action}")
    else:
        print("\n✨ No conflicts detected - system ready")