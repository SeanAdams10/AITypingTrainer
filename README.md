# Snippets Library

A comprehensive code snippets management application with both desktop (PySide6) and web (React) user interfaces.

## Features

- **Categories Management**: Create, edit, and delete code categories
- **Snippets Management**: Create, edit, view, and delete code snippets within categories
- **Search Functionality**: Filter snippets by name or content
- **Desktop UI**: Native application built with PySide6
- **Web UI**: Responsive web interface built with React and Material UI
- **GraphQL API**: Backend API with persistent storage

## Architecture

The Snippets Library follows a three-tier architecture:

1. **User Interfaces**:
   - Desktop UI (PySide6)
   - Web UI (React + Material UI)

2. **API Layer**:
   - GraphQL API (Flask + Graphene)
   - RESTful endpoints for auxiliary functionality

3. **Data Layer**:
   - SQLite database
   - Pydantic models for validation

## Installation

### Requirements

- Python 3.8+
- Node.js 14+ (for web UI)
- npm 6+ (for web UI)

### Setup

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd AITypingTrainer
   ```

2. **Install Python dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Install Web UI dependencies**:
   ```
   npm install
   ```

## Running the Application

### Run Everything (Recommended)

Use the combined runner to start the API server and both user interfaces:

```
python run_snippets_library.py --web
```

- Use without the `--web` flag to only run the desktop UI.

### Run Components Separately

**API Server**:
```
python api/run_library_api.py
```

**Desktop UI**:
```
python desktop_ui/library_main.py
```

**Web UI**:
```
npm start
```

## Testing

The application includes comprehensive tests for all components:

### Run Python Tests

```
pytest tests/
```

### Run Web UI Tests

```
npm test
```

### Run End-to-End Tests

```
pytest tests/integration/test_end_to_end.py
```

## Development

### Project Structure

- `api/`: API server implementation
- `desktop_ui/`: PySide6 desktop UI
- `web_ui/`: React web UI
- `models/`: Shared data models
- `tests/`: Tests for all components

### Adding a New Feature

1. Write tests first (following TDD practice)
2. Implement the feature
3. Ensure all tests pass
4. Document the new functionality

## License

MIT

## Credits

This project was developed as part of the AI Typing Trainer application.
