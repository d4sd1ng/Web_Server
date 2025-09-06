"""
Confluence Coordinator Agent
Coordinates pattern confluence for >90% win rate targeting
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class ConfluenceCoordinatorAgent(BaseAgent):
    """
    Master coordination agent for pattern confluence
    Ensures minimum confluence requirements for >90% win rate
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("confluence_coordinator", config)
        
        # Confluence requirements for >90% win rate
        self.min_confluence_patterns = config.get('min_confluence_patterns', {
            'forex': 6,    # Forex needs more confluence
            'crypto': 5    # Crypto can work with slightly less
        })
        
        # Pattern weights for confluence scoring
        self.pattern_weights = config.get('pattern_weights', {
            # Core ICT/SMC patterns (highest weight)
            'fair_value_gaps': 1.5,
            'order_blocks': 1.5,
            'market_structure': 1.8,  # MSS very important
            'liquidity_sweeps': 1.3,
            'premium_discount': 1.2,
            'ote': 1.4,
            
            # Advanced patterns (high weight)
            'breaker_blocks': 1.3,
            'displacement': 1.4,
            'engulfing': 1.2,
            'mitigation_blocks': 1.1,
            
            # Confluence patterns (very high weight)
            'pattern_cluster': 2.0,  # Highest weight
            'htf_confluence': 1.8,
            'killzone': 1.6,
            
            # Supporting patterns (moderate weight)
            'sof': 1.1,
            'swing_failure_pattern': 1.0,
            'judas_swing': 1.2,
            'turtle_soup': 1.1,
            'imbalance': 1.0,
            'momentum_shift': 1.3,
            
            # Analysis patterns (supporting weight)
            'volume_analysis': 1.2,
            'session_analysis': 1.0,
            'technical_indicators': 0.8,
            'sentiment': 0.7
        })
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Confluence tracking
        self.confluence_history = []
        self.high_quality_setups = []
        self.rejected_setups = []
        
        # Performance tracking for >90% win rate
        self.setup_performance = {'wins': 0, 'losses': 0, 'total': 0, 'win_rate': 0.0}
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Confluence Coordinator initialized for {self.market_type} - targeting >90% win rate")
    
    def apply_market_specific_config(self):
        """Apply market-specific confluence requirements"""
        if self.market_type == 'forex':
            # Forex: Stricter requirements due to institutional competition
            self.min_confluence_score = 8.0  # Very high score required
            self.session_confluence_bonus = 2.0  # Session timing very important
            self.htf_confluence_required = True
        elif self.market_type == 'crypto':
            # Crypto: High requirements but slightly more flexible
            self.min_confluence_score = 7.0  # High score required
            self.volume_confluence_bonus = 1.5  # Volume very important
            self.htf_confluence_required = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all agent signals to determine confluence quality
        
        Args:
            data: Dictionary containing all agent results
            
        Returns:
            Dictionary with confluence analysis and trading decision
        """
        required_fields = ['symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        
        try:
            # Collect all agent signals
            agent_signals = self.collect_agent_signals(data)
            
            # Calculate confluence score
            confluence_analysis = self.calculate_confluence_score(agent_signals)
            
            # Apply >90% win rate filters
            trading_decision = self.apply_winrate_filters(confluence_analysis, agent_signals, data)
            
            # Update tracking
            self.update_confluence_tracking(confluence_analysis, trading_decision, symbol)
            
            # Calculate signal strength
            signal_strength = self.calculate_confluence_signal_strength(confluence_analysis, trading_decision)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agent_signals': agent_signals,
                'confluence_analysis': confluence_analysis,
                'trading_decision': trading_decision,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'win_rate_targeting': '>90%',
                'setup_quality': self.assess_setup_quality(confluence_analysis, trading_decision)
            }
            
            # Publish high-quality setups only
            if trading_decision['approved_for_trading']:
                self.publish("high_quality_setup", {
                    'symbol': symbol,
                    'direction': trading_decision['direction'],
                    'confluence_score': confluence_analysis['total_score'],
                    'expected_win_rate': trading_decision['expected_win_rate'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing confluence data for {symbol}: {e}")
            return {'confluence_analysis': {}, 'signal_strength': 0.0, 'error': str(e)}
    
    def collect_agent_signals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect and organize signals from all agents
        """
        agent_signals = {
            'ict_smc_signals': {},
            'analysis_signals': {},
            'ml_signals': {},
            'total_active_patterns': 0,
            'bullish_patterns': 0,
            'bearish_patterns': 0
        }
        
        # ICT/SMC agent signals
        ict_smc_agents = [
            'fair_value_gaps', 'order_blocks', 'market_structure', 'liquidity_sweeps',
            'premium_discount', 'ote', 'breaker_blocks', 'sof', 'displacement',
            'engulfing', 'mitigation_blocks', 'killzone', 'pattern_cluster',
            'swing_failure_pattern', 'htf_confluence', 'judas_swing', 'power_of_three',
            'market_maker_model', 'turtle_soup', 'imbalance', 'momentum_shift'
        ]
        
        for agent_name in ict_smc_agents:
            if agent_name in data:
                agent_data = data[agent_name]
                signal_strength = agent_data.get('signal_strength', 0.0)
                
                if signal_strength > 0.5:  # Only consider strong signals
                    agent_signals['ict_smc_signals'][agent_name] = {
                        'strength': signal_strength,
                        'data': agent_data,
                        'weight': self.pattern_weights.get(agent_name, 1.0)
                    }
                    agent_signals['total_active_patterns'] += 1
                    
                    # Count directional bias
                    bias = self.determine_agent_bias(agent_name, agent_data)
                    if bias == 'bullish':
                        agent_signals['bullish_patterns'] += 1
                    elif bias == 'bearish':
                        agent_signals['bearish_patterns'] += 1
        
        # Analysis agent signals
        analysis_agents = ['volume_analysis', 'session_analysis', 'technical_indicators']
        for agent_name in analysis_agents:
            if agent_name in data:
                agent_data = data[agent_name]
                signal_strength = agent_data.get('signal_strength', 0.0)
                
                agent_signals['analysis_signals'][agent_name] = {
                    'strength': signal_strength,
                    'data': agent_data,
                    'weight': self.pattern_weights.get(agent_name, 0.8)
                }
        
        # ML signals
        if 'ml_ensemble' in data:
            ml_data = data['ml_ensemble']
            agent_signals['ml_signals'] = {
                'ensemble_prediction': ml_data.get('ensemble_prediction', {}),
                'final_decision': ml_data.get('final_decision', {}),
                'model_agreement': ml_data.get('model_agreement', 0.0)
            }
        
        return agent_signals
    
    def determine_agent_bias(self, agent_name: str, agent_data: Dict[str, Any]) -> str:
        """Determine directional bias from agent data"""
        # Agent-specific bias determination
        if agent_name == 'fair_value_gaps':
            fvgs = agent_data.get('fvgs', [])
            bullish_fvgs = sum(1 for fvg in fvgs if fvg.get('type') == 'bullish')
            bearish_fvgs = sum(1 for fvg in fvgs if fvg.get('type') == 'bearish')
            if bullish_fvgs > bearish_fvgs:
                return 'bullish'
            elif bearish_fvgs > bullish_fvgs:
                return 'bearish'
        
        elif agent_name == 'market_structure':
            if agent_data.get('bullish_mss', False) or agent_data.get('bos_bull', False):
                return 'bullish'
            elif agent_data.get('bearish_mss', False) or agent_data.get('bos_bear', False):
                return 'bearish'
        
        elif agent_name == 'premium_discount':
            pd_zone = agent_data.get('current_pd_zone', 'equilibrium')
            if pd_zone == 'discount':
                return 'bullish'
            elif pd_zone == 'premium':
                return 'bearish'
        
        elif agent_name == 'displacement':
            if agent_data.get('bullish_displacement', False):
                return 'bullish'
            elif agent_data.get('bearish_displacement', False):
                return 'bearish'
        
        # Add more agent-specific bias logic...
        
        return 'neutral'
    
    def calculate_confluence_score(self, agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive confluence score for >90% win rate
        """
        confluence_analysis = {
            'total_score': 0.0,
            'ict_smc_score': 0.0,
            'analysis_score': 0.0,
            'ml_score': 0.0,
            'pattern_count': agent_signals['total_active_patterns'],
            'directional_bias': 'neutral',
            'confluence_quality': 'poor'
        }
        
        # Calculate ICT/SMC confluence score
        ict_smc_score = 0.0
        for agent_name, signal_data in agent_signals['ict_smc_signals'].items():
            weighted_strength = signal_data['strength'] * signal_data['weight']
            ict_smc_score += weighted_strength
        
        confluence_analysis['ict_smc_score'] = ict_smc_score
        
        # Calculate analysis score
        analysis_score = 0.0
        for agent_name, signal_data in agent_signals['analysis_signals'].items():
            weighted_strength = signal_data['strength'] * signal_data['weight']
            analysis_score += weighted_strength
        
        confluence_analysis['analysis_score'] = analysis_score
        
        # Calculate ML score
        ml_signals = agent_signals['ml_signals']
        if ml_signals:
            ml_agreement = ml_signals.get('model_agreement', 0.0)
            final_decision = ml_signals.get('final_decision', {})
            ml_confidence = final_decision.get('confidence', 0.0)
            
            confluence_analysis['ml_score'] = (ml_agreement * 0.6 + ml_confidence * 0.4) * 3.0  # Weight ML highly
        
        # Total confluence score
        confluence_analysis['total_score'] = (confluence_analysis['ict_smc_score'] + 
                                            confluence_analysis['analysis_score'] + 
                                            confluence_analysis['ml_score'])
        
        # Determine directional bias
        bullish_patterns = agent_signals['bullish_patterns']
        bearish_patterns = agent_signals['bearish_patterns']
        
        if bullish_patterns > bearish_patterns * 1.5:
            confluence_analysis['directional_bias'] = 'bullish'
        elif bearish_patterns > bullish_patterns * 1.5:
            confluence_analysis['directional_bias'] = 'bearish'
        else:
            confluence_analysis['directional_bias'] = 'neutral'
        
        # Assess confluence quality
        confluence_analysis['confluence_quality'] = self.assess_confluence_quality(confluence_analysis)
        
        return confluence_analysis
    
    def assess_confluence_quality(self, confluence_analysis: Dict[str, Any]) -> str:
        """Assess overall confluence quality"""
        total_score = confluence_analysis['total_score']
        pattern_count = confluence_analysis['pattern_count']
        
        min_patterns = self.min_confluence_patterns[self.market_type]
        
        if total_score >= self.min_confluence_score and pattern_count >= min_patterns:
            return 'excellent'  # >90% win rate quality
        elif total_score >= self.min_confluence_score * 0.8 and pattern_count >= min_patterns - 1:
            return 'good'       # 80-90% win rate quality
        elif total_score >= self.min_confluence_score * 0.6:
            return 'fair'       # 70-80% win rate quality
        else:
            return 'poor'       # <70% win rate quality
    
    def apply_winrate_filters(self, confluence_analysis: Dict[str, Any], 
                            agent_signals: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply strict filters for >90% win rate targeting
        """
        decision = {
            'approved_for_trading': False,
            'direction': None,
            'expected_win_rate': 0.0,
            'rejection_reasons': [],
            'quality_score': 0.0,
            'filters_passed': [],
            'filters_failed': []
        }
        
        # Filter 1: Minimum confluence score
        if confluence_analysis['total_score'] >= self.min_confluence_score:
            decision['filters_passed'].append('confluence_score_passed')
        else:
            decision['filters_failed'].append('confluence_score_failed')
            decision['rejection_reasons'].append(f"Confluence score too low: {confluence_analysis['total_score']:.2f}/{self.min_confluence_score}")
        
        # Filter 2: Minimum pattern count
        min_patterns = self.min_confluence_patterns[self.market_type]
        if confluence_analysis['pattern_count'] >= min_patterns:
            decision['filters_passed'].append('pattern_count_passed')
        else:
            decision['filters_failed'].append('pattern_count_failed')
            decision['rejection_reasons'].append(f"Insufficient patterns: {confluence_analysis['pattern_count']}/{min_patterns}")
        
        # Filter 3: Directional consistency
        if confluence_analysis['directional_bias'] != 'neutral':
            decision['filters_passed'].append('directional_bias_passed')
            decision['direction'] = confluence_analysis['directional_bias']
        else:
            decision['filters_failed'].append('directional_bias_failed')
            decision['rejection_reasons'].append("No clear directional bias")
        
        # Filter 4: HTF confluence requirement
        htf_signals = agent_signals['ict_smc_signals'].get('htf_confluence', {})
        if self.htf_confluence_required:
            if htf_signals and htf_signals['strength'] > 0.7:
                decision['filters_passed'].append('htf_confluence_passed')
            else:
                decision['filters_failed'].append('htf_confluence_failed')
                decision['rejection_reasons'].append("HTF confluence not confirmed")
        
        # Filter 5: ML ensemble agreement
        ml_signals = agent_signals['ml_signals']
        if ml_signals:
            ml_decision = ml_signals.get('final_decision', {})
            if ml_decision.get('should_trade', False) and ml_decision.get('confidence', 0) > 0.8:
                decision['filters_passed'].append('ml_ensemble_passed')
            else:
                decision['filters_failed'].append('ml_ensemble_failed')
                decision['rejection_reasons'].append("ML ensemble not confident enough")
        else:
            decision['filters_failed'].append('ml_ensemble_missing')
            decision['rejection_reasons'].append("No ML ensemble data")
        
        # Filter 6: Market-specific requirements
        market_filter = self.apply_market_specific_filters(agent_signals, data)
        if market_filter['passed']:
            decision['filters_passed'].extend(market_filter['passed_filters'])
        else:
            decision['filters_failed'].extend(market_filter['failed_filters'])
            decision['rejection_reasons'].extend(market_filter['rejection_reasons'])
        
        # Final decision
        if len(decision['filters_failed']) == 0:
            decision['approved_for_trading'] = True
            decision['quality_score'] = confluence_analysis['total_score']
            decision['expected_win_rate'] = self.estimate_setup_win_rate(confluence_analysis, decision)
            
            self.logger.info(f"HIGH QUALITY SETUP APPROVED: {symbol} {decision['direction']} - Score: {decision['quality_score']:.2f}, Expected Win Rate: {decision['expected_win_rate']:.1%}")
        
        else:
            self.logger.debug(f"Setup rejected for {symbol}: {', '.join(decision['rejection_reasons'])}")
        
        return decision
    
    def apply_market_specific_filters(self, agent_signals: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply market-specific filters"""
        if self.market_type == 'forex':
            return self.apply_forex_filters(agent_signals, data)
        elif self.market_type == 'crypto':
            return self.apply_crypto_filters(agent_signals, data)
        
        return {'passed': True, 'passed_filters': [], 'failed_filters': [], 'rejection_reasons': []}
    
    def apply_forex_filters(self, agent_signals: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply forex-specific filters for >90% win rate"""
        result = {'passed': True, 'passed_filters': [], 'failed_filters': [], 'rejection_reasons': []}
        
        # Session quality requirement
        session_signals = agent_signals['analysis_signals'].get('session_analysis', {})
        if session_signals:
            session_quality = session_signals.get('data', {}).get('session_analysis', {}).get('session_quality', 0.0)
            if session_quality >= 0.8:
                result['passed_filters'].append('forex_session_quality')
            else:
                result['passed'] = False
                result['failed_filters'].append('forex_session_quality')
                result['rejection_reasons'].append(f"Poor forex session quality: {session_quality:.2f}")
        
        # Killzone requirement
        killzone_signals = agent_signals['ict_smc_signals'].get('killzone', {})
        if killzone_signals and killzone_signals['strength'] > 0.6:
            result['passed_filters'].append('forex_killzone')
        else:
            result['passed'] = False
            result['failed_filters'].append('forex_killzone')
            result['rejection_reasons'].append("Not in valid forex killzone")
        
        return result
    
    def apply_crypto_filters(self, agent_signals: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply crypto-specific filters for >90% win rate"""
        result = {'passed': True, 'passed_filters': [], 'failed_filters': [], 'rejection_reasons': []}
        
        # Volume confirmation requirement
        volume_signals = agent_signals['analysis_signals'].get('volume_analysis', {})
        if volume_signals:
            volume_data = volume_signals.get('data', {})
            volume_spike = volume_data.get('volume_spike', False)
            if volume_spike:
                result['passed_filters'].append('crypto_volume_confirmation')
            else:
                result['passed'] = False
                result['failed_filters'].append('crypto_volume_confirmation')
                result['rejection_reasons'].append("No volume confirmation for crypto trade")
        
        # Momentum confirmation
        momentum_signals = agent_signals['ict_smc_signals'].get('momentum_shift', {})
        if momentum_signals and momentum_signals['strength'] > 0.6:
            result['passed_filters'].append('crypto_momentum')
        else:
            result['passed'] = False
            result['failed_filters'].append('crypto_momentum')
            result['rejection_reasons'].append("Insufficient momentum for crypto trade")
        
        return result
    
    def estimate_setup_win_rate(self, confluence_analysis: Dict[str, Any], decision: Dict[str, Any]) -> float:
        """
        Estimate win rate for approved setup
        """
        base_win_rate = 0.75  # Start with 75%
        
        # Confluence score bonus
        score_bonus = min((confluence_analysis['total_score'] - self.min_confluence_score) * 0.02, 0.15)
        
        # Pattern count bonus
        min_patterns = self.min_confluence_patterns[self.market_type]
        pattern_bonus = min((confluence_analysis['pattern_count'] - min_patterns) * 0.02, 0.1)
        
        # Quality bonus
        quality = confluence_analysis['confluence_quality']
        quality_bonuses = {'excellent': 0.15, 'good': 0.1, 'fair': 0.05, 'poor': 0.0}
        quality_bonus = quality_bonuses.get(quality, 0.0)
        
        # Filter bonus (all filters passed)
        filter_bonus = len(decision['filters_passed']) * 0.01
        
        estimated_win_rate = base_win_rate + score_bonus + pattern_bonus + quality_bonus + filter_bonus
        
        return min(estimated_win_rate, 0.95)  # Cap at 95%
    
    def assess_setup_quality(self, confluence_analysis: Dict[str, Any], trading_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall setup quality"""
        return {
            'quality_rating': confluence_analysis['confluence_quality'],
            'confluence_score': confluence_analysis['total_score'],
            'pattern_count': confluence_analysis['pattern_count'],
            'directional_clarity': confluence_analysis['directional_bias'],
            'trading_approved': trading_decision['approved_for_trading'],
            'expected_win_rate': trading_decision.get('expected_win_rate', 0.0),
            'quality_factors': {
                'ict_smc_strength': confluence_analysis['ict_smc_score'],
                'analysis_support': confluence_analysis['analysis_score'],
                'ml_confirmation': confluence_analysis['ml_score']
            }
        }
    
    def calculate_confluence_signal_strength(self, confluence_analysis: Dict[str, Any], 
                                           trading_decision: Dict[str, Any]) -> float:
        """
        Calculate confluence coordinator signal strength
        """
        if not trading_decision['approved_for_trading']:
            return 0.0  # No signal if not approved
        
        strength_factors = []
        
        # Confluence score strength
        score_strength = min(confluence_analysis['total_score'] / (self.min_confluence_score * 1.5), 1.0)
        strength_factors.append(score_strength)
        
        # Quality strength
        quality = confluence_analysis['confluence_quality']
        quality_strengths = {'excellent': 1.0, 'good': 0.8, 'fair': 0.6, 'poor': 0.3}
        quality_strength = quality_strengths.get(quality, 0.3)
        strength_factors.append(quality_strength)
        
        # Expected win rate strength
        expected_win_rate = trading_decision.get('expected_win_rate', 0.0)
        win_rate_strength = min(expected_win_rate / 0.9, 1.0)  # Normalize to 90%
        strength_factors.append(win_rate_strength)
        
        # Filter pass rate
        total_filters = len(trading_decision['filters_passed']) + len(trading_decision['filters_failed'])
        filter_strength = len(trading_decision['filters_passed']) / total_filters if total_filters > 0 else 0
        strength_factors.append(filter_strength)
        
        return np.mean(strength_factors)
    
    def update_confluence_tracking(self, confluence_analysis: Dict[str, Any], 
                                 trading_decision: Dict[str, Any], symbol: str):
        """Update confluence tracking for performance monitoring"""
        confluence_entry = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'confluence_analysis': confluence_analysis,
            'trading_decision': trading_decision,
            'market_type': self.market_type
        }
        
        self.confluence_history.append(confluence_entry)
        
        # Track high-quality vs rejected setups
        if trading_decision['approved_for_trading']:
            self.high_quality_setups.append(confluence_entry)
        else:
            self.rejected_setups.append(confluence_entry)
        
        # Limit tracking sizes
        if len(self.confluence_history) > 500:
            self.confluence_history = self.confluence_history[-500:]
        
        if len(self.high_quality_setups) > 100:
            self.high_quality_setups = self.high_quality_setups[-100:]
        
        if len(self.rejected_setups) > 200:
            self.rejected_setups = self.rejected_setups[-200:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_confluence_summary(self) -> Dict[str, Any]:
        """Get comprehensive confluence summary"""
        approval_rate = len(self.high_quality_setups) / (len(self.high_quality_setups) + len(self.rejected_setups)) if (self.high_quality_setups or self.rejected_setups) else 0
        
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'confluence_history_count': len(self.confluence_history),
            'high_quality_setups_count': len(self.high_quality_setups),
            'rejected_setups_count': len(self.rejected_setups),
            'setup_approval_rate': approval_rate,
            'current_win_rate': self.setup_performance['win_rate'],
            'min_confluence_score': self.min_confluence_score,
            'min_patterns_required': self.min_confluence_patterns[self.market_type],
            'last_signal_strength': self.get_signal_strength(),
            'targeting': '>90% win rate through strict confluence'
        }
    
    def update_setup_performance(self, symbol: str, direction: str, outcome: str):
        """Update setup performance tracking"""
        self.setup_performance['total'] += 1
        
        if outcome == 'win':
            self.setup_performance['wins'] += 1
        elif outcome == 'loss':
            self.setup_performance['losses'] += 1
        
        # Calculate win rate
        if self.setup_performance['total'] > 0:
            self.setup_performance['win_rate'] = self.setup_performance['wins'] / self.setup_performance['total']
        
        self.logger.info(f"Setup performance updated: {self.setup_performance['wins']}/{self.setup_performance['total']} = {self.setup_performance['win_rate']:.1%}")
    
    def requires_continuous_processing(self) -> bool:
        """Confluence coordinator doesn't need continuous processing"""
        return False