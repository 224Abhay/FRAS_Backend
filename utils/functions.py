from datetime import datetime

def get_weekday_name(weekday_number):
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return days_of_week[weekday_number - 1]

def convert_flutter_to_mysql_time(date):
    return datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")