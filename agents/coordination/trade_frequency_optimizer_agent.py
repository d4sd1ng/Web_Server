"""
Trade Frequency Optimizer Agent
Balances >90% win rate targeting with adequate trade execution frequency
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

from agents.base_agent import BaseAgent


class TradeFrequencyOptimizerAgent(BaseAgent):
    """
    Critical agent for balancing win rate targeting with trade execution frequency
    Prevents over-filtering that results in no trades
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("trade_frequency_optimizer", config)
        
        # Trade frequency configuration
        self.min_trades_per_day = config.get('min_trades_per_day', 2)  # Minimum viable frequency
        self.max_trades_per_day = config.get('max_trades_per_day', 10) # Maximum for quality
        self.target_trades_per_week = config.get('target_trades_per_week', 15)
        self.frequency_monitoring_window = config.get('frequency_monitoring_window', 7)  # days
        
        # Dynamic adjustment parameters
        self.confluence_adjustment_step = config.get('confluence_adjustment_step', 0.5)
        self.ml_confidence_adjustment_step = config.get('ml_confidence_adjustment_step', 0.05)
        self.max_adjustment_iterations = config.get('max_adjustment_iterations', 5)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Tracking
        self.trade_frequency_history = []
        self.parameter_adjustments = []
        self.current_settings = self.load_initial_settings()
        
        # Performance vs frequency balance
        self.balance_metrics = {
            'current_frequency': 0.0,
            'current_win_rate': 0.0,
            'balance_score': 0.0,
            'last_adjustment': None
        }
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Trade Frequency Optimizer initialized for {self.market_type} - balancing >90% win rate with execution frequency")
    
    def load_initial_settings(self) -> Dict[str, Any]:
        """Load initial conservative but tradeable settings"""
        if self.market_type == 'forex':
            return {
                'min_confluence_patterns': 4,  # Start conservative but tradeable
                'min_confluence_score': 6.0,   # Relaxed from 10.0
                'ml_confidence_threshold': 0.8, # Relaxed from 0.95
                'ml_agreement_threshold': 0.75, # Relaxed from 0.9
                'session_quality_min': 0.6,    # Relaxed from 0.8
                'quality_gate_threshold': 0.65  # Relaxed from 0.8
            }
        else:  # crypto
            return {
                'min_confluence_patterns': 3,   # Start conservative but tradeable
                'min_confluence_score': 5.0,   # Relaxed from 8.5
                'ml_confidence_threshold': 0.75, # Relaxed from 0.9
                'ml_agreement_threshold': 0.7,  # Relaxed from 0.85
                'volume_confirmation_flexibility': True,
                'quality_gate_threshold': 0.6   # Relaxed from 0.8
            }
    
    def apply_market_specific_config(self):
        """Apply market-specific frequency optimization"""
        if self.market_type == 'forex':
            # Forex: Session-based frequency expectations
            self.min_trades_per_day = max(self.min_trades_per_day, 1)  # At least 1 per day
            self.session_based_frequency = True
            self.news_pause_periods = True
        elif self.market_type == 'crypto':
            # Crypto: 24/7 trading allows higher frequency
            self.min_trades_per_day = max(self.min_trades_per_day, 2)  # At least 2 per day
            self.session_based_frequency = False
            self.volatility_based_frequency = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process trade frequency data and optimize settings
        
        Args:
            data: Dictionary containing frequency metrics and performance data
            
        Returns:
            Dictionary with frequency optimization results
        """
        try:
            action = data.get('action', 'monitor')
            
            if action == 'monitor_frequency':
                return self.monitor_trade_frequency(data)
            elif action == 'optimize_settings':
                return self.optimize_frequency_settings(data)
            elif action == 'emergency_adjustment':
                return self.emergency_frequency_adjustment(data)
            else:
                return self.get_frequency_status()
                
        except Exception as e:
            self.logger.error(f"Error processing frequency optimization data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def monitor_trade_frequency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor current trade execution frequency
        """
        # Get recent trade data
        recent_trades = data.get('recent_trades', [])
        rejected_opportunities = data.get('rejected_opportunities', [])
        
        # Calculate frequency metrics
        frequency_metrics = self.calculate_frequency_metrics(recent_trades, rejected_opportunities)
        
        # Check if frequency is too low
        frequency_issues = self.identify_frequency_issues(frequency_metrics)
        
        # Update tracking
        self.update_frequency_tracking(frequency_metrics)
        
        # Determine if adjustment is needed
        adjustment_needed = self.assess_adjustment_necessity(frequency_metrics, frequency_issues)
        
        results = {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'frequency_metrics': frequency_metrics,
            'frequency_issues': frequency_issues,
            'adjustment_needed': adjustment_needed,
            'current_settings': self.current_settings,
            'market_type': self.market_type,
            'balance_score': self.calculate_balance_score(frequency_metrics)
        }
        
        # Publish frequency alerts if needed
        if frequency_issues:
            self.publish("trade_frequency_alert", {
                'issues': frequency_issues,
                'adjustment_needed': adjustment_needed,
                'market_type': self.market_type
            })
        
        return results
    
    def calculate_frequency_metrics(self, recent_trades: List[Dict[str, Any]], 
                                   rejected_opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive frequency metrics"""
        now = datetime.now(timezone.utc)
        
        # Filter recent data (last 7 days)
        cutoff_time = now - timedelta(days=self.frequency_monitoring_window)
        
        recent_trades_filtered = [
            trade for trade in recent_trades 
            if datetime.fromisoformat(trade.get('timestamp', '2020-01-01T00:00:00+00:00').replace('Z', '+00:00')) > cutoff_time
        ]
        
        recent_rejections_filtered = [
            rej for rej in rejected_opportunities
            if datetime.fromisoformat(rej.get('timestamp', '2020-01-01T00:00:00+00:00').replace('Z', '+00:00')) > cutoff_time
        ]
        
        # Calculate metrics
        trades_per_day = len(recent_trades_filtered) / self.frequency_monitoring_window
        opportunities_per_day = len(recent_rejections_filtered) / self.frequency_monitoring_window
        total_opportunities_per_day = trades_per_day + opportunities_per_day
        
        # Execution rate
        execution_rate = trades_per_day / total_opportunities_per_day if total_opportunities_per_day > 0 else 0
        
        # Win rate from recent trades
        if recent_trades_filtered:
            wins = sum(1 for trade in recent_trades_filtered if trade.get('outcome') == 'win')
            current_win_rate = wins / len(recent_trades_filtered)
        else:
            current_win_rate = 0.0
        
        return {
            'trades_per_day': trades_per_day,
            'opportunities_per_day': opportunities_per_day,
            'total_opportunities_per_day': total_opportunities_per_day,
            'execution_rate': execution_rate,
            'current_win_rate': current_win_rate,
            'monitoring_window_days': self.frequency_monitoring_window,
            'total_recent_trades': len(recent_trades_filtered),
            'total_recent_rejections': len(recent_rejections_filtered)
        }
    
    def identify_frequency_issues(self, frequency_metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify frequency-related issues"""
        issues = []
        
        trades_per_day = frequency_metrics['trades_per_day']
        execution_rate = frequency_metrics['execution_rate']
        current_win_rate = frequency_metrics['current_win_rate']
        
        # Too few trades issue
        if trades_per_day < self.min_trades_per_day:
            severity = 'critical' if trades_per_day < self.min_trades_per_day * 0.5 else 'high'
            issues.append({
                'type': 'insufficient_trade_frequency',
                'severity': severity,
                'description': f"Only {trades_per_day:.1f} trades/day (min: {self.min_trades_per_day})",
                'recommended_action': 'relax_confluence_requirements'
            })
        
        # Too low execution rate
        if execution_rate < 0.1:  # Less than 10% of opportunities executed
            issues.append({
                'type': 'very_low_execution_rate',
                'severity': 'critical',
                'description': f"Only {execution_rate:.1%} execution rate",
                'recommended_action': 'significantly_relax_filters'
            })
        elif execution_rate < 0.2:  # Less than 20% execution rate
            issues.append({
                'type': 'low_execution_rate',
                'severity': 'high',
                'description': f"Only {execution_rate:.1%} execution rate",
                'recommended_action': 'moderately_relax_filters'
            })
        
        # No trades at all
        if trades_per_day == 0:
            issues.append({
                'type': 'zero_trade_execution',
                'severity': 'emergency',
                'description': "No trades executed in monitoring window",
                'recommended_action': 'emergency_parameter_relaxation'
            })
        
        # Win rate vs frequency balance
        if current_win_rate > 0.95 and trades_per_day < self.min_trades_per_day:
            issues.append({
                'type': 'over_optimization',
                'severity': 'medium',
                'description': f"Win rate {current_win_rate:.1%} but too few trades ({trades_per_day:.1f}/day)",
                'recommended_action': 'slightly_relax_for_frequency'
            })
        
        return issues
    
    def assess_adjustment_necessity(self, frequency_metrics: Dict[str, Any], 
                                   frequency_issues: List[Dict[str, str]]) -> Dict[str, Any]:
        """Assess if parameter adjustment is necessary"""
        adjustment_assessment = {
            'adjustment_needed': False,
            'adjustment_urgency': 'none',
            'adjustment_type': 'none',
            'recommended_adjustments': []
        }
        
        # Check issue severity
        critical_issues = [issue for issue in frequency_issues if issue['severity'] in ['critical', 'emergency']]
        high_issues = [issue for issue in frequency_issues if issue['severity'] == 'high']
        
        if critical_issues:
            adjustment_assessment.update({
                'adjustment_needed': True,
                'adjustment_urgency': 'immediate',
                'adjustment_type': 'significant_relaxation',
                'recommended_adjustments': self.generate_relaxation_adjustments('significant')
            })
        
        elif high_issues:
            adjustment_assessment.update({
                'adjustment_needed': True,
                'adjustment_urgency': 'soon',
                'adjustment_type': 'moderate_relaxation',
                'recommended_adjustments': self.generate_relaxation_adjustments('moderate')
            })
        
        elif frequency_metrics['trades_per_day'] < self.min_trades_per_day * 0.8:
            adjustment_assessment.update({
                'adjustment_needed': True,
                'adjustment_urgency': 'planned',
                'adjustment_type': 'minor_relaxation',
                'recommended_adjustments': self.generate_relaxation_adjustments('minor')
            })
        
        return adjustment_assessment
    
    def generate_relaxation_adjustments(self, adjustment_level: str) -> List[Dict[str, Any]]:
        """Generate parameter relaxation adjustments"""
        adjustments = []
        
        if adjustment_level == 'significant':
            # Emergency relaxation - ensure trades happen
            adjustments.extend([
                {
                    'agent': 'confluence_coordinator',
                    'parameter': 'min_confluence_patterns',
                    'adjustment': -2,  # Reduce by 2
                    'reason': 'Emergency: No trades executing'
                },
                {
                    'agent': 'confluence_coordinator', 
                    'parameter': 'min_confluence_score',
                    'adjustment': -3.0,  # Reduce by 3.0
                    'reason': 'Emergency: Score too restrictive'
                },
                {
                    'agent': 'ml_ensemble',
                    'parameter': 'confidence_threshold',
                    'adjustment': -0.15,  # Reduce by 15%
                    'reason': 'Emergency: ML threshold too high'
                },
                {
                    'agent': 'master_coordinator',
                    'parameter': 'decision_confidence_threshold',
                    'adjustment': -0.1,  # Reduce by 10%
                    'reason': 'Emergency: Final threshold too strict'
                }
            ])
        
        elif adjustment_level == 'moderate':
            # Moderate relaxation - balance quality and frequency
            adjustments.extend([
                {
                    'agent': 'confluence_coordinator',
                    'parameter': 'min_confluence_patterns',
                    'adjustment': -1,  # Reduce by 1
                    'reason': 'Moderate: Increase trade frequency'
                },
                {
                    'agent': 'confluence_coordinator',
                    'parameter': 'min_confluence_score',
                    'adjustment': -1.5,  # Reduce by 1.5
                    'reason': 'Moderate: Balance quality and frequency'
                },
                {
                    'agent': 'ml_ensemble',
                    'parameter': 'confidence_threshold',
                    'adjustment': -0.05,  # Reduce by 5%
                    'reason': 'Moderate: Slightly lower ML threshold'
                }
            ])
        
        elif adjustment_level == 'minor':
            # Minor relaxation - fine tuning
            adjustments.extend([
                {
                    'agent': 'confluence_coordinator',
                    'parameter': 'min_confluence_score',
                    'adjustment': -0.5,  # Reduce by 0.5
                    'reason': 'Minor: Fine-tune for frequency'
                },
                {
                    'agent': 'ml_ensemble',
                    'parameter': 'confidence_threshold',
                    'adjustment': -0.02,  # Reduce by 2%
                    'reason': 'Minor: Slight ML adjustment'
                }
            ])
        
        return adjustments
    
    def optimize_frequency_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize settings for balanced frequency and win rate
        """
        frequency_metrics = data.get('frequency_metrics', {})
        performance_metrics = data.get('performance_metrics', {})
        
        if not frequency_metrics:
            return {'error': 'No frequency metrics provided'}
        
        # Assess current balance
        balance_assessment = self.assess_frequency_balance(frequency_metrics, performance_metrics)
        
        # Generate optimization strategy
        optimization_strategy = self.generate_optimization_strategy(balance_assessment)
        
        # Apply optimizations
        optimization_results = self.apply_frequency_optimizations(optimization_strategy)
        
        # Update tracking
        self.update_optimization_tracking(balance_assessment, optimization_strategy, optimization_results)
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'balance_assessment': balance_assessment,
            'optimization_strategy': optimization_strategy,
            'optimization_results': optimization_results,
            'new_settings': self.current_settings,
            'market_type': self.market_type
        }
    
    def assess_frequency_balance(self, frequency_metrics: Dict[str, Any], 
                                performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess balance between frequency and performance"""
        trades_per_day = frequency_metrics.get('trades_per_day', 0)
        current_win_rate = frequency_metrics.get('current_win_rate', 0)
        execution_rate = frequency_metrics.get('execution_rate', 0)
        
        # Calculate balance score
        # Perfect balance: adequate frequency + high win rate
        frequency_score = min(trades_per_day / self.min_trades_per_day, 2.0) / 2.0  # Normalize to 1.0
        win_rate_score = current_win_rate / 0.9 if current_win_rate > 0 else 0  # Normalize to 90%
        execution_score = min(execution_rate / 0.2, 1.0)  # Target 20%+ execution rate
        
        # Weighted balance score
        balance_score = (frequency_score * 0.4 + win_rate_score * 0.4 + execution_score * 0.2)
        
        return {
            'balance_score': balance_score,
            'frequency_score': frequency_score,
            'win_rate_score': win_rate_score,
            'execution_score': execution_score,
            'trades_per_day': trades_per_day,
            'current_win_rate': current_win_rate,
            'execution_rate': execution_rate,
            'balance_status': self.classify_balance_status(balance_score),
            'primary_issue': self.identify_primary_issue(frequency_score, win_rate_score, execution_score)
        }
    
    def classify_balance_status(self, balance_score: float) -> str:
        """Classify balance status"""
        if balance_score >= 0.8:
            return 'excellent_balance'
        elif balance_score >= 0.6:
            return 'good_balance'
        elif balance_score >= 0.4:
            return 'poor_balance'
        else:
            return 'critical_imbalance'
    
    def identify_primary_issue(self, frequency_score: float, win_rate_score: float, execution_score: float) -> str:
        """Identify primary issue affecting balance"""
        scores = {
            'frequency': frequency_score,
            'win_rate': win_rate_score,
            'execution': execution_score
        }
        
        lowest_score = min(scores.values())
        primary_issue = [key for key, value in scores.items() if value == lowest_score][0]
        
        if primary_issue == 'frequency':
            return 'insufficient_trade_frequency'
        elif primary_issue == 'win_rate':
            return 'poor_win_rate_performance'
        else:
            return 'poor_execution_rate'
    
    def generate_optimization_strategy(self, balance_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization strategy based on balance assessment"""
        balance_status = balance_assessment['balance_status']
        primary_issue = balance_assessment['primary_issue']
        
        strategy = {
            'strategy_type': 'maintain',
            'adjustments': [],
            'expected_impact': 'none',
            'risk_level': 'low'
        }
        
        if balance_status == 'critical_imbalance':
            if primary_issue == 'insufficient_trade_frequency':
                strategy.update({
                    'strategy_type': 'aggressive_relaxation',
                    'adjustments': self.generate_relaxation_adjustments('significant'),
                    'expected_impact': 'major_frequency_increase',
                    'risk_level': 'medium'
                })
        
        elif balance_status == 'poor_balance':
            if primary_issue == 'insufficient_trade_frequency':
                strategy.update({
                    'strategy_type': 'moderate_relaxation',
                    'adjustments': self.generate_relaxation_adjustments('moderate'),
                    'expected_impact': 'moderate_frequency_increase',
                    'risk_level': 'low'
                })
            elif primary_issue == 'poor_win_rate_performance':
                strategy.update({
                    'strategy_type': 'quality_enhancement',
                    'adjustments': self.generate_quality_adjustments(),
                    'expected_impact': 'win_rate_improvement',
                    'risk_level': 'low'
                })
        
        return strategy
    
    def generate_quality_adjustments(self) -> List[Dict[str, Any]]:
        """Generate adjustments to improve quality (when win rate is low)"""
        return [
            {
                'agent': 'confluence_coordinator',
                'parameter': 'min_confluence_patterns',
                'adjustment': 1,  # Increase by 1
                'reason': 'Improve win rate quality'
            },
            {
                'agent': 'ml_ensemble',
                'parameter': 'confidence_threshold',
                'adjustment': 0.05,  # Increase by 5%
                'reason': 'Improve ML precision'
            }
        ]
    
    def apply_frequency_optimizations(self, optimization_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Apply frequency optimization adjustments"""
        applied_adjustments = []
        failed_adjustments = []
        
        for adjustment in optimization_strategy.get('adjustments', []):
            try:
                # Apply adjustment to current settings
                self.apply_parameter_adjustment(adjustment)
                applied_adjustments.append(adjustment)
                
                self.logger.info(f"Applied adjustment: {adjustment['agent']}.{adjustment['parameter']} "
                               f"by {adjustment['adjustment']} ({adjustment['reason']})")
                
            except Exception as e:
                self.logger.error(f"Failed to apply adjustment: {e}")
                failed_adjustments.append({'adjustment': adjustment, 'error': str(e)})
        
        return {
            'applied_adjustments': len(applied_adjustments),
            'failed_adjustments': len(failed_adjustments),
            'adjustments_details': applied_adjustments,
            'strategy_type': optimization_strategy['strategy_type']
        }
    
    def apply_parameter_adjustment(self, adjustment: Dict[str, Any]):
        """Apply individual parameter adjustment"""
        agent = adjustment['agent']
        parameter = adjustment['parameter']
        adjustment_value = adjustment['adjustment']
        
        # Update current settings
        if agent not in self.current_settings:
            self.current_settings[agent] = {}
        
        current_value = self.current_settings[agent].get(parameter, 0)
        new_value = current_value + adjustment_value
        
        # Apply bounds checking
        new_value = self.apply_parameter_bounds(agent, parameter, new_value)
        
        self.current_settings[agent][parameter] = new_value
        
        # Record adjustment
        adjustment_record = {
            'timestamp': datetime.now(timezone.utc),
            'agent': agent,
            'parameter': parameter,
            'old_value': current_value,
            'new_value': new_value,
            'adjustment': adjustment_value,
            'reason': adjustment['reason']
        }
        self.parameter_adjustments.append(adjustment_record)
    
    def apply_parameter_bounds(self, agent: str, parameter: str, value: float) -> float:
        """Apply bounds checking to parameter values"""
        # Define reasonable bounds for key parameters
        bounds = {
            'min_confluence_patterns': (1, 10),    # At least 1, max 10
            'min_confluence_score': (1.0, 15.0),   # At least 1.0, max 15.0
            'confidence_threshold': (0.5, 0.99),   # 50% to 99%
            'ml_agreement_threshold': (0.5, 0.99), # 50% to 99%
            'session_quality_min': (0.3, 1.0),     # 30% to 100%
            'quality_gate_threshold': (0.3, 1.0)   # 30% to 100%
        }
        
        if parameter in bounds:
            min_val, max_val = bounds[parameter]
            return max(min_val, min(value, max_val))
        
        return value
    
    def emergency_frequency_adjustment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Emergency adjustment when no trades are executing"""
        self.logger.warning("EMERGENCY FREQUENCY ADJUSTMENT - No trades executing!")
        
        # Apply emergency relaxation
        emergency_adjustments = [
            {
                'agent': 'confluence_coordinator',
                'parameter': 'min_confluence_patterns',
                'adjustment': -2,
                'reason': 'EMERGENCY: Restore trade execution'
            },
            {
                'agent': 'confluence_coordinator',
                'parameter': 'min_confluence_score', 
                'adjustment': -4.0,
                'reason': 'EMERGENCY: Major score relaxation'
            },
            {
                'agent': 'ml_ensemble',
                'parameter': 'confidence_threshold',
                'adjustment': -0.2,
                'reason': 'EMERGENCY: Major ML relaxation'
            },
            {
                'agent': 'master_coordinator',
                'parameter': 'decision_confidence_threshold',
                'adjustment': -0.15,
                'reason': 'EMERGENCY: Major decision relaxation'
            }
        ]
        
        # Apply emergency adjustments
        for adjustment in emergency_adjustments:
            self.apply_parameter_adjustment(adjustment)
        
        # Publish emergency alert
        self.publish("emergency_frequency_adjustment", {
            'adjustments_applied': len(emergency_adjustments),
            'new_settings': self.current_settings,
            'market_type': self.market_type
        })
        
        return {
            'emergency_adjustment_completed': True,
            'adjustments_applied': len(emergency_adjustments),
            'new_settings': self.current_settings,
            'expected_impact': 'significant_frequency_increase'
        }
    
    def calculate_balance_score(self, frequency_metrics: Dict[str, Any]) -> float:
        """Calculate overall balance score"""
        trades_per_day = frequency_metrics.get('trades_per_day', 0)
        current_win_rate = frequency_metrics.get('current_win_rate', 0)
        execution_rate = frequency_metrics.get('execution_rate', 0)
        
        # Ideal targets
        ideal_frequency = self.min_trades_per_day * 2  # 2x minimum
        ideal_win_rate = 0.85  # 85% realistic target
        ideal_execution_rate = 0.25  # 25% execution rate
        
        # Calculate component scores
        frequency_score = min(trades_per_day / ideal_frequency, 1.0)
        win_rate_score = min(current_win_rate / ideal_win_rate, 1.0)
        execution_score = min(execution_rate / ideal_execution_rate, 1.0)
        
        # Weighted balance (frequency gets higher weight to ensure trading)
        balance_score = (frequency_score * 0.5 + win_rate_score * 0.3 + execution_score * 0.2)
        
        return balance_score
    
    def update_frequency_tracking(self, frequency_metrics: Dict[str, Any]):
        """Update frequency tracking history"""
        tracking_entry = {
            'timestamp': datetime.now(timezone.utc),
            'frequency_metrics': frequency_metrics,
            'current_settings': self.current_settings.copy(),
            'balance_score': self.calculate_balance_score(frequency_metrics),
            'market_type': self.market_type
        }
        
        self.trade_frequency_history.append(tracking_entry)
        
        # Update balance metrics
        self.balance_metrics.update({
            'current_frequency': frequency_metrics.get('trades_per_day', 0),
            'current_win_rate': frequency_metrics.get('current_win_rate', 0),
            'balance_score': tracking_entry['balance_score'],
            'last_adjustment': datetime.now(timezone.utc) if self.parameter_adjustments else None
        })
        
        # Limit tracking size
        if len(self.trade_frequency_history) > 100:
            self.trade_frequency_history = self.trade_frequency_history[-100:]
    
    def update_optimization_tracking(self, balance_assessment: Dict[str, Any], 
                                   optimization_strategy: Dict[str, Any], 
                                   optimization_results: Dict[str, Any]):
        """Update optimization tracking"""
        optimization_record = {
            'timestamp': datetime.now(timezone.utc),
            'balance_assessment': balance_assessment,
            'optimization_strategy': optimization_strategy,
            'optimization_results': optimization_results,
            'settings_before': self.current_settings.copy(),
            'market_type': self.market_type
        }
        
        # This would be stored for analysis
        self.logger.info(f"Frequency optimization completed: {optimization_strategy['strategy_type']}")
    
    def get_frequency_status(self) -> Dict[str, Any]:
        """Get comprehensive frequency optimization status"""
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'market_type': self.market_type,
            'current_settings': self.current_settings,
            'balance_metrics': self.balance_metrics,
            'frequency_targets': {
                'min_trades_per_day': self.min_trades_per_day,
                'max_trades_per_day': self.max_trades_per_day,
                'target_trades_per_week': self.target_trades_per_week
            },
            'parameter_adjustments_count': len(self.parameter_adjustments),
            'last_adjustment': self.parameter_adjustments[-1] if self.parameter_adjustments else None,
            'optimization_health': self.assess_optimization_health()
        }
    
    def assess_optimization_health(self) -> str:
        """Assess health of frequency optimization"""
        balance_score = self.balance_metrics['balance_score']
        
        if balance_score >= 0.8:
            return 'excellent'
        elif balance_score >= 0.6:
            return 'good'
        elif balance_score >= 0.4:
            return 'needs_attention'
        else:
            return 'critical'
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on frequency balance"""
        return self.balance_metrics.get('balance_score', 0.0)
    
    def requires_continuous_processing(self) -> bool:
        """Trade frequency optimizer needs continuous monitoring"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for frequency monitoring"""
        try:
            # Check if frequency has dropped too low
            current_frequency = self.balance_metrics.get('current_frequency', 0)
            
            if current_frequency < self.min_trades_per_day * 0.5:
                self.logger.warning(f"Trade frequency critically low: {current_frequency:.1f}/day")
                
                # Trigger automatic adjustment
                self.publish("frequency_critical_alert", {
                    'current_frequency': current_frequency,
                    'minimum_required': self.min_trades_per_day,
                    'market_type': self.market_type
                })
        
        except Exception as e:
            self.logger.error(f"Error in frequency optimizer continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval"""
        return 1800.0  # Check every 30 minutes