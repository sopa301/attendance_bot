from datetime import datetime
from zoneinfo import ZoneInfo
from util.objects import Status

# format for date_time eg: day/month/year,hour:minute
def parse_dt_to_iso(date_time: str, status: Status) -> str: 
  curr_date = datetime.today()

  dt = date_time.strip().split(",")

  if len(dt) != 2:
    status.set_message("Invalid format")
    return ""
  
  date = dt[0].strip().split("/")
  timings = dt[1].strip().split("-")

  if len(date) < 3:
    # invalid format
    status.set_message("Missing date fields")
    return "" 
  
  if len(timings) < 2: 
    status.set_message("Missing time fields")
    return "" 

  try:
    day = int(date[0])
    month = int(date[1])
    year = int(date[2])
    [start_HH, start_MM] = timings[0].strip().split(":")
    [end_HH, end_MM] = timings[1].strip().split(":") 

    start_HH = int(start_HH)
    start_MM = int(start_MM)
    end_HH = int(end_HH)
    end_MM = int(end_MM)

    start_date = datetime(year, month, day, start_HH, start_MM)
    end_date = datetime(year, month, day, start_HH, start_MM)


    if start_date < curr_date:
      status.set_message("Input date has passed. Please give another date")
      return "" 
    
    if start_date > end_date:
      status.set_message("End timing cannot be before start timing. Please give valid time")

    status.set_success()
    return (start_date.isoformat(), end_date.isoformat())

  except ValueError as e:
    status.set_message("Invalid date time input.\n1. Check if you added additional symbols.\n2. Check if day or month is valid.")
    return "" 


def compare_time(time1: str, time2: str) -> int:
  t1 = datetime.fromisoformat(time1)
  t2 = datetime.fromisoformat(time2)

  if t1 < t2:
    return -1
  elif t1 == t2:
    return 0
  else:
    return 1

