"""
Engulfing Rejection Agent
Detects engulfing patterns using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class EngulfingAgent(ICTSMCAgent):
    """
    Specialized agent for Engulfing pattern detection
    Uses existing detect_engulfing_rejection() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("engulfing", config)
        
        # Engulfing configuration
        self.min_body_ratio = config.get('min_body_ratio', 0.6)
        self.volume_confirmation = config.get('volume_confirmation', True)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Engulfing tracking
        self.engulfing_events = []
        self.rejection_zones = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Engulfing Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific configuration adjustments"""
        if self.market_type == 'forex':
            # Forex: More conservative engulfing detection
            self.min_body_ratio = max(self.min_body_ratio, 0.7)
            self.volume_weight = 0.3  # Volume less reliable in forex
            self.session_importance = True
        elif self.market_type == 'crypto':
            # Crypto: Standard engulfing detection with volume focus
            self.min_body_ratio = min(self.min_body_ratio, 0.6)
            self.volume_weight = 0.8  # Volume very important in crypto
            self.session_importance = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect engulfing patterns
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with engulfing analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < 2:
            return {'engulfing_detected': False, 'signal_strength': 0.0}
        
        try:
            # Use existing detect_engulfing_rejection function
            bullish_engulf, bearish_engulf = self.detect_engulfing_rejection(df)
            
            # Get detailed engulfing analysis
            engulfing_analysis = self.analyze_engulfing_patterns(df, bullish_engulf, bearish_engulf)
            
            # Detect rejection zones
            rejection_zones = self.identify_rejection_zones(df, bullish_engulf, bearish_engulf)
            
            # Update tracking
            self.update_engulfing_tracking(bullish_engulf, bearish_engulf, df, rejection_zones)
            
            # Calculate signal strength
            signal_strength = self.calculate_engulfing_signal_strength(
                bullish_engulf, bearish_engulf, engulfing_analysis, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bullish_engulfing': bullish_engulf,
                'bearish_engulfing': bearish_engulf,
                'engulfing_analysis': engulfing_analysis,
                'rejection_zones': rejection_zones,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'reversal_signals': self.generate_reversal_signals(
                    bullish_engulf, bearish_engulf, engulfing_analysis
                )
            }
            
            # Publish engulfing signals
            if bullish_engulf or bearish_engulf:
                self.publish("engulfing_detected", {
                    'symbol': symbol,
                    'bullish_engulfing': bullish_engulf,
                    'bearish_engulfing': bearish_engulf,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing engulfing data for {symbol}: {e}")
            return {'engulfing_detected': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_engulfing_rejection(self, df: pd.DataFrame) -> tuple:
        """
        Detect engulfing patterns using existing implementation
        """
        if len(df) < 2:
            return False, False
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # Basic engulfing logic from your existing code
        bullish = (
            curr['close'] > curr['open'] and
            prev['close'] < prev['open'] and
            curr['close'] > prev['open'] and
            curr['open'] < prev['close']
        )
        
        bearish = (
            curr['close'] < curr['open'] and
            prev['close'] > prev['open'] and
            curr['close'] < prev['open'] and
            curr['open'] > prev['close']
        )
        
        # Additional validation
        if bullish:
            bullish = self.validate_engulfing_pattern(df, 'bullish')
        if bearish:
            bearish = self.validate_engulfing_pattern(df, 'bearish')
        
        return bullish, bearish
    
    def validate_engulfing_pattern(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate engulfing pattern with market-specific criteria"""
        if len(df) < 2:
            return False
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # Body size validation
        prev_body = abs(prev['close'] - prev['open'])
        curr_body = abs(curr['close'] - curr['open'])
        prev_range = prev['high'] - prev['low']
        curr_range = curr['high'] - curr['low']
        
        # Require minimum body ratios
        if prev_range > 0:
            prev_body_ratio = prev_body / prev_range
            if prev_body_ratio < 0.4:  # Previous candle must have decent body
                return False
        
        if curr_range > 0:
            curr_body_ratio = curr_body / curr_range
            if curr_body_ratio < self.min_body_ratio:  # Current candle must have strong body
                return False
        
        # Size relationship validation
        if curr_body < prev_body * 1.1:  # Engulfing candle should be larger
            return False
        
        # Market-specific validation
        if self.market_type == 'forex':
            return self.validate_forex_engulfing(df, direction)
        elif self.market_type == 'crypto':
            return self.validate_crypto_engulfing(df, direction)
        
        return True
    
    def validate_forex_engulfing(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate engulfing for forex markets"""
        try:
            # Session-based validation for forex
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                
                # Engulfing more significant during active sessions
                if 8 <= hour <= 22:  # London or NY sessions
                    return True
                else:
                    # Require additional confirmation outside major sessions
                    return self.has_additional_confirmation(df, direction)
            
            return True
            
        except Exception:
            return True
    
    def validate_crypto_engulfing(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate engulfing for crypto markets"""
        try:
            # Volume-based validation for crypto
            if 'volume' in df.columns and self.volume_confirmation:
                current_volume = df['volume'].iloc[-1]
                prev_volume = df['volume'].iloc[-2]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                
                # Require volume expansion for crypto engulfing
                volume_expansion = current_volume > prev_volume * 1.2
                above_avg_volume = current_volume > avg_volume * 1.3
                
                return volume_expansion and above_avg_volume
            
            return True
            
        except Exception:
            return True
    
    def has_additional_confirmation(self, df: pd.DataFrame, direction: str) -> bool:
        """Check for additional confirmation factors"""
        try:
            # RSI confirmation
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
                if direction == 'bullish' and rsi < 35:
                    return True  # Oversold + bullish engulfing
                elif direction == 'bearish' and rsi > 65:
                    return True  # Overbought + bearish engulfing
            
            # Support/Resistance level confirmation
            current_price = df['close'].iloc[-1]
            recent_highs = df['high'].rolling(20).max().iloc[-1]
            recent_lows = df['low'].rolling(20).min().iloc[-1]
            
            if direction == 'bullish' and abs(current_price - recent_lows) / recent_lows < 0.02:
                return True  # Engulfing near support
            elif direction == 'bearish' and abs(current_price - recent_highs) / recent_highs < 0.02:
                return True  # Engulfing near resistance
            
            return False
            
        except Exception:
            return False
    
    def analyze_engulfing_patterns(self, df: pd.DataFrame, bullish_engulf: bool, bearish_engulf: bool) -> Dict[str, Any]:
        """
        Analyze engulfing pattern characteristics
        """
        analysis = {
            'engulfing_strength': 0.0,
            'reversal_probability': 0.5,
            'pattern_quality': 'unknown'
        }
        
        if not (bullish_engulf or bearish_engulf):
            return analysis
        
        if len(df) < 2:
            return analysis
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        # Calculate engulfing strength
        prev_body = abs(prev['close'] - prev['open'])
        curr_body = abs(curr['close'] - curr['open'])
        
        if prev_body > 0:
            size_ratio = curr_body / prev_body
            analysis['engulfing_strength'] = min(size_ratio / 2.0, 1.0)
        
        # Pattern quality assessment
        if analysis['engulfing_strength'] > 0.8:
            analysis['pattern_quality'] = 'excellent'
            analysis['reversal_probability'] = 0.75
        elif analysis['engulfing_strength'] > 0.6:
            analysis['pattern_quality'] = 'good'
            analysis['reversal_probability'] = 0.65
        elif analysis['engulfing_strength'] > 0.4:
            analysis['pattern_quality'] = 'fair'
            analysis['reversal_probability'] = 0.55
        else:
            analysis['pattern_quality'] = 'weak'
            analysis['reversal_probability'] = 0.45
        
        # Market-specific adjustments
        if self.market_type == 'forex':
            analysis['reversal_probability'] += 0.05  # Forex engulfing slightly more reliable
        elif self.market_type == 'crypto':
            # Crypto engulfing reliability depends on volume
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                if vol_ratio > 2.0:
                    analysis['reversal_probability'] += 0.1
                else:
                    analysis['reversal_probability'] -= 0.05
        
        return analysis
    
    def identify_rejection_zones(self, df: pd.DataFrame, bullish_engulf: bool, bearish_engulf: bool) -> List[Dict[str, Any]]:
        """Identify rejection zones based on engulfing patterns"""
        rejection_zones = []
        
        if not (bullish_engulf or bearish_engulf) or len(df) < 2:
            return rejection_zones
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        if bullish_engulf:
            # Bullish engulfing creates resistance rejection zone
            rejection_zones.append({
                'type': 'resistance_rejection',
                'zone': (min(prev['open'], prev['close']), max(prev['open'], prev['close'])),
                'rejection_price': curr['close'],
                'strength': self.calculate_rejection_strength(df, 'bullish'),
                'market_type': self.market_type
            })
        
        if bearish_engulf:
            # Bearish engulfing creates support rejection zone
            rejection_zones.append({
                'type': 'support_rejection',
                'zone': (min(prev['open'], prev['close']), max(prev['open'], prev['close'])),
                'rejection_price': curr['close'],
                'strength': self.calculate_rejection_strength(df, 'bearish'),
                'market_type': self.market_type
            })
        
        return rejection_zones
    
    def calculate_rejection_strength(self, df: pd.DataFrame, direction: str) -> float:
        """Calculate rejection strength"""
        if len(df) < 2:
            return 0.5
        
        strength_factors = []
        curr = df.iloc[-1]
        
        # Body strength
        body = abs(curr['close'] - curr['open'])
        total_range = curr['high'] - curr['low']
        if total_range > 0:
            body_strength = body / total_range
            strength_factors.append(body_strength)
        
        # Volume strength (market-specific)
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_strength = min(current_volume / avg_volume, 2.5) / 2.5
            strength_factors.append(volume_strength * self.volume_weight)
        
        # Market-specific factors
        if self.market_type == 'forex' and hasattr(df.index[-1], 'hour'):
            hour = df.index[-1].hour
            session_strength = self.calculate_forex_time_strength(hour)
            strength_factors.append(session_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.5
    
    def calculate_forex_time_strength(self, hour: int) -> float:
        """Calculate time-based strength for forex"""
        if 13 <= hour <= 16:  # London-NY overlap
            return 0.9
        elif 8 <= hour <= 17:  # London session
            return 0.8
        elif 13 <= hour <= 22:  # NY session
            return 0.8
        else:  # Asian session
            return 0.5
    
    def generate_reversal_signals(self, bullish_engulf: bool, bearish_engulf: bool, 
                                engulfing_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate reversal signals based on engulfing patterns"""
        signals = []
        
        if bullish_engulf:
            signals.append({
                'type': 'bullish_engulfing_reversal',
                'direction': 'bullish',
                'strength': engulfing_analysis['engulfing_strength'],
                'probability': engulfing_analysis['reversal_probability'],
                'message': f'Bullish engulfing in {self.market_type} - potential upward reversal',
                'market_specific_note': self.get_engulfing_market_note('bullish')
            })
        
        if bearish_engulf:
            signals.append({
                'type': 'bearish_engulfing_reversal',
                'direction': 'bearish',
                'strength': engulfing_analysis['engulfing_strength'],
                'probability': engulfing_analysis['reversal_probability'],
                'message': f'Bearish engulfing in {self.market_type} - potential downward reversal',
                'market_specific_note': self.get_engulfing_market_note('bearish')
            })
        
        return signals
    
    def get_engulfing_market_note(self, direction: str) -> str:
        """Get market-specific engulfing interpretation"""
        if self.market_type == 'forex':
            if direction == 'bullish':
                return "Forex bullish engulfing: Potential shift to risk-on sentiment or central bank dovish stance"
            else:
                return "Forex bearish engulfing: Possible risk-off flows or hawkish central bank sentiment"
        elif self.market_type == 'crypto':
            if direction == 'bullish':
                return "Crypto bullish engulfing: Strong buying interest, possible whale accumulation phase"
            else:
                return "Crypto bearish engulfing: Heavy selling pressure, potential distribution phase"
        
        return f"{direction.capitalize()} engulfing pattern detected"
    
    def calculate_engulfing_signal_strength(self, bullish_engulf: bool, bearish_engulf: bool,
                                          engulfing_analysis: Dict[str, Any], 
                                          df: pd.DataFrame) -> float:
        """
        Calculate engulfing signal strength
        """
        if not (bullish_engulf or bearish_engulf):
            return 0.0
        
        strength_factors = []
        
        # Base engulfing strength
        base_strength = 0.7  # Engulfing is a strong reversal signal
        strength_factors.append(base_strength)
        
        # Pattern strength from analysis
        if 'engulfing_strength' in engulfing_analysis:
            strength_factors.append(engulfing_analysis['engulfing_strength'])
        
        # Market-specific strength
        market_strength = self.get_market_specific_engulfing_strength(df)
        strength_factors.append(market_strength)
        
        # Volume confirmation strength
        if 'volume' in df.columns:
            volume_strength = self.calculate_volume_confirmation_strength(df)
            strength_factors.append(volume_strength)
        
        return np.mean(strength_factors)
    
    def get_market_specific_engulfing_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific engulfing strength"""
        if self.market_type == 'forex':
            # Forex strength based on session
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                return self.calculate_forex_time_strength(hour)
            return 0.7
        
        elif self.market_type == 'crypto':
            # Crypto strength based on volume and volatility
            strength = 0.7
            
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(vol_ratio / 2.0, 1.0)
                strength += volume_factor * 0.3
            
            return min(strength, 1.0)
        
        return 0.7
    
    def calculate_volume_confirmation_strength(self, df: pd.DataFrame) -> float:
        """Calculate volume confirmation strength"""
        if 'volume' not in df.columns or len(df) < 2:
            return 0.5
        
        current_volume = df['volume'].iloc[-1]
        prev_volume = df['volume'].iloc[-2]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        
        # Volume expansion strength
        expansion_strength = min(current_volume / prev_volume, 3.0) / 3.0
        
        # Above average volume strength
        avg_strength = min(current_volume / avg_volume, 2.0) / 2.0
        
        return (expansion_strength * 0.6 + avg_strength * 0.4)
    
    def update_engulfing_tracking(self, bullish_engulf: bool, bearish_engulf: bool, 
                                df: pd.DataFrame, rejection_zones: List[Dict[str, Any]]):
        """Update engulfing event tracking"""
        if bullish_engulf or bearish_engulf:
            engulfing_event = {
                'timestamp': datetime.now(timezone.utc),
                'bullish_engulfing': bullish_engulf,
                'bearish_engulfing': bearish_engulf,
                'price': df['close'].iloc[-1],
                'volume': df['volume'].iloc[-1] if 'volume' in df.columns else 0,
                'market_type': self.market_type,
                'rejection_zones': rejection_zones
            }
            
            self.engulfing_events.append(engulfing_event)
            
            # Update rejection zones
            self.rejection_zones.extend(rejection_zones)
            
            # Limit tracking sizes
            if len(self.engulfing_events) > 100:
                self.engulfing_events = self.engulfing_events[-100:]
            
            if len(self.rejection_zones) > 50:
                self.rejection_zones = self.rejection_zones[-50:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_engulfing_summary(self) -> Dict[str, Any]:
        """Get comprehensive engulfing summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'engulfing_events_count': len(self.engulfing_events),
            'rejection_zones_count': len(self.rejection_zones),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'min_body_ratio': self.min_body_ratio,
                'volume_confirmation': self.volume_confirmation,
                'volume_weight': self.volume_weight
            }
        }
    
    def has_recent_engulfing(self, direction: str = None, bars_back: int = 3) -> bool:
        """Check for recent engulfing patterns"""
        if not self.engulfing_events:
            return False
        
        recent_events = self.engulfing_events[-bars_back:] if len(self.engulfing_events) >= bars_back else self.engulfing_events
        
        if direction == 'bullish':
            return any(event['bullish_engulfing'] for event in recent_events)
        elif direction == 'bearish':
            return any(event['bearish_engulfing'] for event in recent_events)
        else:
            return any(event['bullish_engulfing'] or event['bearish_engulfing'] for event in recent_events)
    
    def requires_continuous_processing(self) -> bool:
        """Engulfing agent doesn't need continuous processing"""
        return False