from pathlib import Path
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import timezone
from zoneinfo import ZoneInfo
import json
import base64
import pandas as pd
import requests
import uvicorn
import logging

# Create folders for logs, backups, and config file if needed
ROOT = Path(os.path.expanduser("~/.local/state/rad_raspberry/"))
LOG_PATH = ROOT / "log"
BACKUP_PATH = ROOT / "backup"
RESIDENTS = ROOT / 'residents.csv'
SWIPES_DB = ROOT / 'swipes.db'
os.makedirs(LOG_PATH, exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)

LOG_FILE_NAME = f"{datetime.now().strftime('%Y-%m-%d')}.log"

# Configure logging
logging.basicConfig(
    filename=LOG_PATH / LOG_FILE_NAME,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI()

# Database setup
conn = sqlite3.connect(SWIPES_DB, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS swipes
    (penn_id TEXT, timestamp TEXT)
''')
conn.commit()

# Email API configuration
EMAIL_API_URL = os.environ["EMAIL_API_URL"]
EMAIL_API_TOKEN = os.environ["EMAIL_API_TOKEN"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
SUMMARY_RECIPIENT = os.environ["SUMMARY_RECIPIENT"]

if not EMAIL_API_TOKEN:
    raise ValueError("EMAIL_API_TOKEN environment variable is not set")

email_headers = {
    "Authorization": f"Bearer {EMAIL_API_TOKEN}",
    "Content-Type": "application/json"
}

class SwipeData(BaseModel):
    penn_id: str

def send_email(to: str, subject: str, body: str, attachments: list = list()):
    payload = {
        "from": EMAIL_FROM,
        "to": to,
        "subject": subject,
        "html": body
    }
    logging.info(f"sending {json.dumps(payload)}")

    if len(attachments):
        files = list()
        for attachment in attachments:
            with open(attachment, 'rb') as file:
                files.append(
                    {
                        "filename": os.path.basename(attachment),
                        "content": base64.b64encode(file.read()).decode('utf-8'),
                    }
                )
        payload["attachments"] = files

    response = requests.post(
        EMAIL_API_URL,
        json=payload,
        headers=email_headers,
    )

    if response.status_code != 200:
        logging.error("unable to send email", response.content)
        raise HTTPException(status_code=500, detail="Failed to send email")

def get_residents():
    # Load CSV file
    return pd.read_csv(
        RESIDENTS,
        dtype={
            "name": str,
            "penn_id": str,
            "email": str,
        }
    )


@app.post("/swipe")
async def swipe(data: SwipeData):
    penn_id = data.penn_id
    now = datetime.now(tz=timezone.utc)
    pretty_now = now.astimezone(ZoneInfo("America/New_York")).strftime('%Y-%m-%d, %I:%M:%S %p')
    day = datetime.now().astimezone(ZoneInfo("America/New_York")).strftime('%B %d, %Y')
    logging.info(f"/swipe: {pretty_now} {penn_id} {now}")

    r = get_residents()

    # Find email for the badge ID
    user_data = r[r['penn_id'] == penn_id]
    if user_data.empty:
        logging.error(f"unable to find {penn_id}")
        raise HTTPException(status_code=404, detail="Badge ID not found")

    # Record swipe to database
    cursor.execute("INSERT INTO swipes (penn_id, timestamp) VALUES (?, ?)",
                   (penn_id, now))
    conn.commit()

    email = user_data['email'].iloc[0]
    name = user_data['name'].iloc[0]

    # Send email
    subject = f"Attendance Confirmed ({day})"
    body = f"Hello {name}, your attendance has been recorded: <br/> {pretty_now} <br/> Penn Radiology"
    send_email(email, subject, body)

    return {"message": "Swipe recorded and email sent"}


@app.post("/send-summary")
async def send_summary():
    now = datetime.now().astimezone(ZoneInfo("America/New_York")).strftime('%Y-%m-%d-%H:%M:%S')
    day = datetime.now().astimezone(ZoneInfo("America/New_York")).strftime('%B %d, %Y')
    logging.info(f"/send-summary {now}")

    # Get swipes from the last day
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()

    # Read the data from the database into a DataFrame
    swipes_df = pd.read_sql_query(
        "SELECT penn_id, timestamp FROM swipes WHERE timestamp > ?",
        conn,
        params=[yesterday],
        parse_dates=["timestamp"],
        )

    r = get_residents()

    summary_df = swipes_df.merge(r, on='penn_id', how='left')

    as_ny = summary_df.timestamp.dt.tz_convert(ZoneInfo("America/New_York"))
    summary_df["swipe_time"] = as_ny.dt.strftime('%Y-%m-%d %I:%M:%S %p')
    summary_df = summary_df.drop("timestamp", axis=1)

    # Save as Excel and CSV
    summary_df.to_excel(BACKUP_PATH / f'{now}.xlsx', index=False)
    summary_df.to_csv(BACKUP_PATH / f'{now}.csv', index=False)

    # Send email with attachments
    subject = f"Lecture Attendance ({day})"
    body = "Please find attached the daily swipe summary."
    attachments = [
        BACKUP_PATH / f"{now}.xlsx",
        BACKUP_PATH / f"{now}.csv",
    ]
    send_email(SUMMARY_RECIPIENT, subject, body, attachments)

    return {"message": "Summary sent successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
