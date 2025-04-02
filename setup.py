from setuptools import setup, find_packages

setup(
    name="university-student-tools",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Pillow",
        "pyperclip",
        "watchdog",
    ],
    entry_points={
        "console_scripts": [
            "image-clipboard=university_student_tools.clipboard.image_clipboard:main",
            "copy-files=university_student_tools.file_manager.copy_files:main",
        ],
    },
    author="Mattia",
    description="A collection of tools for university students",
    python_requires=">=3.6",
) 