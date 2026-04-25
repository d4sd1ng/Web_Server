"""
Market Structure Agent
Analyzes market structure shifts, BOS, CHOCH, and higher highs/lower lows
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class MarketStructureAgent(ICTSMCAgent):
    """
    Specialized agent for Market Structure analysis
    Uses existing detect_mss(), BOS/CHOCH functions from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("market_structure", config)
        
        # Market Structure specific configuration
        self.lookback = config.get('lookback', 20)
        self.confirmation_bars = config.get('confirmation_bars', 3)
        
        # Market structure state
        self.current_trend = 'neutral'
        self.structure_breaks = []
        self.character_changes = []
        self.swing_points = {'highs': [], 'lows': []}
        
        self.logger.info("Market Structure Agent initialized")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to analyze market structure
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with market structure analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback:
            return {'market_structure': 'insufficient_data', 'signal_strength': 0.0}
        
        try:
            # Detect Market Structure Shifts
            mss_results = self.detect_mss(df)
            
            # Detect Break of Structure
            bos_results = self.detect_bos(df)
            
            # Detect Change of Character
            choch_results = self.detect_choch(df)
            
            # Identify swing points
            swing_points = self.identify_swing_points(df)
            
            # Determine current market structure
            current_structure = self.determine_market_structure(df, mss_results, bos_results)
            
            # Calculate signal strength
            signal_strength = self.calculate_structure_signal_strength(
                mss_results, bos_results, choch_results, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'market_structure_shifts': mss_results,
                'break_of_structure': bos_results,
                'change_of_character': choch_results,
                'swing_points': swing_points,
                'current_structure': current_structure,
                'current_trend': self.current_trend,
                'signal_strength': signal_strength,
                'trading_bias': self.get_trading_bias(current_structure, mss_results, bos_results)
            }
            
            # Publish market structure updates
            if mss_results['bullish_mss'] or mss_results['bearish_mss']:
                self.publish("market_structure_shift", {
                    'symbol': symbol,
                    'mss_results': mss_results,
                    'new_structure': current_structure
                })
            
            if bos_results['bos_bull'] or bos_results['bos_bear']:
                self.publish("break_of_structure", {
                    'symbol': symbol,
                    'bos_results': bos_results,
                    'signal_strength': signal_strength
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing market structure data for {symbol}: {e}")
            return {'market_structure': 'error', 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_mss(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Market Structure Shifts - Using existing optimized implementation
        """
        try:
            # Import and use existing MSS detection
            from ict_smc_enhancement import ICTSMCEngine
            
            # Use the optimized ICT/SMC engine
            ict_engine = ICTSMCEngine(df)
            optimized_mss = ict_engine.detect_market_structure_shifts(lookback=self.lookback)
            
            # Check if the last candle has any MSS events
            bullish_mss = False
            bearish_mss = False
            mss_details = []
            
            for mss in optimized_mss:
                mss_details.append({
                    'type': mss['type'],
                    'index': mss['index'],
                    'strength': mss.get('strength', 0),
                    'timestamp': df.index[mss['index']] if mss['index'] < len(df) else None
                })
                
                if mss['index'] == len(df) - 1:  # Last candle
                    if 'bullish' in mss['type']:
                        bullish_mss = True
                    elif 'bearish' in mss['type']:
                        bearish_mss = True
            
            return {
                'bullish_mss': bullish_mss,
                'bearish_mss': bearish_mss,
                'mss_details': mss_details,
                'total_mss_events': len(mss_details)
            }
            
        except ImportError:
            # Fallback to basic MSS detection
            return self.basic_mss_detection(df)
        except Exception as e:
            self.logger.error(f"Error in MSS detection: {e}")
            return {'bullish_mss': False, 'bearish_mss': False, 'mss_details': []}
    
    def basic_mss_detection(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Basic Market Structure Shift detection (fallback)
        """
        if len(df) < 4:
            return {'bullish_mss': False, 'bearish_mss': False, 'mss_details': []}
        
        # Simple MSS logic from your existing code
        bullish_mss = ((df['low'].iloc[-1] > df['low'].iloc[-2]) and 
                       (df['low'].iloc[-2] < df['low'].iloc[-3]))
        
        bearish_mss = ((df['high'].iloc[-1] < df['high'].iloc[-2]) and 
                       (df['high'].iloc[-2] > df['high'].iloc[-3]))
        
        mss_details = []
        if bullish_mss:
            mss_details.append({
                'type': 'bullish_mss',
                'index': len(df) - 1,
                'strength': 0.7,
                'timestamp': df.index[-1]
            })
        
        if bearish_mss:
            mss_details.append({
                'type': 'bearish_mss',
                'index': len(df) - 1,
                'strength': 0.7,
                'timestamp': df.index[-1]
            })
        
        return {
            'bullish_mss': bullish_mss,
            'bearish_mss': bearish_mss,
            'mss_details': mss_details,
            'total_mss_events': len(mss_details)
        }
    
    def detect_bos(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Break of Structure using existing logic
        """
        if len(df) < 3:
            return {'bos_bull': False, 'bos_bear': False, 'bos_details': []}
        
        # Use existing BOS logic from your trading bot
        higher_high = df['high'].iloc[-1] > df['high'].iloc[-2]
        lower_low = df['low'].iloc[-1] < df['low'].iloc[-2]
        
        bos_bull = higher_high and (df['close'].iloc[-1] > df['high'].iloc[-2])
        bos_bear = lower_low and (df['close'].iloc[-1] < df['low'].iloc[-2])
        
        bos_details = []
        if bos_bull:
            bos_details.append({
                'type': 'bullish_bos',
                'index': len(df) - 1,
                'previous_high': df['high'].iloc[-2],
                'new_high': df['high'].iloc[-1],
                'break_confirmation': df['close'].iloc[-1] > df['high'].iloc[-2],
                'timestamp': df.index[-1]
            })
        
        if bos_bear:
            bos_details.append({
                'type': 'bearish_bos',
                'index': len(df) - 1,
                'previous_low': df['low'].iloc[-2],
                'new_low': df['low'].iloc[-1],
                'break_confirmation': df['close'].iloc[-1] < df['low'].iloc[-2],
                'timestamp': df.index[-1]
            })
        
        return {
            'bos_bull': bos_bull,
            'bos_bear': bos_bear,
            'bos_details': bos_details,
            'higher_high': higher_high,
            'lower_low': lower_low
        }
    
    def detect_choch(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect Change of Character (CHOCH)
        """
        if len(df) < 5:
            return {'choch_bull': False, 'choch_bear': False, 'choch_details': []}
        
        # CHOCH detection logic
        choch_bull = False
        choch_bear = False
        choch_details = []
        
        # Look for trend change patterns
        recent_highs = df['high'].iloc[-5:].tolist()
        recent_lows = df['low'].iloc[-5:].tolist()
        
        # Bullish CHOCH: Series of lower lows followed by higher high
        if (len(recent_lows) >= 3 and 
            recent_lows[-1] > recent_lows[-2] and 
            recent_lows[-2] < recent_lows[-3]):
            choch_bull = True
            choch_details.append({
                'type': 'bullish_choch',
                'index': len(df) - 1,
                'pattern': 'lower_lows_to_higher_low',
                'timestamp': df.index[-1]
            })
        
        # Bearish CHOCH: Series of higher highs followed by lower high
        if (len(recent_highs) >= 3 and 
            recent_highs[-1] < recent_highs[-2] and 
            recent_highs[-2] > recent_highs[-3]):
            choch_bear = True
            choch_details.append({
                'type': 'bearish_choch',
                'index': len(df) - 1,
                'pattern': 'higher_highs_to_lower_high',
                'timestamp': df.index[-1]
            })
        
        return {
            'choch_bull': choch_bull,
            'choch_bear': choch_bear,
            'choch_details': choch_details
        }
    
    def identify_swing_points(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify swing highs and swing lows
        """
        highs = []
        lows = []
        
        # Simple swing point identification
        for i in range(2, len(df) - 2):
            # Swing high: higher than surrounding bars
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i+1] and
                df['high'].iloc[i] > df['high'].iloc[i-2] and 
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                
                highs.append({
                    'price': df['high'].iloc[i],
                    'index': i,
                    'timestamp': df.index[i],
                    'type': 'swing_high'
                })
            
            # Swing low: lower than surrounding bars
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i+1] and
                df['low'].iloc[i] < df['low'].iloc[i-2] and 
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                
                lows.append({
                    'price': df['low'].iloc[i],
                    'index': i,
                    'timestamp': df.index[i],
                    'type': 'swing_low'
                })
        
        return {'highs': highs, 'lows': lows}
    
    def determine_market_structure(self, df: pd.DataFrame, mss_results: Dict[str, Any], bos_results: Dict[str, Any]) -> str:
        """
        Determine current market structure
        """
        # Analyze recent price action
        if len(df) < 10:
            return 'insufficient_data'
        
        recent_highs = df['high'].iloc[-10:]
        recent_lows = df['low'].iloc[-10:]
        
        # Check for trending patterns
        if (recent_highs.iloc[-1] > recent_highs.iloc[-5] and 
            recent_lows.iloc[-1] > recent_lows.iloc[-5]):
            structure = 'uptrend'
        elif (recent_highs.iloc[-1] < recent_highs.iloc[-5] and 
              recent_lows.iloc[-1] < recent_lows.iloc[-5]):
            structure = 'downtrend'
        else:
            structure = 'sideways'
        
        # Factor in MSS and BOS
        if mss_results['bullish_mss'] or bos_results['bos_bull']:
            structure = 'bullish_structure_break'
        elif mss_results['bearish_mss'] or bos_results['bos_bear']:
            structure = 'bearish_structure_break'
        
        # Update current trend
        self.current_trend = structure
        
        return structure
    
    def calculate_structure_signal_strength(self, mss_results: Dict[str, Any], 
                                          bos_results: Dict[str, Any], 
                                          choch_results: Dict[str, Any], 
                                          df: pd.DataFrame) -> float:
        """
        Calculate overall market structure signal strength
        """
        strength_factors = []
        
        # MSS strength
        if mss_results['bullish_mss'] or mss_results['bearish_mss']:
            mss_strength = 0.8
            if mss_results['mss_details']:
                avg_mss_strength = np.mean([mss['strength'] for mss in mss_results['mss_details']])
                mss_strength = avg_mss_strength
            strength_factors.append(mss_strength)
        
        # BOS strength
        if bos_results['bos_bull'] or bos_results['bos_bear']:
            bos_strength = 0.7
            # Add volume confirmation
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
                bos_strength *= (0.7 + volume_factor * 0.3)
            strength_factors.append(bos_strength)
        
        # CHOCH strength
        if choch_results['choch_bull'] or choch_results['choch_bear']:
            choch_strength = 0.6  # CHOCH is typically weaker than MSS/BOS
            strength_factors.append(choch_strength)
        
        # Trend consistency
        if len(df) >= 20:
            trend_consistency = self.calculate_trend_consistency(df)
            strength_factors.append(trend_consistency * 0.5)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def calculate_trend_consistency(self, df: pd.DataFrame) -> float:
        """
        Calculate trend consistency over recent periods
        """
        if len(df) < 20:
            return 0.5
        
        # Analyze last 20 bars for trend consistency
        recent_data = df.iloc[-20:]
        
        # Count higher highs and higher lows (bullish trend)
        higher_highs = sum(1 for i in range(1, len(recent_data)) 
                          if recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1])
        higher_lows = sum(1 for i in range(1, len(recent_data)) 
                         if recent_data['low'].iloc[i] > recent_data['low'].iloc[i-1])
        
        # Count lower highs and lower lows (bearish trend)
        lower_highs = sum(1 for i in range(1, len(recent_data)) 
                         if recent_data['high'].iloc[i] < recent_data['high'].iloc[i-1])
        lower_lows = sum(1 for i in range(1, len(recent_data)) 
                        if recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1])
        
        # Calculate consistency scores
        bullish_consistency = (higher_highs + higher_lows) / (2 * (len(recent_data) - 1))
        bearish_consistency = (lower_highs + lower_lows) / (2 * (len(recent_data) - 1))
        
        return max(bullish_consistency, bearish_consistency)
    
    def get_trading_bias(self, current_structure: str, mss_results: Dict[str, Any], bos_results: Dict[str, Any]) -> str:
        """
        Determine trading bias based on market structure
        """
        # Strong bullish bias
        if (current_structure in ['uptrend', 'bullish_structure_break'] or
            mss_results['bullish_mss'] or 
            bos_results['bos_bull']):
            return 'bullish'
        
        # Strong bearish bias
        elif (current_structure in ['downtrend', 'bearish_structure_break'] or
              mss_results['bearish_mss'] or 
              bos_results['bos_bear']):
            return 'bearish'
        
        # Neutral/sideways
        else:
            return 'neutral'
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_market_structure_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive market structure summary
        """
        return {
            'agent_id': self.agent_id,
            'current_trend': self.current_trend,
            'structure_breaks_count': len(self.structure_breaks),
            'character_changes_count': len(self.character_changes),
            'swing_highs_count': len(self.swing_points['highs']),
            'swing_lows_count': len(self.swing_points['lows']),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'confirmation_bars': self.confirmation_bars
            }
        }
    
    def is_bullish_structure(self) -> bool:
        """Check if current structure is bullish"""
        return self.current_trend in ['uptrend', 'bullish_structure_break']
    
    def is_bearish_structure(self) -> bool:
        """Check if current structure is bearish"""
        return self.current_trend in ['downtrend', 'bearish_structure_break']
    
    def is_sideways_structure(self) -> bool:
        """Check if current structure is sideways"""
        return self.current_trend in ['sideways', 'neutral']
    
    def get_recent_swing_high(self) -> Dict[str, Any]:
        """Get most recent swing high"""
        if self.swing_points['highs']:
            return max(self.swing_points['highs'], key=lambda x: x['index'])
        return None
    
    def get_recent_swing_low(self) -> Dict[str, Any]:
        """Get most recent swing low"""
        if self.swing_points['lows']:
            return max(self.swing_points['lows'], key=lambda x: x['index'])
        return None
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "price_update":
            # Update market structure based on price changes
            symbol = message['data']['symbol']
            price_data = message['data']
            
            self.logger.debug(f"Received price update for {symbol}: {price_data}")
            # Could trigger structure validation updates here
        
        elif topic == "volume_spike":
            # Volume spikes can confirm structure breaks
            self.logger.debug("Received volume spike notification")
        
        super().on_message(topic, message)
    
    def requires_continuous_processing(self) -> bool:
        """Market Structure agent doesn't need continuous background processing"""
        return False