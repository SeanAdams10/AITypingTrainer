When a typing drill finishes - it does a complex series of events, I'd you to make sure that all these events are happening in the right order (because right now some of these steps are not completing successfully)


Deliverable:
- Updated code that is run at the end of the typing drill, which saves the session, then saves the keystrokes for that session, then invokes the ngram_manager to analyze and save the base ngram details into session_ngram_speed; and session_ngram_errors.    It then summarizes the performance of ngrams for this session (using the @ngram_analytics_service.py to create the entry into session_ngram_summary.    finally it must make the ngram speed smmary entries into ngram_speed_summary_curr and hist - also using the analytics service.
- If any of these fail to complete with a success code - then an exception must be raised
- all of that must be done before the summary screen shows when the typing drill saves the results

Assumptions:
- All the base code to do this work already exists - it just needs to be reorganized
- there may be race conditions causing this to not work currently - so the order above is important
- Please update any tests that use this functionalyt
- This code should probably not be in TypingDrill - please use your judgement, but I think that much of this should be refactored into ngram_analytics_service
- Please also fix any mypy or ruff issues identified in any of the files you touch iteratively until there are none left
- All variables need to be type checked
- Functions should follow Martin Fowler's "Single Responsiblity" principle - if not, please refactor gradually to fix this using the extract function pattern.    
- Test cases must be updated to comprensively test any functionality added or changed.    Do not adjust test cases only to fix failing tests - test cases must achieve the outcome in the .md file.     Any new tests should make use of common test fixtures, and should be parameterized tests where possible.
- Requirement files (.md specifications) should contain the most up to date requirements for functionality, in a structured fashion, along with the 
- Please follow the guidance in @code_generation_standards.md , @python_coding_standards.md @tdd_delivery.md and @testing_and_trustability.md 

Non Goals: 
- Do not change other areas of the code unless you get explicit confirmtaion from me

Acceptance:
- No ruff or Mypy issues
- Defect identified is resolved
- Test case coverage is at 90%+ without committing demeter violations (create test affordances if needed)
