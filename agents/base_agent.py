"""
Base Agent Class for Trading System
Provides common functionality for all specialized trading agents
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
import pandas as pd
import numpy as np


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents
    Provides common functionality and enforces agent interface
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any] = None):
        """
        Initialize base agent
        
        Args:
            agent_id: Unique identifier for this agent
            config: Configuration dictionary for agent settings
        """
        self.agent_id = agent_id
        self.config = config or {}
        self.is_active = False
        self.last_update = None
        self.message_bus = None
        self.subscribers = []
        self.subscriptions = []
        
        # Setup logging
        self.logger = logging.getLogger(f"Agent.{agent_id}")
        self.logger.setLevel(logging.INFO)
        
        # Performance metrics
        self.metrics = {
            'signals_generated': 0,
            'processing_time_avg': 0.0,
            'last_signal_time': None,
            'error_count': 0,
            'uptime_start': datetime.now(timezone.utc)
        }
        
        # Thread management
        self._stop_event = threading.Event()
        self._worker_thread = None
        
        self.logger.info(f"Agent {agent_id} initialized")
    
    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming data and generate signals/analysis
        
        Args:
            data: Input data dictionary
            
        Returns:
            Dict containing analysis results and signals
        """
        pass
    
    @abstractmethod
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        
        Returns:
            Signal strength value
        """
        pass
    
    def start(self):
        """Start the agent"""
        if self.is_active:
            self.logger.warning(f"Agent {self.agent_id} is already active")
            return
            
        self.is_active = True
        self.metrics['uptime_start'] = datetime.now(timezone.utc)
        
        # Start worker thread if agent needs continuous processing
        if self.requires_continuous_processing():
            self._worker_thread = threading.Thread(target=self._worker_loop)
            self._worker_thread.daemon = True
            self._worker_thread.start()
            
        self.logger.info(f"Agent {self.agent_id} started")
    
    def stop(self):
        """Stop the agent"""
        if not self.is_active:
            return
            
        self.is_active = False
        self._stop_event.set()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            
        self.logger.info(f"Agent {self.agent_id} stopped")
    
    def requires_continuous_processing(self) -> bool:
        """
        Override this method if agent needs continuous background processing
        
        Returns:
            True if agent needs background thread
        """
        return False
    
    def _worker_loop(self):
        """Background worker loop for continuous processing"""
        while not self._stop_event.is_set():
            try:
                if self.is_active:
                    self._continuous_process()
                time.sleep(self.get_processing_interval())
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
                self.metrics['error_count'] += 1
    
    def _continuous_process(self):
        """Override this method for continuous background processing"""
        pass
    
    def get_processing_interval(self) -> float:
        """
        Get processing interval for continuous processing
        
        Returns:
            Interval in seconds
        """
        return self.config.get('processing_interval', 1.0)
    
    def set_message_bus(self, message_bus):
        """Set the message bus for inter-agent communication"""
        self.message_bus = message_bus
    
    def publish(self, topic: str, data: Dict[str, Any]):
        """
        Publish data to message bus
        
        Args:
            topic: Topic/channel to publish to
            data: Data to publish
        """
        if self.message_bus:
            # Add agent metadata
            message = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data': data
            }
            self.message_bus.publish(topic, message)
            self.metrics['signals_generated'] += 1
            self.metrics['last_signal_time'] = datetime.now(timezone.utc)
    
    def subscribe(self, topics: List[str], callback: Callable = None):
        """
        Subscribe to topics on message bus
        
        Args:
            topics: List of topics to subscribe to
            callback: Optional callback function, defaults to self.on_message
        """
        if self.message_bus:
            callback = callback or self.on_message
            for topic in topics:
                self.message_bus.subscribe(self.agent_id, topic, callback)
                self.subscriptions.append(topic)
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from message bus
        Override this method to handle specific messages
        
        Args:
            topic: Topic the message was published to
            message: Message data
        """
        self.logger.debug(f"Received message on topic {topic}: {message}")
    
    def update_metrics(self, processing_time: float):
        """
        Update performance metrics
        
        Args:
            processing_time: Time taken to process data
        """
        # Update average processing time
        current_avg = self.metrics['processing_time_avg']
        count = self.metrics['signals_generated']
        
        if count > 0:
            self.metrics['processing_time_avg'] = (
                (current_avg * (count - 1) + processing_time) / count
            )
        else:
            self.metrics['processing_time_avg'] = processing_time
        
        self.last_update = datetime.now(timezone.utc)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status and metrics
        
        Returns:
            Status dictionary
        """
        uptime = datetime.now(timezone.utc) - self.metrics['uptime_start']
        
        return {
            'agent_id': self.agent_id,
            'is_active': self.is_active,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'uptime_seconds': uptime.total_seconds(),
            'signals_generated': self.metrics['signals_generated'],
            'avg_processing_time': self.metrics['processing_time_avg'],
            'error_count': self.metrics['error_count'],
            'subscriptions': self.subscriptions,
            'signal_strength': self.get_signal_strength()
        }
    
    def validate_data(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate input data has required fields
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            
        Returns:
            True if data is valid
        """
        if not isinstance(data, dict):
            self.logger.error("Data must be a dictionary")
            return False
            
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            self.logger.error(f"Missing required fields: {missing_fields}")
            return False
            
        return True
    
    def safe_process(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Safely process data with error handling and metrics
        
        Args:
            data: Input data
            
        Returns:
            Processing results or None if error occurred
        """
        start_time = time.time()
        
        try:
            result = self.process_data(data)
            processing_time = time.time() - start_time
            self.update_metrics(processing_time)
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing data: {e}")
            self.metrics['error_count'] += 1
            return None
    
    def __str__(self):
        return f"Agent({self.agent_id})"
    
    def __repr__(self):
        return f"Agent(id={self.agent_id}, active={self.is_active})"


class ICTSMCAgent(BaseAgent):
    """
    Specialized base class for ICT/SMC agents
    Provides common ICT/SMC functionality
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any] = None):
        super().__init__(agent_id, config)
        
        # ICT/SMC specific configuration
        self.lookback_periods = config.get('lookback_periods', 20)
        self.min_signal_strength = config.get('min_signal_strength', 0.5)
        self.timeframes = config.get('timeframes', ['1h', '4h', '1d'])
        
        # Common ICT/SMC data structures
        self.current_market_structure = None
        self.active_zones = []
        self.signal_history = []
    
    def calculate_zone_strength(self, zone_data: Dict[str, Any]) -> float:
        """
        Calculate strength of an ICT/SMC zone
        
        Args:
            zone_data: Zone information
            
        Returns:
            Strength value (0.0 to 1.0)
        """
        # Base implementation - override in specific agents
        return 0.5
    
    def is_zone_valid(self, zone_data: Dict[str, Any]) -> bool:
        """
        Check if an ICT/SMC zone is still valid
        
        Args:
            zone_data: Zone information
            
        Returns:
            True if zone is valid
        """
        # Base implementation - override in specific agents
        return True
    
    def update_market_structure(self, data: Dict[str, Any]):
        """
        Update current market structure based on new data
        
        Args:
            data: Market data
        """
        # Base implementation - override in specific agents
        pass
    
    def get_confluence_score(self, signals: List[Dict[str, Any]]) -> float:
        """
        Calculate confluence score from multiple signals
        
        Args:
            signals: List of signal dictionaries
            
        Returns:
            Confluence score (0.0 to 1.0)
        """
        if not signals:
            return 0.0
            
        weights = [signal.get('strength', 0.5) for signal in signals]
        return np.mean(weights)