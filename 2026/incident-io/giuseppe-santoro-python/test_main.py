import json
import pytest
from datetime import datetime
from dateutil import parser as date_parser

from main import _flatten, load_data, process_schedule, write_output_json, _validate_entries
from models import ScheduleEntry


# Test for requirement 1: Check that schedule entries do not overlap
class TestScheduleEntriesDoNotOverlap:
    def test_should_throw_error_for_overlapping_schedule_entries(self):
        """Guards against two engineers scheduled at the same time.
        Without this check the output would silently assign two people to the same window."""
        overlapping_schedule = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 17, 0, 0)
            ),
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 16, 0, 0),  # Overlaps with previous entry
                end_at=datetime(2024, 1, 1, 20, 0, 0)
            )
        ]
        
        with pytest.raises(ValueError):
            process_schedule(overlapping_schedule, [])
    
    def test_should_not_throw_error_for_non_overlapping_schedule_entries(self):
        """Confirms back-to-back shifts (end == next start) are valid.
        This is the normal case and must not be rejected as an overlap."""
        non_overlapping_schedule = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 17, 0, 0)
            ),
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 17, 0, 0),  # Starts when previous ends
                end_at=datetime(2024, 1, 1, 20, 0, 0)
            )
        ]
        
        # Should not raise any exception
        process_schedule(non_overlapping_schedule, [])


# Test for requirement 2: Check that there are no gaps in the schedule
class TestNoGapsInSchedule:
    def test_should_throw_error_for_schedule_with_gaps(self):
        """Guards against periods where nobody is on-call.
        A gap means the pager has no owner, which is the core failure mode the spec forbids."""
        schedule_with_gaps = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 17, 0, 0)
            ),
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 18, 0, 0),  # 1 hour gap
                end_at=datetime(2024, 1, 1, 20, 0, 0)
            )
        ]
        
        with pytest.raises(ValueError):
            process_schedule(schedule_with_gaps, [])
    
    def test_should_not_throw_error_for_schedule_without_gaps(self):
        """Confirms that a perfectly continuous schedule is accepted without error.
        The happy path must not be rejected by the gap check."""
        schedule_without_gaps = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 17, 0, 0)
            ),
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 17, 0, 0),  # No gap
                end_at=datetime(2024, 1, 1, 20, 0, 0)
            )
        ]
        
        # Should not raise any exception
        process_schedule(schedule_without_gaps, [])


# Test for requirement 3: Check that override entries do not overlap
class TestOverrideEntriesDoNotOverlap:
    def test_should_throw_error_for_overlapping_override_entries(self):
        """Guards against two overrides claiming the same window.
        If allowed, it would be ambiguous who is actually on-call during the overlap."""
        overlapping_overrides = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 12, 0, 0),
                end_at=datetime(2024, 1, 1, 15, 0, 0)
            ),
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 14, 0, 0),  # Overlaps with previous
                end_at=datetime(2024, 1, 1, 17, 0, 0)
            )
        ]
        
        valid_schedule = [
            ScheduleEntry(
                user_id='3',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 20, 0, 0)
            )
        ]
        
        with pytest.raises(ValueError):
            process_schedule(valid_schedule, overlapping_overrides)
    
    def test_should_not_throw_error_for_non_overlapping_override_entries(self):
        """Confirms overrides with a gap between them are valid.
        Unlike the base schedule, overrides don't need to be contiguous."""
        non_overlapping_overrides = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 12, 0, 0),
                end_at=datetime(2024, 1, 1, 15, 0, 0)
            ),
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 16, 0, 0),  # No overlap
                end_at=datetime(2024, 1, 1, 18, 0, 0)
            )
        ]
        
        valid_schedule = [
            ScheduleEntry(
                user_id='3',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 20, 0, 0)
            )
        ]
        
        # Should not raise any exception
        process_schedule(valid_schedule, non_overlapping_overrides)


