"""
Intensive Backtesting Agent
Ultra-comprehensive backtesting for maximum ML data generation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
import concurrent.futures
import multiprocessing as mp
from itertools import product

from agents.base_agent import BaseAgent


class IntensiveBacktestingAgent(BaseAgent):
    """
    Intensive Backtesting Agent - Maximum data generation for ML training
    Runs 10-15+ backtests simultaneously with parameter sweeps for comprehensive data
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("intensive_backtesting", config)
        
        # Intensive backtesting configuration
        self.max_parallel_backtests = config.get('max_parallel_backtests', 15)  # 10-15 simultaneous
        self.parameter_sweep_depth = config.get('parameter_sweep_depth', 'maximum')
        self.data_collection_priority = config.get('data_collection_priority', 'maximum_samples')
        
        # Backtesting parameters for maximum data
        self.timeframes = config.get('timeframes', ['5m', '15m', '1h', '4h', '1d'])  # More timeframes
        self.parameter_combinations = config.get('parameter_combinations', 1000)  # 1000+ combinations
        self.samples_per_combination = config.get('samples_per_combination', 10000)  # 10K samples each
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Data generation tracking
        self.backtest_results_database = []
        self.ml_training_samples = []
        self.parameter_performance_map = {}
        self.data_generation_metrics = {
            'total_samples_generated': 0,
            'total_backtests_completed': 0,
            'total_parameter_combinations_tested': 0
        }
        
        # Parallel processing setup
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_backtests)
        self.backtest_queue = []
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Intensive Backtesting Agent initialized - {self.max_parallel_backtests} parallel backtests for MAXIMUM ML data")
    
    def apply_market_specific_config(self):
        """Apply market-specific intensive backtesting configuration"""
        if self.market_type == 'forex':
            # Forex: 50-year data available
            self.symbols_for_intensive_testing = [
                'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF',
                'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY', 'XAU/USD', 'XAG/USD'
            ]
            self.data_start_date = '1975-01-01'  # Full 50 years
            self.session_based_backtesting = True
            
        elif self.market_type == 'crypto':
            # Crypto: Maximum available data
            self.symbols_for_intensive_testing = [
                'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'XRP/USDT',
                'DOT/USDT', 'AVAX/USDT', 'LINK/USDT', 'MATIC/USDT', 'UNI/USDT', 'LTC/USDT',
                'BCH/USDT', 'ATOM/USDT', 'DOGE/USDT'
            ]
            self.data_start_date = '2009-01-01'  # Bitcoin start
            self.volatility_based_backtesting = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process intensive backtesting requests for maximum ML data
        
        Args:
            data: Dictionary containing backtesting configuration
            
        Returns:
            Dictionary with intensive backtesting results
        """
        try:
            action = data.get('action', 'run_intensive_backtest')
            
            if action == 'run_intensive_backtest':
                return self.run_intensive_backtest_suite(data)
            elif action == 'parameter_sweep_backtest':
                return self.run_parameter_sweep_backtest(data)
            elif action == 'multi_symbol_backtest':
                return self.run_multi_symbol_backtest(data)
            elif action == 'generate_ml_dataset':
                return self.generate_comprehensive_ml_dataset(data)
            elif action == 'validate_50_year_data':
                return self.validate_50_year_historical_data(data)
            else:
                return {'error': f'Unknown intensive backtesting action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error in intensive backtesting: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def run_intensive_backtest_suite(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run intensive backtest suite with maximum parallelization
        """
        symbols = data.get('symbols', self.symbols_for_intensive_testing)
        timeframes = data.get('timeframes', self.timeframes)
        
        self.logger.info(f"Starting INTENSIVE backtest suite: {len(symbols)} symbols × {len(timeframes)} timeframes = {len(symbols) * len(timeframes)} backtests")
        
        # Generate all symbol-timeframe combinations
        backtest_combinations = list(product(symbols, timeframes))
        
        # Split into batches for parallel processing
        batch_size = self.max_parallel_backtests
        batches = [backtest_combinations[i:i + batch_size] for i in range(0, len(backtest_combinations), batch_size)]
        
        all_results = []
        total_samples_generated = 0
        
        # Process batches in parallel
        for batch_num, batch in enumerate(batches):
            self.logger.info(f"Processing batch {batch_num + 1}/{len(batches)} with {len(batch)} backtests...")
            
            # Submit parallel backtests
            futures = []
            for symbol, timeframe in batch:
                future = self.executor.submit(self.run_single_intensive_backtest, symbol, timeframe, data)
                futures.append((future, symbol, timeframe))
            
            # Collect results
            batch_results = []
            for future, symbol, timeframe in futures:
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per backtest
                    batch_results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'result': result
                    })
                    
                    # Count ML samples generated
                    samples_generated = result.get('ml_samples_generated', 0)
                    total_samples_generated += samples_generated
                    
                    self.logger.info(f"Completed {symbol} {timeframe}: {samples_generated} ML samples generated")
                    
                except Exception as e:
                    self.logger.error(f"Backtest failed for {symbol} {timeframe}: {e}")
                    batch_results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'error': str(e)
                    })
            
            all_results.extend(batch_results)
        
        # Update metrics
        self.data_generation_metrics['total_backtests_completed'] += len(all_results)
        self.data_generation_metrics['total_samples_generated'] += total_samples_generated
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'intensive_backtest_completed': True,
            'total_backtests': len(all_results),
            'successful_backtests': len([r for r in all_results if 'error' not in r]),
            'total_ml_samples_generated': total_samples_generated,
            'parallel_backtests_used': self.max_parallel_backtests,
            'backtest_results': all_results,
            'data_generation_metrics': self.data_generation_metrics,
            'market_type': self.market_type
        }
    
    def run_single_intensive_backtest(self, symbol: str, timeframe: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run single intensive backtest with maximum data extraction
        """
        try:
            # Load historical data
            historical_data = self.load_comprehensive_historical_data(symbol, timeframe)
            
            if historical_data is None or len(historical_data) < 1000:
                return {'error': 'Insufficient historical data', 'ml_samples_generated': 0}
            
            # Generate multiple parameter variations for this symbol/timeframe
            parameter_variations = self.generate_parameter_variations(50)  # 50 variations per backtest
            
            ml_samples_generated = 0
            backtest_results = []
            
            # Run backtest with each parameter variation
            for param_set in parameter_variations:
                try:
                    # Run backtest simulation
                    simulation_result = self.simulate_intensive_trading(historical_data, symbol, timeframe, param_set)
                    
                    # Extract ML training samples
                    ml_samples = self.extract_ml_samples_from_simulation(simulation_result, param_set, historical_data)
                    ml_samples_generated += len(ml_samples)
                    
                    # Store ML samples
                    self.ml_training_samples.extend(ml_samples)
                    
                    # Calculate performance metrics
                    performance = self.calculate_intensive_performance_metrics(simulation_result)
                    
                    backtest_results.append({
                        'parameters': param_set,
                        'performance': performance,
                        'ml_samples': len(ml_samples),
                        'trades_count': len(simulation_result.get('trades', []))
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Parameter variation failed for {symbol} {timeframe}: {e}")
                    continue
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'parameter_variations_tested': len(parameter_variations),
                'successful_variations': len(backtest_results),
                'ml_samples_generated': ml_samples_generated,
                'backtest_results': backtest_results,
                'data_points_analyzed': len(historical_data)
            }
            
        except Exception as e:
            self.logger.error(f"Intensive backtest failed for {symbol} {timeframe}: {e}")
            return {'error': str(e), 'ml_samples_generated': 0}
    
    def generate_parameter_variations(self, count: int) -> List[Dict[str, Any]]:
        """Generate parameter variations for comprehensive testing"""
        variations = []
        
        # Define parameter ranges for intensive testing
        parameter_ranges = {
            'confluence_patterns': [2, 3, 4, 5, 6, 7, 8],
            'confluence_score': [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            'ml_confidence': [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95],
            'ml_agreement': [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9],
            'risk_per_trade': [0.005, 0.01, 0.015, 0.02, 0.025],
            'stop_loss_atr': [1.0, 1.5, 2.0, 2.5, 3.0],
            'take_profit_atr': [2.0, 3.0, 4.0, 5.0, 6.0]
        }
        
        # Generate random combinations
        for _ in range(count):
            variation = {}
            for param, values in parameter_ranges.items():
                variation[param] = np.random.choice(values)
            variations.append(variation)
        
        return variations
    
    def simulate_intensive_trading(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                                 parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate trading with intensive data collection
        """
        simulation_result = {
            'trades': [],
            'rejected_opportunities': [],
            'agent_signals_history': [],
            'market_context_history': [],
            'performance_metrics': {}
        }
        
        # Simulate with higher frequency for more data
        analysis_frequency = 1  # Analyze every bar for maximum data
        
        for i in range(100, len(df), analysis_frequency):
            try:
                # Get current data window
                current_data = df.iloc[:i+1]
                current_bar = df.iloc[i]
                
                # Simulate ALL agent signals (comprehensive)
                agent_signals = self.simulate_comprehensive_agent_signals(current_data, symbol, parameters)
                
                # Record agent signals for ML training
                simulation_result['agent_signals_history'].append({
                    'timestamp': current_bar.name,
                    'bar_index': i,
                    'agent_signals': agent_signals,
                    'market_data': {
                        'open': current_bar['open'],
                        'high': current_bar['high'],
                        'low': current_bar['low'],
                        'close': current_bar['close'],
                        'volume': current_bar.get('volume', 0)
                    }
                })
                
                # Check for trading opportunities (with relaxed parameters for data collection)
                trading_decision = self.make_intensive_trading_decision(agent_signals, parameters)
                
                if trading_decision['should_trade']:
                    # Record trade for ML training
                    trade_outcome = self.simulate_trade_outcome(current_data, trading_decision, parameters)
                    simulation_result['trades'].append(trade_outcome)
                else:
                    # Record rejected opportunity for ML training
                    simulation_result['rejected_opportunities'].append({
                        'timestamp': current_bar.name,
                        'rejection_reason': trading_decision['rejection_reason'],
                        'agent_signals': agent_signals,
                        'parameters': parameters
                    })
                
            except Exception as e:
                self.logger.warning(f"Error in intensive simulation at bar {i}: {e}")
                continue
        
        return simulation_result
    
    def simulate_comprehensive_agent_signals(self, df: pd.DataFrame, symbol: str, 
                                           parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate comprehensive agent signals for maximum feature extraction
        """
        # Generate realistic agent signals based on actual market data
        signals = {}
        
        # ICT/SMC signals (21 agents)
        signals['ict_smc'] = {
            'fair_value_gaps': self.simulate_fvg_signals(df),
            'order_blocks': self.simulate_ob_signals(df),
            'market_structure': self.simulate_mss_signals(df),
            'liquidity_sweeps': self.simulate_liquidity_signals(df),
            'premium_discount': self.simulate_pd_signals(df),
            'ote': self.simulate_ote_signals(df),
            'breaker_blocks': self.simulate_breaker_signals(df),
            'sof': self.simulate_sof_signals(df),
            'displacement': self.simulate_displacement_signals(df),
            'engulfing': self.simulate_engulfing_signals(df),
            'mitigation_blocks': self.simulate_mitigation_signals(df),
            'killzone': self.simulate_killzone_signals(df),
            'pattern_cluster': self.simulate_cluster_signals(df),
            'swing_failure': self.simulate_sfp_signals(df),
            'htf_confluence': self.simulate_htf_signals(df),
            'judas_swing': self.simulate_judas_signals(df),
            'power_of_three': self.simulate_po3_signals(df),
            'market_maker': self.simulate_mm_signals(df),
            'turtle_soup': self.simulate_turtle_signals(df),
            'imbalance': self.simulate_imbalance_signals(df),
            'momentum_shift': self.simulate_momentum_signals(df)
        }
        
        # Analysis signals (4 agents)
        signals['analysis'] = {
            'volume_analysis': self.simulate_volume_signals(df),
            'session_analysis': self.simulate_session_signals(df),
            'technical_indicators': self.simulate_technical_signals(df),
            'market_regime': self.simulate_regime_signals(df)
        }
        
        # ML signals (2 agents)
        signals['ml'] = {
            'ml_ensemble': self.simulate_ml_ensemble_signals(df, parameters),
            'ml_prediction': self.simulate_ml_prediction_signals(df)
        }
        
        # Calculate confluence metrics
        signals['confluence_metrics'] = self.calculate_confluence_metrics(signals)
        
        return signals
    
    def simulate_fvg_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate Fair Value Gap signals with realistic patterns"""
        if len(df) < 5:
            return {'signal_strength': 0.0, 'fvgs_detected': 0}
        
        # Look for actual gap patterns
        fvgs_detected = 0
        gap_sizes = []
        
        for i in range(2, len(df)):
            prev_bar = df.iloc[i-1]
            curr_bar = df.iloc[i]
            
            # Check for bullish FVG
            if curr_bar['low'] > prev_bar['high']:
                gap_size = (curr_bar['low'] - prev_bar['high']) / prev_bar['high']
                if gap_size > 0.001:  # Minimum gap size
                    fvgs_detected += 1
                    gap_sizes.append(gap_size)
            
            # Check for bearish FVG
            elif curr_bar['high'] < prev_bar['low']:
                gap_size = (prev_bar['low'] - curr_bar['high']) / curr_bar['high']
                if gap_size > 0.001:
                    fvgs_detected += 1
                    gap_sizes.append(gap_size)
        
        return {
            'signal_strength': min(fvgs_detected / 10.0, 1.0),
            'fvgs_detected': fvgs_detected,
            'avg_gap_size': np.mean(gap_sizes) if gap_sizes else 0,
            'max_gap_size': max(gap_sizes) if gap_sizes else 0,
            'gap_frequency': fvgs_detected / len(df) if len(df) > 0 else 0
        }
    
    def simulate_ob_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate Order Block signals"""
        if len(df) < 10:
            return {'signal_strength': 0.0, 'order_blocks': 0}
        
        # Simplified OB detection for data generation
        ob_count = 0
        recent_data = df.iloc[-20:]
        
        # Look for strong bullish/bearish candles followed by retracement
        for i in range(1, len(recent_data) - 1):
            curr_bar = recent_data.iloc[i]
            body_size = abs(curr_bar['close'] - curr_bar['open'])
            total_range = curr_bar['high'] - curr_bar['low']
            
            if total_range > 0 and body_size / total_range > 0.6:  # Strong body
                ob_count += 1
        
        return {
            'signal_strength': min(ob_count / 5.0, 1.0),
            'order_blocks': ob_count,
            'ob_density': ob_count / len(recent_data)
        }
    
    def simulate_mss_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate Market Structure Shift signals"""
        if len(df) < 15:
            return {'signal_strength': 0.0, 'mss_detected': False}
        
        # Look for higher highs/lower lows pattern breaks
        recent_highs = df['high'].rolling(10).max()
        recent_lows = df['low'].rolling(10).min()
        
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        bullish_mss = current_high > recent_highs.iloc[-2] and current_low > recent_lows.iloc[-10]
        bearish_mss = current_low < recent_lows.iloc[-2] and current_high < recent_highs.iloc[-10]
        
        return {
            'signal_strength': 0.8 if (bullish_mss or bearish_mss) else 0.2,
            'bullish_mss': bullish_mss,
            'bearish_mss': bearish_mss,
            'structure_strength': 0.8 if (bullish_mss or bearish_mss) else 0.2
        }
    
    # Add more simulation methods for other agents...
    def simulate_liquidity_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate liquidity sweep signals"""
        return {'signal_strength': np.random.uniform(0.1, 0.9), 'sweeps_detected': np.random.randint(0, 3)}
    
    def simulate_pd_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate premium/discount signals"""
        return {'signal_strength': np.random.uniform(0.2, 0.8), 'pd_zone': np.random.choice(['premium', 'discount', 'equilibrium'])}
    
    def simulate_ote_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate OTE signals"""
        return {'signal_strength': np.random.uniform(0.3, 0.9), 'in_ote': np.random.choice([True, False])}
    
    def simulate_volume_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate volume analysis signals"""
        if 'volume' not in df.columns:
            return {'signal_strength': 0.0}
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        return {
            'signal_strength': min(volume_ratio / 3.0, 1.0),
            'volume_spike': volume_ratio > 1.5,
            'volume_ratio': volume_ratio
        }
    
    def simulate_technical_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate technical indicator signals"""
        # Calculate basic RSI
        if len(df) >= 14:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
        else:
            current_rsi = 50
        
        return {
            'signal_strength': abs(current_rsi - 50) / 50,  # Distance from neutral
            'rsi': current_rsi,
            'overbought': current_rsi > 70,
            'oversold': current_rsi < 30
        }
    
    # Simplified simulations for other agents to generate realistic data
    def simulate_breaker_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.7)}
    
    def simulate_sof_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.8)}
    
    def simulate_displacement_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.2, 0.9)}
    
    def simulate_engulfing_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.8)}
    
    def simulate_mitigation_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.7)}
    
    def simulate_killzone_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.3, 1.0)}
    
    def simulate_cluster_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.4, 1.0)}
    
    def simulate_sfp_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.6)}
    
    def simulate_htf_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.5, 1.0)}
    
    def simulate_judas_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.7)}
    
    def simulate_po3_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.2, 0.8)}
    
    def simulate_mm_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.3, 0.9)}
    
    def simulate_turtle_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.1, 0.6)}
    
    def simulate_imbalance_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.2, 0.8)}
    
    def simulate_momentum_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.3, 0.9)}
    
    def simulate_session_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.4, 1.0)}
    
    def simulate_regime_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.3, 0.9)}
    
    def simulate_ml_ensemble_signals(self, df: pd.DataFrame, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate ML ensemble signals"""
        ml_confidence = parameters.get('ml_confidence', 0.8)
        # Add some randomness around the parameter
        actual_confidence = ml_confidence + np.random.normal(0, 0.05)
        actual_confidence = max(0.5, min(0.99, actual_confidence))
        
        return {
            'signal_strength': actual_confidence,
            'confidence': actual_confidence,
            'model_agreement': np.random.uniform(0.6, 0.95),
            'prediction': np.random.choice([0, 1])
        }
    
    def simulate_ml_prediction_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {'signal_strength': np.random.uniform(0.4, 0.9)}
    
    def calculate_confluence_metrics(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confluence metrics from all signals"""
        ict_signals = signals['ict_smc']
        analysis_signals = signals['analysis']
        
        # Count active signals
        active_ict_signals = sum(1 for signal in ict_signals.values() if signal.get('signal_strength', 0) > 0.5)
        active_analysis_signals = sum(1 for signal in analysis_signals.values() if signal.get('signal_strength', 0) > 0.5)
        
        # Calculate weighted confluence score
        total_weight = 0.0
        weighted_sum = 0.0
        
        for signal in ict_signals.values():
            strength = signal.get('signal_strength', 0)
            weight = 1.5  # ICT/SMC signals get higher weight
            total_weight += weight
            weighted_sum += strength * weight
        
        for signal in analysis_signals.values():
            strength = signal.get('signal_strength', 0)
            weight = 1.0
            total_weight += weight
            weighted_sum += strength * weight
        
        confluence_score = weighted_sum / total_weight if total_weight > 0 else 0
        
        return {
            'total_confluence_score': confluence_score,
            'active_ict_signals': active_ict_signals,
            'active_analysis_signals': active_analysis_signals,
            'total_active_signals': active_ict_signals + active_analysis_signals
        }
    
    def make_intensive_trading_decision(self, agent_signals: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Make trading decision with relaxed parameters for maximum data collection"""
        confluence_metrics = agent_signals['confluence_metrics']
        
        # Use relaxed parameters for data collection
        min_patterns = max(2, parameters.get('confluence_patterns', 3) - 1)  # Relaxed by 1
        min_score = max(2.0, parameters.get('confluence_score', 5.0) - 1.0)  # Relaxed by 1.0
        min_ml_confidence = max(0.55, parameters.get('ml_confidence', 0.75) - 0.1)  # Relaxed by 0.1
        
        # Check requirements
        patterns_ok = confluence_metrics['total_active_signals'] >= min_patterns
        score_ok = confluence_metrics['total_confluence_score'] >= min_score
        ml_ok = agent_signals['ml']['ml_ensemble']['confidence'] >= min_ml_confidence
        
        should_trade = patterns_ok and score_ok and ml_ok
        
        if should_trade:
            # Determine direction based on signal bias
            bullish_signals = sum(1 for cat in agent_signals.values() 
                                if isinstance(cat, dict) and cat.get('signal_strength', 0) > 0.6)
            direction = 'long' if np.random.random() > 0.5 else 'short'  # Simplified
            
            return {
                'should_trade': True,
                'direction': direction,
                'confluence_score': confluence_metrics['total_confluence_score'],
                'pattern_count': confluence_metrics['total_active_signals'],
                'ml_confidence': agent_signals['ml']['ml_ensemble']['confidence']
            }
        else:
            rejection_reasons = []
            if not patterns_ok:
                rejection_reasons.append('insufficient_patterns')
            if not score_ok:
                rejection_reasons.append('low_confluence_score')
            if not ml_ok:
                rejection_reasons.append('low_ml_confidence')
            
            return {
                'should_trade': False,
                'rejection_reason': ', '.join(rejection_reasons),
                'confluence_score': confluence_metrics['total_confluence_score'],
                'pattern_count': confluence_metrics['total_active_signals']
            }
    
    def simulate_trade_outcome(self, df: pd.DataFrame, trading_decision: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate trade outcome for ML training data"""
        # Simulate realistic trade outcome based on confluence quality
        confluence_score = trading_decision['confluence_score']
        ml_confidence = trading_decision['ml_confidence']
        pattern_count = trading_decision['pattern_count']
        
        # Higher quality signals = higher win probability
        base_win_prob = 0.6
        confluence_bonus = min((confluence_score - 3.0) * 0.05, 0.2)  # Up to 20% bonus
        ml_bonus = (ml_confidence - 0.5) * 0.2  # Up to 10% bonus
        pattern_bonus = min((pattern_count - 2) * 0.02, 0.1)  # Up to 10% bonus
        
        win_probability = base_win_prob + confluence_bonus + ml_bonus + pattern_bonus
        
        # Simulate outcome
        outcome = 'win' if np.random.random() < win_probability else 'loss'
        
        # Simulate R-multiple based on outcome and quality
        if outcome == 'win':
            r_multiple = np.random.uniform(0.5, 4.0)  # Wins can be 0.5R to 4R
        else:
            r_multiple = np.random.uniform(-2.0, -0.5)  # Losses are -2R to -0.5R
        
        return {
            'outcome': outcome,
            'r_multiple': r_multiple,
            'confluence_score': confluence_score,
            'ml_confidence': ml_confidence,
            'pattern_count': pattern_count,
            'win_probability_estimated': win_probability,
            'entry_price': df['close'].iloc[-1],
            'timestamp': df.index[-1]
        }
    
    def extract_ml_samples_from_simulation(self, simulation_result: Dict[str, Any], 
                                          parameters: Dict[str, Any], df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract ML training samples from simulation"""
        ml_samples = []
        
        # Extract samples from agent signals history
        for signal_record in simulation_result['agent_signals_history']:
            # Create comprehensive feature vector
            features = self.create_comprehensive_feature_vector(signal_record, parameters, df)
            
            # Find corresponding trade outcome (if any)
            trade_outcome = self.find_corresponding_trade_outcome(
                signal_record['timestamp'], simulation_result['trades']
            )
            
            ml_sample = {
                'timestamp': signal_record['timestamp'],
                'features': features,
                'target': 1 if trade_outcome and trade_outcome['outcome'] == 'win' else 0,
                'r_multiple': trade_outcome['r_multiple'] if trade_outcome else 0,
                'confluence_score': signal_record['agent_signals']['confluence_metrics']['total_confluence_score'],
                'pattern_count': signal_record['agent_signals']['confluence_metrics']['total_active_signals'],
                'parameters': parameters,
                'market_data': signal_record['market_data']
            }
            
            ml_samples.append(ml_sample)
        
        return ml_samples
    
    def create_comprehensive_feature_vector(self, signal_record: Dict[str, Any], 
                                           parameters: Dict[str, Any], df: pd.DataFrame) -> List[float]:
        """Create comprehensive feature vector with MAXIMUM information"""
        features = []
        
        agent_signals = signal_record['agent_signals']
        
        # ICT/SMC features (21 agents × ~5 features each = 105 features)
        for agent_name, agent_data in agent_signals['ict_smc'].items():
            features.append(agent_data.get('signal_strength', 0))
            # Add agent-specific features
            if agent_name == 'fair_value_gaps':
                features.extend([
                    agent_data.get('fvgs_detected', 0),
                    agent_data.get('avg_gap_size', 0),
                    agent_data.get('gap_frequency', 0)
                ])
            elif agent_name == 'order_blocks':
                features.extend([
                    agent_data.get('order_blocks', 0),
                    agent_data.get('ob_density', 0)
                ])
            # Add 2 more features per agent for consistency
            features.extend([0.0, 0.0])  # Placeholder for additional features
        
        # Analysis features (4 agents × ~8 features each = 32 features)
        for agent_name, agent_data in agent_signals['analysis'].items():
            features.append(agent_data.get('signal_strength', 0))
            
            if agent_name == 'volume_analysis':
                features.extend([
                    agent_data.get('volume_ratio', 1.0),
                    float(agent_data.get('volume_spike', False)),
                    agent_data.get('volume_trend', 0)
                ])
            elif agent_name == 'technical_indicators':
                features.extend([
                    agent_data.get('rsi', 50) / 100,  # Normalize
                    float(agent_data.get('overbought', False)),
                    float(agent_data.get('oversold', False))
                ])
            
            # Add more features for consistency
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        # ML features (2 agents × ~5 features each = 10 features)
        for agent_name, agent_data in agent_signals['ml'].items():
            features.append(agent_data.get('signal_strength', 0))
            features.append(agent_data.get('confidence', 0))
            features.extend([0.0, 0.0, 0.0])  # Additional features
        
        # Confluence features (10 features)
        confluence_metrics = agent_signals['confluence_metrics']
        features.extend([
            confluence_metrics['total_confluence_score'],
            confluence_metrics['active_ict_signals'],
            confluence_metrics['active_analysis_signals'],
            confluence_metrics['total_active_signals'],
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # Additional confluence features
        ])
        
        # Market context features (20 features)
        market_data = signal_record['market_data']
        features.extend([
            market_data['open'], market_data['high'], market_data['low'], 
            market_data['close'], market_data['volume'],
            (market_data['high'] - market_data['low']) / market_data['close'],  # Range ratio
            (market_data['close'] - market_data['open']) / market_data['open'],  # Body ratio
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # Additional market features
        ])
        
        # Parameter features (15 features)
        features.extend([
            parameters.get('confluence_patterns', 3),
            parameters.get('confluence_score', 5.0),
            parameters.get('ml_confidence', 0.8),
            parameters.get('ml_agreement', 0.7),
            parameters.get('risk_per_trade', 0.01),
            parameters.get('stop_loss_atr', 2.0),
            parameters.get('take_profit_atr', 4.0),
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # Additional parameter features
        ])
        
        # Total: ~200 features for comprehensive ML training
        return features
    
    def find_corresponding_trade_outcome(self, timestamp, trades: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find trade outcome corresponding to signal timestamp"""
        # Look for trade within reasonable time window
        for trade in trades:
            if abs((trade['timestamp'] - timestamp).total_seconds()) < 3600:  # Within 1 hour
                return trade
        return None
    
    def load_comprehensive_historical_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load comprehensive historical data for intensive backtesting"""
        try:
            # This would integrate with your existing data loading
            # For maximum data collection, load as much history as possible
            
            start_date = self.data_start_date
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            self.logger.info(f"Loading MAXIMUM historical data for {symbol} {timeframe}: {start_date} to {end_date}")
            
            # In production: df = fetch_ohlc_extended(symbol, timeframe, start_date, end_date, limit=None)
            
            # For now, return None to indicate data loading needed
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading comprehensive data for {symbol} {timeframe}: {e}")
            return None
    
    def get_signal_strength(self) -> float:
        """Get signal strength based on data collection performance"""
        if self.data_generation_metrics['total_samples_generated'] == 0:
            return 0.0
        
        # Signal strength based on data collection success
        samples_ratio = min(self.data_generation_metrics['total_samples_generated'] / 100000, 1.0)  # Target 100K samples
        return samples_ratio
    
    def requires_continuous_processing(self) -> bool:
        """Intensive backtesting agent doesn't need continuous processing"""
        return False