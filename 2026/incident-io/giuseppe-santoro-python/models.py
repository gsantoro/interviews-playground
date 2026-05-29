from datetime import datetime
from typing import List


class ScheduleEntry:
    def __init__(self, user_id: str, start_at: datetime, end_at: datetime):
        self.user_id = user_id
        self.start_at = start_at
        self.end_at = end_at


class ScheduleData:
    def __init__(self, schedule_entries: List[ScheduleEntry], override_entries: List[ScheduleEntry]):
        self.schedule_entries = schedule_entries
        self.override_entries = override_entries