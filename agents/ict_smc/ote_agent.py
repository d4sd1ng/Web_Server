"""
Optimal Trade Entry (OTE) Agent
Analyzes OTE zones using Fibonacci retracement levels
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class OTEAgent(ICTSMCAgent):
    """
    Specialized agent for Optimal Trade Entry zone analysis
    Uses existing calculate_ote_and_targets() function
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ote", config)
        
        # OTE configuration
        self.swing_lookback = config.get('swing_lookback', 20)
        self.fib_618_level = config.get('fib_618_level', 0.618)
        self.fib_786_level = config.get('fib_786_level', 0.786)
        self.ote_fib_level = config.get('ote_fib_level', 0.705)  # From your config
        
        # OTE tracking
        self.current_ote_zones = {'long': None, 'short': None}
        self.ote_history = []
        self.successful_otes = []
        
        self.logger.info("OTE Agent initialized")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to analyze OTE zones
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with OTE analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.swing_lookback:
            return {'ote_zones': {}, 'signal_strength': 0.0}
        
        try:
            # Calculate OTE zones for both directions using existing function
            ote_long = self.calculate_ote_and_targets(df, direction='long', swing_lookback=self.swing_lookback)
            ote_short = self.calculate_ote_and_targets(df, direction='short', swing_lookback=self.swing_lookback)
            
            # Analyze current price position relative to OTE zones
            current_price = df['close'].iloc[-1]
            ote_analysis = self.analyze_ote_position(ote_long, ote_short, current_price)
            
            # Calculate signal strength
            signal_strength = self.calculate_ote_signal_strength(ote_long, ote_short, current_price, df)
            
            # Update OTE tracking
            self.update_ote_tracking(ote_long, ote_short, current_price)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ote_long': ote_long,
                'ote_short': ote_short,
                'ote_analysis': ote_analysis,
                'signal_strength': signal_strength,
                'trading_setups': self.identify_ote_setups(ote_long, ote_short, current_price, df),
                'fibonacci_levels': self.get_fibonacci_levels(df)
            }
            
            # Publish OTE signals
            if ote_analysis['in_ote_long'] or ote_analysis['in_ote_short']:
                self.publish("ote_zone_entry", {
                    'symbol': symbol,
                    'ote_type': 'long' if ote_analysis['in_ote_long'] else 'short',
                    'signal_strength': signal_strength,
                    'ote_zones': {'long': ote_long, 'short': ote_short}
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing OTE data for {symbol}: {e}")
            return {'ote_zones': {}, 'signal_strength': 0.0, 'error': str(e)}
    
    def calculate_ote_and_targets(self, df: pd.DataFrame, direction: str = 'long', swing_lookback: int = 20) -> Dict[str, Any]:
        """
        Calculate OTE zone and targets using existing implementation
        """
        swing_high = df['high'].iloc[-swing_lookback:].max()
        swing_low = df['low'].iloc[-swing_lookback:].min()
        
        if direction == 'long':
            # For long trades, OTE is in the lower part of the range
            ote_zone = (
                swing_high - self.fib_786_level * (swing_high - swing_low),
                swing_high - self.fib_618_level * (swing_high - swing_low)
            )
        else:
            # For short trades, OTE is in the upper part of the range
            ote_zone = (
                swing_low + self.fib_618_level * (swing_high - swing_low),
                swing_low + self.fib_786_level * (swing_high - swing_low)
            )
        
        # Ensure zone is properly ordered (low, high)
        ote_zone = tuple(sorted(ote_zone))
        
        price = df['close'].iloc[-1]
        in_ote = ote_zone[0] <= price <= ote_zone[1]
        entry = price
        
        if direction == 'long':
            sl = swing_low
            risk = entry - sl
            tp1 = entry + risk * 1
            tp2 = entry + risk * 2
            tp3 = entry + risk * 3
            tp4 = entry + risk * 4
        else:
            sl = swing_high
            risk = sl - entry
            tp1 = entry - risk * 1
            tp2 = entry - risk * 2
            tp3 = entry - risk * 3
            tp4 = entry - risk * 4
        
        return {
            'direction': direction,
            'swing_high': swing_high,
            'swing_low': swing_low,
            'ote_zone': ote_zone,
            'in_ote': in_ote,
            'entry': entry,
            'sl': sl,
            'risk': risk,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'tp4': tp4,
            'rr_ratio': 4.0,  # Risk:Reward for TP4
            'rr4_roi': 3.0,  # 300% ROI on risked amount
            'zone_width': ote_zone[1] - ote_zone[0],
            'distance_to_zone': self.calculate_distance_to_ote(price, ote_zone)
        }
    
    def calculate_distance_to_ote(self, price: float, ote_zone: tuple) -> float:
        """Calculate distance from current price to OTE zone"""
        zone_low, zone_high = ote_zone
        
        if zone_low <= price <= zone_high:
            return 0.0  # Price is in OTE zone
        elif price < zone_low:
            return zone_low - price
        else:
            return price - zone_high
    
    def analyze_ote_position(self, ote_long: Dict[str, Any], ote_short: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Analyze current price position relative to OTE zones
        """
        return {
            'in_ote_long': ote_long['in_ote'],
            'in_ote_short': ote_short['in_ote'],
            'distance_to_long_ote': ote_long['distance_to_zone'],
            'distance_to_short_ote': ote_short['distance_to_zone'],
            'closer_to_long_ote': ote_long['distance_to_zone'] < ote_short['distance_to_zone'],
            'closer_to_short_ote': ote_short['distance_to_zone'] < ote_long['distance_to_zone'],
            'in_any_ote': ote_long['in_ote'] or ote_short['in_ote'],
            'ote_preference': 'long' if ote_long['in_ote'] else 'short' if ote_short['in_ote'] else 'none'
        }
    
    def identify_ote_setups(self, ote_long: Dict[str, Any], ote_short: Dict[str, Any], 
                           current_price: float, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify OTE trading setups
        """
        setups = []
        
        # Long OTE setup
        if ote_long['in_ote']:
            setups.append({
                'direction': 'long',
                'setup_type': 'ote_entry',
                'entry_zone': ote_long['ote_zone'],
                'entry_price': current_price,
                'stop_loss': ote_long['sl'],
                'take_profit_1': ote_long['tp1'],
                'take_profit_2': ote_long['tp2'],
                'take_profit_3': ote_long['tp3'],
                'take_profit_4': ote_long['tp4'],
                'risk_amount': ote_long['risk'],
                'risk_reward_ratio': ote_long['rr_ratio'],
                'setup_quality': self.assess_ote_quality(ote_long, df),
                'confluence_factors': self.get_ote_confluence(ote_long, df, 'long')
            })
        
        # Short OTE setup
        if ote_short['in_ote']:
            setups.append({
                'direction': 'short',
                'setup_type': 'ote_entry',
                'entry_zone': ote_short['ote_zone'],
                'entry_price': current_price,
                'stop_loss': ote_short['sl'],
                'take_profit_1': ote_short['tp1'],
                'take_profit_2': ote_short['tp2'],
                'take_profit_3': ote_short['tp3'],
                'take_profit_4': ote_short['tp4'],
                'risk_amount': ote_short['risk'],
                'risk_reward_ratio': ote_short['rr_ratio'],
                'setup_quality': self.assess_ote_quality(ote_short, df),
                'confluence_factors': self.get_ote_confluence(ote_short, df, 'short')
            })
        
        return setups
    
    def assess_ote_quality(self, ote_data: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Assess the quality of an OTE setup
        """
        quality_factors = []
        
        # Zone width quality (tighter zones are better)
        zone_width = ote_data['zone_width']
        if 'atr' in df.columns:
            atr = df['atr'].iloc[-1]
            width_quality = max(0, 1 - (zone_width / atr))  # Better if zone < 1 ATR
            quality_factors.append(width_quality)
        
        # Risk:Reward quality
        rr_ratio = ote_data['rr_ratio']
        rr_quality = min(rr_ratio / 4.0, 1.0)  # Normalize to 1.0 at 4:1 RR
        quality_factors.append(rr_quality)
        
        # Distance to stop loss (closer stop = higher quality)
        risk = ote_data['risk']
        entry = ote_data['entry']
        if entry > 0:
            risk_quality = max(0, 1 - (risk / entry * 20))  # Penalize if risk > 5% of entry
            quality_factors.append(risk_quality)
        
        # Volume confirmation
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_quality = min(current_volume / avg_volume, 2.0) / 2.0
            quality_factors.append(volume_quality)
        
        return np.mean(quality_factors) if quality_factors else 0.5
    
    def get_ote_confluence(self, ote_data: Dict[str, Any], df: pd.DataFrame, direction: str) -> List[str]:
        """
        Get confluence factors for OTE setup
        """
        confluence_factors = []
        
        # Always in OTE if we're calling this
        confluence_factors.append('in_ote_zone')
        
        # Check for additional confluence
        current_price = df['close'].iloc[-1]
        
        # Volume confluence
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            if current_volume > 1.5 * avg_volume:
                confluence_factors.append('volume_confirmation')
        
        # Price action confluence
        if direction == 'long':
            # Look for bullish price action in OTE zone
            if df['close'].iloc[-1] > df['open'].iloc[-1]:
                confluence_factors.append('bullish_candle')
            
            # Check for higher low formation
            if len(df) >= 3 and df['low'].iloc[-1] > df['low'].iloc[-2]:
                confluence_factors.append('higher_low')
        
        else:  # short direction
            # Look for bearish price action in OTE zone
            if df['close'].iloc[-1] < df['open'].iloc[-1]:
                confluence_factors.append('bearish_candle')
            
            # Check for lower high formation
            if len(df) >= 3 and df['high'].iloc[-1] < df['high'].iloc[-2]:
                confluence_factors.append('lower_high')
        
        # RSI confluence (if available)
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if direction == 'long' and rsi < 40:
                confluence_factors.append('oversold_rsi')
            elif direction == 'short' and rsi > 60:
                confluence_factors.append('overbought_rsi')
        
        return confluence_factors
    
    def get_fibonacci_levels(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate comprehensive Fibonacci levels
        """
        if len(df) < self.swing_lookback:
            return {}
        
        swing_high = df['high'].iloc[-self.swing_lookback:].max()
        swing_low = df['low'].iloc[-self.swing_lookback:].min()
        range_size = swing_high - swing_low
        
        # Standard Fibonacci levels
        fib_levels = {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'range_size': range_size,
            'fib_0': swing_high,
            'fib_236': swing_high - 0.236 * range_size,
            'fib_382': swing_high - 0.382 * range_size,
            'fib_500': swing_high - 0.500 * range_size,
            'fib_618': swing_high - 0.618 * range_size,
            'fib_705': swing_high - 0.705 * range_size,  # Your OTE level
            'fib_786': swing_high - 0.786 * range_size,
            'fib_886': swing_high - 0.886 * range_size,
            'fib_100': swing_low,
            'fib_1272': swing_low - 0.272 * range_size,  # Extension
            'fib_1618': swing_low - 0.618 * range_size   # Extension
        }
        
        # Calculate current price position
        current_price = df['close'].iloc[-1]
        price_position = (current_price - swing_low) / range_size if range_size > 0 else 0.5
        
        fib_levels['current_price_position'] = price_position
        fib_levels['nearest_fib_level'] = self.find_nearest_fib_level(current_price, fib_levels)
        
        return fib_levels
    
    def find_nearest_fib_level(self, price: float, fib_levels: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find the nearest Fibonacci level to current price
        """
        fib_prices = {
            level: fib_levels[level] for level in fib_levels 
            if level.startswith('fib_') and isinstance(fib_levels[level], (int, float))
        }
        
        if not fib_prices:
            return {}
        
        # Find closest level
        closest_level = min(fib_prices.items(), key=lambda x: abs(x[1] - price))
        
        return {
            'level_name': closest_level[0],
            'level_price': closest_level[1],
            'distance': abs(closest_level[1] - price),
            'distance_percent': abs(closest_level[1] - price) / price * 100
        }
    
    def calculate_ote_signal_strength(self, ote_long: Dict[str, Any], ote_short: Dict[str, Any], 
                                    current_price: float, df: pd.DataFrame) -> float:
        """
        Calculate OTE signal strength
        """
        strength_factors = []
        
        # In-zone strength
        if ote_long['in_ote']:
            # Calculate position within OTE zone
            zone_low, zone_high = ote_long['ote_zone']
            zone_position = (current_price - zone_low) / (zone_high - zone_low)
            # Stronger signal closer to optimal level (0.705)
            optimal_position = 0.5  # Middle of OTE zone is optimal
            position_strength = 1 - abs(zone_position - optimal_position)
            strength_factors.append(position_strength)
        
        if ote_short['in_ote']:
            zone_low, zone_high = ote_short['ote_zone']
            zone_position = (current_price - zone_low) / (zone_high - zone_low)
            position_strength = 1 - abs(zone_position - 0.5)
            strength_factors.append(position_strength)
        
        # Risk:Reward strength
        if ote_long['in_ote']:
            rr_strength = min(ote_long['rr_ratio'] / 4.0, 1.0)
            strength_factors.append(rr_strength)
        
        if ote_short['in_ote']:
            rr_strength = min(ote_short['rr_ratio'] / 4.0, 1.0)
            strength_factors.append(rr_strength)
        
        # Volume confirmation
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_strength = min(current_volume / avg_volume, 2.0) / 2.0
            strength_factors.append(volume_strength * 0.5)
        
        # Historical OTE success rate
        success_rate = self.calculate_ote_success_rate()
        strength_factors.append(success_rate)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def calculate_ote_success_rate(self) -> float:
        """
        Calculate historical OTE success rate
        """
        if len(self.ote_history) < 10:
            return 0.5  # Default
        
        successful_otes = len(self.successful_otes)
        total_otes = len(self.ote_history)
        
        return successful_otes / total_otes if total_otes > 0 else 0.5
    
    def update_ote_tracking(self, ote_long: Dict[str, Any], ote_short: Dict[str, Any], current_price: float):
        """
        Update OTE tracking and history
        """
        # Update current OTE zones
        self.current_ote_zones['long'] = ote_long
        self.current_ote_zones['short'] = ote_short
        
        # Add to history if price is in any OTE zone
        if ote_long['in_ote'] or ote_short['in_ote']:
            ote_entry = {
                'timestamp': datetime.now(timezone.utc),
                'price': current_price,
                'ote_long': ote_long.copy(),
                'ote_short': ote_short.copy(),
                'active_direction': 'long' if ote_long['in_ote'] else 'short'
            }
            
            self.ote_history.append(ote_entry)
            
            # Limit history size
            if len(self.ote_history) > 200:
                self.ote_history = self.ote_history[-200:]
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_ote_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive OTE summary
        """
        return {
            'agent_id': self.agent_id,
            'current_ote_zones': self.current_ote_zones,
            'ote_history_count': len(self.ote_history),
            'successful_otes_count': len(self.successful_otes),
            'ote_success_rate': self.calculate_ote_success_rate(),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'swing_lookback': self.swing_lookback,
                'fib_618_level': self.fib_618_level,
                'fib_786_level': self.fib_786_level,
                'ote_fib_level': self.ote_fib_level
            }
        }
    
    def is_in_ote_long(self, price: float = None) -> bool:
        """Check if price is in long OTE zone"""
        if price is None:
            return self.current_ote_zones['long']['in_ote'] if self.current_ote_zones['long'] else False
        
        if self.current_ote_zones['long']:
            zone_low, zone_high = self.current_ote_zones['long']['ote_zone']
            return zone_low <= price <= zone_high
        
        return False
    
    def is_in_ote_short(self, price: float = None) -> bool:
        """Check if price is in short OTE zone"""
        if price is None:
            return self.current_ote_zones['short']['in_ote'] if self.current_ote_zones['short'] else False
        
        if self.current_ote_zones['short']:
            zone_low, zone_high = self.current_ote_zones['short']['ote_zone']
            return zone_low <= price <= zone_high
        
        return False
    
    def is_in_any_ote(self, price: float = None) -> bool:
        """Check if price is in any OTE zone"""
        return self.is_in_ote_long(price) or self.is_in_ote_short(price)
    
    def get_ote_targets(self, direction: str) -> Dict[str, float]:
        """Get OTE targets for specified direction"""
        if direction == 'long' and self.current_ote_zones['long']:
            ote_data = self.current_ote_zones['long']
            return {
                'entry': ote_data['entry'],
                'sl': ote_data['sl'],
                'tp1': ote_data['tp1'],
                'tp2': ote_data['tp2'],
                'tp3': ote_data['tp3'],
                'tp4': ote_data['tp4']
            }
        elif direction == 'short' and self.current_ote_zones['short']:
            ote_data = self.current_ote_zones['short']
            return {
                'entry': ote_data['entry'],
                'sl': ote_data['sl'],
                'tp1': ote_data['tp1'],
                'tp2': ote_data['tp2'],
                'tp3': ote_data['tp3'],
                'tp4': ote_data['tp4']
            }
        
        return {}
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "price_update":
            # Update OTE zone status
            symbol = message['data']['symbol']
            price_data = message['data']
            
            if 'close' in price_data:
                self.check_ote_zone_changes(price_data['close'])
        
        elif topic == "market_structure_shift":
            # Market structure shifts may invalidate current OTE zones
            self.logger.info("Market structure shift - recalculating OTE zones")
        
        super().on_message(topic, message)
    
    def check_ote_zone_changes(self, current_price: float):
        """
        Check for OTE zone entry/exit events
        """
        if not self.current_ote_zones['long'] or not self.current_ote_zones['short']:
            return
        
        # Check long OTE zone
        long_ote = self.current_ote_zones['long']
        zone_low, zone_high = long_ote['ote_zone']
        in_long_ote = zone_low <= current_price <= zone_high
        
        if in_long_ote and not long_ote['in_ote']:
            self.logger.info(f"Entered long OTE zone at {current_price}")
            self.publish("ote_zone_entry", {
                'direction': 'long',
                'price': current_price,
                'ote_zone': long_ote['ote_zone']
            })
        
        # Check short OTE zone
        short_ote = self.current_ote_zones['short']
        zone_low, zone_high = short_ote['ote_zone']
        in_short_ote = zone_low <= current_price <= zone_high
        
        if in_short_ote and not short_ote['in_ote']:
            self.logger.info(f"Entered short OTE zone at {current_price}")
            self.publish("ote_zone_entry", {
                'direction': 'short',
                'price': current_price,
                'ote_zone': short_ote['ote_zone']
            })
    
    def requires_continuous_processing(self) -> bool:
        """OTE agent doesn't need continuous background processing"""
        return False