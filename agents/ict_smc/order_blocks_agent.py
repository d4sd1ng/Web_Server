"""
Order Blocks Agent
Detects and analyzes Order Blocks using existing ICT/SMC implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class OrderBlocksAgent(ICTSMCAgent):
    """
    Specialized agent for Order Block detection and analysis
    Uses existing detect_order_blocks() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("order_blocks", config)
        
        # Order Block specific configuration
        self.lookback = config.get('lookback', 30)
        self.min_body = config.get('min_body', 0.3)
        self.retest_confirmation_bars = config.get('retest_confirmation_bars', 3)
        
        # Active Order Blocks tracking
        self.active_order_blocks = []
        self.validated_order_blocks = []
        self.invalidated_order_blocks = []
        
        self.logger.info("Order Blocks Agent initialized")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect Order Blocks
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with Order Block analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback:
            return {'order_blocks': [], 'signal_strength': 0.0}
        
        try:
            # Use existing detect_order_blocks function
            order_blocks = self.detect_order_blocks(df, self.lookback, self.min_body)
            
            # Analyze Order Block patterns
            analysis_results = self.analyze_order_blocks(order_blocks, df, symbol)
            
            # Update active Order Blocks
            self.update_active_order_blocks(order_blocks, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_ob_signal_strength(order_blocks, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'order_blocks': order_blocks,
                'active_order_blocks': self.active_order_blocks,
                'validated_order_blocks': self.validated_order_blocks,
                'invalidated_order_blocks': self.invalidated_order_blocks,
                'analysis': analysis_results,
                'signal_strength': signal_strength,
                'trading_opportunities': self.identify_ob_trading_opportunities(order_blocks, df)
            }
            
            # Publish Order Block signals
            if order_blocks:
                self.publish("order_blocks_detected", {
                    'symbol': symbol,
                    'order_blocks': order_blocks,
                    'signal_strength': signal_strength
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing Order Block data for {symbol}: {e}")
            return {'order_blocks': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_order_blocks(self, df: pd.DataFrame, lookback: int = 30, min_body: float = 0.3) -> List[Dict[str, Any]]:
        """
        Detect Order Blocks - Using existing optimized implementation
        """
        try:
            # Import the ICTSMCEngine from your existing code
            from ict_smc_enhancement import ICTSMCEngine
            
            # Use the optimized ICT/SMC engine for better detection
            ict_engine = ICTSMCEngine(df)
            optimized_obs = ict_engine.detect_order_blocks(lookback=lookback)
            
            # Convert to the expected format for compatibility
            obs = []
            for ob in optimized_obs:
                zone = (ob['low'], ob['high'])
                
                # Check for retest (simplified)
                retest = False
                if ob['index'] + self.retest_confirmation_bars < len(df):
                    future_lows = df['low'].iloc[ob['index']+self.retest_confirmation_bars:]
                    future_highs = df['high'].iloc[ob['index']+self.retest_confirmation_bars:]
                    retest = ((future_lows < zone[1]) & (future_highs > zone[0])).any()
                
                obs.append({
                    'type': ob['type'].replace('volume_', '').replace('_bullish', 'bullish').replace('_bearish', 'bearish'),
                    'zone': zone,
                    'retest': retest,
                    'index': ob['index'],
                    'strength': ob.get('strength', 0),
                    'volume': ob.get('volume', 0),
                    'timestamp': df.index[ob['index']] if ob['index'] < len(df) else None,
                    'validation_status': 'pending'
                })
            
            return obs
            
        except ImportError:
            # Fallback to basic Order Block detection
            return self.basic_order_block_detection(df, lookback, min_body)
        except Exception as e:
            self.logger.error(f"Error in Order Block detection: {e}")
            return []
    
    def basic_order_block_detection(self, df: pd.DataFrame, lookback: int = 30, min_body: float = 0.3) -> List[Dict[str, Any]]:
        """
        Basic Order Block detection (fallback implementation)
        """
        obs = []
        
        for i in range(lookback, len(df) - 2):
            current = df.iloc[i]
            
            # Calculate body size
            body_size = abs(current['close'] - current['open'])
            candle_range = current['high'] - current['low']
            body_ratio = body_size / candle_range if candle_range > 0 else 0
            
            # Check for bullish Order Block
            if (current['close'] > current['open'] and  # Bullish candle
                body_ratio >= min_body and  # Strong body
                current['volume'] > df['volume'].rolling(20).mean().iloc[i]):  # Above average volume
                
                # Look for subsequent bearish movement (order block formation)
                if i + 2 < len(df) and df['low'].iloc[i+1:i+3].min() < current['low']:
                    zone = (current['open'], current['close'])
                    
                    obs.append({
                        'type': 'bullish',
                        'zone': zone,
                        'retest': False,  # Will be updated later
                        'index': i,
                        'strength': self.calculate_basic_ob_strength(df, i, 'bullish'),
                        'volume': current['volume'],
                        'timestamp': df.index[i],
                        'validation_status': 'pending'
                    })
            
            # Check for bearish Order Block
            elif (current['close'] < current['open'] and  # Bearish candle
                  body_ratio >= min_body and  # Strong body
                  current['volume'] > df['volume'].rolling(20).mean().iloc[i]):  # Above average volume
                
                # Look for subsequent bullish movement
                if i + 2 < len(df) and df['high'].iloc[i+1:i+3].max() > current['high']:
                    zone = (current['close'], current['open'])
                    
                    obs.append({
                        'type': 'bearish',
                        'zone': zone,
                        'retest': False,  # Will be updated later
                        'index': i,
                        'strength': self.calculate_basic_ob_strength(df, i, 'bearish'),
                        'volume': current['volume'],
                        'timestamp': df.index[i],
                        'validation_status': 'pending'
                    })
        
        return obs
    
    def calculate_basic_ob_strength(self, df: pd.DataFrame, index: int, ob_type: str) -> float:
        """Calculate basic Order Block strength"""
        try:
            current = df.iloc[index]
            
            # Volume strength
            avg_volume = df['volume'].rolling(20).mean().iloc[index]
            volume_strength = min(current['volume'] / avg_volume, 3.0) / 3.0
            
            # Body strength
            body_size = abs(current['close'] - current['open'])
            candle_range = current['high'] - current['low']
            body_strength = body_size / candle_range if candle_range > 0 else 0
            
            # Volatility context
            if 'atr' in df.columns:
                atr = df['atr'].iloc[index]
                volatility_strength = min(candle_range / atr, 2.0) / 2.0
            else:
                volatility_strength = 0.5
            
            # Combine strengths
            return (volume_strength * 0.4 + body_strength * 0.4 + volatility_strength * 0.2)
            
        except Exception:
            return 0.5
    
    def analyze_order_blocks(self, order_blocks: List[Dict[str, Any]], df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze Order Block patterns and characteristics
        """
        if not order_blocks:
            return {'total_obs': 0, 'bullish_obs': 0, 'bearish_obs': 0}
        
        bullish_obs = [ob for ob in order_blocks if ob['type'] == 'bullish']
        bearish_obs = [ob for ob in order_blocks if ob['type'] == 'bearish']
        
        # Calculate retest statistics
        bullish_retests = sum(1 for ob in bullish_obs if ob['retest'])
        bearish_retests = sum(1 for ob in bearish_obs if ob['retest'])
        
        # Calculate average strengths
        avg_bullish_strength = np.mean([ob['strength'] for ob in bullish_obs]) if bullish_obs else 0
        avg_bearish_strength = np.mean([ob['strength'] for ob in bearish_obs]) if bearish_obs else 0
        
        return {
            'total_obs': len(order_blocks),
            'bullish_obs': len(bullish_obs),
            'bearish_obs': len(bearish_obs),
            'bullish_retests': bullish_retests,
            'bearish_retests': bearish_retests,
            'bullish_retest_rate': bullish_retests / len(bullish_obs) if bullish_obs else 0,
            'bearish_retest_rate': bearish_retests / len(bearish_obs) if bearish_obs else 0,
            'avg_bullish_strength': avg_bullish_strength,
            'avg_bearish_strength': avg_bearish_strength,
            'ob_bias': 'bullish' if len(bullish_obs) > len(bearish_obs) else 'bearish' if len(bearish_obs) > len(bullish_obs) else 'neutral'
        }
    
    def update_active_order_blocks(self, new_obs: List[Dict[str, Any]], df: pd.DataFrame):
        """
        Update active Order Blocks and validate them
        """
        current_price = df['close'].iloc[-1]
        
        # Validate existing active Order Blocks
        still_active = []
        for ob in self.active_order_blocks:
            validation_result = self.validate_order_block(ob, df, current_price)
            
            if validation_result == 'validated':
                ob['validation_status'] = 'validated'
                self.validated_order_blocks.append(ob)
                self.logger.info(f"{ob['type'].capitalize()} Order Block validated")
            elif validation_result == 'invalidated':
                ob['validation_status'] = 'invalidated'
                self.invalidated_order_blocks.append(ob)
                self.logger.info(f"{ob['type'].capitalize()} Order Block invalidated")
            else:
                still_active.append(ob)
        
        # Add new Order Blocks
        for ob in new_obs:
            if ob not in still_active:
                ob['detected_time'] = datetime.now(timezone.utc)
                still_active.append(ob)
        
        self.active_order_blocks = still_active
        
        # Limit active Order Blocks
        if len(self.active_order_blocks) > 100:
            self.active_order_blocks = self.active_order_blocks[-100:]
    
    def validate_order_block(self, ob: Dict[str, Any], df: pd.DataFrame, current_price: float) -> str:
        """
        Validate Order Block based on price action
        """
        zone_low, zone_high = ob['zone']
        
        # Check if Order Block has been broken
        if ob['type'] == 'bullish':
            if current_price < zone_low:
                return 'invalidated'  # Price broke below bullish OB
            elif zone_low <= current_price <= zone_high:
                return 'validated'  # Price retesting bullish OB
        else:  # bearish
            if current_price > zone_high:
                return 'invalidated'  # Price broke above bearish OB
            elif zone_low <= current_price <= zone_high:
                return 'validated'  # Price retesting bearish OB
        
        return 'pending'  # Still waiting for validation
    
    def identify_ob_trading_opportunities(self, order_blocks: List[Dict[str, Any]], df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify trading opportunities based on Order Blocks
        """
        opportunities = []
        current_price = df['close'].iloc[-1]
        
        if 'atr' not in df.columns:
            return opportunities
        
        current_atr = df['atr'].iloc[-1]
        
        for ob in order_blocks:
            zone_low, zone_high = ob['zone']
            
            # Check if price is near or in the Order Block
            in_zone = zone_low <= current_price <= zone_high
            distance_to_zone = 0 if in_zone else min(abs(current_price - zone_low), abs(current_price - zone_high))
            
            if in_zone or distance_to_zone <= 2.0 * current_atr:
                opportunity = {
                    'ob_type': ob['type'],
                    'zone': ob['zone'],
                    'in_zone': in_zone,
                    'distance': distance_to_zone,
                    'strength': ob['strength'],
                    'retest_status': ob['retest'],
                    'opportunity_type': 'retest' if in_zone else 'approach',
                    'recommended_action': self.get_ob_recommendation(ob, current_price, current_atr, in_zone)
                }
                opportunities.append(opportunity)
        
        return opportunities
    
    def get_ob_recommendation(self, ob: Dict[str, Any], current_price: float, atr: float, in_zone: bool) -> str:
        """
        Get trading recommendation based on Order Block analysis
        """
        zone_low, zone_high = ob['zone']
        
        if ob['type'] == 'bullish':
            if in_zone:
                return f"LONG opportunity - Price retesting bullish Order Block"
            elif current_price < zone_low:
                return f"LONG setup - Wait for price to reach Order Block"
            else:
                return f"Order Block above current price - Monitor for retest"
        
        else:  # bearish Order Block
            if in_zone:
                return f"SHORT opportunity - Price retesting bearish Order Block"
            elif current_price > zone_high:
                return f"SHORT setup - Wait for price to reach Order Block"
            else:
                return f"Order Block below current price - Monitor for retest"
    
    def calculate_ob_signal_strength(self, order_blocks: List[Dict[str, Any]], df: pd.DataFrame) -> float:
        """
        Calculate overall Order Block signal strength
        """
        if not order_blocks:
            return 0.0
        
        current_price = df['close'].iloc[-1]
        current_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['close'].iloc[-1] * 0.01
        
        strength_scores = []
        
        for ob in order_blocks:
            # Individual OB strength
            base_strength = ob['strength']
            
            # Proximity bonus
            zone_low, zone_high = ob['zone']
            distance = min(abs(current_price - zone_low), abs(current_price - zone_high))
            proximity_score = max(0, 1 - (distance / (3.0 * current_atr)))
            
            # Retest bonus
            retest_bonus = 0.3 if ob['retest'] else 0
            
            # Volume bonus
            volume_bonus = min(ob.get('volume', 0) / df['volume'].mean(), 2.0) / 2.0 * 0.2
            
            total_strength = base_strength + proximity_score * 0.3 + retest_bonus + volume_bonus
            strength_scores.append(min(total_strength, 1.0))
        
        return np.mean(strength_scores) if strength_scores else 0.0
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_valid_bullish_obs(self) -> List[Dict[str, Any]]:
        """
        Get validated bullish Order Blocks
        """
        return [ob for ob in self.validated_order_blocks if ob['type'] == 'bullish']
    
    def get_valid_bearish_obs(self) -> List[Dict[str, Any]]:
        """
        Get validated bearish Order Blocks
        """
        return [ob for ob in self.validated_order_blocks if ob['type'] == 'bearish']
    
    def get_order_blocks_near_price(self, price: float, atr: float) -> List[Dict[str, Any]]:
        """
        Get Order Blocks near the specified price
        """
        near_obs = []
        
        for ob in self.active_order_blocks + self.validated_order_blocks:
            zone_low, zone_high = ob['zone']
            
            # Check if price is in zone or nearby
            in_zone = zone_low <= price <= zone_high
            distance = 0 if in_zone else min(abs(price - zone_low), abs(price - zone_high))
            
            if in_zone or distance <= 2.0 * atr:
                ob_copy = ob.copy()
                ob_copy['distance_to_price'] = distance
                ob_copy['in_zone'] = in_zone
                near_obs.append(ob_copy)
        
        # Sort by distance (closest first)
        near_obs.sort(key=lambda x: x['distance_to_price'])
        return near_obs
    
    def get_ob_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive Order Block summary
        """
        return {
            'agent_id': self.agent_id,
            'active_obs_count': len(self.active_order_blocks),
            'validated_obs_count': len(self.validated_order_blocks),
            'invalidated_obs_count': len(self.invalidated_order_blocks),
            'active_bullish_obs': len([ob for ob in self.active_order_blocks if ob['type'] == 'bullish']),
            'active_bearish_obs': len([ob for ob in self.active_order_blocks if ob['type'] == 'bearish']),
            'validated_bullish_obs': len([ob for ob in self.validated_order_blocks if ob['type'] == 'bullish']),
            'validated_bearish_obs': len([ob for ob in self.validated_order_blocks if ob['type'] == 'bearish']),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'min_body': self.min_body,
                'retest_confirmation_bars': self.retest_confirmation_bars
            }
        }
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "price_update":
            # Update Order Block validation status
            symbol = message['data']['symbol']
            price_data = message['data']
            
            self.logger.debug(f"Received price update for {symbol}: {price_data}")
            self.update_ob_validations(price_data)
        
        elif topic == "market_structure_update":
            # React to market structure changes
            self.logger.debug("Received market structure update")
        
        super().on_message(topic, message)
    
    def update_ob_validations(self, price_data: Dict[str, Any]):
        """
        Update Order Block validations based on price action
        """
        if 'close' not in price_data:
            return
        
        current_price = price_data['close']
        
        # Check active Order Blocks for validation changes
        validation_changes = 0
        for ob in self.active_order_blocks[:]:  # Copy to avoid modification during iteration
            old_status = ob['validation_status']
            
            # Simple validation check
            zone_low, zone_high = ob['zone']
            
            if ob['type'] == 'bullish':
                if current_price < zone_low:
                    ob['validation_status'] = 'invalidated'
                    self.active_order_blocks.remove(ob)
                    self.invalidated_order_blocks.append(ob)
                    validation_changes += 1
                elif zone_low <= current_price <= zone_high and old_status == 'pending':
                    ob['validation_status'] = 'validated'
                    ob['retest'] = True
                    validation_changes += 1
            
            else:  # bearish
                if current_price > zone_high:
                    ob['validation_status'] = 'invalidated'
                    self.active_order_blocks.remove(ob)
                    self.invalidated_order_blocks.append(ob)
                    validation_changes += 1
                elif zone_low <= current_price <= zone_high and old_status == 'pending':
                    ob['validation_status'] = 'validated'
                    ob['retest'] = True
                    validation_changes += 1
        
        if validation_changes > 0:
            self.logger.info(f"Updated {validation_changes} Order Block validations")
    
    def requires_continuous_processing(self) -> bool:
        """Order Block agent doesn't need continuous background processing"""
        return False