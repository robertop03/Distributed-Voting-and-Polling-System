import threading

state_lock = threading.RLock()

# Protects all file I/O (WAL, checkpoint). May be acquired while holding
# state_lock, but never acquire state_lock while holding storage_lock.
storage_lock = threading.RLock()