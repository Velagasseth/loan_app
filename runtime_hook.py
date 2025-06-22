import os
import sys
import sqlite3
import logging
from pathlib import Path


def setup_logging():
    """Configure logging for the application"""
    log_dir = get_data_directory() / 'logs'
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        filename=log_dir / 'loan_system.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def get_data_directory() -> Path:
    """Determine the correct data directory path"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_path = Path(sys.executable).parent
    else:
        # Running in development environment
        base_path = Path(__file__).parent

    return base_path / 'loan_data'


def initialize_database(db_path: Path):
    """Initialize the SQLite database with required tables"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create loans table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            national_id TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            physical_address TEXT,
            amount REAL NOT NULL,
            payment_per_day REAL NOT NULL,
            term_months INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_to_repay REAL NOT NULL,
            remaining_balance REAL NOT NULL,
            status TEXT NOT NULL,
            created_by TEXT NOT NULL,
            last_modified TEXT,
            loan_file TEXT
        )
        ''')

        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
        ''')

        # Create default admin user if none exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
            ''', ('admin', 'default_hash', 'Administrator', 'admin'))

        conn.commit()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
        raise
    finally:
        conn.close()


def create_initial_files():
    """Create necessary data directory and files"""
    try:
        data_dir = get_data_directory()
        data_dir.mkdir(exist_ok=True)

        # Initialize SQLite database
        db_path = data_dir / 'loan_system.db'
        if not db_path.exists():
            initialize_database(db_path)

        logging.info(f"Data directory initialized at {data_dir}")
    except Exception as e:
        logging.error(f"Initialization failed: {str(e)}")
        raise


if __name__ == '__main__':
    setup_logging()
    try:
        create_initial_files()
        logging.info("Runtime hook executed successfully")
    except Exception as e:
        logging.critical(f"Runtime hook failed: {str(e)}")
        sys.exit(1)