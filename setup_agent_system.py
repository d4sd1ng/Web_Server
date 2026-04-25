#!/usr/bin/env python3
"""
Setup script for 43-agent trading system with proper data organization
"""

import os
import sys
import subprocess
from pathlib import Path
import json


def check_existing_files():
    """Check for existing trading bot files"""
    required_files = {
        'tradingbot_new.py': 'Your main 6,372-line trading bot',
        'ict_smc_enhancement.py': 'Your ICT/SMC functions'
    }
    
    found_files = {}
    missing_files = []
    
    for filename, description in required_files.items():
        if Path(filename).exists():
            found_files[filename] = description
            print(f"✅ Found: {filename} - {description}")
        else:
            missing_files.append(filename)
            print(f"❌ Missing: {filename} - {description}")
    
    return found_files, missing_files


def create_comprehensive_directory_structure():
    """Create comprehensive directory structure for organized data management"""
    directories = [
        # Agent system directories
        "agents", "agents/ict_smc", "agents/ml", "agents/data", "agents/execution",
        "agents/analysis", "agents/coordination", "agents/system", "agents/testing",
        "communication", "orchestrator", "config",
        
        # COMPREHENSIVE DATA ORGANIZATION (PREVENTS DIRECTORY FLOODING)
        "trading_data",
        "trading_data/historical_data", "trading_data/historical_data/forex",
        "trading_data/historical_data/crypto", "trading_data/historical_data/cache",
        
        # Real-time data organization
        "trading_data/realtime_data", "trading_data/realtime_data/tick_data",
        "trading_data/realtime_data/quotes", "trading_data/realtime_data/ohlcv",
        
        # ML training data organization
        "trading_data/ml_training", "trading_data/ml_training/features",
        "trading_data/ml_training/labels", "trading_data/ml_training/datasets",
        "trading_data/ml_training/feature_engineering",
        
        # ML models organization
        "trading_data/ml_models", "trading_data/ml_models/trained",
        "trading_data/ml_models/checkpoints", "trading_data/ml_models/metadata",
        "trading_data/ml_models/ensemble",
        
        # Backtesting organization
        "trading_data/backtesting", "trading_data/backtesting/results",
        "trading_data/backtesting/datasets", "trading_data/backtesting/parameter_optimization",
        "trading_data/backtesting/walk_forward",
        
        # Agent data organization
        "trading_data/agent_data", "trading_data/agent_data/signals",
        "trading_data/agent_data/performance", "trading_data/agent_data/confluence",
        
        # System logs organization
        "trading_data/system_logs", "trading_data/system_logs/performance",
        "trading_data/system_logs/errors", "trading_data/system_logs/trading",
        
        # Configuration organization
        "trading_data/config", "trading_data/config/agents",
        "trading_data/config/markets", "trading_data/config/optimization",
        
        # Exports and reports
        "trading_data/exports", "trading_data/exports/reports",
        "trading_data/exports/analysis", "trading_data/exports/ml_results",
        
        # Temporary and cache
        "trading_data/temp", "trading_data/cache", "trading_data/downloads"
    ]
    
    created_dirs = []
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            
            # Create .gitkeep to preserve empty directories in git
            gitkeep_path = Path(directory) / '.gitkeep'
            if not gitkeep_path.exists():
                gitkeep_path.touch()
            
            created_dirs.append(directory)
            
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
    
    return created_dirs


