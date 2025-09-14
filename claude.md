# DollhouseMCP Activation Script for Voice Automation Project

This file automatically activates all required DollhouseMCP elements for continued work on the voice automation and echo calibration improvements.

## Required Elements (20 total)

### Agent (1)
- Meta-Problem-Solver-v2 - Coordination and decision making

### Skills (4)
- Reality-Check-Validator - Prevent overstated claims and validate evidence
- voice-summary-narrator - Create voice-friendly session summaries
- Session-State-Tracker - Maintain session continuity
- Meta-Problem-Orchestration - Team coordination and process management

### Personas (12)
- Ruthless-Technical-Critic (v1.3-autonomous) - Evidence-based validation
- Technical Analyst - User experience analysis
- Full Stack Dev - Interface implementation
- Implementation-Gap-Detector - Missing UX pieces identification
- Debug Detective - Technical investigation
- Systems-Architecture-Critic - UX architecture review
- Loop-Prevention-Expert (v1.1-autonomous) - Prevent analysis loops
- QA Engineer - UX testing methodology
- Cross-Domain-Innovation-Catalyst - Creative UX solutions
- Document-Synchronization-Specialist - Session continuity
- Termination-Criteria-Specialist - Quality thresholds
- Feedback-Integration-Specialist - User input synthesis

### Templates (3)
- Meta-Problem-Session-Documentation - Session tracking
- Session-State-Report - Status reporting
- Claude-Desktop-Implementation-Guide - Implementation guidance

## Auto-Activation Commands

```
activate agent Meta-Problem-Solver-v2
activate skill Reality-Check-Validator
activate skill voice-summary-narrator
activate skill Session-State-Tracker
activate skill Meta-Problem-Orchestration
activate persona Ruthless-Technical-Critic
activate persona Technical Analyst
activate persona Full Stack Dev
activate persona Implementation-Gap-Detector
activate persona Debug Detective
activate persona Systems-Architecture-Critic
activate persona Loop-Prevention-Expert
activate persona QA Engineer
activate persona Cross-Domain-Innovation-Catalyst
activate persona Document-Synchronization-Specialist
activate persona Termination-Criteria-Specialist
activate persona Feedback-Integration-Specialist
activate template Meta-Problem-Session-Documentation
activate template Session-State-Report
activate template Claude-Desktop-Implementation-Guide
```

## Current Project Context

**Status**: Echo calibration investigation complete. Voice interface running at localhost:8087.

**Next Priority**: Present user experience improvement options for echo calibration based on session notes:

1. **Visual Calibration Indicator** - Web interface shows calibration progress
2. **Audio Optimization** - Lower TTS volume during voice input phases
3. **Accelerated Learning** - Faster echo blocker learning algorithm
4. **Smart Initialization** - Guided setup for optimal microphone positioning

**Key Files**:
- `integrated_ultra_fast_voice_interface.py` - Working voice interface (port 8087)
- `gaze_detection_foundation.py` - MultiModalIntentRouter implementation
- `docs/SESSION_NOTES_2025-09-13_ECHO_CALIBRATION_INVESTIGATION.md` - Investigation findings

**Mission**: Improve user experience for echo calibration based on user preference for "better user experience rather than a broken one."