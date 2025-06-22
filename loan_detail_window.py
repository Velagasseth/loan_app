
import shutil
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os

import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta




class LoanDetailWindow(ctk.CTkToplevel):
    def __init__(self, parent, loan_id, user_system):
        super().__init__(parent)
        self.parent = parent
        self.loan_id = loan_id
        self.user_system = user_system
        self.current_user = parent.current_user

        # Configure window
        self.title(f"Loan Details - ID {loan_id}")
        self.geometry("900x700")
        self.minsize(800, 600)
        self.after(100, lambda: self.wm_state('zoomed'))

        # Create main container
        self.container = ctk.CTkFrame(self)
        self.container.pack(pady=20, padx=20, fill="both", expand=True)

        # Load loan data - using the proper file path method
        self.loan_data, self.payments_df = self._load_loan_details()
        if not self.loan_data:
            self.destroy()
            return


        # Initialize UI
        self._setup_container()
        self._create_ui()

        # Prevent multiple instances
        self.transient(parent)
        self.grab_set()

        # Load data and build UI
        self.refresh_data()

    def _setup_history_tab(self):
        """Modern layout for Payment History tab with Remove Payment functionality"""
        tab = self.notebook.tab("Payment History")

        # Main container
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Payment entry card
        entry_card = ctk.CTkFrame(main_frame, border_width=1, border_color="#e0e0e0", corner_radius=12)
        entry_card.pack(fill="x", padx=10, pady=(0, 15))

        # Payment entry form with Remove button
        entry_frame = ctk.CTkFrame(entry_card, fg_color="transparent")
        entry_frame.pack(padx=15, pady=15)

        # Existing entry widgets
        ctk.CTkLabel(entry_frame, text="Amount (KES):").grid(row=0, column=0, padx=5)
        self.amount_entry = ctk.CTkEntry(entry_frame, width=120)
        self.amount_entry.grid(row=0, column=1, padx=5)

        ctk.CTkLabel(entry_frame, text="Date:").grid(row=0, column=2, padx=5)
        self.date_entry = ctk.CTkEntry(entry_frame, width=120)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=0, column=3, padx=5)

        ctk.CTkLabel(entry_frame, text="Notes:").grid(row=0, column=4, padx=5)
        self.notes_entry = ctk.CTkEntry(entry_frame, width=200)
        self.notes_entry.grid(row=0, column=5, padx=5)

        # Add Payment button
        add_btn = ctk.CTkButton(
            entry_frame,
            text="Add Payment",
            command=self._add_payment,
            width=100,
            fg_color="#2ecc71",  # Green color
            hover_color="#27ae60"
        )
        add_btn.grid(row=0, column=6, padx=5)

        # Remove Payment button
        remove_btn = ctk.CTkButton(
            entry_frame,
            text="Remove Payment",
            command=self._remove_payment,
            width=100,
            fg_color="#e74c3c",  # Red color
            hover_color="#c0392b"
        )
        remove_btn.grid(row=0, column=7, padx=5)

        # Payment ID entry for removal
        ctk.CTkLabel(entry_frame, text="Payment ID:").grid(row=1, column=0, padx=5, pady=5)
        self.payment_id_entry = ctk.CTkEntry(entry_frame, width=120)
        self.payment_id_entry.grid(row=1, column=1, padx=5, pady=5)

        # History card
        history_card = ctk.CTkFrame(main_frame, border_width=1, border_color="#e0e0e0", corner_radius=12)
        history_card.pack(fill="both", expand=True, padx=10, pady=10)

        # History scrollable area
        scroll_frame = ctk.CTkScrollableFrame(history_card, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        if self.payments_df.empty:
            ctk.CTkLabel(scroll_frame, text="No payment history found").pack(pady=20)
            return

        # Modern table header
        header_frame = ctk.CTkFrame(scroll_frame, fg_color="#2c3e50", height=40)
        header_frame.pack(fill="x", pady=(0, 5))

        headers = ["ID", "Date", "Amount", "Received By", "Notes"]
        widths = [50, 120, 100, 150, 250]

        for col, (header, width) in enumerate(zip(headers, widths)):
            ctk.CTkLabel(
                header_frame,
                text=header,
                font=ctk.CTkFont(weight="bold"),
                text_color="white",
                width=width
            ).grid(row=0, column=col, padx=5, sticky="w")

        # Payment rows with alternating colors
        for row, (_, payment) in enumerate(self.payments_df.iterrows(), 1):
            row_frame = ctk.CTkFrame(
                scroll_frame,
                fg_color="#f8f9fa" if row % 2 == 0 else "white",
                height=35
            )
            row_frame.pack(fill="x", pady=1)

            # Payment ID
            ctk.CTkLabel(
                row_frame,
                text=str(payment['payment_id']),
                width=widths[0]
            ).grid(row=0, column=0, padx=5, sticky="w")

            # Date
            ctk.CTkLabel(
                row_frame,
                text=str(payment['date']),
                width=widths[1]
            ).grid(row=0, column=1, padx=5, sticky="w")

            # Amount
            ctk.CTkLabel(
                row_frame,
                text=f"{float(payment['amount']):,.2f}",
                width=widths[2],
                anchor="e"
            ).grid(row=0, column=2, padx=5)

            # Received By
            ctk.CTkLabel(
                row_frame,
                text=str(payment['received_by']),
                width=widths[3]
            ).grid(row=0, column=3, padx=5, sticky="w")

            # Notes
            ctk.CTkLabel(
                row_frame,
                text=str(payment['notes']),
                width=widths[4]
            ).grid(row=0, column=4, padx=5, sticky="w")

    def _remove_payment(self):
        """Remove a payment from the loan"""
        try:
            payment_id = int(self.payment_id_entry.get())

            # Find the payment to remove
            payment_to_remove = self.payments_df[self.payments_df['payment_id'] == payment_id]
            if payment_to_remove.empty:
                messagebox.showerror("Error", "Payment ID not found")
                return

            confirm = messagebox.askyesno(
                "Confirm Removal",
                f"Are you sure you want to remove payment ID {payment_id} of KES {float(payment_to_remove.iloc[0]['amount']):,.2f}?"
            )
            if not confirm:
                return

            # Get loan filename
            loans_df = self.user_system.get_loans_data()
            loan_record = loans_df[loans_df['loan_id'] == self.loan_id]
            if loan_record.empty:
                messagebox.showerror("Error", "Loan not found")
                return

            loan_file = loan_record.iloc[0]['loan_file']
            # Replace hardcoded paths with:
            loan_filepath = os.path.join(self.user_system.data_folder, loan_file)  # Instead of user_system.data_folder
            # Create backup
            backup_path = loan_filepath + ".backup"
            shutil.copy2(loan_filepath, backup_path)

            try:
                # Read existing data
                details_df = pd.read_excel(loan_filepath, sheet_name='Loan Details', engine='openpyxl')
                payments_df = pd.read_excel(loan_filepath, sheet_name='Payments', engine='openpyxl')

                # Remove the payment
                payments_df = payments_df[payments_df['payment_id'] != payment_id]

                # Update loan details (add back the payment amount to remaining balance)
                payment_amount = float(payment_to_remove.iloc[0]['amount'])
                details_df.at[0, 'remaining_balance'] = float(details_df.at[0, 'remaining_balance']) + payment_amount

                # If loan was marked as Paid but we're removing a payment, set back to Active
                if details_df.at[0, 'status'] == "Paid":
                    details_df.at[0, 'status'] = "Active"

                # Save updated data
                with pd.ExcelWriter(loan_filepath, engine='openpyxl') as writer:
                    details_df.to_excel(writer, sheet_name='Loan Details', index=False)
                    payments_df.to_excel(writer, sheet_name='Payments', index=False)

                # Refresh the view
                self.loan_data, self.payments_df = self.user_system.get_loan_details(self.loan_id)
                for widget in self.container.winfo_children():
                    widget.destroy()
                self._create_ui()

                messagebox.showinfo("Success", f"Payment ID {payment_id} removed successfully")

            except Exception as e:
                # Restore from backup if error occurs
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, loan_filepath)
                messagebox.showerror("Error", f"Failed to remove payment: {str(e)}")

            finally:
                # Clean up backup file
                if os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                    except:
                        pass

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid Payment ID")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def _create_compliance_section(self, parent, data):
        """Create payment compliance section with enhanced Settle All functionality"""
        frame = ctk.CTkFrame(
            parent,
            border_width=1,
            border_color="#e0e0e0",
            corner_radius=12
        )
        frame.pack(fill="x", pady=(0, 20))

        # Header
        ctk.CTkLabel(
            frame,
            text="Payment Compliance",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10))

        # Compliance details
        details = [
            f"• Expected Payments: {data['expected_payment_days']} days",
            f"• Actual Payments: {data['actual_payment_days']} days",
            f"• Daily Amount: KES {data['daily_payment']:,.2f}",
            f"• Missed Days: {data['missed_days']} days",
            f"• Accumulated: KES {data['accumulated_missed']:,.2f}"
        ]

        for detail in details:
            ctk.CTkLabel(
                frame,
                text=detail,
                font=ctk.CTkFont(size=12),
                justify="left"
            ).pack(anchor="w", padx=20, pady=2)

        # Missed payments warning (if applicable)
        if data['missed_days'] > 0:
            warning_frame = ctk.CTkFrame(
                frame,
                fg_color="#fff3cd",
                corner_radius=8
            )
            warning_frame.pack(fill="x", padx=15, pady=10)

            ctk.CTkLabel(
                warning_frame,
                text=f"⚠️ {data['missed_days']} Missed Days (KES {data['accumulated_missed']:,.2f})",
                text_color="#856404",
                font=ctk.CTkFont(weight="bold")
            ).pack(pady=5)

            # Settlement buttons
            btn_frame = ctk.CTkFrame(warning_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=(0, 5))

            # Enhanced Settle All button with confirmation
            ctk.CTkButton(
                btn_frame,
                text=f"Settle All (KES {data['accumulated_missed']:,.2f})",
                command=lambda: self._confirm_settle_missed(data['accumulated_missed'], "all"),
                fg_color="#e74c3c",
                hover_color="#c0392b",
                height=30
            ).pack(side="left", padx=5, fill="x", expand=True)

            # Partial settlement options
            partial_options = [
                ("5 Days", 5),
                ("10 Days", 10),
                ("Half", data['missed_days'] // 2)
            ]

            for label, days in partial_options:
                amount = min(data['daily_payment'] * days, data['accumulated_missed'])
                if amount > 0:
                    ctk.CTkButton(
                        btn_frame,
                        text=f"Settle {label} (KES {amount:,.2f})",
                        command=lambda amt=amount: self._confirm_settle_missed(amt, label),
                        fg_color="#f39c12",
                        hover_color="#e67e22",
                        height=30
                    ).pack(side="left", padx=5, fill="x", expand=True)

    def _confirm_settle_missed(self, amount, description):
        """Show confirmation dialog before settling missed payments"""
        confirm = messagebox.askyesno(
            "Confirm Settlement",
            f"Are you sure you want to settle {description} missed payments?\n"
            f"Amount: KES {amount:,.2f}"
        )
        if confirm:
            self._settle_missed_payments(amount)

    def _settle_missed_payments(self, amount):
        """Handle settlement of missed payments with UI refresh"""
        try:
            success, message, updated_loans = self.user_system.settle_missed_payments(self.loan_id, amount)

            if success:
                # Refresh all data
                self.loan_data, self.payments_df = self.user_system.get_loan_details(self.loan_id)

                # Refresh parent window if available
                if hasattr(self.master, 'display_loans'):
                    self.master.display_loans(updated_loans)
                if hasattr(self.master, '_refresh_loan_payments_tab'):
                    self.master._refresh_loan_payments_tab()

                # Completely rebuild this window
                for widget in self.container.winfo_children():
                    widget.destroy()
                self._create_ui()

                messagebox.showinfo("Success", f"Missed payments settled successfully!\n{message}")
            else:
                messagebox.showerror("Error", message)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to settle missed payments: {str(e)}")








    def _setup_container(self):
        """Create main container with proper destruction handling"""
        if hasattr(self, 'container'):
            try:
                self.container.destroy()
            except:
                pass

        self.container = ctk.CTkFrame(self)
        self.container.pack(pady=20, padx=20, fill="both", expand=True)

    def _create_ui(self):
        """Build the UI components"""
        try:
            # Load loan data
            self.loan_data, self.payments_df = self._load_loan_details()
            if not self.loan_data:
                self.destroy()
                return

            """Create all UI components"""
            # Top button frame
            button_frame = ctk.CTkFrame(self.container)
            button_frame.pack(fill="x", pady=(0, 10))

            # Print button
            print_btn = ctk.CTkButton(
                button_frame,
                text="Print Full Report",
                command=self._print_report,
                fg_color="#2e8b57",
                hover_color="#3cb371",
                width=150
            )
            print_btn.pack(side="left", padx=5)

            # Print payment history button
            print_history_btn = ctk.CTkButton(
                button_frame,
                text="Print Payment History",
                command=self._print_payment_history,
                width=150
            )
            print_history_btn.pack(side="left", padx=5)

            # Main content notebook
            self.notebook = ctk.CTkTabview(self.container)
            self.notebook.pack(fill="both", expand=True)

            # Add tabs
            self.notebook.add("Loan Details")
            self.notebook.add("Payment History")
            self.notebook.add("Payment Summary")  # New tab

            # Configure tabs
            self._setup_details_tab()
            self._setup_history_tab()
            self._setup_summary_tab()  # New method for summary tab

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create UI: {str(e)}")
            self.destroy()

    def _load_loan_details(self):
        """Safely load loan details"""
        try:
            return self.user_system.get_loan_details(self.loan_id)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load loan details: {str(e)}")
            return None, None

    def refresh_data(self, updated_loan=None):
        """Refresh all data and UI"""
        # Clear existing widgets
        for widget in self.container.winfo_children():
            widget.destroy()

        # Load data
        if updated_loan:
            self.loan_data = updated_loan
            # Get fresh payments data
            _, self.payments_df = self.user_system.get_loan_details(self.loan_id)
        else:
            self.loan_data, self.payments_df = self.user_system.get_loan_details(self.loan_id)
            if not self.loan_data:
                self.destroy()
                return

        # Rebuild UI
        self._create_ui()

    def _setup_summary_tab(self):
        """Modern, robust implementation of Payment Summary tab"""
        try:
            # Initialize tab
            tab = self.notebook.tab("Payment Summary")
            for widget in tab.winfo_children():
                widget.destroy()

            # Create main container
            main_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            main_frame.pack(fill="both", expand=True, padx=15, pady=15)

            # Load fresh data
            summary_data = self._calculate_payment_summary()

            # ===== 1. Header with Refresh =====
            header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            header_frame.pack(fill="x", pady=(0, 15))

            ctk.CTkLabel(
                header_frame,
                text="Payment Summary",
                font=ctk.CTkFont(size=20, weight="bold", family="Arial"),
                text_color="#2c3e50"
            ).pack(side="left")

            refresh_btn = ctk.CTkButton(
                header_frame,
                text="⟳ Refresh Data",
                width=120,
                height=30,
                command=self._safe_refresh,
                fg_color="#3498db",
                hover_color="#2980b9"
            )
            refresh_btn.pack(side="right")

            # ===== 2. Financial Overview Cards =====
            cards_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            cards_frame.pack(fill="x", pady=(0, 20))

            cards = [
                {
                    "title": "Loan Amount",
                    "value": f"KES {summary_data['amount_given']:,.2f}",
                    "icon": "💰",
                    "color": "#3498db"
                },
                {
                    "title": "Amount Paid",
                    "value": f"KES {summary_data['amount_paid']:,.2f}",
                    "icon": "💳",
                    "color": "#27ae60"
                },
                {
                    "title": "Outstanding",
                    "value": f"KES {summary_data['amount_out']:,.2f}",
                    "icon": "⚠️" if summary_data['amount_out'] > 0 else "✅",
                    "color": "#e74c3c" if summary_data['amount_out'] > 0 else "#27ae60"
                }
            ]

            for card in cards:
                self._create_finance_card(cards_frame, **card)

            # ===== 3. Payment Progress =====
            self._create_progress_section(main_frame, summary_data)

            # ===== 4. Compliance Status =====
            self._create_compliance_section(main_frame, summary_data)

            # ===== 5. Recent Activity =====
            if summary_data.get('last_payment'):
                self._create_recent_activity(main_frame, summary_data['last_payment'])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load summary: {str(e)}")
            self.destroy()

    def _create_finance_card(self, parent, title, value, icon, color):
        """Create a uniform financial metric card"""
        card = ctk.CTkFrame(
            parent,
            border_width=1,
            border_color="#e0e0e0",
            corner_radius=12,
            height=110,
            width=180
        )
        card.pack(side="left", expand=True, padx=5, pady=5)

        # Card content
        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=28),
            text_color=color
        ).pack(pady=(12, 5))

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack()

        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color
        ).pack(pady=(0, 12))

    def _create_progress_section(self, parent, data):
        """Create visual repayment progress"""
        frame = ctk.CTkFrame(
            parent,
            border_width=1,
            border_color="#e0e0e0",
            corner_radius=12
        )
        frame.pack(fill="x", pady=(0, 20))

        # Header
        ctk.CTkLabel(
            frame,
            text="Repayment Progress",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10))

        # Progress bar
        progress = ctk.CTkProgressBar(
            frame,
            orientation="horizontal",
            height=20,
            width=400,
            progress_color="#27ae60",
            corner_radius=10
        )
        progress.set(data['completion_percentage'] / 100)
        progress.pack(pady=(0, 10))

        # Labels
        progress_frame = ctk.CTkFrame(frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            progress_frame,
            text=f"{data['completion_percentage']:.1f}% Complete",
            font=ctk.CTkFont(weight="bold")
        ).pack(side="left")

        ctk.CTkLabel(
            progress_frame,
            text=f"KES {data['amount_paid']:,.2f} of KES {data['amount_given']:,.2f}",
            font=ctk.CTkFont(size=12)
        ).pack(side="right")



    def _create_recent_activity(self, parent, payment):
        """Show last payment details"""
        frame = ctk.CTkFrame(
            parent,
            border_width=1,
            border_color="#e0e0e0",
            corner_radius=12
        )
        frame.pack(fill="x")

        ctk.CTkLabel(
            frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10))

        details = [
            f"Last Payment: KES {float(payment['amount']):,.2f}",
            f"Date: {payment['date']}",
            f"Received by: {payment['received_by']}",
            f"Notes: {payment.get('notes', 'None')}"
        ]

        for detail in details:
            ctk.CTkLabel(
                frame,
                text=detail,
                font=ctk.CTkFont(size=12),
                justify="left"
            ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(
            frame,
            text="View full history in Payments tab",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(pady=(5, 15))

    def _safe_refresh(self):
        """Safe wrapper for refresh operation"""
        try:
            self._setup_summary_tab()
        except Exception as e:
            messagebox.showerror("Error", f"Refresh failed: {str(e)}")

    def _create_summary_card(self, parent, title, value, color, column):
        """Helper to create uniform metric cards"""
        card = ctk.CTkFrame(
            parent,
            border_width=1,
            corner_radius=8,
            height=100
        )
        card.grid(row=0, column=column, padx=5, pady=5, sticky="nsew")
        parent.columnconfigure(column, weight=1)

        # Icon
        ctk.CTkLabel(
            card,
            text="💰" if "Amount" in title else "📈" if "Interest" in title else "✅" if "Paid" in title else "⚠️",
            font=ctk.CTkFont(size=24),
            text_color=color
        ).pack(pady=(10, 0))

        # Title
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12)
        ).pack()

        # Value
        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color
        ).pack(pady=(0, 10))

    def _refresh_summary_data(self):
        """Refresh all summary data"""
        self.loan_data, self.payments_df = self.user_system.get_loan_details(self.loan_id)
        for widget in self.notebook.tab("Payment Summary").winfo_children():
            widget.destroy()
        self._setup_summary_tab()
        messagebox.showinfo("Refreshed", "Payment summary data has been updated")

    def _safe_command(self, func):
        """Wrapper to prevent uncaught exceptions in button commands"""

        def wrapped():
            try:
                return func()
            except Exception as e:
                messagebox.showerror("Error", f"Operation failed: {str(e)}")

        return wrapped

    def _create_metric_card(self, parent, title, value, icon, color, column):
        """Helper to create uniform metric cards"""
        card = ctk.CTkFrame(
            parent,
            border_width=1,
            corner_radius=8,
            height=100
        )
        card.grid(row=0, column=column, padx=5, pady=5, sticky="nsew")
        parent.columnconfigure(column, weight=1)

        # Icon
        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=24),
            text_color=color
        ).pack(pady=(10, 0))

        # Title
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12)
        ).pack()

        # Value
        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color
        ).pack(pady=(0, 10))

    def _refresh_summary_tab(self):
        """Refresh all summary data"""
        self.loan_data, self.payments_df = self.user_system.get_loan_details(self.loan_id)
        for widget in self.notebook.tab("Payment Summary").winfo_children():
            widget.destroy()
        self._setup_summary_tab()



    def _calculate_payment_summary(self):
        """Calculate payment summary including exact missed days"""
        # Add this at the start of the method
        if hasattr(self, '_last_calculation_date'):
            today = datetime.now().date()
            if self._last_calculation_date != today:
                # Reset daily payment tracking
                self.user_system.reset_daily_payments()
        self._last_calculation_date = datetime.now().date()
        """Calculate payment summary including exact missed days"""
        amount_given = float(self.loan_data['amount'])
        total_to_repay = float(self.loan_data['total_to_repay'])
        remaining_balance = float(self.loan_data['remaining_balance'])
        daily_payment = float(self.loan_data['payment_per_day'])

        # Basic calculations (unchanged)
        amount_paid = total_to_repay - remaining_balance
        total_interest = total_to_repay - amount_given
        amount_out = remaining_balance

        # ===== NEW: Precise missed payment calculation =====
        start_date = datetime.strptime(self.loan_data['start_date'], "%Y-%m-%d").date()
        today = datetime.now().date()
        term_days = int(self.loan_data['term_months']) * 30  # Approx 30 days/month
        expected_days = (today - start_date).days + 1  # +1 to include start day

        # Count actual unique payment days
        if not self.payments_df.empty:
            payment_dates = pd.to_datetime(self.payments_df['date']).dt.date
            unique_payment_days = len(payment_dates.unique())
        else:
            unique_payment_days = 0

        # Calculate missed days (only for active loans)
        missed_days = 0
        accumulated_missed = 0
        end_date = start_date + timedelta(days=term_days)

        if self.loan_data['status'] == 'Active' and today <= end_date:
            missed_days = max(0, expected_days - unique_payment_days)
            accumulated_missed = missed_days * daily_payment

        # Last payment info
        last_payment = None
        if not self.payments_df.empty:
            last_payment = self.payments_df.iloc[-1].to_dict()

        return {
            'amount_given': amount_given,
            'amount_paid': amount_paid,
            'total_interest': total_interest,
            'amount_out': amount_out,
            'daily_payment': daily_payment,
            'last_payment': last_payment,
            'completion_percentage': (amount_paid / total_to_repay) * 100,
            # New fields:
            'missed_days': missed_days,
            'accumulated_missed': accumulated_missed,
            'expected_payment_days': expected_days,
            'actual_payment_days': unique_payment_days
        }

    def _create_progress_bar(self, parent, summary_data):
        """Create payment progress visualization"""
        progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        progress_frame.pack(fill="x", pady=15, padx=10)

        ctk.CTkLabel(
            progress_frame,
            text="Payment Progress",
            font=ctk.CTkFont(weight="bold")
        ).pack()

        # Progress percentage
        ctk.CTkLabel(
            progress_frame,
            text=f"{summary_data['completion_percentage']:.1f}% Complete",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(5, 0))

        # Progress bar
        progress_bar = ctk.CTkProgressBar(
            progress_frame,
            orientation="horizontal",
            width=400,
            height=20,
            corner_radius=10
        )
        progress_bar.pack(pady=5)
        progress_bar.set(summary_data['completion_percentage'] / 100)

        # Progress labels
        progress_labels = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_labels.pack(fill="x")

        ctk.CTkLabel(
            progress_labels,
            text=f"KES {summary_data['amount_paid']:,.2f} paid",
            font=ctk.CTkFont(size=10)
        ).pack(side="left")

        ctk.CTkLabel(
            progress_labels,
            text=f"KES {summary_data['amount_out']:,.2f} remaining",
            font=ctk.CTkFont(size=10)
        ).pack(side="right")

    def _setup_details_tab(self):
        """Modern layout with high-visibility text colors"""
        tab = self.notebook.tab("Loan Details")

        # Main container with light background
        main_frame = ctk.CTkFrame(tab, fg_color="#f8f9fa")  # Light gray background
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Card container with white background
        card = ctk.CTkFrame(main_frame, border_width=1, border_color="#e0e0e0",
                            corner_radius=12, fg_color="white")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        # Content frame
        content_frame = ctk.CTkFrame(card, fg_color="white")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Two-column layout
        left_col = ctk.CTkFrame(content_frame, fg_color="white")
        left_col.pack(side="left", fill="both", expand=True, padx=10)

        right_col = ctk.CTkFrame(content_frame, fg_color="white")
        right_col.pack(side="right", fill="both", expand=True, padx=10)

        # Vibrant color scheme
        PRIMARY_COLOR = "#2c3e50"  # Dark blue for headers
        SECONDARY_COLOR = "#e74c3c"  # Bright red for important values
        TEXT_COLOR = "#2c3e50"  # Dark text for readability
        HIGHLIGHT_COLOR = "#3498db"  # Bright blue for interactive elements

        # Add loan cycle information
        try:
            cycle_count = self.user_system.get_loan_cycle({
                'customer_name': self.loan_data['customer_name'],
                'national_id': self.loan_data.get('national_id', ''),
                'phone_number': self.loan_data.get('phone_number', '')
            })

            cycle_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            cycle_frame.pack(fill="x", pady=(10, 5))

            ctk.CTkLabel(
                cycle_frame,
                text="Loan Cycle:",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=100
            ).pack(side="left")

            cycle_label = ctk.CTkLabel(
                cycle_frame,
                text=str(cycle_count),
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#9b59b6"  # Purple color
            )
            cycle_label.pack(side="left")

            # Add visual indicator for repeat customers
            if cycle_count > 1:
                ctk.CTkLabel(
                    cycle_frame,
                    text=f"(Returning Customer)",
                    text_color="#27ae60",  # Green
                    font=ctk.CTkFont(size=12)
                ).pack(side="left", padx=10)

        except Exception as e:
            print(f"Error loading loan cycle: {str(e)}")
            # Fallback UI if cycle count fails
            ctk.CTkLabel(
                content_frame,
                text="Loan Cycle: Data unavailable",
                text_color="gray"
            ).pack()

        # Section header style
        def create_section_header(parent, text):
            header = ctk.CTkLabel(
                parent,
                text=text,
                font=ctk.CTkFont(size=14, weight="bold", family="Helvetica"),
                text_color=PRIMARY_COLOR,
                anchor="w",
                fg_color="white"
            )
            header.pack(pady=(15, 10))
            return header

        # Field row style with improved contrast
        def create_field_row(parent, label, value, highlight=False):
            row = ctk.CTkFrame(parent, fg_color="white")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row,
                text=label,
                font=ctk.CTkFont(size=13, family="Helvetica"),
                text_color=TEXT_COLOR,
                anchor="w",
                fg_color="white"
            ).pack(side="left")

            text_color = HIGHLIGHT_COLOR if highlight else TEXT_COLOR
            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(size=13, weight="bold", family="Helvetica"),
                text_color=text_color,
                anchor="w",
                fg_color="white"
            ).pack(side="right")
            return row

        # Left Column - Loan Info
        create_section_header(left_col, "LOAN INFORMATION")

        create_field_row(left_col, "Loan ID:", str(self.loan_id), highlight=True)
        create_field_row(left_col, "Status:", str(self.loan_data['status']))
        create_field_row(left_col, "Created By:", str(self.loan_data['created_by']))

        create_section_header(left_col, "DATES")

        create_field_row(left_col, "Start Date:", str(self.loan_data['start_date']))
        create_field_row(left_col, "End Date:", str(self.loan_data['end_date']))
        create_field_row(left_col, "Term:", f"{int(self.loan_data['term_months'])} months")

        # Right Column - Customer Info
        create_section_header(right_col, "CUSTOMER DETAILS")

        create_field_row(right_col, "Name:", str(self.loan_data['customer_name']), highlight=True)
        create_field_row(right_col, "National ID:", str(self.loan_data.get('national_id', 'N/A')))
        create_field_row(right_col, "Phone:", str(self.loan_data.get('phone_number', 'N/A')))
        create_field_row(right_col, "Address:", str(self.loan_data.get('physical_address', 'N/A')))

        # Financial Section with bright colors
        create_section_header(card, "FINANCIAL SUMMARY")

        finance_frame = ctk.CTkFrame(card, fg_color="white")
        finance_frame.pack(fill="x", padx=15, pady=5)

        amounts = [
            ("Loan Amount", f"KES {float(self.loan_data['amount']):,.2f}", "#27ae60"),  # Bright green
            ("Daily Payment", f"KES {float(self.loan_data['payment_per_day']):,.2f}", "#3498db"),  # Bright blue
            ("Total Repayable", f"KES {float(self.loan_data['total_to_repay']):,.2f}", "#2c3e50"),  # Dark blue
            ("Remaining", f"KES {float(self.loan_data['remaining_balance']):,.2f}",
             "#e74c3c" if float(self.loan_data['remaining_balance']) > 0 else "#27ae60")  # Red/Green
        ]

        for label, value, color in amounts:
            row = ctk.CTkFrame(finance_frame, fg_color="white")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row,
                text=label,
                font=ctk.CTkFont(size=13, family="Helvetica"),
                text_color=TEXT_COLOR,
                anchor="w",
                fg_color="white"
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(size=13, weight="bold", family="Helvetica"),
                text_color=color,
                anchor="e",
                fg_color="white"
            ).pack(side="right")



    def _add_payment(self):
        """Add a new payment and refresh all relevant views"""
        try:
            amount = float(self.amount_entry.get())
            date = self.date_entry.get()
            notes = self.notes_entry.get()

            payment_data = {
                'date': date,
                'amount': amount,
                'received_by': self.current_user,
                'notes': notes or ""
            }

            success, message, updated_loans = self.user_system.add_payment(self.loan_id, payment_data)
            if success:
                # Refresh the parent dashboard's views
                if hasattr(self.master, 'display_loans'):
                    self.master.display_loans(updated_loans)
                if hasattr(self.master, '_refresh_loan_payments_tab'):
                    self.master._refresh_loan_payments_tab()

                # Refresh this detail window
                self.loan_data, self.payments_df = self.user_system.get_loan_details(self.loan_id)
                for widget in self.container.winfo_children():
                    widget.destroy()
                self._create_ui()

                # Clear the payment form
                self.amount_entry.delete(0, 'end')
                self.notes_entry.delete(0, 'end')

                messagebox.showinfo("Success", "Payment recorded and views updated!")
            else:
                messagebox.showerror("Error", message)

        except ValueError:
            messagebox.showerror("Error", "Please enter valid payment details")

    def _print_payment_history(self):
        """Generate and save payment history report"""
        try:
            pdf = FPDF()
            pdf.add_page()

            # Header
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Payment History - Loan ID {self.loan_id}", 0, 1, 'C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, f"Customer: {self.loan_data['customer_name']}", 0, 1)
            pdf.ln(5)

            # Payment History
            self._add_payment_history_to_pdf(pdf)

            # Save the PDF
            self._save_pdf(pdf, "Payment_History")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate payment history: {str(e)}")

    def _add_payment_history_to_pdf(self, pdf):
        """Add payment history table to PDF"""
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Payment History", 0, 1)

        if self.payments_df.empty:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, "No payments recorded yet", 0, 1)
            return

        # Table header
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(40, 8, "Date", 1, 0, 'C', 1)
        pdf.cell(30, 8, "Amount", 1, 0, 'C', 1)
        pdf.cell(50, 8, "Received By", 1, 0, 'C', 1)
        pdf.cell(0, 8, "Notes", 1, 1, 'C', 1)

        # Table rows - ensure all values are converted to strings
        pdf.set_font("Arial", '', 10)
        pdf.set_fill_color(255, 255, 255)
        for _, payment in self.payments_df.iterrows():
            # Convert all values to strings explicitly
            date_str = str(payment['date'])
            amount_str = f"{float(payment['amount']):,.2f}"
            received_by_str = str(payment['received_by'])
            notes_str = str(payment.get('notes', ''))

            pdf.cell(40, 8, date_str, 1)
            pdf.cell(30, 8, amount_str, 1, 0, 'R')
            pdf.cell(50, 8, received_by_str, 1)
            pdf.cell(0, 8, notes_str, 1, 1)

    def _print_report(self):
        """Generate and save a comprehensive loan report"""
        try:
            pdf = FPDF()
            pdf.add_page()

            # Header
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Loan Management System - Loan Report", 0, 1, 'C')
            pdf.ln(10)

            # Loan Details - ensure all values are converted to strings
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Loan Details", 0, 1)
            pdf.set_font("Arial", '', 10)

            details = [
                ("Loan ID:", str(self.loan_id)),  # Convert loan_id to string
                ("Customer Name:", str(self.loan_data['customer_name'])),
                ("Loan Amount:", f"KES {float(self.loan_data['amount']):,.2f}"),
                ("Daily Payment:", f"KES {float(self.loan_data['payment_per_day']):,.2f}"),
                ("Term:", f"{int(self.loan_data['term_months'])} months"),  # Convert to int then string
                ("Start Date:", str(self.loan_data['start_date'])),
                ("End Date:", str(self.loan_data['end_date'])),
                ("Total to Repay:", f"KES {float(self.loan_data['total_to_repay']):,.2f}"),
                ("Remaining Balance:", f"KES {float(self.loan_data['remaining_balance']):,.2f}"),
                ("Status:", str(self.loan_data['status'])),
                ("Created By:", str(self.loan_data['created_by']))
            ]

            for label, value in details:
                pdf.cell(50, 8, str(label), 0, 0)  # Ensure label is string
                pdf.cell(0, 8, str(value), 0, 1)  # Ensure value is string

            pdf.ln(10)

            # Payment History
            self._add_payment_history_to_pdf(pdf)

            # Save the PDF
            self._save_pdf(pdf, "Loan_Report")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")

    def _save_pdf(self, pdf, report_type):
        """Save PDF file and open it"""
        filename = f"{report_type}_Loan_{self.loan_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=filename
        )

        if filepath:
            pdf.output(filepath)
            messagebox.showinfo("Success", f"Report saved to:\n{filepath}")
            try:
                os.startfile(filepath)
            except:
                messagebox.showinfo("Info", f"Report saved but could not open automatically:\n{filepath}")
