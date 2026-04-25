"""
ML Prediction Agent
Handles machine learning predictions using existing MLModel class
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import threading
import logging

from agents.base_agent import BaseAgent


class MLPredictionAgent(BaseAgent):
    """
    Specialized agent for ML predictions
    Uses existing MLModel class from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ml_prediction", config)
        
        # ML configuration
        self.model_type = config.get('model_type', 'RandomForest')
        self.threshold = config.get('threshold', 0.5)
        self.model_path = config.get('model_path', 'ml_model.pkl')
        self.scaler_path = config.get('scaler_path', 'scaler.pkl')
        self.retrain_interval_hours = config.get('retrain_interval_hours', 24)
        
        # ML model instance
        self.ml_model = None
        self.feature_names = []
        self.last_retrain_time = None
        self.prediction_history = []
        
        # Threading for model operations
        self.ml_lock = threading.Lock()
        
        # Initialize ML model
        self.initialize_ml_model()
        
        self.logger.info(f"ML Prediction Agent initialized with {self.model_type}")
    
    def initialize_ml_model(self):
        """Initialize ML model using existing MLModel class"""
        try:
            # Import MLModel from your existing code
            from tradingbot_new import MLModel
            
            self.ml_model = MLModel(
                model_type=self.model_type,
                model_path=self.model_path,
                scaler_path=self.scaler_path,
                threshold=self.threshold
            )
            
            # Try to load existing model
            if self.ml_model.load():
                self.logger.info("Loaded existing ML model")
            else:
                self.logger.info("No existing model found - will train when data is available")
            
        except Exception as e:
            self.logger.error(f"Error initializing ML model: {e}")
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to generate ML predictions
        
        Args:
            data: Dictionary containing 'features' (feature array) and 'symbol'
            
        Returns:
            Dictionary with ML prediction results
        """
        required_fields = ['features', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        features = data['features']
        symbol = data['symbol']
        
        if not self.ml_model or not hasattr(self.ml_model, 'model') or self.ml_model.model is None:
            return {'should_trade': False, 'probability': 0.0, 'error': 'Model not trained'}
        
        try:
            with self.ml_lock:
                # Get prediction using existing MLModel
                should_trade, trade_prob = self.ml_model.should_trade(features)
                
                # Get additional prediction details
                prediction_details = self.get_prediction_details(features)
                
                # Store prediction in history
                self.store_prediction(symbol, features, should_trade, trade_prob)
                
                results = {
                    'agent_id': self.agent_id,
                    'symbol': symbol,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'should_trade': should_trade,
                    'probability': trade_prob,
                    'threshold': self.threshold,
                    'model_type': self.model_type,
                    'prediction_details': prediction_details,
                    'feature_count': len(features),
                    'model_confidence': self.calculate_model_confidence(trade_prob)
                }
                
                # Publish ML signals
                if should_trade:
                    self.publish("ml_trade_signal", {
                        'symbol': symbol,
                        'probability': trade_prob,
                        'should_trade': should_trade,
                        'model_type': self.model_type
                    })
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error processing ML prediction for {symbol}: {e}")
            return {'should_trade': False, 'probability': 0.0, 'error': str(e)}
    
    def get_prediction_details(self, features: List[float]) -> Dict[str, Any]:
        """
        Get detailed prediction information
        """
        details = {}
        
        try:
            if self.ml_model and hasattr(self.ml_model, 'model'):
                # Get probability for both classes if available
                if hasattr(self.ml_model.model, 'predict_proba'):
                    probabilities = self.ml_model.model.predict_proba([features])[0]
                    details['class_probabilities'] = {
                        'no_trade': float(probabilities[0]),
                        'trade': float(probabilities[1])
                    }
                
                # Get feature importance if available
                if hasattr(self.ml_model.model, 'feature_importances_'):
                    importances = self.ml_model.model.feature_importances_
                    if len(importances) == len(features):
                        # Calculate feature contributions
                        feature_contributions = []
                        for i, (feature_val, importance) in enumerate(zip(features, importances)):
                            contribution = feature_val * importance
                            feature_contributions.append({
                                'feature_index': i,
                                'value': float(feature_val),
                                'importance': float(importance),
                                'contribution': float(contribution)
                            })
                        
                        # Sort by contribution magnitude
                        feature_contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
                        details['top_features'] = feature_contributions[:10]  # Top 10 contributing features
                
        except Exception as e:
            self.logger.warning(f"Error getting prediction details: {e}")
        
        return details
    
    def calculate_model_confidence(self, probability: float) -> str:
        """
        Calculate model confidence level
        """
        if probability >= 0.8:
            return 'very_high'
        elif probability >= 0.7:
            return 'high'
        elif probability >= 0.6:
            return 'medium'
        elif probability >= 0.5:
            return 'low'
        else:
            return 'very_low'
    
    def store_prediction(self, symbol: str, features: List[float], should_trade: bool, probability: float):
        """
        Store prediction in history for analysis
        """
        prediction_entry = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'features': features.copy(),
            'should_trade': should_trade,
            'probability': probability,
            'model_type': self.model_type
        }
        
        self.prediction_history.append(prediction_entry)
        
        # Limit history size
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-1000:]
    
    def train_model(self, training_data: Dict[str, Any]) -> bool:
        """
        Train or retrain the ML model
        
        Args:
            training_data: Dictionary containing 'X' (features) and 'y' (labels)
            
        Returns:
            True if training successful, False otherwise
        """
        if not self.validate_data(training_data, ['X', 'y']):
            return False
        
        X = training_data['X']
        y = training_data['y']
        
        try:
            with self.ml_lock:
                self.logger.info(f"Training {self.model_type} model with {len(X)} samples")
                
                # Train model using existing implementation
                self.ml_model.train(X, y, verbose=True)
                
                # Update last retrain time
                self.last_retrain_time = datetime.now(timezone.utc)
                
                self.logger.info("ML model training completed successfully")
                
                # Publish training completion
                self.publish("ml_model_trained", {
                    'model_type': self.model_type,
                    'training_samples': len(X),
                    'features': len(X[0]) if len(X) > 0 else 0,
                    'timestamp': self.last_retrain_time.isoformat()
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error training ML model: {e}")
            return False
    
    def get_feature_importance(self) -> List[Dict[str, Any]]:
        """
        Get feature importance from the trained model
        """
        if not self.ml_model or not hasattr(self.ml_model.model, 'feature_importances_'):
            return []
        
        try:
            importances = self.ml_model.model.feature_importances_
            feature_importance = []
            
            for i, importance in enumerate(importances):
                feature_name = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"
                feature_importance.append({
                    'feature_name': feature_name,
                    'feature_index': i,
                    'importance': float(importance)
                })
            
            # Sort by importance
            feature_importance.sort(key=lambda x: x['importance'], reverse=True)
            return feature_importance
            
        except Exception as e:
            self.logger.error(f"Error getting feature importance: {e}")
            return []
    
    def get_model_performance_metrics(self) -> Dict[str, Any]:
        """
        Get model performance metrics
        """
        if not self.prediction_history:
            return {}
        
        try:
            recent_predictions = self.prediction_history[-100:]  # Last 100 predictions
            
            total_predictions = len(recent_predictions)
            positive_predictions = sum(1 for p in recent_predictions if p['should_trade'])
            avg_probability = np.mean([p['probability'] for p in recent_predictions])
            
            # Calculate prediction distribution
            prob_distribution = {
                'very_high': sum(1 for p in recent_predictions if p['probability'] >= 0.8),
                'high': sum(1 for p in recent_predictions if 0.7 <= p['probability'] < 0.8),
                'medium': sum(1 for p in recent_predictions if 0.6 <= p['probability'] < 0.7),
                'low': sum(1 for p in recent_predictions if 0.5 <= p['probability'] < 0.6),
                'very_low': sum(1 for p in recent_predictions if p['probability'] < 0.5)
            }
            
            return {
                'total_predictions': total_predictions,
                'positive_predictions': positive_predictions,
                'positive_rate': positive_predictions / total_predictions,
                'average_probability': avg_probability,
                'probability_distribution': prob_distribution,
                'last_retrain_time': self.last_retrain_time.isoformat() if self.last_retrain_time else None
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength based on recent predictions
        """
        if not self.prediction_history:
            return 0.0
        
        # Use average probability of recent predictions as signal strength
        recent_predictions = self.prediction_history[-10:]  # Last 10 predictions
        avg_probability = np.mean([p['probability'] for p in recent_predictions])
        
        return avg_probability
    
    def should_retrain(self) -> bool:
        """
        Check if model should be retrained
        """
        if not self.last_retrain_time:
            return True
        
        hours_since_retrain = (datetime.now(timezone.utc) - self.last_retrain_time).total_seconds() / 3600
        return hours_since_retrain >= self.retrain_interval_hours
    
    def get_ml_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive ML summary
        """
        return {
            'agent_id': self.agent_id,
            'model_type': self.model_type,
            'threshold': self.threshold,
            'model_loaded': self.ml_model is not None and hasattr(self.ml_model, 'model'),
            'prediction_history_count': len(self.prediction_history),
            'last_retrain_time': self.last_retrain_time.isoformat() if self.last_retrain_time else None,
            'should_retrain': self.should_retrain(),
            'performance_metrics': self.get_model_performance_metrics(),
            'feature_importance_available': (self.ml_model and 
                                           hasattr(self.ml_model, 'model') and 
                                           hasattr(self.ml_model.model, 'feature_importances_')),
            'last_signal_strength': self.get_signal_strength()
        }
    
    def prepare_features_from_agents(self, agent_data: Dict[str, Any]) -> List[float]:
        """
        Prepare ML features from other agent outputs
        
        Args:
            agent_data: Dictionary containing data from various agents
            
        Returns:
            Feature array ready for ML prediction
        """
        features = []
        
        try:
            # Technical indicators
            if 'technical_indicators' in agent_data:
                tech_data = agent_data['technical_indicators']
                features.extend([
                    tech_data.get('rsi', 50),
                    tech_data.get('adx', 25),
                    tech_data.get('macd', 0),
                    tech_data.get('macd_signal', 0),
                    tech_data.get('atr', 0.01),
                    tech_data.get('volume', 1000000)
                ])
            
            # ICT/SMC features
            if 'order_blocks' in agent_data:
                ob_data = agent_data['order_blocks']
                features.extend([
                    1 if ob_data.get('valid_bull_ob', False) else 0,
                    1 if ob_data.get('valid_bear_ob', False) else 0
                ])
            
            if 'fair_value_gaps' in agent_data:
                fvg_data = agent_data['fair_value_gaps']
                features.extend([
                    1 if fvg_data.get('near_fvg_bull', False) else 0,
                    1 if fvg_data.get('near_fvg_bear', False) else 0
                ])
            
            if 'market_structure' in agent_data:
                ms_data = agent_data['market_structure']
                features.extend([
                    1 if ms_data.get('bullish_mss', False) else 0,
                    1 if ms_data.get('bearish_mss', False) else 0,
                    1 if ms_data.get('bos_bull', False) else 0,
                    1 if ms_data.get('bos_bear', False) else 0
                ])
            
            if 'liquidity_sweeps' in agent_data:
                liq_data = agent_data['liquidity_sweeps']
                features.extend([
                    1 if liq_data.get('swept_high', False) else 0,
                    1 if liq_data.get('swept_low', False) else 0,
                    1 if liq_data.get('internal_buy_grab', False) else 0,
                    1 if liq_data.get('internal_sell_grab', False) else 0
                ])
            
            if 'premium_discount' in agent_data:
                pd_data = agent_data['premium_discount']
                pd_zone = pd_data.get('current_pd_zone', 'equilibrium')
                features.extend([
                    1 if pd_zone == 'premium' else 0,
                    1 if pd_zone == 'discount' else 0,
                    1 if 'equilibrium' in pd_zone else 0
                ])
            
            if 'ote' in agent_data:
                ote_data = agent_data['ote']
                features.extend([
                    1 if ote_data.get('in_ote_long', False) else 0,
                    1 if ote_data.get('in_ote_short', False) else 0
                ])
            
            # Macro features
            if 'macro_data' in agent_data:
                macro_data = agent_data['macro_data']
                features.extend([
                    macro_data.get('spx', 0),
                    macro_data.get('dxy', 0),
                    macro_data.get('us10y', 0),
                    macro_data.get('vix', 0),
                    macro_data.get('gold', 0)
                ])
            
            # Sentiment features
            if 'sentiment' in agent_data:
                sentiment = agent_data['sentiment'].get('sentiment', 'neutral')
                sentiment_map = {'bullish': 1.0, 'bearish': -1.0, 'neutral': 0.0}
                features.append(sentiment_map.get(sentiment, 0.0))
            
            # Time-based features
            if 'time_data' in agent_data:
                time_data = agent_data['time_data']
                features.extend([
                    time_data.get('hour', 12),
                    time_data.get('day_of_week', 3),
                    1 if time_data.get('in_killzone', False) else 0
                ])
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
            return []
    
    def calculate_model_confidence(self, probability: float) -> float:
        """
        Calculate model confidence score
        """
        # Distance from threshold indicates confidence
        distance_from_threshold = abs(probability - self.threshold)
        max_distance = max(self.threshold, 1.0 - self.threshold)
        
        return distance_from_threshold / max_distance
    
    def get_signal_strength(self) -> float:
        """
        Get current signal strength (0.0 to 1.0)
        """
        if not self.prediction_history:
            return 0.0
        
        # Use recent prediction probability as signal strength
        recent_prediction = self.prediction_history[-1]
        return recent_prediction['probability']
    
    def retrain_model_with_new_data(self, training_data: Dict[str, Any]) -> bool:
        """
        Retrain model with new data
        """
        return self.train_model(training_data)
    
    def get_prediction_statistics(self) -> Dict[str, Any]:
        """
        Get prediction statistics and performance metrics
        """
        if not self.prediction_history:
            return {}
        
        try:
            predictions = self.prediction_history
            
            # Basic statistics
            total_predictions = len(predictions)
            positive_predictions = sum(1 for p in predictions if p['should_trade'])
            
            # Probability statistics
            probabilities = [p['probability'] for p in predictions]
            prob_stats = {
                'mean': np.mean(probabilities),
                'std': np.std(probabilities),
                'min': np.min(probabilities),
                'max': np.max(probabilities),
                'median': np.median(probabilities)
            }
            
            # Recent performance (last 50 predictions)
            recent_predictions = predictions[-50:] if len(predictions) >= 50 else predictions
            recent_positive = sum(1 for p in recent_predictions if p['should_trade'])
            recent_avg_prob = np.mean([p['probability'] for p in recent_predictions])
            
            return {
                'total_predictions': total_predictions,
                'positive_predictions': positive_predictions,
                'positive_rate': positive_predictions / total_predictions,
                'probability_statistics': prob_stats,
                'recent_performance': {
                    'recent_predictions': len(recent_predictions),
                    'recent_positive': recent_positive,
                    'recent_positive_rate': recent_positive / len(recent_predictions),
                    'recent_avg_probability': recent_avg_prob
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating prediction statistics: {e}")
            return {}
    
    def on_message(self, topic: str, message: Dict[str, Any]):
        """
        Handle incoming messages from other agents
        """
        if topic == "retrain_request":
            # Handle model retraining requests
            training_data = message['data']
            self.logger.info("Received retrain request")
            self.retrain_model_with_new_data(training_data)
        
        elif topic == "feature_update":
            # Handle feature updates from other agents
            symbol = message['data'].get('symbol')
            features = message['data'].get('features')
            
            if features:
                # Generate prediction with new features
                prediction_result = self.process_data({
                    'features': features,
                    'symbol': symbol
                })
                
                # Publish updated prediction
                if prediction_result.get('should_trade'):
                    self.publish("ml_prediction_update", {
                        'symbol': symbol,
                        'prediction': prediction_result
                    })
        
        super().on_message(topic, message)
    
    def requires_continuous_processing(self) -> bool:
        """ML agent can benefit from continuous processing for retraining checks"""
        return True
    
    def _continuous_process(self):
        """
        Continuous background processing for ML agent
        """
        try:
            # Check if model needs retraining
            if self.should_retrain():
                self.logger.info("Model retrain interval reached")
                # Could trigger retraining here if we have new data
                # For now, just log the event
                
            # Clean up old prediction history
            if len(self.prediction_history) > 2000:
                self.prediction_history = self.prediction_history[-1000:]
                self.logger.info("Cleaned up old prediction history")
                
        except Exception as e:
            self.logger.error(f"Error in ML continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """
        Get processing interval for continuous processing
        """
        return 300.0  # Check every 5 minutes