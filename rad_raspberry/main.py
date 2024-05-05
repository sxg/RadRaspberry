import os
import sys
import pandas as pd
from termios import tcflush, TCIOFLUSH
from timedinput import timedinput, TimeoutOccurred
import time
from datetime import datetime, date, timedelta
import schedule
import resend
import logging
import shutil
import configparser
from supabase import create_client

# Create folders for logs, backups, and config file if needed
LOG_PATH = os.path.expanduser("~/.local/state/rad_raspberry/log")
BACKUP_PATH = os.path.expanduser("~/.local/state/rad_raspberry/backup")
CONFIG_PATH = os.path.expanduser("~/.config/rad_raspberry")
os.makedirs(LOG_PATH, exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)
os.makedirs(CONFIG_PATH, exist_ok=True)

LOG_FILE_NAME = f"Log {datetime.now().strftime('%Y-%m-%d')}.log"

# Configure logging
logging.basicConfig(
    filename=os.path.join(LOG_PATH, LOG_FILE_NAME),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
schedule_logger = logging.getLogger("schedule")
schedule_logger.setLevel(logging.DEBUG)

# Read the config file
config_file_path = os.path.join(CONFIG_PATH, "config.ini")
config = configparser.ConfigParser()
try:
    config_file = config.read(config_file_path)
    if not config_file:
        raise FileNotFoundError(
            f"Config file not found at path {config_file_path}."
        )
    else:
        logging.debug(
            f"Configuration file at {config_file_path} successfully loaded."
        )
except FileNotFoundError as e:
    logging.error(str(e))
    raise

EXCEL_FILE_NAME = f"{config['Email']['attachment_prefix']} ({datetime.now().strftime('%Y-%m-%d %H-%M-%S)')}.xlsx"
EXCEL_FILE_PATH = os.path.join(BACKUP_PATH, EXCEL_FILE_NAME)
EXCEL_COLUMNS = ["Penn ID", "Badge ID", "All Swipe Data", "Badge Swipe Time"]

SWIPE_TIMEOUT = 60  # Seconds to wait for a swipe

resend.api_key = config["API"]["resend_api_key"]
supabase = create_client(
    config["API"]["supabase_url"], config["API"]["supabase_api_key"]
)
try:
    supabase.auth.sign_in_with_password(
        {
            "email": config["API"]["supabase_username"],
            "password": config["API"]["supabase_password"],
        }
    )
    logging.info(
        f"Signed in to Supabase as {config['API']['supabase_username']}."
    )
except Exception as e:
    logging.error(
        f"Error logging in to Supabase as {config['API']['supabase_username']}: {str(e)}"
    )
    raise


# Creates/overwrites an Excel file with initial headers
def setup_excel_file():
    df = pd.DataFrame(columns=EXCEL_COLUMNS)
    df.to_excel(
        EXCEL_FILE_PATH,
        index=False,
    )
    logging.debug(f"Saved new Excel file at {EXCEL_FILE_PATH}.")


# Save data to the Excel file
def add_row_to_excel_file(data):
    df = pd.read_excel(EXCEL_FILE_PATH)
    new_row = pd.DataFrame([data], columns=EXCEL_COLUMNS)
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel(EXCEL_FILE_PATH, index=False)
    logging.debug(f"Updated Excel file at {EXCEL_FILE_PATH}.")


def clean_state_files():
    # Timestamp for 30 days ago
    cutoff_time = datetime.now() - timedelta(days=30)
    for filename in os.listdir(BACKUP_PATH):
        file_path = os.path.join(BACKUP_PATH, filename)
        if os.path.isfile(file_path):
            file_modified_time = datetime.fromtimestamp(
                os.path.getmtime(file_path)
            )
            if file_modified_time < cutoff_time:
                os.remove(file_path)
                logging.info(f"Deleting backup file at {file_path}.")

    for filename in os.listdir(LOG_PATH):
        file_path = os.path.join(LOG_PATH, filename)
        if os.path.isfile(file_path):
            file_modified_time = datetime.fromtimestamp(
                os.path.getmtime(file_path)
            )
            if file_modified_time < cutoff_time:
                os.remove(file_path)
                logging.info(f"Deleting log file at {file_path}.")


def send_email():
    try:
        with open(EXCEL_FILE_PATH, mode="rb") as f:
            try:
                buffer = f.read()
                logging.debug(
                    f"Opened Excel file at {EXCEL_FILE_PATH} to prepare for emailing."
                )
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

    except Exception as e:
        logging.error(
            f"An error occurred in saving the attendance file: {str(e)}"
        )


def parse_card_info(card_info):
    # If the input didn't time out and format basically makes sense
    if card_info.count("=") == 2 and len(card_info) > 15:
        # Remove the trailing "0"
        penn_id = card_info.split("?")[0].split("%")[1][:-1]
        badge_id = card_info.split("=")[1][1:]  # Remove leading "1"
        timestamp = datetime.now().__str__()
        if len(penn_id) < 7:  # More format checking
            return None
        else:
            return [penn_id, badge_id, card_info, timestamp]
    else:
        return None


# Schedule the email
schedule.every().monday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().tuesday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().wednesday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().thursday.at(config["Operation"]["close_time"]).do(send_email)
schedule.every().friday.at(config["Operation"]["close_time"]).do(send_email)


def main():
    clean_state_files()  # Delete old backup and log files
    setup_excel_file()  # Create a new Excel file

    now = datetime.now()
    close_time = now.replace(
        hour=int(config["Operation"]["close_time"].split(":")[0]),
        minute=int(config["Operation"]["close_time"].split(":")[1]),
        second=0,
        microsecond=0,
    )
    while now < close_time:  # If accepting swipes
        # Clear standard input before taking input
        tcflush(sys.stdin, TCIOFLUSH)
        try:
            card_info = timedinput("Swipe badge: ", timeout=SWIPE_TIMEOUT)
            logging.debug(f"Input detected: {card_info}")
            data = parse_card_info(card_info)
            if data:
                supabase.table("attendance").insert(
                    {
                        "penn_id": data[0],
                        "raw_data": card_info,
                        "time": data[3],
                    }
                ).execute()
                logging.info(
                    f"Swipe detected with Penn ID: {data[0]} and Badge ID: {data[1]}"
                )
                add_row_to_excel_file(data)

        except TimeoutOccurred as e:
            logging.error("Swipe timed out.")
            pass

        now = datetime.now()  # Update the timestamp for the next loop

    schedule.run_pending()  # Email the Excel file


if __name__ == "__main__":
    main()
