"""
Breaker Blocks Agent
Detects and analyzes breaker block patterns in ICT/SMC methodology
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from ..base_agent import BasePatternAgent


class BreakerBlocksAgent(BasePatternAgent):
    """
    Agent for detecting Breaker Block patterns.
    
    Breaker Blocks are order blocks that have been broken and then retested,
    often indicating strong institutional interest and potential reversal zones.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.lookback_period = self.get_config_value('lookback_period', 30)
        self.min_block_size = self.get_config_value('min_block_size', 0.001)  # 0.1% minimum
        self.retest_threshold = self.get_config_value('retest_threshold', 0.0005)  # 0.05%
        self.volume_multiplier = self.get_config_value('volume_multiplier', 1.5)
        self.confirmation_bars = self.get_config_value('confirmation_bars', 3)
        
        # Pattern tracking
        self.active_breakers = []
        self.validated_breakers = []
        
    def process_data(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Process market data to detect breaker block patterns.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing breaker block analysis
        """
        if not self.validate_data(df):
            return {'error': 'Invalid data provided'}
        
        try:
            # Detect potential order blocks first
            order_blocks = self._detect_order_blocks(df)
            
            # Identify broken order blocks
            broken_blocks = self._identify_broken_blocks(df, order_blocks)
            
            # Detect breaker block formations
            breaker_blocks = self._detect_breaker_blocks(df, broken_blocks)
            
            # Analyze current price action relative to breaker blocks
            price_analysis = self._analyze_price_action(df, breaker_blocks)
            
            # Calculate pattern strength
            pattern_strength = self._calculate_breaker_strength(breaker_blocks, price_analysis)
            
            return {
                'order_blocks': order_blocks,
                'broken_blocks': broken_blocks,
                'breaker_blocks': breaker_blocks,
                'price_analysis': price_analysis,
                'pattern_strength': pattern_strength,
                'active_breakers': len(self.active_breakers),
                'validated_breakers': len(self.validated_breakers)
            }
            
        except Exception as e:
            self.logger.error(f"Error in breaker blocks analysis: {e}")
            return {'error': str(e)}
    
    def get_signal_strength(self, df: pd.DataFrame, symbol: str = None) -> float:
        """
        Calculate signal strength based on breaker block patterns.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Signal strength (0.0 to 1.0)
        """
        if not self.validate_data(df):
            return 0.0
        
        try:
            analysis = self.process_data(df, symbol)
            if 'error' in analysis:
                return 0.0
            
            pattern_strength = analysis.get('pattern_strength', 0.0)
            breaker_blocks = analysis.get('breaker_blocks', [])
            price_analysis = analysis.get('price_analysis', {})
            
            if not breaker_blocks:
                return 0.0
            
            # Base strength from pattern detection
            base_strength = min(pattern_strength, 0.8)
            
            # Boost for price action confirmation
            price_boost = 0.0
            if price_analysis.get('near_breaker_zone'):
                price_boost += 0.1
            if price_analysis.get('rejection_confirmed'):
                price_boost += 0.1
            if price_analysis.get('volume_confirmation'):
                price_boost += 0.1
            
            final_strength = min(base_strength + price_boost, 1.0)
            return final_strength
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def _detect_order_blocks(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect potential order blocks (supply/demand zones)."""
        order_blocks = []
        
        if len(df) < 10:
            return order_blocks
        
        # Look for strong moves (displacement candles)
        for i in range(5, len(df) - 5):
            current_bar = df.iloc[i]
            
            # Calculate candle body size
            body_size = abs(current_bar['close'] - current_bar['open'])
            avg_body = df['close'].iloc[i-5:i].sub(df['open'].iloc[i-5:i]).abs().mean()
            
            # Check for displacement candle
            is_displacement = body_size > avg_body * 2
            
            if is_displacement:
                # Check volume confirmation
                volume_confirmed = True
                if 'volume' in df.columns:
                    avg_volume = df['volume'].iloc[i-5:i].mean()
                    volume_confirmed = current_bar['volume'] > avg_volume * self.volume_multiplier
                
                if volume_confirmed:
                    # Identify the order block (previous candle before displacement)
                    ob_candle = df.iloc[i-1]
                    
                    block_type = 'bullish' if current_bar['close'] > current_bar['open'] else 'bearish'
                    
                    order_block = {
                        'index': i-1,
                        'type': block_type,
                        'high': ob_candle['high'],
                        'low': ob_candle['low'],
                        'open': ob_candle['open'],
                        'close': ob_candle['close'],
                        'displacement_index': i,
                        'strength': min(body_size / avg_body, 3.0) / 3.0,
                        'volume_confirmed': volume_confirmed
                    }
                    
                    order_blocks.append(order_block)
        
        return order_blocks
    
    def _identify_broken_blocks(self, df: pd.DataFrame, 
                               order_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify order blocks that have been broken."""
        broken_blocks = []
        
        for ob in order_blocks:
            break_index = None
            
            # Look for breaks after the order block formation
            search_start = ob['displacement_index'] + 1
            
            for i in range(search_start, len(df)):
                bar = df.iloc[i]
                
                if ob['type'] == 'bullish':
                    # Check if price broke below the bullish order block
                    if bar['low'] < ob['low']:
                        break_index = i
                        break
                else:  # bearish
                    # Check if price broke above the bearish order block
                    if bar['high'] > ob['high']:
                        break_index = i
                        break
            
            if break_index is not None:
                # Confirm the break with body close
                break_bar = df.iloc[break_index]
                body_break = False
                
                if ob['type'] == 'bullish':
                    body_break = break_bar['close'] < ob['low']
                else:
                    body_break = break_bar['close'] > ob['high']
                
                broken_block = ob.copy()
                broken_block.update({
                    'break_index': break_index,
                    'break_price': break_bar['close'],
                    'body_break': body_break,
                    'break_strength': 0.8 if body_break else 0.5
                })
                
                broken_blocks.append(broken_block)
        
        return broken_blocks
    
    def _detect_breaker_blocks(self, df: pd.DataFrame, 
                              broken_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect breaker block formations from broken order blocks."""
        breaker_blocks = []
        
        for broken_block in broken_blocks:
            # Look for retest of the broken order block
            retest_found = False
            retest_index = None
            reaction_strength = 0.0
            
            search_start = broken_block['break_index'] + 1
            
            for i in range(search_start, len(df)):
                bar = df.iloc[i]
                
                # Define the breaker zone
                if broken_block['type'] == 'bullish':
                    # For bullish breaker, look for retest from below
                    zone_low = broken_block['low']
                    zone_high = broken_block['high']
                    
                    # Check if price retests the zone
                    if (bar['high'] >= zone_low - self.retest_threshold and 
                        bar['low'] <= zone_high + self.retest_threshold):
                        
                        # Check for rejection (price should reverse down)
                        reaction_strength = self._measure_reaction_strength(df, i, 'down')
                        if reaction_strength > 0.3:
                            retest_found = True
                            retest_index = i
                            break
                
                else:  # bearish
                    # For bearish breaker, look for retest from above
                    zone_low = broken_block['low']
                    zone_high = broken_block['high']
                    
                    # Check if price retests the zone
                    if (bar['low'] <= zone_high + self.retest_threshold and 
                        bar['high'] >= zone_low - self.retest_threshold):
                        
                        # Check for rejection (price should reverse up)
                        reaction_strength = self._measure_reaction_strength(df, i, 'up')
                        if reaction_strength > 0.3:
                            retest_found = True
                            retest_index = i
                            break
            
            if retest_found:
                # Create breaker block
                breaker_block = broken_block.copy()
                breaker_block.update({
                    'is_breaker': True,
                    'retest_index': retest_index,
                    'reaction_strength': reaction_strength,
                    'breaker_strength': min(broken_block['break_strength'] * reaction_strength, 1.0),
                    'formation_complete': True
                })
                
                breaker_blocks.append(breaker_block)
                
                # Add to active breakers
                if breaker_block not in self.active_breakers:
                    self.active_breakers.append(breaker_block)
        
        return breaker_blocks
    
    def _analyze_price_action(self, df: pd.DataFrame, 
                             breaker_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze current price action relative to breaker blocks."""
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        analysis = {
            'near_breaker_zone': False,
            'rejection_confirmed': False,
            'volume_confirmation': False,
            'closest_breaker': None,
            'distance_to_breaker': float('inf')
        }
        
        if not breaker_blocks:
            return analysis
        
        # Find closest breaker block
        closest_breaker = None
        min_distance = float('inf')
        
        for breaker in breaker_blocks:
            zone_center = (breaker['high'] + breaker['low']) / 2
            distance = abs(current_price - zone_center) / current_price
            
            if distance < min_distance:
                min_distance = distance
                closest_breaker = breaker
        
        if closest_breaker:
            analysis['closest_breaker'] = closest_breaker
            analysis['distance_to_breaker'] = min_distance
            
            # Check if near breaker zone
            if min_distance < 0.01:  # Within 1%
                analysis['near_breaker_zone'] = True
                
                # Check for rejection signs
                rejection_bars = self._count_rejection_bars(df, closest_breaker)
                analysis['rejection_confirmed'] = rejection_bars >= self.confirmation_bars
                
                # Check volume confirmation
                if 'volume' in df.columns:
                    recent_volume = df['volume'].iloc[-3:].mean()
                    avg_volume = df['volume'].iloc[-20:-3].mean()
                    analysis['volume_confirmation'] = recent_volume > avg_volume * 1.2
        
        return analysis
    
    def _measure_reaction_strength(self, df: pd.DataFrame, start_index: int, 
                                  direction: str, lookforward: int = 5) -> float:
        """Measure the strength of price reaction from a level."""
        if start_index + lookforward >= len(df):
            lookforward = len(df) - start_index - 1
        
        if lookforward <= 0:
            return 0.0
        
        start_price = df['close'].iloc[start_index]
        reaction_bars = df.iloc[start_index:start_index + lookforward]
        
        if direction == 'up':
            # Measure upward reaction
            max_high = reaction_bars['high'].max()
            reaction_size = (max_high - start_price) / start_price
        else:  # down
            # Measure downward reaction
            min_low = reaction_bars['low'].min()
            reaction_size = (start_price - min_low) / start_price
        
        # Normalize to 0-1 scale (10% reaction = 1.0)
        return min(reaction_size * 10, 1.0)
    
    def _calculate_breaker_strength(self, breaker_blocks: List[Dict[str, Any]], 
                                   price_analysis: Dict[str, Any]) -> float:
        """Calculate overall breaker pattern strength."""
        if not breaker_blocks:
            return 0.0
        
        strength_factors = []
        
        for breaker in breaker_blocks:
            # Base strength from breaker formation
            base_strength = breaker.get('breaker_strength', 0.0)
            
            # Volume confirmation bonus
            volume_bonus = 0.1 if breaker.get('volume_confirmed', False) else 0.0
            
            # Body break confirmation bonus
            body_bonus = 0.1 if breaker.get('body_break', False) else 0.0
            
            # Reaction strength bonus
            reaction_bonus = breaker.get('reaction_strength', 0.0) * 0.2
            
            total_strength = min(base_strength + volume_bonus + body_bonus + reaction_bonus, 1.0)
            strength_factors.append(total_strength)
        
        # Average strength of all breakers
        base_pattern_strength = sum(strength_factors) / len(strength_factors)
        
        # Current price action multiplier
        price_multiplier = 1.0
        if price_analysis.get('near_breaker_zone'):
            price_multiplier += 0.1
        if price_analysis.get('rejection_confirmed'):
            price_multiplier += 0.2
        if price_analysis.get('volume_confirmation'):
            price_multiplier += 0.1
        
        return min(base_pattern_strength * price_multiplier, 1.0)
    
    def _count_rejection_bars(self, df: pd.DataFrame, breaker_block: Dict[str, Any], 
                             lookback: int = 5) -> int:
        """Count rejection bars near breaker block."""
        if len(df) < lookback:
            return 0
        
        rejection_count = 0
        recent_bars = df.tail(lookback)
        
        zone_high = breaker_block['high']
        zone_low = breaker_block['low']
        breaker_type = breaker_block['type']
        
        for _, bar in recent_bars.iterrows():
            is_rejection = False
            
            if breaker_type == 'bullish':
                # Look for bearish rejection at bullish breaker
                if (bar['high'] >= zone_low and bar['low'] <= zone_high and 
                    bar['close'] < bar['open']):  # Red candle
                    is_rejection = True
            else:  # bearish
                # Look for bullish rejection at bearish breaker
                if (bar['low'] <= zone_high and bar['high'] >= zone_low and 
                    bar['close'] > bar['open']):  # Green candle
                    is_rejection = True
            
            if is_rejection:
                rejection_count += 1
        
        return rejection_count
    
    def get_active_breakers(self) -> List[Dict[str, Any]]:
        """Get currently active breaker blocks."""
        return self.active_breakers.copy()
    
    def clear_old_breakers(self, max_age_bars: int = 100):
        """Clear old breaker blocks to prevent memory buildup."""
        current_index = len(self.active_breakers) - 1
        
        self.active_breakers = [
            breaker for breaker in self.active_breakers
            if current_index - breaker.get('retest_index', 0) < max_age_bars
        ]