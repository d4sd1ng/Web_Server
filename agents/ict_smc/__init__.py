"""
ICT/SMC Trading Agents Package
"""

# Use lazy imports to avoid dependency issues during import
__all__ = [
    'BOSCHOCHAgent',
    'BreakerBlocksAgent', 
    'DisplacementAgent',
    'FairValueGapsAgent',
    'OrderBlocksAgent'
]

def __getattr__(name):
    """Lazy import for agent classes."""
    if name == 'BOSCHOCHAgent':
        from .bos_choch_agent import BOSCHOCHAgent
        return BOSCHOCHAgent
    elif name == 'BreakerBlocksAgent':
        from .breaker_blocks_agent import BreakerBlocksAgent
        return BreakerBlocksAgent
    elif name == 'DisplacementAgent':
        from .displacement_agent import DisplacementAgent
        return DisplacementAgent
    elif name == 'FairValueGapsAgent':
        from .fair_value_gaps_agent import FairValueGapsAgent
        return FairValueGapsAgent
    elif name == 'OrderBlocksAgent':
        from .order_blocks_agent import OrderBlocksAgent
        return OrderBlocksAgent
    else:
        raise AttributeError(f"module {__name__} has no attribute {name}")