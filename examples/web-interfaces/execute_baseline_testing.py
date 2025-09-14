#!/usr/bin/env python3
"""
Baseline Performance Testing Execution Script
Automatically execute comprehensive voice pipeline testing to establish baseline performance

This script will:
1. Run the comprehensive testing framework
2. Generate baseline performance data
3. Test ultra-fast processor integration
4. Create detailed comparison analysis
5. Generate actionable recommendations

Run this to establish current system performance before optimizations.
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Import our testing components
from comprehensive_voice_pipeline_tester import VoicePipelineTester
from voice_performance_analyzer import VoicePerformanceAnalyzer
from real_time_voice_tester import RealTimeVoiceTester


class BaselineTestingExecutor:
    """Executes comprehensive baseline testing and analysis"""

    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(f"baseline_performance_{self.session_id}")
        self.output_dir.mkdir(exist_ok=True)

        print(f"🧪 Baseline Testing Executor initialized")
        print(f"📁 Output directory: {self.output_dir}")

    def check_system_prerequisites(self) -> Dict[str, bool]:
        """Check if all system components are ready for testing"""
        print("\n🔍 SYSTEM PREREQUISITES CHECK")
        print("="*50)

        results = {}

        # Check Ollama availability
        try:
            result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                models = json.loads(result.stdout).get('models', [])
                print(f"✅ Ollama: Running with {len(models)} models")
                results['ollama'] = True
                for model in models[:3]:  # Show first 3 models
                    print(f"   - {model.get('name', 'Unknown')}")
            else:
                print("❌ Ollama: Not responding")
                results['ollama'] = False
        except Exception:
            print("❌ Ollama: Connection failed")
            results['ollama'] = False

        # Check RealtimeSTT
        try:
            import RealtimeSTT
            print("✅ RealtimeSTT: Available")
            results['realtimestt'] = True
        except ImportError:
            print("⚠️  RealtimeSTT: Not available (will use mock STT)")
            results['realtimestt'] = False

        # Check macOS TTS
        try:
            result = subprocess.run(['say', '--voice=?'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                voices = len([line for line in result.stdout.split('\n') if line.strip()])
                print(f"✅ macOS TTS: Available with {voices} voices")
                results['tts'] = True
            else:
                print("❌ macOS TTS: Issues detected")
                results['tts'] = False
        except Exception:
            print("❌ macOS TTS: Not available")
            results['tts'] = False

        # Check Python dependencies
        required_packages = ['numpy', 'requests', 'flask', 'subprocess']
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            print(f"⚠️  Missing packages: {', '.join(missing_packages)}")
            results['dependencies'] = False
        else:
            print("✅ Python dependencies: All required packages available")
            results['dependencies'] = True

        # Overall readiness
        critical_components = ['ollama', 'tts', 'dependencies']
        ready = all(results.get(comp, False) for comp in critical_components)

        print(f"\n🎯 System Readiness: {'✅ READY' if ready else '⚠️  PARTIAL'}")

        if not ready:
            print("\n📋 SETUP RECOMMENDATIONS:")
            if not results.get('ollama'):
                print("• Install and start Ollama: https://ollama.ai/")
                print("• Run: ollama pull llama3.1:latest")
            if not results.get('tts'):
                print("• Ensure macOS TTS is working: say 'hello'")
            if not results.get('dependencies'):
                print(f"• Install missing packages: pip install {' '.join(missing_packages)}")

        return results

    def run_comprehensive_mock_testing(self) -> Dict[str, Any]:
        """Run comprehensive testing with mock STT (no microphone required)"""
        print(f"\n📊 COMPREHENSIVE MOCK TESTING")
        print("="*60)
        print("Running full pipeline tests with simulated voice input")
        print("This establishes baseline performance without requiring live voice")

        try:
            # Initialize tester with our output directory
            tester = VoicePipelineTester(output_dir=str(self.output_dir / "comprehensive_tests"))

            # Run the full test suite
            results = tester.run_comprehensive_test_suite()

            print("\n✅ Comprehensive testing completed")
            return results

        except Exception as e:
            print(f"❌ Comprehensive testing failed: {e}")
            return {}

    def run_performance_analysis(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run detailed performance analysis on test results"""
        print(f"\n🔍 PERFORMANCE ANALYSIS")
        print("="*40)

        try:
            analyzer = VoicePerformanceAnalyzer()

            # Extract test data for analysis
            baseline_data = []
            ultra_fast_data = []

            if 'baseline_results' in test_results:
                for scenario_name, scenario_data in test_results['baseline_results'].items():
                    baseline_data.extend(scenario_data.get('results', []))

            if 'ultra_fast_results' in test_results:
                for scenario_name, scenario_data in test_results['ultra_fast_results'].items():
                    ultra_fast_data.extend(scenario_data.get('results', []))

            analysis_results = {}

            # Bottleneck analysis
            if baseline_data:
                print("🔧 Analyzing component bottlenecks...")
                bottlenecks = analyzer.analyze_component_bottlenecks(baseline_data)
                analysis_results['bottlenecks'] = bottlenecks

                print(f"   Found {len(bottlenecks)} performance bottlenecks")
                for bottleneck in bottlenecks[:3]:  # Show top 3
                    print(f"   - {bottleneck.component_name}: {bottleneck.average_time_ms:.0f}ms "
                          f"({bottleneck.percentage_of_total:.1f}% of total)")

            # User experience metrics
            if baseline_data:
                print("👤 Calculating user experience metrics...")
                ux_metrics = analyzer.calculate_user_experience_metrics(baseline_data)
                analysis_results['user_experience'] = ux_metrics

                print(f"   Response Rating: {ux_metrics.response_time_rating}")
                print(f"   Consistency: {ux_metrics.consistency_score:.2f}")
                print(f"   Reliability: {ux_metrics.reliability_score:.2f}")

            # Processor comparison
            if baseline_data and ultra_fast_data:
                print("⚡ Comparing processor performance...")
                comparison = analyzer.compare_processor_performance(baseline_data, ultra_fast_data)
                analysis_results['processor_comparison'] = comparison

                improvements = comparison.get('improvements', {})
                speed_improvement = improvements.get('speed_improvement_percent', 0)
                print(f"   Speed Improvement: {speed_improvement:.1f}%")
                print(f"   Recommendation: {comparison.get('recommendation', 'Unknown')}")

            # Save detailed analysis
            analysis_file = self.output_dir / "performance_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)

            print(f"💾 Analysis saved to: {analysis_file}")
            return analysis_results

        except Exception as e:
            print(f"❌ Performance analysis failed: {e}")
            return {}

    def generate_baseline_report(self, system_check: Dict[str, bool],
                                test_results: Dict[str, Any],
                                analysis_results: Dict[str, Any]) -> str:
        """Generate comprehensive baseline performance report"""

        print(f"\n📋 GENERATING BASELINE REPORT")
        print("="*40)

        report_lines = []
        report_lines.append("VOICE PIPELINE BASELINE PERFORMANCE REPORT")
        report_lines.append("="*80)
        report_lines.append("")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Session ID: {self.session_id}")
        report_lines.append("")

        # System Configuration
        report_lines.append("SYSTEM CONFIGURATION")
        report_lines.append("-"*40)
        for component, status in system_check.items():
            status_icon = "✅" if status else "❌"
            report_lines.append(f"{component.upper()}: {status_icon} {'Available' if status else 'Not Available'}")
        report_lines.append("")

        # Performance Summary
        if 'performance_comparison' in test_results:
            comp = test_results['performance_comparison']
            report_lines.append("PERFORMANCE SUMMARY")
            report_lines.append("-"*40)
            report_lines.append(f"Baseline Average Response: {comp.get('average_baseline_ms', 0):.0f}ms")
            report_lines.append(f"Ultra-Fast Average Response: {comp.get('average_ultra_fast_ms', 0):.0f}ms")
            report_lines.append(f"Speed Improvement: {comp.get('speed_improvement_percent', 0):.1f}%")
            report_lines.append(f"Baseline Success Rate: {comp.get('baseline_success_rate', 0):.1f}%")
            report_lines.append(f"Ultra-Fast Success Rate: {comp.get('ultra_fast_success_rate', 0):.1f}%")
            report_lines.append("")

        # Key Bottlenecks
        if 'bottlenecks' in analysis_results:
            bottlenecks = analysis_results['bottlenecks']
            report_lines.append("KEY PERFORMANCE BOTTLENECKS")
            report_lines.append("-"*40)
            for i, bottleneck in enumerate(bottlenecks[:3], 1):
                report_lines.append(f"{i}. {bottleneck.component_name}")
                report_lines.append(f"   Average Time: {bottleneck.average_time_ms:.0f}ms")
                report_lines.append(f"   % of Total: {bottleneck.percentage_of_total:.1f}%")
                report_lines.append(f"   Optimization Potential: {bottleneck.optimization_potential.upper()}")
                report_lines.append("")

        # User Experience
        if 'user_experience' in analysis_results:
            ux = analysis_results['user_experience']
            report_lines.append("USER EXPERIENCE METRICS")
            report_lines.append("-"*40)
            report_lines.append(f"Response Time Rating: {ux.response_time_rating.upper()}")
            report_lines.append(f"Consistency Score: {ux.consistency_score:.2f}/1.0")
            report_lines.append(f"Reliability Score: {ux.reliability_score:.2f}/1.0")
            report_lines.append(f"Overall UX Rating: {ux.overall_ux_rating.upper()}")
            report_lines.append("")

        # Recommendations
        recommendations = []
        if 'recommendations' in test_results:
            recommendations.extend(test_results['recommendations'])

        # Add analysis-based recommendations
        if 'user_experience' in analysis_results:
            ux = analysis_results['user_experience']
            if ux.response_time_rating == "poor":
                recommendations.append("🔧 Response times are slow - prioritize STT and processing optimization")
            if ux.reliability_score < 0.8:
                recommendations.append("🛠️  Reliability below 80% - investigate error handling and edge cases")

        if 'bottlenecks' in analysis_results:
            bottlenecks = analysis_results['bottlenecks']
            for bottleneck in bottlenecks[:2]:  # Top 2 bottlenecks
                if bottleneck.optimization_potential == "high":
                    recommendations.append(f"⚡ High optimization potential in {bottleneck.component_name} "
                                         f"({bottleneck.average_time_ms:.0f}ms average)")

        if recommendations:
            report_lines.append("RECOMMENDATIONS")
            report_lines.append("-"*40)
            for rec in recommendations:
                report_lines.append(f"• {rec}")
            report_lines.append("")

        # Next Steps
        report_lines.append("NEXT STEPS")
        report_lines.append("-"*40)
        report_lines.append("1. Review bottleneck analysis and optimize slowest components")
        report_lines.append("2. Run real-time testing with actual voice input for validation")
        report_lines.append("3. Compare ultra-fast processor performance in production environment")
        report_lines.append("4. Implement recommended optimizations")
        report_lines.append("5. Re-run baseline testing to measure improvements")
        report_lines.append("")

        report_lines.append("="*80)
        report_lines.append(f"Report generated by Voice Pipeline Testing Framework")
        report_lines.append(f"Output directory: {self.output_dir}")

        report_text = "\n".join(report_lines)

        # Save report
        report_file = self.output_dir / "baseline_performance_report.txt"
        with open(report_file, 'w') as f:
            f.write(report_text)

        print(f"📋 Baseline report saved to: {report_file}")
        return report_text

    def run_complete_baseline_testing(self) -> bool:
        """Run the complete baseline testing workflow"""
        print(f"🚀 COMPLETE VOICE PIPELINE BASELINE TESTING")
        print("="*80)
        print("This will establish comprehensive baseline performance metrics")
        print("for the voice automation pipeline before optimizations.")
        print("="*80)

        try:
            # Step 1: Check system prerequisites
            system_check = self.check_system_prerequisites()

            # Step 2: Run comprehensive testing
            print(f"\n🔄 Starting comprehensive testing...")
            test_results = self.run_comprehensive_mock_testing()

            if not test_results:
                print("❌ Testing failed - cannot continue")
                return False

            # Step 3: Run performance analysis
            analysis_results = self.run_performance_analysis(test_results)

            # Step 4: Generate baseline report
            report = self.generate_baseline_report(system_check, test_results, analysis_results)

            # Step 5: Display key findings
            print(f"\n📊 KEY BASELINE FINDINGS")
            print("="*50)

            if 'performance_comparison' in test_results:
                comp = test_results['performance_comparison']
                print(f"• Baseline Response Time: {comp.get('average_baseline_ms', 0):.0f}ms")
                print(f"• Ultra-Fast Response Time: {comp.get('average_ultra_fast_ms', 0):.0f}ms")
                print(f"• Potential Speed Improvement: {comp.get('speed_improvement_percent', 0):.1f}%")

            if 'user_experience' in analysis_results:
                ux = analysis_results['user_experience']
                print(f"• User Experience Rating: {ux.overall_ux_rating.upper()}")
                print(f"• System Reliability: {ux.reliability_score:.1%}")

            print(f"\n💾 All results saved to: {self.output_dir}")

            # Step 6: Next steps guidance
            print(f"\n📋 NEXT STEPS:")
            print("1. Review the detailed baseline report")
            print("2. Run real-time testing for live validation:")
            print("   python real_time_voice_tester.py")
            print("3. Implement optimizations based on bottleneck analysis")
            print("4. Compare before/after performance improvements")

            return True

        except KeyboardInterrupt:
            print("\n🛑 Testing interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Baseline testing failed: {e}")
            return False


def main():
    """Main execution function"""
    print("🧪 Voice Pipeline Baseline Testing Execution")
    print("="*60)
    print("This script will establish comprehensive baseline performance")
    print("metrics for your voice automation pipeline.")
    print("")

    # Confirmation
    proceed = input("Proceed with baseline testing? (y/N): ").strip().lower()
    if proceed != 'y':
        print("Testing cancelled.")
        return

    # Execute baseline testing
    executor = BaselineTestingExecutor()

    try:
        success = executor.run_complete_baseline_testing()

        if success:
            print(f"\n🎉 BASELINE TESTING COMPLETED SUCCESSFULLY!")
            print(f"📊 Results available in: {executor.output_dir}")
            print(f"🚀 Ready for optimization and improvement testing!")
        else:
            print(f"\n⚠️  Baseline testing completed with issues.")
            print(f"📋 Check logs and results in: {executor.output_dir}")

    except KeyboardInterrupt:
        print(f"\n🛑 Testing stopped by user")
        print(f"📁 Partial results may be available in: {executor.output_dir}")
    except Exception as e:
        print(f"\n❌ Testing execution failed: {e}")


if __name__ == "__main__":
    main()