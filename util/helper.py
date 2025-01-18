from datetime import datetime
from zoneinfo import ZoneInfo

# format for date_time eg: day/month,hour:minute
def is_valid_date_time(date_time: str) -> bool: 
  curr_date = datetime.today()
  curr_year = curr_date.year

  dt = date_time.split(",")
  if len(dt) < 2:
    # invalid format
    return False
  
  date = dt[0].split("/")
  time = dt[1].split(":")

  try:
    day = int(date[0])
    month = int(date[1])
    hour = int(time[0])
    minute = int(time[1])

    # more specific error messages  
    if month < 0 or month > 12:
      # print month not in valid range
      return False

    input_date = datetime.strptime(f"{day}/{month}/{curr_year},{hour}:{minute}", "%d/%m/%Y,%H:%M")

  except ValueError as e:
    return False
