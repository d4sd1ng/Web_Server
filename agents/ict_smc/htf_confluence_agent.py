"""
Higher Timeframe (HTF) Confluence Agent
Analyzes multi-timeframe confluence using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class HTFConfluenceAgent(ICTSMCAgent):
    """
    Specialized agent for Higher Timeframe Confluence analysis
    Uses existing get_htf_confluence() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("htf_confluence", config)
        
        # HTF configuration
        self.htf_timeframes = config.get('htf_timeframes', ['1h', '4h', '1d'])
        self.atr_fvg_distance = config.get('atr_fvg_distance', 2.0)
        self.min_timeframe_agreement = config.get('min_timeframe_agreement', 0.6)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # HTF tracking
        self.htf_analysis_history = []
        self.timeframe_performance = {}
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"HTF Confluence Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific HTF configuration"""
        if self.market_type == 'forex':
            # Forex: Focus on session-aligned timeframes
            self.htf_timeframes = ['1h', '4h', '1d', '1w']  # Include weekly for forex
            self.min_timeframe_agreement = max(self.min_timeframe_agreement, 0.7)
            self.session_alignment_required = True
        elif self.market_type == 'crypto':
            # Crypto: Standard timeframes, lower agreement threshold
            self.htf_timeframes = ['1h', '4h', '1d']
            self.min_timeframe_agreement = min(self.min_timeframe_agreement, 0.6)
            self.session_alignment_required = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data for HTF confluence analysis
        
        Args:
            data: Dictionary containing 'symbol', 'price', and timeframe data
            
        Returns:
            Dictionary with HTF confluence analysis results
        """
        required_fields = ['symbol', 'price']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        price = data['price']
        
        try:
            # Get HTF confluence using existing function
            htf_confluence = self.get_htf_confluence(symbol, price, self.htf_timeframes, self.atr_fvg_distance)
            
            # Analyze confluence patterns
            confluence_analysis = self.analyze_confluence_patterns(htf_confluence)
            
            # Calculate timeframe agreement
            timeframe_agreement = self.calculate_timeframe_agreement(htf_confluence)
            
            # Determine overall HTF bias
            htf_bias = self.determine_htf_bias(htf_confluence, timeframe_agreement)
            
            # Calculate signal strength
            signal_strength = self.calculate_htf_signal_strength(htf_confluence, timeframe_agreement)
            
            # Update tracking
            self.update_htf_tracking(htf_confluence, timeframe_agreement, symbol, price)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'price': price,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'htf_confluence': htf_confluence,
                'confluence_analysis': confluence_analysis,
                'timeframe_agreement': timeframe_agreement,
                'htf_bias': htf_bias,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_context': self.get_htf_trading_context(htf_confluence, htf_bias)
            }
            
            # Publish HTF confluence signals
            if timeframe_agreement['agreement_score'] > self.min_timeframe_agreement:
                self.publish("htf_confluence_aligned", {
                    'symbol': symbol,
                    'htf_bias': htf_bias,
                    'agreement_score': timeframe_agreement['agreement_score'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing HTF confluence data for {symbol}: {e}")
            return {'htf_confluence': {}, 'signal_strength': 0.0, 'error': str(e)}
    
    def get_htf_confluence(self, symbol: str, price: float, htf_timeframes: List[str] = None, atr_fvg_distance: float = 2.0) -> Dict[str, Any]:
        """
        Get HTF confluence using existing implementation (simplified for agent)
        """
        if htf_timeframes is None:
            htf_timeframes = self.htf_timeframes
        
        confluence = {}
        
        try:
            # Import your existing functions
            from tradingbot_new import fetch_ohlc, calculate_all_indicators, best_params
            from tradingbot_new import calculate_dealing_range, get_pd_zone, detect_order_blocks, detect_ifvg, get_daily_bias
            
            for tf in htf_timeframes:
                try:
                    # Fetch HTF data
                    df_htf = fetch_ohlc(symbol, tf, 200)
                    if df_htf.empty:
                        continue
                    
                    df_htf = calculate_all_indicators(df_htf, best_params)
                    
                    # Calculate HTF analysis
                    dealing_range = calculate_dealing_range(df_htf)
                    pd_zone = get_pd_zone(dealing_range, price)
                    ote_zone = dealing_range['ote_zone']
                    in_ote = ote_zone[0] <= price <= ote_zone[1]
                    
                    # Order blocks
                    ob_list = detect_order_blocks(df_htf)
                    valid_bull_ob = any(ob['type'] == 'bullish' and ob['retest'] for ob in ob_list)
                    valid_bear_ob = any(ob['type'] == 'bearish' and ob['retest'] for ob in ob_list)
                    
                    # Fair Value Gaps
                    fvg_list = detect_ifvg(df_htf)
                    atr = df_htf['atr'].iloc[-1]
                    near_fvg_bull = any(fvg['type'] == 'bullish' and abs(price - fvg['zone'][0]) < atr_fvg_distance*atr for fvg in fvg_list)
                    near_fvg_bear = any(fvg['type'] == 'bearish' and abs(price - fvg['zone'][1]) < atr_fvg_distance*atr for fvg in fvg_list)
                    
                    # Bias
                    bias = get_daily_bias(df_htf) if tf in ['1d', '1w'] else 'neutral'
                    
                    confluence[tf] = {
                        'in_ote': in_ote,
                        'valid_bull_ob': valid_bull_ob,
                        'valid_bear_ob': valid_bear_ob,
                        'near_fvg_bull': near_fvg_bull,
                        'near_fvg_bear': near_fvg_bear,
                        'pd_zone': pd_zone,
                        'bias': bias,
                        'dealing_range': dealing_range,
                        'atr': atr
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Error analyzing {tf} timeframe: {e}")
                    continue
            
            return confluence
            
        except ImportError:
            # Fallback if functions not available
            return self.basic_htf_analysis(symbol, price, htf_timeframes)
        except Exception as e:
            self.logger.error(f"Error in HTF confluence analysis: {e}")
            return {}
    
    def basic_htf_analysis(self, symbol: str, price: float, htf_timeframes: List[str]) -> Dict[str, Any]:
        """Basic HTF analysis fallback"""
        # Simplified HTF analysis
        confluence = {}
        
        for tf in htf_timeframes:
            confluence[tf] = {
                'in_ote': False,
                'valid_bull_ob': False,
                'valid_bear_ob': False,
                'near_fvg_bull': False,
                'near_fvg_bear': False,
                'pd_zone': 'equilibrium',
                'bias': 'neutral'
            }
        
        return confluence
    
    def analyze_confluence_patterns(self, htf_confluence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze HTF confluence patterns
        """
        if not htf_confluence:
            return {'pattern': 'no_data'}
        
        analysis = {
            'timeframes_analyzed': len(htf_confluence),
            'bullish_confluence_count': 0,
            'bearish_confluence_count': 0,
            'neutral_confluence_count': 0,
            'ote_agreement': 0,
            'ob_agreement': 0,
            'fvg_agreement': 0
        }
        
        # Count confluences by type
        for tf, tf_data in htf_confluence.items():
            # Bullish confluence
            if (tf_data.get('in_ote') and tf_data.get('valid_bull_ob') and 
                tf_data.get('near_fvg_bull') and tf_data.get('bias') == 'bullish'):
                analysis['bullish_confluence_count'] += 1
            
            # Bearish confluence
            elif (tf_data.get('in_ote') and tf_data.get('valid_bear_ob') and 
                  tf_data.get('near_fvg_bear') and tf_data.get('bias') == 'bearish'):
                analysis['bearish_confluence_count'] += 1
            
            else:
                analysis['neutral_confluence_count'] += 1
            
            # Individual factor agreements
            if tf_data.get('in_ote'):
                analysis['ote_agreement'] += 1
            if tf_data.get('valid_bull_ob') or tf_data.get('valid_bear_ob'):
                analysis['ob_agreement'] += 1
            if tf_data.get('near_fvg_bull') or tf_data.get('near_fvg_bear'):
                analysis['fvg_agreement'] += 1
        
        return analysis
    
    def calculate_timeframe_agreement(self, htf_confluence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate agreement between timeframes
        """
        if not htf_confluence:
            return {'agreement_score': 0.0, 'agreement_type': 'no_data'}
        
        total_timeframes = len(htf_confluence)
        bullish_votes = 0
        bearish_votes = 0
        
        for tf, tf_data in htf_confluence.items():
            # Simple voting system
            bullish_factors = sum([
                tf_data.get('valid_bull_ob', False),
                tf_data.get('near_fvg_bull', False),
                tf_data.get('bias') == 'bullish',
                tf_data.get('pd_zone') == 'discount'
            ])
            
            bearish_factors = sum([
                tf_data.get('valid_bear_ob', False),
                tf_data.get('near_fvg_bear', False),
                tf_data.get('bias') == 'bearish',
                tf_data.get('pd_zone') == 'premium'
            ])
            
            if bullish_factors > bearish_factors:
                bullish_votes += 1
            elif bearish_factors > bullish_factors:
                bearish_votes += 1
        
        # Calculate agreement
        max_votes = max(bullish_votes, bearish_votes)
        agreement_score = max_votes / total_timeframes
        
        if bullish_votes > bearish_votes:
            agreement_type = 'bullish'
        elif bearish_votes > bullish_votes:
            agreement_type = 'bearish'
        else:
            agreement_type = 'neutral'
        
        return {
            'agreement_score': agreement_score,
            'agreement_type': agreement_type,
            'bullish_votes': bullish_votes,
            'bearish_votes': bearish_votes,
            'total_timeframes': total_timeframes
        }
    
    def determine_htf_bias(self, htf_confluence: Dict[str, Any], timeframe_agreement: Dict[str, Any]) -> str:
        """
        Determine overall HTF bias
        """
        agreement_score = timeframe_agreement['agreement_score']
        agreement_type = timeframe_agreement['agreement_type']
        
        if agreement_score >= self.min_timeframe_agreement:
            if agreement_type == 'bullish':
                return 'strong_bullish'
            elif agreement_type == 'bearish':
                return 'strong_bearish'
        
        elif agreement_score >= 0.5:
            if agreement_type == 'bullish':
                return 'weak_bullish'
            elif agreement_type == 'bearish':
                return 'weak_bearish'
        
        return 'neutral'
    
    def get_htf_trading_context(self, htf_confluence: Dict[str, Any], htf_bias: str) -> List[Dict[str, Any]]:
        """
        Get HTF trading context and implications
        """
        context = []
        
        # Overall HTF context
        context.append({
            'type': 'htf_bias',
            'message': f'HTF bias: {htf_bias} for {self.market_type} market',
            'implication': self.get_bias_implication(htf_bias)
        })
        
        # Timeframe-specific context
        for tf, tf_data in htf_confluence.items():
            tf_context = self.get_timeframe_context(tf, tf_data)
            if tf_context:
                context.append(tf_context)
        
        # Market-specific context
        market_context = self.get_market_specific_htf_context(htf_confluence, htf_bias)
        if market_context:
            context.append(market_context)
        
        return context
    
    def get_bias_implication(self, htf_bias: str) -> str:
        """Get trading implication for HTF bias"""
        implications = {
            'strong_bullish': 'High probability long setups, avoid shorts',
            'weak_bullish': 'Favor long setups, cautious on shorts',
            'neutral': 'No HTF bias, rely on lower timeframe signals',
            'weak_bearish': 'Favor short setups, cautious on longs',
            'strong_bearish': 'High probability short setups, avoid longs'
        }
        
        base_implication = implications.get(htf_bias, 'No clear HTF direction')
        
        if self.market_type == 'forex':
            return f"Forex: {base_implication}"
        elif self.market_type == 'crypto':
            return f"Crypto: {base_implication}"
        
        return base_implication
    
    def get_timeframe_context(self, timeframe: str, tf_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get context for specific timeframe"""
        context = {
            'type': 'timeframe_analysis',
            'timeframe': timeframe,
            'message': f'{timeframe} analysis',
            'details': []
        }
        
        # OTE context
        if tf_data.get('in_ote'):
            context['details'].append(f'{timeframe}: In OTE zone')
        
        # Order block context
        if tf_data.get('valid_bull_ob'):
            context['details'].append(f'{timeframe}: Valid bullish Order Block')
        if tf_data.get('valid_bear_ob'):
            context['details'].append(f'{timeframe}: Valid bearish Order Block')
        
        # FVG context
        if tf_data.get('near_fvg_bull'):
            context['details'].append(f'{timeframe}: Near bullish FVG')
        if tf_data.get('near_fvg_bear'):
            context['details'].append(f'{timeframe}: Near bearish FVG')
        
        # P/D zone context
        pd_zone = tf_data.get('pd_zone', 'unknown')
        if pd_zone != 'unknown':
            context['details'].append(f'{timeframe}: In {pd_zone} zone')
        
        # Bias context
        bias = tf_data.get('bias', 'neutral')
        if bias != 'neutral':
            context['details'].append(f'{timeframe}: {bias} bias')
        
        return context if context['details'] else None
    
    def get_market_specific_htf_context(self, htf_confluence: Dict[str, Any], htf_bias: str) -> Dict[str, Any]:
        """Get market-specific HTF context"""
        if self.market_type == 'forex':
            return {
                'type': 'forex_htf_context',
                'message': 'Forex HTF analysis',
                'note': 'HTF confluence critical for forex due to institutional flows',
                'recommendation': 'Require strong HTF agreement before major positions'
            }
        
        elif self.market_type == 'crypto':
            return {
                'type': 'crypto_htf_context',
                'message': 'Crypto HTF analysis',
                'note': 'HTF confluence useful but crypto can move independently of HTF',
                'recommendation': 'HTF confluence adds confidence but not required for all trades'
            }
        
        return None
    
    def calculate_htf_signal_strength(self, htf_confluence: Dict[str, Any], timeframe_agreement: Dict[str, Any]) -> float:
        """
        Calculate HTF confluence signal strength
        """
        if not htf_confluence:
            return 0.0
        
        strength_factors = []
        
        # Agreement strength
        agreement_score = timeframe_agreement['agreement_score']
        strength_factors.append(agreement_score)
        
        # Number of timeframes analyzed
        tf_count_strength = min(len(htf_confluence) / 4.0, 1.0)  # Up to 4 timeframes
        strength_factors.append(tf_count_strength)
        
        # Quality of confluences
        confluence_quality = self.calculate_confluence_quality(htf_confluence)
        strength_factors.append(confluence_quality)
        
        # Market-specific strength
        market_strength = self.get_market_htf_strength(htf_confluence)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors)
    
    def calculate_confluence_quality(self, htf_confluence: Dict[str, Any]) -> float:
        """Calculate quality of HTF confluences"""
        quality_scores = []
        
        for tf, tf_data in htf_confluence.items():
            # Count positive factors
            factors = [
                tf_data.get('in_ote', False),
                tf_data.get('valid_bull_ob', False) or tf_data.get('valid_bear_ob', False),
                tf_data.get('near_fvg_bull', False) or tf_data.get('near_fvg_bear', False),
                tf_data.get('bias') != 'neutral',
                tf_data.get('pd_zone') in ['premium', 'discount']
            ]
            
            factor_score = sum(factors) / len(factors)
            quality_scores.append(factor_score)
        
        return np.mean(quality_scores) if quality_scores else 0.0
    
    def get_market_htf_strength(self, htf_confluence: Dict[str, Any]) -> float:
        """Get market-specific HTF strength"""
        if self.market_type == 'forex':
            # Forex: HTF very important
            return 0.9
        elif self.market_type == 'crypto':
            # Crypto: HTF helpful but less critical
            return 0.7
        
        return 0.8
    
    def update_htf_tracking(self, htf_confluence: Dict[str, Any], timeframe_agreement: Dict[str, Any], 
                           symbol: str, price: float):
        """Update HTF analysis tracking"""
        htf_entry = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'price': price,
            'htf_confluence': htf_confluence,
            'timeframe_agreement': timeframe_agreement,
            'market_type': self.market_type
        }
        
        self.htf_analysis_history.append(htf_entry)
        
        # Limit tracking size
        if len(self.htf_analysis_history) > 100:
            self.htf_analysis_history = self.htf_analysis_history[-100:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_htf_summary(self) -> Dict[str, Any]:
        """Get comprehensive HTF confluence summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'htf_timeframes': self.htf_timeframes,
            'analysis_history_count': len(self.htf_analysis_history),
            'min_timeframe_agreement': self.min_timeframe_agreement,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'htf_timeframes': self.htf_timeframes,
                'atr_fvg_distance': self.atr_fvg_distance,
                'session_alignment_required': getattr(self, 'session_alignment_required', False)
            }
        }
    
    def has_strong_htf_confluence(self, direction: str = None) -> bool:
        """Check for strong HTF confluence"""
        if not self.htf_analysis_history:
            return False
        
        latest_analysis = self.htf_analysis_history[-1]
        agreement = latest_analysis['timeframe_agreement']
        
        if direction:
            return (agreement['agreement_type'] == direction and 
                   agreement['agreement_score'] >= self.min_timeframe_agreement)
        else:
            return agreement['agreement_score'] >= self.min_timeframe_agreement
    
    def requires_continuous_processing(self) -> bool:
        """HTF confluence agent doesn't need continuous processing"""
        return False