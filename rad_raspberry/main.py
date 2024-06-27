import os
import sys
import pandas as pd
from termios import tcflush, TCIOFLUSH
from timedinput import timedinput, TimeoutOccurred
import time
from datetime import datetime, date, timedelta, timezone
import logging
import shutil
import configparser
from supabase import create_client
from postgrest.exceptions import APIError
import requests

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

EXCEL_FILE_NAME = f"{config['Operation']['Location']} ({datetime.now().strftime('%Y-%m-%d %H-%M-%S)')}.xlsx"
EXCEL_FILE_PATH = os.path.join(BACKUP_PATH, EXCEL_FILE_NAME)
EXCEL_COLUMNS = [
    "Penn ID",
    "Badge ID",
    "All Swipe Data",
    "Badge Swipe Time",
    "Location",
]

SWIPE_TIMEOUT = 60  # Seconds to wait for a swipe

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


def parse_card_info(card_info):
    # If the input didn't time out and format basically makes sense
    if card_info.count("=") == 2 and len(card_info) > 15:
        # Remove the trailing "0"
        penn_id = card_info.split("?")[0].split("%")[1][:-1]
        badge_id = card_info.split("=")[1][1:]  # Remove leading "1"
        timestamp = datetime.now(timezone.utc).__str__()
        if len(penn_id) < 7:  # More format checking
            return None
        else:
            return [
                penn_id,
                badge_id,
                card_info,
                timestamp,
                config["Operation"]["Location"],
            ]
    else:
        return None


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
    swipes = 0
    while now < close_time:  # If accepting swipes
        # Clear standard input before taking input
        tcflush(sys.stdin, TCIOFLUSH)
        try:
            card_info = timedinput("Swipe badge: ", timeout=SWIPE_TIMEOUT)
            logging.debug(f"Input detected: {card_info}")
            data = parse_card_info(card_info)

            if data:
                requests.post(
                    f"http://{config["API"]["server_url"]}/swipe",
                    json={"badge_id": data[1]},
                )

                supabase.table("attendance").insert(
                    {
                        "penn_id": data[0],
                        "badge_id": data[1],
                        "location": config["Operation"]["Location"],
                        "raw_data": card_info,
                        "time": data[3],
                    }
                ).execute()
                logging.info(
                    f"Swipe detected with Penn ID: {data[0]} and Badge ID: {data[1]} at location: {config['Operation']['Location']}."
                )
                add_row_to_excel_file(data)
                swipes += 1


        except TimeoutOccurred:
            logging.debug("Swipe timed out.")
            pass
        except APIError as e:
            logging.error(f"Supabase API Error: {e}")
            pass

        now = datetime.now()  # Update the timestamp for the next loop

    # Send the attendance summary email if there's anything to send
    # Only want to send one summary email, so put that responsibility on the HUP device
    if swipes > 0 and config["Operation"]["Location"] == "HUP":
        logging.info(
            f"Invoking attendance-summary-email edge function with {swipes} swipe(s).")
        supabase.functions.invoke("attendance-summary-email")

    # Tear down
    logging.info("Shutting down...")
    logging.shutdown()
    supabase.auth.sign_out()


if __name__ == "__main__":
    main()
