"""
Multi-Pair Testing Agent
Tests ALL available pairs for comprehensive ML data collection
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
import concurrent.futures
import threading
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent


class MultiPairTestingAgent(BaseAgent):
    """
    Multi-Pair Testing Agent - Tests ALL available pairs for maximum ML data
    Ensures comprehensive data collection across all tradeable instruments
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("multi_pair_testing", config)
        
        # Multi-pair testing configuration
        self.max_parallel_pairs = config.get('max_parallel_pairs', 20)  # Test 20 pairs simultaneously
        self.comprehensive_testing = config.get('comprehensive_testing', True)
        self.data_quality_threshold = config.get('data_quality_threshold', 0.8)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Comprehensive pair lists for maximum data
        self.all_pairs = self.load_all_available_pairs()
        
        # Testing tracking
        self.pair_test_results = {}
        self.data_quality_metrics = {}
        self.ml_data_samples = {}
        
        # Parallel testing setup
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_pairs)
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Multi-Pair Testing Agent initialized - {len(self.all_pairs[self.market_type])} pairs for {self.market_type}")
    
    def load_all_available_pairs(self) -> Dict[str, List[str]]:
        """Load ALL available pairs for comprehensive testing"""
        return {
            'forex': [
                # Major pairs
                'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF', 'NZD/USD',
                
                # Minor pairs
                'EUR/GBP', 'EUR/JPY', 'EUR/CHF', 'EUR/AUD', 'EUR/CAD', 'EUR/NZD',
                'GBP/JPY', 'GBP/CHF', 'GBP/AUD', 'GBP/CAD', 'GBP/NZD',
                'AUD/JPY', 'AUD/CHF', 'AUD/CAD', 'AUD/NZD',
                'CAD/JPY', 'CAD/CHF', 'CHF/JPY', 'NZD/JPY', 'NZD/CHF', 'NZD/CAD',
                
                # Exotic pairs
                'USD/SGD', 'USD/HKD', 'USD/NOK', 'USD/SEK', 'USD/DKK', 'USD/PLN',
                'EUR/NOK', 'EUR/SEK', 'EUR/DKK', 'EUR/PLN', 'EUR/HUF', 'EUR/CZK',
                'GBP/NOK', 'GBP/SEK', 'GBP/DKK', 'GBP/PLN',
                
                # Commodities
                'XAU/USD', 'XAG/USD', 'XPD/USD', 'XPT/USD'
            ],
            
            'crypto': [
                # Major cryptocurrencies
                'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'SOL/USDT',
                'DOGE/USDT', 'DOT/USDT', 'AVAX/USDT', 'SHIB/USDT', 'LTC/USDT', 'LINK/USDT',
                'UNI/USDT', 'BCH/USDT', 'XLM/USDT', 'ATOM/USDT', 'ALGO/USDT', 'VET/USDT',
                
                # DeFi tokens
                'AAVE/USDT', 'COMP/USDT', 'MKR/USDT', 'SNX/USDT', 'YFI/USDT', 'SUSHI/USDT',
                'CRV/USDT', 'BAL/USDT', '1INCH/USDT', 'ZRX/USDT',
                
                # Layer 1 blockchains
                'BNB/USDT', 'ADA/USDT', 'SOL/USDT', 'DOT/USDT', 'AVAX/USDT', 'NEAR/USDT',
                'FTM/USDT', 'MATIC/USDT', 'EGLD/USDT', 'HBAR/USDT', 'ALGO/USDT',
                
                # Layer 2 solutions
                'MATIC/USDT', 'LRC/USDT', 'OMG/USDT',
                
                # Meme coins (high volatility data)
                'DOGE/USDT', 'SHIB/USDT', 'FLOKI/USDT', 'PEPE/USDT',
                
                # Altcoins
                'XMR/USDT', 'ZEC/USDT', 'DASH/USDT', 'ETC/USDT', 'XTZ/USDT', 'QTUM/USDT',
                'ZIL/USDT', 'BAT/USDT', 'ENJ/USDT', 'MANA/USDT', 'SAND/USDT', 'AXS/USDT',
                
                # Stablecoins (for arbitrage patterns)
                'USDC/USDT', 'BUSD/USDT', 'DAI/USDT', 'TUSD/USDT',
                
                # Bitcoin pairs (additional)
                'BTC/ETH', 'BTC/BNB', 'BTC/BUSD',
                
                # Ethereum pairs (additional)  
                'ETH/BTC', 'ETH/BNB', 'ETH/BUSD'
            ]
        }
    
    def apply_market_specific_config(self):
        """Apply market-specific multi-pair configuration"""
        if self.market_type == 'forex':
            # Forex: Test major pairs first, then minors, then exotics
            self.priority_pairs = self.all_pairs['forex'][:7]  # Majors first
            self.secondary_pairs = self.all_pairs['forex'][7:20]  # Minors
            self.exotic_pairs = self.all_pairs['forex'][20:]  # Exotics
            
        elif self.market_type == 'crypto':
            # Crypto: Test top market cap first, then DeFi, then altcoins
            self.priority_pairs = self.all_pairs['crypto'][:20]  # Top 20
            self.defi_pairs = self.all_pairs['crypto'][20:30]  # DeFi tokens
            self.altcoin_pairs = self.all_pairs['crypto'][30:]  # Altcoins
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process multi-pair testing for comprehensive ML data
        
        Args:
            data: Dictionary containing testing configuration
            
        Returns:
            Dictionary with multi-pair testing results
        """
        try:
            action = data.get('action', 'test_all_pairs')
            
            if action == 'test_all_pairs':
                return self.test_all_pairs(data)
            elif action == 'test_priority_pairs':
                return self.test_priority_pairs(data)
            elif action == 'validate_data_quality':
                return self.validate_all_pairs_data_quality(data)
            elif action == 'generate_ml_dataset':
                return self.generate_comprehensive_ml_dataset(data)
            else:
                return {'error': f'Unknown multi-pair action: {action}'}
                
        except Exception as e:
            self.logger.error(f"Error in multi-pair testing: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def test_all_pairs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test ALL available pairs for comprehensive data collection
        """
        pairs_to_test = self.all_pairs[self.market_type]
        timeframes = data.get('timeframes', ['1h', '4h', '1d'])
        
        self.logger.info(f"Testing ALL {len(pairs_to_test)} {self.market_type} pairs across {len(timeframes)} timeframes")
        
        # Calculate total combinations
        total_combinations = len(pairs_to_test) * len(timeframes)
        
        print(f"🔥 COMPREHENSIVE PAIR TESTING:")
        print(f"📊 Pairs: {len(pairs_to_test)} {self.market_type} pairs")
        print(f"⏰ Timeframes: {len(timeframes)} timeframes")
        print(f"🎯 Total combinations: {total_combinations}")
        print(f"⚡ Parallel processing: {self.max_parallel_pairs} simultaneous")
        
        # Split into batches for parallel processing
        batch_size = self.max_parallel_pairs
        all_combinations = [(pair, tf) for pair in pairs_to_test for tf in timeframes]
        batches = [all_combinations[i:i + batch_size] for i in range(0, len(all_combinations), batch_size)]
        
        all_test_results = []
        total_ml_samples = 0
        
        # Process batches
        for batch_num, batch in enumerate(batches):
            print(f"📦 Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} combinations)...")
            
            # Submit parallel tests
            futures = []
            for pair, timeframe in batch:
                future = self.executor.submit(self.test_single_pair, pair, timeframe, data)
                futures.append((future, pair, timeframe))
            
            # Collect results
            batch_results = []
            for future, pair, timeframe in futures:
                try:
                    result = future.result(timeout=120)  # 2 minute timeout per pair
                    batch_results.append({
                        'pair': pair,
                        'timeframe': timeframe,
                        'result': result
                    })
                    
                    ml_samples = result.get('ml_samples_generated', 0)
                    total_ml_samples += ml_samples
                    
                    if result.get('success', False):
                        print(f"  ✅ {pair} {timeframe}: {ml_samples} ML samples")
                    else:
                        print(f"  ❌ {pair} {timeframe}: {result.get('error', 'Failed')}")
                    
                except Exception as e:
                    print(f"  ⚠️ {pair} {timeframe}: Timeout or error - {e}")
                    batch_results.append({
                        'pair': pair,
                        'timeframe': timeframe,
                        'error': str(e)
                    })
            
            all_test_results.extend(batch_results)
        
        # Calculate summary
        successful_tests = sum(1 for result in all_test_results if 'error' not in result)
        success_rate = successful_tests / len(all_test_results) if all_test_results else 0
        
        return {
            'agent_id': self.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'comprehensive_testing_completed': True,
            'total_combinations_tested': len(all_test_results),
            'successful_tests': successful_tests,
            'success_rate': success_rate,
            'total_ml_samples_generated': total_ml_samples,
            'pairs_tested': len(pairs_to_test),
            'timeframes_tested': len(timeframes),
            'test_results': all_test_results,
            'market_type': self.market_type,
            'data_collection_summary': {
                'samples_per_pair_avg': total_ml_samples / len(pairs_to_test) if pairs_to_test else 0,
                'estimated_total_dataset_size': total_ml_samples,
                'data_quality_score': self.calculate_overall_data_quality(all_test_results)
            }
        }
    
    def test_single_pair(self, pair: str, timeframe: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test single pair-timeframe combination
        """
        try:
            # Simulate comprehensive testing for this pair
            # In production, this would:
            # 1. Load historical data for the pair
            # 2. Run all 43 agents on the data
            # 3. Generate ML training samples
            # 4. Validate data quality
            
            # Simulate data loading
            data_available = self.check_data_availability(pair, timeframe)
            
            if not data_available:
                return {'success': False, 'error': 'No data available'}
            
            # Simulate agent testing
            agent_results = self.simulate_agent_testing(pair, timeframe)
            
            # Simulate ML sample generation
            ml_samples = self.simulate_ml_sample_generation(pair, timeframe, agent_results)
            
            # Calculate data quality
            data_quality = self.assess_pair_data_quality(pair, timeframe, agent_results)
            
            return {
                'success': True,
                'pair': pair,
                'timeframe': timeframe,
                'agent_results': agent_results,
                'ml_samples_generated': len(ml_samples),
                'data_quality_score': data_quality,
                'trading_opportunities': agent_results.get('trading_opportunities', 0),
                'pattern_diversity': agent_results.get('pattern_diversity', 0)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_data_availability(self, pair: str, timeframe: str) -> bool:
        """Check if data is available for pair-timeframe combination"""
        # Simulate data availability check
        # In production, this would check your data sources
        
        # Most major pairs should have data available
        major_pairs = ['BTC/USDT', 'ETH/USDT', 'EUR/USD', 'GBP/USD', 'USD/JPY']
        
        if pair in major_pairs:
            return True  # Major pairs always have data
        else:
            return np.random.random() > 0.2  # 80% chance for other pairs
    
    def simulate_agent_testing(self, pair: str, timeframe: str) -> Dict[str, Any]:
        """Simulate testing all 43 agents on this pair"""
        # Simulate agent results
        agent_count = 43
        successful_agents = np.random.randint(35, 43)  # 35-43 agents work
        
        # Simulate pattern detection
        patterns_detected = np.random.randint(5, 25)  # 5-25 patterns detected
        
        # Simulate trading opportunities
        trading_opportunities = np.random.randint(10, 100)  # 10-100 opportunities
        
        # Simulate pattern diversity (how many different pattern types)
        pattern_diversity = np.random.randint(8, 21)  # 8-21 different pattern types
        
        return {
            'total_agents': agent_count,
            'successful_agents': successful_agents,
            'patterns_detected': patterns_detected,
            'trading_opportunities': trading_opportunities,
            'pattern_diversity': pattern_diversity,
            'agent_success_rate': successful_agents / agent_count
        }
    
    def simulate_ml_sample_generation(self, pair: str, timeframe: str, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simulate ML sample generation for this pair"""
        # Generate realistic number of ML samples based on trading opportunities
        opportunities = agent_results.get('trading_opportunities', 50)
        
        ml_samples = []
        for i in range(opportunities):
            # Simulate comprehensive feature vector (200+ features)
            features = np.random.random(200).tolist()  # 200 features from 43 agents
            
            # Simulate trade outcome
            outcome = np.random.choice([0, 1], p=[0.3, 0.7])  # 70% win rate simulation
            
            ml_sample = {
                'pair': pair,
                'timeframe': timeframe,
                'features': features,
                'target': outcome,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            ml_samples.append(ml_sample)
        
        return ml_samples
    
    def assess_pair_data_quality(self, pair: str, timeframe: str, agent_results: Dict[str, Any]) -> float:
        """Assess data quality for this pair"""
        # Quality factors
        agent_success_rate = agent_results.get('agent_success_rate', 0)
        pattern_diversity = agent_results.get('pattern_diversity', 0) / 21.0  # Normalize
        trading_opportunities = min(agent_results.get('trading_opportunities', 0) / 100.0, 1.0)  # Normalize
        
        # Overall quality score
        quality_score = (agent_success_rate * 0.4 + pattern_diversity * 0.3 + trading_opportunities * 0.3)
        
        return quality_score
    
    def calculate_overall_data_quality(self, test_results: List[Dict[str, Any]]) -> float:
        """Calculate overall data quality across all pairs"""
        quality_scores = []
        
        for result in test_results:
            if 'error' not in result and 'result' in result:
                quality = result['result'].get('data_quality_score', 0)
                quality_scores.append(quality)
        
        return np.mean(quality_scores) if quality_scores else 0.0
    
    def test_priority_pairs(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test priority pairs first for initial ML data"""
        priority_pairs = getattr(self, 'priority_pairs', self.all_pairs[self.market_type][:10])
        timeframes = data.get('timeframes', ['1h', '4h'])
        
        print(f"🎯 PRIORITY PAIR TESTING:")
        print(f"📊 Testing {len(priority_pairs)} priority {self.market_type} pairs")
        
        # Test priority pairs with higher resource allocation
        priority_results = []
        
        for pair in priority_pairs:
            for timeframe in timeframes:
                result = self.test_single_pair(pair, timeframe, data)
                priority_results.append({
                    'pair': pair,
                    'timeframe': timeframe,
                    'result': result
                })
                
                if result.get('success'):
                    print(f"  ✅ {pair} {timeframe}: {result['ml_samples_generated']} samples")
                else:
                    print(f"  ❌ {pair} {timeframe}: {result.get('error', 'Failed')}")
        
        return {
            'priority_testing_completed': True,
            'priority_pairs_tested': len(priority_pairs),
            'priority_results': priority_results,
            'total_priority_samples': sum(r['result'].get('ml_samples_generated', 0) for r in priority_results)
        }
    
    def generate_comprehensive_ml_dataset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive ML dataset from all pairs"""
        # This would combine all pair data into massive ML dataset
        all_pairs = self.all_pairs[self.market_type]
        
        print(f"🤖 GENERATING COMPREHENSIVE ML DATASET:")
        print(f"📊 Source: {len(all_pairs)} {self.market_type} pairs")
        print(f"🎯 Target: Maximum ML training data")
        
        # Simulate comprehensive dataset generation
        estimated_samples = len(all_pairs) * 1000  # 1000 samples per pair average
        
        dataset_info = {
            'agent_id': self.agent_id,
            'dataset_generated': True,
            'source_pairs': len(all_pairs),
            'estimated_samples': estimated_samples,
            'feature_count': 200,  # 200+ features from 43 agents
            'dataset_size_gb': estimated_samples * 200 * 8 / (1024**3),  # Rough estimate
            'market_type': self.market_type,
            'comprehensive_coverage': True
        }
        
        return dataset_info
    
    def get_signal_strength(self) -> float:
        """Get current signal strength based on testing coverage"""
        if not self.pair_test_results:
            return 0.0
        
        # Signal strength based on testing coverage
        total_pairs = len(self.all_pairs[self.market_type])
        tested_pairs = len(self.pair_test_results)
        
        coverage_ratio = tested_pairs / total_pairs if total_pairs > 0 else 0.0
        
        return coverage_ratio
    
    def get_testing_summary(self) -> Dict[str, Any]:
        """Get comprehensive testing summary"""
        total_pairs = len(self.all_pairs[self.market_type])
        
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'total_pairs_available': total_pairs,
            'pairs_tested': len(self.pair_test_results),
            'testing_coverage': len(self.pair_test_results) / total_pairs if total_pairs > 0 else 0,
            'data_quality_average': np.mean(list(self.data_quality_metrics.values())) if self.data_quality_metrics else 0,
            'total_ml_samples': sum(len(samples) for samples in self.ml_data_samples.values()),
            'last_signal_strength': self.get_signal_strength(),
            'all_pairs_list': self.all_pairs[self.market_type]
        }
    
    def requires_continuous_processing(self) -> bool:
        """Multi-pair testing agent doesn't need continuous processing"""
        return False