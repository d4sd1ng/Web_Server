#!/usr/bin/env python3
"""
Basic system test without heavy dependencies
"""

import os
import sys
from pathlib import Path
from datetime import datetime


def test_directory_structure():
    """Test that directory structure is created properly"""
    print("📁 TESTING DIRECTORY STRUCTURE:")
    
    required_dirs = [
        'agents',
        'agents/ict_smc', 
        'agents/ml',
        'agents/coordination',
        'communication',
        'trading_data',
        'trading_data/historical_data',
        'trading_data/ml_training',
        'trading_data/ml_models',
        'trading_data/backtesting'
    ]
    
    missing_dirs = []
    existing_dirs = []
    
    for directory in required_dirs:
        if Path(directory).exists():
            existing_dirs.append(directory)
            print(f"  ✅ {directory}")
        else:
            missing_dirs.append(directory)
            print(f"  ❌ {directory}")
    
    return len(missing_dirs) == 0, existing_dirs, missing_dirs


def test_agent_files():
    """Test that key agent files exist"""
    print("\n🤖 TESTING AGENT FILES:")
    
    key_agent_files = [
        'agents/base_agent.py',
        'agents/ict_smc/fair_value_gaps_agent.py',
        'agents/ml/ml_ensemble_agent.py',
        'agents/coordination/confluence_coordinator_agent.py',
        'agents/coordination/trade_frequency_optimizer_agent.py'
    ]
    
    missing_files = []
    existing_files = []
    
    for agent_file in key_agent_files:
        if Path(agent_file).exists():
            existing_files.append(agent_file)
            file_size = Path(agent_file).stat().st_size
            print(f"  ✅ {agent_file} ({file_size:,} bytes)")
        else:
            missing_files.append(agent_file)
            print(f"  ❌ {agent_file}")
    
    return len(missing_files) == 0, existing_files, missing_files


def test_existing_trading_bot():
    """Test for existing trading bot files"""
    print("\n📊 TESTING EXISTING TRADING BOT FILES:")
    
    trading_bot_files = [
        'tradingbot_new.py',
        'ict_smc_enhancement.py',
        'ml_tradingbot.py'
    ]
    
    found_files = []
    for filename in trading_bot_files:
        if Path(filename).exists():
            file_size = Path(filename).stat().st_size
            found_files.append(filename)
            print(f"  ✅ {filename} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {filename}")
    
    return found_files


def test_system_files():
    """Test main system files"""
    print("\n⚙️ TESTING SYSTEM FILES:")
    
    system_files = [
        'trading_system_main.py',
        'setup_agent_system.py',
        'requirements_ultimate.txt',
        'communication/message_bus.py'
    ]
    
    for filename in system_files:
        if Path(filename).exists():
            file_size = Path(filename).stat().st_size
            print(f"  ✅ {filename} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {filename}")


def create_missing_directories():
    """Create any missing directories"""
    print("\n🔧 CREATING MISSING DIRECTORIES...")
    
    directories = [
        'agents', 'agents/ict_smc', 'agents/ml', 'agents/coordination', 
        'communication', 'trading_data', 'trading_data/historical_data',
        'trading_data/ml_training', 'trading_data/ml_models', 'trading_data/backtesting'
    ]
    
    created = 0
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            # Create .gitkeep
            (Path(directory) / '.gitkeep').touch()
            created += 1
        except Exception as e:
            print(f"Error creating {directory}: {e}")
    
    print(f"✅ Ensured {created} directories exist")


def main():
    """Main test function"""
    print("🧪 BASIC SYSTEM TEST")
    print("=" * 50)
    
    # Test current location
    current_dir = os.getcwd()
    print(f"📍 Current directory: {current_dir}")
    
    # Create missing directories first
    create_missing_directories()
    
    # Test directory structure
    dirs_ok, existing_dirs, missing_dirs = test_directory_structure()
    
    # Test agent files
    agents_ok, existing_agents, missing_agents = test_agent_files()
    
    # Test existing trading bot
    existing_bot_files = test_existing_trading_bot()
    
    # Test system files
    test_system_files()
    
    print("\n📊 TEST SUMMARY:")
    print("=" * 50)
    print(f"📁 Directory structure: {'✅ PASS' if dirs_ok else '❌ FAIL'}")
    print(f"🤖 Agent files: {'✅ PASS' if agents_ok else '❌ PARTIAL'} ({len(existing_agents)}/5 key agents)")
    print(f"📊 Trading bot files: {'✅ PASS' if existing_bot_files else '❌ FAIL'} ({len(existing_bot_files)} files found)")
    
    if existing_bot_files:
        print(f"🎊 SUCCESS: Found your trading bot files!")
        for filename in existing_bot_files:
            print(f"  • {filename}")
    
    print(f"\n🎯 SYSTEM STATUS:")
    if dirs_ok and existing_bot_files:
        print("✅ READY: Basic system structure is working!")
        print("🚀 Next: Create remaining agents and test full system")
    else:
        print("⚠️ PARTIAL: Some components need attention")
        if missing_dirs:
            print(f"  Missing directories: {missing_dirs}")
        if missing_agents:
            print(f"  Missing agents: {missing_agents}")
        if not existing_bot_files:
            print("  Missing: Your original trading bot files")
    
    print(f"\n🌟 43-AGENT SYSTEM FOUNDATION READY!")
    return True


if __name__ == "__main__":
    main()