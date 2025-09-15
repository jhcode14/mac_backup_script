import os
from dotenv import load_dotenv
import heapq
from datetime import datetime, timezone
import shutil

# Load environment variables from .env file
load_dotenv()

############## Environment Variables ##############
BACKUP_STORAGE_DIR = os.getenv('BACKUP_STORAGE_DIR')
SOURCE_DIR = os.getenv('SOURCE_DIR')
MAX_BACKUP_SIZE = int(os.getenv('MAX_BACKUP_SIZE', '1000000000'))  # Default to 1GB if not set

# Validate required variables
required_vars = {
    'BACKUP_STORAGE_DIR': BACKUP_STORAGE_DIR,
    'SOURCE_DIR': SOURCE_DIR
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"Required environment variable {var_name} is not set")
###################################################

############## Constant ##############
DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
######################################

def backup():
    # Check if BACKUP_STORAGE_DIR exists, if not, create it
    os.makedirs(BACKUP_STORAGE_DIR, exist_ok=True)

    # Get existing cache size & file window
    file_heap, tot_backup_sz = aggregate_dir_size_stats(p=BACKUP_STORAGE_DIR)

    # Validate & Check Obs Vault size
    if not os.path.exists(SOURCE_DIR):
        # TODO: Look into how to fail and not retry? vs retry for other failiure
        raise FileNotFoundError
    
    _, vault_sz = aggregate_dir_size_stats(p=SOURCE_DIR)

    # Evict oldest backup(s) if over max_cache limit
    while(tot_backup_sz+vault_sz) > MAX_BACKUP_SIZE:
        file_entry = heapq.heappop(file_heap)
        success = delete_dir(file_entry[2])
        if not success:
            raise Exception("Error with deleting")
        tot_backup_sz -= file_entry[1]

    # Create & store new backup
    new_BACKUP_STORAGE_DIR = os.path.join(BACKUP_STORAGE_DIR, get_current_datetime_str())
    os.makedirs(new_BACKUP_STORAGE_DIR, exist_ok=False)
    shutil.copytree(SOURCE_DIR, new_BACKUP_STORAGE_DIR)
    # TODO: Look into how to "succeed"


def aggregate_dir_size_stats(p: str):
    """adss

    param: path of the directory that you'd like to query for
    returns: min_heap (timestamp(name), size, path) and total size of dir
    """
    with os.scandir(p) as enteries:
        for entry in enteries:
            name = entry.name
            walk_path = os.path.join(p, name)
            tot_sz = os.path.getsize(walk_path)
            if not entry.is_dir():
                continue # skip non backup dirs
            for root, dirs, files in os.walk(walk_path):
                for f in files:
                    file_path = os.path.join(root, f)
                    tot_sz += os.path.getsize(file_path)
            
            # aggregate stats
            heapq.heappush(file_heap, (name, tot_sz))
            total_backup_sz += tot_sz

# DANGER
def delete_dir(dir_path: str):
    """Safely delete a directory and all its contents"""
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dirpath)
            return True
    except OSError as e:
        print(f"Error deleting directory {dir_path}: {e}")
        return False
    return False
            
# return utc-0 datetime timestamp string in DATETIME_FORMAT
def get_current_datetime_str():
    now = datetime.now(timezone.utc)
    string_stamp = now.strftime(DATETIME_FORMAT)
    return string_stamp

if __name__ == "__main__":
    backup()