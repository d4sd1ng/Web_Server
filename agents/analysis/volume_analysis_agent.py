"""
Volume Analysis Agent
Analyzes volume patterns and spikes using existing functions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class VolumeAnalysisAgent(BaseAgent):
    """
    Specialized agent for Volume analysis
    Uses existing check_volume_spike() and volume analysis functions
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("volume_analysis", config)
        
        # Volume configuration
        self.spike_threshold = config.get('spike_threshold', 1.5)
        self.volume_ma_period = config.get('volume_ma_period', 20)
        self.extreme_volume_threshold = config.get('extreme_volume_threshold', 3.0)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Volume tracking
        self.volume_spikes = []
        self.volume_patterns = []
        self.accumulation_distribution_data = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Volume Analysis Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific volume configuration"""
        if self.market_type == 'forex':
            # Forex: Volume data is tick volume, less reliable
            self.spike_threshold = max(self.spike_threshold, 2.0)  # Higher threshold
            self.volume_reliability = 0.4  # Lower reliability weight
            self.focus_on_price_action = True
        elif self.market_type == 'crypto':
            # Crypto: Real volume data, very reliable
            self.spike_threshold = min(self.spike_threshold, 1.5)  # Lower threshold
            self.volume_reliability = 0.9  # High reliability weight
            self.focus_on_price_action = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data for volume analysis
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with volume analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or 'volume' not in df.columns:
            return {'volume_analysis': 'no_volume_data', 'signal_strength': 0.0}
        
        try:
            # Check for volume spike using existing function
            volume_spike = self.check_volume_spike(df, self.spike_threshold)
            
            # Analyze volume patterns
            volume_patterns = self.analyze_volume_patterns(df)
            
            # Calculate volume metrics
            volume_metrics = self.calculate_volume_metrics(df)
            
            # Detect accumulation/distribution
            acc_dist = self.detect_accumulation_distribution(df)
            
            # Calculate signal strength
            signal_strength = self.calculate_volume_signal_strength(
                volume_spike, volume_patterns, volume_metrics, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'volume_spike': volume_spike,
                'volume_patterns': volume_patterns,
                'volume_metrics': volume_metrics,
                'accumulation_distribution': acc_dist,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'volume_interpretation': self.interpret_volume_for_market(
                    volume_spike, volume_patterns, df
                )
            }
            
            # Publish volume signals
            if volume_spike:
                self.publish("volume_spike", {
                    'symbol': symbol,
                    'spike_ratio': volume_metrics['current_vs_avg'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing volume data for {symbol}: {e}")
            return {'volume_analysis': 'error', 'signal_strength': 0.0, 'error': str(e)}
    
    def check_volume_spike(self, df: pd.DataFrame, threshold: float = 1.5) -> bool:
        """
        Check for volume spike using existing implementation
        """
        try:
            if df.empty or 'volume' not in df.columns:
                return False
            
            avg_volume = df['volume'].iloc[-10:-1].mean()
            current_volume = df['volume'].iloc[-1]
            
            # Market-specific adjustments
            adjusted_threshold = threshold
            if self.market_type == 'forex':
                adjusted_threshold *= 1.3  # Higher threshold for forex tick volume
            
            return current_volume > adjusted_threshold * avg_volume
            
        except Exception as e:
            self.logger.error(f"Volume spike check failed: {e}")
            return False
    
    def analyze_volume_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume patterns and trends
        """
        if len(df) < 20:
            return {'pattern': 'insufficient_data'}
        
        volume = df['volume']
        
        # Volume trend analysis
        volume_ma_short = volume.rolling(5).mean()
        volume_ma_long = volume.rolling(self.volume_ma_period).mean()
        
        volume_trend = 'neutral'
        if volume_ma_short.iloc[-1] > volume_ma_long.iloc[-1] * 1.1:
            volume_trend = 'increasing'
        elif volume_ma_short.iloc[-1] < volume_ma_long.iloc[-1] * 0.9:
            volume_trend = 'decreasing'
        
        # Volume distribution analysis
        recent_volume = volume.iloc[-20:]
        volume_std = recent_volume.std()
        volume_mean = recent_volume.mean()
        
        # Identify volume spikes in recent history
        spike_count = sum(1 for v in recent_volume if v > volume_mean + 2 * volume_std)
        
        # Volume consistency
        volume_consistency = 1.0 - (volume_std / volume_mean) if volume_mean > 0 else 0.0
        
        patterns = {
            'volume_trend': volume_trend,
            'recent_spike_count': spike_count,
            'volume_consistency': volume_consistency,
            'volume_distribution': self.classify_volume_distribution(recent_volume),
            'current_vs_avg': volume.iloc[-1] / volume_ma_long.iloc[-1] if volume_ma_long.iloc[-1] > 0 else 1.0
        }
        
        return patterns
    
    def classify_volume_distribution(self, volume_series: pd.Series) -> str:
        """Classify volume distribution pattern"""
        if len(volume_series) < 10:
            return 'unknown'
        
        # Calculate percentiles
        q25 = volume_series.quantile(0.25)
        q75 = volume_series.quantile(0.75)
        median = volume_series.median()
        mean = volume_series.mean()
        
        # Classify distribution
        if mean > median * 1.5:
            return 'right_skewed'  # Few high volume spikes
        elif mean < median * 0.7:
            return 'left_skewed'   # Consistently low volume
        elif (q75 - median) / (median - q25) > 2.0:
            return 'spike_heavy'   # Many volume spikes
        else:
            return 'normal'
    
    def calculate_volume_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate comprehensive volume metrics
        """
        if 'volume' not in df.columns or len(df) < 20:
            return {}
        
        volume = df['volume']
        
        metrics = {
            'current_volume': volume.iloc[-1],
            'volume_ma_20': volume.rolling(20).mean().iloc[-1],
            'volume_ma_5': volume.rolling(5).mean().iloc[-1],
            'current_vs_avg': volume.iloc[-1] / volume.rolling(20).mean().iloc[-1],
            'volume_std': volume.rolling(20).std().iloc[-1],
            'volume_cv': volume.rolling(20).std().iloc[-1] / volume.rolling(20).mean().iloc[-1],
            'extreme_volume': volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * self.extreme_volume_threshold
        }
        
        # Market-specific metrics
        if self.market_type == 'crypto':
            # Crypto-specific volume metrics
            metrics['volume_reliability'] = self.volume_reliability
            metrics['whale_activity_indicator'] = metrics['current_vs_avg'] > 5.0
            
            # On-Balance Volume (OBV) for crypto
            if 'close' in df.columns:
                metrics['obv_trend'] = self.calculate_obv_trend(df)
        
        elif self.market_type == 'forex':
            # Forex-specific metrics (tick volume)
            metrics['volume_reliability'] = self.volume_reliability
            metrics['session_volume_context'] = self.get_forex_session_volume_context(df)
        
        return metrics
    
    def calculate_obv_trend(self, df: pd.DataFrame) -> str:
        """Calculate On-Balance Volume trend"""
        try:
            # Simple OBV calculation
            obv = np.zeros(len(df))
            for i in range(1, len(df)):
                if df['close'].iloc[i] > df['close'].iloc[i-1]:
                    obv[i] = obv[i-1] + df['volume'].iloc[i]
                elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                    obv[i] = obv[i-1] - df['volume'].iloc[i]
                else:
                    obv[i] = obv[i-1]
            
            # Determine trend
            if len(obv) >= 10:
                recent_obv = obv[-10:]
                if recent_obv[-1] > recent_obv[0]:
                    return 'bullish'
                elif recent_obv[-1] < recent_obv[0]:
                    return 'bearish'
            
            return 'neutral'
            
        except Exception:
            return 'unknown'
    
    def get_forex_session_volume_context(self, df: pd.DataFrame) -> str:
        """Get forex session volume context"""
        if hasattr(df.index[-1], 'hour'):
            hour = df.index[-1].hour
            if 13 <= hour <= 16:
                return 'london_ny_overlap_high_activity'
            elif 8 <= hour <= 17:
                return 'london_session_active'
            elif 13 <= hour <= 22:
                return 'ny_session_active'
            else:
                return 'asian_session_lower_activity'
        
        return 'unknown_session'
    
    def detect_accumulation_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect accumulation/distribution phases
        """
        if len(df) < 20:
            return {'phase': 'unknown'}
        
        # Price and volume relationship analysis
        price_changes = df['close'].pct_change().iloc[-20:]
        volume_changes = df['volume'].pct_change().iloc[-20:]
        
        # Correlation between price and volume changes
        correlation = np.corrcoef(price_changes.dropna(), volume_changes.dropna())[0, 1]
        
        # Phase determination
        if correlation > 0.3:
            if df['close'].iloc[-1] > df['close'].iloc[-20]:
                phase = 'accumulation'
            else:
                phase = 'distribution'
        elif correlation < -0.3:
            phase = 'divergence'  # Price and volume diverging
        else:
            phase = 'neutral'
        
        return {
            'phase': phase,
            'correlation': correlation,
            'confidence': abs(correlation),
            'market_interpretation': self.interpret_acc_dist_for_market(phase, correlation)
        }
    
    def interpret_acc_dist_for_market(self, phase: str, correlation: float) -> str:
        """Interpret accumulation/distribution for specific market"""
        if self.market_type == 'forex':
            if phase == 'accumulation':
                return "Forex accumulation: Institutional buying, potential currency strength"
            elif phase == 'distribution':
                return "Forex distribution: Institutional selling, potential currency weakness"
            elif phase == 'divergence':
                return "Forex divergence: Price-volume mismatch, potential reversal"
        
        elif self.market_type == 'crypto':
            if phase == 'accumulation':
                return "Crypto accumulation: Whale buying, potential price appreciation"
            elif phase == 'distribution':
                return "Crypto distribution: Whale selling, potential price decline"
            elif phase == 'divergence':
                return "Crypto divergence: Smart money vs retail divergence"
        
        return f"Volume phase: {phase}"
    
    def interpret_volume_for_market(self, volume_spike: bool, volume_patterns: Dict[str, Any], df: pd.DataFrame) -> List[str]:
        """Interpret volume data for specific market type"""
        interpretations = []
        
        if volume_spike:
            if self.market_type == 'forex':
                interpretations.append("Forex volume spike: Increased tick activity, possible news event or session start")
            elif self.market_type == 'crypto':
                interpretations.append("Crypto volume spike: High trading activity, possible whale movement or news")
        
        volume_trend = volume_patterns.get('volume_trend', 'neutral')
        if volume_trend == 'increasing':
            if self.market_type == 'forex':
                interpretations.append("Forex volume increasing: Growing interest, possible trend continuation")
            elif self.market_type == 'crypto':
                interpretations.append("Crypto volume increasing: Rising interest, potential breakout preparation")
        
        elif volume_trend == 'decreasing':
            if self.market_type == 'forex':
                interpretations.append("Forex volume decreasing: Reduced activity, possible consolidation")
            elif self.market_type == 'crypto':
                interpretations.append("Crypto volume decreasing: Waning interest, potential trend exhaustion")
        
        return interpretations
    
    def calculate_volume_signal_strength(self, volume_spike: bool, volume_patterns: Dict[str, Any], 
                                       volume_metrics: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate volume signal strength
        """
        strength_factors = []
        
        # Volume spike strength
        if volume_spike:
            spike_strength = 0.8
            
            # Enhance with spike magnitude
            if 'current_vs_avg' in volume_metrics:
                spike_magnitude = min(volume_metrics['current_vs_avg'] / 3.0, 1.0)
                spike_strength *= (0.5 + spike_magnitude * 0.5)
            
            strength_factors.append(spike_strength * self.volume_reliability)
        
        # Volume trend strength
        volume_trend = volume_patterns.get('volume_trend', 'neutral')
        if volume_trend != 'neutral':
            trend_strength = 0.6
            strength_factors.append(trend_strength * self.volume_reliability)
        
        # Extreme volume strength
        if volume_metrics.get('extreme_volume', False):
            extreme_strength = 0.9
            strength_factors.append(extreme_strength * self.volume_reliability)
        
        # Market-specific adjustments
        market_adjustment = self.get_market_specific_volume_strength(df)
        strength_factors.append(market_adjustment)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_market_specific_volume_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific volume strength adjustment"""
        if self.market_type == 'forex':
            # Forex volume strength based on session
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:  # London-NY overlap
                    return 0.8
                elif 8 <= hour <= 22:  # Major sessions
                    return 0.7
                else:
                    return 0.4  # Asian session
            return 0.6
        
        elif self.market_type == 'crypto':
            # Crypto volume strength is consistent 24/7
            return 0.8
        
        return 0.6
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_volume_summary(self) -> Dict[str, Any]:
        """Get comprehensive volume summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'volume_spikes_count': len(self.volume_spikes),
            'volume_patterns_count': len(self.volume_patterns),
            'volume_reliability': self.volume_reliability,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'spike_threshold': self.spike_threshold,
                'volume_ma_period': self.volume_ma_period,
                'extreme_volume_threshold': self.extreme_volume_threshold
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Volume agent doesn't need continuous processing"""
        return False