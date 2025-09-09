"""
Displacement Agent
Detects displacement candles and strong directional moves in ICT/SMC methodology
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from ..base_agent import BasePatternAgent


class DisplacementAgent(BasePatternAgent):
    """
    Agent for detecting Displacement patterns.
    
    Displacement is a strong directional move that indicates institutional activity,
    often creating imbalances and inefficiencies in the market.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.min_body_ratio = self.get_config_value('min_body_ratio', 0.7)  # 70% body
        self.volume_multiplier = self.get_config_value('volume_multiplier', 1.5)
        self.atr_multiplier = self.get_config_value('atr_multiplier', 2.0)
        self.consecutive_threshold = self.get_config_value('consecutive_threshold', 2)
        self.lookback_period = self.get_config_value('lookback_period', 20)
        
        # Displacement tracking
        self.recent_displacements = []
        self.displacement_zones = []
        
    def process_data(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Process market data to detect displacement patterns.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing displacement analysis
        """
        if not self.validate_data(df):
            return {'error': 'Invalid data provided'}
        
        try:
            # Calculate ATR for displacement detection
            atr_values = self._calculate_atr(df)
            
            # Detect individual displacement candles
            single_displacements = self._detect_single_displacements(df, atr_values)
            
            # Detect consecutive displacement sequences
            consecutive_displacements = self._detect_consecutive_displacements(df, atr_values)
            
            # Identify displacement zones and imbalances
            displacement_zones = self._identify_displacement_zones(df, single_displacements, consecutive_displacements)
            
            # Analyze current market context
            market_context = self._analyze_market_context(df, displacement_zones)
            
            # Calculate pattern strength
            pattern_strength = self._calculate_displacement_strength(single_displacements, consecutive_displacements, market_context)
            
            return {
                'single_displacements': single_displacements,
                'consecutive_displacements': consecutive_displacements,
                'displacement_zones': displacement_zones,
                'market_context': market_context,
                'pattern_strength': pattern_strength,
                'current_displacement': self._get_current_displacement_status(df, atr_values)
            }
            
        except Exception as e:
            self.logger.error(f"Error in displacement analysis: {e}")
            return {'error': str(e)}
    
    def get_signal_strength(self, df: pd.DataFrame, symbol: str = None) -> float:
        """
        Calculate signal strength based on displacement patterns.
        
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
            current_displacement = analysis.get('current_displacement', {})
            market_context = analysis.get('market_context', {})
            
            # Base strength from pattern analysis
            base_strength = min(pattern_strength, 0.8)
            
            # Current displacement bonus
            current_bonus = 0.0
            if current_displacement.get('is_displacement'):
                current_bonus += 0.1
            if current_displacement.get('strength', 0.0) > 0.7:
                current_bonus += 0.1
            
            # Market context bonus
            context_bonus = 0.0
            if market_context.get('trend_aligned'):
                context_bonus += 0.05
            if market_context.get('volume_surge'):
                context_bonus += 0.05
            
            final_strength = min(base_strength + current_bonus + context_bonus, 1.0)
            return final_strength
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close_prev = (df['high'] - df['close'].shift(1)).abs()
        low_close_prev = (df['low'] - df['close'].shift(1)).abs()
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr.fillna(0)
    
    def _detect_single_displacements(self, df: pd.DataFrame, atr_values: pd.Series) -> List[Dict[str, Any]]:
        """Detect individual displacement candles."""
        displacements = []
        
        for i in range(1, len(df)):
            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            atr = atr_values.iloc[i]
            
            if atr == 0:
                continue
            
            # Calculate candle metrics
            body_size = abs(bar['close'] - bar['open'])
            candle_range = bar['high'] - bar['low']
            body_ratio = body_size / candle_range if candle_range > 0 else 0
            
            # Check displacement criteria
            is_displacement = False
            displacement_type = None
            strength = 0.0
            
            # Size-based displacement (large body compared to ATR)
            if body_size > atr * self.atr_multiplier:
                is_displacement = True
                strength += 0.4
                
                # Determine direction
                if bar['close'] > bar['open']:
                    displacement_type = 'bullish'
                else:
                    displacement_type = 'bearish'
            
            # Body ratio confirmation
            if body_ratio > self.min_body_ratio:
                strength += 0.2
            
            # Volume confirmation
            volume_confirmed = False
            if 'volume' in df.columns and i > 5:
                avg_volume = df['volume'].iloc[i-5:i].mean()
                if bar['volume'] > avg_volume * self.volume_multiplier:
                    volume_confirmed = True
                    strength += 0.2
            
            # Gap detection (price gap from previous close)
            gap_size = 0
            has_gap = False
            if displacement_type == 'bullish' and bar['open'] > prev_bar['close']:
                gap_size = (bar['open'] - prev_bar['close']) / prev_bar['close']
                has_gap = gap_size > 0.001  # 0.1% gap
            elif displacement_type == 'bearish' and bar['open'] < prev_bar['close']:
                gap_size = (prev_bar['close'] - bar['open']) / prev_bar['close']
                has_gap = gap_size > 0.001  # 0.1% gap
            
            if has_gap:
                strength += 0.2
            
            if is_displacement:
                displacement = {
                    'index': i,
                    'type': displacement_type,
                    'strength': min(strength, 1.0),
                    'body_size': body_size,
                    'body_ratio': body_ratio,
                    'atr_multiple': body_size / atr,
                    'volume_confirmed': volume_confirmed,
                    'has_gap': has_gap,
                    'gap_size': gap_size,
                    'high': bar['high'],
                    'low': bar['low'],
                    'open': bar['open'],
                    'close': bar['close']
                }
                
                displacements.append(displacement)
        
        return displacements
    
    def _detect_consecutive_displacements(self, df: pd.DataFrame, atr_values: pd.Series) -> List[Dict[str, Any]]:
        """Detect consecutive displacement sequences."""
        consecutive_sequences = []
        
        if len(df) < self.consecutive_threshold:
            return consecutive_sequences
        
        # Look for consecutive candles in same direction with strong bodies
        i = self.consecutive_threshold - 1
        while i < len(df):
            sequence = []
            current_direction = None
            
            # Check for consecutive candles
            for j in range(i - self.consecutive_threshold + 1, i + 1):
                bar = df.iloc[j]
                atr = atr_values.iloc[j]
                
                if atr == 0:
                    break
                
                body_size = abs(bar['close'] - bar['open'])
                candle_range = bar['high'] - bar['low']
                body_ratio = body_size / candle_range if candle_range > 0 else 0
                
                # Determine candle direction
                if bar['close'] > bar['open']:
                    direction = 'bullish'
                elif bar['close'] < bar['open']:
                    direction = 'bearish'
                else:
                    direction = 'neutral'
                
                # Check if candle meets displacement criteria
                if (body_size > atr * (self.atr_multiplier * 0.7) and  # Slightly lower threshold for consecutive
                    body_ratio > self.min_body_ratio * 0.8 and
                    direction != 'neutral'):
                    
                    if current_direction is None:
                        current_direction = direction
                    
                    if direction == current_direction:
                        sequence.append({
                            'index': j,
                            'body_size': body_size,
                            'body_ratio': body_ratio,
                            'atr_multiple': body_size / atr,
                            'high': bar['high'],
                            'low': bar['low'],
                            'close': bar['close']
                        })
                    else:
                        break
                else:
                    break
            
            # If we have a valid consecutive sequence
            if len(sequence) >= self.consecutive_threshold:
                total_displacement = 0
                if current_direction == 'bullish':
                    start_price = sequence[0]['close'] if sequence[0]['close'] < df.iloc[sequence[0]['index']]['open'] else df.iloc[sequence[0]['index']]['open']
                    end_price = sequence[-1]['close']
                    total_displacement = (end_price - start_price) / start_price
                else:
                    start_price = sequence[0]['close'] if sequence[0]['close'] > df.iloc[sequence[0]['index']]['open'] else df.iloc[sequence[0]['index']]['open']
                    end_price = sequence[-1]['close']
                    total_displacement = (start_price - end_price) / start_price
                
                # Calculate sequence strength
                avg_body_ratio = sum(candle['body_ratio'] for candle in sequence) / len(sequence)
                avg_atr_multiple = sum(candle['atr_multiple'] for candle in sequence) / len(sequence)
                
                strength = min((avg_body_ratio * 0.3 + 
                               avg_atr_multiple / self.atr_multiplier * 0.4 + 
                               len(sequence) / 5 * 0.3), 1.0)
                
                consecutive_displacement = {
                    'start_index': sequence[0]['index'],
                    'end_index': sequence[-1]['index'],
                    'type': current_direction,
                    'length': len(sequence),
                    'strength': strength,
                    'total_displacement': total_displacement,
                    'avg_body_ratio': avg_body_ratio,
                    'avg_atr_multiple': avg_atr_multiple,
                    'sequence': sequence
                }
                
                consecutive_sequences.append(consecutive_displacement)
                
                # Skip ahead to avoid overlapping sequences
                i = sequence[-1]['index'] + 1
            else:
                i += 1
        
        return consecutive_sequences
    
    def _identify_displacement_zones(self, df: pd.DataFrame, single_displacements: List[Dict], 
                                   consecutive_displacements: List[Dict]) -> List[Dict[str, Any]]:
        """Identify displacement zones and potential imbalances."""
        zones = []
        
        # Process single displacements
        for displacement in single_displacements:
            if displacement['has_gap']:
                # Create imbalance zone from gap
                prev_bar = df.iloc[displacement['index'] - 1]
                curr_bar = df.iloc[displacement['index']]
                
                if displacement['type'] == 'bullish':
                    zone_low = prev_bar['close']
                    zone_high = curr_bar['open']
                else:
                    zone_low = curr_bar['open']
                    zone_high = prev_bar['close']
                
                zone = {
                    'type': 'imbalance',
                    'direction': displacement['type'],
                    'low': zone_low,
                    'high': zone_high,
                    'start_index': displacement['index'] - 1,
                    'end_index': displacement['index'],
                    'strength': displacement['strength'],
                    'filled': False
                }
                
                zones.append(zone)
        
        # Process consecutive displacements
        for sequence in consecutive_displacements:
            # Create displacement zone from the entire sequence
            start_bar = df.iloc[sequence['start_index']]
            end_bar = df.iloc[sequence['end_index']]
            
            if sequence['type'] == 'bullish':
                zone_low = min([candle['low'] for candle in sequence['sequence']])
                zone_high = max([candle['high'] for candle in sequence['sequence']])
            else:
                zone_low = min([candle['low'] for candle in sequence['sequence']])
                zone_high = max([candle['high'] for candle in sequence['sequence']])
            
            zone = {
                'type': 'displacement_sequence',
                'direction': sequence['type'],
                'low': zone_low,
                'high': zone_high,
                'start_index': sequence['start_index'],
                'end_index': sequence['end_index'],
                'length': sequence['length'],
                'strength': sequence['strength'],
                'total_displacement': sequence['total_displacement']
            }
            
            zones.append(zone)
        
        return zones
    
    def _analyze_market_context(self, df: pd.DataFrame, displacement_zones: List[Dict]) -> Dict[str, Any]:
        """Analyze current market context for displacement patterns."""
        current_price = df['close'].iloc[-1]
        
        context = {
            'trend_aligned': False,
            'volume_surge': False,
            'near_displacement_zone': False,
            'displacement_count_recent': 0,
            'dominant_direction': 'neutral'
        }
        
        # Check recent displacement activity
        recent_period = min(20, len(df))
        recent_start_index = len(df) - recent_period
        
        bullish_count = 0
        bearish_count = 0
        
        for zone in displacement_zones:
            if zone['start_index'] >= recent_start_index:
                context['displacement_count_recent'] += 1
                if zone['direction'] == 'bullish':
                    bullish_count += 1
                else:
                    bearish_count += 1
        
        # Determine dominant direction
        if bullish_count > bearish_count:
            context['dominant_direction'] = 'bullish'
        elif bearish_count > bullish_count:
            context['dominant_direction'] = 'bearish'
        
        # Check trend alignment (simple trend based on recent price action)
        if len(df) >= 10:
            recent_high = df['high'].iloc[-10:].max()
            recent_low = df['low'].iloc[-10:].min()
            price_position = (current_price - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
            
            if price_position > 0.7 and context['dominant_direction'] == 'bullish':
                context['trend_aligned'] = True
            elif price_position < 0.3 and context['dominant_direction'] == 'bearish':
                context['trend_aligned'] = True
        
        # Check volume surge
        if 'volume' in df.columns and len(df) >= 10:
            recent_volume = df['volume'].iloc[-3:].mean()
            avg_volume = df['volume'].iloc[-13:-3].mean()
            context['volume_surge'] = recent_volume > avg_volume * 1.5
        
        # Check proximity to displacement zones
        for zone in displacement_zones:
            zone_center = (zone['high'] + zone['low']) / 2
            distance = abs(current_price - zone_center) / current_price
            if distance < 0.02:  # Within 2%
                context['near_displacement_zone'] = True
                break
        
        return context
    
    def _calculate_displacement_strength(self, single_displacements: List[Dict], 
                                       consecutive_displacements: List[Dict],
                                       market_context: Dict) -> float:
        """Calculate overall displacement pattern strength."""
        if not single_displacements and not consecutive_displacements:
            return 0.0
        
        strength_factors = []
        
        # Single displacement strength
        if single_displacements:
            recent_singles = [d for d in single_displacements if d['index'] >= len(single_displacements) - 5]
            if recent_singles:
                avg_single_strength = sum(d['strength'] for d in recent_singles) / len(recent_singles)
                strength_factors.append(avg_single_strength * 0.6)
        
        # Consecutive displacement strength
        if consecutive_displacements:
            recent_consecutives = [d for d in consecutive_displacements if d['end_index'] >= len(consecutive_displacements) - 5]
            if recent_consecutives:
                avg_consecutive_strength = sum(d['strength'] for d in recent_consecutives) / len(recent_consecutives)
                strength_factors.append(avg_consecutive_strength * 0.8)
        
        if not strength_factors:
            return 0.0
        
        base_strength = max(strength_factors)  # Take the stronger signal
        
        # Market context multiplier
        context_multiplier = 1.0
        if market_context.get('trend_aligned'):
            context_multiplier += 0.1
        if market_context.get('volume_surge'):
            context_multiplier += 0.1
        if market_context.get('displacement_count_recent', 0) > 2:
            context_multiplier += 0.1
        
        return min(base_strength * context_multiplier, 1.0)
    
    def _get_current_displacement_status(self, df: pd.DataFrame, atr_values: pd.Series) -> Dict[str, Any]:
        """Get current displacement status for the latest candle."""
        if len(df) < 2:
            return {'is_displacement': False, 'strength': 0.0}
        
        current_bar = df.iloc[-1]
        atr = atr_values.iloc[-1]
        
        if atr == 0:
            return {'is_displacement': False, 'strength': 0.0}
        
        # Check current candle for displacement
        body_size = abs(current_bar['close'] - current_bar['open'])
        candle_range = current_bar['high'] - current_bar['low']
        body_ratio = body_size / candle_range if candle_range > 0 else 0
        
        is_displacement = body_size > atr * self.atr_multiplier and body_ratio > self.min_body_ratio
        
        strength = 0.0
        if is_displacement:
            strength = min((body_size / atr) / self.atr_multiplier * 0.5 + body_ratio * 0.3, 1.0)
        
        direction = None
        if current_bar['close'] > current_bar['open']:
            direction = 'bullish'
        elif current_bar['close'] < current_bar['open']:
            direction = 'bearish'
        
        return {
            'is_displacement': is_displacement,
            'direction': direction,
            'strength': strength,
            'body_size': body_size,
            'body_ratio': body_ratio,
            'atr_multiple': body_size / atr if atr > 0 else 0
        }