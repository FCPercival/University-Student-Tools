# University-Student-Tools
A suite of tools designed to assist university students in taking notes and managing their academic workflow.

## Tools Overview

### 1. TestToolbar
A customizable toolbar application that allows you to create quick-launch buttons for frequently used scripts and applications.

#### Features:
- Draggable interface
- Show/Hide functionality
- Customizable icons and commands
- Process management for running scripts

#### Configuration:
To modify the toolbar commands, edit the `commands` list in `TestToolbar.py`:
```python
self.commands = [
    {
        "name": "NameToShow",
        "command": "C:\\Windows\\System32\\cmd.exe /k python C:\\PATH\\TO\\SCRIPT\\script.py",
        "color": "#5856D6"  # Purple
    }
]
```

### 2. MacroLaTeX
A hotkey manager for LaTeX commands that allows you to quickly format text using keyboard shortcuts.

#### Features:
- Text formatting shortcuts (bold, italic, underline)
- Structure shortcuts (sections, subsections)
- Math mode shortcuts (inline and display math)
- Environment shortcuts (itemize, enumerate)

#### Available Hotkeys:
- **Formatting**:
  - `Ctrl+Alt+B`: Bold
  - `Ctrl+I`: Italic
  - `Ctrl+U`: Underline
- **Structure**:
  - `Ctrl+1`: Section
  - `Ctrl+2`: Subsection
  - `Ctrl+3`: Subsubsection
- **Math**:
  - `Ctrl+M`: Inline Math
  - `Ctrl+Shift+M`: Display Math
- **Environments**:
  - `Ctrl+P`: Itemize Environment
  - `Ctrl+O`: Enumerate Environment

### 3. ImageClipboard
A tool that monitors your clipboard for images and automatically saves them with LaTeX-compatible code.

#### Features:
- Automatic image saving from clipboard
- LaTeX code generation for included images
- Sequential image numbering
- Customizable image width in LaTeX output

#### Usage:
```bash
python imageclipboard.py /path/to/target/directory
```

### 4. CopyFiles
A file monitoring tool that automatically copies new or modified files from one directory to another.

#### Features:
- Real-time file monitoring
- Automatic file copying
- Retry mechanism for failed copies
- Non-recursive directory monitoring

#### Usage:
```bash
python copy_files.py /path/to/source /path/to/destination
```

### 5. ImageLaTeX
A specialized tool for handling image files in LaTeX documents.

#### Features:
- Automatic image renaming
- LaTeX code generation for image inclusion
- Customizable image width in LaTeX output
- Sequential image numbering

#### Usage:
```bash
python imageLaTeX.py /path/to/monitored/directory
```

## Requirements

All tools require Python 3.x and the following dependencies, which can be installed using the requirements file:

```bash
pip install -r requirements.txt
```

See [requirements.txt](requirements.txt) for the complete list of dependencies.

## Usage

Each tool can be run independently based on your needs. The tools are designed to work together to create a seamless note-taking experience:

1. Use `TestToolbar` to create quick access to your scripts
2. Use `MacroLaTeX` for quick LaTeX formatting
3. Use `ImageClipboard` or `ImageLaTeX` for handling images in your LaTeX documents
4. Use `CopyFiles` to maintain synchronized copies of your files

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.