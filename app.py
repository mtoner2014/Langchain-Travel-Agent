"""
Streamlit Chat UI for Michael's Travel Planning Agent
A beautiful and user-friendly interface for travel planning.
"""

import streamlit as st
import uuid
from datetime import datetime
from travel_agent import create_travel_agent, parse_travel_input
from langchain_core.messages import HumanMessage, AIMessage

# Page configuration
st.set_page_config(
    page_title="Michael's Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        padding: 1rem;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #E3F2FD;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FFF3E0;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #E8F5E9;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 10px;
    }
    .sample-input {
        background-color: #F5F5F5;
        border-radius: 5px;
        padding: 1rem;
        font-family: monospace;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "agent" not in st.session_state:
        st.session_state.agent, st.session_state.memory = create_travel_agent()


def render_sidebar():
    """Render the sidebar with instructions and sample input."""
    with st.sidebar:
        st.markdown("## How to Use")

        st.markdown("""
        ### Input Format
        Enter your travel itinerary in this format:

        ```
        City1: [City Name] [Date YYYY-MM-DD]
        [Attraction];[Time Range]
        [Attraction];[Time Range]

        City2: [City Name] [Date YYYY-MM-DD]
        [Attraction];[Time Range]
        ```
        """)

        st.markdown("---")

        st.markdown("### Sample Input")
        sample_text = """City1: Toronto 2026-01-31
CN Tower;8am-9am
Royal Ontario Museum;10am-11am

City2: Chicago 2026-02-01
The Art Institute of Chicago;9am-11am
Griffin Museum of Science and Industry;12pm-13pm"""

        st.code(sample_text, language=None)

        if st.button("Use Sample Input", type="primary"):
            return sample_text

        st.markdown("---")

        st.markdown("### Features")
        st.markdown("""
        - Weather forecasts for each city
        - Clothing recommendations
        - Umbrella suggestions
        - Air quality monitoring
        - Mask requirements (Health Canada guidelines)
        - Tourist attraction addresses
        - Conversation memory for follow-ups
        """)

        st.markdown("---")

        st.markdown("### Restrictions")
        st.markdown("""
        - Max 4 days air quality forecast
        - No travel to countries on Canada's "Avoid all travel" list
        """)

        st.markdown("---")

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.agent, st.session_state.memory = create_travel_agent()
            st.rerun()

    return None


def process_message(user_input: str):
    """Process user message and get agent response."""
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    try:
        # Create the message
        messages = [HumanMessage(content=user_input)]

        # Run the agent
        result = st.session_state.agent.invoke({"messages": messages}, config)

        # Get the last AI message
        for message in reversed(result["messages"]):
            if isinstance(message, AIMessage):
                return message.content

        return "I apologize, but I couldn't generate a response. Please try again."

    except Exception as e:
        return f"An error occurred: {str(e)}. Please check your API keys and try again."


def main():
    """Main application."""
    initialize_session_state()

    # Header
    st.markdown('<div class="main-header">✈️ Michael\'s Travel Planner</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Your AI-powered multi-city travel planning assistant</div>', unsafe_allow_html=True)

    # Render sidebar and check for sample input
    sample_input = render_sidebar()

    # Info box
    with st.expander("About This App", expanded=False):
        st.markdown("""
        This travel planning agent helps Michael plan multi-city trips around the world.

        **What it provides:**
        - Detailed weather forecasts with clothing recommendations
        - Air quality index with mask requirements based on Canadian Health Authority guidelines
        - Tourist attraction addresses via Google Places API
        - Conversation memory for follow-up questions

        **How to use:**
        1. Enter your travel itinerary in the format shown in the sidebar
        2. Ask follow-up questions about your trip
        3. Get recommendations for clothing, umbrellas, and masks
        """)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle sample input button
    if sample_input:
        st.session_state.pending_input = sample_input

    # Chat input
    if prompt := st.chat_input("Enter your travel plan or ask a question..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Process and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Planning your trip..."):
                response = process_message(prompt)
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

    # Handle pending input from sample button
    if hasattr(st.session_state, 'pending_input') and st.session_state.pending_input:
        pending = st.session_state.pending_input
        st.session_state.pending_input = None

        # Create a formatted request
        full_prompt = f"""Please create a detailed travel plan for the following itinerary:

{pending}

Please include:
1. Weather forecast for each city
2. Clothing recommendations
3. Whether I need an umbrella
4. Air quality and mask requirements
5. Addresses for all attractions
6. Total masks needed for the trip"""

        st.session_state.messages.append({"role": "user", "content": full_prompt})

        with st.chat_message("user"):
            st.markdown(full_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Planning your trip..."):
                response = process_message(full_prompt)
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    # Handle pending follow-up from quick action buttons
    if hasattr(st.session_state, 'pending_followup') and st.session_state.pending_followup:
        followup = st.session_state.pending_followup
        st.session_state.pending_followup = None

        st.session_state.messages.append({"role": "user", "content": followup})

        with st.chat_message("user"):
            st.markdown(followup)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_message(followup)
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    # Quick action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("What clothes should I pack?"):
            st.session_state.pending_followup = "Based on my travel plan, what clothes should I pack for the entire trip?"
            st.rerun()

    with col2:
        if st.button("Do I need masks?"):
            st.session_state.pending_followup = "How many masks do I need for my trip and why?"
            st.rerun()

    with col3:
        if st.button("Suggest more attractions"):
            st.session_state.pending_followup = "Can you suggest more tourist attractions to visit in the cities I'm traveling to?"
            st.rerun()

    with col4:
        if st.button("Umbrella needed?"):
            st.session_state.pending_followup = "Do I need to bring an umbrella for any part of my trip?"
            st.rerun()


if __name__ == "__main__":
    main()
