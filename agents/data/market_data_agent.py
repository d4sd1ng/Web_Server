"""
Market Data Agent
Manages real-time market data feeds and processing
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import threading
import time
import queue

from agents.base_agent import BaseAgent


class MarketDataAgent(BaseAgent):
    """
    Specialized agent for Real-time Market Data management
    Handles live price feeds, tick data, and market updates
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("market_data", config)
        
        # Market data configuration
        self.update_frequency = config.get('update_frequency', 1.0)  # seconds
        self.max_tick_buffer = config.get('max_tick_buffer', 1000)
        self.price_precision = config.get('price_precision', 8)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Data streams and buffers
        self.price_streams = {}
        self.tick_buffer = queue.Queue(maxsize=self.max_tick_buffer)
        self.last_prices = {}
        self.price_changes = {}
        self.volume_data = {}
        
        # Threading for real-time data
        self.data_lock = threading.Lock()
        self.stream_active = False
        self.stream_thread = None
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Market Data Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific market data configuration"""
        if self.market_type == 'forex':
            # Forex: Lower update frequency during off-hours
            self.update_frequency = max(self.update_frequency, 1.0)
            self.spread_monitoring = True
            self.session_aware = True
            self.weekend_data = False
        elif self.market_type == 'crypto':
            # Crypto: Higher frequency for volatile markets
            self.update_frequency = min(self.update_frequency, 0.5)
            self.spread_monitoring = False
            self.session_aware = False
            self.weekend_data = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process real-time market data
        
        Args:
            data: Dictionary containing market data update
            
        Returns:
            Dictionary with processed market data
        """
        try:
            # Handle different types of market data
            if 'tick' in data:
                return self.process_tick_data(data['tick'])
            elif 'quote' in data:
                return self.process_quote_data(data['quote'])
            elif 'ohlcv' in data:
                return self.process_ohlcv_data(data['ohlcv'])
            else:
                return self.get_current_market_state()
                
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def process_tick_data(self, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process individual tick data
        """
        symbol = tick_data.get('symbol')
        price = tick_data.get('price')
        volume = tick_data.get('volume', 0)
        timestamp = tick_data.get('timestamp', datetime.now(timezone.utc))
        
        if not symbol or not price:
            return {'error': 'Invalid tick data'}
        
        with self.data_lock:
            # Update last prices
            prev_price = self.last_prices.get(symbol, price)
            self.last_prices[symbol] = price
            
            # Calculate price change
            price_change = price - prev_price if prev_price else 0
            price_change_pct = (price_change / prev_price * 100) if prev_price and prev_price != 0 else 0
            
            self.price_changes[symbol] = {
                'absolute': price_change,
                'percentage': price_change_pct,
                'direction': 'up' if price_change > 0 else 'down' if price_change < 0 else 'unchanged'
            }
            
            # Update volume data
            if symbol not in self.volume_data:
                self.volume_data[symbol] = {'total': 0, 'tick_count': 0}
            
            self.volume_data[symbol]['total'] += volume
            self.volume_data[symbol]['tick_count'] += 1
            
            # Add to tick buffer
            tick_entry = {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'timestamp': timestamp,
                'price_change': price_change,
                'price_change_pct': price_change_pct
            }
            
            try:
                self.tick_buffer.put_nowait(tick_entry)
            except queue.Full:
                # Remove oldest tick if buffer is full
                try:
                    self.tick_buffer.get_nowait()
                    self.tick_buffer.put_nowait(tick_entry)
                except queue.Empty:
                    pass
        
        # Publish tick update
        self.publish("tick_update", {
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'market_type': self.market_type
        })
        
        return {
            'agent_id': self.agent_id,
            'type': 'tick_processed',
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        }
    
    def process_quote_data(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process bid/ask quote data
        """
        symbol = quote_data.get('symbol')
        bid = quote_data.get('bid')
        ask = quote_data.get('ask')
        timestamp = quote_data.get('timestamp', datetime.now(timezone.utc))
        
        if not all([symbol, bid, ask]):
            return {'error': 'Invalid quote data'}
        
        # Calculate spread
        spread = ask - bid
        spread_pct = (spread / ((bid + ask) / 2) * 100) if bid > 0 and ask > 0 else 0
        
        with self.data_lock:
            # Update price streams
            if symbol not in self.price_streams:
                self.price_streams[symbol] = {'bids': [], 'asks': [], 'spreads': []}
            
            stream = self.price_streams[symbol]
            stream['bids'].append({'price': bid, 'timestamp': timestamp})
            stream['asks'].append({'price': ask, 'timestamp': timestamp})
            stream['spreads'].append({'spread': spread, 'spread_pct': spread_pct, 'timestamp': timestamp})
            
            # Limit stream size
            max_stream_size = 100
            for key in ['bids', 'asks', 'spreads']:
                if len(stream[key]) > max_stream_size:
                    stream[key] = stream[key][-max_stream_size:]
            
            # Update last price (use mid-price)
            mid_price = (bid + ask) / 2
            self.last_prices[symbol] = mid_price
        
        # Publish quote update
        if self.spread_monitoring:
            self.publish("quote_update", {
                'symbol': symbol,
                'bid': bid,
                'ask': ask,
                'spread': spread,
                'spread_pct': spread_pct,
                'market_type': self.market_type
            })
        
        return {
            'agent_id': self.agent_id,
            'type': 'quote_processed',
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'spread': spread,
            'spread_pct': spread_pct,
            'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
        }
    
    def process_ohlcv_data(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process OHLCV bar data
        """
        symbol = ohlcv_data.get('symbol')
        timeframe = ohlcv_data.get('timeframe')
        ohlcv = ohlcv_data.get('ohlcv')
        
        if not all([symbol, timeframe, ohlcv]):
            return {'error': 'Invalid OHLCV data'}
        
        # Extract OHLCV values
        open_price = ohlcv.get('open')
        high_price = ohlcv.get('high')
        low_price = ohlcv.get('low')
        close_price = ohlcv.get('close')
        volume = ohlcv.get('volume', 0)
        
        # Calculate bar statistics
        bar_range = high_price - low_price if high_price and low_price else 0
        body_size = abs(close_price - open_price) if close_price and open_price else 0
        bar_direction = 'bullish' if close_price > open_price else 'bearish' if close_price < open_price else 'doji'
        
        with self.data_lock:
            # Update last price
            if close_price:
                self.last_prices[symbol] = close_price
        
        # Publish OHLCV update
        self.publish("ohlcv_update", {
            'symbol': symbol,
            'timeframe': timeframe,
            'ohlcv': ohlcv,
            'bar_direction': bar_direction,
            'bar_range': bar_range,
            'body_size': body_size,
            'market_type': self.market_type
        })
        
        return {
            'agent_id': self.agent_id,
            'type': 'ohlcv_processed',
            'symbol': symbol,
            'timeframe': timeframe,
            'ohlcv': ohlcv,
            'bar_statistics': {
                'direction': bar_direction,
                'range': bar_range,
                'body_size': body_size
            }
        }
    
    def get_current_market_state(self) -> Dict[str, Any]:
        """
        Get current market state for all tracked symbols
        """
        with self.data_lock:
            market_state = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'market_type': self.market_type,
                'tracked_symbols': list(self.last_prices.keys()),
                'last_prices': self.last_prices.copy(),
                'price_changes': self.price_changes.copy(),
                'volume_data': self.volume_data.copy(),
                'tick_buffer_size': self.tick_buffer.qsize(),
                'stream_active': self.stream_active
            }
        
        return market_state
    
    def get_symbol_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed data for specific symbol
        """
        with self.data_lock:
            symbol_data = {
                'symbol': symbol,
                'last_price': self.last_prices.get(symbol),
                'price_change': self.price_changes.get(symbol),
                'volume_data': self.volume_data.get(symbol),
                'price_stream': self.price_streams.get(symbol, {}),
                'market_type': self.market_type
            }
        
        return symbol_data
    
    def start_data_stream(self, symbols: List[str] = None):
        """
        Start real-time data stream for specified symbols
        """
        if self.stream_active:
            self.logger.warning("Data stream already active")
            return
        
        self.stream_active = True
        
        if symbols:
            for symbol in symbols:
                if symbol not in self.last_prices:
                    self.last_prices[symbol] = 0.0
                    self.price_changes[symbol] = {'absolute': 0, 'percentage': 0, 'direction': 'unchanged'}
        
        # Start stream thread
        self.stream_thread = threading.Thread(target=self._stream_worker)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        
        self.logger.info(f"Started market data stream for {self.market_type}")
        
        self.publish("stream_started", {
            'symbols': symbols or [],
            'market_type': self.market_type
        })
    
    def stop_data_stream(self):
        """
        Stop real-time data stream
        """
        if not self.stream_active:
            return
        
        self.stream_active = False
        
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5.0)
        
        self.logger.info("Stopped market data stream")
        
        self.publish("stream_stopped", {
            'market_type': self.market_type
        })
    
    def _stream_worker(self):
        """
        Worker thread for data stream simulation
        """
        while self.stream_active:
            try:
                # Simulate market data updates
                self._simulate_market_data()
                time.sleep(self.update_frequency)
                
            except Exception as e:
                self.logger.error(f"Error in stream worker: {e}")
                time.sleep(1.0)
    
    def _simulate_market_data(self):
        """
        Simulate market data for testing (would be replaced with real feeds)
        """
        # This is a simulation for testing purposes
        # In production, this would connect to real market data feeds
        
        for symbol in self.last_prices.keys():
            current_price = self.last_prices[symbol]
            if current_price > 0:
                # Simulate price movement
                change_pct = np.random.normal(0, 0.001)  # 0.1% volatility
                new_price = current_price * (1 + change_pct)
                
                # Simulate volume
                volume = np.random.exponential(100)
                
                # Process simulated tick
                self.process_tick_data({
                    'symbol': symbol,
                    'price': round(new_price, self.price_precision),
                    'volume': round(volume, 2),
                    'timestamp': datetime.now(timezone.utc)
                })
    
    def calculate_market_statistics(self) -> Dict[str, Any]:
        """
        Calculate market-wide statistics
        """
        with self.data_lock:
            if not self.last_prices:
                return {'no_data': True}
            
            # Price change statistics
            price_changes = [change['percentage'] for change in self.price_changes.values() if 'percentage' in change]
            
            # Volume statistics
            volumes = [vol_data.get('total', 0) for vol_data in self.volume_data.values()]
            
            statistics = {
                'symbols_tracked': len(self.last_prices),
                'price_statistics': {
                    'avg_change_pct': np.mean(price_changes) if price_changes else 0,
                    'volatility': np.std(price_changes) if price_changes else 0,
                    'gainers': sum(1 for change in price_changes if change > 0),
                    'losers': sum(1 for change in price_changes if change < 0)
                },
                'volume_statistics': {
                    'total_volume': sum(volumes),
                    'avg_volume': np.mean(volumes) if volumes else 0,
                    'volume_std': np.std(volumes) if volumes else 0
                },
                'stream_statistics': {
                    'tick_buffer_utilization': self.tick_buffer.qsize() / self.max_tick_buffer,
                    'stream_active': self.stream_active,
                    'update_frequency': self.update_frequency
                }
            }
        
        return statistics
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on data quality and activity"""
        if not self.last_prices:
            return 0.0
        
        # Signal strength based on data activity and quality
        factors = []
        
        # Stream activity
        if self.stream_active:
            factors.append(0.8)
        else:
            factors.append(0.3)
        
        # Data coverage
        symbols_with_data = len(self.last_prices)
        if symbols_with_data > 0:
            factors.append(min(symbols_with_data / 10.0, 1.0))  # Up to 10 symbols
        
        # Tick buffer utilization (healthy level)
        buffer_utilization = self.tick_buffer.qsize() / self.max_tick_buffer
        if 0.1 <= buffer_utilization <= 0.8:  # Healthy range
            factors.append(0.9)
        else:
            factors.append(0.5)
        
        return np.mean(factors) if factors else 0.0
    
    def get_market_data_summary(self) -> Dict[str, Any]:
        """Get comprehensive market data summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'current_state': self.get_current_market_state(),
            'market_statistics': self.calculate_market_statistics(),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'update_frequency': self.update_frequency,
                'max_tick_buffer': self.max_tick_buffer,
                'price_precision': self.price_precision,
                'spread_monitoring': getattr(self, 'spread_monitoring', False),
                'session_aware': getattr(self, 'session_aware', False)
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Market data agent benefits from continuous processing"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for market data management"""
        try:
            # Clean old data from streams
            self._clean_old_stream_data()
            
            # Monitor data quality
            self._monitor_data_quality()
            
        except Exception as e:
            self.logger.error(f"Error in market data continuous processing: {e}")
    
    def _clean_old_stream_data(self):
        """Clean old data from price streams"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        with self.data_lock:
            for symbol, stream in self.price_streams.items():
                for data_type in ['bids', 'asks', 'spreads']:
                    if data_type in stream:
                        stream[data_type] = [
                            item for item in stream[data_type]
                            if item.get('timestamp', cutoff_time) > cutoff_time
                        ]
    
    def _monitor_data_quality(self):
        """Monitor data quality and alert on issues"""
        # Check for stale data
        current_time = datetime.now(timezone.utc)
        stale_symbols = []
        
        with self.data_lock:
            for symbol in self.last_prices.keys():
                # In a real implementation, you'd check timestamp of last update
                # For now, just log active symbols
                pass
        
        if stale_symbols:
            self.logger.warning(f"Stale data detected for symbols: {stale_symbols}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval for continuous updates"""
        return 30.0  # Check every 30 seconds