"""
Message Bus System for Inter-Agent Communication
Handles publish/subscribe messaging between trading agents
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Callable, Optional
import queue


class Message:
    """Represents a message in the system"""
    
    def __init__(self, topic: str, data: Dict[str, Any], sender_id: str = None):
        self.topic = topic
        self.data = data
        self.sender_id = sender_id
        self.timestamp = datetime.now(timezone.utc)
        self.message_id = f"{sender_id}_{int(self.timestamp.timestamp() * 1000000)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'message_id': self.message_id,
            'topic': self.topic,
            'data': self.data,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp.isoformat()
        }


class MessageBus:
    """
    Central message bus for agent communication
    Handles publish/subscribe pattern with topic-based routing
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize message bus
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.subscribers = defaultdict(list)  # topic -> list of (agent_id, callback)
        self.message_history = deque(maxlen=max_history)
        self.message_queue = queue.Queue()
        self.stats = {
            'messages_published': 0,
            'messages_delivered': 0,
            'failed_deliveries': 0,
            'active_subscribers': 0
        }
        
        # Threading
        self._running = False
        self._worker_thread = None
        self._lock = threading.RLock()
        
        # Logging
        self.logger = logging.getLogger("MessageBus")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("Message bus initialized")
    
    def start(self):
        """Start the message bus worker thread"""
        if self._running:
            return
            
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
        
        self.logger.info("Message bus started")
    
    def stop(self):
        """Stop the message bus"""
        if not self._running:
            return
            
        self._running = False
        
        # Add sentinel to wake up worker thread
        self.message_queue.put(None)
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            
        self.logger.info("Message bus stopped")
    
    def publish(self, topic: str, data: Dict[str, Any], sender_id: str = None):
        """
        Publish a message to a topic
        
        Args:
            topic: Topic to publish to
            data: Message data
            sender_id: ID of the sending agent
        """
        message = Message(topic, data, sender_id)
        
        with self._lock:
            self.message_queue.put(message)
            self.message_history.append(message)
            self.stats['messages_published'] += 1
        
        self.logger.debug(f"Message published to topic '{topic}' by {sender_id}")
    
    def subscribe(self, agent_id: str, topic: str, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Subscribe an agent to a topic
        
        Args:
            agent_id: ID of the subscribing agent
            topic: Topic to subscribe to
            callback: Callback function to handle messages
        """
        with self._lock:
            # Check if already subscribed
            for existing_agent_id, _ in self.subscribers[topic]:
                if existing_agent_id == agent_id:
                    self.logger.warning(f"Agent {agent_id} already subscribed to {topic}")
                    return
            
            self.subscribers[topic].append((agent_id, callback))
            self.stats['active_subscribers'] = sum(len(subs) for subs in self.subscribers.values())
        
        self.logger.info(f"Agent {agent_id} subscribed to topic '{topic}'")
    
    def unsubscribe(self, agent_id: str, topic: str = None):
        """
        Unsubscribe an agent from topics
        
        Args:
            agent_id: ID of the agent to unsubscribe
            topic: Specific topic to unsubscribe from, or None for all topics
        """
        with self._lock:
            if topic:
                # Unsubscribe from specific topic
                self.subscribers[topic] = [
                    (aid, callback) for aid, callback in self.subscribers[topic]
                    if aid != agent_id
                ]
                if not self.subscribers[topic]:
                    del self.subscribers[topic]
            else:
                # Unsubscribe from all topics
                for topic_name in list(self.subscribers.keys()):
                    self.subscribers[topic_name] = [
                        (aid, callback) for aid, callback in self.subscribers[topic_name]
                        if aid != agent_id
                    ]
                    if not self.subscribers[topic_name]:
                        del self.subscribers[topic_name]
            
            self.stats['active_subscribers'] = sum(len(subs) for subs in self.subscribers.values())
        
        topic_msg = f" from topic '{topic}'" if topic else " from all topics"
        self.logger.info(f"Agent {agent_id} unsubscribed{topic_msg}")
    
    def _worker_loop(self):
        """Worker thread loop for message delivery"""
        while self._running:
            try:
                # Get message from queue (blocking)
                message = self.message_queue.get(timeout=1.0)
                
                # Sentinel value to stop worker
                if message is None:
                    break
                
                self._deliver_message(message)
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in message bus worker: {e}")
    
    def _deliver_message(self, message: Message):
        """
        Deliver a message to all subscribers
        
        Args:
            message: Message to deliver
        """
        topic = message.topic
        
        with self._lock:
            subscribers = self.subscribers.get(topic, [])
        
        if not subscribers:
            self.logger.debug(f"No subscribers for topic '{topic}'")
            return
        
        # Deliver to all subscribers
        delivered = 0
        for agent_id, callback in subscribers:
            try:
                # Don't deliver to sender
                if agent_id == message.sender_id:
                    continue
                
                callback(topic, message.to_dict())
                delivered += 1
                
            except Exception as e:
                self.logger.error(f"Failed to deliver message to {agent_id}: {e}")
                self.stats['failed_deliveries'] += 1
        
        self.stats['messages_delivered'] += delivered
        self.logger.debug(f"Message delivered to {delivered} subscribers on topic '{topic}'")
    
    def get_subscribers(self, topic: str = None) -> Dict[str, List[str]]:
        """
        Get current subscribers
        
        Args:
            topic: Specific topic, or None for all topics
            
        Returns:
            Dictionary of topic -> list of agent IDs
        """
        with self._lock:
            if topic:
                return {topic: [agent_id for agent_id, _ in self.subscribers.get(topic, [])]}
            else:
                return {
                    topic_name: [agent_id for agent_id, _ in subs]
                    for topic_name, subs in self.subscribers.items()
                }
    
    def get_message_history(self, topic: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get message history
        
        Args:
            topic: Filter by topic, or None for all messages
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        with self._lock:
            messages = list(self.message_history)
        
        if topic:
            messages = [msg for msg in messages if msg.topic == topic]
        
        # Return most recent messages first
        messages = messages[-limit:] if len(messages) > limit else messages
        return [msg.to_dict() for msg in reversed(messages)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        with self._lock:
            return {
                'messages_published': self.stats['messages_published'],
                'messages_delivered': self.stats['messages_delivered'],
                'failed_deliveries': self.stats['failed_deliveries'],
                'active_subscribers': self.stats['active_subscribers'],
                'active_topics': len(self.subscribers),
                'message_history_size': len(self.message_history),
                'queue_size': self.message_queue.qsize()
            }
    
    def clear_history(self):
        """Clear message history"""
        with self._lock:
            self.message_history.clear()
        self.logger.info("Message history cleared")


class EventSystem:
    """
    Event-driven system for agent coordination
    Extends message bus with event-specific functionality
    """
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.event_handlers = defaultdict(list)
        self.logger = logging.getLogger("EventSystem")
    
    def emit_event(self, event_type: str, event_data: Dict[str, Any], sender_id: str = None):
        """
        Emit an event
        
        Args:
            event_type: Type of event
            event_data: Event data
            sender_id: ID of the sending agent
        """
        topic = f"event.{event_type}"
        self.message_bus.publish(topic, event_data, sender_id)
        self.logger.debug(f"Event '{event_type}' emitted by {sender_id}")
    
    def on_event(self, agent_id: str, event_type: str, handler: Callable):
        """
        Register event handler
        
        Args:
            agent_id: ID of the agent
            event_type: Type of event to handle
            handler: Handler function
        """
        topic = f"event.{event_type}"
        self.message_bus.subscribe(agent_id, topic, handler)
        self.logger.info(f"Agent {agent_id} registered for event '{event_type}'")
    
    # Common trading events
    def emit_price_update(self, symbol: str, price_data: Dict[str, Any], sender_id: str = None):
        """Emit price update event"""
        self.emit_event("price_update", {"symbol": symbol, **price_data}, sender_id)
    
    def emit_signal_generated(self, signal_data: Dict[str, Any], sender_id: str = None):
        """Emit signal generated event"""
        self.emit_event("signal_generated", signal_data, sender_id)
    
    def emit_trade_executed(self, trade_data: Dict[str, Any], sender_id: str = None):
        """Emit trade executed event"""
        self.emit_event("trade_executed", trade_data, sender_id)
    
    def emit_risk_alert(self, alert_data: Dict[str, Any], sender_id: str = None):
        """Emit risk alert event"""
        self.emit_event("risk_alert", alert_data, sender_id)