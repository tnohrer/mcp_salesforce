"""Login handler for MCP Salesforce."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import secrets
import webbrowser
import threading
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse, unquote
import keyring
from simple_salesforce import Salesforce
from .config_handler import ConfigurationHandler
from .auth_state import AuthState, AuthContext

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add console handler if it doesn't exist
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

CONFIG_SERVICE_NAME = "goose_salesforce"
CONFIG_KEY_NAME = "consumer_key"

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler for OAuth callback."""
    def do_GET(self):
        try:
            logger.debug(f"OAuth callback received: {self.path}")
            if '#' in self.path:
                # If we somehow get the fragment directly, use it
                full_url = f"http://localhost:{self.server.server_port}{self.path}"
                self.server.callback_url = full_url
                self.server.callback_received.set()
                logger.debug("Received direct fragment")
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Authentication successful! You can close this window.")
            else:
                # Check if this is a callback with the hash parameter
                query = parse_qs(urlparse(self.path).query)
                if 'hash' in query:
                    # We got the fragment data back from the JavaScript
                    fragment = query['hash'][0]
                    full_url = f"http://localhost:{self.server.server_port}/#{fragment}"
                    self.server.callback_url = full_url
                    self.server.callback_received.set()
                    logger.debug("Received hash fragment via query parameter")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"Authentication successful! You can close this window.")
                else:
                    # First request - serve the HTML that will capture and send back the fragment
                    logger.debug("Serving OAuth callback HTML")
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    html = """
                    <html><body>
                    <script>
                        // Get the hash fragment and send it back
                        var hash = window.location.hash;
                        if (hash) {
                            // Remove the leading # before sending
                            var fragment = hash.substring(1);
                            // Send the hash fragment back to the server
                            fetch('/?hash=' + encodeURIComponent(fragment))
                                .then(() => {
                                    document.write("Authentication successful! You can close this window.");
                                });
                        }
                    </script>
                    <p>Processing authentication response...</p>
                    </body></html>
                    """
                    self.wfile.write(html.encode())
                    
        except Exception as e:
            logger.error(f"Error in OAuth callback: {str(e)}", exc_info=True)
            self.send_response(500)
            self.end_headers()

