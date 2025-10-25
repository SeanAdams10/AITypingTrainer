# DynamicContentService

## Overview

The `DynamicContentService` class provides dynamic content generation for typing practice exercises. It supports multiple content modes including n-gram analysis, word-based exercises, and mixed content generation to create personalized typing practice sessions.

## Class: DynamicContentService

### Location
`models/dynamic_content_service.py`

### Purpose
Generates dynamic typing practice content based on user performance analytics, keyboard layout analysis, and configurable practice parameters.

### Key Features
- **Multiple Content Modes**: Supports n-gram, words, and mixed content generation
- **Keyboard Layout Integration**: Considers physical key positions and finger assignments
- **Performance-Based Content**: Uses analytics to focus on problem areas
- **LLM Integration**: Leverages language models for intelligent word selection
- **Dynamic Snippet Management**: Ensures valid snippet IDs for database integrity

### Constructor Parameters
- `in_scope_keys`: List of keys to focus practice on
- `practice_length`: Target length of generated content (1-1000 characters)
- `ngram_focus_list`: Specific n-grams to emphasize in practice
- `content_mode`: Mode of content generation (ContentMode enum)
- `llm_service`: Optional LLM service for word-based content generation

### Methods

#### Core Content Generation
- `generate_content()`: Main method to generate practice content based on configured mode
- `_generate_ngram_content()`: Creates n-gram focused practice text
- `_generate_words_content()`: Generates word-based exercises using LLM
- `_generate_mixed_content()`: Combines n-gram and word-based content

#### Snippet Management
- `ensure_dynamic_snippet_id(category_manager, snippet_manager)`: Ensures a valid dynamic snippet exists for typing drills, coordinating with CategoryManager and SnippetManager to create necessary categories and snippets

#### Utility Methods
- `_get_ngram_weights()`: Calculates weights for n-gram selection
- `_select_weighted_ngrams()`: Selects n-grams based on calculated weights
- `_format_content()`: Formats generated content for typing practice

### Content Modes

#### ContentMode.NGRAMS
Focuses on n-gram patterns identified through performance analytics:
- Emphasizes problematic key combinations
- Uses weighted selection based on error rates
- Generates repetitive patterns for muscle memory development

#### ContentMode.WORDS
Creates word-based exercises using LLM services:
- Generates contextually relevant vocabulary
- Focuses on words containing target key combinations
- Provides more natural typing practice

#### ContentMode.MIXED
Combines n-gram and word-based approaches:
- Balances pattern practice with natural language
- Adapts content ratio based on user preferences
- Provides comprehensive typing skill development

### Usage Examples

#### Basic N-gram Content Generation
```python
from models.dynamic_content_service import DynamicContentService, ContentMode

# Create service for n-gram practice
dcs = DynamicContentService(
    in_scope_keys=['a', 's', 'd', 'f'],
    practice_length=200,
    ngram_focus_list=['as', 'df', 'sad'],
    content_mode=ContentMode.NGRAMS
)

content = dcs.generate_content()
```

#### Word-based Content with LLM
```python
from models.dynamic_content_service import DynamicContentService, ContentMode
from models.llm_ngram_service import LLMNgramService

llm_service = LLMNgramService()
dcs = DynamicContentService(
    in_scope_keys=['q', 'w', 'e', 'r'],
    practice_length=300,
    content_mode=ContentMode.WORDS,
    llm_service=llm_service
)

content = dcs.generate_content()
```

#### Ensuring Dynamic Snippet ID
```python
from models.dynamic_content_service import DynamicContentService
from models.category_manager import CategoryManager
from models.snippet_manager import SnippetManager

# Create service and managers
dcs = DynamicContentService()
category_manager = CategoryManager()
snippet_manager = SnippetManager()

# Ensure valid snippet ID exists for typing drills
snippet_id = dcs.ensure_dynamic_snippet_id(category_manager, snippet_manager)
```

### Integration Points

#### UI Components
- `dynamic_config.py`: Uses DynamicContentService for n-gram practice configuration
- `drill_config.py`: Integrates service for custom text snippet handling

#### Analytics Integration
- Works with `NGramAnalyticsService` for performance-based content selection
- Uses keyboard layout data for physical key relationship analysis

#### Database Integration
- Coordinates with CategoryManager and SnippetManager for snippet persistence
- Ensures foreign key integrity when creating practice sessions

### Error Handling
- Validates practice length parameters (1-1000 characters)
- Handles missing LLM service gracefully for word-based content
- Provides fallback content generation when external services fail
- Raises appropriate exceptions for database operation failures

### Performance Considerations
- Caches n-gram weights to avoid repeated calculations
- Optimizes content generation for target practice length
- Balances content variety with focus on problem areas
- Efficient snippet lookup and creation to minimize database operations

### Dependencies
- `models.ngram_analytics_service`: For performance analytics
- `models.keyboard_manager`: For keyboard layout information
- `models.llm_ngram_service`: For LLM-based content generation
- `models.category_manager`: For category management
- `models.snippet_manager`: For snippet operations
- `enum`: For ContentMode enumeration
- `random`: For content randomization
- `typing`: For type hints

### Notes
- Content generation is deterministic when using the same parameters and seed
- LLM service is optional; word-based content will fall back to n-gram content if unavailable
- Generated content respects keyboard layout constraints for realistic practice scenarios
- The service ensures database integrity by always providing valid snippet IDs for typing drills
