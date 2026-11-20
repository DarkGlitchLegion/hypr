#!/usr/bin/python3

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

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_ID = os.getenv("USER_ID")

LOW_THRESHOLD = 20
FULL_THRESHOLD = 98.9
CHECK_INTERVAL = 60

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_telegram_alert(message):
    if not BOT_TOKEN or not USER_ID:
        print(f"[{timestamp()}] Telegram bot token or user ID not set. Skipping Telegram alert.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": USER_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as exc:
        print(f"[{timestamp()}] Telegram request failed: {exc}")
        return False

    if not response.ok:
        detail = response.text[:500]
        for secret in (BOT_TOKEN, USER_ID):
            if secret:
                detail = detail.replace(secret, "[REDACTED]")
        print(f"[{timestamp()}] Telegram request rejected (HTTP {response.status_code}): {detail}")
        return False

    print(f"[{timestamp()}] Telegram request accepted (HTTP {response.status_code}): {message}")
    return True

def send_sms_alert(message):
    payload = {
        "app_key": SMS_APP_KEY,
        "app_secret": SMS_APP_SECRET,
        "msisdn": f"+{SMS_MSISDN}",
        "shortcode_mask": SMS_SHORTCODE_MASK,
        "rcvd_transid": SMS_RCVD_TRANSID,
        "content": message,
        "intl": SMS_INTL
    }
    try:
        response = requests.post(SMS_URL, json=payload, timeout=10)
    except requests.RequestException as exc:
        print(f"[{timestamp()}] SMS request failed: {exc}")
        return False

    if not response.ok:
        detail = response.text[:500]
        for secret in (SMS_APP_KEY, SMS_APP_SECRET, SMS_MSISDN):
            if secret:
                detail = detail.replace(secret, "[REDACTED]")
        print(f"[{timestamp()}] SMS request rejected (HTTP {response.status_code}): {detail}")
        return False

    print(f"[{timestamp()}] SMS request accepted (HTTP {response.status_code}): {message}")
    return True

def check_battery():
    low_alerted = False
    full_alerted = False

    try:
        while True:
            battery = psutil.sensors_battery()
            if battery is None:
                send_sms_alert("No battery information available.")
                break

            percent = battery.percent
            plugged = battery.power_plugged
            status = "Charging" if plugged else "Discharging"

            print(f"[{timestamp()}] Battery: {percent}% - {status}")

            if not plugged and percent <= LOW_THRESHOLD and not low_alerted:
                low_alerted = send_telegram_alert(
                    f"Low battery alert! Battery is at {percent:.1f}%. Please plug in your charger."
                )
            elif plugged or percent > LOW_THRESHOLD:
                low_alerted = False
            
            if plugged and percent >= FULL_THRESHOLD and not full_alerted:
                full_alerted = send_telegram_alert(
                    f"Battery is fully charged at {percent:.1f}%. You can unplug the charger."
                )
            elif not plugged or percent < FULL_THRESHOLD:
                full_alerted = False

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print(f"[{timestamp()}] Battery notifier stopped by user.")

if __name__ == "__main__":
    check_battery()