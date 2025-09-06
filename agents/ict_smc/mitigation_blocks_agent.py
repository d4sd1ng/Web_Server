"""
Mitigation Blocks Agent
Detects mitigation blocks using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class MitigationBlocksAgent(ICTSMCAgent):
    """
    Specialized agent for Mitigation Block detection
    Uses existing detect_mitigation_blocks() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("mitigation_blocks", config)
        
        # Mitigation block configuration
        self.lookback = config.get('lookback', 30)
        self.validation_bars = config.get('validation_bars', 2)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Mitigation tracking
        self.active_mitigation_blocks = []
        self.validated_mitigations = []
        self.failed_mitigations = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Mitigation Blocks Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific configuration adjustments"""
        if self.market_type == 'forex':
            # Forex: More conservative mitigation detection
            self.lookback = max(self.lookback, 35)
            self.validation_bars = 3
            self.session_weight = 0.8
        elif self.market_type == 'crypto':
            # Crypto: Standard mitigation detection
            self.lookback = min(self.lookback, 30)
            self.validation_bars = 2
            self.session_weight = 0.2
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect mitigation blocks
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with mitigation block analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.lookback + 3:
            return {'mitigation_blocks': [], 'signal_strength': 0.0}
        
        try:
            # Use existing detect_mitigation_blocks function
            mitigation_blocks = self.detect_mitigation_blocks(df, self.lookback)
            
            # Analyze mitigation patterns
            mitigation_analysis = self.analyze_mitigation_patterns(mitigation_blocks, df)
            
            # Update tracking
            self.update_mitigation_tracking(mitigation_blocks, df)
            
            # Calculate signal strength
            signal_strength = self.calculate_mitigation_signal_strength(mitigation_blocks, df)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'mitigation_blocks': mitigation_blocks,
                'mitigation_analysis': mitigation_analysis,
                'active_mitigations': self.active_mitigation_blocks,
                'validated_mitigations': self.validated_mitigations,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'retest_opportunities': self.identify_retest_opportunities(mitigation_blocks, df)
            }
            
            # Publish mitigation signals
            if mitigation_blocks:
                validated_mitigations = [mb for mb in mitigation_blocks if mb['validated']]
                if validated_mitigations:
                    self.publish("mitigation_block_validated", {
                        'symbol': symbol,
                        'mitigation_blocks': validated_mitigations,
                        'signal_strength': signal_strength,
                        'market_type': self.market_type
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing mitigation block data for {symbol}: {e}")
            return {'mitigation_blocks': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_mitigation_blocks(self, df: pd.DataFrame, lookback: int = 30) -> List[Dict[str, Any]]:
        """
        Detect mitigation blocks using existing implementation
        """
        mbs = []
        
        if len(df) < lookback + 3:
            return mbs
        
        for i in range(lookback, len(df)-2):
            # Bullish Mitigation Block
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i+1] > df['low'].iloc[i]):
                
                if df['high'].iloc[i+2] > df['high'].iloc[i-1]:
                    up_candles = [j for j in range(i-2, i+1) 
                                 if df['close'].iloc[j] > df['open'].iloc[j]]
                    
                    if up_candles:
                        mb_idx = up_candles[-1]
                        zone = (df['open'].iloc[mb_idx], df['close'].iloc[mb_idx])
                        validated = df['close'].iloc[i+2] > df['high'].iloc[i-1]
                        
                        # Market-specific validation
                        if self.validate_mitigation_for_market(df, mb_idx, 'bullish'):
                            mbs.append({
                                'type': 'bullish',
                                'zone': zone,
                                'validated': validated,
                                'index': mb_idx,
                                'formation_index': i,
                                'strength': self.calculate_mitigation_strength(df, mb_idx, 'bullish'),
                                'timestamp': df.index[mb_idx] if mb_idx < len(df) else None,
                                'market_type': self.market_type
                            })
            
            # Bearish Mitigation Block
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i+1] < df['high'].iloc[i]):
                
                if df['low'].iloc[i+2] < df['low'].iloc[i-1]:
                    down_candles = [j for j in range(i-2, i+1) 
                                   if df['close'].iloc[j] < df['open'].iloc[j]]
                    
                    if down_candles:
                        mb_idx = down_candles[-1]
                        zone = (df['close'].iloc[mb_idx], df['open'].iloc[mb_idx])
                        validated = df['close'].iloc[i+2] < df['low'].iloc[i-1]
                        
                        # Market-specific validation
                        if self.validate_mitigation_for_market(df, mb_idx, 'bearish'):
                            mbs.append({
                                'type': 'bearish',
                                'zone': zone,
                                'validated': validated,
                                'index': mb_idx,
                                'formation_index': i,
                                'strength': self.calculate_mitigation_strength(df, mb_idx, 'bearish'),
                                'timestamp': df.index[mb_idx] if mb_idx < len(df) else None,
                                'market_type': self.market_type
                            })
        
        return mbs
    
    def validate_mitigation_for_market(self, df: pd.DataFrame, index: int, mb_type: str) -> bool:
        """Validate mitigation block for specific market type"""
        if self.market_type == 'forex':
            return self.validate_forex_mitigation(df, index, mb_type)
        elif self.market_type == 'crypto':
            return self.validate_crypto_mitigation(df, index, mb_type)
        return True
    
    def validate_forex_mitigation(self, df: pd.DataFrame, index: int, mb_type: str) -> bool:
        """Validate mitigation block for forex markets"""
        try:
            # Session-based validation for forex
            if hasattr(df.index[index], 'hour'):
                hour = df.index[index].hour
                
                # Mitigation more significant during major sessions
                if 8 <= hour <= 22:
                    return True
                else:
                    # Require stronger price movement outside major sessions
                    candle = df.iloc[index]
                    body = abs(candle['close'] - candle['open'])
                    total_range = candle['high'] - candle['low']
                    
                    return body / total_range > 0.6 if total_range > 0 else False
            
            return True
            
        except Exception:
            return True
    
    def validate_crypto_mitigation(self, df: pd.DataFrame, index: int, mb_type: str) -> bool:
        """Validate mitigation block for crypto markets"""
        try:
            # Volume-based validation for crypto
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[index]
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                
                # Require elevated volume for crypto mitigation blocks
                return current_volume > 1.2 * avg_volume
            
            return True
            
        except Exception:
            return True
    
    def calculate_mitigation_strength(self, df: pd.DataFrame, index: int, mb_type: str) -> float:
        """Calculate mitigation block strength"""
        try:
            strength_factors = []
            candle = df.iloc[index]
            
            # Body strength
            body = abs(candle['close'] - candle['open'])
            total_range = candle['high'] - candle['low']
            if total_range > 0:
                body_strength = body / total_range
                strength_factors.append(body_strength)
            
            # Volume strength (market-weighted)
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[index]
                avg_volume = df['volume'].rolling(20).mean().iloc[index]
                volume_strength = min(current_volume / avg_volume, 2.0) / 2.0
                
                if self.market_type == 'crypto':
                    strength_factors.append(volume_strength * 0.8)
                else:
                    strength_factors.append(volume_strength * 0.4)
            
            # ATR-relative strength
            if 'atr' in df.columns:
                atr = df['atr'].iloc[index]
                atr_strength = min(total_range / atr, 2.0) / 2.0
                strength_factors.append(atr_strength)
            
            # Session strength (for forex)
            if self.market_type == 'forex' and hasattr(df.index[index], 'hour'):
                session_strength = self.calculate_forex_time_strength(df.index[index].hour)
                strength_factors.append(session_strength * self.session_weight)
            
            return np.mean(strength_factors) if strength_factors else 0.5
            
        except Exception:
            return 0.5
    
    def calculate_forex_time_strength(self, hour: int) -> float:
        """Calculate forex session strength"""
        if 13 <= hour <= 16:  # London-NY overlap
            return 1.0
        elif 8 <= hour <= 17:  # London session
            return 0.8
        elif 13 <= hour <= 22:  # NY session
            return 0.8
        else:  # Asian session
            return 0.5
    
    def analyze_mitigation_patterns(self, mitigation_blocks: List[Dict[str, Any]], df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze mitigation block patterns
        """
        if not mitigation_blocks:
            return {'total_mitigations': 0, 'validated_mitigations': 0}
        
        validated_mitigations = [mb for mb in mitigation_blocks if mb['validated']]
        bullish_mitigations = [mb for mb in mitigation_blocks if mb['type'] == 'bullish']
        bearish_mitigations = [mb for mb in mitigation_blocks if mb['type'] == 'bearish']
        
        analysis = {
            'total_mitigations': len(mitigation_blocks),
            'validated_mitigations': len(validated_mitigations),
            'bullish_mitigations': len(bullish_mitigations),
            'bearish_mitigations': len(bearish_mitigations),
            'validation_rate': len(validated_mitigations) / len(mitigation_blocks),
            'mitigation_bias': self.determine_mitigation_bias(bullish_mitigations, bearish_mitigations),
            'avg_strength': np.mean([mb['strength'] for mb in mitigation_blocks])
        }
        
        return analysis
    
    def determine_mitigation_bias(self, bullish_mitigations: List[Dict[str, Any]], 
                                bearish_mitigations: List[Dict[str, Any]]) -> str:
        """Determine overall mitigation bias"""
        if len(bullish_mitigations) > len(bearish_mitigations):
            return 'bullish'
        elif len(bearish_mitigations) > len(bullish_mitigations):
            return 'bearish'
        else:
            return 'neutral'
    
    def identify_retest_opportunities(self, mitigation_blocks: List[Dict[str, Any]], 
                                   df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify retest opportunities for mitigation blocks"""
        opportunities = []
        current_price = df['close'].iloc[-1]
        
        if 'atr' not in df.columns:
            return opportunities
        
        current_atr = df['atr'].iloc[-1]
        
        for mb in mitigation_blocks:
            if mb['validated']:
                zone_low, zone_high = mb['zone']
                distance_to_zone = min(abs(current_price - zone_low), abs(current_price - zone_high))
                
                # Check if price is approaching mitigation block
                if distance_to_zone <= 2.0 * current_atr:
                    opportunity = {
                        'mb_type': mb['type'],
                        'zone': mb['zone'],
                        'distance': distance_to_zone,
                        'strength': mb['strength'],
                        'opportunity_type': 'retest_approach',
                        'recommended_action': self.get_mitigation_recommendation(mb, current_price),
                        'market_context': self.get_mitigation_market_context(mb, df)
                    }
                    opportunities.append(opportunity)
        
        return opportunities
    
    def get_mitigation_recommendation(self, mb: Dict[str, Any], current_price: float) -> str:
        """Get trading recommendation for mitigation block"""
        zone_low, zone_high = mb['zone']
        
        if mb['type'] == 'bullish':
            if zone_low <= current_price <= zone_high:
                return f"LONG opportunity - Price retesting bullish mitigation block in {self.market_type}"
            elif current_price < zone_low:
                return f"LONG setup - Monitor for bullish mitigation block retest"
            else:
                return f"Bullish mitigation above price - wait for retest"
        
        else:  # bearish mitigation
            if zone_low <= current_price <= zone_high:
                return f"SHORT opportunity - Price retesting bearish mitigation block in {self.market_type}"
            elif current_price > zone_high:
                return f"SHORT setup - Monitor for bearish mitigation block retest"
            else:
                return f"Bearish mitigation below price - wait for retest"
    
    def get_mitigation_market_context(self, mb: Dict[str, Any], df: pd.DataFrame) -> Dict[str, str]:
        """Get market context for mitigation block"""
        context = {}
        
        if self.market_type == 'forex':
            context['market_note'] = "Forex mitigation: Often coincides with institutional rebalancing"
            
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:
                    context['session_note'] = "London-NY overlap - high probability retest"
                elif 8 <= hour <= 22:
                    context['session_note'] = "Major session active - good retest probability"
                else:
                    context['session_note'] = "Asian session - lower retest probability"
        
        elif self.market_type == 'crypto':
            context['market_note'] = "Crypto mitigation: Watch for whale activity and volume confirmation"
            
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                if vol_ratio > 1.5:
                    context['volume_note'] = "Elevated volume - strong retest potential"
                else:
                    context['volume_note'] = "Normal volume - standard retest probability"
        
        return context
    
    def calculate_mitigation_signal_strength(self, mitigation_blocks: List[Dict[str, Any]], df: pd.DataFrame) -> float:
        """
        Calculate mitigation block signal strength
        """
        if not mitigation_blocks:
            return 0.0
        
        strength_factors = []
        
        # Validated mitigation strength
        validated_blocks = [mb for mb in mitigation_blocks if mb['validated']]
        if validated_blocks:
            base_strength = 0.8
            strength_factors.append(base_strength)
            
            # Average mitigation strength
            avg_mb_strength = np.mean([mb['strength'] for mb in validated_blocks])
            strength_factors.append(avg_mb_strength)
        
        # Market-specific strength
        market_strength = self.get_market_specific_mitigation_strength(df)
        strength_factors.append(market_strength)
        
        # Multiple mitigation confluence
        if len(validated_blocks) > 1:
            confluence_bonus = min(len(validated_blocks) * 0.1, 0.3)
            strength_factors.append(confluence_bonus)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_market_specific_mitigation_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific mitigation strength"""
        if self.market_type == 'forex':
            # Session-based strength for forex
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                return self.calculate_forex_time_strength(hour)
            return 0.7
        
        elif self.market_type == 'crypto':
            # Volume-based strength for crypto
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                volume_factor = min(current_volume / avg_volume, 2.0) / 2.0
                return 0.6 + volume_factor * 0.4
            
            return 0.7
        
        return 0.7
    
    def update_mitigation_tracking(self, mitigation_blocks: List[Dict[str, Any]], df: pd.DataFrame):
        """Update mitigation block tracking"""
        current_price = df['close'].iloc[-1]
        
        # Add new mitigation blocks
        for mb in mitigation_blocks:
            if mb['validated'] and mb not in self.active_mitigation_blocks:
                mb['detected_time'] = datetime.now(timezone.utc)
                self.active_mitigation_blocks.append(mb)
        
        # Check existing mitigations for retest/invalidation
        still_active = []
        for mb in self.active_mitigation_blocks:
            status = self.check_mitigation_status(mb, current_price, df)
            
            if status == 'active':
                still_active.append(mb)
            elif status == 'retested':
                mb['retest_time'] = datetime.now(timezone.utc)
                mb['retest_price'] = current_price
                self.validated_mitigations.append(mb)
            elif status == 'failed':
                mb['failed_time'] = datetime.now(timezone.utc)
                mb['failed_price'] = current_price
                self.failed_mitigations.append(mb)
        
        self.active_mitigation_blocks = still_active
        
        # Limit tracking sizes
        if len(self.active_mitigation_blocks) > 50:
            self.active_mitigation_blocks = self.active_mitigation_blocks[-50:]
    
    def check_mitigation_status(self, mb: Dict[str, Any], current_price: float, df: pd.DataFrame) -> str:
        """Check mitigation block status"""
        zone_low, zone_high = mb['zone']
        
        # Check for retest
        if zone_low <= current_price <= zone_high:
            return 'retested'
        
        # Check for invalidation
        if mb['type'] == 'bullish':
            if current_price < zone_low * 0.98:  # 2% below zone
                return 'failed'
        else:  # bearish
            if current_price > zone_high * 1.02:  # 2% above zone
                return 'failed'
        
        return 'active'
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_mitigation_summary(self) -> Dict[str, Any]:
        """Get comprehensive mitigation block summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'active_mitigations_count': len(self.active_mitigation_blocks),
            'validated_mitigations_count': len(self.validated_mitigations),
            'failed_mitigations_count': len(self.failed_mitigations),
            'active_bullish_mitigations': len([mb for mb in self.active_mitigation_blocks if mb['type'] == 'bullish']),
            'active_bearish_mitigations': len([mb for mb in self.active_mitigation_blocks if mb['type'] == 'bearish']),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'lookback': self.lookback,
                'validation_bars': self.validation_bars,
                'session_weight': self.session_weight
            }
        }
    
    def get_valid_bullish_mitigations(self) -> List[Dict[str, Any]]:
        """Get validated bullish mitigation blocks"""
        return [mb for mb in self.validated_mitigations if mb['type'] == 'bullish']
    
    def get_valid_bearish_mitigations(self) -> List[Dict[str, Any]]:
        """Get validated bearish mitigation blocks"""
        return [mb for mb in self.validated_mitigations if mb['type'] == 'bearish']
    
    def requires_continuous_processing(self) -> bool:
        """Mitigation blocks agent doesn't need continuous processing"""
        return False