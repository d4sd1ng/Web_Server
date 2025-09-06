"""
Turtle Soup Agent
Detects turtle soup patterns (failed breakout reversals)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class TurtleSoupAgent(ICTSMCAgent):
    """
    Specialized agent for Turtle Soup pattern detection
    Identifies failed breakout reversals and turtle soup setups
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("turtle_soup", config)
        
        # Turtle soup configuration
        self.breakout_threshold = config.get('breakout_threshold', 0.002)  # 0.2%
        self.failure_confirmation_bars = config.get('failure_confirmation_bars', 3)
        self.lookback_period = config.get('lookback_period', 20)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Turtle soup tracking
        self.turtle_soup_events = []
        self.failed_breakouts = []
        self.reversal_confirmations = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Turtle Soup Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific turtle soup configuration"""
        if self.market_type == 'forex':
            # Forex: Smaller breakout thresholds, longer confirmation
            self.breakout_threshold = max(self.breakout_threshold, 0.001)  # 0.1%
            self.failure_confirmation_bars = max(self.failure_confirmation_bars, 5)
            self.session_dependency = True
            self.news_sensitivity = True
        elif self.market_type == 'crypto':
            # Crypto: Larger breakout thresholds, faster confirmation
            self.breakout_threshold = min(self.breakout_threshold, 0.005)  # 0.5%
            self.failure_confirmation_bars = min(self.failure_confirmation_bars, 3)
            self.session_dependency = False
            self.news_sensitivity = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect turtle soup patterns
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with turtle soup analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback_period + 10:
            return {'turtle_soup_detected': False, 'signal_strength': 0.0}
        
        try:
            # Detect turtle soup patterns
            turtle_soup_patterns = self.detect_turtle_soup_patterns(df)
            
            # Analyze failed breakouts
            failed_breakouts = self.analyze_failed_breakouts(df)
            
            # Detect reversal confirmations
            reversal_confirmations = self.detect_reversal_confirmations(df, turtle_soup_patterns)
            
            # Calculate pattern strength
            pattern_strength = self.calculate_turtle_soup_strength(turtle_soup_patterns, df)
            
            # Update tracking
            self.update_turtle_soup_tracking(turtle_soup_patterns, failed_breakouts, reversal_confirmations)
            
            # Calculate signal strength
            signal_strength = self.calculate_ts_signal_strength(
                turtle_soup_patterns, reversal_confirmations, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'turtle_soup_patterns': turtle_soup_patterns,
                'failed_breakouts': failed_breakouts,
                'reversal_confirmations': reversal_confirmations,
                'pattern_strength': pattern_strength,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'reversal_opportunities': self.identify_reversal_opportunities(
                    turtle_soup_patterns, reversal_confirmations
                )
            }
            
            # Publish turtle soup signals
            if turtle_soup_patterns['turtle_soup_detected']:
                self.publish("turtle_soup_detected", {
                    'symbol': symbol,
                    'pattern_type': turtle_soup_patterns['pattern_type'],
                    'reversal_direction': turtle_soup_patterns['expected_reversal'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing turtle soup data for {symbol}: {e}")
            return {'turtle_soup_detected': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_turtle_soup_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect turtle soup patterns (failed breakout reversals)
        """
        patterns = {
            'turtle_soup_detected': False,
            'pattern_type': None,
            'expected_reversal': None,
            'breakout_details': [],
            'failure_details': []
        }
        
        if len(df) < self.lookback_period + 5:
            return patterns
        
        # Look for breakout attempts in recent data
        for i in range(self.lookback_period, len(df) - self.failure_confirmation_bars):
            breakout_attempt = self.identify_breakout_attempt(df, i)
            
            if breakout_attempt:
                # Check if breakout failed (turtle soup)
                failure_analysis = self.check_breakout_failure(df, i, breakout_attempt)
                
                if failure_analysis['failed']:
                    patterns['turtle_soup_detected'] = True
                    patterns['pattern_type'] = f"turtle_soup_{breakout_attempt['direction']}"
                    patterns['expected_reversal'] = 'short' if breakout_attempt['direction'] == 'bullish' else 'long'
                    patterns['breakout_details'].append(breakout_attempt)
                    patterns['failure_details'].append(failure_analysis)
        
        return patterns
    
    def identify_breakout_attempt(self, df: pd.DataFrame, index: int) -> Dict[str, Any]:
        """
        Identify breakout attempt at specific index
        """
        if index < self.lookback_period:
            return None
        
        # Get resistance/support levels from lookback period
        lookback_data = df.iloc[index - self.lookback_period:index]
        resistance_level = lookback_data['high'].max()
        support_level = lookback_data['low'].min()
        
        current_bar = df.iloc[index]
        
        # Check for breakout above resistance
        if current_bar['high'] > resistance_level * (1 + self.breakout_threshold):
            return {
                'direction': 'bullish',
                'breakout_level': resistance_level,
                'breakout_high': current_bar['high'],
                'breakout_close': current_bar['close'],
                'index': index,
                'volume': current_bar['volume'] if 'volume' in df.columns else 0,
                'market_type': self.market_type
            }
        
        # Check for breakout below support
        elif current_bar['low'] < support_level * (1 - self.breakout_threshold):
            return {
                'direction': 'bearish',
                'breakout_level': support_level,
                'breakout_low': current_bar['low'],
                'breakout_close': current_bar['close'],
                'index': index,
                'volume': current_bar['volume'] if 'volume' in df.columns else 0,
                'market_type': self.market_type
            }
        
        return None
    
    def check_breakout_failure(self, df: pd.DataFrame, breakout_index: int, breakout_attempt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if breakout attempt failed (creating turtle soup)
        """
        failure_analysis = {
            'failed': False,
            'failure_type': None,
            'reversal_strength': 0.0,
            'failure_confirmation_bars': 0
        }
        
        if breakout_index + self.failure_confirmation_bars >= len(df):
            return failure_analysis
        
        # Analyze subsequent bars for failure
        confirmation_data = df.iloc[breakout_index + 1:breakout_index + self.failure_confirmation_bars + 1]
        breakout_level = breakout_attempt['breakout_level']
        breakout_direction = breakout_attempt['direction']
        
        if breakout_direction == 'bullish':
            # Check if price failed to sustain above resistance
            closes_below = sum(1 for close in confirmation_data['close'] if close < breakout_level)
            
            if closes_below >= self.failure_confirmation_bars // 2:
                failure_analysis['failed'] = True
                failure_analysis['failure_type'] = 'failed_resistance_breakout'
                failure_analysis['failure_confirmation_bars'] = closes_below
                
                # Calculate reversal strength
                lowest_after_breakout = confirmation_data['low'].min()
                reversal_strength = (breakout_level - lowest_after_breakout) / breakout_level
                failure_analysis['reversal_strength'] = reversal_strength
        
        else:  # bearish breakout
            # Check if price failed to sustain below support
            closes_above = sum(1 for close in confirmation_data['close'] if close > breakout_level)
            
            if closes_above >= self.failure_confirmation_bars // 2:
                failure_analysis['failed'] = True
                failure_analysis['failure_type'] = 'failed_support_breakout'
                failure_analysis['failure_confirmation_bars'] = closes_above
                
                # Calculate reversal strength
                highest_after_breakout = confirmation_data['high'].max()
                reversal_strength = (highest_after_breakout - breakout_level) / breakout_level
                failure_analysis['reversal_strength'] = reversal_strength
        
        # Market-specific validation
        if failure_analysis['failed']:
            failure_analysis['market_validation'] = self.validate_turtle_soup_for_market(df, breakout_index, breakout_attempt)
        
        return failure_analysis
    
    def validate_turtle_soup_for_market(self, df: pd.DataFrame, index: int, breakout_attempt: Dict[str, Any]) -> bool:
        """Validate turtle soup pattern for specific market"""
        if self.market_type == 'forex':
            return self.validate_forex_turtle_soup(df, index, breakout_attempt)
        elif self.market_type == 'crypto':
            return self.validate_crypto_turtle_soup(df, index, breakout_attempt)
        return True
    
    def validate_forex_turtle_soup(self, df: pd.DataFrame, index: int, breakout_attempt: Dict[str, Any]) -> bool:
        """Validate turtle soup for forex markets"""
        try:
            # Session-based validation
            if hasattr(df.index[index], 'hour'):
                hour = df.index[index].hour
                
                # Turtle soup more reliable during major sessions
                if 8 <= hour <= 22:  # Major sessions
                    return True
                else:
                    # Require additional confirmation outside major sessions
                    return breakout_attempt['volume'] > df['volume'].rolling(20).mean().iloc[index] * 1.5
            
            return True
            
        except Exception:
            return True
    
    def validate_crypto_turtle_soup(self, df: pd.DataFrame, index: int, breakout_attempt: Dict[str, Any]) -> bool:
        """Validate turtle soup for crypto markets"""
        try:
            # Volume-based validation for crypto
            if 'volume' in df.columns:
                breakout_volume = breakout_attempt['volume']
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                
                # Require elevated volume for crypto turtle soup
                return breakout_volume > avg_volume * 1.5
            
            return True
            
        except Exception:
            return True
    
    def analyze_failed_breakouts(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze failed breakout patterns
        """
        analysis = {
            'total_failed_breakouts': len(self.failed_breakouts),
            'failed_resistance_breakouts': 0,
            'failed_support_breakouts': 0,
            'average_reversal_strength': 0.0,
            'failure_rate': 0.0
        }
        
        if not self.failed_breakouts:
            return analysis
        
        # Analyze failure types
        for failure in self.failed_breakouts:
            if failure.get('failure_type') == 'failed_resistance_breakout':
                analysis['failed_resistance_breakouts'] += 1
            elif failure.get('failure_type') == 'failed_support_breakout':
                analysis['failed_support_breakouts'] += 1
        
        # Calculate average reversal strength
        reversal_strengths = [failure.get('reversal_strength', 0) for failure in self.failed_breakouts]
        if reversal_strengths:
            analysis['average_reversal_strength'] = np.mean(reversal_strengths)
        
        return analysis
    
    def detect_reversal_confirmations(self, df: pd.DataFrame, turtle_soup_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect reversal confirmations for turtle soup patterns
        """
        confirmations = []
        
        if not turtle_soup_patterns['turtle_soup_detected']:
            return confirmations
        
        # Check each turtle soup pattern for reversal confirmation
        for breakout_detail in turtle_soup_patterns['breakout_details']:
            confirmation = self.check_turtle_soup_reversal(df, breakout_detail)
            if confirmation:
                confirmations.append(confirmation)
        
        return confirmations
    
    def check_turtle_soup_reversal(self, df: pd.DataFrame, breakout_detail: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for turtle soup reversal confirmation
        """
        breakout_index = breakout_detail['index']
        
        if breakout_index + 10 >= len(df):
            return None
        
        # Analyze reversal confirmation
        reversal_data = df.iloc[breakout_index + 1:breakout_index + 10]
        breakout_direction = breakout_detail['direction']
        breakout_level = breakout_detail['breakout_level']
        
        if breakout_direction == 'bullish':
            # Look for bearish reversal confirmation
            reversal_confirmed = (reversal_data['close'].iloc[-1] < breakout_level and
                                reversal_data['low'].min() < breakout_level * 0.995)
            reversal_strength = (breakout_level - reversal_data['low'].min()) / breakout_level
        else:
            # Look for bullish reversal confirmation
            reversal_confirmed = (reversal_data['close'].iloc[-1] > breakout_level and
                                reversal_data['high'].max() > breakout_level * 1.005)
            reversal_strength = (reversal_data['high'].max() - breakout_level) / breakout_level
        
        if reversal_confirmed:
            return {
                'reversal_confirmed': True,
                'reversal_direction': 'bearish' if breakout_direction == 'bullish' else 'bullish',
                'reversal_strength': reversal_strength,
                'confirmation_bars': len(reversal_data),
                'market_context': self.get_turtle_soup_context(breakout_detail),
                'trading_opportunity': self.assess_turtle_soup_opportunity(breakout_detail, reversal_strength)
            }
        
        return None
    
    def get_turtle_soup_context(self, breakout_detail: Dict[str, Any]) -> str:
        """Get market context for turtle soup pattern"""
        direction = breakout_detail['direction']
        
        if self.market_type == 'forex':
            if direction == 'bullish':
                return "Forex turtle soup: Failed bullish breakout, institutional selling likely"
            else:
                return "Forex turtle soup: Failed bearish breakout, institutional buying likely"
        elif self.market_type == 'crypto':
            if direction == 'bullish':
                return "Crypto turtle soup: Failed pump, whale distribution or retail trap"
            else:
                return "Crypto turtle soup: Failed dump, whale accumulation or oversold bounce"
        
        return f"Turtle soup: Failed {direction} breakout"
    
    def assess_turtle_soup_opportunity(self, breakout_detail: Dict[str, Any], reversal_strength: float) -> Dict[str, Any]:
        """
        Assess trading opportunity from turtle soup pattern
        """
        return {
            'opportunity_type': 'turtle_soup_reversal',
            'entry_direction': 'short' if breakout_detail['direction'] == 'bullish' else 'long',
            'entry_level': breakout_detail['breakout_level'],
            'stop_loss': breakout_detail['breakout_high'] if breakout_detail['direction'] == 'bullish' else breakout_detail['breakout_low'],
            'target_estimation': self.estimate_turtle_soup_target(breakout_detail, reversal_strength),
            'opportunity_strength': min(reversal_strength * 2, 1.0),
            'market_specific_note': self.get_opportunity_market_note(breakout_detail)
        }
    
    def estimate_turtle_soup_target(self, breakout_detail: Dict[str, Any], reversal_strength: float) -> float:
        """Estimate target for turtle soup reversal"""
        breakout_level = breakout_detail['breakout_level']
        
        if breakout_detail['direction'] == 'bullish':
            # Failed bullish breakout - target below
            target_distance = breakout_level * reversal_strength * 2  # 2x reversal strength
            return breakout_level - target_distance
        else:
            # Failed bearish breakout - target above
            target_distance = breakout_level * reversal_strength * 2
            return breakout_level + target_distance
    
    def get_opportunity_market_note(self, breakout_detail: Dict[str, Any]) -> str:
        """Get market-specific opportunity note"""
        if self.market_type == 'forex':
            return "Forex turtle soup: High probability reversal due to institutional order flow"
        elif self.market_type == 'crypto':
            return "Crypto turtle soup: Whale manipulation reversal, strong momentum expected"
        
        return "Turtle soup reversal opportunity"
    
    def identify_reversal_opportunities(self, turtle_soup_patterns: Dict[str, Any], 
                                      reversal_confirmations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify specific reversal trading opportunities
        """
        opportunities = []
        
        if not turtle_soup_patterns['turtle_soup_detected']:
            return opportunities
        
        # Create opportunities from confirmed reversals
        for confirmation in reversal_confirmations:
            if confirmation['reversal_confirmed']:
                opportunity = {
                    'type': 'turtle_soup_reversal',
                    'direction': confirmation['reversal_direction'],
                    'strength': confirmation['reversal_strength'],
                    'confidence': min(confirmation['reversal_strength'] * 1.5, 1.0),
                    'market_context': confirmation['market_context'],
                    'trading_opportunity': confirmation['trading_opportunity'],
                    'risk_level': self.assess_turtle_soup_risk(confirmation)
                }
                opportunities.append(opportunity)
        
        return opportunities
    
    def assess_turtle_soup_risk(self, confirmation: Dict[str, Any]) -> str:
        """Assess risk level for turtle soup trade"""
        reversal_strength = confirmation['reversal_strength']
        
        if reversal_strength > 0.01:  # 1%+ reversal
            return 'low'
        elif reversal_strength > 0.005:  # 0.5%+ reversal
            return 'medium'
        else:
            return 'high'
    
    def calculate_turtle_soup_strength(self, turtle_soup_patterns: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate turtle soup pattern strength
        """
        if not turtle_soup_patterns['turtle_soup_detected']:
            return 0.0
        
        strength_factors = []
        
        # Base turtle soup strength
        base_strength = 0.8  # Turtle soup is a strong reversal pattern
        strength_factors.append(base_strength)
        
        # Number of failed breakouts
        failed_breakout_count = len(turtle_soup_patterns['failure_details'])
        breakout_strength = min(failed_breakout_count / 2.0, 1.0)
        strength_factors.append(breakout_strength)
        
        # Market-specific strength
        market_strength = self.get_market_turtle_soup_strength(df)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors)
    
    def get_market_turtle_soup_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific turtle soup strength"""
        if self.market_type == 'forex':
            # Session-based strength for forex
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:  # London-NY overlap
                    return 0.9
                elif 8 <= hour <= 22:  # Major sessions
                    return 0.8
                else:
                    return 0.6
            return 0.7
        
        elif self.market_type == 'crypto':
            # Volume-based strength for crypto
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                return min(0.6 + vol_ratio / 5.0, 1.0)
            
            return 0.7
        
        return 0.7
    
    def calculate_ts_signal_strength(self, turtle_soup_patterns: Dict[str, Any], 
                                   reversal_confirmations: List[Dict[str, Any]], df: pd.DataFrame) -> float:
        """
        Calculate turtle soup signal strength
        """
        if not turtle_soup_patterns['turtle_soup_detected']:
            return 0.0
        
        strength_factors = []
        
        # Pattern strength
        pattern_strength = self.calculate_turtle_soup_strength(turtle_soup_patterns, df)
        strength_factors.append(pattern_strength)
        
        # Confirmation strength
        if reversal_confirmations:
            confirmation_strength = np.mean([conf['reversal_strength'] for conf in reversal_confirmations])
            strength_factors.append(confirmation_strength * 2)  # Boost confirmed reversals
        
        # Market-specific strength
        market_strength = self.get_market_turtle_soup_strength(df)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors)
    
    def update_turtle_soup_tracking(self, turtle_soup_patterns: Dict[str, Any], 
                                   failed_breakouts: Dict[str, Any], 
                                   reversal_confirmations: List[Dict[str, Any]]):
        """Update turtle soup tracking"""
        if turtle_soup_patterns['turtle_soup_detected']:
            ts_event = {
                'timestamp': datetime.now(timezone.utc),
                'pattern_type': turtle_soup_patterns['pattern_type'],
                'expected_reversal': turtle_soup_patterns['expected_reversal'],
                'breakout_details': turtle_soup_patterns['breakout_details'],
                'failure_details': turtle_soup_patterns['failure_details'],
                'market_type': self.market_type
            }
            
            self.turtle_soup_events.append(ts_event)
            
            # Update failed breakouts
            self.failed_breakouts.extend(turtle_soup_patterns['failure_details'])
            
            # Update reversal confirmations
            self.reversal_confirmations.extend(reversal_confirmations)
            
            # Limit tracking sizes
            if len(self.turtle_soup_events) > 50:
                self.turtle_soup_events = self.turtle_soup_events[-50:]
            
            if len(self.failed_breakouts) > 100:
                self.failed_breakouts = self.failed_breakouts[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_turtle_soup_summary(self) -> Dict[str, Any]:
        """Get comprehensive turtle soup summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'turtle_soup_events_count': len(self.turtle_soup_events),
            'failed_breakouts_count': len(self.failed_breakouts),
            'reversal_confirmations_count': len(self.reversal_confirmations),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'breakout_threshold': self.breakout_threshold,
                'failure_confirmation_bars': self.failure_confirmation_bars,
                'lookback_period': self.lookback_period
            }
        }
    
    def has_recent_turtle_soup(self, direction: str = None) -> bool:
        """Check for recent turtle soup patterns"""
        if not self.turtle_soup_events:
            return False
        
        recent_event = self.turtle_soup_events[-1]
        
        if direction:
            return recent_event['expected_reversal'] == direction
        else:
            return True
    
    def requires_continuous_processing(self) -> bool:
        """Turtle soup agent doesn't need continuous processing"""
        return False