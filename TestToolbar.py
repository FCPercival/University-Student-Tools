# V5.12 - Higher Resolution via Downscaling (Corrected Interpretation)
import tkinter as tk
from tkinter import font as tkFont
from tkinter import colorchooser, ttk
import subprocess
import os
import signal
import psutil
import sys
import platform
import math
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
import base64
import io
import matplotlib.font_manager
import json
import os
import shlex
import threading


# Helper to get the base path of the script
script_base_path = os.path.dirname(os.path.abspath(__file__))

# --- Scaling Factor for Internal Rendering ---
RENDER_SCALE = 3 # Render at 3x size then downscale for sharpness
# ---

# --- Base64 Image ---
SHOW_BUTTON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAACwAAAAsCAYAAAAehFoBAAAACXBIWXMAAAsTAAALEwEAmpwYAAAARElEQVR4nO3WMQoAIAgEwP7/07uDBpTYQlYbLp4a5wIAAAAAAAAAAAAAAADg3UvLSRQuu0QAAAAAAMDKx8R3lPZfAJQj4R8KRzNTAAAAAElFTkSuQmCC" # Sample 44x44 icon placeholder

# --- Constants (Original/Target Display Sizes) ---
BG_COLOR_TRANSPARENT = "#010101"; BAR_BG_COLOR = "#2C2C2E"; BAR_BG_ALPHA = 0.90
SEPARATOR_COLOR = "#4A4A4E"; TEXT_COLOR_PRIMARY = "#FFFFFF"; INDICATOR_COLOR = "#FFFFFF"
ICON_HOVER_BG_COLOR = "#444448"; BUTTON_GRAY_COLOR = "#3A3A3C"; BUTTON_GRAY_HOVER_COLOR = "#4A4A4E"
BUTTON_GRAY_CLICK_COLOR = "#2A2A2C"; CLOSE_BUTTON_COLOR = "#FF453A"

ICON_SIZE = 48 # Target display size for the icon content
ICON_CANVAS_HEIGHT = 52 # Target display height for the canvas holding the icon
ICON_CANVAS_WIDTH_PADDING = 8 # Target display padding within icon canvas
ICON_PADDING_VERTICAL = 6 # Target vertical padding between icons
BAR_PADDING_VERTICAL = 10 # Target top/bottom padding inside the bar frame
BAR_PADDING_HORIZONTAL = 10 # Target left/right padding inside the bar frame
INDICATOR_RADIUS = 3 # Target display radius for indicator
BUTTON_HEIGHT = 30 # Target display height for buttons
CLOSE_BUTTON_SIZE = 18 # Target display size for close button
SHOW_BUTTON_SIZE = 44 # Target display size for show button
SEPARATOR_HEIGHT = 1 # Target display height for separator
CORNER_RADIUS = 14 # Target display corner radius for the bar
CLICK_TIME_THRESHOLD = 300; CLICK_MOVE_THRESHOLD = 5

# --- Pillow Internal Rendering Constants (Apply Scale Here) ---
PILLOW_TARGET_ICON_SIZE = ICON_SIZE # Keep track of final desired size
PILLOW_RENDER_SIZE = PILLOW_TARGET_ICON_SIZE * RENDER_SCALE # Internal canvas size
PILLOW_ICON_FONT_SIZE = int(15 * RENDER_SCALE) # Internal font size
PILLOW_ICON_PADDING = int(4 * RENDER_SCALE) # Internal padding

# --- get JSON ---
def load_commands(config_file="commands.json"):
    if os.path.isabs(config_file):
        config_path = config_file
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_path, config_file)
    try:
        with open(config_path, "r") as f:
            commands = json.load(f)
        # Replace the placeholder in the command string with the actual base path.
        for cmd in commands:
            if "{BASE_PATH}" in cmd["command"]:
                cmd["command"] = cmd["command"].format(BASE_PATH=base_path)
        return commands
    except Exception as e:
        print(f"Error loading command configuration: {e}")
        return []

# --- Font Setup ---
def get_tk_font(size, weight="normal"): # Use unscaled size for Tkinter elements
    family = "Arial";
    if sys.platform == "darwin": family = "SF Pro Text"
    elif sys.platform == "win32":
        try: tkFont.Font(family="Segoe UI", size=size); family = "Segoe UI"
        except tk.TclError: pass
    else:
        available_fonts = tkFont.families()
        if "Cantarell" in available_fonts: family = "Cantarell"
        elif "Noto Sans" in available_fonts: family = "Noto Sans"
        elif "DejaVu Sans" in available_fonts: family = "DejaVu Sans"
    return tkFont.Font(family=family, size=size, weight=weight)

PIL_FONT_PATH = None
if PIL_AVAILABLE:
    try: # Find bold font path (unchanged logic)
        font_prefs = ['Segoe UI Bold', 'DejaVu Sans Bold', 'Cantarell Bold', 'Arial Bold', 'Helvetica Bold']; found_font = None
        for pref in font_prefs:
             try: found_font = matplotlib.font_manager.findfont(pref, fallback_to_default=False);
             except: continue
             if found_font: break
        if not found_font: props = matplotlib.font_manager.FontProperties(family='sans-serif', weight='bold'); found_font = matplotlib.font_manager.findfont(props, fallback_to_default=True)
        if found_font and os.path.exists(found_font): PIL_FONT_PATH = found_font; print(f"Using font: {PIL_FONT_PATH}")
        else: print("Warning: Could not find bold system font for Pillow.")
    except Exception as e: print(f"Warning: Error finding font: {e}.")

# Tkinter fonts (assign later, use unscaled sizes)
FONT_BUTTON = None; FONT_CLOSE_BUTTON = None; FONT_SHOW_BUTTON = None

# --- Helper Function (Unchanged) ---
def adjust_color(hex_color, factor):
    if not hex_color.startswith("#") or len(hex_color) != 7: return hex_color
    r,g,b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
    r=min(255,int(r*factor)); g=min(255,int(g*factor)); b=min(255,int(b*factor))
    return f"#{r:02x}{g:02x}{b:02x}"

