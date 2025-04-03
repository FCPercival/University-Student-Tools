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
        
        args_info = tk.Label(args_label_frame, text="(One per line)", bg=BAR_BG_COLOR, fg=SEPARATOR_COLOR, anchor="w")
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
            self.current_command_index = index
            self.load_command_for_edit(self.commands[index])
            self.enable_edit_panel()
        else:
            self.disable_edit_panel()
    
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
                import shlex
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
        if tool == "custom" and args:
            # For custom, use the first arg as the full command
            command = args[0]
        else:
            # For built-in tools, build the proper command format
            command = f"cmd.exe /k python -m university_student_tools."
            if tool == "copy-files":
                command += f"file_manager.copy_files"
            elif tool == "image-clipboard":
                command += f"clipboard.image_clipboard"
            
            # Add arguments with quotes if they contain spaces
            for arg in args:
                if " " in arg and not (arg.startswith('"') and arg.endswith('"')):
                    command += f' "{arg}"'
                else:
                    command += f" {arg}"
        
        return {
            "name": name,
            "command": command,
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
        # Could implement logic to show tool-specific UI elements
        selected_tool = self.tool_var.get()
        print(f"Selected tool: {selected_tool}")
    
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

        # Calculations use unscaled constants
        num_icons=len(self.commands); icons_height=(num_icons*ICON_CANVAS_HEIGHT)+((num_icons-1)*ICON_PADDING_VERTICAL)
        extra_space=SEPARATOR_HEIGHT+BUTTON_HEIGHT*2+ICON_PADDING_VERTICAL*3; self.bar_width=ICON_SIZE+(2*ICON_CANVAS_WIDTH_PADDING)+(2*BAR_PADDING_HORIZONTAL)
        self.bar_height=icons_height+extra_space+(2*BAR_PADDING_VERTICAL); screen_width=root.winfo_screenwidth(); screen_height=root.winfo_screenheight()
        x=screen_width-self.bar_width-10; y=(screen_height-self.bar_height)//2; self.root.geometry(f"{self.bar_width}x{self.bar_height}+{x}+{y}")
        self.original_width=self.bar_width; self.original_height=self.bar_height

        self.main_frame=tk.Frame(root,bg=BG_COLOR_TRANSPARENT); self.main_frame.pack(fill=tk.BOTH,expand=True)
        self.bar_canvas=tk.Canvas(self.main_frame,width=self.bar_width,height=self.bar_height,bd=0,highlightthickness=0,bg=BG_COLOR_TRANSPARENT if not self.use_alpha_transparency else BAR_BG_COLOR)
        self.bar_canvas.place(x=0,y=0,relwidth=1,relheight=1);
        if not self.use_alpha_transparency: self._draw_bar_background()
        content_bg=BAR_BG_COLOR if not self.use_alpha_transparency else self.bar_canvas.cget('bg'); self.content_frame=tk.Frame(self.bar_canvas,bg=content_bg)

        self.processes={}; self.icon_widgets={}; self._icon_photo_refs=[]
        for cmd_data in self.commands:
             icon_canvas_width=self.bar_width-(2*BAR_PADDING_HORIZONTAL)
             icon=CommandIcon(self.content_frame,icon_canvas_width,ICON_CANVAS_HEIGHT,
                                command_name=cmd_data["name"],command_color=cmd_data["color"],command_action=self.toggle_command)
             if icon.icon_photoimage: self._icon_photo_refs.append(icon.icon_photoimage)
             icon.pack(side=tk.TOP,pady=(ICON_PADDING_VERTICAL//2, ICON_PADDING_VERTICAL//2),padx=0); self.icon_widgets[cmd_data["name"]]=icon
             cmd_func=lambda name=cmd_data["name"]: self.toggle_command(name)
             icon.bind("<Button-1>",lambda event,cmd=cmd_func: self.start_widget_move_or_click(event,cmd)); icon.bind("<ButtonRelease-1>",self.stop_widget_move_or_click); icon.bind("<B1-Motion>",self.do_widget_move)

        separator=tk.Canvas(self.content_frame,height=SEPARATOR_HEIGHT,bg=SEPARATOR_COLOR,highlightthickness=0)
        separator.pack(side=tk.TOP,fill=tk.X,padx=BAR_PADDING_HORIZONTAL,pady=ICON_PADDING_VERTICAL)
        self.separator = separator

        # Settings Button
        self.settings_button=RoundedButton(self.content_frame,self.bar_width-(2*(BAR_PADDING_HORIZONTAL+5)),BUTTON_HEIGHT,BUTTON_HEIGHT/2,
                                         text="Settings",command=self.open_settings,font=FONT_BUTTON,bg=content_bg)
        self.settings_button.pack(side=tk.TOP,pady=(0,ICON_PADDING_VERTICAL//2))
        self.settings_button.bind("<Button-1>",lambda event,cmd=self.settings_button.command: self.start_widget_move_or_click(event,cmd))
        self.settings_button.bind("<ButtonRelease-1>",self.stop_widget_move_or_click)
        self.settings_button.bind("<B1-Motion>",self.do_widget_move)
        
        # Hide Button 
        self.hide_button=RoundedButton(self.content_frame,self.bar_width-(2*(BAR_PADDING_HORIZONTAL+5)),BUTTON_HEIGHT,BUTTON_HEIGHT/2,
                                         text="Hide",command=self.hide_bar,font=FONT_BUTTON,bg=content_bg)
        self.hide_button.pack(side=tk.TOP,pady=(0,ICON_PADDING_VERTICAL//2))
        self.hide_button.bind("<Button-1>",lambda event,cmd=self.hide_button.command: self.start_widget_move_or_click(event,cmd))
        self.hide_button.bind("<ButtonRelease-1>",self.stop_widget_move_or_click)
        self.hide_button.bind("<B1-Motion>",self.do_widget_move)

        self.content_frame.place(x=BAR_PADDING_HORIZONTAL,y=BAR_PADDING_VERTICAL,width=self.bar_width-(2*BAR_PADDING_HORIZONTAL),height=self.bar_height-(2*BAR_PADDING_VERTICAL))
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
        for name in list(self.processes.keys()):
            self.toggle_command(name)  # Turn off any running processes
        
        # Clear existing icon widgets
        for widget in self.icon_widgets.values():
            widget.pack_forget() # Remove from layout
            widget.destroy()
        self.icon_widgets = {}
        self._icon_photo_refs = []
        
        #Remove separator and buttons from layout
        self.separator.pack_forget()
        self.settings_button.pack_forget()
        self.hide_button.pack_forget()

        # Reload commands
        try:
            self.commands = load_commands(self.command_file_path)
        except Exception as e:
            print(f"Error in loading commands from {self.command_file_path}: {e}")
            self.commands = [] # Proceed with an empty list in case of error
        
        # Recreate icons
        for cmd_data in self.commands:
            icon_canvas_width = self.bar_width - (2 * BAR_PADDING_HORIZONTAL)
            icon = CommandIcon(self.content_frame, icon_canvas_width, ICON_CANVAS_HEIGHT,
                             command_name=cmd_data["name"], command_color=cmd_data["color"], command_action=self.toggle_command)
            if icon.icon_photoimage:
                self._icon_photo_refs.append(icon.icon_photoimage)
            icon.pack(side=tk.TOP, pady=(ICON_PADDING_VERTICAL//2, ICON_PADDING_VERTICAL//2), padx=0)
            self.icon_widgets[cmd_data["name"]] = icon
            cmd_func = lambda name=cmd_data["name"]: self.toggle_command(name)
            icon.bind("<Button-1>", lambda event, cmd=cmd_func: self.start_widget_move_or_click(event, cmd))
            icon.bind("<ButtonRelease-1>", self.stop_widget_move_or_click)
            icon.bind("<B1-Motion>", self.do_widget_move)

        # Re-pack the separator and buttons at the bottom
        self.separator.pack(side=tk.TOP, fill=tk.X, padx=BAR_PADDING_HORIZONTAL, pady=ICON_PADDING_VERTICAL)
        self.settings_button.pack(side=tk.TOP, pady=(0, ICON_PADDING_VERTICAL//2))
        self.hide_button.pack(side=tk.TOP, pady=(0, ICON_PADDING_VERTICAL//2))

        # Update bar size based on new number of commands
        self.update_bar_size()
        
    def update_bar_size(self):
        # Recalculate bar size based on current number of commands
        num_icons = len(self.commands)
        icons_height = (num_icons * ICON_CANVAS_HEIGHT) + ((num_icons - 1) * ICON_PADDING_VERTICAL)
        extra_space = SEPARATOR_HEIGHT + BUTTON_HEIGHT * 2 + ICON_PADDING_VERTICAL * 3  # For settings and hide buttons
        self.bar_height = icons_height + extra_space + (2 * BAR_PADDING_VERTICAL)
        
        # Update geometry
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{self.bar_width}x{self.bar_height}+{x}+{y}")
        self.original_height = self.bar_height
        
        # Redraw background if needed
        if not self.use_alpha_transparency:
            self._draw_bar_background()
        
        # Update content frame
        self.content_frame.place(x=BAR_PADDING_HORIZONTAL, y=BAR_PADDING_VERTICAL, 
                              width=self.bar_width-(2*BAR_PADDING_HORIZONTAL), 
                              height=self.bar_height-(2*BAR_PADDING_VERTICAL))

    # --- Generic Widget Drag/Click Handlers (Unchanged) ---
    def start_widget_move_or_click(self, event, command_to_run):
        if isinstance(event.widget, RoundedButton) and not event.widget.image: event.widget.set_pressed_state(True)
        self.widget_press_x_root=event.x_root; self.widget_press_y_root=event.y_root; self.widget_press_time=event.time; self.widget_command_on_click=command_to_run; self.widget_drag_active=False; self.drag_start_x=None; self.drag_start_y=None
    def stop_widget_move_or_click(self, event):
        widget=event.widget;
        if isinstance(widget, RoundedButton) and not widget.image:
            widget.set_pressed_state(False);
            if not self.widget_drag_active:
                 x, y = event.x, event.y; w, h = widget.winfo_width(), widget.winfo_height();
                 if 0<=x<w and 0<=y<h: widget.set_hover_state(True)
                 else: widget.set_hover_state(False)
            else: widget.set_hover_state(False)
        if not self.widget_drag_active:
            moved_dist=abs(event.x_root-self.widget_press_x_root)+abs(event.y_root-self.widget_press_y_root); time_elapsed=event.time-self.widget_press_time
            if moved_dist<CLICK_MOVE_THRESHOLD and time_elapsed<CLICK_TIME_THRESHOLD:
                if self.widget_command_on_click: self.widget_command_on_click()
        self.widget_drag_active=False; self.widget_command_on_click=None; self.drag_start_x=None; self.drag_start_y=None
    def do_widget_move(self, event):
        if self.widget_command_on_click is None: return
        if not self.widget_drag_active:
            moved_dist=abs(event.x_root-self.widget_press_x_root)+abs(event.y_root-self.widget_press_y_root)
            if moved_dist>=CLICK_MOVE_THRESHOLD:
                self.widget_drag_active=True
                if isinstance(event.widget, RoundedButton) and not event.widget.image: event.widget.set_pressed_state(False); event.widget.set_hover_state(False)
        if self.widget_drag_active:
            if self.drag_start_x is None: self.drag_start_x=event.x_root-self.root.winfo_x(); self.drag_start_y=event.y_root-self.root.winfo_y()
            new_x=event.x_root-self.drag_start_x; new_y=event.y_root-self.drag_start_y; self.root.geometry(f"+{new_x}+{new_y}")

    # --- Background Drag Handlers (Unchanged) ---
    def start_move(self, event):
        if self.widget_command_on_click is None: self.drag_start_x=event.x_root-self.root.winfo_x(); self.drag_start_y=event.y_root-self.root.winfo_y()
    def stop_move(self, event): self.drag_start_x = None; self.drag_start_y = None
    def do_move(self, event):
        if self.drag_start_x is not None and self.drag_start_y is not None: new_x=event.x_root-self.drag_start_x; new_y=event.y_root-self.drag_start_y; self.root.geometry(f"+{new_x}+{new_y}")

    # --- Other Methods ---
    def _draw_bar_background(self): # Uses unscaled constants
        self.bar_canvas.delete("bar_bg"); width=self.bar_width; height=self.bar_height; radius=CORNER_RADIUS
        if radius*2>min(width,height): radius=min(width,height)/2
        radius=max(0,radius); x1,y1,x2,y2=0,0,width,height
        points=[x1+radius,y1, x2-radius,y1, x2,y1, x2,y1+radius, x2,y2-radius, x2,y2, x2-radius,y2, x1+radius,y2, x1,y2, x1,y2-radius, x1,y1+radius, x1,y1, x1+radius,y1]
        if points: self.bar_canvas.create_polygon(points, fill=BAR_BG_COLOR, outline="", smooth=True, tags="bar_bg")
    def get_command_details(self, name): # Unchanged
        for cmd in self.commands:
            if cmd["name"]==name: return cmd
        return None
    def toggle_command(self, name): # Unchanged (uses corrected syntax)
        icon_widget=self.icon_widgets.get(name); command_details=self.get_command_details(name)
        if not icon_widget or not command_details: print(f"Error: Could not find details for command '{name}'"); return
        command_str=command_details["command"]; is_currently_on=name in self.processes
        if not is_currently_on:
            try:
                kwargs={}; platform_sys=platform.system()
                if platform_sys=="Windows": kwargs['creationflags']=subprocess.CREATE_NEW_PROCESS_GROUP
                else: kwargs['start_new_session']=True
                process=subprocess.Popen(command_str,shell=True,**kwargs)
                self.processes[name]=process.pid; icon_widget.set_state(True); print(f"Started: '{name}' (PID: {process.pid})")
            except Exception as e: print(f"Error starting '{name}': {e}"); icon_widget.set_state(False)
        else:
            pid=self.processes[name]; print(f"Stopping: '{name}' (PID: {pid})...")
            killed=self.kill_process_tree(pid)
            if killed: print(f"Stopped: '{name}' (PID: {pid}) successfully.")
            else: print(f"Warning: Could not confirm stopping process for '{name}' (PID: {pid}).")
            if name in self.processes: del self.processes[name]
            icon_widget.set_state(False)
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
        except psutil.NoSuchProcess: return True
        except Exception as e: print(f"Error killing tree {pid}: {e}"); return False
    def hide_bar(self): # Uses unscaled constants
        if self.is_hidden: return
        self.original_x=self.root.winfo_x(); self.original_y=self.root.winfo_y()
        self.main_frame.pack_forget(); self.is_hidden=True
        new_size=f"{SHOW_BUTTON_SIZE}x{SHOW_BUTTON_SIZE}" # Unscaled
        new_x=self.original_x+(self.original_width//2)-(SHOW_BUTTON_SIZE//2); new_y=self.original_y+(self.original_height//2)-(SHOW_BUTTON_SIZE//2)
        screen_width=self.root.winfo_screenwidth(); screen_height=self.root.winfo_screenheight()
        new_x=max(0,min(new_x, screen_width-SHOW_BUTTON_SIZE)); new_y=max(0,min(new_y, screen_height-SHOW_BUTTON_SIZE))
        self.root.geometry(f"{new_size}+{new_x}+{new_y}")
        self.root.config(bg=BG_COLOR_TRANSPARENT)
        try: self.show_button_frame.config(bg=BG_COLOR_TRANSPARENT); self.root.attributes("-transparentcolor", BG_COLOR_TRANSPARENT); self.root.attributes('-alpha', 0.99)
        except tk.TclError: self.root.attributes('-alpha', 0.85)
        self.show_button_frame.place(x=0, y=0, relwidth=1, relheight=1)
        cmd_func=self.show_bar
        self.show_button_frame.bind("<Button-1>", lambda event, cmd=cmd_func: self.start_widget_move_or_click(event, cmd)); self.show_button_frame.bind("<ButtonRelease-1>", self.stop_widget_move_or_click); self.show_button_frame.bind("<B1-Motion>", self.do_widget_move)
        self.show_button.bind("<Button-1>", lambda event, cmd=cmd_func: self.start_widget_move_or_click(event, cmd)); self.show_button.bind("<ButtonRelease-1>", self.stop_widget_move_or_click); self.show_button.bind("<B1-Motion>", self.do_widget_move)
    def show_bar(self): # Uses unscaled constants
        if not self.is_hidden: return
        self.show_button_frame.place_forget(); self.is_hidden=False
        self.root.config(bg=BG_COLOR_TRANSPARENT)
        try: self.root.attributes("-transparentcolor", BG_COLOR_TRANSPARENT); self.root.attributes('-alpha', 0.99)
        except tk.TclError: self.root.attributes('-alpha', BAR_BG_ALPHA)
        current_x=self.root.winfo_x(); current_y=self.root.winfo_y()
        restored_x=current_x-(self.original_width//2)+(SHOW_BUTTON_SIZE//2); restored_y=current_y-(self.original_height//2)+(SHOW_BUTTON_SIZE//2)
        screen_width=self.root.winfo_screenwidth(); screen_height=self.root.winfo_screenheight()
        restored_x=max(0,min(restored_x, screen_width-self.original_width)); restored_y=max(0,min(restored_y, screen_height-self.original_height))
        self.root.geometry(f"{self.original_width}x{self.original_height}+{restored_x}+{restored_y}")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
    def on_close(self): # Unchanged
        print("Closing application, stopping all processes...")
        for name, pid in list(self.processes.items()): print(f"Stopping '{name}' (PID: {pid}) on close."); self.kill_process_tree(pid)
        self.root.destroy()

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