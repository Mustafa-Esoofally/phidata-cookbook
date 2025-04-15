"""
GitHub Repository Analyzer App - Chat Focused
"""

import json
import logging
import os
import re

import streamlit as st

# Import agent functionality
from agents import get_github_chat_agent
from dotenv import load_dotenv
from prompts import SIDEBAR_EXAMPLE_QUERIES

# Import utilities and prompts
from utils import (
    CUSTOM_CSS,
    add_message,
    render_sidebar,
)

# App configuration
st.set_page_config(
    page_title="GitHub Repo Chat",
    page_icon="🐙",
    layout="wide",
)

# Add custom styles
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

st.markdown("<h1 class='main-header'>🐙 GitHub Repo Chat</h1>", unsafe_allow_html=True)
st.markdown("Chat with your GitHub repositories using natural language.")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_repo" not in st.session_state:
    st.session_state.selected_repo = None


if "repo_list" not in st.session_state:
    st.session_state.repo_list = []
if "agent" not in st.session_state:
    st.session_state.agent = None  # Initialize agent later

# Render the sidebar using the utility function
with st.sidebar:
    render_sidebar()

if st.session_state.selected_repo and not st.session_state.agent:
    st.session_state.agent = get_github_chat_agent(
        repo_name=st.session_state.selected_repo,
    )

    if not st.session_state.agent:
        # Error handling is now within get_github_chat_agent, but we can add UI feedback
        # Display a generic error; specific logging happened in agents.py
        st.error("Failed to initialize the AI agent. Check logs for details.")
    else:
        logging.info("Agent initialized successfully via agents.py function.")

if st.session_state.selected_repo:
    st.markdown(f"### Chatting about: `{st.session_state.selected_repo}`")
else:
    st.info("👈 Please select a repository from the sidebar to start chatting.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(
    "Ask something about the repository..."
    if st.session_state.selected_repo
    else "Please select a repository first",
    disabled=not st.session_state.selected_repo,
):
    logging.info(f"User input received: {prompt}")
    # Add user message to chat history using the utility function
    add_message("user", prompt)
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare query for the agent
    full_query = prompt
    logging.info(f"Query prepared for agent: {full_query}")

    # Get assistant response
    if st.session_state.agent:
        with st.spinner("Thinking..."):
            try:
                logging.info("Running agent...")
                # Use the stored agent instance
                # The agent.run() call implicitly uses the agent's memory
                # (managed by the Agno framework) to consider previous turns.
                result = st.session_state.agent.run(full_query)
                assistant_response = (
                    str(result.content) if hasattr(result, "content") else str(result)
                )
                logging.info(f"Agent raw response: {assistant_response}")

                # Display assistant response in chat message container
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                # Add assistant response to chat history using the utility function
                add_message("assistant", assistant_response)

            except Exception as e:
                logging.error(f"Error during agent execution: {e}", exc_info=True)
                st.error(f"An error occurred: {e}")
                # Optionally add error message to chat
                error_message = f"Sorry, I encountered an error: {e}"
                with st.chat_message("assistant"):
                    st.markdown(error_message)
                # Add error message to chat history
                add_message("assistant", error_message)
    else:
        # Update error message if agent failed init due to missing token earlier
        if not st.session_state.github_token:
            st.error(
                "Agent cannot run because the GitHub token (GITHUB_ACCESS_TOKEN env var) is missing."
            )
        else:
            st.error("Agent is not initialized. Please check configuration and logs.")
        logging.warning("Agent run skipped: Agent not initialized.")
