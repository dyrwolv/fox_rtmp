# dyrwolv python logger util
# src/utils/logger.py

import time
#our logging system, should move this to the main.py?
def log(message):
    # logging function to print messages with a timestamp.
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")