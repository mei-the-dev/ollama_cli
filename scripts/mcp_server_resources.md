# MCP-server Resources (v2025-12-23)

## Prompt Engineering
- Use the template in mcp_prompt_template.py for all code generation tasks
- Enforce PEP8, type hints, argument validation, usage examples
- Prefer standard library and safe patterns

## Tooling
- Use mcp_server_tools.py for validation, extraction, error taxonomy, event logging
- Post-process all generated code with black, isort, autoflake, flake8, mypy
- Detect and resolve duplicate filenames before saving

## Workflow
1. Generate code using the prompt template
2. Save output to sandboxed directory
3. Run post-processing pipeline
4. Log all events and errors
5. Review and resolve duplicates
6. Validate with tests and type checks

## Error Handling
- All errors must be structured and logged
- Never expose raw exceptions to users
- Use custom error classes for validation, IO, network, and business logic errors

## Example Usage
See mcp_server_tools.py for usage examples and integration patterns.
