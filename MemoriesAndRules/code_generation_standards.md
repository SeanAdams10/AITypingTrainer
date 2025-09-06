Back to Cascade

Back
# Code Generation Standards

These standards define the required practices for all code generated or modified in this project. They are designed to ensure code quality, maintainability, security, and ease of collaboration. Every contributor must follow these standards without exception.

## Table of Contents
1. [General Principles](#general-principles)
2. [Code Style](#code-style)
3. [Documentation](#documentation)
4. [Error Handling](#error-handling)
5. [Security Practices](#security-practices)
6. [File Locations & Imports](#file-locations--imports)
7. [Testing](#testing)
8. [Version Control](#version-control)
9. [Dependency Management](#dependency-management)
10. [Code Review](#code-review)
11. [Continuous Integration](#continuous-integration)
12. [Performance](#performance)
13. [Accessibility & Internationalization](#accessibility--internationalization)
14. [Architectural & Framework Preferences](#architectural--framework-preferences)
15. [Typing & Type Checking](#typing--type-checking)

---

## 1. General Principles
- Write clear, concise, and maintainable code.
- Prioritize readability and simplicity over cleverness.
- Follow the SOLID principles and DRY (Don't Repeat Yourself).
- Refactor code regularly to improve quality.

## 2. Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code, including coding and naming standards.
- Use type hints throughout the codebase (see [Typing & Type Checking](#typing--type-checking)).
- Use Black for code formatting and Ruff for linting. Code must pass Ruff with zero errors. If Flake8 is present, Ruff remains the gate for lint compliance.
- Code must pass `mypy` static type checks with zero errors.
- Use descriptive variable, function, and class names.
- Document complex logic with inline comments.
- Update README files when adding significant features.

## 3. Documentation
- Add module-level docstrings for all modules using Google-style docstrings.    
- All public classes and functions must have docstrings describing their purpose, parameters, and return types.
- Maintain up-to-date changelogs for major releases or deployments.

## 4. Error Handling
- Add proper error handling with specific error messages.
- Validate all user inputs.
- Use try-except blocks appropriately.
- Return meaningful error messages.
- **CRITICAL**: All exception handlers must include `traceback.print_exc()` for full stack trace printing.
- **CRITICAL**: All exception handlers must use `DebugUtil.debugMessage()` for consistent debug output.
- Each class should instantiate its own `DebugUtil` instance in `__init__` method.
- Use `raise ... from err` or `raise ... from None` in exception handlers to maintain exception chaining.
- Example exception handler pattern:
  ```python
  try:
      # risky operation
  except SpecificException as e:
      traceback.print_exc()
      self.debug_util.debugMessage(f"Specific error occurred: {e}")
      logger.error(f"Specific error: {e}")
      # handle or re-raise as appropriate
  except Exception as e:
      traceback.print_exc()
      self.debug_util.debugMessage(f"Unexpected error: {e}")
      logger.error(f"Unexpected error: {e}")
      raise DatabaseError("Operation failed") from e
  ```

## 4.1. Debug Messaging Standards
- **CRITICAL**: Use centralized `DebugUtil` class for all debug output across the application.
- Each class must instantiate its own `DebugUtil` instance: `self.debug_util = DebugUtil()`
- Import required: `from helpers.debug_util import DebugUtil`
- Replace all `print()` statements for debugging with `self.debug_util.debugMessage()`
- Debug mode controlled globally via `AI_TYPING_TRAINER_DEBUG_MODE` environment variable:
  - `"quiet"`: Debug messages logged only (production-friendly)
  - `"loud"`: Debug messages printed to stdout (development-friendly)
- Example debug messaging pattern:
  ```python
  from helpers.debug_util import DebugUtil
  
  class MyClass:
      def __init__(self):
          self.debug_util = DebugUtil()
      
      def my_method(self):
          self.debug_util.debugMessage("Processing started")
          try:
              # operation
              self.debug_util.debugMessage(f"Operation completed: {result}")
          except Exception as e:
              traceback.print_exc()
              self.debug_util.debugMessage(f"Operation failed: {e}")
  ```

## 5. Security Practices
- Avoid hardcoding sensitive information.
- Validate and sanitize all user inputs.
- Use parameterized queries for database operations.
- Follow secure coding practices.

## 6. File Locations & Imports
- Use relative imports for internal modules; absolute imports for external packages.
- **Folder Structure:**
    - All API code: `root/api`
    - All desktop UI code: `root/desktop_ui`
    - All web UI code: `root/web_ui`
    - All core object code: `root/models`
    - All service object code: `root/services`
    - All tests: `root/tests`
        - Core tests: `root/tests/core`
        - API tests: `root/tests/api`
        - Desktop UI tests: `root/tests/desktop_ui`
        - Web UI tests: `root/tests/web_ui`
        - Services tests: `root/tests/services`

## 7. Testing
- Run all existing tests after code changes.
- Create new tests for any new functionality.
- Ensure all tests pass before submitting code changes.
- Use `pytest` exclusively for testing (do not use `pyunit` or `unittest`).
- Use `pytest` fixtures for setup and teardown, including temp DB/file/folder creation.
- All code changes must pass `ruff` and `mypy` locally and in CI.

## 8. Version Control
- Use descriptive commit messages summarizing the intent of changes.
- Group related changes into single commits; avoid large, unrelated changes in one commit.
- Follow branch naming conventions (e.g., `feature/`, `bugfix/`, `hotfix/`).

## 9. Dependency Management
- Pin dependencies in `requirements.txt` or `pyproject.toml`.
- Regularly update dependencies and check for security vulnerabilities.
- Remove unused dependencies promptly.

## 10. Code Review
- All code must be peer-reviewed before merging to main branches.
- Address all reviewer comments before merging.
- Use automated tools for code formatting and linting as part of review.

## 11. Continuous Integration
- All tests and lint checks must pass in CI before merging.
- Use automated CI tools to enforce standards and run tests on every PR.
- CI must run `ruff` and `mypy` gates in addition to unit/integration tests.

## 12. Performance
- Avoid premature optimization; focus on clarity first.
- Profile and refactor performance bottlenecks as needed.
- Write tests for performance-critical paths if relevant.

## 13. Accessibility & Internationalization
- For UI, follow accessibility (a11y) best practices (e.g., ARIA roles, keyboard navigation).
- Use internationalization (i18n) for user-facing text where appropriate.

## 14. Architectural & Framework Preferences
- **Windows Desktop UI:** Strong preference for frameworks that allow maximum testability (e.g., PySide6).
- **Web UI:** Strong preference for web UI frameworks that are flexible, modern-looking, and highly reactive to user input.
- **API Layer:** Strong preference for GraphQL APIs over REST APIs.
- **Database Layer:**
    - All database interactions must be abstracted away from business objects to enable future database layer changes.
    - Use dependency injection so tests can provide a test database layer.
    - All table initialization should be handled by a central database management class, not by individual business objects.

---

**These standards must be applied to all code generated or modified, without exception.**

---

## 15. Typing & Type Checking

- All function/method parameters must have explicit type hints.
- All functions/methods must declare explicit return types (including `-> None` when nothing is returned).
- All newly declared variables must include type annotations. Prefer explicit variable annotations over implicit inference.
- Use standard typing constructs (e.g., `Optional[T]`, `Union`, `Mapping`, `Sequence`, `TypedDict`, `Protocol`) where appropriate.
- Favor `typing` and `collections.abc` types for annotations over concrete container types when expressing interfaces.
- Prefer keyword arguments at call sites for functions/methods, especially when there are multiple parameters or parameters of the same type, to improve safety and readability.
- Ensure `mypy` passes with zero errors for all modified or newly created files. Configure `mypy` to run in CI.
- Where runtime validation is required, use Pydantic models or validators; keep annotations consistent with runtime validation rules.
