import csv
import os
import sys
from termios import tcflush, TCIOFLUSH
from timedinput import timedinput
import time
from datetime import datetime, date
import schedule
import smtplib
from email.message import EmailMessage
import config

CSV_FILE_NAME = "attendance.csv"


def setup_csv_file():
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


# Setup the CSV file on schedule
schedule.every().monday.at(config.open_time).do(setup_csv_file)
schedule.every().tuesday.at(config.open_time).do(setup_csv_file)
schedule.every().wednesday.at(config.open_time).do(setup_csv_file)
schedule.every().thursday.at(config.open_time).do(setup_csv_file)
schedule.every().friday.at(config.open_time).do(setup_csv_file)

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
        tcflush(sys.stdin, TCIOFLUSH)  # Flush stdin before taking new input
        card_info = timedinput(
            "Swipe badge: ", timeout=config.swipe_timeout, default="TIMEOUT"
        )
        if (
            card_info != "TIMEOUT" and card_info.count("=") == 2
        ):  # If the input didn't time out and format basically makes sense
            badge_id = card_info.split("=")[1]
            ts_str = datetime.now().__str__()

            # Ensure the CSV file exists
            if not os.path.exists(CSV_FILE_NAME):
                setup_csv_file()

            # Write to the CSV file
            with open(CSV_FILE_NAME, mode="a", encoding="UTF8") as f:
                writer = csv.writer(f)
                writer.writerow([badge_id, ts_str])
    else:  # If not accepting swipes
        print("Not currently accepting swipes.")
        schedule.run_pending()
        time.sleep(config.swipe_timeout)
