# Self-Destructing Media Downloader

A Python userbot that automatically downloads self-destructing media (photos and videos) from Telegram private messages before they disappear.

## Features

- Automatically download self-destructing photos and videos from private messages
- Organize downloaded media by sender
- Admin commands to manage files and check bot status
- Create ZIP archives of downloaded media
- Docker support for easy deployment

## Requirements

- Python 3.12+
- A Telegram account with API credentials from [my.telegram.org](https://my.telegram.org/)
- Your Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot))

## Installation

### Standard

1. Clone the repository:

```bash
git clone https://github.com/bpstuder/Self-Destructing-Media-Downloader.git
cd Self-Destructing-Media-Downloader
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file at the root of the project:

```bash
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_ADMIN_ID=123456789
```

4. Run the bot:

```bash
python TSDMD.py
```

### Docker

1. Create your `.env` file as above, and add:

```bash
SESSION_DIR=/app/sessions
```

2. First run (interactive — required for Telegram authentication):

```bash
docker compose run --rm tsdmd
```

Enter your phone number, the SMS code, and your 2FA password if enabled.
The session file is saved in `./sessions/` and reused on every subsequent start.

3. Run as a background daemon:

```bash
docker compose up -d
```

4. View logs:

```bash
docker compose logs -f tsdmd
```

5. Stop:

```bash
docker compose down
```

## Configuration

All credentials are loaded from environment variables. **Never hardcode them in the source code.**

| Variable | Description |
|---|---|
| `TELEGRAM_API_ID` | Your API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | Your API hash from my.telegram.org |
| `TELEGRAM_ADMIN_ID` | Your Telegram user ID |
| `SESSION_DIR` | Directory for the session file (optional, default: `.`) |

## Commands

Once the bot is running, send these commands to yourself in a private Telegram chat:

| Command | Description |
|---|---|
| `/help` | Display the help menu |
| `/ping` | Check if the bot is alive and measure ping time |
| `/status` | Get the number of downloaded files (photos/videos) |
| `/files` | List all files in the media folder |
| `/check` | List current files in the media folder |
| `/download [file_path]` | Send a specific file to you |
| `/delete [file_path]` | Delete a specific file |
| `/all` | Send all media files to you |
| `/zip` | Create and send a ZIP of all media files |

## Project Structure

```
Self-Destructing-Media-Downloader/
├── TSDMD.py              # Main bot script
├── requirements.txt      # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── .env                  # Credentials (never commit this)
├── .gitignore
├── sessions/             # Telethon session file (never commit this)
└── Media/                # Downloaded media (never commit this)
```

## Security

- Credentials are stored in `.env`, never in the source code or a JSON file
- The `.session` file and `.env` are excluded from git via `.gitignore`
- File path inputs are validated to prevent directory traversal attacks
- The Docker container runs as a non-root user with minimal capabilities
- The `/zip` command only includes media files, never credentials or session files

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Disclaimer

This tool is for personal and educational use only. Please respect copyright laws and the privacy of others when using this script.