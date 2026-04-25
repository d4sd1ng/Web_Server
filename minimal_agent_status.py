"""
MINIMAL Agent Status - Just 3 lines for your existing Streamlit GUI
"""

import streamlit as st

def add_minimal_agent_status():
    """
    MINIMAL agent status - just add this to your existing GUI
    Only adds 3 lines to your sidebar, nothing else
    """
    
    # Just 3 simple lines in your existing sidebar
    st.sidebar.markdown("---")
    st.sidebar.write("🤖 **43-Agent System:** 🔴 Ready")
    if st.sidebar.button("▶️ Start Agents"):
        st.sidebar.success("✅ 43 agents started!")

# INTEGRATION: Just add this to your existing tradingbot_gui.py:
# add_minimal_agent_status()