#!/usr/bin/env python3
"""
Database migration script for CraftsBuddy
Usage:
  python migrate.py init     # Initialize alembic (first time only)
  python migrate.py migrate  # Generate migration from model changes
  python migrate.py upgrade  # Apply migrations to database
  python migrate.py current  # Show current migration
  python migrate.py history  # Show migration history
"""
import sys
import os
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_alembic_config():
    """Get Alembic configuration"""
    alembic_cfg = Config("alembic.ini")
    
    # Import database config to get properly formatted URL
    from src.config.database import get_database_url
    db_url = get_database_url()
    alembic_cfg.set_main_option('sqlalchemy.url', db_url)
    
    return alembic_cfg

def init_migration():
    """Initialize Alembic (first time setup)"""
    print("Initializing Alembic migration environment...")
    try:
        alembic_cfg = get_alembic_config()
        command.init(alembic_cfg, "alembic")
        print("✓ Alembic initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Alembic: {e}")

def create_migration(message="Auto migration"):
    """Create a new migration"""
    print(f"Creating migration: {message}")
    try:
        alembic_cfg = get_alembic_config()
        command.revision(alembic_cfg, autogenerate=True, message=message)
        print("✓ Migration created successfully")
    except Exception as e:
        print(f"✗ Failed to create migration: {e}")

def upgrade_database():
    """Apply migrations to database"""
    print("Upgrading database...")
    try:
        alembic_cfg = get_alembic_config()
        command.upgrade(alembic_cfg, "head")
        print("✓ Database upgraded successfully")
    except Exception as e:
        print(f"✗ Failed to upgrade database: {e}")

def show_current():
    """Show current migration"""
    try:
        alembic_cfg = get_alembic_config()
        command.current(alembic_cfg)
    except Exception as e:
        print(f"✗ Failed to show current migration: {e}")

def show_history():
    """Show migration history"""
    try:
        alembic_cfg = get_alembic_config()
        command.history(alembic_cfg)
    except Exception as e:
        print(f"✗ Failed to show migration history: {e}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command_arg = sys.argv[1].lower()
    
    if command_arg == "init":
        init_migration()
    elif command_arg == "migrate":
        message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
        create_migration(message)
    elif command_arg == "upgrade":
        upgrade_database()
    elif command_arg == "current":
        show_current()
    elif command_arg == "history":
        show_history()
    else:
        print(f"Unknown command: {command_arg}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
