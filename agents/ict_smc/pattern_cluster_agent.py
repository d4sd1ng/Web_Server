"""
Pattern Cluster Agent
Detects pattern clusters and confluences using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class PatternClusterAgent(ICTSMCAgent):
    """
    Specialized agent for Pattern Cluster detection
    Uses existing detect_pattern_cluster() and pattern evaluation functions
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("pattern_cluster", config)
        
        # Pattern cluster configuration
        self.min_pattern_cluster = config.get('min_pattern_cluster', 3)
        self.pattern_weights = config.get('pattern_weights', {})
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Pattern definitions from your existing code
        self.patterns_long = self.load_long_patterns()
        self.patterns_short = self.load_short_patterns()
        
        # Cluster tracking
        self.detected_clusters = []
        self.pattern_performance = {}
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Pattern Cluster Agent initialized for {self.market_type} market")
    
    def load_long_patterns(self) -> List[Dict[str, Any]]:
        """Load long pattern definitions from existing code"""
        return [
            {
                "name": "engulfing_mss_ote_killzone",
                "keys": ['bullish_engulf', 'bullish_mss', 'in_ote', 'valid_bull_ob', 'bullish_disp', 'in_killzone'],
                "n": 3,
                "description": "Bullish engulfing + MSS + OTE confluence"
            },
            {
                "name": "breaker_disp_ote_killzone",
                "keys": ['bullish_breaker', 'bullish_mss', 'swept_high', 'in_killzone', 'sof_bull', 'in_ote'],
                "n": 3,
                "description": "Breaker + displacement + OTE confluence"
            },
            {
                "name": "ob_liq_ote_killzone",
                "keys": ['valid_bull_ob', 'internal_buy_grab', 'in_ote', 'bullish_disp', 'in_killzone'],
                "n": 3,
                "description": "Order block + liquidity + OTE confluence"
            },
            {
                "name": "comprehensive_bullish_cluster",
                "keys": ['bullish_engulf', 'bullish_mss', 'in_ote', 'valid_bull_ob', 'bullish_disp', 'bullish_breaker', 'sof_bull', 'in_killzone'],
                "n": 5,
                "description": "Comprehensive bullish pattern cluster"
            }
        ]
    
    def load_short_patterns(self) -> List[Dict[str, Any]]:
        """Load short pattern definitions from existing code"""
        return [
            {
                "name": "engulfing_mss_ote_killzone_short",
                "keys": ['bearish_engulf', 'bearish_mss', 'in_ote', 'valid_bear_ob', 'bearish_disp', 'in_killzone'],
                "n": 3,
                "description": "Bearish engulfing + MSS + OTE confluence"
            },
            {
                "name": "breaker_disp_ote_killzone_short",
                "keys": ['bearish_breaker', 'bearish_mss', 'swept_low', 'in_killzone', 'sof_bear', 'in_ote'],
                "n": 3,
                "description": "Bearish breaker + displacement + OTE confluence"
            },
            {
                "name": "ob_liq_ote_killzone_short",
                "keys": ['valid_bear_ob', 'internal_sell_grab', 'in_ote', 'bearish_disp', 'in_killzone'],
                "n": 3,
                "description": "Bearish order block + liquidity + OTE confluence"
            },
            {
                "name": "comprehensive_bearish_cluster",
                "keys": ['bearish_engulf', 'bearish_mss', 'in_ote', 'valid_bear_ob', 'bearish_disp', 'bearish_breaker', 'sof_bear', 'in_killzone'],
                "n": 5,
                "description": "Comprehensive bearish pattern cluster"
            }
        ]
    
    def apply_market_specific_config(self):
        """Apply market-specific pattern cluster configuration"""
        if self.market_type == 'forex':
            # Forex: Require more confluence due to lower volatility
            self.min_pattern_cluster = max(self.min_pattern_cluster, 4)
            self.killzone_weight = 1.5  # Killzones very important for forex
        elif self.market_type == 'crypto':
            # Crypto: Can work with fewer confluences due to higher volatility
            self.min_pattern_cluster = min(self.min_pattern_cluster, 3)
            self.killzone_weight = 1.0  # Killzones less critical for crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to detect pattern clusters
        
        Args:
            data: Dictionary containing agent results and 'symbol'
            
        Returns:
            Dictionary with pattern cluster analysis results
        """
        required_fields = ['symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        
        try:
            # Collect pattern data from other agents
            pattern_data = self.collect_pattern_data(data)
            
            # Evaluate long patterns
            long_clusters = self.evaluate_pattern_clusters(pattern_data, 'long')
            
            # Evaluate short patterns
            short_clusters = self.evaluate_pattern_clusters(pattern_data, 'short')
            
            # Analyze cluster quality
            cluster_analysis = self.analyze_cluster_quality(long_clusters, short_clusters, pattern_data)
            
            # Calculate signal strength
            signal_strength = self.calculate_cluster_signal_strength(long_clusters, short_clusters, pattern_data)
            
            # Update tracking
            self.update_cluster_tracking(long_clusters, short_clusters, pattern_data)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'long_clusters': long_clusters,
                'short_clusters': short_clusters,
                'cluster_analysis': cluster_analysis,
                'pattern_data': pattern_data,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_setups': self.identify_cluster_setups(long_clusters, short_clusters, pattern_data)
            }
            
            # Publish cluster signals
            if long_clusters['triggered_patterns'] or short_clusters['triggered_patterns']:
                self.publish("pattern_cluster_detected", {
                    'symbol': symbol,
                    'long_clusters': long_clusters['triggered_patterns'],
                    'short_clusters': short_clusters['triggered_patterns'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing pattern cluster data for {symbol}: {e}")
            return {'pattern_clusters': [], 'signal_strength': 0.0, 'error': str(e)}
    
    def collect_pattern_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect pattern data from other agent results
        """
        pattern_data = {}
        
        # Fair Value Gaps
        if 'fair_value_gaps' in data:
            fvg_data = data['fair_value_gaps']
            fvgs = fvg_data.get('fvgs', [])
            pattern_data['near_fvg_bull'] = any(fvg['type'] == 'bullish' for fvg in fvgs)
            pattern_data['near_fvg_bear'] = any(fvg['type'] == 'bearish' for fvg in fvgs)
        
        # Order Blocks
        if 'order_blocks' in data:
            ob_data = data['order_blocks']
            obs = ob_data.get('order_blocks', [])
            pattern_data['valid_bull_ob'] = any(ob['type'] == 'bullish' and ob['retest'] for ob in obs)
            pattern_data['valid_bear_ob'] = any(ob['type'] == 'bearish' and ob['retest'] for ob in obs)
        
        # Market Structure
        if 'market_structure' in data:
            ms_data = data['market_structure']
            mss_data = ms_data.get('market_structure_shifts', {})
            bos_data = ms_data.get('break_of_structure', {})
            
            pattern_data['bullish_mss'] = mss_data.get('bullish_mss', False)
            pattern_data['bearish_mss'] = mss_data.get('bearish_mss', False)
            pattern_data['bos_bull'] = bos_data.get('bos_bull', False)
            pattern_data['bos_bear'] = bos_data.get('bos_bear', False)
        
        # Liquidity Sweeps
        if 'liquidity_sweeps' in data:
            liq_data = data['liquidity_sweeps']
            sweep_data = liq_data.get('swing_sweeps', {})
            internal_data = liq_data.get('internal_grabs', {})
            
            pattern_data['swept_high'] = sweep_data.get('swept_high', False)
            pattern_data['swept_low'] = sweep_data.get('swept_low', False)
            pattern_data['internal_buy_grab'] = internal_data.get('internal_buy_grab', False)
            pattern_data['internal_sell_grab'] = internal_data.get('internal_sell_grab', False)
        
        # Premium/Discount
        if 'premium_discount' in data:
            pd_data = data['premium_discount']
            pd_zone = pd_data.get('current_pd_zone', 'equilibrium')
            pattern_data['in_premium'] = pd_zone == 'premium'
            pattern_data['in_discount'] = pd_zone == 'discount'
            pattern_data['in_equilibrium'] = 'equilibrium' in pd_zone
        
        # OTE
        if 'ote' in data:
            ote_data = data['ote']
            ote_analysis = ote_data.get('ote_analysis', {})
            pattern_data['in_ote'] = ote_analysis.get('in_any_ote', False)
            pattern_data['in_ote_long'] = ote_analysis.get('in_ote_long', False)
            pattern_data['in_ote_short'] = ote_analysis.get('in_ote_short', False)
        
        # Killzone
        if 'killzone' in data:
            kz_data = data['killzone']
            kz_status = kz_data.get('killzone_status', {})
            pattern_data['in_killzone'] = kz_status.get('in_killzone', False)
        
        # Breaker Blocks
        if 'breaker_blocks' in data:
            bb_data = data['breaker_blocks']
            pattern_data['bullish_breaker'] = bb_data.get('bullish_breaker', False)
            pattern_data['bearish_breaker'] = bb_data.get('bearish_breaker', False)
        
        # SOF
        if 'sof' in data:
            sof_data = data['sof']
            pattern_data['sof_bull'] = sof_data.get('sof_bull', False)
            pattern_data['sof_bear'] = sof_data.get('sof_bear', False)
        
        # Displacement
        if 'displacement' in data:
            disp_data = data['displacement']
            pattern_data['bullish_disp'] = disp_data.get('bullish_displacement', False)
            pattern_data['bearish_disp'] = disp_data.get('bearish_displacement', False)
        
        # Engulfing
        if 'engulfing' in data:
            eng_data = data['engulfing']
            pattern_data['bullish_engulf'] = eng_data.get('bullish_engulfing', False)
            pattern_data['bearish_engulf'] = eng_data.get('bearish_engulfing', False)
        
        # Mitigation Blocks
        if 'mitigation_blocks' in data:
            mb_data = data['mitigation_blocks']
            mbs = mb_data.get('mitigation_blocks', [])
            pattern_data['valid_bull_mb'] = any(mb['type'] == 'bullish' and mb['validated'] for mb in mbs)
            pattern_data['valid_bear_mb'] = any(mb['type'] == 'bearish' and mb['validated'] for mb in mbs)
        
        return pattern_data
    
    def evaluate_pattern_clusters(self, pattern_data: Dict[str, Any], direction: str) -> Dict[str, Any]:
        """
        Evaluate pattern clusters for specific direction
        """
        patterns = self.patterns_long if direction == 'long' else self.patterns_short
        triggered_patterns = []
        pattern_scores = []
        
        for pattern in patterns:
            # Count how many pattern keys are active
            active_keys = sum(1 for key in pattern['keys'] if pattern_data.get(key, False))
            required_keys = pattern['n']
            
            if active_keys >= required_keys:
                # Pattern is triggered
                pattern_score = self.calculate_pattern_score(pattern, pattern_data, active_keys)
                
                triggered_patterns.append({
                    'name': pattern['name'],
                    'keys': pattern['keys'],
                    'required': required_keys,
                    'active': active_keys,
                    'score': pattern_score,
                    'market_type': self.market_type
                })
                pattern_scores.append(pattern_score)
        
        return {
            'direction': direction,
            'triggered_patterns': triggered_patterns,
            'pattern_count': len(triggered_patterns),
            'avg_pattern_score': np.mean(pattern_scores) if pattern_scores else 0.0,
            'max_pattern_score': max(pattern_scores) if pattern_scores else 0.0,
            'cluster_strength': self.calculate_cluster_strength(triggered_patterns, pattern_data)
        }
    
    def calculate_pattern_score(self, pattern: Dict[str, Any], pattern_data: Dict[str, Any], active_keys: int) -> float:
        """
        Calculate score for individual pattern
        """
        base_score = active_keys / len(pattern['keys'])
        
        # Apply pattern weights
        pattern_weight = self.pattern_weights.get(pattern['name'], 1.0)
        weighted_score = base_score * pattern_weight
        
        # Market-specific adjustments
        if self.market_type == 'forex':
            # Forex patterns need killzone for higher score
            if pattern_data.get('in_killzone', False):
                weighted_score *= 1.3
            else:
                weighted_score *= 0.7
        
        elif self.market_type == 'crypto':
            # Crypto patterns benefit from volume confirmation
            if pattern_data.get('volume_spike', False):
                weighted_score *= 1.2
        
        return min(weighted_score, 1.0)
    
    def calculate_cluster_strength(self, triggered_patterns: List[Dict[str, Any]], pattern_data: Dict[str, Any]) -> float:
        """
        Calculate overall cluster strength
        """
        if not triggered_patterns:
            return 0.0
        
        strength_factors = []
        
        # Number of patterns triggered
        pattern_count_strength = min(len(triggered_patterns) / 3.0, 1.0)
        strength_factors.append(pattern_count_strength)
        
        # Average pattern score
        avg_score = np.mean([p['score'] for p in triggered_patterns])
        strength_factors.append(avg_score)
        
        # Confluence bonus (more patterns = stronger signal)
        if len(triggered_patterns) > 1:
            confluence_bonus = min(len(triggered_patterns) * 0.15, 0.5)
            strength_factors.append(confluence_bonus)
        
        # Market-specific cluster strength
        market_strength = self.get_market_cluster_strength(pattern_data)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors)
    
    def get_market_cluster_strength(self, pattern_data: Dict[str, Any]) -> float:
        """Get market-specific cluster strength"""
        if self.market_type == 'forex':
            # Forex cluster strength enhanced by session timing
            base_strength = 0.7
            if pattern_data.get('in_killzone', False):
                base_strength += 0.2
            return min(base_strength, 1.0)
        
        elif self.market_type == 'crypto':
            # Crypto cluster strength enhanced by volume
            base_strength = 0.7
            if pattern_data.get('volume_spike', False):
                base_strength += 0.2
            return min(base_strength, 1.0)
        
        return 0.7
    
    def analyze_cluster_quality(self, long_clusters: Dict[str, Any], short_clusters: Dict[str, Any], 
                               pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze overall cluster quality
        """
        analysis = {
            'total_clusters': long_clusters['pattern_count'] + short_clusters['pattern_count'],
            'cluster_bias': 'neutral',
            'cluster_quality': 'unknown',
            'confluence_level': 'low'
        }
        
        # Determine cluster bias
        if long_clusters['pattern_count'] > short_clusters['pattern_count']:
            analysis['cluster_bias'] = 'bullish'
        elif short_clusters['pattern_count'] > long_clusters['pattern_count']:
            analysis['cluster_bias'] = 'bearish'
        
        # Determine cluster quality
        max_score = max(long_clusters['max_pattern_score'], short_clusters['max_pattern_score'])
        if max_score > 0.8:
            analysis['cluster_quality'] = 'excellent'
        elif max_score > 0.6:
            analysis['cluster_quality'] = 'good'
        elif max_score > 0.4:
            analysis['cluster_quality'] = 'fair'
        else:
            analysis['cluster_quality'] = 'poor'
        
        # Determine confluence level
        total_patterns = analysis['total_clusters']
        if total_patterns >= 5:
            analysis['confluence_level'] = 'very_high'
        elif total_patterns >= 3:
            analysis['confluence_level'] = 'high'
        elif total_patterns >= 2:
            analysis['confluence_level'] = 'medium'
        else:
            analysis['confluence_level'] = 'low'
        
        # Market-specific quality adjustments
        if self.market_type == 'forex':
            if not pattern_data.get('in_killzone', False):
                analysis['cluster_quality'] = self.downgrade_quality(analysis['cluster_quality'])
        
        return analysis
    
    def downgrade_quality(self, quality: str) -> str:
        """Downgrade cluster quality by one level"""
        quality_levels = ['poor', 'fair', 'good', 'excellent']
        try:
            current_index = quality_levels.index(quality)
            return quality_levels[max(0, current_index - 1)]
        except ValueError:
            return 'poor'
    
    def identify_cluster_setups(self, long_clusters: Dict[str, Any], short_clusters: Dict[str, Any], 
                               pattern_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify trading setups based on pattern clusters
        """
        setups = []
        
        # Long setups
        if long_clusters['triggered_patterns']:
            best_long_pattern = max(long_clusters['triggered_patterns'], key=lambda x: x['score'])
            
            setups.append({
                'direction': 'long',
                'setup_type': 'pattern_cluster',
                'primary_pattern': best_long_pattern['name'],
                'pattern_score': best_long_pattern['score'],
                'confluence_count': best_long_pattern['active'],
                'cluster_strength': long_clusters['cluster_strength'],
                'market_context': self.get_setup_market_context('long', pattern_data),
                'risk_level': self.assess_setup_risk('long', best_long_pattern, pattern_data)
            })
        
        # Short setups
        if short_clusters['triggered_patterns']:
            best_short_pattern = max(short_clusters['triggered_patterns'], key=lambda x: x['score'])
            
            setups.append({
                'direction': 'short',
                'setup_type': 'pattern_cluster',
                'primary_pattern': best_short_pattern['name'],
                'pattern_score': best_short_pattern['score'],
                'confluence_count': best_short_pattern['active'],
                'cluster_strength': short_clusters['cluster_strength'],
                'market_context': self.get_setup_market_context('short', pattern_data),
                'risk_level': self.assess_setup_risk('short', best_short_pattern, pattern_data)
            })
        
        return setups
    
    def get_setup_market_context(self, direction: str, pattern_data: Dict[str, Any]) -> str:
        """Get market context for setup"""
        if self.market_type == 'forex':
            context = f"Forex {direction} cluster: "
            if pattern_data.get('in_killzone', False):
                context += "Session-based setup with high probability"
            else:
                context += "Off-session setup - proceed with caution"
        
        elif self.market_type == 'crypto':
            context = f"Crypto {direction} cluster: "
            if pattern_data.get('volume_spike', False):
                context += "Volume-confirmed setup with good probability"
            else:
                context += "Standard cluster setup"
        
        return context
    
    def assess_setup_risk(self, direction: str, pattern: Dict[str, Any], pattern_data: Dict[str, Any]) -> str:
        """Assess risk level for setup"""
        risk_factors = []
        
        # Pattern score risk
        if pattern['score'] > 0.8:
            risk_factors.append('low')
        elif pattern['score'] > 0.6:
            risk_factors.append('medium')
        else:
            risk_factors.append('high')
        
        # Confluence risk
        if pattern['active'] >= 5:
            risk_factors.append('low')
        elif pattern['active'] >= 3:
            risk_factors.append('medium')
        else:
            risk_factors.append('high')
        
        # Market-specific risk
        if self.market_type == 'forex':
            if not pattern_data.get('in_killzone', False):
                risk_factors.append('high')
        elif self.market_type == 'crypto':
            if not pattern_data.get('volume_spike', False):
                risk_factors.append('medium')
        
        # Determine overall risk
        risk_counts = {'low': 0, 'medium': 0, 'high': 0}
        for risk in risk_factors:
            risk_counts[risk] += 1
        
        if risk_counts['low'] >= risk_counts['medium'] and risk_counts['low'] >= risk_counts['high']:
            return 'low'
        elif risk_counts['high'] > risk_counts['medium']:
            return 'high'
        else:
            return 'medium'
    
    def calculate_cluster_signal_strength(self, long_clusters: Dict[str, Any], short_clusters: Dict[str, Any], 
                                        pattern_data: Dict[str, Any]) -> float:
        """
        Calculate pattern cluster signal strength
        """
        strength_factors = []
        
        # Long cluster strength
        if long_clusters['triggered_patterns']:
            strength_factors.append(long_clusters['cluster_strength'])
        
        # Short cluster strength
        if short_clusters['triggered_patterns']:
            strength_factors.append(short_clusters['cluster_strength'])
        
        # Confluence strength
        total_patterns = long_clusters['pattern_count'] + short_clusters['pattern_count']
        confluence_strength = min(total_patterns / 5.0, 1.0)
        strength_factors.append(confluence_strength)
        
        # Market-specific strength
        market_strength = self.get_market_cluster_strength(pattern_data)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def update_cluster_tracking(self, long_clusters: Dict[str, Any], short_clusters: Dict[str, Any], 
                               pattern_data: Dict[str, Any]):
        """Update pattern cluster tracking"""
        if long_clusters['triggered_patterns'] or short_clusters['triggered_patterns']:
            cluster_event = {
                'timestamp': datetime.now(timezone.utc),
                'long_clusters': long_clusters,
                'short_clusters': short_clusters,
                'pattern_data': pattern_data,
                'market_type': self.market_type
            }
            
            self.detected_clusters.append(cluster_event)
            
            # Limit tracking size
            if len(self.detected_clusters) > 100:
                self.detected_clusters = self.detected_clusters[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_cluster_summary(self) -> Dict[str, Any]:
        """Get comprehensive pattern cluster summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'detected_clusters_count': len(self.detected_clusters),
            'long_patterns_count': len(self.patterns_long),
            'short_patterns_count': len(self.patterns_short),
            'min_pattern_cluster': self.min_pattern_cluster,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'min_pattern_cluster': self.min_pattern_cluster,
                'killzone_weight': self.killzone_weight,
                'pattern_weights': self.pattern_weights
            }
        }
    
    def has_active_cluster(self, direction: str = None, min_score: float = 0.6) -> bool:
        """Check for active high-quality clusters"""
        if not self.detected_clusters:
            return False
        
        recent_cluster = self.detected_clusters[-1]
        
        if direction == 'long':
            long_patterns = recent_cluster['long_clusters']['triggered_patterns']
            return any(p['score'] >= min_score for p in long_patterns)
        elif direction == 'short':
            short_patterns = recent_cluster['short_clusters']['triggered_patterns']
            return any(p['score'] >= min_score for p in short_patterns)
        else:
            # Any direction
            all_patterns = (recent_cluster['long_clusters']['triggered_patterns'] + 
                           recent_cluster['short_clusters']['triggered_patterns'])
            return any(p['score'] >= min_score for p in all_patterns)
    
    def requires_continuous_processing(self) -> bool:
        """Pattern cluster agent doesn't need continuous processing"""
        return False