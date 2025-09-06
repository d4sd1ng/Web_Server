"""
ML Data Collector Agent
Intensive data collection for maximum ML training information
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
import json
import threading
import queue

from agents.base_agent import BaseAgent


class MLDataCollectorAgent(BaseAgent):
    """
    ML Data Collector Agent - Maximum information extraction for ML training
    Collects EVERY possible feature from ALL 42 agents for comprehensive ML datasets
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ml_data_collector", config)
        
        # Data collection configuration for maximum information
        self.collect_all_agent_outputs = config.get('collect_all_agent_outputs', True)
        self.feature_engineering_depth = config.get('feature_engineering_depth', 'maximum')
        self.data_storage_limit = config.get('data_storage_limit', 1000000)  # 1M samples
        self.real_time_collection = config.get('real_time_collection', True)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Comprehensive data storage
        self.raw_agent_data = []
        self.engineered_features = []
        self.market_context_data = []
        self.trade_outcome_data = []
        
        # Feature engineering components
        self.feature_categories = self.define_feature_categories()
        self.feature_extractors = self.initialize_feature_extractors()
        
        # Real-time data collection
        self.data_collection_queue = queue.Queue(maxsize=10000)
        self.collection_thread = None
        self.collecting = False
        
        self.apply_market_specific_config()
        
        self.logger.info(f"ML Data Collector initialized for {self.market_type} - MAXIMUM information extraction mode")
    
    def define_feature_categories(self) -> Dict[str, List[str]]:
        """Define comprehensive feature categories for maximum ML data"""
        return {
            'ict_smc_features': [
                # Fair Value Gaps
                'fvg_bullish_count', 'fvg_bearish_count', 'fvg_total_gap_size', 'fvg_avg_distance',
                'fvg_fill_rate', 'fvg_strength_avg', 'fvg_age_avg', 'fvg_volume_correlation',
                
                # Order Blocks  
                'ob_bullish_count', 'ob_bearish_count', 'ob_retest_rate', 'ob_strength_avg',
                'ob_distance_to_price', 'ob_volume_confirmation', 'ob_age_distribution',
                
                # Market Structure
                'mss_bullish', 'mss_bearish', 'bos_bull', 'bos_bear', 'choch_bull', 'choch_bear',
                'structure_strength', 'structure_consistency', 'trend_duration',
                
                # Liquidity Sweeps
                'sweep_high_count', 'sweep_low_count', 'internal_grab_buy', 'internal_grab_sell',
                'liquidity_efficiency', 'sweep_success_rate', 'liquidity_volume_ratio',
                
                # Premium/Discount
                'pd_zone', 'dealing_range_size', 'price_position_in_range', 'pd_transition_speed',
                
                # OTE
                'in_ote_bullish', 'in_ote_bearish', 'ote_fibonacci_level', 'ote_strength',
                'ote_distance', 'ote_volume_confirmation',
                
                # Advanced Patterns
                'breaker_bullish', 'breaker_bearish', 'breaker_strength', 'breaker_retest_count',
                'sof_bull', 'sof_bear', 'sof_frequency', 'displacement_bull', 'displacement_bear',
                'engulfing_bull', 'engulfing_bear', 'mitigation_bull', 'mitigation_bear',
                
                # Confluence Patterns
                'pattern_cluster_score', 'pattern_cluster_count', 'htf_alignment_score',
                'killzone_active', 'killzone_quality', 'judas_swing_detected',
                'po3_phase', 'po3_strength', 'turtle_soup_detected', 'imbalance_count',
                'momentum_shift_strength'
            ],
            
            'technical_features': [
                # Price Action
                'rsi_14', 'rsi_21', 'rsi_divergence', 'macd_signal', 'macd_histogram',
                'bb_position', 'bb_squeeze', 'stoch_k', 'stoch_d', 'cci', 'adx',
                'atr_normalized', 'volatility_regime', 'trend_strength',
                
                # Volume Analysis
                'volume_spike_ratio', 'volume_trend', 'obv_trend', 'volume_profile_poc',
                'volume_distribution', 'accumulation_distribution', 'volume_consistency',
                
                # Session Analysis
                'session_quality', 'session_volatility', 'session_volume', 'session_type',
                'time_to_session_end', 'session_momentum', 'session_bias'
            ],
            
            'market_context_features': [
                # Market Regime
                'regime_type', 'regime_stability', 'regime_duration', 'regime_transition_prob',
                'volatility_regime', 'trend_regime', 'liquidity_regime',
                
                # Sentiment
                'news_sentiment', 'sentiment_strength', 'sentiment_trend', 'sentiment_volatility',
                
                # Macro Context
                'market_correlation', 'sector_strength', 'risk_sentiment', 'institutional_flow'
            ],
            
            'execution_features': [
                # Risk Metrics
                'position_size_optimal', 'risk_reward_ratio', 'stop_distance_atr',
                'portfolio_heat', 'correlation_risk', 'liquidity_risk',
                
                # Timing Features
                'entry_timing_score', 'entry_precision', 'volume_timing', 'momentum_timing',
                'session_timing', 'volatility_timing'
            ],
            
            'performance_features': [
                # Historical Performance
                'recent_win_rate', 'pattern_success_rate', 'regime_performance',
                'timeframe_performance', 'session_performance', 'volatility_performance',
                'confluence_performance', 'ml_accuracy_recent'
            ]
        }
    
    def initialize_feature_extractors(self) -> Dict[str, Any]:
        """Initialize feature extractors for maximum data collection"""
        return {
            'statistical_extractor': StatisticalFeatureExtractor(),
            'technical_extractor': TechnicalFeatureExtractor(), 
            'pattern_extractor': PatternFeatureExtractor(),
            'sentiment_extractor': SentimentFeatureExtractor(),
            'regime_extractor': RegimeFeatureExtractor(),
            'execution_extractor': ExecutionFeatureExtractor()
        }