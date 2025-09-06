"""
Fair Value Gaps Agent
Detects and analyzes Fair Value Gaps using existing ICT/SMC implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class FairValueGapsAgent(ICTSMCAgent):
    """
    Specialized agent for Fair Value Gap detection and analysis
    Uses existing detect_ifvg() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("fair_value_gaps", config)
        
        # FVG-specific configuration
        self.window = config.get('window', 3)
        self.min_gap = config.get('min_gap', 0.0001)
        self.atr_distance_threshold = config.get('atr_distance_threshold', 2.0)
        
        # Active FVGs tracking
        self.active_fvgs = []
        self.filled_fvgs = []
        
        self.logger.info("Fair Value Gaps Agent initialized")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect Fair Value Gaps
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with FVG analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.window:
            return {'fvgs': [], 'signal_strength': 0.0}
        
        try:
            # Use existing detect_ifvg function
            fvgs = self.detect_ifvg(df, self.window, self.min_gap)
            
            # Analyze FVG strength and trading opportunities
            analysis_results = self.analyze_fvgs(fvgs, df, symbol)
            
            # Update active FVGs
            self.update_active_fvgs(fvgs, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_fvg_signal_strength(fvgs, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'fvgs': fvgs,
                'active_fvgs': self.active_fvgs,
                'filled_fvgs': self.filled_fvgs,
                'analysis': analysis_results,
                'signal_strength': signal_strength,
                'trading_opportunities': self.identify_trading_opportunities(fvgs, df)
            }
            
            # Publish FVG signals
            if fvgs:
                self.publish("fvg_detected", {
                    'symbol': symbol,
                    'fvgs': fvgs,
                    'signal_strength': signal_strength
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing FVG data for {symbol}: {e}")
            return {'fvgs': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_ifvg(self, df: pd.DataFrame, window: int = 3, min_gap: float = 0.0001) -> List[Dict[str, Any]]:
        """
        Detect Fair Value Gaps - Using existing optimized implementation
        """
        try:
            # Import the ICTSMCEngine from your existing code
            from ict_smc_enhancement import ICTSMCEngine
            
            # Use the optimized ICT/SMC engine for better detection
            ict_engine = ICTSMCEngine(df)
            optimized_fvgs = ict_engine.detect_fair_value_gaps(lookback=window)
            
            # Convert to the expected format for compatibility
            gaps = []
            for fvg in optimized_fvgs:
                if fvg['type'] in ['bullish', 'micro_bullish', 'volume_bullish_fvg']:
                    gaps.append({
                        'type': 'bullish',
                        'zone': (fvg['low'], fvg['high']),
                        'index': fvg['index'],
                        'size': fvg['size'],
                        'strength': fvg['strength'],
                        'timestamp': df.index[fvg['index']] if fvg['index'] < len(df) else None
                    })
                elif fvg['type'] in ['bearish', 'micro_bearish', 'volume_bearish_fvg']:
                    gaps.append({
                        'type': 'bearish',
                        'zone': (fvg['low'], fvg['high']),
                        'index': fvg['index'],
                        'size': fvg['size'],
                        'strength': fvg['strength'],
                        'timestamp': df.index[fvg['index']] if fvg['index'] < len(df) else None
                    })
            
            return gaps
            
        except ImportError:
            # Fallback to basic FVG detection if ICTSMCEngine not available
            return self.basic_fvg_detection(df, window, min_gap)
        except Exception as e:
            self.logger.error(f"Error in FVG detection: {e}")
            return []
    
    def basic_fvg_detection(self, df: pd.DataFrame, window: int = 3, min_gap: float = 0.0001) -> List[Dict[str, Any]]:
        """
        Basic Fair Value Gap detection (fallback implementation)
        """
        gaps = []
        
        for i in range(2, len(df)):
            # Check for bullish FVG
            if (df['low'].iloc[i] > df['high'].iloc[i-2] and 
                df['low'].iloc[i] - df['high'].iloc[i-2] > min_gap):
                
                gaps.append({
                    'type': 'bullish',
                    'zone': (df['high'].iloc[i-2], df['low'].iloc[i]),
                    'index': i,
                    'size': df['low'].iloc[i] - df['high'].iloc[i-2],
                    'strength': self.calculate_basic_fvg_strength(df, i, 'bullish'),
                    'timestamp': df.index[i] if i < len(df) else None
                })
            
            # Check for bearish FVG
            elif (df['high'].iloc[i] < df['low'].iloc[i-2] and 
                  df['low'].iloc[i-2] - df['high'].iloc[i] > min_gap):
                
                gaps.append({
                    'type': 'bearish',
                    'zone': (df['high'].iloc[i], df['low'].iloc[i-2]),
                    'index': i,
                    'size': df['low'].iloc[i-2] - df['high'].iloc[i],
                    'strength': self.calculate_basic_fvg_strength(df, i, 'bearish'),
                    'timestamp': df.index[i] if i < len(df) else None
                })
        
        return gaps
    
    def calculate_basic_fvg_strength(self, df: pd.DataFrame, index: int, fvg_type: str) -> float:
        """Calculate basic FVG strength"""
        try:
            # Volume strength
            volume_strength = df['volume'].iloc[index] / df['volume'].rolling(20).mean().iloc[index]
            
            # Size strength (relative to ATR)
            if 'atr' in df.columns:
                atr = df['atr'].iloc[index]
                if fvg_type == 'bullish':
                    size_strength = (df['low'].iloc[index] - df['high'].iloc[index-2]) / atr
                else:
                    size_strength = (df['low'].iloc[index-2] - df['high'].iloc[index]) / atr
            else:
                size_strength = 1.0
            
            # Combine strengths
            return min((volume_strength * 0.5 + size_strength * 0.5) / 2, 1.0)
            
        except Exception:
            return 0.5
    
    def analyze_fvgs(self, fvgs: List[Dict[str, Any]], df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze FVG patterns and characteristics
        """
        if not fvgs:
            return {'total_fvgs': 0, 'bullish_fvgs': 0, 'bearish_fvgs': 0}
        
        bullish_fvgs = [fvg for fvg in fvgs if fvg['type'] == 'bullish']
        bearish_fvgs = [fvg for fvg in fvgs if fvg['type'] == 'bearish']
        
        # Calculate average sizes
        avg_bullish_size = np.mean([fvg['size'] for fvg in bullish_fvgs]) if bullish_fvgs else 0
        avg_bearish_size = np.mean([fvg['size'] for fvg in bearish_fvgs]) if bearish_fvgs else 0
        
        # Calculate average strengths
        avg_bullish_strength = np.mean([fvg['strength'] for fvg in bullish_fvgs]) if bullish_fvgs else 0
        avg_bearish_strength = np.mean([fvg['strength'] for fvg in bearish_fvgs]) if bearish_fvgs else 0
        
        return {
            'total_fvgs': len(fvgs),
            'bullish_fvgs': len(bullish_fvgs),
            'bearish_fvgs': len(bearish_fvgs),
            'avg_bullish_size': avg_bullish_size,
            'avg_bearish_size': avg_bearish_size,
            'avg_bullish_strength': avg_bullish_strength,
            'avg_bearish_strength': avg_bearish_strength,
            'fvg_bias': 'bullish' if len(bullish_fvgs) > len(bearish_fvgs) else 'bearish' if len(bearish_fvgs) > len(bullish_fvgs) else 'neutral'
        }
    
    def update_active_fvgs(self, new_fvgs: List[Dict[str, Any]], df: pd.DataFrame):
        """
        Update active FVGs and check for filled gaps
        """
        current_price = df['close'].iloc[-1]
        
        # Check if any active FVGs are filled
        still_active = []
        for fvg in self.active_fvgs:
            zone_low, zone_high = fvg['zone']
            
            # Check if FVG is filled (price has moved through the gap)
            if fvg['type'] == 'bullish' and current_price <= zone_low:
                # Bullish FVG filled (price moved down through gap)
                fvg['filled_at'] = current_price
                fvg['filled_time'] = datetime.now(timezone.utc)
                self.filled_fvgs.append(fvg)
                self.logger.info(f"Bullish FVG filled at {current_price}")
            elif fvg['type'] == 'bearish' and current_price >= zone_high:
                # Bearish FVG filled (price moved up through gap)
                fvg['filled_at'] = current_price
                fvg['filled_time'] = datetime.now(timezone.utc)
                self.filled_fvgs.append(fvg)
                self.logger.info(f"Bearish FVG filled at {current_price}")
            else:
                still_active.append(fvg)
        
        # Add new FVGs to active list
        for fvg in new_fvgs:
            if fvg not in still_active:
                fvg['detected_time'] = datetime.now(timezone.utc)
                still_active.append(fvg)
        
        self.active_fvgs = still_active
        
        # Limit active FVGs to prevent memory issues
        if len(self.active_fvgs) > 50:
            self.active_fvgs = self.active_fvgs[-50:]
    
    def identify_trading_opportunities(self, fvgs: List[Dict[str, Any]], df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify trading opportunities based on FVGs
        """
        opportunities = []
        current_price = df['close'].iloc[-1]
        
        if 'atr' not in df.columns:
            return opportunities
        
        current_atr = df['atr'].iloc[-1]
        
        for fvg in fvgs:
            zone_low, zone_high = fvg['zone']
            distance_to_zone = min(abs(current_price - zone_low), abs(current_price - zone_high))
            
            # Check if price is near the FVG
            if distance_to_zone <= self.atr_distance_threshold * current_atr:
                opportunity = {
                    'fvg_type': fvg['type'],
                    'zone': fvg['zone'],
                    'distance': distance_to_zone,
                    'strength': fvg['strength'],
                    'opportunity_type': 'retest' if distance_to_zone < 0.5 * current_atr else 'approach',
                    'recommended_action': self.get_fvg_recommendation(fvg, current_price, current_atr)
                }
                opportunities.append(opportunity)
        
        return opportunities
    
    def get_fvg_recommendation(self, fvg: Dict[str, Any], current_price: float, atr: float) -> str:
        """
        Get trading recommendation based on FVG analysis
        """
        zone_low, zone_high = fvg['zone']
        
        if fvg['type'] == 'bullish':
            if zone_low <= current_price <= zone_high:
                return f"LONG opportunity - Price in bullish FVG zone"
            elif current_price < zone_low:
                return f"LONG setup - Wait for price to reach FVG zone"
            else:
                return f"FVG above current price - Monitor for retest"
        
        else:  # bearish FVG
            if zone_low <= current_price <= zone_high:
                return f"SHORT opportunity - Price in bearish FVG zone"
            elif current_price > zone_high:
                return f"SHORT setup - Wait for price to reach FVG zone"
            else:
                return f"FVG below current price - Monitor for retest"
    
    def calculate_fvg_signal_strength(self, fvgs: List[Dict[str, Any]], df: pd.DataFrame) -> float:
        """
        Calculate overall FVG signal strength
        """
        if not fvgs:
            return 0.0
        
        # Weight factors
        strength_weights = []
        proximity_weights = []
        
        current_price = df['close'].iloc[-1]
        current_atr = df['atr'].iloc[-1] if 'atr' in df.columns else df['close'].iloc[-1] * 0.01
        
        for fvg in fvgs:
            # Individual FVG strength
            strength_weights.append(fvg['strength'])
            
            # Proximity to current price
            zone_low, zone_high = fvg['zone']
            distance = min(abs(current_price - zone_low), abs(current_price - zone_high))
            proximity_score = max(0, 1 - (distance / (self.atr_distance_threshold * current_atr)))
            proximity_weights.append(proximity_score)
        
        # Calculate weighted signal strength
        if strength_weights and proximity_weights:
            avg_strength = np.mean(strength_weights)
            avg_proximity = np.mean(proximity_weights)
            return (avg_strength * 0.6 + avg_proximity * 0.4)
        
        return 0.0
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_fvg_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive FVG summary
        """
        return {
            'agent_id': self.agent_id,
            'active_fvgs_count': len(self.active_fvgs),
            'filled_fvgs_count': len(self.filled_fvgs),
            'active_bullish_fvgs': len([fvg for fvg in self.active_fvgs if fvg['type'] == 'bullish']),
            'active_bearish_fvgs': len([fvg for fvg in self.active_fvgs if fvg['type'] == 'bearish']),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'window': self.window,
                'min_gap': self.min_gap,
                'atr_distance_threshold': self.atr_distance_threshold
            }
        }
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "price_update":
            # Update FVG status based on price changes
            symbol = message['data']['symbol']
            price_data = message['data']
            
            self.logger.debug(f"Received price update for {symbol}: {price_data}")
            
            # Check if any FVGs need to be updated
            if hasattr(self, 'active_fvgs'):
                self.check_fvg_fills(price_data)
        
        elif topic == "market_structure_update":
            # React to market structure changes
            self.logger.debug("Received market structure update")
        
        super().on_message(topic, message)
    
    def check_fvg_fills(self, price_data: Dict[str, Any]):
        """
        Check if any active FVGs have been filled by recent price action
        """
        if 'close' not in price_data:
            return
        
        current_price = price_data['close']
        
        # Check active FVGs for fills
        filled_count = 0
        for fvg in self.active_fvgs[:]:  # Copy list to avoid modification during iteration
            zone_low, zone_high = fvg['zone']
            
            if fvg['type'] == 'bullish' and current_price <= zone_low:
                self.mark_fvg_filled(fvg, current_price)
                filled_count += 1
            elif fvg['type'] == 'bearish' and current_price >= zone_high:
                self.mark_fvg_filled(fvg, current_price)
                filled_count += 1
        
        if filled_count > 0:
            self.logger.info(f"Marked {filled_count} FVGs as filled")
    
    def mark_fvg_filled(self, fvg: Dict[str, Any], fill_price: float):
        """
        Mark an FVG as filled and move it to filled list
        """
        fvg['filled_at'] = fill_price
        fvg['filled_time'] = datetime.now(timezone.utc)
        
        # Remove from active and add to filled
        if fvg in self.active_fvgs:
            self.active_fvgs.remove(fvg)
        self.filled_fvgs.append(fvg)
        
        # Publish fill event
        self.publish("fvg_filled", {
            'fvg': fvg,
            'fill_price': fill_price
        })
    
    def get_near_fvgs(self, price: float, atr: float) -> List[Dict[str, Any]]:
        """
        Get FVGs near the specified price
        """
        near_fvgs = []
        
        for fvg in self.active_fvgs:
            zone_low, zone_high = fvg['zone']
            distance = min(abs(price - zone_low), abs(price - zone_high))
            
            if distance <= self.atr_distance_threshold * atr:
                fvg_copy = fvg.copy()
                fvg_copy['distance_to_price'] = distance
                near_fvgs.append(fvg_copy)
        
        # Sort by distance (closest first)
        near_fvgs.sort(key=lambda x: x['distance_to_price'])
        return near_fvgs
    
    def requires_continuous_processing(self) -> bool:
        """FVG agent doesn't need continuous background processing"""
        return False