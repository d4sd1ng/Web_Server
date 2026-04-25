"""
Exit Strategy Agent
Advanced exit management for >90% win rate optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class ExitStrategyAgent(BaseAgent):
    """
    Advanced Exit Strategy Agent
    Sophisticated profit-taking and risk management for >90% win rate
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("exit_strategy", config)
        
        # Exit strategy configuration
        self.profit_taking_levels = config.get('profit_taking_levels', [0.5, 0.75, 1.0, 1.5, 2.0])  # R multiples
        self.trailing_stop_activation = config.get('trailing_stop_activation', 1.0)  # 1R
        self.partial_exit_percentages = config.get('partial_exit_percentages', [25, 25, 25, 25])  # 4 exits
        self.breakeven_activation = config.get('breakeven_activation', 0.5)  # 0.5R
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Exit tracking
        self.active_exits = {}
        self.exit_history = []
        self.exit_performance = {'profitable_exits': 0, 'total_exits': 0, 'avg_r_multiple': 0.0}
        
        # Advanced exit strategies
        self.exit_strategies = self.load_exit_strategies()
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Exit Strategy Agent initialized for {self.market_type} market")
    
    def load_exit_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load sophisticated exit strategies for >90% win rate"""
        return {
            'trend_following': {
                'description': 'Trend-following exits with trailing stops',
                'profit_levels': [0.5, 1.0, 2.0, 3.0],
                'exit_percentages': [20, 30, 30, 20],
                'trailing_activation': 1.0,
                'trailing_distance': 0.5
            },
            'mean_reversion': {
                'description': 'Quick profit-taking for range-bound markets',
                'profit_levels': [0.5, 0.75, 1.0],
                'exit_percentages': [40, 40, 20],
                'trailing_activation': 0.75,
                'trailing_distance': 0.3
            },
            'breakout': {
                'description': 'Breakout exits with extended targets',
                'profit_levels': [1.0, 2.0, 3.0, 5.0],
                'exit_percentages': [15, 25, 35, 25],
                'trailing_activation': 2.0,
                'trailing_distance': 1.0
            },
            'scalping': {
                'description': 'Quick scalping exits',
                'profit_levels': [0.25, 0.5, 0.75],
                'exit_percentages': [50, 30, 20],
                'trailing_activation': 0.5,
                'trailing_distance': 0.2
            },
            'swing': {
                'description': 'Swing trading exits with patience',
                'profit_levels': [1.0, 2.0, 4.0, 6.0],
                'exit_percentages': [20, 25, 30, 25],
                'trailing_activation': 2.0,
                'trailing_distance': 1.0
            }
        }
    
    def apply_market_specific_config(self):
        """Apply market-specific exit configuration"""
        if self.market_type == 'forex':
            # Forex: Tighter exits due to lower volatility
            self.profit_taking_levels = [0.5, 0.75, 1.0, 1.5]  # Shorter targets
            self.trailing_stop_activation = 0.75
            self.session_exit_rules = True
            self.news_exit_protection = True
        elif self.market_type == 'crypto':
            # Crypto: Wider exits due to higher volatility
            self.profit_taking_levels = [0.75, 1.5, 2.5, 4.0]  # Longer targets
            self.trailing_stop_activation = 1.0
            self.session_exit_rules = False
            self.volatility_exit_protection = True
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process trade data for exit strategy management
        
        Args:
            data: Dictionary containing trade information and market data
            
        Returns:
            Dictionary with exit strategy results
        """
        try:
            action = data.get('action', 'monitor')
            
            if action == 'create_exit_plan':
                return self.create_exit_plan(data)
            elif action == 'monitor_exits':
                return self.monitor_active_exits(data)
            elif action == 'execute_exit':
                return self.execute_exit(data)
            elif action == 'update_strategy':
                return self.update_exit_strategy(data)
            else:
                return self.get_exit_status()
                
        except Exception as e:
            self.logger.error(f"Error processing exit strategy data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def create_exit_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create sophisticated exit plan for new trade
        """
        required_fields = ['trade_id', 'symbol', 'direction', 'entry_price', 'stop_loss', 'strategy_type']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for exit plan'}
        
        trade_id = data['trade_id']
        symbol = data['symbol']
        direction = data['direction']
        entry_price = data['entry_price']
        stop_loss = data['stop_loss']
        strategy_type = data.get('strategy_type', 'swing')
        
        # Calculate R-value (risk amount)
        r_value = abs(entry_price - stop_loss)
        
        # Select exit strategy
        exit_strategy = self.exit_strategies.get(strategy_type, self.exit_strategies['swing'])
        
        # Create exit levels
        exit_plan = self.calculate_exit_levels(entry_price, r_value, direction, exit_strategy)
        
        # Add market-specific adjustments
        exit_plan = self.apply_market_exit_adjustments(exit_plan, data)
        
        # Create exit management structure
        exit_management = {
            'trade_id': trade_id,
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'r_value': r_value,
            'strategy_type': strategy_type,
            'exit_plan': exit_plan,
            'created_at': datetime.now(timezone.utc),
            'status': 'active',
            'exits_executed': 0,
            'remaining_position': 100.0,  # Percentage
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
            'max_favorable_excursion': 0.0,
            'max_adverse_excursion': 0.0
        }
        
        # Store active exit plan
        self.active_exits[trade_id] = exit_management
        
        self.logger.info(f"Exit plan created for {trade_id}: {len(exit_plan['levels'])} levels, {strategy_type} strategy")
        
        return {
            'success': True,
            'trade_id': trade_id,
            'exit_plan': exit_plan,
            'exit_levels_count': len(exit_plan['levels']),
            'strategy_type': strategy_type,
            'expected_max_profit': exit_plan['levels'][-1]['target_price'] if exit_plan['levels'] else 0
        }
    
    def calculate_exit_levels(self, entry_price: float, r_value: float, direction: str, 
                            exit_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate sophisticated exit levels
        """
        profit_levels = exit_strategy['profit_levels']
        exit_percentages = exit_strategy['exit_percentages']
        
        exit_levels = []
        
        for i, (r_multiple, exit_percentage) in enumerate(zip(profit_levels, exit_percentages)):
            if direction == 'long':
                target_price = entry_price + (r_value * r_multiple)
            else:  # short
                target_price = entry_price - (r_value * r_multiple)
            
            exit_level = {
                'level': i + 1,
                'r_multiple': r_multiple,
                'target_price': target_price,
                'exit_percentage': exit_percentage,
                'status': 'pending',
                'executed_at': None,
                'execution_price': None
            }
            exit_levels.append(exit_level)
        
        # Trailing stop configuration
        trailing_config = {
            'activation_r': exit_strategy['trailing_activation'],
            'trailing_distance_r': exit_strategy['trailing_distance'],
            'activation_price': entry_price + (r_value * exit_strategy['trailing_activation']) if direction == 'long' 
                              else entry_price - (r_value * exit_strategy['trailing_activation']),
            'current_trail_price': None,
            'active': False
        }
        
        return {
            'levels': exit_levels,
            'trailing_stop': trailing_config,
            'breakeven_move': {
                'activation_r': self.breakeven_activation,
                'activation_price': entry_price + (r_value * self.breakeven_activation) if direction == 'long'
                                  else entry_price - (r_value * self.breakeven_activation),
                'executed': False
            }
        }
    
    def apply_market_exit_adjustments(self, exit_plan: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply market-specific exit adjustments"""
        if self.market_type == 'forex':
            # Forex adjustments
            # Tighter exits during off-sessions
            session_quality = data.get('session_quality', 1.0)
            if session_quality < 0.7:
                # Reduce targets during poor sessions
                for level in exit_plan['levels']:
                    level['r_multiple'] *= 0.8
                    level['target_price'] = data['entry_price'] + (data.get('r_value', 0) * level['r_multiple'])
        
        elif self.market_type == 'crypto':
            # Crypto adjustments
            # Wider exits during high volatility
            volatility_regime = data.get('volatility_regime', 'normal')
            if volatility_regime == 'high':
                # Increase targets during high volatility
                for level in exit_plan['levels']:
                    level['r_multiple'] *= 1.2
                    level['target_price'] = data['entry_price'] + (data.get('r_value', 0) * level['r_multiple'])
        
        return exit_plan
    
    def monitor_active_exits(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monitor all active exit strategies
        """
        if not self.active_exits:
            return {'active_exits': 0, 'monitoring_status': 'no_active_trades'}
        
        monitoring_results = {}
        current_prices = data.get('current_prices', {})
        
        for trade_id, exit_management in self.active_exits.items():
            symbol = exit_management['symbol']
            current_price = current_prices.get(symbol, 0)
            
            if current_price > 0:
                # Update trade metrics
                self.update_trade_metrics(exit_management, current_price)
                
                # Check exit triggers
                exit_triggers = self.check_exit_triggers(exit_management, current_price)
                
                # Update trailing stops
                trailing_update = self.update_trailing_stops(exit_management, current_price)
                
                monitoring_results[trade_id] = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'unrealized_pnl': exit_management['unrealized_pnl'],
                    'exit_triggers': exit_triggers,
                    'trailing_update': trailing_update,
                    'remaining_position': exit_management['remaining_position']
                }
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'active_exits': len(self.active_exits),
            'monitoring_results': monitoring_results,
            'market_type': self.market_type
        }
    
    def update_trade_metrics(self, exit_management: Dict[str, Any], current_price: float):
        """Update trade metrics for active position"""
        entry_price = exit_management['entry_price']
        direction = exit_management['direction']
        
        # Calculate unrealized PnL
        if direction == 'long':
            pnl = current_price - entry_price
            favorable_excursion = max(current_price - entry_price, exit_management['max_favorable_excursion'])
            adverse_excursion = min(current_price - entry_price, exit_management['max_adverse_excursion'])
        else:  # short
            pnl = entry_price - current_price
            favorable_excursion = max(entry_price - current_price, exit_management['max_favorable_excursion'])
            adverse_excursion = min(entry_price - current_price, exit_management['max_adverse_excursion'])
        
        exit_management['unrealized_pnl'] = pnl
        exit_management['max_favorable_excursion'] = favorable_excursion
        exit_management['max_adverse_excursion'] = adverse_excursion
        
        # Calculate R-multiple
        r_value = exit_management['r_value']
        exit_management['current_r_multiple'] = pnl / r_value if r_value > 0 else 0
    
    def check_exit_triggers(self, exit_management: Dict[str, Any], current_price: float) -> List[Dict[str, Any]]:
        """
        Check for exit triggers at profit levels
        """
        triggers = []
        direction = exit_management['direction']
        
        for level in exit_management['exit_plan']['levels']:
            if level['status'] == 'pending':
                target_price = level['target_price']
                
                # Check if target reached
                target_reached = False
                if direction == 'long' and current_price >= target_price:
                    target_reached = True
                elif direction == 'short' and current_price <= target_price:
                    target_reached = True
                
                if target_reached:
                    triggers.append({
                        'level': level['level'],
                        'r_multiple': level['r_multiple'],
                        'target_price': target_price,
                        'exit_percentage': level['exit_percentage'],
                        'trigger_type': 'profit_target',
                        'execution_recommended': True
                    })
        
        # Check breakeven trigger
        breakeven_config = exit_management['exit_plan']['breakeven_move']
        if not breakeven_config['executed']:
            activation_price = breakeven_config['activation_price']
            
            breakeven_reached = False
            if direction == 'long' and current_price >= activation_price:
                breakeven_reached = True
            elif direction == 'short' and current_price <= activation_price:
                breakeven_reached = True
            
            if breakeven_reached:
                triggers.append({
                    'trigger_type': 'breakeven_move',
                    'new_stop_loss': exit_management['entry_price'],
                    'execution_recommended': True
                })
        
        # Check trailing stop triggers
        trailing_config = exit_management['exit_plan']['trailing_stop']
        if trailing_config['active']:
            current_trail = trailing_config['current_trail_price']
            
            trail_triggered = False
            if direction == 'long' and current_price <= current_trail:
                trail_triggered = True
            elif direction == 'short' and current_price >= current_trail:
                trail_triggered = True
            
            if trail_triggered:
                triggers.append({
                    'trigger_type': 'trailing_stop',
                    'trail_price': current_trail,
                    'exit_percentage': exit_management['remaining_position'],
                    'execution_recommended': True
                })
        
        return triggers
    
    def update_trailing_stops(self, exit_management: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Update trailing stop levels
        """
        trailing_config = exit_management['exit_plan']['trailing_stop']
        direction = exit_management['direction']
        r_value = exit_management['r_value']
        
        update_result = {
            'trailing_updated': False,
            'new_trail_price': None,
            'activation_status': trailing_config['active']
        }
        
        # Check for trailing stop activation
        if not trailing_config['active']:
            activation_price = trailing_config['activation_price']
            
            activation_reached = False
            if direction == 'long' and current_price >= activation_price:
                activation_reached = True
            elif direction == 'short' and current_price <= activation_price:
                activation_reached = True
            
            if activation_reached:
                trailing_config['active'] = True
                trailing_distance = trailing_config['trailing_distance_r'] * r_value
                
                if direction == 'long':
                    trailing_config['current_trail_price'] = current_price - trailing_distance
                else:
                    trailing_config['current_trail_price'] = current_price + trailing_distance
                
                update_result['trailing_updated'] = True
                update_result['activation_status'] = True
                update_result['new_trail_price'] = trailing_config['current_trail_price']
                
                self.logger.info(f"Trailing stop activated for {exit_management['trade_id']} at {current_price}")
        
        # Update existing trailing stop
        elif trailing_config['active']:
            trailing_distance = trailing_config['trailing_distance_r'] * r_value
            current_trail = trailing_config['current_trail_price']
            
            if direction == 'long':
                new_trail = current_price - trailing_distance
                if new_trail > current_trail:
                    trailing_config['current_trail_price'] = new_trail
                    update_result['trailing_updated'] = True
                    update_result['new_trail_price'] = new_trail
            else:  # short
                new_trail = current_price + trailing_distance
                if new_trail < current_trail:
                    trailing_config['current_trail_price'] = new_trail
                    update_result['trailing_updated'] = True
                    update_result['new_trail_price'] = new_trail
        
        return update_result
    
    def execute_exit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute exit order based on triggers
        """
        required_fields = ['trade_id', 'exit_trigger']
        if not self.validate_data(data, required_fields):
            return {'error': 'Missing required fields for exit execution'}
        
        trade_id = data['trade_id']
        exit_trigger = data['exit_trigger']
        current_price = data.get('current_price', 0)
        
        if trade_id not in self.active_exits:
            return {'error': 'Trade not found in active exits'}
        
        exit_management = self.active_exits[trade_id]
        
        # Execute the exit
        execution_result = self.process_exit_execution(exit_management, exit_trigger, current_price)
        
        # Update exit management
        self.update_exit_management_after_execution(exit_management, execution_result)
        
        # Check if trade is completely closed
        if exit_management['remaining_position'] <= 0:
            # Move to history
            exit_management['completed_at'] = datetime.now(timezone.utc)
            exit_management['status'] = 'completed'
            self.exit_history.append(exit_management.copy())
            del self.active_exits[trade_id]
            
            # Update performance metrics
            self.update_exit_performance(exit_management)
        
        return {
            'success': True,
            'trade_id': trade_id,
            'execution_result': execution_result,
            'remaining_position': exit_management['remaining_position'],
            'total_realized_pnl': exit_management['realized_pnl']
        }
    
    def process_exit_execution(self, exit_management: Dict[str, Any], 
                              exit_trigger: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """
        Process the actual exit execution
        """
        trigger_type = exit_trigger['trigger_type']
        
        if trigger_type == 'profit_target':
            # Partial exit at profit level
            exit_percentage = exit_trigger['exit_percentage']
            execution_price = exit_trigger['target_price']
            
            # Mark level as executed
            for level in exit_management['exit_plan']['levels']:
                if level['level'] == exit_trigger['level']:
                    level['status'] = 'executed'
                    level['executed_at'] = datetime.now(timezone.utc)
                    level['execution_price'] = execution_price
                    break
        
        elif trigger_type == 'trailing_stop':
            # Full exit via trailing stop
            exit_percentage = exit_management['remaining_position']
            execution_price = current_price
        
        elif trigger_type == 'breakeven_move':
            # Move stop to breakeven
            exit_management['stop_loss'] = exit_management['entry_price']
            exit_management['exit_plan']['breakeven_move']['executed'] = True
            
            return {
                'execution_type': 'stop_loss_adjustment',
                'new_stop_loss': exit_management['entry_price'],
                'exit_percentage': 0  # No position closed
            }
        
        else:
            return {'error': f'Unknown trigger type: {trigger_type}'}
        
        # Calculate PnL for this exit
        entry_price = exit_management['entry_price']
        direction = exit_management['direction']
        
        if direction == 'long':
            pnl_per_unit = execution_price - entry_price
        else:
            pnl_per_unit = entry_price - execution_price
        
        # Update position and PnL
        position_closed = exit_percentage
        exit_management['remaining_position'] -= position_closed
        exit_management['exits_executed'] += 1
        
        realized_pnl = pnl_per_unit * (position_closed / 100.0)
        exit_management['realized_pnl'] += realized_pnl
        
        return {
            'execution_type': 'partial_exit' if exit_management['remaining_position'] > 0 else 'full_exit',
            'exit_percentage': position_closed,
            'execution_price': execution_price,
            'realized_pnl': realized_pnl,
            'r_multiple_achieved': exit_trigger.get('r_multiple', 0)
        }
    
    def update_exit_management_after_execution(self, exit_management: Dict[str, Any], 
                                             execution_result: Dict[str, Any]):
        """Update exit management after execution"""
        # Log the execution
        if 'executions' not in exit_management:
            exit_management['executions'] = []
        
        execution_record = {
            'timestamp': datetime.now(timezone.utc),
            'execution_result': execution_result,
            'remaining_position_after': exit_management['remaining_position']
        }
        exit_management['executions'].append(execution_record)
    
    def update_exit_performance(self, completed_exit: Dict[str, Any]):
        """Update exit strategy performance metrics"""
        self.exit_performance['total_exits'] += 1
        
        # Check if profitable
        if completed_exit['realized_pnl'] > 0:
            self.exit_performance['profitable_exits'] += 1
        
        # Update average R-multiple
        r_achieved = completed_exit['realized_pnl'] / completed_exit['r_value'] if completed_exit['r_value'] > 0 else 0
        
        current_avg = self.exit_performance['avg_r_multiple']
        total_exits = self.exit_performance['total_exits']
        
        self.exit_performance['avg_r_multiple'] = ((current_avg * (total_exits - 1)) + r_achieved) / total_exits
        
        # Calculate win rate
        win_rate = self.exit_performance['profitable_exits'] / self.exit_performance['total_exits']
        
        self.logger.info(f"Exit performance: {self.exit_performance['profitable_exits']}/{self.exit_performance['total_exits']} = {win_rate:.1%}, Avg R: {self.exit_performance['avg_r_multiple']:.2f}")
    
    def get_exit_status(self) -> Dict[str, Any]:
        """Get comprehensive exit strategy status"""
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'market_type': self.market_type,
            'active_exits_count': len(self.active_exits),
            'exit_history_count': len(self.exit_history),
            'exit_performance': self.exit_performance,
            'available_strategies': list(self.exit_strategies.keys()),
            'configuration': {
                'profit_taking_levels': self.profit_taking_levels,
                'trailing_stop_activation': self.trailing_stop_activation,
                'breakeven_activation': self.breakeven_activation
            }
        }
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on exit performance"""
        if self.exit_performance['total_exits'] == 0:
            return 0.5  # Neutral when no data
        
        # Signal strength based on exit performance
        win_rate = self.exit_performance['profitable_exits'] / self.exit_performance['total_exits']
        avg_r = max(0, min(self.exit_performance['avg_r_multiple'] / 2.0, 1.0))  # Normalize R-multiple
        
        return (win_rate * 0.7 + avg_r * 0.3)
    
    def requires_continuous_processing(self) -> bool:
        """Exit strategy agent needs continuous monitoring"""
        return True
    
    def _continuous_process(self):
        """Continuous processing for exit monitoring"""
        try:
            if self.active_exits:
                # Monitor all active exits
                # In production, this would get current prices and check triggers
                self.logger.debug(f"Monitoring {len(self.active_exits)} active exit strategies")
        
        except Exception as e:
            self.logger.error(f"Error in exit strategy continuous processing: {e}")
    
    def get_processing_interval(self) -> float:
        """Get processing interval for exit monitoring"""
        return 5.0  # Check every 5 seconds for exits