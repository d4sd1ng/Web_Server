"""
Market Maker Model Agent
Analyzes institutional market maker behavior and algorithms
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class MarketMakerModelAgent(ICTSMCAgent):
    """
    Specialized agent for Market Maker Model analysis
    Identifies institutional behavior patterns and price delivery algorithms
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("market_maker_model", config)
        
        # Market maker configuration
        self.algorithm_detection_window = config.get('algorithm_detection_window', 50)
        self.institutional_size_threshold = config.get('institutional_size_threshold', 3.0)  # 3x avg volume
        self.price_delivery_tolerance = config.get('price_delivery_tolerance', 0.001)  # 0.1%
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Market maker tracking
        self.institutional_footprints = []
        self.price_delivery_patterns = []
        self.algorithm_signatures = []
        self.liquidity_provision_events = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Market Maker Model Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific market maker configuration"""
        if self.market_type == 'forex':
            # Forex: Major banks and central banks as market makers
            self.institutional_size_threshold = max(self.institutional_size_threshold, 5.0)  # Higher threshold
            self.algorithm_sophistication = 'high'
            self.central_bank_influence = True
            self.interbank_flow_monitoring = True
        elif self.market_type == 'crypto':
            # Crypto: Exchanges and whales as market makers
            self.institutional_size_threshold = min(self.institutional_size_threshold, 3.0)  # Lower threshold
            self.algorithm_sophistication = 'medium'
            self.central_bank_influence = False
            self.whale_activity_monitoring = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to analyze market maker behavior
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with market maker analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.algorithm_detection_window:
            return {'market_maker_activity': 'insufficient_data', 'signal_strength': 0.0}
        
        try:
            # Detect institutional footprints
            institutional_footprints = self.detect_institutional_footprints(df)
            
            # Analyze price delivery algorithms
            price_delivery = self.analyze_price_delivery_algorithms(df)
            
            # Detect liquidity provision patterns
            liquidity_provision = self.detect_liquidity_provision(df)
            
            # Analyze market maker behavior
            mm_behavior = self.analyze_market_maker_behavior(df, institutional_footprints)
            
            # Calculate signal strength
            signal_strength = self.calculate_mm_signal_strength(
                institutional_footprints, price_delivery, liquidity_provision, df
            )
            
            # Update tracking
            self.update_mm_tracking(institutional_footprints, price_delivery, liquidity_provision)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'institutional_footprints': institutional_footprints,
                'price_delivery': price_delivery,
                'liquidity_provision': liquidity_provision,
                'mm_behavior': mm_behavior,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_insights': self.get_mm_trading_insights(
                    institutional_footprints, price_delivery, mm_behavior
                )
            }
            
            # Publish market maker signals
            if institutional_footprints['large_orders_detected']:
                self.publish("institutional_activity", {
                    'symbol': symbol,
                    'activity_type': institutional_footprints['dominant_activity'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing market maker data for {symbol}: {e}")
            return {'market_maker_activity': 'error', 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_institutional_footprints(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect institutional trading footprints
        """
        footprints = {
            'large_orders_detected': False,
            'institutional_buying': 0,
            'institutional_selling': 0,
            'dominant_activity': 'neutral',
            'footprint_details': []
        }
        
        if 'volume' not in df.columns or len(df) < 20:
            return footprints
        
        # Calculate volume statistics
        avg_volume = df['volume'].rolling(20).mean()
        volume_threshold = avg_volume * self.institutional_size_threshold
        
        # Detect large volume events
        for i in range(len(df)):
            if df['volume'].iloc[i] > volume_threshold.iloc[i]:
                # Large volume detected - analyze characteristics
                candle = df.iloc[i]
                
                footprint_detail = {
                    'index': i,
                    'volume': candle['volume'],
                    'volume_ratio': candle['volume'] / avg_volume.iloc[i],
                    'price_impact': self.calculate_price_impact(df, i),
                    'institutional_type': self.classify_institutional_activity(df, i),
                    'market_context': self.get_institutional_context(df, i)
                }
                
                footprints['footprint_details'].append(footprint_detail)
                
                # Count buying vs selling
                if footprint_detail['institutional_type'] == 'buying':
                    footprints['institutional_buying'] += 1
                elif footprint_detail['institutional_type'] == 'selling':
                    footprints['institutional_selling'] += 1
        
        # Determine dominant activity
        if footprints['institutional_buying'] > footprints['institutional_selling']:
            footprints['dominant_activity'] = 'buying'
        elif footprints['institutional_selling'] > footprints['institutional_buying']:
            footprints['dominant_activity'] = 'selling'
        
        footprints['large_orders_detected'] = len(footprints['footprint_details']) > 0
        
        return footprints
    
    def calculate_price_impact(self, df: pd.DataFrame, index: int) -> float:
        """Calculate price impact of large volume event"""
        if index == 0 or index >= len(df) - 1:
            return 0.0
        
        prev_close = df['close'].iloc[index - 1]
        curr_close = df['close'].iloc[index]
        next_close = df['close'].iloc[index + 1] if index + 1 < len(df) else curr_close
        
        # Immediate impact
        immediate_impact = abs(curr_close - prev_close) / prev_close
        
        # Sustained impact
        sustained_impact = abs(next_close - prev_close) / prev_close
        
        return max(immediate_impact, sustained_impact)
    
    def classify_institutional_activity(self, df: pd.DataFrame, index: int) -> str:
        """Classify type of institutional activity"""
        if index >= len(df) - 1:
            return 'unknown'
        
        candle = df.iloc[index]
        
        # Analyze candle characteristics
        body_size = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        
        if total_range == 0:
            return 'unknown'
        
        body_ratio = body_size / total_range
        upper_wick_ratio = upper_wick / total_range
        lower_wick_ratio = lower_wick / total_range
        
        # Classification logic
        if candle['close'] > candle['open'] and body_ratio > 0.6:
            return 'buying'  # Strong bullish candle with volume
        elif candle['close'] < candle['open'] and body_ratio > 0.6:
            return 'selling'  # Strong bearish candle with volume
        elif upper_wick_ratio > 0.5:
            return 'selling'  # Rejection at highs
        elif lower_wick_ratio > 0.5:
            return 'buying'   # Support at lows
        else:
            return 'neutral'  # Unclear activity
    
    def get_institutional_context(self, df: pd.DataFrame, index: int) -> str:
        """Get context for institutional activity"""
        if self.market_type == 'forex':
            # Check session timing for forex
            if hasattr(df.index[index], 'hour'):
                hour = df.index[index].hour
                if 13 <= hour <= 16:
                    return 'london_ny_overlap_institutional'
                elif 8 <= hour <= 17:
                    return 'london_session_institutional'
                elif 13 <= hour <= 22:
                    return 'ny_session_institutional'
                else:
                    return 'asian_session_institutional'
        
        elif self.market_type == 'crypto':
            # Check for crypto-specific patterns
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[index] / df['volume'].rolling(20).mean().iloc[index]
                if vol_ratio > 5.0:
                    return 'whale_activity'
                elif vol_ratio > 3.0:
                    return 'institutional_activity'
                else:
                    return 'large_trader_activity'
        
        return 'institutional_activity'
    
    def analyze_price_delivery_algorithms(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze price delivery algorithm patterns
        """
        if len(df) < 30:
            return {'algorithms_detected': False}
        
        algorithms = {
            'algorithms_detected': False,
            'twap_like_patterns': 0,
            'vwap_like_patterns': 0,
            'iceberg_patterns': 0,
            'stealth_patterns': 0,
            'algorithm_signatures': []
        }
        
        # TWAP-like pattern detection (Time Weighted Average Price)
        twap_patterns = self.detect_twap_patterns(df)
        algorithms['twap_like_patterns'] = len(twap_patterns)
        
        # VWAP-like pattern detection (Volume Weighted Average Price)
        vwap_patterns = self.detect_vwap_patterns(df)
        algorithms['vwap_like_patterns'] = len(vwap_patterns)
        
        # Iceberg order patterns
        iceberg_patterns = self.detect_iceberg_patterns(df)
        algorithms['iceberg_patterns'] = len(iceberg_patterns)
        
        # Stealth trading patterns
        stealth_patterns = self.detect_stealth_patterns(df)
        algorithms['stealth_patterns'] = len(stealth_patterns)
        
        algorithms['algorithms_detected'] = (algorithms['twap_like_patterns'] > 0 or
                                           algorithms['vwap_like_patterns'] > 0 or
                                           algorithms['iceberg_patterns'] > 0 or
                                           algorithms['stealth_patterns'] > 0)
        
        return algorithms
    
    def detect_twap_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect TWAP-like trading patterns"""
        patterns = []
        
        # Look for consistent small orders over time
        for i in range(10, len(df) - 10):
            window = df.iloc[i-10:i+10]
            
            # Check for consistent volume and price progression
            volume_consistency = window['volume'].std() / window['volume'].mean()
            price_progression = abs(window['close'].iloc[-1] - window['close'].iloc[0]) / window['close'].iloc[0]
            
            if (volume_consistency < 0.3 and  # Consistent volume
                0.005 < price_progression < 0.02):  # Steady price movement
                
                patterns.append({
                    'type': 'twap_like',
                    'index': i,
                    'consistency_score': 1.0 - volume_consistency,
                    'price_progression': price_progression
                })
        
        return patterns
    
    def detect_vwap_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect VWAP-like trading patterns"""
        patterns = []
        
        if 'vwap' not in df.columns:
            return patterns
        
        # Look for price clustering around VWAP
        for i in range(20, len(df)):
            recent_data = df.iloc[i-20:i]
            vwap = recent_data['vwap'].iloc[-1]
            
            # Count how often price stays near VWAP
            near_vwap_count = sum(1 for price in recent_data['close'] 
                                if abs(price - vwap) / vwap < 0.005)
            
            if near_vwap_count > 15:  # 75% of time near VWAP
                patterns.append({
                    'type': 'vwap_clustering',
                    'index': i,
                    'vwap_adherence': near_vwap_count / len(recent_data),
                    'vwap_level': vwap
                })
        
        return patterns
    
    def detect_iceberg_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect iceberg order patterns (large orders split into smaller pieces)"""
        patterns = []
        
        if 'volume' not in df.columns or len(df) < 20:
            return patterns
        
        # Look for repeated volume at similar price levels
        for i in range(10, len(df) - 5):
            price_level = df['close'].iloc[i]
            
            # Look for similar prices in surrounding bars
            surrounding_data = df.iloc[i-10:i+5]
            similar_price_bars = []
            
            for j, (idx, row) in enumerate(surrounding_data.iterrows()):
                if abs(row['close'] - price_level) / price_level < self.price_delivery_tolerance:
                    similar_price_bars.append({
                        'index': i - 10 + j,
                        'volume': row['volume'],
                        'price': row['close']
                    })
            
            # Check for iceberg characteristics
            if len(similar_price_bars) >= 3:
                total_volume = sum(bar['volume'] for bar in similar_price_bars)
                avg_volume = df['volume'].rolling(20).mean().iloc[i]
                
                if total_volume > avg_volume * 2:  # Significant cumulative volume
                    patterns.append({
                        'type': 'iceberg_order',
                        'price_level': price_level,
                        'total_volume': total_volume,
                        'execution_bars': len(similar_price_bars),
                        'avg_volume_ratio': total_volume / (avg_volume * len(similar_price_bars))
                    })
        
        return patterns
    
    def detect_stealth_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect stealth trading patterns (gradual accumulation/distribution)"""
        patterns = []
        
        if len(df) < 30:
            return patterns
        
        # Look for gradual price movement with consistent volume
        window_size = 20
        
        for i in range(window_size, len(df)):
            window = df.iloc[i-window_size:i]
            
            # Check for gradual directional movement
            price_start = window['close'].iloc[0]
            price_end = window['close'].iloc[-1]
            total_move = abs(price_end - price_start) / price_start
            
            # Check for consistent volume pattern
            volume_consistency = self.calculate_volume_consistency(window)
            
            # Check for minimal volatility (stealth characteristic)
            price_volatility = window['close'].std() / window['close'].mean()
            
            if (0.01 < total_move < 0.05 and  # Significant but not obvious move
                volume_consistency > 0.7 and     # Consistent volume
                price_volatility < 0.02):         # Low volatility
                
                direction = 'accumulation' if price_end > price_start else 'distribution'
                
                patterns.append({
                    'type': 'stealth_trading',
                    'direction': direction,
                    'total_move': total_move,
                    'volume_consistency': volume_consistency,
                    'stealth_score': self.calculate_stealth_score(window)
                })
        
        return patterns
    
    def calculate_volume_consistency(self, df: pd.DataFrame) -> float:
        """Calculate volume consistency score"""
        if 'volume' not in df.columns:
            return 0.0
        
        volume_cv = df['volume'].std() / df['volume'].mean()
        return max(0, 1.0 - volume_cv)  # Lower CV = higher consistency
    
    def calculate_stealth_score(self, df: pd.DataFrame) -> float:
        """Calculate stealth trading score"""
        if len(df) < 5:
            return 0.0
        
        # Stealth characteristics
        volume_consistency = self.calculate_volume_consistency(df)
        price_smoothness = self.calculate_price_smoothness(df)
        
        return (volume_consistency * 0.6 + price_smoothness * 0.4)
    
    def calculate_price_smoothness(self, df: pd.DataFrame) -> float:
        """Calculate price movement smoothness"""
        if len(df) < 3:
            return 0.0
        
        # Calculate price changes
        price_changes = df['close'].pct_change().dropna()
        
        # Smooth movement has consistent small changes
        change_consistency = 1.0 - (price_changes.std() / abs(price_changes.mean())) if price_changes.mean() != 0 else 0.0
        
        return max(0.0, min(change_consistency, 1.0))
    
    def detect_liquidity_provision(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect liquidity provision patterns
        """
        liquidity = {
            'provision_events': 0,
            'bid_side_provision': 0,
            'ask_side_provision': 0,
            'provision_details': []
        }
        
        if len(df) < 10:
            return liquidity
        
        # Look for liquidity provision patterns
        for i in range(5, len(df) - 5):
            provision_event = self.identify_liquidity_provision_event(df, i)
            if provision_event:
                liquidity['provision_details'].append(provision_event)
                liquidity['provision_events'] += 1
                
                if provision_event['side'] == 'bid':
                    liquidity['bid_side_provision'] += 1
                else:
                    liquidity['ask_side_provision'] += 1
        
        return liquidity
    
    def identify_liquidity_provision_event(self, df: pd.DataFrame, index: int) -> Dict[str, Any]:
        """Identify individual liquidity provision event"""
        # Look for price stabilization after volatility
        before_window = df.iloc[max(0, index-5):index]
        after_window = df.iloc[index:index+5]
        
        if len(before_window) < 3 or len(after_window) < 3:
            return None
        
        # Check for volatility reduction
        before_volatility = before_window['close'].std() / before_window['close'].mean()
        after_volatility = after_window['close'].std() / after_window['close'].mean()
        
        if before_volatility > after_volatility * 2:  # Significant volatility reduction
            # Determine which side liquidity was provided
            current_price = df['close'].iloc[index]
            avg_price = (before_window['close'].mean() + after_window['close'].mean()) / 2
            
            side = 'bid' if current_price < avg_price else 'ask'
            
            return {
                'index': index,
                'side': side,
                'volatility_reduction': before_volatility - after_volatility,
                'stabilization_price': current_price,
                'market_type': self.market_type
            }
        
        return None
    
    def analyze_market_maker_behavior(self, df: pd.DataFrame, institutional_footprints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze overall market maker behavior
        """
        behavior = {
            'market_maker_active': False,
            'behavior_type': 'unknown',
            'confidence': 0.0,
            'market_phase': 'unknown'
        }
        
        if not institutional_footprints['large_orders_detected']:
            return behavior
        
        # Analyze behavior patterns
        footprints = institutional_footprints['footprint_details']
        
        if len(footprints) >= 3:
            behavior['market_maker_active'] = True
            
            # Determine behavior type
            buying_activity = institutional_footprints['institutional_buying']
            selling_activity = institutional_footprints['institutional_selling']
            
            if buying_activity > selling_activity * 2:
                behavior['behavior_type'] = 'accumulation_phase'
            elif selling_activity > buying_activity * 2:
                behavior['behavior_type'] = 'distribution_phase'
            else:
                behavior['behavior_type'] = 'market_making_phase'
            
            # Calculate confidence
            total_activity = buying_activity + selling_activity
            activity_ratio = max(buying_activity, selling_activity) / total_activity
            behavior['confidence'] = activity_ratio
        
        return behavior
    
    def get_mm_trading_insights(self, institutional_footprints: Dict[str, Any], 
                               price_delivery: Dict[str, Any], 
                               mm_behavior: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get trading insights based on market maker analysis
        """
        insights = []
        
        # Institutional activity insights
        if institutional_footprints['large_orders_detected']:
            dominant_activity = institutional_footprints['dominant_activity']
            
            insights.append({
                'type': 'institutional_flow',
                'insight': f'Institutional {dominant_activity} detected in {self.market_type}',
                'implication': self.get_institutional_flow_implication(dominant_activity),
                'confidence': 0.7
            })
        
        # Algorithm insights
        if price_delivery['algorithms_detected']:
            insights.append({
                'type': 'algorithmic_trading',
                'insight': f'Algorithmic trading patterns detected in {self.market_type}',
                'implication': 'Expect systematic price delivery and potential liquidity zones',
                'confidence': 0.6
            })
        
        # Market maker behavior insights
        if mm_behavior['market_maker_active']:
            insights.append({
                'type': 'market_maker_behavior',
                'insight': f'Market maker {mm_behavior["behavior_type"]} in {self.market_type}',
                'implication': self.get_mm_behavior_implication(mm_behavior['behavior_type']),
                'confidence': mm_behavior['confidence']
            })
        
        return insights
    
    def get_institutional_flow_implication(self, activity_type: str) -> str:
        """Get implication of institutional flow"""
        if self.market_type == 'forex':
            if activity_type == 'buying':
                return "Forex institutional buying: Currency strength building, expect upward pressure"
            else:
                return "Forex institutional selling: Currency weakness, expect downward pressure"
        elif self.market_type == 'crypto':
            if activity_type == 'buying':
                return "Crypto institutional buying: Whale accumulation, expect price appreciation"
            else:
                return "Crypto institutional selling: Whale distribution, expect price decline"
        
        return f"Institutional {activity_type} activity detected"
    
    def get_mm_behavior_implication(self, behavior_type: str) -> str:
        """Get implication of market maker behavior"""
        implications = {
            'accumulation_phase': 'Market makers accumulating - expect upward breakout',
            'distribution_phase': 'Market makers distributing - expect downward pressure',
            'market_making_phase': 'Active market making - expect range-bound trading with liquidity'
        }
        
        base_implication = implications.get(behavior_type, 'Unknown market maker behavior')
        
        if self.market_type == 'forex':
            return f"Forex: {base_implication}"
        elif self.market_type == 'crypto':
            return f"Crypto: {base_implication}"
        
        return base_implication
    
    def calculate_mm_signal_strength(self, institutional_footprints: Dict[str, Any], 
                                   price_delivery: Dict[str, Any], 
                                   liquidity_provision: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate market maker signal strength
        """
        strength_factors = []
        
        # Institutional activity strength
        if institutional_footprints['large_orders_detected']:
            activity_strength = min(len(institutional_footprints['footprint_details']) / 5.0, 1.0)
            strength_factors.append(activity_strength)
        
        # Algorithm detection strength
        if price_delivery['algorithms_detected']:
            algo_strength = 0.7
            strength_factors.append(algo_strength)
        
        # Liquidity provision strength
        if liquidity_provision['provision_events'] > 0:
            liq_strength = min(liquidity_provision['provision_events'] / 3.0, 1.0)
            strength_factors.append(liq_strength)
        
        # Market-specific strength
        market_strength = self.get_market_mm_strength(df)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_market_mm_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific market maker strength"""
        if self.market_type == 'forex':
            # Forex market maker strength based on session
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 13 <= hour <= 16:  # London-NY overlap
                    return 0.9  # Highest MM activity
                elif 8 <= hour <= 22:  # Major sessions
                    return 0.8
                else:
                    return 0.5
            return 0.7
        
        elif self.market_type == 'crypto':
            # Crypto market maker strength based on volume
            if 'volume' in df.columns:
                vol_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
                return min(0.5 + vol_ratio / 4.0, 1.0)
            
            return 0.7
        
        return 0.6
    
    def update_mm_tracking(self, institutional_footprints: Dict[str, Any], 
                          price_delivery: Dict[str, Any], liquidity_provision: Dict[str, Any]):
        """Update market maker tracking"""
        # Update institutional footprints
        if institutional_footprints['large_orders_detected']:
            self.institutional_footprints.extend(institutional_footprints['footprint_details'])
        
        # Update price delivery patterns
        if price_delivery['algorithms_detected']:
            self.price_delivery_patterns.append({
                'timestamp': datetime.now(timezone.utc),
                'algorithms': price_delivery,
                'market_type': self.market_type
            })
        
        # Update liquidity provision
        if liquidity_provision['provision_events'] > 0:
            self.liquidity_provision_events.extend(liquidity_provision['provision_details'])
        
        # Limit tracking sizes
        if len(self.institutional_footprints) > 100:
            self.institutional_footprints = self.institutional_footprints[-100:]
        
        if len(self.price_delivery_patterns) > 50:
            self.price_delivery_patterns = self.price_delivery_patterns[-50:]
        
        if len(self.liquidity_provision_events) > 100:
            self.liquidity_provision_events = self.liquidity_provision_events[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_mm_summary(self) -> Dict[str, Any]:
        """Get comprehensive market maker summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'institutional_footprints_count': len(self.institutional_footprints),
            'price_delivery_patterns_count': len(self.price_delivery_patterns),
            'liquidity_provision_events_count': len(self.liquidity_provision_events),
            'algorithm_sophistication': self.algorithm_sophistication,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'institutional_size_threshold': self.institutional_size_threshold,
                'price_delivery_tolerance': self.price_delivery_tolerance,
                'algorithm_detection_window': self.algorithm_detection_window
            }
        }
    
    def has_institutional_activity(self, activity_type: str = None) -> bool:
        """Check for recent institutional activity"""
        if not self.institutional_footprints:
            return False
        
        recent_footprints = self.institutional_footprints[-10:]
        
        if activity_type:
            return any(fp['institutional_type'] == activity_type for fp in recent_footprints)
        else:
            return len(recent_footprints) > 0
    
    def requires_continuous_processing(self) -> bool:
        """Market maker agent doesn't need continuous processing"""
        return False