# --- Image Generation Function (Renders High-Res, Downscales) ---
def create_command_icon_image(final_size, text, color_hex):
    """Generates a downscaled PhotoImage using Pillow for better quality."""
    if not PIL_AVAILABLE or not PIL_FONT_PATH: return None

    render_size = final_size * RENDER_SCALE # Internal high-res size

    try:
        # Create transparent high-res image
        image = Image.new('RGBA', (render_size, render_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Calculate high-res circle properties using scaled padding
        padding = PILLOW_ICON_PADDING # Already scaled
        diameter = render_size - 2 * padding
        x1,y1,x2,y2 = padding, padding, padding+diameter, padding+diameter
        draw.ellipse([(x1, y1), (x2, y2)], fill=color_hex, outline=None, width=0)

        # Load font at scaled size
        try: font = ImageFont.truetype(PIL_FONT_PATH, PILLOW_ICON_FONT_SIZE) # Already scaled
        except IOError: font = ImageFont.load_default()

        # Calculate text position on high-res canvas
        try: # Use textbbox
            bbox = draw.textbbox((0,0),text,font=font,anchor="lt"); text_width=bbox[2]-bbox[0]; text_height=bbox[3]-bbox[1]
            text_x = (render_size - text_width) / 2; text_y = (render_size - text_height) / 2 - (text_height * 0.1)
        except AttributeError: # Fallback
             text_width, text_height = draw.textsize(text, font=font); text_x=(render_size-text_width)/2; text_y=(render_size-text_height)/2
        draw.text((text_x, text_y), text, font=font, fill=TEXT_COLOR_PRIMARY)

        # --- Downscale with high quality ---
        image = image.resize((final_size, final_size), Image.Resampling.LANCZOS)

        # Convert to Tkinter PhotoImage
        photo_image = ImageTk.PhotoImage(image)
        return photo_image

    except Exception as e: print(f"Error generating icon '{text}': {e}"); return None

# --- Custom Widgets ---

class RoundedButton(tk.Canvas):
    # Uses unscaled width/height/radius passed during creation
    def __init__(self, parent, width, height, corner_radius, padding=2, # Default padding unscaled
                 color=BUTTON_GRAY_COLOR, hover_color=BUTTON_GRAY_HOVER_COLOR, click_color=BUTTON_GRAY_CLICK_COLOR,
                 text="", text_color=TEXT_COLOR_PRIMARY, font=None, command=None, image=None, **kwargs):
        parent_bg = kwargs.pop('bg', parent.cget("bg"))
        if image: parent_bg = BG_COLOR_TRANSPARENT
        tk.Canvas.__init__(self, parent, width=width, height=height, bd=0, highlightthickness=0, bg=parent_bg, **kwargs)
        self.command = command; self.base_color = color; self.hover_color = hover_color; self.click_color = click_color
        self.text_color = text_color; self.font = font if font is not None else FONT_BUTTON; self.radius = corner_radius
        self.padding = padding; self._width = width; self._height = height; self.text = text; self.image = image
        self.rect_id = None; self.text_id = None; self.image_id = None
        self.bind("<Configure>", lambda e: self._redraw(e)); self._draw()
        if not self.image: self.bind("<Enter>", self.on_enter); self.bind("<Leave>", self.on_leave)
    def set_pressed_state(self, pressed):
        if not self.image and self.rect_id: self.itemconfig(self.rect_id, fill=(self.click_color if pressed else self.base_color))
    def set_hover_state(self, hovering):
         if not self.image and self.rect_id: self.itemconfig(self.rect_id, fill=(self.hover_color if hovering else self.base_color))
    def _draw(self): # Drawing adapts to current size, uses unscaled padding/radius
        self.delete("all"); w=self._width; h=self._height;
        if w <= 0 or h <= 0: return
        if self.image: self.image_id = self.create_image(w/2, h/2, image=self.image, anchor=tk.CENTER)
        else:
            pad=self.padding; radius=min(self.radius,(w-2*pad)/2,(h-2*pad)/2); radius=max(0,radius); x1,y1,x2,y2=pad,pad,w-pad,h-pad
            points=[x1+radius,y1, x2-radius,y1, x2,y1, x2,y1+radius, x2,y2-radius, x2,y2, x2-radius,y2, x1+radius,y2, x1,y2, x1,y2-radius, x1,y1+radius, x1,y1, x1+radius,y1]
            if points: self.rect_id=self.create_polygon(points,fill=self.base_color,smooth=True); self.text_id=self.create_text(w/2,h/2,text=self.text,fill=self.text_color,font=self.font)
    def _redraw(self, event=None):
        self._width=self.winfo_width(); self._height=self.winfo_height(); current_fill=self.base_color
        if not self.image and self.rect_id: current_fill=self.itemcget(self.rect_id,"fill")
        self._draw();
        if not self.image and self.rect_id: self.itemconfig(self.rect_id,fill=current_fill)
    def on_enter(self, event):
        if self.rect_id: self.itemconfig(self.rect_id, fill=self.hover_color)
    def on_leave(self, event):
         if self.rect_id: self.itemconfig(self.rect_id, fill=self.base_color)

class CommandIcon(tk.Canvas):
    # Uses unscaled width/height for canvas, unscaled constants for indicator
    def __init__(self, parent, width, height, command_name, command_color, command_action, **kwargs):
        self.parent_bg = parent.cget("bg")
        tk.Canvas.__init__(self, parent, width=width, height=height, bd=0, highlightthickness=0, bg=self.parent_bg, **kwargs)
        self.command_name = command_name; self.command_action = command_action
        self._width = width; self._height = height; self.is_on = False
        self.indicator_dot_id = None; self.icon_image_id = None
        self.display_text = command_name[:3].upper()
        # Generate image using PILLOW_TARGET_ICON_SIZE (unscaled)
        self.icon_photoimage = create_command_icon_image(PILLOW_TARGET_ICON_SIZE, self.display_text, command_color)
        self._draw_elements(); self._update_indicator()
        self.bind("<Enter>", self.on_enter); self.bind("<Leave>", self.on_leave); self.bind("<Configure>", lambda e: self._redraw(e))
    def _draw_elements(self): # Draws indicator using unscaled constants
        self.delete("all"); w=self._width; h=self._height;
        if w <= 0 or h <= 0: return
        center_x, center_y = w/2, h/2
        if self.icon_photoimage: self.icon_image_id = self.create_image(center_x, center_y, image=self.icon_photoimage, anchor=tk.CENTER)
        else: # Fallback uses unscaled ICON_SIZE
             icon_radius=(ICON_SIZE*0.75)/2; self.create_oval(center_x-icon_radius, center_y-icon_radius, center_x+icon_radius, center_y+icon_radius, fill="#888", outline=""); self.create_text(center_x, center_y, text="?", fill="white")
        # Indicator uses unscaled constants for position/size
        indicator_x = w - INDICATOR_RADIUS - (ICON_CANVAS_WIDTH_PADDING // 2) - 2
        self.indicator_dot_id = self.create_oval(indicator_x-INDICATOR_RADIUS, center_y-INDICATOR_RADIUS, indicator_x+INDICATOR_RADIUS, center_y+INDICATOR_RADIUS, fill=INDICATOR_COLOR, outline="")
        self._update_indicator()
    def _redraw(self, event=None): self._width=self.winfo_width(); self._height=self.winfo_height(); self._draw_elements()
    def set_state(self, is_on):
        if self.is_on != is_on: self.is_on = is_on; self._update_indicator()
    def _update_indicator(self):
        if self.indicator_dot_id: self.itemconfig(self.indicator_dot_id, state=tk.NORMAL if self.is_on else tk.HIDDEN)
    def on_enter(self, event): self.config(bg=ICON_HOVER_BG_COLOR)
    def on_leave(self, event): self.config(bg=self.parent_bg)

class CommandSettingsWindow:
    def __init__(self, parent, command_bar, on_close_callback, command_file_path="commands.json"):
        self.parent = parent
        self.command_bar = command_bar
        self.command_file_path = command_file_path
        self.on_close_callback = on_close_callback
        self.commands = self.load_commands()
        self.current_command_index = None
        self.tools = self.get_available_tools()
        
        self.window = tk.Toplevel(parent)
        self.window.title("Command Settings")
        self.window.configure(bg=BAR_BG_COLOR)
        self.window.attributes('-topmost', True)
        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
        
        # Scale window size relative to screen
        width = 750
        height = 500
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(self.window, bg=BAR_BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Command list
        list_frame = tk.Frame(main_frame, bg=BAR_BG_COLOR)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=True)
        
        list_label = tk.Label(list_frame, text="Commands", bg=BAR_BG_COLOR, fg=TEXT_COLOR_PRIMARY, font=get_tk_font(12, "bold"))
        list_label.pack(side=tk.TOP, anchor="w", pady=(0, 5))
        
        list_container = tk.Frame(list_frame, bg=BUTTON_GRAY_COLOR)
        list_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.command_listbox = tk.Listbox(list_container, 
                                         bg=BUTTON_GRAY_COLOR, 
                                         fg=TEXT_COLOR_PRIMARY,
                                         selectbackground=ICON_HOVER_BG_COLOR,
                                         selectforeground=TEXT_COLOR_PRIMARY,
                                         font=get_tk_font(10),
                                         bd=0,
                                         highlightthickness=0)
        self.command_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.command_listbox.bind('<<ListboxSelect>>', self.on_command_select)
        
        list_scrollbar = tk.Scrollbar(list_container)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.command_listbox.config(yscrollcommand=list_scrollbar.set)
        list_scrollbar.config(command=self.command_listbox.yview)
        
        # Button controls for list
        button_frame = tk.Frame(list_frame, bg=BAR_BG_COLOR)
        button_frame.pack(side=tk.TOP, fill=tk.X, pady=(10, 0))
        
        self.add_btn = RoundedButton(button_frame, 80, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                                  text="Add", 
                                  command=None,  # Set to None and use bind
                                  bg=BAR_BG_COLOR)
        self.add_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.add_btn.bind("<Button-1>", self.add_command)
        
        self.remove_btn = RoundedButton(button_frame, 80, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                                     text="Remove", 
                                     command=None,  # Set to None and use bind
                                     bg=BAR_BG_COLOR)
        self.remove_btn.pack(side=tk.LEFT, padx=5)
        self.remove_btn.bind("<Button-1>", self.remove_command)
        
        # Direct save button for the list
        self.save_list_btn = RoundedButton(button_frame, 80, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                                  text="Save", 
                                  command=None,  # Set to None and use bind
                                  color="#34C759",  # Green color for save
                                  hover_color="#4CD964",
                                  click_color="#32AE56",
                                  bg=BAR_BG_COLOR)
        self.save_list_btn.pack(side=tk.RIGHT, padx=5)
        self.save_list_btn.bind("<Button-1>", self.save_to_json)
        
        # Command edit panel
        edit_frame = tk.Frame(main_frame, bg=BAR_BG_COLOR)
        edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0), expand=True)
        
        edit_label = tk.Label(edit_frame, text="Edit Command", bg=BAR_BG_COLOR, fg=TEXT_COLOR_PRIMARY, font=get_tk_font(12, "bold"))
        edit_label.pack(side=tk.TOP, anchor="w", pady=(0, 10))
        
        # Tool type
        tool_frame = tk.Frame(edit_frame, bg=BAR_BG_COLOR)
        tool_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        tool_label = tk.Label(tool_frame, text="Tool:", bg=BAR_BG_COLOR, fg=TEXT_COLOR_PRIMARY, anchor="w", width=10)
        tool_label.pack(side=tk.LEFT)
        
        self.tool_var = tk.StringVar()
        self.tool_dropdown = ttk.Combobox(tool_frame, textvariable=self.tool_var, values=self.tools, state="readonly", width=20)
        self.tool_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tool_dropdown.bind("<<ComboboxSelected>>", self.on_tool_change)
        
        # Command name
        name_frame = tk.Frame(edit_frame, bg=BAR_BG_COLOR)
        name_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        name_label = tk.Label(name_frame, text="Name:", bg=BAR_BG_COLOR, fg=TEXT_COLOR_PRIMARY, anchor="w", width=10)
        name_label.pack(side=tk.LEFT)
        
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(name_frame, textvariable=self.name_var, bg=BUTTON_GRAY_COLOR, fg=TEXT_COLOR_PRIMARY, bd=0, highlightthickness=1, highlightbackground=SEPARATOR_COLOR, insertbackground=TEXT_COLOR_PRIMARY)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Color
        color_frame = tk.Frame(edit_frame, bg=BAR_BG_COLOR)
        color_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        color_label = tk.Label(color_frame, text="Color:", bg=BAR_BG_COLOR, fg=TEXT_COLOR_PRIMARY, anchor="w", width=10)
        color_label.pack(side=tk.LEFT)
        
        self.color_var = tk.StringVar()
        color_entry = tk.Entry(color_frame, textvariable=self.color_var, bg=BUTTON_GRAY_COLOR, fg=TEXT_COLOR_PRIMARY, bd=0, highlightthickness=1, highlightbackground=SEPARATOR_COLOR, insertbackground=TEXT_COLOR_PRIMARY, width=10)
        color_entry.pack(side=tk.LEFT)
        
        color_preview = tk.Frame(color_frame, width=20, height=20, bg="#FFFFFF")
        color_preview.pack(side=tk.LEFT, padx=5)
        self.color_preview = color_preview
        
        color_picker_btn = RoundedButton(color_frame, 80, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                                      text="Pick", 
                                      command=None,  # Set to None and use bind
                                      bg=BAR_BG_COLOR)
        color_picker_btn.pack(side=tk.LEFT, padx=5)
        color_picker_btn.bind("<Button-1>", self.pick_color)
        
        # Args label and info
        args_label_frame = tk.Frame(edit_frame, bg=BAR_BG_COLOR)
        args_label_frame.pack(side=tk.TOP, fill=tk.X)
        
        args_label = tk.Label(args_label_frame, text="Arguments:", bg=BAR_BG_COLOR, fg=TEXT_COLOR_PRIMARY, anchor="w")
        args_label.pack(side=tk.LEFT)
        
        args_info = tk.Label(args_label_frame, text="(Write here the command and paths for the tool)", bg=BAR_BG_COLOR, fg=SEPARATOR_COLOR, anchor="w")
        args_info.pack(side=tk.LEFT, padx=5)
        
        # Args text area with scrollbar
        args_frame = tk.Frame(edit_frame, bg=BUTTON_GRAY_COLOR)
        args_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.args_text = tk.Text(args_frame, bg=BUTTON_GRAY_COLOR, fg=TEXT_COLOR_PRIMARY, bd=0, highlightthickness=0, insertbackground=TEXT_COLOR_PRIMARY)
        self.args_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        args_scrollbar = tk.Scrollbar(args_frame)
        args_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.args_text.config(yscrollcommand=args_scrollbar.set)
        args_scrollbar.config(command=self.args_text.yview)
        
        # Save and cancel buttons
        buttons_frame = tk.Frame(edit_frame, bg=BAR_BG_COLOR)
        buttons_frame.pack(side=tk.TOP, fill=tk.X, pady=(10, 0))
        
        save_btn = RoundedButton(buttons_frame, 80, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                              text="Save", 
                              command=None,  # Set to None and use bind
                              color="#34C759",  # Green color for save
                              hover_color="#4CD964",
                              click_color="#32AE56",
                              bg=BAR_BG_COLOR)
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))
        save_btn.bind("<Button-1>", self.save_command)
        
        cancel_btn = RoundedButton(buttons_frame, 80, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                                text="Cancel", 
                                command=None,  # Set to None and use bind 
                                bg=BAR_BG_COLOR)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        cancel_btn.bind("<Button-1>", self.cancel_edit)
        
        # Save all changes button at the bottom
        bottom_frame = tk.Frame(main_frame, bg=BAR_BG_COLOR)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        save_all_btn = RoundedButton(bottom_frame, 150, BUTTON_HEIGHT, BUTTON_HEIGHT/2, 
                                  text="Save All Changes", 
                                  command=None,  # Set to None and use bind
                                  color="#34C759",  # Green color for save
                                  hover_color="#4CD964",
                                  click_color="#32AE56",
                                  bg=BAR_BG_COLOR)
        save_all_btn.pack(side=tk.RIGHT)
        save_all_btn.bind("<Button-1>", self.save_all_changes)
        
        # Populate the list
        self.populate_command_list()
        self.disable_edit_panel()
        
        # Configure style
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TCombobox', 
                     fieldbackground=BUTTON_GRAY_COLOR,
                     background=BUTTON_GRAY_COLOR,
                     foreground=TEXT_COLOR_PRIMARY,
                     arrowcolor=TEXT_COLOR_PRIMARY,
                     borderwidth=0)
        style.map('TCombobox',
               fieldbackground=[('readonly', BUTTON_GRAY_COLOR)],
               selectbackground=[('readonly', BUTTON_GRAY_COLOR)],
               selectforeground=[('readonly', TEXT_COLOR_PRIMARY)])
        
    def get_available_tools(self):
        # Get the list of available tools from the package
        # For simplicity, return the basic tools but this could be extended
        return ["copy-files", "image-clipboard", "custom"]
    
    def load_commands(self):
        try:
            with open(self.command_file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading command configuration: {e}")
            return []
    
    def save_commands_to_file(self):
        try:
            with open(self.command_file_path, "w") as f:
                json.dump(self.commands, f, indent=4)
            print(f"Commands saved to {self.command_file_path}")
            return True
        except Exception as e:
            print(f"Error saving command configuration: {e}")
            return False
    
    def populate_command_list(self):
        self.command_listbox.delete(0, tk.END)
        for cmd in self.commands:
            self.command_listbox.insert(tk.END, cmd["name"])
    
    def on_command_select(self, event):
        selection = self.command_listbox.curselection()
        if selection:
            index = selection[0]
            # If the selected command is not the current command, load it for editing
            if index != self.current_command_index:
                self.current_command_index = index
                self.load_command_for_edit(self.commands[index])
                self.enable_edit_panel()
        #else:
        #    self.disable_edit_panel()
    
    def load_command_for_edit(self, command):
        # Parse command to identify tool and args
        cmd_str = command["command"]
        tool = "custom"  # Default
        args = []
        
        # Try to identify the tool from the command
        for t in self.tools:
            if t in cmd_str and t != "custom":
                tool = t
                break
        
        # Extract arguments based on tool
        if tool != "custom":
            # Extract from the command format: "cmd.exe /k python -m university_student_tools.clipboard.image_clipboard \"Path\""
            parts = cmd_str.split(tool)
            if len(parts) > 1:
                # Get everything after the tool name
                args_part = parts[1].strip()
                # Split by spaces, preserving quoted parts
                try:
                    args = list(shlex.split(args_part))
                except:
                    # Fallback if parsing fails
                    args = [args_part]
        else:
            # For custom commands, just put the whole command as an arg
            args = [cmd_str]
        
        # Set values in the form
        self.tool_var.set(tool)
        self.name_var.set(command["name"])
        self.color_var.set(command["color"])
        self.color_preview.config(bg=command["color"])
        
        # Clear and populate args text
        self.args_text.delete("1.0", tk.END)
        if args:
            self.args_text.insert("1.0", "\n".join(args))
    
    def build_command_from_form(self):
        tool = self.tool_var.get()
        name = self.name_var.get().strip()
        color = self.color_var.get().strip()
        
        # Get arguments from text area
        args_text = self.args_text.get("1.0", tk.END).strip()
        args = [arg for arg in args_text.split("\n") if arg.strip()]
        
        # Build command string based on tool
        command = "" # Initialize command string
        if tool == "custom" and args:
            # For custom, use the first arg as the full command
            command = args[0]
        elif tool in ["copy-files", "image-clipboard"]:
            # For built-in tools, build the python -m command format
            command = f"python -m university_student_tools." # Start with python -m
            if tool == "copy-files":
                command += f"file_manager.copy_files"
            elif tool == "image-clipboard":
                command += f"clipboard.image_clipboard"

            # Add arguments directly, separated by space. Expect paths with spaces to be quoted in the input.
            for arg in args:
                 command += f" {arg}"
        else:
             # Handle potential other tools or cases where args might be empty for built-ins
             print(f"Warning: Unhandled tool type '{tool}' or missing arguments. Command will be empty.")


        return {
            "name": name,
            "command": command, # Use the newly constructed command
            "color": color
        }
    
    def validate_form(self):
        name = self.name_var.get().strip()
        color = self.color_var.get().strip()
        
        if not name:
            return False, "Command name cannot be empty"
        
        # Validate color format
        if not color.startswith("#") or len(color) != 7:
            return False, "Invalid color format. Use #RRGGBB"
        
        try:
            int(color[1:], 16)
        except ValueError:
            return False, "Invalid color format. Use #RRGGBB"
        
        return True, ""
    
    def enable_edit_panel(self):
        self.tool_dropdown.config(state="readonly")
        # Enable all other form fields
    
    def disable_edit_panel(self):
        self.tool_dropdown.config(state="disabled")
        self.name_var.set("")
        self.color_var.set("")
        self.color_preview.config(bg="#FFFFFF")
        self.args_text.delete("1.0", tk.END)
        self.current_command_index = None
        # Disable all other form fields
    
    def add_command(self, event=None):
        # Create a blank command and select it for editing
        new_command = {
            "name": "New Command",
            "command": "",
            "color": "#0066FF"
        }
        self.commands.append(new_command)
        self.populate_command_list()
        
        # Select the new command in the listbox
        new_index = len(self.commands) - 1
        self.command_listbox.selection_clear(0, tk.END)
        self.command_listbox.selection_set(new_index)
        self.command_listbox.see(new_index)
        
        # Load the new command for editing
        self.current_command_index = new_index
        self.load_command_for_edit(new_command)
        self.enable_edit_panel()
        
        print(f"Added new command at index {new_index}")
        return "break"
    
    def remove_command(self, event=None):
        if self.current_command_index is not None:
            command_name = self.commands[self.current_command_index]["name"]
            del self.commands[self.current_command_index]
            self.populate_command_list()
            self.disable_edit_panel()
            print(f"Removed command: {command_name}")
        else:
            print("No command selected to remove")
        return "break"
    
    def save_command(self, event=None):
        if self.current_command_index is None:
            print("No command selected to save")
            return "break"
        
        valid, message = self.validate_form()
        if not valid:
            # Show error message
            print(message)
            return "break"
        
        # Update the command in memory
        command = self.build_command_from_form()
        self.commands[self.current_command_index] = command
        self.populate_command_list()
        
        # Reselect the current command
        self.command_listbox.selection_clear(0, tk.END)
        self.command_listbox.selection_set(self.current_command_index)
        
        # Save immediately to the JSON file
        if self.save_commands_to_file():
            print(f"Command '{command['name']}' saved to {self.command_file_path}")
            # Update the command bar without closing the window
            self.command_bar.reload_commands()
        else:
            print(f"Failed to save command '{command['name']}' to file")
        
        return "break"
    
    def cancel_edit(self, event=None):
        # Reload the current command or clear if none selected
        if self.current_command_index is not None:
            self.load_command_for_edit(self.commands[self.current_command_index])
            print("Cancelled edits")
        else:
            self.disable_edit_panel()
        return "break"
    
    def pick_color(self, event=None):
        # Use a default color if current color is empty or invalid
        initialcolor = "#0066FF"  # Default blue
        current_color = self.color_var.get().strip()
        
        if current_color and current_color.startswith("#") and len(current_color) == 7:
            try:
                int(current_color[1:], 16)
                initialcolor = current_color
            except ValueError:
                pass
                
        color = colorchooser.askcolor(initialcolor=initialcolor)
        if color[1]:  # color is ((r, g, b), hex_color)
            self.color_var.set(color[1])
            self.color_preview.config(bg=color[1])
            print(f"Selected color: {color[1]}")
        return "break"
    
    def on_tool_change(self, event=None):
        selected_tool = self.tool_var.get()
        print(f"Selected tool: {selected_tool}") # Keep for logging

        # Clear existing arguments
        self.args_text.delete("1.0", tk.END)

        # Populate with default arguments based on the selected tool
        default_args = ""
        if selected_tool == "copy-files":
            default_args = '"Source Path"\\n"Destination Path"' # Use double quotes for paths, separated by newline
        elif selected_tool == "image-clipboard":
            default_args = '"Image Directory Path"' # Use double quotes for path
        elif selected_tool == "custom":
            default_args = "# Enter the full custom command here\\n" # Provide a helpful comment for custom commands

        if default_args:
            self.args_text.insert("1.0", default_args)
    
    def save_all_changes(self, event=None):
        # Save current command if editing
        if self.current_command_index is not None:
            valid, message = self.validate_form()
            if valid:
                self.save_command()
            else:
                print(f"Cannot save all changes: {message}")
                return "break"
        
        # Save all commands to file
        if self.save_commands_to_file():
            # Reload the command bar
            self.command_bar.reload_commands()
            # Close the window using the new method
            self.on_window_close()
            print("All changes saved and applied")
        else:
            print("Failed to save changes")
        return "break"

    def save_to_json(self, event=None):
        """Save changes to the JSON file without closing the window."""
        # Save current command if editing
        if self.current_command_index is not None:
            valid, message = self.validate_form()
            if valid:
                command = self.build_command_from_form()
                self.commands[self.current_command_index] = command
                self.populate_command_list()
                # Reselect the command
                self.command_listbox.selection_clear(0, tk.END)
                self.command_listbox.selection_set(self.current_command_index)
            else:
                print(f"Cannot save: {message}")
                return "break"
        
        # Save to file
        if self.save_commands_to_file():
            # Update the command bar without closing the window
            self.command_bar.reload_commands()
            print(f"All changes saved to {self.command_file_path}")
        else:
            print("Failed to save changes to file")
        
        return "break"

    def on_window_close(self):
        """Handles the window close event."""
        if self.on_close_callback:
            self.on_close_callback()
        self.window.destroy()

class CommandBarUIManager:
    """Manages the creation, layout, and reloading of UI elements within the command bar."""
    def __init__(self, command_bar, content_frame, separator, settings_button, hide_button, initial_commands):
        self.command_bar = command_bar # Reference to the main VerticalCommandBar instance
        self.content_frame = content_frame
        self.separator = separator
        self.settings_button = settings_button
        self.hide_button = hide_button

        self.icon_widgets = {} # Dictionary to store CommandIcon widgets {name: widget}
        self._icon_photo_refs = [] # Keep references to PhotoImage objects

        self.build_ui(initial_commands)

    def _clear_widgets(self):
        """Removes existing command icons, separator, and buttons from the layout."""
        # Clear existing icon widgets
        for widget in self.icon_widgets.values():
            widget.pack_forget() # Remove from layout
            widget.destroy() # Destroy the widget
        self.icon_widgets = {}
        self._icon_photo_refs = []

        # Remove separator and buttons from layout
        self.separator.pack_forget()
        self.settings_button.pack_forget()
        self.hide_button.pack_forget()

    def _create_icon(self, cmd_data):
        """Creates and binds a single CommandIcon widget."""
        icon_canvas_width = self.command_bar.bar_width - (2 * BAR_PADDING_HORIZONTAL)
        icon = CommandIcon(self.content_frame, icon_canvas_width, ICON_CANVAS_HEIGHT,
                         command_name=cmd_data["name"], command_color=cmd_data["color"],
                         command_action=self.command_bar.toggle_command) # Action calls method on command_bar
        if icon.icon_photoimage:
            self._icon_photo_refs.append(icon.icon_photoimage)

        # Bind drag/click events - handlers are methods on command_bar
        cmd_func = lambda name=cmd_data["name"]: self.command_bar.toggle_command(name)
        icon.bind("<Button-1>", lambda event, cmd=cmd_func: self.command_bar.start_widget_move_or_click(event, cmd))
        icon.bind("<ButtonRelease-1>", self.command_bar.stop_widget_move_or_click)
        icon.bind("<B1-Motion>", self.command_bar.do_widget_move)

        self.icon_widgets[cmd_data["name"]] = icon
        return icon

    def build_ui(self, commands):
        """Creates and lays out all UI elements based on the provided commands."""
        # Create icons
        for cmd_data in commands:
            icon = self._create_icon(cmd_data)
            icon.pack(side=tk.TOP, pady=(ICON_PADDING_VERTICAL // 2, ICON_PADDING_VERTICAL // 2), padx=0)

        # Re-pack the separator and buttons at the bottom
        self.separator.pack(side=tk.TOP, fill=tk.X, padx=BAR_PADDING_HORIZONTAL, pady=ICON_PADDING_VERTICAL)
        self.settings_button.pack(side=tk.TOP, pady=(0, ICON_PADDING_VERTICAL // 2))
        self.hide_button.pack(side=tk.TOP, pady=(0, ICON_PADDING_VERTICAL // 2))

    def reload_ui(self, new_commands):
        """Clears the existing UI and builds it again with new commands."""
        self._clear_widgets()
        self.build_ui(new_commands)

class VerticalCommandBar:
    # Uses unscaled constants for layout and widget sizes
    def __init__(self, root):
        self.root = root; self.root.title("Command Bar"); self.root.config(bg=BG_COLOR_TRANSPARENT)
        self.root.attributes('-topmost', True);
        try: self.root.overrideredirect(True)
        except tk.TclError: print("Warning: overrideredirect failed.")
        self.use_alpha_transparency=False
        try: self.root.attributes("-transparentcolor",BG_COLOR_TRANSPARENT); self.root.attributes('-alpha',0.99)
        except tk.TclError: self.root.attributes('-alpha',BAR_BG_ALPHA); self.use_alpha_transparency=True; print("Warning: transparentcolor failed.")
        self.is_hidden=False; self.original_x=None; self.original_y=None; self.original_width=None; self.original_height=None
        self.dragging=False; self.drag_start_x=None; self.drag_start_y=None
        self.widget_drag_active=False; self.widget_press_x_root=0; self.widget_press_y_root=0; self.widget_press_time=0; self.widget_command_on_click=None
        # Load commands from the JSON configuration file.
        self.command_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "commands.json")
        self.commands = load_commands(self.command_file_path)
        self.settings_window = None # Add variable to track settings window
        self.processes={} # Track running processes {name: pid}

        # Calculations use unscaled constants
        # Initial calculation based on loaded commands
        num_icons=len(self.commands); icons_height=(num_icons*ICON_CANVAS_HEIGHT)+((num_icons-1)*ICON_PADDING_VERTICAL)
        extra_space=SEPARATOR_HEIGHT+BUTTON_HEIGHT*2+ICON_PADDING_VERTICAL*3; self.bar_width=ICON_SIZE+(2*ICON_CANVAS_WIDTH_PADDING)+(2*BAR_PADDING_HORIZONTAL)
        self.bar_height=icons_height+extra_space+(2*BAR_PADDING_VERTICAL); screen_width=root.winfo_screenwidth(); screen_height=root.winfo_screenheight()
        x=screen_width-self.bar_width-10; y=(screen_height-self.bar_height)//2; self.root.geometry(f"{self.bar_width}x{self.bar_height}+{x}+{y}")
        self.original_width=self.bar_width; self.original_height=self.bar_height

        self.main_frame=tk.Frame(root,bg=BG_COLOR_TRANSPARENT); self.main_frame.pack(fill=tk.BOTH,expand=True)
        self.bar_canvas=tk.Canvas(self.main_frame,width=self.bar_width,height=self.bar_height,bd=0,highlightthickness=0,bg=BG_COLOR_TRANSPARENT if not self.use_alpha_transparency else BAR_BG_COLOR)
        self.bar_canvas.place(x=0,y=0,relwidth=1,relheight=1);
        if not self.use_alpha_transparency: self._draw_bar_background()

        # --- Content Frame and Shared Widgets ---
        content_bg=BAR_BG_COLOR if not self.use_alpha_transparency else self.bar_canvas.cget('bg');
        self.content_frame=tk.Frame(self.bar_canvas,bg=content_bg)

        # Separator and bottom buttons are created here but managed by UIManager
        self.separator=tk.Canvas(self.content_frame,height=SEPARATOR_HEIGHT,bg=SEPARATOR_COLOR,highlightthickness=0)
        self.settings_button=RoundedButton(self.content_frame,self.bar_width-(2*(BAR_PADDING_HORIZONTAL+5)),BUTTON_HEIGHT,BUTTON_HEIGHT/2,
                                         text="Settings",command=self.open_settings,font=FONT_BUTTON,bg=content_bg)
        self.hide_button=RoundedButton(self.content_frame,self.bar_width-(2*(BAR_PADDING_HORIZONTAL+5)),BUTTON_HEIGHT,BUTTON_HEIGHT/2,
                                         text="Hide",command=self.hide_bar,font=FONT_BUTTON,bg=content_bg)

        # Bind events for Settings and Hide buttons
        self.settings_button.bind("<Button-1>",lambda event,cmd=self.settings_button.command: self.start_widget_move_or_click(event,cmd))
        self.settings_button.bind("<ButtonRelease-1>",self.stop_widget_move_or_click)
        self.settings_button.bind("<B1-Motion>",self.do_widget_move)
        self.hide_button.bind("<Button-1>",lambda event,cmd=self.hide_button.command: self.start_widget_move_or_click(event,cmd))
        self.hide_button.bind("<ButtonRelease-1>",self.stop_widget_move_or_click)
        self.hide_button.bind("<B1-Motion>",self.do_widget_move)

        # --- UI Manager ---
        # Create the UI Manager instance, passing necessary components and initial commands
        self.ui_manager = CommandBarUIManager(
            self,
            self.content_frame,
            self.separator,
            self.settings_button,
            self.hide_button,
            self.commands
        )
        # ui_manager.build_ui() is called in its __init__

        # Place the content frame
        self.content_frame.place(x=BAR_PADDING_HORIZONTAL,y=BAR_PADDING_VERTICAL,width=self.bar_width-(2*BAR_PADDING_HORIZONTAL),height=self.bar_height-(2*BAR_PADDING_VERTICAL))

        # --- Close Button ---
        # Close button uses unscaled size/font/offset
        self.close_button=RoundedButton(self.bar_canvas,CLOSE_BUTTON_SIZE,CLOSE_BUTTON_SIZE,CLOSE_BUTTON_SIZE/2,padding=1,
                                          color=CLOSE_BUTTON_COLOR,hover_color=adjust_color(CLOSE_BUTTON_COLOR,1.15),click_color=adjust_color(CLOSE_BUTTON_COLOR,0.85),
                                          text="✕",text_color="white",command=self.on_close,font=FONT_CLOSE_BUTTON,
                                          bg=BAR_BG_COLOR if not self.use_alpha_transparency else self.bar_canvas.cget('bg'))
        self.close_button.place(x=self.bar_width-CLOSE_BUTTON_SIZE-5,y=5)
        self.close_button.bind("<Button-1>",lambda event,cmd=self.close_button.command: self.start_widget_move_or_click(event,cmd))
        self.close_button.bind("<ButtonRelease-1>",self.stop_widget_move_or_click)
        self.close_button.bind("<B1-Motion>",self.do_widget_move)

        # --- Show Button Setup (Renders High-Res, Downscales to unscaled SHOW_BUTTON_SIZE) ---
        self.show_button_frame = tk.Frame(root, bg=BG_COLOR_TRANSPARENT)
        self.show_button_image_ref = None
        show_button_widget = None
        if PIL_AVAILABLE:
            try:
                image_bytes = base64.b64decode(SHOW_BUTTON_BASE64)
                img = Image.open(io.BytesIO(image_bytes))
                # Render/load at higher res
                render_size = SHOW_BUTTON_SIZE * RENDER_SCALE
                img = img.resize((render_size, render_size), Image.Resampling.LANCZOS) # Ensure high-res source
                # Downscale to target size
                img = img.resize((SHOW_BUTTON_SIZE, SHOW_BUTTON_SIZE), Image.Resampling.LANCZOS)
                self.show_button_image_ref = ImageTk.PhotoImage(img)
                show_button_widget = RoundedButton(self.show_button_frame, SHOW_BUTTON_SIZE, SHOW_BUTTON_SIZE, corner_radius=8, # unscaled radius
                                                image=self.show_button_image_ref, command=self.show_bar, bg=BG_COLOR_TRANSPARENT)
            except Exception as e: print(f"Error loading Base64 image: {e}. Falling back.")
        if not show_button_widget: # Fallback uses unscaled size/font
             show_button_widget = RoundedButton(self.show_button_frame, SHOW_BUTTON_SIZE, SHOW_BUTTON_SIZE, SHOW_BUTTON_SIZE / 2.5,
                                            color=BUTTON_GRAY_COLOR, hover_color=BUTTON_GRAY_HOVER_COLOR, click_color=BUTTON_GRAY_CLICK_COLOR,
                                            text="☰", text_color=TEXT_COLOR_PRIMARY, font=FONT_SHOW_BUTTON, command=self.show_bar, bg=BAR_BG_COLOR)
        self.show_button = show_button_widget
        self.show_button.pack(fill=tk.BOTH, expand=True)
        # Bindings set in hide_bar
        # --- End Show Button Setup ---

        # Bind background drag events
        self.bar_canvas.bind("<Button-1>", self.start_move); self.bar_canvas.bind("<ButtonRelease-1>", self.stop_move); self.bar_canvas.bind("<B1-Motion>", self.do_move); self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_settings(self):
        # Check if window exists and is visible
        if self.settings_window and self.settings_window.window.winfo_exists():
            self.settings_window.window.lift() # Bring to front
            self.settings_window.window.focus_force() # Force focus
            print("Settings window already open, bringing to front.")
            return

        # Open the settings window
        print("Opening new settings window.")
        self.settings_window = CommandSettingsWindow(
            self.root,
            self,
            on_close_callback=self.on_settings_close, # Pass callback
            command_file_path=self.command_file_path
        )

    def on_settings_close(self):
        """Callback function when the settings window is closed."""
        print("Settings window closed.")
        self.settings_window = None # Reset the tracker variable

    def reload_commands(self):
        # Reload commands from the JSON file and refresh the UI

        #Turn off any running processes associated with the *current* command list
        #    before reloading the list itself.
        active_processes_before_reload = list(self.processes.keys())
        for name in active_processes_before_reload:
            # Ensure the command still exists in the current list before trying to toggle
            if name in self.ui_manager.icon_widgets: # Check against UI manager's knowledge
                 self.toggle_command(name) # Use toggle to attempt graceful shutdown

        # 2. Reload commands data from file
        try:
            self.commands = load_commands(self.command_file_path)
            print(f"Successfully reloaded {len(self.commands)} commands from {self.command_file_path}")
        except Exception as e:
            print(f"Error loading commands from {self.command_file_path}: {e}")
            self.commands = [] # Proceed with an empty list in case of error

        # 3. Tell the UI manager to rebuild the UI with the new command list
        self.ui_manager.reload_ui(self.commands)
        # The ui_manager now handles clearing old widgets and creating/packing new ones.

        # 4. Update the main bar's size based on the new content
        self.update_bar_size()
        print("Command bar UI refreshed.")

    def update_bar_size(self):
        # Recalculate bar size based on current number of commands
        num_icons = len(self.commands) # Use the reloaded command count
        icons_height = (num_icons * ICON_CANVAS_HEIGHT) + (max(0, num_icons - 1) * ICON_PADDING_VERTICAL) # Ensure non-negative padding
        extra_space = SEPARATOR_HEIGHT + BUTTON_HEIGHT * 2 + ICON_PADDING_VERTICAL * 3  # For settings and hide buttons
        self.bar_height = icons_height + extra_space + (2 * BAR_PADDING_VERTICAL)

        # Update geometry if the bar is not hidden
        if not self.is_hidden:
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            self.root.geometry(f"{self.bar_width}x{self.bar_height}+{x}+{y}")

            # Redraw background if needed
            self.bar_canvas.config(height=self.bar_height) # Update canvas size
            if not self.use_alpha_transparency:
                self._draw_bar_background() # Redraw rounded background for new size

            # Update content frame position and size
            self.content_frame.place(x=BAR_PADDING_HORIZONTAL, y=BAR_PADDING_VERTICAL,
                                  width=self.bar_width-(2*BAR_PADDING_HORIZONTAL),
                                  height=self.bar_height-(2*BAR_PADDING_VERTICAL))

        # Update original height for restoring after hide
        self.original_height = self.bar_height


    # --- Generic Widget Drag/Click Handlers (Unchanged) ---
    # These remain here as they handle general window dragging initiated from widgets
    def start_widget_move_or_click(self, event, command_to_run):
        # Check if the widget is a CommandIcon via the UIManager or other buttons
        widget = event.widget
        # Find the parent CommandIcon if a child element was clicked
        while widget and not isinstance(widget, (CommandIcon, RoundedButton)):
            widget = widget.master
            if widget == self.root: # Stop if we reach the root window
                 widget = None
                 break

        if isinstance(widget, RoundedButton) and not widget.image: widget.set_pressed_state(True)
        elif isinstance(widget, CommandIcon): pass # No visual press state for CommandIcon itself

        self.widget_press_x_root=event.x_root; self.widget_press_y_root=event.y_root; self.widget_press_time=event.time; self.widget_command_on_click=command_to_run; self.widget_drag_active=False; self.drag_start_x=None; self.drag_start_y=None

    def stop_widget_move_or_click(self, event):
        widget=event.widget
        # Find the parent CommandIcon or RoundedButton if a child element was clicked/released
        while widget and not isinstance(widget, (CommandIcon, RoundedButton)):
            widget = widget.master
            if widget == self.root: widget = None; break

        if isinstance(widget, RoundedButton) and not widget.image:
            widget.set_pressed_state(False);
            if not self.widget_drag_active:
                 x, y = event.x, event.y; w, h = widget.winfo_width(), widget.winfo_height();
                 # Need relative coords if event was on a child
                 try:
                     rel_x = event.x_root - widget.winfo_rootx()
                     rel_y = event.y_root - widget.winfo_rooty()
                     if 0<=rel_x<w and 0<=rel_y<h: widget.set_hover_state(True)
                     else: widget.set_hover_state(False)
                 except: # Fallback if winfo fails during redraw/destroy
                      widget.set_hover_state(False)

            else: widget.set_hover_state(False)
        elif isinstance(widget, CommandIcon):
             # Handle hover state for CommandIcon if needed (e.g., on mouse release over it)
             if not self.widget_drag_active:
                 try:
                     rel_x = event.x_root - widget.winfo_rootx()
                     rel_y = event.y_root - widget.winfo_rooty()
                     w, h = widget.winfo_width(), widget.winfo_height()
                     if 0<=rel_x<w and 0<=rel_y<h: widget.on_enter(None) # Simulate enter if released over
                     else: widget.on_leave(None) # Simulate leave
                 except:
                     widget.on_leave(None) # Simulate leave on error

        if not self.widget_drag_active:
            moved_dist=abs(event.x_root-self.widget_press_x_root)+abs(event.y_root-self.widget_press_y_root); time_elapsed=event.time-self.widget_press_time
            if moved_dist<CLICK_MOVE_THRESHOLD and time_elapsed<CLICK_TIME_THRESHOLD:
                if self.widget_command_on_click:
                    print(f"Click detected. Running command: {getattr(self.widget_command_on_click, '__name__', 'lambda')}")
                    self.widget_command_on_click()
                else:
                     print("Click detected, but no command associated.")

        # Reset states
        self.widget_drag_active=False; self.widget_command_on_click=None; self.drag_start_x=None; self.drag_start_y=None


    def do_widget_move(self, event):
        if self.widget_command_on_click is None: return # Only drag if initiated on a widget
        if not self.widget_drag_active:
            moved_dist=abs(event.x_root-self.widget_press_x_root)+abs(event.y_root-self.widget_press_y_root)
            if moved_dist>=CLICK_MOVE_THRESHOLD:
                self.widget_drag_active=True
                print("Drag started.") # Debug print
                # Ensure press/hover states are removed from the original widget when drag starts
                widget = event.widget
                while widget and not isinstance(widget, (CommandIcon, RoundedButton)):
                    widget = widget.master
                    if widget == self.root: widget = None; break
                if isinstance(widget, RoundedButton) and not widget.image: widget.set_pressed_state(False); widget.set_hover_state(False)
                elif isinstance(widget, CommandIcon): widget.on_leave(None) # Ensure hover effect is off

        if self.widget_drag_active:
            # If drag just started, record the offset
            if self.drag_start_x is None:
                 self.drag_start_x=event.x_root-self.root.winfo_x()
                 self.drag_start_y=event.y_root-self.root.winfo_y()
                 print(f"Drag offset calculated: dx={self.drag_start_x}, dy={self.drag_start_y}") # Debug print
            # Calculate new window position and move the root window
            new_x=event.x_root-self.drag_start_x
            new_y=event.y_root-self.drag_start_y
            self.root.geometry(f"+{new_x}+{new_y}")

    # --- Background Drag Handlers (Unchanged) ---
    def start_move(self, event):
        # Only start background drag if not clicking on a widget managed by widget drag handlers
        if self.widget_command_on_click is None:
            self.drag_start_x=event.x_root-self.root.winfo_x(); self.drag_start_y=event.y_root-self.root.winfo_y()
    def stop_move(self, event): self.drag_start_x = None; self.drag_start_y = None
    def do_move(self, event):
        if self.drag_start_x is not None and self.drag_start_y is not None: new_x=event.x_root-self.drag_start_x; new_y=event.y_root-self.drag_start_y; self.root.geometry(f"+{new_x}+{new_y}")

    # --- Other Methods ---
    def _draw_bar_background(self): # Uses unscaled constants
        self.bar_canvas.delete("bar_bg"); width=self.bar_width; height=self.bar_height; radius=CORNER_RADIUS
        if width <= 0 or height <= 0: return # Avoid drawing if dimensions are invalid
        if radius*2>min(width,height): radius=min(width,height)/2
        radius=max(0,radius); x1,y1,x2,y2=0,0,width,height
        points=[x1+radius,y1, x2-radius,y1, x2,y1, x2,y1+radius, x2,y2-radius, x2,y2, x2-radius,y2, x1+radius,y2, x1,y2, x1,y2-radius, x1,y1+radius, x1,y1, x1+radius,y1]
        if points: self.bar_canvas.create_polygon(points, fill=BAR_BG_COLOR, outline="", smooth=True, tags="bar_bg")

    def get_command_details(self, name): # Unchanged
        for cmd in self.commands:
            if cmd["name"]==name: return cmd
        return None

    def _monitor_stderr(self, name, process):
        """
        Function executed in a separate thread to read stderr
        and schedule UI updates when the process finishes.
        """
        # Note: 'process' here is the returned Popen object
        pid = process.pid # Get the PID for logging
        print(f"[{name}] Monitoring stderr for PID: {pid}")
        try:
            # Read stderr line by line as long as it's available
            # Popen was called with text=True, so we receive strings
            for line in iter(process.stderr.readline, ''):
                if line: # Only print if the line is not empty
                    # Print directly to the main console's sys.stderr
                    print(f"[{name} stderr PID:{pid}]: {line.strip()}", file=sys.stderr)

            # Once stderr is closed (process terminated or stream closed)
            process.stderr.close() # Ensure the stream is closed
            process.wait() # Wait for the process to terminate completely to get the returncode

            return_code = process.returncode
            print(f"[{name}] Process PID {pid} finished with code: {return_code}")

            # Schedule the status check in the main Tkinter thread
            self.root.after(0, lambda n=name, p=pid, rc=return_code: self._check_process_end_status(n, p, rc))

        except ValueError:
            # Can happen if trying to read from a closed pipe after wait() has already been called
            # or if the process terminates very abruptly.
            print(f"[{name}] ValueError reading stderr for PID {pid}. Process likely terminated abruptly.", file=sys.stderr)
            # Still attempt to get the final status and update the UI
            final_rc = process.poll() # Get status without waiting again
            self.root.after(0, lambda n=name, p=pid, rc=final_rc: self._check_process_end_status(n, p, rc))
        except Exception as e:
            print(f"[{name}] Error reading stderr for PID {pid}: {e}", file=sys.stderr)
            # Still try to update the UI if the process is still tracked
            final_rc = process.poll()
            self.root.after(0, lambda n=name, p=pid, rc=final_rc: self._check_process_end_status(n, p, rc))
        finally:
            # Ensure wait() is called if there was an exception earlier
            # and the process might still be alive (though unlikely after the error)
            if process.poll() is None: # If it hasn't terminated yet
                try:
                    process.wait(timeout=0.1) # Short final wait
                except (subprocess.TimeoutExpired, ValueError): # Added ValueError here
                    # Could have already terminated between poll() and wait()
                    pass
                except Exception as final_e:
                    print(f"[{name}] Error during final wait for PID {pid}: {final_e}", file=sys.stderr)

            print(f"[{name}] Monitor thread for PID {pid} ending.")


    def _check_process_end_status(self, name, pid, return_code):
        """
        Called from the main thread (via root.after) to handle
        the end of a monitored process. Updates UI if necessary.
        """
        # Check if the terminated process is STILL considered active by us
        # (i.e., the user did NOT click "Stop" in the meantime)
        if name in self.processes and self.processes[name] == pid:
            # Yes, it finished on its own (or crashed) and was still active for us
            print(f"[{name}] Process PID {pid} ended on its own with code {return_code}. Updating UI.")
            icon_widget = self.ui_manager.icon_widgets.get(name)
            if icon_widget:
                icon_widget.set_state(False) # Update the icon to OFF

            del self.processes[name] # Remove from the active list

            if return_code is not None and return_code != 0:
                print(f"[{name}] Process PID {pid} exited unexpectedly or with error code {return_code}.", file=sys.stderr)
            elif return_code is None:
                print(f"[{name}] Process PID {pid} status unknown after termination (return code is None).", file=sys.stderr)

        elif pid not in self.processes.values():
            # The process terminated, but it was NOT (or no longer) in our self.processes list
            # or the PID no longer matches that name.
            # This usually means the user pressed 'Stop'.
            # The stop logic in toggle_command already handled the icon and self.processes.
            print(f"[{name}] Process PID {pid} ended, but was already removed or PID mismatch (likely stopped manually). No UI change needed from monitor.")
        else:
            # Rare case: the name is in self.processes but the PID no longer matches the one that terminated.
            # Could happen if a command is stopped and restarted very quickly.
            print(f"[{name}] Process PID {pid} ended, but the active PID for this name is now {self.processes.get(name)}. Ignoring stale end signal.")


    def toggle_command(self, name):
        icon_widget = self.ui_manager.icon_widgets.get(name)
        command_details = self.get_command_details(name)

        if not icon_widget: print(f"Error: Could not find UI widget for command '{name}'"); return
        if not command_details: print(f"Error: Could not find command details for '{name}'"); return

        command_str = command_details["command"]
        is_currently_on = name in self.processes

        if not is_currently_on:
            # --- STARTING PROCESS ---
            try:
                kwargs = {}
                platform_sys = platform.system()
                if platform_sys == "Windows":
                    # Import only on Windows to avoid errors on other OS
                    # Doing the import here for safety if it's not global
                    import subprocess as sp_win
                    kwargs['creationflags'] = sp_win.CREATE_NEW_PROCESS_GROUP
                else:
                    kwargs['start_new_session'] = True # For Linux/macOS

                global script_base_path # Ensure it's accessible
                kwargs['cwd'] = script_base_path # Keep current working directory

                # --- Command Parsing and Execution Logic ---
                use_shell = True
                cmd_list = None

                if command_str.startswith("python -m "): # Check if it's a python module command
                    try:
                        # Ensure sys is imported
                        # import sys # Hopefully already imported globally
                        parts = shlex.split(command_str)
                        if len(parts) >= 3 and parts[0] == 'python' and parts[1] == '-m':
                            cmd_list = [sys.executable] + parts[1:] # ['python_path', '-m', 'module.name', 'arg1', ...]
                            use_shell = False # Execute directly without shell
                            print(f"Executing with sys.executable: {cmd_list}") # Debug print
                        else:
                            print(f"Warning: Could not parse 'python -m' command correctly: {command_str}")
                    except Exception as parse_error:
                        print(f"Warning: Error parsing command string '{command_str}': {parse_error}")

                if cmd_list is None:
                    cmd_list = command_str # Use the original string
                    use_shell = True # Use shell for custom/unparsed commands
                    print(f"Executing with shell=True: {cmd_list}") # Debug print
                # -------------------------------------------

                # MODIFICATION: START PROCESS CAPTURING STDERR
                process = subprocess.Popen(cmd_list, shell=use_shell,
                                        stdout=subprocess.PIPE,    # Capture standard output instead of DEVNULL
                                        stderr=subprocess.PIPE,    # Capture error output
                                        text=True,       # Decode stderr as text (uses default encoding)
                                        encoding='utf-8', # Specify encoding for safety
                                        errors='replace', # Handles decoding errors
                                        bufsize=1,       # Line-buffered for stderr (more immediate output)
                                        **kwargs)

                # Store the PID immediately after launch
                self.processes[name] = process.pid
                icon_widget.set_state(True)
                print(f"Started: '{name}' (PID: {process.pid})")

                # --- START STDOUT AND STDERR MONITORING THREAD ---
                # Pass the 'process' object itself to the thread
                monitor_thread = threading.Thread(target=self._monitor_process_output, args=(name, process), daemon=True)
                # Daemon=True ensures the thread exits automatically if the main app closes
                monitor_thread.start()
                # ---------------------------------------------

            except Exception as e:
                print(f"Error starting '{name}': {e}", file=sys.stderr)
                # Ensure the icon is turned off if startup fails
                if icon_widget:
                    icon_widget.set_state(False)
                # Remove from the list if it was added before the error occurred
                if name in self.processes:
                    del self.processes[name]
        else:
            # --- STOPPING PROCESS ---
            pid_to_stop = self.processes.get(name) # Use get for safety
            if pid_to_stop:
                print(f"Stopping: '{name}' (PID: {pid_to_stop})...")

                # Remove the process from the list *before* attempting to kill
                # This signals to the monitoring thread (_check_process_end_status)
                # that the stop was intentional.
                del self.processes[name]

                # Attempt to terminate the process and its children
                killed = self.kill_process_tree(pid_to_stop)

                # Update the icon *after* removing from the list and attempting kill
                if icon_widget:
                    icon_widget.set_state(False)

                if killed:
                    print(f"Stopped: '{name}' (PID: {pid_to_stop}) successfully.")
                else:
                    print(f"Warning: Could not confirm stopping process for '{name}' (PID: {pid_to_stop}). It might already be gone or termination failed.")
            else:
                # If the name was in self.processes but PID wasn't found (unlikely)
                print(f"Warning: '{name}' was marked as running, but PID not found. Cleaning up state.")
                if icon_widget:
                    icon_widget.set_state(False)
                # Double-check and safe removal
                if name in self.processes:
                    try:
                        del self.processes[name]
                    except KeyError:
                        pass # Already removed, okay

    def kill_process_tree(self, pid): # Unchanged
        try:
            parent=psutil.Process(pid); children=parent.children(recursive=True); procs_to_kill=children+[parent]
            for proc in procs_to_kill:
                try:
                    if platform.system()=="Windows": proc.terminate()
                    else: proc.send_signal(signal.SIGTERM)
                except (psutil.NoSuchProcess, Exception): pass
            gone, alive=psutil.wait_procs(procs_to_kill, timeout=0.5)
            for proc in alive:
                try: proc.kill()
                except (psutil.NoSuchProcess, Exception): pass
            gone, alive=psutil.wait_procs(alive, timeout=0.5); return len(alive)==0
        except psutil.NoSuchProcess: return True # Process already gone
        except Exception as e: print(f"Error killing tree {pid}: {e}"); return False

    def hide_bar(self): # Uses unscaled constants (mostly unchanged, ensures geometry updates are correct)
        if self.is_hidden: return
        self.original_x=self.root.winfo_x(); self.original_y=self.root.winfo_y()
        # Store current width/height *before* hiding
        self.original_width = self.root.winfo_width()
        self.original_height = self.root.winfo_height() # Use current height which might have changed

        self.main_frame.pack_forget(); self.is_hidden=True
        new_size=f"{SHOW_BUTTON_SIZE}x{SHOW_BUTTON_SIZE}" # Unscaled
        # Center the small button relative to the bar's last position
        new_x=self.original_x+(self.original_width//2)-(SHOW_BUTTON_SIZE//2);
        new_y=self.original_y+(self.original_height//2)-(SHOW_BUTTON_SIZE//2)
        screen_width=self.root.winfo_screenwidth(); screen_height=self.root.winfo_screenheight()
        new_x=max(0,min(new_x, screen_width-SHOW_BUTTON_SIZE)); new_y=max(0,min(new_y, screen_height-SHOW_BUTTON_SIZE))

        self.root.geometry(f"{new_size}+{new_x}+{new_y}")
        self.root.config(bg=BG_COLOR_TRANSPARENT)
        try: self.show_button_frame.config(bg=BG_COLOR_TRANSPARENT); self.root.attributes("-transparentcolor", BG_COLOR_TRANSPARENT); self.root.attributes('-alpha', 0.99)
        except tk.TclError: self.root.attributes('-alpha', 0.85)

        self.show_button_frame.place(x=0, y=0, relwidth=1, relheight=1) # Place instead of pack for specific size

        # Ensure correct bindings for the show button frame and its content
        cmd_func=self.show_bar
        # Bind to the frame itself for drag events
        self.show_button_frame.bind("<Button-1>", lambda event, cmd=cmd_func: self.start_widget_move_or_click(event, cmd));
        self.show_button_frame.bind("<ButtonRelease-1>", self.stop_widget_move_or_click);
        self.show_button_frame.bind("<B1-Motion>", self.do_widget_move)
        # Bind to the button inside the frame as well, especially for the click action
        self.show_button.bind("<Button-1>", lambda event, cmd=cmd_func: self.start_widget_move_or_click(event, cmd));
        self.show_button.bind("<ButtonRelease-1>", self.stop_widget_move_or_click);
        self.show_button.bind("<B1-Motion>", self.do_widget_move) # Allow drag via button too


    def show_bar(self): # Uses unscaled constants (mostly unchanged, ensures geometry updates are correct)
        if not self.is_hidden: return
        self.show_button_frame.place_forget(); self.is_hidden=False
        self.root.config(bg=BG_COLOR_TRANSPARENT)
        try: self.root.attributes("-transparentcolor", BG_COLOR_TRANSPARENT); self.root.attributes('-alpha', 0.99)
        except tk.TclError: self.root.attributes('-alpha', BAR_BG_ALPHA)

        current_x=self.root.winfo_x(); current_y=self.root.winfo_y()
        # Restore centered based on the *updated* original height
        restored_x=current_x-(self.original_width//2)+(SHOW_BUTTON_SIZE//2);
        restored_y=current_y-(self.original_height//2)+(SHOW_BUTTON_SIZE//2) # Use potentially updated original_height
        screen_width=self.root.winfo_screenwidth(); screen_height=self.root.winfo_screenheight()
        restored_x=max(0,min(restored_x, screen_width-self.original_width));
        restored_y=max(0,min(restored_y, screen_height-self.original_height)) # Use potentially updated original_height

        # Use the potentially updated original_height when restoring geometry
        self.root.geometry(f"{self.original_width}x{self.original_height}+{restored_x}+{restored_y}")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        # Redraw background if needed after showing and resizing
        self.bar_canvas.config(height=self.original_height) # Ensure canvas matches restored height
        if not self.use_alpha_transparency:
            self._draw_bar_background()
        # Ensure content frame is correctly placed within the restored bar
        self.content_frame.place(x=BAR_PADDING_HORIZONTAL,y=BAR_PADDING_VERTICAL,
                                 width=self.bar_width-(2*BAR_PADDING_HORIZONTAL),
                                 height=self.original_height-(2*BAR_PADDING_VERTICAL))


    def on_close(self): # Unchanged
        print("Closing application, stopping all processes...")
        # Use self.processes which is correctly managed now
        for name, pid in list(self.processes.items()):
             print(f"Stopping '{name}' (PID: {pid}) on close.")
             self.kill_process_tree(pid)
        self.root.destroy()

    def _monitor_process_output(self, name, process):
        """
        Function executed in a separate thread to read stdout and stderr
        and schedule UI updates when the process finishes.
        """
        # Note: 'process' here is the returned Popen object
        pid = process.pid # Get the PID for logging
        print(f"[{name}] Monitoring output for PID: {pid}")
        
        # Create readers for both stdout and stderr
        stdout_reader = threading.Thread(target=self._read_stream, 
                                       args=(name, process, process.stdout, "stdout", pid), 
                                       daemon=True)
        stderr_reader = threading.Thread(target=self._read_stream, 
                                       args=(name, process, process.stderr, "stderr", pid), 
                                       daemon=True)
        
        # Start both threads
        stdout_reader.start()
        stderr_reader.start()
        
        # Wait for both to complete
        stdout_reader.join()
        stderr_reader.join()
        
        # Wait for the process to terminate completely to get the returncode
        process.wait()
        
        return_code = process.returncode
        print(f"[{name}] Process PID {pid} finished with code: {return_code}")
        
        # Schedule the status check in the main Tkinter thread
        self.root.after(0, lambda n=name, p=pid, rc=return_code: self._check_process_end_status(n, p, rc))
    
    def _read_stream(self, name, process, stream, stream_name, pid):
        """Read from a stream (stdout or stderr) and print to console."""
        try:
            # Read stream line by line as long as it's available
            for line in iter(stream.readline, ''):
                if line:  # Only print if the line is not empty
                    output = f"[{name} {stream_name} PID:{pid}]: {line.strip()}"
                    if stream_name == "stderr":
                        print(output, file=sys.stderr)
                    else:
                        print(output)
                        
            # Once stream is closed, ensure it's fully closed
            stream.close()
            
        except ValueError:
            # Can happen if trying to read from a closed pipe
            print(f"[{name}] ValueError reading {stream_name} for PID {pid}. Stream likely closed.", file=sys.stderr)
        except Exception as e:
            print(f"[{name}] Error reading {stream_name} for PID {pid}: {e}", file=sys.stderr)
        finally:
            print(f"[{name}] {stream_name} reader for PID {pid} ending.")

if __name__ == "__main__":
    if not PIL_AVAILABLE:
        print("----------------------------------------------------")
        print(" Pillow library is required for high-quality icons.")
        print(" Please install it via: pip install Pillow")
        print(" (Also requires: pip install matplotlib )")
        print("----------------------------------------------------")
    root = tk.Tk()
    root.withdraw()
    # --- Load Unscaled Tkinter Fonts ---
    FONT_BUTTON=get_tk_font(11); FONT_CLOSE_BUTTON=get_tk_font(9,"bold"); FONT_SHOW_BUTTON=get_tk_font(18)
    app = VerticalCommandBar(root)
    root.deiconify()
    root.mainloop()