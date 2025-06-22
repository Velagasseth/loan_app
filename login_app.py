# login_app.py
import os
import sqlite3
import sys
import hashlib
import re
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd

from loan_detail_window import LoanDetailWindow
import os
import sys
import shutil
import time
from threading import Thread


class NetworkManager:
    def __init__(self):
        self.shared_mode = False
        self.network_path = r"\\SERVER\KodongoLoanData"
        self.local_path = self._get_local_data_path()
        self.sync_interval = 300  # 5 minutes

    def _get_local_data_path(self):
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            if sys.platform == "win32":
                return os.path.join(os.getenv('APPDATA'), "KodongoLoanSystem")
            elif sys.platform == "darwin":
                return os.path.expanduser("~/Library/Application Support/KodongoLoanSystem")
            else:  # Linux
                return os.path.expanduser("~/.local/share/KodongoLoanSystem")
        else:
            # Running in development
            return os.path.dirname(os.path.abspath(__file__))

    def check_network_share(self):
        """Check if network share is available"""
        try:
            # Try to list the directory
            if os.path.exists(self.network_path):
                return True
            return False
        except:
            return False

    def initialize_data_folder(self):
        """Initialize data folder in appropriate location"""
        if self.check_network_share():
            try:
                data_folder = os.path.join(self.network_path, "Data")
                os.makedirs(data_folder, exist_ok=True)
                self.shared_mode = True
                return data_folder
            except:
                self.shared_mode = False
        else:
            self.shared_mode = False

        # Fall back to local storage
        os.makedirs(self.local_path, exist_ok=True)
        return self.local_path

    def start_sync_thread(self):
        """Start background thread for syncing data"""
        if self.shared_mode:
            Thread(target=self._sync_data, daemon=True).start()

    def _sync_data(self):
        """Sync data between network and local storage"""
        while True:
            try:
                if self.shared_mode and self.check_network_share():
                    network_db = os.path.join(self.network_path, "Data", "kodongo_loans.db")
                    local_db = os.path.join(self.local_path, "kodongo_loans.db")

                    # Sync logic remains the same as before
                    if os.path.exists(network_db) and os.path.exists(local_db):
                        network_mtime = os.path.getmtime(network_db)
                        local_mtime = os.path.getmtime(local_db)

                        if network_mtime > local_mtime:
                            shutil.copy2(network_db, local_db)
                        elif local_mtime > network_mtime:
                            shutil.copy2(local_db, network_db)
                    elif os.path.exists(network_db):
                        shutil.copy2(network_db, local_db)
                    elif os.path.exists(local_db):
                        shutil.copy2(local_db, network_db)

            except Exception as e:
                print(f"Sync error: {str(e)}")

            time.sleep(self.sync_interval)


