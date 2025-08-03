#!/usr/bin/env python3
"""
Text Randomizer Program

Takes a long string of text, extracts unique words (split by space),
and outputs them in random order with each word appearing at most twice.
"""

import random
from typing import List


def randomize_text_words(input_text: str) -> str:
    """
    Process input text to create a randomized output with unique words appearing at most twice.
    
    Args:
        input_text: The input string to process
        
    Returns:
        A space-delimited string with words in random order, each appearing at most twice
    """
    # Split text into words by spaces and get unique words
    words = input_text.split()
    unique_words = list(set(words))
    
    # Create a list where each unique word appears at most twice
    output_words: List[str] = []
    for word in unique_words:
        # Add each word once
        output_words.append(word)
        # Add each word a second time (so each appears at most twice)
        output_words.append(word)
    
    # Shuffle the list randomly
    random.shuffle(output_words)
    
    # Join back into a space-delimited string
    return ' '.join(output_words)


def main() -> None:
    """Main function to demonstrate the text randomizer."""
    # Example usage
    sample_text = """
    The quick brown fox jumps over the lazy dog. The dog was sleeping under the tree.
    A quick fox is very clever and can jump high. The brown animal runs fast through the forest.
    """
    
    print("Original text:")
    print(sample_text.strip())
    print("\nUnique words randomized (each appearing at most twice):")
    
    result = randomize_text_words(sample_text)
    print(result)
    
    # Interactive mode
    print("\n" + "="*50)
    print("Interactive Mode - Enter your own text:")
    user_input = input("Enter text to randomize (or press Enter to exit): ").strip()
    
    if user_input:
        randomized = randomize_text_words(user_input)
        print(f"\nRandomized output:\n{randomized}")


if __name__ == "__main__":
    main()
