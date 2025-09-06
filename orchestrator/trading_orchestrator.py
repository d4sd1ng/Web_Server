"""
Trading Orchestrator
Coordinates all trading agents and makes final trading decisions
"""

import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from agents.base_agent import BaseAgent
from communication.message_bus import MessageBus, EventSystem


class TradingOrchestrator:
    """
    Central orchestrator that coordinates all trading agents
    Makes final trading decisions based on agent inputs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agents = {}
        self.agent_results = {}
        
        # Communication system
        self.message_bus = MessageBus()
        self.event_system = EventSystem(self.message_bus)
        
        # Trading state
        self.current_signals = {}
        self.trading_decisions = []
        self.agent_weights = self.config.get('agent_weights', {})
        
        # Threading
        self.is_running = False
        self._stop_event = threading.Event()
        self._orchestrator_thread = None
        
        # Logging
        self.logger = logging.getLogger("TradingOrchestrator")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("Trading Orchestrator initialized")
    
    def add_agent(self, agent: BaseAgent, weight: float = 1.0):
        """
        Add an agent to the orchestrator
        
        Args:
            agent: Agent instance to add
            weight: Weight for this agent's signals (default: 1.0)
        """
        agent_id = agent.agent_id
        self.agents[agent_id] = agent
        self.agent_weights[agent_id] = weight
        
        # Set up agent communication
        agent.set_message_bus(self.message_bus)
        
        # Subscribe agent to relevant topics
        self.setup_agent_subscriptions(agent)
        
        self.logger.info(f"Added agent: {agent_id} (weight: {weight})")
    
    def setup_agent_subscriptions(self, agent: BaseAgent):
        """
        Set up subscriptions for an agent based on its type
        """
        agent_id = agent.agent_id
        
        # All agents get price updates
        agent.subscribe(["price_update", "market_data_update"])
        
        # ICT/SMC agents get structure updates
        if any(keyword in agent_id for keyword in ['ict', 'smc', 'order_blocks', 'fvg', 'market_structure']):
            agent.subscribe(["market_structure_shift", "volume_spike"])
        
        # ML agents get retrain signals
        if 'ml' in agent_id:
            agent.subscribe(["retrain_request", "feature_update"])
        
        # Execution agents get trade signals
        if any(keyword in agent_id for keyword in ['execution', 'risk', 'order']):
            agent.subscribe(["trade_signal", "risk_alert"])
        
        self.logger.info(f"Set up subscriptions for agent: {agent_id}")
    
    def start(self):
        """Start the orchestrator and all agents"""
        if self.is_running:
            self.logger.warning("Orchestrator is already running")
            return
        
        # Start message bus
        self.message_bus.start()
        
        # Start all agents
        for agent_id, agent in self.agents.items():
            try:
                agent.start()
                self.logger.info(f"Started agent: {agent_id}")
            except Exception as e:
                self.logger.error(f"Error starting agent {agent_id}: {e}")
        
        # Start orchestrator thread
        self.is_running = True
        self._orchestrator_thread = threading.Thread(target=self._orchestrator_loop)
        self._orchestrator_thread.daemon = True
        self._orchestrator_thread.start()
        
        self.logger.info("Trading Orchestrator started")
    
    def stop(self):
        """Stop the orchestrator and all agents"""
        if not self.is_running:
            return
        
        self.is_running = False
        self._stop_event.set()
        
        # Stop all agents
        for agent_id, agent in self.agents.items():
            try:
                agent.stop()
                self.logger.info(f"Stopped agent: {agent_id}")
            except Exception as e:
                self.logger.error(f"Error stopping agent {agent_id}: {e}")
        
        # Stop message bus
        self.message_bus.stop()
        
        # Wait for orchestrator thread
        if self._orchestrator_thread:
            self._orchestrator_thread.join(timeout=5.0)
        
        self.logger.info("Trading Orchestrator stopped")
    
    def _orchestrator_loop(self):
        """Main orchestrator loop"""
        while self.is_running and not self._stop_event.is_set():
            try:
                # Collect agent results
                self.collect_agent_results()
                
                # Make trading decisions
                trading_decisions = self.make_trading_decisions()
                
                # Execute decisions (if any)
                if trading_decisions:
                    self.execute_trading_decisions(trading_decisions)
                
                # Clean up old data
                self.cleanup_old_data()
                
                # Sleep until next iteration
                time.sleep(self.config.get('orchestrator_interval', 60))  # 1 minute default
                
            except Exception as e:
                self.logger.error(f"Error in orchestrator loop: {e}")
                time.sleep(5)  # Short sleep on error
    
    def collect_agent_results(self):
        """Collect current results from all agents"""
        for agent_id, agent in self.agents.items():
            try:
                # Get agent status and latest results
                agent_status = agent.get_status()
                self.agent_results[agent_id] = {
                    'status': agent_status,
                    'last_update': datetime.now(timezone.utc),
                    'signal_strength': agent.get_signal_strength()
                }
                
            except Exception as e:
                self.logger.warning(f"Error collecting results from agent {agent_id}: {e}")
    
    def make_trading_decisions(self) -> List[Dict[str, Any]]:
        """
        Make trading decisions based on agent inputs
        """
        decisions = []
        
        try:
            # Get signals from all agents
            signals = self.aggregate_agent_signals()
            
            # Apply decision logic for each symbol
            for symbol, symbol_signals in signals.items():
                decision = self.evaluate_symbol_signals(symbol, symbol_signals)
                
                if decision and decision['action'] != 'hold':
                    decisions.append(decision)
            
            return decisions
            
        except Exception as e:
            self.logger.error(f"Error making trading decisions: {e}")
            return []
    
    def aggregate_agent_signals(self) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate signals from all agents by symbol
        """
        signals_by_symbol = {}
        
        for agent_id, agent_data in self.agent_results.items():
            try:
                agent_weight = self.agent_weights.get(agent_id, 1.0)
                signal_strength = agent_data.get('signal_strength', 0.0)
                weighted_strength = signal_strength * agent_weight
                
                # Extract symbol-specific signals (this would need to be customized based on actual agent outputs)
                # For now, using a simplified approach
                symbol = 'BTC/USDT'  # This would come from agent data
                
                if symbol not in signals_by_symbol:
                    signals_by_symbol[symbol] = {
                        'agents': {},
                        'total_weighted_strength': 0.0,
                        'bullish_signals': 0,
                        'bearish_signals': 0,
                        'neutral_signals': 0
                    }
                
                signals_by_symbol[symbol]['agents'][agent_id] = {
                    'signal_strength': signal_strength,
                    'weighted_strength': weighted_strength,
                    'weight': agent_weight,
                    'status': agent_data['status']
                }
                
                signals_by_symbol[symbol]['total_weighted_strength'] += weighted_strength
                
                # Classify signal direction (simplified)
                if weighted_strength > 0.6:
                    signals_by_symbol[symbol]['bullish_signals'] += 1
                elif weighted_strength < 0.4:
                    signals_by_symbol[symbol]['bearish_signals'] += 1
                else:
                    signals_by_symbol[symbol]['neutral_signals'] += 1
                
            except Exception as e:
                self.logger.warning(f"Error aggregating signals from agent {agent_id}: {e}")
        
        return signals_by_symbol
    
    def evaluate_symbol_signals(self, symbol: str, signals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate signals for a specific symbol and make trading decision
        """
        try:
            total_agents = len(signals['agents'])
            bullish_signals = signals['bullish_signals']
            bearish_signals = signals['bearish_signals']
            total_weighted_strength = signals['total_weighted_strength']
            
            # Decision thresholds
            min_agent_consensus = self.config.get('min_agent_consensus', 0.6)  # 60% of agents
            min_signal_strength = self.config.get('min_signal_strength', 0.7)
            
            # Calculate consensus
            bullish_consensus = bullish_signals / total_agents
            bearish_consensus = bearish_signals / total_agents
            avg_signal_strength = total_weighted_strength / total_agents
            
            # Make decision
            action = 'hold'
            confidence = 0.0
            reasons = []
            
            if (bullish_consensus >= min_agent_consensus and 
                avg_signal_strength >= min_signal_strength):
                action = 'buy'
                confidence = min(bullish_consensus * avg_signal_strength, 1.0)
                reasons.append(f"Bullish consensus: {bullish_consensus:.1%}")
                reasons.append(f"Signal strength: {avg_signal_strength:.2f}")
            
            elif (bearish_consensus >= min_agent_consensus and 
                  avg_signal_strength >= min_signal_strength):
                action = 'sell'
                confidence = min(bearish_consensus * avg_signal_strength, 1.0)
                reasons.append(f"Bearish consensus: {bearish_consensus:.1%}")
                reasons.append(f"Signal strength: {avg_signal_strength:.2f}")
            
            else:
                reasons.append("Insufficient consensus or signal strength")
            
            decision = {
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'reasons': reasons,
                'agent_analysis': {
                    'total_agents': total_agents,
                    'bullish_signals': bullish_signals,
                    'bearish_signals': bearish_signals,
                    'bullish_consensus': bullish_consensus,
                    'bearish_consensus': bearish_consensus,
                    'avg_signal_strength': avg_signal_strength
                },
                'contributing_agents': list(signals['agents'].keys())
            }
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error evaluating signals for {symbol}: {e}")
            return None
    
    def execute_trading_decisions(self, decisions: List[Dict[str, Any]]):
        """
        Execute trading decisions by sending them to execution agents
        """
        for decision in decisions:
            try:
                # Publish trading decision
                self.event_system.emit_event("trading_decision", decision)
                
                # Log decision
                self.logger.info(f"Trading decision: {decision['action']} {decision['symbol']} "
                               f"(confidence: {decision['confidence']:.2f})")
                
                # Store decision
                self.trading_decisions.append(decision)
                
            except Exception as e:
                self.logger.error(f"Error executing trading decision: {e}")
    
    def cleanup_old_data(self):
        """Clean up old data to prevent memory issues"""
        try:
            # Limit trading decisions history
            if len(self.trading_decisions) > 1000:
                self.trading_decisions = self.trading_decisions[-500:]
            
            # Clean up agent results older than 1 hour
            cutoff_time = datetime.now(timezone.utc).timestamp() - 3600
            
            for agent_id in list(self.agent_results.keys()):
                if ('last_update' in self.agent_results[agent_id] and 
                    self.agent_results[agent_id]['last_update'].timestamp() < cutoff_time):
                    del self.agent_results[agent_id]
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up old data: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status
        """
        try:
            agent_statuses = {}
            for agent_id, agent in self.agents.items():
                agent_statuses[agent_id] = agent.get_status()
            
            return {
                'orchestrator_status': 'running' if self.is_running else 'stopped',
                'total_agents': len(self.agents),
                'active_agents': sum(1 for status in agent_statuses.values() if status['is_active']),
                'agent_statuses': agent_statuses,
                'message_bus_stats': self.message_bus.get_stats(),
                'recent_decisions_count': len(self.trading_decisions),
                'last_decision_time': (self.trading_decisions[-1]['timestamp'] 
                                     if self.trading_decisions else None),
                'system_uptime': self.calculate_system_uptime()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def calculate_system_uptime(self) -> float:
        """Calculate system uptime in seconds"""
        if not hasattr(self, '_start_time'):
            self._start_time = datetime.now(timezone.utc)
        
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()
    
    def process_market_data(self, symbol: str, market_data: Dict[str, Any]):
        """
        Process new market data through all relevant agents
        
        Args:
            symbol: Trading symbol
            market_data: Market data dictionary (OHLCV, etc.)
        """
        try:
            # Publish market data update
            self.event_system.emit_price_update(symbol, market_data)
            
            # Process through specific agents that handle market data
            data_agents = [agent_id for agent_id in self.agents.keys() 
                          if any(keyword in agent_id for keyword in ['data', 'market', 'historical'])]
            
            for agent_id in data_agents:
                try:
                    agent = self.agents[agent_id]
                    result = agent.safe_process({
                        'symbol': symbol,
                        'market_data': market_data
                    })
                    
                    if result:
                        self.agent_results[agent_id] = result
                        
                except Exception as e:
                    self.logger.warning(f"Error processing market data in agent {agent_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing market data for {symbol}: {e}")
    
    def process_technical_analysis(self, symbol: str, df: pd.DataFrame):
        """
        Process technical analysis through ICT/SMC agents
        
        Args:
            symbol: Trading symbol
            df: OHLCV DataFrame with indicators
        """
        try:
            # Process through ICT/SMC agents
            ict_smc_agents = [agent_id for agent_id in self.agents.keys() 
                             if any(keyword in agent_id for keyword in ['ict', 'smc', 'fvg', 'order_blocks', 'ote', 'premium'])]
            
            for agent_id in ict_smc_agents:
                try:
                    agent = self.agents[agent_id]
                    result = agent.safe_process({
                        'symbol': symbol,
                        'df': df
                    })
                    
                    if result:
                        self.agent_results[agent_id] = result
                        
                except Exception as e:
                    self.logger.warning(f"Error processing technical analysis in agent {agent_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing technical analysis for {symbol}: {e}")
    
    def process_ml_prediction(self, symbol: str, features: List[float]):
        """
        Process ML prediction through ML agents
        
        Args:
            symbol: Trading symbol
            features: Feature array for ML prediction
        """
        try:
            # Process through ML agents
            ml_agents = [agent_id for agent_id in self.agents.keys() if 'ml' in agent_id]
            
            for agent_id in ml_agents:
                try:
                    agent = self.agents[agent_id]
                    result = agent.safe_process({
                        'symbol': symbol,
                        'features': features
                    })
                    
                    if result:
                        self.agent_results[agent_id] = result
                        
                except Exception as e:
                    self.logger.warning(f"Error processing ML prediction in agent {agent_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error processing ML prediction for {symbol}: {e}")
    
    def get_trading_recommendation(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive trading recommendation for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Trading recommendation dictionary
        """
        try:
            # Collect relevant agent results for this symbol
            relevant_results = {}
            for agent_id, result in self.agent_results.items():
                if isinstance(result, dict) and result.get('symbol') == symbol:
                    relevant_results[agent_id] = result
            
            if not relevant_results:
                return {
                    'symbol': symbol,
                    'recommendation': 'hold',
                    'confidence': 0.0,
                    'reason': 'No agent data available'
                }
            
            # Aggregate signals
            bullish_strength = 0.0
            bearish_strength = 0.0
            total_weight = 0.0
            
            agent_contributions = []
            
            for agent_id, result in relevant_results.items():
                agent_weight = self.agent_weights.get(agent_id, 1.0)
                signal_strength = result.get('signal_strength', 0.0)
                
                # Determine signal direction based on agent type and results
                signal_direction = self.determine_signal_direction(agent_id, result)
                
                if signal_direction == 'bullish':
                    bullish_strength += signal_strength * agent_weight
                elif signal_direction == 'bearish':
                    bearish_strength += signal_strength * agent_weight
                
                total_weight += agent_weight
                
                agent_contributions.append({
                    'agent_id': agent_id,
                    'signal_strength': signal_strength,
                    'signal_direction': signal_direction,
                    'weight': agent_weight,
                    'contribution': signal_strength * agent_weight
                })
            
            # Normalize strengths
            if total_weight > 0:
                bullish_strength /= total_weight
                bearish_strength /= total_weight
            
            # Make recommendation
            if bullish_strength > bearish_strength and bullish_strength > 0.6:
                recommendation = 'buy'
                confidence = bullish_strength
            elif bearish_strength > bullish_strength and bearish_strength > 0.6:
                recommendation = 'sell'
                confidence = bearish_strength
            else:
                recommendation = 'hold'
                confidence = 0.5
            
            return {
                'symbol': symbol,
                'recommendation': recommendation,
                'confidence': confidence,
                'bullish_strength': bullish_strength,
                'bearish_strength': bearish_strength,
                'agent_contributions': agent_contributions,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting trading recommendation for {symbol}: {e}")
            return {
                'symbol': symbol,
                'recommendation': 'hold',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def determine_signal_direction(self, agent_id: str, result: Dict[str, Any]) -> str:
        """
        Determine signal direction based on agent type and results
        """
        # This is a simplified implementation - would need to be customized for each agent type
        
        if 'ml' in agent_id:
            should_trade = result.get('should_trade', False)
            probability = result.get('probability', 0.0)
            if should_trade and probability > 0.5:
                return 'bullish'  # Simplified - ML could indicate direction
            else:
                return 'neutral'
        
        elif 'fair_value_gaps' in agent_id:
            fvgs = result.get('fvgs', [])
            bullish_fvgs = sum(1 for fvg in fvgs if fvg['type'] == 'bullish')
            bearish_fvgs = sum(1 for fvg in fvgs if fvg['type'] == 'bearish')
            
            if bullish_fvgs > bearish_fvgs:
                return 'bullish'
            elif bearish_fvgs > bullish_fvgs:
                return 'bearish'
            else:
                return 'neutral'
        
        elif 'order_blocks' in agent_id:
            obs = result.get('order_blocks', [])
            valid_bull_obs = sum(1 for ob in obs if ob['type'] == 'bullish' and ob['retest'])
            valid_bear_obs = sum(1 for ob in obs if ob['type'] == 'bearish' and ob['retest'])
            
            if valid_bull_obs > valid_bear_obs:
                return 'bullish'
            elif valid_bear_obs > valid_bull_obs:
                return 'bearish'
            else:
                return 'neutral'
        
        elif 'market_structure' in agent_id:
            current_structure = result.get('current_structure', 'neutral')
            if 'bullish' in current_structure or 'uptrend' in current_structure:
                return 'bullish'
            elif 'bearish' in current_structure or 'downtrend' in current_structure:
                return 'bearish'
            else:
                return 'neutral'
        
        elif 'premium_discount' in agent_id:
            pd_zone = result.get('current_pd_zone', 'equilibrium')
            if pd_zone == 'discount':
                return 'bullish'  # Buy in discount
            elif pd_zone == 'premium':
                return 'bearish'  # Sell in premium
            else:
                return 'neutral'
        
        elif 'ote' in agent_id:
            ote_analysis = result.get('ote_analysis', {})
            if ote_analysis.get('in_ote_long'):
                return 'bullish'
            elif ote_analysis.get('in_ote_short'):
                return 'bearish'
            else:
                return 'neutral'
        
        # Default to neutral for unknown agent types
        return 'neutral'
    
    def get_agent_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for all agents
        """
        metrics = {}
        
        for agent_id, agent in self.agents.items():
            try:
                agent_status = agent.get_status()
                metrics[agent_id] = {
                    'uptime_seconds': agent_status['uptime_seconds'],
                    'signals_generated': agent_status['signals_generated'],
                    'avg_processing_time': agent_status['avg_processing_time'],
                    'error_count': agent_status['error_count'],
                    'signal_strength': agent_status['signal_strength'],
                    'is_active': agent_status['is_active']
                }
                
            except Exception as e:
                self.logger.warning(f"Error getting metrics for agent {agent_id}: {e}")
        
        return metrics
    
    def get_orchestrator_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive orchestrator summary
        """
        return {
            'system_status': self.get_system_status(),
            'agent_performance': self.get_agent_performance_metrics(),
            'recent_decisions': self.trading_decisions[-10:] if self.trading_decisions else [],
            'configuration': self.config,
            'agent_weights': self.agent_weights
        }
    
    def update_agent_weight(self, agent_id: str, new_weight: float):
        """
        Update the weight of a specific agent
        """
        if agent_id in self.agents:
            self.agent_weights[agent_id] = new_weight
            self.logger.info(f"Updated weight for agent {agent_id}: {new_weight}")
        else:
            self.logger.warning(f"Agent {agent_id} not found")
    
    def pause_agent(self, agent_id: str):
        """Pause a specific agent"""
        if agent_id in self.agents:
            self.agents[agent_id].stop()
            self.logger.info(f"Paused agent: {agent_id}")
    
    def resume_agent(self, agent_id: str):
        """Resume a specific agent"""
        if agent_id in self.agents:
            self.agents[agent_id].start()
            self.logger.info(f"Resumed agent: {agent_id}")
    
    def get_active_signals(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get current active signals, optionally filtered by symbol
        """
        active_signals = {}
        
        for agent_id, result in self.agent_results.items():
            if symbol is None or (isinstance(result, dict) and result.get('symbol') == symbol):
                if isinstance(result, dict) and result.get('signal_strength', 0) > 0.5:
                    active_signals[agent_id] = {
                        'signal_strength': result.get('signal_strength'),
                        'timestamp': result.get('timestamp'),
                        'summary': self.get_agent_signal_summary(agent_id, result)
                    }
        
        return active_signals
    
    def get_agent_signal_summary(self, agent_id: str, result: Dict[str, Any]) -> str:
        """
        Get a human-readable summary of an agent's signal
        """
        if 'fair_value_gaps' in agent_id:
            fvg_count = len(result.get('fvgs', []))
            return f"{fvg_count} FVGs detected"
        
        elif 'order_blocks' in agent_id:
            ob_count = len(result.get('order_blocks', []))
            return f"{ob_count} Order Blocks detected"
        
        elif 'market_structure' in agent_id:
            structure = result.get('current_structure', 'unknown')
            return f"Structure: {structure}"
        
        elif 'ml' in agent_id:
            should_trade = result.get('should_trade', False)
            probability = result.get('probability', 0.0)
            return f"ML: {'Trade' if should_trade else 'Hold'} ({probability:.2f})"
        
        elif 'premium_discount' in agent_id:
            pd_zone = result.get('current_pd_zone', 'unknown')
            return f"P/D Zone: {pd_zone}"
        
        elif 'ote' in agent_id:
            in_ote = result.get('ote_analysis', {}).get('in_any_ote', False)
            return f"OTE: {'In zone' if in_ote else 'Outside zone'}"
        
        else:
            return f"Signal strength: {result.get('signal_strength', 0.0):.2f}"