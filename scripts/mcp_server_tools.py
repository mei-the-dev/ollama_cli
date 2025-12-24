"""
MCP-server Tooling Resource Module (v2025-12-23)

This module provides:
- Utility functions for code validation (PEP8, type hints, imports)
- File extraction and sandboxing helpers
- Error taxonomy definitions
- CLI runner for prompt testing
- Post-processing pipeline (black, isort, autoflake, flake8, mypy)
- Duplicate filename detection and resolution
- Structured event logging utilities
- Usage example for each tool

All functions must:
- Be type-annotated
- Handle errors gracefully
- Log events using the logging module
- Include usage examples in docstrings
- Never use absolute paths
- Prefer pathlib and standard library
"""
