#!/usr/bin/env python3
"""
Voice Performance Analyzer
Specialized analysis tools for voice pipeline performance data

Provides detailed analysis of:
- Component performance bottlenecks
- User experience metrics
- System load impact
- Performance trends and patterns
"""

import json
import statistics
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class BottleneckAnalysis:
    """Analysis of performance bottlenecks in the voice pipeline"""
    component_name: str
    average_time_ms: float
    max_time_ms: float
    percentage_of_total: float
    slowest_operations: List[str]
    optimization_potential: str  # "high", "medium", "low"


@dataclass
class UserExperienceMetrics:
    """User experience metrics for voice interactions"""
    response_time_rating: str  # "excellent", "good", "poor"
    consistency_score: float  # 0-1, based on response time variance
    reliability_score: float  # 0-1, based on success rate
    overall_ux_rating: str  # "excellent", "good", "needs_improvement"


class VoicePerformanceAnalyzer:
    """Advanced analysis of voice pipeline performance data"""

    def __init__(self, test_results_dir: str = None):
        self.results_dir = Path(test_results_dir) if test_results_dir else None
        self.performance_thresholds = {
            "excellent": 500,  # <500ms
            "good": 1000,      # <1000ms
            "acceptable": 2000, # <2000ms
        }

        # User experience thresholds
        self.ux_thresholds = {
            "response_time_excellent": 600,
            "response_time_good": 1200,
            "consistency_threshold": 0.3,  # CV threshold for consistency
            "reliability_threshold": 0.9   # Success rate threshold
        }

    def load_test_data(self, test_file: str) -> List[Dict]:
        """Load test data from comprehensive test results"""
        if self.results_dir:
            file_path = self.results_dir / test_file
        else:
            file_path = Path(test_file)

        with open(file_path, 'r') as f:
            data = json.load(f)

        return data

    def analyze_component_bottlenecks(self, test_results: List[Dict]) -> List[BottleneckAnalysis]:
        """Identify performance bottlenecks in pipeline components"""

        # Extract timing data for each component
        stt_times = []
        processing_times = []
        tts_times = []
        total_times = []

        for result in test_results:
            if isinstance(result, dict) and 'results' in result:
                # Handle scenario results
                for test in result['results']:
                    if hasattr(test, 'stt_time_ms'):
                        stt_times.append(test.stt_time_ms)
                        processing_times.append(test.processing_time_ms)
                        tts_times.append(test.tts_time_ms)
                        total_times.append(test.total_response_time_ms)
            else:
                # Handle direct test results
                if hasattr(result, 'stt_time_ms'):
                    stt_times.append(result.stt_time_ms)
                    processing_times.append(result.processing_time_ms)
                    tts_times.append(result.tts_time_ms)
                    total_times.append(result.total_response_time_ms)

        if not total_times:
            return []

        avg_total = statistics.mean(total_times)

        # Analyze each component
        bottlenecks = []

        if stt_times:
            avg_stt = statistics.mean(stt_times)
            max_stt = max(stt_times)
            stt_percentage = (avg_stt / avg_total) * 100

            # Determine optimization potential
            if avg_stt > 800:  # High STT time
                opt_potential = "high"
            elif avg_stt > 400:
                opt_potential = "medium"
            else:
                opt_potential = "low"

            bottlenecks.append(BottleneckAnalysis(
                component_name="Speech-to-Text (STT)",
                average_time_ms=avg_stt,
                max_time_ms=max_stt,
                percentage_of_total=stt_percentage,
                slowest_operations=self._find_slowest_stt_operations(test_results),
                optimization_potential=opt_potential
            ))

        if processing_times:
            avg_processing = statistics.mean(processing_times)
            max_processing = max(processing_times)
            processing_percentage = (avg_processing / avg_total) * 100

            if avg_processing > 1000:
                opt_potential = "high"
            elif avg_processing > 500:
                opt_potential = "medium"
            else:
                opt_potential = "low"

            bottlenecks.append(BottleneckAnalysis(
                component_name="Semantic Processing",
                average_time_ms=avg_processing,
                max_time_ms=max_processing,
                percentage_of_total=processing_percentage,
                slowest_operations=self._find_slowest_processing_operations(test_results),
                optimization_potential=opt_potential
            ))

        if tts_times:
            avg_tts = statistics.mean(tts_times)
            max_tts = max(tts_times)
            tts_percentage = (avg_tts / avg_total) * 100

            if avg_tts > 600:
                opt_potential = "high"
            elif avg_tts > 300:
                opt_potential = "medium"
            else:
                opt_potential = "low"

            bottlenecks.append(BottleneckAnalysis(
                component_name="Text-to-Speech (TTS)",
                average_time_ms=avg_tts,
                max_time_ms=max_tts,
                percentage_of_total=tts_percentage,
                slowest_operations=self._find_slowest_tts_operations(test_results),
                optimization_potential=opt_potential
            ))

        # Sort by percentage of total time (biggest bottlenecks first)
        bottlenecks.sort(key=lambda x: x.percentage_of_total, reverse=True)

        return bottlenecks

    def _find_slowest_stt_operations(self, test_results: List[Dict]) -> List[str]:
        """Find the slowest STT operations"""
        slow_operations = []

        for result in test_results:
            if isinstance(result, dict) and 'results' in result:
                for test in result['results']:
                    if hasattr(test, 'stt_time_ms') and test.stt_time_ms > 1000:
                        slow_operations.append(f"{test.test_command} ({test.stt_time_ms:.0f}ms)")
            elif hasattr(result, 'stt_time_ms') and result.stt_time_ms > 1000:
                slow_operations.append(f"{result.test_command} ({result.stt_time_ms:.0f}ms)")

        return slow_operations[:5]  # Top 5 slowest

    def _find_slowest_processing_operations(self, test_results: List[Dict]) -> List[str]:
        """Find the slowest processing operations"""
        slow_operations = []

        for result in test_results:
            if isinstance(result, dict) and 'results' in result:
                for test in result['results']:
                    if hasattr(test, 'processing_time_ms') and test.processing_time_ms > 1500:
                        slow_operations.append(f"{test.test_command} ({test.processing_time_ms:.0f}ms)")
            elif hasattr(result, 'processing_time_ms') and result.processing_time_ms > 1500:
                slow_operations.append(f"{result.test_command} ({result.processing_time_ms:.0f}ms)")

        return slow_operations[:5]

    def _find_slowest_tts_operations(self, test_results: List[Dict]) -> List[str]:
        """Find the slowest TTS operations"""
        slow_operations = []

        for result in test_results:
            if isinstance(result, dict) and 'results' in result:
                for test in result['results']:
                    if hasattr(test, 'tts_time_ms') and test.tts_time_ms > 800:
                        slow_operations.append(f"{test.test_command} ({test.tts_time_ms:.0f}ms)")
            elif hasattr(result, 'tts_time_ms') and result.tts_time_ms > 800:
                slow_operations.append(f"{result.test_command} ({result.tts_time_ms:.0f}ms)")

        return slow_operations[:5]

    def calculate_user_experience_metrics(self, test_results: List[Dict]) -> UserExperienceMetrics:
        """Calculate user experience metrics"""

        # Extract response times and success rates
        response_times = []
        success_count = 0
        total_count = 0

        for result in test_results:
            if isinstance(result, dict) and 'results' in result:
                for test in result['results']:
                    if hasattr(test, 'total_response_time_ms'):
                        response_times.append(test.total_response_time_ms)
                        if hasattr(test, 'overall_success') and test.overall_success:
                            success_count += 1
                        total_count += 1
            elif hasattr(result, 'total_response_time_ms'):
                response_times.append(result.total_response_time_ms)
                if hasattr(result, 'overall_success') and result.overall_success:
                    success_count += 1
                total_count += 1

        if not response_times:
            return UserExperienceMetrics(
                response_time_rating="unknown",
                consistency_score=0.0,
                reliability_score=0.0,
                overall_ux_rating="unknown"
            )

        # Response time rating
        avg_response_time = statistics.mean(response_times)
        if avg_response_time <= self.ux_thresholds["response_time_excellent"]:
            response_rating = "excellent"
        elif avg_response_time <= self.ux_thresholds["response_time_good"]:
            response_rating = "good"
        else:
            response_rating = "poor"

        # Consistency score (based on coefficient of variation)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        cv = std_dev / avg_response_time if avg_response_time > 0 else 0
        consistency_score = max(0, 1 - (cv / self.ux_thresholds["consistency_threshold"]))

        # Reliability score
        reliability_score = success_count / total_count if total_count > 0 else 0

        # Overall UX rating
        if (response_rating == "excellent" and
            consistency_score >= 0.8 and
            reliability_score >= self.ux_thresholds["reliability_threshold"]):
            overall_rating = "excellent"
        elif (response_rating in ["excellent", "good"] and
              consistency_score >= 0.6 and
              reliability_score >= 0.8):
            overall_rating = "good"
        else:
            overall_rating = "needs_improvement"

        return UserExperienceMetrics(
            response_time_rating=response_rating,
            consistency_score=consistency_score,
            reliability_score=reliability_score,
            overall_ux_rating=overall_rating
        )

    def compare_processor_performance(self, baseline_results: List[Dict],
                                    ultra_fast_results: List[Dict]) -> Dict[str, Any]:
        """Compare performance between standard and ultra-fast processors"""

        def extract_metrics(results):
            times = []
            successes = 0
            total = 0

            for result in results:
                if isinstance(result, dict) and 'results' in result:
                    for test in result['results']:
                        if hasattr(test, 'total_response_time_ms'):
                            times.append(test.total_response_time_ms)
                            if hasattr(test, 'overall_success') and test.overall_success:
                                successes += 1
                            total += 1
                elif hasattr(result, 'total_response_time_ms'):
                    times.append(result.total_response_time_ms)
                    if hasattr(result, 'overall_success') and result.overall_success:
                        successes += 1
                    total += 1

            return {
                'times': times,
                'avg_time': statistics.mean(times) if times else 0,
                'min_time': min(times) if times else 0,
                'max_time': max(times) if times else 0,
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                'success_rate': successes / total if total > 0 else 0,
                'total_tests': total
            }

        baseline_metrics = extract_metrics(baseline_results)
        ultra_fast_metrics = extract_metrics(ultra_fast_results)

        # Calculate improvements
        time_improvement = 0
        if baseline_metrics['avg_time'] > 0:
            time_improvement = ((baseline_metrics['avg_time'] - ultra_fast_metrics['avg_time']) /
                              baseline_metrics['avg_time']) * 100

        consistency_improvement = 0
        if baseline_metrics['std_dev'] > 0:
            baseline_cv = baseline_metrics['std_dev'] / baseline_metrics['avg_time']
            ultra_fast_cv = ultra_fast_metrics['std_dev'] / ultra_fast_metrics['avg_time'] if ultra_fast_metrics['avg_time'] > 0 else 0
            consistency_improvement = ((baseline_cv - ultra_fast_cv) / baseline_cv) * 100

        return {
            "baseline_performance": baseline_metrics,
            "ultra_fast_performance": ultra_fast_metrics,
            "improvements": {
                "speed_improvement_percent": time_improvement,
                "consistency_improvement_percent": consistency_improvement,
                "success_rate_change": ultra_fast_metrics['success_rate'] - baseline_metrics['success_rate']
            },
            "statistical_significance": self._calculate_statistical_significance(
                baseline_metrics['times'], ultra_fast_metrics['times']
            ),
            "recommendation": self._generate_processor_recommendation(time_improvement, consistency_improvement,
                                                                    ultra_fast_metrics['success_rate'])
        }

    def _calculate_statistical_significance(self, baseline_times: List[float],
                                          ultra_fast_times: List[float]) -> Dict[str, Any]:
        """Calculate statistical significance of performance differences"""
        if not baseline_times or not ultra_fast_times:
            return {"significant": False, "p_value": None, "method": "insufficient_data"}

        try:
            from scipy import stats

            # Perform t-test
            t_stat, p_value = stats.ttest_ind(baseline_times, ultra_fast_times)

            return {
                "significant": p_value < 0.05,
                "p_value": p_value,
                "t_statistic": t_stat,
                "method": "two_sample_t_test",
                "interpretation": "statistically_significant" if p_value < 0.05 else "not_significant"
            }
        except ImportError:
            # Fallback to simple comparison if scipy not available
            baseline_mean = statistics.mean(baseline_times)
            ultra_fast_mean = statistics.mean(ultra_fast_times)
            difference_pct = abs(baseline_mean - ultra_fast_mean) / baseline_mean * 100

            return {
                "significant": difference_pct > 10,  # Simple threshold
                "difference_percent": difference_pct,
                "method": "simple_threshold",
                "interpretation": "likely_significant" if difference_pct > 10 else "minimal_difference"
            }

    def _generate_processor_recommendation(self, speed_improvement: float,
                                         consistency_improvement: float,
                                         ultra_fast_success_rate: float) -> str:
        """Generate recommendation based on processor comparison"""

        if speed_improvement > 25 and ultra_fast_success_rate > 0.9:
            return "STRONGLY_RECOMMENDED: Ultra-fast processor shows significant improvements"
        elif speed_improvement > 15 and ultra_fast_success_rate > 0.8:
            return "RECOMMENDED: Ultra-fast processor shows good improvements"
        elif speed_improvement > 5 and ultra_fast_success_rate > 0.7:
            return "CONSIDER: Ultra-fast processor shows modest improvements"
        elif ultra_fast_success_rate < 0.7:
            return "NOT_RECOMMENDED: Ultra-fast processor has reliability issues"
        else:
            return "MINIMAL_BENEFIT: Ultra-fast processor shows little improvement"

    def generate_performance_report(self, analysis_data: Dict[str, Any]) -> str:
        """Generate comprehensive performance report"""

        report = []
        report.append("VOICE PIPELINE PERFORMANCE ANALYSIS REPORT")
        report.append("="*80)
        report.append("")

        # Test session info
        if 'test_session' in analysis_data:
            session = analysis_data['test_session']
            report.append(f"Test Session: {session.get('start_time', 'Unknown')} to {session.get('end_time', 'Unknown')}")
            report.append(f"Total Tests: {session.get('total_tests', 0)}")
            report.append("")

        # Performance comparison
        if 'performance_comparison' in analysis_data:
            comp = analysis_data['performance_comparison']
            report.append("PERFORMANCE COMPARISON")
            report.append("-"*40)
            report.append(f"Baseline Average Response Time: {comp.get('average_baseline_ms', 0):.0f}ms")
            report.append(f"Ultra-Fast Average Response Time: {comp.get('average_ultra_fast_ms', 0):.0f}ms")
            report.append(f"Speed Improvement: {comp.get('speed_improvement_percent', 0):.1f}%")
            report.append(f"Baseline Success Rate: {comp.get('baseline_success_rate', 0):.1f}%")
            report.append(f"Ultra-Fast Success Rate: {comp.get('ultra_fast_success_rate', 0):.1f}%")
            report.append("")

        # Recommendations
        if 'recommendations' in analysis_data:
            report.append("RECOMMENDATIONS")
            report.append("-"*40)
            for rec in analysis_data['recommendations']:
                report.append(f"• {rec}")
            report.append("")

        # System info
        if 'system_info' in analysis_data:
            info = analysis_data['system_info']
            report.append("SYSTEM CONFIGURATION")
            report.append("-"*40)
            report.append(f"STT Available: {info.get('stt_available', False)}")
            report.append(f"Semantic Parser Available: {info.get('semantic_parser_available', False)}")
            report.append(f"Ollama Model: {info.get('ollama_model', 'Unknown')}")
            report.append("")

        return "\n".join(report)

    def export_metrics_csv(self, test_results: List[Dict], output_file: str):
        """Export detailed metrics to CSV for further analysis"""

        rows = []
        for result in test_results:
            if isinstance(result, dict) and 'results' in result:
                for test in result['results']:
                    if hasattr(test, 'test_id'):
                        rows.append({
                            'test_id': test.test_id,
                            'command': test.test_command,
                            'category': test.test_category,
                            'processor': test.processor_used,
                            'stt_time_ms': test.stt_time_ms,
                            'processing_time_ms': test.processing_time_ms,
                            'tts_time_ms': test.tts_time_ms,
                            'total_time_ms': test.total_response_time_ms,
                            'success': test.overall_success,
                            'meets_target': test.meets_target,
                            'response_class': test.response_speed_class
                        })

        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(output_file, index=False)
            print(f"📊 Metrics exported to: {output_file}")
        else:
            print("⚠️  No data to export")


def main():
    """Example usage of the performance analyzer"""
    analyzer = VoicePerformanceAnalyzer()

    print("🔍 Voice Performance Analyzer")
    print("="*50)
    print("This tool analyzes voice pipeline performance data")
    print("Run comprehensive_voice_pipeline_tester.py first to generate test data")
    print("")
    print("Example analysis capabilities:")
    print("• Component bottleneck identification")
    print("• User experience metrics calculation")
    print("• Processor performance comparison")
    print("• Statistical significance testing")
    print("• Performance trend analysis")


if __name__ == "__main__":
    main()