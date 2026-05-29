import json
from dateutil import parser
from typing import List

from models import ScheduleEntry, ScheduleData


def run_script() -> None:
    schedule_data = load_data("input.json")
    
    processed_schedule = process_schedule(schedule_data.schedule_entries, schedule_data.override_entries)
    
    write_output_json(processed_schedule)


def load_data(input_file: str) -> ScheduleData:
    """Load JSON data from the specified input file and parse it into a ScheduleData object."""
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    schedule_entries = []
    for entry in data['schedule_entries']:
        schedule_entries.append(ScheduleEntry(
            user_id=entry['user_id'],
            start_at=parser.isoparse(entry['start_at']),
            end_at=parser.isoparse(entry['end_at'])
        ))
    
    override_entries = []
    for entry in data['override_entries']:
        override_entries.append(ScheduleEntry(
            user_id=entry['user_id'],
            start_at=parser.isoparse(entry['start_at']),
            end_at=parser.isoparse(entry['end_at'])
        ))
    
    return ScheduleData(schedule_entries, override_entries)


def write_output_json(schedule: List[ScheduleEntry]) -> None:
    """Write the processed schedule entries to a JSON file named 'output.json'."""
    output = {
        'entries': [
            {
                'user_id': entry.user_id,
                'start_at': entry.start_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end_at': entry.end_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            for entry in schedule
        ]
    }
    with open('output.json', 'w') as f:
        json.dump(output, f, indent=2)


def _validate_entries(entries: List[ScheduleEntry], label: str, check_gaps: bool = False) -> None:
    """Raise ValueError if entries overlap, or (when check_gaps=True) if there are gaps between them.

    Expects entries to be sorted by start_at.
    """
    for i in range(1, len(entries)):
        prev = entries[i - 1]
        curr = entries[i]
        if curr.start_at < prev.end_at:
            raise ValueError(
                f"{label} entries overlap: "
                f"user {prev.user_id} ends at {prev.end_at}, "
                f"but user {curr.user_id} starts at {curr.start_at}"
            )
        if check_gaps and curr.start_at > prev.end_at:
            raise ValueError(
                f"Gap in {label}: coverage ends at {prev.end_at}, "
                f"but next entry doesn't start until {curr.start_at}"
            )


def process_schedule(schedule: List[ScheduleEntry], overrides: List[ScheduleEntry]) -> List[ScheduleEntry]:
    """
    Validate schedule and overrides, then flatten into a single on-call timeline.

    Raises ValueError if:
    - schedule entries overlap each other
    - schedule entries have gaps (no one on-call for a period)
    - override entries overlap each other
    """
    # Sort then validate each list in sequence: if schedule is invalid we raise immediately
    # and skip the override sort/validation entirely — no point doing more work on bad input.
    sorted_schedule = sorted(schedule, key=lambda e: e.start_at)
    _validate_entries(sorted_schedule, "schedule", check_gaps=True)

    sorted_overrides = sorted(overrides, key=lambda e: e.start_at)
    _validate_entries(sorted_overrides, "override")

    return _flatten(sorted_schedule, sorted_overrides)


def _flatten(schedule: List[ScheduleEntry], overrides: List[ScheduleEntry]) -> List[ScheduleEntry]:
    """Merge sorted schedule and overrides into a single on-call timeline.

    Assumptions:
    - schedule is continuous: no gaps, no overlaps, covers the full window end-to-end.
    - overrides are sorted and non-overlapping, but may have gaps between them.
    - overrides do NOT need to align with schedule entry boundaries.

    Overrides take full priority: wherever an override exists, it replaces the
    schedule user for that window. Outside overrides, the original schedule user
    is emitted as-is.
    """
    result = []
    s_idx = 0
    o_idx = 0
    # Tracks current position within a schedule entry — starts at entry's start_at,
    # but advances to an override's end_at when overrides consume part of the entry.
    current_start = schedule[0].start_at if schedule else None

    # Main loop: walk schedule entries. Two cases per iteration:
    # 1. No overlap with next override → emit schedule entry as-is, advance schedule.
    # 2. Overlap exists → emit schedule prefix (if any), then emit override,
    #    advance current_start to override's end, skip consumed schedule entries.
    # Schedule is always the fallback; override always wins where they conflict.
    while s_idx < len(schedule):
        s = schedule[s_idx]

        # First: no overrides left — output entry as-is and continue.
        # Second: next override starts after this entry ends — no overlap, same action.
        if o_idx >= len(overrides) or overrides[o_idx].start_at >= s.end_at:
            result.append(ScheduleEntry(s.user_id, current_start, s.end_at))
            s_idx += 1
            # Reset current_start to next entry's beginning.
            # current_start may have been left at an override's end_at — reset it
            # so the next entry is processed from its own start, not a stale pointer.
            if s_idx < len(schedule):
                current_start = schedule[s_idx].start_at
            continue

        o = overrides[o_idx]

        # current_start < o.start_at means a gap or partial overlap before override.
        # Either way, that prefix belongs to the schedule user — emit it as-is.
        if current_start < o.start_at:
            result.append(ScheduleEntry(s.user_id, current_start, o.start_at))

        # Override takes full priority for its duration — emit it regardless of
        # what the schedule says for the same window.
        # Advance current_start to override's end; anything before it is consumed.
        result.append(ScheduleEntry(o.user_id, o.start_at, o.end_at))
        current_start = o.end_at
        o_idx += 1

        # Skip schedule entries fully consumed by the override (end_at <= current_start).
        # Could be zero, one, or many. Stop when an entry extends past current_start
        # — that partial entry is handled in the next loop iteration.
        # Bounds check first to avoid indexing past end of schedule.
        while s_idx < len(schedule) and current_start >= schedule[s_idx].end_at:
            s_idx += 1

    return result


if __name__ == "__main__":
    run_script()