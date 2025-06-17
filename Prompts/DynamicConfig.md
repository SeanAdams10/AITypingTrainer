# Dynamic N-gram Practice Configuration Screen

## 1. Overview

The Dynamic N-gram Practice Configuration screen allows users to generate customized typing practice based on their performance data. It analyzes the user's typing patterns to identify challenging n-grams (such as slowest or most error-prone sequences) and generates targeted practice content. This screen helps users focus their practice on specific weak spots to improve typing efficiency and accuracy.

The implementation supports both a PyQt5 desktop UI and a potential web UI in the future, with consistent functionality across platforms.

---

## 2. Functional Requirements

### 2.1 Configuration Panel

- **N-gram Size Selection:**
  - Dropdown to select n-gram length (2-10 characters)
  - Default: 4
  - Updates the n-gram analysis when changed

- **Practice Focus:**
  - Dropdown or radio button group with two options:
    1. Focus on Speed: Targets user's slowest n-grams (uses `NGramManager.slowest_n()`)
    2. Focus on Accuracy: Targets n-grams with most errors (uses `NGramManager.error_n()`)
  - Default: Focus on Speed
  - Updates the n-gram analysis when changed

- **Top N Selection:**
  - Numeric input field for specifying the number of n-grams to target
  - Must be a positive integer
  - Default: 5
  - Minimum: 1
  - Maximum: 20
  - Controls how many weak spots will be included in the practice

- **Practice Length:**
  - Numeric input field for desired practice length in characters
  - Must be a positive integer
  - Default: 200
  - Minimum: 50
  - Maximum: 2000
  - Shows validation feedback for invalid inputs

### 2.2 N-gram Analysis Display

- Shows a read-only text area displaying the top n problematic n-grams based on selection:
  - For speed focus: Shows the n slowest n-grams (using `NGramManager.slowest_n()`)
  - For accuracy focus: Shows the n n-grams with most errors (using `NGramManager.error_n()`)
- Updates automatically when any configuration changes
- Each n-gram is displayed with its performance metrics:
  - For speed: Average time to type (ms)
  - For accuracy: Error count
- Empty state handling if insufficient n-gram data is available

### 2.3 Content Generation

- **Generate Button:**
  - Disabled until all required fields are valid
  - Generates practice text that incorporates the identified weak spot n-grams using the LLM service
  - Shows loading state during generation

- **Generated Content Display:**
  - Preview dialog (or integrated display) showing the generated practice text
  - Content length matches the requested character count
  - Incorporates the targeted weak spot n-grams in a natural, readable format
  - Provides multiple opportunities to practice each weak spot

### 2.4 Drill Launch

- **Start Drill Button:**
  - Enabled only when valid practice content is generated
  - Creates a practice snippet and category if they don't exist
  - Launches the typing drill with the generated text using `typing_drill.py`
  - Passes all required parameters (snippet ID, user ID, keyboard ID, etc.)

- **Cancel Button:**
  - Returns to the previous screen without starting a drill

### 2.5 Status Bar

- Displays at the bottom of the screen, showing:
  - Current user information (name)
  - Current keyboard information
  - Identical implementation to the status bar in `drill_config.py`

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

## 4. Implementation Requirements

### 4.1 Code Structure

- Create `dynamic_config.py` in the `desktop_ui` directory
- Follow the same pattern as `drill_config.py` for consistency
- Implement the UI using PyQt5, maintaining the style of the existing application

### 4.2 Backend Integration

#### N-Gram Data Retrieval
- Use `NGramManager.slowest_n()` to retrieve the slowest n-grams
- Use `NGramManager.error_n()` to retrieve the most error-prone n-grams
- Leverage existing database tables:
  - `session_ngram_speed` for speed data
  - `session_ngram_errors` for error data

#### Practice Text Generation
- Generate text that incorporates the identified weak spot n-grams
- Ensure text is natural, readable, and appropriately challenging
- Aim for a distribution that gives more practice to the weakest areas

#### Drill Initialization
- Create a "Practice" category if it doesn't exist
- Create a practice snippet with the generated text
- Pass the snippet ID, user ID, keyboard ID, and other parameters to `typing_drill.py`
- Launch the typing drill screen with these parameters

### 4.3 Error Handling and Validation
- Validate all user input with clear error messages
- Handle cases with insufficient n-gram data gracefully
- Provide informative feedback during text generation



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

## 10. Future Enhancements

### 10.1 Web UI Integration
- Create a web-based version with identical functionality
- Use React for the frontend
- Implement WebSocket for real-time feedback
- Match desktop UI functionality

### 10.2 Advanced Text Generation
- Consider LLM integration for more natural text generation
- Implement advanced algorithms for optimal n-gram distribution
- Add options for different difficulty levels

### 10.3 Additional Analytics
- Show progress over time for specific n-grams
- Provide recommendations based on performance trends
- Support personalized training paths

---

## 11. Implementation Notes

- Prioritize desktop UI implementation first
- Ensure compatibility with existing database schema
- Maintain consistent UX with other application screens
- Follow the existing UI patterns for consistency

---

This specification defines the requirements for the Dynamic N-gram Practice Configuration screen, ensuring a consistent and effective user experience for targeted typing practice.
