import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

# Import local modules
from summarizer import generate_summary  # , generate_flow_graph

# --- Configuration & Initialization ---

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

if not SLACK_BOT_TOKEN:
    logger.critical("SLACK_BOT_TOKEN environment variable not set. Exiting.")
    exit()
if not SLACK_APP_TOKEN:
    # App token is needed for Socket Mode
    logger.critical("SLACK_APP_TOKEN environment variable not set. Exiting.")
    exit()

# Initialize Slack App
try:
    app = App(token=SLACK_BOT_TOKEN)
    logger.info("Slack App initialized successfully.")
except Exception as e:
    logger.exception(f"Error initializing Slack App: {e}")
    exit()

# --- Helper Functions ---


def fetch_thread_messages(
    client, channel_id: str, thread_ts: str
) -> List[Dict[str, Any]]:
    """Fetches all messages from a specific Slack thread using conversations.replies.
    Handles pagination.
    """
    messages = []
    next_cursor = None
    logger.info(f"Fetching messages for thread {thread_ts} in channel {channel_id}")

    try:
        while True:
            logger.debug(
                f"Calling conversations.replies for channel={channel_id}, ts={thread_ts}, cursor={next_cursor}"
            )
            response = client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                cursor=next_cursor,
                limit=200,  # Max limit per page
            )

            fetched_messages = response.get("messages", [])
            logger.debug(f"Fetched {len(fetched_messages)} messages from page.")
            # The first message in the first page is the parent message, skip it if needed
            # For summarization, we usually want the parent message too.
            # if not next_cursor and fetched_messages:
            #      messages.extend(fetched_messages[1:]) # Skip parent message if desired
            # else:
            #      messages.extend(fetched_messages)
            messages.extend(fetched_messages)

            metadata = response.get("response_metadata", {})
            next_cursor = metadata.get("next_cursor")

            if not next_cursor:
                logger.info(
                    f"Finished fetching all pages. Total messages: {len(messages)}"
                )
                break  # Exit loop if no more pages
            else:
                logger.debug(f"More pages exist, next cursor: {next_cursor}")

    except SlackApiError as e:
        logger.error(
            f"Slack API error fetching thread {thread_ts} in {channel_id}: {e.response['error']}"
        )
        # Optionally re-raise or return partial data if needed
        return []  # Return empty list on error
    except Exception as e:
        logger.exception(f"Unexpected error fetching thread messages: {e}")
        return []

    # We often want to remove the mention itself from the messages to summarize
    # Assuming the mention is always the *last* message fetched (the one triggering the event)
    # This might not be robust if there's delay. A better way is to filter by timestamp or user later.
    # if messages:
    #     messages.pop() # Remove the last message (the mention)

    # Filter out messages without text? Optional, summarizer function can handle it.
    # messages = [m for m in messages if m.get("text")]

    logger.info(
        f"Successfully fetched {len(messages)} messages for thread {thread_ts}."
    )
    return messages


# --- Slack Event Handlers ---


@app.event("app_mention")
def handle_app_mention(body: Dict[str, Any], client, say):
    """Handles mentions of the bot."""
    event = body.get("event", {})
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")  # Timestamp of the parent message if in a thread
    event_ts = event.get("ts")  # Timestamp of the mention event itself
    user_id = event.get("user")
    text = event.get("text", "")

    log_prefix = f"[Mention user={user_id} channel={channel_id} thread={thread_ts} event_ts={event_ts}]"
    logger.info(f"{log_prefix} Received app_mention: '{text}'")

    if thread_ts:
        # Mention is within a thread
        logger.info(f"{log_prefix} Mention is in a thread. Processing request.")

        # Acknowledge receipt immediately
        try:
            say(
                text=f"Got it, <@{user_id}>! Fetching thread messages to summarize...",
                thread_ts=thread_ts,
            )
        except SlackApiError as e:
            logger.error(
                f"{log_prefix} Failed to send acknowledgement: {e.response['error']}"
            )
            # Continue anyway if possible

        # Fetch thread messages
        # The `client` object is automatically passed by slack_bolt and is a WebClient instance
        all_messages = fetch_thread_messages(client, channel_id, thread_ts)

        if not all_messages:
            logger.warning(
                f"{log_prefix} No messages retrieved for the thread. Aborting summary."
            )
            try:
                say(
                    text=f"Sorry <@{user_id}>, I couldn't retrieve the messages for this thread.",
                    thread_ts=thread_ts,
                )
            except SlackApiError as e:
                logger.error(
                    f"{log_prefix} Failed to send retrieval error message: {e.response['error']}"
                )
            return

        # Generate summary (using imported function)
        logger.info(
            f"{log_prefix} Generating summary for {len(all_messages)} messages."
        )
        summary = generate_summary(all_messages)

        # Post summary back to the thread
        logger.info(f"{log_prefix} Posting summary to thread.")
        try:
            # Add a header to the summary message
            summary_header = (
                f"Here's a TL;DR summary of this thread requested by <@{user_id}>:\n---"
            )
            full_message = f"{summary_header}\n{summary}"
            say(text=full_message, thread_ts=thread_ts)
            logger.info(f"{log_prefix} Summary posted successfully.")
        except SlackApiError as e:
            logger.error(f"{log_prefix} Failed to post summary: {e.response['error']}")
            # Optionally try sending a DM or logging more details

        # TODO: Add optional flow graph generation here
        # graph_image = generate_flow_graph(all_messages)
        # if graph_image:
        #    try:
        #        client.files_upload_v2(...) # Upload image
        #    except SlackApiError as e: ...

    else:
        # Mention is in the main channel, not a thread
        logger.info(f"{log_prefix} Mention is not in a thread. Instructing user.")
        try:
            say(
                text=f"Hi <@{user_id}>! To summarize a conversation, please mention me *within* the specific thread you want summarized."
            )
        except SlackApiError as e:
            logger.error(
                f"{log_prefix} Failed to send instructions: {e.response['error']}"
            )


@app.event("message")
def handle_message_events(body, logger):
    """Log message events for debugging if needed, but don't process them.
    This helps see if the bot is receiving messages at all.
    """
    # logger.debug(f"Received message event: {body}")
    pass  # Don't do anything with general messages


# --- Start the App ---

if __name__ == "__main__":
    logger.info("Starting Slack Summarizer Agent...")
    try:
        # SocketModeHandler uses SLACK_APP_TOKEN
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        logger.info("Socket Mode handler initialized. Starting listener...")
        handler.start()  # This blocks until interrupted
    except SlackApiError as e:
        logger.critical(
            f"Error starting Socket Mode handler. Check your SLACK_APP_TOKEN and bot permissions/scopes. Error: {e}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error starting Socket Mode handler: {e}")
