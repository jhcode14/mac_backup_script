!!! The script is currently in testing, use with caution !!!

# Mac (directory/folder) Backup Script

This is a script that is intended to be a launchd job to periodically backup a directory to another directory.

I recently started saving my Obsidian Vault on iCloud so I can use it across my devices without paying for the Obsidian premium. I don't exactly trust iCloud keeping my Obsidian notes safe and sound, so am trying to create a script to automate periodic backup with `launchd`.

## How to setup?

### 1. Create environment file

Follow the `.env.example` to create an `.env` file with the required variables:

- `BACKUP_STORAGE_DIR`: Directory where backups will be stored
- `SOURCE_DIR`: Directory to backup (e.g., your Obsidian vault)
- `MAX_BACKUP_SIZE`: Maximum total backup size in bytes (optional, defaults to 1GB)
- `LOG_LEVEL`: For logging.

### 2. Install dependencies

```bash
pip install python-dotenv
```

### 3. Test the script manually

```bash
python3 main.py
```

### 4. Set up as launchd service

#### User directory installation (recommended for iCloud backups)

```bash
# Create directories
mkdir -p ~/.local/scripts/mac_backup_script
mkdir -p ~/.local/logs/mac_backup_script

# Copy files
cp main.py ~/.local/scripts/mac_backup_script/
cp .env ~/.local/scripts/mac_backup_script/

# Set permissions
chmod +x ~/.local/scripts/mac_backup_script/main.py

# Install launchd job
cp com.example.mac-dir-backup-script.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.example.mac-dir-backup-script.plist
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

## Note:

This script is designed for backing up iCloud-synced directories (like Obsidian vaults). Requirements:

- backups are only checked if they are in directory
- each individual backup directories should be properly timestamped so it can be FIFO evicted
- **iCloud sync**: Make sure your source directory is fully synced before backup runs
- **User permissions**: Script runs as your user account to access iCloud files

## Improvements TODO:

- Create diff based backups to optimize for space?