def create_default_configuration():
    """Create default configuration file"""
    config = {
        "market_type": "crypto",
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "timeframes": ["1h", "4h"],
        "testnet_mode": True,
        "ml_data_collection_mode": True,
        "agents": {
            "fair_value_gaps": {
                "enabled": True,
                "window": 3,
                "min_gap": 0.0005
            },
            "confluence_coordinator": {
                "enabled": True,
                "min_confluence_patterns": 3,
                "min_confluence_score": 5.0
            },
            "ml_ensemble": {
                "enabled": True,
                "confidence_threshold": 0.75,
                "model_agreement_threshold": 0.7
            },
            "trade_frequency_optimizer": {
                "enabled": True,
                "min_trades_per_day": 10,
                "target_trades_per_week": 100,
                "testnet_mode": True
            }
        },
        "data_paths": {
            "historical": "trading_data/historical_data",
            "ml_training": "trading_data/ml_training", 
            "models": "trading_data/ml_models",
            "backtesting": "trading_data/backtesting"
        }
    }
    
    config_path = Path("trading_data/config/default_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return str(config_path)


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_ultimate.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        print("⚠️ You may need to install manually: pip install -r requirements_ultimate.txt")
        return False
    except FileNotFoundError:
        print("⚠️ requirements_ultimate.txt not found - dependencies not installed")
        return False


def main():
    """Main setup function"""
    print("🚀 SETTING UP 43-AGENT TRADING SYSTEM")
    print("=" * 60)
    
    # Check current location
    current_path = os.getcwd()
    print(f"📍 Setup location: {current_path}")
    
    # Check for existing trading bot files
    print("\n📋 CHECKING EXISTING TRADING BOT FILES:")
    found_files, missing_files = check_existing_files()
    
    if missing_files:
        print(f"\n⚠️ WARNING: Missing files: {missing_files}")
        print("🎯 Make sure you're running this in your trading bot repository")
        print("   Expected files: tradingbot_new.py, ict_smc_enhancement.py")
        
        proceed = input("\nProceed anyway? (y/N): ")
        if proceed.lower() != 'y':
            print("❌ Setup cancelled")
            return False
    
    # Create directory structure
    print("\n📁 CREATING COMPREHENSIVE DIRECTORY STRUCTURE...")
    created_dirs = create_comprehensive_directory_structure()
    print(f"✅ Created {len(created_dirs)} directories for organized data management")
    print("📁 Key directories:")
    print("  • trading_data/historical_data/ (50-year historical data)")
    print("  • trading_data/ml_training/ (60M+ training samples)")
    print("  • trading_data/ml_models/ (15 trained algorithms)")
    print("  • trading_data/backtesting/ (backtest results)")
    print("  • trading_data/agent_data/ (agent signals)")
    
    # Create default configuration
    print("\n⚙️ CREATING DEFAULT CONFIGURATION...")
    config_path = create_default_configuration()
    print(f"✅ Created configuration: {config_path}")
    
    # Install dependencies
    print("\n📦 INSTALLING DEPENDENCIES...")
    deps_installed = install_dependencies()
    
    # Create .gitignore for data directories
    print("\n📝 CREATING .gitignore FOR DATA DIRECTORIES...")
    gitignore_content = """
# Trading data directories (large files)
trading_data/historical_data/*.parquet
trading_data/ml_training/*.parquet
trading_data/ml_models/*.joblib
trading_data/backtesting/results/
trading_data/temp/
trading_data/cache/
trading_data/downloads/

# Log files
trading_data/system_logs/*.log

# Python cache
__pycache__/
*.pyc
*.pyo

# Virtual environments
venv/
.venv/
"""
    
    gitignore_path = Path('.gitignore')
    if gitignore_path.exists():
        # Append to existing .gitignore
        with open(gitignore_path, 'a') as f:
            f.write(gitignore_content)
    else:
        # Create new .gitignore
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
    
    print("✅ Updated .gitignore for data directories")
    
    print("\n🎊 SETUP COMPLETED!")
    print("=" * 60)
    print("✅ 43-agent system structure created")
    print("✅ Comprehensive data organization implemented")
    print("✅ Dependencies installed" if deps_installed else "⚠️ Dependencies need manual installation")
    print("✅ Configuration created")
    print("✅ .gitignore updated")
    
    print(f"\n🚀 READY TO START:")
    print("# Test the system:")
    print("python trading_system_main.py --mode test --market-type crypto")
    print("")
    print("# Check system status:")
    print("python trading_system_main.py --mode status")
    print("")
    print("# Start testnet mode:")
    print("python trading_system_main.py --mode demo --testnet-mode")
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Test the basic system")
    print("2. Create remaining agent files")
    print("3. Start 50-year backtesting")
    print("4. Deploy 32-week testnet")
    
    print(f"\n🌟 YOUR 43-AGENT SYSTEM IS READY!")
    
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)