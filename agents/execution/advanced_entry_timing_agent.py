"""
Advanced Entry Timing Agent
Sophisticated entry timing algorithms for optimal trade execution
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class AdvancedEntryTimingAgent(BaseAgent):
    """
    Advanced Entry Timing Agent - Elevates entry timing from 8/10 to 9/10
    Uses sophisticated algorithms for optimal trade entry execution
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("advanced_entry_timing", config)
        
        # Advanced timing configuration
        self.timing_algorithms = config.get('timing_algorithms', [
            'price_action_confirmation',
            'volume_profile_entry',
            'momentum_acceleration',
            'liquidity_cluster_entry',
            'volatility_breakout_timing',
            'session_transition_entry'
        ])
        
        self.entry_precision_target = config.get('entry_precision_target', 0.95)  # 95% precision
        self.max_entry_delay = config.get('max_entry_delay', 5)  # Max 5 bars delay
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Timing tracking
        self.entry_timing_history = []
        self.timing_performance = {}
        self.precision_metrics = {'accurate_entries': 0, 'total_entries': 0}
        
        # Advanced timing models
        self.timing_models = self.initialize_timing_models()
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Advanced Entry Timing Agent initialized for {self.market_type}")
    
    def initialize_timing_models(self) -> Dict[str, Any]:
        """Initialize sophisticated timing models"""
        return {
            'price_action_model': {
                'confirmation_patterns': ['engulfing', 'pin_bar', 'inside_bar_break'],
                'momentum_threshold': 0.7,
                'volume_confirmation': True
            },
            'volume_profile_model': {
                'poc_proximity_threshold': 0.002,  # 0.2% from Point of Control
                'volume_spike_multiplier': 2.0,
                'profile_strength_min': 0.8
            },
            'momentum_acceleration_model': {
                'acceleration_threshold': 1.5,
                'momentum_consistency_bars': 3,
                'divergence_check': True
            },
            'liquidity_cluster_model': {
                'cluster_strength_min': 0.8,
                'liquidity_confirmation': True,
                'sweep_completion_check': True
            },
            'volatility_breakout_model': {
                'volatility_expansion_min': 1.3,
                'breakout_confirmation_bars': 2,
                'false_breakout_protection': True
            },
            'session_transition_model': {
                'session_overlap_bonus': 1.5,
                'transition_timing_window': 30,  # minutes
                'session_volume_confirmation': True
            }
        }
    
    def apply_market_specific_config(self):
        """Apply market-specific timing configuration"""
        if self.market_type == 'forex':
            # Forex: Session-based timing precision
            self.session_timing_weight = 0.8
            self.spread_timing_consideration = True
            self.news_timing_avoidance = True
            
            # Prioritize session-based algorithms
            self.algorithm_weights = {
                'session_transition_entry': 1.5,
                'liquidity_cluster_entry': 1.4,
                'price_action_confirmation': 1.3,
                'momentum_acceleration': 1.0,
                'volume_profile_entry': 0.8,
                'volatility_breakout_timing': 1.1
            }
            
        elif self.market_type == 'crypto':
            # Crypto: Volume and momentum-based timing
            self.volume_timing_weight = 0.8
            self.whale_activity_timing = True
            self.volatility_timing_optimization = True
            
            # Prioritize volume/momentum algorithms
            self.algorithm_weights = {
                'volume_profile_entry': 1.5,
                'momentum_acceleration': 1.4,
                'volatility_breakout_timing': 1.3,
                'liquidity_cluster_entry': 1.2,
                'price_action_confirmation': 1.1,
                'session_transition_entry': 0.7
            }
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process entry timing analysis
        
        Args:
            data: Dictionary containing market data and confluence signals
            
        Returns:
            Dictionary with optimal entry timing analysis
        """
        required_fields = ['df', 'symbol', 'confluence_approved']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        confluence_approved = data['confluence_approved']
        
        if not confluence_approved:
            return {'entry_timing': 'no_confluence', 'should_enter': False}
        
        try:
            # Run all timing algorithms
            timing_analysis = self.run_timing_algorithms(df, data)
            
            # Calculate optimal entry timing
            optimal_timing = self.calculate_optimal_timing(timing_analysis, df)
            
            # Validate entry precision
            entry_validation = self.validate_entry_precision(optimal_timing, df)
            
            # Calculate timing confidence
            timing_confidence = self.calculate_timing_confidence(timing_analysis, optimal_timing)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'timing_analysis': timing_analysis,
                'optimal_timing': optimal_timing,
                'entry_validation': entry_validation,
                'timing_confidence': timing_confidence,
                'should_enter': optimal_timing['entry_approved'],
                'entry_delay_bars': optimal_timing.get('delay_bars', 0),
                'precision_score': entry_validation['precision_score'],
                'market_type': self.market_type
            }
            
            # Update tracking
            self.update_timing_tracking(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing entry timing for {symbol}: {e}")
            return {'entry_timing': 'error', 'should_enter': False, 'error': str(e)}
    
    def run_timing_algorithms(self, df: pd.DataFrame, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all timing algorithms and collect results"""
        timing_results = {}
        
        # Price Action Confirmation Algorithm
        timing_results['price_action_confirmation'] = self.analyze_price_action_timing(df)
        
        # Volume Profile Entry Algorithm
        timing_results['volume_profile_entry'] = self.analyze_volume_profile_timing(df)
        
        # Momentum Acceleration Algorithm
        timing_results['momentum_acceleration'] = self.analyze_momentum_timing(df)
        
        # Liquidity Cluster Entry Algorithm
        timing_results['liquidity_cluster_entry'] = self.analyze_liquidity_timing(df, data)
        
        # Volatility Breakout Timing Algorithm
        timing_results['volatility_breakout_timing'] = self.analyze_volatility_timing(df)
        
        # Session Transition Entry Algorithm (for forex)
        if self.market_type == 'forex':
            timing_results['session_transition_entry'] = self.analyze_session_timing(df)
        
        return timing_results
    
    def analyze_price_action_timing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price action for optimal entry timing"""
        if len(df) < 5:
            return {'score': 0.0, 'ready': False}
        
        recent_bars = df.iloc[-5:]
        current_bar = df.iloc[-1]
        
        # Check for confirmation patterns
        confirmation_score = 0.0
        
        # Engulfing pattern confirmation
        if len(recent_bars) >= 2:
            prev_bar = recent_bars.iloc[-2]
            if (current_bar['close'] > current_bar['open'] and 
                prev_bar['close'] < prev_bar['open'] and
                current_bar['close'] > prev_bar['open'] and
                current_bar['open'] < prev_bar['close']):
                confirmation_score += 0.3
        
        # Pin bar confirmation
        body_size = abs(current_bar['close'] - current_bar['open'])
        total_range = current_bar['high'] - current_bar['low']
        if total_range > 0:
            body_ratio = body_size / total_range
            if body_ratio < 0.3:  # Small body = pin bar
                confirmation_score += 0.2
        
        # Momentum confirmation
        if len(recent_bars) >= 3:
            momentum = (current_bar['close'] - recent_bars.iloc[-3]['close']) / recent_bars.iloc[-3]['close']
            if abs(momentum) > 0.005:  # 0.5% momentum
                confirmation_score += 0.2
        
        # Volume confirmation
        if 'volume' in df.columns:
            current_volume = current_bar['volume']
            avg_volume = recent_bars['volume'].mean()
            if current_volume > avg_volume * 1.2:
                confirmation_score += 0.3
        
        return {
            'score': min(confirmation_score, 1.0),
            'ready': confirmation_score >= 0.7,
            'confirmation_patterns': confirmation_score,
            'timing_quality': 'excellent' if confirmation_score >= 0.8 else 'good' if confirmation_score >= 0.6 else 'fair'
        }
    
    def analyze_volume_profile_timing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume profile for entry timing"""
        if 'volume' not in df.columns or len(df) < 20:
            return {'score': 0.0, 'ready': False}
        
        # Calculate volume-weighted average price (VWAP)
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        current_price = df['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]
        
        # Distance from VWAP
        vwap_distance = abs(current_price - current_vwap) / current_vwap
        
        # Volume spike analysis
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_spike_ratio = current_volume / avg_volume
        
        # Calculate timing score
        proximity_score = max(0, 1.0 - (vwap_distance / 0.01))  # Closer to VWAP = better
        volume_score = min(volume_spike_ratio / 2.0, 1.0)  # Volume spike = better timing
        
        timing_score = (proximity_score * 0.6 + volume_score * 0.4)
        
        return {
            'score': timing_score,
            'ready': timing_score >= 0.7,
            'vwap_distance': vwap_distance,
            'volume_spike_ratio': volume_spike_ratio,
            'timing_quality': 'excellent' if timing_score >= 0.8 else 'good' if timing_score >= 0.6 else 'fair'
        }
    
    def analyze_momentum_timing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze momentum for entry timing"""
        if len(df) < 10:
            return {'score': 0.0, 'ready': False}
        
        # Calculate momentum indicators
        recent_data = df.iloc[-10:]
        
        # Price momentum
        price_momentum = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        
        # Momentum acceleration
        mid_price = recent_data['close'].iloc[len(recent_data)//2]
        first_half_momentum = (mid_price - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        second_half_momentum = (recent_data['close'].iloc[-1] - mid_price) / mid_price
        
        momentum_acceleration = second_half_momentum / first_half_momentum if first_half_momentum != 0 else 0
        
        # Volume momentum (for crypto)
        if 'volume' in df.columns and self.market_type == 'crypto':
            volume_momentum = (recent_data['volume'].iloc[-3:].mean() - recent_data['volume'].iloc[:3].mean()) / recent_data['volume'].iloc[:3].mean()
        else:
            volume_momentum = 0
        
        # Calculate timing score
        momentum_score = min(abs(price_momentum) / 0.02, 1.0)  # Normalize to 2%
        acceleration_score = min(abs(momentum_acceleration) / 2.0, 1.0) if momentum_acceleration != 0 else 0
        volume_momentum_score = min(abs(volume_momentum) / 1.0, 1.0) if self.market_type == 'crypto' else 0.5
        
        if self.market_type == 'crypto':
            timing_score = (momentum_score * 0.4 + acceleration_score * 0.3 + volume_momentum_score * 0.3)
        else:
            timing_score = (momentum_score * 0.6 + acceleration_score * 0.4)
        
        return {
            'score': timing_score,
            'ready': timing_score >= 0.7,
            'price_momentum': price_momentum,
            'momentum_acceleration': momentum_acceleration,
            'volume_momentum': volume_momentum,
            'timing_quality': 'excellent' if timing_score >= 0.8 else 'good' if timing_score >= 0.6 else 'fair'
        }
    
    def analyze_liquidity_timing(self, df: pd.DataFrame, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze liquidity conditions for optimal entry timing"""
        # Get liquidity data from other agents
        liquidity_data = data.get('liquidity_sweeps', {})
        order_blocks = data.get('order_blocks', {})
        
        timing_score = 0.0
        liquidity_factors = []
        
        # Liquidity sweep timing
        if liquidity_data:
            sweep_signals = liquidity_data.get('swing_sweeps', {})
            if sweep_signals.get('swept_high') or sweep_signals.get('swept_low'):
                liquidity_factors.append(0.8)  # Good timing after sweep
        
        # Order block retest timing
        if order_blocks:
            obs = order_blocks.get('order_blocks', [])
            current_price = df['close'].iloc[-1]
            
            for ob in obs:
                if ob.get('retest') and ob.get('type'):
                    ob_zone = ob.get('zone', (0, 0))
                    if ob_zone[0] <= current_price <= ob_zone[1]:
                        liquidity_factors.append(0.9)  # Excellent timing at OB retest
                        break
        
        # Fair Value Gap proximity
        fvg_data = data.get('fair_value_gaps', {})
        if fvg_data:
            fvgs = fvg_data.get('fvgs', [])
            for fvg in fvgs:
                fvg_zone = fvg.get('zone', (0, 0))
                distance = min(abs(current_price - fvg_zone[0]), abs(current_price - fvg_zone[1]))
                if distance < current_price * 0.005:  # Within 0.5%
                    liquidity_factors.append(0.7)
                    break
        
        timing_score = np.mean(liquidity_factors) if liquidity_factors else 0.3
        
        return {
            'score': timing_score,
            'ready': timing_score >= 0.7,
            'liquidity_factors': liquidity_factors,
            'liquidity_quality': len(liquidity_factors),
            'timing_quality': 'excellent' if timing_score >= 0.8 else 'good' if timing_score >= 0.6 else 'fair'
        }
    
    def analyze_volatility_timing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volatility for breakout entry timing"""
        if 'atr' not in df.columns or len(df) < 20:
            return {'score': 0.0, 'ready': False}
        
        current_atr = df['atr'].iloc[-1]
        avg_atr = df['atr'].rolling(20).mean().iloc[-1]
        
        # Volatility expansion
        volatility_expansion = current_atr / avg_atr if avg_atr > 0 else 1.0
        
        # Recent range analysis
        recent_range = df['high'].iloc[-1] - df['low'].iloc[-1]
        avg_range = (df['high'] - df['low']).rolling(10).mean().iloc[-1]
        range_expansion = recent_range / avg_range if avg_range > 0 else 1.0
        
        # Volume confirmation during volatility
        volume_confirmation = 0.5
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_confirmation = min(current_volume / avg_volume / 2.0, 1.0)
        
        # Calculate timing score
        volatility_score = min(volatility_expansion / 1.5, 1.0)
        range_score = min(range_expansion / 1.3, 1.0)
        
        timing_score = (volatility_score * 0.4 + range_score * 0.3 + volume_confirmation * 0.3)
        
        return {
            'score': timing_score,
            'ready': timing_score >= 0.7,
            'volatility_expansion': volatility_expansion,
            'range_expansion': range_expansion,
            'volume_confirmation': volume_confirmation,
            'timing_quality': 'excellent' if timing_score >= 0.8 else 'good' if timing_score >= 0.6 else 'fair'
        }
    
    def analyze_session_timing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze session timing for forex entries"""
        if self.market_type != 'forex' or not hasattr(df.index[-1], 'hour'):
            return {'score': 0.0, 'ready': False}
        
        current_hour = df.index[-1].hour
        current_minute = df.index[-1].minute
        
        # Session timing analysis
        session_scores = {
            'london_open': self.calculate_session_score(current_hour, current_minute, 8, 0, 30),
            'ny_open': self.calculate_session_score(current_hour, current_minute, 13, 0, 30),
            'london_ny_overlap': 1.0 if 13 <= current_hour <= 16 else 0.0,
            'session_close': max(
                self.calculate_session_score(current_hour, current_minute, 17, 0, 30),
                self.calculate_session_score(current_hour, current_minute, 22, 0, 30)
            )
        }
        
        # Overall session timing score
        timing_score = max(session_scores.values())
        
        # Session transition bonus
        transition_bonus = 0.0
        if any(score > 0.5 for score in session_scores.values()):
            transition_bonus = 0.2
        
        final_score = min(timing_score + transition_bonus, 1.0)
        
        return {
            'score': final_score,
            'ready': final_score >= 0.7,
            'session_scores': session_scores,
            'current_session_context': self.get_session_context(current_hour),
            'timing_quality': 'excellent' if final_score >= 0.8 else 'good' if final_score >= 0.6 else 'fair'
        }
    
    def calculate_session_score(self, current_hour: int, current_minute: int, 
                               target_hour: int, target_minute: int, window_minutes: int) -> float:
        """Calculate proximity score to session event"""
        current_total_minutes = current_hour * 60 + current_minute
        target_total_minutes = target_hour * 60 + target_minute
        
        distance_minutes = abs(current_total_minutes - target_total_minutes)
        
        if distance_minutes <= window_minutes:
            return 1.0 - (distance_minutes / window_minutes)
        else:
            return 0.0
    
    def get_session_context(self, hour: int) -> str:
        """Get current session context"""
        if 13 <= hour <= 16:
            return 'london_ny_overlap'
        elif 8 <= hour <= 17:
            return 'london_session'
        elif 13 <= hour <= 22:
            return 'ny_session'
        elif 22 <= hour <= 6:
            return 'asian_session'
        else:
            return 'off_hours'
    
    def calculate_optimal_timing(self, timing_analysis: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate optimal entry timing from all algorithms"""
        # Weight algorithm scores by market-specific weights
        weighted_scores = []
        algorithm_details = {}
        
        for algorithm, result in timing_analysis.items():
            if isinstance(result, dict) and 'score' in result:
                weight = self.algorithm_weights.get(algorithm, 1.0)
                weighted_score = result['score'] * weight
                weighted_scores.append(weighted_score)
                
                algorithm_details[algorithm] = {
                    'score': result['score'],
                    'weight': weight,
                    'weighted_score': weighted_score,
                    'ready': result.get('ready', False),
                    'quality': result.get('timing_quality', 'unknown')
                }
        
        # Calculate overall timing score
        overall_score = np.mean(weighted_scores) if weighted_scores else 0.0
        
        # Determine if entry should proceed
        ready_algorithms = sum(1 for details in algorithm_details.values() if details['ready'])
        total_algorithms = len(algorithm_details)
        
        # Entry approval logic
        entry_approved = (
            overall_score >= 0.75 and  # High overall score
            ready_algorithms >= total_algorithms * 0.6  # 60%+ algorithms ready
        )
        
        # Calculate optimal delay (if any)
        delay_bars = 0
        if not entry_approved and overall_score >= 0.6:
            # Entry might be good in 1-2 bars
            delay_bars = min(2, int((0.75 - overall_score) / 0.05))
        
        return {
            'overall_score': overall_score,
            'entry_approved': entry_approved,
            'ready_algorithms': ready_algorithms,
            'total_algorithms': total_algorithms,
            'algorithm_consensus': ready_algorithms / total_algorithms if total_algorithms > 0 else 0,
            'delay_bars': delay_bars,
            'algorithm_details': algorithm_details,
            'timing_confidence': self.calculate_algorithm_confidence(algorithm_details)
        }
    
    def calculate_algorithm_confidence(self, algorithm_details: Dict[str, Any]) -> float:
        """Calculate confidence in timing decision"""
        if not algorithm_details:
            return 0.0
        
        # High-quality algorithms contribute more to confidence
        excellent_algorithms = sum(1 for details in algorithm_details.values() 
                                 if details['quality'] == 'excellent')
        good_algorithms = sum(1 for details in algorithm_details.values() 
                            if details['quality'] == 'good')
        total_algorithms = len(algorithm_details)
        
        confidence = (excellent_algorithms * 1.0 + good_algorithms * 0.7) / total_algorithms
        
        return min(confidence, 1.0)
    
    def validate_entry_precision(self, optimal_timing: Dict[str, Any], df: pd.DataFrame) -> Dict[str, Any]:
        """Validate entry precision and accuracy"""
        precision_factors = []
        
        # Algorithm consensus precision
        consensus = optimal_timing['algorithm_consensus']
        precision_factors.append(consensus)
        
        # Timing confidence precision
        confidence = optimal_timing['timing_confidence']
        precision_factors.append(confidence)
        
        # Market condition precision
        market_precision = self.assess_market_condition_precision(df)
        precision_factors.append(market_precision)
        
        # Overall precision score
        precision_score = np.mean(precision_factors)
        
        # Precision validation
        precision_validated = precision_score >= self.entry_precision_target
        
        return {
            'precision_score': precision_score,
            'precision_validated': precision_validated,
            'precision_target': self.entry_precision_target,
            'precision_factors': {
                'algorithm_consensus': consensus,
                'timing_confidence': confidence,
                'market_condition_precision': market_precision
            }
        }
    
    def assess_market_condition_precision(self, df: pd.DataFrame) -> float:
        """Assess precision of market conditions for entry"""
        precision_factors = []
        
        # Volatility precision (stable volatility = better precision)
        if 'atr' in df.columns and len(df) >= 20:
            current_atr = df['atr'].iloc[-1]
            avg_atr = df['atr'].rolling(20).mean().iloc[-1]
            volatility_stability = 1.0 - abs(current_atr - avg_atr) / avg_atr if avg_atr > 0 else 0.5
            precision_factors.append(volatility_stability)
        
        # Price action precision (clean price action = better precision)
        if len(df) >= 5:
            recent_closes = df['close'].iloc[-5:]
            price_smoothness = 1.0 - (recent_closes.std() / recent_closes.mean()) if recent_closes.mean() > 0 else 0.5
            precision_factors.append(min(price_smoothness, 1.0))
        
        # Market structure precision
        if len(df) >= 10:
            trend_consistency = self.calculate_trend_consistency(df.iloc[-10:])
            precision_factors.append(trend_consistency)
        
        return np.mean(precision_factors) if precision_factors else 0.5
    
    def calculate_trend_consistency(self, df: pd.DataFrame) -> float:
        """Calculate trend consistency for precision assessment"""
        if len(df) < 5:
            return 0.5
        
        # Calculate directional consistency
        price_changes = df['close'].diff().dropna()
        
        if len(price_changes) == 0:
            return 0.5
        
        positive_changes = sum(1 for change in price_changes if change > 0)
        negative_changes = sum(1 for change in price_changes if change < 0)
        
        # Consistency = dominance of one direction
        consistency = abs(positive_changes - negative_changes) / len(price_changes)
        
        return consistency
    
    def calculate_timing_confidence(self, timing_analysis: Dict[str, Any], optimal_timing: Dict[str, Any]) -> float:
        """Calculate overall timing confidence"""
        confidence_factors = []
        
        # Overall score confidence
        overall_score = optimal_timing['overall_score']
        confidence_factors.append(overall_score)
        
        # Algorithm consensus confidence
        consensus = optimal_timing['algorithm_consensus']
        confidence_factors.append(consensus)
        
        # Individual algorithm confidence
        algorithm_details = optimal_timing['algorithm_details']
        excellent_ratio = sum(1 for details in algorithm_details.values() 
                            if details['quality'] == 'excellent') / len(algorithm_details)
        confidence_factors.append(excellent_ratio)
        
        # Market-specific confidence boost
        if self.market_type == 'forex':
            session_timing = timing_analysis.get('session_transition_entry', {})
            if session_timing.get('score', 0) > 0.8:
                confidence_factors.append(0.9)  # High confidence during good session timing
        
        elif self.market_type == 'crypto':
            volume_timing = timing_analysis.get('volume_profile_entry', {})
            if volume_timing.get('score', 0) > 0.8:
                confidence_factors.append(0.9)  # High confidence with good volume timing
        
        return np.mean(confidence_factors)
    
    def update_timing_tracking(self, timing_results: Dict[str, Any]):
        """Update timing performance tracking"""
        timing_entry = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': timing_results.get('symbol'),
            'timing_confidence': timing_results['timing_confidence'],
            'precision_score': timing_results['entry_validation']['precision_score'],
            'entry_approved': timing_results['should_enter'],
            'market_type': self.market_type
        }
        
        self.entry_timing_history.append(timing_entry)
        
        # Update precision metrics
        if timing_results['should_enter']:
            self.precision_metrics['total_entries'] += 1
            if timing_results['entry_validation']['precision_validated']:
                self.precision_metrics['accurate_entries'] += 1
        
        # Calculate precision rate
        if self.precision_metrics['total_entries'] > 0:
            precision_rate = self.precision_metrics['accurate_entries'] / self.precision_metrics['total_entries']
            self.logger.info(f"Entry timing precision: {self.precision_metrics['accurate_entries']}/{self.precision_metrics['total_entries']} = {precision_rate:.1%}")
        
        # Limit tracking size
        if len(self.entry_timing_history) > 200:
            self.entry_timing_history = self.entry_timing_history[-200:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on timing precision"""
        if self.precision_metrics['total_entries'] == 0:
            return 0.5
        
        precision_rate = self.precision_metrics['accurate_entries'] / self.precision_metrics['total_entries']
        return precision_rate
    
    def requires_continuous_processing(self) -> bool:
        """Entry timing agent doesn't need continuous processing"""
        return False