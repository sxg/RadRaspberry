import os
import sys
import pandas as pd
from termios import tcflush, TCIOFLUSH
from timedinput import timedinput
import time
from datetime import datetime, date
import schedule
import resend
import logging
import shutil
import configparser

config = configparser.ConfigParser()
config.read(os.path.expanduser("~/.config/rad_raspberry.ini"))

EXCEL_FILE_NAME = "attendance.xlsx"
BACKUP_EXCEL_FILE_NAME = f"backup-{date.today().strftime('%Y-%m-%d')}.xlsx"

resend.api_key = config["API"]["api_key"]

# Configure logging
logging.basicConfig(
    filename="/var/log/rad_raspberry.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_excel_file():
    # Creates a new Excel file with initial headers
    df = pd.DataFrame(
        columns=["Penn ID", "Badge ID", "All Swipe Data", "Badge Swipe Time"]
    )
    df.to_excel(EXCEL_FILE_NAME, index=False)


def send_email():
    try:
        shutil.copy(
            EXCEL_FILE_NAME, BACKUP_EXCEL_FILE_NAME
        )  # Copy the working attendance file and save it as a backup
        with open(EXCEL_FILE_NAME, mode="rb") as f:
            try:
                buffer = f.read()
                email = resend.Emails.send(
                    {
                        "text": config["Email"]["email_subject"],
                        "from": config["Email"]["from_email"],
                        "to": config["Email"]["to_email"],
                        "subject": f"{config['Email']['email_subject']} {date.today().strftime(' (%A, %B %d, %Y)')}",
                        "attachments": [
                            {
                                "filename": EXCEL_FILE_NAME,
                                "content": list(buffer),
                            }
                        ],
                    }
                )
                logging.info(f"Email sent: {email}")
            except Exception as e:
                logging.error(
                    f"An error occurred in sending an email: {str(e)}"
                )

        # Reset the Excel file
        setup_excel_file()
    except Exception as e:
        logging.error(
            f"An error occurred in backing up the attendance file: {str(e)}"
        )


# Schedule the email
schedule.every().monday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().tuesday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().wednesday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().thursday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().friday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().sunday.at(config["Operation"]["close_time"]).do(send_email)


def main():
    while True:
        now = datetime.now()
        today_open_time = now.replace(
            hour=int(config["Operation"]["open_time"].split(":")[0]),
            minute=int(config["Operation"]["open_time"].split(":")[1]),
            second=0,
            microsecond=0,
        )
        today_close_time = now.replace(
            hour=int(config["Operation"]["close_time"].split(":")[0]),
            minute=int(config["Operation"]["close_time"].split(":")[1]),
            second=0,
            microsecond=0,
        )

        if (
            now > today_open_time and now < today_close_time
        ):  # If accepting swipes
            tcflush(
                sys.stdin, TCIOFLUSH
            )  # Flush stdin before taking new input
            card_info = timedinput(
                "Swipe badge: ",
                timeout=int(config["Operation"]["swipe_timeout"]),
                default="TIMEOUT",
            )
            if (
                card_info != "TIMEOUT"
                and card_info.count("=") == 2
                and len(card_info) > 15
            ):  # If the input didn't time out and format basically makes sense
                penn_id = card_info.split("?")[0].split("%")[1][
                    :-1
                ]  # Remove trailing '0'
                badge_id = card_info.split("=")[1][1:]  # Remove leading '1'
                ts_str = datetime.now().__str__()

                # Ensure the Excel file exists
                if not os.path.exists(EXCEL_FILE_NAME):
                    setup_excel_file()

                # Write to the Excel file
                df = pd.read_excel(EXCEL_FILE_NAME)
                new_row = pd.DataFrame(
                    [[penn_id, badge_id, card_info, ts_str]],
                    columns=[
                        "Penn ID",
                        "Badge ID",
                        "All Swipe Data",
                        "Badge Swipe Time",
                    ],
                )
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_excel(EXCEL_FILE_NAME, index=False)
        else:  # If not accepting swipes
            print("Not currently accepting swipes.")
            schedule.run_pending()
            time.sleep(int(config["Operation"]["swipe_timeout"]))


if __name__ == "__main__":
    main()
