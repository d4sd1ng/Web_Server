"""
Swing Failure Pattern (SFP) Agent
Detects swing failure patterns and false breakouts
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class SwingFailurePatternAgent(ICTSMCAgent):
    """
    Specialized agent for Swing Failure Pattern detection
    Identifies false breakouts and failed swing attempts
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("swing_failure_pattern", config)
        
        # SFP configuration
        self.lookback = config.get('lookback', 20)
        self.failure_threshold = config.get('failure_threshold', 0.002)  # 0.2% failure tolerance
        self.confirmation_bars = config.get('confirmation_bars', 3)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # SFP tracking
        self.sfp_events = []
        self.false_breakouts = []
        self.swing_levels = {'highs': [], 'lows': []}
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Swing Failure Pattern Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific configuration adjustments"""
        if self.market_type == 'forex':
            # Forex: Tighter failure thresholds due to lower volatility
            self.failure_threshold = max(self.failure_threshold, 0.003)  # 0.3% for forex
            self.session_weight = 0.9  # Session timing very important
            self.news_sensitivity = True
        elif self.market_type == 'crypto':
            # Crypto: Wider failure thresholds due to higher volatility
            self.failure_threshold = min(self.failure_threshold, 0.005)  # 0.5% for crypto
            self.session_weight = 0.4  # Less session dependency
            self.news_sensitivity = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect swing failure patterns
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with SFP analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback + 5:
            return {'sfp_detected': False, 'signal_strength': 0.0}
        
        try:
            # Detect swing failure patterns
            sfp_results = self.detect_swing_failure_patterns(df)
            
            # Detect false breakouts
            false_breakouts = self.detect_false_breakouts(df)
            
            # Identify key swing levels
            swing_levels = self.identify_key_swing_levels(df)
            
            # Analyze failure patterns
            failure_analysis = self.analyze_failure_patterns(sfp_results, false_breakouts, df)
            
            # Update tracking
            self.update_sfp_tracking(sfp_results, false_breakouts, swing_levels)
            
            # Calculate signal strength
            signal_strength = self.calculate_sfp_signal_strength(sfp_results, false_breakouts, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'sfp_results': sfp_results,
                'false_breakouts': false_breakouts,
                'swing_levels': swing_levels,
                'failure_analysis': failure_analysis,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'reversal_opportunities': self.identify_reversal_opportunities(
                    sfp_results, false_breakouts, df
                )
            }
            
            # Publish SFP signals
            if sfp_results['sfp_bullish'] or sfp_results['sfp_bearish']:
                self.publish("swing_failure_pattern", {
                    'symbol': symbol,
                    'sfp_results': sfp_results,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing SFP data for {symbol}: {e}")
            return {'sfp_detected': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_swing_failure_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect swing failure patterns
        """
        if len(df) < self.lookback + 5:
            return {'sfp_bullish': False, 'sfp_bearish': False, 'sfp_details': []}
        
        sfp_details = []
        sfp_bullish = False
        sfp_bearish = False
        
        # Look for swing failure patterns in recent data
        for i in range(len(df) - self.lookback, len(df) - self.confirmation_bars):
            # Bullish SFP: Failed to break above previous high
            recent_highs = df['high'].iloc[i-self.lookback:i]
            if len(recent_highs) > 0:
                resistance_level = recent_highs.max()
                current_high = df['high'].iloc[i]
                
                # Check for failure to break resistance
                if (current_high > resistance_level * (1 - self.failure_threshold) and
                    current_high < resistance_level * (1 + self.failure_threshold)):
                    
                    # Confirm failure with subsequent price action
                    if self.confirm_swing_failure(df, i, 'bullish', resistance_level):
                        sfp_details.append({
                            'type': 'bullish_sfp',
                            'index': i,
                            'failed_level': resistance_level,
                            'attempted_break': current_high,
                            'failure_confirmed': True,
                            'market_context': self.get_sfp_market_context(df, i, 'bullish')
                        })
                        
                        if i >= len(df) - self.confirmation_bars - 1:
                            sfp_bullish = True
            
            # Bearish SFP: Failed to break below previous low
            recent_lows = df['low'].iloc[i-self.lookback:i]
            if len(recent_lows) > 0:
                support_level = recent_lows.min()
                current_low = df['low'].iloc[i]
                
                # Check for failure to break support
                if (current_low < support_level * (1 + self.failure_threshold) and
                    current_low > support_level * (1 - self.failure_threshold)):
                    
                    # Confirm failure with subsequent price action
                    if self.confirm_swing_failure(df, i, 'bearish', support_level):
                        sfp_details.append({
                            'type': 'bearish_sfp',
                            'index': i,
                            'failed_level': support_level,
                            'attempted_break': current_low,
                            'failure_confirmed': True,
                            'market_context': self.get_sfp_market_context(df, i, 'bearish')
                        })
                        
                        if i >= len(df) - self.confirmation_bars - 1:
                            sfp_bearish = True
        
        return {
            'sfp_bullish': sfp_bullish,
            'sfp_bearish': sfp_bearish,
            'sfp_details': sfp_details,
            'total_sfp_events': len(sfp_details)
        }
    
    def confirm_swing_failure(self, df: pd.DataFrame, index: int, direction: str, level: float) -> bool:
        """Confirm swing failure with subsequent price action"""
        if index + self.confirmation_bars >= len(df):
            return False
        
        confirmation_data = df.iloc[index+1:index+self.confirmation_bars+1]
        
        if direction == 'bullish':
            # For bullish SFP, expect price to move away from resistance
            return confirmation_data['close'].iloc[-1] < level
        else:
            # For bearish SFP, expect price to move away from support
            return confirmation_data['close'].iloc[-1] > level
    
    def get_sfp_market_context(self, df: pd.DataFrame, index: int, direction: str) -> Dict[str, Any]:
        """Get market context for SFP"""
        context = {
            'market_type': self.market_type,
            'volume_context': 'normal',
            'session_context': 'unknown'
        }
        
        # Volume context
        if 'volume' in df.columns:
            failure_volume = df['volume'].iloc[index]
            avg_volume = df['volume'].rolling(20).mean().iloc[index]
            
            if failure_volume > 1.5 * avg_volume:
                context['volume_context'] = 'high_volume_failure'
            elif failure_volume < 0.7 * avg_volume:
                context['volume_context'] = 'low_volume_failure'
        
        # Session context (for forex)
        if self.market_type == 'forex' and hasattr(df.index[index], 'hour'):
            hour = df.index[index].hour
            if 13 <= hour <= 16:
                context['session_context'] = 'london_ny_overlap'
            elif 8 <= hour <= 22:
                context['session_context'] = 'major_session'
            else:
                context['session_context'] = 'asian_session'
        
        return context
    
    def detect_false_breakouts(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect false breakout patterns
        """
        false_breakouts = []
        
        if len(df) < 10:
            return false_breakouts
        
        # Look for false breakouts of recent highs/lows
        for i in range(5, len(df) - 3):
            # False breakout above resistance
            resistance = df['high'].iloc[i-5:i].max()
            if (df['high'].iloc[i] > resistance * (1 + self.failure_threshold) and
                df['close'].iloc[i] < resistance):
                
                # Confirm false breakout
                if self.confirm_false_breakout(df, i, 'resistance', resistance):
                    false_breakouts.append({
                        'type': 'false_breakout_resistance',
                        'index': i,
                        'level': resistance,
                        'failed_break': df['high'].iloc[i],
                        'close': df['close'].iloc[i],
                        'market_type': self.market_type
                    })
            
            # False breakout below support
            support = df['low'].iloc[i-5:i].min()
            if (df['low'].iloc[i] < support * (1 - self.failure_threshold) and
                df['close'].iloc[i] > support):
                
                # Confirm false breakout
                if self.confirm_false_breakout(df, i, 'support', support):
                    false_breakouts.append({
                        'type': 'false_breakout_support',
                        'index': i,
                        'level': support,
                        'failed_break': df['low'].iloc[i],
                        'close': df['close'].iloc[i],
                        'market_type': self.market_type
                    })
        
        return false_breakouts
    
    def confirm_false_breakout(self, df: pd.DataFrame, index: int, level_type: str, level: float) -> bool:
        """Confirm false breakout with subsequent price action"""
        if index + 3 >= len(df):
            return False
        
        confirmation_data = df.iloc[index+1:index+4]
        
        if level_type == 'resistance':
            # Confirm by staying below resistance
            return confirmation_data['high'].max() < level
        else:  # support
            # Confirm by staying above support
            return confirmation_data['low'].min() > level
    
    def identify_key_swing_levels(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """Identify key swing levels for failure analysis"""
        swing_highs = []
        swing_lows = []
        
        # Identify swing points
        for i in range(3, len(df) - 3):
            # Swing high
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and
                df['high'].iloc[i] > df['high'].iloc[i+1] and
                df['high'].iloc[i] > df['high'].iloc[i-2] and
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                
                swing_highs.append({
                    'level': df['high'].iloc[i],
                    'index': i,
                    'timestamp': df.index[i],
                    'strength': self.calculate_swing_strength(df, i, 'high'),
                    'market_type': self.market_type
                })
            
            # Swing low
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and
                df['low'].iloc[i] < df['low'].iloc[i+1] and
                df['low'].iloc[i] < df['low'].iloc[i-2] and
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                
                swing_lows.append({
                    'level': df['low'].iloc[i],
                    'index': i,
                    'timestamp': df.index[i],
                    'strength': self.calculate_swing_strength(df, i, 'low'),
                    'market_type': self.market_type
                })
        
        return {'highs': swing_highs, 'lows': swing_lows}
    
    def calculate_swing_strength(self, df: pd.DataFrame, index: int, swing_type: str) -> float:
        """Calculate swing point strength"""
        try:
            strength_factors = []
            
            # Volume strength
            if 'volume' in df.columns:
                swing_volume = df['volume'].iloc[index]
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                volume_strength = min(swing_volume / avg_volume, 2.0) / 2.0
                
                if self.market_type == 'crypto':
                    strength_factors.append(volume_strength * 0.8)
                else:
                    strength_factors.append(volume_strength * 0.4)
            
            # Price significance
            if swing_type == 'high':
                lookback_highs = df['high'].iloc[max(0, index-10):index+10]
                price_significance = (df['high'].iloc[index] - lookback_highs.mean()) / lookback_highs.std()
            else:
                lookback_lows = df['low'].iloc[max(0, index-10):index+10]
                price_significance = (lookback_lows.mean() - df['low'].iloc[index]) / lookback_lows.std()
            
            significance_strength = min(abs(price_significance) / 2.0, 1.0)
            strength_factors.append(significance_strength)
            
            # Time-based strength (for forex)
            if self.market_type == 'forex' and hasattr(df.index[index], 'hour'):
                time_strength = self.calculate_forex_time_strength(df.index[index].hour)
                strength_factors.append(time_strength * self.session_weight)
            
            return np.mean(strength_factors) if strength_factors else 0.5
            
        except Exception:
            return 0.5
    
    def calculate_forex_time_strength(self, hour: int) -> float:
        """Calculate time-based strength for forex"""
        if 13 <= hour <= 16:  # London-NY overlap
            return 1.0
        elif 8 <= hour <= 17:  # London session
            return 0.8
        elif 13 <= hour <= 22:  # NY session
            return 0.8
        else:  # Asian session
            return 0.5
    
    def analyze_failure_patterns(self, sfp_results: Dict[str, Any], 
                               false_breakouts: List[Dict[str, Any]], 
                               df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze failure pattern characteristics
        """
        analysis = {
            'total_failures': 0,
            'false_breakout_rate': 0.0,
            'failure_bias': 'neutral',
            'market_efficiency': 0.5
        }
        
        total_failures = len(sfp_results.get('sfp_details', []) + false_breakouts)
        analysis['total_failures'] = total_failures
        
        if total_failures > 0:
            # Calculate false breakout rate
            total_attempts = self.count_breakout_attempts(df)
            if total_attempts > 0:
                analysis['false_breakout_rate'] = total_failures / total_attempts
            
            # Determine failure bias
            bullish_failures = len([f for f in false_breakouts if 'resistance' in f['type']])
            bearish_failures = len([f for f in false_breakouts if 'support' in f['type']])
            
            if bullish_failures > bearish_failures:
                analysis['failure_bias'] = 'resistance_heavy'
            elif bearish_failures > bullish_failures:
                analysis['failure_bias'] = 'support_heavy'
            
            # Market efficiency (lower = more false breakouts)
            analysis['market_efficiency'] = max(0, 1.0 - analysis['false_breakout_rate'])
        
        return analysis
    
    def count_breakout_attempts(self, df: pd.DataFrame) -> int:
        """Count total breakout attempts for false breakout rate calculation"""
        attempts = 0
        
        if len(df) < 10:
            return attempts
        
        # Simplified breakout attempt counting
        for i in range(5, len(df)):
            prev_high = df['high'].iloc[i-5:i].max()
            prev_low = df['low'].iloc[i-5:i].min()
            
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            # Count as breakout attempt if price exceeds recent levels
            if current_high > prev_high * 1.001:  # 0.1% threshold
                attempts += 1
            if current_low < prev_low * 0.999:
                attempts += 1
        
        return attempts
    
    def identify_reversal_opportunities(self, sfp_results: Dict[str, Any], 
                                      false_breakouts: List[Dict[str, Any]], 
                                      df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify reversal opportunities based on failure patterns
        """
        opportunities = []
        
        # SFP reversal opportunities
        if sfp_results['sfp_bullish']:
            opportunities.append({
                'type': 'sfp_bullish_reversal',
                'direction': 'short',
                'reason': f'Bullish swing failure in {self.market_type} - expect bearish reversal',
                'strength': 0.75,
                'market_note': self.get_sfp_reversal_note('bullish')
            })
        
        if sfp_results['sfp_bearish']:
            opportunities.append({
                'type': 'sfp_bearish_reversal',
                'direction': 'long',
                'reason': f'Bearish swing failure in {self.market_type} - expect bullish reversal',
                'strength': 0.75,
                'market_note': self.get_sfp_reversal_note('bearish')
            })
        
        # False breakout reversal opportunities
        for fb in false_breakouts[-3:]:  # Recent false breakouts
            if 'resistance' in fb['type']:
                opportunities.append({
                    'type': 'false_breakout_reversal',
                    'direction': 'short',
                    'reason': f'False breakout above resistance in {self.market_type}',
                    'strength': 0.7,
                    'failed_level': fb['level']
                })
            else:  # support
                opportunities.append({
                    'type': 'false_breakout_reversal',
                    'direction': 'long',
                    'reason': f'False breakout below support in {self.market_type}',
                    'strength': 0.7,
                    'failed_level': fb['level']
                })
        
        return opportunities
    
    def get_sfp_reversal_note(self, direction: str) -> str:
        """Get market-specific SFP reversal note"""
        if self.market_type == 'forex':
            if direction == 'bullish':
                return "Forex bullish SFP: Failed upside break often leads to institutional selling"
            else:
                return "Forex bearish SFP: Failed downside break often leads to institutional buying"
        elif self.market_type == 'crypto':
            if direction == 'bullish':
                return "Crypto bullish SFP: Failed pump often leads to whale distribution"
            else:
                return "Crypto bearish SFP: Failed dump often leads to whale accumulation"
        
        return f"SFP {direction} reversal expected"
    
    def calculate_sfp_signal_strength(self, sfp_results: Dict[str, Any], 
                                    false_breakouts: List[Dict[str, Any]], 
                                    df: pd.DataFrame) -> float:
        """
        Calculate SFP signal strength
        """
        if not (sfp_results['sfp_bullish'] or sfp_results['sfp_bearish']) and not false_breakouts:
            return 0.0
        
        strength_factors = []
        
        # SFP strength
        if sfp_results['sfp_bullish'] or sfp_results['sfp_bearish']:
            sfp_strength = 0.75
            strength_factors.append(sfp_strength)
        
        # False breakout strength
        if false_breakouts:
            fb_strength = 0.7
            strength_factors.append(fb_strength)
        
        # Market-specific strength
        market_strength = self.get_market_specific_sfp_strength(df)
        strength_factors.append(market_strength)
        
        # Multiple failure confluence
        total_failures = len(sfp_results.get('sfp_details', [])) + len(false_breakouts)
        if total_failures > 1:
            confluence_bonus = min(total_failures * 0.1, 0.3)
            strength_factors.append(confluence_bonus)
        
        return np.mean(strength_factors)
    
    def get_market_specific_sfp_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific SFP strength"""
        if self.market_type == 'forex':
            # Session-based strength for forex
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                return self.calculate_forex_time_strength(hour)
            return 0.7
        
        elif self.market_type == 'crypto':
            # Volume-based strength for crypto
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(vol_ratio / 2.0, 1.0)
                return 0.6 + volume_factor * 0.4
            
            return 0.7
        
        return 0.7
    
    def update_sfp_tracking(self, sfp_results: Dict[str, Any], 
                           false_breakouts: List[Dict[str, Any]], 
                           swing_levels: Dict[str, List[Dict[str, Any]]]):
        """Update SFP tracking data"""
        # Add SFP events
        if sfp_results['sfp_bullish'] or sfp_results['sfp_bearish']:
            sfp_event = {
                'timestamp': datetime.now(timezone.utc),
                'sfp_bullish': sfp_results['sfp_bullish'],
                'sfp_bearish': sfp_results['sfp_bearish'],
                'market_type': self.market_type
            }
            self.sfp_events.append(sfp_event)
        
        # Add false breakouts
        for fb in false_breakouts:
            fb['detected_time'] = datetime.now(timezone.utc)
            self.false_breakouts.append(fb)
        
        # Update swing levels
        self.swing_levels = swing_levels
        
        # Limit tracking sizes
        if len(self.sfp_events) > 100:
            self.sfp_events = self.sfp_events[-100:]
        
        if len(self.false_breakouts) > 100:
            self.false_breakouts = self.false_breakouts[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_sfp_summary(self) -> Dict[str, Any]:
        """Get comprehensive SFP summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'sfp_events_count': len(self.sfp_events),
            'false_breakouts_count': len(self.false_breakouts),
            'swing_highs_count': len(self.swing_levels.get('highs', [])),
            'swing_lows_count': len(self.swing_levels.get('lows', [])),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'failure_threshold': self.failure_threshold,
                'confirmation_bars': self.confirmation_bars,
                'session_weight': self.session_weight
            }
        }
    
    def has_recent_sfp(self, direction: str = None, bars_back: int = 10) -> bool:
        """Check for recent SFP events"""
        if not self.sfp_events:
            return False
        
        recent_events = self.sfp_events[-bars_back:] if len(self.sfp_events) >= bars_back else self.sfp_events
        
        if direction == 'bullish':
            return any(event['sfp_bullish'] for event in recent_events)
        elif direction == 'bearish':
            return any(event['sfp_bearish'] for event in recent_events)
        else:
            return any(event['sfp_bullish'] or event['sfp_bearish'] for event in recent_events)
    
    def requires_continuous_processing(self) -> bool:
        """SFP agent doesn't need continuous processing"""
        return False