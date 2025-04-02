import time
import os
import sys
import shutil
from typing import Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

class CustomHandler(FileSystemEventHandler):
    """Custom handler for Watchdog"""

    def __init__(self, source_path, destination_path, retry_count=3, retry_delay=1):
        self.source_path = source_path
        self.destination_path = destination_path
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    def on_created(self, event: Union[FileCreatedEvent, FileModifiedEvent]):
        self.handle_event(event)

    def on_modified(self, event: Union[FileCreatedEvent, FileModifiedEvent]):
        self.handle_event(event)

    def handle_event(self, event: Union[FileCreatedEvent, FileModifiedEvent]):
        # Check if it's a file event and not a directory event
        if event.is_directory:
            return

        file_path = event.src_path
        file_name = os.path.basename(file_path)
        destination_file_path = os.path.join(self.destination_path, file_name)

        # Verifica se il file esiste prima di tentare la copia
        if os.path.exists(file_path):
            for attempt in range(self.retry_count):
                try:
                    time.sleep(2)
                    # Tenta di copiare il file nella directory di destinazione
                    shutil.copy2(file_path, destination_file_path)
                    print(f"Copied '{file_name}' to '{self.destination_path}'")
                    break  # Esci dal ciclo se la copia ha successo
                except Exception as e:
                    print(f"Attempt {attempt + 1} to copy '{file_name}' failed: {e}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay)  # Aspetta prima di riprovare
                    else:
                        print(f"Failed to copy '{file_name}' after {self.retry_count} attempts.")
        else:
            print(f"File '{file_path}' does not exist. Skipping copy.")

def main():
    # Check if both source and destination paths are provided
    if len(sys.argv) < 3:
        print("Usage: python script_name.py /path/to/source /path/to/destination")
        sys.exit(1)

    # Get the source and destination directories from command line arguments
    source_path = sys.argv[1]
    destination_path = sys.argv[2]

    # Check if the provided paths are valid directories
    if not os.path.isdir(source_path):
        print(f"The path '{source_path}' is not a valid directory.")
        sys.exit(1)

    if not os.path.isdir(destination_path):
        print(f"The path '{destination_path}' is not a valid directory.")
        sys.exit(1)

    print(f"Monitoring directory: {source_path}")
    print(f"Files will be copied to: {destination_path}")

    # Create instance of observer and custom handler
    observer = Observer()
    handler = CustomHandler(source_path, destination_path)

    # Start observer to monitor the folder non-recursively
    observer.schedule(handler, path=source_path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
