import os
import sys
import sqlite3
import shutil
import win32file
import time
from ping3 import ping
import netifaces


def is_network_available():
    try:
        return ping("8.8.8.8", timeout=1) is not None
    except:
        return False


def get_network_share_path():
    # Try predefined path first
    predefined = r'\\SERVER_NAME\LoanSystemData'
    if os.path.exists(predefined):
        return predefined

    # Auto-discover network shares
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                if ip.startswith('192.168') or ip.startswith('10.'):
                    share_path = f'\\\\{ip}\\LoanSystem'
                    if os.path.exists(share_path):
                        return share_path
    return None


def setup_database_schema(db_path):
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
        loan_file TEXT,
        last_modified_by TEXT,
        last_modified_date TEXT
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

    # Create transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        received_by TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (loan_id) REFERENCES loans (loan_id)
    )
    ''')

    # Create system_log table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_time TEXT NOT NULL,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    ''')

    conn.commit()
    conn.close()


def setup_data_directory():
    # Local fallback directory
    LOCAL_DATA_FALLBACK = os.path.expanduser('~/KodongoLoans')

    # Determine where to store data
    if is_network_available():
        network_path = get_network_share_path()
        if network_path:
            DATA_DIR = network_path
            IS_NETWORK = True
        else:
            DATA_DIR = LOCAL_DATA_FALLBACK
            IS_NETWORK = False
    else:
        DATA_DIR = LOCAL_DATA_FALLBACK
        IS_NETWORK = False

    # Create directory if needed
    os.makedirs(DATA_DIR, exist_ok=True)

    # Database file path
    DB_FILE = os.path.join(DATA_DIR, 'kodongo_loans.db')

    # Create lock file for network access
    LOCK_FILE = os.path.join(DATA_DIR, '.lock')

    # Initialize database if it doesn't exist
    if not os.path.exists(DB_FILE):
        setup_database_schema(DB_FILE)

        # Add default admin user if the database is new
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
            ''', ('admin', 'default_hash', 'Administrator', 'admin'))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Admin user already exists
        finally:
            conn.close()

    return DATA_DIR, IS_NETWORK, DB_FILE


def acquire_lock(lockfile):
    """Implement file locking for network share"""
    try:
        handle = win32file.CreateFile(
            lockfile,
            win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_ALWAYS,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None
        )
        win32file.LockFileEx(
            handle,
            win32file.LOCKFILE_EXCLUSIVE_LOCK,
            0, 0xFFFF0000, 0xFFFF0000,
            None
        )
        return handle
    except:
        return None


def release_lock(handle):
    if handle:
        try:
            win32file.UnlockFileEx(
                handle,
                0, 0xFFFF0000, 0xFFFF0000,
                None
            )
            handle.close()
        except:
            pass


if __name__ == '__main__':
    DATA_DIR, IS_NETWORK, DB_FILE = setup_data_directory()
    LOCK_HANDLE = acquire_lock(os.path.join(DATA_DIR, '.lock'))

    # Store these for the main application to use
    os.environ['KODONGO_DATA_DIR'] = DATA_DIR
    os.environ['KODONGO_IS_NETWORK'] = str(IS_NETWORK)
    os.environ['KODONGO_DB_FILE'] = DB_FILE

    # Keep lock until main app starts
    time.sleep(5)
    release_lock(LOCK_HANDLE)