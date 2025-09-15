import os
from dotenv import load_dotenv
import heapq
from datetime import datetime, timezone
import shutil
import sys
import logging
import tempfile

# Load environment variables from .env file
load_dotenv()

############## Environment Variables ##############
BACKUP_STORAGE_DIR = os.getenv('BACKUP_STORAGE_DIR')
SOURCE_DIR = os.getenv('SOURCE_DIR')
MAX_BACKUP_SIZE = int(os.getenv('MAX_BACKUP_SIZE', '1000000000'))  # Default to 1GB if not set
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()  # DEBUG, INFO, WARNING, ERROR, CRITICAL
###################################################

############## Logging ##############
def _coerce_log_level(level_str: str) -> int:
    return getattr(logging, level_str, logging.INFO)

logging.basicConfig(
    level=_coerce_log_level(LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,  # stdout -> captured by launchd StandardOutPath
)
logger = logging.getLogger(__name__)
#####################################

############## Constants ##############
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
######################################

# Validate required variables
required_vars = {
    'BACKUP_STORAGE_DIR': BACKUP_STORAGE_DIR,
    'SOURCE_DIR': SOURCE_DIR
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"Required environment variable {var_name} is not set")

def backup():
    logger.info("Backup job started")
    # Check if BACKUP_STORAGE_DIR exists, if not, create it
    os.makedirs(BACKUP_STORAGE_DIR, exist_ok=True)

    # Get existing cache size & file window
    file_heap, tot_backup_sz = aggregate_dir_size_stats(p=BACKUP_STORAGE_DIR)
    logger.debug(f"Existing backups: count={len(file_heap)} total_size_bytes={tot_backup_sz}")

    # Validate & Check source size
    if not os.path.exists(SOURCE_DIR):
        logger.error(f"Source directory does not exist: {SOURCE_DIR}")
        raise FileNotFoundError(SOURCE_DIR)
    
    _, vault_sz = aggregate_dir_size_stats(p=SOURCE_DIR)
    logger.info(f"Source size bytes: {vault_sz}")

    # Evict oldest backup(s) if over max_cache limit
    while (tot_backup_sz + vault_sz) > MAX_BACKUP_SIZE and file_heap:
        name, size, path = heapq.heappop(file_heap)
        logger.warning(f"Evicting old backup '{name}' size={size} path={path}")
        success = delete_dir(path)
        if not success:
            logger.error(f"Failed to delete backup directory: {path}")
            raise Exception("Error deleting backup directory")
        tot_backup_sz -= size
        logger.debug(f"Post-eviction total backup size: {tot_backup_sz}")
    
    if (tot_backup_sz + vault_sz) > MAX_BACKUP_SIZE and not file_heap:
        raise Exception("Insufficient space after evicting all backups")

    # Create & store new backup
    timestamp = get_current_datetime_str()
    final_dir = os.path.join(BACKUP_STORAGE_DIR, timestamp)
    if os.path.exists(final_dir): # rare collision if two runs in same second
        raise FileExistsError(f"Backup dir already exists: {final_dir}")

    with tempfile.TemporaryDirectory(dir=BACKUP_STORAGE_DIR, prefix=f".tmp_{timestamp}_") as tmp_dir:
        # Note: edge case covered - if .tmp fails, it will be deleted first when running out of space
        logger.info(f"Copying to temp: {tmp_dir}")
        shutil.copytree(SOURCE_DIR, tmp_dir, dirs_exist_ok=True)
        logger.info(f"Renaming {tmp_dir} -> {final_dir}")
        os.rename(tmp_dir, final_dir)

    logger.info("Backup completed successfully")

def aggregate_dir_size_stats(p: str):
    """
    param: path of the directory that you'd like to query for
    returns: min_heap of (name, size_bytes, absolute_path) and total size of dir

    Note: the path feed in should exist...
    """
    file_heap = []
    total_backup_sz = 0

    with os.scandir(p) as entries:
        for entry in entries:
            name = entry.name
            walk_path = os.path.join(p, name)
            if not entry.is_dir(follow_symlinks=False):
                try:
                    total_backup_sz += entry.stat(follow_symlinks=False).st_size
                except (FileNotFoundError, PermissionError) as e:
                    logger.debug(f"Skip root file '{walk_path}': {e}")
                continue  # skip non backup dirs

            tot_sz = 0
            for root, dirs, files in os.walk(walk_path, followlinks=False):
                for f in files:
                    file_path = os.path.join(root, f)
                    try:
                        tot_sz += os.stat(file_path, follow_symlinks=False).st_size
                    except (FileNotFoundError, PermissionError) as e:
                        logger.debug(f"Skip file '{file_path}': {e}")
            heapq.heappush(file_heap, (name, tot_sz, walk_path))
            total_backup_sz += tot_sz

    return file_heap, total_backup_sz

# DANGER
def delete_dir(dir_path: str):
    """Safely delete a directory and all its contents"""
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            return True
    except OSError as e:
        # stderr -> captured by launchd StandardErrorPath
        logger.error(f"Error deleting directory {dir_path}: {e}", exc_info=True)
        return False
    return False

# return utc-0 datetime timestamp string in DATETIME_FORMAT
def get_current_datetime_str():
    now = datetime.now(timezone.utc)
    string_stamp = now.strftime(DATETIME_FORMAT)
    return string_stamp

if __name__ == "__main__":
    try:
        backup()
    except Exception as e:
        logger.exception(f"Backup failed: {e}")
        sys.exit(1)