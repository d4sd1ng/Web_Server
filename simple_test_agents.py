#!/usr/bin/env python3
"""
Simple test script for ICT/SMC Trading Agents
Tests basic instantiation without external dependencies
"""
import sys
import os
import traceback
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_agent_imports():
    """Test that all agents can be imported without errors."""
    print("=" * 60)
    print("TESTING AGENT IMPORTS")
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
            print(f"\n[1/3] Testing {agent_name} import...")
            
            # Import the module
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            print(f"    ✅ Import successful")
            
            # Test instantiation with default config
            agent = agent_class()
            print(f"    ✅ Default instantiation successful")
            
            # Test basic properties
            print(f"    📊 Agent name: {agent.name}")
            print(f"    📊 Is active: {agent.is_active}")
            print(f"    📊 Has config: {bool(agent.config)}")
            
            results.append((agent_name, True, None))
            print(f"    ✅ {agent_name} passed all import tests")
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"    ❌ {agent_name} failed: {error_msg}")
            print(f"    📋 Traceback: {traceback.format_exc()}")
            results.append((agent_name, False, error_msg))
    
    return results

def test_base_agent():
    """Test the base agent class."""
    print("\n" + "=" * 60)
    print("TESTING BASE AGENT CLASS")
    print("=" * 60)
    
    try:
        print("\n[2/3] Testing BasePatternAgent...")
        from agents.base_agent import BasePatternAgent, ICTSMCAgent
        
        print("    ✅ Base agent classes imported successfully")
        
        # Test that we can't instantiate abstract base class
        try:
            abstract_agent = ICTSMCAgent()
            print("    ❌ Abstract class should not be instantiable")
            return False
        except TypeError as e:
            print("    ✅ Abstract class correctly prevents instantiation")
        
        # Test BasePatternAgent (should also be abstract)
        try:
            pattern_agent = BasePatternAgent()
            print("    ❌ BasePatternAgent should be abstract")
            return False
        except TypeError as e:
            print("    ✅ BasePatternAgent correctly prevents instantiation")
        
        print("    ✅ Base agent class tests passed")
        return True
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"    ❌ Base agent test failed: {error_msg}")
        print(f"    📋 Traceback: {traceback.format_exc()}")
        return False

def test_agent_methods():
    """Test that agents have required methods."""
    print("\n" + "=" * 60)
    print("TESTING AGENT METHODS")
    print("=" * 60)
    
    try:
        print("\n[3/3] Testing agent method signatures...")
        
        # Import one agent for testing
        from agents.ict_smc.bos_choch_agent import BOSCHOCHAgent
        
        agent = BOSCHOCHAgent()
        
        # Check required methods exist
        required_methods = ['process_data', 'get_signal_strength', 'get_signals', 'get_status']
        
        for method_name in required_methods:
            if hasattr(agent, method_name):
                method = getattr(agent, method_name)
                print(f"    ✅ {method_name}: {type(method)}")
            else:
                print(f"    ❌ Missing method: {method_name}")
                return False
        
        # Test method signatures (without calling them)
        import inspect
        
        # Check process_data signature
        sig = inspect.signature(agent.process_data)
        params = list(sig.parameters.keys())
        expected_params = ['df', 'symbol']
        
        if all(param in params for param in expected_params):
            print(f"    ✅ process_data signature correct: {params}")
        else:
            print(f"    ❌ process_data signature incorrect: {params}")
            return False
        
        # Check get_signal_strength signature
        sig = inspect.signature(agent.get_signal_strength)
        params = list(sig.parameters.keys())
        expected_params = ['df', 'symbol']
        
        if all(param in params for param in expected_params):
            print(f"    ✅ get_signal_strength signature correct: {params}")
        else:
            print(f"    ❌ get_signal_strength signature incorrect: {params}")
            return False
        
        print("    ✅ All method signature tests passed")
        return True
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"    ❌ Method test failed: {error_msg}")
        print(f"    📋 Traceback: {traceback.format_exc()}")
        return False

def print_final_results(import_results, base_agent_success, method_test_success):
    """Print comprehensive test results."""
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)
    
    # Import results
    print(f"\n📋 IMPORT TEST RESULTS:")
    import_passed = 0
    for agent_name, passed, error in import_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status} {agent_name}")
        if not passed:
            print(f"        Error: {error}")
        else:
            import_passed += 1
    
    print(f"    Summary: {import_passed}/{len(import_results)} agents imported successfully")
    
    # Base agent results
    print(f"\n📋 BASE AGENT TEST RESULTS:")
    base_status = "✅ PASS" if base_agent_success else "❌ FAIL"
    print(f"    {base_status} Base agent class structure")
    
    # Method test results
    print(f"\n📋 METHOD TEST RESULTS:")
    method_status = "✅ PASS" if method_test_success else "❌ FAIL"
    print(f"    {method_status} Agent method signatures")
    
    # Overall results
    print(f"\n🎯 OVERALL RESULTS:")
    total_tests = len(import_results) + 2  # +2 for base agent and method tests
    passed_tests = import_passed + (1 if base_agent_success else 0) + (1 if method_test_success else 0)
    
    print(f"    Tests passed: {passed_tests}/{total_tests}")
    print(f"    Success rate: {passed_tests/total_tests:.1%}")
    
    if passed_tests == total_tests:
        print(f"    🎉 ALL TESTS PASSED! The agent structure is correct.")
        print(f"    💡 Original instantiation errors have been fixed!")
    else:
        print(f"    ⚠️  Some tests failed. Review the errors above.")
    
    return passed_tests == total_tests

def main():
    """Main test function."""
    print("ICT/SMC TRADING AGENTS - SIMPLE TEST SUITE")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing without external dependencies (pandas, numpy, etc.)")
    
    try:
        # Test 1: Agent imports
        import_results = test_agent_imports()
        
        # Test 2: Base agent class
        base_agent_success = test_base_agent()
        
        # Test 3: Agent methods
        method_test_success = test_agent_methods()
        
        # Print final results
        all_passed = print_final_results(import_results, base_agent_success, method_test_success)
        
        print(f"\n📝 NEXT STEPS:")
        if all_passed:
            print(f"    1. Install dependencies (pandas, numpy, etc.)")
            print(f"    2. Run full test suite with: python3 test_agents.py")
            print(f"    3. The original instantiation errors should now be fixed!")
        else:
            print(f"    1. Fix the failing tests above")
            print(f"    2. Re-run this simple test")
            print(f"    3. Then proceed with dependency installation")
        
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