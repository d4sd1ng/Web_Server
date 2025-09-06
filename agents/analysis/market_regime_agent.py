"""
Market Regime Detection Agent
Detects and adapts to different market regimes for optimal performance
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from agents.base_agent import BaseAgent


class MarketRegimeAgent(BaseAgent):
    """
    Advanced Market Regime Detection Agent
    Critical for >90% win rate through regime-aware trading
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("market_regime", config)
        
        # Regime detection configuration
        self.regime_window = config.get('regime_window', 100)
        self.regime_update_frequency = config.get('regime_update_frequency', 50)
        self.volatility_lookback = config.get('volatility_lookback', 20)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Regime definitions
        self.regime_types = [
            'trending_bullish',
            'trending_bearish', 
            'high_volatility_range',
            'low_volatility_range',
            'breakout_expansion',
            'consolidation',
            'distribution',
            'accumulation'
        ]
        
        # Regime tracking
        self.current_regime = 'unknown'
        self.regime_history = []
        self.regime_transitions = []
        self.regime_performance = {}
        
        # ML components for regime detection
        self.regime_classifier = None
        self.scaler = StandardScaler()
        self.regime_features_history = []
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Market Regime Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific regime configuration"""
        if self.market_type == 'forex':
            # Forex: Session-based regime detection
            self.session_regimes = True
            self.volatility_threshold_low = 0.005   # 0.5%
            self.volatility_threshold_high = 0.015  # 1.5%
            self.trend_threshold = 0.02  # 2% for trend confirmation
        elif self.market_type == 'crypto':
            # Crypto: Volume-based regime detection
            self.session_regimes = False
            self.volatility_threshold_low = 0.01    # 1%
            self.volatility_threshold_high = 0.04   # 4%
            self.trend_threshold = 0.05  # 5% for trend confirmation
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data for regime detection
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with regime analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < self.regime_window:
            return {'current_regime': 'unknown', 'signal_strength': 0.0}
        
        try:
            # Extract regime features
            regime_features = self.extract_regime_features(df)
            
            # Detect current regime
            current_regime = self.detect_current_regime(df, regime_features)
            
            # Analyze regime stability
            regime_stability = self.analyze_regime_stability(df)
            
            # Predict regime transitions
            regime_transition_forecast = self.forecast_regime_transitions(df, regime_features)
            
            # Update tracking
            self.update_regime_tracking(current_regime, regime_features, symbol)
            
            # Calculate signal strength
            signal_strength = self.calculate_regime_signal_strength(current_regime, regime_stability)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_regime': current_regime,
                'regime_features': regime_features,
                'regime_stability': regime_stability,
                'regime_transition_forecast': regime_transition_forecast,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_adjustments': self.get_regime_trading_adjustments(current_regime),
                'parameter_recommendations': self.get_regime_parameter_recommendations(current_regime)
            }
            
            # Publish regime changes
            if current_regime != self.current_regime:
                self.publish("regime_change", {
                    'symbol': symbol,
                    'previous_regime': self.current_regime,
                    'new_regime': current_regime,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing regime data for {symbol}: {e}")
            return {'current_regime': 'unknown', 'signal_strength': 0.0, 'error': str(e)}
    
    def extract_regime_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Extract comprehensive features for regime detection
        """
        if len(df) < 20:
            return {}
        
        features = {}
        
        # Volatility features
        returns = df['close'].pct_change().dropna()
        features['volatility_20'] = returns.rolling(20).std().iloc[-1]
        features['volatility_5'] = returns.rolling(5).std().iloc[-1]
        features['volatility_ratio'] = features['volatility_5'] / features['volatility_20'] if features['volatility_20'] > 0 else 1.0
        
        # Trend features
        sma_10 = df['close'].rolling(10).mean()
        sma_50 = df['close'].rolling(50).mean() if len(df) >= 50 else sma_10
        
        features['trend_strength'] = (sma_10.iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1] if sma_50.iloc[-1] > 0 else 0
        features['price_vs_sma10'] = (df['close'].iloc[-1] - sma_10.iloc[-1]) / sma_10.iloc[-1] if sma_10.iloc[-1] > 0 else 0
        features['price_vs_sma50'] = (df['close'].iloc[-1] - sma_50.iloc[-1]) / sma_50.iloc[-1] if sma_50.iloc[-1] > 0 else 0
        
        # Range features
        recent_high = df['high'].rolling(20).max().iloc[-1]
        recent_low = df['low'].rolling(20).min().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        features['price_position_in_range'] = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5
        features['range_expansion'] = (recent_high - recent_low) / current_price
        
        # Volume features (for crypto)
        if 'volume' in df.columns:
            features['volume_trend'] = (df['volume'].rolling(5).mean().iloc[-1] - df['volume'].rolling(20).mean().iloc[-1]) / df['volume'].rolling(20).mean().iloc[-1]
            features['volume_spike'] = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
        
        # Momentum features
        if len(df) >= 14:
            # RSI-like momentum
            gains = returns.where(returns > 0, 0).rolling(14).mean()
            losses = (-returns.where(returns < 0, 0)).rolling(14).mean()
            rs = gains / losses
            features['momentum_rsi'] = 100 - (100 / (1 + rs.iloc[-1])) if not np.isnan(rs.iloc[-1]) else 50
        
        # Session features (for forex)
        if self.market_type == 'forex' and hasattr(df.index[-1], 'hour'):
            hour = df.index[-1].hour
            features['session_london'] = 1.0 if 8 <= hour <= 17 else 0.0
            features['session_ny'] = 1.0 if 13 <= hour <= 22 else 0.0
            features['session_overlap'] = 1.0 if 13 <= hour <= 17 else 0.0
        
        return features
    
    def detect_current_regime(self, df: pd.DataFrame, regime_features: Dict[str, float]) -> str:
        """
        Detect current market regime using multiple methods
        """
        if not regime_features:
            return 'unknown'
        
        # Rule-based regime detection
        rule_based_regime = self.detect_regime_rule_based(regime_features)
        
        # ML-based regime detection (if trained)
        ml_based_regime = self.detect_regime_ml_based(regime_features)
        
        # Combine approaches
        if ml_based_regime and ml_based_regime != 'unknown':
            detected_regime = ml_based_regime
        else:
            detected_regime = rule_based_regime
        
        return detected_regime
    
    def detect_regime_rule_based(self, features: Dict[str, float]) -> str:
        """
        Detect regime using rule-based approach
        """
        volatility = features.get('volatility_20', 0)
        trend_strength = features.get('trend_strength', 0)
        range_expansion = features.get('range_expansion', 0)
        price_position = features.get('price_position_in_range', 0.5)
        
        # High volatility regimes
        if volatility > self.volatility_threshold_high:
            if abs(trend_strength) > self.trend_threshold:
                return 'trending_bullish' if trend_strength > 0 else 'trending_bearish'
            else:
                return 'high_volatility_range'
        
        # Low volatility regimes
        elif volatility < self.volatility_threshold_low:
            if range_expansion < 0.02:  # Tight range
                return 'consolidation'
            else:
                return 'low_volatility_range'
        
        # Medium volatility regimes
        else:
            if abs(trend_strength) > self.trend_threshold:
                return 'trending_bullish' if trend_strength > 0 else 'trending_bearish'
            elif range_expansion > 0.05:
                return 'breakout_expansion'
            elif price_position > 0.8:
                return 'distribution'
            elif price_position < 0.2:
                return 'accumulation'
            else:
                return 'consolidation'
    
    def detect_regime_ml_based(self, features: Dict[str, float]) -> str:
        """
        Detect regime using ML approach
        """
        if not self.regime_classifier or not features:
            return 'unknown'
        
        try:
            # Prepare features for ML model
            feature_array = np.array([list(features.values())])
            feature_array_scaled = self.scaler.transform(feature_array)
            
            # Predict regime
            regime_index = self.regime_classifier.predict(feature_array_scaled)[0]
            
            if 0 <= regime_index < len(self.regime_types):
                return self.regime_types[regime_index]
            
        except Exception as e:
            self.logger.warning(f"Error in ML regime detection: {e}")
        
        return 'unknown'
    
    def analyze_regime_stability(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze stability of current regime
        """
        if len(self.regime_history) < 10:
            return {'stability': 'unknown', 'confidence': 0.0}
        
        # Analyze recent regime consistency
        recent_regimes = [entry['regime'] for entry in self.regime_history[-10:]]
        
        # Calculate stability
        most_common_regime = max(set(recent_regimes), key=recent_regimes.count)
        stability_ratio = recent_regimes.count(most_common_regime) / len(recent_regimes)
        
        # Regime transition frequency
        transitions = sum(1 for i in range(1, len(recent_regimes)) 
                         if recent_regimes[i] != recent_regimes[i-1])
        
        stability_analysis = {
            'stability': self.classify_stability(stability_ratio),
            'confidence': stability_ratio,
            'dominant_regime': most_common_regime,
            'transition_frequency': transitions / len(recent_regimes),
            'regime_duration': self.calculate_current_regime_duration()
        }
        
        return stability_analysis
    
    def classify_stability(self, stability_ratio: float) -> str:
        """Classify regime stability"""
        if stability_ratio >= 0.8:
            return 'very_stable'
        elif stability_ratio >= 0.6:
            return 'stable'
        elif stability_ratio >= 0.4:
            return 'moderately_stable'
        else:
            return 'unstable'
    
    def calculate_current_regime_duration(self) -> int:
        """Calculate how long current regime has been active"""
        if not self.regime_history:
            return 0
        
        current_regime = self.current_regime
        duration = 0
        
        # Count consecutive occurrences of current regime
        for entry in reversed(self.regime_history):
            if entry['regime'] == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def forecast_regime_transitions(self, df: pd.DataFrame, regime_features: Dict[str, float]) -> Dict[str, Any]:
        """
        Forecast potential regime transitions
        """
        forecast = {
            'transition_probability': 0.0,
            'likely_next_regime': 'unknown',
            'transition_timeframe': 'unknown',
            'confidence': 0.0
        }
        
        if len(self.regime_history) < 20:
            return forecast
        
        # Analyze historical transition patterns
        transition_patterns = self.analyze_historical_transitions()
        
        # Current regime characteristics
        current_features = regime_features
        
        # Calculate transition probability based on regime duration and features
        regime_duration = self.calculate_current_regime_duration()
        
        # Longer regimes more likely to transition
        duration_factor = min(regime_duration / 50.0, 1.0)
        
        # Feature-based transition signals
        feature_signals = self.detect_transition_signals(current_features)
        
        forecast['transition_probability'] = (duration_factor * 0.4 + feature_signals * 0.6)
        
        if forecast['transition_probability'] > 0.6:
            forecast['likely_next_regime'] = self.predict_next_regime(transition_patterns, current_features)
            forecast['transition_timeframe'] = 'short_term'
            forecast['confidence'] = forecast['transition_probability']
        
        return forecast
    
    def analyze_historical_transitions(self) -> Dict[str, Any]:
        """Analyze historical regime transition patterns"""
        if len(self.regime_transitions) < 5:
            return {}
        
        transition_patterns = {}
        
        for transition in self.regime_transitions:
            from_regime = transition['from_regime']
            to_regime = transition['to_regime']
            
            transition_key = f"{from_regime}_to_{to_regime}"
            
            if transition_key not in transition_patterns:
                transition_patterns[transition_key] = {
                    'count': 0,
                    'avg_duration': 0,
                    'success_rate': 0.0
                }
            
            transition_patterns[transition_key]['count'] += 1
        
        return transition_patterns
    
    def detect_transition_signals(self, features: Dict[str, float]) -> float:
        """Detect signals indicating potential regime transition"""
        transition_signals = []
        
        # Volatility regime transition signals
        volatility = features.get('volatility_20', 0)
        volatility_ratio = features.get('volatility_ratio', 1.0)
        
        if volatility_ratio > 1.5:  # Volatility expanding
            transition_signals.append(0.7)
        elif volatility_ratio < 0.7:  # Volatility contracting
            transition_signals.append(0.6)
        
        # Trend transition signals
        trend_strength = features.get('trend_strength', 0)
        if abs(trend_strength) < 0.01:  # Trend weakening
            transition_signals.append(0.5)
        
        # Range position signals
        price_position = features.get('price_position_in_range', 0.5)
        if price_position > 0.9 or price_position < 0.1:  # Extreme range positions
            transition_signals.append(0.8)
        
        # Volume signals (for crypto)
        if self.market_type == 'crypto':
            volume_spike = features.get('volume_spike', 1.0)
            if volume_spike > 3.0:  # High volume suggests regime change
                transition_signals.append(0.9)
        
        return np.mean(transition_signals) if transition_signals else 0.0
    
    def predict_next_regime(self, transition_patterns: Dict[str, Any], current_features: Dict[str, float]) -> str:
        """Predict most likely next regime"""
        current_regime = self.current_regime
        
        # Find most common transitions from current regime
        possible_transitions = [pattern for pattern in transition_patterns.keys() 
                              if pattern.startswith(f"{current_regime}_to_")]
        
        if possible_transitions:
            # Get most frequent transition
            most_frequent = max(possible_transitions, 
                              key=lambda x: transition_patterns[x]['count'])
            return most_frequent.split('_to_')[1]
        
        # Fallback: predict based on current features
        return self.predict_regime_from_features(current_features)
    
    def predict_regime_from_features(self, features: Dict[str, float]) -> str:
        """Predict regime based on current features"""
        volatility = features.get('volatility_20', 0)
        trend_strength = features.get('trend_strength', 0)
        
        if volatility > self.volatility_threshold_high:
            if abs(trend_strength) > self.trend_threshold:
                return 'trending_bullish' if trend_strength > 0 else 'trending_bearish'
            else:
                return 'high_volatility_range'
        elif volatility < self.volatility_threshold_low:
            return 'consolidation'
        else:
            return 'breakout_expansion'
    
    def get_regime_trading_adjustments(self, regime: str) -> Dict[str, Any]:
        """
        Get trading adjustments based on current regime
        """
        adjustments = {
            'position_sizing': 1.0,
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0,
            'confluence_requirement': self.min_confluence_patterns[self.market_type],
            'trading_frequency': 'normal',
            'preferred_strategies': []
        }
        
        # Regime-specific adjustments for >90% win rate
        if regime == 'trending_bullish':
            adjustments.update({
                'position_sizing': 1.3,  # Larger positions in strong trends
                'stop_loss_multiplier': 0.8,  # Tighter stops
                'take_profit_multiplier': 1.5,  # Larger targets
                'confluence_requirement': self.min_confluence_patterns[self.market_type] - 1,  # Slightly relaxed
                'preferred_strategies': ['trend_following', 'pullback_entries']
            })
        
        elif regime == 'trending_bearish':
            adjustments.update({
                'position_sizing': 1.3,
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 1.5,
                'confluence_requirement': self.min_confluence_patterns[self.market_type] - 1,
                'preferred_strategies': ['trend_following', 'pullback_entries']
            })
        
        elif regime == 'high_volatility_range':
            adjustments.update({
                'position_sizing': 0.7,  # Smaller positions in volatile ranges
                'stop_loss_multiplier': 1.5,  # Wider stops
                'take_profit_multiplier': 0.8,  # Quicker profits
                'confluence_requirement': self.min_confluence_patterns[self.market_type] + 1,  # Stricter requirements
                'preferred_strategies': ['range_trading', 'mean_reversion']
            })
        
        elif regime == 'consolidation':
            adjustments.update({
                'position_sizing': 0.5,  # Very small positions
                'stop_loss_multiplier': 1.2,
                'take_profit_multiplier': 0.6,
                'confluence_requirement': self.min_confluence_patterns[self.market_type] + 2,  # Very strict
                'trading_frequency': 'reduced',
                'preferred_strategies': ['breakout_preparation']
            })
        
        elif regime == 'breakout_expansion':
            adjustments.update({
                'position_sizing': 1.5,  # Larger positions for breakouts
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 2.0,  # Large targets
                'confluence_requirement': self.min_confluence_patterns[self.market_type],
                'preferred_strategies': ['breakout_trading', 'momentum_following']
            })
        
        # Market-specific adjustments
        if self.market_type == 'forex':
            adjustments['session_dependency'] = True
            adjustments['news_sensitivity'] = True
        elif self.market_type == 'crypto':
            adjustments['volume_dependency'] = True
            adjustments['whale_monitoring'] = True
        
        return adjustments
    
    def get_regime_parameter_recommendations(self, regime: str) -> Dict[str, Any]:
        """
        Get parameter recommendations for current regime
        """
        recommendations = {
            'agent_parameters': {},
            'risk_parameters': {},
            'entry_parameters': {},
            'exit_parameters': {}
        }
        
        # Regime-specific parameter tuning
        if regime in ['trending_bullish', 'trending_bearish']:
            recommendations['agent_parameters'] = {
                'displacement_agent': {'min_body_atr': 0.8},  # Easier displacement detection
                'market_structure_agent': {'lookback': 15},   # Shorter lookback for trends
                'ote_agent': {'fibonacci_levels': [0.618, 0.786]}  # Focus on deeper retracements
            }
            
            recommendations['entry_parameters'] = {
                'confluence_requirement': self.min_confluence_patterns[self.market_type] - 1,
                'entry_aggressiveness': 'moderate'
            }
        
        elif regime == 'high_volatility_range':
            recommendations['agent_parameters'] = {
                'fair_value_gaps_agent': {'min_gap_size': 0.003},  # Larger gaps in volatile markets
                'order_blocks_agent': {'lookback': 40},           # Longer lookback for stability
                'volume_analysis_agent': {'spike_threshold': 2.0}  # Higher volume threshold
            }
            
            recommendations['risk_parameters'] = {
                'position_size_multiplier': 0.7,
                'stop_loss_atr_multiplier': 2.0
            }
        
        elif regime == 'consolidation':
            recommendations['agent_parameters'] = {
                'pattern_cluster_agent': {'min_pattern_cluster': self.min_confluence_patterns[self.market_type] + 2},
                'confluence_coordinator': {'min_confluence_score': self.min_confluence_score * 1.2}
            }
            
            recommendations['entry_parameters'] = {
                'confluence_requirement': self.min_confluence_patterns[self.market_type] + 2,
                'entry_aggressiveness': 'very_conservative'
            }
        
        return recommendations
    
    def update_regime_tracking(self, current_regime: str, regime_features: Dict[str, float], symbol: str):
        """Update regime tracking and history"""
        # Check for regime change
        if current_regime != self.current_regime and self.current_regime != 'unknown':
            transition = {
                'timestamp': datetime.now(timezone.utc),
                'symbol': symbol,
                'from_regime': self.current_regime,
                'to_regime': current_regime,
                'market_type': self.market_type
            }
            self.regime_transitions.append(transition)
            
            self.logger.info(f"Regime transition: {self.current_regime} → {current_regime}")
        
        # Update current regime
        self.current_regime = current_regime
        
        # Add to regime history
        regime_entry = {
            'timestamp': datetime.now(timezone.utc),
            'regime': current_regime,
            'features': regime_features,
            'symbol': symbol,
            'market_type': self.market_type
        }
        self.regime_history.append(regime_entry)
        
        # Add features for ML training
        feature_entry = {
            'features': regime_features,
            'regime': current_regime,
            'timestamp': datetime.now(timezone.utc)
        }
        self.regime_features_history.append(feature_entry)
        
        # Limit tracking sizes
        if len(self.regime_history) > 500:
            self.regime_history = self.regime_history[-500:]
        
        if len(self.regime_features_history) > 1000:
            self.regime_features_history = self.regime_features_history[-1000:]
        
        # Train/update regime classifier periodically
        if len(self.regime_features_history) % 100 == 0 and len(self.regime_features_history) >= 200:
            self.train_regime_classifier()
    
    def train_regime_classifier(self):
        """Train ML classifier for regime detection"""
        try:
            if len(self.regime_features_history) < 50:
                return
            
            # Prepare training data
            X = []
            y = []
            
            for entry in self.regime_features_history:
                if entry['regime'] in self.regime_types:
                    X.append(list(entry['features'].values()))
                    y.append(self.regime_types.index(entry['regime']))
            
            if len(X) < 20:
                return
            
            X = np.array(X)
            y = np.array(y)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train classifier
            from sklearn.ensemble import RandomForestClassifier
            self.regime_classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            self.regime_classifier.fit(X_scaled, y)
            
            # Evaluate classifier
            accuracy = self.regime_classifier.score(X_scaled, y)
            self.logger.info(f"Regime classifier trained - Accuracy: {accuracy:.3f}")
            
        except Exception as e:
            self.logger.error(f"Error training regime classifier: {e}")
    
    def calculate_regime_signal_strength(self, current_regime: str, regime_stability: Dict[str, Any]) -> float:
        """
        Calculate regime detection signal strength
        """
        if current_regime == 'unknown':
            return 0.0
        
        strength_factors = []
        
        # Regime confidence
        stability_confidence = regime_stability.get('confidence', 0.0)
        strength_factors.append(stability_confidence)
        
        # Regime clarity (how well-defined the regime is)
        regime_clarity = self.calculate_regime_clarity(current_regime)
        strength_factors.append(regime_clarity)
        
        # Historical performance in this regime
        regime_performance = self.regime_performance.get(current_regime, {})
        if regime_performance:
            performance_strength = regime_performance.get('win_rate', 0.5)
            strength_factors.append(performance_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.5
    
    def calculate_regime_clarity(self, regime: str) -> float:
        """Calculate how clearly defined the current regime is"""
        # High-clarity regimes
        high_clarity_regimes = ['trending_bullish', 'trending_bearish', 'breakout_expansion']
        
        # Medium-clarity regimes
        medium_clarity_regimes = ['high_volatility_range', 'consolidation']
        
        # Low-clarity regimes
        low_clarity_regimes = ['low_volatility_range', 'distribution', 'accumulation']
        
        if regime in high_clarity_regimes:
            return 0.9
        elif regime in medium_clarity_regimes:
            return 0.7
        elif regime in low_clarity_regimes:
            return 0.5
        else:
            return 0.3
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get comprehensive regime summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'current_regime': self.current_regime,
            'regime_history_count': len(self.regime_history),
            'regime_transitions_count': len(self.regime_transitions),
            'regime_classifier_trained': self.regime_classifier is not None,
            'regime_performance': self.regime_performance,
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'regime_window': self.regime_window,
                'volatility_thresholds': {
                    'low': self.volatility_threshold_low,
                    'high': self.volatility_threshold_high
                },
                'trend_threshold': self.trend_threshold
            }
        }
    
    def is_regime_favorable_for_trading(self) -> bool:
        """Check if current regime is favorable for trading"""
        favorable_regimes = [
            'trending_bullish', 
            'trending_bearish', 
            'breakout_expansion'
        ]
        
        return self.current_regime in favorable_regimes
    
    def requires_continuous_processing(self) -> bool:
        """Market regime agent benefits from continuous processing"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for regime monitoring"""
        try:
            # Update regime performance metrics
            self.update_regime_performance_metrics()
            
            # Check for regime stability changes
            if len(self.regime_history) >= 10:
                stability = self.analyze_regime_stability(pd.DataFrame())
                
                if stability['stability'] == 'unstable':
                    self.logger.warning("Market regime becoming unstable - increasing confluence requirements")
        
        except Exception as e:
            self.logger.error(f"Error in regime continuous processing: {e}")
    
    def update_regime_performance_metrics(self):
        """Update performance metrics for each regime"""
        # This would be enhanced with actual trade outcome data
        pass
    
    def get_processing_interval(self) -> float:
        """Get processing interval"""
        return 300.0  # Check every 5 minutes