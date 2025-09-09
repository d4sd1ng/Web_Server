"""
Fair Value Gaps Agent
Detects and analyzes Fair Value Gap patterns in ICT/SMC methodology
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from ..base_agent import BasePatternAgent


class FairValueGapsAgent(BasePatternAgent):
    """
    Agent for detecting Fair Value Gap (FVG) patterns.
    
    Fair Value Gaps are price inefficiencies that occur when there is a gap between
    candles that typically get filled by future price action.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.min_gap_size = self.get_config_value('min_gap_size', 0.0001)  # 0.01%
        self.gap_timeout_bars = self.get_config_value('gap_timeout_bars', 50)
        self.volume_threshold = self.get_config_value('volume_threshold', 1.2)
        self.extend_gap_wicks = self.get_config_value('extend_gap_wicks', True)
        
        # Gap tracking
        self.active_gaps = []
        self.filled_gaps = []
        
    def process_data(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Process market data to detect Fair Value Gap patterns.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing FVG analysis
        """
        if not self.validate_data(df):
            return {'error': 'Invalid data provided'}
        
        try:
            # Detect new Fair Value Gaps
            new_gaps = self._detect_fair_value_gaps(df)
            
            # Update existing gaps status
            self._update_gap_status(df)
            
            # Analyze gap characteristics
            gap_analysis = self._analyze_gap_characteristics(new_gaps)
            
            # Check current price relative to gaps
            price_analysis = self._analyze_price_vs_gaps(df)
            
            # Calculate pattern strength
            pattern_strength = self._calculate_fvg_strength(new_gaps, gap_analysis, price_analysis)
            
            return {
                'new_gaps': new_gaps,
                'active_gaps': len(self.active_gaps),
                'filled_gaps': len(self.filled_gaps),
                'gap_analysis': gap_analysis,
                'price_analysis': price_analysis,
                'pattern_strength': pattern_strength,
                'gap_zones': self._get_current_gap_zones()
            }
            
        except Exception as e:
            self.logger.error(f"Error in FVG analysis: {e}")
            return {'error': str(e)}
    
    def get_signal_strength(self, df: pd.DataFrame, symbol: str = None) -> float:
        """
        Calculate signal strength based on Fair Value Gap patterns.
        
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
            price_analysis = analysis.get('price_analysis', {})
            new_gaps = analysis.get('new_gaps', [])
            
            # Base strength from pattern analysis
            base_strength = min(pattern_strength, 0.7)
            
            # Recent gap formation bonus
            recent_bonus = 0.0
            if new_gaps:
                recent_gaps_strength = sum(gap.get('strength', 0.0) for gap in new_gaps) / len(new_gaps)
                recent_bonus = min(recent_gaps_strength * 0.2, 0.2)
            
            # Price action near gaps bonus
            proximity_bonus = 0.0
            if price_analysis.get('near_gap'):
                proximity_bonus += 0.05
            if price_analysis.get('filling_gap'):
                proximity_bonus += 0.05
            if price_analysis.get('respecting_gap'):
                proximity_bonus += 0.05
            
            final_strength = min(base_strength + recent_bonus + proximity_bonus, 1.0)
            return final_strength
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def _detect_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect Fair Value Gaps in the price data."""
        gaps = []
        
        if len(df) < 3:
            return gaps
        
        # Look for 3-candle FVG patterns
        for i in range(2, len(df)):
            candle1 = df.iloc[i-2]  # First candle
            candle2 = df.iloc[i-1]  # Middle candle (displacement)
            candle3 = df.iloc[i]    # Third candle
            
            gap_info = self._check_fvg_pattern(candle1, candle2, candle3, i)
            
            if gap_info:
                # Add additional analysis
                gap_info.update({
                    'formation_index': i,
                    'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i,
                    'age_bars': 0,
                    'filled': False,
                    'partially_filled': False,
                    'respect_count': 0
                })
                
                # Check volume confirmation
                if 'volume' in df.columns:
                    displacement_volume = candle2['volume']
                    if i >= 5:
                        avg_volume = df['volume'].iloc[i-5:i-1].mean()
                        volume_confirmed = displacement_volume > avg_volume * self.volume_threshold
                        gap_info['volume_confirmed'] = volume_confirmed
                        if volume_confirmed:
                            gap_info['strength'] += 0.1
                
                gaps.append(gap_info)
                
                # Add to active gaps
                self.active_gaps.append(gap_info)
        
        return gaps
    
    def _check_fvg_pattern(self, candle1: pd.Series, candle2: pd.Series, 
                          candle3: pd.Series, index: int) -> Optional[Dict[str, Any]]:
        """Check if three candles form a Fair Value Gap pattern."""
        
        # Bullish FVG: candle1_low > candle3_high (gap between them)
        # Middle candle should be strongly bullish (displacement)
        if (candle2['close'] > candle2['open'] and  # Middle candle is bullish
            candle1['low'] > candle3['high']):      # Gap exists
            
            gap_size = candle1['low'] - candle3['high']
            candle2_body = candle2['close'] - candle2['open']
            candle2_range = candle2['high'] - candle2['low']
            
            # Validate gap size and displacement strength
            if (gap_size > self.min_gap_size and 
                candle2_body > candle2_range * 0.6):  # Strong displacement candle
                
                # Define gap zone (can extend to wicks if enabled)
                if self.extend_gap_wicks:
                    gap_high = max(candle1['low'], candle1['high'] * 0.999)  # Slightly below low for precision
                    gap_low = min(candle3['high'], candle3['low'] * 1.001)   # Slightly above high for precision
                else:
                    gap_high = candle1['low']
                    gap_low = candle3['high']
                
                # Calculate strength
                displacement_strength = candle2_body / candle2_range
                gap_size_relative = gap_size / candle2['close']  # Gap size relative to price
                strength = min(displacement_strength * 0.6 + gap_size_relative * 100 * 0.4, 1.0)
                
                return {
                    'type': 'bullish_fvg',
                    'gap_high': gap_high,
                    'gap_low': gap_low,
                    'gap_size': gap_size,
                    'gap_size_relative': gap_size_relative,
                    'strength': strength,
                    'displacement_candle_index': index - 1,
                    'displacement_strength': displacement_strength,
                    'candle1_index': index - 2,
                    'candle3_index': index
                }
        
        # Bearish FVG: candle1_high < candle3_low (gap between them)  
        # Middle candle should be strongly bearish (displacement)
        elif (candle2['close'] < candle2['open'] and  # Middle candle is bearish
              candle1['high'] < candle3['low']):      # Gap exists
            
            gap_size = candle3['low'] - candle1['high']
            candle2_body = candle2['open'] - candle2['close']  # Bearish body
            candle2_range = candle2['high'] - candle2['low']
            
            # Validate gap size and displacement strength
            if (gap_size > self.min_gap_size and 
                candle2_body > candle2_range * 0.6):  # Strong displacement candle
                
                # Define gap zone
                if self.extend_gap_wicks:
                    gap_high = max(candle3['low'], candle3['high'] * 0.999)  # Slightly below low
                    gap_low = min(candle1['high'], candle1['low'] * 1.001)   # Slightly above high
                else:
                    gap_high = candle3['low']
                    gap_low = candle1['high']
                
                # Calculate strength
                displacement_strength = candle2_body / candle2_range
                gap_size_relative = gap_size / candle2['close']
                strength = min(displacement_strength * 0.6 + gap_size_relative * 100 * 0.4, 1.0)
                
                return {
                    'type': 'bearish_fvg',
                    'gap_high': gap_high,
                    'gap_low': gap_low,
                    'gap_size': gap_size,
                    'gap_size_relative': gap_size_relative,
                    'strength': strength,
                    'displacement_candle_index': index - 1,
                    'displacement_strength': displacement_strength,
                    'candle1_index': index - 2,
                    'candle3_index': index
                }
        
        return None
    
    def _update_gap_status(self, df: pd.DataFrame):
        """Update the status of existing gaps."""
        current_index = len(df) - 1
        current_bar = df.iloc[-1]
        
        gaps_to_remove = []
        
        for i, gap in enumerate(self.active_gaps):
            # Update age
            gap['age_bars'] = current_index - gap['formation_index']
            
            # Check if gap is filled
            if not gap['filled']:
                is_filled, fill_type = self._check_gap_fill(gap, current_bar)
                
                if is_filled:
                    gap['filled'] = True
                    gap['fill_type'] = fill_type
                    gap['fill_index'] = current_index
                    
                    # Move to filled gaps
                    self.filled_gaps.append(gap)
                    gaps_to_remove.append(i)
                
                elif self._check_partial_fill(gap, current_bar):
                    gap['partially_filled'] = True
                
                elif self._check_gap_respect(gap, current_bar):
                    gap['respect_count'] += 1
            
            # Remove old gaps
            if gap['age_bars'] > self.gap_timeout_bars:
                gaps_to_remove.append(i)
        
        # Remove filled or expired gaps
        for i in reversed(gaps_to_remove):
            if i < len(self.active_gaps):
                self.active_gaps.pop(i)
    
    def _check_gap_fill(self, gap: Dict[str, Any], current_bar: pd.Series) -> Tuple[bool, str]:
        """Check if a gap has been filled."""
        gap_high = gap['gap_high']
        gap_low = gap['gap_low']
        
        # Full body fill
        if gap_low <= current_bar['close'] <= gap_high and gap_low <= current_bar['open'] <= gap_high:
            return True, 'body_fill'
        
        # Wick fill (price touched through the gap)
        if gap_low <= current_bar['low'] and current_bar['high'] >= gap_high:
            return True, 'wick_fill'
        
        # Partial significant fill (50% or more of gap filled by body)
        if gap['type'] == 'bullish_fvg':
            if current_bar['close'] <= gap_high and current_bar['close'] >= (gap_high + gap_low) / 2:
                return True, 'partial_significant_fill'
        else:  # bearish_fvg
            if current_bar['close'] >= gap_low and current_bar['close'] <= (gap_high + gap_low) / 2:
                return True, 'partial_significant_fill'
        
        return False, None
    
    def _check_partial_fill(self, gap: Dict[str, Any], current_bar: pd.Series) -> bool:
        """Check if gap has been partially filled."""
        gap_high = gap['gap_high']
        gap_low = gap['gap_low']
        
        # Check if price has entered the gap zone but not filled it completely
        if gap['type'] == 'bullish_fvg':
            return current_bar['low'] < gap_high and current_bar['high'] < gap_low
        else:  # bearish_fvg
            return current_bar['high'] > gap_low and current_bar['low'] > gap_high
    
    def _check_gap_respect(self, gap: Dict[str, Any], current_bar: pd.Series) -> bool:
        """Check if price respected the gap (bounced off it)."""
        gap_high = gap['gap_high']
        gap_low = gap['gap_low']
        
        # For bullish FVG, check if price approached from below and bounced up
        if gap['type'] == 'bullish_fvg':
            return (current_bar['low'] <= gap_low * 1.002 and  # Approached gap
                    current_bar['close'] > current_bar['open'] and  # Bounced up (bullish candle)
                    current_bar['close'] > gap_low)  # Closed above gap
        
        # For bearish FVG, check if price approached from above and bounced down
        else:  # bearish_fvg
            return (current_bar['high'] >= gap_high * 0.998 and  # Approached gap
                    current_bar['close'] < current_bar['open'] and  # Bounced down (bearish candle)
                    current_bar['close'] < gap_high)  # Closed below gap
    
    def _analyze_gap_characteristics(self, new_gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze characteristics of detected gaps."""
        if not new_gaps:
            return {
                'total_new_gaps': 0,
                'bullish_gaps': 0,
                'bearish_gaps': 0,
                'avg_strength': 0.0,
                'avg_gap_size': 0.0
            }
        
        bullish_count = sum(1 for gap in new_gaps if gap['type'] == 'bullish_fvg')
        bearish_count = sum(1 for gap in new_gaps if gap['type'] == 'bearish_fvg')
        avg_strength = sum(gap['strength'] for gap in new_gaps) / len(new_gaps)
        avg_gap_size = sum(gap['gap_size_relative'] for gap in new_gaps) / len(new_gaps)
        
        return {
            'total_new_gaps': len(new_gaps),
            'bullish_gaps': bullish_count,
            'bearish_gaps': bearish_count,
            'avg_strength': avg_strength,
            'avg_gap_size': avg_gap_size,
            'dominant_direction': 'bullish' if bullish_count > bearish_count else 'bearish' if bearish_count > bullish_count else 'neutral'
        }
    
    def _analyze_price_vs_gaps(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze current price action relative to gaps."""
        current_price = df['close'].iloc[-1]
        current_bar = df.iloc[-1]
        
        analysis = {
            'near_gap': False,
            'filling_gap': False,
            'respecting_gap': False,
            'closest_gap_distance': float('inf'),
            'gaps_above': 0,
            'gaps_below': 0
        }
        
        if not self.active_gaps:
            return analysis
        
        gaps_above = 0
        gaps_below = 0
        min_distance = float('inf')
        
        for gap in self.active_gaps:
            gap_center = (gap['gap_high'] + gap['gap_low']) / 2
            distance = abs(current_price - gap_center) / current_price
            
            if distance < min_distance:
                min_distance = distance
            
            if gap_center > current_price:
                gaps_above += 1
            else:
                gaps_below += 1
            
            # Check proximity (within 1%)
            if distance < 0.01:
                analysis['near_gap'] = True
                
                # Check if currently filling
                if (gap['gap_low'] <= current_bar['high'] and 
                    gap['gap_high'] >= current_bar['low']):
                    analysis['filling_gap'] = True
                
                # Check if respecting
                if self._check_gap_respect(gap, current_bar):
                    analysis['respecting_gap'] = True
        
        analysis.update({
            'closest_gap_distance': min_distance,
            'gaps_above': gaps_above,
            'gaps_below': gaps_below
        })
        
        return analysis
    
    def _calculate_fvg_strength(self, new_gaps: List[Dict], gap_analysis: Dict, 
                               price_analysis: Dict) -> float:
        """Calculate overall FVG pattern strength."""
        if not new_gaps and not self.active_gaps:
            return 0.0
        
        strength_factors = []
        
        # New gaps strength
        if new_gaps:
            avg_new_gap_strength = sum(gap['strength'] for gap in new_gaps) / len(new_gaps)
            volume_bonus = sum(0.1 for gap in new_gaps if gap.get('volume_confirmed', False)) / len(new_gaps)
            new_gap_strength = min(avg_new_gap_strength + volume_bonus, 1.0)
            strength_factors.append(new_gap_strength * 0.7)  # High weight for new gaps
        
        # Active gaps quality
        if self.active_gaps:
            respected_gaps = sum(1 for gap in self.active_gaps if gap.get('respect_count', 0) > 0)
            unfilled_ratio = len(self.active_gaps) / max(len(self.active_gaps) + len(self.filled_gaps), 1)
            active_gap_strength = (respected_gaps / len(self.active_gaps)) * unfilled_ratio
            strength_factors.append(active_gap_strength * 0.3)  # Lower weight for existing gaps
        
        if not strength_factors:
            return 0.0
        
        base_strength = sum(strength_factors)
        
        # Price action multiplier
        price_multiplier = 1.0
        if price_analysis.get('near_gap'):
            price_multiplier += 0.1
        if price_analysis.get('respecting_gap'):
            price_multiplier += 0.15
        if price_analysis.get('filling_gap'):
            price_multiplier += 0.05  # Lower bonus as it might indicate gap closure
        
        return min(base_strength * price_multiplier, 1.0)
    
    def _get_current_gap_zones(self) -> List[Dict[str, Any]]:
        """Get current active gap zones for visualization/analysis."""
        return [{
            'type': gap['type'],
            'high': gap['gap_high'],
            'low': gap['gap_low'],
            'strength': gap['strength'],
            'age_bars': gap.get('age_bars', 0),
            'respect_count': gap.get('respect_count', 0),
            'partially_filled': gap.get('partially_filled', False)
        } for gap in self.active_gaps]
    
    def get_gap_statistics(self) -> Dict[str, Any]:
        """Get comprehensive gap statistics."""
        total_gaps = len(self.active_gaps) + len(self.filled_gaps)
        
        if total_gaps == 0:
            return {
                'total_gaps_detected': 0,
                'active_gaps': 0,
                'filled_gaps': 0,
                'fill_rate': 0.0,
                'avg_respect_count': 0.0
            }
        
        fill_rate = len(self.filled_gaps) / total_gaps
        
        # Calculate average respect count for active gaps
        total_respects = sum(gap.get('respect_count', 0) for gap in self.active_gaps)
        avg_respect_count = total_respects / len(self.active_gaps) if self.active_gaps else 0
        
        return {
            'total_gaps_detected': total_gaps,
            'active_gaps': len(self.active_gaps),
            'filled_gaps': len(self.filled_gaps),
            'fill_rate': fill_rate,
            'avg_respect_count': avg_respect_count,
            'bullish_active': sum(1 for gap in self.active_gaps if gap['type'] == 'bullish_fvg'),
            'bearish_active': sum(1 for gap in self.active_gaps if gap['type'] == 'bearish_fvg')
        }
    
    def clear_old_gaps(self, max_age_bars: int = None):
        """Clear old gaps to prevent memory buildup."""
        if max_age_bars is None:
            max_age_bars = self.gap_timeout_bars
        
        self.active_gaps = [gap for gap in self.active_gaps 
                           if gap.get('age_bars', 0) < max_age_bars]
        
        # Keep only recent filled gaps
        self.filled_gaps = self.filled_gaps[-100:]  # Keep last 100 filled gaps