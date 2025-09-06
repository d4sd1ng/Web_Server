"""
Premium/Discount Agent
Analyzes premium and discount zones using existing dealing range logic
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class PremiumDiscountAgent(ICTSMCAgent):
    """
    Specialized agent for Premium/Discount zone analysis
    Uses existing calculate_dealing_range() and get_pd_zone() functions
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("premium_discount", config)
        
        # Premium/Discount configuration
        self.swing_lookback = config.get('swing_lookback', 50)
        self.zone_threshold = config.get('zone_threshold', 0.1)  # 10% from equilibrium
        
        # Zone tracking
        self.current_dealing_range = None
        self.zone_history = []
        self.equilibrium_tests = []
        
        self.logger.info("Premium/Discount Agent initialized")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to analyze premium/discount zones
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with premium/discount analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.swing_lookback:
            return {'pd_zone': 'unknown', 'signal_strength': 0.0}
        
        try:
            # Calculate dealing range using existing function
            dealing_range = self.calculate_dealing_range(df, self.swing_lookback)
            
            # Get current premium/discount zone
            current_price = df['close'].iloc[-1]
            pd_zone = self.get_pd_zone(dealing_range, current_price)
            
            # Analyze zone characteristics
            zone_analysis = self.analyze_pd_zones(dealing_range, df, current_price)
            
            # Calculate signal strength
            signal_strength = self.calculate_pd_signal_strength(dealing_range, df, pd_zone)
            
            # Update zone tracking
            self.update_zone_tracking(dealing_range, pd_zone, current_price)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'dealing_range': dealing_range,
                'current_pd_zone': pd_zone,
                'zone_analysis': zone_analysis,
                'signal_strength': signal_strength,
                'trading_recommendations': self.get_pd_trading_recommendations(
                    dealing_range, pd_zone, current_price, df
                ),
                'zone_transitions': self.analyze_zone_transitions()
            }
            
            # Publish zone updates
            self.publish("pd_zone_update", {
                'symbol': symbol,
                'pd_zone': pd_zone,
                'dealing_range': dealing_range,
                'signal_strength': signal_strength
            })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing P/D zone data for {symbol}: {e}")
            return {'pd_zone': 'error', 'signal_strength': 0.0, 'error': str(e)}
    
    def calculate_dealing_range(self, df: pd.DataFrame, swing_lookback: int = 50) -> Dict[str, Any]:
        """
        Calculate dealing range using existing implementation
        """
        recent_high = df['high'].rolling(swing_lookback).max().iloc[-1]
        recent_low = df['low'].rolling(swing_lookback).min().iloc[-1]
        midpoint = (recent_high + recent_low) / 2
        
        return {
            'high': recent_high,
            'low': recent_low,
            'midpoint': midpoint,
            'range_size': recent_high - recent_low,
            'premium_zone': (midpoint, recent_high),
            'discount_zone': (recent_low, midpoint),
            'ote_zone': (
                recent_high - 0.79 * (recent_high - recent_low), 
                recent_high - 0.618 * (recent_high - recent_low)
            ),
            'equilibrium': midpoint
        }
    
    def get_pd_zone(self, dealing_range: Dict[str, Any], price: float) -> str:
        """
        Get premium/discount zone classification using existing logic
        """
        midpoint = dealing_range['midpoint']
        range_size = dealing_range['range_size']
        
        # Calculate distance from equilibrium as percentage
        distance_from_eq = abs(price - midpoint) / range_size
        
        if price < midpoint:
            if distance_from_eq > self.zone_threshold:
                return 'discount'
            else:
                return 'equilibrium_discount'
        elif price > midpoint:
            if distance_from_eq > self.zone_threshold:
                return 'premium'
            else:
                return 'equilibrium_premium'
        else:
            return 'equilibrium'
    
    def analyze_pd_zones(self, dealing_range: Dict[str, Any], df: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """
        Analyze premium/discount zone characteristics
        """
        range_size = dealing_range['range_size']
        midpoint = dealing_range['midpoint']
        
        # Calculate price position within range
        price_position = (current_price - dealing_range['low']) / range_size
        
        # Distance from key levels
        distance_from_eq = abs(current_price - midpoint)
        distance_from_high = abs(current_price - dealing_range['high'])
        distance_from_low = abs(current_price - dealing_range['low'])
        
        # Zone strength based on recent rejections
        zone_strength = self.calculate_zone_strength(df, dealing_range)
        
        return {
            'price_position_in_range': price_position,
            'distance_from_equilibrium': distance_from_eq,
            'distance_from_high': distance_from_high,
            'distance_from_low': distance_from_low,
            'range_size': range_size,
            'zone_strength': zone_strength,
            'in_premium': price_position > 0.6,
            'in_discount': price_position < 0.4,
            'near_equilibrium': 0.4 <= price_position <= 0.6
        }
    
    def calculate_zone_strength(self, df: pd.DataFrame, dealing_range: Dict[str, Any]) -> float:
        """
        Calculate zone strength based on historical reactions
        """
        if len(df) < 20:
            return 0.5
        
        high_level = dealing_range['high']
        low_level = dealing_range['low']
        midpoint = dealing_range['midpoint']
        
        # Count reactions at key levels
        high_reactions = 0
        low_reactions = 0
        eq_reactions = 0
        
        for i in range(1, len(df)):
            prev_close = df['close'].iloc[i-1]
            curr_close = df['close'].iloc[i]
            
            # Check for reactions at high level
            if (abs(prev_close - high_level) / high_level < 0.01 and 
                curr_close < prev_close):
                high_reactions += 1
            
            # Check for reactions at low level
            if (abs(prev_close - low_level) / low_level < 0.01 and 
                curr_close > prev_close):
                low_reactions += 1
            
            # Check for reactions at equilibrium
            if (abs(prev_close - midpoint) / midpoint < 0.01):
                eq_reactions += 1
        
        # Calculate overall zone strength
        total_reactions = high_reactions + low_reactions + eq_reactions
        if total_reactions > 0:
            return min(total_reactions / len(df) * 10, 1.0)  # Scale to 0-1
        
        return 0.5
    
    def get_pd_trading_recommendations(self, dealing_range: Dict[str, Any], 
                                     pd_zone: str, current_price: float, 
                                     df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Get trading recommendations based on premium/discount analysis
        """
        recommendations = []
        
        # Premium zone recommendations
        if pd_zone in ['premium', 'equilibrium_premium']:
            recommendations.append({
                'zone': pd_zone,
                'bias': 'short',
                'reason': 'Price in premium zone - look for shorts',
                'target': dealing_range['low'],
                'stop_level': dealing_range['high'],
                'confidence': 0.7 if pd_zone == 'premium' else 0.5
            })
        
        # Discount zone recommendations
        elif pd_zone in ['discount', 'equilibrium_discount']:
            recommendations.append({
                'zone': pd_zone,
                'bias': 'long',
                'reason': 'Price in discount zone - look for longs',
                'target': dealing_range['high'],
                'stop_level': dealing_range['low'],
                'confidence': 0.7 if pd_zone == 'discount' else 0.5
            })
        
        # Equilibrium recommendations
        elif pd_zone == 'equilibrium':
            recommendations.append({
                'zone': pd_zone,
                'bias': 'neutral',
                'reason': 'Price at equilibrium - wait for direction',
                'target': 'TBD based on break direction',
                'stop_level': 'Opposite side of range',
                'confidence': 0.3
            })
        
        # Add OTE zone recommendations
        ote_zone = dealing_range['ote_zone']
        if ote_zone[0] <= current_price <= ote_zone[1]:
            recommendations.append({
                'zone': 'ote',
                'bias': 'long',
                'reason': 'Price in OTE zone - optimal long entry',
                'target': dealing_range['high'],
                'stop_level': dealing_range['low'],
                'confidence': 0.8
            })
        
        return recommendations
    
    def calculate_pd_signal_strength(self, dealing_range: Dict[str, Any], 
                                   df: pd.DataFrame, pd_zone: str) -> float:
        """
        Calculate premium/discount signal strength
        """
        strength_factors = []
        
        # Zone extremity strength
        range_size = dealing_range['range_size']
        current_price = df['close'].iloc[-1]
        midpoint = dealing_range['midpoint']
        
        distance_from_eq = abs(current_price - midpoint)
        extremity_score = (distance_from_eq / (range_size / 2))  # 0 at eq, 1 at extremes
        strength_factors.append(extremity_score)
        
        # Zone clarity strength
        zone_clarity = {
            'premium': 0.8,
            'discount': 0.8,
            'equilibrium_premium': 0.5,
            'equilibrium_discount': 0.5,
            'equilibrium': 0.3
        }
        strength_factors.append(zone_clarity.get(pd_zone, 0.3))
        
        # Historical zone strength
        zone_strength = self.calculate_zone_strength(df, dealing_range)
        strength_factors.append(zone_strength)
        
        # Volume confirmation
        if 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
            strength_factors.append(volume_factor * 0.5)
        
        return np.mean(strength_factors)
    
    def update_zone_tracking(self, dealing_range: Dict[str, Any], pd_zone: str, current_price: float):
        """
        Update zone tracking and history
        """
        # Update current dealing range
        self.current_dealing_range = dealing_range
        
        # Add to zone history
        zone_entry = {
            'timestamp': datetime.now(timezone.utc),
            'pd_zone': pd_zone,
            'price': current_price,
            'dealing_range': dealing_range.copy()
        }
        
        self.zone_history.append(zone_entry)
        
        # Limit history size
        if len(self.zone_history) > 100:
            self.zone_history = self.zone_history[-100:]
        
        # Check for equilibrium tests
        if pd_zone == 'equilibrium':
            self.equilibrium_tests.append({
                'timestamp': datetime.now(timezone.utc),
                'price': current_price,
                'equilibrium': dealing_range['midpoint']
            })
    
    def analyze_zone_transitions(self) -> Dict[str, Any]:
        """
        Analyze zone transition patterns
        """
        if len(self.zone_history) < 10:
            return {'transitions': [], 'patterns': []}
        
        transitions = []
        recent_history = self.zone_history[-10:]
        
        for i in range(1, len(recent_history)):
            prev_zone = recent_history[i-1]['pd_zone']
            curr_zone = recent_history[i]['pd_zone']
            
            if prev_zone != curr_zone:
                transitions.append({
                    'from_zone': prev_zone,
                    'to_zone': curr_zone,
                    'timestamp': recent_history[i]['timestamp']
                })
        
        # Analyze transition patterns
        patterns = self.identify_transition_patterns(transitions)
        
        return {
            'transitions': transitions,
            'patterns': patterns,
            'transition_frequency': len(transitions) / len(recent_history)
        }
    
    def identify_transition_patterns(self, transitions: List[Dict[str, Any]]) -> List[str]:
        """
        Identify common zone transition patterns
        """
        patterns = []
        
        if len(transitions) < 3:
            return patterns
        
        # Look for common patterns
        transition_sequence = [t['to_zone'] for t in transitions[-3:]]
        
        # Premium to discount sweep
        if 'premium' in transition_sequence and 'discount' in transition_sequence:
            patterns.append('premium_to_discount_sweep')
        
        # Equilibrium rejection patterns
        eq_count = sum(1 for zone in transition_sequence if 'equilibrium' in zone)
        if eq_count >= 2:
            patterns.append('equilibrium_rejection_pattern')
        
        # Range bound pattern
        if len(set(transition_sequence)) >= 3:
            patterns.append('range_bound_trading')
        
        return patterns
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_pd_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive premium/discount summary
        """
        current_zone = self.zone_history[-1]['pd_zone'] if self.zone_history else 'unknown'
        
        return {
            'agent_id': self.agent_id,
            'current_pd_zone': current_zone,
            'current_dealing_range': self.current_dealing_range,
            'zone_history_count': len(self.zone_history),
            'equilibrium_tests_count': len(self.equilibrium_tests),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'swing_lookback': self.swing_lookback,
                'zone_threshold': self.zone_threshold
            }
        }
    
    def is_in_premium(self, price: float = None) -> bool:
        """Check if price is in premium zone"""
        if not self.current_dealing_range:
            return False
        
        if price is None and self.zone_history:
            return 'premium' in self.zone_history[-1]['pd_zone']
        
        if price is not None:
            pd_zone = self.get_pd_zone(self.current_dealing_range, price)
            return 'premium' in pd_zone
        
        return False
    
    def is_in_discount(self, price: float = None) -> bool:
        """Check if price is in discount zone"""
        if not self.current_dealing_range:
            return False
        
        if price is None and self.zone_history:
            return 'discount' in self.zone_history[-1]['pd_zone']
        
        if price is not None:
            pd_zone = self.get_pd_zone(self.current_dealing_range, price)
            return 'discount' in pd_zone
        
        return False
    
    def is_at_equilibrium(self, price: float = None, tolerance: float = 0.02) -> bool:
        """Check if price is at equilibrium"""
        if not self.current_dealing_range:
            return False
        
        if price is None and self.zone_history:
            return 'equilibrium' == self.zone_history[-1]['pd_zone']
        
        if price is not None:
            midpoint = self.current_dealing_range['midpoint']
            return abs(price - midpoint) / midpoint <= tolerance
        
        return False
    
    def get_distance_to_equilibrium(self, price: float) -> float:
        """Get distance to equilibrium as percentage of range"""
        if not self.current_dealing_range:
            return 0.0
        
        midpoint = self.current_dealing_range['midpoint']
        range_size = self.current_dealing_range['range_size']
        
        return abs(price - midpoint) / range_size
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "price_update":
            # Update premium/discount classification
            symbol = message['data']['symbol']
            price_data = message['data']
            
            if 'close' in price_data and self.current_dealing_range:
                new_pd_zone = self.get_pd_zone(self.current_dealing_range, price_data['close'])
                
                # Check for zone changes
                if (self.zone_history and 
                    new_pd_zone != self.zone_history[-1]['pd_zone']):
                    
                    self.logger.info(f"Zone transition: {self.zone_history[-1]['pd_zone']} → {new_pd_zone}")
                    
                    # Publish zone change
                    self.publish("pd_zone_change", {
                        'symbol': symbol,
                        'from_zone': self.zone_history[-1]['pd_zone'],
                        'to_zone': new_pd_zone,
                        'price': price_data['close']
                    })
        
        super().on_message(topic, message)
    
    def requires_continuous_processing(self) -> bool:
        """Premium/Discount agent doesn't need continuous background processing"""
        return False