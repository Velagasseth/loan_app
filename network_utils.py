import os
import sqlite3
import shutil
import configparser
import platform
import time
from pathlib import Path


class DatabaseManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, 'kodongo_loans.db')
        self._initialize_database()

    def _initialize_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
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
            )
            ''')

            # Add default admin user if none exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
                ''', ('admin', 'default_hash', 'Administrator', 'admin'))

            conn.commit()

    def get_connection(self):
        """Get a new database connection"""
        return sqlite3.connect(self.db_path)


class NetworkManager:
    def __init__(self):
        self.config = self._load_config()
        self.network_available = False
        self.last_checked = 0
        self.check_interval = 300  # 5 minutes
        self.db_manager = None

    def _load_config(self):
        """Load network configuration from config.ini"""
        config = configparser.ConfigParser()
        config.read('config.ini')

        return {
            'shared_mode': config.getboolean('Network', 'shared_mode', fallback=False),
            'network_path': config.get('Network', 'network_path', fallback=''),
            'fallback': config.getboolean('Network', 'fallback_to_local', fallback=True),
            'retry_interval': config.getint('Network', 'retry_interval', fallback=5),
            'max_retries': config.getint('Network', 'max_retries', fallback=3)
        }

    def verify_network_share(self):
        """Verify if network share is accessible with retries"""
        if not self.config['shared_mode']:
            return False

        if time.time() - self.last_checked < self.check_interval:
            return self.network_available

        retries = 0
        while retries < self.config['max_retries']:
            try:
                test_file = os.path.join(self.config['network_path'], 'connection_test.tmp')
                with open(test_file, 'w') as f:
                    f.write(str(time.time()))
                os.remove(test_file)
                self.network_available = True
                self.last_checked = time.time()
                return True
            except Exception as e:
                retries += 1
                time.sleep(self.config['retry_interval'])

        self.network_available = False
        return False

    def get_data_directory(self):
        """Determine the appropriate data directory with fallback"""
        if self.verify_network_share():
            return self.config['network_path']

        if self.config['fallback']:
            local_path = self._get_local_data_path()
            os.makedirs(local_path, exist_ok=True)
            return local_path

        raise ConnectionError("Network storage unavailable and fallback disabled")

    def _get_local_data_path(self):
        """Get platform-specific local data path"""
        system = platform.system()
        if system == 'Windows':
            return os.path.join(os.getenv('APPDATA'), "KodongoLoanSystem")
        elif system == 'Darwin':
            return os.path.expanduser("~/Library/Application Support/KodongoLoanSystem")
        else:
            return os.path.expanduser("~/.local/share/KodongoLoanSystem")

    def sync_databases(self, local_path):
        """Attempt to sync local database to network when available"""
        if not self.config['shared_mode'] or not self.verify_network_share():
            return False

        try:
            local_db = os.path.join(local_path, 'kodongo_loans.db')
            network_db = os.path.join(self.config['network_path'], 'kodongo_loans.db')

            # Only sync if local database exists and is newer
            if os.path.exists(local_db):
                if not os.path.exists(network_db) or \
                        os.path.getmtime(local_db) > os.path.getmtime(network_db):
                    shutil.copy2(local_db, network_db)
                    return True
            return False
        except Exception as e:
            print(f"Database sync failed: {str(e)}")
            return False

    def initialize_database(self):
        """Initialize the database manager with the appropriate data directory"""
        data_dir = self.get_data_directory()
        self.db_manager = DatabaseManager(data_dir)
        return self.db_manager


if __name__ == '__main__':
    network_manager = NetworkManager()
    db_manager = network_manager.initialize_database()

    # Store configuration for main application
    os.environ['KODONGO_DATA_DIR'] = db_manager.data_dir
    os.environ['KODONGO_DB_PATH'] = db_manager.db_path
    os.environ['KODONGO_NETWORK_MODE'] = str(network_manager.config['shared_mode'])