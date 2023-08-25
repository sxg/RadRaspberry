# rad_raspberry

This is a small script that will read badge swipes from a card reader via standard input to take attendance. A `config.py` file is required but not included since it contains a password and deployment specific information. Here's a sample `config.py` file:

```python
from_email = "from_me@gmail.com"
to_emails = ["to_you@gmail.com", "also_to_you@yahoo.com"]
password = "password"
email_subject = "Subject Line of My Email"
open_time = "06:30"  # When to start accepting swipes (24 hr time)
close_time = "08:25"  # When to stop accepting swipes (24 hr time)
swipe_timeout = 3600  # Number of seconds to wait after last swipe
```

# Installation

This script is intended to run on a Raspberry Pi in headless mode. To have the script automatically run when starting the Raspberry Pi, call the script from `~/.bashrc`:

```python
python /path/to/script/rad_raspberry/main.py
````

# Automatic Updates

This is a bare bones script, and so is the "automatic update" mechanism. Just pull the repository from GitHub in `~/.bashrc` before running the script:

```python
sleep 30
git -C /path/to/script/rad_raspberry pull origin main
python /path/to/script/rad_raspberry/main.py
```

The `sleep 30` command pauses for 30 seconds to allow the Raspberry Pi time to connect to WiFi.