class DatabaseManager:
    def __init__(self, db_path, network_manager):
        self.db_path = db_path
        self.network_manager = network_manager
        self._initialize_database()

    def _initialize_database(self):
        """Initialize the database with required tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            """)

            # Loans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loans (
                    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_per_day REAL NOT NULL,
                    term_months INTEGER NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_to_repay REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    remaining_balance REAL NOT NULL,
                    physical_address TEXT,
                    national_id TEXT,
                    phone_number TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    received_by TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (loan_id) REFERENCES loans (loan_id)
                )
            """)

            # Loan cycles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loan_cycles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    national_id TEXT,
                    phone_number TEXT,
                    loan_cycles INTEGER NOT NULL DEFAULT 1
                )
            """)

            # Check if default admin user exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'Kodongo'")
            if cursor.fetchone()[0] == 0:
                default_password = self._hash_password("Kodongo123")
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ('Kodongo', default_password, 'Admin')
                )

            conn.commit()

    def _get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _hash_password(password):
        """Hash the password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()


class SQLiteUserSystem:
    def __init__(self):
        # Initialize network manager
        self.network_manager = NetworkManager()

        # Initialize database paths
        self.data_folder = self.network_manager.initialize_data_folder()
        self.db_path = os.path.join(self.data_folder, "kodongo_loans.db")
        self.shared_mode = self.network_manager.shared_mode

        # Start sync thread
        self.network_manager.start_sync_thread()

        # Initialize database
        self.db_manager = DatabaseManager(self.db_path, self.network_manager)
        self.cycles_path = self.db_path
    def _initialize_paths(self):
        """Initialize all file paths consistently"""
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            if sys.platform == "win32":
                self.data_folder = os.path.join(os.getenv('APPDATA'), "KodongoLoanSystem")
            elif sys.platform == "darwin":
                self.data_folder = os.path.expanduser("~/Library/Application Support/KodongoLoanSystem")
            else:  # Linux
                self.data_folder = os.path.expanduser("~/.local/share/KodongoLoanSystem")
        else:
            # Running in development
            self.data_folder = os.path.dirname(os.path.abspath(__file__))

        self.db_path = os.path.join(self.data_folder, "kodongo_loans.db")

    def validate_login(self, username, password):
        """Validate user login credentials"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()

            if not result:
                return False, "Invalid username"

            stored_hash = result[0]
            input_hash = self.db_manager._hash_password(password)

            return (stored_hash == input_hash,
                    "Login successful" if stored_hash == input_hash else "Invalid password")

    def change_password(self, username, old_password, new_password):
        """Change user password after validating old password"""
        # Validate password complexity
        valid, message = self._validate_password_complexity(new_password)
        if not valid:
            return False, message

        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Verify old password
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()

            if not result:
                return False, "User not found"

            stored_hash = result[0]
            input_hash = self.db_manager._hash_password(old_password)

            if stored_hash != input_hash:
                return False, "Old password is incorrect"

            # Update password
            new_hash = self.db_manager._hash_password(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (new_hash, username)
            )
            conn.commit()

            return True, "Password changed successfully"

    def _validate_password_complexity(self, password):
        """Check if password meets complexity requirements"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one number"
        return True, "Password meets requirements"

    def add_loan(self, loan_data):
        """Add a new loan to the system"""
        try:
            # Calculate loan details
            amount = float(loan_data['amount'])
            payment_per_day = float(loan_data['payment_per_day'])
            term_months = int(loan_data['term_months'])

            # Calculate total to repay
            days_in_term = term_months * 30
            total_to_repay = payment_per_day * days_in_term

            # Calculate end date
            start_date = datetime.strptime(loan_data['start_date'], "%Y-%m-%d")
            end_date = start_date + timedelta(days=days_in_term)

            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Insert loan record
                cursor.execute("""
                    INSERT INTO loans (
                        customer_name, amount, payment_per_day, term_months,
                        start_date, end_date, total_to_repay, status,
                        created_by, remaining_balance, physical_address,
                        national_id, phone_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    loan_data['customer_name'],
                    amount,
                    payment_per_day,
                    term_months,
                    loan_data['start_date'],
                    end_date.strftime("%Y-%m-%d"),
                    total_to_repay,
                    loan_data.get('status', 'Active'),
                    loan_data['created_by'],
                    total_to_repay,
                    loan_data.get('physical_address', ''),
                    loan_data.get('national_id', ''),
                    loan_data.get('phone_number', '')
                ))

                loan_id = cursor.lastrowid
                conn.commit()

                return True, "Loan added successfully"

        except Exception as e:
            return False, f"Error saving loan: {str(e)}"

    def get_loans_data(self):
        """Get all loans data"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    loan_id, customer_name, amount, payment_per_day,
                    term_months, start_date, end_date, total_to_repay,
                    status, created_by, remaining_balance, physical_address,
                    national_id, phone_number
                FROM loans
            """)

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                return pd.DataFrame(columns=columns)

            return pd.DataFrame(rows, columns=columns)

    def get_loan_details(self, loan_id):
        """Get details for a specific loan"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Get loan details
                cursor.execute("""
                    SELECT 
                        loan_id, customer_name, amount, payment_per_day,
                        term_months, start_date, end_date, total_to_repay,
                        status, created_by, remaining_balance, physical_address,
                        national_id, phone_number
                    FROM loans
                    WHERE loan_id = ?
                """, (loan_id,))

                loan_data = cursor.fetchone()

                if not loan_data:
                    return None, None

                # Get column names
                columns = [desc[0] for desc in cursor.description]
                loan_dict = dict(zip(columns, loan_data))

                # Get payments for this loan
                cursor.execute("""
                    SELECT 
                        payment_id, date, amount, received_by, notes
                    FROM payments
                    WHERE loan_id = ?
                    ORDER BY date DESC
                """, (loan_id,))

                payments = cursor.fetchall()
                payment_columns = [desc[0] for desc in cursor.description]
                payments_df = pd.DataFrame(payments, columns=payment_columns) if payments else pd.DataFrame()

                return loan_dict, payments_df

        except Exception as e:
            messagebox.showerror("Error", f"Could not load loan details: {str(e)}")
            return None, None

    def update_loan(self, loan_id, updated_data):
        """Update a loan record"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Get current loan data
                cursor.execute("""
                    SELECT 
                        payment_per_day, term_months, start_date, status,
                        total_to_repay
                    FROM loans
                    WHERE loan_id = ?
                """, (loan_id,))

                current_data = cursor.fetchone()
                if not current_data:
                    return False, "Loan not found", None

                # Calculate any derived fields
                if 'payment_per_day' in updated_data or 'term_months' in updated_data:
                    payment = float(updated_data.get('payment_per_day', current_data[0]))
                    term = int(updated_data.get('term_months', current_data[1]))
                    updated_data['total_to_repay'] = payment * (term * 30)

                    if updated_data.get('status', current_data[3]) == 'Active':
                        updated_data['remaining_balance'] = updated_data['total_to_repay']
                    else:
                        updated_data['remaining_balance'] = 0

                # Update dates if needed
                if 'start_date' in updated_data or 'term_months' in updated_data:
                    start_date = datetime.strptime(
                        updated_data.get('start_date', current_data[2]),
                        "%Y-%m-%d"
                    )
                    term_months = int(updated_data.get('term_months', current_data[1]))
                    updated_data['end_date'] = (start_date + timedelta(days=term_months * 30)).strftime("%Y-%m-%d")

                # Build update query
                set_clauses = []
                params = []

                for field, value in updated_data.items():
                    set_clauses.append(f"{field} = ?")
                    params.append(value)

                params.append(loan_id)

                update_query = f"""
                    UPDATE loans
                    SET {', '.join(set_clauses)}, last_updated = CURRENT_TIMESTAMP
                    WHERE loan_id = ?
                """

                cursor.execute(update_query, params)
                conn.commit()

                # Get updated loan data
                cursor.execute("""
                    SELECT 
                        loan_id, customer_name, amount, payment_per_day,
                        term_months, start_date, end_date, total_to_repay,
                        status, created_by, remaining_balance, physical_address,
                        national_id, phone_number
                    FROM loans
                    WHERE loan_id = ?
                """, (loan_id,))

                updated_loan = cursor.fetchone()
                columns = [desc[0] for desc in cursor.description]
                updated_loan_dict = dict(zip(columns, updated_loan))

                return True, "Loan updated successfully", updated_loan_dict

        except Exception as e:
            return False, f"Error updating loan: {str(e)}", None

    def add_payment(self, loan_id, payment_data):
        """Add a payment to a loan"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Verify loan exists
                cursor.execute("SELECT status, total_to_repay, remaining_balance FROM loans WHERE loan_id = ?",
                               (loan_id,))
                loan = cursor.fetchone()

                if not loan:
                    return False, "Loan not found", None

                status, total_to_repay, current_balance = loan

                # Add payment record
                cursor.execute("""
                    INSERT INTO payments (
                        loan_id, date, amount, received_by, notes
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    loan_id,
                    payment_data['date'],
                    float(payment_data['amount']),
                    payment_data['received_by'],
                    payment_data.get('notes', '')
                ))

                payment_id = cursor.lastrowid

                # Update loan balance
                payment_amount = float(payment_data['amount'])
                new_balance = max(0, current_balance - payment_amount)

                # Update status if fully paid
                new_status = status
                if new_balance <= 0:
                    new_status = "Paid"
                    new_balance = 0

                cursor.execute("""
                    UPDATE loans
                    SET remaining_balance = ?, status = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE loan_id = ?
                """, (new_balance, new_status, loan_id))

                conn.commit()

                # Return updated loan data
                loans_df = self.get_loans_data()
                return True, "Payment recorded successfully", loans_df

        except Exception as e:
            return False, f"Error processing payment: {str(e)}", None

    def get_loan_cycle(self, customer_name, national_id="", phone_number=""):
        """Get loan cycle count for a customer"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Try matching by most reliable identifier first
                if phone_number:
                    cursor.execute("""
                        SELECT loan_cycles FROM loan_cycles
                        WHERE phone_number = ?
                    """, (phone_number,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]

                # Fallback to national_id if available
                if national_id:
                    cursor.execute("""
                        SELECT loan_cycles FROM loan_cycles
                        WHERE national_id = ?
                    """, (national_id,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]

                # Final fallback - name only
                cursor.execute("""
                    SELECT loan_cycles FROM loan_cycles
                    WHERE customer_name = ?
                """, (customer_name,))
                result = cursor.fetchone()

                return result[0] if result else 1

        except Exception as e:
            print(f"Error in get_loan_cycle: {str(e)}")
            return 1  # Always return 1 if any error occurs

    def update_loan_cycle(self, customer_name, national_id="", phone_number=""):
        """Update loan cycle count for a customer"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Find existing record
                if phone_number:
                    cursor.execute("""
                        SELECT id FROM loan_cycles
                        WHERE phone_number = ?
                    """, (phone_number,))
                    result = cursor.fetchone()
                elif national_id:
                    cursor.execute("""
                        SELECT id FROM loan_cycles
                        WHERE national_id = ?
                    """, (national_id,))
                    result = cursor.fetchone()
                else:
                    cursor.execute("""
                        SELECT id FROM loan_cycles
                        WHERE customer_name = ?
                    """, (customer_name,))
                    result = cursor.fetchone()

                if result:
                    # Update existing record
                    cursor.execute("""
                        UPDATE loan_cycles
                        SET loan_cycles = loan_cycles + 1
                        WHERE id = ?
                    """, (result[0],))
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO loan_cycles (
                            customer_name, national_id, phone_number, loan_cycles
                        ) VALUES (?, ?, ?, 1)
                    """, (customer_name, national_id, phone_number))

                conn.commit()
                return True

        except Exception as e:
            print(f"Error in update_loan_cycle: {str(e)}")
            return False

    def get_daily_financial_summary(self):
        """Calculate all required financial metrics"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Get total amount given
            cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM loans")
            amount_given = cursor.fetchone()[0]

            # Get outstanding balance
            cursor.execute("SELECT COALESCE(SUM(remaining_balance), 0) FROM loans")
            outstanding = cursor.fetchone()[0]

            # Get total interest
            cursor.execute("SELECT COALESCE(SUM(total_to_repay - amount), 0) FROM loans")
            total_interest = cursor.fetchone()[0]

            # Get today's payments
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM payments
                WHERE date = ?
            """, (today,))
            daily_paid = cursor.fetchone()[0]

            # Count active and paid loans
            cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Active'")
            active_loans = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Paid'")
            paid_loans = cursor.fetchone()[0]

            return {
                'amount_given': amount_given,
                'outstanding': outstanding,
                'total_interest': total_interest,
                'daily_paid': daily_paid,
                'active_loans': active_loans,
                'paid_loans': paid_loans
            }

    def get_payment_compliance_report(self):
        """Get list of loans with payment compliance status"""
        today = datetime.now().strftime("%Y-%m-%d")

        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Get active loans and their payment status for today
            cursor.execute("""
                SELECT 
                    l.loan_id, l.customer_name, l.payment_per_day,
                    CASE WHEN p.payment_id IS NOT NULL THEN 'Yes' ELSE 'No' END as paid_today,
                    COALESCE(MAX(p.date), 'Never') as last_payment
                FROM loans l
                LEFT JOIN payments p ON l.loan_id = p.loan_id AND p.date = ?
                WHERE l.status = 'Active'
                GROUP BY l.loan_id, l.customer_name, l.payment_per_day, paid_today
            """, (today,))

            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            if not results:
                return pd.DataFrame(columns=columns)

            return pd.DataFrame(results, columns=columns)

    def generate_payments_summary_report(self):
        """Generate summary report of all payments"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Get loan summary with payment info
            cursor.execute("""
                SELECT 
                    l.loan_id, l.customer_name, l.amount as loan_amount,
                    COALESCE(SUM(p.amount), 0) as total_paid,
                    l.remaining_balance as remaining,
                    l.status,
                    COALESCE(MAX(p.date), 'Never') as last_payment
                FROM loans l
                LEFT JOIN payments p ON l.loan_id = p.loan_id
                GROUP BY l.loan_id, l.customer_name, l.amount, l.remaining_balance, l.status
            """)

            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            if not results:
                return pd.DataFrame(columns=columns)

            return pd.DataFrame(results, columns=columns)

    def reset_daily_payments(self):
        """Reset daily payments tracking and clean up old loans"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Archive and delete paid loans older than 24 hours
                cutoff_time = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

                # Get loans to archive
                cursor.execute("""
                    SELECT * FROM loans
                    WHERE status = 'Paid' 
                    AND last_updated < ?
                """, (cutoff_time,))

                old_loans = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                # Delete these loans
                cursor.execute("""
                    DELETE FROM loans
                    WHERE status = 'Paid' 
                    AND last_updated < ?
                """, (cutoff_time,))

                # Also delete their payments
                cursor.execute("""
                    DELETE FROM payments
                    WHERE loan_id IN (
                        SELECT loan_id FROM loans
                        WHERE status = 'Paid'
                        AND last_updated < ?
                    )
                """, (cutoff_time,))

                conn.commit()

                return {
                    'paid_loans': len(old_loans),
                    'active_loans': self.get_daily_financial_summary()['active_loans']
                }

        except Exception as e:
            print(f"Error in reset_daily_payments: {str(e)}")
            return None

    def get_missed_payments(self, loan_id):
        """Calculate accumulated missed payments for a loan"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()

            # Get loan details
            cursor.execute("""
                SELECT payment_per_day, start_date, status
                FROM loans
                WHERE loan_id = ?
            """, (loan_id,))

            loan = cursor.fetchone()
            if not loan:
                return 0

            daily_payment, start_date_str, status = loan

            # If loan is paid, no missed payments
            if status == "Paid":
                return 0

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()

            # Calculate expected payment days
            expected_days = (today - start_date).days + 1

            # Get actual unique payment days
            cursor.execute("""
                SELECT COUNT(DISTINCT date) 
                FROM payments
                WHERE loan_id = ?
            """, (loan_id,))

            unique_payment_days = cursor.fetchone()[0] or 0

            # Calculate missed days and accumulated amount
            missed_days = max(0, expected_days - unique_payment_days)
            accumulated_amount = missed_days * daily_payment

            return accumulated_amount

    def settle_missed_payments(self, loan_id, amount):
        """Record a payment to settle accumulated missed payments"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Add payment record
                cursor.execute("""
                    INSERT INTO payments (
                        loan_id, date, amount, received_by, notes
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    loan_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    float(amount),
                    "System (Missed Payments Settlement)",
                    "Settlement of accumulated missed payments"
                ))

                # Update loan balance
                cursor.execute("""
                    UPDATE loans
                    SET remaining_balance = remaining_balance - ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE loan_id = ?
                """, (float(amount), loan_id))

                # Check if loan is now paid
                cursor.execute("""
                    UPDATE loans
                    SET status = 'Paid'
                    WHERE loan_id = ? AND remaining_balance <= 0
                """, (loan_id,))

                conn.commit()

                # Return updated loan data
                return True, "Missed payments settled successfully", self.get_loans_data()

        except Exception as e:
            return False, f"Error settling missed payments: {str(e)}", None

    def process_daily_operations(self):
        """Handle all daily operations including payments and cleanup"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                today = datetime.now().strftime("%Y-%m-%d")

                # Process daily payments for active loans
                cursor.execute("""
                    UPDATE loans
                    SET remaining_balance = remaining_balance - payment_per_day,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE status = 'Active'
                """)

                # Mark loans as paid if balance <= 0
                cursor.execute("""
                    UPDATE loans
                    SET status = 'Paid',
                        remaining_balance = 0
                    WHERE status = 'Active' AND remaining_balance <= 0
                """)

                # Record payments for all active loans
                cursor.execute("""
                    INSERT INTO payments (loan_id, date, amount, received_by, notes)
                    SELECT 
                        loan_id, ?, payment_per_day, 'System', 'Daily auto-payment'
                    FROM loans
                    WHERE status = 'Active'
                """, (today,))

                # Get daily collection amount
                cursor.execute("""
                    SELECT SUM(payment_per_day) FROM loans
                    WHERE status = 'Active'
                """)
                daily_collection = cursor.fetchone()[0] or 0

                # Count active loans
                cursor.execute("SELECT COUNT(*) FROM loans WHERE status = 'Active'")
                active_loans = cursor.fetchone()[0]

                # Clean up paid loans older than 24 hours
                cutoff_time = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    SELECT COUNT(*) FROM loans
                    WHERE status = 'Paid' 
                    AND last_updated < ?
                """, (cutoff_time,))
                paid_loans = cursor.fetchone()[0]

                cursor.execute("""
                    DELETE FROM loans
                    WHERE status = 'Paid' 
                    AND last_updated < ?
                """, (cutoff_time,))

                cursor.execute("""
                    DELETE FROM payments
                    WHERE loan_id IN (
                        SELECT loan_id FROM loans
                        WHERE status = 'Paid'
                        AND last_updated < ?
                    )
                """, (cutoff_time,))

                conn.commit()

                return {
                    'daily_collection': daily_collection,
                    'active_loans': active_loans,
                    'paid_loans': paid_loans
                }

        except Exception as e:
            print(f"Error in daily operations: {str(e)}")
            return None


