"""SOQL query validator."""
import re
from typing import Tuple, Optional

class QueryValidator:
    # List of forbidden operations
    FORBIDDEN_OPERATIONS = [
        'INSERT', 'UPDATE', 'DELETE', 'UPSERT', 'MERGE', 'UNDELETE',
        'CREATE', 'MODIFY', 'TRUNCATE'
    ]

    @staticmethod
    def validate_query(soql: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a SOQL query against security and performance rules.
        Returns (is_valid, error_message)
        """
        # Convert to uppercase for easier pattern matching
        soql_upper = soql.upper().strip()
        
        # Check if this is a SELECT query
        if not soql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed. DML operations are not permitted."
            
        # Check for any forbidden operations using word boundaries
        for operation in QueryValidator.FORBIDDEN_OPERATIONS:
            # Use word boundaries \b to match whole words only
            if re.search(rf'\b{operation}\b', soql_upper):
                return False, f"{operation} operations are not permitted. Only SELECT queries are allowed."
            
        # Check for COUNT queries
        count_match = re.search(r'COUNT\s*\(([^)]*)\)', soql_upper)
        if count_match:
            # Verify COUNT has a field specified
            count_field = count_match.group(1).strip()
            if not count_field:
                return False, "COUNT queries must specify a field to count (e.g., COUNT(Id))"
                
            # Verify COUNT has WHERE clause
            if 'WHERE' not in soql_upper:
                return False, "COUNT queries must include a WHERE clause for performance reasons"

        # Additional security checks
        # Block potential SQL injection attempts
        if re.search(r';\s*\w+', soql):  # Check for multiple statements
            return False, "Multiple SQL statements are not allowed"
                
        return True, None