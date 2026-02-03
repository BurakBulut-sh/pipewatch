# Contributing to Pipewatch

Thank you for your interest in contributing to Pipewatch! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork and clone the repository
2. Install in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Code Style

We use:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **pytest** for testing

Run checks before committing:
```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest
```

## Testing

- Write tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage

## Commit Messages

Use conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior

## Code of Conduct

Be respectful and constructive in all interactions.
