"""
Main Trading System with Agent Architecture
Integrates all agents and orchestrator for complete trading system
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from typing import Dict, Any

# Add paths for agent imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator.trading_orchestrator import TradingOrchestrator

# ICT/SMC Agents
from agents.ict_smc.fair_value_gaps_agent import FairValueGapsAgent
from agents.ict_smc.order_blocks_agent import OrderBlocksAgent
from agents.ict_smc.market_structure_agent import MarketStructureAgent
from agents.ict_smc.liquidity_sweeps_agent import LiquiditySweepsAgent
from agents.ict_smc.premium_discount_agent import PremiumDiscountAgent
from agents.ict_smc.ote_agent import OTEAgent
from agents.ict_smc.breaker_blocks_agent import BreakerBlocksAgent
from agents.ict_smc.sof_agent import SOFAgent
from agents.ict_smc.displacement_agent import DisplacementAgent
from agents.ict_smc.engulfing_agent import EngulfingAgent
from agents.ict_smc.mitigation_blocks_agent import MitigationBlocksAgent
from agents.ict_smc.killzone_agent import KillzoneAgent
from agents.ict_smc.pattern_cluster_agent import PatternClusterAgent
from agents.ict_smc.swing_failure_pattern_agent import SwingFailurePatternAgent
from agents.ict_smc.htf_confluence_agent import HTFConfluenceAgent

# Analysis Agents
from agents.analysis.volume_analysis_agent import VolumeAnalysisAgent
from agents.analysis.session_analysis_agent import SessionAnalysisAgent
from agents.analysis.technical_indicators_agent import TechnicalIndicatorsAgent

# Data Agents
from agents.data.sentiment_agent import SentimentAgent
from agents.data.historical_data_agent import HistoricalDataAgent
from agents.data.market_data_agent import MarketDataAgent

# ML Agents
from agents.ml.ml_prediction_agent import MLPredictionAgent

# Execution Agents
from agents.execution.risk_management_agent import RiskManagementAgent
from agents.execution.order_execution_agent import OrderExecutionAgent

# Additional ICT/SMC Agents
from agents.ict_smc.judas_swing_agent import JudasSwingAgent
from agents.ict_smc.power_of_three_agent import PowerOfThreeAgent
from agents.ict_smc.market_maker_model_agent import MarketMakerModelAgent
from agents.ict_smc.turtle_soup_agent import TurtleSoupAgent
from agents.ict_smc.imbalance_agent import ImbalanceAgent
from agents.ict_smc.momentum_shift_agent import MomentumShiftAgent


class TradingSystem:
    """
    Complete trading system with agent architecture
    Integrates all ICT/SMC and ML agents
    """
    
    def __init__(self, config_file: str = None):
        """
        Initialize the trading system
        
        Args:
            config_file: Path to configuration file
        """
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Setup logging
        self.setup_logging()
        
        # Initialize orchestrator
        self.orchestrator = TradingOrchestrator(self.config.get('orchestrator', {}))
        
        # Initialize agents
        self.agents = {}
        self.initialize_agents()
        
        self.logger = logging.getLogger("TradingSystem")
        self.logger.info("Trading System initialized")
    
    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Load system configuration"""
        default_config = {
            'orchestrator': {
                'min_agent_consensus': 0.6,
                'min_signal_strength': 0.7,
                'orchestrator_interval': 60
            },
            'agents': {
                'fair_value_gaps': {
                    'window': 3,
                    'min_gap': 0.0001,
                    'atr_distance_threshold': 2.0
                },
                'order_blocks': {
                    'lookback': 30,
                    'min_body': 0.3,
                    'retest_confirmation_bars': 3
                },
                'market_structure': {
                    'lookback': 20,
                    'confirmation_bars': 3
                },
                'liquidity_sweeps': {
                    'lookback': 10,
                    'equal_level_tolerance': 0.001,
                    'volume_threshold': 1.5
                },
                'premium_discount': {
                    'swing_lookback': 50,
                    'zone_threshold': 0.1
                },
                'ote': {
                    'swing_lookback': 20,
                    'fib_618_level': 0.618,
                    'fib_786_level': 0.786,
                    'ote_fib_level': 0.705
                },
                'ml_prediction': {
                    'model_type': 'RandomForest',
                    'threshold': 0.5,
                    'retrain_interval_hours': 24
                }
            },
            'agent_weights': {
                'fair_value_gaps': 1.2,
                'order_blocks': 1.5,
                'market_structure': 1.3,
                'liquidity_sweeps': 1.1,
                'premium_discount': 1.0,
                'ote': 1.4,
                'ml_prediction': 1.0
            },
            'trading': {
                'max_open_trades': 3,
                'risk_per_trade': 0.01,
                'leverage': 25
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                import json
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                
                # Merge configurations
                self.merge_configs(default_config, file_config)
                
            except Exception as e:
                print(f"Error loading config file {config_file}: {e}")
        
        return default_config
    
    def merge_configs(self, default: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self.merge_configs(default[key], value)
            else:
                default[key] = value
    
    def setup_logging(self):
        """Setup system logging"""
        log_level = self.config.get('log_level', 'INFO')
        log_format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('trading_system.log')
            ]
        )
    
    def initialize_agents(self):
        """Initialize all trading agents"""
        agent_configs = self.config.get('agents', {})
        agent_weights = self.config.get('agent_weights', {})
        market_type = self.config.get('market_type', 'crypto')
        
        print(f"🤖 Initializing agents for {market_type} market...")
        
        # Initialize ICT/SMC agents
        self.agents['fair_value_gaps'] = FairValueGapsAgent({**agent_configs.get('fair_value_gaps', {}), 'market_type': market_type})
        self.agents['order_blocks'] = OrderBlocksAgent({**agent_configs.get('order_blocks', {}), 'market_type': market_type})
        self.agents['market_structure'] = MarketStructureAgent({**agent_configs.get('market_structure', {}), 'market_type': market_type})
        self.agents['liquidity_sweeps'] = LiquiditySweepsAgent({**agent_configs.get('liquidity_sweeps', {}), 'market_type': market_type})
        self.agents['premium_discount'] = PremiumDiscountAgent({**agent_configs.get('premium_discount', {}), 'market_type': market_type})
        self.agents['ote'] = OTEAgent({**agent_configs.get('ote', {}), 'market_type': market_type})
        self.agents['breaker_blocks'] = BreakerBlocksAgent({**agent_configs.get('breaker_blocks', {}), 'market_type': market_type})
        self.agents['sof'] = SOFAgent({**agent_configs.get('sof', {}), 'market_type': market_type})
        self.agents['displacement'] = DisplacementAgent({**agent_configs.get('displacement', {}), 'market_type': market_type})
        self.agents['engulfing'] = EngulfingAgent({**agent_configs.get('engulfing', {}), 'market_type': market_type})
        self.agents['mitigation_blocks'] = MitigationBlocksAgent({**agent_configs.get('mitigation_blocks', {}), 'market_type': market_type})
        self.agents['killzone'] = KillzoneAgent({**agent_configs.get('killzone', {}), 'market_type': market_type})
        self.agents['pattern_cluster'] = PatternClusterAgent({**agent_configs.get('pattern_cluster', {}), 'market_type': market_type})
        self.agents['swing_failure_pattern'] = SwingFailurePatternAgent({**agent_configs.get('swing_failure_pattern', {}), 'market_type': market_type})
        self.agents['htf_confluence'] = HTFConfluenceAgent({**agent_configs.get('htf_confluence', {}), 'market_type': market_type})
        
        # Initialize additional ICT/SMC agents
        self.agents['judas_swing'] = JudasSwingAgent({**agent_configs.get('judas_swing', {}), 'market_type': market_type})
        self.agents['power_of_three'] = PowerOfThreeAgent({**agent_configs.get('power_of_three', {}), 'market_type': market_type})
        self.agents['market_maker_model'] = MarketMakerModelAgent({**agent_configs.get('market_maker_model', {}), 'market_type': market_type})
        self.agents['turtle_soup'] = TurtleSoupAgent({**agent_configs.get('turtle_soup', {}), 'market_type': market_type})
        self.agents['imbalance'] = ImbalanceAgent({**agent_configs.get('imbalance', {}), 'market_type': market_type})
        self.agents['momentum_shift'] = MomentumShiftAgent({**agent_configs.get('momentum_shift', {}), 'market_type': market_type})
        
        # Initialize Analysis agents
        self.agents['volume_analysis'] = VolumeAnalysisAgent({**agent_configs.get('volume_analysis', {}), 'market_type': market_type})
        self.agents['session_analysis'] = SessionAnalysisAgent({**agent_configs.get('session_analysis', {}), 'market_type': market_type})
        self.agents['technical_indicators'] = TechnicalIndicatorsAgent({**agent_configs.get('technical_indicators', {}), 'market_type': market_type})
        
        # Initialize Data agents
        self.agents['sentiment'] = SentimentAgent({**agent_configs.get('sentiment', {}), 'market_type': market_type})
        self.agents['historical_data'] = HistoricalDataAgent({**agent_configs.get('historical_data', {}), 'market_type': market_type})
        self.agents['market_data'] = MarketDataAgent({**agent_configs.get('market_data', {}), 'market_type': market_type})
        
        # Initialize ML agents
        self.agents['ml_prediction'] = MLPredictionAgent(agent_configs.get('ml_prediction', {}))
        
        # Initialize Execution agents
        self.agents['risk_management'] = RiskManagementAgent({**agent_configs.get('risk_management', {}), 'market_type': market_type})
        self.agents['order_execution'] = OrderExecutionAgent({**agent_configs.get('order_execution', {}), 'market_type': market_type})
        
        # Add agents to orchestrator
        for agent_id, agent in self.agents.items():
            weight = agent_weights.get(agent_id, 1.0)
            self.orchestrator.add_agent(agent, weight)
        
        print(f"✅ Initialized {len(self.agents)} agents:")
        print("🎯 Core ICT/SMC Agents:")
        for agent_id in ['fair_value_gaps', 'order_blocks', 'market_structure', 'liquidity_sweeps', 
                        'premium_discount', 'ote', 'breaker_blocks', 'sof', 'displacement', 
                        'engulfing', 'mitigation_blocks', 'killzone']:
            print(f"  • {agent_id}")
        
        print("🔥 Advanced ICT/SMC Agents:")
        for agent_id in ['pattern_cluster', 'swing_failure_pattern', 'htf_confluence', 'judas_swing', 
                        'power_of_three', 'market_maker_model', 'turtle_soup', 'imbalance', 'momentum_shift']:
            print(f"  • {agent_id}")
        
        print("📊 Analysis Agents:")
        for agent_id in ['volume_analysis', 'session_analysis', 'technical_indicators']:
            print(f"  • {agent_id}")
        
        print("🤖 Data & ML Agents:")
        for agent_id in ['sentiment', 'historical_data', 'market_data', 'ml_prediction']:
            print(f"  • {agent_id}")
        
        print("⚡ Execution Agents:")
        for agent_id in ['risk_management', 'order_execution']:
            print(f"  • {agent_id}")
    
    def start(self):
        """Start the complete trading system"""
        try:
            print("🚀 Starting Trading System...")
            print("=" * 50)
            
            # Start orchestrator (which starts all agents)
            self.orchestrator.start()
            
            print("✅ Trading System started successfully!")
            print(f"📊 Active agents: {len(self.agents)}")
            print(f"🤖 Orchestrator running")
            print(f"📡 Message bus active")
            print("=" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting trading system: {e}")
            return False
    
    def stop(self):
        """Stop the complete trading system"""
        try:
            print("⏹️  Stopping Trading System...")
            
            # Stop orchestrator (which stops all agents)
            self.orchestrator.stop()
            
            print("✅ Trading System stopped successfully!")
            
        except Exception as e:
            print(f"❌ Error stopping trading system: {e}")
    
    def process_symbol(self, symbol: str, market_data: Dict[str, Any]):
        """
        Process a complete trading cycle for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            market_data: Market data including OHLCV DataFrame
        """
        try:
            # Process market data through orchestrator
            self.orchestrator.process_market_data(symbol, market_data)
            
            # If we have OHLCV data, process through technical analysis
            if 'df' in market_data:
                self.orchestrator.process_technical_analysis(symbol, market_data['df'])
            
            # If we have features, process through ML
            if 'features' in market_data:
                self.orchestrator.process_ml_prediction(symbol, market_data['features'])
            
            # Get trading recommendation
            recommendation = self.orchestrator.get_trading_recommendation(symbol)
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {e}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        return self.orchestrator.get_system_status()
    
    def get_agent_summaries(self) -> Dict[str, Any]:
        """Get summaries from all agents"""
        summaries = {}
        
        for agent_id, agent in self.agents.items():
            try:
                if hasattr(agent, 'get_fvg_summary'):
                    summaries[agent_id] = agent.get_fvg_summary()
                elif hasattr(agent, 'get_ob_summary'):
                    summaries[agent_id] = agent.get_ob_summary()
                elif hasattr(agent, 'get_market_structure_summary'):
                    summaries[agent_id] = agent.get_market_structure_summary()
                elif hasattr(agent, 'get_liquidity_summary'):
                    summaries[agent_id] = agent.get_liquidity_summary()
                elif hasattr(agent, 'get_pd_summary'):
                    summaries[agent_id] = agent.get_pd_summary()
                elif hasattr(agent, 'get_ote_summary'):
                    summaries[agent_id] = agent.get_ote_summary()
                elif hasattr(agent, 'get_ml_summary'):
                    summaries[agent_id] = agent.get_ml_summary()
                else:
                    summaries[agent_id] = agent.get_status()
                    
            except Exception as e:
                self.logger.warning(f"Error getting summary for agent {agent_id}: {e}")
        
        return summaries


def main():
    """Main function for running the trading system"""
    parser = argparse.ArgumentParser(description='Advanced ICT/SMC Trading System with Agents')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--mode', choices=['test', 'live', 'demo'], default='test', help='Trading mode')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Trading symbol')
    parser.add_argument('--market-type', choices=['forex', 'crypto'], default='crypto', help='Market type (forex or crypto)')
    parser.add_argument('--status', action='store_true', help='Show system status and exit')
    
    args = parser.parse_args()
    
    # Initialize trading system with market type
    config_override = {'market_type': args.market_type}
    trading_system = TradingSystem(args.config)
    
    # Override market type from command line
    trading_system.config['market_type'] = args.market_type
    
    if args.status:
        # Just show status and exit
        print("🔍 Trading System Status Check")
        print("=" * 40)
        
        # Try to start system briefly to get status
        if trading_system.start():
            time.sleep(2)  # Let system initialize
            
            status = trading_system.get_system_status()
            summaries = trading_system.get_agent_summaries()
            
            print(f"📊 Total Agents: {status['total_agents']}")
            print(f"✅ Active Agents: {status['active_agents']}")
            print(f"📡 Message Bus Stats: {status['message_bus_stats']}")
            
            print("\n🤖 Agent Summaries:")
            print("-" * 30)
            for agent_id, summary in summaries.items():
                print(f"• {agent_id}: {summary.get('last_signal_strength', 0.0):.2f} strength")
            
            trading_system.stop()
        else:
            print("❌ Failed to start trading system")
        
        return
    
    try:
        # Start the trading system
        print(f"🚀 Starting Advanced ICT/SMC Trading System")
        print(f"Mode: {args.mode}")
        print(f"Symbol: {args.symbol}")
        print("=" * 60)
        
        if not trading_system.start():
            print("❌ Failed to start trading system")
            return
        
        # Demo mode - process some sample data
        if args.mode == 'test':
            print("🧪 Running in test mode...")
            
            # Import your existing functions for demo
            try:
                from tradingbot_new import fetch_ohlc, calculate_all_indicators, CONFIG, best_params
                
                # Fetch sample data
                print(f"📊 Fetching data for {args.symbol}...")
                df = fetch_ohlc(args.symbol, '15m', 100)
                
                if not df.empty:
                    # Calculate indicators
                    df = calculate_all_indicators(df, best_params)
                    
                    # Process through agent system
                    market_data = {
                        'df': df,
                        'symbol': args.symbol,
                        'close': df['close'].iloc[-1],
                        'volume': df['volume'].iloc[-1]
                    }
                    
                    recommendation = trading_system.process_symbol(args.symbol, market_data)
                    
                    print(f"\n📈 Trading Recommendation for {args.symbol}:")
                    print("-" * 40)
                    print(f"Action: {recommendation['recommendation'].upper()}")
                    print(f"Confidence: {recommendation['confidence']:.2f}")
                    print(f"Bullish Strength: {recommendation['bullish_strength']:.2f}")
                    print(f"Bearish Strength: {recommendation['bearish_strength']:.2f}")
                    
                    print(f"\n🤖 Agent Contributions:")
                    for contrib in recommendation.get('agent_contributions', []):
                        print(f"  • {contrib['agent_id']}: {contrib['signal_direction']} "
                              f"({contrib['signal_strength']:.2f})")
                    
                    # Show agent summaries
                    print(f"\n📊 Agent Summaries:")
                    summaries = trading_system.get_agent_summaries()
                    for agent_id, summary in summaries.items():
                        strength = summary.get('last_signal_strength', 0.0)
                        print(f"  • {agent_id}: {strength:.2f} signal strength")
                
                else:
                    print(f"❌ No data available for {args.symbol}")
                    
            except ImportError as e:
                print(f"⚠️  Could not import trading bot functions: {e}")
                print("💡 Make sure tradingbot_new.py is in the Python path")
        
        elif args.mode == 'live':
            print("🔴 Live trading mode - Running continuously...")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    # In live mode, the orchestrator handles everything
                    # Just monitor and show status
                    time.sleep(60)
                    
                    status = trading_system.get_system_status()
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - "
                          f"Active agents: {status['active_agents']}/{status['total_agents']}")
                    
            except KeyboardInterrupt:
                print("\n⏹️  Stopping live trading...")
        
        else:  # demo mode
            print("🎭 Demo mode - Simulated trading...")
            # Add demo logic here
            time.sleep(10)
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error running trading system: {e}")
    finally:
        # Always stop the system cleanly
        trading_system.stop()
        print("👋 Trading system shutdown complete")


if __name__ == "__main__":
    main()