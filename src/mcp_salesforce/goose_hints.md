# MCP Salesforce Extension Hints

## SOQL Query Patterns

### Counting Records
When counting records in SOQL queries:
- Always use `COUNT(Id)` instead of `COUNT()`
- Example: `SELECT COUNT(Id) total FROM Case`
- Incorrect: `SELECT COUNT() FROM Case`

### Aggregate Queries
For aggregate queries:
- Always include a WHERE clause for performance
- Group by queries should use COUNT(Id)
- Example: `SELECT Status, COUNT(Id) total FROM Case WHERE Id != null GROUP BY Status`

### Best Practices
- Include WHERE clauses for large queries
- Use specific field selections instead of SELECT *
- Add appropriate filters for large objects
- Always alias count fields (e.g., `COUNT(Id) total`)

### Common Query Patterns
```sql
# Basic count
SELECT COUNT(Id) total FROM Object WHERE Id != null

# Count with grouping
SELECT Field, COUNT(Id) total FROM Object WHERE Id != null GROUP BY Field

# Count with time filter
SELECT COUNT(Id) total FROM Object WHERE CreatedDate = LAST_N_DAYS:30

# Count with multiple groups
SELECT Field1, Field2, COUNT(Id) total FROM Object WHERE Id != null GROUP BY Field1, Field2
```
