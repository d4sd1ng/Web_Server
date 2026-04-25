"""
Structure of Failure (SOF) Agent
Detects SOF patterns using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class SOFAgent(ICTSMCAgent):
    """
    Specialized agent for Structure of Failure detection
    Uses existing detect_sof() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("sof", config)
        
        # SOF configuration
        self.lookback = config.get('lookback', 10)
        self.confirmation_bars = config.get('confirmation_bars', 3)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # SOF tracking
        self.sof_events = []
        self.active_sof_warnings = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"SOF Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific configuration adjustments"""
        if self.market_type == 'forex':
            # Forex: More conservative SOF detection
            self.lookback = max(self.lookback, 15)  # Longer lookback for forex
            self.confirmation_threshold = 0.7
            self.session_weight = 0.8  # Session timing important
        elif self.market_type == 'crypto':
            # Crypto: More aggressive SOF detection
            self.lookback = min(self.lookback, 10)  # Shorter for volatile crypto
            self.confirmation_threshold = 0.6
            self.session_weight = 0.3  # 24/7 market, session less important
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect Structure of Failure
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with SOF analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback + 1:
            return {'sof_detected': False, 'signal_strength': 0.0}
        
        try:
            # Use existing detect_sof function
            sof_bull, sof_bear = self.detect_sof(df, self.lookback)
            
            # Get detailed SOF analysis
            sof_analysis = self.analyze_sof_patterns(df, sof_bull, sof_bear)
            
            # Update SOF tracking
            self.update_sof_tracking(sof_bull, sof_bear, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_sof_signal_strength(sof_bull, sof_bear, sof_analysis, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'sof_bull': sof_bull,
                'sof_bear': sof_bear,
                'sof_analysis': sof_analysis,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'reversal_warnings': self.generate_reversal_warnings(sof_bull, sof_bear, sof_analysis),
                'trading_implications': self.get_sof_trading_implications(sof_bull, sof_bear, df)
            }
            
            # Publish SOF signals
            if sof_bull or sof_bear:
                self.publish("sof_detected", {
                    'symbol': symbol,
                    'sof_bull': sof_bull,
                    'sof_bear': sof_bear,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type,
                    'reversal_warning': True
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing SOF data for {symbol}: {e}")
            return {'sof_detected': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_sof(self, df: pd.DataFrame, lookback: int = 10) -> tuple:
        """
        Detect Structure of Failure using existing implementation
        """
        if len(df) < lookback + 1:
            return False, False
        
        prev_highs = df['high'].iloc[-(lookback+1):-1]
        prev_lows = df['low'].iloc[-(lookback+1):-1]
        last_high = df['high'].iloc[-1]
        last_low = df['low'].iloc[-1]
        
        # Basic SOF detection from your existing code
        sof_bull = last_high > prev_highs.max()
        sof_bear = last_low < prev_lows.min()
        
        # Market-specific validation
        if self.market_type == 'forex':
            sof_bull = sof_bull and self.validate_forex_sof(df, 'bullish')
            sof_bear = sof_bear and self.validate_forex_sof(df, 'bearish')
        elif self.market_type == 'crypto':
            sof_bull = sof_bull and self.validate_crypto_sof(df, 'bullish')
            sof_bear = sof_bear and self.validate_crypto_sof(df, 'bearish')
        
        return sof_bull, sof_bear
    
    def validate_forex_sof(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate SOF for forex markets"""
        try:
            # Forex SOF requires session-based validation
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                
                # SOF more significant during major sessions
                if 8 <= hour <= 22:  # London or NY session
                    return True
                else:
                    # Require stronger confirmation outside major sessions
                    if 'volume' in df.columns:
                        # Even though forex doesn't have centralized volume,
                        # tick volume can still be meaningful
                        current_vol = df['volume'].iloc[-1]
                        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
                        return current_vol > 1.2 * avg_vol
                    return False
            
            return True  # Default if no time info
            
        except Exception:
            return True
    
    def validate_crypto_sof(self, df: pd.DataFrame, direction: str) -> bool:
        """Validate SOF for crypto markets"""
        try:
            # Crypto SOF requires volume confirmation
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                
                # Require elevated volume for crypto SOF
                if current_volume > 1.5 * avg_volume:
                    return True
                else:
                    return False
            
            # Also check volatility
            if 'atr' in df.columns:
                current_atr = df['atr'].iloc[-1]
                avg_atr = df['atr'].rolling(20).mean().iloc[-1]
                return current_atr > 1.3 * avg_atr
            
            return True  # Default
            
        except Exception:
            return True
    
    def analyze_sof_patterns(self, df: pd.DataFrame, sof_bull: bool, sof_bear: bool) -> Dict[str, Any]:
        """
        Analyze SOF patterns and characteristics
        """
        analysis = {
            'sof_strength': 0.0,
            'reversal_probability': 0.0,
            'continuation_probability': 0.0,
            'market_context': self.get_market_context(df)
        }
        
        if sof_bull or sof_bear:
            # Calculate SOF strength
            analysis['sof_strength'] = self.calculate_individual_sof_strength(df, sof_bull, sof_bear)
            
            # Estimate probabilities based on market type and context
            if self.market_type == 'forex':
                analysis['reversal_probability'] = 0.65  # Forex SOF often leads to reversal
                analysis['continuation_probability'] = 0.35
            elif self.market_type == 'crypto':
                analysis['reversal_probability'] = 0.55  # Crypto can be more unpredictable
                analysis['continuation_probability'] = 0.45
            
            # Adjust based on market context
            if analysis['market_context']['trending']:
                analysis['continuation_probability'] += 0.15
                analysis['reversal_probability'] -= 0.15
        
        return analysis
    
    def get_market_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get market context for SOF analysis"""
        context = {
            'trending': False,
            'trend_direction': 'neutral',
            'volatility_regime': 'normal',
            'session_context': 'unknown'
        }
        
        if len(df) < 20:
            return context
        
        # Trend analysis
        recent_highs = df['high'].iloc[-20:]
        recent_lows = df['low'].iloc[-20:]
        
        if recent_highs.iloc[-1] > recent_highs.iloc[0] and recent_lows.iloc[-1] > recent_lows.iloc[0]:
            context['trending'] = True
            context['trend_direction'] = 'bullish'
        elif recent_highs.iloc[-1] < recent_highs.iloc[0] and recent_lows.iloc[-1] < recent_lows.iloc[0]:
            context['trending'] = True
            context['trend_direction'] = 'bearish'
        
        # Volatility regime
        if 'atr' in df.columns:
            current_atr = df['atr'].iloc[-1]
            avg_atr = df['atr'].rolling(50).mean().iloc[-1]
            
            if current_atr > 1.5 * avg_atr:
                context['volatility_regime'] = 'high'
            elif current_atr < 0.7 * avg_atr:
                context['volatility_regime'] = 'low'
        
        # Session context (for forex)
        if self.market_type == 'forex' and hasattr(df.index[-1], 'hour'):
            hour = df.index[-1].hour
            if 13 <= hour <= 16:
                context['session_context'] = 'london_ny_overlap'
            elif 8 <= hour <= 17:
                context['session_context'] = 'london_session'
            elif 13 <= hour <= 22:
                context['session_context'] = 'ny_session'
            elif 22 <= hour <= 6:
                context['session_context'] = 'asian_session'
        
        return context
    
    def calculate_individual_sof_strength(self, df: pd.DataFrame, sof_bull: bool, sof_bear: bool) -> float:
        """Calculate individual SOF strength"""
        if not (sof_bull or sof_bear):
            return 0.0
        
        strength_factors = []
        
        # Distance of failure
        if sof_bull:
            prev_highs = df['high'].iloc[-(self.lookback+1):-1]
            failure_distance = (df['high'].iloc[-1] - prev_highs.max()) / prev_highs.max()
            strength_factors.append(min(failure_distance * 10, 1.0))
        
        if sof_bear:
            prev_lows = df['low'].iloc[-(self.lookback+1):-1]
            failure_distance = (prev_lows.min() - df['low'].iloc[-1]) / prev_lows.min()
            strength_factors.append(min(failure_distance * 10, 1.0))
        
        # Volume confirmation
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_strength = min(current_volume / avg_volume, 2.0) / 2.0
            strength_factors.append(volume_strength * self.volume_weight)
        
        return np.mean(strength_factors) if strength_factors else 0.5
    
    def generate_reversal_warnings(self, sof_bull: bool, sof_bear: bool, 
                                 sof_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate reversal warnings based on SOF"""
        warnings = []
        
        if sof_bull:
            warnings.append({
                'type': 'bullish_sof_reversal_warning',
                'message': f'Bullish SOF detected in {self.market_type} market - potential trend reversal',
                'probability': sof_analysis['reversal_probability'],
                'recommended_action': 'Watch for bearish reversal signals',
                'market_specific_note': self.get_market_specific_sof_note('bullish')
            })
        
        if sof_bear:
            warnings.append({
                'type': 'bearish_sof_reversal_warning',
                'message': f'Bearish SOF detected in {self.market_type} market - potential trend reversal',
                'probability': sof_analysis['reversal_probability'],
                'recommended_action': 'Watch for bullish reversal signals',
                'market_specific_note': self.get_market_specific_sof_note('bearish')
            })
        
        return warnings
    
    def get_market_specific_sof_note(self, direction: str) -> str:
        """Get market-specific SOF interpretation"""
        if self.market_type == 'forex':
            if direction == 'bullish':
                return "Forex bullish SOF: Watch for central bank intervention or session-end profit taking"
            else:
                return "Forex bearish SOF: Monitor for safe-haven flows or risk-off sentiment"
        elif self.market_type == 'crypto':
            if direction == 'bullish':
                return "Crypto bullish SOF: Potential whale profit-taking or resistance test failure"
            else:
                return "Crypto bearish SOF: Possible support breakdown or panic selling exhaustion"
        
        return f"SOF detected - monitor for trend reversal"
    
    def get_sof_trading_implications(self, sof_bull: bool, sof_bear: bool, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Get trading implications of SOF patterns"""
        implications = []
        
        if sof_bull:
            implications.append({
                'sof_type': 'bullish',
                'immediate_implication': 'Downtrend failure - expect reversal or consolidation',
                'trading_bias': 'Prepare for long entries',
                'risk_level': 'Medium-High',
                'time_horizon': 'Short to Medium term',
                'market_specific_strategy': self.get_market_specific_strategy('bullish', df)
            })
        
        if sof_bear:
            implications.append({
                'sof_type': 'bearish',
                'immediate_implication': 'Uptrend failure - expect reversal or consolidation',
                'trading_bias': 'Prepare for short entries',
                'risk_level': 'Medium-High',
                'time_horizon': 'Short to Medium term',
                'market_specific_strategy': self.get_market_specific_strategy('bearish', df)
            })
        
        return implications
    
    def get_market_specific_strategy(self, direction: str, df: pd.DataFrame) -> str:
        """Get market-specific trading strategy for SOF"""
        if self.market_type == 'forex':
            if direction == 'bullish':
                strategy = "Forex bullish SOF strategy: "
                if hasattr(df.index[-1], 'hour'):
                    hour = df.index[-1].hour
                    if 13 <= hour <= 16:
                        strategy += "London-NY overlap - high probability reversal. Look for long entries with tight stops."
                    else:
                        strategy += "Outside major session - wait for session confirmation before entering."
                else:
                    strategy += "Monitor for session-based confirmation of reversal."
            else:
                strategy = "Forex bearish SOF strategy: Monitor for risk-off sentiment confirmation."
        
        elif self.market_type == 'crypto':
            if direction == 'bullish':
                strategy = "Crypto bullish SOF strategy: "
                if 'volume' in df.columns:
                    vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                    if vol_ratio > 2.0:
                        strategy += "High volume SOF - strong reversal signal. Consider long entries."
                    else:
                        strategy += "Low volume SOF - wait for volume confirmation."
                else:
                    strategy += "Monitor volume for reversal confirmation."
            else:
                strategy = "Crypto bearish SOF strategy: Watch for panic selling exhaustion and volume climax."
        
        else:
            strategy = f"General SOF strategy: Monitor for reversal confirmation signals."
        
        return strategy
    
    def calculate_sof_signal_strength(self, sof_bull: bool, sof_bear: bool, 
                                    sof_analysis: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate SOF signal strength
        """
        if not (sof_bull or sof_bear):
            return 0.0
        
        strength_factors = []
        
        # Base SOF strength
        base_strength = 0.7  # SOF is a strong reversal signal
        strength_factors.append(base_strength)
        
        # SOF analysis strength
        if 'sof_strength' in sof_analysis:
            strength_factors.append(sof_analysis['sof_strength'])
        
        # Market-specific strength adjustments
        market_strength = self.get_market_specific_strength(df)
        strength_factors.append(market_strength)
        
        # Volume confirmation (more important for crypto)
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
            
            if self.market_type == 'crypto':
                strength_factors.append(volume_factor * 0.8)  # High weight for crypto
            else:
                strength_factors.append(volume_factor * 0.3)  # Lower weight for forex
        
        # Multiple SOF confluence
        if sof_bull and sof_bear:
            strength_factors.append(0.9)  # Very strong signal
        
        return np.mean(strength_factors)
    
    def get_market_specific_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific strength adjustment"""
        if self.market_type == 'forex':
            # Forex strength based on session
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:  # London-NY overlap
                    return 0.9
                elif 8 <= hour <= 22:  # Major sessions
                    return 0.8
                else:  # Asian session
                    return 0.5
            return 0.7
        
        elif self.market_type == 'crypto':
            # Crypto strength based on volatility and volume
            strength = 0.7
            
            if 'atr' in df.columns:
                current_atr = df['atr'].iloc[-1]
                avg_atr = df['atr'].rolling(50).mean().iloc[-1]
                volatility_factor = min(current_atr / avg_atr, 2.0) / 2.0
                strength += volatility_factor * 0.2
            
            return min(strength, 1.0)
        
        return 0.7
    
    def update_sof_tracking(self, sof_bull: bool, sof_bear: bool, df: pd.DataFrame):
        """Update SOF event tracking"""
        if sof_bull or sof_bear:
            sof_event = {
                'timestamp': datetime.now(timezone.utc),
                'sof_bull': sof_bull,
                'sof_bear': sof_bear,
                'price': df['close'].iloc[-1],
                'market_type': self.market_type,
                'lookback_period': self.lookback
            }
            
            self.sof_events.append(sof_event)
            
            # Add to active warnings
            warning = {
                'timestamp': datetime.now(timezone.utc),
                'type': 'bullish_sof' if sof_bull else 'bearish_sof',
                'price': df['close'].iloc[-1],
                'expires_after_bars': 20  # SOF warning expires after 20 bars
            }
            self.active_sof_warnings.append(warning)
            
            # Limit tracking sizes
            if len(self.sof_events) > 100:
                self.sof_events = self.sof_events[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_sof_summary(self) -> Dict[str, Any]:
        """Get comprehensive SOF summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'sof_events_count': len(self.sof_events),
            'active_warnings_count': len(self.active_sof_warnings),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'confirmation_bars': self.confirmation_bars,
                'confirmation_threshold': self.confirmation_threshold
            }
        }
    
    def has_active_sof_warning(self, sof_type: str = None) -> bool:
        """Check if there are active SOF warnings"""
        if sof_type:
            return any(warning['type'] == sof_type for warning in self.active_sof_warnings)
        return len(self.active_sof_warnings) > 0
    
    def requires_continuous_processing(self) -> bool:
        """SOF agent doesn't need continuous processing"""
        return False