class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Initialize after_ids before any other operations
        self.after_ids = set()

        # Configure window
        self.title("Kodongo Loan System")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        # With platform-specific window management:
        if sys.platform == "win32":
            self.after(100, lambda: self.state('zoomed'))  # Windows
        elif sys.platform == "darwin":
            self.after(100, lambda: self.attributes('-zoomed', True))  # macOS
        else:
            self.after(100, lambda: self.attributes('-zoomed', True))  # Li
        # Handle DPI scaling
        self._set_dpi_awareness()

        # Initialize user system
        self.user_system = SQLiteUserSystem()
        self.current_user = None

        # Setup UI
        self._setup_ui()
        self.after_ids = set()  # Track scheduled callbacks
        self._loan_detail_window = None  # Track detail window
        self.after(1000, self.check_network_status)

    def check_network_status(self):
        """Check and display network status"""
        if hasattr(self, 'user_system') and hasattr(self.user_system, 'network_manager'):
            if self.user_system.network_manager.shared_mode:
                status = "Connected to network share"
                color = "green"
            else:
                status = "Using local storage (network unavailable)"
                color = "orange"

            if hasattr(self, 'status_label'):
                self.status_label.configure(text=status, text_color=color)

        # Check every minute
        self.after(60000, self.check_network_status)

    def _cleanup_callbacks(self):
        """Cancel all pending callbacks"""
        for after_id in list(self.after_ids):
            try:
                self.after_cancel(after_id)
                self.after_ids.remove(after_id)
            except:
                pass

    def show_loan_details(self, loan_id):
        """Safely show loan details window"""
        self._cleanup_callbacks()

        # Close existing window if it exists
        if self._loan_detail_window is not None:
            try:
                self._loan_detail_window.destroy()
            except:
                pass

        # Create new window
        self._loan_detail_window = LoanDetailWindow(self, loan_id, self.user_system)
        self._position_window(self._loan_detail_window)

        # Set up proper destruction handler
        self._loan_detail_window.protocol("WM_DELETE_WINDOW", self._on_detail_window_close)

    def _on_detail_window_close(self):
        """Handle detail window closing"""
        if self._loan_detail_window is not None:
            try:
                self._loan_detail_window.destroy()
            except:
                pass
        self._loan_detail_window = None

    def _position_window(self, window):
        """Center a window on screen"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"+{x}+{y}")

    def _setup_ui(self):
        """Initialize the main UI container"""
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Show login frame by default
        self.show_login_frame()

    def _set_dpi_awareness(self):
        """Handle high DPI displays on Windows"""
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass

    def _cleanup_after_calls(self):
        """Cancel all pending after() calls"""
        if hasattr(self, 'after_ids'):
            for after_id in list(self.after_ids):
                try:
                    self.after_cancel(after_id)
                    self.after_ids.remove(after_id)
                except:
                    pass

    def __del__(self):
        """Clean up when window is destroyed"""
        self._cleanup_after_calls()

    def show_login_frame(self):
        """Display the modern login form"""
        self._cleanup_after_calls()
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()

        # Main login frame
        login_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        login_frame.pack(expand=True, fill="both", padx=100, pady=50)

        # Left side - Branding
        left_frame = ctk.CTkFrame(login_frame, fg_color="transparent", width=400)
        left_frame.pack(side="left", fill="y", expand=False, padx=20, pady=20)

        # Logo/Title
        ctk.CTkLabel(
            left_frame,
            text="Kodongo\nLoan System",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#2e8b57",
            justify="center"
        ).pack(pady=50)

        ctk.CTkLabel(
            left_frame,
            text="Modern Financial Management",
            font=ctk.CTkFont(size=18),
            text_color="gray70"
        ).pack()

        # Right side - Login Form
        right_frame = ctk.CTkFrame(
            login_frame,
            width=400,
            corner_radius=15,
            border_width=1,
            border_color="gray20"
        )
        right_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # Form header
        ctk.CTkLabel(
            right_frame,
            text="Welcome Back",
            font=ctk.CTkFont(size=24, weight="bold"),
            pady=30
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            right_frame,
            text="Sign in to continue",
            font=ctk.CTkFont(size=14),
            text_color="gray70"
        ).pack(pady=(0, 30))

        # Form fields
        form_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        form_frame.pack(fill="x", padx=40, pady=10)

        # Username field
        ctk.CTkLabel(
            form_frame,
            text="Username",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(5, 0))

        self.username_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Enter your username",
            height=45,
            corner_radius=8
        )
        self.username_entry.pack(fill="x", pady=(5, 15))

        # Password field
        ctk.CTkLabel(
            form_frame,
            text="Password",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(5, 0))

        self.password_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Enter your password",
            show="•",
            height=45,
            corner_radius=8
        )
        self.password_entry.pack(fill="x", pady=(5, 5))

        # Remember me checkbox
        remember_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        remember_frame.pack(fill="x", pady=(5, 20))

        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            remember_frame,
            text="Remember me",
            variable=self.remember_var
        ).pack(side="left")

        # Login button
        login_button = ctk.CTkButton(
            form_frame,
            text="Login",
            command=self.login,
            height=45,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2e8b57",
            hover_color="#3cb371"
        )
        login_button.pack(fill="x", pady=(10, 20))

        # Footer note
        ctk.CTkLabel(
            form_frame,
            text="Need help? Contact system administrator",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        ).pack(pady=(20, 10))

    def login(self):
        """Handle login attempt"""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return

        success, message = self.user_system.validate_login(username, password)

        if success:
            self.current_user = username
            messagebox.showinfo("Success", message)
            self.show_dashboard()
        else:
            messagebox.showerror("Error", message)

    def show_dashboard(self):
        # Clear container and cancel any pending after() events
        for widget in self.container.winfo_children():
            widget.destroy()

        # Cancel any pending after events
        for after_id in self.after_ids:
            self.after_cancel(after_id)
        self.after_ids.clear()

        # Main container with padding
        main_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header frame with welcome message and buttons
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        # Welcome message with user role
        welcome_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        welcome_frame.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            welcome_frame,
            text=f"Welcome back, {self.current_user}",
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            welcome_frame,
            text="Loan Management Dashboard",
            font=ctk.CTkFont(size=14),
            text_color="gray70",
            anchor="w"
        ).pack(fill="x")

        # Action buttons frame
        action_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        action_frame.pack(side="right")

        # Change password button
        ctk.CTkButton(
            action_frame,
            text="Change Password",
            command=self.show_change_password_frame,
            width=150,
            height=35,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        ).pack(side="left", padx=5)

        # Reports button
        ctk.CTkButton(
            action_frame,
            text="Reports",
            command=self.show_reports_window,
            width=100,
            height=35,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

        # Logout button
        ctk.CTkButton(
            action_frame,
            text="Logout",
            command=self.show_login_frame,
            width=100,
            height=35,
            fg_color="#e74c3c",
            hover_color="#c0392b"
        ).pack(side="left", padx=5)

        # Create tab view for all sections
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True, pady=(0, 10))

        # Add all tabs
        self.tabview.add("View Loans")
        self.tabview.add("Add Loan")
        self.tabview.add("Loan Payments")

        # Configure each tab
        self._setup_view_loans_tab()
        self._setup_add_loan_tab()
        self._setup_loan_payments_tab()
        self._cleanup_callbacks()  # Clean up before creating new UI

    def _setup_view_loans_tab(self):
        """Configure the View Loans tab with status filtering"""
        tab = self.tabview.tab("View Loans")

        # Search and filter frame
        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 10), padx=5)

        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by name or loan ID...",
            height=40
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.filter_loans())

        # Search button
        ctk.CTkButton(
            search_frame,
            text="Search",
            width=100,
            height=40,
            command=self.filter_loans
        ).pack(side="left", padx=(0, 10))

        # Status filter dropdown
        self.status_filter = ctk.CTkComboBox(
            search_frame,
            values=["All", "Active", "Paid", "Defaulted", "Overdue"],
            width=120,
            height=40
        )
        self.status_filter.set("All")
        self.status_filter.pack(side="left")

        # Loans table
        self.loans_scroll_frame = ctk.CTkScrollableFrame(
            tab,
            border_width=1,
            border_color="gray20"
        )
        self.loans_scroll_frame.pack(fill="both", expand=True)

        # Display all loans initially
        self.display_loans(self.user_system.get_loans_data())

    def display_loans(self, loans_df):
        """Display loans with status coloring"""
        # Clear existing loans
        for widget in self.loans_scroll_frame.winfo_children():
            widget.destroy()

        if loans_df.empty:
            ctk.CTkLabel(
                self.loans_scroll_frame,
                text="No loans found",
                font=ctk.CTkFont(size=14),
                text_color="gray70"
            ).pack(pady=50)
            return

        # Header row
        header_frame = ctk.CTkFrame(
            self.loans_scroll_frame,
            fg_color="#2c3e50",
            height=40
        )
        header_frame.pack(fill="x", pady=(0, 5))

        headers = [
            ("ID", 80), ("Customer", 180), ("Amount", 120),
            ("Daily", 100), ("Term", 80), ("Total", 120),
            ("Status", 120), ("", 160)
        ]

        for col, (header, width) in enumerate(headers):
            ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                text_color="white",
                width=width
            ).grid(row=0, column=col, padx=2)

        # Loan rows
        for _, loan in loans_df.iterrows():
            self._create_loan_row(loan)

    def _create_loan_row(self, loan):
        """Create a loan row with dynamic status coloring"""
        loan_frame = ctk.CTkFrame(self.loans_scroll_frame)
        loan_frame.pack(fill="x", pady=2)

        # Determine status and color
        status, color = self._determine_loan_status(loan)

        # Loan ID
        ctk.CTkLabel(
            loan_frame,
            text=str(loan['loan_id']),
            width=80
        ).grid(row=0, column=0, padx=5)

        # Customer Name
        ctk.CTkLabel(
            loan_frame,
            text=str(loan['customer_name']),
            width=120
        ).grid(row=0, column=1, padx=10)

        # Amount
        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['amount']:,.2f}",
            width=80
        ).grid(row=0, column=2, padx=10)

        # Daily Payment
        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['payment_per_day']:,.2f}",
            width=80
        ).grid(row=0, column=3, padx=10)

        # Term
        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['term_months']} months",
            width=80
        ).grid(row=0, column=4, padx=10)

        # Total to Repay
        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['total_to_repay']:,.2f}",
            width=120
        ).grid(row=0, column=5, padx=10)

        # Status label (dynamic color)
        status_label = ctk.CTkLabel(
            loan_frame,
            text=status,
            width=100,
            text_color="white",
            fg_color=color,
            corner_radius=4
        )
        status_label.grid(row=0, column=6, padx=5)

        # Action buttons frame
        btn_frame = ctk.CTkFrame(loan_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=7, padx=5)

        # View button
        ctk.CTkButton(
            btn_frame,
            text="View",
            width=70,
            command=lambda lid=loan['loan_id']: self._safe_show_loan_details(lid)
        ).pack(side="left", padx=2)

        # Edit button with dropdown menu
        edit_menu = ctk.CTkSegmentedButton(
            btn_frame,
            values=["Edit", "Delete"],
            width=140,
            command=lambda v, lid=loan['loan_id']: self._handle_loan_action(v, lid)
        )
        edit_menu.pack(side="left", padx=2)
        edit_menu.set("Options")  # Default display text

    def _safe_show_loan_details(self, loan_id):
        """Wrapper to prevent callback errors"""
        try:
            self.show_loan_details(loan_id)
        except Exception as e:
            messagebox.showerror("Error", f"Could not show loan details: {str(e)}")

    def _handle_loan_action(self, action, loan_id):
        """Handle edit/delete actions"""
        if action == "Edit":
            self.show_edit_loan_window(loan_id)
        elif action == "Delete":
            self._confirm_delete_loan(loan_id)

    def _confirm_delete_loan(self, loan_id):
        """Show confirmation dialog before deletion"""
        confirm = ctk.CTkToplevel(self)
        confirm.title("Confirm Deletion")
        confirm.geometry("500x300")
        confirm.grab_set()  # Make modal

        # Center the window
        confirm.update_idletasks()
        width = confirm.winfo_width()
        height = confirm.winfo_height()
        x = (confirm.winfo_screenwidth() // 2) - (width // 2)
        y = (confirm.winfo_screenheight() // 2) - (height // 2)
        confirm.geometry(f"+{x}+{y}")

        # Content
        ctk.CTkLabel(
            confirm,
            text=f"Confirm permanent deletion of Loan ID {loan_id}?",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=20)

        ctk.CTkLabel(
            confirm,
            text="This will remove all loan records permanently!",
            text_color="red"
        ).pack()

        # Admin password entry
        ctk.CTkLabel(confirm, text="Admin Password:").pack(pady=5)
        password_entry = ctk.CTkEntry(confirm, show="*", width=200)
        password_entry.pack()

        # Buttons
        btn_frame = ctk.CTkFrame(confirm)
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Delete",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=lambda: self._execute_delete(loan_id, password_entry.get(), confirm),
            width=100
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=confirm.destroy,
            width=100
        ).pack(side="right", padx=10)

    def _execute_delete(self, loan_id, password, confirm_window):
        """Perform the actual deletion after validation"""
        # Verify admin password
        valid, _ = self.user_system.validate_login("Kodongo", password)
        if not valid:
            messagebox.showerror("Error", "Invalid admin password")
            return

        try:
            with self.user_system.db_manager._get_connection() as conn:
                cursor = conn.cursor()

                # Delete loan payments first
                cursor.execute("DELETE FROM payments WHERE loan_id = ?", (loan_id,))

                # Then delete the loan
                cursor.execute("DELETE FROM loans WHERE loan_id = ?", (loan_id,))

                conn.commit()

                # Refresh UI
                loans_df = self.user_system.get_loans_data()
                self.display_loans(loans_df)
                messagebox.showinfo("Success", f"Loan ID {loan_id} permanently deleted")
                confirm_window.destroy()

                # Refresh parent views if available
                if hasattr(self.master, 'display_loans'):
                    self.master.display_loans(loans_df)

        except Exception as e:
            messagebox.showerror("Error", f"Deletion failed: {str(e)}")

    def _determine_loan_status(self, loan):
        """Determine status text and color for a loan"""
        today = datetime.now().date()
        end_date = datetime.strptime(loan['end_date'], "%Y-%m-%d").date()

        if loan['status'] == 'Paid':
            return "Paid", "#2ecc71"  # Green

        if today > end_date and float(loan['remaining_balance']) > 0:
            return "Overdue", "#e67e22"  # Orange

        if loan['status'] == 'Defaulted':
            return "Defaulted", "#e74c3c"  # Red

        return "Active", "#3498db"  # Blue

    def filter_loans(self):
        """Filter loans based on search term and status"""
        search_term = self.search_entry.get().strip().lower()
        status_filter = self.status_filter.get()

        loans_df = self.user_system.get_loans_data()

        # Apply status filter first
        if status_filter != "All":
            if status_filter == "Overdue":
                today = datetime.now().date()
                loans_df = loans_df[
                    (loans_df['status'] == 'Active') &
                    (loans_df['end_date'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date()) < today) &
                    (loans_df['remaining_balance'].astype(float) > 0)
                    ]
            else:
                loans_df = loans_df[loans_df['status'] == status_filter]

        # Apply search term
        if search_term:
            try:
                # Try searching by loan ID
                loan_id = int(search_term)
                loans_df = loans_df[loans_df['loan_id'] == loan_id]
            except ValueError:
                # Search by customer name if not numeric
                loans_df = loans_df[
                    loans_df['customer_name'].str.lower().str.contains(search_term)
                ]

        self.display_loans(loans_df)

    def _setup_add_loan_tab(self):
        """Setup the Add Loan tab with working functionality"""
        tab = self.tabview.tab("Add Loan")

        # Form container with padding
        form_frame = ctk.CTkFrame(tab, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Form fields with modern styling
        fields = [
            ("customer_name", "Customer Name"),
            ("amount", "Loan Amount (KES)"),
            ("payment_per_day", "Daily Payment (KES)"),
            ("term_months", "Term (months)"),
            ("start_date", "Start Date (YYYY-MM-DD)"),
            ("physical_address", "Physical Address"),
            ("national_id", "National ID"),
            ("phone_number", "Phone Number")
        ]

        self.loan_entries = {}

        for i, (field, label) in enumerate(fields):
            # Field frame
            field_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            field_frame.pack(fill="x", pady=5)

            # Label
            ctk.CTkLabel(
                field_frame,
                text=label,
                font=ctk.CTkFont(weight="bold"),
                width=180,
                anchor="w"
            ).pack(side="left", padx=5)

            # Entry field
            entry = ctk.CTkEntry(
                field_frame,
                height=35,
                corner_radius=8,
                border_width=1,
                border_color="#e0e0e0"
            )
            entry.pack(side="right", fill="x", expand=True)
            self.loan_entries[field] = entry

        # Set default values
        self.loan_entries['term_months'].insert(0, "1")
        self.loan_entries['start_date'].insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Button frame
        button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=10)

        # Calculate button
        ctk.CTkButton(
            button_frame,
            text="Calculate Total Repayment",
            command=self.calculate_repayment,
            height=40,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5, fill="x", expand=True)

        # Submit button with working functionality
        ctk.CTkButton(
            button_frame,
            text="Add Loan",
            command=self._execute_add_loan,
            height=40,
            fg_color="#2ecc71",
            hover_color="#27ae60"
        ).pack(side="right", padx=5, fill="x", expand=True)

        # Total repayment display
        self.total_repay_label = ctk.CTkLabel(
            form_frame,
            text="Total to repay: KES 0.00",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2e8b57"
        )
        self.total_repay_label.pack(pady=2)

    def _execute_add_loan(self):
        """Handle the Add Loan button click with validation and status"""
        try:
            # Validate required fields
            required_fields = ['customer_name', 'amount', 'payment_per_day', 'term_months', 'start_date']
            for field in required_fields:
                if not self.loan_entries[field].get().strip():
                    raise ValueError(f"{field.replace('_', ' ').title()} is required")

            # Prepare loan data with status included
            loan_data = {
                'customer_name': self.loan_entries['customer_name'].get(),
                'amount': float(self.loan_entries['amount'].get()),
                'payment_per_day': float(self.loan_entries['payment_per_day'].get()),
                'term_months': int(self.loan_entries['term_months'].get()),
                'start_date': self.loan_entries['start_date'].get(),
                'status': 'Active',  # Explicitly set status to Active for new loans
                'physical_address': self.loan_entries['physical_address'].get(),
                'national_id': self.loan_entries['national_id'].get(),
                'phone_number': self.loan_entries['phone_number'].get(),
                'created_by': self.current_user
            }

            # Call the user system to add loan
            success, message = self.user_system.add_loan(loan_data)

            if success:
                messagebox.showinfo("Success", message)
                self._clear_loan_form()
                # Refresh the loans display if available
                if hasattr(self, 'display_loans'):
                    self.display_loans(self.user_system.get_loans_data())
            else:
                messagebox.showerror("Error", message)

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("System Error", f"Failed to add loan: {str(e)}")

    def _clear_loan_form(self):
        """Clear all fields in the add loan form"""
        for entry in self.loan_entries.values():
            entry.delete(0, 'end')
        self.total_repay_label.configure(text="Total to repay: KES 0.00")
        # Reset default values
        self.loan_entries['term_months'].insert(0, "1")
        self.loan_entries['start_date'].insert(0, datetime.now().strftime("%Y-%m-%d"))

    def calculate_repayment(self):
        """Calculate total repayment amount"""
        try:
            payment_per_day = float(self.loan_entries['payment_per_day'].get())
            term_months = int(self.loan_entries['term_months'].get())

            if term_months < 1:
                raise ValueError("Term must be at least 1 month")

            # Calculate total repayment (payment_per_day * days_in_term)
            days_in_term = term_months * 30
            total_to_repay = payment_per_day * days_in_term

            self.total_repay_label.configure(
                text=f"Total to repay: KES {total_to_repay:,.2f}",
                text_color="#2e8b57"
            )
        except ValueError as e:
            messagebox.showerror("Calculation Error", f"Invalid input: {str(e)}")

    def _setup_loan_payments_tab(self):
        """Refresh the Loan Payments tab with updated data"""
        tab = self.tabview.tab("Loan Payments")

        # Clear existing widgets
        for widget in tab.winfo_children():
            widget.destroy()

        # Get updated data
        loans_df = self.user_system.get_loans_data()
        summary = self.user_system.get_daily_financial_summary()

        # Rebuild the UI with fresh data
        self._create_financial_summary_section(tab, summary)
        self._create_daily_operations_section(tab)
        self._create_loan_status_section(tab, loans_df)

    def _create_financial_summary_section(self, parent, summary_data):
        """Create financial summary section"""
        section_frame = ctk.CTkFrame(parent, border_width=1, corner_radius=10)
        section_frame.pack(fill="x", pady=(0, 5), padx=5)

        # Section title
        ctk.CTkLabel(
            section_frame,
            text="Financial Summary",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(5, 5))

        # Grid layout for metrics
        grid_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5, padx=10)

        # Financial metrics to display
        metrics = [
            ("Total Amount Given", f"KES {summary_data['amount_given']:,.2f}", "#2ecc71"),
            ("Outstanding Balance", f"KES {summary_data['outstanding']:,.2f}",
             "#e74c3c" if summary_data['outstanding'] > 0 else "#2ecc71"),
            ("Total Interest", f"KES {summary_data['total_interest']:,.2f}", "#f39c12"),
            ("Today's Payments", f"KES {summary_data['daily_paid']:,.2f}", "#3498db")
        ]

        # Create metric rows
        for i, (label, value, color) in enumerate(metrics):
            row_frame = ctk.CTkFrame(grid_frame, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", pady=2)

            ctk.CTkLabel(
                row_frame,
                text=label + ":",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
                width=180
            ).pack(side="left", padx=5)

            ctk.CTkLabel(
                row_frame,
                text=value,
                font=ctk.CTkFont(size=12),
                text_color=color,
                anchor="e"
            ).pack(side="right", padx=5)

    def _create_daily_operations_section(self, parent):
        """Create daily operations section"""
        section_frame = ctk.CTkFrame(parent, border_width=1, corner_radius=10)
        section_frame.pack(fill="x", pady=(0, 5), padx=5)

        ctk.CTkLabel(
            section_frame,
            text="Daily Operations",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(5, 5))

        # Button frame
        btn_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5, padx=10)

        # Reset button
        self.reset_btn = ctk.CTkButton(
            btn_frame,
            text="Reset Daily Payments",
            command=self._reset_daily_payments,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=40
        )
        self.reset_btn.pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            btn_frame,
            text="Click at midnight to reset daily totals",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        self.status_label.pack(side="left", padx=10)

    def _create_loan_status_section(self, parent, loans_df):
        """Create loan status overview section"""
        section_frame = ctk.CTkFrame(parent, border_width=1, corner_radius=10)
        section_frame.pack(fill="x", pady=(0, 10), padx=5)

        ctk.CTkLabel(
            section_frame,
            text="Loan Portfolio Status",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(5, 5))

        # Status frame
        status_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        status_frame.pack(fill="x", pady=5, padx=10)

        # Count loans by status
        active_loans = len(loans_df[loans_df['status'] == 'Active'])
        paid_loans = len(loans_df[loans_df['status'] == 'Paid'])

        # Status cards
        statuses = [
            ("Active Loans", active_loans, "#2ecc71"),
            ("Paid Loans", paid_loans, "#3498db")
        ]

        for i, (label, count, color) in enumerate(statuses):
            card = ctk.CTkFrame(
                status_frame,
                border_width=1,
                border_color="#e0e0e0",
                corner_radius=8,
                height=80
            )
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            status_frame.columnconfigure(i, weight=1)

            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=color
            ).pack(pady=(10, 0))

            ctk.CTkLabel(
                card,
                text=str(count),
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(0, 10))

        # Refresh button
        refresh_btn = ctk.CTkButton(
            section_frame,
            text="🔄 Refresh Data",
            command=lambda: self._setup_loan_payments_tab(),
            width=150,
            height=35,
            fg_color="#2e8b57",
            hover_color="#3cb371"
        )
        refresh_btn.pack(pady=(0, 5))

    def _reset_daily_payments(self):
        """Handle daily reset operation"""
        confirm = messagebox.askyesno(
            "Confirm Reset",
            "This will reset daily payment totals and remove loans paid >24hrs ago.\nContinue?"
        )
        if not confirm:
            return

        self.reset_btn.configure(state="disabled", text="Resetting...")
        self.status_label.configure(text="Processing daily reset...")
        self.update()

        try:
            summary = self.user_system.reset_daily_payments()
            if summary:
                self._setup_loan_payments_tab()  # Refresh the tab
                messagebox.showinfo(
                    "Success",
                    f"Daily reset completed:\n"
                    f"- Removed {summary.get('paid_loans', 0)} paid loans\n"
                    f"- Daily totals reset"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Daily reset failed: {str(e)}")
        finally:
            self.reset_btn.configure(state="normal", text="Reset Daily Payments")

    def show_change_password_frame(self):
        """Display the password change form"""
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()

        # Title
        title_label = ctk.CTkLabel(
            self.container,
            text="Change Password",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)

        # Old password entry
        old_pass_label = ctk.CTkLabel(self.container, text="Current Password:")
        old_pass_label.pack(pady=5)
        self.old_pass_entry = ctk.CTkEntry(
            self.container,
            show="*",
            width=250
        )
        self.old_pass_entry.pack(pady=5)

        # New password entry
        new_pass_label = ctk.CTkLabel(self.container, text="New Password:")
        new_pass_label.pack(pady=5)
        self.new_pass_entry = ctk.CTkEntry(
            self.container,
            show="*",
            width=250
        )
        self.new_pass_entry.pack(pady=5)

        # Password requirements label
        requirements_label = ctk.CTkLabel(
            self.container,
            text="Password must be at least 8 characters with:\n- One uppercase letter\n- One lowercase letter\n- One number",
            text_color="gray",
            justify="left"
        )
        requirements_label.pack(pady=5)

        # Confirm new password entry
        confirm_pass_label = ctk.CTkLabel(self.container, text="Confirm New Password:")
        confirm_pass_label.pack(pady=5)
        self.confirm_pass_entry = ctk.CTkEntry(
            self.container,
            show="*",
            width=250
        )
        self.confirm_pass_entry.pack(pady=5)

        # Submit button
        submit_button = ctk.CTkButton(
            self.container,
            text="Change Password",
            command=self.change_password,
            width=250,
            height=40
        )
        submit_button.pack(pady=20)

        # Back button
        back_button = ctk.CTkButton(
            self.container,
            text="Back to Dashboard",
            command=self.show_dashboard,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        back_button.pack(pady=10)

    def change_password(self):
        """Handle password change request"""
        old_password = self.old_pass_entry.get()
        new_password = self.new_pass_entry.get()
        confirm_password = self.confirm_pass_entry.get()

        if not old_password or not new_password or not confirm_password:
            messagebox.showerror("Error", "All fields are required")
            return

        if new_password != confirm_password:
            messagebox.showerror("Error", "New passwords don't match")
            return

        success, message = self.user_system.change_password(
            self.current_user,
            old_password,
            new_password
        )

        if success:
            messagebox.showinfo("Success", message)
            self.show_dashboard()
        else:
            messagebox.showerror("Error", message)

    def show_reports_window(self):
        """Show the reports management window"""
        # Create new window
        reports_window = ctk.CTkToplevel(self)
        reports_window.title("Loan Reports")
        reports_window.geometry("1100x750")

        # Make window responsive
        reports_window.grid_rowconfigure(0, weight=1)
        reports_window.grid_columnconfigure(0, weight=1)

        # Create notebook for tabs
        notebook = ctk.CTkTabview(reports_window)
        notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Add tabs
        notebook.add("Payment Compliance")
        notebook.add("Payments Summary")

        # Build tabs
        self._build_compliance_tab(notebook.tab("Payment Compliance"))
        self._build_summary_tab(notebook.tab("Payments Summary"))

        # Close button
        close_btn = ctk.CTkButton(
            reports_window,
            text="Close",
            command=reports_window.destroy,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            height=40
        )
        close_btn.grid(row=1, column=0, pady=10)

    def _build_compliance_tab(self, tab):
        """Build payment compliance tab with search functionality"""
        tab.grid_rowconfigure(2, weight=1)  # Changed from 1 to 2 to accommodate search frame
        tab.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            header_frame,
            text="Daily Payment Compliance",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Action buttons
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Refresh",
            command=lambda: self._refresh_compliance(tab),
            width=100
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Print",
            command=self._print_compliance_report,
            width=100
        ).pack(side="left", padx=5)

        # Search/Filter frame
        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))

        ctk.CTkLabel(
            search_frame,
            text="Filter by Payment Status:",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=5)

        # Payment status filter dropdown
        self.payment_filter = ctk.CTkComboBox(
            search_frame,
            values=["All", "Yes", "No"],
            width=100,
            command=lambda _: self._filter_compliance_data()
        )
        self.payment_filter.pack(side="left", padx=5)
        self.payment_filter.set("All")

        # Search by name/ID
        self.compliance_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by name or ID...",
            width=200
        )
        self.compliance_search_entry.pack(side="left", padx=5)
        self.compliance_search_entry.bind("<Return>", lambda _: self._filter_compliance_data())

        ctk.CTkButton(
            search_frame,
            text="Search",
            command=self._filter_compliance_data,
            width=80
        ).pack(side="left", padx=5)

        # Create scrollable frame for table
        self.compliance_frame = ctk.CTkScrollableFrame(tab)
        self.compliance_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # Load initial data
        self._load_compliance_data()

    def _filter_compliance_data(self):
        """Filter compliance data based on search criteria"""
        # Get the original data
        df = self.user_system.get_payment_compliance_report()
        if df.empty:
            return

        # Apply payment status filter
        payment_filter = self.payment_filter.get()
        if payment_filter == "Yes":
            df = df[df['paid_today'] == 'Yes']
        elif payment_filter == "No":
            df = df[df['paid_today'] == 'No']

        # Apply search term filter
        search_term = self.compliance_search_entry.get().lower()
        if search_term:
            df = df[
                df['customer_name'].str.lower().str.contains(search_term) |
                df['loan_id'].astype(str).str.contains(search_term)
                ]

        # Clear existing widgets
        for widget in self.compliance_frame.winfo_children():
            widget.destroy()

        if df.empty:
            ctk.CTkLabel(
                self.compliance_frame,
                text="No matching records found",
                font=ctk.CTkFont(size=12)
            ).pack(pady=20)
            return

        # Create headers
        headers = ["Loan ID", "Customer", "Daily Amount", "Paid Today", "Last Payment"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(
                self.compliance_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                width=150 if col != 1 else 200,
                anchor="w"
            ).grid(row=0, column=col, padx=5, pady=5, sticky="w")

        # Add filtered data rows
        for row, (_, item) in enumerate(df.iterrows(), 1):
            ctk.CTkLabel(
                self.compliance_frame,
                text=str(item['loan_id']),
                width=150,
                anchor="w"
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")

            ctk.CTkLabel(
                self.compliance_frame,
                text=str(item['customer_name']),
                width=200,
                anchor="w"
            ).grid(row=row, column=1, padx=5, pady=2, sticky="w")

            ctk.CTkLabel(
                self.compliance_frame,
                text=f"KES {float(item['daily_amount']):,.2f}",
                width=150,
                anchor="w"
            ).grid(row=row, column=2, padx=5, pady=2, sticky="w")

            paid_color = "#27ae60" if item['paid_today'] == 'Yes' else "#e74c3c"
            ctk.CTkLabel(
                self.compliance_frame,
                text=item['paid_today'],
                text_color=paid_color,
                width=150,
                anchor="w"
            ).grid(row=row, column=3, padx=5, pady=2, sticky="w")

            ctk.CTkLabel(
                self.compliance_frame,
                text=str(item['last_payment']),
                width=150,
                anchor="w"
            ).grid(row=row, column=4, padx=5, pady=2, sticky="w")

    def _load_compliance_data(self):
        """Load payment compliance data into the table"""
        # Clear existing widgets
        for widget in self.compliance_frame.winfo_children():
            widget.destroy()

        # Get data from system
        compliance_data = self.user_system.get_payment_compliance_report()

        if compliance_data.empty:
            ctk.CTkLabel(
                self.compliance_frame,
                text="No active loans found",
                font=ctk.CTkFont(size=12)
            ).pack(pady=20)
            return

        # Create headers
        headers = ["Loan ID", "Customer", "Daily Amount", "Paid Today", "Last Payment"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(
                self.compliance_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                width=150 if col != 1 else 200,
                anchor="w"
            ).grid(row=0, column=col, padx=5, pady=5, sticky="w")

        # Add data rows
        for row, (_, loan) in enumerate(compliance_data.iterrows(), 1):
            # Loan ID
            ctk.CTkLabel(
                self.compliance_frame,
                text=str(loan['loan_id']),
                width=150,
                anchor="w"
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")

            # Customer Name
            ctk.CTkLabel(
                self.compliance_frame,
                text=str(loan['customer_name']),
                width=200,
                anchor="w"
            ).grid(row=row, column=1, padx=5, pady=2, sticky="w")

            # Daily Amount
            ctk.CTkLabel(
                self.compliance_frame,
                text=f"KES {float(loan['payment_per_day']):,.2f}",
                width=150,
                anchor="w"
            ).grid(row=row, column=2, padx=5, pady=2, sticky="w")

            # Paid Today (with color coding)
            paid_color = "#27ae60" if loan['paid_today'] == 'Yes' else "#e74c3c"
            ctk.CTkLabel(
                self.compliance_frame,
                text=str(loan['paid_today']),
                text_color=paid_color,
                width=150,
                anchor="w"
            ).grid(row=row, column=3, padx=5, pady=2, sticky="w")

            # Last Payment
            ctk.CTkLabel(
                self.compliance_frame,
                text=str(loan['last_payment']),
                width=150,
                anchor="w"
            ).grid(row=row, column=4, padx=5, pady=2, sticky="w")

    def _refresh_compliance(self, tab):
        """Refresh compliance data"""
        self._load_compliance_data()
        messagebox.showinfo("Refreshed", "Compliance data updated")

    def _print_compliance_report(self):
        """Generate PDF of compliance report"""
        try:
            from fpdf import FPDF
            import os

            df = self.user_system.get_payment_compliance_report()
            if df.empty:
                messagebox.showwarning("No Data", "No compliance data to print")
                return

            pdf = FPDF()
            pdf.add_page()

            # Title
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Daily Payment Compliance Report", 0, 1, 'C')
            pdf.ln(10)

            # Date
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
            pdf.ln(5)

            # Table header
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(30, 10, "Loan ID", 1, 0, 'C', 1)
            pdf.cell(50, 10, "Customer", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Daily Amount", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Paid Today", 1, 0, 'C', 1)
            pdf.cell(40, 10, "Last Payment", 1, 1, 'C', 1)

            # Table data
            pdf.set_font("Arial", '', 10)
            for _, row in df.iterrows():
                pdf.cell(30, 10, str(row['loan_id']), 1)
                pdf.cell(50, 10, str(row['customer_name']), 1)
                pdf.cell(30, 10, f"KES {float(row['daily_amount']):,.2f}", 1)
                pdf.cell(30, 10, str(row['paid_today']), 1)
                pdf.cell(40, 10, str(row['last_payment']), 1)
                pdf.ln()

            # Save file
            filename = f"compliance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")],
                initialfile=filename
            )

            if filepath:
                pdf.output(filepath)
                messagebox.showinfo("Success", f"Report saved to:\n{filepath}")
                os.startfile(filepath)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")

    def _build_summary_tab(self, tab):
        """Build payments summary tab"""
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            header_frame,
            text="Payments Summary Report",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Buttons
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="Refresh",
            command=lambda: self._refresh_summary(tab),
            width=100
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Print",
            command=self._print_summary_report,
            width=100
        ).pack(side="left", padx=5)

        # Create scrollable frame
        self.summary_frame = ctk.CTkScrollableFrame(tab)
        self.summary_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Load initial data
        self._load_summary_data()

    def _load_summary_data(self):
        """Load payments summary data into the table"""
        # Clear existing widgets
        for widget in self.summary_frame.winfo_children():
            widget.destroy()

        # Get data from system
        summary_data = self.user_system.generate_payments_summary_report()

        if summary_data.empty:
            ctk.CTkLabel(
                self.summary_frame,
                text="No loan data found",
                font=ctk.CTkFont(size=12)
            ).pack(pady=20)
            return

        # Create headers
        headers = ["Loan ID", "Customer", "Loan Amount", "Total Paid", "Remaining", "Status"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(
                self.summary_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                width=120 if col != 1 else 150,
                anchor="w"
            ).grid(row=0, column=col, padx=5, pady=5, sticky="w")

        # Add data rows
        for row, (_, loan) in enumerate(summary_data.iterrows(), 1):
            # Loan ID
            ctk.CTkLabel(
                self.summary_frame,
                text=str(loan['loan_id']),
                width=120,
                anchor="w"
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")

            # Customer Name
            ctk.CTkLabel(
                self.summary_frame,
                text=str(loan['customer_name']),
                width=150,
                anchor="w"
            ).grid(row=row, column=1, padx=5, pady=2, sticky="w")

            # Loan Amount
            ctk.CTkLabel(
                self.summary_frame,
                text=f"KES {float(loan['loan_amount']):,.2f}",
                width=120,
                anchor="w"
            ).grid(row=row, column=2, padx=5, pady=2, sticky="w")

            # Total Paid
            ctk.CTkLabel(
                self.summary_frame,
                text=f"KES {float(loan['total_paid']):,.2f}",
                width=120,
                anchor="w"
            ).grid(row=row, column=3, padx=5, pady=2, sticky="w")

            # Remaining (color coded)
            remaining_color = "#e74c3c" if float(loan['remaining']) > 0 else "#27ae60"
            ctk.CTkLabel(
                self.summary_frame,
                text=f"KES {float(loan['remaining']):,.2f}",
                text_color=remaining_color,
                width=120,
                anchor="w"
            ).grid(row=row, column=4, padx=5, pady=2, sticky="w")

            # Status (color coded)
            status_color = "#27ae60" if loan['status'] == 'Paid' else "#f39c12"
            ctk.CTkLabel(
                self.summary_frame,
                text=str(loan['status']),
                text_color=status_color,
                width=120,
                anchor="w"
            ).grid(row=row, column=5, padx=5, pady=2, sticky="w")

    def _refresh_summary(self, tab):
        """Refresh summary data"""
        self._load_summary_data()
        messagebox.showinfo("Updated", "Payments summary data refreshed")

    def _print_summary_report(self):
        """Generate PDF of payments summary report"""
        try:
            from fpdf import FPDF
            import os

            df = self.user_system.generate_payments_summary_report()
            if df.empty:
                messagebox.showwarning("No Data", "No payment data to print")
                return

            pdf = FPDF()
            pdf.add_page()

            # Title
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Payments Summary Report", 0, 1, 'C')
            pdf.ln(10)

            # Date
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", 0, 1)
            pdf.ln(5)

            # Table header
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(25, 10, "Loan ID", 1, 0, 'C', 1)
            pdf.cell(45, 10, "Customer", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Loan Amount", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Total Paid", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Remaining", 1, 0, 'C', 1)
            pdf.cell(25, 10, "Status", 1, 1, 'C', 1)

            # Table data
            pdf.set_font("Arial", '', 10)
            for _, row in df.iterrows():
                pdf.cell(25, 10, str(row['loan_id']), 1)
                pdf.cell(45, 10, str(row['customer_name']), 1)
                pdf.cell(30, 10, f"KES {float(row['loan_amount']):,.2f}", 1)
                pdf.cell(30, 10, f"KES {float(row['total_paid']):,.2f}", 1)
                pdf.cell(30, 10, f"KES {float(row['remaining']):,.2f}", 1)
                pdf.cell(25, 10, str(row['status']), 1)
                pdf.ln()

            # Save file
            filename = f"payments_summary_{datetime.now().strftime('%Y%m%d')}.pdf"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")],
                initialfile=filename
            )

            if filepath:
                pdf.output(filepath)
                messagebox.showinfo("Success", f"Report saved to:\n{filepath}")
                os.startfile(filepath)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")

    def show_edit_loan_window(self, loan_id):
        """Show edit window with proper refresh handling"""
        loan_data, _ = self.user_system.get_loan_details(loan_id)
        if not loan_data:
            messagebox.showerror("Error", "Loan not found")
            return

        edit_window = ctk.CTkToplevel(self)
        edit_window.title(f"Edit Loan ID {loan_id}")
        edit_window.geometry("500x600")
        edit_window.after(100, edit_window.grab_set)

        # Center window
        edit_window.update_idletasks()
        width = edit_window.winfo_width()
        height = edit_window.winfo_height()
        x = (edit_window.winfo_screenwidth() // 2) - (width // 2)
        y = (edit_window.winfo_screenheight() // 2) - (height // 2)
        edit_window.geometry(f"+{x}+{y}")

        # Form fields
        fields = [
            ("customer_name", "Customer Name"),
            ("amount", "Loan Amount (KES)"),
            ("payment_per_day", "Daily Payment (KES)"),
            ("term_months", "Term (months)"),
            ("start_date", "Start Date (YYYY-MM-DD)"),
            ("physical_address", "Physical Address"),
            ("national_id", "National ID"),
            ("phone_number", "Phone Number"),
            ("status", "Status")
        ]

        entries = {}
        for i, (field, label) in enumerate(fields):
            ctk.CTkLabel(edit_window, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="w")

            if field == "status":
                status_var = ctk.StringVar(value=loan_data.get(field, 'Active'))
                dropdown = ctk.CTkComboBox(
                    edit_window,
                    variable=status_var,
                    values=["Active", "Paid", "Defaulted"],
                    state="readonly"
                )
                dropdown.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                entries[field] = status_var
            else:
                entry = ctk.CTkEntry(edit_window)
                entry.insert(0, str(loan_data.get(field, "")))
                entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                entries[field] = entry

        def update_loan():
            """Handle the update with complete refresh"""
            try:
                updated_data = {
                    'customer_name': entries['customer_name'].get(),
                    'amount': float(entries['amount'].get()),
                    'payment_per_day': float(entries['payment_per_day'].get()),
                    'term_months': int(entries['term_months'].get()),
                    'start_date': entries['start_date'].get(),
                    'status': entries['status'].get(),
                    'physical_address': entries['physical_address'].get(),
                    'national_id': entries['national_id'].get(),
                    'phone_number': entries['phone_number'].get()
                }

                success, message, updated_loan = self.user_system.update_loan(loan_id, updated_data)
                if success:
                    messagebox.showinfo("Success", message)
                    edit_window.destroy()

                    # Force complete refresh of all views
                    loans_df = self.user_system.get_loans_data()

                    # Refresh main loans list
                    if hasattr(self, 'display_loans'):
                        self.display_loans(loans_df)

                    # Refresh detail window if open
                    if hasattr(self, '_loan_detail_window') and self._loan_detail_window:
                        if self._loan_detail_window.winfo_exists() and str(self._loan_detail_window.loan_id) == str(
                                loan_id):
                            # Get fresh data including payments
                            loan_data, payments_df = self.user_system.get_loan_details(loan_id)
                            if loan_data:
                                self._loan_detail_window.loan_data = loan_data
                                self._loan_detail_window.payments_df = payments_df
                                self._loan_detail_window.refresh_data(loan_data)

                    # Refresh reports/payments tabs
                    if hasattr(self, '_setup_loan_payments_tab'):
                        self._setup_loan_payments_tab()

                    if hasattr(self, 'reports_window') and self.reports_window.winfo_exists():
                        self.reports_window._refresh_compliance_tab()
                        self.reports_window._refresh_summary_tab()

                else:
                    messagebox.showerror("Error", message)

            except ValueError as e:
                messagebox.showerror("Input Error", f"Invalid input: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update loan: {str(e)}")

        update_button = ctk.CTkButton(
            edit_window,
            text="Update Loan",
            command=update_loan,
            height=40
        )
        update_button.grid(row=len(fields) + 1, column=0, columnspan=2, pady=20)

    def clear_search(self):
        """Clear search and show all loans"""
        self.search_entry.delete(0, 'end')
        self.display_loans(self.user_system.get_loans_data())


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()

