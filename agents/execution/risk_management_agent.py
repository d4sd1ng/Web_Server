"""
Risk Management Agent
Handles risk management using existing functions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class RiskManagementAgent(BaseAgent):
    """
    Specialized agent for Risk Management
    Uses existing risk management functions from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("risk_management", config)
        
        # Risk configuration
        self.max_open_trades = config.get('max_open_trades', 3)
        self.risk_per_trade = config.get('risk_per_trade', 0.01)  # 1%
        self.max_daily_risk = config.get('max_daily_risk', 0.05)  # 5%
        self.max_drawdown = config.get('max_drawdown', 0.15)  # 15%
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Risk tracking
        self.open_trades = []
        self.daily_pnl = 0.0
        self.total_drawdown = 0.0
        self.risk_events = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Risk Management Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific risk configuration"""
        if self.market_type == 'forex':
            # Forex: Lower risk due to leverage and volatility
            self.risk_per_trade = min(self.risk_per_trade, 0.005)  # 0.5% max for forex
            self.max_daily_risk = min(self.max_daily_risk, 0.03)   # 3% max daily
            self.leverage_limit = 100  # Typical forex leverage
            self.correlation_monitoring = True  # Monitor currency correlations
        elif self.market_type == 'crypto':
            # Crypto: Standard risk, higher volatility tolerance
            self.risk_per_trade = max(self.risk_per_trade, 0.01)   # 1% for crypto
            self.max_daily_risk = max(self.max_daily_risk, 0.05)   # 5% daily
            self.leverage_limit = 25   # Typical crypto leverage
            self.correlation_monitoring = False  # Less correlation in crypto
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process trading data for risk management
        
        Args:
            data: Dictionary containing trade information and account data
            
        Returns:
            Dictionary with risk management analysis
        """
        try:
            # Calculate current risk exposure
            risk_exposure = self.calculate_risk_exposure(data)
            
            # Assess position sizing
            position_sizing = self.calculate_position_sizing(data)
            
            # Check risk limits
            risk_checks = self.perform_risk_checks(data, risk_exposure)
            
            # Calculate signal strength (risk-adjusted)
            signal_strength = self.calculate_risk_signal_strength(risk_exposure, risk_checks)
            
            results = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'risk_exposure': risk_exposure,
                'position_sizing': position_sizing,
                'risk_checks': risk_checks,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'risk_recommendations': self.generate_risk_recommendations(risk_exposure, risk_checks)
            }
            
            # Publish risk alerts
            if risk_checks['risk_level'] == 'high':
                self.publish("risk_alert", {
                    'risk_level': 'high',
                    'risk_checks': risk_checks,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing risk management data: {e}")
            return {'risk_level': 'unknown', 'signal_strength': 0.0, 'error': str(e)}
    
    def calculate_risk_exposure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate current risk exposure
        """
        account_balance = data.get('account_balance', 10000)
        open_trades = data.get('open_trades', [])
        
        total_risk = 0.0
        position_risk = 0.0
        
        for trade in open_trades:
            trade_risk = trade.get('risk_amount', 0)
            total_risk += trade_risk
            
            # Calculate position risk
            position_size = trade.get('position_size', 0)
            entry_price = trade.get('entry_price', 0)
            if entry_price > 0:
                position_value = position_size * entry_price
                position_risk += position_value
        
        return {
            'total_risk_amount': total_risk,
            'total_risk_percent': total_risk / account_balance if account_balance > 0 else 0,
            'position_risk_amount': position_risk,
            'position_risk_percent': position_risk / account_balance if account_balance > 0 else 0,
            'open_trades_count': len(open_trades),
            'available_risk': max(0, account_balance * self.max_daily_risk - total_risk),
            'risk_utilization': total_risk / (account_balance * self.max_daily_risk) if account_balance > 0 else 0
        }
    
    def calculate_position_sizing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate appropriate position sizing
        """
        account_balance = data.get('account_balance', 10000)
        entry_price = data.get('entry_price', 0)
        stop_loss = data.get('stop_loss', 0)
        
        if entry_price <= 0 or stop_loss <= 0:
            return {'position_size': 0, 'risk_amount': 0}
        
        # Calculate risk per trade
        risk_amount = account_balance * self.risk_per_trade
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance <= 0:
            return {'position_size': 0, 'risk_amount': 0}
        
        # Calculate position size
        position_size = risk_amount / stop_distance
        
        # Market-specific adjustments
        if self.market_type == 'forex':
            # Forex position sizing considerations
            position_size = min(position_size, account_balance * 0.1)  # Max 10% of account
        elif self.market_type == 'crypto':
            # Crypto position sizing considerations
            position_size = min(position_size, account_balance * 0.2)  # Max 20% of account
        
        return {
            'position_size': position_size,
            'risk_amount': risk_amount,
            'stop_distance': stop_distance,
            'risk_reward_ratio': self.calculate_risk_reward_ratio(data),
            'position_value': position_size * entry_price
        }
    
    def calculate_risk_reward_ratio(self, data: Dict[str, Any]) -> float:
        """Calculate risk-reward ratio"""
        entry_price = data.get('entry_price', 0)
        stop_loss = data.get('stop_loss', 0)
        take_profit = data.get('take_profit', 0)
        
        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return 0.0
        
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        return reward / risk if risk > 0 else 0.0
    
    def perform_risk_checks(self, data: Dict[str, Any], risk_exposure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive risk checks
        """
        checks = {
            'max_trades_check': risk_exposure['open_trades_count'] < self.max_open_trades,
            'daily_risk_check': risk_exposure['total_risk_percent'] < self.max_daily_risk,
            'drawdown_check': self.total_drawdown < self.max_drawdown,
            'correlation_check': True,  # Would implement correlation check
            'leverage_check': True,     # Would implement leverage check
            'liquidity_check': True    # Would implement liquidity check
        }
        
        # Market-specific checks
        if self.market_type == 'forex':
            checks['session_check'] = self.check_forex_session_risk(data)
            checks['news_check'] = self.check_forex_news_risk(data)
        elif self.market_type == 'crypto':
            checks['volatility_check'] = self.check_crypto_volatility_risk(data)
            checks['weekend_check'] = self.check_crypto_weekend_risk(data)
        
        # Determine overall risk level
        failed_checks = sum(1 for check in checks.values() if not check)
        total_checks = len(checks)
        
        if failed_checks == 0:
            risk_level = 'low'
        elif failed_checks <= total_checks * 0.2:
            risk_level = 'medium'
        else:
            risk_level = 'high'
        
        checks['risk_level'] = risk_level
        checks['failed_checks'] = failed_checks
        checks['check_score'] = (total_checks - failed_checks) / total_checks
        
        return checks
    
    def check_forex_session_risk(self, data: Dict[str, Any]) -> bool:
        """Check forex session-based risk"""
        # Simplified session risk check
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        
        # Higher risk outside major sessions
        if 8 <= hour <= 22:  # Major sessions
            return True
        else:
            return False  # Higher risk during Asian session
    
    def check_forex_news_risk(self, data: Dict[str, Any]) -> bool:
        """Check forex news-based risk"""
        # Would implement news calendar check
        # For now, assume normal risk
        return True
    
    def check_crypto_volatility_risk(self, data: Dict[str, Any]) -> bool:
        """Check crypto volatility risk"""
        # Would check current volatility vs historical
        return True
    
    def check_crypto_weekend_risk(self, data: Dict[str, Any]) -> bool:
        """Check crypto weekend risk"""
        current_time = datetime.now(timezone.utc)
        is_weekend = current_time.weekday() >= 5
        
        # Crypto trades 24/7 but weekends can be lower volume
        return not is_weekend or self.market_type == 'crypto'
    
    def generate_risk_recommendations(self, risk_exposure: Dict[str, Any], risk_checks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate risk management recommendations"""
        recommendations = []
        
        # Risk exposure recommendations
        if risk_exposure['risk_utilization'] > 0.8:
            recommendations.append({
                'type': 'risk_exposure',
                'level': 'warning',
                'message': f'High risk utilization ({risk_exposure["risk_utilization"]:.1%}) for {self.market_type}',
                'action': 'Consider reducing position sizes'
            })
        
        # Trade count recommendations
        if risk_exposure['open_trades_count'] >= self.max_open_trades:
            recommendations.append({
                'type': 'trade_count',
                'level': 'alert',
                'message': f'Maximum trades reached ({self.max_open_trades}) for {self.market_type}',
                'action': 'No new trades until positions close'
            })
        
        # Market-specific recommendations
        if self.market_type == 'forex':
            if not risk_checks.get('session_check', True):
                recommendations.append({
                    'type': 'session_risk',
                    'level': 'warning',
                    'message': 'Trading outside major forex sessions',
                    'action': 'Reduce position sizes or avoid new trades'
                })
        
        elif self.market_type == 'crypto':
            if not risk_checks.get('weekend_check', True):
                recommendations.append({
                    'type': 'weekend_risk',
                    'level': 'info',
                    'message': 'Weekend crypto trading - potentially lower volume',
                    'action': 'Monitor liquidity and consider smaller positions'
                })
        
        return recommendations
    
    def calculate_risk_signal_strength(self, risk_exposure: Dict[str, Any], risk_checks: Dict[str, Any]) -> float:
        """
        Calculate risk-adjusted signal strength
        """
        # Start with base strength
        base_strength = 0.5
        
        # Risk check score
        check_score = risk_checks.get('check_score', 0.5)
        
        # Risk utilization penalty
        risk_utilization = risk_exposure.get('risk_utilization', 0.0)
        utilization_penalty = risk_utilization * 0.3  # Reduce strength as risk increases
        
        # Calculate adjusted strength
        adjusted_strength = base_strength + (check_score - 0.5) * 0.5 - utilization_penalty
        
        return max(0.0, min(adjusted_strength, 1.0))
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.5  # Default risk-neutral strength
        return self._last_signal_strength
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'open_trades_count': len(self.open_trades),
            'daily_pnl': self.daily_pnl,
            'total_drawdown': self.total_drawdown,
            'risk_events_count': len(self.risk_events),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'max_open_trades': self.max_open_trades,
                'risk_per_trade': self.risk_per_trade,
                'max_daily_risk': self.max_daily_risk,
                'max_drawdown': self.max_drawdown,
                'leverage_limit': getattr(self, 'leverage_limit', 25)
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Risk management agent benefits from continuous monitoring"""
        return True
    
    def _continuous_process(self):
        """Continuous risk monitoring"""
        try:
            # Monitor open trades for risk events
            self.monitor_open_trades()
            
            # Check for risk limit breaches
            self.check_risk_limits()
            
            # Update daily PnL
            self.update_daily_pnl()
            
        except Exception as e:
            self.logger.error(f"Error in risk continuous processing: {e}")
    
    def monitor_open_trades(self):
        """Monitor open trades for risk management"""
        # Would implement actual trade monitoring
        pass
    
    def check_risk_limits(self):
        """Check if any risk limits are breached"""
        # Would implement risk limit checking
        pass
    
    def update_daily_pnl(self):
        """Update daily PnL tracking"""
        # Would implement daily PnL calculation
        pass
    
    def get_processing_interval(self) -> float:
        """Get processing interval for risk monitoring"""
        return 30.0  # Check every 30 seconds for risk management