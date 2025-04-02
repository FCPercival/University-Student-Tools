#VERSION 1.2
import time
import pathlib
import os
import sys
import re
import pyperclip
from typing import Union
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

class CustomHandler(FileSystemEventHandler):
    """Custom handler for Watchdog"""

    def __init__(self, folder_path):
        self.folder_path = folder_path

    def on_created(self, event: Union[FileCreatedEvent]):
        # Check if it's a file creation event
        if isinstance(event, FileCreatedEvent):
            file_path = event.src_path
            file_name = os.path.basename(file_path)

            # Check if the file is "img.png"
            if file_name == "img.png":
                print(f"File 'img.png' detected at: {file_path}")

                # Get the highest number from files starting with "image" and ending with ".png"
                max_image_number = self.get_max_image_number()

                # Create the new file name
                new_file_name = f"image{max_image_number + 1}.png"
                new_file_path = os.path.join(self.folder_path, new_file_name)

                time.sleep(0.5)

                # Rename the file
                os.rename(file_path, new_file_path)
                print(f"Renamed '{file_name}' to '{new_file_name}'")

                # Copy the LaTeX command with image number to the clipboard
                image_number = max_image_number + 1
                latex_command = f"""\\begin{{center}}\n    \\includegraphics[width=0.8\\textwidth]{{images/image{image_number}}}\n\\end{{center}}"""
                pyperclip.copy(latex_command)
                print(f"Copied LaTeX command for image {image_number} to clipboard")

    def get_max_image_number(self):
        """Find the maximum image number in the directory"""
        max_number = 0
        # Regex to match files like "imageX.png" where X is a number
        pattern = re.compile(r"^image(\d+)\.png$")

        # Iterate through files in the folder
        for f in os.listdir(self.folder_path):
            match = pattern.match(f)
            if match:
                # Extract the number and convert it to an integer
                image_number = int(match.group(1))
                max_number = max(max_number, image_number)

        return max_number

def main():
    # Check if a path argument is provided
    if len(sys.argv) < 2:
        print("Usage: python script_name.py /path/to/directory")
        sys.exit(1)

    # Get the directory to monitor from the command line argument
    folder_path = sys.argv[1]

    # Check if the provided path is a valid directory
    if not os.path.isdir(folder_path):
        print(f"The path '{folder_path}' is not a valid directory.")
        sys.exit(1)

    print(f"Monitoring directory: {folder_path}")

    # Create instance of observer and custom handler
    observer = Observer()
    handler = CustomHandler(folder_path)

    # Start observer to monitor the folder non-recursively
    observer.schedule(handler, path=folder_path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
