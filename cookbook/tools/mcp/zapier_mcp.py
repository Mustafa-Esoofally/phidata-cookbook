"""📁 MCP Zapier Agent - Your Personal Automation Assistant!

This example shows how to create a Zapier agent that uses MCP to perform real-world actions through Zapier's integrations.

Environment variables needed:
- ZAPIER_MCP_URL: Your Zapier MCP endpoint URL (get from https://actions.zapier.com/settings/mcp/)

Example prompts to try:
- "Send an email to test@example.com with subject 'Hello' and message 'Testing MCP'"
- "Create a calendar event for tomorrow at 2 PM"
- "Add a new row to my Google Sheet"

"""

import asyncio
import os
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def create_zapier_agent(session):
    """Create and configure an agent capable of using Zapier actions via MCP."""
    mcp_tools = MCPTools(session=session)
    await mcp_tools.initialize()

    return Agent(
        model=OpenAIChat(),
        tools=[mcp_tools],
        instructions=dedent("""\
            You are a Zapier automation assistant that can perform real-world tasks.
            Use the available Zapier actions to help users accomplish their goals.
            Be clear about what actions you're taking and ask for clarification if needed.\
        """),
        markdown=True,
        show_tool_calls=True,
    )


async def run_agent(message: str) -> None:
    """Run the Zapier agent with the given message."""
    zapier_mcp_url = os.getenv("ZAPIER_MCP_URL")
    if not zapier_mcp_url:
        raise ValueError("ZAPIER_MCP_URL environment variable is required")

    # Initialize mcp-remote to connect to Zapier
    server_params = StdioServerParameters(
        command="npx.cmd" if os.name == "nt" else "npx",
        args=["-y", "mcp-remote", zapier_mcp_url],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            agent = await create_zapier_agent(session)
            await agent.aprint_response(message, stream=True)


# Example usage
if __name__ == "__main__":
    # Email example
    asyncio.run(
        run_agent(
            "Send an email to test@example.com with the subject 'MCP Test' and message 'Hello from Agno Zapier MCP!'"
        )
    )


# More example prompts to explore:
"""
1. "Draft an email to the team about the project update"
2. "Create a recurring event for daily standups"
3. "Create a new Google Doc for meeting notes"
4. "Add a row to my expense tracking spreadsheet"
5. "Update the project timeline in Notion"
6. "Save today's meeting summary to Evernote"
7. "Create a new task in my todo list"
"""
