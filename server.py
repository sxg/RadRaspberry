import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import base64
import pandas as pd
import requests
import uvicorn

app = FastAPI()

# Database setup
conn = sqlite3.connect('swipes.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS swipes
    (badge_id TEXT, timestamp TEXT)
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
    badge_id: str

def send_email(to: str, subject: str, body: str, attachments: list = list()):
    payload = {
        "from": EMAIL_FROM,
        "to": to,
        "subject": subject,
        "html": body
    }

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

    print(response)
    print(response.content)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to send email")

def get_residents():
    # Load CSV file
    return pd.read_csv(
        'badge_data.csv',
        dtype={
            "name": str,
            "badge_id": str,
            "email": str,
        }
    )


@app.post("/swipe")
async def swipe(data: SwipeData):
    badge_id = data.badge_id
    timestamp = datetime.now().isoformat()

    # Record swipe to database
    cursor.execute("INSERT INTO swipes (badge_id, timestamp) VALUES (?, ?)",
                   (badge_id, timestamp))
    conn.commit()

    r = get_residents()

    # Find email for the badge ID
    user_data = r[r['badge_id'] == badge_id]
    if user_data.empty:
        raise HTTPException(status_code=404, detail="Badge ID not found")

    email = user_data['email'].iloc[0]
    name = user_data['name'].iloc[0]

    # Send email
    subject = "Swipe Confirmation"
    body = f"Hello {name}, your badge (ID: {badge_id}) was swiped at {timestamp}"
    send_email(email, subject, body)

    return {"message": "Swipe recorded and email sent"}

@app.post("/send-summary")
async def send_summary():
    # Get swipes from the last day
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()

    # Read the data from the database into a DataFrame
    swipes_df = pd.read_sql_query("SELECT badge_id, timestamp FROM swipes WHERE timestamp > ?", conn, params=[yesterday])

    r = get_residents()

    summary_df = swipes_df.merge(r, on='badge_id', how='left')

    # Save as Excel and CSV
    summary_df.to_excel('summary.xlsx', index=False)
    summary_df.to_csv('summary.csv', index=False)

    # Send email with attachments
    subject = "Daily Swipe Summary"
    body = "Please find attached the daily swipe summary."
    attachments = ["summary.xlsx", "summary.csv"]
    send_email(SUMMARY_RECIPIENT, subject, body, attachments)

    return {"message": "Summary sent successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
