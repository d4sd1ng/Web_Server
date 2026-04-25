"""
TINY Agent Status Addon
Just 5 lines to add to your existing Streamlit GUI
"""

import streamlit as st

def add_tiny_agent_status():
    """
    TINY agent status - just add this ONE function call to your existing GUI
    Adds only 3 lines to your sidebar, preserves everything else
    """
    
    # Initialize agent system state
    if 'agents_active' not in st.session_state:
        st.session_state.agents_active = False
    
    # TINY addition to your existing sidebar (just 3 lines)
    st.sidebar.markdown("---")
    status_text = "🟢 43 Agents Active" if st.session_state.agents_active else "🔴 43 Agents Ready"
    st.sidebar.write(f"🤖 **Agent System:** {status_text}")
    
    # Simple toggle
    if st.sidebar.button("🔄 Toggle Agents"):
        st.session_state.agents_active = not st.session_state.agents_active
        st.rerun()

# TO INTEGRATE: Just add this ONE line to your existing tradingbot_gui.py:
# add_tiny_agent_status()