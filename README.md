!!! The script is currently half-baked, use with caution !!!

# Mac Backup Script

This is a script that is intended to be a cron/launchmd job to peridically backup a directory to another directory.

I recently started saving my Obsidian Vault on iCloud so I can use it across my devices without paying for the Obsidian premium. I don't exactly trust iCloud keeping my Obsidian notes safe and sound, so am trying to create a script to automate periodic backup with `launchd`.

## How to setup?

1. Follow the `.env.example` to create an `.env` file with the required variables
   (rest is to be added...)

## Note:

this dosen't work for anybackups. Requirements:

- backups are only checked if they are in directory
- each individual backup directories should be properly timestampped so it can be FIFO evicted

## TODO

- try-catch and error logging
- improve readme
- make it testable
- write tests

Long term goal:

- Create diff based backups to optimize for space?
