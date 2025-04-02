#!/usr/bin/env python3

#pip install keyboard pyperclip

from abc import ABC, abstractmethod
import keyboard
import pyperclip
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass


@dataclass
class HotkeyBinding:
    """Data class for hotkey configuration"""
    key_combination: str
    description: str
    category: str


import time


class LaTeXMacro(ABC):
    """Abstract base class for LaTeX macros"""

    def __init__(self, hotkey_binding: HotkeyBinding):
        self.hotkey_binding = hotkey_binding

    def get_selected_text(self) -> str:
        """Get currently selected text using clipboard"""
        previous_clipboard = pyperclip.paste()
        keyboard.send('ctrl+c')
        # Use time.sleep instead of keyboard.wait
        time.sleep(0.15)
        selected_text = pyperclip.paste()
        pyperclip.copy(previous_clipboard)

        if selected_text == previous_clipboard:
            return ''
        return selected_text

    def execute(self) -> None:
        """Execute the macro on selected text"""
        text = self.get_selected_text()
        if text and text != '':
            result = self.apply(text)
            pyperclip.copy(result)
            keyboard.send('ctrl+v')
            # Add a small delay after pasting
            #time.sleep(0.1)


class CommandMacro(LaTeXMacro):
    """Macro for LaTeX commands with arguments"""

    def __init__(self, command: str, hotkey_binding: HotkeyBinding):
        super().__init__(hotkey_binding)
        self.command = command

    def apply(self, text: str) -> str:
        return f"\\{self.command}{{{text}}}"


class EnvironmentMacro(LaTeXMacro):
    """Macro for LaTeX environments"""

    def __init__(self, environment: str, hotkey_binding: HotkeyBinding):
        super().__init__(hotkey_binding)
        self.environment = environment

    def apply(self, text: str) -> str:
        return f"\\begin{{{self.environment}}}\n{text}\n\\end{{{self.environment}}}"


class InlineMathMacro(LaTeXMacro):
    """Macro for inline math mode"""

    def apply(self, text: str) -> str:
        return f"${text}$"


class DisplayMathMacro(LaTeXMacro):
    """Macro for display math mode"""

    def apply(self, text: str) -> str:
        return f"\$${text}\$$"


class LaTeXHotkeyManager:
    """Manages LaTeX hotkeys and macros"""

    def __init__(self):
        self.macros: Dict[str, LaTeXMacro] = {}
        self.setup_logging()
        self.register_default_macros()

    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def register_macro(self, macro: LaTeXMacro) -> None:
        """Register a new macro with its hotkey"""
        try:
            keyboard.add_hotkey(
                macro.hotkey_binding.key_combination,
                macro.execute
            )
            self.macros[macro.hotkey_binding.key_combination] = macro
            self.logger.info(
                f"Registered {macro.hotkey_binding.description} "
                f"with hotkey: {macro.hotkey_binding.key_combination}"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to register {macro.hotkey_binding.description}: {str(e)}"
            )

    def register_default_macros(self):
        """Register all default LaTeX macros"""
        default_macros = [
            # Text formatting
            CommandMacro("textbf", HotkeyBinding(
                "ctrl+alt+b", "Bold", "formatting")),
            CommandMacro("textit", HotkeyBinding(
                "ctrl+i", "Italic", "formatting")),
            CommandMacro("underline", HotkeyBinding(
                "ctrl+u", "Underline", "formatting")),

            # Structure
            CommandMacro("section", HotkeyBinding(
                "ctrl+1", "Section", "structure")),
            CommandMacro("subsection", HotkeyBinding(
                "ctrl+2", "Subsection", "structure")),
            CommandMacro("subsubsection", HotkeyBinding(
                "ctrl+3", "Subsubsection", "structure")),

            # Math
            InlineMathMacro(HotkeyBinding(
                "ctrl+m", "Inline Math", "math")),
            DisplayMathMacro(HotkeyBinding(
                "ctrl+shift+m", "Display Math", "math")),

            # Environments
            EnvironmentMacro("itemize", HotkeyBinding(
                "ctrl+p", "Itemize Environment", "environment")),
            EnvironmentMacro("enumerate", HotkeyBinding(
                "ctrl+o", "Enumerate Environment", "environment")),
        ]

        for macro in default_macros:
            self.register_macro(macro)

    def get_macros_by_category(self) -> Dict[str, List[LaTeXMacro]]:
        """Group registered macros by category"""
        categories: Dict[str, List[LaTeXMacro]] = {}
        for macro in self.macros.values():
            category = macro.hotkey_binding.category
            if category not in categories:
                categories[category] = []
            categories[category].append(macro)
        return categories

    def print_available_hotkeys(self):
        """Print all available hotkeys grouped by category"""
        categories = self.get_macros_by_category()
        print("\nAvailable Hotkeys:")
        for category, macros in categories.items():
            print(f"\n{category.title()}:")
            for macro in macros:
                print(f"  {macro.hotkey_binding.key_combination}: "
                      f"{macro.hotkey_binding.description}")

    def start(self):
        """Start the hotkey listener"""
        self.logger.info("LaTeX Hotkey Manager started")
        self.print_available_hotkeys()
        print("\nPress ESC to exit")
        keyboard.wait('esc')


def main():
    """Main entry point"""
    try:
        manager = LaTeXHotkeyManager()
        manager.start()
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise


if __name__ == "__main__":
    main()