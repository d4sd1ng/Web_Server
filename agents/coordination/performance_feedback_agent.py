"""
Performance Feedback Agent
Real-time performance monitoring and system optimization for >90% win rate
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
import json

from agents.base_agent import BaseAgent


class PerformanceFeedbackAgent(BaseAgent):
    """
    Advanced Performance Feedback Agent
    Monitors system performance and optimizes for >90% win rate
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("performance_feedback", config)
        
        # Performance monitoring configuration
        self.target_win_rate = config.get('target_win_rate', 0.9)  # 90%
        self.performance_window = config.get('performance_window', 50)  # Last 50 trades
        self.optimization_frequency = config.get('optimization_frequency', 20)  # Every 20 trades
        self.min_trades_for_analysis = config.get('min_trades_for_analysis', 10)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Performance tracking
        self.trade_outcomes = []
        self.agent_performance = {}
        self.parameter_optimization_history = []
        self.system_health_metrics = {}
        
        # Optimization state
        self.current_win_rate = 0.0
        self.performance_trend = 'unknown'
        self.optimization_recommendations = []
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Performance Feedback Agent initialized for {self.market_type} - targeting {self.target_win_rate:.1%} win rate")
    
    def apply_market_specific_config(self):
        """Apply market-specific performance configuration"""
        if self.market_type == 'forex':
            # Forex: Lower target due to institutional competition
            self.target_win_rate = min(self.target_win_rate, 0.85)  # 85% for forex
            self.performance_sensitivity = 'high'
            self.session_performance_tracking = True
        elif self.market_type == 'crypto':
            # Crypto: Higher target possible due to inefficiencies
            self.target_win_rate = max(self.target_win_rate, 0.9)   # 90% for crypto
            self.performance_sensitivity = 'medium'
            self.volatility_performance_tracking = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process performance data and generate optimization recommendations
        
        Args:
            data: Dictionary containing performance data and trade outcomes
            
        Returns:
            Dictionary with performance analysis and optimization recommendations
        """
        try:
            action = data.get('action', 'analyze')
            
            if action == 'record_trade':
                return self.record_trade_outcome(data)
            elif action == 'analyze_performance':
                return self.analyze_system_performance(data)
            elif action == 'optimize_parameters':
                return self.optimize_system_parameters(data)
            elif action == 'get_recommendations':
                return self.get_optimization_recommendations(data)
            else:
                return self.get_performance_status()
                
        except Exception as e:
            self.logger.error(f"Error processing performance feedback data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def record_trade_outcome(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record trade outcome for performance tracking
        """
        required_fields = ['trade_id', 'symbol', 'direction', 'outcome', 'pnl', 'r_multiple']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for trade recording'}
        
        # Record trade outcome
        trade_record = {
            'trade_id': data['trade_id'],
            'symbol': data['symbol'],
            'direction': data['direction'],
            'outcome': data['outcome'],  # 'win' or 'loss'
            'pnl': data['pnl'],
            'r_multiple': data['r_multiple'],
            'timestamp': datetime.now(timezone.utc),
            'market_type': self.market_type,
            'confluence_score': data.get('confluence_score', 0),
            'pattern_count': data.get('pattern_count', 0),
            'ml_confidence': data.get('ml_confidence', 0),
            'regime': data.get('market_regime', 'unknown')
        }
        
        self.trade_outcomes.append(trade_record)
        
        # Limit history size
        if len(self.trade_outcomes) > 1000:
            self.trade_outcomes = self.trade_outcomes[-1000:]
        
        # Update current win rate
        self.update_current_win_rate()
        
        # Check if optimization is needed
        if len(self.trade_outcomes) % self.optimization_frequency == 0:
            self.trigger_optimization_analysis()
        
        self.logger.info(f"Trade recorded: {data['outcome']} - Current win rate: {self.current_win_rate:.1%}")
        
        return {
            'success': True,
            'current_win_rate': self.current_win_rate,
            'total_trades': len(self.trade_outcomes),
            'optimization_triggered': len(self.trade_outcomes) % self.optimization_frequency == 0
        }
    
    def update_current_win_rate(self):
        """Update current win rate calculation"""
        if not self.trade_outcomes:
            self.current_win_rate = 0.0
            return
        
        # Calculate win rate for recent trades
        recent_trades = self.trade_outcomes[-self.performance_window:] if len(self.trade_outcomes) >= self.performance_window else self.trade_outcomes
        
        wins = sum(1 for trade in recent_trades if trade['outcome'] == 'win')
        total = len(recent_trades)
        
        self.current_win_rate = wins / total if total > 0 else 0.0
        
        # Update performance trend
        if len(self.trade_outcomes) >= self.performance_window * 2:
            older_trades = self.trade_outcomes[-(self.performance_window * 2):-self.performance_window]
            older_wins = sum(1 for trade in older_trades if trade['outcome'] == 'win')
            older_win_rate = older_wins / len(older_trades) if older_trades else 0
            
            if self.current_win_rate > older_win_rate + 0.05:
                self.performance_trend = 'improving'
            elif self.current_win_rate < older_win_rate - 0.05:
                self.performance_trend = 'declining'
            else:
                self.performance_trend = 'stable'
    
    def analyze_system_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive system performance analysis
        """
        if len(self.trade_outcomes) < self.min_trades_for_analysis:
            return {'analysis': 'insufficient_data'}
        
        recent_trades = self.trade_outcomes[-self.performance_window:]
        
        # Overall performance metrics
        performance_analysis = {
            'current_win_rate': self.current_win_rate,
            'target_win_rate': self.target_win_rate,
            'performance_gap': self.target_win_rate - self.current_win_rate,
            'performance_trend': self.performance_trend,
            'total_trades_analyzed': len(recent_trades),
            'avg_r_multiple': np.mean([trade['r_multiple'] for trade in recent_trades]),
            'best_r_multiple': max([trade['r_multiple'] for trade in recent_trades]),
            'worst_r_multiple': min([trade['r_multiple'] for trade in recent_trades])
        }
        
        # Pattern performance analysis
        pattern_performance = self.analyze_pattern_performance(recent_trades)
        
        # ML performance analysis
        ml_performance = self.analyze_ml_performance(recent_trades)
        
        # Regime performance analysis
        regime_performance = self.analyze_regime_performance(recent_trades)
        
        # Identify performance issues
        performance_issues = self.identify_performance_issues(performance_analysis, pattern_performance, ml_performance)
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_performance': performance_analysis,
            'pattern_performance': pattern_performance,
            'ml_performance': ml_performance,
            'regime_performance': regime_performance,
            'performance_issues': performance_issues,
            'market_type': self.market_type,
            'optimization_needed': performance_analysis['performance_gap'] > 0.05
        }
    
    def analyze_pattern_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by pattern confluence levels"""
        if not trades:
            return {}
        
        # Group trades by confluence score
        confluence_groups = {
            'low_confluence': [t for t in trades if t.get('confluence_score', 0) < 5],
            'medium_confluence': [t for t in trades if 5 <= t.get('confluence_score', 0) < 8],
            'high_confluence': [t for t in trades if t.get('confluence_score', 0) >= 8]
        }
        
        performance_by_confluence = {}
        
        for group_name, group_trades in confluence_groups.items():
            if group_trades:
                wins = sum(1 for trade in group_trades if trade['outcome'] == 'win')
                win_rate = wins / len(group_trades)
                avg_r = np.mean([trade['r_multiple'] for trade in group_trades])
                
                performance_by_confluence[group_name] = {
                    'trade_count': len(group_trades),
                    'win_rate': win_rate,
                    'avg_r_multiple': avg_r,
                    'meets_target': win_rate >= self.target_win_rate
                }
        
        return performance_by_confluence
    
    def analyze_ml_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ML model performance contribution"""
        if not trades:
            return {}
        
        # Group trades by ML confidence levels
        confidence_groups = {
            'low_ml_confidence': [t for t in trades if t.get('ml_confidence', 0) < 0.7],
            'medium_ml_confidence': [t for t in trades if 0.7 <= t.get('ml_confidence', 0) < 0.9],
            'high_ml_confidence': [t for t in trades if t.get('ml_confidence', 0) >= 0.9]
        }
        
        ml_performance = {}
        
        for group_name, group_trades in confidence_groups.items():
            if group_trades:
                wins = sum(1 for trade in group_trades if trade['outcome'] == 'win')
                win_rate = wins / len(group_trades)
                avg_r = np.mean([trade['r_multiple'] for trade in group_trades])
                
                ml_performance[group_name] = {
                    'trade_count': len(group_trades),
                    'win_rate': win_rate,
                    'avg_r_multiple': avg_r,
                    'meets_target': win_rate >= self.target_win_rate
                }
        
        return ml_performance
    
    def analyze_regime_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by market regime"""
        if not trades:
            return {}
        
        # Group trades by regime
        regime_groups = {}
        for trade in trades:
            regime = trade.get('regime', 'unknown')
            if regime not in regime_groups:
                regime_groups[regime] = []
            regime_groups[regime].append(trade)
        
        regime_performance = {}
        
        for regime, regime_trades in regime_groups.items():
            if regime_trades:
                wins = sum(1 for trade in regime_trades if trade['outcome'] == 'win')
                win_rate = wins / len(regime_trades)
                avg_r = np.mean([trade['r_multiple'] for trade in regime_trades])
                
                regime_performance[regime] = {
                    'trade_count': len(regime_trades),
                    'win_rate': win_rate,
                    'avg_r_multiple': avg_r,
                    'meets_target': win_rate >= self.target_win_rate,
                    'regime_suitability': self.assess_regime_suitability(win_rate, avg_r)
                }
        
        return regime_performance
    
    def assess_regime_suitability(self, win_rate: float, avg_r: float) -> str:
        """Assess how suitable a regime is for trading"""
        if win_rate >= self.target_win_rate and avg_r >= 1.0:
            return 'excellent'
        elif win_rate >= self.target_win_rate * 0.8 and avg_r >= 0.8:
            return 'good'
        elif win_rate >= self.target_win_rate * 0.6:
            return 'fair'
        else:
            return 'poor'
    
    def identify_performance_issues(self, overall_performance: Dict[str, Any], 
                                   pattern_performance: Dict[str, Any], 
                                   ml_performance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify specific performance issues and root causes
        """
        issues = []
        
        # Overall win rate issue
        if overall_performance['current_win_rate'] < self.target_win_rate:
            gap = overall_performance['performance_gap']
            severity = 'critical' if gap > 0.2 else 'high' if gap > 0.1 else 'medium'
            
            issues.append({
                'type': 'win_rate_below_target',
                'severity': severity,
                'description': f"Win rate {overall_performance['current_win_rate']:.1%} below target {self.target_win_rate:.1%}",
                'gap': gap,
                'recommendations': self.get_win_rate_improvement_recommendations(gap)
            })
        
        # Pattern confluence issues
        if pattern_performance:
            for confluence_level, performance in pattern_performance.items():
                if not performance['meets_target']:
                    issues.append({
                        'type': 'pattern_confluence_underperforming',
                        'severity': 'medium',
                        'description': f"{confluence_level} win rate: {performance['win_rate']:.1%}",
                        'confluence_level': confluence_level,
                        'recommendations': ['increase_confluence_requirements', 'add_more_pattern_filters']
                    })
        
        # ML performance issues
        if ml_performance:
            for confidence_level, performance in ml_performance.items():
                if not performance['meets_target']:
                    issues.append({
                        'type': 'ml_confidence_underperforming',
                        'severity': 'high',
                        'description': f"{confidence_level} win rate: {performance['win_rate']:.1%}",
                        'confidence_level': confidence_level,
                        'recommendations': ['retrain_ml_models', 'increase_ml_confidence_threshold']
                    })
        
        # R-multiple issues
        if overall_performance['avg_r_multiple'] < 1.0:
            issues.append({
                'type': 'poor_risk_reward',
                'severity': 'high',
                'description': f"Average R-multiple {overall_performance['avg_r_multiple']:.2f} below 1.0",
                'recommendations': ['improve_exit_strategy', 'tighten_stop_losses', 'extend_profit_targets']
            })
        
        return issues
    
    def get_win_rate_improvement_recommendations(self, performance_gap: float) -> List[str]:
        """Get specific recommendations to improve win rate"""
        recommendations = []
        
        if performance_gap > 0.2:  # >20% gap - critical
            recommendations.extend([
                'increase_confluence_requirements_by_2',
                'raise_ml_confidence_threshold_to_0.95',
                'add_market_regime_filters',
                'implement_session_quality_gates',
                'reduce_trading_frequency_significantly'
            ])
        
        elif performance_gap > 0.1:  # >10% gap - high priority
            recommendations.extend([
                'increase_confluence_requirements_by_1',
                'raise_ml_confidence_threshold_to_0.9',
                'add_volume_confirmation_requirements',
                'implement_stricter_exit_criteria'
            ])
        
        else:  # <10% gap - fine tuning
            recommendations.extend([
                'fine_tune_pattern_weights',
                'optimize_exit_timing',
                'add_minor_confluence_filters'
            ])
        
        return recommendations
    
    def optimize_system_parameters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize system parameters based on performance analysis
        """
        if len(self.trade_outcomes) < self.min_trades_for_analysis:
            return {'optimization': 'insufficient_data'}
        
        # Analyze current performance
        performance_analysis = self.analyze_system_performance(data)
        
        # Generate parameter optimizations
        parameter_optimizations = self.generate_parameter_optimizations(performance_analysis)
        
        # Apply optimizations
        optimization_results = self.apply_parameter_optimizations(parameter_optimizations)
        
        # Record optimization
        optimization_record = {
            'timestamp': datetime.now(timezone.utc),
            'performance_before': performance_analysis['overall_performance'],
            'optimizations_applied': parameter_optimizations,
            'optimization_results': optimization_results,
            'market_type': self.market_type
        }
        
        self.parameter_optimization_history.append(optimization_record)
        
        return {
            'agent_id': self.agent_id,
            'optimization_completed': True,
            'optimizations_applied': len(parameter_optimizations),
            'expected_improvement': optimization_results.get('expected_improvement', 0),
            'optimization_record': optimization_record
        }
    
    def generate_parameter_optimizations(self, performance_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate specific parameter optimizations
        """
        optimizations = []
        overall_perf = performance_analysis['overall_performance']
        pattern_perf = performance_analysis.get('pattern_performance', {})
        ml_perf = performance_analysis.get('ml_performance', {})
        
        # Confluence requirement optimization
        if overall_perf['current_win_rate'] < self.target_win_rate:
            gap = overall_perf['performance_gap']
            
            if gap > 0.15:  # Large gap
                new_confluence_req = self.min_confluence_patterns[self.market_type] + 2
                optimizations.append({
                    'agent': 'confluence_coordinator',
                    'parameter': 'min_confluence_patterns',
                    'old_value': self.min_confluence_patterns[self.market_type],
                    'new_value': new_confluence_req,
                    'reason': f'Win rate {gap:.1%} below target - increasing confluence requirements'
                })
            
            elif gap > 0.05:  # Medium gap
                new_confluence_req = self.min_confluence_patterns[self.market_type] + 1
                optimizations.append({
                    'agent': 'confluence_coordinator',
                    'parameter': 'min_confluence_patterns',
                    'old_value': self.min_confluence_patterns[self.market_type],
                    'new_value': new_confluence_req,
                    'reason': f'Win rate {gap:.1%} below target - slight confluence increase'
                })
        
        # ML confidence threshold optimization
        if ml_perf and 'high_ml_confidence' in ml_perf:
            high_conf_perf = ml_perf['high_ml_confidence']
            if high_conf_perf['meets_target']:
                # High confidence ML performs well - raise threshold
                optimizations.append({
                    'agent': 'ml_ensemble',
                    'parameter': 'confidence_threshold',
                    'old_value': 0.9,
                    'new_value': 0.95,
                    'reason': 'High ML confidence shows good performance - raising threshold'
                })
        
        # Pattern weight optimization
        if pattern_perf:
            for confluence_level, perf in pattern_perf.items():
                if perf['meets_target'] and perf['trade_count'] >= 5:
                    # This confluence level works well - increase its weight
                    optimizations.append({
                        'agent': 'pattern_cluster',
                        'parameter': f'{confluence_level}_weight',
                        'old_value': 1.0,
                        'new_value': 1.2,
                        'reason': f'{confluence_level} shows {perf["win_rate"]:.1%} win rate'
                    })
        
        return optimizations
    
    def apply_parameter_optimizations(self, optimizations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply parameter optimizations to the system
        """
        applied_count = 0
        failed_count = 0
        
        for optimization in optimizations:
            try:
                # In a full implementation, this would update agent parameters
                # For now, just log the optimization
                self.logger.info(f"Optimization: {optimization['agent']}.{optimization['parameter']} "
                               f"{optimization['old_value']} → {optimization['new_value']} "
                               f"({optimization['reason']})")
                applied_count += 1
                
            except Exception as e:
                self.logger.error(f"Error applying optimization: {e}")
                failed_count += 1
        
        expected_improvement = self.estimate_optimization_impact(optimizations)
        
        return {
            'optimizations_applied': applied_count,
            'optimizations_failed': failed_count,
            'expected_improvement': expected_improvement
        }
    
    def estimate_optimization_impact(self, optimizations: List[Dict[str, Any]]) -> float:
        """Estimate expected improvement from optimizations"""
        # Simplified impact estimation
        impact_per_optimization = 0.02  # 2% improvement per optimization
        return len(optimizations) * impact_per_optimization
    
    def trigger_optimization_analysis(self):
        """Trigger optimization analysis"""
        self.logger.info(f"Triggering optimization analysis - Current win rate: {self.current_win_rate:.1%}")
        
        # Publish optimization trigger
        self.publish("optimization_analysis_triggered", {
            'current_win_rate': self.current_win_rate,
            'target_win_rate': self.target_win_rate,
            'performance_gap': self.target_win_rate - self.current_win_rate,
            'market_type': self.market_type
        })
    
    def get_optimization_recommendations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current optimization recommendations
        """
        if len(self.trade_outcomes) < self.min_trades_for_analysis:
            return {'recommendations': [], 'reason': 'insufficient_data'}
        
        # Analyze current performance
        performance_analysis = self.analyze_system_performance(data)
        
        # Generate recommendations
        recommendations = []
        
        # Win rate recommendations
        if performance_analysis['overall_performance']['current_win_rate'] < self.target_win_rate:
            recommendations.extend(self.get_win_rate_improvement_recommendations(
                performance_analysis['overall_performance']['performance_gap']
            ))
        
        # Pattern-specific recommendations
        pattern_perf = performance_analysis.get('pattern_performance', {})
        for confluence_level, perf in pattern_perf.items():
            if not perf['meets_target']:
                recommendations.append(f"Improve {confluence_level} performance: current {perf['win_rate']:.1%}")
        
        # ML-specific recommendations
        ml_perf = performance_analysis.get('ml_performance', {})
        for confidence_level, perf in ml_perf.items():
            if not perf['meets_target']:
                recommendations.append(f"Improve {confidence_level} ML performance: current {perf['win_rate']:.1%}")
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recommendations': recommendations,
            'performance_analysis': performance_analysis,
            'optimization_priority': self.determine_optimization_priority(performance_analysis)
        }
    
    def determine_optimization_priority(self, performance_analysis: Dict[str, Any]) -> str:
        """Determine optimization priority level"""
        performance_gap = performance_analysis['overall_performance']['performance_gap']
        
        if performance_gap > 0.2:
            return 'critical'
        elif performance_gap > 0.1:
            return 'high'
        elif performance_gap > 0.05:
            return 'medium'
        else:
            return 'low'
    
    def get_performance_status(self) -> Dict[str, Any]:
        """Get comprehensive performance status"""
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'market_type': self.market_type,
            'current_performance': {
                'win_rate': self.current_win_rate,
                'target_win_rate': self.target_win_rate,
                'performance_gap': self.target_win_rate - self.current_win_rate,
                'performance_trend': self.performance_trend,
                'total_trades': len(self.trade_outcomes)
            },
            'optimization_status': {
                'optimizations_performed': len(self.parameter_optimization_history),
                'last_optimization': self.parameter_optimization_history[-1]['timestamp'].isoformat() if self.parameter_optimization_history else None,
                'optimization_recommendations_count': len(self.optimization_recommendations)
            },
            'system_health': self.calculate_system_health()
        }
    
    def calculate_system_health(self) -> Dict[str, Any]:
        """Calculate overall system health metrics"""
        health = {
            'overall_health': 'unknown',
            'performance_health': 'poor',
            'optimization_health': 'good',
            'data_health': 'good'
        }
        
        # Performance health
        if self.current_win_rate >= self.target_win_rate:
            health['performance_health'] = 'excellent'
        elif self.current_win_rate >= self.target_win_rate * 0.9:
            health['performance_health'] = 'good'
        elif self.current_win_rate >= self.target_win_rate * 0.8:
            health['performance_health'] = 'fair'
        
        # Overall health
        health_scores = {'excellent': 4, 'good': 3, 'fair': 2, 'poor': 1}
        avg_health = np.mean([health_scores[h] for h in [health['performance_health'], health['optimization_health'], health['data_health']]])
        
        if avg_health >= 3.5:
            health['overall_health'] = 'excellent'
        elif avg_health >= 2.5:
            health['overall_health'] = 'good'
        elif avg_health >= 1.5:
            health['overall_health'] = 'fair'
        else:
            health['overall_health'] = 'poor'
        
        return health
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on performance"""
        if len(self.trade_outcomes) < self.min_trades_for_analysis:
            return 0.5  # Neutral when insufficient data
        
        # Signal strength based on win rate achievement
        win_rate_factor = min(self.current_win_rate / self.target_win_rate, 1.0)
        
        # Trend factor
        trend_factors = {'improving': 1.0, 'stable': 0.8, 'declining': 0.5, 'unknown': 0.6}
        trend_factor = trend_factors.get(self.performance_trend, 0.6)
        
        return (win_rate_factor * 0.8 + trend_factor * 0.2)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'performance_metrics': {
                'current_win_rate': self.current_win_rate,
                'target_win_rate': self.target_win_rate,
                'performance_gap': self.target_win_rate - self.current_win_rate,
                'performance_trend': self.performance_trend,
                'total_trades': len(self.trade_outcomes)
            },
            'optimization_metrics': {
                'optimizations_performed': len(self.parameter_optimization_history),
                'optimization_recommendations': len(self.optimization_recommendations)
            },
            'last_signal_strength': self.get_signal_strength(),
            'system_health': self.calculate_system_health(),
            'configuration': {
                'target_win_rate': self.target_win_rate,
                'performance_window': self.performance_window,
                'optimization_frequency': self.optimization_frequency
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Performance feedback agent benefits from continuous monitoring"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for performance monitoring"""
        try:
            # Update system health metrics
            self.update_system_health_metrics()
            
            # Check for performance degradation
            if self.performance_trend == 'declining':
                self.logger.warning("Performance declining - triggering optimization analysis")
                self.trigger_optimization_analysis()
        
        except Exception as e:
            self.logger.error(f"Error in performance feedback continuous processing: {e}")
    
    def update_system_health_metrics(self):
        """Update system health metrics"""
        # Calculate recent performance metrics
        if len(self.trade_outcomes) >= 10:
            recent_trades = self.trade_outcomes[-10:]
            recent_win_rate = sum(1 for trade in recent_trades if trade['outcome'] == 'win') / len(recent_trades)
            
            self.system_health_metrics['recent_win_rate'] = recent_win_rate
            self.system_health_metrics['last_updated'] = datetime.now(timezone.utc)
    
    def get_processing_interval(self) -> float:
        """Get processing interval"""
        return 60.0  # Check every minute for performance updates