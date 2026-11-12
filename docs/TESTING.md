# Testing Guide

## Running Tests

### Run all tests

```bash
uv run pytest
```

### Run specific test file

```bash
uv run pytest tests/unit/test_engine.py
```

### Run with verbose output

```bash
uv run pytest -v
```

### Run with coverage report

```bash
uv run pytest --cov-report=html
open htmlcov/index.html
```

## Test Output Configuration

Tests are configured to suppress **all** application logging and output by default. This keeps test output clean and focused on test results only.

### What's suppressed

- ✅ All `logger.info()`, `logger.debug()`, etc. from application code
- ✅ asyncio debug messages ("Using selector: EpollSelector")
- ✅ Print statements from application code
- ✅ Warnings

### Enabling logs for debugging

If you need to see logs during a specific test for debugging:

```python
def test_with_logging(enable_logging):
    """This test will show all logs."""
    # Test code here
```

Or run pytest with logging enabled:

```bash
uv run pytest -v --log-cli-level=DEBUG
```

## Test Structure

```text
tests/
├── unit/           # Fast, isolated unit tests
│   ├── test_cli.py
│   ├── test_engine.py
│   ├── test_scanner.py
│   └── ...
├── integration/    # Slower tests that test multiple components
└── conftest.py     # Shared fixtures and configuration
```

## Writing Tests

### Basic test template

```python
def test_something():
    """Clear description of what this tests."""
    # Arrange
    input_data = "test"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Using mocks

```python
from unittest.mock import patch, MagicMock

@patch("qemulab.services.engine.NetworkService")
def test_with_mock(mock_network):
    """Test that uses a mock."""
    mock_network.setup_bridge.return_value = True
    
    # Test code
    result = engine.prepare()
    
    # Verify mock was called
    mock_network.setup_bridge.assert_called_once()
```

### Async tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    result = await async_function()
    assert result is not None
```

## Common Issues

### "Logger output appearing in tests"

If you see application logs in test output:

1. Check that `conftest.py` is in the `tests/` directory
2. Ensure `suppress_all_output` fixture is being applied
3. Run: `uv run pytest --fixtures` to verify fixtures are loaded

### "Tests passing but coverage is low"

Add `# pragma: no cover` to code that shouldn't be tested:

- Error handling that's hard to trigger
- CLI entry points
- Defensive code

### "Mocks not working"

Ensure you're patching the right import path:

- ✅ Patch where it's **used**: `@patch("qemulab.ui.app.Scanner")`
- ❌ Not where it's defined: `@patch("qemulab.services.scanner.Scanner")`

## CI/CD Integration

Tests run automatically on:

- Every push to main
- Every pull request
- Scheduled daily builds

See `.github/workflows/test.yml` for CI configuration.
