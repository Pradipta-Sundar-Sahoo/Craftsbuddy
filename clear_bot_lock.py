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
            print(f"✓ Removed lockfile: {lockfile}")
            return True
        except Exception as e:
            print(f"✗ Failed to remove lockfile: {e}")
            return False
    else:
        print(f"✓ No lockfile found: {lockfile}")
        return True

if __name__ == "__main__":
    print("CraftBuddy Bot Lockfile Cleaner")
    print("=" * 35)
    
    success = clear_lock()
    sys.exit(0 if success else 1)
