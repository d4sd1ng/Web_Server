"""
Technical Indicators Agent
Analyzes technical indicators using existing functions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import BaseAgent


class TechnicalIndicatorsAgent(BaseAgent):
    """
    Specialized agent for Technical Indicator analysis
    Uses existing indicator calculation functions from tradingbot_new.py
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("technical_indicators", config)
        
        # Indicator configuration
        self.rsi_window = config.get('rsi_window', 14)
        self.adx_window = config.get('adx_window', 14)
        self.atr_window = config.get('atr_window', 14)
        self.sma_short_period = config.get('sma_short_period', 10)
        self.sma_long_period = config.get('sma_long_period', 50)
        self.macd_fast = config.get('macd_fast', 12)
        self.macd_slow = config.get('macd_slow', 26)
        self.macd_signal = config.get('macd_signal', 9)
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # Indicator tracking
        self.indicator_signals = []
        self.divergence_events = []
        self.overbought_oversold_events = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Technical Indicators Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific indicator configuration"""
        if self.market_type == 'forex':
            # Forex: Longer periods due to lower volatility
            self.rsi_window = max(self.rsi_window, 14)
            self.adx_window = max(self.adx_window, 14)
            self.sma_long_period = max(self.sma_long_period, 50)
            self.overbought_level = 75  # Higher for forex
            self.oversold_level = 25
        elif self.market_type == 'crypto':
            # Crypto: Shorter periods due to higher volatility
            self.rsi_window = min(self.rsi_window, 14)
            self.adx_window = min(self.adx_window, 14)
            self.sma_long_period = min(self.sma_long_period, 50)
            self.overbought_level = 70  # Standard for crypto
            self.oversold_level = 30
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data for technical indicator analysis
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with technical indicator analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < max(self.sma_long_period, 50):
            return {'indicators': {}, 'signal_strength': 0.0}
        
        try:
            # Calculate all indicators using existing functions
            df_with_indicators = self.calculate_all_indicators(df)
            
            # Analyze indicator signals
            indicator_signals = self.analyze_indicator_signals(df_with_indicators)
            
            # Detect divergences
            divergences = self.detect_divergences(df_with_indicators)
            
            # Detect overbought/oversold conditions
            ob_os_conditions = self.detect_overbought_oversold(df_with_indicators)
            
            # Calculate signal strength
            signal_strength = self.calculate_indicator_signal_strength(
                indicator_signals, divergences, ob_os_conditions, df_with_indicators
            )
            
            # Update tracking
            self.update_indicator_tracking(indicator_signals, divergences, ob_os_conditions)
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'indicators': self.extract_current_indicators(df_with_indicators),
                'indicator_signals': indicator_signals,
                'divergences': divergences,
                'overbought_oversold': ob_os_conditions,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_signals': self.generate_indicator_trading_signals(
                    indicator_signals, divergences, ob_os_conditions
                )
            }
            
            # Publish indicator signals
            if indicator_signals['strong_signals']:
                self.publish("technical_indicator_signal", {
                    'symbol': symbol,
                    'signals': indicator_signals['strong_signals'],
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing technical indicator data for {symbol}: {e}")
            return {'indicators': {}, 'signal_strength': 0.0, 'error': str(e)}
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators using existing functions
        """
        try:
            # Import your existing indicator functions
            from tradingbot_new import calculate_atr, calculate_rsi, calculate_adx, calculate_sma, calculate_macd, calculate_vwap
            
            # Create a copy to avoid modifying original
            df_calc = df.copy()
            
            # Calculate indicators using your existing functions
            df_calc = calculate_atr(df_calc, window=self.atr_window)
            df_calc = calculate_rsi(df_calc, window=self.rsi_window)
            df_calc = calculate_adx(df_calc, window=self.adx_window)
            df_calc = calculate_sma(df_calc, short_period=self.sma_short_period, long_period=self.sma_long_period)
            df_calc = calculate_macd(df_calc, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
            df_calc = calculate_vwap(df_calc)
            
            # Add additional indicators
            import ta
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df_calc['close'], window=20, window_dev=2)
            df_calc['bb_upper'] = bb.bollinger_hband()
            df_calc['bb_middle'] = bb.bollinger_mavg()
            df_calc['bb_lower'] = bb.bollinger_lband()
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(df_calc['high'], df_calc['low'], df_calc['close'], window=14, smooth_window=3)
            df_calc['stoch_k'] = stoch.stoch()
            df_calc['stoch_d'] = stoch.stoch_signal()
            
            # CCI
            cci = ta.trend.CCIIndicator(df_calc['high'], df_calc['low'], df_calc['close'], window=20)
            df_calc['cci'] = cci.cci()
            
            return df_calc
            
        except ImportError:
            # Fallback if functions not available
            return self.calculate_basic_indicators(df)
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return df
    
    def calculate_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate basic indicators if main functions unavailable"""
        df_calc = df.copy()
        
        # Basic RSI
        delta = df_calc['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_window).mean()
        rs = gain / loss
        df_calc['rsi'] = 100 - (100 / (1 + rs))
        
        # Basic SMA
        df_calc['SMA_short'] = df_calc['close'].rolling(self.sma_short_period).mean()
        df_calc['SMA_long'] = df_calc['close'].rolling(self.sma_long_period).mean()
        
        # Basic ATR
        high_low = df_calc['high'] - df_calc['low']
        high_close = np.abs(df_calc['high'] - df_calc['close'].shift())
        low_close = np.abs(df_calc['low'] - df_calc['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df_calc['atr'] = true_range.rolling(self.atr_window).mean()
        
        return df_calc
    
    def extract_current_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract current indicator values"""
        indicators = {}
        
        # Extract latest values
        if 'rsi' in df.columns:
            indicators['rsi'] = df['rsi'].iloc[-1]
        if 'adx' in df.columns:
            indicators['adx'] = df['adx'].iloc[-1]
        if 'atr' in df.columns:
            indicators['atr'] = df['atr'].iloc[-1]
        if 'SMA_short' in df.columns:
            indicators['sma_short'] = df['SMA_short'].iloc[-1]
        if 'SMA_long' in df.columns:
            indicators['sma_long'] = df['SMA_long'].iloc[-1]
        if 'MACD' in df.columns:
            indicators['macd'] = df['MACD'].iloc[-1]
        if 'MACD_signal' in df.columns:
            indicators['macd_signal'] = df['MACD_signal'].iloc[-1]
        if 'vwap' in df.columns:
            indicators['vwap'] = df['vwap'].iloc[-1]
        if 'bb_upper' in df.columns:
            indicators['bb_upper'] = df['bb_upper'].iloc[-1]
            indicators['bb_middle'] = df['bb_middle'].iloc[-1]
            indicators['bb_lower'] = df['bb_lower'].iloc[-1]
        if 'stoch_k' in df.columns:
            indicators['stoch_k'] = df['stoch_k'].iloc[-1]
            indicators['stoch_d'] = df['stoch_d'].iloc[-1]
        if 'cci' in df.columns:
            indicators['cci'] = df['cci'].iloc[-1]
        
        # Add current price for reference
        indicators['close'] = df['close'].iloc[-1]
        
        return indicators
    
    def analyze_indicator_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze signals from technical indicators
        """
        signals = {
            'bullish_signals': [],
            'bearish_signals': [],
            'neutral_signals': [],
            'strong_signals': [],
            'signal_count': 0
        }
        
        current_indicators = self.extract_current_indicators(df)
        
        # RSI signals
        if 'rsi' in current_indicators:
            rsi = current_indicators['rsi']
            if rsi > self.overbought_level:
                signals['bearish_signals'].append(f'RSI overbought ({rsi:.1f})')
            elif rsi < self.oversold_level:
                signals['bullish_signals'].append(f'RSI oversold ({rsi:.1f})')
        
        # SMA crossover signals
        if 'sma_short' in current_indicators and 'sma_long' in current_indicators:
            sma_short = current_indicators['sma_short']
            sma_long = current_indicators['sma_long']
            close = current_indicators['close']
            
            if sma_short > sma_long and close > sma_short:
                signals['bullish_signals'].append('SMA bullish alignment')
            elif sma_short < sma_long and close < sma_short:
                signals['bearish_signals'].append('SMA bearish alignment')
        
        # MACD signals
        if 'macd' in current_indicators and 'macd_signal' in current_indicators:
            macd = current_indicators['macd']
            macd_signal = current_indicators['macd_signal']
            
            if macd > macd_signal and macd > 0:
                signals['bullish_signals'].append('MACD bullish crossover')
            elif macd < macd_signal and macd < 0:
                signals['bearish_signals'].append('MACD bearish crossover')
        
        # ADX trend strength
        if 'adx' in current_indicators:
            adx = current_indicators['adx']
            if adx > 25:
                signals['strong_signals'].append(f'Strong trend (ADX: {adx:.1f})')
        
        # Bollinger Band signals
        if all(key in current_indicators for key in ['bb_upper', 'bb_lower', 'close']):
            close = current_indicators['close']
            bb_upper = current_indicators['bb_upper']
            bb_lower = current_indicators['bb_lower']
            
            if close > bb_upper:
                signals['bearish_signals'].append('Price above Bollinger upper band')
            elif close < bb_lower:
                signals['bullish_signals'].append('Price below Bollinger lower band')
        
        signals['signal_count'] = len(signals['bullish_signals']) + len(signals['bearish_signals'])
        
        return signals
    
    def detect_divergences(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect divergences between price and indicators
        """
        divergences = []
        
        if len(df) < 20:
            return divergences
        
        # RSI divergence
        if 'rsi' in df.columns:
            rsi_divergence = self.detect_rsi_divergence(df)
            if rsi_divergence:
                divergences.append(rsi_divergence)
        
        # MACD divergence
        if 'MACD' in df.columns:
            macd_divergence = self.detect_macd_divergence(df)
            if macd_divergence:
                divergences.append(macd_divergence)
        
        return divergences
    
    def detect_rsi_divergence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect RSI divergence"""
        if len(df) < 20:
            return None
        
        recent_data = df.iloc[-20:]
        
        # Find recent highs and lows
        price_high_idx = recent_data['high'].idxmax()
        price_low_idx = recent_data['low'].idxmin()
        
        # Check for bullish divergence (price lower low, RSI higher low)
        if (recent_data['low'].iloc[-1] < recent_data['low'].iloc[0] and
            recent_data['rsi'].iloc[-1] > recent_data['rsi'].iloc[0]):
            
            return {
                'type': 'bullish_rsi_divergence',
                'strength': 0.7,
                'market_implication': f'{self.market_type} bullish divergence - potential reversal up'
            }
        
        # Check for bearish divergence (price higher high, RSI lower high)
        elif (recent_data['high'].iloc[-1] > recent_data['high'].iloc[0] and
              recent_data['rsi'].iloc[-1] < recent_data['rsi'].iloc[0]):
            
            return {
                'type': 'bearish_rsi_divergence',
                'strength': 0.7,
                'market_implication': f'{self.market_type} bearish divergence - potential reversal down'
            }
        
        return None
    
    def detect_macd_divergence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect MACD divergence"""
        if len(df) < 20 or 'MACD' not in df.columns:
            return None
        
        recent_data = df.iloc[-20:]
        
        # Bullish MACD divergence
        if (recent_data['low'].iloc[-1] < recent_data['low'].iloc[0] and
            recent_data['MACD'].iloc[-1] > recent_data['MACD'].iloc[0]):
            
            return {
                'type': 'bullish_macd_divergence',
                'strength': 0.6,
                'market_implication': f'{self.market_type} MACD bullish divergence detected'
            }
        
        # Bearish MACD divergence
        elif (recent_data['high'].iloc[-1] > recent_data['high'].iloc[0] and
              recent_data['MACD'].iloc[-1] < recent_data['MACD'].iloc[0]):
            
            return {
                'type': 'bearish_macd_divergence',
                'strength': 0.6,
                'market_implication': f'{self.market_type} MACD bearish divergence detected'
            }
        
        return None
    
    def detect_overbought_oversold(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect overbought/oversold conditions
        """
        conditions = {
            'overbought': False,
            'oversold': False,
            'extreme_conditions': [],
            'multiple_confirmations': False
        }
        
        if 'rsi' not in df.columns:
            return conditions
        
        current_rsi = df['rsi'].iloc[-1]
        
        # RSI overbought/oversold
        if current_rsi > self.overbought_level:
            conditions['overbought'] = True
            conditions['extreme_conditions'].append(f'RSI overbought ({current_rsi:.1f})')
        elif current_rsi < self.oversold_level:
            conditions['oversold'] = True
            conditions['extreme_conditions'].append(f'RSI oversold ({current_rsi:.1f})')
        
        # Stochastic confirmation
        if 'stoch_k' in df.columns:
            stoch_k = df['stoch_k'].iloc[-1]
            if stoch_k > 80 and conditions['overbought']:
                conditions['multiple_confirmations'] = True
                conditions['extreme_conditions'].append(f'Stochastic confirms overbought ({stoch_k:.1f})')
            elif stoch_k < 20 and conditions['oversold']:
                conditions['multiple_confirmations'] = True
                conditions['extreme_conditions'].append(f'Stochastic confirms oversold ({stoch_k:.1f})')
        
        # CCI confirmation
        if 'cci' in df.columns:
            cci = df['cci'].iloc[-1]
            if cci > 100 and conditions['overbought']:
                conditions['multiple_confirmations'] = True
                conditions['extreme_conditions'].append(f'CCI confirms overbought ({cci:.1f})')
            elif cci < -100 and conditions['oversold']:
                conditions['multiple_confirmations'] = True
                conditions['extreme_conditions'].append(f'CCI confirms oversold ({cci:.1f})')
        
        return conditions
    
    def generate_indicator_trading_signals(self, indicator_signals: Dict[str, Any], 
                                         divergences: List[Dict[str, Any]], 
                                         ob_os_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on indicator analysis
        """
        trading_signals = []
        
        # Trend following signals
        if len(indicator_signals['bullish_signals']) > len(indicator_signals['bearish_signals']):
            trading_signals.append({
                'type': 'trend_following',
                'direction': 'bullish',
                'strength': 0.6,
                'reason': 'Multiple bullish indicator signals',
                'market_note': f'{self.market_type} trend following setup'
            })
        elif len(indicator_signals['bearish_signals']) > len(indicator_signals['bullish_signals']):
            trading_signals.append({
                'type': 'trend_following',
                'direction': 'bearish',
                'strength': 0.6,
                'reason': 'Multiple bearish indicator signals',
                'market_note': f'{self.market_type} trend following setup'
            })
        
        # Divergence signals
        for divergence in divergences:
            trading_signals.append({
                'type': 'divergence_reversal',
                'direction': 'bullish' if 'bullish' in divergence['type'] else 'bearish',
                'strength': divergence['strength'],
                'reason': divergence['type'],
                'market_note': divergence['market_implication']
            })
        
        # Overbought/oversold signals
        if ob_os_conditions['oversold']:
            trading_signals.append({
                'type': 'mean_reversion',
                'direction': 'bullish',
                'strength': 0.8 if ob_os_conditions['multiple_confirmations'] else 0.6,
                'reason': 'Oversold conditions',
                'market_note': f'{self.market_type} oversold bounce opportunity'
            })
        elif ob_os_conditions['overbought']:
            trading_signals.append({
                'type': 'mean_reversion',
                'direction': 'bearish',
                'strength': 0.8 if ob_os_conditions['multiple_confirmations'] else 0.6,
                'reason': 'Overbought conditions',
                'market_note': f'{self.market_type} overbought correction opportunity'
            })
        
        return trading_signals
    
    def calculate_indicator_signal_strength(self, indicator_signals: Dict[str, Any], 
                                          divergences: List[Dict[str, Any]], 
                                          ob_os_conditions: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate technical indicator signal strength
        """
        strength_factors = []
        
        # Signal consensus strength
        total_signals = indicator_signals['signal_count']
        if total_signals > 0:
            bullish_ratio = len(indicator_signals['bullish_signals']) / total_signals
            bearish_ratio = len(indicator_signals['bearish_signals']) / total_signals
            consensus_strength = max(bullish_ratio, bearish_ratio)
            strength_factors.append(consensus_strength)
        
        # Divergence strength
        if divergences:
            avg_divergence_strength = np.mean([div['strength'] for div in divergences])
            strength_factors.append(avg_divergence_strength)
        
        # Extreme condition strength
        if ob_os_conditions['overbought'] or ob_os_conditions['oversold']:
            extreme_strength = 0.8 if ob_os_conditions['multiple_confirmations'] else 0.6
            strength_factors.append(extreme_strength)
        
        # Market-specific adjustments
        market_strength = self.get_market_indicator_strength(df)
        strength_factors.append(market_strength)
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def get_market_indicator_strength(self, df: pd.DataFrame) -> float:
        """Get market-specific indicator strength"""
        if self.market_type == 'forex':
            # Forex indicators more reliable during major sessions
            if hasattr(df.index[-1], 'hour'):
                hour = df.index[-1].hour
                if 8 <= hour <= 22:
                    return 0.8
                else:
                    return 0.5
            return 0.7
        
        elif self.market_type == 'crypto':
            # Crypto indicators consistent 24/7
            return 0.8
        
        return 0.7
    
    def update_indicator_tracking(self, indicator_signals: Dict[str, Any], 
                                divergences: List[Dict[str, Any]], 
                                ob_os_conditions: Dict[str, Any]):
        """Update indicator tracking"""
        # Track indicator signals
        signal_event = {
            'timestamp': datetime.now(timezone.utc),
            'bullish_signals': len(indicator_signals['bullish_signals']),
            'bearish_signals': len(indicator_signals['bearish_signals']),
            'market_type': self.market_type
        }
        self.indicator_signals.append(signal_event)
        
        # Track divergences
        for divergence in divergences:
            divergence['timestamp'] = datetime.now(timezone.utc)
            self.divergence_events.append(divergence)
        
        # Track extreme conditions
        if ob_os_conditions['overbought'] or ob_os_conditions['oversold']:
            ob_os_event = {
                'timestamp': datetime.now(timezone.utc),
                'condition': 'overbought' if ob_os_conditions['overbought'] else 'oversold',
                'multiple_confirmations': ob_os_conditions['multiple_confirmations'],
                'market_type': self.market_type
            }
            self.overbought_oversold_events.append(ob_os_event)
        
        # Limit tracking sizes
        if len(self.indicator_signals) > 100:
            self.indicator_signals = self.indicator_signals[-100:]
        
        if len(self.divergence_events) > 50:
            self.divergence_events = self.divergence_events[-50:]
        
        if len(self.overbought_oversold_events) > 50:
            self.overbought_oversold_events = self.overbought_oversold_events[-50:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_indicator_summary(self) -> Dict[str, Any]:
        """Get comprehensive technical indicator summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'indicator_signals_count': len(self.indicator_signals),
            'divergence_events_count': len(self.divergence_events),
            'overbought_oversold_events_count': len(self.overbought_oversold_events),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'rsi_window': self.rsi_window,
                'adx_window': self.adx_window,
                'atr_window': self.atr_window,
                'sma_periods': [self.sma_short_period, self.sma_long_period],
                'macd_settings': [self.macd_fast, self.macd_slow, self.macd_signal],
                'overbought_level': self.overbought_level,
                'oversold_level': self.oversold_level
            }
        }
    
    def requires_continuous_processing(self) -> bool:
        """Technical indicators agent doesn't need continuous processing"""
        return False