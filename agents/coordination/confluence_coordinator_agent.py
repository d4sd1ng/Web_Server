"""
Confluence Coordinator Agent
Coordinates pattern confluence for >90% win rate targeting
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent


class ConfluenceCoordinatorAgent(BaseAgent):
    """
    Master coordination agent for pattern confluence
    Ensures minimum confluence requirements for high win rate
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("confluence_coordinator", config)
        
        # Confluence requirements (BALANCED for trade execution)
        self.min_confluence_patterns = config.get('min_confluence_patterns', {
            'forex': 4,    # Start tradeable (not 6)
            'crypto': 3    # Start tradeable (not 5)
        })
        
        self.min_confluence_score = config.get('min_confluence_score', {
            'forex': 6.0,   # Start tradeable (not 10.0)
            'crypto': 5.0   # Start tradeable (not 8.5)
        })
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Confluence tracking
        self.confluence_history = []
        self.approved_setups = []
        self.rejected_setups = []
        
        self.apply_market_specific_config()
        
        self.logger.info(f"Confluence Coordinator initialized for {self.market_type} - BALANCED for trade execution")
    
    def apply_market_specific_config(self):
        """Apply market-specific confluence requirements"""
        if self.market_type == 'forex':
            self.min_patterns = self.min_confluence_patterns['forex']
            self.min_score = self.min_confluence_score['forex']
            self.session_weight = 1.0
        elif self.market_type == 'crypto':
            self.min_patterns = self.min_confluence_patterns['crypto']
            self.min_score = self.min_confluence_score['crypto']
            self.volume_weight = 1.0
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process all agent signals to determine confluence quality"""
        required_fields = ['symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        symbol = data['symbol']
        
        try:
            # Collect agent signals
            agent_signals = self.collect_agent_signals(data)
            
            # Calculate confluence score
            confluence_analysis = self.calculate_confluence_score(agent_signals)
            
            # Make trading decision
            trading_decision = self.make_confluence_decision(confluence_analysis, agent_signals)
            
            # Update tracking
            self.update_confluence_tracking(confluence_analysis, trading_decision, symbol)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'confluence_analysis': confluence_analysis,
                'trading_decision': trading_decision,
                'signal_strength': trading_decision.get('confidence', 0.0),
                'market_type': self.market_type
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing confluence data for {symbol}: {e}")
            return {'confluence_analysis': {}, 'signal_strength': 0.0, 'error': str(e)}
    
    def collect_agent_signals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect signals from all agents"""
        signals = {
            'ict_smc_signals': 0,
            'analysis_signals': 0,
            'ml_signals': 0,
            'total_signals': 0,
            'signal_strengths': []
        }
        
        # Count active signals from various agents
        for key, value in data.items():
            if isinstance(value, dict) and 'signal_strength' in value:
                strength = value['signal_strength']
                if strength > 0.5:  # Only count strong signals
                    signals['total_signals'] += 1
                    signals['signal_strengths'].append(strength)
                    
                    # Categorize signals
                    if 'ict' in key or 'smc' in key or key in ['fair_value_gaps', 'order_blocks', 'market_structure']:
                        signals['ict_smc_signals'] += 1
                    elif key in ['volume_analysis', 'session_analysis', 'technical_indicators']:
                        signals['analysis_signals'] += 1
                    elif 'ml' in key:
                        signals['ml_signals'] += 1
        
        return signals
    
    def calculate_confluence_score(self, agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate confluence score"""
        total_signals = agent_signals['total_signals']
        signal_strengths = agent_signals['signal_strengths']
        
        # Calculate weighted score
        if signal_strengths:
            avg_strength = np.mean(signal_strengths)
            confluence_score = total_signals * avg_strength
        else:
            confluence_score = 0.0
        
        return {
            'total_score': confluence_score,
            'pattern_count': total_signals,
            'avg_strength': np.mean(signal_strengths) if signal_strengths else 0.0,
            'ict_smc_count': agent_signals['ict_smc_signals'],
            'analysis_count': agent_signals['analysis_signals'],
            'ml_count': agent_signals['ml_signals']
        }
    
    def make_confluence_decision(self, confluence_analysis: Dict[str, Any], agent_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Make trading decision based on confluence"""
        pattern_count = confluence_analysis['pattern_count']
        confluence_score = confluence_analysis['total_score']
        
        # Check requirements (BALANCED for trade execution)
        patterns_ok = pattern_count >= self.min_patterns
        score_ok = confluence_score >= self.min_score
        
        approved = patterns_ok and score_ok
        
        # Calculate confidence
        if approved:
            confidence = min(confluence_score / (self.min_score * 1.5), 1.0)
        else:
            confidence = confluence_score / self.min_score if self.min_score > 0 else 0.0
        
        return {
            'approved': approved,
            'confidence': confidence,
            'pattern_count': pattern_count,
            'confluence_score': confluence_score,
            'patterns_required': self.min_patterns,
            'score_required': self.min_score,
            'rejection_reason': None if approved else f'Insufficient confluence: {pattern_count}/{self.min_patterns} patterns, {confluence_score:.1f}/{self.min_score} score'
        }
    
    def update_confluence_tracking(self, confluence_analysis: Dict[str, Any], trading_decision: Dict[str, Any], symbol: str):
        """Update confluence tracking"""
        confluence_entry = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'confluence_analysis': confluence_analysis,
            'trading_decision': trading_decision,
            'market_type': self.market_type
        }
        
        self.confluence_history.append(confluence_entry)
        
        if trading_decision['approved']:
            self.approved_setups.append(confluence_entry)
        else:
            self.rejected_setups.append(confluence_entry)
        
        # Limit tracking sizes
        if len(self.confluence_history) > 200:
            self.confluence_history = self.confluence_history[-200:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength"""
        if not self.confluence_history:
            return 0.0
        
        # Signal strength based on recent approvals
        recent_entries = self.confluence_history[-10:] if len(self.confluence_history) >= 10 else self.confluence_history
        approved_count = sum(1 for entry in recent_entries if entry['trading_decision']['approved'])
        
        return approved_count / len(recent_entries) if recent_entries else 0.0
    
    def requires_continuous_processing(self) -> bool:
        """Confluence coordinator doesn't need continuous processing"""
        return False