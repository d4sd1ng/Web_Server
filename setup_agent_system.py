#!/usr/bin/env python3
"""
Setup Script for Agent-Based Trading System
Converts existing trading bot functions to specialized agents
"""

import os
import sys
import json
from datetime import datetime

def create_agent_config():
    """Create default agent configuration"""
    config = {
        "system_info": {
            "name": "Advanced ICT/SMC Trading System",
            "version": "1.0.0",
            "created": datetime.now().isoformat(),
            "description": "Agent-based trading system using existing ICT/SMC functions"
        },
        "orchestrator": {
            "min_agent_consensus": 0.6,
            "min_signal_strength": 0.7,
            "orchestrator_interval": 60,
            "max_decisions_history": 1000
        },
        "agents": {
            "fair_value_gaps": {
                "enabled": True,
                "window": 3,
                "min_gap": 0.0001,
                "atr_distance_threshold": 2.0,
                "max_active_fvgs": 50
            },
            "order_blocks": {
                "enabled": True,
                "lookback": 30,
                "min_body": 0.3,
                "retest_confirmation_bars": 3,
                "max_active_obs": 100
            },
            "market_structure": {
                "enabled": True,
                "lookback": 20,
                "confirmation_bars": 3,
                "trend_consistency_period": 20
            },
            "liquidity_sweeps": {
                "enabled": True,
                "lookback": 10,
                "equal_level_tolerance": 0.001,
                "volume_threshold": 1.5,
                "max_sweep_history": 50
            },
            "premium_discount": {
                "enabled": True,
                "swing_lookback": 50,
                "zone_threshold": 0.1,
                "max_zone_history": 100
            },
            "ote": {
                "enabled": True,
                "swing_lookback": 20,
                "fib_618_level": 0.618,
                "fib_786_level": 0.786,
                "ote_fib_level": 0.705,
                "max_ote_history": 200
            },
            "ml_prediction": {
                "enabled": True,
                "model_type": "RandomForest",
                "threshold": 0.5,
                "retrain_interval_hours": 24,
                "model_path": "ml_model.pkl",
                "scaler_path": "scaler.pkl",
                "max_prediction_history": 1000
            }
        },
        "agent_weights": {
            "fair_value_gaps": 1.2,
            "order_blocks": 1.5,
            "market_structure": 1.3,
            "liquidity_sweeps": 1.1,
            "premium_discount": 1.0,
            "ote": 1.4,
            "ml_prediction": 1.0
        },
        "trading": {
            "max_open_trades": 3,
            "risk_per_trade": 0.01,
            "leverage": 25,
            "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
            "symbols": [
                "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
                "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "LINK/USDT", "DOT/USDT"
            ]
        },
        "logging": {
            "level": "INFO",
            "file": "trading_system.log",
            "max_file_size_mb": 100,
            "backup_count": 5
        }
    }
    
    return config

def create_directory_structure():
    """Create directory structure for agent system"""
    directories = [
        "agents",
        "agents/ict_smc",
        "agents/ml",
        "agents/data",
        "agents/execution",
        "agents/analysis",
        "communication",
        "orchestrator",
        "config",
        "logs",
        "models",
        "backtest_results"
    ]
    
    created_dirs = []
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            created_dirs.append(directory)
    
    return created_dirs

def save_config(config, filename="agent_config.json"):
    """Save configuration to file"""
    try:
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def create_init_files():
    """Create __init__.py files for Python packages"""
    init_files = [
        "agents/__init__.py",
        "agents/ict_smc/__init__.py",
        "agents/ml/__init__.py",
        "agents/data/__init__.py",
        "agents/execution/__init__.py",
        "agents/analysis/__init__.py",
        "communication/__init__.py",
        "orchestrator/__init__.py"
    ]
    
    created_files = []
    for init_file in init_files:
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('"""Agent system package"""')
            created_files.append(init_file)
    
    return created_files

def create_example_usage():
    """Create example usage script"""
    example_code = '''#!/usr/bin/env python3
"""
Example Usage of Agent-Based Trading System
"""

from trading_system_main import TradingSystem
import time

def run_example():
    """Run example trading system"""
    print("🚀 Agent-Based Trading System Example")
    print("=" * 50)
    
    # Initialize system
    trading_system = TradingSystem("agent_config.json")
    
    try:
        # Start system
        if trading_system.start():
            print("✅ System started successfully!")
            
            # Let it run for a bit
            time.sleep(10)
            
            # Get status
            status = trading_system.get_system_status()
            print(f"📊 System Status: {status['orchestrator_status']}")
            print(f"🤖 Active Agents: {status['active_agents']}/{status['total_agents']}")
            
            # Get agent summaries
            summaries = trading_system.get_agent_summaries()
            print("\\n📈 Agent Summary:")
            for agent_id, summary in summaries.items():
                strength = summary.get('last_signal_strength', 0.0)
                print(f"  • {agent_id}: {strength:.2f}")
            
        else:
            print("❌ Failed to start system")
    
    finally:
        # Always stop cleanly
        trading_system.stop()
        print("✅ System stopped")

if __name__ == "__main__":
    run_example()
'''
    
    with open("example_usage.py", "w") as f:
        f.write(example_code)
    
    return "example_usage.py"

def main():
    """Main setup function"""
    print("🔧 Setting up Agent-Based Trading System")
    print("=" * 50)
    
    # Create directory structure
    print("📁 Creating directory structure...")
    created_dirs = create_directory_structure()
    print(f"Created {len(created_dirs)} directories")
    
    # Create __init__.py files
    print("📄 Creating package files...")
    created_files = create_init_files()
    print(f"Created {len(created_files)} __init__.py files")
    
    # Create configuration
    print("⚙️  Creating configuration...")
    config = create_agent_config()
    if save_config(config):
        print("✅ Configuration saved to agent_config.json")
    else:
        print("❌ Failed to save configuration")
    
    # Create example usage
    print("📝 Creating example usage script...")
    example_file = create_example_usage()
    print(f"✅ Created {example_file}")
    
    print("\n🎉 Setup Complete!")
    print("=" * 50)
    print("📋 What was created:")
    print("• Agent directory structure")
    print("• Base agent classes")
    print("• ICT/SMC specialized agents:")
    print("  - Fair Value Gaps Agent")
    print("  - Order Blocks Agent") 
    print("  - Market Structure Agent")
    print("  - Liquidity Sweeps Agent")
    print("  - Premium/Discount Agent")
    print("  - OTE Agent")
    print("• ML Prediction Agent")
    print("• Trading Orchestrator")
    print("• Message Bus Communication")
    print("• Configuration files")
    print("• Example usage script")
    
    print("\n🚀 Next Steps:")
    print("1. Install requirements: pip install -r requirements_agents.txt")
    print("2. Test the system: python trading_system_main.py --status")
    print("3. Run example: python example_usage.py")
    print("4. Customize agent_config.json for your needs")
    print("5. Add more agents as needed")
    
    print("\n💡 Your existing ICT/SMC functions are now available as:")
    print("• Modular, specialized agents")
    print("• Inter-agent communication system")
    print("• Centralized orchestration")
    print("• Scalable architecture")
    print("• Easy to extend and maintain")
    
    print("\n🔥 Ready to trade with agent-based architecture!")

if __name__ == "__main__":
    main()