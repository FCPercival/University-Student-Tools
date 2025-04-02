"""
Module for handling file copying operations with monitoring capabilities
"""

import time
import os
import sys
import shutil
from typing import Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

class CustomHandler(FileSystemEventHandler):
    """Custom handler for Watchdog to handle file system events."""

    def __init__(self, source_path: str, destination_path: str, retry_count: int = 3, retry_delay: int = 1):
        """
        Initialize the handler with source and destination paths.
        
        Args:
            source_path: Path to monitor for changes
            destination_path: Path to copy files to
            retry_count: Number of times to retry failed copies
            retry_delay: Delay between retry attempts in seconds
        """
        self.source_path = source_path
        self.destination_path = destination_path
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    def on_created(self, event: Union[FileCreatedEvent, FileModifiedEvent]) -> None:
        """Handle file creation events."""
        self.handle_event(event)

    def on_modified(self, event: Union[FileCreatedEvent, FileModifiedEvent]) -> None:
        """Handle file modification events."""
        self.handle_event(event)

    def handle_event(self, event: Union[FileCreatedEvent, FileModifiedEvent]) -> None:
        """
        Handle file system events by copying files to destination.
        
        Args:
            event: The file system event that occurred
        """
        if event.is_directory:
            return

        file_path = event.src_path
        file_name = os.path.basename(file_path)
        destination_file_path = os.path.join(self.destination_path, file_name)

        if os.path.exists(file_path):
            for attempt in range(self.retry_count):
                try:
                    time.sleep(2)
                    shutil.copy2(file_path, destination_file_path)
                    print(f"Copied '{file_name}' to '{self.destination_path}'")
                    break
                except Exception as e:
                    print(f"Attempt {attempt + 1} to copy '{file_name}' failed: {e}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay)
                    else:
                        print(f"Failed to copy '{file_name}' after {self.retry_count} attempts.")
        else:
            print(f"File '{file_path}' does not exist. Skipping copy.")

def monitor_directory(source_path: str, destination_path: str) -> None:
    """
    Monitor a directory for changes and copy files to destination.
    
    Args:
        source_path: Path to monitor for changes
        destination_path: Path to copy files to
    """
    observer = Observer()
    handler = CustomHandler(source_path, destination_path)
    observer.schedule(handler, path=source_path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 3:
        print("Usage: python -m university_student_tools.file_manager.copy_files /path/to/source /path/to/destination")
        sys.exit(1)

    source_path = sys.argv[1]
    destination_path = sys.argv[2]

    if not os.path.isdir(source_path):
        print(f"The path '{source_path}' is not a valid directory.")
        sys.exit(1)

    if not os.path.isdir(destination_path):
        print(f"The path '{destination_path}' is not a valid directory.")
        sys.exit(1)

    print(f"Monitoring directory: {source_path}")
    print(f"Files will be copied to: {destination_path}")
    monitor_directory(source_path, destination_path)

if __name__ == '__main__':
    main() 