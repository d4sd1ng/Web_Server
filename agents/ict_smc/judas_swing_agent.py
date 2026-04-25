"""
Judas Swing Agent
Detects Judas swing patterns (false moves before true direction)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import pytz

from agents.base_agent import ICTSMCAgent


class JudasSwingAgent(ICTSMCAgent):
    """
    Specialized agent for Judas Swing pattern detection
    Identifies false moves that precede the true market direction
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("judas_swing", config)
        
        # Judas swing configuration
        self.session_start_window = config.get('session_start_window', 60)  # Minutes from session start
        self.false_move_threshold = config.get('false_move_threshold', 0.005)  # 0.5%
        self.reversal_confirmation_bars = config.get('reversal_confirmation_bars', 5)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Judas tracking
        self.judas_events = []
        self.session_openings = []
        self.false_move_patterns = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Judas Swing Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific Judas swing configuration"""
        if self.market_type == 'forex':
            # Forex: Judas swings common at session openings
            self.session_start_window = 90  # Wider window for forex
            self.false_move_threshold = 0.003  # Smaller moves in forex
            self.key_sessions = ['london', 'ny', 'asian']
            self.session_importance = 1.0
        elif self.market_type == 'crypto':
            # Crypto: Less session-dependent but still occurs
            self.session_start_window = 60  # Standard window
            self.false_move_threshold = 0.008  # Larger moves in crypto
            self.key_sessions = ['london_ny_overlap']  # Focus on major overlap
            self.session_importance = 0.6
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect Judas swing patterns
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with Judas swing analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        current_time = data.get('current_time', datetime.now(timezone.utc))
        
        if df.empty or len(df) < 20:
            return {'judas_detected': False, 'signal_strength': 0.0}
        
        try:
            # Detect Judas swing patterns
            judas_patterns = self.detect_judas_swing_patterns(df, current_time)
            
            # Analyze session-based false moves
            session_analysis = self.analyze_session_false_moves(df, current_time)
            
            # Detect reversal confirmations
            reversal_confirmations = self.detect_reversal_confirmations(df, judas_patterns)
            
            # Calculate signal strength
            signal_strength = self.calculate_judas_signal_strength(
                judas_patterns, session_analysis, reversal_confirmations, df
            )
            
            # Update tracking
            self.update_judas_tracking(judas_patterns, session_analysis, current_time)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': current_time.isoformat(),
                'judas_patterns': judas_patterns,
                'session_analysis': session_analysis,
                'reversal_confirmations': reversal_confirmations,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_implications': self.get_judas_trading_implications(
                    judas_patterns, reversal_confirmations
                )
            }
            
            # Publish Judas swing signals
            if judas_patterns['judas_detected']:
                self.publish("judas_swing_detected", {
                    'symbol': symbol,
                    'judas_direction': judas_patterns['judas_direction'],
                    'expected_reversal': judas_patterns['expected_reversal_direction'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing Judas swing data for {symbol}: {e}")
            return {'judas_detected': False, 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_judas_swing_patterns(self, df: pd.DataFrame, current_time: datetime) -> Dict[str, Any]:
        """
        Detect Judas swing patterns
        """
        judas_patterns = {
            'judas_detected': False,
            'judas_direction': None,
            'expected_reversal_direction': None,
            'false_move_details': [],
            'session_context': None
        }
        
        if len(df) < 10:
            return judas_patterns
        
        # Check if we're near a session opening
        session_context = self.get_session_context(current_time)
        judas_patterns['session_context'] = session_context
        
        if not session_context['near_session_start']:
            return judas_patterns
        
        # Look for false moves in recent data
        recent_data = df.iloc[-20:]  # Last 20 bars
        
        # Detect false breakouts at session start
        false_moves = self.detect_session_false_moves(recent_data, session_context)
        
        if false_moves:
            judas_patterns['judas_detected'] = True
            judas_patterns['false_move_details'] = false_moves
            
            # Determine Judas direction and expected reversal
            latest_false_move = false_moves[-1]
            judas_patterns['judas_direction'] = latest_false_move['direction']
            judas_patterns['expected_reversal_direction'] = 'short' if latest_false_move['direction'] == 'bullish' else 'long'
        
        return judas_patterns
    
    def get_session_context(self, current_time: datetime) -> Dict[str, Any]:
        """
        Get session context for Judas swing analysis
        """
        context = {
            'near_session_start': False,
            'active_session': None,
            'minutes_from_session_start': None,
            'session_importance': 0.0
        }
        
        # Convert to major timezones
        london_time = current_time.astimezone(pytz.timezone('Europe/London'))
        ny_time = current_time.astimezone(pytz.timezone('America/New_York'))
        tokyo_time = current_time.astimezone(pytz.timezone('Asia/Tokyo'))
        
        # Check for session starts
        sessions_to_check = [
            ('london', london_time, 8),  # London opens at 8 AM
            ('ny', ny_time, 9),          # NY opens at 9 AM
            ('asian', tokyo_time, 9)     # Tokyo opens at 9 AM
        ]
        
        for session_name, session_time, open_hour in sessions_to_check:
            if session_name in self.key_sessions:
                minutes_from_open = (session_time.hour - open_hour) * 60 + session_time.minute
                
                # Check if within session start window
                if 0 <= minutes_from_open <= self.session_start_window:
                    context['near_session_start'] = True
                    context['active_session'] = session_name
                    context['minutes_from_session_start'] = minutes_from_open
                    context['session_importance'] = self.get_session_importance(session_name)
                    break
        
        return context
    
    def get_session_importance(self, session_name: str) -> float:
        """Get importance weight for session"""
        if self.market_type == 'forex':
            importance_weights = {
                'london': 1.0,
                'ny': 1.0,
                'asian': 0.6
            }
        elif self.market_type == 'crypto':
            importance_weights = {
                'london': 0.8,
                'ny': 0.8,
                'asian': 0.7
            }
        else:
            importance_weights = {'london': 0.8, 'ny': 0.8, 'asian': 0.6}
        
        return importance_weights.get(session_name, 0.5)
    
    def detect_session_false_moves(self, recent_data: pd.DataFrame, session_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect false moves at session openings
        """
        false_moves = []
        
        if len(recent_data) < 10:
            return false_moves
        
        # Look for initial direction followed by reversal
        session_start_index = max(0, len(recent_data) - 10)  # Approximate session start
        
        for i in range(session_start_index, len(recent_data) - 5):
            # Check for initial move
            initial_move = self.identify_initial_move(recent_data, i)
            
            if initial_move:
                # Check for reversal
                reversal = self.check_for_reversal(recent_data, i, initial_move)
                
                if reversal:
                    false_moves.append({
                        'direction': initial_move['direction'],
                        'initial_move_size': initial_move['move_size'],
                        'reversal_confirmation': reversal,
                        'session': session_context['active_session'],
                        'market_type': self.market_type,
                        'timestamp': recent_data.index[i] if i < len(recent_data) else None
                    })
        
        return false_moves
    
    def identify_initial_move(self, df: pd.DataFrame, start_index: int) -> Dict[str, Any]:
        """
        Identify initial move from session start
        """
        if start_index + 3 >= len(df):
            return None
        
        start_price = df['close'].iloc[start_index]
        
        # Check next few bars for directional move
        for i in range(start_index + 1, min(start_index + 4, len(df))):
            current_price = df['close'].iloc[i]
            move_size = abs(current_price - start_price) / start_price
            
            if move_size > self.false_move_threshold:
                direction = 'bullish' if current_price > start_price else 'bearish'
                
                return {
                    'direction': direction,
                    'move_size': move_size,
                    'start_price': start_price,
                    'end_price': current_price,
                    'start_index': start_index,
                    'end_index': i
                }
        
        return None
    
    def check_for_reversal(self, df: pd.DataFrame, move_start_index: int, initial_move: Dict[str, Any]) -> bool:
        """
        Check for reversal after initial move
        """
        move_end_index = initial_move['end_index']
        reversal_start = move_end_index + 1
        reversal_end = min(reversal_start + self.reversal_confirmation_bars, len(df))
        
        if reversal_end <= reversal_start:
            return False
        
        # Check for reversal in opposite direction
        move_direction = initial_move['direction']
        end_price = initial_move['end_price']
        
        reversal_data = df.iloc[reversal_start:reversal_end]
        
        if move_direction == 'bullish':
            # Look for bearish reversal
            lowest_price = reversal_data['low'].min()
            reversal_size = (end_price - lowest_price) / end_price
            return reversal_size > self.false_move_threshold
        
        else:  # bearish initial move
            # Look for bullish reversal
            highest_price = reversal_data['high'].max()
            reversal_size = (highest_price - end_price) / end_price
            return reversal_size > self.false_move_threshold
    
    def analyze_session_false_moves(self, df: pd.DataFrame, current_time: datetime) -> Dict[str, Any]:
        """
        Analyze session-based false move patterns
        """
        analysis = {
            'session_false_move_frequency': 0.0,
            'most_common_false_direction': 'unknown',
            'average_false_move_size': 0.0,
            'reversal_success_rate': 0.0
        }
        
        if len(self.judas_events) < 5:
            return analysis
        
        # Analyze historical Judas events
        recent_events = self.judas_events[-20:] if len(self.judas_events) >= 20 else self.judas_events
        
        # Calculate frequency
        total_sessions = len(self.session_openings) if hasattr(self, 'session_openings') else len(recent_events)
        if total_sessions > 0:
            analysis['session_false_move_frequency'] = len(recent_events) / total_sessions
        
        # Find most common false direction
        bullish_false_moves = sum(1 for event in recent_events if event.get('judas_direction') == 'bullish')
        bearish_false_moves = sum(1 for event in recent_events if event.get('judas_direction') == 'bearish')
        
        if bullish_false_moves > bearish_false_moves:
            analysis['most_common_false_direction'] = 'bullish'
        elif bearish_false_moves > bullish_false_moves:
            analysis['most_common_false_direction'] = 'bearish'
        
        # Calculate average false move size
        false_move_sizes = [event.get('false_move_size', 0) for event in recent_events if 'false_move_size' in event]
        if false_move_sizes:
            analysis['average_false_move_size'] = np.mean(false_move_sizes)
        
        # Calculate reversal success rate
        successful_reversals = sum(1 for event in recent_events if event.get('reversal_confirmed', False))
        if recent_events:
            analysis['reversal_success_rate'] = successful_reversals / len(recent_events)
        
        return analysis
    
    def detect_reversal_confirmations(self, df: pd.DataFrame, judas_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect reversal confirmations for Judas swings
        """
        confirmations = []
        
        if not judas_patterns['judas_detected']:
            return confirmations
        
        false_moves = judas_patterns['false_move_details']
        
        for false_move in false_moves:
            confirmation = self.check_judas_reversal_confirmation(df, false_move)
            if confirmation:
                confirmations.append(confirmation)
        
        return confirmations
    
    def check_judas_reversal_confirmation(self, df: pd.DataFrame, false_move: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for Judas swing reversal confirmation
        """
        if 'timestamp' not in false_move or len(df) < 10:
            return None
        
        # Find the index of the false move
        false_move_time = false_move['timestamp']
        
        # Look for confirmation in subsequent bars
        confirmation_data = df.iloc[-self.reversal_confirmation_bars:]
        
        if len(confirmation_data) < 3:
            return None
        
        # Check for reversal pattern
        if false_move['direction'] == 'bullish':
            # Look for bearish reversal confirmation
            reversal_confirmed = (confirmation_data['close'].iloc[-1] < confirmation_data['close'].iloc[0] and
                                confirmation_data['low'].iloc[-1] < confirmation_data['low'].iloc[0])
        else:
            # Look for bullish reversal confirmation
            reversal_confirmed = (confirmation_data['close'].iloc[-1] > confirmation_data['close'].iloc[0] and
                                confirmation_data['high'].iloc[-1] > confirmation_data['high'].iloc[0])
        
        if reversal_confirmed:
            return {
                'reversal_confirmed': True,
                'reversal_direction': 'bearish' if false_move['direction'] == 'bullish' else 'bullish',
                'confirmation_strength': self.calculate_reversal_strength(confirmation_data, false_move),
                'market_context': self.get_reversal_market_context(false_move)
            }
        
        return None
    
    def calculate_reversal_strength(self, confirmation_data: pd.DataFrame, false_move: Dict[str, Any]) -> float:
        """
        Calculate strength of reversal confirmation
        """
        try:
            strength_factors = []
            
            # Price movement strength
            start_price = confirmation_data['close'].iloc[0]
            end_price = confirmation_data['close'].iloc[-1]
            price_move = abs(end_price - start_price) / start_price
            move_strength = min(price_move / 0.02, 1.0)  # Normalize to 2% move
            strength_factors.append(move_strength)
            
            # Volume confirmation
            if 'volume' in confirmation_data.columns:
                avg_volume = confirmation_data['volume'].mean()
                latest_volume = confirmation_data['volume'].iloc[-1]
                volume_strength = min(latest_volume / avg_volume, 2.0) / 2.0
                
                if self.market_type == 'crypto':
                    strength_factors.append(volume_strength * 0.8)
                else:
                    strength_factors.append(volume_strength * 0.4)
            
            # Consistency strength (multiple bars confirming)
            if false_move['direction'] == 'bullish':
                bearish_bars = sum(1 for i in range(len(confirmation_data)) 
                                 if confirmation_data['close'].iloc[i] < confirmation_data['open'].iloc[i])
                consistency = bearish_bars / len(confirmation_data)
            else:
                bullish_bars = sum(1 for i in range(len(confirmation_data)) 
                                 if confirmation_data['close'].iloc[i] > confirmation_data['open'].iloc[i])
                consistency = bullish_bars / len(confirmation_data)
            
            strength_factors.append(consistency)
            
            return np.mean(strength_factors) if strength_factors else 0.5
            
        except Exception:
            return 0.5
    
    def get_reversal_market_context(self, false_move: Dict[str, Any]) -> str:
        """Get market context for reversal"""
        session = false_move.get('session', 'unknown')
        
        if self.market_type == 'forex':
            if session == 'london':
                return "Forex London Judas: European session false move, expect institutional reversal"
            elif session == 'ny':
                return "Forex NY Judas: US session false move, expect dollar-based reversal"
            elif session == 'asian':
                return "Forex Asian Judas: Yen session false move, expect range-bound reversal"
        
        elif self.market_type == 'crypto':
            return f"Crypto Judas at {session}: Whale false move, expect smart money reversal"
        
        return f"Judas swing in {session} session"
    
    def get_judas_trading_implications(self, judas_patterns: Dict[str, Any], 
                                     reversal_confirmations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get trading implications of Judas swing patterns
        """
        implications = []
        
        if not judas_patterns['judas_detected']:
            return implications
        
        expected_direction = judas_patterns['expected_reversal_direction']
        
        # Primary implication
        implications.append({
            'type': 'judas_reversal_setup',
            'direction': expected_direction,
            'confidence': 0.75,
            'reason': f'Judas swing detected in {self.market_type} - expect {expected_direction} reversal',
            'market_note': self.get_judas_market_note(judas_patterns),
            'timing': 'Immediate to short-term'
        })
        
        # Confirmation-based implications
        if reversal_confirmations:
            for confirmation in reversal_confirmations:
                implications.append({
                    'type': 'judas_reversal_confirmed',
                    'direction': confirmation['reversal_direction'],
                    'confidence': confirmation['confirmation_strength'],
                    'reason': 'Judas swing reversal confirmed by price action',
                    'market_note': confirmation['market_context'],
                    'timing': 'Active trade opportunity'
                })
        
        return implications
    
    def get_judas_market_note(self, judas_patterns: Dict[str, Any]) -> str:
        """Get market-specific note for Judas swing"""
        session = judas_patterns['session_context']['active_session']
        judas_direction = judas_patterns['judas_direction']
        
        if self.market_type == 'forex':
            return f"Forex Judas in {session}: {judas_direction} false move likely institutional trap before true direction"
        elif self.market_type == 'crypto':
            return f"Crypto Judas in {session}: {judas_direction} false move likely whale manipulation before real direction"
        
        return f"Judas swing: {judas_direction} false move detected"
    
    def calculate_judas_signal_strength(self, judas_patterns: Dict[str, Any], 
                                      session_analysis: Dict[str, Any], 
                                      reversal_confirmations: List[Dict[str, Any]], 
                                      df: pd.DataFrame) -> float:
        """
        Calculate Judas swing signal strength
        """
        if not judas_patterns['judas_detected']:
            return 0.0
        
        strength_factors = []
        
        # Base Judas strength
        base_strength = 0.75  # Judas is a strong reversal pattern
        strength_factors.append(base_strength)
        
        # Session timing strength
        session_context = judas_patterns['session_context']
        if session_context['near_session_start']:
            session_strength = session_context['session_importance'] * self.session_importance
            strength_factors.append(session_strength)
        
        # Confirmation strength
        if reversal_confirmations:
            confirmation_strength = np.mean([conf['confirmation_strength'] for conf in reversal_confirmations])
            strength_factors.append(confirmation_strength)
        
        # Market-specific strength
        market_strength = self.get_market_judas_strength(df, session_context)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors)
    
    def get_market_judas_strength(self, df: pd.DataFrame, session_context: Dict[str, Any]) -> float:
        """Get market-specific Judas strength"""
        if self.market_type == 'forex':
            # Forex Judas strength based on session
            session = session_context.get('active_session')
            if session in ['london', 'ny']:
                return 0.9  # High strength during major sessions
            else:
                return 0.6  # Lower strength during Asian session
        
        elif self.market_type == 'crypto':
            # Crypto Judas strength based on volume
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                return min(0.6 + vol_ratio / 4.0, 1.0)
            
            return 0.7
        
        return 0.7
    
    def update_judas_tracking(self, judas_patterns: Dict[str, Any], 
                             session_analysis: Dict[str, Any], current_time: datetime):
        """Update Judas swing tracking"""
        if judas_patterns['judas_detected']:
            judas_event = {
                'timestamp': current_time,
                'judas_direction': judas_patterns['judas_direction'],
                'expected_reversal': judas_patterns['expected_reversal_direction'],
                'session': judas_patterns['session_context']['active_session'],
                'market_type': self.market_type,
                'false_move_details': judas_patterns['false_move_details']
            }
            
            self.judas_events.append(judas_event)
            
            # Limit tracking size
            if len(self.judas_events) > 50:
                self.judas_events = self.judas_events[-50:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_judas_summary(self) -> Dict[str, Any]:
        """Get comprehensive Judas swing summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'judas_events_count': len(self.judas_events),
            'session_openings_tracked': len(getattr(self, 'session_openings', [])),
            'key_sessions': self.key_sessions,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'session_start_window': self.session_start_window,
                'false_move_threshold': self.false_move_threshold,
                'reversal_confirmation_bars': self.reversal_confirmation_bars,
                'session_importance': self.session_importance
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Judas swing agent benefits from continuous processing for session timing"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for session timing"""
        try:
            current_time = datetime.now(timezone.utc)
            session_context = self.get_session_context(current_time)
            
            # Track session openings
            if session_context['near_session_start'] and session_context['minutes_from_session_start'] <= 5:
                # Near session start - prime time for Judas swings
                if not hasattr(self, '_last_session_alert') or self._last_session_alert != session_context['active_session']:
                    self.logger.info(f"Session opening: {session_context['active_session']} - monitoring for Judas swings")
                    self._last_session_alert = session_context['active_session']
                    
                    self.publish("session_opening_judas_watch", {
                        'session': session_context['active_session'],
                        'market_type': self.market_type
                    })
            
        except Exception as e:
            self.logger.error(f"Error in Judas continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval"""
        return 300.0  # Check every 5 minutes for session timing