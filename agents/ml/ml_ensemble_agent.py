"""
ML Ensemble Agent
Advanced machine learning ensemble with ALL algorithms for >90% win rate
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import joblib
import warnings
warnings.filterwarnings('ignore')

from agents.base_agent import BaseAgent


class MLEnsembleAgent(BaseAgent):
    """
    Advanced ML Ensemble Agent using ALL available algorithms
    Designed for >90% win rate through sophisticated ensemble methods
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ml_ensemble", config)
        
        # Ensemble configuration
        self.ensemble_method = config.get('ensemble_method', 'weighted_voting')
        self.min_model_agreement = config.get('min_model_agreement', 0.8)  # 80% agreement for >90% win rate
        self.confidence_threshold = config.get('confidence_threshold', 0.9)  # Very high threshold
        self.feature_importance_threshold = config.get('feature_importance_threshold', 0.01)
        
        # Model configuration
        self.models_config = self.load_all_models_config()
        self.trained_models = {}
        self.model_weights = {}
        self.model_performance = {}
        
        # Feature engineering
        self.feature_columns = []
        self.feature_importance_history = []
        
        # Prediction tracking
        self.prediction_history = []
        self.ensemble_performance = {'correct': 0, 'total': 0, 'win_rate': 0.0}
        
        self.logger.info(f"ML Ensemble Agent initialized with {len(self.models_config)} algorithms")
    
    def load_all_models_config(self) -> Dict[str, Any]:
        """Load configuration for ALL ML algorithms"""
        return {
            'xgboost': {
                'name': 'XGBoost',
                'params': {
                    'n_estimators': 200,
                    'max_depth': 8,
                    'learning_rate': 0.1,
                    'subsample': 0.8,
                    'colsample_bytree': 0.8,
                    'random_state': 42,
                    'n_jobs': -1
                },
                'weight': 1.5  # High weight for strong performer
            },
            'lightgbm': {
                'name': 'LightGBM',
                'params': {
                    'n_estimators': 200,
                    'max_depth': 8,
                    'learning_rate': 0.1,
                    'subsample': 0.8,
                    'colsample_bytree': 0.8,
                    'random_state': 42,
                    'n_jobs': -1,
                    'verbose': -1
                },
                'weight': 1.5  # High weight for strong performer
            },
            'catboost': {
                'name': 'CatBoost',
                'params': {
                    'iterations': 200,
                    'depth': 8,
                    'learning_rate': 0.1,
                    'random_seed': 42,
                    'verbose': False
                },
                'weight': 1.4
            },
            'random_forest': {
                'name': 'RandomForest',
                'params': {
                    'n_estimators': 200,
                    'max_depth': 10,
                    'random_state': 42,
                    'n_jobs': -1
                },
                'weight': 1.2
            },
            'extra_trees': {
                'name': 'ExtraTrees',
                'params': {
                    'n_estimators': 200,
                    'max_depth': 10,
                    'random_state': 42,
                    'n_jobs': -1
                },
                'weight': 1.1
            },
            'lstm': {
                'name': 'LSTM',
                'params': {
                    'units': [128, 64, 32],
                    'dropout': 0.2,
                    'epochs': 100,
                    'batch_size': 32,
                    'sequence_length': 60
                },
                'weight': 1.3  # Good for time series
            },
            'gru': {
                'name': 'GRU',
                'params': {
                    'units': [128, 64],
                    'dropout': 0.2,
                    'epochs': 100,
                    'batch_size': 32,
                    'sequence_length': 60
                },
                'weight': 1.2
            },
            'svm': {
                'name': 'SVM',
                'params': {
                    'kernel': 'rbf',
                    'C': 1.0,
                    'gamma': 'scale',
                    'probability': True
                },
                'weight': 0.9
            },
            'logistic_regression': {
                'name': 'LogisticRegression',
                'params': {
                    'C': 1.0,
                    'random_state': 42,
                    'n_jobs': -1
                },
                'weight': 0.8
            },
            'adaboost': {
                'name': 'AdaBoost',
                'params': {
                    'n_estimators': 100,
                    'learning_rate': 1.0,
                    'random_state': 42
                },
                'weight': 0.9
            },
            'gradient_boosting': {
                'name': 'GradientBoosting',
                'params': {
                    'n_estimators': 200,
                    'learning_rate': 0.1,
                    'max_depth': 6,
                    'random_state': 42
                },
                'weight': 1.1
            },
            'neural_network': {
                'name': 'MLPClassifier',
                'params': {
                    'hidden_layer_sizes': (128, 64, 32),
                    'activation': 'relu',
                    'solver': 'adam',
                    'alpha': 0.001,
                    'random_state': 42,
                    'max_iter': 500
                },
                'weight': 1.0
            }
        }
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data for ML ensemble prediction
        
        Args:
            data: Dictionary containing features and optional target
            
        Returns:
            Dictionary with ensemble prediction results
        """
        try:
            action = data.get('action', 'predict')
            
            if action == 'train':
                return self.train_ensemble(data)
            elif action == 'predict':
                return self.predict_ensemble(data)
            elif action == 'evaluate':
                return self.evaluate_ensemble(data)
            else:
                return {'error': f'Unknown action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error processing ML ensemble data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def train_ensemble(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train the complete ensemble with ALL algorithms
        """
        required_fields = ['X', 'y']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing training data'}
        
        X = data['X']
        y = data['y']
        feature_names = data.get('feature_names', [f'feature_{i}' for i in range(X.shape[1])])
        
        self.logger.info(f"Training ensemble with {len(self.models_config)} algorithms on {X.shape[0]} samples, {X.shape[1]} features")
        
        training_results = {}
        
        # Train each model
        for model_name, model_config in self.models_config.items():
            try:
                self.logger.info(f"Training {model_config['name']}...")
                
                model, performance = self.train_individual_model(model_name, model_config, X, y)
                
                if model is not None:
                    self.trained_models[model_name] = model
                    self.model_performance[model_name] = performance
                    training_results[model_name] = performance
                    
                    self.logger.info(f"{model_config['name']} trained - Accuracy: {performance['accuracy']:.3f}")
                
            except Exception as e:
                self.logger.error(f"Error training {model_name}: {e}")
                training_results[model_name] = {'error': str(e)}
        
        # Calculate ensemble weights based on performance
        self.calculate_ensemble_weights()
        
        # Store feature names
        self.feature_columns = feature_names
        
        # Save ensemble
        self.save_ensemble()
        
        return {
            'agent_id': self.agent_id,
            'training_completed': True,
            'models_trained': len(self.trained_models),
            'training_results': training_results,
            'ensemble_weights': self.model_weights,
            'feature_count': len(feature_names),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def train_individual_model(self, model_name: str, model_config: Dict[str, Any], 
                              X: np.ndarray, y: np.ndarray) -> Tuple[Any, Dict[str, float]]:
        """Train individual ML model"""
        try:
            # Import required libraries
            from sklearn.model_selection import cross_val_score, StratifiedKFold
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            
            # Initialize model based on type
            model = self.initialize_model(model_name, model_config['params'])
            
            # Train model
            if model_name in ['lstm', 'gru']:
                # Neural network models need special handling
                model, performance = self.train_neural_model(model, model_name, X, y)
            else:
                # Scikit-learn compatible models
                model.fit(X, y)
                
                # Calculate performance with cross-validation
                cv_scores = cross_val_score(model, X, y, cv=StratifiedKFold(n_splits=5), scoring='accuracy')
                
                # Get predictions for detailed metrics
                y_pred = model.predict(X)
                
                performance = {
                    'accuracy': cv_scores.mean(),
                    'accuracy_std': cv_scores.std(),
                    'precision': precision_score(y, y_pred, average='weighted'),
                    'recall': recall_score(y, y_pred, average='weighted'),
                    'f1_score': f1_score(y, y_pred, average='weighted'),
                    'cv_scores': cv_scores.tolist()
                }
            
            return model, performance
            
        except Exception as e:
            self.logger.error(f"Error training {model_name}: {e}")
            return None, {'error': str(e)}
    
    def initialize_model(self, model_name: str, params: Dict[str, Any]):
        """Initialize ML model based on type"""
        try:
            if model_name == 'xgboost':
                import xgboost as xgb
                return xgb.XGBClassifier(**params)
            
            elif model_name == 'lightgbm':
                import lightgbm as lgb
                return lgb.LGBMClassifier(**params)
            
            elif model_name == 'catboost':
                from catboost import CatBoostClassifier
                return CatBoostClassifier(**params)
            
            elif model_name == 'random_forest':
                from sklearn.ensemble import RandomForestClassifier
                return RandomForestClassifier(**params)
            
            elif model_name == 'extra_trees':
                from sklearn.ensemble import ExtraTreesClassifier
                return ExtraTreesClassifier(**params)
            
            elif model_name == 'svm':
                from sklearn.svm import SVC
                return SVC(**params)
            
            elif model_name == 'logistic_regression':
                from sklearn.linear_model import LogisticRegression
                return LogisticRegression(**params)
            
            elif model_name == 'adaboost':
                from sklearn.ensemble import AdaBoostClassifier
                return AdaBoostClassifier(**params)
            
            elif model_name == 'gradient_boosting':
                from sklearn.ensemble import GradientBoostingClassifier
                return GradientBoostingClassifier(**params)
            
            elif model_name == 'neural_network':
                from sklearn.neural_network import MLPClassifier
                return MLPClassifier(**params)
            
            elif model_name in ['lstm', 'gru']:
                return self.create_neural_model(model_name, params)
            
            else:
                raise ValueError(f"Unknown model type: {model_name}")
                
        except ImportError as e:
            self.logger.error(f"Required library not available for {model_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error initializing {model_name}: {e}")
            return None
    
    def create_neural_model(self, model_type: str, params: Dict[str, Any]):
        """Create neural network model (LSTM/GRU)"""
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout
            
            model = Sequential()
            
            # Add layers based on model type
            units = params['units']
            dropout = params['dropout']
            
            if model_type == 'lstm':
                for i, unit_count in enumerate(units):
                    return_sequences = i < len(units) - 1
                    model.add(LSTM(unit_count, return_sequences=return_sequences))
                    model.add(Dropout(dropout))
            
            elif model_type == 'gru':
                for i, unit_count in enumerate(units):
                    return_sequences = i < len(units) - 1
                    model.add(GRU(unit_count, return_sequences=return_sequences))
                    model.add(Dropout(dropout))
            
            # Output layer
            model.add(Dense(1, activation='sigmoid'))
            
            # Compile model
            model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
            
            return model
            
        except ImportError:
            self.logger.error(f"TensorFlow not available for {model_type}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating {model_type}: {e}")
            return None
    
    def train_neural_model(self, model, model_name: str, X: np.ndarray, y: np.ndarray) -> Tuple[Any, Dict[str, float]]:
        """Train neural network model"""
        try:
            # Reshape data for LSTM/GRU if needed
            if model_name in ['lstm', 'gru']:
                sequence_length = self.models_config[model_name]['params']['sequence_length']
                X_reshaped = self.reshape_for_neural_network(X, sequence_length)
                if X_reshaped is None:
                    raise ValueError("Insufficient data for sequence modeling")
                X = X_reshaped
            
            # Train model
            epochs = self.models_config[model_name]['params']['epochs']
            batch_size = self.models_config[model_name]['params']['batch_size']
            
            history = model.fit(X, y, epochs=epochs, batch_size=batch_size, 
                              validation_split=0.2, verbose=0)
            
            # Calculate performance
            y_pred_prob = model.predict(X)
            y_pred = (y_pred_prob > 0.5).astype(int).flatten()
            
            accuracy = np.mean(y == y_pred)
            
            performance = {
                'accuracy': accuracy,
                'val_accuracy': max(history.history['val_accuracy']),
                'final_loss': history.history['loss'][-1],
                'val_loss': history.history['val_loss'][-1]
            }
            
            return model, performance
            
        except Exception as e:
            self.logger.error(f"Error training neural model {model_name}: {e}")
            return None, {'error': str(e)}
    
    def reshape_for_neural_network(self, X: np.ndarray, sequence_length: int) -> Optional[np.ndarray]:
        """Reshape data for LSTM/GRU models"""
        if len(X) < sequence_length:
            return None
        
        # Create sequences
        sequences = []
        for i in range(sequence_length, len(X)):
            sequences.append(X[i-sequence_length:i])
        
        return np.array(sequences)
    
    def predict_ensemble(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make ensemble prediction with >90% win rate targeting
        """
        required_fields = ['features']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing features for prediction'}
        
        features = data['features']
        
        if not self.trained_models:
            return {'error': 'No trained models available'}
        
        try:
            # Get predictions from all models
            model_predictions = {}
            model_probabilities = {}
            
            for model_name, model in self.trained_models.items():
                try:
                    if model_name in ['lstm', 'gru']:
                        # Neural network prediction
                        prob = self.predict_neural_model(model, model_name, features)
                        prediction = 1 if prob > 0.5 else 0
                    else:
                        # Scikit-learn prediction
                        prediction = model.predict([features])[0]
                        prob = model.predict_proba([features])[0][1] if hasattr(model, 'predict_proba') else 0.5
                    
                    model_predictions[model_name] = prediction
                    model_probabilities[model_name] = prob
                    
                except Exception as e:
                    self.logger.warning(f"Error getting prediction from {model_name}: {e}")
                    continue
            
            # Calculate ensemble prediction
            ensemble_result = self.calculate_ensemble_prediction(model_predictions, model_probabilities)
            
            # Apply >90% win rate filters
            final_decision = self.apply_high_winrate_filters(ensemble_result, data)
            
            # Update tracking
            self.update_prediction_tracking(ensemble_result, final_decision)
            
            return {
                'agent_id': self.agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ensemble_prediction': ensemble_result,
                'final_decision': final_decision,
                'model_predictions': model_predictions,
                'model_probabilities': model_probabilities,
                'model_agreement': ensemble_result['agreement_score'],
                'confidence': ensemble_result['confidence'],
                'should_trade': final_decision['should_trade'],
                'trade_direction': final_decision.get('direction'),
                'win_rate_filters_applied': final_decision['filters_applied']
            }
            
        except Exception as e:
            self.logger.error(f"Error making ensemble prediction: {e}")
            return {'error': str(e), 'should_trade': False}
    
    def predict_neural_model(self, model, model_name: str, features: np.ndarray) -> float:
        """Make prediction with neural network model"""
        try:
            if model_name in ['lstm', 'gru']:
                # Reshape for sequence prediction
                sequence_length = self.models_config[model_name]['params']['sequence_length']
                if len(features) >= sequence_length:
                    # Use last sequence_length features
                    features_seq = features[-sequence_length:].reshape(1, sequence_length, -1)
                    prob = model.predict(features_seq)[0][0]
                else:
                    # Pad with zeros if insufficient data
                    padded_features = np.zeros((sequence_length, len(features)))
                    padded_features[-1] = features
                    features_seq = padded_features.reshape(1, sequence_length, -1)
                    prob = model.predict(features_seq)[0][0]
                
                return float(prob)
            
            return 0.5
            
        except Exception as e:
            self.logger.error(f"Error predicting with {model_name}: {e}")
            return 0.5
    
    def calculate_ensemble_prediction(self, model_predictions: Dict[str, int], 
                                    model_probabilities: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate ensemble prediction using weighted voting
        """
        if not model_predictions:
            return {'prediction': 0, 'confidence': 0.0, 'agreement_score': 0.0}
        
        # Weighted voting
        weighted_sum = 0.0
        total_weight = 0.0
        
        for model_name, prediction in model_predictions.items():
            weight = self.model_weights.get(model_name, 1.0)
            prob = model_probabilities.get(model_name, 0.5)
            
            weighted_sum += prob * weight
            total_weight += weight
        
        # Calculate ensemble probability
        ensemble_prob = weighted_sum / total_weight if total_weight > 0 else 0.5
        ensemble_prediction = 1 if ensemble_prob > 0.5 else 0
        
        # Calculate agreement score
        predictions_list = list(model_predictions.values())
        agreement_score = predictions_list.count(ensemble_prediction) / len(predictions_list)
        
        # Calculate confidence
        confidence = abs(ensemble_prob - 0.5) * 2  # Scale to 0-1
        
        return {
            'prediction': ensemble_prediction,
            'probability': ensemble_prob,
            'confidence': confidence,
            'agreement_score': agreement_score,
            'models_voted': len(model_predictions)
        }
    
    def apply_high_winrate_filters(self, ensemble_result: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply strict filters for >90% win rate targeting
        """
        filters_applied = []
        should_trade = False
        
        # Filter 1: Minimum model agreement (80%+)
        if ensemble_result['agreement_score'] >= self.min_model_agreement:
            filters_applied.append('model_agreement_passed')
        else:
            filters_applied.append('model_agreement_failed')
            return {
                'should_trade': False,
                'reason': 'Insufficient model agreement',
                'agreement_score': ensemble_result['agreement_score'],
                'filters_applied': filters_applied
            }
        
        # Filter 2: High confidence threshold (90%+)
        if ensemble_result['confidence'] >= self.confidence_threshold:
            filters_applied.append('confidence_threshold_passed')
        else:
            filters_applied.append('confidence_threshold_failed')
            return {
                'should_trade': False,
                'reason': 'Insufficient confidence',
                'confidence': ensemble_result['confidence'],
                'filters_applied': filters_applied
            }
        
        # Filter 3: Pattern confluence requirement
        pattern_confluence = data.get('pattern_confluence_count', 0)
        min_patterns_required = 5 if self.market_type == 'forex' else 4  # Strict requirements
        
        if pattern_confluence >= min_patterns_required:
            filters_applied.append('pattern_confluence_passed')
        else:
            filters_applied.append('pattern_confluence_failed')
            return {
                'should_trade': False,
                'reason': f'Insufficient pattern confluence ({pattern_confluence}/{min_patterns_required})',
                'pattern_confluence': pattern_confluence,
                'filters_applied': filters_applied
            }
        
        # Filter 4: Market regime filter
        market_regime = data.get('market_regime', 'unknown')
        if market_regime in ['trending', 'high_volatility']:
            filters_applied.append('market_regime_favorable')
        else:
            filters_applied.append('market_regime_unfavorable')
            return {
                'should_trade': False,
                'reason': f'Unfavorable market regime: {market_regime}',
                'filters_applied': filters_applied
            }
        
        # Filter 5: Session/Volume confirmation
        if self.market_type == 'forex':
            session_quality = data.get('session_quality', 0.0)
            if session_quality >= 0.8:
                filters_applied.append('session_quality_passed')
            else:
                filters_applied.append('session_quality_failed')
                return {
                    'should_trade': False,
                    'reason': f'Poor session quality: {session_quality}',
                    'filters_applied': filters_applied
                }
        
        elif self.market_type == 'crypto':
            volume_confirmation = data.get('volume_confirmation', False)
            if volume_confirmation:
                filters_applied.append('volume_confirmation_passed')
            else:
                filters_applied.append('volume_confirmation_failed')
                return {
                    'should_trade': False,
                    'reason': 'No volume confirmation',
                    'filters_applied': filters_applied
                }
        
        # All filters passed
        filters_applied.append('all_filters_passed')
        
        return {
            'should_trade': True,
            'direction': 'long' if ensemble_result['prediction'] == 1 else 'short',
            'confidence': ensemble_result['confidence'],
            'agreement_score': ensemble_result['agreement_score'],
            'probability': ensemble_result['probability'],
            'filters_applied': filters_applied,
            'expected_win_rate': self.estimate_win_rate(ensemble_result, filters_applied)
        }
    
    def estimate_win_rate(self, ensemble_result: Dict[str, Any], filters_applied: List[str]) -> float:
        """Estimate win rate based on ensemble quality and filters"""
        base_win_rate = 0.6  # Base 60%
        
        # Agreement bonus
        agreement_bonus = (ensemble_result['agreement_score'] - 0.5) * 0.4  # Up to 20% bonus
        
        # Confidence bonus
        confidence_bonus = (ensemble_result['confidence'] - 0.5) * 0.3  # Up to 15% bonus
        
        # Filter bonus
        filter_bonus = len([f for f in filters_applied if 'passed' in f]) * 0.05  # 5% per passed filter
        
        estimated_win_rate = base_win_rate + agreement_bonus + confidence_bonus + filter_bonus
        
        return min(estimated_win_rate, 0.95)  # Cap at 95%
    
    def calculate_ensemble_weights(self):
        """Calculate ensemble weights based on model performance"""
        if not self.model_performance:
            return
        
        # Weight models based on accuracy and other metrics
        for model_name, performance in self.model_performance.items():
            if 'error' not in performance:
                # Base weight from configuration
                base_weight = self.models_config[model_name]['weight']
                
                # Performance adjustment
                accuracy = performance.get('accuracy', 0.5)
                f1_score = performance.get('f1_score', 0.5)
                
                # Calculate performance multiplier
                performance_multiplier = (accuracy * 0.7 + f1_score * 0.3)
                
                # Final weight
                final_weight = base_weight * performance_multiplier
                self.model_weights[model_name] = final_weight
                
                self.logger.info(f"{model_name} weight: {final_weight:.3f} (accuracy: {accuracy:.3f})")
    
    def evaluate_ensemble(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate ensemble performance"""
        # Implementation for ensemble evaluation
        return {
            'ensemble_performance': self.ensemble_performance,
            'model_count': len(self.trained_models),
            'current_win_rate': self.ensemble_performance['win_rate']
        }
    
    def save_ensemble(self):
        """Save trained ensemble"""
        try:
            ensemble_data = {
                'trained_models': self.trained_models,
                'model_weights': self.model_weights,
                'model_performance': self.model_performance,
                'feature_columns': self.feature_columns,
                'config': self.config,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            joblib.dump(ensemble_data, 'ml_ensemble_model.joblib')
            self.logger.info("Ensemble saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving ensemble: {e}")
    
    def update_prediction_tracking(self, ensemble_result: Dict[str, Any], final_decision: Dict[str, Any]):
        """Update prediction tracking for performance monitoring"""
        prediction_entry = {
            'timestamp': datetime.now(timezone.utc),
            'ensemble_result': ensemble_result,
            'final_decision': final_decision,
            'should_trade': final_decision['should_trade']
        }
        
        self.prediction_history.append(prediction_entry)
        
        # Limit history size
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-1000:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on ensemble quality"""
        if not self.trained_models:
            return 0.0
        
        # Signal strength based on ensemble quality
        factors = []
        
        # Model count factor
        model_count_factor = min(len(self.trained_models) / 10.0, 1.0)
        factors.append(model_count_factor)
        
        # Average model performance
        if self.model_performance:
            accuracies = [perf.get('accuracy', 0.5) for perf in self.model_performance.values() 
                         if 'error' not in perf]
            if accuracies:
                avg_accuracy = np.mean(accuracies)
                factors.append(avg_accuracy)
        
        # Current win rate
        factors.append(self.ensemble_performance['win_rate'])
        
        return np.mean(factors) if factors else 0.0
    
    def get_ensemble_summary(self) -> Dict[str, Any]:
        """Get comprehensive ensemble summary"""
        return {
            'agent_id': self.agent_id,
            'models_trained': len(self.trained_models),
            'model_types': list(self.trained_models.keys()),
            'ensemble_performance': self.ensemble_performance,
            'prediction_history_count': len(self.prediction_history),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'ensemble_method': self.ensemble_method,
                'min_model_agreement': self.min_model_agreement,
                'confidence_threshold': self.confidence_threshold
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """ML ensemble agent doesn't need continuous processing"""
        return False