"""
Momentum Shift Agent
Detects momentum shifts and trend changes using existing functions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class MomentumShiftAgent(ICTSMCAgent):
    """
    Specialized agent for Momentum Shift detection
    Uses existing momentum analysis functions from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("momentum_shift", config)
        
        # Momentum configuration
        self.momentum_window = config.get('momentum_window', 10)
        self.shift_threshold = config.get('shift_threshold', 0.005)  # 0.5%
        self.confirmation_bars = config.get('confirmation_bars', 3)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Momentum tracking
        self.momentum_history = []
        self.shift_events = []
        self.trend_changes = []
        self.current_momentum = 'neutral'
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Momentum Shift Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific momentum configuration"""
        if self.market_type == 'forex':
            # Forex: Smaller momentum shifts, longer confirmation
            self.shift_threshold = max(self.shift_threshold, 0.003)  # 0.3%
            self.confirmation_bars = max(self.confirmation_bars, 5)
            self.session_momentum = True
        elif self.market_type == 'crypto':
            # Crypto: Larger momentum shifts, faster confirmation
            self.shift_threshold = min(self.shift_threshold, 0.008)  # 0.8%
            self.confirmation_bars = min(self.confirmation_bars, 3)
            self.session_momentum = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect momentum shifts
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with momentum shift analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.momentum_window + 5:
            return {'momentum_shift': False, 'signal_strength': 0.0}
        
        try:
            # Calculate current momentum
            current_momentum = self.calculate_momentum(df)
            
            # Detect momentum shifts
            momentum_shift = self.detect_momentum_shift(df, current_momentum)
            
            # Analyze momentum patterns
            momentum_analysis = self.analyze_momentum_patterns(df, current_momentum)
            
            # Detect trend changes
            trend_changes = self.detect_trend_changes(df, momentum_shift)
            
            # Update tracking
            self.update_momentum_tracking(current_momentum, momentum_shift, trend_changes)
            
            # Calculate signal strength
            signal_strength = self.calculate_momentum_signal_strength(
                momentum_shift, momentum_analysis, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_momentum': current_momentum,
                'momentum_shift': momentum_shift,
                'momentum_analysis': momentum_analysis,
                'trend_changes': trend_changes,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'momentum_implications': self.get_momentum_implications(
                    momentum_shift, trend_changes, current_momentum
                )
            }
            
            # Publish momentum shift signals
            if momentum_shift['shift_detected']:
                self.publish("momentum_shift_detected", {
                    'symbol': symbol,
                    'shift_type': momentum_shift['shift_type'],
                    'new_momentum': momentum_shift['new_momentum'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing momentum shift data for {symbol}: {e}")
            return {'momentum_shift': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def calculate_momentum(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate current momentum using multiple methods
        """
        if len(df) < self.momentum_window:
            return {'momentum': 'unknown', 'strength': 0.0}
        
        momentum_indicators = {}
        
        # Price momentum
        recent_data = df.iloc[-self.momentum_window:]
        price_momentum = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        momentum_indicators['price_momentum'] = price_momentum
        
        # Volume momentum
        if 'volume' in df.columns:
            recent_volume = recent_data['volume'].mean()
            historical_volume = df['volume'].rolling(self.momentum_window * 2).mean().iloc[-1]
            volume_momentum = (recent_volume - historical_volume) / historical_volume if historical_volume > 0 else 0
            momentum_indicators['volume_momentum'] = volume_momentum
        
        # Volatility momentum
        if 'atr' in df.columns:
            recent_atr = recent_data['atr'].iloc[-1] if 'atr' in recent_data.columns else 0
            historical_atr = df['atr'].rolling(self.momentum_window * 2).mean().iloc[-1]
            volatility_momentum = (recent_atr - historical_atr) / historical_atr if historical_atr > 0 else 0
            momentum_indicators['volatility_momentum'] = volatility_momentum
        
        # Combine momentum indicators
        overall_momentum = self.combine_momentum_indicators(momentum_indicators)
        
        return {
            'momentum': overall_momentum['direction'],
            'strength': overall_momentum['strength'],
            'indicators': momentum_indicators,
            'market_context': self.get_momentum_market_context(df, overall_momentum)
        }
    
    def combine_momentum_indicators(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Combine multiple momentum indicators"""
        momentum_values = []
        weights = []
        
        # Price momentum (highest weight)
        if 'price_momentum' in indicators:
            momentum_values.append(indicators['price_momentum'])
            weights.append(0.6)
        
        # Volume momentum (market-dependent weight)
        if 'volume_momentum' in indicators:
            momentum_values.append(indicators['volume_momentum'])
            if self.market_type == 'crypto':
                weights.append(0.3)  # High weight for crypto
            else:
                weights.append(0.1)  # Low weight for forex
        
        # Volatility momentum
        if 'volatility_momentum' in indicators:
            momentum_values.append(indicators['volatility_momentum'])
            weights.append(0.1)
        
        if not momentum_values:
            return {'direction': 'neutral', 'strength': 0.0}
        
        # Calculate weighted momentum
        weighted_momentum = np.average(momentum_values, weights=weights)
        momentum_strength = abs(weighted_momentum)
        
        # Determine direction
        if weighted_momentum > self.shift_threshold:
            direction = 'bullish'
        elif weighted_momentum < -self.shift_threshold:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        return {
            'direction': direction,
            'strength': momentum_strength,
            'weighted_value': weighted_momentum
        }
    
    def get_momentum_market_context(self, df: pd.DataFrame, momentum: Dict[str, Any]) -> str:
        """Get market context for momentum"""
        if self.market_type == 'forex':
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:
                    return f"Forex {momentum['direction']} momentum during London-NY overlap"
                elif 8 <= hour <= 22:
                    return f"Forex {momentum['direction']} momentum during major session"
                else:
                    return f"Forex {momentum['direction']} momentum during Asian session"
        
        elif self.market_type == 'crypto':
            return f"Crypto {momentum['direction']} momentum - 24/7 market"
        
        return f"{momentum['direction']} momentum detected"
    
    def detect_momentum_shift(self, df: pd.DataFrame, current_momentum: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect momentum shifts from previous state
        """
        shift = {
            'shift_detected': False,
            'shift_type': None,
            'previous_momentum': self.current_momentum,
            'new_momentum': current_momentum['momentum'],
            'shift_strength': 0.0
        }
        
        new_momentum = current_momentum['momentum']
        
        # Check for momentum change
        if new_momentum != self.current_momentum:
            shift['shift_detected'] = True
            
            # Classify shift type
            if self.current_momentum == 'neutral':
                shift['shift_type'] = f'neutral_to_{new_momentum}'
            elif new_momentum == 'neutral':
                shift['shift_type'] = f'{self.current_momentum}_to_neutral'
            else:
                shift['shift_type'] = f'{self.current_momentum}_to_{new_momentum}'
            
            # Calculate shift strength
            shift['shift_strength'] = current_momentum['strength']
            
            # Market-specific shift validation
            if self.validate_momentum_shift_for_market(df, shift):
                return shift
        
        return shift
    
    def validate_momentum_shift_for_market(self, df: pd.DataFrame, shift: Dict[str, Any]) -> bool:
        """Validate momentum shift for specific market"""
        if self.market_type == 'forex':
            # Forex momentum shifts need session confirmation
            if self.session_momentum:
                if hasattr(df.index[-1], 'hour'):
                    hour = df.index[-1].hour
                    return 8 <= hour <= 22  # Major sessions only
            return True
        
        elif self.market_type == 'crypto':
            # Crypto momentum shifts need volume confirmation
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                return vol_ratio > 1.2  # Above average volume
            return True
        
        return True
    
    def analyze_momentum_patterns(self, df: pd.DataFrame, current_momentum: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze momentum patterns and characteristics
        """
        analysis = {
            'momentum_consistency': 0.0,
            'momentum_acceleration': 0.0,
            'momentum_sustainability': 0.0
        }
        
        if len(self.momentum_history) < 5:
            return analysis
        
        recent_momentum = self.momentum_history[-5:]
        
        # Momentum consistency
        momentum_directions = [m['momentum'] for m in recent_momentum]
        most_common = max(set(momentum_directions), key=momentum_directions.count)
        consistency = momentum_directions.count(most_common) / len(momentum_directions)
        analysis['momentum_consistency'] = consistency
        
        # Momentum acceleration
        momentum_strengths = [m['strength'] for m in recent_momentum]
        if len(momentum_strengths) >= 2:
            acceleration = momentum_strengths[-1] - momentum_strengths[0]
            analysis['momentum_acceleration'] = acceleration
        
        # Momentum sustainability (based on volume for crypto, session for forex)
        if self.market_type == 'crypto' and 'volume' in df.columns:
            vol_trend = self.analyze_volume_trend_for_momentum(df)
            analysis['momentum_sustainability'] = vol_trend
        elif self.market_type == 'forex':
            session_sustainability = self.analyze_session_momentum_sustainability(df)
            analysis['momentum_sustainability'] = session_sustainability
        
        return analysis
    
    def analyze_volume_trend_for_momentum(self, df: pd.DataFrame) -> float:
        """Analyze volume trend to assess momentum sustainability"""
        if len(df) < 10:
            return 0.5
        
        recent_volume = df['volume'].iloc[-5:].mean()
        previous_volume = df['volume'].iloc[-10:-5].mean()
        
        if previous_volume > 0:
            volume_change = (recent_volume - previous_volume) / previous_volume
            return min(max(volume_change + 0.5, 0.0), 1.0)  # Normalize to 0-1
        
        return 0.5
    
    def analyze_session_momentum_sustainability(self, df: pd.DataFrame) -> float:
        """Analyze session-based momentum sustainability for forex"""
        if not hasattr(df.index[-1], 'hour'):
            return 0.5
        
        hour = df.index[-1].hour
        
        # Momentum more sustainable during major sessions
        if 13 <= hour <= 16:  # London-NY overlap
            return 0.9
        elif 8 <= hour <= 22:  # Major sessions
            return 0.8
        else:  # Asian session
            return 0.4
    
    def detect_trend_changes(self, df: pd.DataFrame, momentum_shift: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect trend changes based on momentum shifts
        """
        trend_changes = []
        
        if not momentum_shift['shift_detected']:
            return trend_changes
        
        shift_type = momentum_shift['shift_type']
        
        # Significant trend change patterns
        significant_shifts = [
            'bearish_to_bullish',
            'bullish_to_bearish',
            'neutral_to_bullish',
            'neutral_to_bearish'
        ]
        
        if shift_type in significant_shifts:
            trend_change = {
                'type': 'momentum_trend_change',
                'new_trend': momentum_shift['new_momentum'],
                'previous_trend': momentum_shift['previous_momentum'],
                'change_strength': momentum_shift['shift_strength'],
                'confirmation_level': self.assess_trend_change_confirmation(df, momentum_shift),
                'market_implication': self.get_trend_change_implication(momentum_shift)
            }
            trend_changes.append(trend_change)
        
        return trend_changes
    
    def assess_trend_change_confirmation(self, df: pd.DataFrame, momentum_shift: Dict[str, Any]) -> str:
        """Assess confirmation level of trend change"""
        if len(df) < self.confirmation_bars:
            return 'insufficient_data'
        
        # Check recent bars for confirmation
        recent_data = df.iloc[-self.confirmation_bars:]
        
        new_momentum = momentum_shift['new_momentum']
        
        if new_momentum == 'bullish':
            bullish_bars = sum(1 for i in range(len(recent_data)) 
                             if recent_data['close'].iloc[i] > recent_data['open'].iloc[i])
            confirmation_ratio = bullish_bars / len(recent_data)
        
        elif new_momentum == 'bearish':
            bearish_bars = sum(1 for i in range(len(recent_data)) 
                             if recent_data['close'].iloc[i] < recent_data['open'].iloc[i])
            confirmation_ratio = bearish_bars / len(recent_data)
        
        else:  # neutral
            confirmation_ratio = 0.5
        
        # Classify confirmation level
        if confirmation_ratio > 0.8:
            return 'strong_confirmation'
        elif confirmation_ratio > 0.6:
            return 'moderate_confirmation'
        elif confirmation_ratio > 0.4:
            return 'weak_confirmation'
        else:
            return 'no_confirmation'
    
    def get_trend_change_implication(self, momentum_shift: Dict[str, Any]) -> str:
        """Get trading implication of trend change"""
        shift_type = momentum_shift['shift_type']
        
        implications = {
            'bearish_to_bullish': 'Potential trend reversal to upside',
            'bullish_to_bearish': 'Potential trend reversal to downside',
            'neutral_to_bullish': 'Bullish momentum building',
            'neutral_to_bearish': 'Bearish momentum building',
            'bullish_to_neutral': 'Bullish momentum weakening',
            'bearish_to_neutral': 'Bearish momentum weakening'
        }
        
        base_implication = implications.get(shift_type, 'Momentum change detected')
        
        if self.market_type == 'forex':
            return f"Forex: {base_implication}"
        elif self.market_type == 'crypto':
            return f"Crypto: {base_implication}"
        
        return base_implication
    
    def get_momentum_implications(self, momentum_shift: Dict[str, Any], 
                                trend_changes: List[Dict[str, Any]], 
                                current_momentum: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get trading implications of momentum analysis
        """
        implications = []
        
        # Momentum shift implications
        if momentum_shift['shift_detected']:
            implications.append({
                'type': 'momentum_shift',
                'direction': momentum_shift['new_momentum'],
                'strength': momentum_shift['shift_strength'],
                'implication': self.get_trend_change_implication(momentum_shift),
                'confidence': min(momentum_shift['shift_strength'] * 2, 1.0)
            })
        
        # Trend change implications
        for trend_change in trend_changes:
            implications.append({
                'type': 'trend_change',
                'direction': trend_change['new_trend'],
                'strength': trend_change['change_strength'],
                'implication': trend_change['market_implication'],
                'confidence': self.get_trend_change_confidence(trend_change)
            })
        
        # Current momentum implications
        if current_momentum['strength'] > 0.5:
            implications.append({
                'type': 'strong_momentum',
                'direction': current_momentum['momentum'],
                'strength': current_momentum['strength'],
                'implication': f'Strong {current_momentum["momentum"]} momentum in {self.market_type}',
                'confidence': current_momentum['strength']
            })
        
        return implications
    
    def get_trend_change_confidence(self, trend_change: Dict[str, Any]) -> float:
        """Get confidence level for trend change"""
        confirmation_level = trend_change['confirmation_level']
        
        confidence_levels = {
            'strong_confirmation': 0.9,
            'moderate_confirmation': 0.7,
            'weak_confirmation': 0.5,
            'no_confirmation': 0.3
        }
        
        base_confidence = confidence_levels.get(confirmation_level, 0.5)
        
        # Adjust for change strength
        change_strength = trend_change['change_strength']
        strength_adjustment = min(change_strength * 0.5, 0.2)
        
        return min(base_confidence + strength_adjustment, 1.0)
    
    def calculate_momentum_signal_strength(self, momentum_shift: Dict[str, Any], 
                                         momentum_analysis: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate momentum shift signal strength
        """
        strength_factors = []
        
        # Shift detection strength
        if momentum_shift['shift_detected']:
            shift_strength = momentum_shift['shift_strength']
            strength_factors.append(shift_strength)
        
        # Momentum consistency strength
        consistency = momentum_analysis.get('momentum_consistency', 0.0)
        strength_factors.append(consistency)
        
        # Market-specific strength
        market_strength = self.get_market_momentum_strength(df)
        strength_factors.append(market_strength)
        
        # Acceleration bonus
        acceleration = momentum_analysis.get('momentum_acceleration', 0.0)
        if acceleration > 0:
            acceleration_bonus = min(acceleration * 2, 0.3)
            strength_factors.append(acceleration_bonus)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_market_momentum_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific momentum strength"""
        if self.market_type == 'forex':
            # Session-based strength for forex
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:
                    return 0.9
                elif 8 <= hour <= 22:
                    return 0.8
                else:
                    return 0.5
            return 0.7
        
        elif self.market_type == 'crypto':
            # Volume-based strength for crypto
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                return min(0.6 + vol_ratio / 5.0, 1.0)
            
            return 0.7
        
        return 0.7
    
    def update_momentum_tracking(self, current_momentum: Dict[str, Any], 
                               momentum_shift: Dict[str, Any], trend_changes: List[Dict[str, Any]]):
        """Update momentum tracking"""
        # Update current momentum state
        self.current_momentum = current_momentum['momentum']
        
        # Add to momentum history
        momentum_entry = {
            'timestamp': datetime.now(timezone.utc),
            'momentum': current_momentum['momentum'],
            'strength': current_momentum['strength'],
            'indicators': current_momentum['indicators'],
            'market_type': self.market_type
        }
        self.momentum_history.append(momentum_entry)
        
        # Add shift events
        if momentum_shift['shift_detected']:
            shift_event = {
                'timestamp': datetime.now(timezone.utc),
                'shift_type': momentum_shift['shift_type'],
                'shift_strength': momentum_shift['shift_strength'],
                'market_type': self.market_type
            }
            self.shift_events.append(shift_event)
        
        # Add trend changes
        self.trend_changes.extend(trend_changes)
        
        # Limit tracking sizes
        if len(self.momentum_history) > 100:
            self.momentum_history = self.momentum_history[-100:]
        
        if len(self.shift_events) > 50:
            self.shift_events = self.shift_events[-50:]
        
        if len(self.trend_changes) > 50:
            self.trend_changes = self.trend_changes[-50:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_momentum_summary(self) -> Dict[str, Any]:
        """Get comprehensive momentum summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'current_momentum': self.current_momentum,
            'momentum_history_count': len(self.momentum_history),
            'shift_events_count': len(self.shift_events),
            'trend_changes_count': len(self.trend_changes),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'momentum_window': self.momentum_window,
                'shift_threshold': self.shift_threshold,
                'confirmation_bars': self.confirmation_bars,
                'session_momentum': getattr(self, 'session_momentum', False)
            }
        }
    
    def has_strong_momentum(self, direction: str = None) -> bool:
        """Check for strong momentum in specified direction"""
        if not self.momentum_history:
            return False
        
        latest_momentum = self.momentum_history[-1]
        
        if direction:
            return (latest_momentum['momentum'] == direction and 
                   latest_momentum['strength'] > 0.6)
        else:
            return latest_momentum['strength'] > 0.6
    
    def requires_continuous_processing(self) -> bool:
        """Momentum shift agent doesn't need continuous processing"""
        return False