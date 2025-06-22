import os
import time
import errno
from typing import Optional


class FileLock:
    """
    A simple file-based lock implementation with timeout support.

    This class provides a cross-process locking mechanism using lock files.
    It supports context manager protocol for easy use with 'with' statements.

    Args:
        filename (str): Base filename to use for the lock
        timeout (float): Maximum time to wait for the lock (in seconds)
        delay (float): Delay between lock acquisition attempts (in seconds)
        pid_aware (bool): Whether to include process ID in lock file
    """

    def __init__(self, filename: str, timeout: float = 10.0, delay: float = 0.1, pid_aware: bool = True):
        self.lock_file = f"{filename}.lock"
        self.timeout = timeout
        self.delay = delay
        self.pid_aware = pid_aware
        self.fd: Optional[int] = None
        self._locked = False

    def acquire(self) -> bool:
        """
        Acquire the lock by creating a lock file.

        Returns:
            bool: True if lock was acquired, False if timeout occurred
        """
        start_time = time.time()

        while True:
            try:
                # Try to create the lock file exclusively
                self.fd = os.open(
                    self.lock_file,
                    os.O_CREAT | os.O_EXCL | os.O_RDWR,
                    0o644  # Set permissions (rw-r--r--)
                )

                if self.pid_aware:
                    # Write current PID to lock file
                    os.write(self.fd, str(os.getpid()).encode())

                self._locked = True
                return True

            except OSError as e:
                if e.errno != errno.EEXIST:  # Only handle "file exists" error
                    raise

                # Check if lock is stale (process that created it no longer exists)
                if self._is_stale():
                    self._break_lock()
                    continue

                # Check timeout
                if time.time() - start_time >= self.timeout:
                    return False

                # Wait before retrying
                time.sleep(self.delay)

    def release(self) -> None:
        """Release the lock by removing the lock file."""
        if not self._locked:
            return

        try:
            if self.fd is not None:
                os.close(self.fd)
            os.unlink(self.lock_file)
        except OSError:
            pass
        finally:
            self.fd = None
            self._locked = False

    def _is_stale(self) -> bool:
        """Check if the lock file is stale (owner process no longer exists)."""
        try:
            with open(self.lock_file, 'r') as f:
                pid_str = f.read().strip()

            if pid_str and pid_str.isdigit():
                pid = int(pid_str)
                try:
                    os.kill(pid, 0)  # Check if process exists
                    return False
                except OSError:
                    return True  # Process doesn't exist
        except (IOError, ValueError):
            pass

        return False

    def _break_lock(self) -> None:
        """Forcefully remove a stale lock file."""
        try:
            os.unlink(self.lock_file)
        except OSError:
            pass

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    @property
    def is_locked(self) -> bool:
        """Check if the lock is currently held."""
        return self._locked

    def __del__(self):
        """Clean up lock file when object is garbage collected."""
        self.release()