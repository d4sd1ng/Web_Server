"""
Trade Frequency Optimizer Agent
CRITICAL: Prevents over-filtering that results in no trades
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent


class TradeFrequencyOptimizerAgent(BaseAgent):
    """
    CRITICAL agent for balancing win rate targeting with trade execution frequency
    Prevents over-filtering that results in no trades
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("trade_frequency_optimizer", config)
        
        # Trade frequency configuration for MAXIMUM ML data collection
        self.min_trades_per_day = config.get('min_trades_per_day', 10)   # Higher for ML data
        self.max_trades_per_day = config.get('max_trades_per_day', 200)  # MAXIMUM for backtesting
        self.target_trades_per_week = config.get('target_trades_per_week', 500) # MAXIMUM ML data
        self.testnet_mode = config.get('testnet_mode', True)  # Enable testnet mode
        self.ml_data_collection_mode = config.get('ml_data_collection_mode', True)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Current settings (BALANCED for trade execution)
        self.current_settings = self.load_balanced_settings()
        
        # Frequency tracking
        self.frequency_history = []
        self.parameter_adjustments = []
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Trade Frequency Optimizer initialized - MAXIMUM data collection mode for {self.market_type}")
    
    def load_balanced_settings(self) -> Dict[str, Any]:
        """Load balanced settings that ensure trade execution"""
        if self.market_type == 'forex':
            return {
                'confluence_coordinator': {
                    'min_confluence_patterns': 3,  # BALANCED (not 6)
                    'min_confluence_score': 4.0    # BALANCED (not 10.0)
                },
                'ml_ensemble': {
                    'confidence_threshold': 0.7,   # BALANCED (not 0.95)
                    'model_agreement_threshold': 0.65  # BALANCED (not 0.9)
                },
                'master_coordinator': {
                    'decision_confidence_threshold': 0.75  # BALANCED (not 0.95)
                }
            }
        else:  # crypto
            return {
                'confluence_coordinator': {
                    'min_confluence_patterns': 2,  # BALANCED (not 5)
                    'min_confluence_score': 3.5    # BALANCED (not 8.5)
                },
                'ml_ensemble': {
                    'confidence_threshold': 0.65,  # BALANCED (not 0.9)
                    'model_agreement_threshold': 0.6   # BALANCED (not 0.85)
                },
                'master_coordinator': {
                    'decision_confidence_threshold': 0.7   # BALANCED (not 0.95)
                }
            }
    
    def apply_market_specific_config(self):
        """Apply market-specific frequency optimization"""
        if self.testnet_mode or self.ml_data_collection_mode:
            # MAXIMUM DATA COLLECTION MODE
            self.min_trades_per_day = max(self.min_trades_per_day, 15)  # 15+ trades/day minimum
            self.max_trades_per_day = max(self.max_trades_per_day, 200) # Up to 200 trades/day
            self.target_trades_per_week = max(self.target_trades_per_week, 500) # 500+ trades/week
            self.logger.info("MAXIMUM DATA COLLECTION MODE: Ultra-high frequency for ML training")
        
        if self.market_type == 'crypto':
            # Crypto: 24/7 trading allows MAXIMUM frequency for ML data
            if self.testnet_mode or self.ml_data_collection_mode:
                self.min_trades_per_day = max(self.min_trades_per_day, 20) # 20+ per day for ML data
                self.target_trades_per_day = 50  # Target 50 trades/day for maximum data
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process trade frequency optimization"""
        try:
            # Monitor current frequency
            frequency_metrics = self.calculate_frequency_metrics(data)
            
            # Check if adjustment needed
            adjustment_needed = self.assess_adjustment_necessity(frequency_metrics)
            
            # Apply adjustments if needed
            if adjustment_needed['adjustment_needed']:
                adjustment_result = self.apply_frequency_adjustments(adjustment_needed)
            else:
                adjustment_result = {'adjustments_applied': 0}
            
            results = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'frequency_metrics': frequency_metrics,
                'adjustment_needed': adjustment_needed,
                'adjustment_result': adjustment_result,
                'current_settings': self.current_settings,
                'signal_strength': self.calculate_frequency_signal_strength(frequency_metrics),
                'market_type': self.market_type
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in frequency optimization: {e}")
            return {'frequency_optimization': 'error', 'signal_strength': 0.0, 'error': str(e)}
    
    def calculate_frequency_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate trade frequency metrics"""
        recent_trades = data.get('recent_trades', [])
        rejected_opportunities = data.get('rejected_opportunities', [])
        
        # Simplified frequency calculation
        trades_count = len(recent_trades)
        rejections_count = len(rejected_opportunities)
        total_opportunities = trades_count + rejections_count
        
        execution_rate = trades_count / total_opportunities if total_opportunities > 0 else 0
        trades_per_day = trades_count / 7.0  # Assume 7-day window
        
        return {
            'trades_per_day': trades_per_day,
            'execution_rate': execution_rate,
            'total_opportunities': total_opportunities,
            'trades_count': trades_count,
            'rejections_count': rejections_count
        }
    
    def assess_adjustment_necessity(self, frequency_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess if parameter adjustment is needed"""
        trades_per_day = frequency_metrics['trades_per_day']
        execution_rate = frequency_metrics['execution_rate']
        
        adjustment_needed = False
        adjustment_type = 'none'
        
        # Check for low frequency issues
        if trades_per_day < self.min_trades_per_day * 0.5:
            adjustment_needed = True
            adjustment_type = 'emergency_relaxation'
        elif trades_per_day < self.min_trades_per_day * 0.8:
            adjustment_needed = True
            adjustment_type = 'moderate_relaxation'
        elif execution_rate < 0.1:  # Less than 10% execution
            adjustment_needed = True
            adjustment_type = 'filter_relaxation'
        
        return {
            'adjustment_needed': adjustment_needed,
            'adjustment_type': adjustment_type,
            'trades_per_day': trades_per_day,
            'min_required': self.min_trades_per_day,
            'execution_rate': execution_rate
        }
    
    def apply_frequency_adjustments(self, adjustment_needed: Dict[str, Any]) -> Dict[str, Any]:
        """Apply frequency adjustments to maintain trade flow"""
        adjustment_type = adjustment_needed['adjustment_type']
        
        if adjustment_type == 'emergency_relaxation':
            # Emergency: Significantly relax parameters
            adjustments = [
                ('confluence_coordinator', 'min_confluence_patterns', -1),
                ('confluence_coordinator', 'min_confluence_score', -2.0),
                ('ml_ensemble', 'confidence_threshold', -0.1)
            ]
            self.logger.warning("EMERGENCY: Relaxing parameters to restore trade execution")
            
        elif adjustment_type == 'moderate_relaxation':
            # Moderate: Slightly relax parameters
            adjustments = [
                ('confluence_coordinator', 'min_confluence_score', -1.0),
                ('ml_ensemble', 'confidence_threshold', -0.05)
            ]
            self.logger.info("MODERATE: Relaxing parameters to improve trade frequency")
            
        elif adjustment_type == 'filter_relaxation':
            # Light: Minor adjustments
            adjustments = [
                ('confluence_coordinator', 'min_confluence_score', -0.5)
            ]
            self.logger.info("LIGHT: Minor parameter relaxation for frequency")
        else:
            adjustments = []
        
        # Apply adjustments
        applied_count = 0
        for agent, parameter, adjustment in adjustments:
            try:
                if agent not in self.current_settings:
                    self.current_settings[agent] = {}
                
                old_value = self.current_settings[agent].get(parameter, 0)
                new_value = max(0.1, old_value + adjustment)  # Ensure positive values
                self.current_settings[agent][parameter] = new_value
                
                applied_count += 1
                self.logger.info(f"Adjusted {agent}.{parameter}: {old_value:.2f} → {new_value:.2f}")
                
            except Exception as e:
                self.logger.error(f"Error applying adjustment: {e}")
        
        return {
            'adjustments_applied': applied_count,
            'adjustment_type': adjustment_type,
            'new_settings': self.current_settings
        }
    
    def calculate_frequency_signal_strength(self, frequency_metrics: Dict[str, Any]) -> float:
        """Calculate signal strength based on frequency balance"""
        trades_per_day = frequency_metrics['trades_per_day']
        execution_rate = frequency_metrics['execution_rate']
        
        # Balance between frequency and quality
        frequency_score = min(trades_per_day / self.min_trades_per_day, 1.0)
        execution_score = min(execution_rate / 0.2, 1.0)  # Target 20% execution
        
        return (frequency_score * 0.6 + execution_score * 0.4)
    
    def get_signal_strength(self) -> float:
        """Get current signal strength"""
        return 0.8  # Default good strength for frequency optimizer
    
    def requires_continuous_processing(self) -> bool:
        """Frequency optimizer needs monitoring"""
        return True