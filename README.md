# Mac (directory/folder) Backup Script

This is a script that is intended to be a launchd job to periodically backup a directory to another directory.

I recently started saving my Obsidian Vault on iCloud so I can use it across my devices without paying for the Obsidian premium. I don't exactly trust iCloud keeping my Obsidian notes safe and sound, so am trying to create a script to automate periodic backup with `launchd`.

## How to setup?

### 0. Clone/download repo & set up the system

Run the steps below in CLI to set up the system

```bash
# 0.1 Check Python is available, if not, download it and check again
python3 --version

# 0.2 (Option A) Clone with git
# Replace with your fork if applicable
git clone https://github.com/jhasu/mac_backup_script.git
cd mac_backup_script

#    (Option B) Download ZIP
#    - Click "Code" → "Download ZIP"
#    - Unzip and `cd` into the folder in Terminal

# 0.3 Create user-level script and log directories
mkdir -p ~/.local/scripts/mac_backup_script
mkdir -p ~/.local/logs/mac_backup_script

# 0.4 Create an empty .env file (you will fill this in Step 1)
: > ~/.local/scripts/mac_backup_script/.env

# 0.5 (Optional) Open the .env file in your editor
# open -e ~/.local/scripts/mac_backup_script/.env   # TextEdit
# code ~/.local/scripts/mac_backup_script/.env      # VS Code, if installed
```

### 1. Create environment file

Follow the `.env.example` to create an `.env` file with the required variables:

- `BACKUP_STORAGE_DIR`: Directory where backups will be stored
- `SOURCE_DIR`: Directory to backup (e.g., your Obsidian vault)
- `MAX_BACKUP_SIZE`: Maximum total backup size in bytes (optional, defaults to 1GB)
- `LOG_LEVEL`: For logging.

Update `com.example.mac-dir-backup-script.plist` to use your user name instead of john_doe.

```
For example:
<string>/Users/john_doe/.local/scripts/mac_backup_script/.venv/bin/python</string>

Change to:

<string>/Users/<your_user>/.local/scripts/mac_backup_script/.venv/bin/python</string>

To find out what <your_user> is, type `whoami` in your terminal
```

### 2. Create a virtual environment and install dependencies (recommended)

```bash
# Create directories for script and logs (if not already created)
mkdir -p ~/.local/scripts/mac_backup_script
mkdir -p ~/.local/logs/mac_backup_script

# Copy files into the script directory used by launchd
cp main.py ~/.local/scripts/mac_backup_script/
cp .env ~/.local/scripts/mac_backup_script/

# Create a virtual environment next to the script
python3 -m venv ~/.local/scripts/mac_backup_script/.venv

# Upgrade pip and install dependencies into the venv
~/.local/scripts/mac_backup_script/.venv/bin/python -m pip install --upgrade pip
~/.local/scripts/mac_backup_script/.venv/bin/pip install python-dotenv

# (Optional) Freeze versions for reproducibility
~/.local/scripts/mac_backup_script/.venv/bin/pip freeze > ~/.local/scripts/mac_backup_script/requirements.lock.txt
```

### 3. Test the script manually

```bash
# Run from the working directory so the .env is picked up
cd ~/.local/scripts/mac_backup_script
~/.local/scripts/mac_backup_script/.venv/bin/python main.py
```

### 4. Set up as launchd service

#### User directory installation

```bash
# Set permissions
chmod +x ~/.local/scripts/mac_backup_script/main.py

# Install (or update) the launchd job
cp com.example.mac-dir-backup-script.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.example.mac-dir-backup-script.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.example.mac-dir-backup-script.plist
launchctl kickstart -k gui/$(id -u)/com.example.mac-dir-backup-script
```

Note: You can also setup System-wide installation, instructions not provided.

### 5. Verify installation

```bash
# Check if job is loaded
launchctl list | grep com.example.mac-dir-backup-script

# Check logs
tail -f ~/.local/logs/mac_backup_script/backup.log
tail -f ~/.local/logs/mac_backup_script/backup_error.log
```

### 6. Manage the service

```bash
# Unload the job
launchctl unload ~/Library/LaunchAgents/com.example.mac-dir-backup-script.plist

# Reload after changes
launchctl unload ~/Library/LaunchAgents/com.example.mac-dir-backup-script.plist
launchctl load ~/Library/LaunchAgents/com.example.mac-dir-backup-script.plist
```

## Note on the script behavior:

This script is designed for backing up iCloud-synced directories (like Obsidian vaults). Requirements:

- backups are only checked if they are in directory
- each individual backup directories should be properly timestamped so it can be FIFO evicted
- **iCloud sync**: Make sure your source directory is fully synced before backup runs
- **User permissions**: Script runs as your user account to access iCloud files

The provided example launchd script will run at this cadence:

- Once when loaded (start/login) with `RunAtLoad` property
- While awake: Script runs every `StartInterval` seconds as scheduled
- After sleep (missed intervals): Run ONCE on wake if missed one or more scheduled jobs. Resumes the schedule.

## Improvements TODO:

- Create diff based backups to optimize for space?
