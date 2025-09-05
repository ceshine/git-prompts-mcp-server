# Development Guidelines

## Philosophy

### Core Beliefs

- **Incremental progress over big bangs** - Small changes that compile and pass tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Be boring and obvious

### Simplicity Means

- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks - choose the boring solution
- If you need to explain it, it's too complex

## Technical Standards

### Architecture Principles

- **Composition over inheritance** - Use dependency injection
- **Interfaces over singletons** - Enable testing and flexibility
- **Explicit over implicit** - Clear data flow and dependencies
- **Test-driven when possible** - Never disable tests, fix them

### Error Handling

- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions

### Code Style Guidelines

When writing or modifying Python code, you **MUST** adhere to the PEP-8 style guide. Pay particular attention to:

- **Import Grouping:** Imports should be grouped in the following order, with a blank line separating each group:
    1.  Standard library imports (e.g., `os`, `sys`, `json`)
    2.  Third-party imports (e.g., `fastapi`, `pydantic`, `uvicorn`)
    3.  Local application/monorepo-specific imports
- Naming conventions, and whitespace.

## Decision Framework

When multiple valid approaches exist, choose based on:

1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?

## Python Environment (UV)

This project uses uv for Python setup and dependency management.

- Prepare the environment (creates/updates the virtualenv from the lockfile):
  - uv sync --frozen

- Run all tools and scripts via uv:
  - uv run pytest
  - uv run python path/to/script.py
  - uvx ruff check .

Pre-Submission Check:

- After committing your work and before submitting it for review, always run a final lint check (i.e., `uvx ruff check .`) within the working subproject folder to catch any remaining issues.
- Additionally, format the code using `uvx ruff format --line-length 120`.

Guidelines for commands and CI:

- Always prefix runtime commands with uv run.
- Do not use pip/poetry/venv directly in instructions.
