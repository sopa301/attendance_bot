"""Helper functions for date and time formatting, parsing and comparison."""

from datetime import datetime
from typing import List

from .status import Status


# format for date_time eg: day/month/year,hour:minute
def parse_dt_to_iso(date_time: str, status: Status) -> str:
    """
    Parses a date time string to ISO format and populates status object.
    """
    curr_date = datetime.today()

    dt = date_time.strip().split(",")

    if len(dt) != 2:
        status.set_message("Invalid format")
        return ""

    date = dt[0].strip().split("/")
    time = dt[1].strip().split(":")

    if len(date) < 3:
        # invalid format
        status.set_message("Missing date fields")
        return ""

    if len(time) < 2:
        status.set_message("Missing time fields")
        return ""

    try:
        day = int(date[0])
        month = int(date[1])
        year = int(date[2])
        hour = int(time[0])
        minute = int(time[1])

        input_date = datetime.strptime(
            f"{day}/{month}/{year},{hour}:{minute}", "%d/%m/%Y,%H:%M"
        )

        if input_date < curr_date:
            status.set_message("Input date has passed. Please give another date")
            return ""

        status.set_success()
        return input_date.isoformat()

    except ValueError:
        status.set_message(
            "Invalid date time input.\n1. Check if you added additional symbols.\n"
            "2. Check if day or month is valid."
        )
        return ""


def compare_time(time1: str, time2: str) -> int:
    """
    Compares two ISO formatted time strings.
    """
    t1 = datetime.fromisoformat(time1)
    t2 = datetime.fromisoformat(time2)

    if t1 < t2:
        return -1
    if t1 == t2:
        return 0
    return 1


def format_dt_string(iso_dt: str) -> List[str]:
    """Formats date time in DD/MM/YYYY and h:mma format from ISO format."""
    # Parse datetime
    dt = datetime.strptime(iso_dt, "%Y-%m-%dT%H:%M:%S")

    # Format date
    date = dt.strftime("%a, %d/%m/%Y")

    # Format time in 12-hour format, then manually remove leading zero
    hour = dt.strftime("%I").lstrip("0")  # hour without leading zero
    minute = dt.strftime("%M")
    ampm = dt.strftime("%p").lower()
    time = f"{hour}:{minute}{ampm}"

    return date, time
