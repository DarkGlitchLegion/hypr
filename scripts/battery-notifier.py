from datetime import datetime
import os
import time
import psutil
import requests
from dotenv import load_dotenv

load_dotenv()

SMS_URL = os.getenv("SMS_URL")
SMS_APP_KEY = os.getenv("SMS_APP_KEY")
SMS_APP_SECRET = os.getenv("SMS_APP_SECRET")
SMS_MSISDN = os.getenv("SMS_MSISDN")
SMS_SHORTCODE_MASK = os.getenv("SMS_SHORTCODE_MASK")
SMS_RCVD_TRANSID = os.getenv("SMS_RCVD_TRANSID")
SMS_INTL = os.getenv("SMS_INTL")

LOW_THRESHOLD = 20
FULL_THRESHOLD = 99
CHECK_INTERVAL = 60

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_alert(message):
    url = SMS_URL
    payload = {
        "app_key": SMS_APP_KEY,
        "app_secret": SMS_APP_SECRET,
        "msisdn": SMS_MSISDN,
        "shortcode_mask": SMS_SHORTCODE_MASK,
        "rcvd_transid": SMS_RCVD_TRANSID,
        "message": message,
        "intl": SMS_INTL
    }
    response = requests.post(url, json=payload)
    print(f"[{timestamp()}] {message} - SMS sent with status code: {response.status_code}")

def check_battery():
    low_alerted = False
    full_alerted = False

    try:
        while True:
            battery = psutil.sensors_battery()
            if battery is None:
                print_alert("No battery information available.")
                break

            percent = battery.percent
            plugged = battery.power_plugged
            status = "Charging" if plugged else "Discharging"

            print(f"[{timestamp()}] Battery: {percent}% - {status}")

            if not plugged and percent <= LOW_THRESHOLD and not low_alerted:
                print_alert(f"Low battery alert! Battery is at {percent}%. Please plug in your charger.")
                low_alerted = True
            elif plugged or percent > LOW_THRESHOLD:
                low_alerted = False
            
            if plugged and percent >= FULL_THRESHOLD and not full_alerted:
                print_alert(f"Battery is fully charged at {percent}%. You can unplug the charger.")
                full_alerted = True
            elif not plugged or percent < FULL_THRESHOLD:
                full_alerted = False

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print_alert("Battery notifier stopped by user.")

if __name__ == "__main__":
    check_battery()