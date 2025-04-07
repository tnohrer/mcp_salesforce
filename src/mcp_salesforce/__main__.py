"""Main entry point for mcp_salesforce"""
import asyncio
from mcp_salesforce.server import run_mcp_server

def main():
    """MCP Salesforce: Salesforce integration for Goose."""
    asyncio.run(run_mcp_server())

if __name__ == "__main__":
    main()