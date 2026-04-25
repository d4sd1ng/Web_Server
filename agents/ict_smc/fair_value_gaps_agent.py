"""
Fair Value Gaps Agent
Uses your existing detect_ifvg() function from tradingbot_new.py
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import ICTSMCAgent


class FairValueGapsAgent(ICTSMCAgent):
    """
    Fair Value Gaps detection using your existing functions
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("fair_value_gaps", config)
        
        # FVG configuration
        self.window = config.get('window', 3)
        self.min_gap = config.get('min_gap', 0.0001)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # FVG tracking
        self.active_fvgs = []
        self.filled_fvgs = []
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Fair Value Gaps Agent initialized for {self.market_type}")
    
    def apply_market_specific_config(self):
        """Apply market-specific FVG configuration"""
        if self.market_type == 'forex':
            self.min_gap = max(self.min_gap, 0.0001)  # Smaller gaps for forex
            self.volume_weight = 0.3  # Lower volume weight for forex
        elif self.market_type == 'crypto':
            self.min_gap = max(self.min_gap, 0.0005)  # Larger gaps for crypto
            self.volume_weight = 0.8  # Higher volume weight for crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process market data to detect Fair Value Gaps"""
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < 5:
            return {'fvgs': [], 'signal_strength': 0.0}
        
        try:
            # Use your existing detect_ifvg function
            fvgs = self.detect_ifvg(df, self.window)
            
            # Update FVG tracking
            self.update_fvg_tracking(fvgs, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_fvg_signal_strength(fvgs, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'fvgs': fvgs,
                'active_fvgs': self.active_fvgs,
                'signal_strength': signal_strength,
                'market_type': self.market_type
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing FVG data for {symbol}: {e}")
            return {'fvgs': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_ifvg(self, df: pd.DataFrame, window: int = 3) -> List[Dict[str, Any]]:
        """
        Detect Fair Value Gaps using your existing logic
        """
        fvgs = []
        
        if len(df) < window + 2:
            return fvgs
        
        for i in range(window, len(df) - 1):
            # Check for bullish FVG
            if (df['low'].iloc[i+1] > df['high'].iloc[i-1] and
                df['high'].iloc[i] < df['low'].iloc[i+1]):
                
                gap_size = (df['low'].iloc[i+1] - df['high'].iloc[i-1]) / df['high'].iloc[i-1]
                
                if gap_size >= self.min_gap:
                    fvg = {
                        'type': 'bullish',
                        'zone': (df['high'].iloc[i-1], df['low'].iloc[i+1]),
                        'gap_size': gap_size,
                        'created_at': df.index[i+1],
                        'filled': False,
                        'strength': self.calculate_fvg_strength(df, i, 'bullish')
                    }
                    fvgs.append(fvg)
            
            # Check for bearish FVG
            elif (df['high'].iloc[i+1] < df['low'].iloc[i-1] and
                  df['low'].iloc[i] > df['high'].iloc[i+1]):
                
                gap_size = (df['low'].iloc[i-1] - df['high'].iloc[i+1]) / df['high'].iloc[i+1]
                
                if gap_size >= self.min_gap:
                    fvg = {
                        'type': 'bearish',
                        'zone': (df['high'].iloc[i+1], df['low'].iloc[i-1]),
                        'gap_size': gap_size,
                        'created_at': df.index[i+1],
                        'filled': False,
                        'strength': self.calculate_fvg_strength(df, i, 'bearish')
                    }
                    fvgs.append(fvg)
        
        return fvgs
    
    def calculate_fvg_strength(self, df: pd.DataFrame, index: int, fvg_type: str) -> float:
        """Calculate FVG strength"""
        try:
            strength_factors = []
            
            # Gap size strength
            if fvg_type == 'bullish':
                gap_size = (df['low'].iloc[index+1] - df['high'].iloc[index-1]) / df['high'].iloc[index-1]
            else:
                gap_size = (df['low'].iloc[index-1] - df['high'].iloc[index+1]) / df['high'].iloc[index+1]
            
            gap_strength = min(gap_size / 0.01, 1.0)  # Normalize to 1% gap
            strength_factors.append(gap_strength)
            
            # Volume confirmation
            if 'volume' in df.columns:
                gap_volume = df['volume'].iloc[index+1]
                avg_volume = df['volume'].rolling(20).mean().iloc[index+1]
                volume_strength = min(gap_volume / avg_volume, 2.0) / 2.0
                strength_factors.append(volume_strength * self.volume_weight)
            
            return np.mean(strength_factors) if strength_factors else 0.5
            
        except Exception:
            return 0.5
    
    def update_fvg_tracking(self, fvgs: List[Dict[str, Any]], df: pd.DataFrame):
        """Update FVG tracking"""
        # Add new FVGs
        for fvg in fvgs:
            if fvg not in self.active_fvgs:
                self.active_fvgs.append(fvg)
        
        # Check for filled FVGs
        current_price = df['close'].iloc[-1]
        still_active = []
        
        for fvg in self.active_fvgs:
            zone_low, zone_high = fvg['zone']
            
            # Check if FVG is filled
            if zone_low <= current_price <= zone_high:
                fvg['filled'] = True
                fvg['filled_at'] = datetime.now(timezone.utc)
                self.filled_fvgs.append(fvg)
            else:
                still_active.append(fvg)
        
        self.active_fvgs = still_active
        
        # Limit tracking sizes
        if len(self.filled_fvgs) > 100:
            self.filled_fvgs = self.filled_fvgs[-100:]
    
    def calculate_fvg_signal_strength(self, fvgs: List[Dict[str, Any]], df: pd.DataFrame) -> float:
        """Calculate FVG signal strength"""
        if not fvgs:
            return 0.0
        
        # Average strength of detected FVGs
        avg_strength = np.mean([fvg['strength'] for fvg in fvgs])
        
        # Number of FVGs factor
        count_factor = min(len(fvgs) / 3.0, 1.0)
        
        return avg_strength * 0.7 + count_factor * 0.3
    
    def get_signal_strength(self) -> float:
        """Get current signal strength"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def requires_continuous_processing(self) -> bool:
        """FVG agent doesn't need continuous processing"""
        return False