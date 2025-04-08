# Slack Thread Summarizer Agent

This agent listens for mentions in Slack threads and provides a TL;DR summary.

## Setup

1.  **Create a Slack App:**

    - Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app.
    - Enable **Socket Mode** under "Settings".
    - Navigate to "OAuth & Permissions" and add the following Bot Token Scopes:
      - `app_mentions:read` (To receive mention events)
      - `channels:history` (To read messages in public channels the bot is added to)
      - `groups:history` (To read messages in private channels the bot is added to)
      - `chat:write` (To post messages)
      - `users:read` (Optional, but helpful for mapping user IDs to names if needed later)
    - Install the app to your workspace.
    - Copy the **Bot User OAuth Token** (starts with `xoxb-`). This will be your `SLACK_BOT_TOKEN`.
    - Go back to "Basic Information", scroll down to "App-Level Tokens", generate a token with the `connections:write` scope, and copy it (starts with `xapp-`). This will be your `SLACK_APP_TOKEN`.

2.  **Environment Variables:**

    - Create a file named `.env` in the `cookbook/examples/apps/slack_summarizer/` directory.
    - Add the following lines, replacing the placeholders with your actual tokens:
      ```dotenv
      SLACK_BOT_TOKEN=xoxb-YOUR_BOT_TOKEN_HERE
      SLACK_APP_TOKEN=xapp-YOUR_APP_LEVEL_TOKEN_HERE
      # Add any API keys needed for the summarization LLM later
      # OPENAI_API_KEY=sk-...
      ```

3.  **Install Dependencies:**
    - Activate your virtual environment (e.g., `source .venv/bin/activate`). Make sure the `agno` library is also installed/available in this environment.
    - Install requirements: `pip install -r cookbook/examples/apps/slack_summarizer/requirements.txt`

## Running the Agent

1.  Ensure your virtual environment is active.
2.  Navigate to the agent directory: `cd cookbook/examples/apps/slack_summarizer`
3.  Run the app: `python agent.py`

## Usage

1.  Invite the bot to a channel.
2.  Mention the bot (`@YourBotName`) within a specific thread you want to summarize.
3.  The bot will reply in the thread with the summary (feature under development).
