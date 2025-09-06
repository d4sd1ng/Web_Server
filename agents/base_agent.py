"""
Base Agent Classes for Trading System
Provides foundation for all specialized trading agents
"""

import uuid
import logging
import threading
import time
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable


class BaseAgent(ABC):
    """
    Base class for all trading agents
    Provides common functionality and interface
    """
    
    def __init__(self, agent_type: str, config: Dict[str, Any] = None):
        self.agent_id = str(uuid.uuid4())
        self.agent_type = agent_type
        self.config = config or {}
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Agent state
        self.active = False
        self.last_update = None
        self.message_bus = None
        self.subscriptions = []
        
        # Performance tracking
        self.processing_times = []
        self.error_count = 0
        self.success_count = 0
        
        # Continuous processing
        self.continuous_processing = False
        self.processing_thread = None
        self.processing_interval = 60.0  # Default 1 minute
        
        self.logger.info(f"Base agent initialized: {self.agent_type} (ID: {self.agent_id})")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup agent-specific logging"""
        logger = logging.getLogger(f"Agent.{self.agent_type}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def set_message_bus(self, message_bus):
        """Set message bus for inter-agent communication"""
        self.message_bus = message_bus
    
    def subscribe(self, topics: List[str]):
        """Subscribe to message bus topics"""
        if self.message_bus:
            self.subscriptions.extend(topics)
            self.message_bus.subscribe(self, topics)
    
    def publish(self, topic: str, data: Dict[str, Any]):
        """Publish message to message bus"""
        if self.message_bus:
            self.message_bus.publish(topic, data, sender_id=self.agent_id)
    
    def start(self):
        """Start the agent"""
        self.active = True
        self.logger.info(f"Agent {self.agent_type} started")
        
        # Start continuous processing if required
        if self.requires_continuous_processing():
            self.start_continuous_processing()
    
    def stop(self):
        """Stop the agent"""
        self.active = False
        
        # Stop continuous processing
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info(f"Agent {self.agent_type} stopped")
    
    def validate_data(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate input data has required fields"""
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Missing required field: {field}")
                return False
        return True
    
    # Abstract methods that subclasses must implement
    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data and return results"""
        pass
    
    @abstractmethod
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    def requires_continuous_processing(self) -> bool:
        """Whether this agent needs continuous processing"""
        pass


class ICTSMCAgent(BaseAgent):
    """
    Specialized base class for ICT/SMC agents
    """
    
    def __init__(self, agent_type: str, config: Dict[str, Any] = None):
        super().__init__(agent_type, config)
        
        # ICT/SMC specific configuration
        self.timeframe_sensitivity = config.get('timeframe_sensitivity', True)
        self.session_awareness = config.get('session_awareness', True)
        self.confluence_tracking = config.get('confluence_tracking', True)
        
        # Common ICT/SMC parameters
        self.atr_multiplier = config.get('atr_multiplier', 1.0)
        self.volume_weight = config.get('volume_weight', 0.5)