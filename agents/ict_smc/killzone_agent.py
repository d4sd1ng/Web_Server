"""
Killzone Agent
Analyzes trading killzones and session-based opportunities
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import pytz

from agents.base_agent import ICTSMCAgent


class KillzoneAgent(ICTSMCAgent):
    """
    Specialized agent for Killzone analysis
    Uses existing killzone functions from utils.py and tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("killzone", config)
        
        # Killzone configuration
        self.killzones = config.get('killzones', [
            {'name': 'London', 'start': '08:00', 'end': '12:00', 'timezone': 'Europe/London', 'weight': 1.0},
            {'name': 'New York', 'start': '13:00', 'end': '17:00', 'timezone': 'America/New_York', 'weight': 1.0},
            {'name': 'Asian', 'start': '22:00', 'end': '02:00', 'timezone': 'Asia/Tokyo', 'weight': 0.7},
            {'name': 'London-NY Overlap', 'start': '13:00', 'end': '14:00', 'timezone': 'Europe/London', 'weight': 1.5}
        ])
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Killzone tracking
        self.killzone_performance = {}
        self.session_analytics = {}
        self.optimization_data = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Killzone Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific killzone configurations"""
        if self.market_type == 'forex':
            # Forex: Session timing is critical
            self.session_importance = 1.0
            self.overlap_bonus = 0.5  # London-NY overlap very important
            
            # Adjust killzone weights for forex
            for kz in self.killzones:
                if 'overlap' in kz['name'].lower():
                    kz['weight'] *= 1.5  # Boost overlap importance
                elif 'london' in kz['name'].lower():
                    kz['weight'] *= 1.2  # London important for forex
                elif 'new york' in kz['name'].lower():
                    kz['weight'] *= 1.2  # NY important for forex
        
        elif self.market_type == 'crypto':
            # Crypto: 24/7 market, but some sessions still matter
            self.session_importance = 0.6
            self.overlap_bonus = 0.3  # Less critical for crypto
            
            # Crypto trades 24/7 but still has preferred times
            for kz in self.killzones:
                if 'asian' in kz['name'].lower():
                    kz['weight'] *= 1.1  # Asia important for crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to analyze killzones
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame), 'symbol', and optional 'current_time'
            
        Returns:
            Dictionary with killzone analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        current_time = data.get('current_time', datetime.now(timezone.utc))
        
        try:
            # Get current killzone status
            killzone_status = self.is_in_killzone(current_time, return_details=True)
            
            # Analyze killzone performance
            performance_analysis = self.analyze_killzone_performance(df, symbol)
            
            # Get session analytics
            session_analytics = self.get_session_analytics(df, current_time)
            
            # Calculate killzone quality
            killzone_quality = self.calculate_killzone_quality(killzone_status, performance_analysis, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_killzone_signal_strength(killzone_status, killzone_quality, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': current_time.isoformat(),
                'killzone_status': killzone_status,
                'performance_analysis': performance_analysis,
                'session_analytics': session_analytics,
                'killzone_quality': killzone_quality,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_recommendations': self.get_killzone_recommendations(
                    killzone_status, killzone_quality, session_analytics
                )
            }
            
            # Publish killzone signals
            if killzone_status['in_killzone']:
                self.publish("killzone_active", {
                    'symbol': symbol,
                    'active_killzones': killzone_status['active_killzones'],
                    'killzone_quality': killzone_quality,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing killzone data for {symbol}: {e}")
            return {'killzone_status': {}, 'signal_strength': 0.0, 'error': str(e)}
    
    def is_in_killzone(self, current_time: datetime = None, return_details: bool = False) -> Dict[str, Any]:
        """
        Check if current time is in any killzone
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        active_killzones = []
        total_weight = 0.0
        
        for killzone in self.killzones:
            if self.is_time_in_killzone(current_time, killzone):
                # Apply market-specific weight adjustments
                adjusted_weight = self.adjust_killzone_weight_for_market(killzone)
                
                active_killzones.append({
                    'name': killzone['name'],
                    'weight': adjusted_weight,
                    'original_weight': killzone['weight'],
                    'start': killzone['start'],
                    'end': killzone['end'],
                    'timezone': killzone['timezone']
                })
                total_weight += adjusted_weight
        
        in_killzone = len(active_killzones) > 0
        killzone_quality = min(total_weight, 2.0) / 2.0  # Normalize to 0-1
        
        if return_details:
            return {
                'in_killzone': in_killzone,
                'active_killzones': active_killzones,
                'total_weight': total_weight,
                'killzone_quality': killzone_quality,
                'current_time': current_time.isoformat(),
                'market_type': self.market_type
            }
        
        return {'in_killzone': in_killzone}
    
    def is_time_in_killzone(self, current_time: datetime, killzone: Dict[str, Any]) -> bool:
        """Check if specific time is in a killzone"""
        try:
            # Convert to killzone timezone
            kz_timezone = pytz.timezone(killzone['timezone'])
            kz_time = current_time.astimezone(kz_timezone)
            
            start_hour, start_minute = map(int, killzone['start'].split(':'))
            end_hour, end_minute = map(int, killzone['end'].split(':'))
            
            current_minutes = kz_time.hour * 60 + kz_time.minute
            start_minutes = start_hour * 60 + start_minute
            end_minutes = end_hour * 60 + end_minute
            
            # Handle overnight sessions (e.g., Asian session)
            if end_minutes < start_minutes:  # Crosses midnight
                return current_minutes >= start_minutes or current_minutes <= end_minutes
            else:
                return start_minutes <= current_minutes <= end_minutes
            
        except Exception as e:
            self.logger.warning(f"Error checking killzone time: {e}")
            return False
    
    def adjust_killzone_weight_for_market(self, killzone: Dict[str, Any]) -> float:
        """Adjust killzone weight based on market type"""
        base_weight = killzone['weight']
        
        if self.market_type == 'forex':
            # Forex: Session timing very important
            if 'overlap' in killzone['name'].lower():
                return base_weight * 1.5
            elif 'london' in killzone['name'].lower() or 'new york' in killzone['name'].lower():
                return base_weight * 1.2
            else:
                return base_weight * 0.8
        
        elif self.market_type == 'crypto':
            # Crypto: 24/7 but some sessions still preferred
            if 'overlap' in killzone['name'].lower():
                return base_weight * 1.2  # Still important but less than forex
            elif 'asian' in killzone['name'].lower():
                return base_weight * 1.1  # Asia important for crypto
            else:
                return base_weight
        
        return base_weight
    
    def analyze_killzone_performance(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze killzone performance using historical data
        """
        if len(df) < 50:
            return {'insufficient_data': True}
        
        performance = {
            'total_bars_analyzed': len(df),
            'killzone_bars': 0,
            'non_killzone_bars': 0,
            'killzone_performance': {},
            'session_breakdown': {}
        }
        
        # Analyze each bar for killzone status
        for i in range(len(df)):
            try:
                bar_time = df.index[i]
                if hasattr(bar_time, 'to_pydatetime'):
                    bar_time = bar_time.to_pydatetime()
                
                kz_status = self.is_in_killzone(bar_time, return_details=True)
                
                if kz_status['in_killzone']:
                    performance['killzone_bars'] += 1
                    
                    # Track performance by killzone
                    for active_kz in kz_status['active_killzones']:
                        kz_name = active_kz['name']
                        if kz_name not in performance['killzone_performance']:
                            performance['killzone_performance'][kz_name] = {
                                'bars_count': 0,
                                'avg_volume': 0,
                                'avg_volatility': 0
                            }
                        
                        performance['killzone_performance'][kz_name]['bars_count'] += 1
                        
                        if 'volume' in df.columns:
                            performance['killzone_performance'][kz_name]['avg_volume'] += df['volume'].iloc[i]
                        
                        if 'atr' in df.columns:
                            performance['killzone_performance'][kz_name]['avg_volatility'] += df['atr'].iloc[i]
                
                else:
                    performance['non_killzone_bars'] += 1
            
            except Exception as e:
                self.logger.warning(f"Error analyzing bar {i}: {e}")
                continue
        
        # Calculate averages
        for kz_name, kz_perf in performance['killzone_performance'].items():
            if kz_perf['bars_count'] > 0:
                kz_perf['avg_volume'] /= kz_perf['bars_count']
                kz_perf['avg_volatility'] /= kz_perf['bars_count']
        
        return performance
    
    def get_session_analytics(self, df: pd.DataFrame, current_time: datetime) -> Dict[str, Any]:
        """Get detailed session analytics"""
        analytics = {
            'current_session': self.identify_current_session(current_time),
            'session_transition': self.check_session_transition(current_time),
            'optimal_trading_hours': self.get_optimal_trading_hours(),
            'market_type_adjustments': self.get_market_type_session_adjustments()
        }
        
        return analytics
    
    def identify_current_session(self, current_time: datetime) -> str:
        """Identify current trading session"""
        # Convert to major timezone for session identification
        london_time = current_time.astimezone(pytz.timezone('Europe/London'))
        ny_time = current_time.astimezone(pytz.timezone('America/New_York'))
        tokyo_time = current_time.astimezone(pytz.timezone('Asia/Tokyo'))
        
        london_hour = london_time.hour
        ny_hour = ny_time.hour
        tokyo_hour = tokyo_time.hour
        
        # Session identification
        if 8 <= london_hour <= 17 and 8 <= ny_hour <= 17:
            return 'london_ny_overlap'
        elif 8 <= london_hour <= 17:
            return 'london_session'
        elif 8 <= ny_hour <= 17:
            return 'ny_session'
        elif 9 <= tokyo_hour <= 18:
            return 'asian_session'
        else:
            return 'off_hours'
    
    def check_session_transition(self, current_time: datetime) -> Dict[str, Any]:
        """Check for upcoming session transitions"""
        transitions = {
            'upcoming_transition': None,
            'minutes_to_transition': None,
            'transition_type': None
        }
        
        # This would be enhanced with actual session transition logic
        # For now, simplified implementation
        
        return transitions
    
    def get_optimal_trading_hours(self) -> Dict[str, Any]:
        """Get optimal trading hours based on market type"""
        if self.market_type == 'forex':
            return {
                'primary_hours': ['London-NY Overlap (13:00-16:00 UTC)', 'London Session (08:00-17:00 UTC)'],
                'secondary_hours': ['NY Session (13:00-22:00 UTC)'],
                'avoid_hours': ['Asian Session (22:00-06:00 UTC)'],
                'best_overlap': 'London-NY (13:00-16:00 UTC)',
                'market_note': 'Forex most active during European/US business hours'
            }
        elif self.market_type == 'crypto':
            return {
                'primary_hours': ['24/7 Trading Available'],
                'secondary_hours': ['London-NY Overlap still preferred'],
                'avoid_hours': ['None - but lower volume during weekends'],
                'best_overlap': 'London-NY (13:00-16:00 UTC) for highest volume',
                'market_note': 'Crypto trades 24/7 but volume peaks during traditional market hours'
            }
        
        return {}
    
    def get_market_type_session_adjustments(self) -> Dict[str, Any]:
        """Get market-specific session adjustments"""
        adjustments = {}
        
        if self.market_type == 'forex':
            adjustments = {
                'session_multiplier': 1.0,
                'overlap_importance': 'critical',
                'weekend_trading': False,
                'news_impact': 'high',
                'central_bank_hours': 'monitor_closely'
            }
        elif self.market_type == 'crypto':
            adjustments = {
                'session_multiplier': 0.7,
                'overlap_importance': 'moderate',
                'weekend_trading': True,
                'news_impact': 'medium',
                'whale_activity': 'monitor_24_7'
            }
        
        return adjustments
    
    def calculate_killzone_quality(self, killzone_status: Dict[str, Any], 
                                 performance_analysis: Dict[str, Any], 
                                 df: pd.DataFrame) -> float:
        """
        Calculate killzone quality score
        """
        if not killzone_status.get('in_killzone', False):
            return 0.0
        
        quality_factors = []
        
        # Base killzone weight
        total_weight = killzone_status.get('total_weight', 0.0)
        weight_quality = min(total_weight / 2.0, 1.0)  # Normalize
        quality_factors.append(weight_quality)
        
        # Historical performance
        if not performance_analysis.get('insufficient_data', False):
            killzone_bars = performance_analysis.get('killzone_bars', 0)
            total_bars = performance_analysis.get('total_bars_analyzed', 1)
            historical_quality = killzone_bars / total_bars
            quality_factors.append(historical_quality)
        
        # Volume confirmation (for crypto)
        if self.market_type == 'crypto' and 'volume' in df.columns:
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_quality = min(current_volume / avg_volume, 2.0) / 2.0
            quality_factors.append(volume_quality * 0.5)
        
        # Session alignment (for forex)
        if self.market_type == 'forex':
            session_quality = self.calculate_forex_session_quality(killzone_status)
            quality_factors.append(session_quality)
        
        return np.mean(quality_factors) if quality_factors else 0.0
    
    def calculate_forex_session_quality(self, killzone_status: Dict[str, Any]) -> float:
        """Calculate session quality for forex"""
        active_killzones = killzone_status.get('active_killzones', [])
        
        # Check for high-impact sessions
        for kz in active_killzones:
            if 'overlap' in kz['name'].lower():
                return 0.95  # London-NY overlap is highest quality
            elif 'london' in kz['name'].lower() or 'new york' in kz['name'].lower():
                return 0.85  # Major sessions are high quality
        
        return 0.6  # Other sessions
    
    def get_killzone_recommendations(self, killzone_status: Dict[str, Any], 
                                   killzone_quality: float, 
                                   session_analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get killzone-based trading recommendations"""
        recommendations = []
        
        if killzone_status.get('in_killzone', False):
            # Active killzone recommendations
            for kz in killzone_status.get('active_killzones', []):
                recommendation = {
                    'killzone': kz['name'],
                    'recommendation': 'active_trading',
                    'quality_score': killzone_quality,
                    'weight': kz['weight'],
                    'market_specific_note': self.get_killzone_market_note(kz['name'])
                }
                recommendations.append(recommendation)
        
        else:
            # No active killzone
            recommendations.append({
                'killzone': 'none',
                'recommendation': 'reduced_trading' if self.market_type == 'forex' else 'normal_trading',
                'quality_score': 0.0,
                'market_specific_note': self.get_off_hours_note()
            })
        
        return recommendations
    
    def get_killzone_market_note(self, killzone_name: str) -> str:
        """Get market-specific note for killzone"""
        if self.market_type == 'forex':
            if 'overlap' in killzone_name.lower():
                return "Forex London-NY overlap: Highest liquidity and volatility. Best trading opportunities."
            elif 'london' in killzone_name.lower():
                return "Forex London session: High activity, good for EUR/GBP pairs."
            elif 'new york' in killzone_name.lower():
                return "Forex NY session: USD pairs most active, good liquidity."
            elif 'asian' in killzone_name.lower():
                return "Forex Asian session: Lower volatility, good for JPY pairs."
        
        elif self.market_type == 'crypto':
            if 'overlap' in killzone_name.lower():
                return "Crypto London-NY overlap: Highest volume period, institutional activity."
            elif 'london' in killzone_name.lower():
                return "Crypto London session: European institutional activity, good volume."
            elif 'new york' in killzone_name.lower():
                return "Crypto NY session: US institutional activity, strong moves."
            elif 'asian' in killzone_name.lower():
                return "Crypto Asian session: Asian market activity, different trading patterns."
        
        return f"{killzone_name} active for {self.market_type} trading"
    
    def get_off_hours_note(self) -> str:
        """Get note for off-hours trading"""
        if self.market_type == 'forex':
            return "Forex off-hours: Reduced liquidity and volatility. Consider smaller positions."
        elif self.market_type == 'crypto':
            return "Crypto off-hours: Still tradeable 24/7 but potentially lower institutional volume."
        
        return "Outside major trading sessions"
    
    def calculate_killzone_signal_strength(self, killzone_status: Dict[str, Any], 
                                         killzone_quality: float, df: pd.DataFrame) -> float:
        """
        Calculate killzone signal strength
        """
        if not killzone_status.get('in_killzone', False):
            return 0.0
        
        strength_factors = []
        
        # Base killzone strength
        base_strength = 0.6
        strength_factors.append(base_strength)
        
        # Quality factor
        strength_factors.append(killzone_quality)
        
        # Weight factor
        total_weight = killzone_status.get('total_weight', 0.0)
        weight_strength = min(total_weight / 2.0, 1.0)
        strength_factors.append(weight_strength)
        
        # Market-specific adjustments
        if self.market_type == 'forex':
            # Forex gets bonus during major sessions
            active_kzs = killzone_status.get('active_killzones', [])
            if any('overlap' in kz['name'].lower() for kz in active_kzs):
                strength_factors.append(0.9)  # High bonus for overlap
        
        elif self.market_type == 'crypto':
            # Crypto gets volume-based adjustment
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                volume_adjustment = min(vol_ratio / 2.0, 1.0) * 0.3
                strength_factors.append(volume_adjustment)
        
        return np.mean(strength_factors)
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_killzone_summary(self) -> Dict[str, Any]:
        """Get comprehensive killzone summary"""
        current_status = self.is_in_killzone(return_details=True)
        
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'current_killzone_status': current_status,
            'configured_killzones': len(self.killzones),
            'performance_data_points': len(self.optimization_data),
            'last_signal_strength': self.get_signal_strength(),
            'session_importance': self.session_importance,
            'configuration': {
                'killzones': self.killzones,
                'overlap_bonus': self.overlap_bonus
            }
        }
    
    def should_trade_in_killzone(self, base_probability: float, killzone_quality: float, 
                               threshold: float = 0.5) -> float:
        """
        Determine if trading should occur based on killzone analysis
        """
        # Adjust probability based on killzone quality
        adjusted_probability = base_probability * (0.5 + killzone_quality * 0.5)
        
        # Market-specific adjustments
        if self.market_type == 'forex':
            # Forex requires killzone for good trades
            if killzone_quality < 0.3:
                adjusted_probability *= 0.5  # Penalize off-session forex trades
        elif self.market_type == 'crypto':
            # Crypto is more forgiving of off-hours trading
            if killzone_quality < 0.3:
                adjusted_probability *= 0.8  # Smaller penalty for crypto
        
        return adjusted_probability if adjusted_probability > threshold else 0.0
    
    def requires_continuous_processing(self) -> bool:
        """Killzone agent benefits from continuous processing for time-based updates"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for killzone updates"""
        try:
            # Check for killzone transitions
            current_time = datetime.now(timezone.utc)
            current_status = self.is_in_killzone(current_time, return_details=True)
            
            # Check if killzone status changed
            if hasattr(self, '_last_killzone_status'):
                if current_status['in_killzone'] != self._last_killzone_status['in_killzone']:
                    # Killzone transition occurred
                    if current_status['in_killzone']:
                        self.logger.info("Entered killzone")
                        self.publish("killzone_entered", current_status)
                    else:
                        self.logger.info("Exited killzone")
                        self.publish("killzone_exited", self._last_killzone_status)
            
            self._last_killzone_status = current_status
            
        except Exception as e:
            self.logger.error(f"Error in killzone continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval for continuous updates"""
        return 60.0  # Check every minute for session changes