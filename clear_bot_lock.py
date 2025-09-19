#!/usr/bin/env python3
"""
Utility script to clear bot lockfile if bot crashed or was force-stopped
"""
import os
import sys

def clear_lock():
    lockfile = "bot.lock"
    
    if os.path.exists(lockfile):
        try:
            os.remove(lockfile)
            return True
        except Exception as e:
            return False
    else:
        return True

if __name__ == "__main__":
    success = clear_lock()
    sys.exit(0 if success else 1)
