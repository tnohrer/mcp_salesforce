"""MCP Salesforce Extension for Goose."""
import logging
import os
from typing import Dict, Any, Optional
import webbrowser
from mcp.server.fastmcp.server import FastMCP
from simple_salesforce import Salesforce
from .login_handler import LoginHandler
from .query_validator import QueryValidator

logger = logging.getLogger(__name__)

class MCPSalesforceExtension(FastMCP):
    """MCP Salesforce Extension."""

    def __init__(self):
        """Initialize the extension."""
        # Read the hints file
        hints_path = os.path.join(os.path.dirname(__file__), 'goose_hints.md')
        with open(hints_path, 'r') as f:
            hints_content = f.read()
        
        # Create comprehensive system instructions with hints
        system_instructions = f"""MCP Salesforce Extension.

IMPORTANT: Always follow these query patterns and best practices for any SOQL query:

{hints_content}

These patterns must be followed for every query. Validate all queries against these patterns before execution.
"""
        
        super().__init__(
            name="mcp_salesforce",
            display_name="MCP Salesforce",
            description="Salesforce integration for Goose - Read-only operations",
            system_instructions=system_instructions,
        )
        self.login_handler = LoginHandler()
        self._setup_tools()
        
    def _setup_tools(self):
        """Set up the extension's tools."""
        @self.tool("mcp_salesforce_login")
        async def login(
            environment: str = None
        ) -> dict:
            """Login to Salesforce."""
            try:
                # Show environment selector if not provided
                if not environment:
                    from .environment_selector import EnvironmentSelector
                    selector = EnvironmentSelector()
                    result = selector.show()
                    
                    if not result or result.get("environment") == "cancel":
                        return {
                            "success": False,
                            "error": "Login cancelled"
                        }
                    
                    environment = result["environment"]
                
                # Start login flow with selected environment
                return self.login_handler.start_login_flow(environment)
                
            except Exception as e:
                logger.error(f"Login failed: {str(e)}")
                return {"success": False, "error": str(e)}

        @self.tool("mcp_salesforce_handle_oauth")
        async def handle_oauth(
            callback_url: str
        ) -> dict:
            """Handle OAuth callback."""
            try:
                return self.login_handler.handle_oauth_callback(callback_url)
            except Exception as e:
                logger.error(f"OAuth callback failed: {str(e)}")
                return {"success": False, "error": str(e)}

        @self.tool("mcp_salesforce_logout")
        async def logout() -> dict:
            """Logout from Salesforce."""
            try:
                self.login_handler.clear_session()
                return {"success": True, "message": "Successfully logged out"}
            except Exception as e:
                logger.error(f"Logout failed: {str(e)}")
                return {"success": False, "error": str(e)}

        @self.tool("mcp_salesforce_query")
        async def query(soql: str) -> dict:
            """Execute a SOQL query with safety features."""
            try:
                sf = self.login_handler.get_sf()
                if not sf:
                    return {
                        "success": False,
                        "error": "Not authenticated. Please login first using mcp_salesforce_login"
                    }

                # Use QueryValidator for comprehensive validation
                is_valid, error_message = QueryValidator.validate_query(soql)
                if not is_valid:
                    return {
                        "success": False,
                        "error": error_message
                    }
                
                # Add LIMIT if not present and not a COUNT query
                soql_upper = soql.upper().strip()
                if 'LIMIT' not in soql_upper and 'COUNT(' not in soql_upper:
                    soql = f"{soql.rstrip()} LIMIT 200"
                    logger.info(f"Added LIMIT clause. Modified query: {soql}")
                
                # Execute query
                try:
                    logger.info(f"Executing SOQL query: {soql}")
                    results = sf.query_all(soql)
                    return {"success": True, "results": results}
                except Exception as e:
                    # Session management - handle expired sessions
                    if "INVALID_SESSION_ID" in str(e):
                        logger.warning("Session expired, clearing session")
                        self.login_handler.clear_session()
                        return {
                            "success": False,
                            "error": "Session expired. Please login again."
                        }
                    return {
                        "success": False,
                        "error": str(e)
                    }
                    
            except Exception as e:
                logger.error(f"Query failed: {str(e)}")
                return {"success": False, "error": str(e)}

        @self.tool("mcp_salesforce_search")
        async def search(search_term: str) -> dict:
            """Execute a SOSL search."""
            try:
                sf = self.login_handler.get_sf()
                if not sf:
                    return {
                        "success": False,
                        "error": "Not authenticated. Please login first using mcp_salesforce_login"
                    }
                
                try:
                    logger.info(f"Executing SOSL search: {search_term}")
                    results = sf.search(search_term)
                    return {"success": True, "results": results}
                except Exception as e:
                    # Session management - handle expired sessions
                    if "INVALID_SESSION_ID" in str(e):
                        logger.warning("Session expired, clearing session")
                        self.login_handler.clear_session()
                        return {
                            "success": False,
                            "error": "Session expired. Please login again."
                        }
                    return {
                        "success": False,
                        "error": str(e)
                    }
                    
            except Exception as e:
                logger.error(f"Search failed: {str(e)}")
                return {"success": False, "error": str(e)}

def run_mcp_server():
    """Run the extension server."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up logging to both file and console
    log_file = os.path.join(log_dir, 'mcp_salesforce.log')
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG to capture all levels of logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # File handler - logs everything to a file
            logging.FileHandler(log_file),
            # Console handler - also show in terminal
            logging.StreamHandler()
        ]
    )
    logger.info(f"Starting MCP Salesforce Extension - Logging to {log_file}")
    extension = MCPSalesforceExtension()
    extension.run()

if __name__ == "__main__":
    run_mcp_server()