import mesop as me

from components.conversation import conversation
from state.state import AppState


def conversation_page(app_state: AppState):
    """Conversation Page with MBUI styling"""
    state = me.state(AppState)
    
    # Hide footer on conversation page for better focus
    state.show_footer = False
    
    # Remove the scaffold wrapper since it's already provided at the page level in main.py
    conversation()