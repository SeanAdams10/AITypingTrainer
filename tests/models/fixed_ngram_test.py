"""
Corrected version of test_four_keystrokes_no_errors
"""

def test_four_keystrokes_no_errors(self, temp_db, test_practice_session, four_keystrokes_no_errors):
    """
    Test objective: Verify that four keystrokes produce correct n-grams with proper timing.
    
    This test checks that:
    1. The analyzer properly handles four keystrokes with no errors
    2. Three bigrams, two trigrams, and one 4-gram are identified with correct timing:
       - Bigram 'Th': 500ms
       - Bigram 'he': 1000ms
       - Bigram 'en': 300ms
       - Trigram 'The': 1500ms
       - Trigram 'hen': 1300ms
       - 4-gram 'Then': 1800ms
    3. All identified n-grams are clean (no errors)
    4. N-grams are correctly saved to the database
    5. No error n-grams are identified
    """
    # Define the session ID constant for better readability in assertions
    session_id = test_practice_session.session_id
    
    # Create NGramAnalyzer instance with four keystrokes
    analyzer = NGramAnalyzer(test_practice_session, four_keystrokes_no_errors, temp_db)
    
    # Run the analyzer for n-grams of default sizes (2-5)
    analyzer.analyze()
    
    # Verify analysis was completed
    assert analyzer.analysis_complete is True, "Analysis should be marked as complete"
    
    # === VERIFY BIGRAMS ===
    assert 2 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for bigrams"
    assert len(analyzer.speed_ngrams[2]) == 3, "Should be exactly three speed bigrams"
    
    # Validate the first bigram 'Th'
    bigram1_text = "Th"  # The expected first bigram text
    bigram1 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram1_text)
    assert bigram1 is not None, "Bigram 'Th' not found in speed_ngrams[2]"
    assert bigram1.text == bigram1_text, "Bigram text should be 'Th'"
    assert bigram1.size == 2, "Bigram size should be 2"
    assert len(bigram1.keystrokes) == 2, "Bigram should have 2 keystrokes"
    assert bigram1.total_time_ms == 500, "Bigram 'Th' time should be 500ms"
    assert bigram1.avg_time_per_char_ms == 250, "Bigram 'Th' avg time should be 250ms per char"
    assert bigram1.is_clean is True, "Bigram should be clean (no errors)"
    assert bigram1.is_valid is True, "Bigram should be valid for timing tracking"
    
    # Validate the second bigram 'he'
    bigram2_text = "he"  # The expected second bigram text
    bigram2 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram2_text)
    assert bigram2 is not None, "Bigram 'he' not found in speed_ngrams[2]"
    assert bigram2.text == bigram2_text, "Bigram text should be 'he'"
    assert bigram2.size == 2, "Bigram size should be 2"
    assert len(bigram2.keystrokes) == 2, "Bigram should have 2 keystrokes"
    assert bigram2.total_time_ms == 1000, "Bigram 'he' time should be 1000ms"
    assert bigram2.avg_time_per_char_ms == 500, "Bigram 'he' avg time should be 500ms per char"
    assert bigram2.is_clean is True, "Bigram should be clean (no errors)"
    assert bigram2.is_valid is True, "Bigram should be valid for timing tracking"
    
    # Validate the third bigram 'en'
    bigram3_text = "en"  # The expected third bigram text
    bigram3 = _find_ngram_in_list(analyzer.speed_ngrams[2], bigram3_text)
    assert bigram3 is not None, "Bigram 'en' not found in speed_ngrams[2]"
    assert bigram3.text == bigram3_text, "Bigram text should be 'en'"
    assert bigram3.size == 2, "Bigram size should be 2"
    assert len(bigram3.keystrokes) == 2, "Bigram should have 2 keystrokes"
    assert bigram3.total_time_ms == 300, "Bigram 'en' time should be 300ms"
    assert bigram3.avg_time_per_char_ms == 150, "Bigram 'en' avg time should be 150ms per char"
    assert bigram3.is_clean is True, "Bigram should be clean (no errors)"
    assert bigram3.is_valid is True, "Bigram should be valid for timing tracking"
    
    # === VERIFY TRIGRAMS ===
    assert 3 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for trigrams"
    assert len(analyzer.speed_ngrams[3]) == 2, "Should be exactly two speed trigrams"
    
    # Validate the first trigram 'The'
    trigram1_text = "The"  # The expected first trigram text
    trigram1 = _find_ngram_in_list(analyzer.speed_ngrams[3], trigram1_text)
    assert trigram1 is not None, "Trigram 'The' not found in speed_ngrams[3]"
    assert trigram1.text == trigram1_text, "Trigram text should be 'The'"
    assert trigram1.size == 3, "Trigram size should be 3"
    assert len(trigram1.keystrokes) == 3, "Trigram should have 3 keystrokes"
    assert trigram1.total_time_ms == 1500, "Trigram 'The' total time should be 1500ms"
    assert trigram1.avg_time_per_char_ms == 500, "Trigram 'The' avg time should be 500ms per char"
    assert trigram1.is_clean is True, "Trigram should be clean (no errors)"
    assert trigram1.is_valid is True, "Trigram should be valid for timing tracking"
    
    # Validate the second trigram 'hen'
    trigram2_text = "hen"  # The expected second trigram text
    trigram2 = _find_ngram_in_list(analyzer.speed_ngrams[3], trigram2_text)
    assert trigram2 is not None, "Trigram 'hen' not found in speed_ngrams[3]"
    assert trigram2.text == trigram2_text, "Trigram text should be 'hen'"
    assert trigram2.size == 3, "Trigram size should be 3"
    assert len(trigram2.keystrokes) == 3, "Trigram should have 3 keystrokes"
    assert trigram2.total_time_ms == 1300, "Trigram 'hen' total time should be 1300ms"
    assert trigram2.avg_time_per_char_ms == pytest.approx(433.33, abs=0.1), "Trigram 'hen' avg time should be ~433.33ms per char"
    assert trigram2.is_clean is True, "Trigram should be clean (no errors)"
    assert trigram2.is_valid is True, "Trigram should be valid for timing tracking"
    
    # === VERIFY 4-GRAM ===
    assert 4 in analyzer.speed_ngrams, "Speed n-grams dictionary should have key for 4-grams"
    assert len(analyzer.speed_ngrams[4]) == 1, "Should be exactly one 4-gram"
    
    # Validate the 4-gram 'Then'
    fourgram_text = "Then"  # 4-gram
    fourgram = _find_ngram_in_list(analyzer.speed_ngrams[4], fourgram_text)
    assert fourgram is not None, "4-gram 'Then' not found in speed_ngrams[4]"
    assert fourgram.text == fourgram_text, "4-gram text should be 'Then'"
    assert fourgram.size == 4, "4-gram size should be 4"
    assert len(fourgram.keystrokes) == 4, "4-gram should have 4 keystrokes"
    assert fourgram.total_time_ms == 1800, "4-gram 'Then' total time should be 1800ms"
    assert fourgram.avg_time_per_char_ms == 450, "4-gram 'Then' avg time should be 450ms per char"
    assert fourgram.is_clean is True, "4-gram should be clean (no errors)"
    assert fourgram.is_valid is True, "4-gram should be valid for timing tracking"
    
    # === VERIFY NO ERROR N-GRAMS ===
    # Using `.get()` to safely access error_ngrams without KeyError if the keys don't exist
    assert len(analyzer.error_ngrams.get(2, [])) == 0, "Should be no error bigrams"
    assert len(analyzer.error_ngrams.get(3, [])) == 0, "Should be no error trigrams"
    assert len(analyzer.error_ngrams.get(4, [])) == 0, "Should be no error 4-grams"
    
    # === SAVE TO DATABASE AND VERIFY ===
    save_result = analyzer.save_to_database()
    assert save_result is True, "Save operation should succeed"
    
    # Verify speed n-grams were saved to the database correctly
    speed_ngrams = temp_db.fetchall(
        """SELECT ngram_size, ngram, ngram_time_ms 
           FROM session_ngram_speed 
           WHERE session_id = ?
           ORDER BY ngram_size, ngram""", 
        (session_id,)
    )
    
    assert len(speed_ngrams) == 6, "Should be exactly six speed n-grams in the database"
    
    # Verify the bigrams in the database
    # Note: We sort the results by ngram_size and then by ngram text
    db_bigram1 = speed_ngrams[0]  # 'Th'
    assert db_bigram1[0] == 2, "Database bigram1 size should be 2"
    assert db_bigram1[1] == "Th", "Database bigram1 text should be 'Th'"
    assert db_bigram1[2] == 250, "Database bigram1 avg time should be 250ms per char"
    
    db_bigram2 = speed_ngrams[1]  # 'en'
    assert db_bigram2[0] == 2, "Database bigram2 size should be 2"
    assert db_bigram2[1] == "en", "Database bigram2 text should be 'en'"
    assert db_bigram2[2] == 150, "Database bigram2 avg time should be 150ms per char"
    
    db_bigram3 = speed_ngrams[2]  # 'he'
    assert db_bigram3[0] == 2, "Database bigram3 size should be 2"
    assert db_bigram3[1] == "he", "Database bigram3 text should be 'he'"
    assert db_bigram3[2] == 500, "Database bigram3 avg time should be 500ms per char"
    
    # Verify the trigrams in the database
    db_trigram1 = speed_ngrams[3]  # 'The'
    assert db_trigram1[0] == 3, "Database trigram1 size should be 3"
    assert db_trigram1[1] == "The", "Database trigram1 text should be 'The'"
    assert db_trigram1[2] == 500, "Database trigram1 avg time should be 500ms per char"
    
    db_trigram2 = speed_ngrams[4]  # 'hen'
    assert db_trigram2[0] == 3, "Database trigram2 size should be 3"
    assert db_trigram2[1] == "hen", "Database trigram2 text should be 'hen'"
    assert db_trigram2[2] == pytest.approx(433.33, abs=0.1), "Database trigram2 avg time should be ~433.33ms per char"
    
    # Verify the 4-gram in the database
    db_fourgram = speed_ngrams[5]  # 'Then'
    assert db_fourgram[0] == 4, "Database 4-gram size should be 4"
    assert db_fourgram[1] == "Then", "Database 4-gram text should be 'Then'"
    assert db_fourgram[2] == 450, "Database 4-gram avg time should be 450ms per char"
    
    # Verify no error n-grams were saved to the database
    error_ngrams_count = temp_db.fetchone(
        "SELECT COUNT(*) FROM session_ngram_errors WHERE session_id = ?", 
        (session_id,)
    )[0]
    assert error_ngrams_count == 0, "Should be no error n-grams in the database"
    
    # Verify retrieval of slowest n-grams
    slowest_bigrams = analyzer.get_slowest_ngrams(size=2)
    assert len(slowest_bigrams) == 3, "Should be three slowest bigrams"
    # The slowest should be 'he' (500ms/char), then 'Th' (250ms/char), then 'en' (150ms/char)
    assert slowest_bigrams[0].text == "he", "Slowest bigram should be 'he'"
    assert slowest_bigrams[1].text == "Th", "Second slowest bigram should be 'Th'"
    assert slowest_bigrams[2].text == "en", "Third slowest bigram should be 'en'"
    
    slowest_trigrams = analyzer.get_slowest_ngrams(size=3)
    assert len(slowest_trigrams) == 2, "Should be two slowest trigrams"
    # The slowest should be 'The' (500ms/char) then 'hen' (~433ms/char)
    assert slowest_trigrams[0].text == "The", "Slowest trigram should be 'The'"
    assert slowest_trigrams[1].text == "hen", "Second slowest trigram should be 'hen'"
    
    # Get error-prone n-grams - should return empty lists since we have no errors
    error_prone_ngrams = analyzer.get_most_error_prone_ngrams(size=2)
    assert len(error_prone_ngrams) == 0, "Should be no error-prone n-grams"
