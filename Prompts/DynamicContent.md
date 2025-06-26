# Dynamic Content Manager Requirements

## Overview
The Dynamic Content Manager (DCM) is a component responsible for generating customizable typing practice content based on specific parameters. It allows for different modes of content generation and focuses on specified n-grams and character sets.

## Core Features

### Configurable Parameters
The DCM supports the following configurable parameters:

1. **In-Scope Keys**
   - A list of keyboard keys/characters that are allowed in the generated content
   - Each key represents a single character on the keyboard
   - All generated content must only use characters from this list

2. **Practice Length**
   - Integer value between 1 and 1000
   - Determines the maximum length of the generated practice content in characters
   - The system will generate content that fits within this limit

3. **N-gram Focus List**
   - List of n-grams to emphasize in the generated content
   - Each n-gram is a sequence of characters (typically 2-4 characters) that appears frequently in text
   - The generated content will contain these n-grams according to the selected mode

4. **Content Generation Mode**
   - Determines how content is generated and what elements it includes
   - Three supported modes:
     - **NGramOnly**: Practice text consists solely of n-grams from the focus list
     - **WordsOnly**: Practice text consists of valid words containing the focus n-grams
     - **Mixed**: Practice text combines both individual n-grams and complete words

### Content Generation
The primary function of the DCM is to generate practice content based on the configured parameters:

1. **NGramOnly Mode**
   - Takes n-grams from the focus list and arranges them randomly
   - Ensures that only n-grams containing in-scope keys are included
   - Joins the n-grams using a specified delimiter (default: space)
   - Limits the content to the specified practice length

2. **WordsOnly Mode**
   - Uses the LLM N-gram Service to obtain words containing the focus n-grams
   - Filters the words to ensure they only contain in-scope keys
   - Randomizes the word order for varied practice
   - Joins the words using a specified delimiter (default: space)
   - Limits the content to the specified practice length

3. **Mixed Mode**
   - Combines both n-gram sequences and words containing those n-grams
   - Ensures a good mix of both element types
   - Shuffles the combined elements for varied practice
   - Joins the elements using a specified delimiter (default: space)
   - Limits the content to the specified practice length

## Integration Points

1. **LLM N-gram Service**
   - Required for WordsOnly and Mixed modes
   - Provides words containing specific n-grams
   - Can be configured with API keys and model settings

## Usage Examples

```python
# Create a manager for practicing specific n-grams
dcm = DynamicContentManager(
    in_scope_keys=["a", "s", "d", "f", "j", "k", "l"],
    practice_length=200,
    ngram_focus_list=["as", "df", "jk"],
    mode=ContentMode.NGRAM_ONLY
)

# Generate practice content
practice_text = dcm.generate_content()  # Uses default space delimiter
```

```python
# Create a manager for practicing words with specific n-grams
from models.llm_ngram_service import LLMNgramService

# Initialize LLM service for word generation
llm_service = LLMNgramService(api_key="your-api-key")

dcm = DynamicContentManager(
    in_scope_keys=["e", "t", "a", "o", "i", "n", "s", "h"],
    practice_length=500,
    ngram_focus_list=["th", "in", "an"],
    mode=ContentMode.MIXED,
    llm_service=llm_service
)

# Generate practice content with custom delimiter
practice_text = dcm.generate_content(delimiter=" | ")
```

## Requirements

1. The system must validate that all generated content only uses characters from the in-scope keys list
2. The system must validate that the practice length is within the allowed range (1-1000)
3. The system must ensure that generated content respects the specified maximum length
4. In NGramOnly mode, the system must use n-grams directly from the focus list
5. In WordsOnly mode, the system must use actual words containing the focus n-grams
6. In Mixed mode, the system must balance between individual n-grams and complete words
7. The system must randomize the order of elements in the generated content
8. The system must allow for a configurable delimiter between content elements
