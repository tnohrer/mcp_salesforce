# MCP Salesforce AKA > GooseForce

A Salesforce OAuth extension for Goose that allows secure authentication with Salesforce orgs.
Author: Tristan Nohrer

## Features
- Secure OAuth 2.0 implementation with enhanced state management
- Support for sandbox and production orgs with improved environment selection
- Secure credential storage using system keychain
- Per-org Connected App support
- Query Best Practice
- Query Warnings and Limits
- DML Restriction
- Improved logging and debugging capabilities

## Setup Instructions

### For Administrators
1. Create a Connected App in your Salesforce org:
   - Go to Setup > App Manager
   - Click "New Connected App"
   - Fill in:
     - Connected App Name: Goose for Salesforce
     - API Name: Goose_for_Salesforce
     - Contact Email: [your admin email]
   - Enable OAuth Settings:
     - Check "Enable OAuth Settings"
     - Callback URL: http://localhost:8787
     - Selected OAuth Scopes:
       - Access and manage your data (api)
       - Perform requests on your behalf at any time (refresh_token)
       - Full access (full)
     - Check "Require Secret for Web Server Flow" only
   - Click Save
2. After saving, wait ~10 minutes for settings to propagate
3. Get the Consumer Key from Manage > View Consumer Details
4. Share the Consumer Key with your team

### For Users

#### Method 1: Manual Installation (Current)
1. Clone the repository:
```bash
git clone https://github.com/tnohrer/mcp_salesforce.git
```

2. Install dependencies:
```bash
cd mcp_salesforce
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
```

3. Configure the extension in Goose:
   - Add the extension path to your Goose configuration
   - First time setup:
     - Enter the Consumer Key provided by your admin
     - Select sandbox or production environment
     - Authorize the application

#### Method 2: Extension Manager Installation (Coming Soon)
1. Install the extension through Goose Desktop's Extension Manager
2. First time setup:
   - Enter the Consumer Key provided by your admin
   - Select sandbox or production environment
   - Authorize the application
3. Subsequent uses will use the stored configuration

## Requirements
- Python 3.8+
- Goose Desktop Application
- Access to a Salesforce org

## Project Structure and File Overview

### Key Files
```
/mcp_salesforce/
├── Info.plist              # macOS configuration file
├── README.md              # Project documentation
├── extension.json         # Extension configuration
├── pyproject.toml        # Project dependencies and metadata
├── requirements.txt      # Python package requirements
├── run.py               # Extension entry point
└── src/
    └── mcp_salesforce/
        ├── __init__.py
        ├── __main__.py
        ├── auth_state.py          # Authentication state management
        ├── config_handler.py      # Configuration management
        ├── environment_selector.py # Environment selection UI
        ├── login_handler.py       # OAuth flow management
        ├── query_validator.py     # Query validation and safety
        ├── salesforce.py          # Core Salesforce interaction
        ├── server.py              # FastMCP integration
        ├── logs/                  # Log directory
        │   └── mcp_salesforce.log # Application logs
        └── templates/             # UI templates
            ├── environment_selector.html
            └── oauth_callback.html
```

### Core Components

1. **Server Components** (`server.py`)
   - Main extension implementation using FastMCP
   - Tool registration and endpoint handling
   - Response formatting and error management
   - Enhanced logging configuration

2. **Salesforce Integration** (`salesforce.py`)
   - Core Salesforce API interaction
   - Query execution and result processing
   - API connection management

3. **Authentication System**
   - `auth_state.py`: Manages authentication state and sessions
   - `login_handler.py`: Implements OAuth flow with improved state management
   - `environment_selector.py`: Provides enhanced environment selection UI
   - Templates for login and callback pages

4. **Query Management** (`query_validator.py`)
   - Query validation and safety checks
   - DML operation prevention
   - Query limitations enforcement
   - Syntax validation

5. **Configuration Management** (`config_handler.py`)
   - Configuration file handling
   - Connected app settings
   - Environment preferences

### Safety Features

1. **Query Protection**
   - Read-only operations enforced
   - Automatic LIMIT 200 for unlimited queries
   - Required WHERE clause for COUNT queries
   - Query syntax validation

2. **Authentication Security**
   - Enhanced OAuth 2.0 implementation with improved state management
   - Secure state token generation and validation
   - Protection against CSRF attacks
   - Session timeout handling
   - Connected app validation
   - Environment selection enforcement

## Available Tools

```python
@tool("mcp_salesforce_login")        # Authentication
@tool("mcp_salesforce_handle_oauth") # OAuth callback processing
@tool("mcp_salesforce_logout")       # Session termination
@tool("mcp_salesforce_query")        # SOQL query execution
@tool("mcp_salesforce_search")       # SOSL search execution
```

## Security Features
- No hardcoded credentials
- Secure storage using system keychain
- Per-org Connected Apps
- Enhanced OAuth 2.0 security practices
- Improved state management with CSRF protection
- Updated query handling and best practices:
  - DML prevention
  - Syntax checks
  - LIMIT enforcements
  - Clause enforcements

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)