"""Salesforce API client."""
import logging
import requests
from typing import Dict, Any, Optional
from .query_validator import QueryValidator

logger = logging.getLogger(__name__)

class SalesforceClient:
    def __init__(self, instance_url: str, access_token: str):
        self.instance_url = instance_url
        self.access_token = access_token
        self.api_version = "v58.0"
        self.validator = QueryValidator()
        
    def query(self, soql: str) -> Dict[str, Any]:
        """Execute a SOQL query."""
        # Validate query first
        is_valid, error_message = self.validator.validate_query(soql)
        if not is_valid:
            raise ValueError(error_message)
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.instance_url}/services/data/{self.api_version}/query"
        response = requests.get(url, headers=headers, params={"q": soql})
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Query failed: {response.text}")
            raise Exception(f"Query failed: {response.status_code}")