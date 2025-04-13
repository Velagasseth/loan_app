import os
import pandas as pd
import customtkinter as ctk
from tkinter import messagebox
import hashlib
import re
from datetime import datetime, timedelta
import time
from threading import Thread
from PIL import Image, ImageTk
import itertools


class WelcomePage(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._after_ids = set()  # Using set to avoid duplicates
        self._running = True
        self._thread = None

        # Configure window
        self.title("Kodongo Loan System")
        self.geometry("800x500")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.protocol("WM_DELETE_WINDOW", self._safe_destroy)
        self.resizable(False, False)

        # Center the window
        self._center_window()

        # Create main container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        # Show welcome content
        self._show_welcome_content()

        # Start loading animation after 2 seconds
        self._schedule(self._start_loading, 2000)

    def _schedule(self, func, delay):
        """Safely schedule an after event"""
        after_id = self.after(delay, func)
        self._after_ids.add(after_id)
        return after_id

    def _center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = 800  # Fixed width since window isn't visible yet
        height = 500
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _show_welcome_content(self):
        """Display welcome content"""
        for widget in self.container.winfo_children():
            widget.destroy()

        logo_label = ctk.CTkLabel(
            self.container,
            text="Kodongo Loan System",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="#3498db"
        )
        logo_label.pack(pady=40)

        title_label = ctk.CTkLabel(
            self.container,
            text="Loan Management System",
            font=ctk.CTkFont(size=24),
            text_color="white"
        )
        title_label.pack(pady=10)

        self.loading_label = ctk.CTkLabel(
            self.container,
            text="Initializing system...",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.loading_label.pack(pady=30)

    def _start_loading(self):
        """Start loading animation"""
        if not self._running:
            return

        self.loading_label.configure(text="Loading system components")
        self.loading_dots = itertools.cycle([".", "..", "..."])
        self._animate_dots()

        self.progress = ctk.CTkProgressBar(
            self.container,
            width=300,
            height=4,
            mode="indeterminate"
        )
        self.progress.pack(pady=10)
        self.progress.start()

        # Start loading thread
        self._thread = Thread(target=self._simulate_loading, daemon=True)
        self._thread.start()

    def _animate_dots(self):
        """Animate loading dots"""
        if not self._running:
            return

        current_text = self.loading_label.cget("text")
        if current_text.endswith("..."):
            current_text = current_text[:-3]
        self.loading_label.configure(text=current_text + next(self.loading_dots))
        self._schedule(self._animate_dots, 500)

    def _simulate_loading(self):
        """Simulate loading process"""
        for i in range(1, 4):
            if not self._running:
                return
            time.sleep(1)
            if self._running:
                self.loading_label.configure(text=f"Loading system components... ({i}/3)")

        if self._running:
            self._transition_to_login()

    def _transition_to_login(self):
        """Transition to login page"""
        if not self._running:
            return

        self.loading_label.configure(text="System ready! Redirecting to login...")
        self._schedule(self._open_login_page, 1000)

    def _open_login_page(self):
        """Open login page"""
        if not self._running:
            return

        self._safe_destroy()
        LoginApp().mainloop()

    def _safe_destroy(self):
        """Safely destroy the window with cleanup"""
        self._running = False

        # Cancel all scheduled events
        for after_id in self._after_ids:
            try:
                self.after_cancel(after_id)
            except:
                pass
        self._after_ids.clear()

        # Stop progress bar if exists
        if hasattr(self, 'progress'):
            try:
                self.progress.stop()
            except:
                pass

        # Wait for thread to finish if running
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

        # Destroy window
        try:
            self.destroy()
        except:
            pass


def migrate_existing_loans():
    """Run this once to add remaining_balance to existing loans"""
    user_system = ExcelUserSystem()
    loans_df = user_system.get_loans_data()

    if not loans_df.empty and 'remaining_balance' not in loans_df.columns:
        if 'total_to_repay' in loans_df.columns:
            loans_df['remaining_balance'] = loans_df['total_to_repay']
        else:
            loans_df['remaining_balance'] = loans_df['amount']

        loans_df.to_excel(user_system.loans_path, index=False, engine='openpyxl')
        print("Successfully migrated loan data")
    else:
        print("No migration needed")


# Run this once:
# migrate_existing_loans()
class ExcelUserSystem:
    def __init__(self):
        """Initialize the user system with Excel backend"""
        self.data_folder = "app_data"
        self.users_file = "users.xlsx"
        self.loans_file = "loans.xlsx"
        self.file_path = os.path.join(self.data_folder, self.users_file)
        self.loans_path = os.path.join(self.data_folder, self.loans_file)

        # Create folder and files if they don't exist
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

        # Initialize files
        self._initialize_files()

    def _initialize_files(self):
        """Create Excel files with required structure if they don't exist"""
        # Users file initialization (unchanged)

        # Master loans file
        if not os.path.exists(self.loans_path):
            columns = [
                'loan_id', 'customer_name', 'amount', 'payment_per_day',
                'term_months', 'start_date', 'end_date', 'total_to_repay',
                'status', 'created_by', 'loan_file', 'remaining_balance'  # Added this column
            ]
            df = pd.DataFrame(columns=columns)
            df.to_excel(self.loans_path, index=False, engine='openpyxl')

    def _hash_password(self, password):
        """Hash the password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

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

    def validate_login(self, username, password):
        """Validate user login credentials"""
        try:
            users_df = pd.read_excel(self.file_path, engine='openpyxl')
        except FileNotFoundError:
            return False, "System error: User database not found"

        user = users_df[users_df['username'] == username]

        if user.empty:
            return False, "Invalid username"

        stored_hash = user.iloc[0]['password_hash']
        input_hash = self._hash_password(password)

        if stored_hash == input_hash:
            return True, "Login successful"
        else:
            return False, "Invalid password"

    def change_password(self, username, old_password, new_password):
        """Change user password after validating old password"""
        # Validate password complexity
        valid, message = self._validate_password_complexity(new_password)
        if not valid:
            return False, message

        try:
            users_df = pd.read_excel(self.file_path, engine='openpyxl')
        except FileNotFoundError:
            return False, "System error: User database not found"

        user_index = users_df.index[users_df['username'] == username].tolist()
        if not user_index:
            return False, "User not found"

        user_index = user_index[0]

        # Verify old password
        stored_hash = users_df.at[user_index, 'password_hash']
        input_hash = self._hash_password(old_password)

        if stored_hash != input_hash:
            return False, "Old password is incorrect"

        # Update password
        users_df.at[user_index, 'password_hash'] = self._hash_password(new_password)

        try:
            users_df.to_excel(self.file_path, index=False, engine='openpyxl')
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Error saving changes: {str(e)}"

    def get_loans_data(self):
        """Load loans data from Excel with default values for missing columns"""
        try:
            loans_df = pd.read_excel(self.loans_path, engine='openpyxl')

            # Ensure required columns exist
            if 'remaining_balance' not in loans_df.columns:
                if 'total_to_repay' in loans_df.columns:
                    loans_df['remaining_balance'] = loans_df['total_to_repay']  # Initialize balance
                else:
                    loans_df['remaining_balance'] = loans_df['amount']  # Fallback to original amount

            return loans_df
        except FileNotFoundError:
            return pd.DataFrame()

    def add_loan(self, loan_data):
        """Add a new loan to the system"""
        try:
            loans_df = self.get_loans_data()

            # Generate loan ID
            new_id = 1 if loans_df.empty else loans_df['loan_id'].max() + 1

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

            # Create loan filename
            loan_filename = f"loan_{new_id}.xlsx"
            loan_filepath = os.path.join(self.data_folder, loan_filename)

            # Prepare loan data
            loan_record = {
                'loan_id': new_id,
                'customer_name': loan_data['customer_name'],
                'amount': amount,
                'payment_per_day': payment_per_day,
                'term_months': term_months,
                'start_date': loan_data['start_date'],
                'end_date': end_date.strftime("%Y-%m-%d"),
                'total_to_repay': total_to_repay,
                'status': 'Active',
                'created_by': loan_data['created_by'],
                'loan_file': loan_filename,
                'remaining_balance': total_to_repay
            }

            # Convert to DataFrame properly
            new_loan_df = pd.DataFrame([loan_record])

            # Handle empty loans_df case
            if loans_df.empty:
                loans_df = new_loan_df
            else:
                loans_df = pd.concat([loans_df, new_loan_df], ignore_index=True)

            # Create payment records sheet
            payments_df = pd.DataFrame(columns=['payment_id', 'date', 'amount', 'received_by', 'notes'])

            # Save to Excel
            with pd.ExcelWriter(loan_filepath, engine='openpyxl') as writer:
                pd.DataFrame([loan_record]).to_excel(writer, sheet_name='Loan Details', index=False)
                payments_df.to_excel(writer, sheet_name='Payments', index=False)

            # Save master file
            loans_df.to_excel(self.loans_path, index=False, engine='openpyxl')

            return True, "Loan added successfully"  # Now returns exactly 2 values

        except Exception as e:
            return False, f"Error saving loan: {str(e)}"  # Now returns exactly 2 values

    def get_loan_details(self, loan_id):

        """Get details for a specific loan"""
        loan_file = self._get_loan_filename(loan_id)
        if not loan_file:
            return None

        loan_filepath = os.path.join(self.data_folder, loan_file)
        try:
            details_df = pd.read_excel(loan_filepath, sheet_name='Loan Details', engine='openpyxl')
            payments_df = pd.read_excel(loan_filepath, sheet_name='Payments', engine='openpyxl')
            return details_df.iloc[0].to_dict(), payments_df
        except Exception as e:
            messagebox.showerror("Error", f"Could not load loan details: {str(e)}")
            return None

    def _get_loan_filename(self, loan_id):
        """Get the filename for a specific loan"""
        loans_df = self.get_loans_data()
        loan = loans_df[loans_df['loan_id'] == loan_id]
        if loan.empty:
            return None
        return loan.iloc[0]['loan_file']

    def add_payment(self, loan_id, payment_data):
        """Add a payment to a loan"""
        try:
            # Get loan filename from master file
            loans_df = self.get_loans_data()
            loan_record = loans_df[loans_df['loan_id'] == loan_id]

            if loan_record.empty:
                return False, "Loan not found"

            loan_file = loan_record.iloc[0]['loan_file']
            loan_filepath = os.path.join(self.data_folder, loan_file)

            # Read existing data
            details_df = pd.read_excel(loan_filepath, sheet_name='Loan Details', engine='openpyxl')
            payments_df = pd.read_excel(loan_filepath, sheet_name='Payments', engine='openpyxl')

            # Generate payment ID
            new_payment_id = 1 if payments_df.empty else payments_df['payment_id'].max() + 1

            # Add payment record
            payment_record = {
                'payment_id': new_payment_id,
                'date': payment_data['date'],
                'amount': float(payment_data['amount']),
                'received_by': payment_data['received_by'],
                'notes': payment_data.get('notes', '')
            }
            payments_df = pd.concat([payments_df, pd.DataFrame([payment_record])], ignore_index=True)

            # Update loan details
            payment_amount = float(payment_data['amount'])
            current_balance = float(details_df.at[0, 'remaining_balance'])
            new_balance = max(0, current_balance - payment_amount)  # Prevent negative balance

            details_df.at[0, 'remaining_balance'] = new_balance
            details_df.at[0, 'last_payment_date'] = payment_data['date']
            details_df.at[0, 'last_payment_amount'] = payment_amount

            # Update status if fully paid
            if new_balance <= 0:
                details_df.at[0, 'status'] = "Paid"
                # Update master file status
                loan_index = loans_df.index[loans_df['loan_id'] == loan_id].tolist()[0]
                loans_df.at[loan_index, 'status'] = "Paid"
                loans_df.at[loan_index, 'remaining_balance'] = 0
                loans_df.to_excel(self.loans_path, index=False, engine='openpyxl')

            # Save updated data
            with pd.ExcelWriter(loan_filepath, engine='openpyxl') as writer:
                details_df.to_excel(writer, sheet_name='Loan Details', index=False)
                payments_df.to_excel(writer, sheet_name='Payments', index=False)

            return True, "Payment recorded successfully"

        except Exception as e:
            return False, f"Error recording payment: {str(e)}"


class LoanDetailWindow(ctk.CTkToplevel):
    def __init__(self, parent, loan_id, user_system):
        super().__init__(parent)
        self.loan_id = loan_id
        self.user_system = user_system
        self.current_user = parent.current_user

        # Configure window
        self.title(f"Loan Details - ID {loan_id}")
        self.geometry("600x500")
        self.master = parent

        # Load loan data
        self.loan_data, self.payments_df = self.user_system.get_loan_details(loan_id)
        if not self.loan_data:
            self.destroy()
            return

        # Create main container
        self.container = ctk.CTkFrame(self)
        self.container.pack(pady=20, padx=20, fill="both", expand=True)

        # Display loan information
        self._display_loan_info()

        # Payment section
        self._setup_payment_section()

        # Payments history
        self._setup_payments_history()

    def _display_loan_info(self):
        """Display the loan information section"""
        info_frame = ctk.CTkFrame(self.container)
        info_frame.pack(fill="x", pady=5, padx=5)

        # Loan details
        details = [
            ("Customer:", self.loan_data['customer_name']),
            ("Loan Amount:", f"KES {self.loan_data['amount']:,.2f}"),
            ("Daily Payment:", f"KES {self.loan_data['payment_per_day']:,.2f}"),
            ("Term:", f"{self.loan_data['term_months']} months"),
            ("Start Date:", self.loan_data['start_date']),
            ("End Date:", self.loan_data['end_date']),
            ("Total to Repay:", f"KES {self.loan_data['total_to_repay']:,.2f}"),
            ("Remaining Balance:", f"KES {self.loan_data['remaining_balance']:,.2f}"),
            ("Status:", self.loan_data['status'])
        ]

        for i, (label, value) in enumerate(details):
            ctk.CTkLabel(info_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(row=i, column=0, sticky="w",
                                                                                       padx=5, pady=2)
            ctk.CTkLabel(info_frame, text=value).grid(row=i, column=1, sticky="w", padx=5, pady=2)

    def _setup_payment_section(self):
        """Setup the payment entry section"""
        payment_frame = ctk.CTkFrame(self.container)
        payment_frame.pack(fill="x", pady=10, padx=5)

        # Payment amount
        ctk.CTkLabel(payment_frame, text="Payment Amount (KES):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.payment_amount_entry = ctk.CTkEntry(payment_frame)
        self.payment_amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Payment date
        ctk.CTkLabel(payment_frame, text="Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.payment_date_entry = ctk.CTkEntry(payment_frame)
        self.payment_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.payment_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Notes
        ctk.CTkLabel(payment_frame, text="Notes:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.payment_notes_entry = ctk.CTkEntry(payment_frame)
        self.payment_notes_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Add payment button
        add_button = ctk.CTkButton(
            payment_frame,
            text="Record Payment",
            command=self.record_payment,
            height=40
        )
        add_button.grid(row=3, column=0, columnspan=2, pady=10)

    def _setup_payments_history(self):
        """Setup the payments history section"""
        history_frame = ctk.CTkFrame(self.container)
        history_frame.pack(fill="both", expand=True, pady=5, padx=5)

        # Title
        ctk.CTkLabel(history_frame, text="Payment History", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(history_frame)
        scroll_frame.pack(fill="both", expand=True)

        if self.payments_df.empty:
            ctk.CTkLabel(scroll_frame, text="No payments recorded yet").pack(pady=20)
            return

        # Header row
        header_frame = ctk.CTkFrame(scroll_frame)
        header_frame.pack(fill="x", pady=2)

        headers = ["Date", "Amount (KES)", "Received By", "Notes"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                width=120 if i != 3 else 200
            ).grid(row=0, column=i, padx=2)

        # Payment rows
        for _, payment in self.payments_df.iterrows():
            payment_frame = ctk.CTkFrame(scroll_frame)
            payment_frame.pack(fill="x", pady=2)

            ctk.CTkLabel(
                payment_frame,
                text=payment['date'],
                width=120
            ).grid(row=0, column=0, padx=2)

            ctk.CTkLabel(
                payment_frame,
                text=f"{payment['amount']:,.2f}",
                width=120
            ).grid(row=0, column=1, padx=2)

            ctk.CTkLabel(
                payment_frame,
                text=payment['received_by'],
                width=120
            ).grid(row=0, column=2, padx=2)

            ctk.CTkLabel(
                payment_frame,
                text=payment['notes'],
                width=200
            ).grid(row=0, column=3, padx=2)

    def record_payment(self):
        """Handle payment recording"""
        amount = self.payment_amount_entry.get()
        date = self.payment_date_entry.get()
        notes = self.payment_notes_entry.get()

        if not amount or not date:
            messagebox.showerror("Error", "Amount and date are required")
            return

        try:
            payment_data = {
                'date': date,
                'amount': float(amount),
                'received_by': self.current_user,
                'notes': notes if notes else ""
            }

            success, message = self.master.user_system.add_payment(self.loan_id, payment_data)

            if success:
                messagebox.showinfo("Success", message)
                # Refresh data
                self.loan_data, self.payments_df = self.master.user_system.get_loan_details(self.loan_id)
                # Update display
                for widget in self.container.winfo_children():
                    widget.destroy()
                self._display_loan_info()
                self._setup_payment_section()
                self._setup_payments_history()

                # Refresh parent window's loan list
                if hasattr(self.master, 'display_loans'):
                    self.master.display_loans(self.master.user_system.get_loans_data())
            else:
                messagebox.showerror("Error", message)

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid payment amount")


class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("Loan Management System")
        self.geometry("500x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self.title("Kodongo Loan System - Login")
        self.geometry("400x500")

        # Initialize user system
        self.user_system = ExcelUserSystem()
        self.current_user = None

        # Create main container
        self.container = ctk.CTkFrame(self)
        self.container.pack(pady=20, padx=20, fill="both", expand=True)

        # Show login frame by default
        self.show_login_frame()

    def show_login_frame(self):
        """Display the login form"""
        self.current_user = None

        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()

        # Title
        title_label = ctk.CTkLabel(
            self.container,
            text="Loan System Login",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)

        # Username entry
        self.username_entry = ctk.CTkEntry(
            self.container,
            placeholder_text="Username",
            width=250
        )
        self.username_entry.pack(pady=10)

        # Password entry
        self.password_entry = ctk.CTkEntry(
            self.container,
            placeholder_text="Password",
            show="*",
            width=250
        )
        self.password_entry.pack(pady=10)

        # Login button
        login_button = ctk.CTkButton(
            self.container,
            text="Login",
            command=self.login,
            width=250,
            height=40
        )
        login_button.pack(pady=20)

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
        """Display the loan management dashboard"""
        # Clear container
        for widget in self.container.winfo_children():
            widget.destroy()

        # Configure grid
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=0)
        self.container.grid_rowconfigure(1, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(self.container)
        header_frame.grid(row=0, column=0, sticky="nsew", pady=10, padx=10)

        # Welcome message
        welcome_label = ctk.CTkLabel(
            header_frame,
            text=f"Welcome, {self.current_user}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        welcome_label.pack(side="left", padx=10)

        # Change password button
        change_pass_button = ctk.CTkButton(
            header_frame,
            text="Change Password",
            command=self.show_change_password_frame,
            width=120
        )
        change_pass_button.pack(side="left", padx=5)

        # Logout button
        logout_button = ctk.CTkButton(
            header_frame,
            text="Logout",
            command=self.show_login_frame,
            width=100
        )
        logout_button.pack(side="right", padx=10)

        # Main content frame
        content_frame = ctk.CTkFrame(self.container)
        content_frame.grid(row=1, column=0, sticky="nsew", pady=10, padx=10)

        # Tab view for different sections
        self.tabview = ctk.CTkTabview(content_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)

        # Add tabs
        self.tabview.add("View Loans")
        self.tabview.add("Add Loan")

        # Configure tabs
        self._setup_view_loans_tab()
        self._setup_add_loan_tab()

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

    def _setup_view_loans_tab(self):
        """Setup the loans viewing tab with search functionality"""
        tab = self.tabview.tab("View Loans")

        # Search frame
        search_frame = ctk.CTkFrame(tab)
        search_frame.pack(fill="x", pady=5, padx=5)

        # Search entry
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by customer name or loan ID",
            width=300
        )
        self.search_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        # Search button
        search_button = ctk.CTkButton(
            search_frame,
            text="Search",
            command=self.filter_loans,
            width=80
        )
        search_button.pack(side="left", padx=5, pady=5)

        # Clear search button
        clear_button = ctk.CTkButton(
            search_frame,
            text="Clear",
            command=self.clear_search,
            width=80,
            fg_color="gray"
        )
        clear_button.pack(side="left", padx=5, pady=5)

        # Create scrollable frame for loans
        self.loans_scroll_frame = ctk.CTkScrollableFrame(tab)
        self.loans_scroll_frame.pack(fill="both", expand=True)

        # Display all loans initially
        self.display_loans(self.user_system.get_loans_data())

    def _calculate_summary_stats(self, loans_df):
        """Calculate and return loan summary statistics with error handling"""
        try:
            stats = {
                'total_loans': len(loans_df),
                'total_amount': loans_df['amount'].sum(),
                'total_paid': 0  # Initialize default value
            }

            # Handle missing columns gracefully
            if 'remaining_balance' in loans_df.columns and 'total_to_repay' in loans_df.columns:
                stats['total_paid'] = (loans_df['total_to_repay'] - loans_df['remaining_balance']).sum()
            elif 'total_to_repay' in loans_df.columns:
                stats['total_paid'] = loans_df['total_to_repay'].sum()  # Assume nothing paid if no balance column

            stats['percentage_paid'] = (stats['total_paid'] / stats['total_amount'] * 100) if stats[
                                                                                                  'total_amount'] > 0 else 0
            return stats
        except Exception as e:
            print(f"Error calculating stats: {e}")
            return {
                'total_loans': 0,
                'total_amount': 0,
                'total_paid': 0,
                'percentage_paid': 0
            }

    def display_loans(self, loans_df):
        """Display loans in the scrollable frame with summary statistics"""
        # Clear existing loans
        for widget in self.loans_scroll_frame.winfo_children():
            widget.destroy()

        # Calculate summary statistics
        stats = self._calculate_summary_stats(loans_df)

        # Create summary frame
        summary_frame = ctk.CTkFrame(self.loans_scroll_frame)
        summary_frame.pack(fill="x", pady=10, padx=5)

        stat_labels = [
            ("Total Loans:", f"{stats['total_loans']}"),
            ("Total Amount Given:", f"KES {stats['total_amount']:,.2f}"),
            ("Total Amount Paid:", f"KES {stats['total_paid']:,.2f}"),
            ("Percentage Paid:", f"{stats['percentage_paid']:.1f}%")
        ]

        for i, (label, value) in enumerate(stat_labels):
            ctk.CTkLabel(summary_frame, text=label, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=i * 2, padx=5, sticky="e")
            ctk.CTkLabel(summary_frame, text=value).grid(
                row=0, column=i * 2 + 1, padx=5, sticky="w")

        if loans_df.empty:
            ctk.CTkLabel(
                self.loans_scroll_frame,
                text="No loans found",
                font=ctk.CTkFont(size=14)
            ).pack(pady=20)
            return

        # Create header row
        header_frame = ctk.CTkFrame(self.loans_scroll_frame)
        header_frame.pack(fill="x", pady=5)

        headers = ["ID", "Customer", "Amount (KES)", "Daily Pay", "Term", "Total Repay", "Status", "Action"]
        for i, header in enumerate(headers):
            width = 80 if i not in [1, 5] else 120
            ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                width=width
            ).grid(row=0, column=i, padx=2)

        # Add loan rows
        for _, loan in loans_df.iterrows():
            self._create_loan_row(loan)

    def _create_loan_row(self, loan):
        """Create a single loan row in the display"""
        loan_frame = ctk.CTkFrame(self.loans_scroll_frame)
        loan_frame.pack(fill="x", pady=2)

        # Display loan information
        ctk.CTkLabel(
            loan_frame,
            text=str(loan['loan_id']),
            width=80
        ).grid(row=0, column=0, padx=2)

        ctk.CTkLabel(
            loan_frame,
            text=loan['customer_name'],
            width=120
        ).grid(row=0, column=1, padx=2)

        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['amount']:,.2f}",
            width=80
        ).grid(row=0, column=2, padx=2)

        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['payment_per_day']:,.2f}",
            width=80
        ).grid(row=0, column=3, padx=2)

        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['term_months']} months",
            width=80
        ).grid(row=0, column=4, padx=2)

        ctk.CTkLabel(
            loan_frame,
            text=f"{loan['total_to_repay']:,.2f}",
            width=120
        ).grid(row=0, column=5, padx=2)

        # Status with different colors
        status_color = {
            'Active': 'green',
            'Paid': '#3498db',  # Light blue
            'Defaulted': 'red'
        }.get(loan['status'], 'gray')

        status_label = ctk.CTkLabel(
            loan_frame,
            text=loan['status'],
            width=80,
            text_color="white",
            fg_color=status_color
        )
        status_label.grid(row=0, column=6, padx=2)

        # Delete button
        delete_button = ctk.CTkButton(
            loan_frame,
            text="Delete",
            width=80,
            fg_color="#ff4444",
            hover_color="#cc0000",
            command=lambda loan_id=loan['loan_id']: self.confirm_delete_loan(loan_id)
        )
        delete_button.grid(row=0, column=7, padx=2)

        # Make the row clickable (except delete button)
        loan_frame.bind("<Button-1>", lambda e, loan_id=loan['loan_id']: self.show_loan_details(loan_id))
        for child in loan_frame.winfo_children():
            if child != delete_button:
                child.bind("<Button-1>", lambda e, loan_id=loan['loan_id']: self.show_loan_details(loan_id))

    def confirm_delete_loan(self, loan_id):
        """Confirm loan deletion with admin password"""
        # Create popup window
        popup = ctk.CTkToplevel(self)
        popup.title("Confirm Deletion")
        popup.geometry("400x200")
        popup.grab_set()  # Make it modal

        # Center the popup
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f"+{x}+{y}")

        # Add content
        ctk.CTkLabel(
            popup,
            text=f"Confirm deletion of Loan ID {loan_id}",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            popup,
            text="Enter admin password to confirm:"
        ).pack(pady=5)

        password_entry = ctk.CTkEntry(
            popup,
            show="*",
            width=200
        )
        password_entry.pack(pady=5)

        def attempt_delete():
            password = password_entry.get()
            success, message = self.user_system.validate_login("admin", password)
            if success:
                self.delete_loan(loan_id)
                popup.destroy()
            else:
                messagebox.showerror("Error", "Invalid admin password")

        button_frame = ctk.CTkFrame(popup)
        button_frame.pack(pady=10)

        ctk.CTkButton(
            button_frame,
            text="Delete",
            command=attempt_delete,
            fg_color="#ff4444",
            hover_color="#cc0000",
            width=100
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=popup.destroy,
            width=100
        ).pack(side="right", padx=10)

    def delete_loan(self, loan_id):
        """Delete a loan from the system"""
        try:
            # Get loans data
            loans_df = self.user_system.get_loans_data()

            # Find the loan to delete
            loan_to_delete = loans_df[loans_df['loan_id'] == loan_id]
            if loan_to_delete.empty:
                messagebox.showerror("Error", "Loan not found")
                return

            # Get the loan filename - ensure it's converted to string
            loan_file = str(loan_to_delete.iloc[0]['loan_file'])
            loan_filepath = os.path.join(self.user_system.data_folder, loan_file)

            # Remove the loan file
            if os.path.exists(loan_filepath):
                os.remove(loan_filepath)
            else:
                messagebox.showwarning("Warning", f"Loan file {loan_file} not found")

            # Remove from master loans file
            loans_df = loans_df[loans_df['loan_id'] != loan_id]
            loans_df.to_excel(self.user_system.loans_path, index=False, engine='openpyxl')

            messagebox.showinfo("Success", f"Loan ID {loan_id} deleted successfully")

            # Refresh the loans display
            self.display_loans(loans_df)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete loan: {str(e)}")

    def filter_loans(self):
        """Filter loans based on search term"""
        search_term = self.search_entry.get().strip().lower()

        if not search_term:
            self.display_loans(self.user_system.get_loans_data())
            return

        loans_df = self.user_system.get_loans_data()

        try:
            # Try to convert search term to loan ID (integer)
            loan_id = int(search_term)
            filtered_df = loans_df[loans_df['loan_id'] == loan_id]
        except ValueError:
            # If not a number, search by customer name
            filtered_df = loans_df[loans_df['customer_name'].str.lower().str.contains(search_term)]

        self.display_loans(filtered_df)

    def clear_search(self):
        """Clear search and show all loans"""
        self.search_entry.delete(0, 'end')
        self.display_loans(self.user_system.get_loans_data())

    # [Rest of the code remains exactly the same]

    def show_loan_details(self, loan_id):
        """Show details for a specific loan in a centered modal window"""
        loan_details = LoanDetailWindow(self, loan_id, self.user_system)

        # Center the window
        loan_details.update_idletasks()
        width = loan_details.winfo_width()
        height = loan_details.winfo_height()
        x = (loan_details.winfo_screenwidth() // 2) - (width // 2)
        y = (loan_details.winfo_screenheight() // 2) - (height // 2)
        loan_details.geometry(f"+{x}+{y}")

        loan_details.grab_set()  # Make it modal

    def _setup_add_loan_tab(self):
        """Setup the loan creation tab"""
        tab = self.tabview.tab("Add Loan")

        # Form fields
        fields = [
            ("customer_name", "Customer Name"),
            ("amount", "Loan Amount (KES)"),
            ("payment_per_day", "Daily Payment (KES)"),
            ("term_months", "Term (months)"),
            ("start_date", "Start Date (YYYY-MM-DD)"),
            ("status", "Status")
        ]

        self.loan_entries = {}

        for i, (field, label) in enumerate(fields):
            ctk.CTkLabel(tab, text=label).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(tab)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            self.loan_entries[field] = entry

        # Set default values
        self.loan_entries['status'].insert(0, "Active")
        self.loan_entries['term_months'].insert(0, "1")  # Default to minimum 1 month

        # Calculate button
        calculate_button = ctk.CTkButton(
            tab,
            text="Calculate Total Repayment",
            command=self.calculate_repayment,
            height=30
        )
        calculate_button.grid(row=len(fields), column=0, columnspan=2, pady=10)

        # Total repayment display
        self.total_repay_label = ctk.CTkLabel(
            tab,
            text="Total to repay: KES 0.00",
            font=ctk.CTkFont(weight="bold")
        )
        self.total_repay_label.grid(row=len(fields) + 1, column=0, columnspan=2, pady=5)

        # Submit button
        submit_button = ctk.CTkButton(
            tab,
            text="Add Loan",
            command=self.add_loan,
            height=40
        )
        submit_button.grid(row=len(fields) + 2, column=0, columnspan=2, pady=20)

    def calculate_repayment(self):
        """Calculate and display the total repayment amount"""
        try:
            payment_per_day = float(self.loan_entries['payment_per_day'].get())
            term_months = int(self.loan_entries['term_months'].get())

            if term_months < 1:
                messagebox.showerror("Error", "Term must be at least 1 month")
                return

            # Calculate total repayment (payment_per_day * days_in_term)
            days_in_term = term_months * 30  # Approximate 30 days per month
            total_to_repay = payment_per_day * days_in_term

            self.total_repay_label.configure(
                text=f"Total to repay: KES {total_to_repay:,.2f}",
                text_color="white"
            )
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for daily payment and term")

    def _clear_loan_form(self):
        """Clear all fields in the add loan form"""
        for entry in self.loan_entries.values():
            entry.delete(0, 'end')
        self.total_repay_label.configure(text="Total to repay: KES 0.00")
        # Reset to default values if needed
        self.loan_entries['status'].insert(0, "Active")
        self.loan_entries['term_months'].insert(0, "1")

    def add_loan(self):
        """Handle loan creation with refresh"""
        # Validate inputs
        try:
            term_months = int(self.loan_entries['term_months'].get())
            if term_months < 1:
                messagebox.showerror("Error", "Term must be at least 1 month")
                return
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for term")
            return

        # Prepare loan data
        loan_data = {
            'customer_name': self.loan_entries['customer_name'].get(),
            'amount': float(self.loan_entries['amount'].get()),
            'payment_per_day': float(self.loan_entries['payment_per_day'].get()),
            'term_months': term_months,
            'start_date': self.loan_entries['start_date'].get(),
            'status': self.loan_entries['status'].get(),
            'created_by': self.current_user
        }

        # Call add_loan (now expecting 2 return values)
        success, message = self.user_system.add_loan(loan_data)

        if success:
            messagebox.showinfo("Success", message)
            # Refresh the view by reloading data
            self.display_loans(self.user_system.get_loans_data())
            # Clear form
            self._clear_loan_form()
        else:
            messagebox.showerror("Error", message)


print(f"Loan files are stored at: {os.path.abspath('app_data')}")
if __name__ == "__main__":
    welcome = WelcomePage()
    welcome.mainloop()
    app = LoginApp()
    app.mainloop()
