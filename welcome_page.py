
import os
import sys
import time
import itertools
from threading import Thread
import customtkinter as ctk
from tkinter import messagebox
from login_app import LoginApp


class WelcomePage(ctk.CTk):
    def __init__(self):
        # Initialize attributes FIRST before calling super()
        self._after_ids = set()
        self._running = True
        self._thread = None

        # Now call super()
        super().__init__()

        # Configure window
        self.title("Kodongo Loan System")
        self.geometry("900x600")
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
        self.after(2000, self._start_loading)
        self.create_footer()

    def _center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = 900
        height = 600
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

    def _animate_dots(self, count=0):
        """Animate loading dots with proper termination"""
        if not hasattr(self, '_running') or not self._running or count >= 12:
            return

        dots = '.' * (count % 4)
        self.loading_label.configure(text=f"Loading{dots}")
        self.after(500, lambda: self._animate_dots(count + 1))

    def _simulate_loading(self):
        """Simulate loading process"""
        for i in range(1, 4):
            if not hasattr(self, '_running') or not self._running:
                return
            time.sleep(1)
            if self._running:
                self.loading_label.configure(text=f"Loading system components... ({i}/3)")

        if self._running:
            self._transition_to_login()

    def _transition_to_login(self):
        """Transition to login page"""
        if not hasattr(self, '_running') or not self._running:
            return

        self.loading_label.configure(text="System ready! Redirecting to login...")
        self.after(1000, self._open_login_page)

    def _open_login_page(self):
        """Open the login page and destroy welcome page"""
        if hasattr(self, '_running'):
            self._running = False
        self.destroy()
        try:
            app = LoginApp()
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start application: {str(e)}")
            sys.exit(1)

    def create_footer(self):
        """Create footer with developer info"""
        footer_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        footer_frame.pack(side="bottom", fill="x")

        developer_info = "Developed by Seth Odero | Contact: +254759812041"
        footer_label = ctk.CTkLabel(
            footer_frame,
            text=developer_info,
            font=("Arial", 10),
            text_color="gray"
        )
        footer_label.pack(side="right", padx=10)

        copyright_label = ctk.CTkLabel(
            footer_frame,
            text="© 2025",
            font=("Arial", 10),
            text_color="gray"
        )
        copyright_label.pack(side="right", padx=10)

    def _safe_destroy(self):
        """Safely destroy the window with cleanup"""
        if hasattr(self, '_running'):
            self._running = False

        # Cancel all pending after events
        if hasattr(self, '_after_ids'):
            for after_id in list(self._after_ids):
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
        if hasattr(self, '_thread') and self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

        # Destroy window
        try:
            self.destroy()
        except:
            pass