import os
import time
import shutil
import sys
import re
import pyperclip
from PIL import ImageGrab
from io import BytesIO

def get_max_image_number(folder_path):
    max_number = 0
    pattern = re.compile(r"^image(\d+)\.png$")
    for f in os.listdir(folder_path):
        match = pattern.match(f)
        if match:
            image_number = int(match.group(1))
            if image_number > max_number:
                max_number = image_number
    return max_number

def save_image_to_folder(image, folder_path, image_number):
    new_file_name = f"image{image_number}.png"
    new_file_path = os.path.join(folder_path, new_file_name)
    image.save(new_file_path)
    return new_file_name

def get_latex_code(folder_path, file_name):
    return f"\\begin{{center}}\n    \\includegraphics[width=0.5\\linewidth]{{images/{file_name}}}\n\\end{{center}}"

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py /path/to/target/directory")
        sys.exit(1)

    folder_path = sys.argv[1]

    if not os.path.isdir(folder_path):
        print(f"The path '{folder_path}' is not a valid directory.")
        sys.exit(1)

    print(f"Monitoring clipboard and saving images to: {folder_path}")

    last_paste_time = 0
    while True:
        try:
            # Check if there's an image in the clipboard
            image = ImageGrab.grabclipboard()
            if image and image.format == 'PNG':
                current_time = time.time()
                if current_time - last_paste_time > 1:  # Prevent rapid successive saves
                    max_number = get_max_image_number(folder_path)
                    new_file_name = save_image_to_folder(image, folder_path, max_number + 1)
                    latex_code = get_latex_code(folder_path, new_file_name)
                    pyperclip.copy(latex_code)
                    print(f"Saved {new_file_name} and copied LaTeX code to clipboard.")
                    last_paste_time = current_time
        except Exception as e:
            print(f"An error occurred: {e}")
        time.sleep(1)

if __name__ == '__main__':
    main()
