"""
Breaker Blocks Agent
Detects breaker blocks (failed order blocks) using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class BreakerBlocksAgent(ICTSMCAgent):
    """
    Specialized agent for Breaker Block detection
    Uses existing detect_breaker_blocks() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("breaker_blocks", config)
        
        # Breaker block configuration
        self.lookback = config.get('lookback', 30)
        self.min_confirmation_bars = config.get('min_confirmation_bars', 2)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')  # 'crypto' or 'forex'
        
        # Breaker block tracking
        self.active_breaker_blocks = []
        self.validated_breakers = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Breaker Blocks Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific configuration adjustments"""
        if self.market_type == 'forex':
            # Forex markets are more liquid, need tighter parameters
            self.lookback = min(self.lookback, 20)
            self.min_confirmation_bars = 3
            self.volume_weight = 0.3  # Volume less important in forex
        elif self.market_type == 'crypto':
            # Crypto markets are more volatile, need wider parameters
            self.lookback = max(self.lookback, 30)
            self.min_confirmation_bars = 2
            self.volume_weight = 0.7  # Volume very important in crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect breaker blocks
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with breaker block analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback + 3:
            return {'breaker_blocks': [], 'signal_strength': 0.0}
        
        try:
            # Use existing detect_breaker_blocks function
            bullish_breaker, bearish_breaker = self.detect_breaker_blocks(df, self.lookback)
            
            # Get detailed breaker block information
            breaker_details = self.get_breaker_block_details(df, self.lookback)
            
            # Update tracking
            self.update_breaker_tracking(breaker_details, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_breaker_signal_strength(
                bullish_breaker, bearish_breaker, breaker_details, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bullish_breaker': bullish_breaker,
                'bearish_breaker': bearish_breaker,
                'breaker_details': breaker_details,
                'active_breakers': self.active_breaker_blocks,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_opportunities': self.identify_breaker_opportunities(
                    bullish_breaker, bearish_breaker, breaker_details, df
                )
            }
            
            # Publish breaker block signals
            if bullish_breaker or bearish_breaker:
                self.publish("breaker_block_detected", {
                    'symbol': symbol,
                    'bullish_breaker': bullish_breaker,
                    'bearish_breaker': bearish_breaker,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing breaker block data for {symbol}: {e}")
            return {'breaker_blocks': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_breaker_blocks(self, df: pd.DataFrame, lookback: int = 30) -> tuple:
        """
        Detect breaker blocks using existing implementation from tradingbot_new.py
        """
        if len(df) < lookback + 3:
            return False, False
        
        bullish_breaker = False
        bearish_breaker = False
        
        for i in range(len(df) - lookback, len(df) - 2):
            # Bullish breaker: sweep a low, then break above a down candle, then retest
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['close'].iloc[i+1] > df['high'].iloc[i]):
                
                # Retest: last bar closes above the breaker candle's high
                if (df['low'].iloc[-1] <= df['high'].iloc[i] and 
                    df['close'].iloc[-1] > df['high'].iloc[i]):
                    
                    # Market-specific validation
                    if self.validate_breaker_for_market(df, i, 'bullish'):
                        bullish_breaker = True
            
            # Bearish breaker: sweep a high, then break below an up candle, then retest
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['close'].iloc[i+1] < df['low'].iloc[i]):
                
                # Retest: last bar closes below the breaker candle's low
                if (df['high'].iloc[-1] >= df['low'].iloc[i] and 
                    df['close'].iloc[-1] < df['low'].iloc[i]):
                    
                    # Market-specific validation
                    if self.validate_breaker_for_market(df, i, 'bearish'):
                        bearish_breaker = True
        
        return bullish_breaker, bearish_breaker
    
    def validate_breaker_for_market(self, df: pd.DataFrame, index: int, breaker_type: str) -> bool:
        """
        Validate breaker block based on market type
        """
        if self.market_type == 'forex':
            # Forex validation: Check for session-based confirmation
            return self.validate_forex_breaker(df, index, breaker_type)
        elif self.market_type == 'crypto':
            # Crypto validation: Check for volume confirmation
            return self.validate_crypto_breaker(df, index, breaker_type)
        else:
            return True  # Default validation
    
    def validate_forex_breaker(self, df: pd.DataFrame, index: int, breaker_type: str) -> bool:
        """Validate breaker block for forex markets"""
        try:
            # Forex-specific validation
            # Check if breaker occurs during major session overlap
            if hasattr(df.index[index], 'hour'):
                hour = df.index[index].hour
                
                # London-NY overlap (13:00-16:00 UTC) is most significant for forex
                if 13 <= hour <= 16:
                    return True
                
                # London session (8:00-17:00 UTC)
                elif 8 <= hour <= 17:
                    return True
                
                # NY session (13:00-22:00 UTC)
                elif 13 <= hour <= 22:
                    return True
                
                # Less significant during Asian session
                else:
                    return False
            
            return True  # Default if no time info
            
        except Exception:
            return True
    
    def validate_crypto_breaker(self, df: pd.DataFrame, index: int, breaker_type: str) -> bool:
        """Validate breaker block for crypto markets"""
        try:
            # Crypto-specific validation
            # Volume is crucial in crypto markets
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[index]
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                
                # Require above-average volume for crypto breakers
                if current_volume > 1.3 * avg_volume:
                    return True
                else:
                    return False
            
            # Also check for volatility (crypto is more volatile)
            if 'atr' in df.columns:
                current_atr = df['atr'].iloc[index]
                avg_atr = df['atr'].rolling(20).mean().iloc[index]
                
                # Require elevated volatility
                if current_atr > 1.2 * avg_atr:
                    return True
            
            return True  # Default validation
            
        except Exception:
            return True
    
    def get_breaker_block_details(self, df: pd.DataFrame, lookback: int) -> List[Dict[str, Any]]:
        """
        Get detailed information about detected breaker blocks
        """
        breaker_details = []
        
        if len(df) < lookback + 3:
            return breaker_details
        
        for i in range(len(df) - lookback, len(df) - 2):
            # Check for bullish breaker formation
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['close'].iloc[i+1] > df['high'].iloc[i]):
                
                if (df['low'].iloc[-1] <= df['high'].iloc[i] and 
                    df['close'].iloc[-1] > df['high'].iloc[i]):
                    
                    breaker_details.append({
                        'type': 'bullish',
                        'formation_index': i,
                        'swept_level': df['low'].iloc[i],
                        'break_level': df['high'].iloc[i],
                        'retest_confirmed': True,
                        'strength': self.calculate_breaker_strength(df, i, 'bullish'),
                        'timestamp': df.index[i] if i < len(df) else None,
                        'market_type': self.market_type
                    })
            
            # Check for bearish breaker formation
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['close'].iloc[i+1] < df['low'].iloc[i]):
                
                if (df['high'].iloc[-1] >= df['low'].iloc[i] and 
                    df['close'].iloc[-1] < df['low'].iloc[i]):
                    
                    breaker_details.append({
                        'type': 'bearish',
                        'formation_index': i,
                        'swept_level': df['high'].iloc[i],
                        'break_level': df['low'].iloc[i],
                        'retest_confirmed': True,
                        'strength': self.calculate_breaker_strength(df, i, 'bearish'),
                        'timestamp': df.index[i] if i < len(df) else None,
                        'market_type': self.market_type
                    })
        
        return breaker_details
    
    def calculate_breaker_strength(self, df: pd.DataFrame, index: int, breaker_type: str) -> float:
        """
        Calculate breaker block strength with market-specific factors
        """
        try:
            strength_factors = []
            
            # Volume strength (weighted by market type)
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[index]
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                volume_strength = min(current_volume / avg_volume, 3.0) / 3.0
                strength_factors.append(volume_strength * self.volume_weight)
            
            # Price movement strength
            if breaker_type == 'bullish':
                price_move = (df['high'].iloc[index+1] - df['low'].iloc[index]) / df['low'].iloc[index]
            else:
                price_move = (df['high'].iloc[index] - df['low'].iloc[index+1]) / df['high'].iloc[index]
            
            move_strength = min(price_move * 20, 1.0)  # Normalize large moves
            strength_factors.append(move_strength)
            
            # Time-based strength (for forex)
            if self.market_type == 'forex' and hasattr(df.index[index], 'hour'):
                time_strength = self.calculate_forex_time_strength(df.index[index].hour)
                strength_factors.append(time_strength)
            
            # Volatility strength (for crypto)
            if self.market_type == 'crypto' and 'atr' in df.columns:
                atr = df['atr'].iloc[index]
                candle_range = df['high'].iloc[index] - df['low'].iloc[index]
                volatility_strength = min(candle_range / atr, 2.0) / 2.0
                strength_factors.append(volatility_strength)
            
            return np.mean(strength_factors) if strength_factors else 0.5
            
        except Exception:
            return 0.5
    
    def calculate_forex_time_strength(self, hour: int) -> float:
        """Calculate time-based strength for forex markets"""
        # London-NY overlap (strongest)
        if 13 <= hour <= 16:
            return 1.0
        # London session
        elif 8 <= hour <= 17:
            return 0.8
        # NY session
        elif 13 <= hour <= 22:
            return 0.8
        # Asian session
        elif 22 <= hour <= 6:
            return 0.5
        else:
            return 0.3
    
    def identify_breaker_opportunities(self, bullish_breaker: bool, bearish_breaker: bool, 
                                    breaker_details: List[Dict[str, Any]], 
                                    df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify trading opportunities based on breaker blocks
        """
        opportunities = []
        
        if bullish_breaker:
            opportunities.append({
                'type': 'bullish_breaker',
                'direction': 'long',
                'reason': f'Bullish breaker confirmed - {self.market_type} market',
                'strength': 0.8,
                'market_specific_factors': self.get_market_specific_factors(df, 'bullish')
            })
        
        if bearish_breaker:
            opportunities.append({
                'type': 'bearish_breaker',
                'direction': 'short',
                'reason': f'Bearish breaker confirmed - {self.market_type} market',
                'strength': 0.8,
                'market_specific_factors': self.get_market_specific_factors(df, 'bearish')
            })
        
        return opportunities
    
    def get_market_specific_factors(self, df: pd.DataFrame, direction: str) -> List[str]:
        """Get market-specific confirmation factors"""
        factors = []
        
        if self.market_type == 'forex':
            # Forex-specific factors
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:
                    factors.append('london_ny_overlap')
                elif 8 <= hour <= 17:
                    factors.append('london_session')
                elif 13 <= hour <= 22:
                    factors.append('ny_session')
            
            # Check for news events (simplified)
            factors.append('forex_session_active')
        
        elif self.market_type == 'crypto':
            # Crypto-specific factors
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                if current_volume > 2.0 * avg_volume:
                    factors.append('high_volume_confirmation')
            
            # 24/7 market - no session restrictions
            factors.append('crypto_24_7_market')
            
            # Volatility factor
            if 'atr' in df.columns:
                current_atr = df['atr'].iloc[-1]
                avg_atr = df['atr'].rolling(20).mean().iloc[-1]
                if current_atr > 1.5 * avg_atr:
                    factors.append('elevated_volatility')
        
        return factors
    
    def calculate_breaker_signal_strength(self, bullish_breaker: bool, bearish_breaker: bool,
                                        breaker_details: List[Dict[str, Any]], 
                                        df: pd.DataFrame) -> float:
        """
        Calculate breaker block signal strength
        """
        if not (bullish_breaker or bearish_breaker):
            return 0.0
        
        strength_factors = []
        
        # Base breaker strength
        if bullish_breaker or bearish_breaker:
            base_strength = 0.8
            strength_factors.append(base_strength)
        
        # Breaker detail strength
        if breaker_details:
            avg_detail_strength = np.mean([detail['strength'] for detail in breaker_details])
            strength_factors.append(avg_detail_strength)
        
        # Market-specific strength adjustments
        market_adjustment = self.get_market_strength_adjustment(df)
        strength_factors.append(market_adjustment)
        
        # Multiple breaker confluence
        if bullish_breaker and bearish_breaker:
            strength_factors.append(0.9)  # High strength for both directions
        
        return np.mean(strength_factors)
    
    def get_market_strength_adjustment(self, df: pd.DataFrame) -> float:
        """Get market-specific strength adjustment"""
        if self.market_type == 'forex':
            # Forex strength based on session
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                return self.calculate_forex_time_strength(hour)
            return 0.7
        
        elif self.market_type == 'crypto':
            # Crypto strength based on volume and volatility
            strength = 0.7  # Base
            
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
                strength += volume_factor * 0.3
            
            return min(strength, 1.0)
        
        return 0.7
    
    def update_breaker_tracking(self, breaker_details: List[Dict[str, Any]], df: pd.DataFrame):
        """Update breaker block tracking"""
        # Add new breakers
        for breaker in breaker_details:
            if breaker not in self.active_breaker_blocks:
                breaker['detected_time'] = datetime.now(timezone.utc)
                self.active_breaker_blocks.append(breaker)
        
        # Validate existing breakers
        current_price = df['close'].iloc[-1]
        still_active = []
        
        for breaker in self.active_breaker_blocks:
            if self.is_breaker_still_valid(breaker, current_price):
                still_active.append(breaker)
            else:
                breaker['invalidated_time'] = datetime.now(timezone.utc)
                self.validated_breakers.append(breaker)
        
        self.active_breaker_blocks = still_active
        
        # Limit tracking sizes
        if len(self.active_breaker_blocks) > 50:
            self.active_breaker_blocks = self.active_breaker_blocks[-50:]
    
    def is_breaker_still_valid(self, breaker: Dict[str, Any], current_price: float) -> bool:
        """Check if breaker block is still valid"""
        # Simplified validation - could be enhanced
        if breaker['type'] == 'bullish':
            return current_price >= breaker['break_level']
        else:
            return current_price <= breaker['break_level']
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_breaker_summary(self) -> Dict[str, Any]:
        """Get comprehensive breaker block summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'active_breakers_count': len(self.active_breaker_blocks),
            'validated_breakers_count': len(self.validated_breakers),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'min_confirmation_bars': self.min_confirmation_bars,
                'volume_weight': self.volume_weight
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Breaker blocks agent doesn't need continuous processing"""
        return False