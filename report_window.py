from datetime import datetime
from tkinter import messagebox, ttk, filedialog
import customtkinter as ctk
import pandas as pd


class ReportsWindow(ctk.CTkToplevel):
    def __init__(self, parent, user_system):
        super().__init__(parent)
        self.user_system = user_system
        self.title("Loan Reports")
        self.geometry("1200x800")

        # Make window appear on top and take focus
        self.transient(parent)
        self.grab_set()

        # Track refresh times
        self._last_refresh = {
            'compliance': None,
            'summary': None,
            'overview': None
        }

        self._setup_ui()
        self._load_initial_data()

        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_ui(self):
        """Initialize the main UI components"""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Create notebook for tabs
        self.notebook = ctk.CTkTabview(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add tabs
        self.notebook.add("Payment Compliance")
        self.notebook.add("Payments Summary")
        self.notebook.add("Financial Overview")

        # Configure each tab
        self._setup_compliance_tab()
        self._setup_summary_tab()
        self._setup_overview_tab()

        # Action buttons at bottom
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Export button
        ctk.CTkButton(
            btn_frame,
            text="Export All",
            command=self._export_all_reports,
            fg_color="#2e8b57",
            width=120
        ).pack(side="left", padx=5)

        # Refresh all button
        ctk.CTkButton(
            btn_frame,
            text="Refresh All",
            command=self._refresh_all,
            width=120
        ).pack(side="left", padx=5)

        # Close button
        ctk.CTkButton(
            btn_frame,
            text="Close",
            command=self._on_close,
            fg_color="#e74c3c",
            width=120
        ).pack(side="right", padx=5)

    def _setup_compliance_tab(self):
        """Set up the Payment Compliance tab"""
        tab = self.notebook.tab("Payment Compliance")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Title
        ctk.CTkLabel(
            header_frame,
            text="Daily Payment Compliance",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        # Search/filter frame
        search_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        search_frame.pack(side="right")

        # Search entry
        self.compliance_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search...",
            width=200
        )
        self.compliance_search.pack(side="left", padx=5)
        self.compliance_search.bind("<Return>", lambda e: self._filter_compliance())

        # Status filter
        self.compliance_filter = ctk.CTkComboBox(
            search_frame,
            values=["All", "Paid", "Not Paid"],
            width=100
        )
        self.compliance_filter.set("All")
        self.compliance_filter.pack(side="left", padx=5)

        # Refresh button
        ctk.CTkButton(
            search_frame,
            text="Refresh",
            command=self._refresh_compliance,
            width=80
        ).pack(side="left", padx=5)

        # Treeview frame
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Create treeview with scrollbars
        self.compliance_tree = ttk.Treeview(
            tree_frame,
            columns=("loan_id", "customer", "daily_payment", "paid_today", "last_payment", "status"),
            show="headings",
            selectmode="extended"
        )

        # Configure columns
        self.compliance_tree.heading("loan_id", text="Loan ID")
        self.compliance_tree.heading("customer", text="Customer")
        self.compliance_tree.heading("daily_payment", text="Daily Payment")
        self.compliance_tree.heading("paid_today", text="Paid Today")
        self.compliance_tree.heading("last_payment", text="Last Payment")
        self.compliance_tree.heading("status", text="Status")

        self.compliance_tree.column("loan_id", width=80, anchor="center")
        self.compliance_tree.column("customer", width=200)
        self.compliance_tree.column("daily_payment", width=120, anchor="e")
        self.compliance_tree.column("paid_today", width=100, anchor="center")
        self.compliance_tree.column("last_payment", width=120)
        self.compliance_tree.column("status", width=100, anchor="center")

        # Add scrollbars
        y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.compliance_tree.yview)
        x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.compliance_tree.xview)
        self.compliance_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Grid layout
        self.compliance_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Tag configurations for row coloring
        self.compliance_tree.tag_configure("paid", background="#e8f5e9")
        self.compliance_tree.tag_configure("unpaid", background="#ffebee")
        self.compliance_tree.tag_configure("overdue", background="#fff3e0")

    def _setup_summary_tab(self):
        """Set up the Payments Summary tab"""
        tab = self.notebook.tab("Payments Summary")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Title
        ctk.CTkLabel(
            header_frame,
            text="Payments Summary",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        # Action buttons
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        # Refresh button
        ctk.CTkButton(
            btn_frame,
            text="Refresh",
            command=self._refresh_summary,
            width=100
        ).pack(side="left", padx=5)

        # Export button
        ctk.CTkButton(
            btn_frame,
            text="Export",
            command=lambda: self._export_report("summary"),
            width=100
        ).pack(side="left", padx=5)

        # Treeview frame
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Create treeview
        self.summary_tree = ttk.Treeview(
            tree_frame,
            columns=("loan_id", "customer", "loan_amount", "total_paid", "remaining", "status", "completion"),
            show="headings",
            selectmode="extended"
        )

        # Configure columns
        columns = [
            ("loan_id", "Loan ID", 80, "center"),
            ("customer", "Customer", 200, "w"),
            ("loan_amount", "Loan Amount", 120, "e"),
            ("total_paid", "Total Paid", 120, "e"),
            ("remaining", "Remaining", 120, "e"),
            ("status", "Status", 100, "center"),
            ("completion", "Completion", 100, "center")
        ]

        for col, heading, width, anchor in columns:
            self.summary_tree.heading(col, text=heading)
            self.summary_tree.column(col, width=width, anchor=anchor)

        # Add scrollbars
        y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.summary_tree.yview)
        x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.summary_tree.xview)
        self.summary_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Grid layout
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Tag configurations
        self.summary_tree.tag_configure("paid", background="#e8f5e9")
        self.summary_tree.tag_configure("active", background="#e3f2fd")
        self.summary_tree.tag_configure("defaulted", background="#ffebee")

    def _setup_overview_tab(self):
        """Set up the Financial Overview tab"""
        tab = self.notebook.tab("Financial Overview")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Title
        ctk.CTkLabel(
            header_frame,
            text="Financial Overview",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        # Refresh button
        ctk.CTkButton(
            header_frame,
            text="Refresh",
            command=self._refresh_overview,
            width=100
        ).pack(side="right")

        # Metrics frame
        metrics_frame = ctk.CTkFrame(tab, fg_color="transparent")
        metrics_frame.grid(row=1, column=0, sticky="nsew", pady=10)

        # Create metric cards in a grid
        self.metric_cards = {}
        metrics = [
            ("total_loans", "Total Loans", "#3498db"),
            ("active_loans", "Active Loans", "#2ecc71"),
            ("amount_out", "Amount Out", "#e74c3c"),
            ("daily_collection", "Daily Collection", "#f39c12"),
            ("total_interest", "Total Interest", "#9b59b6"),
            ("recovery_rate", "Recovery Rate", "#1abc9c")
        ]

        for i, (key, title, color) in enumerate(metrics):
            row = i // 3
            col = i % 3

            card = ctk.CTkFrame(
                metrics_frame,
                border_width=1,
                border_color="#e0e0e0",
                corner_radius=10,
                height=100
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            card.grid_propagate(False)

            # Title
            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=color
            ).pack(pady=(10, 5))

            # Value
            value_label = ctk.CTkLabel(
                card,
                text="0",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            value_label.pack(pady=(0, 10))

            self.metric_cards[key] = value_label

        # Configure grid weights
        for i in range(3):
            metrics_frame.grid_columnconfigure(i, weight=1)

        # Chart placeholder
        chart_frame = ctk.CTkFrame(tab)
        chart_frame.grid(row=2, column=0, sticky="nsew", pady=10)

        ctk.CTkLabel(
            chart_frame,
            text="Performance charts will be displayed here",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        ).pack(pady=50)

    def _load_initial_data(self):
        """Load data for all tabs when window opens"""
        self._load_compliance_data()
        self._load_summary_data()
        self._load_overview_data()

        # Update refresh timestamps
        now = datetime.now()
        self._last_refresh = {
            'compliance': now,
            'summary': now,
            'overview': now
        }

    def _load_compliance_data(self):
        """Load data into compliance tab"""
        # Clear existing data
        for item in self.compliance_tree.get_children():
            self.compliance_tree.delete(item)

        try:
            # Get data from system
            df = self.user_system.get_payment_compliance_report()

            if df.empty:
                return

            # Add data to treeview
            for _, row in df.iterrows():
                loan_id = row.get('loan_id', '')
                customer = row.get('customer_name', '')
                # Change from 'daily_amount' to 'payment_per_day'
                daily_payment = row.get('payment_per_day', 0)
                paid_today = row.get('paid_today', 'No')
                last_payment = row.get('last_payment', 'Never')
                status = row.get('status', 'Active')

                # Determine tag for row coloring
                tags = []
                if paid_today == 'Yes':
                    tags.append('paid')
                else:
                    tags.append('unpaid')

                if status.lower() == 'overdue':
                    tags.append('overdue')

                # Insert row
                self.compliance_tree.insert(
                    "", "end",
                    values=(
                        loan_id,
                        customer,
                        f"KES {float(daily_payment):,.2f}",
                        paid_today,
                        last_payment,
                        status
                    ),
                    tags=tags
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load compliance data: {str(e)}")

    def _load_summary_data(self):
        """Load data into payments summary tab"""
        # Clear existing data
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        try:
            # Get data from system
            df = self.user_system.generate_payments_summary_report()

            if df.empty:
                return

            # Add data to treeview
            for _, row in df.iterrows():
                loan_id = row.get('loan_id', '')
                customer = row.get('customer_name', '')
                loan_amount = row.get('loan_amount', 0)
                total_paid = row.get('total_paid', 0)
                remaining = row.get('remaining', 0)
                status = row.get('status', 'Active')

                # Calculate completion percentage
                try:
                    completion = (float(total_paid) / float(loan_amount)) * 100
                except ZeroDivisionError:
                    completion = 0

                # Determine tag for row coloring
                tags = [status.lower()]

                # Insert row
                self.summary_tree.insert(
                    "", "end",
                    values=(
                        loan_id,
                        customer,
                        f"KES {float(loan_amount):,.2f}",
                        f"KES {float(total_paid):,.2f}",
                        f"KES {float(remaining):,.2f}",
                        status,
                        f"{completion:.1f}%"
                    ),
                    tags=tags
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load summary data: {str(e)}")

    def _load_overview_data(self):
        """Load data into financial overview tab"""
        try:
            # Get summary data
            summary = self.user_system.get_daily_financial_summary()

            # Update metric cards
            self.metric_cards['total_loans'].configure(
                text=str(summary.get('total_loans', 0)))

            self.metric_cards['active_loans'].configure(
                text=str(summary.get('active_loans', 0)))

            self.metric_cards['amount_out'].configure(
                text=f"KES {summary.get('outstanding', 0):,.2f}")

            self.metric_cards['daily_collection'].configure(
                text=f"KES {summary.get('daily_paid', 0):,.2f}")

            self.metric_cards['total_interest'].configure(
                text=f"KES {summary.get('total_interest', 0):,.2f}")

            # Calculate recovery rate
            try:
                amount_given = float(summary.get('amount_given', 1))
                total_repaid = amount_given - float(summary.get('outstanding', 0))
                recovery_rate = (total_repaid / amount_given) * 100
            except ZeroDivisionError:
                recovery_rate = 0

            self.metric_cards['recovery_rate'].configure(
                text=f"{recovery_rate:.1f}%")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load overview data: {str(e)}")

    def _filter_compliance(self):
        """Filter compliance data based on search and filter criteria"""
        search_term = self.compliance_search.get().lower()
        filter_value = self.compliance_filter.get()

        # Show all items first
        for item in self.compliance_tree.get_children():
            self.compliance_tree.item(item, open=True)

        # Apply filters
        for item in self.compliance_tree.get_children():
            values = self.compliance_tree.item(item, 'values')
            visible = True

            # Apply search filter
            if search_term:
                if not any(search_term in str(v).lower() for v in values):
                    visible = False

            # Apply status filter
            if filter_value == "Paid" and values[3] != "Yes":
                visible = False
            elif filter_value == "Not Paid" and values[3] == "Yes":
                visible = False

            # Set item visibility
            self.compliance_tree.item(item, open=visible)

    def _refresh_compliance(self):
        """Refresh compliance tab data"""
        try:
            self._load_compliance_data()
            self._last_refresh['compliance'] = datetime.now()
            messagebox.showinfo("Success", "Compliance data refreshed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh compliance data: {str(e)}")

    def _refresh_summary(self):
        """Refresh summary tab data"""
        try:
            self._load_summary_data()
            self._last_refresh['summary'] = datetime.now()
            messagebox.showinfo("Success", "Summary data refreshed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh summary data: {str(e)}")

    def _refresh_overview(self):
        """Refresh overview tab data"""
        try:
            self._load_overview_data()
            self._last_refresh['overview'] = datetime.now()
            messagebox.showinfo("Success", "Overview data refreshed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh overview data: {str(e)}")

    def _refresh_all(self):
        """Refresh all tabs"""
        self._refresh_compliance()
        self._refresh_summary()
        self._refresh_overview()

    def _export_report(self, report_type):
        """Export report to file"""
        try:
            # Get appropriate data based on report type
            if report_type == "compliance":
                df = self.user_system.get_payment_compliance_report()
                default_name = "payment_compliance"
            else:
                df = self.user_system.generate_payments_summary_report()
                default_name = "payments_summary"

            if df.empty:
                messagebox.showwarning("No Data", "No data available to export")
                return

            # Ask for file path
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[
                    ("Excel Files", "*.xlsx"),
                    ("CSV Files", "*.csv"),
                    ("All Files", "*.*")
                ],
                initialfile=f"{default_name}_{datetime.now().strftime('%Y%m%d')}"
            )

            if not filepath:
                return

            # Save based on file extension
            if filepath.endswith('.xlsx'):
                df.to_excel(filepath, index=False)
            else:
                df.to_csv(filepath, index=False)

            messagebox.showinfo("Success", f"Report exported to:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export report: {str(e)}")

    def _export_all_reports(self):
        """Export all reports to a zip file"""
        try:
            # Get all reports
            compliance_df = self.user_system.get_payment_compliance_report()
            summary_df = self.user_system.generate_payments_summary_report()

            if compliance_df.empty and summary_df.empty:
                messagebox.showwarning("No Data", "No data available to export")
                return

            # Ask for directory to save files
            dir_path = filedialog.askdirectory(title="Select folder to save reports")
            if not dir_path:
                return

            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save files
            files = []
            if not compliance_df.empty:
                compliance_path = f"{dir_path}/payment_compliance_{timestamp}.xlsx"
                compliance_df.to_excel(compliance_path, index=False)
                files.append(compliance_path)

            if not summary_df.empty:
                summary_path = f"{dir_path}/payments_summary_{timestamp}.xlsx"
                summary_df.to_excel(summary_path, index=False)
                files.append(summary_path)

            messagebox.showinfo(
                "Success",
                f"Reports exported to:\n{dir_path}\n\nFiles:\n" + "\n".join(files))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to export reports: {str(e)}")

    def _on_close(self):
        """Handle window close event"""
        self.grab_release()
        self.destroy()