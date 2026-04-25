"""
Historical Data Agent
Manages historical data fetching and caching using existing functions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import threading
import time

from agents.base_agent import BaseAgent


class HistoricalDataAgent(BaseAgent):
    """
    Specialized agent for Historical Data management
    Uses existing fetch_ohlc() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("historical_data", config)
        
        # Data configuration
        self.cache_timeout = config.get('cache_timeout', 1800)  # 30 minutes
        self.max_cache_size = config.get('max_cache_size', 100)  # Max cached datasets
        self.default_limit = config.get('default_limit', 1000)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Data cache and tracking
        self.data_cache = {}
        self.fetch_history = []
        self.data_quality_metrics = {}
        
        # Threading for data operations
        self.data_lock = threading.Lock()
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Historical Data Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific data configuration"""
        if self.market_type == 'forex':
            # Forex: More stable data, longer cache timeout
            self.cache_timeout = max(self.cache_timeout, 3600)  # 1 hour
            self.data_reliability = 0.9
            self.weekend_data_available = False
        elif self.market_type == 'crypto':
            # Crypto: More volatile, shorter cache timeout
            self.cache_timeout = min(self.cache_timeout, 1800)  # 30 minutes
            self.data_reliability = 0.95
            self.weekend_data_available = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data request and return historical data
        
        Args:
            data: Dictionary containing 'symbol', 'timeframe', and optional 'limit'
            
        Returns:
            Dictionary with historical data and metadata
        """
        required_fields = ['symbol', 'timeframe']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        timeframe = data['timeframe']
        limit = data.get('limit', self.default_limit)
        force_refresh = data.get('force_refresh', False)
        
        try:
            # Check cache first
            cached_data = self.get_cached_data(symbol, timeframe, force_refresh)
            
            if cached_data is not None:
                self.logger.debug(f"Returning cached data for {symbol} {timeframe}")
                return self.format_data_response(cached_data, symbol, timeframe, 'cache')
            
            # Fetch new data
            fresh_data = self.fetch_historical_data(symbol, timeframe, limit)
            
            if fresh_data is not None and not fresh_data.empty:
                # Cache the data
                self.cache_data(symbol, timeframe, fresh_data)
                
                # Update fetch history
                self.update_fetch_history(symbol, timeframe, len(fresh_data), 'success')
                
                return self.format_data_response(fresh_data, symbol, timeframe, 'fresh')
            
            else:
                self.update_fetch_history(symbol, timeframe, 0, 'failed')
                return {'error': 'No data available', 'symbol': symbol, 'timeframe': timeframe}
            
        except Exception as e:
            self.logger.error(f"Error processing data request for {symbol} {timeframe}: {e}")
            self.update_fetch_history(symbol, timeframe, 0, 'error')
            return {'error': str(e), 'symbol': symbol, 'timeframe': timeframe}
    
    def fetch_historical_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Fetch historical data using existing function
        """
        try:
            # Import your existing fetch function
            from tradingbot_new import fetch_ohlc
            
            with self.data_lock:
                df = fetch_ohlc(symbol, timeframe, limit)
                
                if df is not None and not df.empty:
                    # Validate data quality
                    quality_score = self.assess_data_quality(df, symbol, timeframe)
                    
                    # Store quality metrics
                    cache_key = f"{symbol}_{timeframe}"
                    self.data_quality_metrics[cache_key] = {
                        'quality_score': quality_score,
                        'last_updated': datetime.now(timezone.utc),
                        'data_points': len(df),
                        'market_type': self.market_type
                    }
                    
                    self.logger.info(f"Fetched {len(df)} bars for {symbol} {timeframe} (quality: {quality_score:.2f})")
                    return df
                
                return None
                
        except ImportError:
            # Fallback if function not available
            return self.fetch_basic_data(symbol, timeframe, limit)
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
            return None
    
    def fetch_basic_data(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Basic data fetch fallback"""
        # This would implement a basic data fetch
        # For now, return None
        self.logger.warning(f"Basic data fetch not implemented for {symbol} {timeframe}")
        return None
    
    def assess_data_quality(self, df: pd.DataFrame, symbol: str, timeframe: str) -> float:
        """
        Assess quality of fetched data
        """
        if df.empty:
            return 0.0
        
        quality_factors = []
        
        # Completeness check
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        completeness = (len(required_columns) - len(missing_columns)) / len(required_columns)
        quality_factors.append(completeness)
        
        # Data consistency checks
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # OHLC consistency
            ohlc_valid = (
                (df['high'] >= df['low']).all() and
                (df['high'] >= df['open']).all() and
                (df['high'] >= df['close']).all() and
                (df['low'] <= df['open']).all() and
                (df['low'] <= df['close']).all()
            )
            quality_factors.append(1.0 if ohlc_valid else 0.5)
        
        # Null value check
        null_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        null_quality = 1.0 - null_ratio
        quality_factors.append(null_quality)
        
        # Volume data quality (for crypto)
        if self.market_type == 'crypto' and 'volume' in df.columns:
            non_zero_volume_ratio = (df['volume'] > 0).sum() / len(df)
            quality_factors.append(non_zero_volume_ratio)
        
        # Timestamp continuity
        if hasattr(df.index, 'to_series'):
            time_diffs = df.index.to_series().diff().dropna()
            if len(time_diffs) > 0:
                # Check for consistent time intervals
                mode_diff = time_diffs.mode().iloc[0] if len(time_diffs.mode()) > 0 else time_diffs.median()
                consistent_intervals = (time_diffs == mode_diff).sum() / len(time_diffs)
                quality_factors.append(consistent_intervals)
        
        return np.mean(quality_factors) if quality_factors else 0.5
    
    def get_cached_data(self, symbol: str, timeframe: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Get data from cache if available and not expired
        """
        if force_refresh:
            return None
        
        cache_key = f"{symbol}_{timeframe}"
        
        with self.data_lock:
            if cache_key in self.data_cache:
                cache_entry = self.data_cache[cache_key]
                cache_time = cache_entry['timestamp']
                
                # Check if cache is still valid
                if (datetime.now(timezone.utc) - cache_time).total_seconds() < self.cache_timeout:
                    return cache_entry['data']
                else:
                    # Remove expired cache
                    del self.data_cache[cache_key]
        
        return None
    
    def cache_data(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """
        Cache data for future use
        """
        cache_key = f"{symbol}_{timeframe}"
        
        with self.data_lock:
            self.data_cache[cache_key] = {
                'data': df.copy(),
                'timestamp': datetime.now(timezone.utc),
                'symbol': symbol,
                'timeframe': timeframe,
                'data_points': len(df)
            }
            
            # Limit cache size
            if len(self.data_cache) > self.max_cache_size:
                # Remove oldest entries
                oldest_key = min(self.data_cache.keys(), 
                               key=lambda k: self.data_cache[k]['timestamp'])
                del self.data_cache[oldest_key]
    
    def format_data_response(self, df: pd.DataFrame, symbol: str, timeframe: str, source: str) -> Dict[str, Any]:
        """
        Format data response with metadata
        """
        return {
            'agent_id': self.agent_id,
            'symbol': symbol,
            'timeframe': timeframe,
            'data': df,
            'data_points': len(df),
            'source': source,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'market_type': self.market_type,
            'data_quality': self.data_quality_metrics.get(f"{symbol}_{timeframe}", {}).get('quality_score', 0.0),
            'data_range': {
                'start': df.index[0].isoformat() if len(df) > 0 else None,
                'end': df.index[-1].isoformat() if len(df) > 0 else None
            }
        }
    
    def update_fetch_history(self, symbol: str, timeframe: str, data_points: int, status: str):
        """Update fetch history for monitoring"""
        fetch_entry = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'timeframe': timeframe,
            'data_points': data_points,
            'status': status,
            'market_type': self.market_type
        }
        
        self.fetch_history.append(fetch_entry)
        
        # Limit history size
        if len(self.fetch_history) > 200:
            self.fetch_history = self.fetch_history[-200:]
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """Get data fetching and caching statistics"""
        if not self.fetch_history:
            return {'no_data': True}
        
        recent_fetches = self.fetch_history[-50:] if len(self.fetch_history) >= 50 else self.fetch_history
        
        success_count = sum(1 for fetch in recent_fetches if fetch['status'] == 'success')
        error_count = sum(1 for fetch in recent_fetches if fetch['status'] == 'error')
        
        return {
            'total_fetches': len(self.fetch_history),
            'recent_fetches': len(recent_fetches),
            'success_rate': success_count / len(recent_fetches) if recent_fetches else 0,
            'error_rate': error_count / len(recent_fetches) if recent_fetches else 0,
            'cached_datasets': len(self.data_cache),
            'cache_hit_ratio': self.calculate_cache_hit_ratio(),
            'average_data_quality': self.calculate_average_data_quality()
        }
    
    def calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        if not self.fetch_history:
            return 0.0
        
        cache_hits = sum(1 for fetch in self.fetch_history if fetch['status'] == 'cache')
        total_requests = len(self.fetch_history)
        
        return cache_hits / total_requests if total_requests > 0 else 0.0
    
    def calculate_average_data_quality(self) -> float:
        """Calculate average data quality across all cached datasets"""
        if not self.data_quality_metrics:
            return 0.0
        
        quality_scores = [metrics['quality_score'] for metrics in self.data_quality_metrics.values()]
        return np.mean(quality_scores) if quality_scores else 0.0
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on data availability and quality"""
        stats = self.get_data_statistics()
        
        if 'no_data' in stats:
            return 0.0
        
        # Signal strength based on success rate and data quality
        success_rate = stats.get('success_rate', 0.0)
        avg_quality = stats.get('average_data_quality', 0.0)
        
        return (success_rate * 0.7 + avg_quality * 0.3)
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get comprehensive data summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'data_statistics': self.get_data_statistics(),
            'cache_status': {
                'cached_datasets': len(self.data_cache),
                'cache_timeout': self.cache_timeout,
                'max_cache_size': self.max_cache_size
            },
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'default_limit': self.default_limit,
                'data_reliability': self.data_reliability,
                'weekend_data_available': self.weekend_data_available
            }
        }
    
    def clear_cache(self, symbol: str = None, timeframe: str = None):
        """Clear cache (optionally filtered by symbol/timeframe)"""
        with self.data_lock:
            if symbol and timeframe:
                cache_key = f"{symbol}_{timeframe}"
                if cache_key in self.data_cache:
                    del self.data_cache[cache_key]
                    self.logger.info(f"Cleared cache for {symbol} {timeframe}")
            elif symbol:
                # Clear all timeframes for symbol
                keys_to_remove = [key for key in self.data_cache.keys() if key.startswith(f"{symbol}_")]
                for key in keys_to_remove:
                    del self.data_cache[key]
                self.logger.info(f"Cleared cache for all {symbol} timeframes")
            else:
                # Clear all cache
                self.data_cache.clear()
                self.logger.info("Cleared all cached data")
    
    def preload_data(self, symbols: List[str], timeframes: List[str], limit: int = None):
        """
        Preload data for multiple symbols and timeframes
        """
        if limit is None:
            limit = self.default_limit
        
        self.logger.info(f"Preloading data for {len(symbols)} symbols, {len(timeframes)} timeframes")
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    self.process_data({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'limit': limit
                    })
                    time.sleep(0.1)  # Small delay to avoid rate limits
                except Exception as e:
                    self.logger.warning(f"Error preloading {symbol} {timeframe}: {e}")
        
        self.logger.info("Data preloading completed")
    
    def get_available_data(self) -> List[Dict[str, Any]]:
        """Get list of available cached data"""
        available_data = []
        
        with self.data_lock:
            for cache_key, cache_entry in self.data_cache.items():
                symbol, timeframe = cache_key.split('_', 1)
                available_data.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'data_points': cache_entry['data_points'],
                    'cached_at': cache_entry['timestamp'].isoformat(),
                    'age_minutes': (datetime.now(timezone.utc) - cache_entry['timestamp']).total_seconds() / 60
                })
        
        return available_data
    
    def requires_continuous_processing(self) -> bool:
        """Historical data agent benefits from continuous processing for cache management"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for cache management"""
        try:
            # Clean expired cache entries
            self.clean_expired_cache()
            
            # Update data quality metrics
            self.update_data_quality_metrics()
            
        except Exception as e:
            self.logger.error(f"Error in data continuous processing: {e}")
    
    def clean_expired_cache(self):
        """Clean expired cache entries"""
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        with self.data_lock:
            for cache_key, cache_entry in self.data_cache.items():
                age_seconds = (current_time - cache_entry['timestamp']).total_seconds()
                if age_seconds > self.cache_timeout:
                    expired_keys.append(cache_key)
            
            for key in expired_keys:
                del self.data_cache[key]
        
        if expired_keys:
            self.logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def update_data_quality_metrics(self):
        """Update data quality metrics for monitoring"""
        # This could include additional quality checks
        # For now, just log current cache status
        if len(self.data_cache) > 0:
            self.logger.debug(f"Cache status: {len(self.data_cache)} datasets cached")
    
    def get_processing_interval(self) -> float:
        """Get processing interval for cache management"""
        return 300.0  # Check every 5 minutes