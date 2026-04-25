"""
Sentiment Analysis Agent
Analyzes news sentiment using existing implementation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import time

from agents.base_agent import BaseAgent


class SentimentAgent(BaseAgent):
    """
    Specialized agent for News Sentiment analysis
    Uses existing get_sentiment() function from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("sentiment", config)
        
        # Sentiment configuration
        self.fetch_interval_hours = config.get('fetch_interval_hours', 8)
        self.sentiment_cache_size = config.get('sentiment_cache_size', 100)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Sentiment tracking
        self.sentiment_cache = {}
        self.sentiment_history = []
        self.news_impact_events = []
        
        # Market-specific symbol mapping
        self.symbol_to_keyword = self.load_symbol_keywords()
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Sentiment Agent initialized for {self.market_type} market")
    
    def load_symbol_keywords(self) -> Dict[str, str]:
        """Load symbol to keyword mapping"""
        if self.market_type == 'crypto':
            return {
                # Crypto symbols
                'BTC/USDT': 'Bitcoin', 'ETH/USDT': 'Ethereum', 'BNB/USDT': 'Binance Coin', 
                'SOL/USDT': 'Solana', 'XRP/USDT': 'Ripple', 'ADA/USDT': 'Cardano',
                'AVAX/USDT': 'Avalanche', 'DOGE/USDT': 'Dogecoin', 'LINK/USDT': 'Chainlink',
                'DOT/USDT': 'Polkadot', 'MATIC/USDT': 'Polygon', 'UNI/USDT': 'Uniswap',
                'LTC/USDT': 'Litecoin', 'BCH/USDT': 'Bitcoin Cash', 'ATOM/USDT': 'Cosmos'
            }
        elif self.market_type == 'forex':
            return {
                # Forex symbols
                'EUR/USD': 'Euro Dollar', 'GBP/USD': 'Pound Dollar', 'USD/JPY': 'Dollar Yen',
                'AUD/USD': 'Australian Dollar', 'USD/CAD': 'Dollar Canadian', 'USD/CHF': 'Dollar Swiss',
                'NZD/USD': 'New Zealand Dollar', 'EUR/GBP': 'Euro Pound', 'EUR/JPY': 'Euro Yen',
                'GBP/JPY': 'Pound Yen', 'XAU/USD': 'Gold', 'XAG/USD': 'Silver'
            }
        
        return {}
    
    def apply_market_specific_config(self):
        """Apply market-specific sentiment configuration"""
        if self.market_type == 'forex':
            # Forex: News impact is very high
            self.news_impact_weight = 0.9
            self.central_bank_weight = 1.2  # Central bank news very important
            self.economic_data_weight = 1.0
        elif self.market_type == 'crypto':
            # Crypto: News impact is moderate to high
            self.news_impact_weight = 0.7
            self.regulatory_weight = 1.1  # Regulatory news important for crypto
            self.adoption_weight = 1.0
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data for sentiment analysis
        
        Args:
            data: Dictionary containing 'symbol' and optional 'force_update'
            
        Returns:
            Dictionary with sentiment analysis results
        """
        required_fields = ['symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        force_update = data.get('force_update', False)
        
        try:
            # Get sentiment using existing function
            sentiment = self.get_sentiment(symbol, force_update)
            
            # Analyze sentiment trends
            sentiment_trend = self.analyze_sentiment_trend(symbol)
            
            # Calculate sentiment strength
            sentiment_strength = self.calculate_sentiment_strength(sentiment, sentiment_trend)
            
            # Get market-specific sentiment interpretation
            market_interpretation = self.interpret_sentiment_for_market(sentiment, symbol)
            
            # Calculate signal strength
            signal_strength = self.calculate_sentiment_signal_strength(sentiment, sentiment_strength)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'sentiment': sentiment,
                'sentiment_trend': sentiment_trend,
                'sentiment_strength': sentiment_strength,
                'market_interpretation': market_interpretation,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'news_impact': self.assess_news_impact(sentiment, symbol)
            }
            
            # Publish sentiment signals
            if sentiment != 'neutral':
                self.publish("sentiment_update", {
                    'symbol': symbol,
                    'sentiment': sentiment,
                    'strength': sentiment_strength,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing sentiment data for {symbol}: {e}")
            return {'sentiment': 'neutral', 'signal_strength': 0.0, 'error': str(e)}
    
    def get_sentiment(self, symbol: str, force_update: bool = False) -> str:
        """
        Get sentiment using existing implementation
        """
        if symbol not in self.symbol_to_keyword:
            return 'neutral'
        
        keyword = self.symbol_to_keyword[symbol]
        current_time = time.time()
        
        # Check cache first (unless force update)
        if not force_update and symbol in self.sentiment_cache:
            last_fetch, cached_sentiment = self.sentiment_cache[symbol]
            if current_time - last_fetch < self.fetch_interval_hours * 3600:
                return cached_sentiment
        
        try:
            # This would use your existing news API implementation
            # For now, simplified implementation
            sentiment = self.fetch_news_sentiment(keyword, symbol)
            
            # Cache the result
            self.sentiment_cache[symbol] = (current_time, sentiment)
            
            # Add to history
            self.sentiment_history.append({
                'timestamp': datetime.now(timezone.utc),
                'symbol': symbol,
                'sentiment': sentiment,
                'keyword': keyword,
                'market_type': self.market_type
            })
            
            # Limit history size
            if len(self.sentiment_history) > self.sentiment_cache_size:
                self.sentiment_history = self.sentiment_history[-self.sentiment_cache_size:]
            
            return sentiment
            
        except Exception as e:
            self.logger.error(f"Error fetching sentiment for {symbol}: {e}")
            return 'neutral'
    
    def fetch_news_sentiment(self, keyword: str, symbol: str) -> str:
        """
        Fetch news sentiment (simplified implementation)
        """
        try:
            # This would integrate with your existing NewsData API implementation
            # For now, return neutral as placeholder
            
            # Your existing implementation would go here:
            # response = rate_limited_request(api.news_api, q=keyword, language='en', size=10)
            # ... sentiment analysis logic ...
            
            return 'neutral'  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Error fetching news for {keyword}: {e}")
            return 'neutral'
    
    def analyze_sentiment_trend(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze sentiment trend for symbol
        """
        symbol_history = [entry for entry in self.sentiment_history if entry['symbol'] == symbol]
        
        if len(symbol_history) < 3:
            return {'trend': 'insufficient_data', 'confidence': 0.0}
        
        # Analyze recent sentiment changes
        recent_sentiments = [entry['sentiment'] for entry in symbol_history[-5:]]
        
        # Convert to numeric for trend analysis
        sentiment_values = []
        for sentiment in recent_sentiments:
            if sentiment == 'bullish':
                sentiment_values.append(1)
            elif sentiment == 'bearish':
                sentiment_values.append(-1)
            else:
                sentiment_values.append(0)
        
        # Calculate trend
        if len(sentiment_values) >= 3:
            trend_slope = np.polyfit(range(len(sentiment_values)), sentiment_values, 1)[0]
            
            if trend_slope > 0.2:
                trend = 'improving'
            elif trend_slope < -0.2:
                trend = 'deteriorating'
            else:
                trend = 'stable'
            
            confidence = min(abs(trend_slope), 1.0)
        else:
            trend = 'stable'
            confidence = 0.5
        
        return {
            'trend': trend,
            'confidence': confidence,
            'recent_sentiments': recent_sentiments,
            'sentiment_values': sentiment_values
        }
    
    def calculate_sentiment_strength(self, sentiment: str, sentiment_trend: Dict[str, Any]) -> float:
        """
        Calculate sentiment strength
        """
        # Base sentiment strength
        base_strengths = {
            'bullish': 0.8,
            'bearish': 0.8,
            'neutral': 0.3
        }
        
        base_strength = base_strengths.get(sentiment, 0.3)
        
        # Trend adjustment
        trend = sentiment_trend.get('trend', 'stable')
        trend_confidence = sentiment_trend.get('confidence', 0.5)
        
        if trend == 'improving' and sentiment == 'bullish':
            base_strength += trend_confidence * 0.2
        elif trend == 'improving' and sentiment == 'bearish':
            base_strength -= trend_confidence * 0.2
        elif trend == 'deteriorating' and sentiment == 'bullish':
            base_strength -= trend_confidence * 0.2
        elif trend == 'deteriorating' and sentiment == 'bearish':
            base_strength += trend_confidence * 0.2
        
        return max(0.0, min(base_strength, 1.0))
    
    def interpret_sentiment_for_market(self, sentiment: str, symbol: str) -> List[str]:
        """Interpret sentiment for specific market type"""
        interpretations = []
        
        if self.market_type == 'forex':
            if sentiment == 'bullish':
                if 'USD' in symbol:
                    interpretations.append("Positive USD sentiment: Dollar strength expected")
                elif 'EUR' in symbol:
                    interpretations.append("Positive EUR sentiment: Euro strength expected")
                elif 'GBP' in symbol:
                    interpretations.append("Positive GBP sentiment: Pound strength expected")
                else:
                    interpretations.append(f"Positive sentiment for {symbol}")
            
            elif sentiment == 'bearish':
                interpretations.append(f"Negative sentiment for {symbol}: Risk-off flows possible")
        
        elif self.market_type == 'crypto':
            if sentiment == 'bullish':
                interpretations.append(f"Positive crypto sentiment for {symbol}: Adoption/institutional interest")
            elif sentiment == 'bearish':
                interpretations.append(f"Negative crypto sentiment for {symbol}: Regulatory concerns/selling pressure")
        
        return interpretations
    
    def assess_news_impact(self, sentiment: str, symbol: str) -> Dict[str, Any]:
        """Assess potential news impact on trading"""
        impact = {
            'impact_level': 'low',
            'time_sensitivity': 'normal',
            'trading_adjustment': 'none'
        }
        
        if sentiment != 'neutral':
            if self.market_type == 'forex':
                # Forex news can have immediate and strong impact
                impact['impact_level'] = 'high'
                impact['time_sensitivity'] = 'immediate'
                impact['trading_adjustment'] = 'increase_position_size' if sentiment == 'bullish' else 'reduce_exposure'
            
            elif self.market_type == 'crypto':
                # Crypto news impact varies
                impact['impact_level'] = 'medium'
                impact['time_sensitivity'] = 'hours_to_days'
                impact['trading_adjustment'] = 'monitor_closely'
        
        return impact
    
    def calculate_sentiment_signal_strength(self, sentiment: str, sentiment_strength: float) -> float:
        """
        Calculate sentiment signal strength
        """
        if sentiment == 'neutral':
            return 0.0
        
        strength_factors = []
        
        # Base sentiment strength
        strength_factors.append(sentiment_strength)
        
        # Market-specific weight
        if self.market_type == 'forex':
            strength_factors.append(self.news_impact_weight)
        elif self.market_type == 'crypto':
            strength_factors.append(self.news_impact_weight)
        
        # Recency bonus (more recent sentiment is stronger)
        recency_bonus = 0.2  # Fresh sentiment gets bonus
        strength_factors.append(recency_bonus)
        
        return np.mean(strength_factors)
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_sentiment_summary(self) -> Dict[str, Any]:
        """Get comprehensive sentiment summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'cached_symbols': len(self.sentiment_cache),
            'sentiment_history_count': len(self.sentiment_history),
            'news_impact_events': len(self.news_impact_events),
            'fetch_interval_hours': self.fetch_interval_hours,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'news_impact_weight': self.news_impact_weight,
                'symbol_keywords_count': len(self.symbol_to_keyword)
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Sentiment agent benefits from continuous processing for news updates"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for sentiment updates"""
        try:
            # Update sentiment for cached symbols periodically
            current_time = time.time()
            
            for symbol, (last_fetch, _) in list(self.sentiment_cache.items()):
                if current_time - last_fetch > self.fetch_interval_hours * 3600:
                    # Time to refresh sentiment
                    new_sentiment = self.get_sentiment(symbol, force_update=True)
                    
                    if new_sentiment != 'neutral':
                        self.publish("sentiment_update", {
                            'symbol': symbol,
                            'sentiment': new_sentiment,
                            'market_type': self.market_type
                        })
            
        except Exception as e:
            self.logger.error(f"Error in sentiment continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval"""
        return 3600.0  # Check every hour for sentiment updates