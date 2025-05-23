# Python Coding Standards & Best Practices

## 1. General Principles
- **Follow PEP8**: All code must comply with PEP8 style guidelines for readability and consistency.
- **Type Annotations**: Use explicit type hints for all variables, function signatures, and class attributes. Prefer type-checked code at all layers.
- **Use Pydantic**: Leverage Pydantic models for type safety, validation, and serialization wherever possible.
- **Defensive Programming**: Always validate inputs, check for errors, and handle edge cases gracefully.
- **Observability**: Include structured logging, telemetry, and error reporting. Make all services and components observable for operational monitoring.
- **Testability**: Design software so that every layer (backend, service, API, desktop, web) can be tested with a stand-in/mock database.
- **Maintainability**: Write clean, minimal, and modular code. Prefer clarity over cleverness.
- **Refactoring**: Refactor code regularly to improve structure, readability, and performance. Apply object-oriented and functional patterns as appropriate.
- **Static Analysis on Every Change**: After altering any file, immediately check it using both `mypy` (in strict/most verbose mode) and `ruff`, and resolve all issues before considering the change complete.

## 2. Development Best Practices
- **Pragmatic Programmer Principles**: Keep code DRY (Don't Repeat Yourself), use meaningful names, and automate repetitive tasks.
- **Clean Code**: Write small, single-purpose functions. Use intention-revealing names. Avoid side effects and global state.
- **TDD**: Practice Test-Driven Development. Write tests before implementing features. Ensure all code is covered by robust, independent tests.
- **Object Patterns**: Use composition over inheritance where possible. Apply design patterns (e.g., Factory, Strategy, Adapter) judiciously.
- **Error Handling**: Use exceptions for error reporting, not control flow. Catch and handle exceptions at appropriate layers.
- **Documentation**: Document all public APIs, classes, and complex logic with docstrings. Keep documentation up to date.

## 3. API & UI Standards
- **APIs**: Prefer GraphQL for new APIs unless not possible. REST is acceptable for legacy or simple endpoints.
- **Backend**: Python is the backend language of choice.
- **Desktop Frontend**: Should be modern, testable, and run on Windows. Prefer PyQt5 or similar for testability.
- **Web Frontend**: Must be modern, clean, minimal, and work across all browsers. Prioritize accessibility and responsiveness.

## 4. Security & Validation
- **SQL Injection**: Always use parameterized queries. Never interpolate user input into SQL directly.
- **Input Validation**: Validate and sanitize all user input at the API boundary and business logic layers.
- **Secrets Management**: Never hardcode secrets or sensitive data. Use environment variables or secure vaults.

## 5. Testing & Quality
- **Layered Testing**: Test at all levels: unit, integration, API, UI (web & desktop). All tests must be robust, isolated, and order-independent.
- **Mocking & Fixtures**: Use pytest, pytest-mock, and fixtures for isolation and repeatability.
- **Parameterization**: Use pytest parameterization for repeated or edge-case tests.
- **Continuous Integration**: Integrate with CI pipelines to run tests, type checks, and linters on every commit.
- **Code Quality Tools**: Use mypy (strict mode) and ruff. Fix all warnings and errors before release.

## 6. Operational Monitoring
- **Logging**: Use structured, leveled logging (DEBUG, INFO, WARNING, ERROR, CRITICAL). Never log sensitive data.
- **Telemetry**: Instrument code for metrics and traces. Monitor key business and technical metrics.
- **Alerting**: Set up alerts for error rates, latency, and critical failures.

## 7. Additional Best Practices
- **YAGNI**: Don't implement features until they are needed.
- **KISS**: Keep it simple and straightforward.
- **SOLID Principles**: Apply SOLID object-oriented design principles.
- **Open/Closed Principle**: Code should be open for extension but closed for modification.
- **Single Responsibility Principle**: Each class/function should have one clear responsibility.
- **Separation of Concerns**: Keep business logic, data access, and presentation layers separate.
- **Immutable Data**: Prefer immutable data structures where possible.
- **Functional Patterns**: Use pure functions and avoid side effects when practical.

---

**These standards are mandatory for all new development and must be reviewed regularly.**