# Edge cases: empty, single entry, two entries, unsorted input
class TestEdgeCases:
    def test_empty_schedule_and_overrides(self):
        """Guards against a crash on empty input; the script should handle a no-op gracefully."""
        process_schedule([], [])

    def test_single_schedule_entry(self):
        """Confirms the minimum valid schedule works.
        A single entry has no neighbours to compare, so loop boundary conditions must be handled correctly."""
        process_schedule([
            ScheduleEntry(user_id='1', start_at=datetime(2024, 1, 1, 9, 0, 0), end_at=datetime(2024, 1, 1, 17, 0, 0))
        ], [])

    def test_single_override_entry(self):
        """Confirms one override inside one schedule entry works end-to-end.
        The simplest non-trivial case for the flatten path."""
        process_schedule([
            ScheduleEntry(user_id='1', start_at=datetime(2024, 1, 1, 9, 0, 0), end_at=datetime(2024, 1, 1, 17, 0, 0))
        ], [
            ScheduleEntry(user_id='2', start_at=datetime(2024, 1, 1, 12, 0, 0), end_at=datetime(2024, 1, 1, 14, 0, 0))
        ])

    def test_unsorted_valid_schedule_entries_do_not_raise(self):
        """Confirms the script sorts before validating, so callers don't need to pre-sort input."""
        # Entries given in reverse order — sort must happen before validation
        process_schedule([
            ScheduleEntry(user_id='2', start_at=datetime(2024, 1, 1, 17, 0, 0), end_at=datetime(2024, 1, 1, 20, 0, 0)),
            ScheduleEntry(user_id='1', start_at=datetime(2024, 1, 1, 9, 0, 0), end_at=datetime(2024, 1, 1, 17, 0, 0)),
        ], [])

    def test_unsorted_overlapping_schedule_entries_still_detected(self):
        """Confirms sorting first doesn't hide a real overlap — after sorting, validation must still catch it."""
        # Entries given in reverse order but overlap exists — must still raise
        with pytest.raises(ValueError):
            process_schedule([
                ScheduleEntry(user_id='2', start_at=datetime(2024, 1, 1, 16, 0, 0), end_at=datetime(2024, 1, 1, 20, 0, 0)),
                ScheduleEntry(user_id='1', start_at=datetime(2024, 1, 1, 9, 0, 0), end_at=datetime(2024, 1, 1, 17, 0, 0)),
            ], [])

    def test_unsorted_overlapping_override_entries_still_detected(self):
        """Same as the schedule overlap case but for overrides — sort + validate must apply to both lists."""
        with pytest.raises(ValueError):
            process_schedule([
                ScheduleEntry(user_id='3', start_at=datetime(2024, 1, 1, 9, 0, 0), end_at=datetime(2024, 1, 1, 20, 0, 0))
            ], [
                ScheduleEntry(user_id='2', start_at=datetime(2024, 1, 1, 14, 0, 0), end_at=datetime(2024, 1, 1, 17, 0, 0)),
                ScheduleEntry(user_id='1', start_at=datetime(2024, 1, 1, 12, 0, 0), end_at=datetime(2024, 1, 1, 15, 0, 0)),
            ])


# Functional test: full pipeline against real input.json / output.json
class TestFunctional:
    def test_output_is_valid_contiguous_timeline(self):
        """End-to-end: load input.json, process, then validate every entry in the result."""
        schedule_data = load_data("input.json")
        result = process_schedule(schedule_data.schedule_entries, schedule_data.override_entries)

        # Every entry must have a positive duration
        for entry in result:
            assert entry.start_at < entry.end_at, (
                f"Invalid entry for user {entry.user_id}: "
                f"start {entry.start_at} is not before end {entry.end_at}"
            )

        # Result must be gapless and overlap-free — reuse the same validation logic
        sorted_result = sorted(result, key=lambda e: e.start_at)
        _validate_entries(sorted_result, "output", check_gaps=True)

        # Result must span exactly the same window as the original schedule
        sorted_schedule = sorted(schedule_data.schedule_entries, key=lambda e: e.start_at)
        assert sorted_result[0].start_at == sorted_schedule[0].start_at, "Output starts too late"
        assert sorted_result[-1].end_at == sorted_schedule[-1].end_at, "Output ends too early"


