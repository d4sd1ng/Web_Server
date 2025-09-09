"""
Order Blocks Agent
Detects and analyzes Order Block patterns in ICT/SMC methodology
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime

from ..base_agent import BasePatternAgent


class OrderBlocksAgent(BasePatternAgent):
    """
    Agent for detecting Order Block patterns.
    
    Order Blocks are areas where large institutional orders were placed,
    often identified by strong price moves followed by consolidation or reversal.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.min_displacement_ratio = self.get_config_value('min_displacement_ratio', 2.0)
        self.volume_threshold = self.get_config_value('volume_threshold', 1.5)
        self.retest_threshold = self.get_config_value('retest_threshold', 0.002)  # 0.2%
        self.min_consolidation_bars = self.get_config_value('min_consolidation_bars', 3)
        self.ob_timeout_bars = self.get_config_value('ob_timeout_bars', 100)
        
        # Order block tracking
        self.active_order_blocks = []
        self.tested_order_blocks = []
        
    def process_data(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Process market data to detect Order Block patterns.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing Order Block analysis
        """
        if not self.validate_data(df):
            return {'error': 'Invalid data provided'}
        
        try:
            # Detect displacement moves
            displacements = self._detect_displacement_moves(df)
            
            # Identify potential order blocks
            potential_obs = self._identify_order_blocks(df, displacements)
            
            # Validate order blocks
            validated_obs = self._validate_order_blocks(df, potential_obs)
            
            # Update existing order blocks status
            self._update_order_blocks_status(df)
            
            # Analyze current price vs order blocks
            price_analysis = self._analyze_price_vs_order_blocks(df)
            
            # Calculate pattern strength
            pattern_strength = self._calculate_ob_strength(validated_obs, price_analysis)
            
            return {
                'displacements': displacements,
                'potential_obs': potential_obs,
                'validated_obs': validated_obs,
                'active_obs': len(self.active_order_blocks),
                'tested_obs': len(self.tested_order_blocks),
                'price_analysis': price_analysis,
                'pattern_strength': pattern_strength,
                'current_ob_zones': self._get_current_ob_zones()
            }
            
        except Exception as e:
            self.logger.error(f"Error in Order Blocks analysis: {e}")
            return {'error': str(e)}
    
    def get_signal_strength(self, df: pd.DataFrame, symbol: str = None) -> float:
        """
        Calculate signal strength based on Order Block patterns.
        
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
            validated_obs = analysis.get('validated_obs', [])
            
            # Base strength from pattern analysis
            base_strength = min(pattern_strength, 0.8)
            
            # Fresh order block bonus
            fresh_ob_bonus = 0.0
            if validated_obs:
                fresh_ob_strength = sum(ob.get('strength', 0.0) for ob in validated_obs) / len(validated_obs)
                fresh_ob_bonus = min(fresh_ob_strength * 0.15, 0.15)
            
            # Price interaction bonus
            interaction_bonus = 0.0
            if price_analysis.get('near_order_block'):
                interaction_bonus += 0.05
            if price_analysis.get('testing_order_block'):
                interaction_bonus += 0.1
            if price_analysis.get('respected_order_block'):
                interaction_bonus += 0.05
            
            final_strength = min(base_strength + fresh_ob_bonus + interaction_bonus, 1.0)
            return final_strength
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def _detect_displacement_moves(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect strong displacement moves that create order blocks."""
        displacements = []
        
        if len(df) < 10:
            return displacements
        
        # Calculate average candle body size
        for i in range(5, len(df) - 1):
            current_bar = df.iloc[i]
            
            # Calculate metrics
            body_size = abs(current_bar['close'] - current_bar['open'])
            candle_range = current_bar['high'] - current_bar['low']
            
            # Get average body size for comparison
            recent_bars = df.iloc[i-5:i]
            avg_body_size = recent_bars['close'].sub(recent_bars['open']).abs().mean()
            
            # Check for displacement criteria
            if body_size > avg_body_size * self.min_displacement_ratio and candle_range > 0:
                
                body_ratio = body_size / candle_range
                direction = 'bullish' if current_bar['close'] > current_bar['open'] else 'bearish'
                
                # Volume confirmation
                volume_confirmed = True
                if 'volume' in df.columns:
                    avg_volume = df['volume'].iloc[i-5:i].mean()
                    volume_confirmed = current_bar['volume'] > avg_volume * self.volume_threshold
                
                # Calculate displacement strength
                displacement_ratio = body_size / avg_body_size
                strength = min((displacement_ratio / self.min_displacement_ratio) * 0.5 + body_ratio * 0.3, 1.0)
                
                if volume_confirmed:
                    strength += 0.2
                
                displacement = {
                    'index': i,
                    'direction': direction,
                    'strength': min(strength, 1.0),
                    'body_size': body_size,
                    'body_ratio': body_ratio,
                    'displacement_ratio': displacement_ratio,
                    'volume_confirmed': volume_confirmed,
                    'high': current_bar['high'],
                    'low': current_bar['low'],
                    'open': current_bar['open'],
                    'close': current_bar['close']
                }
                
                displacements.append(displacement)
        
        return displacements
    
    def _identify_order_blocks(self, df: pd.DataFrame, displacements: List[Dict]) -> List[Dict[str, Any]]:
        """Identify potential order blocks before displacement moves."""
        order_blocks = []
        
        for displacement in displacements:
            disp_index = displacement['index']
            direction = displacement['direction']
            
            # Look for the last consolidation/order block before displacement
            ob_candidates = []
            
            # Search backwards from displacement for potential OB candles
            search_start = max(0, disp_index - 20)  # Look back up to 20 bars
            
            for i in range(disp_index - 1, search_start - 1, -1):
                candidate_bar = df.iloc[i]
                
                # For bullish displacement, look for the last bearish/consolidation candle
                # For bearish displacement, look for the last bullish/consolidation candle
                if direction == 'bullish':
                    # Look for bearish or neutral candles that could be order blocks
                    if candidate_bar['close'] <= candidate_bar['open']:
                        ob_candidates.append({
                            'index': i,
                            'type': 'bearish_ob',
                            'high': candidate_bar['high'],
                            'low': candidate_bar['low'],
                            'open': candidate_bar['open'],
                            'close': candidate_bar['close'],
                            'body_size': candidate_bar['open'] - candidate_bar['close'],
                            'displacement_index': disp_index,
                            'displacement_direction': direction
                        })
                else:  # bearish displacement
                    # Look for bullish or neutral candles that could be order blocks
                    if candidate_bar['close'] >= candidate_bar['open']:
                        ob_candidates.append({
                            'index': i,
                            'type': 'bullish_ob',
                            'high': candidate_bar['high'],
                            'low': candidate_bar['low'],
                            'open': candidate_bar['open'],
                            'close': candidate_bar['close'],
                            'body_size': candidate_bar['close'] - candidate_bar['open'],
                            'displacement_index': disp_index,
                            'displacement_direction': direction
                        })
                
                # Stop searching if we find a strong move in the opposite direction
                current_body = abs(candidate_bar['close'] - candidate_bar['open'])
                if i > search_start + 5:  # Don't break too early
                    recent_avg = df.iloc[i-5:i]['close'].sub(df.iloc[i-5:i]['open']).abs().mean()
                    if current_body > recent_avg * 1.5:
                        break
            
            # Select the best order block candidate (closest to displacement)
            if ob_candidates:
                best_ob = ob_candidates[0]  # Closest to displacement
                
                # Add displacement information
                best_ob.update({
                    'displacement_strength': displacement['strength'],
                    'displacement_volume_confirmed': displacement['volume_confirmed'],
                    'formation_complete': True
                })
                
                order_blocks.append(best_ob)
        
        return order_blocks
    
    def _validate_order_blocks(self, df: pd.DataFrame, potential_obs: List[Dict]) -> List[Dict[str, Any]]:
        """Validate potential order blocks with additional criteria."""
        validated_obs = []
        
        for ob in potential_obs:
            validation_score = 0.0
            max_score = 5.0
            
            # 1. Displacement strength validation (0-1 points)
            disp_strength = ob.get('displacement_strength', 0.0)
            validation_score += disp_strength
            
            # 2. Volume validation (0-1 points)
            if ob.get('displacement_volume_confirmed', False):
                validation_score += 1.0
            
            # 3. Order block position validation (0-1 points)
            # OB should be near the start of the displacement move
            displacement_index = ob['displacement_index']
            ob_index = ob['index']
            distance = displacement_index - ob_index
            if distance <= 3:  # Very close
                validation_score += 1.0
            elif distance <= 5:  # Close
                validation_score += 0.7
            elif distance <= 10:  # Moderate
                validation_score += 0.4
            
            # 4. Order block size validation (0-1 points)
            # OB should have reasonable size compared to recent price action
            ob_range = ob['high'] - ob['low']
            if displacement_index >= 10:
                recent_bars = df.iloc[displacement_index-10:displacement_index]
                avg_range = (recent_bars['high'] - recent_bars['low']).mean()
                
                if ob_range >= avg_range * 0.5:  # At least 50% of average range
                    range_ratio = min(ob_range / avg_range, 2.0) / 2.0  # Cap at 2x average
                    validation_score += range_ratio
            
            # 5. Market context validation (0-1 points)
            # Check if the order block makes sense in market context
            if displacement_index >= 5:
                # Look at trend before displacement
                pre_trend_bars = df.iloc[displacement_index-5:displacement_index]
                trend_direction = 'neutral'
                
                if pre_trend_bars['close'].iloc[-1] > pre_trend_bars['close'].iloc[0]:
                    trend_direction = 'bullish'
                elif pre_trend_bars['close'].iloc[-1] < pre_trend_bars['close'].iloc[0]:
                    trend_direction = 'bearish'
                
                # Bullish OB should occur in bearish/neutral context before bullish displacement
                # Bearish OB should occur in bullish/neutral context before bearish displacement
                if ((ob['type'] == 'bullish_ob' and ob['displacement_direction'] == 'bearish') or
                    (ob['type'] == 'bearish_ob' and ob['displacement_direction'] == 'bullish') or
                    trend_direction == 'neutral'):
                    validation_score += 0.8
                
            # Calculate final strength
            final_strength = min(validation_score / max_score, 1.0)
            
            # Only include OBs with reasonable strength
            if final_strength >= 0.4:
                ob['validation_score'] = validation_score
                ob['strength'] = final_strength
                ob['validated'] = True
                
                # Add to active order blocks
                ob['age_bars'] = 0
                ob['tested'] = False
                ob['respected_count'] = 0
                ob['formation_timestamp'] = datetime.now()
                
                validated_obs.append(ob)
                self.active_order_blocks.append(ob)
        
        return validated_obs
    
    def _update_order_blocks_status(self, df: pd.DataFrame):
        """Update status of existing order blocks."""
        current_index = len(df) - 1
        current_bar = df.iloc[-1]
        
        obs_to_remove = []
        
        for i, ob in enumerate(self.active_order_blocks):
            # Update age
            ob['age_bars'] = current_index - ob['displacement_index']
            
            # Check for retest/interaction
            if not ob.get('tested', False):
                is_tested, test_result = self._check_order_block_test(ob, current_bar)
                
                if is_tested:
                    ob['tested'] = True
                    ob['test_result'] = test_result
                    ob['test_index'] = current_index
                    
                    if test_result == 'respected':
                        ob['respected_count'] = ob.get('respected_count', 0) + 1
                    elif test_result == 'broken':
                        # Move to tested blocks
                        self.tested_order_blocks.append(ob)
                        obs_to_remove.append(i)
            
            # Remove expired order blocks
            if ob['age_bars'] > self.ob_timeout_bars:
                obs_to_remove.append(i)
        
        # Remove tested or expired order blocks
        for i in reversed(obs_to_remove):
            if i < len(self.active_order_blocks):
                self.active_order_blocks.pop(i)
    
    def _check_order_block_test(self, ob: Dict[str, Any], current_bar: pd.Series) -> Tuple[bool, str]:
        """Check if order block is being tested by current price action."""
        ob_high = ob['high']
        ob_low = ob['low']
        ob_type = ob['type']
        
        # Define test zone with small buffer
        test_buffer = (ob_high - ob_low) * 0.1  # 10% buffer
        test_zone_high = ob_high + test_buffer
        test_zone_low = ob_low - test_buffer
        
        # Check if price is interacting with the order block
        price_in_zone = (current_bar['low'] <= test_zone_high and 
                        current_bar['high'] >= test_zone_low)
        
        if not price_in_zone:
            return False, None
        
        # Determine test result based on order block type and price action
        if ob_type == 'bullish_ob':
            # For bullish OB, we expect price to find support
            if (current_bar['low'] <= ob_high and current_bar['close'] > ob_low):
                # Price touched the OB and closed above it - potential respect
                if current_bar['close'] > current_bar['open']:  # Bullish candle
                    return True, 'respected'
                else:
                    return True, 'tested'  # Neutral test
            elif current_bar['close'] < ob_low:
                # Price closed below OB - broken
                return True, 'broken'
        
        else:  # bearish_ob
            # For bearish OB, we expect price to find resistance
            if (current_bar['high'] >= ob_low and current_bar['close'] < ob_high):
                # Price touched the OB and closed below it - potential respect
                if current_bar['close'] < current_bar['open']:  # Bearish candle
                    return True, 'respected'
                else:
                    return True, 'tested'  # Neutral test
            elif current_bar['close'] > ob_high:
                # Price closed above OB - broken
                return True, 'broken'
        
        return True, 'tested'  # Default to tested if in zone but unclear result
    
    def _analyze_price_vs_order_blocks(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze current price action relative to order blocks."""
        current_price = df['close'].iloc[-1]
        current_bar = df.iloc[-1]
        
        analysis = {
            'near_order_block': False,
            'testing_order_block': False,
            'respected_order_block': False,
            'closest_ob_distance': float('inf'),
            'obs_above': 0,
            'obs_below': 0,
            'strongest_ob_nearby': None
        }
        
        if not self.active_order_blocks:
            return analysis
        
        obs_above = 0
        obs_below = 0
        min_distance = float('inf')
        strongest_ob = None
        max_strength = 0.0
        
        for ob in self.active_order_blocks:
            ob_center = (ob['high'] + ob['low']) / 2
            distance = abs(current_price - ob_center) / current_price
            
            if distance < min_distance:
                min_distance = distance
            
            if ob.get('strength', 0.0) > max_strength and distance < 0.02:  # Within 2%
                max_strength = ob['strength']
                strongest_ob = ob
            
            if ob_center > current_price:
                obs_above += 1
            else:
                obs_below += 1
            
            # Check proximity (within 1%)
            if distance < 0.01:
                analysis['near_order_block'] = True
                
                # Check if currently testing
                is_testing, test_result = self._check_order_block_test(ob, current_bar)
                if is_testing:
                    analysis['testing_order_block'] = True
                    if test_result == 'respected':
                        analysis['respected_order_block'] = True
        
        analysis.update({
            'closest_ob_distance': min_distance,
            'obs_above': obs_above,
            'obs_below': obs_below,
            'strongest_ob_nearby': strongest_ob
        })
        
        return analysis
    
    def _calculate_ob_strength(self, validated_obs: List[Dict], price_analysis: Dict) -> float:
        """Calculate overall Order Block pattern strength."""
        if not validated_obs and not self.active_order_blocks:
            return 0.0
        
        strength_factors = []
        
        # New order blocks strength
        if validated_obs:
            avg_new_ob_strength = sum(ob['strength'] for ob in validated_obs) / len(validated_obs)
            volume_bonus = sum(0.1 for ob in validated_obs if ob.get('displacement_volume_confirmed', False)) / len(validated_obs)
            new_ob_strength = min(avg_new_ob_strength + volume_bonus, 1.0)
            strength_factors.append(new_ob_strength * 0.8)  # High weight for new OBs
        
        # Active order blocks quality
        if self.active_order_blocks:
            respected_obs = sum(1 for ob in self.active_order_blocks if ob.get('respected_count', 0) > 0)
            untested_obs = sum(1 for ob in self.active_order_blocks if not ob.get('tested', False))
            
            # Quality based on respect rate and untested OBs
            respect_rate = respected_obs / len(self.active_order_blocks) if self.active_order_blocks else 0
            untested_rate = untested_obs / len(self.active_order_blocks) if self.active_order_blocks else 0
            
            active_ob_quality = (respect_rate * 0.7) + (untested_rate * 0.3)  # Untested OBs have potential
            strength_factors.append(active_ob_quality * 0.4)  # Moderate weight for existing OBs
        
        if not strength_factors:
            return 0.0
        
        base_strength = sum(strength_factors)
        
        # Price interaction multiplier
        price_multiplier = 1.0
        if price_analysis.get('near_order_block'):
            price_multiplier += 0.1
        if price_analysis.get('testing_order_block'):
            price_multiplier += 0.15
        if price_analysis.get('respected_order_block'):
            price_multiplier += 0.1
        
        # Strongest nearby OB bonus
        strongest_ob = price_analysis.get('strongest_ob_nearby')
        if strongest_ob and strongest_ob.get('strength', 0.0) > 0.7:
            price_multiplier += 0.05
        
        return min(base_strength * price_multiplier, 1.0)
    
    def _get_current_ob_zones(self) -> List[Dict[str, Any]]:
        """Get current active order block zones."""
        return [{
            'type': ob['type'],
            'high': ob['high'],
            'low': ob['low'],
            'strength': ob['strength'],
            'age_bars': ob.get('age_bars', 0),
            'respected_count': ob.get('respected_count', 0),
            'tested': ob.get('tested', False),
            'displacement_direction': ob['displacement_direction']
        } for ob in self.active_order_blocks]
    
    def get_order_block_statistics(self) -> Dict[str, Any]:
        """Get comprehensive order block statistics."""
        total_obs = len(self.active_order_blocks) + len(self.tested_order_blocks)
        
        if total_obs == 0:
            return {
                'total_obs_detected': 0,
                'active_obs': 0,
                'tested_obs': 0,
                'respect_rate': 0.0,
                'break_rate': 0.0
            }
        
        # Calculate respect and break rates
        respected_count = sum(1 for ob in self.tested_order_blocks if ob.get('test_result') == 'respected')
        broken_count = sum(1 for ob in self.tested_order_blocks if ob.get('test_result') == 'broken')
        total_tested = len(self.tested_order_blocks)
        
        respect_rate = respected_count / total_tested if total_tested > 0 else 0
        break_rate = broken_count / total_tested if total_tested > 0 else 0
        
        return {
            'total_obs_detected': total_obs,
            'active_obs': len(self.active_order_blocks),
            'tested_obs': len(self.tested_order_blocks),
            'respect_rate': respect_rate,
            'break_rate': break_rate,
            'bullish_active': sum(1 for ob in self.active_order_blocks if ob['type'] == 'bullish_ob'),
            'bearish_active': sum(1 for ob in self.active_order_blocks if ob['type'] == 'bearish_ob'),
            'avg_age_bars': sum(ob.get('age_bars', 0) for ob in self.active_order_blocks) / len(self.active_order_blocks) if self.active_order_blocks else 0
        }
    
    def clear_old_order_blocks(self, max_age_bars: int = None):
        """Clear old order blocks to prevent memory buildup."""
        if max_age_bars is None:
            max_age_bars = self.ob_timeout_bars
        
        self.active_order_blocks = [ob for ob in self.active_order_blocks 
                                  if ob.get('age_bars', 0) < max_age_bars]
        
        # Keep only recent tested order blocks
        self.tested_order_blocks = self.tested_order_blocks[-100:]  # Keep last 100 tested OBs