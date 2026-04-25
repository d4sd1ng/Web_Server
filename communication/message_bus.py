"""
Message Bus for Inter-Agent Communication
Handles all communication between the 43 agents
"""

import threading
import time
import logging
from typing import Dict, Any, List, Callable
from datetime import datetime, timezone
import queue


class MessageBus:
    """
    Advanced message bus for 43-agent coordination
    Handles high-volume message passing with efficiency
    """
    
    def __init__(self):
        self.subscribers = {}
        self.message_queue = queue.Queue(maxsize=10000)
        self.lock = threading.Lock()
        
        # Setup logging
        self.logger = logging.getLogger("MessageBus")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Message processing
        self.processing_active = False
        self.processing_thread = None
        
        # Statistics
        self.message_stats = {
            'total_messages': 0,
            'messages_per_second': 0.0,
            'active_subscribers': 0
        }
    
    def start(self):
        """Start message bus processing"""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._message_processor)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info("Message bus started")
    
    def stop(self):
        """Stop message bus processing"""
        self.processing_active = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info("Message bus stopped")
    
    def subscribe(self, agent, topics: List[str]):
        """Subscribe agent to topics"""
        with self.lock:
            for topic in topics:
                if topic not in self.subscribers:
                    self.subscribers[topic] = []
                if agent not in self.subscribers[topic]:
                    self.subscribers[topic].append(agent)
                    self.logger.debug(f"Agent {agent.agent_type} subscribed to topic '{topic}'")
    
    def publish(self, topic: str, data: Dict[str, Any], sender_id: str = "System"):
        """Publish message to topic"""
        try:
            message = {
                'topic': topic,
                'data': data,
                'sender_id': sender_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.message_queue.put_nowait(message)
            self.message_stats['total_messages'] += 1
            
        except queue.Full:
            self.logger.warning(f"Message queue full, dropping message for topic '{topic}'")
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
    
    def _message_processor(self):
        """Process messages from queue"""
        while self.processing_active:
            try:
                message = self.message_queue.get(timeout=1.0)
                self._deliver_message(message)
                self.message_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    def _deliver_message(self, message: Dict[str, Any]):
        """Deliver message to subscribers"""
        topic = message['topic']
        data = message['data']
        sender_id = message['sender_id']
        
        with self.lock:
            if topic in self.subscribers:
                for agent in self.subscribers[topic]:
                    if hasattr(agent, 'agent_id') and agent.agent_id != sender_id:
                        try:
                            # Deliver message in separate thread
                            threading.Thread(
                                target=agent.receive_message,
                                args=(topic, data, sender_id),
                                daemon=True
                            ).start()
                        except Exception as e:
                            self.logger.error(f"Error delivering message to {agent.agent_type}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics"""
        with self.lock:
            total_subscribers = sum(len(subs) for subs in self.subscribers.values())
            
        return {
            'total_messages': self.message_stats['total_messages'],
            'queue_size': self.message_queue.qsize(),
            'total_subscribers': total_subscribers,
            'active_topics': len(self.subscribers),
            'processing_active': self.processing_active
        }