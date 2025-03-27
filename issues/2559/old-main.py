import asyncio
import os
import shutil
import sys

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv as envr
from mcp import StdioServerParameters

envr()

CLAUDE_MODEL_ID = os.getenv("CLAUDE_MODEL_ID")
API_KEY = os.getenv("API_KEY")


def get_npx_path():
    """Get the absolute path to npx executable, handling Windows path issues."""
    if sys.platform == "win32":
        # On Windows, try to find npx.cmd or npx.exe in PATH
        for ext in (".cmd", ".exe", ".bat", ""):
            npx_path = shutil.which(f"npx{ext}")
            if npx_path:
                print(f"Using npx at: {npx_path}")
                return npx_path
    else:
        # On Unix systems, 'npx' should work without extension
        npx_path = shutil.which("npx")
        if npx_path:
            print(f"Using npx at: {npx_path}")
            return npx_path

    raise FileNotFoundError("Could not find npx executable. Make sure Node.js is installed correctly.")


async def run_agent(message: str) -> None:
    """Run the Playwright agent with the given message."""
    try:
        # Get npx path, ensuring it's correctly resolved for Windows
        npx_path = get_npx_path()

        # Create environment variables
        env = os.environ.copy()
        env["NODE_OPTIONS"] = "--max-old-space-size=4096"
        env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"  # Skip browser download on startup

        # Create server parameters with the correct executable path
        server_params = StdioServerParameters(
            command=npx_path,
            args=["@playwright/mcp@latest"],
            env=env
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

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(
            run_agent(
                "Go to Wikipedia web page, search for the Incompleteness Theorem, and take a snapshot."
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