class LoginHandler:
    def __init__(self):
        logger.debug("Initializing LoginHandler")
        self.sf = None
        self._states = {}  # Dictionary to store multiple states with timestamps
        self._server = None
        self._server_thread = None
        self.client_id = None
        self.callback_url = "http://localhost:8787"
        self.auth_context = AuthContext()
        self._cleanup_interval = 300  # 5 minutes in seconds

    def start_login_flow(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """Start the sequential login flow."""
        try:
            logger.debug("Starting login flow")
            # Initialize state
            self.auth_context = AuthContext(state=AuthState.INITIAL)
            
            # Step 1: Check configuration
            self.client_id = self._load_configuration()
            if not self.client_id:
                logger.debug("No client ID found, showing configuration screen")
                self.auth_context.update_state(AuthState.WAITING_FOR_CONFIG)
                self.client_id = self._show_configuration_screen()
                
                if not self.client_id:
                    logger.error("Configuration required - no client ID provided")
                    self.auth_context.update_state(AuthState.ERROR, "Configuration required")
                    return {
                        "success": False,
                        "error": "Configuration required. Please configure the Consumer Key."
                    }
            
            # Step 2: Show environment selector if no environment provided
            if not environment:
                logger.debug("No environment specified, showing selector")
                from .environment_selector import EnvironmentSelector
                selector = EnvironmentSelector()
                selection = selector.show()
                
                if not selection:
                    logger.error("No environment selected")
                    self.auth_context.update_state(AuthState.ERROR, "No environment selected")
                    return {
                        "success": False,
                        "error": "Environment selection required"
                    }
                
                environment = selection["environment"]
                logger.debug(f"Environment selected: {environment}")
            
            self.auth_context.environment = environment
            
            # Step 3: Start OAuth flow
            logger.debug("Starting OAuth flow")
            self.auth_context.update_state(AuthState.OAUTH_FLOW)
            result = self._start_oauth_flow()
            
            if result["success"]:
                logger.info("Login flow completed successfully")
                self.auth_context.update_state(AuthState.COMPLETED)
            else:
                logger.error(f"Login flow failed: {result['error']}")
                self.auth_context.update_state(AuthState.ERROR, result["error"])
            
            return result
            
        except Exception as e:
            logger.error(f"Error in login flow: {str(e)}", exc_info=True)
            self.auth_context.update_state(AuthState.ERROR, str(e))
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_state(self) -> str:
        """Generate and store a new state token with timestamp."""
        state = secrets.token_urlsafe(16)
        self._states[state] = {
            'timestamp': time.time(),
            'used': False
        }
        self._cleanup_expired_states()
        return state

    def _validate_state(self, received_state: str) -> bool:
        """Validate a received state token."""
        if received_state not in self._states:
            return False
        
        state_data = self._states[received_state]
        if state_data['used']:
            return False
            
        # Check if state has expired (5 minute timeout)
        if time.time() - state_data['timestamp'] > self._cleanup_interval:
            del self._states[received_state]
            return False
            
        # Mark state as used
        state_data['used'] = True
        return True

    def _cleanup_expired_states(self):
        """Remove expired states."""
        current_time = time.time()
        expired_states = [
            state for state, data in self._states.items()
            if current_time - data['timestamp'] > self._cleanup_interval or data['used']
        ]
        for state in expired_states:
            del self._states[state]

    def _start_oauth_flow(self) -> Dict[str, Any]:
        """Start the OAuth flow."""
        try:
            state = self._generate_state()
            logger.debug(f"Generated OAuth state: {state}")
            
            # Start callback server first
            self._start_callback_server()
            logger.info("Started OAuth callback server")
            
            # Build OAuth URL based on selected environment
            base_url = "https://test.salesforce.com" if self.auth_context.environment == "sandbox" else "https://login.salesforce.com"
            auth_url = f"{base_url}/services/oauth2/authorize"
            logger.info(f"Using auth URL for {self.auth_context.environment}: {auth_url}")
            
            params = {
                'response_type': 'token',
                'client_id': self.client_id,
                'redirect_uri': self.callback_url,
                'state': state,  # Use new state
                'scope': 'api full refresh_token',
                'prompt': 'login consent select_account',
                'display': 'page'
            }
            
            full_url = f"{auth_url}?{urlencode(params)}"
            logger.info(f"Generated OAuth URL: {full_url}")
            
            # Open browser with OAuth URL
            webbrowser.open(full_url)
            
            # Wait for callback
            if self._server.callback_received.wait(timeout=300):
                callback_url = self._server.callback_url
                logger.info(f"Received callback URL: {callback_url}")
                self._server.shutdown()
                self._server.server_close()
                return self.handle_oauth_callback(callback_url)
            else:
                logger.error("Timeout waiting for OAuth callback")
                return {
                    "success": False,
                    "error": "Timeout waiting for authentication"
                }
                
        except Exception as e:
            logger.error(f"Error in OAuth flow: {str(e)}", exc_info=True)
            if self._server:
                self._server.shutdown()
                self._server.server_close()
            return {
                "success": False,
                "error": str(e)
            }

    def handle_oauth_callback(self, callback_url: str) -> Dict[str, Any]:
        """Handle the OAuth callback."""
        try:
            logger.info(f"Processing callback URL: {callback_url}")
            
            # Get the fragment from the URL
            fragment = callback_url.split('#', 1)[1] if '#' in callback_url else ''
            logger.info(f"Fragment: {fragment}")
            
            if not fragment:
                logger.error("No fragment in callback URL")
                return {
                    "success": False,
                    "error": "Invalid callback URL format"
                }
            
            # Parse the fragment parameters
            params = {}
            for param in fragment.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = unquote(value)
            
            logger.info(f"Parsed parameters: {params}")
            
            # Get tokens from fragment
            access_token = params.get('access_token')
            instance_url = params.get('instance_url')
            received_state = params.get('state')
            
            logger.info(f"Access Token: {access_token[:10]}... (truncated)")
            logger.info(f"Instance URL: {instance_url}")
            logger.info(f"Received State: {received_state}")
            
            if not access_token or not instance_url:
                logger.error("No access token or instance URL received")
                return {
                    "success": False,
                    "error": "Authentication failed - no access token received"
                }
                
            if not received_state or not self._validate_state(received_state):
                logger.error(f"Invalid state received: {received_state}")
                return {
                    "success": False,
                    "error": "Invalid state parameter - possible CSRF attempt"
                }
            
            # Initialize Salesforce client with tokens
            self.sf = Salesforce(
                instance_url=instance_url,
                session_id=access_token
            )
            
            logger.info("Successfully authenticated with Salesforce")
            return {
                "success": True,
                "message": "Successfully authenticated with Salesforce"
            }
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _load_configuration(self) -> Optional[str]:
        """Load the Consumer Key from secure storage."""
        try:
            logger.debug("Loading configuration from keyring")
            return keyring.get_password(CONFIG_SERVICE_NAME, CONFIG_KEY_NAME)
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            return None

    def _save_configuration(self, consumer_key: str) -> bool:
        """Save the Consumer Key to secure storage."""
        try:
            logger.debug("Saving configuration to keyring")
            keyring.set_password(CONFIG_SERVICE_NAME, CONFIG_KEY_NAME, consumer_key)
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False

    def _show_configuration_screen(self) -> Optional[str]:
        """Show configuration screen to get Consumer Key from user."""
        try:
            logger.debug("Showing configuration screen")
            # Create configuration server
            server = HTTPServer(('localhost', 8788), ConfigurationHandler)
            server.config_received = threading.Event()
            server.consumer_key = None
            
            # Start server thread
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

            # Open browser to configuration page
            webbrowser.open('http://localhost:8788')

            # Wait for configuration
            if server.config_received.wait(timeout=300):  # 5 minute timeout
                consumer_key = server.consumer_key
                server.shutdown()
                server.server_close()

                if consumer_key:
                    # Save the configuration
                    if self._save_configuration(consumer_key):
                        logger.info("Successfully saved consumer key")
                        return consumer_key
            return None
        except Exception as e:
            logger.error(f"Error in configuration screen: {str(e)}", exc_info=True)
            return None
        finally:
            try:
                server.shutdown()
                server.server_close()
            except:
                pass

    def _start_callback_server(self) -> None:
        """Start local server to handle OAuth callback."""
        try:
            logger.debug("Starting OAuth callback server")
            server = HTTPServer(('localhost', 8787), OAuthCallbackHandler)
            server.callback_received = threading.Event()
            server.callback_url = None
            
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            
            self._server = server
            self._server_thread = thread
            logger.debug("OAuth callback server started successfully")
            
        except Exception as e:
            logger.error(f"Error starting callback server: {str(e)}", exc_info=True)
            raise

    def clear_session(self):
        """Clear the current session."""
        logger.debug("Clearing session")
        self.sf = None
        self._state = None
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        
    def get_sf(self) -> Optional[Salesforce]:
        """Get the Salesforce client instance."""
        return self.sf