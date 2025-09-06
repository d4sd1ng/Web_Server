"""
Order Execution Agent
Handles order placement and execution using existing functions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import threading
import queue
from enum import Enum

from agents.base_agent import BaseAgent


class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderExecutionAgent(BaseAgent):
    """
    Specialized agent for Order Execution
    Handles order placement, monitoring, and execution logic
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("order_execution", config)
        
        # Execution configuration
        self.max_slippage = config.get('max_slippage', 0.001)  # 0.1%
        self.order_timeout = config.get('order_timeout', 300)  # 5 minutes
        self.retry_attempts = config.get('retry_attempts', 3)
        self.partial_fill_threshold = config.get('partial_fill_threshold', 0.1)  # 10%
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Order management
        self.active_orders = {}
        self.order_history = []
        self.execution_metrics = {}
        self.order_queue = queue.Queue()
        
        # Threading for order processing
        self.execution_lock = threading.Lock()
        self.processing_active = False
        self.processing_thread = None
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Order Execution Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific execution configuration"""
        if self.market_type == 'forex':
            # Forex: Lower slippage tolerance, faster execution
            self.max_slippage = min(self.max_slippage, 0.0005)  # 0.05%
            self.order_timeout = min(self.order_timeout, 180)   # 3 minutes
            self.spread_consideration = True
            self.session_aware_execution = True
        elif self.market_type == 'crypto':
            # Crypto: Higher slippage tolerance, longer timeout
            self.max_slippage = max(self.max_slippage, 0.002)   # 0.2%
            self.order_timeout = max(self.order_timeout, 300)   # 5 minutes
            self.spread_consideration = False
            self.session_aware_execution = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process order execution requests and management
        
        Args:
            data: Dictionary containing order information or execution request
            
        Returns:
            Dictionary with execution results
        """
        try:
            action = data.get('action', 'status')
            
            if action == 'place_order':
                return self.place_order(data)
            elif action == 'cancel_order':
                return self.cancel_order(data.get('order_id'))
            elif action == 'modify_order':
                return self.modify_order(data.get('order_id'), data.get('modifications', {}))
            elif action == 'status':
                return self.get_execution_status()
            else:
                return {'error': f'Unknown action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error processing execution request: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a new order
        """
        required_fields = ['symbol', 'side', 'quantity', 'order_type']
        
        for field in required_fields:
            if field not in order_data:
                return {'error': f'Missing required field: {field}'}
        
        # Create order object
        order = self.create_order(order_data)
        
        if 'error' in order:
            return order
        
        # Validate order
        validation_result = self.validate_order(order)
        if not validation_result['valid']:
            return {'error': f'Order validation failed: {validation_result["reason"]}'}
        
        # Add to order queue
        with self.execution_lock:
            self.active_orders[order['order_id']] = order
            
        try:
            self.order_queue.put(order, timeout=1.0)
        except queue.Full:
            return {'error': 'Order queue is full'}
        
        # Start processing if not active
        if not self.processing_active:
            self.start_order_processing()
        
        self.logger.info(f"Order placed: {order['order_id']} - {order['side']} {order['quantity']} {order['symbol']}")
        
        # Publish order placement
        self.publish("order_placed", {
            'order_id': order['order_id'],
            'symbol': order['symbol'],
            'side': order['side'],
            'quantity': order['quantity'],
            'order_type': order['order_type'],
            'market_type': self.market_type
        })
        
        return {
            'success': True,
            'order_id': order['order_id'],
            'status': order['status'],
            'message': 'Order placed successfully'
        }
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create order object from order data
        """
        try:
            order_id = f"{order_data['symbol']}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            
            order = {
                'order_id': order_id,
                'symbol': order_data['symbol'],
                'side': order_data['side'].lower(),
                'quantity': float(order_data['quantity']),
                'order_type': order_data['order_type'].lower(),
                'price': order_data.get('price'),
                'stop_price': order_data.get('stop_price'),
                'status': OrderStatus.PENDING.value,
                'created_at': datetime.now(timezone.utc),
                'filled_quantity': 0.0,
                'average_fill_price': 0.0,
                'fees': 0.0,
                'market_type': self.market_type,
                'retry_count': 0,
                'last_error': None
            }
            
            # Add market-specific fields
            if self.market_type == 'forex':
                order['spread_tolerance'] = order_data.get('spread_tolerance', 0.0001)
            elif self.market_type == 'crypto':
                order['slippage_tolerance'] = order_data.get('slippage_tolerance', self.max_slippage)
            
            return order
            
        except Exception as e:
            return {'error': f'Error creating order: {e}'}
    
    def validate_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate order before execution
        """
        validation = {'valid': True, 'reason': None}
        
        # Basic validation
        if order['quantity'] <= 0:
            validation = {'valid': False, 'reason': 'Quantity must be positive'}
        
        elif order['side'] not in ['buy', 'sell']:
            validation = {'valid': False, 'reason': 'Invalid order side'}
        
        elif order['order_type'] not in ['market', 'limit', 'stop', 'stop_limit']:
            validation = {'valid': False, 'reason': 'Invalid order type'}
        
        # Type-specific validation
        elif order['order_type'] in ['limit', 'stop_limit'] and not order.get('price'):
            validation = {'valid': False, 'reason': 'Limit orders require price'}
        
        elif order['order_type'] in ['stop', 'stop_limit'] and not order.get('stop_price'):
            validation = {'valid': False, 'reason': 'Stop orders require stop price'}
        
        # Market-specific validation
        elif self.market_type == 'forex':
            validation = self.validate_forex_order(order)
        
        elif self.market_type == 'crypto':
            validation = self.validate_crypto_order(order)
        
        return validation
    
    def validate_forex_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Validate forex-specific order requirements"""
        # Check session timing
        if self.session_aware_execution:
            current_hour = datetime.now(timezone.utc).hour
            if not (8 <= current_hour <= 22):  # Outside major sessions
                return {'valid': False, 'reason': 'Forex trading outside major sessions'}
        
        # Check minimum quantity (lot size)
        min_quantity = 0.01  # Micro lot
        if order['quantity'] < min_quantity:
            return {'valid': False, 'reason': f'Minimum quantity is {min_quantity}'}
        
        return {'valid': True, 'reason': None}
    
    def validate_crypto_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Validate crypto-specific order requirements"""
        # Check minimum notional value
        if order.get('price'):
            notional_value = order['quantity'] * order['price']
            min_notional = 10.0  # $10 minimum
            if notional_value < min_notional:
                return {'valid': False, 'reason': f'Minimum notional value is ${min_notional}'}
        
        return {'valid': True, 'reason': None}
    
    def start_order_processing(self):
        """Start order processing thread"""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._order_processor)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        self.logger.info("Order processing started")
    
    def stop_order_processing(self):
        """Stop order processing thread"""
        if not self.processing_active:
            return
        
        self.processing_active = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info("Order processing stopped")
    
    def _order_processor(self):
        """Order processing worker thread"""
        while self.processing_active:
            try:
                # Get order from queue
                order = self.order_queue.get(timeout=1.0)
                
                # Execute order
                execution_result = self.execute_order(order)
                
                # Update order status
                self.update_order_status(order['order_id'], execution_result)
                
                # Mark task as done
                self.order_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in order processor: {e}")
    
    def execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute individual order
        """
        order_id = order['order_id']
        
        try:
            # Update status to submitted
            with self.execution_lock:
                if order_id in self.active_orders:
                    self.active_orders[order_id]['status'] = OrderStatus.SUBMITTED.value
            
            # Simulate order execution (would integrate with real broker API)
            execution_result = self.simulate_order_execution(order)
            
            # Process execution result
            if execution_result['success']:
                with self.execution_lock:
                    if order_id in self.active_orders:
                        active_order = self.active_orders[order_id]
                        active_order['status'] = execution_result['status']
                        active_order['filled_quantity'] = execution_result['filled_quantity']
                        active_order['average_fill_price'] = execution_result['fill_price']
                        active_order['fees'] = execution_result.get('fees', 0.0)
                        active_order['executed_at'] = datetime.now(timezone.utc)
                
                # Publish execution
                self.publish("order_executed", {
                    'order_id': order_id,
                    'status': execution_result['status'],
                    'filled_quantity': execution_result['filled_quantity'],
                    'fill_price': execution_result['fill_price'],
                    'market_type': self.market_type
                })
                
                self.logger.info(f"Order executed: {order_id} - {execution_result['status']}")
            
            else:
                # Handle execution failure
                with self.execution_lock:
                    if order_id in self.active_orders:
                        self.active_orders[order_id]['last_error'] = execution_result['error']
                        self.active_orders[order_id]['retry_count'] += 1
                
                self.logger.warning(f"Order execution failed: {order_id} - {execution_result['error']}")
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Error executing order {order_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def simulate_order_execution(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate order execution (would be replaced with real broker integration)
        """
        # This is a simulation for testing purposes
        # In production, this would integrate with broker APIs
        
        import random
        
        # Simulate execution success/failure
        success_probability = 0.95 if order['order_type'] == 'market' else 0.85
        
        if random.random() < success_probability:
            # Successful execution
            fill_price = order.get('price', 100.0)  # Placeholder price
            
            # Add some slippage for market orders
            if order['order_type'] == 'market':
                slippage_factor = random.uniform(-self.max_slippage, self.max_slippage)
                fill_price *= (1 + slippage_factor)
            
            # Simulate partial fills occasionally
            fill_ratio = 1.0
            if random.random() < 0.1:  # 10% chance of partial fill
                fill_ratio = random.uniform(0.5, 0.9)
            
            filled_quantity = order['quantity'] * fill_ratio
            status = OrderStatus.FILLED.value if fill_ratio == 1.0 else OrderStatus.PARTIALLY_FILLED.value
            
            # Calculate fees
            fees = filled_quantity * fill_price * 0.001  # 0.1% fee
            
            return {
                'success': True,
                'status': status,
                'filled_quantity': filled_quantity,
                'fill_price': fill_price,
                'fees': fees
            }
        
        else:
            # Failed execution
            error_reasons = ['Insufficient liquidity', 'Price moved too far', 'System error']
            return {
                'success': False,
                'error': random.choice(error_reasons)
            }
    
    def update_order_status(self, order_id: str, execution_result: Dict[str, Any]):
        """Update order status based on execution result"""
        with self.execution_lock:
            if order_id in self.active_orders:
                order = self.active_orders[order_id]
                
                if execution_result['success']:
                    # Move completed orders to history
                    if execution_result['status'] == OrderStatus.FILLED.value:
                        order['completed_at'] = datetime.now(timezone.utc)
                        self.order_history.append(order.copy())
                        del self.active_orders[order_id]
                
                else:
                    # Handle failed orders
                    if order['retry_count'] >= self.retry_attempts:
                        order['status'] = OrderStatus.REJECTED.value
                        order['rejected_at'] = datetime.now(timezone.utc)
                        self.order_history.append(order.copy())
                        del self.active_orders[order_id]
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an active order"""
        with self.execution_lock:
            if order_id not in self.active_orders:
                return {'error': 'Order not found'}
            
            order = self.active_orders[order_id]
            
            # Check if order can be cancelled
            if order['status'] in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value]:
                return {'error': f'Cannot cancel order with status: {order["status"]}'}
            
            # Cancel order
            order['status'] = OrderStatus.CANCELLED.value
            order['cancelled_at'] = datetime.now(timezone.utc)
            
            # Move to history
            self.order_history.append(order.copy())
            del self.active_orders[order_id]
        
        self.logger.info(f"Order cancelled: {order_id}")
        
        # Publish cancellation
        self.publish("order_cancelled", {
            'order_id': order_id,
            'market_type': self.market_type
        })
        
        return {'success': True, 'message': 'Order cancelled successfully'}
    
    def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an active order"""
        with self.execution_lock:
            if order_id not in self.active_orders:
                return {'error': 'Order not found'}
            
            order = self.active_orders[order_id]
            
            # Check if order can be modified
            if order['status'] not in [OrderStatus.PENDING.value, OrderStatus.SUBMITTED.value]:
                return {'error': f'Cannot modify order with status: {order["status"]}'}
            
            # Apply modifications
            for key, value in modifications.items():
                if key in ['price', 'stop_price', 'quantity']:
                    order[key] = value
                    order['modified_at'] = datetime.now(timezone.utc)
        
        self.logger.info(f"Order modified: {order_id}")
        
        return {'success': True, 'message': 'Order modified successfully'}
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        with self.execution_lock:
            status = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'market_type': self.market_type,
                'active_orders_count': len(self.active_orders),
                'order_history_count': len(self.order_history),
                'processing_active': self.processing_active,
                'queue_size': self.order_queue.qsize(),
                'execution_metrics': self.calculate_execution_metrics()
            }
        
        return status
    
    def calculate_execution_metrics(self) -> Dict[str, Any]:
        """Calculate execution performance metrics"""
        if not self.order_history:
            return {'no_data': True}
        
        filled_orders = [order for order in self.order_history if order['status'] == OrderStatus.FILLED.value]
        
        if not filled_orders:
            return {'no_filled_orders': True}
        
        # Calculate metrics
        total_orders = len(self.order_history)
        fill_rate = len(filled_orders) / total_orders
        
        # Average execution time
        execution_times = []
        for order in filled_orders:
            if 'executed_at' in order and 'created_at' in order:
                exec_time = (order['executed_at'] - order['created_at']).total_seconds()
                execution_times.append(exec_time)
        
        avg_execution_time = np.mean(execution_times) if execution_times else 0
        
        # Fee analysis
        total_fees = sum(order.get('fees', 0) for order in filled_orders)
        avg_fees = total_fees / len(filled_orders) if filled_orders else 0
        
        return {
            'total_orders': total_orders,
            'filled_orders': len(filled_orders),
            'fill_rate': fill_rate,
            'avg_execution_time_seconds': avg_execution_time,
            'total_fees': total_fees,
            'avg_fees_per_order': avg_fees
        }
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on execution performance"""
        metrics = self.calculate_execution_metrics()
        
        if 'no_data' in metrics or 'no_filled_orders' in metrics:
            return 0.5  # Neutral when no data
        
        # Signal strength based on execution performance
        factors = []
        
        # Fill rate
        fill_rate = metrics.get('fill_rate', 0)
        factors.append(fill_rate)
        
        # Execution speed (faster = better)
        avg_exec_time = metrics.get('avg_execution_time_seconds', 300)
        speed_factor = max(0, 1.0 - (avg_exec_time / 300))  # 5 minutes max
        factors.append(speed_factor)
        
        # Processing status
        if self.processing_active:
            factors.append(0.8)
        else:
            factors.append(0.4)
        
        return np.mean(factors) if factors else 0.5
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'status': self.get_execution_status(),
            'execution_metrics': self.calculate_execution_metrics(),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'max_slippage': self.max_slippage,
                'order_timeout': self.order_timeout,
                'retry_attempts': self.retry_attempts,
                'partial_fill_threshold': self.partial_fill_threshold
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Order execution agent benefits from continuous processing"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for order management"""
        try:
            # Check for timed out orders
            self._check_order_timeouts()
            
            # Update execution metrics
            self._update_execution_metrics()
            
        except Exception as e:
            self.logger.error(f"Error in execution continuous processing: {e}")
    
    def _check_order_timeouts(self):
        """Check for and handle order timeouts"""
        current_time = datetime.now(timezone.utc)
        timeout_orders = []
        
        with self.execution_lock:
            for order_id, order in self.active_orders.items():
                age_seconds = (current_time - order['created_at']).total_seconds()
                if age_seconds > self.order_timeout:
                    timeout_orders.append(order_id)
        
        # Cancel timed out orders
        for order_id in timeout_orders:
            self.cancel_order(order_id)
            self.logger.warning(f"Order timed out and cancelled: {order_id}")
    
    def _update_execution_metrics(self):
        """Update execution metrics for monitoring"""
        # This could include additional metric calculations
        pass
    
    def get_processing_interval(self) -> float:
        """Get processing interval for continuous updates"""
        return 10.0  # Check every 10 seconds for timeouts