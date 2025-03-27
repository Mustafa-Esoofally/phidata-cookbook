# Issue #2559: FileNotFoundError when running Agent with MCPTools using Playwright

## Problem Description

When attempting to run an Agent with MCPTools using Playwright on Windows systems, users encounter a `FileNotFoundError` indicating that the system cannot find the specified file (`npx`).

## Root Cause

Although the Python MCP SDK has built-in Windows path resolution in its `stdio_client` function, we found it wasn't correctly resolving the `npx` command on all Windows systems. The issue specifically affects Windows environments where command resolution through `shutil.which()` behaves differently than expected.

## Solution

After analyzing the Python MCP SDK code and testing different approaches, we implemented a targeted fix that:

1. Specifically handles the `npx` command on Windows platforms
2. Directly resolves the path using `shutil.which()` with proper extensions (`.cmd`, `.exe`, `.bat`)
3. Applies the fix only when needed, without disrupting other commands or platforms

The solution remains transparent to users - they can continue writing simple code:

```python
# This simple code now works on all platforms
server_params = StdioServerParameters(
    command="npx",
    args=["@playwright/mcp@latest"],
)

async with MCPTools(server_params=server_params) as mcp_tools:
    # Use mcp_tools...
```

## Implementation Details

The fix is minimalist and focused:

1. Added a specific check in the `MCPTools.__init__` method to detect when:
   - We're on Windows (`sys.platform == "win32"`)
   - The command is specifically "npx"
   - A server_params object is provided
2. For this specific case, we manually resolve the path with extensions
3. This is a targeted fix that doesn't affect other commands or platforms

## Usage

To run the example:

1. Ensure you have Node.js installed
2. Set up environment variables in `.env` file:
   ```
   CLAUDE_MODEL_ID=your_model_id
   API_KEY=your_api_key
   ```
3. Run the script:
   ```
   python main.py
   ```

## Additional Notes

- Our fix is intentionally targeted at the specific issue with `npx` on Windows
- We avoided larger changes to the codebase to minimize potential side effects
- The SDK's built-in path resolution still handles most other cases properly

## References

- [Playwright MCP on GitHub](https://github.com/microsoft/playwright-mcp)
- [MCP Python SDK source code](https://github.com/microsoft/mcp/tree/main/python)
