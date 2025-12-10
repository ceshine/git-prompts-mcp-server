from importlib import metadata

try:
    __version__ = metadata.version("git_prompts_mcp_server")
except metadata.PackageNotFoundError:
    # This handles the case where the package is imported
    # without being installed (e.g., local script execution)
    __version__ = "unknown"