# Test for requirement 4: Flatten schedule and overrides into single list
class TestFlattenScheduleAndOverrides:
    def test_should_correctly_flatten_schedule_and_overrides_into_single_list(self):
        """Core correctness test for requirement 4: one override in the middle of a shift must produce
        three segments — schedule prefix, override window, schedule suffix."""
        schedule_entries = [
            ScheduleEntry(
                user_id='1',
                start_at=datetime(2024, 1, 1, 9, 0, 0),
                end_at=datetime(2024, 1, 1, 17, 0, 0)
            )
        ]
        
        override_entries = [
            ScheduleEntry(
                user_id='2',
                start_at=datetime(2024, 1, 1, 12, 0, 0),
                end_at=datetime(2024, 1, 1, 14, 0, 0)
            )
        ]
        
        result = process_schedule(schedule_entries, override_entries)
        
        # Expected result: 3 entries
        # 1. User 1: 9:00-12:00 (original schedule before override)
        # 2. User 2: 12:00-14:00 (override period)
        # 3. User 1: 14:00-17:00 (original schedule after override)
        assert len(result) == 3
        
        expected_slots = [
            {'user_id': '1', 'start_at': datetime(2024, 1, 1, 9, 0, 0), 'end_at': datetime(2024, 1, 1, 12, 0, 0)},
            {'user_id': '2', 'start_at': datetime(2024, 1, 1, 12, 0, 0), 'end_at': datetime(2024, 1, 1, 14, 0, 0)},
            {'user_id': '1', 'start_at': datetime(2024, 1, 1, 14, 0, 0), 'end_at': datetime(2024, 1, 1, 17, 0, 0)}
        ]
        
        # Check that each expected entry exists in the result
        for expected in expected_slots:
            found = False
            for entry in result:
                if (entry.user_id == expected['user_id'] and
                    entry.start_at == expected['start_at'] and
                    entry.end_at == expected['end_at']):
                    found = True
                    break
            
            if not found:
                # Build useful error message showing actual vs expected
                actual_entries = '\n'.join([
                    f"User {entry.user_id}: {entry.start_at.isoformat()} → {entry.end_at.isoformat()}"
                    for entry in result
                ])
                
                expected_entry = f"User {expected['user_id']}: {expected['start_at'].isoformat()} → {expected['end_at'].isoformat()}"
                
                raise AssertionError(f"Expected to find entry: {expected_entry}\n\nActual entries found:\n{actual_entries}")


# Unit tests for _flatten directly
class TestFlatten:
    def test_no_overrides_returns_schedule_unchanged(self):
        """Baseline: with no overrides, _flatten must return the schedule exactly as given — no entries added or dropped."""
        schedule = [
            ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 12, 0, 0)),
            ScheduleEntry('2', datetime(2024, 1, 1, 12, 0, 0), datetime(2024, 1, 1, 17, 0, 0)),
        ]
        result = _flatten(schedule, [])
        assert len(result) == 2
        assert result[0].user_id == '1'
        assert result[1].user_id == '2'

    def test_override_at_start_of_schedule_entry(self):
        """Verifies no empty prefix is emitted when the override starts exactly when the schedule entry does."""
        schedule = [ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 17, 0, 0))]
        overrides = [ScheduleEntry('2', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 12, 0, 0))]
        result = _flatten(schedule, overrides)
        assert len(result) == 2
        assert result[0].user_id == '2'
        assert result[0].start_at == datetime(2024, 1, 1, 9, 0, 0)
        assert result[0].end_at == datetime(2024, 1, 1, 12, 0, 0)
        assert result[1].user_id == '1'
        assert result[1].start_at == datetime(2024, 1, 1, 12, 0, 0)
        assert result[1].end_at == datetime(2024, 1, 1, 17, 0, 0)

    def test_override_at_end_of_schedule_entry(self):
        """Verifies no empty suffix is emitted when the override ends exactly when the schedule entry does."""
        schedule = [ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 17, 0, 0))]
        overrides = [ScheduleEntry('2', datetime(2024, 1, 1, 14, 0, 0), datetime(2024, 1, 1, 17, 0, 0))]
        result = _flatten(schedule, overrides)
        assert len(result) == 2
        assert result[0].user_id == '1'
        assert result[0].end_at == datetime(2024, 1, 1, 14, 0, 0)
        assert result[1].user_id == '2'
        assert result[1].start_at == datetime(2024, 1, 1, 14, 0, 0)
        assert result[1].end_at == datetime(2024, 1, 1, 17, 0, 0)

    def test_override_exactly_matches_schedule_entry(self):
        """When an override covers the entire entry, only one entry (the override) should appear — no zero-length prefix or suffix."""
        schedule = [ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 17, 0, 0))]
        overrides = [ScheduleEntry('2', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 17, 0, 0))]
        result = _flatten(schedule, overrides)
        assert len(result) == 1
        assert result[0].user_id == '2'

    def test_override_spans_multiple_schedule_entries(self):
        """The override crosses an entry boundary; the algorithm must consume entries without duplicating or dropping coverage."""
        schedule = [
            ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 17, 0, 0)),
            ScheduleEntry('2', datetime(2024, 1, 1, 17, 0, 0), datetime(2024, 1, 1, 23, 0, 0)),
        ]
        overrides = [ScheduleEntry('3', datetime(2024, 1, 1, 15, 0, 0), datetime(2024, 1, 1, 20, 0, 0))]
        result = _flatten(schedule, overrides)
        # user1 9–15, user3 15–20, user2 20–23
        assert len(result) == 3
        assert result[0].user_id == '1'
        assert result[0].end_at == datetime(2024, 1, 1, 15, 0, 0)
        assert result[1].user_id == '3'
        assert result[1].start_at == datetime(2024, 1, 1, 15, 0, 0)
        assert result[1].end_at == datetime(2024, 1, 1, 20, 0, 0)
        assert result[2].user_id == '2'
        assert result[2].start_at == datetime(2024, 1, 1, 20, 0, 0)
        assert result[2].end_at == datetime(2024, 1, 1, 23, 0, 0)

    def test_multiple_non_adjacent_overrides(self):
        """Two overrides with a gap between them; the schedule user must appear three times — before, between, and after."""
        schedule = [ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 20, 0, 0))]
        overrides = [
            ScheduleEntry('2', datetime(2024, 1, 1, 11, 0, 0), datetime(2024, 1, 1, 13, 0, 0)),
            ScheduleEntry('3', datetime(2024, 1, 1, 15, 0, 0), datetime(2024, 1, 1, 17, 0, 0)),
        ]
        result = _flatten(schedule, overrides)
        # user1 9–11, user2 11–13, user1 13–15, user3 15–17, user1 17–20
        assert len(result) == 5
        assert result[0].user_id == '1'
        assert result[0].end_at == datetime(2024, 1, 1, 11, 0, 0)
        assert result[1].user_id == '2'
        assert result[2].user_id == '1'
        assert result[2].start_at == datetime(2024, 1, 1, 13, 0, 0)
        assert result[2].end_at == datetime(2024, 1, 1, 15, 0, 0)
        assert result[3].user_id == '3'
        assert result[4].user_id == '1'
        assert result[4].start_at == datetime(2024, 1, 1, 17, 0, 0)
        assert result[4].end_at == datetime(2024, 1, 1, 20, 0, 0)


