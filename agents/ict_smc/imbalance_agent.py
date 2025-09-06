"""
Imbalance Agent
Detects price imbalances and inefficiencies
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class ImbalanceAgent(ICTSMCAgent):
    """
    Specialized agent for Price Imbalance detection
    Identifies market inefficiencies and gap areas
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("imbalance", config)
        
        # Imbalance configuration
        self.min_gap_size = config.get('min_gap_size', 0.001)  # 0.1%
        self.max_gap_age = config.get('max_gap_age', 20)  # bars
        self.fill_threshold = config.get('fill_threshold', 0.5)  # 50% fill to consider filled
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Imbalance tracking
        self.active_imbalances = []
        self.filled_imbalances = []
        self.imbalance_statistics = {}
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Imbalance Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific imbalance configuration"""
        if self.market_type == 'forex':
            # Forex: Smaller gaps, longer fill times
            self.min_gap_size = max(self.min_gap_size, 0.0005)  # 0.05%
            self.max_gap_age = max(self.max_gap_age, 30)
            self.gap_significance = 'high'  # Gaps more significant in forex
        elif self.market_type == 'crypto':
            # Crypto: Larger gaps, faster fill times
            self.min_gap_size = min(self.min_gap_size, 0.002)   # 0.2%
            self.max_gap_age = min(self.max_gap_age, 15)
            self.gap_significance = 'medium'  # Gaps less significant in crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect imbalances
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with imbalance analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < 3:
            return {'imbalances': [], 'signal_strength': 0.0}
        
        try:
            # Detect new imbalances
            new_imbalances = self.detect_imbalances(df)
            
            # Update existing imbalances
            self.update_imbalance_status(df)
            
            # Analyze imbalance patterns
            imbalance_analysis = self.analyze_imbalance_patterns(df)
            
            # Calculate signal strength
            signal_strength = self.calculate_imbalance_signal_strength(new_imbalances, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'new_imbalances': new_imbalances,
                'active_imbalances': self.active_imbalances,
                'filled_imbalances': self.filled_imbalances[-10:],  # Recent fills
                'imbalance_analysis': imbalance_analysis,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'fill_opportunities': self.identify_fill_opportunities(df)
            }
            
            # Publish imbalance signals
            if new_imbalances:
                self.publish("imbalance_detected", {
                    'symbol': symbol,
                    'new_imbalances': new_imbalances,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing imbalance data for {symbol}: {e}")
            return {'imbalances': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_imbalances(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect price imbalances (gaps) in the data
        """
        imbalances = []
        
        if len(df) < 2:
            return imbalances
        
        for i in range(1, len(df)):
            prev_bar = df.iloc[i-1]
            curr_bar = df.iloc[i]
            
            # Check for gap up (imbalance above)
            if curr_bar['low'] > prev_bar['high']:
                gap_size = (curr_bar['low'] - prev_bar['high']) / prev_bar['high']
                
                if gap_size >= self.min_gap_size:
                    imbalance = {
                        'type': 'gap_up',
                        'gap_low': prev_bar['high'],
                        'gap_high': curr_bar['low'],
                        'gap_size': gap_size,
                        'gap_size_pct': gap_size * 100,
                        'created_at': curr_bar.name if hasattr(curr_bar, 'name') else i,
                        'index': i,
                        'filled': False,
                        'fill_percentage': 0.0,
                        'market_context': self.get_imbalance_context(df, i, 'gap_up')
                    }
                    imbalances.append(imbalance)
            
            # Check for gap down (imbalance below)
            elif curr_bar['high'] < prev_bar['low']:
                gap_size = (prev_bar['low'] - curr_bar['high']) / curr_bar['high']
                
                if gap_size >= self.min_gap_size:
                    imbalance = {
                        'type': 'gap_down',
                        'gap_low': curr_bar['high'],
                        'gap_high': prev_bar['low'],
                        'gap_size': gap_size,
                        'gap_size_pct': gap_size * 100,
                        'created_at': curr_bar.name if hasattr(curr_bar, 'name') else i,
                        'index': i,
                        'filled': False,
                        'fill_percentage': 0.0,
                        'market_context': self.get_imbalance_context(df, i, 'gap_down')
                    }
                    imbalances.append(imbalance)
        
        # Add new imbalances to active list
        for imbalance in imbalances:
            if imbalance not in self.active_imbalances:
                self.active_imbalances.append(imbalance)
        
        return imbalances
    
    def get_imbalance_context(self, df: pd.DataFrame, index: int, gap_type: str) -> Dict[str, Any]:
        """Get context for imbalance creation"""
        context = {
            'market_type': self.market_type,
            'volume_context': 'normal',
            'session_context': 'unknown',
            'trend_context': 'neutral'
        }
        
        # Volume context
        if 'volume' in df.columns:
            gap_volume = df['volume'].iloc[index]
            avg_volume = df['volume'].rolling(20).mean().iloc[index]
            
            if gap_volume > avg_volume * 2:
                context['volume_context'] = 'high_volume_gap'
            elif gap_volume < avg_volume * 0.5:
                context['volume_context'] = 'low_volume_gap'
        
        # Session context (for forex)
        if self.market_type == 'forex' and hasattr(df.index[index], 'hour'):
            hour = df.index[index].hour
            if hour < 8 or hour > 22:
                context['session_context'] = 'weekend_or_overnight_gap'
            else:
                context['session_context'] = 'session_gap'
        
        # Trend context
        if len(df) >= index + 10:
            recent_data = df.iloc[max(0, index-10):index+10]
            if recent_data['close'].iloc[-1] > recent_data['close'].iloc[0]:
                context['trend_context'] = 'uptrend'
            elif recent_data['close'].iloc[-1] < recent_data['close'].iloc[0]:
                context['trend_context'] = 'downtrend'
        
        return context
    
    def update_imbalance_status(self, df: pd.DataFrame):
        """Update status of existing imbalances"""
        current_price = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        still_active = []
        
        for imbalance in self.active_imbalances:
            # Check if imbalance has been filled
            fill_status = self.check_imbalance_fill(imbalance, current_price, current_high, current_low)
            
            if fill_status['filled']:
                # Move to filled imbalances
                imbalance.update(fill_status)
                imbalance['filled_at'] = datetime.now(timezone.utc)
                self.filled_imbalances.append(imbalance)
                
                self.logger.info(f"Imbalance filled: {imbalance['type']} at {imbalance['gap_low']:.6f}-{imbalance['gap_high']:.6f}")
                
                # Publish fill event
                self.publish("imbalance_filled", {
                    'imbalance': imbalance,
                    'market_type': self.market_type
                })
            
            else:
                # Check if imbalance is too old
                if self.is_imbalance_expired(imbalance, df):
                    imbalance['expired'] = True
                    imbalance['expired_at'] = datetime.now(timezone.utc)
                    self.filled_imbalances.append(imbalance)
                else:
                    # Update fill percentage
                    imbalance.update(fill_status)
                    still_active.append(imbalance)
        
        self.active_imbalances = still_active
        
        # Limit filled imbalances history
        if len(self.filled_imbalances) > 100:
            self.filled_imbalances = self.filled_imbalances[-100:]
    
    def check_imbalance_fill(self, imbalance: Dict[str, Any], current_price: float, 
                           current_high: float, current_low: float) -> Dict[str, Any]:
        """Check if imbalance has been filled"""
        gap_low = imbalance['gap_low']
        gap_high = imbalance['gap_high']
        gap_range = gap_high - gap_low
        
        # Determine how much of the gap has been filled
        if gap_range == 0:
            return {'filled': True, 'fill_percentage': 100.0}
        
        # Calculate fill based on price penetration into gap
        if imbalance['type'] == 'gap_up':
            # For gap up, check how far price has moved down into the gap
            if current_low <= gap_low:
                fill_percentage = 100.0  # Completely filled
            elif current_low < gap_high:
                fill_percentage = (gap_high - current_low) / gap_range * 100
            else:
                fill_percentage = 0.0
        
        else:  # gap_down
            # For gap down, check how far price has moved up into the gap
            if current_high >= gap_high:
                fill_percentage = 100.0  # Completely filled
            elif current_high > gap_low:
                fill_percentage = (current_high - gap_low) / gap_range * 100
            else:
                fill_percentage = 0.0
        
        # Consider filled if above threshold
        filled = fill_percentage >= self.fill_threshold * 100
        
        return {
            'filled': filled,
            'fill_percentage': fill_percentage,
            'fill_price': current_price
        }
    
    def is_imbalance_expired(self, imbalance: Dict[str, Any], df: pd.DataFrame) -> bool:
        """Check if imbalance has expired due to age"""
        imbalance_index = imbalance['index']
        current_index = len(df) - 1
        
        age_in_bars = current_index - imbalance_index
        return age_in_bars > self.max_gap_age
    
    def analyze_imbalance_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze patterns in imbalance behavior
        """
        analysis = {
            'total_imbalances': len(self.active_imbalances) + len(self.filled_imbalances),
            'active_imbalances': len(self.active_imbalances),
            'fill_rate': 0.0,
            'avg_fill_time': 0.0,
            'gap_bias': 'neutral'
        }
        
        if not self.filled_imbalances:
            return analysis
        
        # Calculate fill rate
        total_created = analysis['total_imbalances']
        filled_count = len([imb for imb in self.filled_imbalances if imb.get('filled', False)])
        analysis['fill_rate'] = filled_count / total_created if total_created > 0 else 0
        
        # Calculate average fill time
        fill_times = []
        for imbalance in self.filled_imbalances:
            if 'filled_at' in imbalance and 'created_at' in imbalance:
                fill_time = (imbalance['filled_at'] - imbalance['created_at']).total_seconds() / 3600
                fill_times.append(fill_time)
        
        analysis['avg_fill_time'] = np.mean(fill_times) if fill_times else 0
        
        # Determine gap bias
        gap_ups = len([imb for imb in self.filled_imbalances if imb['type'] == 'gap_up'])
        gap_downs = len([imb for imb in self.filled_imbalances if imb['type'] == 'gap_down'])
        
        if gap_ups > gap_downs:
            analysis['gap_bias'] = 'gap_up_dominant'
        elif gap_downs > gap_ups:
            analysis['gap_bias'] = 'gap_down_dominant'
        
        return analysis
    
    def identify_fill_opportunities(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Identify opportunities to trade imbalance fills
        """
        opportunities = []
        current_price = df['close'].iloc[-1]
        
        if 'atr' not in df.columns:
            return opportunities
        
        current_atr = df['atr'].iloc[-1]
        
        for imbalance in self.active_imbalances:
            gap_low = imbalance['gap_low']
            gap_high = imbalance['gap_high']
            
            # Check proximity to gap
            distance_to_gap = min(abs(current_price - gap_low), abs(current_price - gap_high))
            
            if distance_to_gap <= 2.0 * current_atr:  # Within 2 ATR of gap
                opportunity = {
                    'imbalance_type': imbalance['type'],
                    'gap_range': (gap_low, gap_high),
                    'distance': distance_to_gap,
                    'opportunity_type': self.classify_fill_opportunity(imbalance, current_price),
                    'trade_direction': self.get_fill_trade_direction(imbalance, current_price),
                    'market_context': self.get_fill_market_context(imbalance, df)
                }
                opportunities.append(opportunity)
        
        return opportunities
    
    def classify_fill_opportunity(self, imbalance: Dict[str, Any], current_price: float) -> str:
        """Classify the type of fill opportunity"""
        gap_low = imbalance['gap_low']
        gap_high = imbalance['gap_high']
        gap_mid = (gap_low + gap_high) / 2
        
        if imbalance['type'] == 'gap_up':
            if current_price > gap_high:
                return 'approaching_from_above'
            elif current_price > gap_mid:
                return 'partial_fill_continuation'
            else:
                return 'full_fill_opportunity'
        
        else:  # gap_down
            if current_price < gap_low:
                return 'approaching_from_below'
            elif current_price < gap_mid:
                return 'partial_fill_continuation'
            else:
                return 'full_fill_opportunity'
    
    def get_fill_trade_direction(self, imbalance: Dict[str, Any], current_price: float) -> str:
        """Get recommended trade direction for gap fill"""
        gap_low = imbalance['gap_low']
        gap_high = imbalance['gap_high']
        
        if imbalance['type'] == 'gap_up':
            # Gap up - expect price to move down to fill
            if current_price > gap_high:
                return 'short'  # Trade down into the gap
            else:
                return 'neutral'  # Already in gap
        
        else:  # gap_down
            # Gap down - expect price to move up to fill
            if current_price < gap_low:
                return 'long'  # Trade up into the gap
            else:
                return 'neutral'  # Already in gap
    
    def get_fill_market_context(self, imbalance: Dict[str, Any], df: pd.DataFrame) -> str:
        """Get market context for gap fill"""
        context = imbalance.get('market_context', {})
        
        if self.market_type == 'forex':
            if context.get('session_context') == 'weekend_or_overnight_gap':
                return "Forex weekend/overnight gap - high probability fill during session"
            else:
                return "Forex intraday gap - moderate fill probability"
        
        elif self.market_type == 'crypto':
            volume_context = context.get('volume_context', 'normal')
            if volume_context == 'high_volume_gap':
                return "Crypto high-volume gap - strong momentum, slower fill"
            elif volume_context == 'low_volume_gap':
                return "Crypto low-volume gap - fast fill likely"
            else:
                return "Crypto standard gap - normal fill probability"
        
        return "Standard gap fill opportunity"
    
    def calculate_imbalance_signal_strength(self, new_imbalances: List[Dict[str, Any]], df: pd.DataFrame) -> float:
        """
        Calculate imbalance signal strength
        """
        if not new_imbalances and not self.active_imbalances:
            return 0.0
        
        strength_factors = []
        
        # New imbalance strength
        if new_imbalances:
            avg_gap_size = np.mean([imb['gap_size'] for imb in new_imbalances])
            gap_strength = min(avg_gap_size / 0.01, 1.0)  # Normalize to 1% gap
            strength_factors.append(gap_strength)
        
        # Active imbalance strength
        if self.active_imbalances:
            active_strength = min(len(self.active_imbalances) / 5.0, 1.0)
            strength_factors.append(active_strength)
        
        # Market-specific strength
        market_strength = self.get_market_imbalance_strength(df)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_market_imbalance_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific imbalance strength"""
        if self.market_type == 'forex':
            # Forex gaps are more significant
            base_strength = 0.8
            
            # Session timing affects strength
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if hour < 8 or hour > 22:  # Overnight
                    base_strength *= 1.2  # Overnight gaps more significant
            
            return min(base_strength, 1.0)
        
        elif self.market_type == 'crypto':
            # Crypto gaps less significant due to 24/7 trading
            base_strength = 0.6
            
            # Volume affects significance
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(vol_ratio / 3.0, 1.0)
                base_strength += volume_factor * 0.3
            
            return min(base_strength, 1.0)
        
        return 0.7
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_imbalance_summary(self) -> Dict[str, Any]:
        """Get comprehensive imbalance summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'active_imbalances_count': len(self.active_imbalances),
            'filled_imbalances_count': len(self.filled_imbalances),
            'imbalance_analysis': self.analyze_imbalance_patterns(pd.DataFrame()),  # Empty df for analysis
            'gap_significance': self.gap_significance,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'min_gap_size': self.min_gap_size,
                'max_gap_age': self.max_gap_age,
                'fill_threshold': self.fill_threshold
            }
        }
    
    def get_active_gaps_near_price(self, price: float, atr: float) -> List[Dict[str, Any]]:
        """Get active gaps near specified price"""
        nearby_gaps = []
        
        for imbalance in self.active_imbalances:
            gap_low = imbalance['gap_low']
            gap_high = imbalance['gap_high']
            
            # Check if gap is within reasonable distance
            distance_to_gap = min(abs(price - gap_low), abs(price - gap_high))
            
            if distance_to_gap <= 3.0 * atr:
                imbalance['distance_to_price'] = distance_to_gap
                nearby_gaps.append(imbalance)
        
        # Sort by distance
        nearby_gaps.sort(key=lambda x: x['distance_to_price'])
        
        return nearby_gaps
    
    def requires_continuous_processing(self) -> bool:
        """Imbalance agent doesn't need continuous processing"""
        return False