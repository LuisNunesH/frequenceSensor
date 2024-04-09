from datetime import datetime, timedelta

start_time = datetime.now()
end_time = start_time + timedelta(seconds=600)
print(end_time)