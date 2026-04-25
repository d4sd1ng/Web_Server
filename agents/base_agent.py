"""
Base Agent Class for ICT/SMC Trading System
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import logging


class ICTSMCAgent(ABC):
    """
    Abstract base class for all ICT/SMC trading agents.
    
    All concrete agent implementations must inherit from this class
    and implement the required abstract methods.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the agent with configuration parameters.
        
        Args:
            config: Dictionary containing agent configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.is_active = True
        self.last_signal_time = None
        self.signal_history = []
        
    @abstractmethod
    def process_data(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Process market data and return analysis results.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        pass
    
    @abstractmethod
    def get_signal_strength(self, df: pd.DataFrame, symbol: str = None) -> float:
        """
        Calculate the strength of the current signal (0.0 to 1.0).
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Signal strength as float between 0.0 and 1.0
        """
        pass
    
    def get_signals(self, df: pd.DataFrame, symbol: str = None) -> Dict[str, Any]:
        """
        Get trading signals from the agent.
        
        Args:
            df: OHLCV DataFrame with indicators
            symbol: Trading symbol (optional)
            
        Returns:
            Dictionary containing signal information
        """
        try:
            if not self.is_active or df.empty:
                return self._empty_signal()
            
            # Process the data
            analysis = self.process_data(df, symbol)
            
            # Get signal strength
            strength = self.get_signal_strength(df, symbol)
            
            # Combine results
            signals = {
                'agent_name': self.name,
                'symbol': symbol,
                'timestamp': datetime.now(),
                'signal_strength': strength,
                'analysis': analysis,
                'is_valid': strength > 0.0,
                'confidence': min(strength, 1.0)
            }
            
            # Store signal history
            self._update_signal_history(signals)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error in {self.name}.get_signals: {e}")
            return self._empty_signal()
    
    def _empty_signal(self) -> Dict[str, Any]:
        """Return an empty signal structure."""
        return {
            'agent_name': self.name,
            'symbol': None,
            'timestamp': datetime.now(),
            'signal_strength': 0.0,
            'analysis': {},
            'is_valid': False,
            'confidence': 0.0
        }
    
    def _update_signal_history(self, signal: Dict[str, Any], max_history: int = 100):
        """Update signal history with size limit."""
        self.signal_history.append(signal)
        if len(self.signal_history) > max_history:
            self.signal_history = self.signal_history[-max_history:]
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback."""
        return self.config.get(key, default)
    
    def set_active(self, active: bool):
        """Enable or disable the agent."""
        self.is_active = active
        self.logger.info(f"{self.name} {'activated' if active else 'deactivated'}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            'name': self.name,
            'is_active': self.is_active,
            'last_signal_time': self.last_signal_time,
            'signal_count': len(self.signal_history),
            'config': self.config
        }


class BasePatternAgent(ICTSMCAgent):
    """
    Base class for pattern-based ICT/SMC agents.
    Provides common pattern detection functionality.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.lookback_period = self.get_config_value('lookback_period', 20)
        self.min_pattern_strength = self.get_config_value('min_pattern_strength', 0.5)
        
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate that DataFrame has minimum required data."""
        if df is None or df.empty:
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            return False
        
        if len(df) < self.lookback_period:
            return False
        
        return True
    
    def calculate_pattern_strength(self, conditions: List[bool], weights: List[float] = None) -> float:
        """
        Calculate pattern strength based on multiple conditions.
        
        Args:
            conditions: List of boolean conditions
            weights: Optional weights for each condition
            
        Returns:
            Pattern strength between 0.0 and 1.0
        """
        if not conditions:
            return 0.0
        
        if weights is None:
            weights = [1.0] * len(conditions)
        
        if len(weights) != len(conditions):
            weights = [1.0] * len(conditions)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(w for c, w in zip(conditions, weights) if c)
        return min(weighted_score / total_weight, 1.0)