# University Student Tools

A collection of utilities for university students to help with common tasks.

## Installation

1. Clone this repository
2. Install the package in development mode:
```bash
pip install -e .
```

## Features

### Image Clipboard Tool
A tool that monitors the clipboard for images and automatically saves them with LaTeX code generation.

Usage:
```bash
python -m university_student_tools.clipboard.image_clipboard /path/to/target/directory
```

### File Copy Manager
A tool that monitors a directory for changes and automatically copies files to a destination directory.

Usage:
```bash
python -m university_student_tools.file_manager.copy_files /path/to/source /path/to/destination
```

## Dependencies

- Pillow
- pyperclip
- watchdog

## Development

The package is structured as follows:
```
university_student_tools/
├── clipboard/
│   ├── __init__.py
│   └── image_clipboard.py
├── file_manager/
│   ├── __init__.py
│   └── copy_files.py
└── __init__.py
```

## License

MIT License