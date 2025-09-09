#!/usr/bin/env python3
"""
Test script for ICT/SMC Trading Agents
Verifies that all agents can be instantiated and work correctly
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import traceback
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def create_sample_data(n_bars=100):
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    
    # Generate price data with some trend
    base_price = 100.0
    price_changes = np.random.normal(0, 0.5, n_bars)
    prices = [base_price]
    
    for change in price_changes:
        prices.append(prices[-1] + change)
    
    prices = np.array(prices[1:])
    
    # Create OHLCV data
    data = []
    for i, close in enumerate(prices):
        # Add some randomness to create realistic candles
        high_offset = np.random.uniform(0, 2)
        low_offset = np.random.uniform(0, 2)
        open_offset = np.random.uniform(-0.5, 0.5)
        
        open_price = close + open_offset
        high = max(open_price, close) + high_offset
        low = min(open_price, close) - low_offset
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    # Create DataFrame with datetime index
    df = pd.DataFrame(data)
    df.index = pd.date_range(start=datetime.now() - timedelta(hours=n_bars), 
                            periods=n_bars, freq='H')
    
    return df

def test_agent_instantiation():
    """Test that all agents can be instantiated without errors."""
    print("=" * 60)
    print("TESTING AGENT INSTANTIATION")
    print("=" * 60)
    
    agents_to_test = [
        ('BOSCHOCHAgent', 'agents.ict_smc.bos_choch_agent', 'BOSCHOCHAgent'),
        ('BreakerBlocksAgent', 'agents.ict_smc.breaker_blocks_agent', 'BreakerBlocksAgent'),
        ('DisplacementAgent', 'agents.ict_smc.displacement_agent', 'DisplacementAgent'),
        ('FairValueGapsAgent', 'agents.ict_smc.fair_value_gaps_agent', 'FairValueGapsAgent'),
        ('OrderBlocksAgent', 'agents.ict_smc.order_blocks_agent', 'OrderBlocksAgent'),
    ]
    
    results = []
    
    for agent_name, module_path, class_name in agents_to_test:
        try:
            print(f"\n[1/4] Testing {agent_name} instantiation...")
            
            # Import the module
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Test instantiation with default config
            agent = agent_class()
            print(f"    ✅ Default instantiation successful")
            
            # Test instantiation with custom config
            config = {
                'lookback_period': 25,
                'min_pattern_strength': 0.6,
                'volume_threshold': 1.8
            }
            agent_with_config = agent_class(config)
            print(f"    ✅ Custom config instantiation successful")
            
            # Test basic methods
            status = agent.get_status()
            print(f"    ✅ get_status() works: {agent.name} is {'active' if status['is_active'] else 'inactive'}")
            
            results.append((agent_name, True, agent, None))
            print(f"    ✅ {agent_name} passed all instantiation tests")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"    ❌ {agent_name} failed: {error_msg}")
            results.append((agent_name, False, None, error_msg))
    
    return results

def test_agent_functionality(instantiation_results):
    """Test core functionality of successfully instantiated agents."""
    print("\n" + "=" * 60)
    print("TESTING AGENT FUNCTIONALITY") 
    print("=" * 60)
    
    # Create sample data
    print("\n[2/4] Creating sample market data...")
    df = create_sample_data(200)
    print(f"    ✅ Created {len(df)} bars of sample data")
    print(f"    📊 Price range: {df['low'].min():.2f} - {df['high'].max():.2f}")
    
    functionality_results = []
    
    for agent_name, instantiated, agent, error in instantiation_results:
        if not instantiated:
            print(f"\n[3/4] Skipping {agent_name} (instantiation failed)")
            functionality_results.append((agent_name, False, f"Skipped: {error}"))
            continue
        
        print(f"\n[3/4] Testing {agent_name} functionality...")
        
        try:
            # Test process_data method
            print(f"    🔄 Testing process_data()...")
            analysis = agent.process_data(df)
            
            if 'error' in analysis:
                print(f"    ❌ process_data() returned error: {analysis['error']}")
                functionality_results.append((agent_name, False, f"process_data error: {analysis['error']}"))
                continue
            else:
                print(f"    ✅ process_data() successful")
                print(f"    📊 Analysis keys: {list(analysis.keys())}")
            
            # Test get_signal_strength method
            print(f"    🔄 Testing get_signal_strength()...")
            strength = agent.get_signal_strength(df)
            print(f"    ✅ Signal strength: {strength:.3f}")
            
            # Test get_signals method (inherited from base class)
            print(f"    🔄 Testing get_signals()...")
            signals = agent.get_signals(df)
            
            print(f"    ✅ Signals generated:")
            print(f"        - Agent: {signals['agent_name']}")
            print(f"        - Valid: {signals['is_valid']}")
            print(f"        - Strength: {signals['signal_strength']:.3f}")
            print(f"        - Confidence: {signals['confidence']:.3f}")
            
            # Test with smaller dataset (edge case)
            print(f"    🔄 Testing with small dataset...")
            small_df = df.head(10)
            small_analysis = agent.process_data(small_df)
            small_strength = agent.get_signal_strength(small_df)
            print(f"    ✅ Small dataset handled (strength: {small_strength:.3f})")
            
            functionality_results.append((agent_name, True, "All functionality tests passed"))
            print(f"    ✅ {agent_name} passed all functionality tests")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"    ❌ {agent_name} functionality test failed: {error_msg}")
            print(f"    📋 Traceback: {traceback.format_exc()}")
            functionality_results.append((agent_name, False, error_msg))
    
    return functionality_results

def test_agent_integration():
    """Test integration of multiple agents working together."""
    print("\n" + "=" * 60)
    print("TESTING AGENT INTEGRATION")
    print("=" * 60)
    
    try:
        print("\n[4/4] Testing multi-agent integration...")
        
        # Create sample data
        df = create_sample_data(150)
        
        # Import and instantiate all agents
        agents = {}
        
        agent_configs = {
            'bos_choch': {'lookback_period': 20, 'swing_lookback': 8},
            'breaker_blocks': {'lookback_period': 25, 'volume_multiplier': 1.3},
            'displacement': {'min_body_ratio': 0.6, 'atr_multiplier': 1.8},
            'fair_value_gaps': {'min_gap_size': 0.0005, 'gap_timeout_bars': 40},
            'order_blocks': {'min_displacement_ratio': 1.8, 'volume_threshold': 1.3}
        }
        
        # Instantiate agents
        from agents.ict_smc.bos_choch_agent import BOSCHOCHAgent
        from agents.ict_smc.breaker_blocks_agent import BreakerBlocksAgent
        from agents.ict_smc.displacement_agent import DisplacementAgent
        from agents.ict_smc.fair_value_gaps_agent import FairValueGapsAgent
        from agents.ict_smc.order_blocks_agent import OrderBlocksAgent
        
        agents = {
            'bos_choch': BOSCHOCHAgent(agent_configs['bos_choch']),
            'breaker_blocks': BreakerBlocksAgent(agent_configs['breaker_blocks']),
            'displacement': DisplacementAgent(agent_configs['displacement']),
            'fair_value_gaps': FairValueGapsAgent(agent_configs['fair_value_gaps']),
            'order_blocks': OrderBlocksAgent(agent_configs['order_blocks'])
        }
        
        print(f"    ✅ All {len(agents)} agents instantiated successfully")
        
        # Run analysis on all agents
        all_signals = {}
        combined_strength = 0.0
        
        for name, agent in agents.items():
            signals = agent.get_signals(df, symbol="TEST/USDT")
            all_signals[name] = signals
            combined_strength += signals['signal_strength']
            print(f"    📊 {name}: strength={signals['signal_strength']:.3f}, valid={signals['is_valid']}")
        
        avg_strength = combined_strength / len(agents)
        print(f"    📈 Average signal strength: {avg_strength:.3f}")
        
        # Test consensus building
        valid_signals = [s for s in all_signals.values() if s['is_valid']]
        consensus_strength = len(valid_signals) / len(agents)
        
        print(f"    🤝 Consensus: {len(valid_signals)}/{len(agents)} agents agree (strength: {consensus_strength:.2%})")
        
        # Test agent status
        print(f"    🔄 Testing agent management...")
        for name, agent in agents.items():
            status = agent.get_status()
            print(f"        - {name}: {status['signal_count']} signals in history")
        
        print(f"    ✅ Integration test completed successfully")
        return True
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"    ❌ Integration test failed: {error_msg}")
        print(f"    📋 Traceback: {traceback.format_exc()}")
        return False

def print_final_results(instantiation_results, functionality_results, integration_success):
    """Print comprehensive test results."""
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)
    
    # Instantiation results
    print(f"\n📋 INSTANTIATION TEST RESULTS:")
    instantiation_passed = 0
    for agent_name, passed, agent, error in instantiation_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status} {agent_name}")
        if not passed:
            print(f"        Error: {error}")
        else:
            instantiation_passed += 1
    
    print(f"    Summary: {instantiation_passed}/{len(instantiation_results)} agents instantiated successfully")
    
    # Functionality results
    print(f"\n📋 FUNCTIONALITY TEST RESULTS:")
    functionality_passed = 0
    for agent_name, passed, message in functionality_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status} {agent_name}")
        if not passed:
            print(f"        Error: {message}")
        else:
            functionality_passed += 1
    
    print(f"    Summary: {functionality_passed}/{len(functionality_results)} agents functioning correctly")
    
    # Integration results
    print(f"\n📋 INTEGRATION TEST RESULTS:")
    integration_status = "✅ PASS" if integration_success else "❌ FAIL"
    print(f"    {integration_status} Multi-agent integration")
    
    # Overall results
    print(f"\n🎯 OVERALL RESULTS:")
    total_tests = len(instantiation_results) + len(functionality_results) + 1  # +1 for integration
    passed_tests = instantiation_passed + functionality_passed + (1 if integration_success else 0)
    
    print(f"    Tests passed: {passed_tests}/{total_tests}")
    print(f"    Success rate: {passed_tests/total_tests:.1%}")
    
    if passed_tests == total_tests:
        print(f"    🎉 ALL TESTS PASSED! The ICT/SMC agent system is working correctly.")
    else:
        print(f"    ⚠️  Some tests failed. Review the errors above for details.")
    
    return passed_tests == total_tests

def main():
    """Main test function."""
    print("ICT/SMC TRADING AGENTS TEST SUITE")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test 1: Agent instantiation
        instantiation_results = test_agent_instantiation()
        
        # Test 2: Agent functionality
        functionality_results = test_agent_functionality(instantiation_results)
        
        # Test 3: Agent integration
        integration_success = test_agent_integration()
        
        # Print final results
        all_passed = print_final_results(instantiation_results, functionality_results, integration_success)
        
        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n❌ Test suite failed with unexpected error:")
        print(f"   {type(e).__name__}: {str(e)}")
        print(f"\n📋 Full traceback:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()