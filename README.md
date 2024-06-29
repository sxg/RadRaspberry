# rad_raspberry

This is a CLI tool that runs on Linux and macOS that will read badge swipes from a card reader via standard input to take attendance and record the data to Supabase.

## Installation

This tool is designed to be deployed on Raspberry Pis running in headless mode, which you can setup through the Raspberry Pis’ system settings. Install this tool using `pip`:
```bash
pip install -U git+https://github.com/sxg/rad_raspberry
```

Note: you might need to add the `--break-system-packages` flag at the end to install the tool globally. You can confirm the installation and version with `pip show rad_raspberry`.

The current method for starting this file on startup (and every shell invocation) is by appending to `.bashrc`:
```
/home/pennradiology/.local/bin/rad_raspberry
```

### Config
A `config.ini` file is required and located at `~/.config/rad_raspberry/config.ini`. Here are the required values in a sample `config.ini` file:
```
[API]
supabase_url = <Supabase URL>
supabase_api_key = <Supabase API Key>
supabase_username = <Supabase Username>
supabase_password = <Supabase Password>

server_url = <tailscale url>

[Operation]
# When to stop accepting swipes (24 hr time in local timezone)
close_time = 09:00
location = HUP
```
`close_time` specifies when the script stops running for the day. `location` is a text description that uniquely identifies the Raspberry Pi. This is represented as an enum in the Supabase `attendance` table, so if you want to use a new value here, be sure to also add it to the defined enum in Supabase.

## Updates

You can update this tool with the same command you used to install it:
```bash
pip install -U git+https://github.com/sxg/rad_raspberry
```
This will install the latest committed version on the `main` branch. Remember to update the version number of the tool in `setup.py`.

## Automatic Reboot

Since the Raspberry Pi will typically be connected to a guest WiFi network, it's at risk of periodically being kicked off the network. To workaround this, set a cron job to automatically and periodically restart the Raspberry Pi. Use `sudo crontab -e` to edit the cron job file, and add this line:
```
0 4 * * * /usr/sbin/shutdown -r now
```
This will automatically restart the Raspberry Pi every day at 4 am, and on startup, it should automatically reconnect to the same WiFi network with a fresh connection.


# server config

install server requirements in `server-requirements.txt`

create an env file and load into environment that server will be running in. can consider using dotenv or just `export $(cat .env | xargs)`

```
EMAIL_FROM="Penn Radiology <attendance@pennrads.com>"
EMAIL_API_URL=https://api.resend.com/emails
EMAIL_API_TOKEN=<token>
SUMMARY_RECIPIENT=<recipient email>
```
create a csv of all residents with the following columns:
`name`, `email`, `badge_id`. Place it in `~/.local/state/rad_raspberry/residents.csv`

start the server to test:
```
uvicorn server:app --reload --timeout-keep-alive 120
```

start only on one raspberry pi. note the (tailscale) IP or domain name for this pi. you'll need to update all clients to point to this server in the config above, `server_url`. be sure to include the port.

copy the service file to the appropriate location and start/enable service:
```
ln -s /home/pennradiology/rad_raspberry/rad.service /usr/lib/systemd/system/rad.service
sudo systemctl daemon-reload
sudo systemctl start rad
sudo systemctl enable rad
```

to send a daily summary email using the server architecture at 9am, add this to your crontab:

```
0 9 * * * /usr/bin/curl http://<server url>/send-summary
```
