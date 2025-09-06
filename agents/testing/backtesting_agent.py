"""
Backtesting Agent
Comprehensive backtesting system for 50-year historical data validation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone, timedelta
import concurrent.futures
import threading

from agents.base_agent import BaseAgent


class BacktestingAgent(BaseAgent):
    """
    Advanced Backtesting Agent for 50-year historical validation
    Critical for validating >90% win rate claims with extensive data
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("backtesting", config)
        
        # Backtesting configuration
        self.backtest_start_date = config.get('backtest_start_date', '1975-01-01')  # 50 years
        self.backtest_end_date = config.get('backtest_end_date', '2025-01-01')
        self.timeframes = config.get('timeframes', ['1h', '4h', '1d'])
        self.initial_balance = config.get('initial_balance', 100000)
        self.max_parallel_tests = config.get('max_parallel_tests', 4)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Backtesting data
        self.backtest_results = {}
        self.walk_forward_results = []
        self.parameter_optimization_results = {}
        self.regime_performance = {}
        
        # Historical data cache
        self.historical_data_cache = {}
        
        # Performance metrics
        self.comprehensive_metrics = {}
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Backtesting Agent initialized for {self.market_type} - 50-year validation capability")
    
    def apply_market_specific_config(self):
        """Apply market-specific backtesting configuration"""
        if self.market_type == 'forex':
            # Forex: Full 50-year data available
            self.symbols_to_test = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD']
            self.data_availability_start = '1975-01-01'
            self.session_aware_testing = True
        elif self.market_type == 'crypto':
            # Crypto: Limited to available history (2009+ for BTC)
            self.symbols_to_test = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
            self.data_availability_start = '2009-01-01'  # Bitcoin start
            self.volatility_aware_testing = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process backtesting requests and data
        
        Args:
            data: Dictionary containing backtest configuration
            
        Returns:
            Dictionary with backtesting results
        """
        try:
            action = data.get('action', 'run_backtest')
            
            if action == 'run_backtest':
                return self.run_comprehensive_backtest(data)
            elif action == 'walk_forward_analysis':
                return self.run_walk_forward_analysis(data)
            elif action == 'parameter_optimization':
                return self.run_parameter_optimization(data)
            elif action == 'regime_analysis':
                return self.analyze_regime_performance(data)
            elif action == 'get_results':
                return self.get_backtest_results(data)
            else:
                return {'error': f'Unknown backtesting action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error processing backtesting data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def run_comprehensive_backtest(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive backtest with 50-year data
        """
        symbols = data.get('symbols', self.symbols_to_test)
        timeframes = data.get('timeframes', self.timeframes)
        start_date = data.get('start_date', self.backtest_start_date)
        end_date = data.get('end_date', self.backtest_end_date)
        
        self.logger.info(f"Starting comprehensive backtest: {len(symbols)} symbols, {len(timeframes)} timeframes, {start_date} to {end_date}")
        
        backtest_results = {}
        
        # Run backtest for each symbol-timeframe combination
        for symbol in symbols:
            backtest_results[symbol] = {}
            
            for timeframe in timeframes:
                self.logger.info(f"Backtesting {symbol} {timeframe}...")
                
                try:
                    # Load historical data
                    historical_data = self.load_historical_data(symbol, timeframe, start_date, end_date)
                    
                    if historical_data is None or historical_data.empty:
                        self.logger.warning(f"No data available for {symbol} {timeframe}")
                        continue
                    
                    # Run backtest simulation
                    backtest_result = self.simulate_trading(historical_data, symbol, timeframe)
                    
                    # Calculate comprehensive metrics
                    performance_metrics = self.calculate_comprehensive_metrics(backtest_result, historical_data)
                    
                    backtest_results[symbol][timeframe] = {
                        'backtest_result': backtest_result,
                        'performance_metrics': performance_metrics,
                        'data_points': len(historical_data),
                        'date_range': {
                            'start': historical_data.index[0].isoformat(),
                            'end': historical_data.index[-1].isoformat()
                        }
                    }
                    
                    self.logger.info(f"Completed {symbol} {timeframe}: Win Rate {performance_metrics['win_rate']:.1%}, "
                                   f"Total Return {performance_metrics['total_return']:.1%}")
                
                except Exception as e:
                    self.logger.error(f"Error backtesting {symbol} {timeframe}: {e}")
                    backtest_results[symbol][timeframe] = {'error': str(e)}
        
        # Store results
        self.backtest_results = backtest_results
        
        # Generate summary
        summary = self.generate_backtest_summary(backtest_results)
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'backtest_completed': True,
            'symbols_tested': len(symbols),
            'timeframes_tested': len(timeframes),
            'backtest_results': backtest_results,
            'summary': summary,
            'market_type': self.market_type
        }
    
    def load_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Load comprehensive historical data for backtesting
        """
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        
        # Check cache first
        if cache_key in self.historical_data_cache:
            return self.historical_data_cache[cache_key]
        
        try:
            # This would integrate with your existing data fetching
            # For now, simulate data loading
            self.logger.info(f"Loading historical data for {symbol} {timeframe} from {start_date} to {end_date}")
            
            # In production, this would use your fetch_ohlc function with extended date range
            # df = fetch_ohlc_historical(symbol, timeframe, start_date, end_date)
            
            # For now, return None to indicate data loading needed
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading historical data for {symbol} {timeframe}: {e}")
            return None
    
    def simulate_trading(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Simulate trading using the complete agent system
        """
        simulation_result = {
            'trades': [],
            'equity_curve': [],
            'drawdown_curve': [],
            'trade_statistics': {},
            'agent_performance': {}
        }
        
        # Initialize simulation state
        balance = self.initial_balance
        position = None
        trade_count = 0
        
        # Simulate bar-by-bar
        for i in range(100, len(df)):  # Start after enough data for indicators
            try:
                # Get current bar data
                current_data = df.iloc[:i+1]
                current_bar = df.iloc[i]
                
                # Simulate agent analysis (simplified for backtesting)
                agent_signals = self.simulate_agent_signals(current_data, symbol)
                
                # Check for entry signals
                if position is None:  # No open position
                    entry_signal = self.check_entry_signals(agent_signals, current_bar)
                    
                    if entry_signal['should_enter']:
                        # Open position
                        position = {
                            'symbol': symbol,
                            'direction': entry_signal['direction'],
                            'entry_price': current_bar['close'],
                            'entry_time': current_bar.name,
                            'stop_loss': entry_signal['stop_loss'],
                            'take_profit_levels': entry_signal['take_profit_levels'],
                            'confluence_score': agent_signals.get('confluence_score', 0),
                            'ml_confidence': agent_signals.get('ml_confidence', 0)
                        }
                        
                        self.logger.debug(f"Position opened: {symbol} {entry_signal['direction']} at {current_bar['close']}")
                
                else:  # Open position exists
                    # Check for exit signals
                    exit_signal = self.check_exit_signals(position, current_bar, agent_signals)
                    
                    if exit_signal['should_exit']:
                        # Close position
                        trade_result = self.close_position(position, current_bar, exit_signal)
                        simulation_result['trades'].append(trade_result)
                        
                        # Update balance
                        balance += trade_result['pnl']
                        
                        # Reset position
                        position = None
                        trade_count += 1
                        
                        self.logger.debug(f"Position closed: {trade_result['outcome']} PnL: {trade_result['pnl']:.2f}")
                
                # Record equity curve
                unrealized_pnl = self.calculate_unrealized_pnl(position, current_bar) if position else 0
                current_equity = balance + unrealized_pnl
                
                simulation_result['equity_curve'].append({
                    'timestamp': current_bar.name,
                    'equity': current_equity,
                    'balance': balance,
                    'unrealized_pnl': unrealized_pnl
                })
                
            except Exception as e:
                self.logger.error(f"Error in simulation at bar {i}: {e}")
                continue
        
        # Close any remaining position
        if position:
            final_bar = df.iloc[-1]
            final_trade = self.close_position(position, final_bar, {'exit_type': 'end_of_data'})
            simulation_result['trades'].append(final_trade)
        
        return simulation_result
    
    def simulate_agent_signals(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Simulate agent signals for backtesting (simplified)
        """
        # This is a simplified simulation of agent signals
        # In production, this would run actual agents
        
        # Simulate confluence score
        confluence_score = np.random.uniform(2, 12)  # Random for simulation
        
        # Simulate ML confidence
        ml_confidence = np.random.uniform(0.5, 0.98)
        
        # Simulate pattern detection
        patterns_detected = np.random.randint(1, 8)
        
        return {
            'confluence_score': confluence_score,
            'ml_confidence': ml_confidence,
            'patterns_detected': patterns_detected,
            'signal_strength': np.random.uniform(0.3, 0.9)
        }
    
    def check_entry_signals(self, agent_signals: Dict[str, Any], current_bar: pd.Series) -> Dict[str, Any]:
        """Check for entry signals based on current settings"""
        # Apply current frequency optimizer settings
        min_patterns = self.current_settings.get('confluence_coordinator', {}).get('min_confluence_patterns', 3)
        min_score = self.current_settings.get('confluence_coordinator', {}).get('min_confluence_score', 5.0)
        ml_threshold = self.current_settings.get('ml_ensemble', {}).get('confidence_threshold', 0.8)
        
        # Check if signals meet current requirements
        patterns_ok = agent_signals.get('patterns_detected', 0) >= min_patterns
        score_ok = agent_signals.get('confluence_score', 0) >= min_score
        ml_ok = agent_signals.get('ml_confidence', 0) >= ml_threshold
        
        should_enter = patterns_ok and score_ok and ml_ok
        
        if should_enter:
            # Determine direction (simplified)
            direction = 'long' if np.random.random() > 0.5 else 'short'
            
            # Calculate stop loss and take profit
            atr = current_bar.get('atr', current_bar['close'] * 0.02)  # 2% if no ATR
            
            if direction == 'long':
                stop_loss = current_bar['close'] - (2 * atr)
                take_profit_levels = [
                    current_bar['close'] + (1 * atr),
                    current_bar['close'] + (2 * atr),
                    current_bar['close'] + (4 * atr)
                ]
            else:
                stop_loss = current_bar['close'] + (2 * atr)
                take_profit_levels = [
                    current_bar['close'] - (1 * atr),
                    current_bar['close'] - (2 * atr),
                    current_bar['close'] - (4 * atr)
                ]
            
            return {
                'should_enter': True,
                'direction': direction,
                'stop_loss': stop_loss,
                'take_profit_levels': take_profit_levels,
                'confluence_score': agent_signals['confluence_score'],
                'ml_confidence': agent_signals['ml_confidence']
            }
        
        return {'should_enter': False}
    
    def check_exit_signals(self, position: Dict[str, Any], current_bar: pd.Series, 
                          agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Check for exit signals"""
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        direction = position['direction']
        current_price = current_bar['close']
        
        # Check stop loss
        if direction == 'long' and current_price <= stop_loss:
            return {'should_exit': True, 'exit_type': 'stop_loss', 'exit_price': stop_loss}
        elif direction == 'short' and current_price >= stop_loss:
            return {'should_exit': True, 'exit_type': 'stop_loss', 'exit_price': stop_loss}
        
        # Check take profit levels
        for i, tp_level in enumerate(position['take_profit_levels']):
            if direction == 'long' and current_price >= tp_level:
                return {'should_exit': True, 'exit_type': f'take_profit_{i+1}', 'exit_price': tp_level}
            elif direction == 'short' and current_price <= tp_level:
                return {'should_exit': True, 'exit_type': f'take_profit_{i+1}', 'exit_price': tp_level}
        
        return {'should_exit': False}
    
    def close_position(self, position: Dict[str, Any], current_bar: pd.Series, exit_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Close position and calculate trade result"""
        entry_price = position['entry_price']
        exit_price = exit_signal.get('exit_price', current_bar['close'])
        direction = position['direction']
        
        # Calculate PnL
        if direction == 'long':
            pnl = exit_price - entry_price
        else:
            pnl = entry_price - exit_price
        
        # Calculate R-multiple
        risk = abs(entry_price - position['stop_loss'])
        r_multiple = pnl / risk if risk > 0 else 0
        
        # Determine outcome
        outcome = 'win' if pnl > 0 else 'loss'
        
        return {
            'symbol': position['symbol'],
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_time': position['entry_time'],
            'exit_time': current_bar.name,
            'pnl': pnl,
            'r_multiple': r_multiple,
            'outcome': outcome,
            'exit_type': exit_signal.get('exit_type', 'unknown'),
            'confluence_score': position.get('confluence_score', 0),
            'ml_confidence': position.get('ml_confidence', 0)
        }
    
    def calculate_unrealized_pnl(self, position: Dict[str, Any], current_bar: pd.Series) -> float:
        """Calculate unrealized PnL for open position"""
        if not position:
            return 0.0
        
        entry_price = position['entry_price']
        current_price = current_bar['close']
        direction = position['direction']
        
        if direction == 'long':
            return current_price - entry_price
        else:
            return entry_price - current_price
    
    def calculate_comprehensive_metrics(self, backtest_result: Dict[str, Any], historical_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate comprehensive backtesting metrics
        """
        trades = backtest_result['trades']
        equity_curve = backtest_result['equity_curve']
        
        if not trades:
            return {'error': 'No trades in backtest'}
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade['outcome'] == 'win')
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # PnL metrics
        total_pnl = sum(trade['pnl'] for trade in trades)
        avg_win = np.mean([trade['pnl'] for trade in trades if trade['outcome'] == 'win']) if winning_trades > 0 else 0
        avg_loss = np.mean([trade['pnl'] for trade in trades if trade['outcome'] == 'loss']) if losing_trades > 0 else 0
        
        # R-multiple metrics
        r_multiples = [trade['r_multiple'] for trade in trades]
        avg_r_multiple = np.mean(r_multiples)
        
        # Equity curve metrics
        if equity_curve:
            equity_values = [point['equity'] for point in equity_curve]
            initial_equity = equity_values[0]
            final_equity = equity_values[-1]
            total_return = (final_equity - initial_equity) / initial_equity
            
            # Drawdown calculation
            running_max = np.maximum.accumulate(equity_values)
            drawdown = (equity_values - running_max) / running_max
            max_drawdown = abs(np.min(drawdown))
            
            # Sharpe ratio (simplified)
            returns = pd.Series(equity_values).pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            total_return = 0
            max_drawdown = 0
            sharpe_ratio = 0
        
        # Advanced metrics
        profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss < 0 and losing_trades > 0 else float('inf')
        
        # Frequency metrics
        if len(historical_data) > 0:
            days_tested = (historical_data.index[-1] - historical_data.index[0]).days
            trades_per_day = total_trades / days_tested if days_tested > 0 else 0
        else:
            trades_per_day = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_r_multiple': avg_r_multiple,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'trades_per_day': trades_per_day,
            'meets_win_rate_target': win_rate >= 0.85,  # Realistic target
            'meets_frequency_target': trades_per_day >= self.min_trades_per_day / 7,  # Weekly average
            'balance_score': self.calculate_backtest_balance_score(win_rate, trades_per_day)
        }
    
    def calculate_backtest_balance_score(self, win_rate: float, trades_per_day: float) -> float:
        """Calculate balance score between win rate and frequency"""
        # Normalize scores
        win_rate_score = min(win_rate / 0.85, 1.0)  # Target 85%
        frequency_score = min(trades_per_day / (self.min_trades_per_day / 7), 1.0)  # Target min frequency
        
        # Balanced score (both are important)
        return (win_rate_score * 0.6 + frequency_score * 0.4)
    
    def run_walk_forward_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run walk-forward analysis for robust validation
        """
        symbol = data.get('symbol', 'BTC/USDT')
        timeframe = data.get('timeframe', '1h')
        walk_forward_periods = data.get('periods', 12)  # 12 periods
        
        self.logger.info(f"Starting walk-forward analysis: {symbol} {timeframe} with {walk_forward_periods} periods")
        
        # Load full dataset
        full_data = self.load_historical_data(symbol, timeframe, self.backtest_start_date, self.backtest_end_date)
        
        if full_data is None or len(full_data) < 1000:
            return {'error': 'Insufficient data for walk-forward analysis'}
        
        # Split data into periods
        period_size = len(full_data) // walk_forward_periods
        walk_forward_results = []
        
        for period in range(walk_forward_periods):
            start_idx = period * period_size
            end_idx = min((period + 1) * period_size, len(full_data))
            
            period_data = full_data.iloc[start_idx:end_idx]
            
            # Run backtest on this period
            period_result = self.simulate_trading(period_data, symbol, timeframe)
            period_metrics = self.calculate_comprehensive_metrics(period_result, period_data)
            
            walk_forward_results.append({
                'period': period + 1,
                'start_date': period_data.index[0].isoformat(),
                'end_date': period_data.index[-1].isoformat(),
                'metrics': period_metrics,
                'data_points': len(period_data)
            })
            
            self.logger.info(f"Period {period + 1}: Win Rate {period_metrics['win_rate']:.1%}, "
                           f"Trades/Day {period_metrics['trades_per_day']:.2f}")
        
        # Calculate walk-forward summary
        wf_summary = self.calculate_walk_forward_summary(walk_forward_results)
        
        return {
            'agent_id': self.agent_id,
            'walk_forward_completed': True,
            'periods_tested': walk_forward_periods,
            'walk_forward_results': walk_forward_results,
            'walk_forward_summary': wf_summary,
            'symbol': symbol,
            'timeframe': timeframe
        }
    
    def calculate_walk_forward_summary(self, wf_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate walk-forward analysis summary"""
        if not wf_results:
            return {}
        
        # Extract metrics from all periods
        win_rates = [period['metrics']['win_rate'] for period in wf_results if 'error' not in period['metrics']]
        trades_per_day = [period['metrics']['trades_per_day'] for period in wf_results if 'error' not in period['metrics']]
        total_returns = [period['metrics']['total_return'] for period in wf_results if 'error' not in period['metrics']]
        balance_scores = [period['metrics']['balance_score'] for period in wf_results if 'error' not in period['metrics']]
        
        if not win_rates:
            return {'error': 'No valid periods'}
        
        return {
            'avg_win_rate': np.mean(win_rates),
            'win_rate_std': np.std(win_rates),
            'min_win_rate': np.min(win_rates),
            'max_win_rate': np.max(win_rates),
            'avg_trades_per_day': np.mean(trades_per_day),
            'trades_per_day_std': np.std(trades_per_day),
            'avg_total_return': np.mean(total_returns),
            'avg_balance_score': np.mean(balance_scores),
            'consistent_performance': np.std(win_rates) < 0.1,  # Low std = consistent
            'meets_frequency_target': np.mean(trades_per_day) >= self.min_trades_per_day / 7,
            'meets_win_rate_target': np.mean(win_rates) >= 0.8,  # 80% average target
            'robust_system': np.mean(balance_scores) >= 0.7
        }
    
    def generate_backtest_summary(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive backtest summary"""
        all_metrics = []
        
        # Collect all metrics
        for symbol, symbol_results in backtest_results.items():
            for timeframe, tf_results in symbol_results.items():
                if 'performance_metrics' in tf_results:
                    metrics = tf_results['performance_metrics']
                    metrics['symbol'] = symbol
                    metrics['timeframe'] = timeframe
                    all_metrics.append(metrics)
        
        if not all_metrics:
            return {'error': 'No valid backtest results'}
        
        # Calculate aggregate metrics
        avg_win_rate = np.mean([m['win_rate'] for m in all_metrics])
        avg_trades_per_day = np.mean([m['trades_per_day'] for m in all_metrics])
        avg_balance_score = np.mean([m['balance_score'] for m in all_metrics])
        
        # Count successful configurations
        successful_configs = sum(1 for m in all_metrics if m['meets_win_rate_target'] and m['meets_frequency_target'])
        total_configs = len(all_metrics)
        
        return {
            'total_configurations_tested': total_configs,
            'successful_configurations': successful_configs,
            'success_rate': successful_configs / total_configs if total_configs > 0 else 0,
            'average_win_rate': avg_win_rate,
            'average_trades_per_day': avg_trades_per_day,
            'average_balance_score': avg_balance_score,
            'system_validation': 'passed' if avg_balance_score >= 0.7 else 'failed',
            'frequency_adequacy': 'adequate' if avg_trades_per_day >= self.min_trades_per_day / 7 else 'inadequate',
            'win_rate_achievement': 'target_met' if avg_win_rate >= 0.8 else 'below_target'
        }
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on backtesting results"""
        if not self.backtest_results:
            return 0.0
        
        # Signal strength based on backtesting validation
        balance_score = self.balance_metrics.get('balance_score', 0.0)
        return balance_score
    
    def requires_continuous_processing(self) -> bool:
        """Backtesting agent doesn't need continuous processing"""
        return False