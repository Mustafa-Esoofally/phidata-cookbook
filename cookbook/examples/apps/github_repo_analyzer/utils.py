"""
Utility functions for the GitHub Repository Analyzer.
"""

import datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import streamlit as st
from github import Github, GithubException

# Import prompts - change from relative to direct import
# from .prompts import ABOUT_TEXT
from prompts import ABOUT_TEXT, SIDEBAR_EXAMPLE_QUERIES

# Keep only necessary CSS styles
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #0366d6;
        font-weight: 600;
    }
    .sub-header {
        font-size: 1.5rem;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        color: #2f363d;
        font-weight: 500;
    }
    .metric-card {
        background-color: #f6f8fa;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 5px solid #0366d6;
    }
    .pr-card {
        background-color: #f1f8ff;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        border-left: 5px solid #6f42c1;
    }
</style>
"""

# Predefined list of popular repositories
POPULAR_REPOS = [
    "agno-agi/agno",  # Ensure agno is included
    "facebook/react",
    "tensorflow/tensorflow",
    "microsoft/vscode",
    "torvalds/linux",
    "openai/openai-python",  # Added one more popular repo
]

# Add logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def add_message(
    role: str, content: str, tool_calls: Optional[List[Dict]] = None
) -> None:
    """Add a message to the chat history."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    message = {"role": role, "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls

    st.session_state["messages"].append(message)


def about_widget() -> None:
    """Display the about section with application information."""
    st.sidebar.markdown("### About GitHub Repo Chat")
    st.sidebar.markdown(ABOUT_TEXT)


def get_combined_repositories(user_repo_limit: int = 10) -> list[str]:
    """
    Fetches user repositories (if token provided) and combines them with
    a predefined list of popular repositories.

    Args:
        user_repo_limit: Max number of user-specific repos to fetch.

    Returns:
        A combined list of unique repository names.
    """
    user_repos = []
    try:
        g = Github()
        user = g.get_user()
        logging.info(f"Authenticated as GitHub user: {user.login}")
        repos = user.get_repos(
            affiliation="owner,collaborator,organization_member",
            sort="updated",
            direction="desc",
        )
        count = 0
        for repo in repos:
            if count >= user_repo_limit:
                break
            user_repos.append(repo.full_name)
            count += 1
        logging.info(f"Fetched {len(user_repos)} user repositories: {user_repos}")
    except GithubException as e:
        logging.error(
            f"GitHub API error while fetching user repositories: {e.status} - {e.data}"
        )
        # Don't show error in UI here, let the main app handle UI feedback if needed
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while fetching user repositories: {e}"
        )
        # Don't show error in UI here

    # Combine user repos with popular repos, ensuring uniqueness and order
    combined_list = []
    seen = set()

    # Add user repos first
    for repo in user_repos:
        if repo not in seen:
            combined_list.append(repo)
            seen.add(repo)

    # Add popular repos
    for repo in POPULAR_REPOS:
        if repo not in seen:
            combined_list.append(repo)
            seen.add(repo)

    logging.info(
        f"Final combined repository list ({len(combined_list)}): {combined_list}"
    )
    return combined_list


def render_sidebar() -> None:
    """Renders the sidebar UI components."""
    # Fetch repositories if not already in session state
    if "repo_list" not in st.session_state or not st.session_state.repo_list:
        with st.spinner("Fetching repositories..."):
            st.session_state.repo_list = get_combined_repositories(user_repo_limit=5)
            if not st.session_state.repo_list:
                st.sidebar.warning("Could not load any repositories.")

    # Repository Selection Dropdown
    if st.session_state.repo_list:
        st.header("Select Repository")
        default_repo = "agno-agi/agno"
        options = st.session_state.repo_list
        try:
            default_index = (
                options.index(default_repo) if default_repo in options else 0
            )
        except ValueError:
            default_index = 0

        current_selection_index = default_index
        if st.session_state.get("selected_repo") in options:
            try:
                current_selection_index = options.index(st.session_state.selected_repo)
            except ValueError:
                st.session_state.selected_repo = None
                st.session_state.agent = None
                logging.warning(
                    "Previously selected repo not found in current list. Resetting."
                )
                st.rerun()

        selected_repo = st.selectbox(
            "Choose a repository to chat with:",
            options=options,
            index=current_selection_index,
            key="repo_selector",
        )

        if selected_repo != st.session_state.get("selected_repo"):
            st.session_state.selected_repo = selected_repo
            st.session_state.messages = []
            st.session_state.agent = None
            logging.info(f"Selected repository changed to: {selected_repo}")
            st.rerun()

    # Example Queries
    st.markdown("---")
    st.markdown("### Example Queries")
    for query in SIDEBAR_EXAMPLE_QUERIES:
        st.markdown(f"- {query}")

    # About Widget
    st.markdown("---")
    about_widget()
