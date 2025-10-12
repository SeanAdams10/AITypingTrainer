"""Tests for KeystrokeCollection class."""

import random
import uuid
from datetime import datetime, timedelta

from models.keystroke import Keystroke
from models.keystroke_collection import KeystrokeCollection


class TestKeystrokeCollection:
    """Test cases for KeystrokeCollection functionality."""

    def test_initialization(self):
        """Test that KeystrokeCollection initializes with empty lists."""
        collection = KeystrokeCollection()

        assert collection.raw_keystrokes == []
        assert collection.net_keystrokes == []
        assert collection.get_raw_count() == 0
        assert collection.get_net_count() == 0

    def test_add_single_backspace(self):
        """Test that adding only a backspace results in raw keystroke but no net keystrokes."""
        collection = KeystrokeCollection()

        # Create a backspace keystroke
        backspace_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="a",
            key_index=0,
            keystroke_time=datetime.now(),
        )

        collection.add_keystroke(backspace_keystroke)

        # Raw keystrokes should include the backspace
        assert collection.get_raw_count() == 1
        assert collection.raw_keystrokes[0].keystroke_char == "\b"

        # Net keystrokes should be empty (no previous characters to remove)
        assert collection.get_net_count() == 0
        assert collection.net_keystrokes == []

    def test_add_character_then_backspace(self):
        """Test adding 'a' then backspace - raw should have both, net should be empty."""
        collection = KeystrokeCollection()

        # Create keystroke for 'a'
        a_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=datetime.now(),
        )

        # Create backspace keystroke
        backspace_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=1,
            keystroke_time=datetime.now(),
        )

        collection.add_keystroke(a_keystroke)
        collection.add_keystroke(backspace_keystroke)

        # Raw keystrokes should have both 'a' and backspace
        assert collection.get_raw_count() == 2
        assert collection.raw_keystrokes[0].keystroke_char == "a"
        assert collection.raw_keystrokes[1].keystroke_char == "\b"

        # Net keystrokes should be empty (backspace removed the 'a')
        assert collection.get_net_count() == 0
        assert collection.net_keystrokes == []

    def test_add_character_then_backspace_then_continue(self):
        """Test adding 'a' then backspace - raw should have both, net should be empty."""
        collection = KeystrokeCollection()

        # Create keystroke for 'a'
        a_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=datetime.now(),
        )

        # Create backspace keystroke
        backspace_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=1,
            keystroke_time=datetime.now() + timedelta(milliseconds=120),
        )

        # add the letter b
        b_keystroke: Keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="b",
            expected_char="b",
            key_index=1,
            keystroke_time=datetime.now() + timedelta(milliseconds=250),
        )

        # add the letter c
        c_keystroke: Keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="c",
            expected_char="c",
            key_index=1,
            keystroke_time=datetime.now() + timedelta(milliseconds=380),
        )

        collection.add_keystroke(a_keystroke)
        collection.add_keystroke(backspace_keystroke)
        collection.add_keystroke(b_keystroke)
        collection.add_keystroke(c_keystroke)

        # Raw keystrokes should have both 'a' and backspace and 'b' and 'c'
        assert collection.get_raw_count() == 4
        assert collection.raw_keystrokes[0].keystroke_char == "a"
        assert collection.raw_keystrokes[1].keystroke_char == "\b"
        assert collection.raw_keystrokes[2].keystroke_char == "b"
        assert collection.raw_keystrokes[3].keystroke_char == "c"

        # Net keystrokes should only have the b and c (backspace removed the 'a')
        assert collection.get_net_count() == 2
        assert collection.net_keystrokes[0].keystroke_char == "b"
        assert collection.net_keystrokes[1].keystroke_char == "c"
        assert collection.net_keystrokes[0].time_since_previous == -1
        assert (
            collection.net_keystrokes[1].time_since_previous
            == collection.raw_keystrokes[3].time_since_previous
        )

    def test_add_two_characters(self):
        """Test adding 'a' then 'b' - both raw and net should have 2 entries."""
        collection = KeystrokeCollection()

        # Create keystroke for 'a'
        a_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=datetime.now(),
        )

        # Create keystroke for 'b'
        b_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="b",
            expected_char="b",
            key_index=1,
            keystroke_time=datetime.now(),
        )

        collection.add_keystroke(a_keystroke)
        collection.add_keystroke(b_keystroke)

        # Raw keystrokes should have both 'a' and 'b'
        assert collection.get_raw_count() == 2
        assert collection.raw_keystrokes[0].keystroke_char == "a"
        assert collection.raw_keystrokes[1].keystroke_char == "b"

        # Net keystrokes should also have both 'a' and 'b'
        assert collection.get_net_count() == 2
        assert collection.net_keystrokes[0].keystroke_char == "a"
        assert collection.net_keystrokes[1].keystroke_char == "b"

    def test_memory_management_large_list(self):
        """Ensure large keystroke collections can be managed and reset."""
        collection = KeystrokeCollection()
        base_time = datetime.now()

        large_count = 10_000
        for index in range(large_count):
            keystroke = Keystroke(
                session_id="memory-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=base_time + timedelta(milliseconds=index),
                keystroke_char="a",
                expected_char="a",
                is_error=False,
            )
            collection.add_keystroke(keystroke)

        assert collection.get_raw_count() == large_count

        collection.clear()
        assert collection.get_raw_count() == 0
        assert collection.get_net_count() == 0

    def test_complex_sequence_with_multiple_backspaces(self):
        """Test a complex sequence: type 'hello', backspace twice, type 'p'."""
        collection = KeystrokeCollection()

        # Type 'hello'
        for i, char in enumerate("hello"):
            keystroke = Keystroke(
                session_id="test-session",
                keystroke_char=char,
                expected_char=char,
                key_index=i,
                keystroke_time=datetime.now(),
            )
            collection.add_keystroke(keystroke)

        # Backspace twice (remove 'o' and 'l')
        for i in range(2):
            backspace = Keystroke(
                session_id="test-session",
                keystroke_char="\b",
                expected_char="",
                key_index=5 + i,
                keystroke_time=datetime.now(),
            )
            collection.add_keystroke(backspace)

        # Type 'p'
        p_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="p",
            expected_char="p",
            key_index=7,
            keystroke_time=datetime.now(),
        )
        collection.add_keystroke(p_keystroke)

        # Raw should have all keystrokes: h,e,l,l,o,backspace,backspace,p
        assert collection.get_raw_count() == 8
        raw_chars = [ks.keystroke_char for ks in collection.raw_keystrokes]
        expected_raw = ["h", "e", "l", "l", "o", "\b", "\b", "p"]
        assert raw_chars == expected_raw

        # Gross should have: h,e,l,p (after backspaces removed 'l' and 'o')
        assert collection.get_net_count() == 4
        net_chars = [ks.keystroke_char for ks in collection.net_keystrokes]
        expected_net = ["h", "e", "l", "p"]
        assert net_chars == expected_net

    def test_complex_sequence_with_multiple_backspaces_2(self):
        """Test a complex sequence: type 'hello', backspace twice, type 'p'."""
        collection = KeystrokeCollection()

        # Type 'hello'
        for i, char in enumerate("hello"):
            keystroke = Keystroke(
                session_id="test-session",
                keystroke_char=char,
                expected_char=char,
                key_index=i,
                keystroke_time=datetime.now(),
            )
            collection.add_keystroke(keystroke)

        # Backspace twice (remove 'o' and 'l')
        for i in range(2):
            backspace = Keystroke(
                session_id="test-session",
                keystroke_char="\b",
                expected_char="",
                key_index=5 + i,
                keystroke_time=datetime.now(),
            )
            collection.add_keystroke(backspace)

        # Type 'p'
        p_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="p",
            expected_char="p",
            key_index=7,
            keystroke_time=datetime.now(),
        )
        collection.add_keystroke(p_keystroke)

        # append two more backspaces
        backspace = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=8,
            keystroke_time=datetime.now(),
        )
        collection.add_keystroke(backspace)

        backspace = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=9,
            keystroke_time=datetime.now(),
        )
        collection.add_keystroke(backspace)

        # Finally add the character m
        m_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="m",
            expected_char="m",
            key_index=10,
            keystroke_time=datetime.now(),
        )
        collection.add_keystroke(m_keystroke)

        # Raw should have all keystrokes: h,e,l,l,o,backspace,backspace,p,backspace, backspace, m
        assert collection.get_raw_count() == 11
        raw_chars = [ks.keystroke_char for ks in collection.raw_keystrokes]
        expected_raw = ["h", "e", "l", "l", "o", "\b", "\b", "p", "\b", "\b", "m"]
        assert raw_chars == expected_raw

        # Net should have all keystrokes: h,e,m
        assert collection.get_net_count() == 3
        net_chars = [ks.keystroke_char for ks in collection.net_keystrokes]
        expected_net = ["h", "e", "m"]
        assert net_chars == expected_net

        # the sum of time since previous for the raw keystrokes should equal
        # the sum of time since previous of the net keystrokes
        raw_time_sum = sum(ks.time_since_previous for ks in collection.raw_keystrokes)
        net_time_sum = sum(ks.time_since_previous for ks in collection.net_keystrokes)
        assert raw_time_sum == net_time_sum

        # the time since previous for net keystroke 2 should equal the sum of all
        # time since previous of the raw keystrokes from index 1 to the end
        net_keystroke_2_time = collection.net_keystrokes[1].time_since_previous
        raw_keystrokes_sum = sum(ks.time_since_previous for ks in collection.raw_keystrokes[1:])
        assert net_keystroke_2_time == raw_keystrokes_sum

        # the time since previous for net keystroke 2 should equal the difference
        # between keystroke time of raw keystroke index 1 and keystroke time of raw index 10
        start_time: datetime = collection.raw_keystrokes[1].keystroke_time
        end_time: datetime = collection.raw_keystrokes[10].keystroke_time
        time_diff = end_time - start_time
        offset_ms: int = int(time_diff.total_seconds() * 1000)
        assert collection.net_keystrokes[1].time_since_previous == offset_ms

    def test_multiple_backspaces_on_empty_gross(self):
        """Test multiple backspaces when net_keystrokes is already empty."""
        collection = KeystrokeCollection()

        # Add multiple backspaces
        for i in range(3):
            backspace = Keystroke(
                session_id="test-session",
                keystroke_char="\b",
                expected_char="",
                key_index=i,
                keystroke_time=datetime.now(),
            )
            collection.add_keystroke(backspace)

        # Raw should have all 3 backspaces
        assert collection.get_raw_count() == 3
        assert all(ks.keystroke_char == "\b" for ks in collection.raw_keystrokes)

        # Gross should remain empty (no characters to remove)
        assert collection.get_net_count() == 0
        assert collection.net_keystrokes == []

    def test_clear_functionality(self):
        """Test that clear() empties both collections."""
        collection = KeystrokeCollection()

        # Add some keystrokes
        keystroke1 = Keystroke(
            session_id="test-session", keystroke_char="a", expected_char="a", key_index=0
        )
        keystroke2 = Keystroke(
            session_id="test-session", keystroke_char="b", expected_char="b", key_index=1
        )

        collection.add_keystroke(keystroke1)
        collection.add_keystroke(keystroke2)

        # Verify collections have data
        assert collection.get_raw_count() == 2
        assert collection.get_net_count() == 2

        # Clear and verify empty
        collection.clear()
        assert collection.get_raw_count() == 0
        assert collection.get_net_count() == 0
        assert collection.raw_keystrokes == []
        assert collection.net_keystrokes == []

    def test_key_index_preservation(self):
        """Test that key_index values are preserved correctly."""
        collection = KeystrokeCollection()

        # Add keystrokes with specific key_index values
        keystroke1 = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=5,  # Non-sequential key_index
            keystroke_time=datetime.now(),
        )

        backspace = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=10,  # Non-sequential key_index
            keystroke_time=datetime.now(),
        )

        collection.add_keystroke(keystroke1)
        collection.add_keystroke(backspace)

        # Verify key_index preservation in raw_keystrokes
        assert collection.raw_keystrokes[0].key_index == 5
        assert collection.raw_keystrokes[1].key_index == 10

        # Verify net_keystrokes is empty due to backspace
        assert collection.get_net_count() == 0

    def test_different_character_types(self):
        """Test with different types of characters (letters, numbers, symbols)."""
        collection = KeystrokeCollection()

        characters = ["a", "1", "@", " ", "\t", "Z"]

        for i, char in enumerate(characters):
            keystroke = Keystroke(
                session_id="test-session",
                keystroke_char=char,
                expected_char=char,
                key_index=i,
                keystroke_time=datetime.now(),
            )
            collection.add_keystroke(keystroke)

        # Both collections should have all characters
        assert collection.get_raw_count() == len(characters)
        assert collection.get_net_count() == len(characters)

        # Verify character preservation
        raw_chars = [ks.keystroke_char for ks in collection.raw_keystrokes]
        net_chars = [ks.keystroke_char for ks in collection.net_keystrokes]

        assert raw_chars == characters
        assert net_chars == characters


