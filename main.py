import os
import sys
import ctypes
from tkinter import messagebox

from dpi_awareness import set_dpi_awareness, scale_for_dpi
from network_utils import NetworkManager
from file_locking import FileLock

# At application startup
set_dpi_awareness()
network_mgr = NetworkManager()
data_dir = network_mgr.get_data_directory()


def check_network_storage(self):
    """Periodically check network storage availability"""
    if self.user_system.shared_mode:
        if not os.path.exists(self.user_system.data_folder):
            if messagebox.askyesno(
                    "Network Error",
                    "Network storage unavailable. Switch to local mode temporarily?"
            ):
                self.user_system.shared_mode = False
                self.user_system._initialize_paths()
                messagebox.showinfo(
                    "Local Mode",
                    "Now running in local-only mode. Data will sync when network is available."
                )

    # Reschedule check every 5 minutes
    self.after(300000, self.check_network_storage)


if __name__ == "__main__":

    try:
        from welcome_page import WelcomePage

        welcome = WelcomePage()
        welcome.mainloop()
    except Exception as e:
        print(f"Application failed to start: {str(e)}")
        sys.exit(1)
