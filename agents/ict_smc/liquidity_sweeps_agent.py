"""
Liquidity Sweeps Agent
Detects liquidity sweeps, equal highs/lows, and liquidity grabs
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class LiquiditySweepsAgent(ICTSMCAgent):
    """
    Specialized agent for Liquidity Sweep detection
    Uses existing detect_swing_sweep() and liquidity grab functions
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("liquidity_sweeps", config)
        
        # Liquidity sweep configuration
        self.lookback = config.get('lookback', 10)
        self.equal_level_tolerance = config.get('equal_level_tolerance', 0.001)
        self.volume_threshold = config.get('volume_threshold', 1.5)
        
        # Liquidity tracking
        self.recent_sweeps = []
        self.liquidity_levels = {'highs': [], 'lows': []}
        self.grab_history = []
        
        self.logger.info("Liquidity Sweeps Agent initialized")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect liquidity sweeps
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with liquidity sweep analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback:
            return {'sweeps': [], 'signal_strength': 0.0}
        
        try:
            # Detect swing sweeps using existing function
            swing_sweeps = self.detect_swing_sweep(df, self.lookback)
            
            # Detect internal liquidity grabs
            internal_grabs = self.detect_internal_liquidity_grab(df, self.lookback)
            
            # Detect session-based liquidity grabs
            session_grabs = self.detect_session_liquidity_grabs(df)
            
            # Identify equal highs/lows
            equal_levels = self.identify_equal_levels(df)
            
            # Calculate signal strength
            signal_strength = self.calculate_liquidity_signal_strength(
                swing_sweeps, internal_grabs, session_grabs, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'swing_sweeps': swing_sweeps,
                'internal_grabs': internal_grabs,
                'session_grabs': session_grabs,
                'equal_levels': equal_levels,
                'signal_strength': signal_strength,
                'liquidity_analysis': self.analyze_liquidity_patterns(
                    swing_sweeps, internal_grabs, session_grabs, df
                ),
                'trading_opportunities': self.identify_liquidity_opportunities(
                    swing_sweeps, internal_grabs, df
                )
            }
            
            # Publish liquidity sweep signals
            if swing_sweeps['swept_high'] or swing_sweeps['swept_low']:
                self.publish("liquidity_sweep", {
                    'symbol': symbol,
                    'sweep_type': 'high' if swing_sweeps['swept_high'] else 'low',
                    'signal_strength': signal_strength
                })
            
            if internal_grabs['internal_buy_grab'] or internal_grabs['internal_sell_grab']:
                self.publish("internal_liquidity_grab", {
                    'symbol': symbol,
                    'grab_type': 'buy' if internal_grabs['internal_buy_grab'] else 'sell',
                    'signal_strength': signal_strength
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing liquidity sweep data for {symbol}: {e}")
            return {'sweeps': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_swing_sweep(self, df: pd.DataFrame, lookback: int = 10) -> Dict[str, Any]:
        """
        Detect swing sweeps using existing optimized implementation
        """
        try:
            # Import and use existing swing sweep detection
            from ict_smc_enhancement import ICTSMCEngine
            
            # Use the optimized ICT/SMC engine
            ict_engine = ICTSMCEngine(df)
            optimized_sweeps = ict_engine.detect_liquidity_sweeps(lookback=lookback)
            
            # Check if the last candle has any sweep events
            swept_high = False
            swept_low = False
            sweep_details = []
            
            for sweep in optimized_sweeps:
                sweep_details.append({
                    'type': sweep['type'],
                    'index': sweep['index'],
                    'strength': sweep.get('strength', 0),
                    'timestamp': df.index[sweep['index']] if sweep['index'] < len(df) else None
                })
                
                if sweep['index'] == len(df) - 1:  # Last candle
                    if 'bullish' in sweep['type'] or 'high' in sweep['type']:
                        swept_high = True
                    elif 'bearish' in sweep['type'] or 'low' in sweep['type']:
                        swept_low = True
            
            return {
                'swept_high': swept_high,
                'swept_low': swept_low,
                'sweep_details': sweep_details,
                'total_sweeps': len(sweep_details)
            }
            
        except ImportError:
            # Fallback to basic swing sweep detection
            return self.basic_swing_sweep_detection(df, lookback)
        except Exception as e:
            self.logger.error(f"Error in swing sweep detection: {e}")
            return {'swept_high': False, 'swept_low': False, 'sweep_details': []}
    
    def basic_swing_sweep_detection(self, df: pd.DataFrame, lookback: int = 10) -> Dict[str, Any]:
        """
        Basic swing sweep detection (fallback)
        """
        if len(df) < lookback + 1:
            return {'swept_high': False, 'swept_low': False, 'sweep_details': []}
        
        # Get recent swing points
        recent_highs = df['high'].iloc[-lookback-1:-1]
        recent_lows = df['low'].iloc[-lookback-1:-1]
        
        last_high = df['high'].iloc[-1]
        last_low = df['low'].iloc[-1]
        
        # Check for swing high sweep
        max_recent_high = recent_highs.max()
        swept_high = last_high > max_recent_high
        
        # Check for swing low sweep
        min_recent_low = recent_lows.min()
        swept_low = last_low < min_recent_low
        
        sweep_details = []
        if swept_high:
            sweep_details.append({
                'type': 'swing_high_sweep',
                'index': len(df) - 1,
                'swept_level': max_recent_high,
                'new_level': last_high,
                'strength': 0.7,
                'timestamp': df.index[-1]
            })
        
        if swept_low:
            sweep_details.append({
                'type': 'swing_low_sweep',
                'index': len(df) - 1,
                'swept_level': min_recent_low,
                'new_level': last_low,
                'strength': 0.7,
                'timestamp': df.index[-1]
            })
        
        return {
            'swept_high': swept_high,
            'swept_low': swept_low,
            'sweep_details': sweep_details,
            'total_sweeps': len(sweep_details)
        }
    
    def detect_internal_liquidity_grab(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
        """
        Detect internal liquidity grabs using existing implementation
        """
        if len(df) < lookback + 1:
            return {'internal_buy_grab': False, 'internal_sell_grab': False}
        
        # Use existing internal liquidity grab detection logic
        prev_highs = df['high'].iloc[-(lookback+1):-1]
        prev_lows = df['low'].iloc[-(lookback+1):-1]
        last_high = df['high'].iloc[-1]
        last_low = df['low'].iloc[-1]
        
        max_high = prev_highs.max()
        min_low = prev_lows.min()
        
        # Internal buy grab: sweep a swing high, but not the absolute high
        internal_buy_grab = (last_high > max_high and 
                            last_high < df['high'].iloc[-(lookback+1):].max())
        
        # Internal sell grab: sweep a swing low, but not the absolute low
        internal_sell_grab = (last_low < min_low and 
                             last_low > df['low'].iloc[-(lookback+1):].min())
        
        grab_details = []
        if internal_buy_grab:
            grab_details.append({
                'type': 'internal_buy_grab',
                'index': len(df) - 1,
                'grabbed_level': max_high,
                'new_level': last_high,
                'timestamp': df.index[-1]
            })
        
        if internal_sell_grab:
            grab_details.append({
                'type': 'internal_sell_grab',
                'index': len(df) - 1,
                'grabbed_level': min_low,
                'new_level': last_low,
                'timestamp': df.index[-1]
            })
        
        return {
            'internal_buy_grab': internal_buy_grab,
            'internal_sell_grab': internal_sell_grab,
            'grab_details': grab_details
        }
    
    def detect_session_liquidity_grabs(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect session-based liquidity grabs
        """
        session_grabs = {}
        
        try:
            # London session grab (3:00-8:00 UTC)
            london_grab = self.detect_liquidity_grab(df, '03:00', '08:00')
            session_grabs['london'] = london_grab
            
            # New York session grab (8:00-12:00 UTC)
            ny_grab = self.detect_liquidity_grab(df, '08:00', '12:00')
            session_grabs['new_york'] = ny_grab
            
            # Asian session grab (22:00-02:00 UTC)
            asian_grab = self.detect_liquidity_grab(df, '22:00', '02:00')
            session_grabs['asian'] = asian_grab
            
        except Exception as e:
            self.logger.warning(f"Error detecting session liquidity grabs: {e}")
        
        return session_grabs
    
    def detect_liquidity_grab(self, df: pd.DataFrame, session_start: str, session_end: str, direction: str = 'both') -> str:
        """
        Detect liquidity grab for specific session using existing logic
        """
        try:
            # Filter data for session (simplified - assumes UTC timestamps)
            if hasattr(df.index, 'time'):
                session_df = df.between_time(session_start, session_end)
                
                if len(session_df) == 0:
                    return None
                
                # Get data before session
                pre_session_df = df[df.index < session_df.index[0]]
                
                if len(pre_session_df) == 0:
                    return None
                
                if direction in ['buy', 'both']:
                    # Check if session high exceeds previous highs
                    session_high = session_df['high'].max()
                    pre_session_high = pre_session_df['high'].max()
                    
                    if session_high > pre_session_high:
                        return 'buy'
                
                if direction in ['sell', 'both']:
                    # Check if session low breaks previous lows
                    session_low = session_df['low'].min()
                    pre_session_low = pre_session_df['low'].min()
                    
                    if session_low < pre_session_low:
                        return 'sell'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error in session liquidity grab detection: {e}")
            return None
    
    def identify_equal_levels(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify equal highs and equal lows that could be liquidity targets
        """
        equal_highs = []
        equal_lows = []
        
        if len(df) < 10:
            return {'equal_highs': equal_highs, 'equal_lows': equal_lows}
        
        # Find equal highs
        for i in range(5, len(df) - 5):
            current_high = df['high'].iloc[i]
            
            # Look for similar highs in surrounding area
            nearby_highs = df['high'].iloc[i-5:i+5]
            equal_high_count = sum(1 for h in nearby_highs 
                                  if abs(h - current_high) / current_high <= self.equal_level_tolerance)
            
            if equal_high_count >= 3:  # At least 3 similar highs
                equal_highs.append({
                    'level': current_high,
                    'index': i,
                    'count': equal_high_count,
                    'timestamp': df.index[i],
                    'type': 'equal_high'
                })
        
        # Find equal lows
        for i in range(5, len(df) - 5):
            current_low = df['low'].iloc[i]
            
            # Look for similar lows in surrounding area
            nearby_lows = df['low'].iloc[i-5:i+5]
            equal_low_count = sum(1 for l in nearby_lows 
                                 if abs(l - current_low) / current_low <= self.equal_level_tolerance)
            
            if equal_low_count >= 3:  # At least 3 similar lows
                equal_lows.append({
                    'level': current_low,
                    'index': i,
                    'count': equal_low_count,
                    'timestamp': df.index[i],
                    'type': 'equal_low'
                })
        
        return {'equal_highs': equal_highs, 'equal_lows': equal_lows}
    
    def analyze_liquidity_patterns(self, swing_sweeps: Dict[str, Any], 
                                 internal_grabs: Dict[str, Any], 
                                 session_grabs: Dict[str, Any], 
                                 df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze liquidity patterns and market behavior
        """
        analysis = {
            'sweep_frequency': 0,
            'grab_frequency': 0,
            'dominant_liquidity_direction': 'neutral',
            'liquidity_efficiency': 0.5
        }
        
        # Count recent liquidity events
        total_events = 0
        bullish_events = 0
        bearish_events = 0
        
        # Swing sweep events
        if swing_sweeps['swept_high']:
            total_events += 1
            bullish_events += 1
        if swing_sweeps['swept_low']:
            total_events += 1
            bearish_events += 1
        
        # Internal grab events
        if internal_grabs['internal_buy_grab']:
            total_events += 1
            bullish_events += 1
        if internal_grabs['internal_sell_grab']:
            total_events += 1
            bearish_events += 1
        
        # Session grab events
        for session, grab_type in session_grabs.items():
            if grab_type == 'buy':
                total_events += 1
                bullish_events += 1
            elif grab_type == 'sell':
                total_events += 1
                bearish_events += 1
        
        # Calculate frequencies and patterns
        if total_events > 0:
            analysis['sweep_frequency'] = total_events / len(df) * 100  # Per 100 bars
            
            if bullish_events > bearish_events:
                analysis['dominant_liquidity_direction'] = 'bullish'
            elif bearish_events > bullish_events:
                analysis['dominant_liquidity_direction'] = 'bearish'
            
            # Liquidity efficiency (how often sweeps lead to continuation)
            analysis['liquidity_efficiency'] = self.calculate_liquidity_efficiency(df)
        
        return analysis
    
    def calculate_liquidity_efficiency(self, df: pd.DataFrame) -> float:
        """
        Calculate how efficiently liquidity sweeps predict price movement
        """
        if len(df) < 20:
            return 0.5
        
        # Simple efficiency calculation based on recent price action
        # This could be enhanced with more sophisticated analysis
        
        recent_volume = df['volume'].iloc[-10:].mean()
        avg_volume = df['volume'].mean()
        volume_efficiency = min(recent_volume / avg_volume, 2.0) / 2.0
        
        # Price momentum after sweeps
        price_momentum = abs(df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        momentum_efficiency = min(price_momentum * 10, 1.0)  # Scale to 0-1
        
        return (volume_efficiency * 0.6 + momentum_efficiency * 0.4)
    
    def identify_liquidity_opportunities(self, swing_sweeps: Dict[str, Any], 
                                       internal_grabs: Dict[str, Any], 
                                       df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify trading opportunities based on liquidity analysis
        """
        opportunities = []
        current_price = df['close'].iloc[-1]
        
        # Swing sweep opportunities
        if swing_sweeps['swept_high']:
            opportunities.append({
                'type': 'swing_high_sweep',
                'direction': 'reversal_short',
                'reason': 'High swept - expect reversal or continuation down',
                'strength': 0.7,
                'entry_bias': 'short'
            })
        
        if swing_sweeps['swept_low']:
            opportunities.append({
                'type': 'swing_low_sweep',
                'direction': 'reversal_long',
                'reason': 'Low swept - expect reversal or continuation up',
                'strength': 0.7,
                'entry_bias': 'long'
            })
        
        # Internal grab opportunities
        if internal_grabs['internal_buy_grab']:
            opportunities.append({
                'type': 'internal_buy_grab',
                'direction': 'continuation_long',
                'reason': 'Internal buy liquidity grabbed - expect continuation up',
                'strength': 0.6,
                'entry_bias': 'long'
            })
        
        if internal_grabs['internal_sell_grab']:
            opportunities.append({
                'type': 'internal_sell_grab',
                'direction': 'continuation_short',
                'reason': 'Internal sell liquidity grabbed - expect continuation down',
                'strength': 0.6,
                'entry_bias': 'short'
            })
        
        return opportunities
    
    def calculate_liquidity_signal_strength(self, swing_sweeps: Dict[str, Any], 
                                          internal_grabs: Dict[str, Any], 
                                          session_grabs: Dict[str, Any], 
                                          df: pd.DataFrame) -> float:
        """
        Calculate overall liquidity signal strength
        """
        strength_factors = []
        
        # Swing sweep strength
        if swing_sweeps['swept_high'] or swing_sweeps['swept_low']:
            sweep_strength = 0.8
            # Add volume confirmation
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
                sweep_strength *= (0.7 + volume_factor * 0.3)
            strength_factors.append(sweep_strength)
        
        # Internal grab strength
        if internal_grabs['internal_buy_grab'] or internal_grabs['internal_sell_grab']:
            grab_strength = 0.6
            strength_factors.append(grab_strength)
        
        # Session grab strength
        session_grab_count = sum(1 for grab in session_grabs.values() if grab in ['buy', 'sell'])
        if session_grab_count > 0:
            session_strength = min(session_grab_count * 0.3, 0.7)
            strength_factors.append(session_strength)
        
        # Multiple liquidity event bonus
        total_events = (
            (1 if swing_sweeps['swept_high'] or swing_sweeps['swept_low'] else 0) +
            (1 if internal_grabs['internal_buy_grab'] or internal_grabs['internal_sell_grab'] else 0) +
            session_grab_count
        )
        
        if total_events > 1:
            confluence_bonus = min(total_events * 0.2, 0.4)
            strength_factors.append(confluence_bonus)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_liquidity_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive liquidity summary
        """
        return {
            'agent_id': self.agent_id,
            'recent_sweeps_count': len(self.recent_sweeps),
            'grab_history_count': len(self.grab_history),
            'equal_highs_count': len(self.liquidity_levels['highs']),
            'equal_lows_count': len(self.liquidity_levels['lows']),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'equal_level_tolerance': self.equal_level_tolerance,
                'volume_threshold': self.volume_threshold
            }
        }
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "price_update":
            # Monitor for new liquidity sweeps
            symbol = message['data']['symbol']
            price_data = message['data']
            
            self.logger.debug(f"Received price update for {symbol}: {price_data}")
            self.check_for_new_sweeps(price_data)
        
        elif topic == "volume_spike":
            # Volume spikes often accompany liquidity grabs
            self.logger.debug("Received volume spike - potential liquidity event")
        
        super().on_message(topic, message)
    
    def check_for_new_sweeps(self, price_data: Dict[str, Any]):
        """
        Check for new liquidity sweeps based on price updates
        """
        if 'high' not in price_data or 'low' not in price_data:
            return
        
        current_high = price_data['high']
        current_low = price_data['low']
        
        # Check against recent levels for potential sweeps
        for level in self.liquidity_levels['highs']:
            if current_high > level['level'] * (1 + self.equal_level_tolerance):
                self.logger.info(f"Potential high sweep detected at {current_high}")
                self.recent_sweeps.append({
                    'type': 'high_sweep',
                    'level': level['level'],
                    'new_level': current_high,
                    'timestamp': datetime.now(timezone.utc)
                })
        
        for level in self.liquidity_levels['lows']:
            if current_low < level['level'] * (1 - self.equal_level_tolerance):
                self.logger.info(f"Potential low sweep detected at {current_low}")
                self.recent_sweeps.append({
                    'type': 'low_sweep',
                    'level': level['level'],
                    'new_level': current_low,
                    'timestamp': datetime.now(timezone.utc)
                })
        
        # Limit recent sweeps history
        if len(self.recent_sweeps) > 50:
            self.recent_sweeps = self.recent_sweeps[-50:]
    
    def requires_continuous_processing(self) -> bool:
        """Liquidity Sweeps agent doesn't need continuous background processing"""
        return False