class TestKeystrokeCollectionTimingSince:
    """Test cases for time_since_previous functionality in KeystrokeCollection."""

    def test_single_keystroke_timing(self):
        """Test that a single keystroke has time_since_previous = -1."""
        collection = KeystrokeCollection()
        base_time = datetime.now()

        # Create a single keystroke
        keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=base_time,
        )

        collection.add_keystroke(keystroke)

        # First keystroke should have time_since_previous = -1
        assert collection.get_raw_count() == 1
        assert collection.raw_keystrokes[0].time_since_previous == -1

        # Also check net keystrokes
        assert collection.get_net_count() == 1
        assert collection.net_keystrokes[0].time_since_previous == -1

    def test_single_keystroke_deleted_timing(self):
        """Test timing when a single keystroke is deleted leaving none remaining."""

        collection = KeystrokeCollection()
        base_time = datetime.now()

        # Add a character
        char_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=base_time,
        )
        collection.add_keystroke(char_keystroke)

        # Add a backspace after random delay (50-200ms)
        delay_ms = random.randint(50, 200)
        backspace_time = base_time + timedelta(milliseconds=delay_ms)

        backspace_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=1,
            keystroke_time=backspace_time,
        )
        collection.add_keystroke(backspace_keystroke)

        # Raw keystrokes should have both with correct timing
        assert collection.get_raw_count() == 2
        assert collection.raw_keystrokes[0].time_since_previous == -1
        assert collection.raw_keystrokes[1].time_since_previous == delay_ms

        # Net keystrokes should be empty (character was deleted)
        assert collection.get_net_count() == 0
        assert len(collection.net_keystrokes) == 0

    def test_character_delete_replace_timing(self):
        """Test timing for sequence: a, a, backspace, b with random delays."""
        collection = KeystrokeCollection()
        base_time = datetime.now()
        current_time = base_time

        # Define random delays between keystrokes (50-200ms)
        delays = [random.randint(50, 200) for _ in range(3)]

        # First 'a'
        first_a = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=current_time,
        )
        collection.add_keystroke(first_a)

        # Second 'a' (after delay)
        current_time += timedelta(milliseconds=delays[0])
        second_a = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=1,
            keystroke_time=current_time,
        )
        collection.add_keystroke(second_a)

        # Backspace (after delay)
        current_time += timedelta(milliseconds=delays[1])
        backspace = Keystroke(
            session_id="test-session",
            keystroke_char="\b",
            expected_char="",
            key_index=2,
            keystroke_time=current_time,
        )
        collection.add_keystroke(backspace)

        # 'b' (after delay)
        current_time += timedelta(milliseconds=delays[2])
        b_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="b",
            expected_char="b",
            key_index=3,
            keystroke_time=current_time,
        )
        collection.add_keystroke(b_keystroke)

        # Validate raw keystrokes timing
        assert collection.get_raw_count() == 4
        assert collection.raw_keystrokes[0].time_since_previous == -1  # First keystroke
        assert collection.raw_keystrokes[1].time_since_previous == delays[0]  # Second 'a'
        assert collection.raw_keystrokes[2].time_since_previous == delays[1]  # Backspace
        assert collection.raw_keystrokes[3].time_since_previous == delays[2]  # 'b'

        # Validate net keystrokes timing (should be: first 'a', then 'b')
        assert collection.get_net_count() == 2
        assert collection.net_keystrokes[0].time_since_previous == -1  # First 'a'
        # 'b' should have timing relative to the first 'a' (sum of all delays)
        expected_b_timing = sum(delays)
        # Expected timing = (time_b - time_a) * 1000 = (1.0 - 0.5) * 1000 = 500ms

        # confirm that the timing in the net keystrokes is correct - should equal all the delays
        assert collection.net_keystrokes[1].time_since_previous == expected_b_timing

        # confirm that the timing in the net keystrokes is correct - should equal the difference
        # between the first and last keystroke times
        start_time = collection.net_keystrokes[0].keystroke_time
        end_time: datetime = collection.net_keystrokes[1].keystroke_time
        assert (end_time - start_time).total_seconds() * 1000 == expected_b_timing

    def test_multiple_characters_with_random_timing(self):
        """Test timing calculations with multiple characters and random delays."""
        collection = KeystrokeCollection()
        base_time = datetime.now()
        current_time = base_time

        characters = ["h", "e", "l", "l", "o"]
        delays = [random.randint(50, 200) for _ in range(len(characters) - 1)]

        # Add first character
        first_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char=characters[0],
            expected_char=characters[0],
            key_index=0,
            keystroke_time=current_time,
        )
        collection.add_keystroke(first_keystroke)

        # Add remaining characters with delays
        for i, char in enumerate(characters[1:], 1):
            current_time += timedelta(milliseconds=delays[i - 1])
            keystroke = Keystroke(
                session_id="test-session",
                keystroke_char=char,
                expected_char=char,
                key_index=i,
                keystroke_time=current_time,
            )
            collection.add_keystroke(keystroke)

        # Validate timing calculations
        assert collection.get_raw_count() == len(characters)
        assert collection.get_net_count() == len(characters)

        # First keystroke should have -1
        assert collection.raw_keystrokes[0].time_since_previous == -1
        assert collection.net_keystrokes[0].time_since_previous == -1

        # Subsequent keystrokes should have correct delays
        for i, expected_delay in enumerate(delays, 1):
            assert collection.raw_keystrokes[i].time_since_previous == expected_delay
            assert collection.net_keystrokes[i].time_since_previous == expected_delay

    def test_timing_with_multiple_backspaces(self):
        """Test timing calculations when multiple consecutive backspaces are used."""
        collection = KeystrokeCollection()
        base_time = datetime.now()
        current_time = base_time

        # Type 'abc'
        chars = ["a", "b", "c"]
        delays = []

        for i, char in enumerate(chars):
            if i > 0:
                delay = random.randint(50, 200)
                delays.append(delay)
                current_time += timedelta(milliseconds=delay)

            keystroke = Keystroke(
                session_id="test-session",
                keystroke_char=char,
                expected_char=char,
                key_index=i,
                keystroke_time=current_time,
            )
            collection.add_keystroke(keystroke)

        # Add two backspaces
        backspace_delays = []
        for i in range(2):
            delay = random.randint(50, 200)
            backspace_delays.append(delay)
            current_time += timedelta(milliseconds=delay)

            backspace = Keystroke(
                session_id="test-session",
                keystroke_char="\b",
                expected_char="",
                key_index=len(chars) + i,
                keystroke_time=current_time,
            )
            collection.add_keystroke(backspace)

        # Raw keystrokes: all 5 keystrokes (a, b, c, backspace, backspace)
        assert collection.get_raw_count() == 5
        assert collection.raw_keystrokes[0].time_since_previous == -1
        assert collection.raw_keystrokes[1].time_since_previous == delays[0]
        assert collection.raw_keystrokes[2].time_since_previous == delays[1]
        assert collection.raw_keystrokes[3].time_since_previous == backspace_delays[0]
        assert collection.raw_keystrokes[4].time_since_previous == backspace_delays[1]

        # Net keystrokes: only 'a' remains (backspaces removed 'b' and 'c')
        assert collection.get_net_count() == 1
        assert collection.net_keystrokes[0].time_since_previous == -1

    def test_timing_precision_milliseconds(self):
        """Test that timing calculations are properly converted to milliseconds."""
        collection = KeystrokeCollection()
        base_time = datetime.now()

        # Create keystrokes with precise timing
        first_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=base_time,
        )
        collection.add_keystroke(first_keystroke)

        # Second keystroke exactly 150.5 milliseconds later
        precise_delay = 150.5
        second_time = base_time + timedelta(milliseconds=precise_delay)
        second_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="b",
            expected_char="b",
            key_index=1,
            keystroke_time=second_time,
        )
        collection.add_keystroke(second_keystroke)

        # Should be rounded down to 150ms (int conversion)
        expected_ms = int(precise_delay)
        assert collection.raw_keystrokes[1].time_since_previous == expected_ms
        assert collection.net_keystrokes[1].time_since_previous == expected_ms

    def test_timing_edge_case_same_timestamp(self):
        """Test timing calculation when keystrokes have identical timestamps."""
        collection = KeystrokeCollection()
        same_time = datetime.now()

        # Two keystrokes at exactly the same time
        first_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=same_time,
        )
        collection.add_keystroke(first_keystroke)

        second_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="b",
            expected_char="b",
            key_index=1,
            keystroke_time=same_time,  # Same timestamp
        )
        collection.add_keystroke(second_keystroke)

        # Time difference should be 0
        assert collection.raw_keystrokes[0].time_since_previous == -1
        assert collection.raw_keystrokes[1].time_since_previous == 0
        assert collection.net_keystrokes[1].time_since_previous == 0

    def test_timing_after_clear(self):
        """Test that timing resets properly after clearing the collection."""
        collection = KeystrokeCollection()
        base_time = datetime.now()

        # Add some keystrokes
        first_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="a",
            expected_char="a",
            key_index=0,
            keystroke_time=base_time,
        )
        collection.add_keystroke(first_keystroke)

        delay = random.randint(50, 200)
        second_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="b",
            expected_char="b",
            key_index=1,
            keystroke_time=base_time + timedelta(milliseconds=delay),
        )
        collection.add_keystroke(second_keystroke)

        # Clear the collection
        collection.clear()

        # Add new keystroke after clear
        new_time = datetime.now()
        new_keystroke = Keystroke(
            session_id="test-session",
            keystroke_char="x",
            expected_char="x",
            key_index=0,
            keystroke_time=new_time,
        )
        collection.add_keystroke(new_keystroke)

        # Should reset to -1 (no previous keystroke)
        assert collection.get_raw_count() == 1
        assert collection.raw_keystrokes[0].time_since_previous == -1
        assert collection.net_keystrokes[0].time_since_previous == -1
