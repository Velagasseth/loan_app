import sys
import ctypes
import platform


def set_dpi_awareness():
    """
    Set DPI awareness for the application to handle high DPI displays properly
    """
    if sys.platform == 'win32':
        try:
            # Windows 8.1 and later
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per monitor DPI aware
        except (AttributeError, OSError):
            try:
                # Windows Vista and later
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass
    elif sys.platform == 'darwin':
        # macOS generally handles DPI scaling well automatically
        pass
    else:
        # Linux - set GDK scale if available
        try:
            from gi.repository import Gtk
            Gtk.init()
            settings = Gtk.Settings.get_default()
            settings.set_property('gtk-xft-dpi', 96 * 2)  # Example 2x scaling
        except ImportError:
            pass


def scale_for_dpi(window):
    """
    Scale window elements based on DPI
    """
    if sys.platform == 'win32':
        try:
            # Get DPI scaling factor
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(window.winfo_id())
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            scaling = dpi / 96.0  # 96 is 100% scaling

            # Scale fonts and widgets
            window.tk.call('tk', 'scaling', scaling)
            return scaling
        except:
            return 1.0
    return 1.0