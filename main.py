import csv
import time
from datetime import datetime

# Open a CSV file
with open("attendance.csv", "w", encoding="UTF8") as f:
    writer = csv.writer(f)

    # First column will be the badge id and second column is the timestamp
    writer.writerow("Badge ID", "Badge Swipe Time")
    card_info = input("Swipe your badge: ")
    print(f"Here's what I got: {card_info}")
    badge_id = card_info.split("=")[1]
    ts_str = datetime.now().__str__()

    # Write to the CSV file
    writer.writerow([badge_id, ts_str])
