import csv
import timedinput
import time
from datetime import datetime, date
import schedule
import smtplib
from email.message import EmailMessage
import os
import config

CSV_FILE_NAME = "attendance.csv"


def setup_csv():
    # Overwrite the existing CSV file with a new one including headers
    with open(CSV_FILE_NAME, mode="w", encoding="UTF8") as f:
        writer = csv.writer(f)
        writer.writerow(["Badge ID", "Badge Swipe Time"])


def send_email():
    msg = EmailMessage()
    with open(CSV_FILE_NAME, mode="r", encoding="UTF8") as f:
        msg.set_content(f.read())
        msg["Subject"] = config.email_subject + date.today().strftime(
            " (%A, %B %d, %Y)"
        )
        msg["From"] = config.from_email
        msg["To"] = ", ".join(config.to_emails)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
        smtp_server.login(config.from_email, config.password)
        smtp_server.sendmail(config.from_email, config.to_emails, msg.as_string())

    os.remove(CSV_FILE_NAME)


# Schedule the CSV file setup
schedule.every().monday.at(config.open_time).do(setup_csv)
schedule.every().tuesday.at(config.open_time).do(setup_csv)
schedule.every().wednesday.at(config.open_time).do(setup_csv)
schedule.every().thursday.at(config.open_time).do(setup_csv)
schedule.every().friday.at(config.open_time).do(setup_csv)

# Schedule the email
schedule.every().monday.at(config.close_time).do(send_email)
schedule.every().tuesday.at(config.close_time).do(send_email)
schedule.every().wednesday.at(config.close_time).do(send_email)
schedule.every().thursday.at(config.close_time).do(send_email)
schedule.every().friday.at(config.close_time).do(send_email)

while True:
    now = datetime.now()
    today_open_time = now.replace(
        hour=int(config.open_time.split(":")[0]),
        minute=int(config.open_time.split(":")[1]),
        second=0,
        microsecond=0,
    )
    today_close_time = now.replace(
        hour=int(config.close_time.split(":")[0]),
        minute=int(config.close_time.split(":")[1]),
        second=0,
        microsecond=0,
    )

    if now > today_open_time and now < today_close_time:  # If accepting swipes
        card_info = timedinput("Swipe your badge: ", timeout=config.swipe_timeout)
        print(f"Here's what I got: {card_info}")
        badge_id = card_info.split("=")[1]
        ts_str = datetime.now().__str__()

        # Write to the CSV file
        with open(CSV_FILE_NAME, mode="a", encoding="UTF8") as f:
            writer = csv.writer(f)
            writer.writerow([badge_id, ts_str])
    else:  # If not accepting swipes
        schedule.run_pending()
        time.sleep(1800)  # Pause for 30 minutes