# Unit tests for load_data
class TestLoadData:
    def test_loads_schedule_and_override_counts_from_input_json(self):
        """Confirms the parser reads the correct number of entries; guards against silent truncation or duplication."""
        data = load_data("input.json")
        assert len(data.schedule_entries) == 9
        assert len(data.override_entries) == 4

    def test_parses_first_schedule_entry_correctly(self):
        """Spot-checks that user_id, start_at, and end_at are mapped to the right fields from the JSON structure."""
        data = load_data("input.json")
        first = data.schedule_entries[0]
        assert first.user_id == "1"
        assert first.start_at == date_parser.isoparse("2024-11-02T16:00:00Z")
        assert first.end_at == date_parser.isoparse("2024-11-09T16:00:00Z")

    def test_parses_dates_as_datetime_objects(self):
        """Ensures dates are parsed into datetime objects, not left as strings — downstream code relies on datetime comparison operators."""
        data = load_data("input.json")
        assert isinstance(data.schedule_entries[0].start_at, datetime)
        assert isinstance(data.override_entries[0].start_at, datetime)


# Unit tests for write_output_json
class TestWriteOutputJson:
    def test_writes_entries_as_json_to_output_file(self, tmp_path, monkeypatch):
        """Confirms the output file is valid JSON with the expected structure and ISO 8601 date format.
        Uses tmp_path to avoid overwriting the real output.json."""
        monkeypatch.chdir(tmp_path)
        entries = [ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 17, 0, 0))]
        write_output_json(entries)
        with open('output.json') as f:
            data = json.load(f)
        assert data['entries'][0]['user_id'] == '1'
        assert data['entries'][0]['start_at'] == '2024-01-01T09:00:00Z'
        assert data['entries'][0]['end_at'] == '2024-01-01T17:00:00Z'

    def test_writes_multiple_entries_in_order(self, tmp_path, monkeypatch):
        """Confirms multiple entries are written in the same order they were passed in, preserving the chronological sequence."""
        monkeypatch.chdir(tmp_path)
        entries = [
            ScheduleEntry('1', datetime(2024, 1, 1, 9, 0, 0), datetime(2024, 1, 1, 12, 0, 0)),
            ScheduleEntry('2', datetime(2024, 1, 1, 12, 0, 0), datetime(2024, 1, 1, 17, 0, 0)),
        ]
        write_output_json(entries)
        with open('output.json') as f:
            data = json.load(f)
        assert len(data['entries']) == 2
        assert data['entries'][0]['user_id'] == '1'
        assert data['entries'][1]['user_id'] == '2'