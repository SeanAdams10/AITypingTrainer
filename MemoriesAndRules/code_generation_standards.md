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

---

## 1. General Principles
- Write clear, concise, and maintainable code.
- Prioritize readability and simplicity over cleverness.
- Follow the SOLID principles and DRY (Don't Repeat Yourself).
- Refactor code regularly to improve quality.

## 2. Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Use type hints throughout the codebase.
- Use Black for code formatting and Flake8 for linting.
- Use descriptive variable, function, and class names.
- Document complex logic with inline comments.
- Update README files when adding significant features.

## 3. Documentation
- Add module-level docstrings for all modules.
- All public classes and functions must have docstrings describing their purpose, parameters, and return types.
- Maintain up-to-date changelogs for major releases or deployments.

## 4. Error Handling
- Add proper error handling with specific error messages.
- Validate all user inputs.
- Use try-except blocks appropriately.
- Return meaningful error messages.

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