"""
Power of Three (PO3) Agent
Analyzes Accumulation, Manipulation, Distribution phases
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

from agents.base_agent import ICTSMCAgent


class PowerOfThreeAgent(ICTSMCAgent):
    """
    Specialized agent for Power of Three analysis
    Identifies AMD (Accumulation, Manipulation, Distribution) phases
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("power_of_three", config)
        
        # PO3 configuration
        self.accumulation_threshold = config.get('accumulation_threshold', 0.002)  # 0.2%
        self.manipulation_threshold = config.get('manipulation_threshold', 0.005)  # 0.5%
        self.distribution_threshold = config.get('distribution_threshold', 0.01)   # 1.0%
        self.phase_min_duration = config.get('phase_min_duration', 5)  # Minimum bars per phase
        
        # Market type specialization
        self.market_type = config.get('market_type', 'crypto')
        
        # PO3 tracking
        self.current_phase = 'unknown'
        self.phase_history = []
        self.amd_cycles = []
        self.phase_transitions = []
        
        # Market-specific adjustments
        self.apply_market_specific_config()
        
        self.logger.info(f"Power of Three Agent initialized for {self.market_type} market")
    
    def apply_market_specific_config(self):
        """Apply market-specific PO3 configuration"""
        if self.market_type == 'forex':
            # Forex: Tighter thresholds, longer phases
            self.accumulation_threshold = max(self.accumulation_threshold, 0.001)  # 0.1%
            self.manipulation_threshold = max(self.manipulation_threshold, 0.003)  # 0.3%
            self.distribution_threshold = max(self.distribution_threshold, 0.008)  # 0.8%
            self.phase_min_duration = max(self.phase_min_duration, 8)  # Longer phases
            self.session_dependency = True
        elif self.market_type == 'crypto':
            # Crypto: Wider thresholds, shorter phases
            self.accumulation_threshold = min(self.accumulation_threshold, 0.003)  # 0.3%
            self.manipulation_threshold = min(self.manipulation_threshold, 0.008)  # 0.8%
            self.distribution_threshold = min(self.distribution_threshold, 0.015)  # 1.5%
            self.phase_min_duration = min(self.phase_min_duration, 5)   # Shorter phases
            self.session_dependency = False
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process market data to analyze Power of Three phases
        
        Args:
            data: Dictionary containing 'df' (OHLCV DataFrame) and 'symbol'
            
        Returns:
            Dictionary with PO3 analysis results
        """
        required_fields = ['df', 'symbol']
        if not self.validate_data(data, required_fields):
            return {}
        
        df = data['df']
        symbol = data['symbol']
        
        if df.empty or len(df) < 20:
            return {'current_phase': 'unknown', 'signal_strength': 0.0}
        
        try:
            # Detect current PO3 phase
            current_phase_analysis = self.detect_current_phase(df)
            
            # Analyze phase progression
            phase_progression = self.analyze_phase_progression(df)
            
            # Detect complete AMD cycles
            amd_cycles = self.detect_amd_cycles(df)
            
            # Calculate phase strength
            phase_strength = self.calculate_phase_strength(current_phase_analysis, df)
            
            # Update tracking
            self.update_po3_tracking(current_phase_analysis, phase_progression, amd_cycles)
            
            # Calculate signal strength
            signal_strength = self.calculate_po3_signal_strength(
                current_phase_analysis, phase_progression, df
            )
            
            results = {
                'agent_id': self.agent_id,
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_phase': current_phase_analysis,
                'phase_progression': phase_progression,
                'amd_cycles': amd_cycles,
                'phase_strength': phase_strength,
                'signal_strength': signal_strength,
                'market_type': self.market_type,
                'trading_strategy': self.get_po3_trading_strategy(current_phase_analysis, phase_progression)
            }
            
            # Publish PO3 phase signals
            if current_phase_analysis['phase'] != 'unknown':
                self.publish("po3_phase_detected", {
                    'symbol': symbol,
                    'phase': current_phase_analysis['phase'],
                    'phase_strength': phase_strength,
                    'signal_strength': signal_strength,
                    'market_type': self.market_type
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing PO3 data for {symbol}: {e}")
            return {'current_phase': 'unknown', 'signal_strength': 0.0, 'error': str(e)}
    
    def detect_current_phase(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect current Power of Three phase
        """
        if len(df) < 15:
            return {'phase': 'unknown', 'confidence': 0.0}
        
        # Analyze recent price action for phase identification
        recent_data = df.iloc[-15:]
        
        # Calculate price range and volatility
        price_range = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean()
        price_volatility = recent_data['close'].std() / recent_data['close'].mean()
        
        # Volume analysis (if available)
        volume_pattern = 'unknown'
        if 'volume' in recent_data.columns:
            volume_trend = self.analyze_volume_trend(recent_data)
            volume_pattern = volume_trend
        
        # Phase detection logic
        phase = self.classify_phase(price_range, price_volatility, volume_pattern, recent_data)
        confidence = self.calculate_phase_confidence(phase, recent_data)
        
        return {
            'phase': phase,
            'confidence': confidence,
            'price_range': price_range,
            'volatility': price_volatility,
            'volume_pattern': volume_pattern,
            'phase_duration': self.estimate_phase_duration(phase, recent_data)
        }
    
    def classify_phase(self, price_range: float, volatility: float, volume_pattern: str, df: pd.DataFrame) -> str:
        """
        Classify current market phase
        """
        # Accumulation phase characteristics
        if (price_range < self.accumulation_threshold and 
            volatility < self.accumulation_threshold * 0.5):
            if self.market_type == 'crypto' and volume_pattern == 'increasing':
                return 'accumulation'
            elif self.market_type == 'forex':
                return 'accumulation'
        
        # Distribution phase characteristics
        elif (price_range > self.distribution_threshold or 
              volatility > self.distribution_threshold * 0.8):
            if self.market_type == 'crypto' and volume_pattern == 'decreasing':
                return 'distribution'
            elif self.market_type == 'forex':
                return 'distribution'
        
        # Manipulation phase characteristics
        elif (self.accumulation_threshold < price_range < self.distribution_threshold and
              self.manipulation_threshold * 0.5 < volatility < self.manipulation_threshold * 1.5):
            
            # Check for manipulation patterns
            if self.detect_manipulation_patterns(df):
                return 'manipulation'
        
        return 'transition'  # Between phases
    
    def detect_manipulation_patterns(self, df: pd.DataFrame) -> bool:
        """
        Detect manipulation patterns within the data
        """
        if len(df) < 10:
            return False
        
        # Look for manipulation characteristics
        recent_data = df.iloc[-10:]
        
        # Sudden spikes followed by reversals
        for i in range(1, len(recent_data) - 1):
            prev_close = recent_data['close'].iloc[i-1]
            curr_high = recent_data['high'].iloc[i]
            curr_close = recent_data['close'].iloc[i]
            next_close = recent_data['close'].iloc[i+1]
            
            # Check for spike and reversal
            spike_up = (curr_high - prev_close) / prev_close > self.manipulation_threshold
            reversal_down = (curr_close - next_close) / curr_close > self.manipulation_threshold * 0.5
            
            if spike_up and reversal_down:
                return True
            
            # Check for drop and reversal
            curr_low = recent_data['low'].iloc[i]
            spike_down = (prev_close - curr_low) / prev_close > self.manipulation_threshold
            reversal_up = (next_close - curr_close) / curr_close > self.manipulation_threshold * 0.5
            
            if spike_down and reversal_up:
                return True
        
        return False
    
    def analyze_volume_trend(self, df: pd.DataFrame) -> str:
        """Analyze volume trend for phase identification"""
        if 'volume' not in df.columns or len(df) < 5:
            return 'unknown'
        
        volume = df['volume']
        early_volume = volume.iloc[:len(volume)//2].mean()
        late_volume = volume.iloc[len(volume)//2:].mean()
        
        if late_volume > early_volume * 1.2:
            return 'increasing'
        elif late_volume < early_volume * 0.8:
            return 'decreasing'
        else:
            return 'stable'
    
    def calculate_phase_confidence(self, phase: str, df: pd.DataFrame) -> float:
        """Calculate confidence in phase identification"""
        if phase == 'unknown':
            return 0.0
        
        confidence_factors = []
        
        # Duration confidence (longer phases = higher confidence)
        if len(df) >= self.phase_min_duration:
            duration_confidence = min(len(df) / (self.phase_min_duration * 2), 1.0)
            confidence_factors.append(duration_confidence)
        
        # Consistency confidence
        if len(df) >= 10:
            consistency = self.calculate_phase_consistency(phase, df)
            confidence_factors.append(consistency)
        
        # Market-specific confidence
        if self.market_type == 'forex' and self.session_dependency:
            session_confidence = self.calculate_forex_session_confidence()
            confidence_factors.append(session_confidence)
        elif self.market_type == 'crypto':
            volume_confidence = self.calculate_crypto_volume_confidence(df)
            confidence_factors.append(volume_confidence)
        
        return np.mean(confidence_factors) if confidence_factors else 0.5
    
    def calculate_phase_consistency(self, phase: str, df: pd.DataFrame) -> float:
        """Calculate how consistent the phase characteristics are"""
        if len(df) < 5:
            return 0.5
        
        # Split data into segments and check consistency
        segment_size = max(3, len(df) // 3)
        segments = [df.iloc[i:i+segment_size] for i in range(0, len(df), segment_size)]
        
        consistent_segments = 0
        
        for segment in segments:
            if len(segment) >= 3:
                segment_range = (segment['high'].max() - segment['low'].min()) / segment['close'].mean()
                segment_volatility = segment['close'].std() / segment['close'].mean()
                
                # Check if segment matches phase characteristics
                if phase == 'accumulation':
                    if segment_range < self.accumulation_threshold * 1.5:
                        consistent_segments += 1
                elif phase == 'distribution':
                    if segment_range > self.distribution_threshold * 0.7:
                        consistent_segments += 1
                elif phase == 'manipulation':
                    if self.accumulation_threshold < segment_range < self.distribution_threshold:
                        consistent_segments += 1
        
        return consistent_segments / len(segments) if segments else 0.5
    
    def calculate_forex_session_confidence(self) -> float:
        """Calculate session-based confidence for forex"""
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        
        # Higher confidence during major sessions
        if 13 <= hour <= 16:  # London-NY overlap
            return 0.9
        elif 8 <= hour <= 22:  # Major sessions
            return 0.8
        else:
            return 0.5
    
    def calculate_crypto_volume_confidence(self, df: pd.DataFrame) -> float:
        """Calculate volume-based confidence for crypto"""
        if 'volume' not in df.columns:
            return 0.5
        
        # Volume consistency indicates phase confidence
        volume_cv = df['volume'].std() / df['volume'].mean()
        
        # Lower CV = more consistent volume = higher confidence
        return max(0.3, 1.0 - volume_cv)
    
    def analyze_phase_progression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze progression through PO3 phases
        """
        if len(df) < 30:
            return {'progression': 'insufficient_data'}
        
        # Divide recent data into three sections
        section_size = len(df) // 3
        sections = [
            df.iloc[:section_size],
            df.iloc[section_size:section_size*2],
            df.iloc[section_size*2:]
        ]
        
        section_phases = []
        for i, section in enumerate(sections):
            if len(section) >= 5:
                section_analysis = self.detect_current_phase(section)
                section_phases.append({
                    'section': i + 1,
                    'phase': section_analysis['phase'],
                    'confidence': section_analysis['confidence']
                })
        
        # Analyze progression pattern
        progression_pattern = self.identify_progression_pattern(section_phases)
        
        return {
            'section_phases': section_phases,
            'progression_pattern': progression_pattern,
            'amd_cycle_completion': self.check_amd_cycle_completion(section_phases)
        }
    
    def identify_progression_pattern(self, section_phases: List[Dict[str, Any]]) -> str:
        """Identify the progression pattern through phases"""
        if len(section_phases) < 3:
            return 'unknown'
        
        phases = [section['phase'] for section in section_phases]
        
        # Classic AMD progression
        if phases == ['accumulation', 'manipulation', 'distribution']:
            return 'classic_amd'
        
        # Reverse AMD (distribution first)
        elif phases == ['distribution', 'manipulation', 'accumulation']:
            return 'reverse_amd'
        
        # Extended accumulation
        elif phases.count('accumulation') >= 2:
            return 'extended_accumulation'
        
        # Extended distribution
        elif phases.count('distribution') >= 2:
            return 'extended_distribution'
        
        # Manipulation dominant
        elif phases.count('manipulation') >= 2:
            return 'manipulation_dominant'
        
        else:
            return 'irregular_pattern'
    
    def check_amd_cycle_completion(self, section_phases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if a complete AMD cycle is forming or completed"""
        if len(section_phases) < 3:
            return {'cycle_complete': False, 'cycle_stage': 'early'}
        
        phases = [section['phase'] for section in section_phases]
        
        # Check for complete cycle
        has_accumulation = 'accumulation' in phases
        has_manipulation = 'manipulation' in phases
        has_distribution = 'distribution' in phases
        
        if has_accumulation and has_manipulation and has_distribution:
            return {
                'cycle_complete': True,
                'cycle_stage': 'complete',
                'cycle_type': self.identify_progression_pattern(section_phases),
                'next_expected_phase': 'accumulation'  # New cycle starts
            }
        
        elif has_accumulation and has_manipulation:
            return {
                'cycle_complete': False,
                'cycle_stage': 'late',
                'next_expected_phase': 'distribution'
            }
        
        elif has_accumulation:
            return {
                'cycle_complete': False,
                'cycle_stage': 'early',
                'next_expected_phase': 'manipulation'
            }
        
        else:
            return {
                'cycle_complete': False,
                'cycle_stage': 'unknown',
                'next_expected_phase': 'accumulation'
            }
    
    def detect_amd_cycles(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect complete AMD cycles in historical data
        """
        cycles = []
        
        if len(self.phase_history) < 10:
            return cycles
        
        # Look for complete AMD sequences in history
        for i in range(len(self.phase_history) - 2):
            if (self.phase_history[i]['phase'] == 'accumulation' and
                self.phase_history[i+1]['phase'] == 'manipulation' and
                self.phase_history[i+2]['phase'] == 'distribution'):
                
                cycle = {
                    'start_timestamp': self.phase_history[i]['timestamp'],
                    'end_timestamp': self.phase_history[i+2]['timestamp'],
                    'accumulation_duration': self.phase_history[i]['duration'],
                    'manipulation_duration': self.phase_history[i+1]['duration'],
                    'distribution_duration': self.phase_history[i+2]['duration'],
                    'total_cycle_duration': (self.phase_history[i+2]['timestamp'] - 
                                           self.phase_history[i]['timestamp']).total_seconds() / 3600,
                    'market_type': self.market_type
                }
                cycles.append(cycle)
        
        return cycles
    
    def estimate_phase_duration(self, phase: str, df: pd.DataFrame) -> int:
        """Estimate how long the current phase has been active"""
        # Simplified duration estimation
        return len(df)  # Would be enhanced with actual phase start detection
    
    def calculate_phase_strength(self, phase_analysis: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate strength of current phase
        """
        phase = phase_analysis['phase']
        confidence = phase_analysis['confidence']
        
        if phase == 'unknown':
            return 0.0
        
        strength_factors = []
        
        # Base phase strength
        phase_strengths = {
            'accumulation': 0.6,
            'manipulation': 0.8,  # Manipulation is most actionable
            'distribution': 0.7,
            'transition': 0.4
        }
        
        base_strength = phase_strengths.get(phase, 0.5)
        strength_factors.append(base_strength)
        
        # Confidence factor
        strength_factors.append(confidence)
        
        # Market-specific strength
        if self.market_type == 'forex':
            # Forex PO3 strength based on session
            session_strength = self.calculate_forex_session_confidence()
            strength_factors.append(session_strength * 0.8)
        elif self.market_type == 'crypto':
            # Crypto PO3 strength based on volume
            volume_strength = self.calculate_crypto_volume_confidence(df)
            strength_factors.append(volume_strength * 0.8)
        
        return np.mean(strength_factors)
    
    def get_po3_trading_strategy(self, current_phase_analysis: Dict[str, Any], 
                               phase_progression: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get trading strategy based on PO3 analysis
        """
        strategies = []
        phase = current_phase_analysis['phase']
        
        if phase == 'accumulation':
            strategies.append({
                'phase': 'accumulation',
                'strategy': 'prepare_for_manipulation',
                'action': 'Monitor for manipulation phase entry',
                'bias': 'neutral_to_bullish',
                'risk_level': 'low',
                'market_note': self.get_accumulation_market_note()
            })
        
        elif phase == 'manipulation':
            strategies.append({
                'phase': 'manipulation',
                'strategy': 'trade_the_manipulation',
                'action': 'Trade breakouts and reversals',
                'bias': 'directional_trades',
                'risk_level': 'medium_high',
                'market_note': self.get_manipulation_market_note()
            })
        
        elif phase == 'distribution':
            strategies.append({
                'phase': 'distribution',
                'strategy': 'prepare_for_cycle_end',
                'action': 'Take profits, reduce exposure',
                'bias': 'neutral_to_bearish',
                'risk_level': 'high',
                'market_note': self.get_distribution_market_note()
            })
        
        # Add cycle-based strategy
        cycle_completion = phase_progression.get('amd_cycle_completion', {})
        if cycle_completion.get('cycle_complete'):
            strategies.append({
                'phase': 'cycle_completion',
                'strategy': 'new_cycle_preparation',
                'action': 'Prepare for new AMD cycle',
                'bias': 'reset_to_accumulation',
                'risk_level': 'low',
                'market_note': 'Complete AMD cycle - new cycle beginning'
            })
        
        return strategies
    
    def get_accumulation_market_note(self) -> str:
        """Get market-specific note for accumulation phase"""
        if self.market_type == 'forex':
            return "Forex accumulation: Central banks and institutions building positions"
        elif self.market_type == 'crypto':
            return "Crypto accumulation: Whales and institutions accumulating before major move"
        return "Accumulation phase: Smart money building positions"
    
    def get_manipulation_market_note(self) -> str:
        """Get market-specific note for manipulation phase"""
        if self.market_type == 'forex':
            return "Forex manipulation: Stop hunting and liquidity grabs by major players"
        elif self.market_type == 'crypto':
            return "Crypto manipulation: Whale manipulation to shake out weak hands"
        return "Manipulation phase: False moves to trap retail traders"
    
    def get_distribution_market_note(self) -> str:
        """Get market-specific note for distribution phase"""
        if self.market_type == 'forex':
            return "Forex distribution: Institutional profit-taking and position unwinding"
        elif self.market_type == 'crypto':
            return "Crypto distribution: Whale profit-taking and smart money exit"
        return "Distribution phase: Smart money taking profits"
    
    def calculate_po3_signal_strength(self, current_phase_analysis: Dict[str, Any], 
                                    phase_progression: Dict[str, Any], df: pd.DataFrame) -> float:
        """
        Calculate Power of Three signal strength
        """
        strength_factors = []
        
        # Phase strength
        phase_strength = self.calculate_phase_strength(current_phase_analysis, df)
        strength_factors.append(phase_strength)
        
        # Progression strength
        progression_pattern = phase_progression.get('progression_pattern', 'unknown')
        if progression_pattern in ['classic_amd', 'reverse_amd']:
            strength_factors.append(0.9)  # Strong pattern
        elif 'extended' in progression_pattern:
            strength_factors.append(0.7)  # Moderate pattern
        else:
            strength_factors.append(0.5)  # Weak pattern
        
        # Cycle completion strength
        cycle_completion = phase_progression.get('amd_cycle_completion', {})
        if cycle_completion.get('cycle_complete'):
            strength_factors.append(0.8)  # Strong signal at cycle completion
        
        return np.mean(strength_factors) if strength_factors else 0.0
    
    def update_po3_tracking(self, current_phase_analysis: Dict[str, Any], 
                           phase_progression: Dict[str, Any], amd_cycles: List[Dict[str, Any]]):
        """Update Power of Three tracking"""
        # Update current phase
        new_phase = current_phase_analysis['phase']
        
        if new_phase != self.current_phase:
            # Phase transition
            if self.current_phase != 'unknown':
                transition = {
                    'timestamp': datetime.now(timezone.utc),
                    'from_phase': self.current_phase,
                    'to_phase': new_phase,
                    'market_type': self.market_type
                }
                self.phase_transitions.append(transition)
            
            self.current_phase = new_phase
            
            # Add to phase history
            phase_entry = {
                'timestamp': datetime.now(timezone.utc),
                'phase': new_phase,
                'confidence': current_phase_analysis['confidence'],
                'duration': current_phase_analysis.get('phase_duration', 0),
                'market_type': self.market_type
            }
            self.phase_history.append(phase_entry)
        
        # Update AMD cycles
        self.amd_cycles.extend(amd_cycles)
        
        # Limit tracking sizes
        if len(self.phase_history) > 100:
            self.phase_history = self.phase_history[-100:]
        
        if len(self.amd_cycles) > 20:
            self.amd_cycles = self.amd_cycles[-20:]
    
    def get_signal_strength(self) -> float:
        """Get current signal strength (0.0 to 1.0)"""
        if not hasattr(self, '_last_signal_strength'):
            return 0.0
        return self._last_signal_strength
    
    def get_po3_summary(self) -> Dict[str, Any]:
        """Get comprehensive Power of Three summary"""
        return {
            'agent_id': self.agent_id,
            'market_type': self.market_type,
            'current_phase': self.current_phase,
            'phase_history_count': len(self.phase_history),
            'amd_cycles_count': len(self.amd_cycles),
            'phase_transitions_count': len(self.phase_transitions),
            'last_signal_strength': self.get_signal_strength(),
            'configuration': {
                'accumulation_threshold': self.accumulation_threshold,
                'manipulation_threshold': self.manipulation_threshold,
                'distribution_threshold': self.distribution_threshold,
                'phase_min_duration': self.phase_min_duration
            }
        }
    
    def get_current_phase(self) -> str:
        """Get current PO3 phase"""
        return self.current_phase
    
    def is_in_manipulation_phase(self) -> bool:
        """Check if currently in manipulation phase"""
        return self.current_phase == 'manipulation'
    
    def is_cycle_complete(self) -> bool:
        """Check if current AMD cycle is complete"""
        return len(self.amd_cycles) > 0 and self.amd_cycles[-1].get('cycle_complete', False)
    
    def requires_continuous_processing(self) -> bool:
        """PO3 agent doesn't need continuous processing"""
        return False