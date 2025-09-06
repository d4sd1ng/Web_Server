"""
Displacement Agent
Detects displacement (impulse) candles using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class DisplacementAgent(ICTSMCAgent):
    """
    Specialized agent for Displacement candle detection
    Uses existing detect_displacement_candle() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("displacement", config)
        
        # Displacement configuration
        self.min_body_atr = config.get('min_body_atr', 1.0)
        self.volume_threshold = config.get('volume_threshold', 1.5)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Displacement tracking
        self.displacement_events = []
        self.impulse_sequences = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Displacement Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific configuration adjustments"""
        if self.market_type == 'forex':
            # Forex: More conservative displacement detection
            self.min_body_atr = max(self.min_body_atr, 1.2)  # Larger body requirement
            self.volume_threshold = 1.3  # Lower volume threshold (forex volume less reliable)
            self.session_multiplier = True  # Consider session timing
        elif self.market_type == 'crypto':
            # Crypto: More aggressive displacement detection
            self.min_body_atr = min(self.min_body_atr, 1.0)  # Smaller body ok for crypto
            self.volume_threshold = max(self.volume_threshold, 1.8)  # Higher volume requirement
            self.session_multiplier = False  # 24/7 market
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect displacement candles
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with displacement analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < 3:
            return {'displacement_detected': False, 'signal_strength': 0.0}
        
        try:
            # Use existing detect_displacement_candle function
            bullish_disp, bearish_disp = self.detect_displacement_candle(df, self.min_body_atr)
            
            # Get detailed displacement analysis
            displacement_analysis = self.analyze_displacement_patterns(df, bullish_disp, bearish_disp)
            
            # Detect impulse sequences
            impulse_sequence = self.detect_impulse_sequence(df)
            
            # Update tracking
            self.update_displacement_tracking(bullish_disp, bearish_disp, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_displacement_signal_strength(
                bullish_disp, bearish_disp, displacement_analysis, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bullish_displacement': bullish_disp,
                'bearish_displacement': bearish_disp,
                'displacement_analysis': displacement_analysis,
                'impulse_sequence': impulse_sequence,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'momentum_implications': self.get_momentum_implications(
                    bullish_disp, bearish_disp, impulse_sequence
                )
            }
            
            # Publish displacement signals
            if bullish_disp or bearish_disp:
                self.publish("displacement_detected", {
                    'symbol': symbol,
                    'bullish_displacement': bullish_disp,
                    'bearish_displacement': bearish_disp,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing displacement data for {symbol}: {e}")
            return {'displacement_detected': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_displacement_candle(self, df: pd.DataFrame, min_body_atr: float = 1.0) -> tuple:
        """
        Detect displacement candles using existing implementation
        """
        if len(df) < 2 or 'atr' not in df.columns:
            return False, False
        
        curr = df.iloc[-1]
        body = abs(curr['close'] - curr['open'])
        atr = df['atr'].iloc[-1]
        
        # Basic displacement logic from your existing code
        bullish = (curr['close'] > curr['open'] and 
                  body >= min_body_atr * atr)
        
        bearish = (curr['close'] < curr['open'] and 
                  body >= min_body_atr * atr)
        
        # Market-specific validation
        if self.market_type == 'forex':
            bullish = bullish and self.validate_forex_displacement(df, 'bullish')
            bearish = bearish and self.validate_forex_displacement(df, 'bearish')
        elif self.market_type == 'crypto':
            bullish = bullish and self.validate_crypto_displacement(df, 'bullish')
            bearish = bearish and self.validate_crypto_displacement(df, 'bearish')
        
        return bullish, bearish
    
    def validate_forex_displacement(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate displacement for forex markets"""
        try:
            # Forex displacement validation
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                
                # Displacement more significant during major sessions
                if 8 <= hour <= 22:  # London or NY session
                    return True
                else:
                    # Require stronger confirmation outside major sessions
                    curr = df.iloc[-1]
                    body = abs(curr['close'] - curr['open'])
                    total_range = curr['high'] - curr['low']
                    
                    # Require larger body ratio for Asian session
                    return body / total_range > 0.7
            
            return True
            
        except Exception:
            return True
    
    def validate_crypto_displacement(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate displacement for crypto markets"""
        try:
            # Crypto displacement requires volume confirmation
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                
                # Require elevated volume for crypto displacement
                return current_volume > self.volume_threshold * avg_volume
            
            return True
            
        except Exception:
            return True
    
    def analyze_displacement_patterns(self, df: pd.DataFrame, bullish_disp: bool, bearish_disp: bool) -> Dict[str, Any]:
        """
        Analyze displacement patterns and characteristics
        """
        analysis = {
            'displacement_strength': 0.0,
            'momentum_rating': 'neutral',
            'follow_through_probability': 0.5,
            'market_context': self.get_displacement_market_context(df)
        }
        
        if bullish_disp or bearish_disp:
            # Calculate displacement strength
            analysis['displacement_strength'] = self.calculate_individual_displacement_strength(df)
            
            # Determine momentum rating
            if analysis['displacement_strength'] > 0.8:
                analysis['momentum_rating'] = 'very_strong'
            elif analysis['displacement_strength'] > 0.6:
                analysis['momentum_rating'] = 'strong'
            elif analysis['displacement_strength'] > 0.4:
                analysis['momentum_rating'] = 'moderate'
            else:
                analysis['momentum_rating'] = 'weak'
            
            # Estimate follow-through probability based on market type
            if self.market_type == 'forex':
                analysis['follow_through_probability'] = 0.65  # Forex tends to follow through
            elif self.market_type == 'crypto':
                analysis['follow_through_probability'] = 0.55  # Crypto more unpredictable
        
        return analysis
    
    def get_displacement_market_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get market context for displacement analysis"""
        context = {
            'trend_alignment': False,
            'volatility_expansion': False,
            'session_context': 'unknown'
        }
        
        if len(df) < 10:
            return context
        
        # Check trend alignment
        if 'SMA_short' in df.columns and 'SMA_long' in df.columns:
            sma_short = df['SMA_short'].iloc[-1]
            sma_long = df['SMA_long'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # Bullish trend alignment
            if sma_short > sma_long and current_price > sma_short:
                context['trend_alignment'] = 'bullish'
            # Bearish trend alignment
            elif sma_short < sma_long and current_price < sma_short:
                context['trend_alignment'] = 'bearish'
        
        # Check volatility expansion
        if 'atr' in df.columns:
            current_atr = df['atr'].iloc[-1]
            avg_atr = df['atr'].rolling(20).mean().iloc[-1]
            context['volatility_expansion'] = current_atr > 1.3 * avg_atr
        
        # Session context for forex
        if self.market_type == 'forex' and hasattr(df.index[-1], 'hour'):
            hour = df.index[-1].hour
            if 13 <= hour <= 16:
                context['session_context'] = 'london_ny_overlap'
            elif 8 <= hour <= 17:
                context['session_context'] = 'london_session'
            elif 13 <= hour <= 22:
                context['session_context'] = 'ny_session'
        
        return context
    
    def detect_impulse_sequence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect sequences of impulse candles
        """
        if len(df) < 5:
            return {'sequence_detected': False, 'sequence_length': 0}
        
        # Look for consecutive displacement candles
        sequence_count = 0
        sequence_direction = None
        
        for i in range(len(df) - 5, len(df)):
            if i >= 1 and 'atr' in df.columns:
                curr = df.iloc[i]
                body = abs(curr['close'] - curr['open'])
                atr = df['atr'].iloc[i]
                
                if body >= self.min_body_atr * atr:
                    if curr['close'] > curr['open']:  # Bullish impulse
                        if sequence_direction == 'bullish' or sequence_direction is None:
                            sequence_count += 1
                            sequence_direction = 'bullish'
                        else:
                            break
                    elif curr['close'] < curr['open']:  # Bearish impulse
                        if sequence_direction == 'bearish' or sequence_direction is None:
                            sequence_count += 1
                            sequence_direction = 'bearish'
                        else:
                            break
                else:
                    break
        
        return {
            'sequence_detected': sequence_count >= 2,
            'sequence_length': sequence_count,
            'sequence_direction': sequence_direction,
            'sequence_strength': min(sequence_count / 5.0, 1.0)  # Normalize to 1.0
        }
    
    def calculate_individual_displacement_strength(self, df: pd.DataFrame) -> float:
        """Calculate individual displacement strength"""
        if len(df) < 2 or 'atr' not in df.columns:
            return 0.0
        
        strength_factors = []
        curr = df.iloc[-1]
        
        # Body to ATR ratio
        body = abs(curr['close'] - curr['open'])
        atr = df['atr'].iloc[-1]
        body_atr_ratio = body / atr
        body_strength = min(body_atr_ratio / 2.0, 1.0)  # Normalize
        strength_factors.append(body_strength)
        
        # Body to total range ratio
        total_range = curr['high'] - curr['low']
        if total_range > 0:
            body_ratio = body / total_range
            strength_factors.append(body_ratio)
        
        # Volume confirmation (market-specific weight)
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_strength = min(current_volume / avg_volume, 3.0) / 3.0
            
            if self.market_type == 'crypto':
                strength_factors.append(volume_strength * 0.8)
            else:
                strength_factors.append(volume_strength * 0.4)
        
        # Wick analysis (small wicks = stronger displacement)
        upper_wick = curr['high'] - max(curr['open'], curr['close'])
        lower_wick = min(curr['open'], curr['close']) - curr['low']
        avg_wick = (upper_wick + lower_wick) / 2
        
        if total_range > 0:
            wick_ratio = avg_wick / total_range
            wick_strength = 1.0 - wick_ratio  # Smaller wicks = higher strength
            strength_factors.append(wick_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_momentum_implications(self, bullish_disp: bool, bearish_disp: bool, 
                                impulse_sequence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get momentum implications of displacement"""
        implications = []
        
        if bullish_disp:
            implications.append({
                'type': 'bullish_displacement',
                'momentum_direction': 'upward',
                'strength': 'strong' if impulse_sequence['sequence_detected'] else 'moderate',
                'trading_implication': f'Strong bullish momentum in {self.market_type} market',
                'expected_follow_through': self.get_expected_follow_through('bullish', impulse_sequence),
                'market_specific_note': self.get_displacement_market_note('bullish')
            })
        
        if bearish_disp:
            implications.append({
                'type': 'bearish_displacement',
                'momentum_direction': 'downward',
                'strength': 'strong' if impulse_sequence['sequence_detected'] else 'moderate',
                'trading_implication': f'Strong bearish momentum in {self.market_type} market',
                'expected_follow_through': self.get_expected_follow_through('bearish', impulse_sequence),
                'market_specific_note': self.get_displacement_market_note('bearish')
            })
        
        return implications
    
    def get_expected_follow_through(self, direction: str, impulse_sequence: Dict[str, Any]) -> str:
        """Get expected follow-through based on market type and sequence"""
        if impulse_sequence['sequence_detected']:
            if self.market_type == 'forex':
                return f"High probability {direction} continuation during session"
            elif self.market_type == 'crypto':
                return f"Strong {direction} momentum - expect continuation with volume"
        else:
            if self.market_type == 'forex':
                return f"Moderate {direction} momentum - monitor for session confirmation"
            elif self.market_type == 'crypto':
                return f"Single {direction} impulse - wait for volume confirmation"
        
        return f"Monitor for {direction} continuation"
    
    def get_displacement_market_note(self, direction: str) -> str:
        """Get market-specific displacement interpretation"""
        if self.market_type == 'forex':
            if direction == 'bullish':
                return "Forex bullish displacement: Likely institutional buying or risk-on sentiment"
            else:
                return "Forex bearish displacement: Possible institutional selling or risk-off flows"
        elif self.market_type == 'crypto':
            if direction == 'bullish':
                return "Crypto bullish displacement: Strong buying pressure, possible whale accumulation"
            else:
                return "Crypto bearish displacement: Heavy selling pressure, possible whale distribution"
        
        return f"{direction.capitalize()} displacement detected"
    
    def calculate_displacement_signal_strength(self, bullish_disp: bool, bearish_disp: bool,
                                             displacement_analysis: Dict[str, Any], 
                                             df: pd.DataFrame) -> float:
        """
        Calculate displacement signal strength
        """
        if not (bullish_disp or bearish_disp):
            return 0.0
        
        strength_factors = []
        
        # Base displacement strength
        base_strength = 0.75  # Displacement is a strong momentum signal
        strength_factors.append(base_strength)
        
        # Individual displacement strength
        if 'displacement_strength' in displacement_analysis:
            strength_factors.append(displacement_analysis['displacement_strength'])
        
        # Market-specific strength
        market_strength = self.get_market_specific_displacement_strength(df)
        strength_factors.append(market_strength)
        
        # Sequence strength bonus
        if displacement_analysis.get('impulse_sequence', {}).get('sequence_detected'):
            sequence_bonus = 0.2
            strength_factors.append(sequence_bonus)
        
        return np.mean(strength_factors)
    
    def get_market_specific_displacement_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific displacement strength"""
        if self.market_type == 'forex':
            # Forex strength based on session timing
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:  # London-NY overlap
                    return 0.9
                elif 8 <= hour <= 22:  # Major sessions
                    return 0.8
                else:  # Asian session
                    return 0.6
            return 0.7
        
        elif self.market_type == 'crypto':
            # Crypto strength based on volume
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(current_volume / avg_volume, 3.0) / 3.0
                return 0.6 + volume_factor * 0.4
            
            return 0.7
        
        return 0.7
    
    def update_displacement_tracking(self, bullish_disp: bool, bearish_disp: bool, df: pd.DataFrame):
        """Update displacement event tracking"""
        if bullish_disp or bearish_disp:
            displacement_event = {
                'timestamp': datetime.now(timezone.utc),
                'bullish_displacement': bullish_disp,
                'bearish_displacement': bearish_disp,
                'price': df['close'].iloc[-1],
                'body_size': abs(df['close'].iloc[-1] - df['open'].iloc[-1]),
                'atr': df['atr'].iloc[-1] if 'atr' in df.columns else 0,
                'market_type': self.market_type
            }
            
            self.displacement_events.append(displacement_event)
            
            # Limit tracking size
            if len(self.displacement_events) > 100:
                self.displacement_events = self.displacement_events[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_displacement_summary(self) -> Dict[str, Any]:
        """Get comprehensive displacement summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'displacement_events_count': len(self.displacement_events),
            'impulse_sequences_count': len(self.impulse_sequences),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'min_body_atr': self.min_body_atr,
                'volume_threshold': self.volume_threshold,
                'session_multiplier': getattr(self, 'session_multiplier', False)
            }
        }
    
    def has_recent_displacement(self, direction: str = None, bars_back: int = 5) -> bool:
        """Check for recent displacement events"""
        if not self.displacement_events:
            return False
        
        recent_events = self.displacement_events[-bars_back:] if len(self.displacement_events) >= bars_back else self.displacement_events
        
        if direction == 'bullish':
            return any(event['bullish_displacement'] for event in recent_events)
        elif direction == 'bearish':
            return any(event['bearish_displacement'] for event in recent_events)
        else:
            return any(event['bullish_displacement'] or event['bearish_displacement'] for event in recent_events)
    
    def requires_continuous_processing(self) -> bool:
        """Displacement agent doesn't need continuous processing"""
        return False