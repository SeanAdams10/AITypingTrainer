# Dynamic N-gram Practice Configuration Screen

## 1. Overview

The Dynamic N-gram Practice Configuration screen allows users to generate customized typing practice based on their performance data. It analyzes the user's typing patterns to identify challenging n-grams and generates targeted practice content using an LLM. This screen is available both as a modern web UI and a desktop UI, with identical functionality and a unified backend API.

---

## 2. Functional Requirements

### 2.1 Configuration Panel

- **N-gram Size Selection:**
  - Dropdown to select n-gram length (3-10 characters)
  - Default: 4
  - Updates the n-gram analysis when changed

- **Practice Focus:**
  - Radio button group with two options:
    1. Focus on Speed: Targets user's slowest n-grams
    2. Focus on Accuracy: Targets n-grams with most errors
  - Default: Focus on Speed
  - Updates the n-gram analysis when changed

- **Practice Length:**
  - Numeric input field for desired practice length in characters
  - Must be a positive integer
  - Default: 200
  - Minimum: 50
  - Maximum: 2000
  - Shows validation feedback for invalid inputs

### 2.2 N-gram Analysis Display

- Shows a read-only text area displaying the top 5 problematic n-grams based on selection:
  - For speed focus: Shows the 5 slowest n-grams (based on average of last 20 entries)
  - For accuracy focus: Shows the 5 n-grams with most errors (from last 20 sessions)
- Updates automatically when any configuration changes
- Each n-gram is displayed with its performance metrics:
  - For speed: Average time to type (ms)
  - For accuracy: Error count and error rate

### 2.3 Content Generation

- **Generate Button:**
  - Disabled until all required fields are valid
  - Triggers the LLM service to generate practice content
  - Shows loading state during generation

- **Generated Content Display:**
  - Read-only text area showing the LLM-generated practice text
  - Content length matches the requested number of characters
  - Includes the selected problematic n-grams in natural context
  - Formatted for readability with proper line breaks

### 2.4 Drill Launch

- **Start Drill Button:**
  - Enabled only when valid practice content is generated
  - Launches the typing drill with the generated content
  - Uses the same drill interface as the standard typing drill

- **Cancel Button:**
  - Returns to the previous screen
  - Confirms if there are unsaved changes

---

## 3. Data Flow

1. **Initial Load:**
   - Fetch user's typing statistics from `session_ngram_speed` and `session_ngram_errors` tables
   - Populate initial n-gram analysis based on default settings

2. **Configuration Change:**
   - When any setting changes, requery the database for relevant n-gram data
   - Update the n-gram analysis display
   - Clear any previously generated content

3. **Content Generation:**
   - On Generate button click:
     1. Collect selected n-grams and configuration
     2. Call `llm_ngram_service.generate_practice_content()`
     3. Display generated content in the preview area

4. **Drill Launch:**
   - Pass generated content to the typing drill interface
   - Use the same session tracking as standard drills

---

## 4. Database Schema Requirements

### session_ngram_speed
- `id` (PK)
- `user_id` (FK to users)
- `ngram` (TEXT)
- `average_time_ms` (FLOAT)
- `sample_size` (INTEGER)
- `last_updated` (TIMESTAMP)

### session_ngram_errors
- `id` (PK)
- `user_id` (FK to users)
- `ngram` (TEXT)
- `error_count` (INTEGER)
- `total_occurrences` (INTEGER)
- `last_updated` (TIMESTAMP)

---

## 5. API Endpoints

### GET /api/ngram/analysis
- Parameters:
  - `length`: N-gram length (3-10)
  - `focus`: 'speed' or 'accuracy'
  - `limit`: Number of n-grams to return (default: 5)
- Returns: JSON array of n-grams with metrics

### POST /api/ngram/generate
- Request Body:
  ```json
  {
    "ngrams": ["th", "he", "in"],
    "length": 200,
    "focus": "speed"
  }
  ```
- Returns: Generated practice text

---

## 6. Error Handling

- **Invalid Input:**
  - Show clear error messages for invalid configuration
  - Disable Generate button until all inputs are valid

- **Generation Failures:**
  - Show user-friendly error if LLM service fails
  - Provide option to retry

- **Database Issues:**
  - Handle missing or incomplete n-gram data gracefully
  - Provide fallback content if needed

---

## 7. Testing Requirements

### Unit Tests
- N-gram analysis logic
- Input validation
- Data transformation

### Integration Tests
- API endpoints
- Database queries
- LLM service integration

### UI Tests
- Configuration changes update analysis
- Generate button behavior
- Error states and validation
- Drill launch flow

### Performance Tests
- N-gram analysis response time
- Content generation time

---

## 8. Security Considerations

- Validate all user inputs
- Sanitize generated content before display
- Implement rate limiting for generation endpoint
- Ensure proper access controls for user data

---

## 9. Accessibility

- Keyboard navigation support
- Screen reader compatibility
- Sufficient color contrast
- Clear focus indicators
- Descriptive labels and instructions

---

This specification defines the requirements for the Dynamic N-gram Practice Configuration screen, ensuring a consistent and effective user experience for targeted typing practice.
