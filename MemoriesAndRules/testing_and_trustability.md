# Testing and Trustability Rules

## General Principles
- All functionality in `.md` spec files under `prompts` and `@MemoriesAndRules` must be implemented and robustly tested.
- Robust tests must exist for all happy paths, edge cases, and destructive scenarios (e.g., injection, boundary, non-ASCII, blank, volume, timeout).
- Testing must proceed layer by layer; do not move on until all tests in the current layer pass with no failures or warnings.

## Test Design & Execution
- All tests must run independently and in any order.
- Use `pytest`/`pytest-mock` for all Python tests (strong preference over `unittest`).
- For UI, use the most controllable test framework (e.g., Selenium, Playwright, PyQt test utilities).
- Never use or alter the production DB (`project_root/typing_trainer.db`).
- All tests must use a temporary, isolated DB via pytest fixtures, cleaned up after each test.
- Core tables (e.g., `text_category`) must be created via app initialization, not manual SQL.
- Use pytest parameterization for repeated tests.
- All tests must leave the environment unchanged.

## Test Execution Order
1. Class/Core level: `tests/core`
2. API level: `tests/api`
3. Web UI: `tests/web` (if exists)
4. Desktop UI: `tests/desktop` (if exists)
- Do not skip or ignore any tests or warnings.

## After All Tests Pass
- Only then address all currently known problems (`@current_problems`).
- Then run `mypy` (most verbose mode) on all `.py` files (excluding `.venv`) and fix all issues.
- Then run `pylint` and `flake8` on all `.py` files under `services`, `web_ui`, `tests`, `core`, and `api` (never `.venv`).
- After all tests, type checks, and lints are clean, update `.md` spec files to reflect the latest functionality. **Signal all changes to `.md` files loudly and visibly—these require explicit user acceptance.**

## Persistent Context
- Always bring rules or memories in `.md` files under `@MemoriesAndRules` into context for every run.
- Review and apply all relevant project memories and user rules before executing any testing or trustability actions.


please will you add the following at the very bottom of all pytest tests, so that they can be run in standalone mode:

if __name__ == "__main__":
    pytest.main([__file__])