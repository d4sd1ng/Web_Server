#!/usr/bin/env python3
"""
Create complete 43-agent system directly in your trading bot repository
Run this script in your actual trading bot directory: /mnt/g/Projects/trading_bot
"""

import os
import sys
from pathlib import Path

def create_complete_directory_structure():
    """Create comprehensive directory structure for organized data management"""
    directories = [
        # Agent system directories
        "agents",
        "agents/ict_smc",
        "agents/ml", 
        "agents/data",
        "agents/execution",
        "agents/analysis",
        "agents/coordination",
        "agents/system",
        "agents/testing",
        "communication",
        "orchestrator",
        "config",
        
        # Comprehensive data organization (PREVENTS DIRECTORY FLOODING)
        "trading_data",
        "trading_data/historical_data",
        "trading_data/historical_data/forex",
        "trading_data/historical_data/crypto",
        "trading_data/historical_data/cache",
        
        # Real-time data organization
        "trading_data/realtime_data",
        "trading_data/realtime_data/tick_data",
        "trading_data/realtime_data/quotes",
        "trading_data/realtime_data/ohlcv",
        
        # ML training data organization
        "trading_data/ml_training",
        "trading_data/ml_training/features", 
        "trading_data/ml_training/labels",
        "trading_data/ml_training/datasets",
        "trading_data/ml_training/feature_engineering",
        
        # ML models organization
        "trading_data/ml_models",
        "trading_data/ml_models/trained",
        "trading_data/ml_models/checkpoints",
        "trading_data/ml_models/metadata",
        "trading_data/ml_models/ensemble",
        
        # Backtesting organization
        "trading_data/backtesting",
        "trading_data/backtesting/results",
        "trading_data/backtesting/datasets", 
        "trading_data/backtesting/parameter_optimization",
        "trading_data/backtesting/walk_forward",
        
        # Agent data organization
        "trading_data/agent_data",
        "trading_data/agent_data/signals",
        "trading_data/agent_data/performance",
        "trading_data/agent_data/confluence",
        
        # System logs organization
        "trading_data/system_logs",
        "trading_data/system_logs/performance",
        "trading_data/system_logs/errors",
        "trading_data/system_logs/trading",
        
        # Configuration organization
        "trading_data/config",
        "trading_data/config/agents",
        "trading_data/config/markets",
        "trading_data/config/optimization",
        
        # Exports and reports
        "trading_data/exports",
        "trading_data/exports/reports",
        "trading_data/exports/analysis",
        "trading_data/exports/ml_results",
        
        # Temporary and cache
        "trading_data/temp",
        "trading_data/cache",
        "trading_data/downloads"
    ]
    
    created_dirs = []
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            created_dirs.append(directory)
            
            # Create .gitkeep files to preserve empty directories
            gitkeep_path = Path(directory) / '.gitkeep'
            if not gitkeep_path.exists():
                gitkeep_path.touch()
                
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
    
    return created_dirs

def create_directory_documentation():
    """Create README files explaining directory purposes"""
    directory_docs = {
        'trading_data': "# Trading Data Organization\n\nThis directory contains ALL trading-related data in organized structure to prevent directory flooding.\n\n- historical_data/: 50-year historical market data\n- ml_training/: ML training datasets (60M+ samples)\n- ml_models/: Trained ML models (15 algorithms)\n- backtesting/: Backtest results and analysis\n- agent_data/: Agent signals and performance\n- system_logs/: System logging (auto-cleanup)",
        'trading_data/historical_data': "# Historical Data Storage\n\n- forex/: 50-year forex data (1975+) organized by symbol\n- crypto/: 16-year crypto data (2009+) organized by symbol\n- cache/: Processed data cache for faster access",
        'trading_data/ml_training': "# ML Training Data\n\n- features/: Engineered features from all 43 agents\n- labels/: Trade outcomes and targets\n- datasets/: Complete training datasets (60M+ samples)\n- feature_engineering/: Feature analysis and selection",
        'trading_data/ml_models': "# ML Models Storage\n\n- trained/: Final trained models organized by algorithm\n- checkpoints/: Training checkpoints for neural networks\n- ensemble/: Ensemble model combinations\n- metadata/: Model performance and configuration data",
        'trading_data/backtesting': "# Backtesting Results\n\n- results/: Individual backtest results organized by date\n- parameter_optimization/: Parameter sweep results\n- walk_forward/: Walk-forward analysis results\n- datasets/: Prepared backtesting datasets"
    }
    
    for dir_path, content in directory_docs.items():
        try:
            readme_path = Path(dir_path) / 'README.md'
            readme_path.parent.mkdir(parents=True, exist_ok=True)
            with open(readme_path, 'w') as f:
                f.write(content)
        except Exception as e:
            print(f"Could not create README for {dir_path}: {e}")

def check_existing_files():
    """Check what files already exist"""
    current_dir = Path('.')
    existing_files = {
        'tradingbot_new.py': current_dir / 'tradingbot_new.py',
        'ict_smc_enhancement.py': current_dir / 'ict_smc_enhancement.py', 
        'ml_tradingbot.py': current_dir / 'ml_tradingbot.py',
        '.env': current_dir / '.env'
    }
    
    found_files = {}
    for name, path in existing_files.items():
        if path.exists():
            found_files[name] = str(path)
            print(f"✅ Found existing file: {name}")
        else:
            print(f"❌ Missing file: {name}")
    
    return found_files

def main():
    print("🚀 CREATING 43-AGENT SYSTEM IN YOUR TRADING BOT REPOSITORY")
    print("=" * 60)
    
    # Check current location
    current_path = os.getcwd()
    print(f"📍 Current directory: {current_path}")
    
    # Check for existing trading bot files
    print("\n📋 CHECKING EXISTING FILES:")
    existing_files = check_existing_files()
    
    if 'tradingbot_new.py' not in existing_files:
        print("\n❌ ERROR: tradingbot_new.py not found!")
        print("🎯 Please run this script in your actual trading bot repository")
        print("   Expected location: /mnt/g/Projects/trading_bot")
        return False
    
    print(f"\n✅ CONFIRMED: You're in the right trading bot repository!")
    print(f"📄 Found tradingbot_new.py: {existing_files['tradingbot_new.py']}")
    
    # Create directory structure
    print("\n📁 CREATING COMPREHENSIVE DIRECTORY STRUCTURE...")
    created_dirs = create_complete_directory_structure()
    print(f"✅ Created {len(created_dirs)} directories for organized data management")
    
    # Create documentation
    print("\n📚 CREATING DIRECTORY DOCUMENTATION...")
    create_directory_documentation()
    print("✅ Created README files for major directories")
    
    print("\n🎊 DIRECTORY STRUCTURE SETUP COMPLETE!")
    print("=" * 60)
    print("📁 Your repository now has proper data organization:")
    print("✅ trading_data/ - All data organized here (prevents flooding)")
    print("✅ agents/ - Ready for 43 agent files")
    print("✅ communication/ - Message bus system")
    print("✅ orchestrator/ - Agent coordination")
    print("")
    print("🔧 NEXT STEPS:")
    print("1. Copy/create the 43 agent files")
    print("2. Create trading_system_main.py") 
    print("3. Install requirements_ultimate.txt")
    print("4. Test the complete system")
    print("")
    print("🎯 Ready for agent system creation!")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🚀 READY TO PROCEED WITH AGENT CREATION!")
    else:
        print("\n❌ PLEASE RUN IN YOUR ACTUAL TRADING BOT REPOSITORY")
        sys.exit(1)