import datetime

def get_ist_now():
    """Returns the current naive datetime in IST (UTC+5:30)."""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

if __name__ == "__main__":
    utc_now = datetime.datetime.utcnow()
    ist_now = get_ist_now()
    
    print(f"Server UTC Time:  {utc_now}")
    print(f"Server UTC Date:  {utc_now.strftime('%Y-%m-%d')}")
    print("-" * 30)
    print(f"Target IST Time:  {ist_now}")
    print(f"Target IST Date:  {ist_now.strftime('%Y-%m-%d')}")
