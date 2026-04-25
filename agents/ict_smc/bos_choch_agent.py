"""
Break of Structure (BOS) and Change of Character (CHOCH) Agent
Detects market structure shifts and trend changes in ICT/SMC methodology
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from ..base_agent import BasePatternAgent


class BOSCHOCHAgent(BasePatternAgent):
    """
    Agent for detecting Break of Structure (BOS) and Change of Character (CHOCH) patterns.
    
    BOS: Break above a previous high or below a previous low
    CHOCH: Change from bullish to bearish structure or vice versa
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.swing_lookback = self.get_config_value('swing_lookback', 10)
        self.structure_lookback = self.get_config_value('structure_lookback', 50)
        self.min_swing_size = self.get_config_value('min_swing_size', 0.001)  # 0.1% minimum
        self.choch_confirmation_bars = self.get_config_value('choch_confirmation_bars', 3)
        
        # Structure tracking
        self.recent_highs = []
        self.recent_lows = []
        self.current_trend = 'neutral'  # 'bullish', 'bearish', 'neutral'
        self.last_bos = None
        self.last_choch = None
        
    def process_data(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Process market data to detect BOS and CHOCH patterns.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing BOS/CHOCH analysis
        """
        if not self.validate_data(df):
            return {'error': 'Invalid data provided'}
        
        try:
            # Identify swing points
            swing_highs, swing_lows = self._identify_swing_points(df)
            
            # Detect BOS patterns
            bos_results = self._detect_bos_patterns(df, swing_highs, swing_lows)
            
            # Detect CHOCH patterns
            choch_results = self._detect_choch_patterns(df, swing_highs, swing_lows)
            
            # Determine current market structure
            market_structure = self._analyze_market_structure(df, swing_highs, swing_lows)
            
            # Calculate pattern quality
            pattern_quality = self._calculate_pattern_quality(bos_results, choch_results)
            
            return {
                'swing_highs': swing_highs,
                'swing_lows': swing_lows,
                'bos_patterns': bos_results,
                'choch_patterns': choch_results,
                'market_structure': market_structure,
                'pattern_quality': pattern_quality,
                'current_trend': self.current_trend,
                'last_bos': self.last_bos,
                'last_choch': self.last_choch
            }
            
        except Exception as e:
            self.logger.error(f"Error in BOS/CHOCH analysis: {e}")
            return {'error': str(e)}
    
    def get_signal_strength(self, df: pd.DataFrame, symbol: str = None) -> float:
        """
        Calculate signal strength based on BOS/CHOCH patterns.
        
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
            
            strength_factors = []
            
            # BOS strength
            bos_patterns = analysis.get('bos_patterns', {})
            if bos_patterns.get('bullish_bos') or bos_patterns.get('bearish_bos'):
                bos_strength = min(bos_patterns.get('strength', 0.0), 1.0)
                strength_factors.append(bos_strength * 0.6)  # 60% weight
            
            # CHOCH strength
            choch_patterns = analysis.get('choch_patterns', {})
            if choch_patterns.get('bullish_choch') or choch_patterns.get('bearish_choch'):
                choch_strength = min(choch_patterns.get('strength', 0.0), 1.0)
                strength_factors.append(choch_strength * 0.4)  # 40% weight
            
            # Pattern quality multiplier
            quality = analysis.get('pattern_quality', 0.5)
            quality_multiplier = 0.5 + (quality * 0.5)  # 0.5 to 1.0 range
            
            if not strength_factors:
                return 0.0
            
            base_strength = sum(strength_factors)
            final_strength = min(base_strength * quality_multiplier, 1.0)
            
            return final_strength
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def _identify_swing_points(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Identify swing highs and lows."""
        swing_highs = []
        swing_lows = []
        
        if len(df) < self.swing_lookback * 2 + 1:
            return swing_highs, swing_lows
        
        # Find swing highs
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            high_val = df['high'].iloc[i]
            is_swing_high = True
            
            # Check if current high is higher than surrounding bars
            for j in range(i - self.swing_lookback, i + self.swing_lookback + 1):
                if j != i and df['high'].iloc[j] >= high_val:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append({
                    'index': i,
                    'price': high_val,
                    'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                })
        
        # Find swing lows
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            low_val = df['low'].iloc[i]
            is_swing_low = True
            
            # Check if current low is lower than surrounding bars
            for j in range(i - self.swing_lookback, i + self.swing_lookback + 1):
                if j != i and df['low'].iloc[j] <= low_val:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append({
                    'index': i,
                    'price': low_val,
                    'timestamp': df.index[i] if hasattr(df.index, '__getitem__') else i
                })
        
        return swing_highs, swing_lows
    
    def _detect_bos_patterns(self, df: pd.DataFrame, swing_highs: List[Dict], 
                            swing_lows: List[Dict]) -> Dict[str, Any]:
        """Detect Break of Structure patterns."""
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        bos_results = {
            'bullish_bos': False,
            'bearish_bos': False,
            'bos_level': None,
            'strength': 0.0,
            'confirmation': False
        }
        
        # Check for bullish BOS (break above recent swing high)
        if swing_highs:
            recent_swing_high = max(swing_highs[-3:], key=lambda x: x['price']) if len(swing_highs) >= 3 else swing_highs[-1]
            
            if current_high > recent_swing_high['price']:
                # Confirm the break with body close
                body_break = current_price > recent_swing_high['price'] * 0.9999  # Allow small wick
                volume_confirmation = self._check_volume_confirmation(df)
                
                bos_results.update({
                    'bullish_bos': True,
                    'bos_level': recent_swing_high['price'],
                    'strength': 0.7 if body_break else 0.5,
                    'confirmation': body_break and volume_confirmation
                })
                
                self.last_bos = {
                    'type': 'bullish',
                    'level': recent_swing_high['price'],
                    'timestamp': datetime.now()
                }
        
        # Check for bearish BOS (break below recent swing low)
        if swing_lows:
            recent_swing_low = min(swing_lows[-3:], key=lambda x: x['price']) if len(swing_lows) >= 3 else swing_lows[-1]
            
            if current_low < recent_swing_low['price']:
                # Confirm the break with body close
                body_break = current_price < recent_swing_low['price'] * 1.0001  # Allow small wick
                volume_confirmation = self._check_volume_confirmation(df)
                
                bos_results.update({
                    'bearish_bos': True,
                    'bos_level': recent_swing_low['price'],
                    'strength': 0.7 if body_break else 0.5,
                    'confirmation': body_break and volume_confirmation
                })
                
                self.last_bos = {
                    'type': 'bearish',
                    'level': recent_swing_low['price'],
                    'timestamp': datetime.now()
                }
        
        return bos_results
    
    def _detect_choch_patterns(self, df: pd.DataFrame, swing_highs: List[Dict], 
                              swing_lows: List[Dict]) -> Dict[str, Any]:
        """Detect Change of Character patterns."""
        choch_results = {
            'bullish_choch': False,
            'bearish_choch': False,
            'choch_level': None,
            'strength': 0.0,
            'confirmation_bars': 0
        }
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return choch_results
        
        current_price = df['close'].iloc[-1]
        
        # Analyze recent structure for CHOCH
        recent_structure = self._analyze_recent_structure(df, swing_highs, swing_lows)
        
        # Bullish CHOCH: Break above previous lower high in downtrend
        if (recent_structure['trend'] == 'bearish' and 
            recent_structure['structure_break'] == 'bullish'):
            
            confirmation_bars = self._count_confirmation_bars(df, 'bullish')
            
            choch_results.update({
                'bullish_choch': True,
                'choch_level': recent_structure['break_level'],
                'strength': min(0.8, 0.4 + (confirmation_bars * 0.1)),
                'confirmation_bars': confirmation_bars
            })
            
            if confirmation_bars >= self.choch_confirmation_bars:
                self.current_trend = 'bullish'
                self.last_choch = {
                    'type': 'bullish',
                    'level': recent_structure['break_level'],
                    'timestamp': datetime.now()
                }
        
        # Bearish CHOCH: Break below previous higher low in uptrend  
        if (recent_structure['trend'] == 'bullish' and 
            recent_structure['structure_break'] == 'bearish'):
            
            confirmation_bars = self._count_confirmation_bars(df, 'bearish')
            
            choch_results.update({
                'bearish_choch': True,
                'choch_level': recent_structure['break_level'],
                'strength': min(0.8, 0.4 + (confirmation_bars * 0.1)),
                'confirmation_bars': confirmation_bars
            })
            
            if confirmation_bars >= self.choch_confirmation_bars:
                self.current_trend = 'bearish'
                self.last_choch = {
                    'type': 'bearish',
                    'level': recent_structure['break_level'],
                    'timestamp': datetime.now()
                }
        
        return choch_results
    
    def _analyze_market_structure(self, df: pd.DataFrame, swing_highs: List[Dict], 
                                 swing_lows: List[Dict]) -> Dict[str, Any]:
        """Analyze overall market structure."""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {'trend': 'neutral', 'structure_quality': 0.0}
        
        # Get recent swings
        recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
        recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
        
        # Analyze high structure
        high_trend = 'neutral'
        if len(recent_highs) >= 2:
            if recent_highs[-1]['price'] > recent_highs[-2]['price']:
                high_trend = 'bullish'
            elif recent_highs[-1]['price'] < recent_highs[-2]['price']:
                high_trend = 'bearish'
        
        # Analyze low structure
        low_trend = 'neutral'
        if len(recent_lows) >= 2:
            if recent_lows[-1]['price'] > recent_lows[-2]['price']:
                low_trend = 'bullish'
            elif recent_lows[-1]['price'] < recent_lows[-2]['price']:
                low_trend = 'bearish'
        
        # Determine overall trend
        overall_trend = 'neutral'
        structure_quality = 0.0
        
        if high_trend == 'bullish' and low_trend == 'bullish':
            overall_trend = 'bullish'
            structure_quality = 0.8
        elif high_trend == 'bearish' and low_trend == 'bearish':
            overall_trend = 'bearish'
            structure_quality = 0.8
        elif high_trend == 'bullish' or low_trend == 'bullish':
            overall_trend = 'bullish'
            structure_quality = 0.5
        elif high_trend == 'bearish' or low_trend == 'bearish':
            overall_trend = 'bearish'
            structure_quality = 0.5
        
        return {
            'trend': overall_trend,
            'high_trend': high_trend,
            'low_trend': low_trend,
            'structure_quality': structure_quality,
            'recent_highs_count': len(recent_highs),
            'recent_lows_count': len(recent_lows)
        }
    
    def _analyze_recent_structure(self, df: pd.DataFrame, swing_highs: List[Dict], 
                                 swing_lows: List[Dict]) -> Dict[str, Any]:
        """Analyze recent structure for CHOCH detection."""
        result = {
            'trend': 'neutral',
            'structure_break': None,
            'break_level': None
        }
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return result
        
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Check for structure in recent swings
        recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
        recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
        
        # Determine recent trend based on swing structure
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            last_high = recent_highs[-1]['price']
            prev_high = recent_highs[-2]['price']
            last_low = recent_lows[-1]['price']
            prev_low = recent_lows[-2]['price']
            
            # Bearish trend: Lower highs and lower lows
            if last_high < prev_high and last_low < prev_low:
                result['trend'] = 'bearish'
                # Check for bullish structure break
                if current_high > last_high:
                    result['structure_break'] = 'bullish'
                    result['break_level'] = last_high
            
            # Bullish trend: Higher highs and higher lows
            elif last_high > prev_high and last_low > prev_low:
                result['trend'] = 'bullish'
                # Check for bearish structure break
                if current_low < last_low:
                    result['structure_break'] = 'bearish'
                    result['break_level'] = last_low
        
        return result
    
    def _calculate_pattern_quality(self, bos_results: Dict, choch_results: Dict) -> float:
        """Calculate overall pattern quality."""
        quality_factors = []
        
        # BOS quality
        if bos_results.get('bullish_bos') or bos_results.get('bearish_bos'):
            bos_quality = bos_results.get('strength', 0.0)
            if bos_results.get('confirmation'):
                bos_quality += 0.2
            quality_factors.append(bos_quality)
        
        # CHOCH quality
        if choch_results.get('bullish_choch') or choch_results.get('bearish_choch'):
            choch_quality = choch_results.get('strength', 0.0)
            confirmation_bars = choch_results.get('confirmation_bars', 0)
            if confirmation_bars >= self.choch_confirmation_bars:
                choch_quality += 0.2
            quality_factors.append(choch_quality)
        
        if not quality_factors:
            return 0.0
        
        return min(sum(quality_factors) / len(quality_factors), 1.0)
    
    def _check_volume_confirmation(self, df: pd.DataFrame, lookback: int = 5) -> bool:
        """Check if current volume confirms the pattern."""
        if 'volume' not in df.columns or len(df) < lookback + 1:
            return True  # Assume confirmed if no volume data
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-lookback-1:-1].mean()
        
        return current_volume > avg_volume * 1.2  # 20% above average
    
    def _count_confirmation_bars(self, df: pd.DataFrame, direction: str, 
                                lookback: int = 5) -> int:
        """Count confirmation bars in the specified direction."""
        if len(df) < lookback:
            return 0
        
        confirmation_count = 0
        recent_bars = df.tail(lookback)
        
        for _, bar in recent_bars.iterrows():
            if direction == 'bullish':
                if bar['close'] > bar['open']:  # Green/bullish candle
                    confirmation_count += 1
            else:  # bearish
                if bar['close'] < bar['open']:  # Red/bearish candle
                    confirmation_count += 1
        
        return confirmation_count