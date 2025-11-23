# Symbol Tests - Isolated Test Setup

## Overview

The symbol tests have been moved to a completely isolated test environment to prevent test pollution from other test files that modify the shared database state.

## Structure

```
tests/
├── test_symbols_isolated/
│   ├── __init__.py
│   ├── conftest.py           # Isolated database setup
│   └── test_symbols.py        # Symbol API endpoint tests
└── conftest.py                # Global test fixtures (unchanged)
```

## Why Isolation?

The symbol tests were failing when run as part of the full test suite due to:

1. **Shared in-memory SQLite database** - All tests shared the same session-scoped database
2. **SQLAlchemy identity map pollution** - Previous tests modified `AutotradeTable.exchange_id`
3. **SymbolsCrud dependency** - The CRUD class reads `exchange_id` from AutotradeTable in `__init__`
4. **Cross-test contamination** - When `test_bots.py` or `test_autotrade_settings.py` ran before symbol tests, they modified the database in ways that broke symbol filtering

## Solution

Created a separate test directory with its own `conftest.py` that:

- **Separate in-memory database** - Symbol tests get their own isolated SQLite instance
- **Module-scoped setup** - Database is created fresh for the test_symbols_isolated module
- **Fixed autotrade settings** - `AutotradeTable.exchange_id` is always "binance" in this isolated environment
- **Independent session mocking** - Patches `independent_session()` at all import locations to use the isolated database

## Test Results

- **Isolated run**: `pytest tests/test_symbols_isolated/test_symbols.py -v` → ✅ 7/7 PASSED
- **Full suite**: `pytest tests/ -v` → ✅ 53/53 PASSED (including 7 symbol tests)
- **No interference**: Other tests remain completely unchanged and unaffected

## Maintenance

To add new symbol tests:
1. Add them to `tests/test_symbols_isolated/test_symbols.py`
2. Tests will automatically use the isolated database via the module's `conftest.py`
3. No need to worry about test pollution or database state from other tests

## Original Global Tests

The original `tests/test_symbols.py` has been removed since the isolated version works reliably in both isolated and full suite contexts.
