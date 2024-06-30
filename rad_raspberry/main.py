import os
import sys
from termios import tcflush, TCIOFLUSH
from datetime import datetime
import logging
import aiohttp
from pathlib import Path
import asyncio
from asyncio.exceptions import CancelledError

SERVER_URL = os.environ["SERVER_URL"]

ROOT = Path(os.path.expanduser("~/.local/state/rad_raspberry/"))
LOG_PATH = ROOT / "log"
os.makedirs(LOG_PATH, exist_ok=True)

LOG_FILE_NAME = f"client-{datetime.now().strftime('%Y-%m-%d')}.log"

# Configure logging
logging.basicConfig(
    filename=LOG_PATH / LOG_FILE_NAME,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def parse_card_info(card_info):
    # If the input didn't time out and format basically makes sense
    if card_info.count("=") == 2 and len(card_info) > 15:
        # Remove the trailing "0"
        penn_id = card_info.split("?")[0].split("%")[1][:-1]
        badge_id = card_info.split("=")[1][1:]  # Remove leading "1"
        if len(penn_id) < 7:  # More format checking
            return None
        else:
            return [
                penn_id,
                badge_id,
                card_info,
            ]
    else:
        return None


async def swipe(session, penn_id):
    try:
        async with session.post(
            '/swipe',
            json={"penn_id": penn_id},
        ) as r:
            logging.info(await r.text())
    except (KeyboardInterrupt, RuntimeError, CancelledError):
        pass
    except:
        logging.exception("error")


async def run():
    tcflush(sys.stdin, TCIOFLUSH)
    async with aiohttp.ClientSession(SERVER_URL) as session:
        while True:
            try:
                card_info = await asyncio.to_thread(input, "swipe: ")
                logging.info(f"card info: {card_info}")
                data = parse_card_info(card_info)
                if data is not None:
                    asyncio.create_task(swipe(session, str(data[0])))
            except (KeyboardInterrupt, RuntimeError, CancelledError):
                pass
            except:
                logging.exception("error")

def main():
    asyncio.run(run())

if __name__ == "__main__":
    main()
