"""
Session Analysis Agent
Analyzes trading sessions and time-based patterns
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import pytz

from agents.base_agent import BaseAgent


class SessionAnalysisAgent(BaseAgent):
    """
    Specialized agent for Trading Session analysis
    Analyzes session-based patterns and time-dependent behaviors
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("session_analysis", config)
        
        # Session configuration
        self.sessions = config.get('sessions', {
            'asian': {'start': '22:00', 'end': '06:00', 'timezone': 'Asia/Tokyo'},
            'london': {'start': '08:00', 'end': '17:00', 'timezone': 'Europe/London'},
            'ny': {'start': '13:00', 'end': '22:00', 'timezone': 'America/New_York'},
            'london_ny_overlap': {'start': '13:00', 'end': '17:00', 'timezone': 'UTC'}
        })
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Session tracking
        self.session_performance = {}
        self.session_transitions = []
        self.hourly_patterns = {}
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Session Analysis Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific session configuration"""
        if self.market_type == 'forex':
            # Forex: Sessions are critical
            self.session_importance = 1.0
            self.overlap_multiplier = 2.0
            self.weekend_penalty = 0.1  # Heavy penalty for weekend forex
        elif self.market_type == 'crypto':
            # Crypto: Sessions matter but less critical
            self.session_importance = 0.6
            self.overlap_multiplier = 1.3
            self.weekend_penalty = 0.8  # Light penalty for weekend crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data for session analysis
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with session analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        current_time = data.get('current_time', datetime.now(timezone.utc))
        
        try:
            # Identify current session
            current_session = self.identify_current_session(current_time)
            
            # Analyze session characteristics
            session_analysis = self.analyze_session_characteristics(df, current_time)
            
            # Get session performance metrics
            session_performance = self.calculate_session_performance(df)
            
            # Analyze hourly patterns
            hourly_analysis = self.analyze_hourly_patterns(df)
            
            # Check for session transitions
            transition_analysis = self.analyze_session_transitions(current_time)
            
            # Calculate signal strength
            signal_strength = self.calculate_session_signal_strength(
                current_session, session_analysis, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': current_time.isoformat(),
                'current_session': current_session,
                'session_analysis': session_analysis,
                'session_performance': session_performance,
                'hourly_analysis': hourly_analysis,
                'transition_analysis': transition_analysis,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_recommendations': self.get_session_recommendations(
                    current_session, session_analysis
                )
            }
            
            # Publish session signals
            if current_session['active_sessions']:
                self.publish("session_active", {
                    'symbol': symbol,
                    'active_sessions': current_session['active_sessions'],
                    'session_quality': session_analysis['session_quality'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing session data for {symbol}: {e}")
            return {'session_analysis': 'error', 'signal_strength': 0.0, 'error': str(e)}
    
    def identify_current_session(self, current_time: datetime) -> Dict[str, Any]:
        """
        Identify currently active trading sessions
        """
        active_sessions = []
        session_weights = 0.0
        
        for session_name, session_config in self.sessions.items():
            if self.is_session_active(current_time, session_config):
                weight = self.get_session_weight(session_name)
                active_sessions.append({
                    'name': session_name,
                    'weight': weight,
                    'config': session_config
                })
                session_weights += weight
        
        # Determine primary session
        primary_session = None
        if active_sessions:
            primary_session = max(active_sessions, key=lambda x: x['weight'])['name']
        
        return {
            'active_sessions': active_sessions,
            'primary_session': primary_session,
            'total_weight': session_weights,
            'is_overlap': len(active_sessions) > 1,
            'current_time': current_time.isoformat()
        }
    
    def is_session_active(self, current_time: datetime, session_config: Dict[str, Any]) -> bool:
        """Check if a specific session is active"""
        try:
            session_tz = pytz.timezone(session_config['timezone'])
            session_time = current_time.astimezone(session_tz)
            
            start_hour, start_minute = map(int, session_config['start'].split(':'))
            end_hour, end_minute = map(int, session_config['end'].split(':'))
            
            current_minutes = session_time.hour * 60 + session_time.minute
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            
            # Handle overnight sessions
            if end_minutes < start_minutes:  # Crosses midnight
                return current_minutes >= start_minutes or current_minutes <= end_minutes
            else:
                return start_minutes <= current_minutes <= end_minutes
            
        except Exception:
            return False
    
    def get_session_weight(self, session_name: str) -> float:
        """Get weight for specific session based on market type"""
        base_weights = {
            'london_ny_overlap': 2.0,
            'london': 1.5,
            'ny': 1.5,
            'asian': 1.0
        }
        
        base_weight = base_weights.get(session_name, 1.0)
        
        if self.market_type == 'forex':
            # Forex: Major sessions very important
            if 'overlap' in session_name:
                return base_weight * 1.5
            elif session_name in ['london', 'ny']:
                return base_weight * 1.2
            else:
                return base_weight * 0.8
        
        elif self.market_type == 'crypto':
            # Crypto: Sessions matter but less critical
            if 'overlap' in session_name:
                return base_weight * 1.2
            else:
                return base_weight
        
        return base_weight
    
    def analyze_session_characteristics(self, df: pd.DataFrame, current_time: datetime) -> Dict[str, Any]:
        """
        Analyze characteristics of current session
        """
        analysis = {
            'session_quality': 0.5,
            'volatility_level': 'normal',
            'liquidity_level': 'normal',
            'typical_behavior': 'unknown'
        }
        
        # Get current session info
        current_session_info = self.identify_current_session(current_time)
        
        if not current_session_info['active_sessions']:
            analysis['session_quality'] = 0.2  # Off-session
            analysis['typical_behavior'] = 'low_activity'
            return analysis
        
        primary_session = current_session_info['primary_session']
        
        # Session-specific analysis
        if primary_session == 'london_ny_overlap':
            analysis['session_quality'] = 0.9
            analysis['volatility_level'] = 'high'
            analysis['liquidity_level'] = 'very_high'
            analysis['typical_behavior'] = 'trending_breakouts'
        
        elif primary_session in ['london', 'ny']:
            analysis['session_quality'] = 0.8
            analysis['volatility_level'] = 'medium_high'
            analysis['liquidity_level'] = 'high'
            analysis['typical_behavior'] = 'directional_moves'
        
        elif primary_session == 'asian':
            analysis['session_quality'] = 0.5 if self.market_type == 'forex' else 0.7
            analysis['volatility_level'] = 'low_medium'
            analysis['liquidity_level'] = 'medium'
            analysis['typical_behavior'] = 'range_bound'
        
        # Market-specific adjustments
        if self.market_type == 'crypto':
            # Crypto is less session-dependent
            analysis['session_quality'] = min(analysis['session_quality'] + 0.2, 1.0)
        
        return analysis
    
    def calculate_session_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate performance metrics for different sessions
        """
        if len(df) < 50:
            return {'insufficient_data': True}
        
        performance = {}
        
        # Analyze performance by hour (simplified)
        if hasattr(df.index[0], 'hour'):
            hourly_data = {}
            
            for i in range(len(df)):
                hour = df.index[i].hour
                if hour not in hourly_data:
                    hourly_data[hour] = {'count': 0, 'volume': 0, 'volatility': 0}
                
                hourly_data[hour]['count'] += 1
                hourly_data[hour]['volume'] += df['volume'].iloc[i] if 'volume' in df.columns else 0
                
                if i > 0:
                    price_change = abs(df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
                    hourly_data[hour]['volatility'] += price_change
            
            # Calculate averages
            for hour, data in hourly_data.items():
                if data['count'] > 0:
                    data['avg_volume'] = data['volume'] / data['count']
                    data['avg_volatility'] = data['volatility'] / data['count']
                    
                    # Classify session for this hour
                    session = self.classify_hour_to_session(hour)
                    if session not in performance:
                        performance[session] = {'hours': [], 'avg_volume': 0, 'avg_volatility': 0}
                    
                    performance[session]['hours'].append(hour)
                    performance[session]['avg_volume'] += data['avg_volume']
                    performance[session]['avg_volatility'] += data['avg_volatility']
            
            # Finalize session averages
            for session, data in performance.items():
                if data['hours']:
                    data['avg_volume'] /= len(data['hours'])
                    data['avg_volatility'] /= len(data['hours'])
        
        return performance
    
    def classify_hour_to_session(self, hour: int) -> str:
        """Classify hour to trading session"""
        if 13 <= hour <= 16:
            return 'london_ny_overlap'
        elif 8 <= hour <= 17:
            return 'london'
        elif 13 <= hour <= 22:
            return 'ny'
        elif 22 <= hour <= 6:
            return 'asian'
        else:
            return 'off_hours'
    
    def analyze_hourly_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze hourly trading patterns
        """
        if len(df) < 24 or not hasattr(df.index[0], 'hour'):
            return {'patterns': 'insufficient_data'}
        
        hourly_stats = {}
        
        # Group by hour
        for i in range(len(df)):
            hour = df.index[i].hour
            if hour not in hourly_stats:
                hourly_stats[hour] = {
                    'price_changes': [],
                    'volumes': [],
                    'ranges': []
                }
            
            if i > 0:
                price_change = (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
                hourly_stats[hour]['price_changes'].append(price_change)
            
            if 'volume' in df.columns:
                hourly_stats[hour]['volumes'].append(df['volume'].iloc[i])
            
            candle_range = (df['high'].iloc[i] - df['low'].iloc[i]) / df['close'].iloc[i]
            hourly_stats[hour]['ranges'].append(candle_range)
        
        # Calculate hourly metrics
        hourly_metrics = {}
        for hour, stats in hourly_stats.items():
            if stats['price_changes']:
                hourly_metrics[hour] = {
                    'avg_price_change': np.mean(np.abs(stats['price_changes'])),
                    'avg_volume': np.mean(stats['volumes']) if stats['volumes'] else 0,
                    'avg_range': np.mean(stats['ranges']),
                    'volatility': np.std(stats['price_changes']),
                    'sample_size': len(stats['price_changes'])
                }
        
        # Find best and worst hours
        best_hours = self.find_optimal_hours(hourly_metrics)
        
        return {
            'hourly_metrics': hourly_metrics,
            'best_hours': best_hours,
            'pattern_type': self.classify_hourly_pattern(hourly_metrics)
        }
    
    def find_optimal_hours(self, hourly_metrics: Dict[str, Any]) -> Dict[str, List[int]]:
        """Find optimal trading hours"""
        if not hourly_metrics:
            return {'high_volatility': [], 'high_volume': [], 'best_overall': []}
        
        # Sort hours by different metrics
        hours_by_volatility = sorted(hourly_metrics.items(), 
                                   key=lambda x: x[1]['volatility'], reverse=True)
        hours_by_volume = sorted(hourly_metrics.items(), 
                               key=lambda x: x[1]['avg_volume'], reverse=True)
        
        # Combined score for best overall hours
        hours_by_combined = []
        for hour, metrics in hourly_metrics.items():
            combined_score = (metrics['volatility'] * 0.4 + 
                            (metrics['avg_volume'] / max(h[1]['avg_volume'] for h in hourly_metrics.items())) * 0.3 +
                            metrics['avg_range'] * 0.3)
            hours_by_combined.append((hour, combined_score))
        
        hours_by_combined.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'high_volatility': [h[0] for h in hours_by_volatility[:6]],
            'high_volume': [h[0] for h in hours_by_volume[:6]],
            'best_overall': [h[0] for h in hours_by_combined[:6]]
        }
    
    def classify_hourly_pattern(self, hourly_metrics: Dict[str, Any]) -> str:
        """Classify the overall hourly pattern"""
        if not hourly_metrics:
            return 'unknown'
        
        # Calculate volatility distribution
        volatilities = [metrics['volatility'] for metrics in hourly_metrics.values()]
        vol_std = np.std(volatilities)
        vol_mean = np.mean(volatilities)
        
        if vol_std / vol_mean > 0.5:
            return 'session_dependent'  # High variation between hours
        else:
            return 'session_independent'  # Consistent across hours
    
    def analyze_session_transitions(self, current_time: datetime) -> Dict[str, Any]:
        """
        Analyze upcoming session transitions
        """
        transitions = {
            'next_transition': None,
            'minutes_to_transition': None,
            'transition_type': None,
            'transition_impact': 'unknown'
        }
        
        # Calculate time to next major session transition
        # This would be enhanced with actual session transition logic
        # For now, simplified implementation
        
        current_hour = current_time.hour
        
        # Major transition times (UTC)
        major_transitions = [
            (8, 'london_open'),
            (13, 'ny_open_london_overlap'),
            (17, 'london_close'),
            (22, 'ny_close_asian_open')
        ]
        
        # Find next transition
        for transition_hour, transition_name in major_transitions:
            if current_hour < transition_hour:
                minutes_to = (transition_hour - current_hour) * 60 - current_time.minute
                transitions['next_transition'] = transition_name
                transitions['minutes_to_transition'] = minutes_to
                transitions['transition_impact'] = self.get_transition_impact(transition_name)
                break
        
        return transitions
    
    def get_transition_impact(self, transition_name: str) -> str:
        """Get expected impact of session transition"""
        if self.market_type == 'forex':
            if 'london_open' in transition_name:
                return 'high_volatility_expected'
            elif 'overlap' in transition_name:
                return 'very_high_activity_expected'
            elif 'close' in transition_name:
                return 'activity_decrease_expected'
            else:
                return 'moderate_change_expected'
        
        elif self.market_type == 'crypto':
            if 'overlap' in transition_name:
                return 'increased_institutional_activity'
            else:
                return 'moderate_activity_change'
        
        return 'unknown'
    
    def get_session_recommendations(self, current_session: Dict[str, Any], 
                                  session_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get session-based trading recommendations"""
        recommendations = []
        
        session_quality = session_analysis['session_quality']
        
        if session_quality > 0.7:
            recommendations.append({
                'recommendation': 'active_trading',
                'reason': f'High quality session for {self.market_type}',
                'confidence': session_quality,
                'market_note': self.get_session_market_note(current_session['primary_session'])
            })
        
        elif session_quality > 0.4:
            recommendations.append({
                'recommendation': 'moderate_trading',
                'reason': f'Moderate session quality for {self.market_type}',
                'confidence': session_quality,
                'market_note': 'Standard trading conditions'
            })
        
        else:
            if self.market_type == 'forex':
                recommendations.append({
                    'recommendation': 'reduced_trading',
                    'reason': 'Low session quality for forex',
                    'confidence': session_quality,
                    'market_note': 'Consider smaller positions or avoid trading'
                })
            else:
                recommendations.append({
                    'recommendation': 'normal_trading',
                    'reason': 'Crypto trades 24/7',
                    'confidence': session_quality + 0.2,  # Boost for crypto
                    'market_note': 'Crypto less dependent on sessions'
                })
        
        return recommendations
    
    def get_session_market_note(self, session_name: str) -> str:
        """Get market-specific note for session"""
        if not session_name:
            return "No active major session"
        
        if self.market_type == 'forex':
            if session_name == 'london_ny_overlap':
                return "Forex peak hours: Highest liquidity and volatility"
            elif session_name == 'london':
                return "London session: EUR/GBP pairs most active"
            elif session_name == 'ny':
                return "NY session: USD pairs most active"
            elif session_name == 'asian':
                return "Asian session: JPY pairs focus, lower volatility"
        
        elif self.market_type == 'crypto':
            if session_name == 'london_ny_overlap':
                return "Crypto institutional hours: Highest volume and institutional activity"
            else:
                return f"Crypto {session_name} session: Continued 24/7 trading"
        
        return f"{session_name} session active"
    
    def calculate_session_signal_strength(self, current_session: Dict[str, Any], 
                                        session_analysis: Dict[str, Any], 
                                        df: pd.DataFrame) -> float:
        """
        Calculate session-based signal strength
        """
        strength_factors = []
        
        # Base session strength
        session_quality = session_analysis['session_quality']
        strength_factors.append(session_quality)
        
        # Active session weight
        total_weight = current_session['total_weight']
        weight_strength = min(total_weight / 3.0, 1.0)  # Normalize
        strength_factors.append(weight_strength)
        
        # Overlap bonus
        if current_session['is_overlap']:
            overlap_bonus = 0.3 * self.overlap_multiplier
            strength_factors.append(overlap_bonus)
        
        # Market-specific session strength
        market_session_strength = self.get_market_session_strength(current_session)
        strength_factors.append(market_session_strength)
        
        # Weekend penalty (for forex)
        if self.market_type == 'forex':
            current_time = datetime.now(timezone.utc)
            if current_time.weekday() >= 5:  # Weekend
                strength_factors.append(self.weekend_penalty)
        
        return np.mean(strength_factors)
    
    def get_market_session_strength(self, current_session: Dict[str, Any]) -> float:
        """Get market-specific session strength"""
        if not current_session['active_sessions']:
            return 0.2
        
        primary_session = current_session['primary_session']
        
        if self.market_type == 'forex':
            session_strengths = {
                'london_ny_overlap': 1.0,
                'london': 0.8,
                'ny': 0.8,
                'asian': 0.4
            }
            return session_strengths.get(primary_session, 0.5)
        
        elif self.market_type == 'crypto':
            # Crypto is less session-dependent but still has preferences
            session_strengths = {
                'london_ny_overlap': 0.9,
                'london': 0.8,
                'ny': 0.8,
                'asian': 0.7
            }
            return session_strengths.get(primary_session, 0.7)
        
        return 0.6
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        current_time = datetime.now(timezone.utc)
        current_session = self.identify_current_session(current_time)
        
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'current_session_info': current_session,
            'session_performance_data_points': len(self.session_performance),
            'session_transitions_tracked': len(self.session_transitions),
            'last_signal_strength': self.get_signal_strength(),
            'session_importance': self.session_importance,
            'configuration': {
                'sessions': self.sessions,
                'overlap_multiplier': self.overlap_multiplier,
                'weekend_penalty': self.weekend_penalty
            }
        }
    
    def is_optimal_trading_time(self) -> bool:
        """Check if current time is optimal for trading"""
        current_time = datetime.now(timezone.utc)
        session_info = self.identify_current_session(current_time)
        
        if self.market_type == 'forex':
            # Forex optimal times
            return session_info['total_weight'] > 1.5
        elif self.market_type == 'crypto':
            # Crypto is more forgiving
            return session_info['total_weight'] > 1.0
        
        return True
    
    def requires_continuous_processing(self) -> bool:
        """Session agent benefits from continuous processing for time updates"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for session updates"""
        try:
            current_time = datetime.now(timezone.utc)
            current_session = self.identify_current_session(current_time)
            
            # Check for session changes
            if hasattr(self, '_last_session_info'):
                if current_session['primary_session'] != self._last_session_info['primary_session']:
                    # Session transition occurred
                    self.logger.info(f"Session transition: {self._last_session_info['primary_session']} → {current_session['primary_session']}")
                    
                    self.publish("session_transition", {
                        'from_session': self._last_session_info['primary_session'],
                        'to_session': current_session['primary_session'],
                        'market_type': self.market_type
                    })
            
            self._last_session_info = current_session
            
        except Exception as e:
            self.logger.error(f"Error in session continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval for continuous updates"""
        return 300.0  # Check every 5 minutes for session changes