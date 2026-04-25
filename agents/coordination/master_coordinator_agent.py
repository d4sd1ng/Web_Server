"""
Master Coordinator Agent
Ultimate decision-making agent for >90% win rate targeting
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class MasterCoordinatorAgent(BaseAgent):
    """
    Master Coordinator Agent - The final decision maker
    Coordinates all agents for >90% win rate achievement
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("master_coordinator", config)
        
        # Master coordination configuration
        self.target_win_rate = config.get('target_win_rate', 0.9)  # 90%
        self.ultra_strict_mode = config.get('ultra_strict_mode', True)
        self.decision_confidence_threshold = config.get('decision_confidence_threshold', 0.95)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Decision framework for >90% win rate
        self.decision_framework = self.load_decision_framework()
        
        # Tracking
        self.trading_decisions = []
        self.rejected_opportunities = []
        self.performance_tracking = {'approved': 0, 'rejected': 0, 'win_rate': 0.0}
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Master Coordinator initialized for {self.market_type} - ULTRA STRICT MODE for >90% win rate")
    
    def load_decision_framework(self) -> Dict[str, Any]:
        """Load ultra-strict decision framework for >90% win rate"""
        return {
            'mandatory_requirements': {
                'forex': {
                    'min_confluence_patterns': 6,
                    'min_confluence_score': 10.0,
                    'min_ml_confidence': 0.95,
                    'min_ml_model_agreement': 0.9,
                    'htf_confluence_required': True,
                    'session_quality_min': 0.8,
                    'killzone_required': True,
                    'pattern_cluster_required': True
                },
                'crypto': {
                    'min_confluence_patterns': 5,
                    'min_confluence_score': 8.5,
                    'min_ml_confidence': 0.9,
                    'min_ml_model_agreement': 0.85,
                    'htf_confluence_required': True,
                    'volume_confirmation_required': True,
                    'momentum_confirmation_required': True,
                    'pattern_cluster_required': True
                }
            },
            'quality_gates': {
                'pattern_quality': 0.8,
                'signal_consistency': 0.85,
                'risk_reward_min': 2.0,
                'market_regime_favorable': True,
                'no_conflicting_signals': True
            },
            'rejection_criteria': {
                'any_mandatory_failed': 'immediate_rejection',
                'low_confluence': 'immediate_rejection',
                'ml_disagreement': 'immediate_rejection',
                'poor_market_regime': 'immediate_rejection',
                'conflicting_timeframes': 'immediate_rejection'
            }
        }
    
    def apply_market_specific_config(self):
        """Apply market-specific master coordination"""
        requirements = self.decision_framework['mandatory_requirements'][self.market_type]
        
        self.min_confluence_patterns = requirements['min_confluence_patterns']
        self.min_confluence_score = requirements['min_confluence_score']
        self.min_ml_confidence = requirements['min_ml_confidence']
        self.min_ml_model_agreement = requirements['min_ml_model_agreement']
        
        if self.market_type == 'forex':
            self.session_dependency = True
            self.news_sensitivity = True
        elif self.market_type == 'crypto':
            self.volume_dependency = True
            self.volatility_sensitivity = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Master decision processing - final trading decision
        
        Args:
            data: Dictionary containing ALL agent results
            
        Returns:
            Dictionary with final trading decision
        """
        required_fields = ['symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        
        try:
            # Stage 1: Collect all agent signals
            agent_signals = self.collect_all_agent_signals(data)
            
            # Stage 2: Apply mandatory requirements
            mandatory_check = self.check_mandatory_requirements(agent_signals)
            
            if not mandatory_check['passed']:
                return self.create_rejection_decision(symbol, 'mandatory_requirements_failed', mandatory_check)
            
            # Stage 3: Apply quality gates
            quality_check = self.check_quality_gates(agent_signals)
            
            if not quality_check['passed']:
                return self.create_rejection_decision(symbol, 'quality_gates_failed', quality_check)
            
            # Stage 4: Final decision synthesis
            final_decision = self.synthesize_final_decision(agent_signals, mandatory_check, quality_check)
            
            # Stage 5: Apply ultra-strict filters
            ultra_strict_decision = self.apply_ultra_strict_filters(final_decision, agent_signals)
            
            # Update tracking
            self.update_decision_tracking(symbol, ultra_strict_decision, agent_signals)
            
            # Calculate signal strength
            signal_strength = self.calculate_master_signal_strength(ultra_strict_decision, agent_signals)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'final_decision': ultra_strict_decision,
                'mandatory_check': mandatory_check,
                'quality_check': quality_check,
                'agent_signals_summary': self.summarize_agent_signals(agent_signals),
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'decision_framework': 'ultra_strict_90_percent_targeting'
            }
            
            # Publish final decision
            if ultra_strict_decision['approved']:
                self.publish("master_trading_decision", {
                    'symbol': symbol,
                    'direction': ultra_strict_decision['direction'],
                    'confidence': ultra_strict_decision['confidence'],
                    'expected_win_rate': ultra_strict_decision['expected_win_rate'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in master coordination for {symbol}: {e}")
            return {'final_decision': {'approved': False, 'reason': 'coordination_error'}, 'error': str(e)}
    
    def collect_all_agent_signals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect and organize ALL agent signals
        """
        signals = {
            'ict_smc_agents': {},
            'analysis_agents': {},
            'ml_agents': {},
            'execution_agents': {},
            'coordination_agents': {},
            'total_active_signals': 0,
            'signal_quality_score': 0.0
        }
        
        # ICT/SMC agents
        ict_smc_agents = [
            'fair_value_gaps', 'order_blocks', 'market_structure', 'liquidity_sweeps',
            'premium_discount', 'ote', 'breaker_blocks', 'sof', 'displacement',
            'engulfing', 'mitigation_blocks', 'killzone', 'pattern_cluster',
            'swing_failure_pattern', 'htf_confluence', 'judas_swing', 'power_of_three',
            'market_maker_model', 'turtle_soup', 'imbalance', 'momentum_shift'
        ]
        
        active_ict_signals = 0
        total_ict_strength = 0.0
        
        for agent_name in ict_smc_agents:
            if agent_name in data:
                agent_data = data[agent_name]
                signal_strength = agent_data.get('signal_strength', 0.0)
                
                if signal_strength > 0.6:  # Only high-quality signals
                    signals['ict_smc_agents'][agent_name] = {
                        'strength': signal_strength,
                        'data': agent_data,
                        'bias': self.determine_agent_bias(agent_name, agent_data)
                    }
                    active_ict_signals += 1
                    total_ict_strength += signal_strength
        
        signals['ict_smc_summary'] = {
            'active_signals': active_ict_signals,
            'avg_strength': total_ict_strength / active_ict_signals if active_ict_signals > 0 else 0.0
        }
        
        # Analysis agents
        analysis_agents = ['volume_analysis', 'session_analysis', 'technical_indicators', 'market_regime']
        for agent_name in analysis_agents:
            if agent_name in data:
                signals['analysis_agents'][agent_name] = data[agent_name]
        
        # ML agents
        ml_agents = ['ml_ensemble', 'ml_prediction']
        for agent_name in ml_agents:
            if agent_name in data:
                signals['ml_agents'][agent_name] = data[agent_name]
        
        # Coordination agents
        coordination_agents = ['confluence_coordinator', 'performance_feedback']
        for agent_name in coordination_agents:
            if agent_name in data:
                signals['coordination_agents'][agent_name] = data[agent_name]
        
        # Calculate total active signals
        signals['total_active_signals'] = (
            len(signals['ict_smc_agents']) +
            len(signals['analysis_agents']) +
            len(signals['ml_agents']) +
            len(signals['coordination_agents'])
        )
        
        return signals
    
    def check_mandatory_requirements(self, agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check mandatory requirements for >90% win rate
        """
        requirements = self.decision_framework['mandatory_requirements'][self.market_type]
        
        check_result = {
            'passed': True,
            'failed_requirements': [],
            'passed_requirements': [],
            'requirement_scores': {}
        }
        
        # Check minimum confluence patterns
        ict_signals_count = len(agent_signals['ict_smc_agents'])
        min_patterns = requirements['min_confluence_patterns']
        
        if ict_signals_count >= min_patterns:
            check_result['passed_requirements'].append('min_confluence_patterns')
            check_result['requirement_scores']['confluence_patterns'] = ict_signals_count / min_patterns
        else:
            check_result['passed'] = False
            check_result['failed_requirements'].append(f'min_confluence_patterns ({ict_signals_count}/{min_patterns})')
        
        # Check confluence score
        confluence_data = agent_signals['coordination_agents'].get('confluence_coordinator', {})
        if confluence_data:
            confluence_score = confluence_data.get('confluence_analysis', {}).get('total_score', 0)
            min_score = requirements['min_confluence_score']
            
            if confluence_score >= min_score:
                check_result['passed_requirements'].append('min_confluence_score')
                check_result['requirement_scores']['confluence_score'] = confluence_score / min_score
            else:
                check_result['passed'] = False
                check_result['failed_requirements'].append(f'min_confluence_score ({confluence_score:.1f}/{min_score})')
        
        # Check ML requirements
        ml_data = agent_signals['ml_agents'].get('ml_ensemble', {})
        if ml_data:
            ml_confidence = ml_data.get('final_decision', {}).get('confidence', 0)
            ml_agreement = ml_data.get('model_agreement', 0)
            
            # ML confidence check
            if ml_confidence >= requirements['min_ml_confidence']:
                check_result['passed_requirements'].append('min_ml_confidence')
                check_result['requirement_scores']['ml_confidence'] = ml_confidence / requirements['min_ml_confidence']
            else:
                check_result['passed'] = False
                check_result['failed_requirements'].append(f'min_ml_confidence ({ml_confidence:.2f}/{requirements["min_ml_confidence"]})')
            
            # ML model agreement check
            if ml_agreement >= requirements['min_ml_model_agreement']:
                check_result['passed_requirements'].append('min_ml_model_agreement')
                check_result['requirement_scores']['ml_agreement'] = ml_agreement / requirements['min_ml_model_agreement']
            else:
                check_result['passed'] = False
                check_result['failed_requirements'].append(f'min_ml_model_agreement ({ml_agreement:.2f}/{requirements["min_ml_model_agreement"]})')
        else:
            check_result['passed'] = False
            check_result['failed_requirements'].append('ml_ensemble_data_missing')
        
        # Market-specific requirements
        if self.market_type == 'forex':
            # Session quality requirement
            session_data = agent_signals['analysis_agents'].get('session_analysis', {})
            if session_data:
                session_quality = session_data.get('session_analysis', {}).get('session_quality', 0)
                if session_quality >= requirements['session_quality_min']:
                    check_result['passed_requirements'].append('session_quality')
                else:
                    check_result['passed'] = False
                    check_result['failed_requirements'].append(f'session_quality ({session_quality:.2f}/{requirements["session_quality_min"]})')
            
            # Killzone requirement
            killzone_data = agent_signals['ict_smc_agents'].get('killzone', {})
            if killzone_data and killzone_data['strength'] > 0.7:
                check_result['passed_requirements'].append('killzone_active')
            else:
                check_result['passed'] = False
                check_result['failed_requirements'].append('killzone_not_active')
        
        elif self.market_type == 'crypto':
            # Volume confirmation requirement
            volume_data = agent_signals['analysis_agents'].get('volume_analysis', {})
            if volume_data and volume_data.get('volume_spike', False):
                check_result['passed_requirements'].append('volume_confirmation')
            else:
                check_result['passed'] = False
                check_result['failed_requirements'].append('volume_confirmation_missing')
            
            # Momentum confirmation requirement
            momentum_data = agent_signals['ict_smc_agents'].get('momentum_shift', {})
            if momentum_data and momentum_data['strength'] > 0.7:
                check_result['passed_requirements'].append('momentum_confirmation')
            else:
                check_result['passed'] = False
                check_result['failed_requirements'].append('momentum_confirmation_missing')
        
        return check_result
    
    def check_quality_gates(self, agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check quality gates for ultra-high win rate
        """
        quality_gates = self.decision_framework['quality_gates']
        
        check_result = {
            'passed': True,
            'failed_gates': [],
            'passed_gates': [],
            'quality_scores': {}
        }
        
        # Pattern quality gate
        pattern_quality = self.calculate_pattern_quality(agent_signals)
        if pattern_quality >= quality_gates['pattern_quality']:
            check_result['passed_gates'].append('pattern_quality')
            check_result['quality_scores']['pattern_quality'] = pattern_quality
        else:
            check_result['passed'] = False
            check_result['failed_gates'].append(f'pattern_quality ({pattern_quality:.2f}/{quality_gates["pattern_quality"]})')
        
        # Signal consistency gate
        signal_consistency = self.calculate_signal_consistency(agent_signals)
        if signal_consistency >= quality_gates['signal_consistency']:
            check_result['passed_gates'].append('signal_consistency')
            check_result['quality_scores']['signal_consistency'] = signal_consistency
        else:
            check_result['passed'] = False
            check_result['failed_gates'].append(f'signal_consistency ({signal_consistency:.2f}/{quality_gates["signal_consistency"]})')
        
        # Market regime gate
        regime_data = agent_signals['analysis_agents'].get('market_regime', {})
        if regime_data:
            current_regime = regime_data.get('current_regime', 'unknown')
            favorable_regimes = ['trending_bullish', 'trending_bearish', 'breakout_expansion']
            
            if current_regime in favorable_regimes:
                check_result['passed_gates'].append('market_regime_favorable')
            else:
                check_result['passed'] = False
                check_result['failed_gates'].append(f'unfavorable_market_regime ({current_regime})')
        
        # No conflicting signals gate
        conflicting_signals = self.detect_conflicting_signals(agent_signals)
        if not conflicting_signals:
            check_result['passed_gates'].append('no_conflicting_signals')
        else:
            check_result['passed'] = False
            check_result['failed_gates'].append(f'conflicting_signals_detected ({len(conflicting_signals)})')
        
        return check_result
    
    def calculate_pattern_quality(self, agent_signals: Dict[str, Any]) -> float:
        """Calculate overall pattern quality score"""
        ict_signals = agent_signals['ict_smc_agents']
        
        if not ict_signals:
            return 0.0
        
        # Weight high-importance patterns more heavily
        high_importance_patterns = ['market_structure', 'pattern_cluster', 'htf_confluence', 'order_blocks']
        
        quality_scores = []
        weights = []
        
        for agent_name, signal_data in ict_signals.items():
            strength = signal_data['strength']
            weight = 2.0 if agent_name in high_importance_patterns else 1.0
            
            quality_scores.append(strength)
            weights.append(weight)
        
        return np.average(quality_scores, weights=weights) if quality_scores else 0.0
    
    def calculate_signal_consistency(self, agent_signals: Dict[str, Any]) -> float:
        """Calculate consistency across all signals"""
        all_signals = []
        
        # Collect all signal strengths
        for category in ['ict_smc_agents', 'analysis_agents', 'ml_agents']:
            for agent_name, signal_data in agent_signals[category].items():
                if isinstance(signal_data, dict) and 'strength' in signal_data:
                    all_signals.append(signal_data['strength'])
                elif isinstance(signal_data, dict) and 'signal_strength' in signal_data:
                    all_signals.append(signal_data['signal_strength'])
        
        if not all_signals:
            return 0.0
        
        # Consistency = 1 - coefficient of variation
        mean_strength = np.mean(all_signals)
        std_strength = np.std(all_signals)
        
        if mean_strength > 0:
            cv = std_strength / mean_strength
            consistency = max(0, 1.0 - cv)
        else:
            consistency = 0.0
        
        return consistency
    
    def detect_conflicting_signals(self, agent_signals: Dict[str, Any]) -> List[str]:
        """Detect conflicting signals between agents"""
        conflicts = []
        
        # Collect directional biases
        bullish_agents = []
        bearish_agents = []
        
        for agent_name, signal_data in agent_signals['ict_smc_agents'].items():
            bias = signal_data.get('bias', 'neutral')
            if bias == 'bullish':
                bullish_agents.append(agent_name)
            elif bias == 'bearish':
                bearish_agents.append(agent_name)
        
        # Check for major conflicts
        if len(bullish_agents) > 0 and len(bearish_agents) > 0:
            # Check if conflict is significant
            if abs(len(bullish_agents) - len(bearish_agents)) < 2:
                conflicts.append('directional_bias_conflict')
        
        # Check ML vs pattern conflicts
        ml_data = agent_signals['ml_agents'].get('ml_ensemble', {})
        if ml_data:
            ml_direction = ml_data.get('final_decision', {}).get('direction')
            pattern_bias = 'bullish' if len(bullish_agents) > len(bearish_agents) else 'bearish'
            
            if ml_direction and ml_direction != pattern_bias:
                conflicts.append('ml_pattern_conflict')
        
        return conflicts
    
    def synthesize_final_decision(self, agent_signals: Dict[str, Any], 
                                mandatory_check: Dict[str, Any], 
                                quality_check: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize final trading decision
        """
        # Determine direction from strongest signals
        direction = self.determine_final_direction(agent_signals)
        
        # Calculate overall confidence
        confidence = self.calculate_overall_confidence(agent_signals, mandatory_check, quality_check)
        
        # Estimate win rate
        estimated_win_rate = self.estimate_setup_win_rate(agent_signals, confidence)
        
        decision = {
            'approved': False,  # Will be determined by ultra-strict filters
            'direction': direction,
            'confidence': confidence,
            'estimated_win_rate': estimated_win_rate,
            'mandatory_passed': mandatory_check['passed'],
            'quality_passed': quality_check['passed'],
            'signal_count': agent_signals['total_active_signals'],
            'decision_basis': 'comprehensive_agent_synthesis'
        }
        
        return decision
    
    def determine_final_direction(self, agent_signals: Dict[str, Any]) -> str:
        """Determine final trading direction"""
        # Weight votes by agent importance and strength
        bullish_weight = 0.0
        bearish_weight = 0.0
        
        for agent_name, signal_data in agent_signals['ict_smc_agents'].items():
            strength = signal_data['strength']
            bias = signal_data['bias']
            
            # High-importance agents get more weight
            importance_multiplier = 2.0 if agent_name in ['market_structure', 'pattern_cluster', 'htf_confluence'] else 1.0
            
            weighted_strength = strength * importance_multiplier
            
            if bias == 'bullish':
                bullish_weight += weighted_strength
            elif bias == 'bearish':
                bearish_weight += weighted_strength
        
        # Include ML vote with high weight
        ml_data = agent_signals['ml_agents'].get('ml_ensemble', {})
        if ml_data:
            ml_direction = ml_data.get('final_decision', {}).get('direction')
            ml_confidence = ml_data.get('final_decision', {}).get('confidence', 0)
            
            ml_weight = ml_confidence * 3.0  # High weight for ML
            
            if ml_direction == 'long':
                bullish_weight += ml_weight
            elif ml_direction == 'short':
                bearish_weight += ml_weight
        
        # Determine final direction
        if bullish_weight > bearish_weight * 1.2:  # Require clear dominance
            return 'long'
        elif bearish_weight > bullish_weight * 1.2:
            return 'short'
        else:
            return 'neutral'  # No clear direction
    
    def calculate_overall_confidence(self, agent_signals: Dict[str, Any], 
                                   mandatory_check: Dict[str, Any], 
                                   quality_check: Dict[str, Any]) -> float:
        """Calculate overall confidence in the trading decision"""
        confidence_factors = []
        
        # Mandatory requirements confidence
        req_scores = list(mandatory_check.get('requirement_scores', {}).values())
        if req_scores:
            mandatory_confidence = np.mean(req_scores)
            confidence_factors.append(mandatory_confidence * 0.3)
        
        # Quality gates confidence
        quality_scores = list(quality_check.get('quality_scores', {}).values())
        if quality_scores:
            quality_confidence = np.mean(quality_scores)
            confidence_factors.append(quality_confidence * 0.3)
        
        # Signal strength confidence
        ict_avg_strength = agent_signals['ict_smc_summary']['avg_strength']
        confidence_factors.append(ict_avg_strength * 0.4)
        
        return np.mean(confidence_factors) if confidence_factors else 0.0
    
    def estimate_setup_win_rate(self, agent_signals: Dict[str, Any], confidence: float) -> float:
        """Estimate win rate for current setup"""
        base_win_rate = 0.6  # 60% base
        
        # Confidence bonus
        confidence_bonus = (confidence - 0.5) * 0.4  # Up to 20% bonus
        
        # Pattern count bonus
        pattern_count = len(agent_signals['ict_smc_agents'])
        pattern_bonus = min(pattern_count / 10.0, 0.2)  # Up to 20% bonus
        
        # ML ensemble bonus
        ml_data = agent_signals['ml_agents'].get('ml_ensemble', {})
        if ml_data:
            ml_agreement = ml_data.get('model_agreement', 0)
            ml_bonus = ml_agreement * 0.15  # Up to 15% bonus
        else:
            ml_bonus = 0
        
        estimated_win_rate = base_win_rate + confidence_bonus + pattern_bonus + ml_bonus
        
        return min(estimated_win_rate, 0.98)  # Cap at 98%
    
    def apply_ultra_strict_filters(self, decision: Dict[str, Any], agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply ultra-strict filters for >90% win rate targeting
        """
        ultra_decision = decision.copy()
        ultra_decision['ultra_strict_filters'] = []
        
        # Ultra-strict filter 1: Direction must not be neutral
        if decision['direction'] == 'neutral':
            ultra_decision['approved'] = False
            ultra_decision['rejection_reason'] = 'no_clear_directional_bias'
            return ultra_decision
        
        # Ultra-strict filter 2: Confidence must be extremely high
        if decision['confidence'] < self.decision_confidence_threshold:
            ultra_decision['approved'] = False
            ultra_decision['rejection_reason'] = f'confidence_too_low ({decision["confidence"]:.2f}/{self.decision_confidence_threshold})'
            return ultra_decision
        
        # Ultra-strict filter 3: Estimated win rate must meet target
        if decision['estimated_win_rate'] < self.target_win_rate:
            ultra_decision['approved'] = False
            ultra_decision['rejection_reason'] = f'estimated_win_rate_below_target ({decision["estimated_win_rate"]:.1%}/{self.target_win_rate:.1%})'
            return ultra_decision
        
        # Ultra-strict filter 4: All mandatory and quality checks passed
        if not (decision['mandatory_passed'] and decision['quality_passed']):
            ultra_decision['approved'] = False
            ultra_decision['rejection_reason'] = 'mandatory_or_quality_checks_failed'
            return ultra_decision
        
        # All ultra-strict filters passed
        ultra_decision['approved'] = True
        ultra_decision['ultra_strict_filters'] = ['all_filters_passed']
        ultra_decision['approval_reason'] = f'ultra_strict_approval_for_{self.target_win_rate:.0%}_targeting'
        
        return ultra_decision
    
    def create_rejection_decision(self, symbol: str, rejection_type: str, check_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create rejection decision with detailed reasoning"""
        rejection = {
            'agent_id': self.agent_id,
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'final_decision': {
                'approved': False,
                'rejection_type': rejection_type,
                'rejection_details': check_result,
                'direction': None,
                'confidence': 0.0
            },
            'signal_strength': 0.0,
            'market_type': self.market_type
        }
        
        # Track rejection
        self.rejected_opportunities.append({
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc),
            'rejection_type': rejection_type,
            'rejection_details': check_result
        })
        
        return rejection
    
    def determine_agent_bias(self, agent_name: str, agent_data: Dict[str, Any]) -> str:
        """Determine directional bias from agent data"""
        # Implement agent-specific bias determination
        # This would be enhanced with specific logic for each agent type
        return 'neutral'  # Placeholder
    
    def summarize_agent_signals(self, agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize agent signals for logging"""
        return {
            'ict_smc_agents_active': len(agent_signals['ict_smc_agents']),
            'analysis_agents_active': len(agent_signals['analysis_agents']),
            'ml_agents_active': len(agent_signals['ml_agents']),
            'coordination_agents_active': len(agent_signals['coordination_agents']),
            'total_signals': agent_signals['total_active_signals'],
            'avg_ict_strength': agent_signals['ict_smc_summary']['avg_strength']
        }
    
    def calculate_master_signal_strength(self, decision: Dict[str, Any], agent_signals: Dict[str, Any]) -> float:
        """Calculate master coordinator signal strength"""
        if not decision['approved']:
            return 0.0
        
        # Signal strength based on decision quality
        strength_factors = [
            decision['confidence'],
            decision['estimated_win_rate'] / self.target_win_rate,
            min(agent_signals['total_active_signals'] / 15.0, 1.0),  # Up to 15 signals
            agent_signals['ict_smc_summary']['avg_strength']
        ]
        
        return np.mean(strength_factors)
    
    def update_decision_tracking(self, symbol: str, decision: Dict[str, Any], agent_signals: Dict[str, Any]):
        """Update decision tracking"""
        decision_record = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'decision': decision,
            'agent_signals_count': agent_signals['total_active_signals'],
            'market_type': self.market_type
        }
        
        self.trading_decisions.append(decision_record)
        
        # Update performance tracking
        if decision['approved']:
            self.performance_tracking['approved'] += 1
        else:
            self.performance_tracking['rejected'] += 1
        
        # Calculate approval rate
        total_decisions = self.performance_tracking['approved'] + self.performance_tracking['rejected']
        approval_rate = self.performance_tracking['approved'] / total_decisions if total_decisions > 0 else 0
        
        self.logger.info(f"Decision tracking: {self.performance_tracking['approved']}/{total_decisions} approved ({approval_rate:.1%})")
        
        # Limit tracking sizes
        if len(self.trading_decisions) > 200:
            self.trading_decisions = self.trading_decisions[-200:]
        
        if len(self.rejected_opportunities) > 500:
            self.rejected_opportunities = self.rejected_opportunities[-500:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_master_summary(self) -> Dict[str, Any]:
        """Get comprehensive master coordinator summary"""
        total_decisions = self.performance_tracking['approved'] + self.performance_tracking['rejected']
        approval_rate = self.performance_tracking['approved'] / total_decisions if total_decisions > 0 else 0
        
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'decision_tracking': {
                'total_decisions': total_decisions,
                'approved_decisions': self.performance_tracking['approved'],
                'rejected_decisions': self.performance_tracking['rejected'],
                'approval_rate': approval_rate
            },
            'targeting': {
                'target_win_rate': self.target_win_rate,
                'ultra_strict_mode': self.ultra_strict_mode,
                'decision_confidence_threshold': self.decision_confidence_threshold
            },
            'requirements': self.decision_framework['mandatory_requirements'][self.market_type],
            'last_signal_strength': self.get_signal_strength()
        }
    
    def requires_continuous_processing(self) -> bool:
        """Master coordinator doesn't need continuous processing"""
        return False