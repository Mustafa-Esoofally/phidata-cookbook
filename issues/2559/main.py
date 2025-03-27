import asyncio
import os
import sys

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv as envr
from mcp import StdioServerParameters

envr()

CLAUDE_MODEL_ID = os.getenv("CLAUDE_MODEL_ID")
API_KEY = os.getenv("API_KEY")


async def run_agent(message: str) -> None:
    """Run the Playwright agent with the given message."""

    # Create server parameters with default npx command
    # Our MCPTools class now handles Windows-specific path resolution for npx
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "@playwright/mcp@latest",
        ],
    )

    # Use the MCP tools with proper async context management
    async with MCPTools(server_params=server_params) as mcp_tools:
        print("MCP Tools initialized successfully")

        agent = Agent(
            model=Claude(id=CLAUDE_MODEL_ID, api_key=API_KEY),
            tools=[mcp_tools],
            role="Your task is to use your web browsing capabilities to find information and take actions on the web.",
            markdown=True,
            show_tool_calls=True,
        )

        await agent.aprint_response(message=message, stream=True)


if __name__ == "__main__":
    try:
        # Print diagnostic info
        print(f"Python version: {sys.version}")
        print(f"Platform: {sys.platform}")

        # Run the agent
        asyncio.run(
            run_agent(
                "Go to Wikipedia web page, search for the Incompleteness Theorem, and take a snapshot."
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
