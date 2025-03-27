import sys
import shutil

print(f"Platform: {sys.platform}")
print(f"Testing path resolution for 'npx':")

# Test direct resolution
print(f"Direct 'npx': {shutil.which('npx')}")

# Test with extensions
for ext in [".cmd", ".exe", ".bat"]:
    path = shutil.which(f"npx{ext}")
    print(f"npx{ext}: {path}")

# Print PATH environment variable
import os
print("\nPATH environment variable:")
path_entries = os.environ.get("PATH", "").split(os.pathsep)
for i, path in enumerate(path_entries):
    print(f"{i+1}. {path}")

# Test the actual resolution from the SDK (if installed)
try:
    from mcp.client.stdio.win32 import get_windows_executable_command
    sdk_result = get_windows_executable_command("npx")
    print(f"\nSDK resolution result: {sdk_result}")
except ImportError:
    print("\nSDK not installed, skipping SDK test")

print("\nDone!")
